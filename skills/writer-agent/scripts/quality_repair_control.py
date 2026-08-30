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

from article_generation_state import ledger_has_public_effect


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
    legacy = bool(
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
    current = bool(
        value.get("platform") is None
        and value.get("lang") in {"ja", "en"}
        and value.get("published") is False
        and value.get("verified_logged_in") is False
        and value.get("draft_url") is None
        and value.get("live_url") is None
        and state == "quality-blocked:block_freeze"
        and isinstance(value.get("topic_id"), str)
        and value.get("topic_id", "").strip()
        and value.get("topic_source") == "paid-demand"
        and isinstance(value.get("editorial_form"), str)
        and value.get("editorial_form", "").strip()
    )
    return legacy or current


def _quality_audit_topic_id(ledger: Path, run_id: str) -> str | None:
    if not ledger.exists():
        return None
    rows: list[dict[str, Any]] = []
    for line in ledger.read_text(encoding="utf-8").splitlines():
        try:
            value = json.loads(line)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(value, dict) and value.get("run_id") == run_id:
            rows.append(value)
    if (
        len(rows) != 2
        or {row.get("lang") for row in rows} != {"ja", "en"}
        or not all(_is_quality_block_audit(row) for row in rows)
    ):
        return None
    topics = {row.get("topic_id") for row in rows}
    return next(iter(topics)) if len(topics) == 1 else None


def _terminal_quality_block(
    run_dir: Path, ledger: Path
) -> dict[str, Any] | None:
    """Build a hash-bound rejection only for the known exhausted gate shape."""
    gates = run_dir / "gates"
    if (gates / "publication-state.json").exists() or ledger_has_public_effect(
        ledger, run_dir.name
    ):
        return None
    quality_path = gates / "quality-self-heal.json"
    blocker_path = gates / "quality-repair-blocker.json"
    quality = _read_json(quality_path)
    blocker = _read_json(blocker_path)
    route = _read_json(gates / "topic-route.json")
    if not (
        quality
        and quality.get("version") == CURRENT_QUALITY_VERSION
        and quality.get("attempt") == 2
        and quality.get("action") == "evaluate_reroute"
        and blocker
        and blocker.get("status") == "blocked"
        and blocker.get("run_id") == run_dir.name
        and blocker.get("action_from_quality_self_heal") == "evaluate_reroute"
        and blocker.get("publication") == "not_started"
        and blocker.get("archived_evidence") == "preserved"
        and "high-escalation-exhausted" in str(blocker.get("reason", ""))
        and route
        and isinstance(route.get("topic_id"), str)
        and route.get("topic_id", "").strip()
        and isinstance(route.get("editorial_form"), str)
        and route.get("editorial_form", "").strip()
    ):
        return None
    records = quality.get("quality")
    blocker_drafts = blocker.get("drafts")
    if not isinstance(records, dict) or not isinstance(blocker_drafts, dict):
        return None
    drafts: dict[str, str] = {}
    editorial_receipts: dict[str, str] = {}
    reader_receipts: dict[str, str] = {}
    feedback_items: list[dict[str, str]] = []
    reader_cap_languages: list[str] = []
    for lang in ("ja", "en"):
        article = run_dir / f"article-{lang}.md"
        editorial_path = gates / f"editorial-{lang}.json"
        reader_path = gates / f"reader-testing-gate-{lang}.terminal.json"
        attempt_path = gates / ".attempts" / f"reader-testing-gate-{lang}.json"
        editorial = _read_json(editorial_path)
        reader = _read_json(reader_path)
        attempt = _read_json(attempt_path)
        if not article.is_file() or article.is_symlink() or not editorial or not reader or not attempt:
            return None
        digest = _sha256(article)
        record = records.get(lang)
        if not (
            isinstance(record, dict)
            and record.get("article_sha256") == digest
            and blocker_drafts.get(lang) == digest
            and record.get("identity_current") is True
            and record.get("reader_current") is True
            and record.get("evaluation_current") is False
            and record.get("ready") is False
            and editorial.get("verdict") == "FAIL"
            and editorial.get("requested_reasoning_effort") == "high"
            and editorial.get("article_sha256") != digest
            and reader.get("article_sha256") == digest
            and attempt.get("article_sha256") == digest
        ):
            return None
        drafts[lang] = digest
        editorial_receipts[lang] = _sha256(editorial_path)
        reader_receipts[lang] = _sha256(reader_path)
        for index, fix in enumerate(editorial.get("fixes", []), start=1):
            if isinstance(fix, str) and fix.strip():
                feedback_items.append({"id": f"editorial-{lang}-{index}", "lang": lang, "kind": "editorial_fix", "text": fix.strip()})
        payload = reader.get("payload")
        if (
            int(attempt.get("attempts", 0)) >= 3
            and isinstance(payload, dict)
            and payload.get("verdict") == "FAIL"
            and payload.get("unanswered_questions")
        ):
            reader_cap_languages.append(lang)
    if not reader_cap_languages:
        return None
    return {
        "version": 1,
        "status": "terminal_quality_blocked",
        "run_id": run_dir.name,
        "reason": "evaluation_budget_exhausted",
        "created_at": _utc_now(),
        "drafts": drafts,
        "quality_sha256": _sha256(quality_path),
        "blocker_sha256": _sha256(blocker_path),
        "editorial_receipts": editorial_receipts,
        "reader_receipts": reader_receipts,
        "reader_cap_languages": reader_cap_languages,
        "topic_id": route["topic_id"].strip(),
        "editorial_form": route["editorial_form"].strip(),
        "quality_failure_feedback": {"version": 1, "source_run_id": run_dir.name, "items": feedback_items},
        "publication": "not_started",
    }


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
        == "skills/writer-agent/scripts/bookmark-gate.sh"
        and defect.get("source_immutable") is True
        and bookmark
        and bookmark.get("gate") in {"", "bookmark"}
        and bookmark.get("language") in {"", "ja"}
        and bookmark.get("verdict") == "FAIL"
        and bookmark.get("exit_code") == 1
        and bookmark.get("stdout") == "FAIL names<2\n"
    )


