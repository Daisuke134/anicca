#!/usr/bin/env python3
"""Wire the H2 repair channel into the installed loop. SSOT §9.3.1 item H2.

`writer_repair_candidate.py` was built, tested and then called from nothing, so
H2 had no production receipt.  This module is the caller.  It picks the one
incident that a completed investigation has already handed to this stage, runs
the channel's own `prepare` and `execute` against it, and registers the outcome
through the queue's existing `register_candidate` consumer.  It stops there:
deploying the candidate, resuming the work item, and the public readback are
Order 5.

**Where this runs, and why not in the resume tick.**  The resume tick fires
every 300 s and holds the publication lock for its whole body; the repair
channel's budget is 900 s for the model plus up to 900 s for the test gate.  A
120-second investigation inside that lock was already measured as a starvation
risk for publication, for `ai.anicca.article-zenn-retry` and for the 06:00
creator, which is why `writer_repair_dispatch` defers its model call whenever
the tick owes publication work.  A repair is an order of magnitude worse, and it
cannot be deferred the same way without never running at all.  It therefore runs
under its own launchd label, `ai.anicca.article-repair-candidate`, which never
takes the publication lock, never plans or performs publication, and never
creates a run.  The alternatives and why they were rejected:

| Placement | Rejected because |
|---|---|
| slice the repair per tick like the investigation | the channel's unit of work is one attempt -- write, gate, then verify or hard-revert -- and it has no mid-attempt resume point.  Slicing it means building a second checkpoint layer beside H3's and still holding the lock across a model turn |
| run it outside the lock inside the same tick | the resume worker *is* the single same-run recovery owner.  Occupying it for up to 30 minutes stops publication recovery for 30 minutes even with the lock released, and launchd coalesces the ticks it misses |
| its own label plus its own repair-only lock | the incident queue already has an exclusive advisory lock and the incidents already carry leases.  A second lock beside them is the parallel mechanism §9.3.1 warns against, and launchd will not start a second copy of one label anyway |
| its own label, no publication lock (**chosen**) | publication cannot be delayed by something that never asks for its lock, and R6 is preserved because this label neither creates the daily run nor recovers it |

**Concurrency** is the queue's own `fcntl` lock plus the lease that already
exists.  An incident that reaches a verdict is deliberately left `CLAIMED` so it
stops consuming ticks; `writer_repair_dispatch.select` ignores `CLAIMED`
entirely, so the resume tick can never race this worker.  Between two repair
workers, selection and the in-flight marker are written inside one locked
read/write pair, so the second worker sees `REPAIR_CANDIDATE_IN_PROGRESS` and
finds nothing repair-ready.  The lease is never rotated: the same lease the
investigation handed over is the lease `register_candidate` is called with.

**Bounds** are the channel's own.  This module invents no second budget: the
attempt count, the trigger token and the degrade-and-stop rule all come from
`writer_repair_candidate` and `writer_repair_investigation_session`.  The one
bound added here covers the case those cannot see -- a repair that fails before
`prepare` returns a plan, which would otherwise re-run every tick forever, the
way routing failures did until they were bounded.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import time
from pathlib import Path
from typing import Any


SCRIPTS = Path(__file__).resolve().parent


def _module(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:  # pragma: no cover - import machinery guard
        raise RuntimeError(f"cannot load {name}")
    spec.loader.exec_module(module)
    return module


incidents = _module("writer_incident_queue")
candidate = _module("writer_repair_candidate")
session = _module("writer_repair_investigation_session")
dispatch_module = _module("writer_repair_dispatch")

_queue_lock = dispatch_module._queue_lock
priority = dispatch_module.priority

SCHEMA = "writer.self-heal.repair-candidate-attempt"
VERSION = 1

# The budgets are the channel's, referenced rather than restated.
DEFAULT_MAX_CANDIDATE_ATTEMPTS = candidate.DEFAULT_MAX_CANDIDATE_ATTEMPTS
DEFAULT_BUDGET_SECONDS = candidate.DEFAULT_BUDGET_SECONDS

# The only bound this module adds, for the failure mode the channel cannot see.
DEFAULT_MAX_PREPARATION_FAILURES = 3

# Written under the queue's own lock in the same read/write pair as selection,
# so a second worker cannot see the incident as repair-ready.
IN_PROGRESS = "REPAIR_CANDIDATE_IN_PROGRESS"

# The next actions a completed investigation hands to this stage. Anything else
# -- a runbook decision, an unrouted claim, a characterization still owed, a
# candidate already verified -- belongs to another stage and is left alone.
REPAIR_READY_NEXT_ACTIONS = frozenset({
    "COLLECT_GAPS_THEN_SEARCH_OFFICIAL_PRIMARY_DOCS",
    "GENERATE_CANDIDATE_FIX",
})

EXHAUSTION_KIND = "repair-candidates"

PREPARATION_DEGRADE_REASON = (
    "the repair channel could not even be prepared {count} times for this "
    "trigger, so no attempt was ever charged against its bounded budget; per "
    "SSOT §9.3.1 the loop degrades to the safest known state and stops until a "
    "genuinely new trigger arrives"
)


# ---------------------------------------------------------------------------
# selection
# ---------------------------------------------------------------------------

def repair_ready(item: Any, state_root: Path) -> bool:
    """Is this the incident a completed investigation handed to the repair stage?

    Four independent facts must hold, and the verdict is the decisive one: an
    incident that is merely `CLAIMED` -- by a runbook handoff, by a live
    investigation, by a stranded pre-checkpoint lease -- has no completed
    verdict and is therefore invisible here.
    """
    if not isinstance(item, dict):
        return False
    fingerprint = str(item.get("fingerprint") or "")
    if candidate.FINGERPRINT_RE.fullmatch(fingerprint) is None:
        return False
    if item.get("state") != "CLAIMED" or not item.get("lease_id"):
        return False
    if item.get("candidate_receipt") is not None:
        return False
    if item.get("next_action") not in REPAIR_READY_NEXT_ACTIONS:
        return False
    checkpoint = session.read_checkpoint(state_root, fingerprint)
    if not isinstance(checkpoint, dict) or checkpoint.get("status") != "COMPLETE":
        return False
    verdict = checkpoint.get("verdict")
    return isinstance(verdict, dict) and verdict.get("complete") is True


def select(queue: dict[str, Any], state_root: Path) -> dict[str, Any] | None:
    """Blocking revenue-set work first, then oldest first -- the queue's order."""
    ready = [
        item for item in queue.get("items", {}).values()
        if repair_ready(item, state_root)
    ]
    if not ready:
        return None
    return min(ready, key=priority)


