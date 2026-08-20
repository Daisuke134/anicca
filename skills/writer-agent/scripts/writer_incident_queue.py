#!/usr/bin/env python3
"""Durable, deduplicated Writer self-heal incident queue."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
from typing import Any


SCHEMA = "writer.self-heal.incident-queue"
VERSION = 1


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"schema": SCHEMA, "version": VERSION, "items": {}}
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema") != SCHEMA or value.get("version") != VERSION:
        raise ValueError("unsupported incident queue")
    if not isinstance(value.get("items"), dict):
        raise ValueError("incident queue items must be an object")
    return value


def _atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


CONTENT_REJECTION_STATUSES = ("400", "409", "415", "422", "451")


def _is_publisher_content_rejection(phase: str, text: str) -> bool:
    """A publisher refused this exact body; retrying the same bytes cannot help.

    This is deliberately narrower than "any 4xx".  401/403 are credential
    problems and 429 is a rate limit; both already have precise classes and are
    checked before this one.  The remaining content-bearing statuses mean the
    destination read the artifact and rejected it, which needs a different
    repair from a transport or process failure.
    """
    if not phase.startswith("destination:"):
        return False
    if not any(status in text for status in CONTENT_REJECTION_STATUSES):
        return False
    return any(
        token in text
        for token in (
            "invalid", "unprocessable", "rejected", "not allowed", "unsupported",
            "利用できない", "使用できない", "不正",
        )
    )


def _classification(phase: str, reason: str, signature: str = "") -> str:
    # A publisher often carries a terse `reason` and puts the real status and
    # message in `error_signature`; both are observed evidence of one failure.
    lowered = f"{reason}\n{signature}".lower()
    if reason == "invalid_receipt":
        return "state-corruption"
    if reason == "expected_receipt_missing":
        if phase == "metrics":
            return "measurement"
        if phase == "money":
            return "money-invariant"
        if phase == "readback" or phase.startswith("destination:"):
            return "publication-readback"
        if phase.startswith("gate:") or phase == "quality":
            return "content-quality"
        return "process"
    if "stale" in lowered:
        return "state-corruption"
    if "403" in lowered or "credential" in lowered or "unauthorized" in lowered:
        return "credential"
    if "429" in lowered or "rate-limit" in lowered or "rate_limit" in lowered:
        return "rate-limit"
    if _is_publisher_content_rejection(phase, lowered):
        return "publisher-content-rejection"
    if any(token in lowered for token in ("editor", "anchor", "selector", "dom")):
        return "DOM/selector"
    if "timeout" in lowered or "heartbeat" in lowered:
        return "process"
    if "provider" in lowered or "model" in lowered:
        return "provider"
    if "api" in lowered or "contract" in lowered:
        return "API-contract"
    if phase == "metrics":
        return "measurement"
    if phase == "money":
        return "money-invariant"
    return "process"


DESTINATION_IDENTITY_SCHEME = "run+artifact+destination+failure_class"

# A taxonomy refinement is not a new failure.  When a new precise class takes
# work away from a coarser one, the incident recorded under the coarse class is
# the same incident and MUST be adopted in place, keeping its lease, state,
# attempt history, and occurrences.  Only classes a new rule actually
# supersedes may be adopted; this never merges two independently classified
# failures on the same destination.
SUPERSEDED_FAILURE_CLASSES: dict[str, tuple[str, ...]] = {
    "publisher-content-rejection": ("process",),
}


def _digest(stable: dict[str, Any]) -> str:
    encoded = json.dumps(stable, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def _legacy_fingerprint(item: dict[str, Any]) -> str:
    """The pre-destination-identity key, kept so old incidents stay reachable."""
    source = item.get("source_receipt")
    source_path = source.get("path") if isinstance(source, dict) else None
    return _digest({
        "phase": item.get("phase"),
        "reason": item.get("reason"),
        "source_path": source_path,
    })


def _destination_identity(item: dict[str, Any], failure_class: str) -> str | None:
    run_id = item.get("run_id")
    artifact = item.get("artifact_id")
    destination = item.get("destination")
    if not (run_id and artifact and destination):
        return None
    return _digest({
        "scheme": DESTINATION_IDENTITY_SCHEME,
        "run_id": run_id,
        "artifact_id": artifact,
        "destination": destination,
        "failure_class": failure_class,
    })


def _fingerprint(item: dict[str, Any], failure_class: str) -> str:
    """One incident per run + artifact + destination + failure class.

    A publisher error signature is observed evidence, not identity: the same
    destination failing the same way must reuse one incident even when the
    publisher rewords its message.  Work that carries no destination identity
    keeps the original phase/reason/source key unchanged.
    """
    identity = _destination_identity(item, failure_class)
    return identity if identity is not None else _legacy_fingerprint(item)


def ingest(queue: dict[str, Any], replay: dict[str, Any], observed_at: str) -> dict[str, Any]:
    if replay.get("schema") != "writer.observability.slo-replay":
        raise ValueError("input is not Writer SLO replay")
    items = queue["items"]
    for work in replay.get("slo_work", []):
        if not isinstance(work, dict):
            continue
        phase = str(work.get("phase") or "unknown")
        reason = str(work.get("reason") or "unknown")
        signature = str(work.get("error_signature") or reason)
        failure_class = _classification(phase, reason, signature)
        fingerprint = _fingerprint(work, failure_class)
        occurrence = {
            "work_id": work.get("work_id"),
            "execution_id": work.get("execution_id"),
            "trace_id": work.get("trace_id"),
            "span_id": work.get("span_id"),
            "source_receipt": work.get("source_receipt"),
            "error_signature": signature,
            "observed_at": observed_at,
        }
        existing = items.get(fingerprint)
        if existing is None:
            # A refined taxonomy renames the same failure.  Reclaim the
            # incident stored under a class this rule superseded before
            # considering the pre-destination-identity key.
            for superseded in SUPERSEDED_FAILURE_CLASSES.get(failure_class, ()):
                previous = _destination_identity(work, superseded)
                if previous is None or previous == fingerprint:
                    continue
                reclassified = items.pop(previous, None)
                if reclassified is None:
                    continue
                reclassified["fingerprint"] = fingerprint
                reclassified["previous_fingerprint"] = previous
                reclassified["failure_class"] = failure_class
                reclassified["classification"] = failure_class
                items[fingerprint] = reclassified
                existing = reclassified
                break
        if existing is None:
            # An incident recorded before destination identity existed is the
            # same incident.  Adopt it in place, keeping its lease, state, and
            # attempt history, instead of opening a duplicate beside it.
            legacy = _legacy_fingerprint(work)
            adopted = items.pop(legacy, None) if legacy != fingerprint else None
            if adopted is not None:
                adopted["fingerprint"] = fingerprint
                adopted["previous_fingerprint"] = legacy
                adopted["failure_class"] = failure_class
                adopted.update({
                    key: work[key]
                    for key in ("run_id", "artifact_id", "destination",
                                "revenue_role", "blocking")
                    if work.get(key) is not None
                })
                items[fingerprint] = adopted
                existing = adopted
        if existing is None:
            items[fingerprint] = {
                "fingerprint": fingerprint,
                "phase": phase,
                "reason": reason,
                "classification": failure_class,
                "failure_class": failure_class,
                "error_signature": signature,
                **{
                    key: work[key]
                    for key in ("run_id", "artifact_id", "destination",
                                "revenue_role", "blocking")
                    if work.get(key) is not None
                },
                "state": "OPEN",
                "owner": "writer-self-heal",
                "first_seen_at": observed_at,
                "last_seen_at": observed_at,
                "occurrence_count": 1,
                "occurrences": [occurrence],
                "attempt_count": 0,
                "next_action": "CLAIM",
            }
            continue
        known = {str(row.get("work_id")) for row in existing.get("occurrences", [])}
        is_new_occurrence = str(occurrence["work_id"]) not in known
        if is_new_occurrence:
            existing.setdefault("occurrences", []).append(occurrence)
            existing["occurrence_count"] = len(existing["occurrences"])
        # Every distinct signature stays in `occurrences`; the top level tracks
        # the most recently observed one alongside `last_seen_at`.
        existing["error_signature"] = signature
        existing["last_seen_at"] = observed_at
        if existing.get("state") == "RESOLVED":
            existing["state"] = "OPEN"
            existing["next_action"] = "CLAIM"
            existing["regression_count"] = int(existing.get("regression_count", 0)) + 1
        elif (
            existing.get("state") == "FAILED"
            and isinstance(existing.get("exhausted"), dict)
            and is_new_occurrence
        ):
            # §9.3.1: an exhausted incident waits for a genuinely new trigger,
            # and a fresh occurrence of the same failure is exactly that. Only
            # incidents this queue escalated are re-armed, so a FAILED state set
            # by any other path keeps its meaning.
            existing["state"] = "OPEN"
            existing["next_action"] = "CLAIM"
            existing["rearmed_at"] = observed_at
            record = existing.pop("exhausted")
            existing.setdefault("exhaustion_history", []).append(record)
            existing["previous_exhaustion"] = record
            existing["rearmed_by"] = {
                "kind": "new-occurrence", "observed_at": observed_at,
            }
            existing["rearm_count"] = int(existing.get("rearm_count", 0)) + 1
    queue["updated_at"] = observed_at
    return queue


def claim(
    queue: dict[str, Any], lease_id: str, observed_at: str,
    fingerprint: str | None = None,
) -> dict[str, Any] | None:
    available = [item for item in queue["items"].values() if item.get("state") in {"OPEN", "RETRY"}]
    if fingerprint is not None:
        available = [item for item in available if item.get("fingerprint") == fingerprint]
    if not available:
        return None
    item = min(available, key=lambda row: (str(row.get("first_seen_at")), row["fingerprint"]))
    item["state"] = "CLAIMED"
    item["lease_id"] = lease_id
    item["claimed_at"] = observed_at
    item["attempt_count"] = int(item.get("attempt_count", 0)) + 1
    item["next_action"] = "RUNBOOK_OR_INVESTIGATE"
    queue["updated_at"] = observed_at
    return item


def resolve(
    queue: dict[str, Any], fingerprint: str, lease_id: str,
    effect_receipt: Path, observed_at: str,
) -> dict[str, Any]:
    item = queue["items"].get(fingerprint)
    if item is None:
        raise ValueError("unknown incident fingerprint")
    if item.get("state") != "CLAIMED" or item.get("lease_id") != lease_id:
        raise ValueError("incident is not claimed by this lease")
    if not effect_receipt.is_file() or effect_receipt.is_symlink():
        raise ValueError("real effect receipt is required")
    item["state"] = "RESOLVED"
    item["resolved_at"] = observed_at
    item["effect_receipt"] = {
        "path": str(effect_receipt.resolve()),
        "sha256": hashlib.sha256(effect_receipt.read_bytes()).hexdigest(),
    }
    item["next_action"] = "MONITOR_RECURRENCE"
    queue["updated_at"] = observed_at
    return item


def retry(
    queue: dict[str, Any], fingerprint: str, lease_id: str,
    runbook_receipt: Path, observed_at: str,
) -> dict[str, Any]:
    item = queue["items"].get(fingerprint)
    if item is None:
        raise ValueError("unknown incident fingerprint")
    if item.get("state") != "CLAIMED" or item.get("lease_id") != lease_id:
        raise ValueError("incident is not claimed by this lease")
    if not runbook_receipt.is_file() or runbook_receipt.is_symlink():
        raise ValueError("runbook receipt is required")
    item["state"] = "RETRY"
    item["last_runbook_receipt"] = {
        "path": str(runbook_receipt.resolve()),
        "sha256": hashlib.sha256(runbook_receipt.read_bytes()).hexdigest(),
    }
    item["next_action"] = "CLAIM"
    item.pop("lease_id", None)
    queue["updated_at"] = observed_at
    return item


def continue_investigation(
    queue: dict[str, Any], fingerprint: str, lease_id: str,
    attempt_receipt: Path, observed_at: str,
    next_action: str = "CONTINUE_INVESTIGATION",
) -> dict[str, Any]:
    """Release the lease on a checkpointed investigation so a later tick continues it.

    A lease bounds one tick's work.  Holding it across ticks would be a lock
    with no live holder and no expiry, which is exactly how an incident becomes
    permanently unselectable: `select()` considers only OPEN and RETRY, so a
    CLAIMED incident whose owner has exited can never be picked up again.  The
    checkpoint, not the lease, is what carries the investigation forward.
    """
    item = queue["items"].get(fingerprint)
    if item is None:
        raise ValueError("unknown incident fingerprint")
    if item.get("state") != "CLAIMED" or item.get("lease_id") != lease_id:
        raise ValueError("incident is not claimed by this lease")
    if not attempt_receipt.is_file() or attempt_receipt.is_symlink():
        raise ValueError("repair attempt receipt is required")
    item["state"] = "RETRY"
    item["last_attempt_receipt"] = {
        "path": str(attempt_receipt.resolve()),
        "sha256": hashlib.sha256(attempt_receipt.read_bytes()).hexdigest(),
    }
    item["next_action"] = next_action
    item["released_at"] = observed_at
    item.pop("lease_id", None)
    queue["updated_at"] = observed_at
    return item


# §9.3.1 escalation, taken from Flagger, Argo Rollouts, SapFix and the
# circuit-breaker pattern rather than invented: bounded attempts, then degrade
# to the safest known state, then stop and wait for a genuinely new trigger.
# FAILED already sits outside `select()`, so an escalated incident stops
# consuming ticks entirely instead of being re-claimed without bound.
EXHAUSTION_NEXT_ACTIONS = {
    "routing-failure": "ESCALATE_AFTER_ROUTING_FAILURE_BUDGET_EXHAUSTED",
    "investigation-slices": "ESCALATE_AFTER_INVESTIGATION_BUDGET_EXHAUSTED",
    # H2's bounded repair attempts degrade through this same mechanism rather
    # than through a second one, so `rearm_on_new_code` and `ingest` re-arm a
    # spent repair budget exactly as they re-arm a spent investigation budget.
    "repair-candidates": "ESCALATE_AFTER_REPAIR_CANDIDATE_BUDGET_EXHAUSTED",
}


def escalate_exhausted(
    queue: dict[str, Any], fingerprint: str, lease_id: str,
    attempt_receipt: Path, observed_at: str, *, kind: str,
    failure_count: int, trigger: Any, reason: str,
    deployed_commit: str | None = None,
) -> dict[str, Any]:
    """Stop working an incident that has spent its bounded attempts.

    Nothing is deleted or rewritten: occurrences, attempt history and every
    receipt stay exactly as they are.  Only the state and the next action
    change, so the incident stops consuming ticks until `ingest` observes a
    genuinely new occurrence.
    """
    if kind not in EXHAUSTION_NEXT_ACTIONS:
        raise ValueError(f"unsupported exhaustion kind: {kind}")
    item = queue["items"].get(fingerprint)
    if item is None:
        raise ValueError("unknown incident fingerprint")
    if item.get("state") != "CLAIMED" or item.get("lease_id") != lease_id:
        raise ValueError("incident is not claimed by this lease")
    if not attempt_receipt.is_file() or attempt_receipt.is_symlink():
        raise ValueError("repair attempt receipt is required")
    item["state"] = "FAILED"
    item["exhausted"] = {
        "kind": kind,
        "count": failure_count,
        "trigger": trigger,
        "reason": reason,
        "observed_at": observed_at,
        # The code version this incident failed under, so a later deploy can be
        # recognised as the new input that makes it eligible again.
        "deployed_commit": deployed_commit,
    }
    item["last_attempt_receipt"] = {
        "path": str(attempt_receipt.resolve()),
        "sha256": hashlib.sha256(attempt_receipt.read_bytes()).hexdigest(),
    }
    item["next_action"] = EXHAUSTION_NEXT_ACTIONS[kind]
    item["escalated_at"] = observed_at
    item.pop("lease_id", None)
    queue["updated_at"] = observed_at
    return item


# A deploy re-arms an exhausted incident, but a permanently unfixable incident
# must not be re-armed by every deploy forever. Bound the number of rounds a
# code change may buy; after that only a genuinely new occurrence -- a real new
# signal from the world, not from us -- can revive it.
DEFAULT_MAX_CODE_REARM_ROUNDS = 3


def rearm_on_new_code(
    queue: dict[str, Any], deployed_commit: str | None, observed_at: str,
    max_rounds: int = DEFAULT_MAX_CODE_REARM_ROUNDS,
) -> list[dict[str, Any]]:
    """Make incidents exhausted under older code eligible again after a deploy.

    Without this the loop cannot close: every incident that failed under the
    old code stays dead forever, so a deployed repair can never be validated by
    the very thing it repaired. SSOT §9.3.1 takes the rule from Flagger, which
    "does not retry until a new commit arrives".

    Nothing is erased. The exhaustion record is moved into
    `exhaustion_history`, occurrences and every receipt are untouched, and the
    incident carries a visible round counter under the new code version.
    """
    if not deployed_commit:
        # Fail closed: an unreadable marker is not evidence of a new version.
        return []
    rearmed: list[dict[str, Any]] = []
    for fingerprint, item in queue.get("items", {}).items():
        if not isinstance(item, dict) or item.get("state") != "FAILED":
            continue
        record = item.get("exhausted")
        if not isinstance(record, dict):
            continue
        previous_commit = record.get("deployed_commit")
        if previous_commit == deployed_commit:
            continue  # same code; nothing new has arrived
        rounds = int(item.get("code_rearm_rounds", 0))
        if rounds >= max_rounds:
            item["code_rearm_capped"] = {
                "rounds": rounds,
                "max_rounds": max_rounds,
                "reason": (
                    "this incident has already been re-armed by a code change "
                    f"{rounds} times and exhausted its budget each time; only a "
                    "genuinely new occurrence can revive it now"
                ),
                "observed_at": observed_at,
            }
            continue
        item["state"] = "OPEN"
        item["next_action"] = "CLAIM"
        item["rearmed_at"] = observed_at
        item.pop("exhausted", None)
        item.setdefault("exhaustion_history", []).append(record)
        item["previous_exhaustion"] = record
        item["code_rearm_rounds"] = rounds + 1
        item["rearmed_by"] = {
            "kind": "deployed-commit-change",
            "from": previous_commit,
            "to": deployed_commit,
            "round": rounds + 1,
            "observed_at": observed_at,
        }
        rearmed.append({
            "fingerprint": fingerprint,
            "from_deployed_commit": previous_commit,
            "to_deployed_commit": deployed_commit,
            "round": rounds + 1,
            "previous_exhaustion_kind": record.get("kind"),
        })
    if rearmed:
        queue["updated_at"] = observed_at
    return rearmed


def register_runbook_decision(
    queue: dict[str, Any], fingerprint: str, lease_id: str,
    decision_receipt: Path, observed_at: str,
) -> dict[str, Any]:
    """Bind a KNOWN routing decision to its incident without executing it.

    The mirror of `register_investigation` for the deterministic branch: it
    records which runbook was selected and at which version, and leaves the
    incident CLAIMED under the same lease so the Order 5 worker that actually
    runs the command owns an unambiguous, receipted instruction.
    """
    item = queue["items"].get(fingerprint)
    if item is None:
        raise ValueError("unknown incident fingerprint")
    if item.get("state") != "CLAIMED" or item.get("lease_id") != lease_id:
        raise ValueError("incident is not claimed by this lease")
    if not decision_receipt.is_file() or decision_receipt.is_symlink():
        raise ValueError("runbook decision receipt is required")
    receipt = json.loads(decision_receipt.read_text(encoding="utf-8"))
    if (
        receipt.get("schema") != "writer.self-heal.runbook-decision"
        or receipt.get("version") != 1
        or receipt.get("fingerprint") != fingerprint
        or receipt.get("route") != "KNOWN"
        or receipt.get("executed") is not False
        or not isinstance(receipt.get("runbook_id"), str)
        or not receipt.get("runbook_id")
        or len(str(receipt.get("command_sha256") or "")) != 64
        or receipt.get("next_action") != "EXECUTE_BOUNDED_RUNBOOK"
    ):
        raise ValueError("runbook decision receipt does not name an unexecuted runbook")
    item["runbook_decision_receipt"] = {
        "path": str(decision_receipt.resolve()),
        "sha256": hashlib.sha256(decision_receipt.read_bytes()).hexdigest(),
        "runbook_id": receipt["runbook_id"],
        "runbook_version": receipt.get("runbook_version"),
        "mode": receipt.get("mode"),
        "command_sha256": receipt["command_sha256"],
    }
    item["routed_at"] = observed_at
    item["next_action"] = "EXECUTE_BOUNDED_RUNBOOK"
    queue["updated_at"] = observed_at
    return item


def register_investigation(
    queue: dict[str, Any], fingerprint: str, lease_id: str,
    investigation_receipt: Path, observed_at: str,
) -> dict[str, Any]:
    item = queue["items"].get(fingerprint)
    if item is None:
        raise ValueError("unknown incident fingerprint")
    if item.get("state") != "CLAIMED" or item.get("lease_id") != lease_id:
        raise ValueError("incident is not claimed by this lease")
    if not investigation_receipt.is_file() or investigation_receipt.is_symlink():
        raise ValueError("investigation receipt is required")
    receipt = json.loads(investigation_receipt.read_text(encoding="utf-8"))
    if (
        receipt.get("schema") != "writer.self-heal.unknown-investigation"
        or receipt.get("version") != 1
        or receipt.get("fingerprint") != fingerprint
    ):
        raise ValueError("investigation receipt does not match incident")
    next_action = receipt.get("next_action")
    if next_action not in {
        "COLLECT_GAPS_THEN_SEARCH_OFFICIAL_PRIMARY_DOCS",
        "CHARACTERIZE_PREEXISTING_EFFECT_RECONCILIATION",
    }:
        raise ValueError("investigation next action is unsupported")
    item["investigation_receipt"] = {
        "path": str(investigation_receipt.resolve()),
        "sha256": hashlib.sha256(investigation_receipt.read_bytes()).hexdigest(),
        "cause_status": receipt.get("cause_status"),
    }
    item["investigated_at"] = observed_at
    item["next_action"] = next_action
    queue["updated_at"] = observed_at
    return item


def register_characterization(
    queue: dict[str, Any], fingerprint: str, lease_id: str,
    characterization_receipt: Path, observed_at: str,
) -> dict[str, Any]:
    item = queue["items"].get(fingerprint)
    if item is None:
        raise ValueError("unknown incident fingerprint")
    if item.get("state") != "CLAIMED" or item.get("lease_id") != lease_id:
        raise ValueError("incident is not claimed by this lease")
    if not characterization_receipt.is_file() or characterization_receipt.is_symlink():
        raise ValueError("characterization receipt is required")
    receipt = json.loads(characterization_receipt.read_text(encoding="utf-8"))
    test_path = receipt.get("test_path")
    changed_paths = receipt.get("changed_paths")
    if (
        receipt.get("schema") != "writer.self-heal.characterization-receipt"
        or receipt.get("version") != 1
        or receipt.get("status") != "RED_VERIFIED"
        or receipt.get("fingerprint") != fingerprint
        or not isinstance(receipt.get("observed_exit_code"), int)
        or receipt.get("observed_exit_code") == 0
        or not isinstance(receipt.get("failure_signature"), str)
        or not receipt.get("failure_signature")
        or not isinstance(test_path, str)
        or not test_path.startswith("skills/writer-agent/tests/")
        or not isinstance(changed_paths, list)
        or test_path not in changed_paths
        or not all(
            isinstance(path, str)
            and path.startswith("skills/writer-agent/tests/")
            for path in changed_paths
        )
        or receipt.get("next_action") != "GENERATE_CANDIDATE_FIX"
    ):
        raise ValueError("characterization receipt does not prove captured RED")
    test_sha256 = next(
        (
            change.get("sha256")
            for change in receipt.get("change_receipts", [])
            if isinstance(change, dict) and change.get("path") == test_path
        ),
        None,
    )
    item["characterization_receipt"] = {
        "path": str(characterization_receipt.resolve()),
        "sha256": hashlib.sha256(characterization_receipt.read_bytes()).hexdigest(),
        "status": receipt["status"],
        "test_path": test_path,
        "test_sha256": test_sha256,
        "failure_signature": receipt["failure_signature"],
    }
    item["characterized_at"] = observed_at
    item["next_action"] = "GENERATE_CANDIDATE_FIX"
    queue["updated_at"] = observed_at
    return item


def register_candidate(
    queue: dict[str, Any], fingerprint: str, lease_id: str,
    candidate_receipt: Path, observed_at: str,
) -> dict[str, Any]:
    item = queue["items"].get(fingerprint)
    if item is None:
        raise ValueError("unknown incident fingerprint")
    if item.get("state") != "CLAIMED" or item.get("lease_id") != lease_id:
        raise ValueError("incident is not claimed by this lease")
    if not candidate_receipt.is_file() or candidate_receipt.is_symlink():
        raise ValueError("candidate verification receipt is required")
    receipt = json.loads(candidate_receipt.read_text(encoding="utf-8"))
    commit = receipt.get("feature_commit")
    artifacts = receipt.get("artifacts")
    invariants = receipt.get("invariants")
    if (
        receipt.get("schema")
        != "writer.self-heal.candidate-verification-receipt"
        or receipt.get("version") != 1
        or receipt.get("status") != "CANDIDATE_VERIFIED"
        or receipt.get("fingerprint") != fingerprint
        or not isinstance(commit, str)
        or len(commit) != 40
        or any(char not in "0123456789abcdef" for char in commit)
        or not isinstance(artifacts, list)
        or not artifacts
        or not all(
            isinstance(artifact, dict)
            and isinstance(artifact.get("path"), str)
            and artifact["path"].startswith("skills/writer-agent/")
            and isinstance(artifact.get("sha256"), str)
            and len(artifact["sha256"]) == 64
            and all(char in "0123456789abcdef" for char in artifact["sha256"])
            for artifact in artifacts
        )
        or invariants != {
            "draft_is_public": False,
            "incident_resolved": False,
            "deployed": False,
        }
        or receipt.get("next_action")
        != "VERIFY_SENSITIVE_REPAIR_IN_ISOLATED_FIXTURE"
    ):
        raise ValueError("candidate receipt does not prove a safe verified fix")
    item["candidate_receipt"] = {
        "path": str(candidate_receipt.resolve()),
        "sha256": hashlib.sha256(candidate_receipt.read_bytes()).hexdigest(),
        "status": receipt["status"],
        "feature_commit": commit,
    }
    item["candidate_verified_at"] = observed_at
    item["next_action"] = "VERIFY_SENSITIVE_REPAIR_IN_ISOLATED_FIXTURE"
    queue["updated_at"] = observed_at
    return item


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", required=True, type=Path)
    parser.add_argument("--observed-at", required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    ingest_parser = sub.add_parser("ingest")
    ingest_parser.add_argument("--slo-replay", required=True, type=Path)
    claim_parser = sub.add_parser("claim")
    claim_parser.add_argument("--lease-id", required=True)
    claim_parser.add_argument("--fingerprint")
    resolve_parser = sub.add_parser("resolve")
    resolve_parser.add_argument("--fingerprint", required=True)
    resolve_parser.add_argument("--lease-id", required=True)
    resolve_parser.add_argument("--effect-receipt", required=True, type=Path)
    retry_parser = sub.add_parser("retry")
    retry_parser.add_argument("--fingerprint", required=True)
    retry_parser.add_argument("--lease-id", required=True)
    retry_parser.add_argument("--runbook-receipt", required=True, type=Path)
    route_parser = sub.add_parser("route")
    route_parser.add_argument("--fingerprint", required=True)
    route_parser.add_argument("--lease-id", required=True)
    route_parser.add_argument("--decision-receipt", required=True, type=Path)
    investigate_parser = sub.add_parser("investigate")
    investigate_parser.add_argument("--fingerprint", required=True)
    investigate_parser.add_argument("--lease-id", required=True)
    investigate_parser.add_argument("--investigation-receipt", required=True, type=Path)
    characterize_parser = sub.add_parser("characterize")
    characterize_parser.add_argument("--fingerprint", required=True)
    characterize_parser.add_argument("--lease-id", required=True)
    characterize_parser.add_argument("--characterization-receipt", required=True, type=Path)
    candidate_parser = sub.add_parser("candidate")
    candidate_parser.add_argument("--fingerprint", required=True)
    candidate_parser.add_argument("--lease-id", required=True)
    candidate_parser.add_argument("--candidate-receipt", required=True, type=Path)
    args = parser.parse_args()
    lock_path = args.queue.with_name(f".{args.queue.name}.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        queue = _read(args.queue)
        if args.command == "ingest":
            replay = json.loads(args.slo_replay.read_text(encoding="utf-8"))
            result = ingest(queue, replay, args.observed_at)
        elif args.command == "claim":
            result = claim(queue, args.lease_id, args.observed_at, args.fingerprint)
        elif args.command == "resolve":
            result = resolve(
                queue, args.fingerprint, args.lease_id,
                args.effect_receipt, args.observed_at,
            )
        elif args.command == "retry":
            result = retry(
                queue, args.fingerprint, args.lease_id,
                args.runbook_receipt, args.observed_at,
            )
        elif args.command == "route":
            result = register_runbook_decision(
                queue, args.fingerprint, args.lease_id,
                args.decision_receipt, args.observed_at,
            )
        elif args.command == "investigate":
            result = register_investigation(
                queue, args.fingerprint, args.lease_id,
                args.investigation_receipt, args.observed_at,
            )
        elif args.command == "characterize":
            result = register_characterization(
                queue, args.fingerprint, args.lease_id,
                args.characterization_receipt, args.observed_at,
            )
        else:
            result = register_candidate(
                queue, args.fingerprint, args.lease_id,
                args.candidate_receipt, args.observed_at,
            )
        _atomic(args.queue, queue)
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
