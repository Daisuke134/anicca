#!/usr/bin/env python3
"""One bounded research recovery for an unpublished replacement quality block."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
from typing import Any


MAX_INVOCATIONS = 2
STATE_NAME = "quality-feedback-recovery-state.json"


class QualityFeedbackRecoveryError(ValueError):
    """The run cannot safely enter or advance feedback recovery."""


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return None
    return value if isinstance(value, dict) else None


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _atomic_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _refused(reason: str) -> dict[str, str]:
    return {"status": "REFUSED", "reason": reason}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _owner_is_alive(owner_pid: Any) -> bool:
    if not isinstance(owner_pid, int) or owner_pid <= 0:
        return False
    try:
        os.kill(owner_pid, 0)
    except (OSError, ValueError):
        return False
    return True


def _age_seconds(timestamp: Any) -> float | None:
    if not isinstance(timestamp, str):
        return None
    try:
        started = datetime.fromisoformat(timestamp)
    except ValueError:
        return None
    if started.tzinfo is None:
        return None
    return (datetime.now(timezone.utc) - started).total_seconds()


def _is_quality_audit(row: dict[str, Any]) -> bool:
    state = row.get("state")
    return bool(
        row.get("platform") == "quality"
        and row.get("published") is False
        and isinstance(state, str)
        and state.startswith("carry-over:quality-block:")
    )


def _ledger_has_delivery_row(ledger: Path, run_id: str) -> bool:
    if not ledger.exists():
        return False
    for line in ledger.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except (json.JSONDecodeError, TypeError):
            continue
        if (
            isinstance(row, dict)
            and row.get("run_id") == run_id
            and not _is_quality_audit(row)
        ):
            return True
    return False


def _feedback_for_terminal(gates: Path, run_id: str) -> dict[str, Any] | None:
    quality = _read_json(gates / "quality-self-heal.json")
    if (
        quality is None
        or quality.get("version") != 2
        or quality.get("action") != "block_freeze"
        or int(quality.get("attempt", 0)) < 2
        or not isinstance(quality.get("quality"), dict)
    ):
        return None
    scripts = Path(__file__).resolve().parent
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from article_daily_start_control import (  # pylint: disable=import-outside-toplevel
        _quality_failure_feedback,
    )

    feedback = _quality_failure_feedback(gates, run_id, quality["quality"])
    if feedback is None:
        return None
    for lang in ("ja", "en"):
        draft = gates.parent / f"article-{lang}.md"
        if (
            draft.is_symlink()
            or not draft.is_file()
            or feedback["article_sha256"].get(lang) != _sha256(draft)
        ):
            return None
    return feedback


def plan(run_dir: Path | str, ledger: Path | str) -> dict[str, Any]:
    run_dir = Path(run_dir).resolve()
    ledger = Path(ledger).resolve()
    gates = run_dir / "gates"
    if not run_dir.is_dir() or not gates.is_dir():
        return _refused("run-directory-missing")
    if (gates / "publication-state.json").exists():
        return _refused("publication-state-exists")
    if _ledger_has_delivery_row(ledger, run_dir.name):
        return _refused("ledger-row-exists")
    replacement = _read_json(gates / "quality-replacement.json")
    if (
        replacement is None
        or replacement.get("replacement_run_id") != run_dir.name
        or not isinstance(replacement.get("replaced_run_id"), str)
    ):
        return _refused("not-a-quality-replacement")
    prior_repair = _read_json(gates / "quality-repair-state.json")
    if prior_repair is not None and prior_repair.get("status") != "terminal-blocked":
        return _refused("prior-quality-repair-not-terminal")

    state_path = gates / STATE_NAME
    state = _read_json(state_path)
    if state is not None:
        prompt = Path(str(state.get("prompt_path", "")))
        attempts = int(state.get("attempts", 0))
        if (
            state.get("status") in {"prepared", "retryable-incomplete"}
            and attempts < MAX_INVOCATIONS
            and prompt.is_file()
            and state.get("prompt_sha256") == _sha256(prompt)
        ):
            return {
                "status": "READY",
                "reason": "prepared-quality-feedback-recovery",
                "run_id": run_dir.name,
                "run_dir": str(run_dir),
                "prompt_path": str(prompt),
                "prompt_sha256": state["prompt_sha256"],
                "attempts": attempts,
            }
        age = _age_seconds(state.get("started_at"))
        if (
            state.get("status") == "invoking"
            and attempts < MAX_INVOCATIONS
            and not _owner_is_alive(state.get("owner_pid"))
            and age is not None
            and age >= 60
            and prompt.is_file()
            and state.get("prompt_sha256") == _sha256(prompt)
        ):
            return {
                "status": "READY",
                "reason": "orphaned-quality-feedback-recovery",
                "run_id": run_dir.name,
                "run_dir": str(run_dir),
                "prompt_path": str(prompt),
                "prompt_sha256": state["prompt_sha256"],
                "attempts": attempts,
            }
        return _refused(
            "quality-feedback-recovery-already-"
            + str(state.get("status", "unknown"))
        )

    feedback = _feedback_for_terminal(gates, run_dir.name)
    if feedback is None:
        return _refused("terminal-quality-feedback-invalid")
    return {
        "status": "READY",
        "reason": "terminal-quality-feedback",
        "run_id": run_dir.name,
        "run_dir": str(run_dir),
        "feedback": feedback,
    }


def _recovery_prompt(run_dir: Path, ledger: Path, feedback: Path) -> str:
    script = Path(__file__).resolve()
    return f"""Run ONE bounded feedback research recovery for this unpublished Writer run.

