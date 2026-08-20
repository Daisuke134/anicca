#!/usr/bin/env python3
"""Bounded repair for exact unpublished quality blocks after source fixes."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any


CURRENT_QUALITY_VERSION = 2
REPAIR_EPOCH = 1
MAX_REPAIR_ATTEMPTS = 2


class QualityRepairError(ValueError):
    """The run is not an exact bounded quality-repair candidate."""


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


def _is_quality_block_audit(value: dict[str, Any]) -> bool:
    state = value.get("state")
    return bool(
        value.get("platform") == "quality"
        and value.get("lang") == "ja+en"
        and value.get("published") is False
        and value.get("verified_logged_in") is False
        and value.get("draft_url") is None
        and value.get("live_url") is None
        and value.get("reality_gate") in {None, ""}
        and isinstance(state, str)
        and state.startswith("carry-over:quality-block:")
    )


def _ledger_has_delivery_row(ledger: Path, run_id: str) -> bool:
    if not ledger.exists():
        return False
    for line in ledger.read_text(encoding="utf-8").splitlines():
        try:
            value = json.loads(line)
        except (json.JSONDecodeError, TypeError):
            continue
        if (
            isinstance(value, dict)
            and value.get("run_id") == run_id
            and not _is_quality_block_audit(value)
        ):
            return True
    return False


def _quality_module() -> Any:
    scripts = Path(__file__).resolve().parent
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    import quality_self_heal  # pylint: disable=import-outside-toplevel

    return quality_self_heal


def _tracked_bookmark_source_defect(gates: Path) -> bool:
    defect = _read_json(gates / "source-defect-bookmark-ja.json")
    bookmark = _read_json(gates / "bookmark-ja.json")
    return bool(
        defect
        and defect.get("gate") == "bookmark"
        and defect.get("affected_artifact") == "article-ja"
        and defect.get("status") == "pending"
        and defect.get("verdict") == "FAIL"
        and defect.get("observed_output") == "FAIL names<2"
        and defect.get("source_file")
        == "skills/article-writer/scripts/bookmark-gate.sh"
        and defect.get("source_immutable") is True
        and bookmark
        and bookmark.get("gate") in {"", "bookmark"}
        and bookmark.get("language") in {"", "ja"}
        and bookmark.get("verdict") == "FAIL"
        and bookmark.get("exit_code") == 1
        and bookmark.get("stdout") == "FAIL names<2\n"
    )


def _bookmark_gate_now_passes(run_dir: Path, article: Path) -> bool:
    try:
        title = next(
            line[2:].strip()
            for line in article.read_text(encoding="utf-8").splitlines()
            if line.startswith("# ") and line[2:].strip()
        )
    except (OSError, StopIteration):
        return False
    gate = Path(__file__).resolve().parent / "bookmark-gate.sh"
    try:
        completed = subprocess.run(
            [
                "bash",
                str(gate),
                title,
                str(article),
                "--lang",
                "ja",
            ],
            cwd=run_dir,
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return completed.returncode == 0 and completed.stdout.startswith("OK ")


def plan(run_dir: Path | str, ledger: Path | str) -> dict[str, Any]:
    run_dir = Path(run_dir).resolve()
    ledger = Path(ledger).resolve()
    gates = run_dir / "gates"
    run_id = run_dir.name
    if not run_dir.is_dir() or not gates.is_dir():
        return _refused("run-directory-missing")
    if (gates / "publication-state.json").exists():
        return _refused("publication-state-exists")
    if _ledger_has_delivery_row(ledger, run_id):
        return _refused("ledger-row-exists")
    repair_state = _read_json(gates / "quality-repair-state.json")
    if repair_state:
        prompt_path = Path(str(repair_state.get("prompt_path", "")))
        attempts = int(repair_state.get("attempts", 0))
        if (
            repair_state.get("status")
            in {"prepared", "retryable-incomplete"}
            and attempts < MAX_REPAIR_ATTEMPTS
            and prompt_path.is_file()
            and repair_state.get("prompt_sha256") == _sha256(prompt_path)
        ):
            return {
                "status": "READY",
                "reason": "prepared-quality-repair",
                "run_id": run_id,
                "run_dir": str(run_dir),
                "repair_epoch": REPAIR_EPOCH,
                "prompt_path": str(prompt_path),
                "prompt_sha256": repair_state["prompt_sha256"],
                "attempts": attempts,
            }
        age = _age_seconds(repair_state.get("started_at"))
        if (
            repair_state.get("status") == "invoking"
            and attempts < MAX_REPAIR_ATTEMPTS
            and not _owner_is_alive(repair_state.get("owner_pid"))
            and age is not None
            and age >= 60
            and prompt_path.is_file()
            and repair_state.get("prompt_sha256") == _sha256(prompt_path)
        ):
            return {
                "status": "READY",
                "reason": "orphaned-quality-repair",
                "run_id": run_id,
                "run_dir": str(run_dir),
                "repair_epoch": REPAIR_EPOCH,
                "prompt_path": str(prompt_path),
                "prompt_sha256": repair_state["prompt_sha256"],
                "attempts": attempts,
                "orphaned_owner_pid": repair_state.get("owner_pid"),
            }
        return _refused(
            f"quality-repair-already-{repair_state.get('status', 'unknown')}"
        )
    prompt = run_dir / "article-daily-prompt.txt"
    generation = _read_json(gates / "generation-state.json")
    if (
        not prompt.is_file()
        or not generation
        or generation.get("run_id") != run_id
        or generation.get("run_dir") != str(run_dir)
        or generation.get("prompt_path") != str(prompt)
        or generation.get("prompt_sha256") != _sha256(prompt)
        or generation.get("status") != "provider-returned"
    ):
        return _refused("generation-state-not-provider-returned")
    canonical = _read_json(gates / "quality-self-heal.json")
    legacy = bool(
        canonical
        and canonical.get("version") == 1
        and canonical.get("action") == "block_freeze"
    )
    source_defect = bool(
        canonical
        and canonical.get("version") == CURRENT_QUALITY_VERSION
        and canonical.get("action") == "block_freeze"
        and _tracked_bookmark_source_defect(gates)
    )
    if not legacy and not source_defect:
        return _refused("quality-block-not-legacy")
    attempt_one = _read_json(gates / "quality-self-heal-attempt-1.json")
    attempt_two = _read_json(gates / "quality-self-heal-attempt-2.json")
    expected_version = CURRENT_QUALITY_VERSION if source_defect else 1
    if (
        not attempt_one
        or attempt_one.get("version") != expected_version
        or attempt_one.get("action") != "reroute"
        or not attempt_two
        or attempt_two != canonical
    ):
        return _refused("legacy-quality-history-invalid")
    route = _read_json(gates / "topic-route.json")
    forbidden = attempt_one.get("forbidden_editorial_form")
    if (
        not route
        or not isinstance(forbidden, str)
        or route.get("editorial_form") == forbidden
    ):
        return _refused("legacy-reroute-not-distinct")
    drafts = {
        "ja": run_dir / "article-ja.md",
        "en": run_dir / "article-en.md",
    }
    if any(
        not path.is_file() or path.is_symlink() for path in drafts.values()
    ):
        return _refused("draft-missing-or-unsafe")
    canonical_quality = canonical.get("quality")
    if not isinstance(canonical_quality, dict) or any(
        not isinstance(canonical_quality.get(lang), dict)
        or canonical_quality[lang].get("article_sha256")
        != _sha256(drafts[lang])
        for lang in ("ja", "en")
    ):
        return _refused("legacy-block-draft-hash-mismatch")
    if source_defect:
        if not _bookmark_gate_now_passes(run_dir, drafts["ja"]):
            return _refused("tracked-bookmark-source-defect-still-failing")
        return {
            "status": "READY",
            "reason": "tracked-bookmark-source-defect",
            "run_id": run_id,
            "run_dir": str(run_dir),
            "repair_epoch": REPAIR_EPOCH,
            "source_defect": "bookmark-ja",
            "drafts": {
                lang: _sha256(path) for lang, path in drafts.items()
            },
        }
    quality = _quality_module()
    current = {
        lang: quality.language_quality(run_dir, lang, drafts[lang])
        for lang in ("ja", "en")
    }
    if all(row.get("evaluation_current") is True for row in current.values()):
        return _refused("legacy-block-evaluations-already-current")
    return {
        "status": "READY",
        "reason": "legacy-stale-quality-block",
        "run_id": run_id,
        "run_dir": str(run_dir),
        "repair_epoch": REPAIR_EPOCH,
        "drafts": {lang: _sha256(path) for lang, path in drafts.items()},
    }


def _active_receipts(gates: Path) -> list[Path]:
    names = [
        "attempt-budget.json",
        "editorial-ja.json",
        "editorial-en.json",
        "identity-ja.json",
        "identity-en.json",
        "quality-self-heal-attempt-2.json",
        "quality-self-heal.json",
        "reader-testing-gate-ja.terminal.json",
        "reader-testing-gate-en.terminal.json",
        "bookmark-ja.json",
        "source-defect-bookmark-ja.json",
    ]
    paths = [gates / name for name in names if (gates / name).is_file()]
    attempts = gates / ".attempts"
    if attempts.is_dir():
        paths.extend(
            path
            for path in sorted(attempts.rglob("*"))
            if path.is_file() and not path.is_symlink()
        )
    return paths


def _repair_prompt(run_dir: Path, ledger: Path, archive: Path) -> str:
    scripts = Path(__file__).resolve().parent
    return f"""Run ONE bounded quality repair for the existing unpublished Writer run.