def _tracked_reader_terminal_source_defect(
    run_dir: Path, gates: Path, canonical: dict[str, Any]
) -> bool:
    defect = _read_json(gates / "quality-gate-defect.json")
    reader_source = Path(__file__).resolve().parent / "reader-testing-gate.sh"
    try:
        source_fixed = "READER_STDOUT_SCHEMA_VERSION=2" in reader_source.read_text(
            encoding="utf-8"
        )
    except OSError:
        return False
    if not (
        defect
        and defect.get("status") == "pending-source-fix"
        and defect.get("run_id") == run_dir.name
        and defect.get("component")
        == "reader-testing-gate.sh / quality_self_heal.py contract"
        and canonical.get("version") == CURRENT_QUALITY_VERSION
        and canonical.get("action") == "evaluate_reroute"
        and source_fixed
    ):
        return False
    quality = canonical.get("quality")
    if not isinstance(quality, dict):
        return False
    for lang in ("ja", "en"):
        article = run_dir / f"article-{lang}.md"
        attempt = _read_json(
            gates / ".attempts" / f"reader-testing-gate-{lang}.json"
        )
        terminal = _read_json(gates / f"reader-testing-gate-{lang}.terminal.json")
        if not article.is_file() or article.is_symlink():
            return False
        digest = _sha256(article)
        if (
            quality.get(lang, {}).get("article_sha256") != digest
            or not attempt
            or attempt.get("gate") != "reader-testing-gate"
            or attempt.get("lang") != lang
            or int(attempt.get("attempts", 0)) < 1
            or attempt.get("article_sha256") != digest
            or not terminal
            or terminal.get("verdict") not in {"PASS", "FAIL"}
            or terminal.get("article_sha256") is not None
        ):
            return False
    return True