# ---------------------------------------------------------------------------
# durable helpers
# ---------------------------------------------------------------------------

def _atomic(path: Path, value: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)
    return path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _release(item: dict[str, Any]) -> None:
    """Drop this worker's bookkeeping so the queue row stays readable."""
    item.pop("repair_candidate_started_at", None)
    item.pop("repair_candidate_previous_next_action", None)


# ---------------------------------------------------------------------------
# the tick
# ---------------------------------------------------------------------------

def dispatch(
    *, state_root: Path, repo: Path, base_ref: str, repair_root: Path,
    model_runner: Path, observed_at: str,
    budget_seconds: int = DEFAULT_BUDGET_SECONDS,
    max_attempts: int = DEFAULT_MAX_CANDIDATE_ATTEMPTS,
    max_preparation_failures: int = DEFAULT_MAX_PREPARATION_FAILURES,
    test_commands: list[list[str]] | None = None,
    environment: dict[str, str] | None = None,
    source_registry: dict[str, Any] | None = None,
    getter: Any | None = None,
) -> dict[str, Any]:
    """Run at most one bounded repair attempt for at most one incident."""
    state_root = Path(state_root).resolve()
    self_heal = state_root / "self-heal"
    queue_path = self_heal / "incident-queue.json"
    if not queue_path.is_file():
        return {"status": "NO_INCIDENT_QUEUE", "observed_at": observed_at}

    # ---- select and take the incident out of the repair-ready set ---------
    with _queue_lock(queue_path) as queue:
        chosen = select(queue, state_root)
        if chosen is None:
            return {
                "status": "NO_REPAIR_READY_INCIDENT", "observed_at": observed_at,
            }
        fingerprint = str(chosen["fingerprint"])
        lease_id = str(chosen["lease_id"])
        previous_next_action = str(chosen["next_action"])
        item = queue["items"][fingerprint]
        item["next_action"] = IN_PROGRESS
        item["repair_candidate_started_at"] = observed_at
        item["repair_candidate_previous_next_action"] = previous_next_action

    started = time.monotonic()
    deployed_commit = session.read_deployed_commit(state_root)
    investigation = session.read_checkpoint(state_root, fingerprint) or {}
    trigger = session.trigger_token(
        (investigation.get("trigger") or {}).get("occurrence_count"),
        deployed_commit,
    )
    attempt_receipt: dict[str, Any] = {
        "schema": SCHEMA, "version": VERSION,
        "observed_at": observed_at,
        "fingerprint": fingerprint,
        "lease_id": lease_id,
        "run_id": chosen.get("run_id"),
        "destination": chosen.get("destination"),
        "revenue_role": chosen.get("revenue_role"),
        "blocking": chosen.get("blocking"),
        "handed_over_from": previous_next_action,
        "trigger": trigger,
        "deployed_commit": deployed_commit,
        "repo_path": str(Path(repo).resolve()),
        "base_ref": base_ref,
        "max_attempts": max_attempts,
        "budget_seconds": budget_seconds,
        # This stage stops at a verified candidate. Order 5 owns the rest.
        "invariants": {
            "draft_is_public": False, "incident_resolved": False, "deployed": False,
        },
    }
    attempt_path = self_heal / "repair-candidate-attempts" / f"{fingerprint}-{lease_id}.json"

    # ---- prepare, outside the publication lock and outside the queue lock --
    try:
        plan = candidate.prepare(
            repo=Path(repo), base_ref=base_ref, repair_root=Path(repair_root),
            state_root=state_root, fingerprint=fingerprint,
            observed_at=observed_at, max_attempts=max_attempts,
            test_commands=test_commands,
            # The destination is what makes a curated source registry resolvable
            # without asking a model to recall a URL. It is read from the queue
            # row this worker already holds, so no second read is introduced.
            destination=chosen.get("destination"),
            source_registry=source_registry, getter=getter,
        )
    except Exception as error:  # noqa: BLE001 - every failure must be recorded
        return _preparation_failed(
            error=error, attempt=attempt_receipt, attempt_path=attempt_path,
            queue_path=queue_path, fingerprint=fingerprint, lease_id=lease_id,
            previous_next_action=previous_next_action, observed_at=observed_at,
            trigger=trigger, deployed_commit=deployed_commit,
            max_preparation_failures=max_preparation_failures, started=started,
        )

    if plan.get("status") == "EXHAUSTED":
        attempt_receipt["stage"] = "PREPARE"
        attempt_receipt["outcome"] = "REPAIR_BUDGET_EXHAUSTED"
        attempt_receipt["attempts_used"] = plan.get("attempts_used")
        attempt_receipt["reason"] = plan.get("reason")
        attempt_receipt["next_action"] = "WAIT_FOR_NEW_TRIGGER"
        attempt_receipt["latency_ms"] = int((time.monotonic() - started) * 1000)
        path = _atomic(attempt_path, attempt_receipt)
        with _queue_lock(queue_path) as queue:
            incidents.escalate_exhausted(
                queue, fingerprint, lease_id, path, observed_at,
                kind=EXHAUSTION_KIND,
                failure_count=int(plan.get("attempts_used") or 0),
                trigger=plan.get("trigger"), reason=str(plan.get("reason") or ""),
                deployed_commit=deployed_commit,
            )
            _release(queue["items"][fingerprint])
        return {
            "status": "REPAIR_BUDGET_EXHAUSTED", "observed_at": observed_at,
            "fingerprint": fingerprint, "lease_id": lease_id,
            "attempts_used": plan.get("attempts_used"),
            "reason": plan.get("reason"),
            "repair_attempt_receipt": str(path),
        }

    attempt_receipt["stage"] = "EXECUTE"
    attempt_receipt["attempt"] = plan.get("attempt")
    attempt_receipt["branch"] = plan.get("branch")
    attempt_receipt["workspace_path"] = plan.get("workspace_path")
    attempt_receipt["base_head"] = plan.get("base_head")
    attempt_receipt["test_commands_sha256"] = plan.get("test_commands_sha256")

    # ---- one bounded attempt ----------------------------------------------
    try:
        receipt = candidate.execute(
            plan=plan, model_runner=Path(model_runner), observed_at=observed_at,
            budget_seconds=budget_seconds, environment=environment,
        )
    except Exception as error:  # noqa: BLE001 - a crashed attempt must not strand
        attempt_receipt["outcome"] = "REPAIR_FAILED"
        attempt_receipt["error"] = f"{type(error).__name__}: {error}"
        attempt_receipt["next_action"] = previous_next_action
        attempt_receipt["latency_ms"] = int((time.monotonic() - started) * 1000)
        path = _atomic(attempt_path, attempt_receipt)
        with _queue_lock(queue_path) as queue:
            item = queue["items"][fingerprint]
            item["next_action"] = previous_next_action
            item["repair_candidate_last_error"] = {
                "observed_at": observed_at,
                "error": attempt_receipt["error"],
                "attempt": plan.get("attempt"),
                "receipt": {"path": str(path), "sha256": _sha256(path)},
            }
            _release(item)
            queue["updated_at"] = observed_at
        return {
            "status": "REPAIR_FAILED", "observed_at": observed_at,
            "fingerprint": fingerprint, "lease_id": lease_id,
            "error": attempt_receipt["error"],
            "repair_attempt_receipt": str(path),
        }

    receipt_path = Path(receipt["receipt_path"])
    attempt_receipt["candidate_receipt"] = {
        "path": str(receipt_path), "sha256": _sha256(receipt_path),
        "status": receipt["status"],
    }
    attempt_receipt["tokens"] = receipt.get("tokens")
    attempt_receipt["latency_ms"] = int((time.monotonic() - started) * 1000)

    if receipt["status"] == "CANDIDATE_VERIFIED":
        attempt_receipt["outcome"] = "CANDIDATE_VERIFIED"
        attempt_receipt["feature_commit"] = receipt["feature_commit"]
        attempt_receipt["next_action"] = candidate.NEXT_ACTION
        path = _atomic(attempt_path, attempt_receipt)
        with _queue_lock(queue_path) as queue:
            # The only consumer, and it accepts nothing but a green candidate.
            # The lease is the one the investigation handed over; the incident
            # stays CLAIMED as a handoff to Order 5.
            incidents.register_candidate(
                queue, fingerprint, lease_id, receipt_path, observed_at,
            )
            _release(queue["items"][fingerprint])
        return {
            "status": "CANDIDATE_VERIFIED", "observed_at": observed_at,
            "fingerprint": fingerprint, "lease_id": lease_id,
            "attempt": plan["attempt"], "max_attempts": max_attempts,
            "feature_commit": receipt["feature_commit"],
            "branch": plan["branch"],
            "candidate_receipt": str(receipt_path),
            "repair_attempt_receipt": str(path),
            "next_action": candidate.NEXT_ACTION,
        }

    # Discarded: record why, hand the incident back to the repair-ready set and
    # let the channel's own bound decide when to stop.
    attempt_receipt["outcome"] = "CANDIDATE_DISCARDED"
    attempt_receipt["failed_check"] = receipt.get("failed_check")
    attempt_receipt["reason"] = receipt.get("reason")
    attempt_receipt["revert"] = receipt.get("revert")
    attempt_receipt["next_action"] = previous_next_action
    path = _atomic(attempt_path, attempt_receipt)
    with _queue_lock(queue_path) as queue:
        item = queue["items"][fingerprint]
        item["next_action"] = previous_next_action
        item["repair_candidate_last_discard"] = {
            "observed_at": observed_at,
            "attempt": plan["attempt"],
            "max_attempts": max_attempts,
            "failed_check": receipt.get("failed_check"),
            "reason": receipt.get("reason"),
            "receipt": {"path": str(receipt_path), "sha256": _sha256(receipt_path)},
        }
        _release(item)
        queue["updated_at"] = observed_at
    return {
        "status": "CANDIDATE_DISCARDED", "observed_at": observed_at,
        "fingerprint": fingerprint, "lease_id": lease_id,
        "attempt": plan["attempt"], "max_attempts": max_attempts,
        "failed_check": receipt.get("failed_check"),
        "reason": receipt.get("reason"),
        "candidate_receipt": str(receipt_path),
        "repair_attempt_receipt": str(path),
    }