RUN_DIR={run_dir}
LEDGER={ledger}
ORIGINAL_PROMPT={run_dir / "article-daily-prompt.txt"}
ARCHIVED_EVIDENCE={archive}

Hard boundaries:
- This model call is the active repair executor. The wrapper sets ARTICLE_QUALITY_REPAIR_ACTIVE=1 and ARTICLE_QUALITY_REPAIR_OWNER_PID to its own parent PID.
- quality-repair-state status=invoking and that owner PID describe this exact execution. Do not wait for quality-repair-state or monitor its owner; doing so deadlocks the child against its parent. Start the gate work immediately.
- Do not select a new topic, perform new research, create another run, or change gates/topic-route.json.
- Do not replace the JA/EN artifact identities. Work only on article-ja.md and article-en.md in RUN_DIR.
- No staging or publication is allowed until quality_self_heal.py returns action=ready_to_freeze and current-hash quality terminals exist.
- The archived receipts under ARCHIVED_EVIDENCE are immutable evidence. Never edit, delete, or move them.

Read the archived receipts, editorial and reader findings, the current route, and both current drafts. Run bookmark-gate.sh for JA first; if it does not PASS on the current bytes, publish nothing and stop. Run the remaining current deterministic checks. For BOTH languages, run editorial-gate.sh, identity-gate.sh, and reader-testing-gate.sh against the current bytes. Apply only the bounded revisions those gates request; after any revision, restore and validate canonical media and CTA invariants before re-running the relevant gate. A same-hash editorial FAIL must be revised before rejudge. Reader questions remain stable and each language gets at most three evaluations.