def _tracked_editorial_hash_scope_source_defect(
    run_dir: Path, gates: Path, canonical: dict[str, Any]
) -> bool:
    blocker = _read_json(gates / "editorial-reroute-blocker.json")
    editorial_source = Path(__file__).resolve().parent / "editorial-gate.sh"
    try:
        source = editorial_source.read_text(encoding="utf-8")
    except OSError:
        return False
    if not (
        blocker
        and blocker.get("gate") == "editorial"
        and blocker.get("status") == "blocked"
        and blocker.get("exit_code") == 77
        and blocker.get("reason") == "high-escalation-exhausted"
        and canonical.get("version") == CURRENT_QUALITY_VERSION
        and canonical.get("attempt") == 2
        and canonical.get("action") == "evaluate_reroute"
        and 'HIGH_CLAIM_ROOT="$ARTICLE_RUN_DIR/gates/.attempts/editorial-high-$LANG_A"'
        in source
        and 'mkdir "$HIGH_CLAIM"' in source
    ):
        return False
    quality = canonical.get("quality")
    if not isinstance(quality, dict):
        return False
    for lang in ("ja", "en"):
        article = run_dir / f"article-{lang}.md"
        if not article.is_file() or article.is_symlink():
            return False
        digest = _sha256(article)
        if (
            quality.get(lang, {}).get("article_sha256") != digest
            or blocker.get(f"{lang}_article_sha256") != digest
        ):
            return False
    return True


def _tracked_topic_router_reroute_source_defect(
    run_dir: Path, gates: Path, canonical: dict[str, Any]
) -> bool:
    router_source = Path(__file__).resolve().parent / "topic_router.py"
    try:
        source = router_source.read_text(encoding="utf-8")
    except OSError:
        return False
    attempt_one = _read_json(gates / "quality-self-heal-attempt-1.json")
    attempt_two = _read_json(gates / "quality-self-heal-attempt-2.json")
    route = _read_json(gates / "topic-route.json")
    generation = _read_json(gates / "generation-state.json")
    attempts = generation.get("attempts") if generation else None
    if not (
        "current-run reroute must preserve topic_id" in source
        and "current-run reroute must change editorial_form" in source
        and canonical.get("version") == CURRENT_QUALITY_VERSION
        and canonical.get("attempt") == 2
        and canonical.get("action") == "block_freeze"
        and canonical.get("reason") == "editorial_form_not_changed"
        and attempt_two == canonical
        and attempt_one
        and attempt_one.get("version") == CURRENT_QUALITY_VERSION
        and attempt_one.get("attempt") == 1
        and attempt_one.get("action") == "reroute"
        and attempt_one.get("required_changes") == ["editorial_form", "outline"]
        and isinstance(attempt_one.get("forbidden_editorial_form"), str)
        and attempt_one.get("forbidden_editorial_form")
        == attempt_one.get("editorial_form")
        and route
        and isinstance(route.get("topic_id"), str)
        and route.get("topic_id", "").strip()
        and route.get("editorial_form")
        == attempt_one.get("forbidden_editorial_form")
        and isinstance(attempts, list)
        and len(attempts) == 2
        and all(
            isinstance(row, dict)
            and row.get("attempt") == index
            and row.get("status") == "provider-returned"
            and row.get("return_code") == 0
            for index, row in enumerate(attempts, start=1)
        )
    ):
        return False
    quality = canonical.get("quality")
    attempt_quality = attempt_one.get("quality")
    if not isinstance(quality, dict) or not isinstance(attempt_quality, dict):
        return False
    for lang in ("ja", "en"):
        article = run_dir / f"article-{lang}.md"
        if not article.is_file() or article.is_symlink():
            return False
        digest = _sha256(article)
        prior_digest = attempt_quality.get(lang, {}).get("article_sha256")
        if (
            quality.get(lang, {}).get("article_sha256") != digest
            or not isinstance(prior_digest, str)
            or len(prior_digest) != 64
            or prior_digest == digest
        ):
            return False
    return True


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
    if ledger_has_public_effect(ledger, run_id):
        return _refused("ledger-row-exists")
    repair_state = _read_json(gates / "quality-repair-state.json")
    if repair_state:
        if _terminal_quality_block(run_dir, ledger) is not None:
            return {
                "status": "READY",
                "reason": "structurally-exhausted-quality-evaluations",
                "run_id": run_id,
                "run_dir": str(run_dir),
                "repair_epoch": REPAIR_EPOCH,
                "attempts": int(repair_state.get("attempts", 0)),
            }
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
    reader_source_defect = bool(
        canonical
        and _tracked_reader_terminal_source_defect(run_dir, gates, canonical)
    )
    editorial_source_defect = bool(
        canonical
        and _tracked_editorial_hash_scope_source_defect(
            run_dir, gates, canonical
        )
    )
    topic_router_source_defect = bool(
        canonical
        and _tracked_topic_router_reroute_source_defect(
            run_dir, gates, canonical
        )
    )
    if (
        not legacy
        and not source_defect
        and not reader_source_defect
        and not editorial_source_defect
        and not topic_router_source_defect
    ):
        return _refused("quality-block-not-legacy")
    if topic_router_source_defect:
        return {
            "status": "READY",
            "reason": "tracked-topic-router-reroute-source-defect",
            "run_id": run_id,
            "run_dir": str(run_dir),
            "repair_epoch": REPAIR_EPOCH,
            "source_defect": "topic-router-reroute",
            "drafts": {
                lang: _sha256(run_dir / f"article-{lang}.md")
                for lang in ("ja", "en")
            },
        }
    if editorial_source_defect:
        return {
            "status": "READY",
            "reason": "tracked-editorial-hash-scope-source-defect",
            "run_id": run_id,
            "run_dir": str(run_dir),
            "repair_epoch": REPAIR_EPOCH,
            "source_defect": "editorial-hash-scope",
            "drafts": {
                lang: _sha256(run_dir / f"article-{lang}.md")
                for lang in ("ja", "en")
            },
        }
    if reader_source_defect:
        return {
            "status": "READY",
            "reason": "tracked-reader-terminal-source-defect",
            "run_id": run_id,
            "run_dir": str(run_dir),
            "repair_epoch": REPAIR_EPOCH,
            "source_defect": "reader-terminal-hash",
            "drafts": {
                lang: _sha256(run_dir / f"article-{lang}.md")
                for lang in ("ja", "en")
            },
        }
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
        "quality-gate-defect.json",
        "editorial-reroute-blocker.json",
        "quality-self-heal-final.json",
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