RUN_DIR={run_dir}
LEDGER={ledger}
FEEDBACK_PLAN={feedback}
ORIGINAL_PROMPT={run_dir / "article-daily-prompt.txt"}

Hard boundaries:
- This call must research each feedback item before rewriting either draft.
- Do not monitor or wait for the parent owner, recovery state, or this model process. The parent waits for this call; start research immediately.
- Do not create another run, choose another topic, weaken a gate, stage, or publish early.
- Keep gates/topic-route.json immutable. Add evidence under RUN_DIR/research/feedback-recovery/.
- Use primary sources where available. Never fabricate a quote, result, price, or experience.
- Write gates/quality-feedback-consumption.json with version=1, the exact feedback_plan_sha256, current JA/EN draft SHA-256 values, and exact-one item for every feedback ID. Each item needs feedback_id, source_name, https source_url, concrete evidence, and languages. Every source_url must appear in the final Sources block of each listed language.
- Rewrite both drafts from the researched evidence and a new outline. Then run the deterministic, editorial, identity, and reader gates for both current hashes.
- Run quality_self_heal.py assess. A missing or incomplete consumption receipt must remain block_freeze.
- Run `python3 {script} verify --run-dir "$ARTICLE_RUN_DIR"` and require status=PASS.
- Only after assess returns ready_to_freeze and verify returns PASS, read ORIGINAL_PROMPT and continue STEP 4.8 through STEP 20 for this same run. Note remains ¥500 and both Substack posts remain paid-only. Require authenticated and public readback.
"""


def begin(run_dir: Path | str, ledger: Path | str) -> dict[str, Any]:
    run_dir = Path(run_dir).resolve()
    ledger = Path(ledger).resolve()
    decision = plan(run_dir, ledger)
    if (
        decision.get("status") != "READY"
        or decision.get("reason") != "terminal-quality-feedback"
    ):
        raise QualityFeedbackRecoveryError(
            str(decision.get("reason", "not-ready"))
        )
    gates = run_dir / "gates"
    feedback = dict(decision["feedback"])
    feedback["drafts"] = dict(feedback["article_sha256"])
    plan_path = gates / "quality-feedback-plan.json"
    _atomic_write(plan_path, feedback)
    prompt_path = gates / "quality-feedback-recovery/epoch-1/prompt.txt"
    prompt_path.parent.mkdir(parents=True, exist_ok=False)
    prompt_path.write_text(
        _recovery_prompt(run_dir, ledger, plan_path),
        encoding="utf-8",
    )
    state = {
        "version": 1,
        "status": "prepared",
        "run_id": run_dir.name,
        "attempts": 0,
        "feedback_sha256": feedback["feedback_sha256"],
        "feedback_plan_path": str(plan_path),
        "route_sha256": _sha256(gates / "topic-route.json"),
        "prompt_path": str(prompt_path),
        "prompt_sha256": _sha256(prompt_path),
    }
    _atomic_write(gates / STATE_NAME, state)
    return state


def mark_invoking(
    run_dir: Path | str,
    ledger: Path | str,
    *,
    owner_pid: int,
) -> dict[str, Any]:
    run_dir = Path(run_dir).resolve()
    decision = plan(run_dir, ledger)
    if decision.get("status") != "READY" or decision.get("reason") not in {
        "prepared-quality-feedback-recovery",
        "orphaned-quality-feedback-recovery",
    }:
        raise QualityFeedbackRecoveryError(
            str(decision.get("reason", "not-prepared"))
        )
    state_path = run_dir / "gates" / STATE_NAME
    state = _read_json(state_path)
    if state is None:
        raise QualityFeedbackRecoveryError("feedback-recovery-state-missing")
    if state.get("route_sha256") != _sha256(run_dir / "gates/topic-route.json"):
        raise QualityFeedbackRecoveryError("feedback-recovery-route-changed")
    attempts = int(state.get("attempts", 0)) + 1
    if attempts > MAX_INVOCATIONS:
        raise QualityFeedbackRecoveryError("feedback-recovery-attempt-limit")
    if attempts > 1:
        old_prompt = Path(str(state.get("prompt_path", "")))
        old_hash = str(state.get("prompt_sha256", ""))
        prompt_dir = run_dir / "gates/quality-feedback-recovery/epoch-1"
        archived = prompt_dir / f"prompt-attempt-{attempts - 1}.txt"
        if archived.exists():
            if not archived.is_file() or _sha256(archived) != old_hash:
                raise QualityFeedbackRecoveryError(
                    "feedback-recovery-prompt-archive-conflicts"
                )
        else:
            shutil.copy2(old_prompt, archived)
        if _sha256(archived) != old_hash:
            raise QualityFeedbackRecoveryError(
                "feedback-recovery-prompt-archive-mismatch"
            )
        feedback_plan = Path(str(state.get("feedback_plan_path", "")))
        new_prompt = prompt_dir / f"prompt-attempt-{attempts}.txt"
        new_prompt.write_text(
            _recovery_prompt(
                run_dir,
                Path(ledger).resolve(),
                feedback_plan,
            ),
            encoding="utf-8",
        )
        state.update(
            {
                "prompt_path": str(new_prompt),
                "prompt_sha256": _sha256(new_prompt),
            }
        )
    state.update(
        {
            "status": "invoking",
            "attempts": attempts,
            "owner_pid": owner_pid,
            "started_at": _utc_now(),
        }
    )
    _atomic_write(state_path, state)
    return state


def validate_consumption(run_dir: Path | str) -> dict[str, Any]:
    run_dir = Path(run_dir).resolve()
    gates = run_dir / "gates"
    state = _read_json(gates / STATE_NAME)
    feedback = _read_json(gates / "quality-feedback-plan.json")
    consumption = _read_json(gates / "quality-feedback-consumption.json")
    if state is None or feedback is None:
        return {"status": "FAIL", "reason": "feedback-plan-missing"}
    if consumption is None:
        return {"status": "FAIL", "reason": "feedback-consumption-missing"}
    if (
        feedback.get("feedback_sha256") != state.get("feedback_sha256")
        or consumption.get("feedback_plan_sha256")
        != state.get("feedback_sha256")
        or consumption.get("version") != 1
    ):
        return {"status": "FAIL", "reason": "feedback-consumption-identity-mismatch"}

    drafts: dict[str, str] = {}
    for lang in ("ja", "en"):
        path = run_dir / f"article-{lang}.md"
        if path.is_symlink() or not path.is_file():
            return {"status": "FAIL", "reason": f"draft-{lang}-missing"}
        drafts[lang] = _sha256(path)
    if consumption.get("drafts") != drafts:
        return {"status": "FAIL", "reason": "feedback-consumption-draft-mismatch"}

    planned_items = feedback.get("items")
    consumed_items = consumption.get("items")
    if not isinstance(planned_items, list) or not isinstance(consumed_items, list):
        return {"status": "FAIL", "reason": "feedback-items-invalid"}
    planned = {
        item.get("id"): item
        for item in planned_items
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    consumed: dict[str, dict[str, Any]] = {}
    for item in consumed_items:
        if not isinstance(item, dict):
            return {"status": "FAIL", "reason": "feedback-consumption-item-invalid"}
        feedback_id = item.get("feedback_id")
        if not isinstance(feedback_id, str) or feedback_id in consumed:
            return {"status": "FAIL", "reason": "feedback-consumption-id-invalid"}
        consumed[feedback_id] = item
    if set(consumed) != set(planned):
        return {"status": "FAIL", "reason": "feedback-consumption-coverage-mismatch"}

    for feedback_id, item in consumed.items():
        source_name = item.get("source_name")
        source_url = item.get("source_url")
        evidence = item.get("evidence")
        languages = item.get("languages")
        if (
            not isinstance(source_name, str)
            or not source_name.strip()
            or not isinstance(source_url, str)
            or re.fullmatch(r"https://\S+", source_url) is None
            or not isinstance(evidence, str)
            or not evidence.strip()
            or not isinstance(languages, list)
            or not languages
            or any(lang not in {"ja", "en"} for lang in languages)
            or planned[feedback_id].get("lang") not in languages
        ):
            return {"status": "FAIL", "reason": "feedback-evidence-invalid"}
        for lang in languages:
            article = (run_dir / f"article-{lang}.md").read_text(encoding="utf-8")
            if source_url not in article:
                return {
                    "status": "FAIL",
                    "reason": f"feedback-source-not-visible:{feedback_id}:{lang}",
                }
    return {
        "status": "PASS",
        "feedback_ids": [item["id"] for item in planned_items],
        "drafts": drafts,
        "feedback_plan_sha256": state["feedback_sha256"],
    }


def verify(run_dir: Path | str) -> dict[str, Any]:
    run_dir = Path(run_dir).resolve()
    result = validate_consumption(run_dir)
    _atomic_write(
        run_dir / "gates/quality-feedback-verification.json",
        result,
    )
    return result


def record_result(
    run_dir: Path | str,
    ledger: Path | str,
    *,
    return_code: int,
    owner_pid: int,
    caller_parent_pid: int | None = None,
) -> dict[str, Any]:
    run_dir = Path(run_dir).resolve()
    ledger = Path(ledger).resolve()
    gates = run_dir / "gates"
    state_path = gates / STATE_NAME
    state = _read_json(state_path)
    if state is None or state.get("status") != "invoking":
        raise QualityFeedbackRecoveryError("feedback-recovery-not-invoking")
    actual_parent_pid = os.getppid() if caller_parent_pid is None else caller_parent_pid
    if state.get("owner_pid") != owner_pid or actual_parent_pid != owner_pid:
        raise QualityFeedbackRecoveryError("feedback-recovery-result-owner-mismatch")
    attempts = int(state.get("attempts", 0))
    quality = _read_json(gates / "quality-self-heal.json")
    if (gates / "publication-state.json").is_file():
        status = "handed-to-publication"
    elif _ledger_has_delivery_row(ledger, run_dir.name):
        status = "terminal-ambiguous-ledger-without-publication-state"
    elif attempts < MAX_INVOCATIONS:
        status = "retryable-incomplete"
    elif (
        quality is not None
        and quality.get("action") == "ready_to_freeze"
        and validate_consumption(run_dir).get("status") == "PASS"
    ):
        status = "terminal-ready-not-published"
    else:
        status = "terminal-blocked"
    state.update(
        {
            "status": status,
            "return_code": return_code,
            "finished_at": _utc_now(),
        }
    )
    _atomic_write(state_path, state)
    return state


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=("plan", "begin", "invoke", "verify", "result"),
    )
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--ledger", type=Path)
    parser.add_argument("--owner-pid", type=int)
    parser.add_argument("--return-code", type=int)
    args = parser.parse_args()
    if args.command == "verify":
        value = verify(args.run_dir)
    else:
        if args.ledger is None:
            parser.error("--ledger is required")
        if args.command == "plan":
            value = plan(args.run_dir, args.ledger)
        elif args.command == "begin":
            value = begin(args.run_dir, args.ledger)
        elif args.command == "invoke":
            if args.owner_pid is None:
                parser.error("--owner-pid is required for invoke")
            value = mark_invoking(
                args.run_dir,
                args.ledger,
                owner_pid=args.owner_pid,
            )
        else:
            if args.return_code is None:
                parser.error("--return-code is required for result")
            if args.owner_pid is None:
                parser.error("--owner-pid is required for result")
            value = record_result(
                args.run_dir,
                args.ledger,
                return_code=args.return_code,
                owner_pid=args.owner_pid,
            )
    print(json.dumps(value, ensure_ascii=False, separators=(",", ":")))
    return 0 if value.get("status") not in {"REFUSED", "FAIL"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