Then run:
python3 {scripts / "quality_self_heal.py"} assess --run-dir "$ARTICLE_RUN_DIR" --draft-ja "$ARTICLE_RUN_DIR/article-ja.md" --draft-en "$ARTICLE_RUN_DIR/article-en.md"

If action=evaluate_reroute, run every missing current-hash editorial, identity, and reader evaluation before calling assess again. If action=block_freeze, preserve the evidence, publish nothing, report the honest block, and stop. If action=ready_to_freeze, read ORIGINAL_PROMPT and continue only STEP 4.8 through STEP 20 for this same run. The original armed money contract remains authoritative: note is ¥500 and both Substack posts are paid-only. Require real remote readback and never claim publication from a local receipt.
"""


def begin(run_dir: Path | str, ledger: Path | str) -> dict[str, Any]:
    run_dir = Path(run_dir).resolve()
    ledger = Path(ledger).resolve()
    decision = plan(run_dir, ledger)
    if decision.get("status") != "READY":
        raise QualityRepairError(str(decision.get("reason", "not-ready")))
    gates = run_dir / "gates"
    archive_parent = gates / "quality-repair" / f"epoch-{REPAIR_EPOCH}"
    archive = archive_parent / "original"
    if archive_parent.exists():
        raise QualityRepairError("quality-repair-archive-exists")
    active = _active_receipts(gates)
    entries: list[dict[str, str]] = []
    for source in active:
        relative = source.relative_to(gates)
        entries.append(
            {
                "path": str(relative),
                "sha256": _sha256(source),
            }
        )
    state = {
        "version": 1,
        "status": "archiving",
        "run_id": run_dir.name,
        "repair_epoch": REPAIR_EPOCH,
        "attempts": 0,
        "drafts": decision["drafts"],
        "route_sha256": _sha256(gates / "topic-route.json"),
        "entries": entries,
    }
    _atomic_write(gates / "quality-repair-state.json", state)
    archive.mkdir(parents=True)
    for row, source in zip(entries, active, strict=True):
        destination = archive / row["path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        os.replace(source, destination)
        if (
            not destination.is_file()
            or destination.is_symlink()
            or _sha256(destination) != row["sha256"]
        ):
            raise QualityRepairError("quality-repair-archive-verification-failed")
    attempts = gates / ".attempts"
    if attempts.exists():
        shutil.rmtree(attempts)
    _atomic_write(
        archive_parent / "manifest.json",
        {
            "version": 1,
            "run_id": run_dir.name,
            "repair_epoch": REPAIR_EPOCH,
            "entries": entries,
        },
    )
    quality = _quality_module()
    current = quality.assess(
        run_dir,
        {
            "ja": run_dir / "article-ja.md",
            "en": run_dir / "article-en.md",
        },
    )
    if (
        current.get("version") != CURRENT_QUALITY_VERSION
        or current.get("action") != "evaluate_reroute"
    ):
        raise QualityRepairError("quality-repair-did-not-open-current-evaluation")
    prompt_path = archive_parent / "repair-prompt.txt"
    prompt_path.write_text(
        _repair_prompt(run_dir, ledger, archive),
        encoding="utf-8",
    )
    state.update(
        {
            "status": "prepared",
            "quality_action": current["action"],
            "prompt_path": str(prompt_path),
            "prompt_sha256": _sha256(prompt_path),
        }
    )
    _atomic_write(gates / "quality-repair-state.json", state)
    return state


def mark_invoking(
    run_dir: Path | str,
    ledger: Path | str,
    *,
    owner_pid: int,
) -> dict[str, Any]:
    run_dir = Path(run_dir).resolve()
    ledger = Path(ledger).resolve()
    decision = plan(run_dir, ledger)
    if (
        decision.get("status") != "READY"
        or decision.get("reason")
        not in {"prepared-quality-repair", "orphaned-quality-repair"}
    ):
        raise QualityRepairError(str(decision.get("reason", "not-prepared")))
    state_path = run_dir / "gates" / "quality-repair-state.json"
    state = _read_json(state_path)
    if not state:
        raise QualityRepairError("quality-repair-state-missing")
    route = run_dir / "gates" / "topic-route.json"
    if state.get("route_sha256") != _sha256(route):
        raise QualityRepairError("quality-repair-route-changed")
    attempts = int(state.get("attempts", 0)) + 1
    if attempts > MAX_REPAIR_ATTEMPTS:
        raise QualityRepairError("quality-repair-attempt-limit")
    if decision.get("reason") == "orphaned-quality-repair":
        old_prompt = Path(str(state.get("prompt_path", "")))
        old_hash = str(state.get("prompt_sha256", ""))
        prompts = (
            run_dir
            / "gates"
            / "quality-repair"
            / f"epoch-{REPAIR_EPOCH}"
            / "prompts"
        )
        prompts.mkdir(parents=True, exist_ok=True)
        archived_prompt = prompts / f"attempt-{attempts - 1}.txt"
        if archived_prompt.exists():
            raise QualityRepairError("quality-repair-prompt-archive-conflicts")
        shutil.copy2(old_prompt, archived_prompt)
        if _sha256(archived_prompt) != old_hash:
            raise QualityRepairError("quality-repair-prompt-archive-mismatch")
        new_prompt = (
            run_dir
            / "gates"
            / "quality-repair"
            / f"epoch-{REPAIR_EPOCH}"
            / f"repair-prompt-attempt-{attempts}.txt"
        )
        new_prompt.write_text(
            _repair_prompt(
                run_dir,
                ledger,
                run_dir
                / "gates"
                / "quality-repair"
                / f"epoch-{REPAIR_EPOCH}"
                / "original",
            ),
            encoding="utf-8",
        )
        state.update(
            {
                "prompt_path": str(new_prompt),
                "prompt_sha256": _sha256(new_prompt),
                "orphaned_owner_pid": decision.get(
                    "orphaned_owner_pid"
                ),
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


def record_result(
    run_dir: Path | str,
    ledger: Path | str,
    *,
    return_code: int,
) -> dict[str, Any]:
    run_dir = Path(run_dir).resolve()
    ledger = Path(ledger).resolve()
    gates = run_dir / "gates"
    state_path = gates / "quality-repair-state.json"
    state = _read_json(state_path)
    if not state or state.get("status") != "invoking":
        raise QualityRepairError("quality-repair-not-invoking")
    attempts = int(state.get("attempts", 0))
    quality = _read_json(gates / "quality-self-heal.json")
    if (gates / "publication-state.json").is_file():
        status = "handed-to-publication"
    elif _ledger_has_delivery_row(ledger, run_dir.name):
        status = "terminal-ambiguous-ledger-without-publication-state"
    elif quality and quality.get("action") == "block_freeze":
        status = "terminal-blocked"
    elif attempts < MAX_REPAIR_ATTEMPTS:
        status = "retryable-incomplete"
    else:
        status = "terminal-incomplete"
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
        choices=("plan", "begin", "invoke", "result"),
    )
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--owner-pid", type=int)
    parser.add_argument("--return-code", type=int)
    args = parser.parse_args()
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
        value = record_result(
            args.run_dir,
            args.ledger,
            return_code=args.return_code,
        )
    print(json.dumps(value, ensure_ascii=False, separators=(",", ":")))
    return 0 if value.get("status") != "REFUSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