def _repair_prompt(
    run_dir: Path, ledger: Path, archive: Path, source_defect: str | None
) -> str:
    scripts = Path(__file__).resolve().parent
    if source_defect == "topic-router-reroute":
        return f"""Run ONE bounded reroute repair for the existing unpublished Writer run.

RUN_DIR={run_dir}
LEDGER={ledger}
ORIGINAL_PROMPT={run_dir / "article-daily-prompt.txt"}
ARCHIVED_EVIDENCE={archive}

The canonical quality receipt is the restored attempt-1 action=reroute. Read it and gates/topic-route.json. Run topic_router.py validate through the normal route command, preserve the current topic_id exactly, and select an editorial_form different from forbidden_editorial_form. Do not hand-edit topic-route.json. Rewrite the outline plus article-ja.md and article-en.md for that same topic in the new form.

No staging or publication is allowed until every current-hash editorial, identity, reader, media, CTA, and quality gate passes and quality_self_heal.py returns action=ready_to_freeze. The archived receipts are immutable. If any gate returns block_freeze, preserve evidence, publish nothing, and stop. On ready_to_freeze, continue only STEP 4.8 through STEP 20 of ORIGINAL_PROMPT for this same run, with real remote readback and no local-only publication claim.
"""
    if source_defect == "reader-terminal-hash":
        first_gate = (
            "Run reader-testing-gate.sh for BOTH languages first and verify "
            "each terminal carries the current article SHA-256."
        )
    elif source_defect == "editorial-hash-scope":
        first_gate = (
            "Run editorial-gate.sh for BOTH languages first and verify each "
            "receipt carries the current article SHA-256."
        )
    else:
        first_gate = (
            "Run bookmark-gate.sh for JA first; if it does not PASS on the "
            "current bytes, publish nothing and stop."
        )
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