def _preparation_failed(
    *, error: BaseException, attempt: dict[str, Any], attempt_path: Path,
    queue_path: Path, fingerprint: str, lease_id: str,
    previous_next_action: str, observed_at: str, trigger: Any,
    deployed_commit: str | None, max_preparation_failures: int, started: float,
) -> dict[str, Any]:
    """A repair that never started still must not spin every tick forever.

    `writer_repair_candidate` charges a slot only once it has written a plan, so
    a failure before that point is invisible to its budget. The routing path had
    exactly this hole and produced eleven identical receipts on a five-minute
    cadence before it was bounded; this is the same bound, keyed on the same
    trigger token, escalated through the same queue API.
    """
    attempt["stage"] = "PREPARE"
    attempt["error"] = f"{type(error).__name__}: {error}"
    attempt["latency_ms"] = int((time.monotonic() - started) * 1000)
    if isinstance(error, candidate.UnresolvableSourcesError):
        # A refusal must be readable per URL, or "no evidence" and "evidence we
        # failed to fetch" collapse into one indistinguishable receipt.
        attempt["source_resolution"] = {
            "status": error.status,
            "rows": error.resolution,
        }

    with _queue_lock(queue_path) as queue:
        item = queue["items"][fingerprint]
        prior = (
            int(item.get("repair_preparation_failure_count", 0))
            if item.get("repair_preparation_failure_trigger") == trigger else 0
        )
        count = prior + 1
    attempt["preparation_failure_count"] = count
    attempt["max_preparation_failures"] = max_preparation_failures
    exhausted = count >= max_preparation_failures
    reason = PREPARATION_DEGRADE_REASON.format(count=count)
    attempt["outcome"] = (
        "REPAIR_PREPARATION_EXHAUSTED" if exhausted else "REPAIR_FAILED"
    )
    attempt["next_action"] = (
        "WAIT_FOR_NEW_TRIGGER" if exhausted else previous_next_action
    )
    if exhausted:
        attempt["reason"] = reason
    path = _atomic(attempt_path, attempt)

    with _queue_lock(queue_path) as queue:
        if exhausted:
            incidents.escalate_exhausted(
                queue, fingerprint, lease_id, path, observed_at,
                kind=EXHAUSTION_KIND, failure_count=count, trigger=trigger,
                reason=reason, deployed_commit=deployed_commit,
            )
            item = queue["items"][fingerprint]
            item.pop("repair_preparation_failure_count", None)
            item.pop("repair_preparation_failure_trigger", None)
        else:
            item = queue["items"][fingerprint]
            item["next_action"] = previous_next_action
            item["repair_preparation_failure_count"] = count
            item["repair_preparation_failure_trigger"] = trigger
            item["repair_candidate_last_error"] = {
                "observed_at": observed_at,
                "error": attempt["error"],
                "receipt": {"path": str(path), "sha256": _sha256(path)},
            }
        _release(queue["items"][fingerprint])
        queue["updated_at"] = observed_at

    result = {
        "status": attempt["outcome"], "observed_at": observed_at,
        "fingerprint": fingerprint, "lease_id": lease_id,
        "error": attempt["error"],
        "preparation_failure_count": count,
        "repair_attempt_receipt": str(path),
    }
    if exhausted:
        result["reason"] = reason
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-root", required=True, type=Path)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--base-ref", required=True)
    parser.add_argument("--repair-root", required=True, type=Path)
    parser.add_argument("--model-runner", required=True, type=Path)
    parser.add_argument("--observed-at", required=True)
    parser.add_argument(
        "--budget-seconds", type=int,
        default=int(os.environ.get(
            "ARTICLE_REPAIR_BUDGET_SECONDS", DEFAULT_BUDGET_SECONDS,
        )),
    )
    parser.add_argument(
        "--max-preparation-failures", type=int,
        default=DEFAULT_MAX_PREPARATION_FAILURES,
    )
    args = parser.parse_args()
    outcome = dispatch(
        state_root=args.state_root,
        repo=args.repo,
        base_ref=args.base_ref,
        repair_root=args.repair_root,
        model_runner=args.model_runner,
        observed_at=args.observed_at,
        budget_seconds=args.budget_seconds,
        max_preparation_failures=args.max_preparation_failures,
    )
    print(json.dumps(outcome, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