Read the archived receipts, editorial and reader findings, the current route, and both current drafts. {first_gate} Run the remaining current deterministic checks. For BOTH languages, run editorial-gate.sh, identity-gate.sh, and reader-testing-gate.sh against the current bytes. Apply only the bounded revisions those gates request; after any revision, restore and validate canonical media and CTA invariants before re-running the relevant gate. A same-hash editorial FAIL must be revised before rejudge. Reader questions remain stable and each language gets at most three evaluations.

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
        "source_defect": decision.get("source_defect"),
        "route_sha256": _sha256(gates / "topic-route.json"),
        "topic_id": _read_json(gates / "topic-route.json").get("topic_id"),
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
    if decision.get("source_defect") == "topic-router-reroute":
        current = _read_json(gates / "quality-self-heal-attempt-1.json")
        if not current:
            raise QualityRepairError("quality-reroute-attempt-one-missing")
        _atomic_write(gates / "quality-self-heal.json", current)
    else:
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
        or current.get("action")
        != (
            "reroute"
            if decision.get("source_defect") == "topic-router-reroute"
            else "evaluate_reroute"
        )
    ):
        raise QualityRepairError("quality-repair-did-not-open-current-evaluation")
    prompt_path = archive_parent / "repair-prompt.txt"
    prompt_path.write_text(
        _repair_prompt(run_dir, ledger, archive, decision.get("source_defect")),
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
        current_route = _read_json(route)
        archived_attempt = _read_json(
            run_dir
            / "gates"
            / "quality-repair"
            / f"epoch-{REPAIR_EPOCH}"
            / "original"
            / "quality-self-heal.json"
        )
        expected_topic = state.get("topic_id") or _quality_audit_topic_id(
            ledger, run_dir.name
        )
        if not (
            state.get("source_defect") == "topic-router-reroute"
            and current_route
            and current_route.get("topic_id") == expected_topic
            and isinstance(current_route.get("editorial_form"), str)
            and current_route.get("editorial_form", "").strip()
            and archived_attempt
            and current_route.get("editorial_form")
            != archived_attempt.get("editorial_form")
        ):
            raise QualityRepairError("quality-repair-route-changed")
        state["topic_id"] = expected_topic
        state["route_sha256"] = _sha256(route)
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
                    state.get("source_defect"),
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
    terminal = _terminal_quality_block(run_dir, ledger)
    if terminal is not None:
        _atomic_write(gates / "terminal-quality-blocked.json", terminal)
        status = "terminal-quality-blocked"
    elif (gates / "publication-state.json").is_file():
        status = "handed-to-publication"
    elif ledger_has_public_effect(ledger, run_dir.name):
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


def terminalize(run_dir: Path | str, ledger: Path | str) -> dict[str, Any]:
    """Close an already-finished repair without another provider invocation."""
    run_dir = Path(run_dir).resolve()
    ledger = Path(ledger).resolve()
    gates = run_dir / "gates"
    terminal = _terminal_quality_block(run_dir, ledger)
    state_path = gates / "quality-repair-state.json"
    state = _read_json(state_path)
    if terminal is None or state is None:
        raise QualityRepairError("quality-evaluations-not-structurally-exhausted")
    _atomic_write(gates / "terminal-quality-blocked.json", terminal)
    state.update({
        "status": "terminal-quality-blocked",
        "finished_at": terminal["created_at"],
    })
    _atomic_write(state_path, state)
    return state


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=("plan", "begin", "invoke", "result", "terminalize"),
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
    elif args.command == "terminalize":
        value = terminalize(args.run_dir, args.ledger)
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
