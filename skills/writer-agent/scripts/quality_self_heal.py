#!/usr/bin/env python3
"""Bounded editorial/reader quality recovery controller."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
from typing import Any


EDITORIAL_FORMS = {
    "explainer",
    "how-to",
    "case-study",
    "comparison",
    "field-note",
    "opinion",
    "report",
}
MAX_REROUTES = 5
MAX_ITERATIONS = 5
CURRENT_VERSION = 2


class QualitySelfHealError(ValueError):
    """Quality evidence is missing, stale, or contradictory."""


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return None
    return value if isinstance(value, dict) else None


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _receipt_hash(payload: dict[str, Any]) -> str:
    unsigned = {
        key: value for key, value in payload.items() if key != "receipt_sha256"
    }
    return hashlib.sha256(
        json.dumps(
            unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def _snapshot_receipts(
    run_dir: Path, attempt: int, quality: dict[str, Any]
) -> dict[str, dict[str, str]]:
    """Copy each gate receipt into an immutable, attempt-scoped evidence set."""
    gates = run_dir / "gates"
    destination = gates / f"quality-attempt-{attempt}"
    if destination.exists():
        if destination.is_symlink() or not destination.is_dir():
            raise QualitySelfHealError("quality attempt snapshot is not a directory")
    else:
        destination.mkdir()
    snapshots: dict[str, dict[str, str]] = {}
    names = {
        "editorial": lambda lang: f"editorial-{lang}.json",
        "reader": lambda lang: f"reader-testing-gate-{lang}.terminal.json",
        "identity": lambda lang: f"identity-{lang}.json",
    }
    for lang in ("ja", "en"):
        record = quality.get(lang)
        if not isinstance(record, dict):
            raise QualitySelfHealError("quality language record is missing")
        snapshots[lang] = {}
        for kind, filename in names.items():
            source = gates / filename(lang)
            if source.is_symlink() or not source.is_file():
                raise QualitySelfHealError(
                    f"quality {kind} receipt is missing for {lang}"
                )
            target = destination / filename(lang)
            if target.exists() or target.is_symlink():
                if target.is_symlink() or not target.is_file():
                    raise QualitySelfHealError("quality receipt snapshot is invalid")
                if _sha256(target) != _sha256(source):
                    raise QualitySelfHealError("quality receipt snapshot conflicts with current gate")
            else:
                shutil.copy2(source, target)
            digest = _sha256(target)
            snapshots[lang][kind] = digest
            observed = _read_json(target)
            if (
                observed is None
                or observed.get("article_sha256") != record.get("article_sha256")
            ):
                raise QualitySelfHealError("quality receipt snapshot hash binding failed")
    return snapshots


def language_quality(
    run_dir: Path,
    lang: str,
    draft: Path,
) -> dict[str, Any]:
    """Return hash-bound editorial and reader readiness for one draft."""

    digest = _sha256(draft)
    gates = run_dir / "gates"
    editorial = _read_json(gates / f"editorial-{lang}.json")
    reader = _read_json(
        gates / f"reader-testing-gate-{lang}.terminal.json"
    )
    identity = _read_json(gates / f"identity-{lang}.json")
    reasons: list[str] = []
    editorial_current = bool(
        editorial and editorial.get("article_sha256") == digest
    )
    editorial_pass = bool(
        editorial_current
        and editorial
        and editorial.get("verdict") == "PASS"
    )
    if not editorial_pass:
        reasons.append("editorial_not_current_pass")
    reader_current = bool(
        reader and reader.get("article_sha256") == digest
    )
    reader_pass = bool(
        reader_current
        and reader
        and reader.get("status") == "pass"
        and (
            reader.get("exit_code") == 0
            or (
                isinstance(reader.get("payload"), dict)
                and reader["payload"].get("verdict") == "PASS"
            )
        )
    )
    if not reader_pass:
        reasons.append("reader_not_current_pass")
    identity_current = bool(
        identity and identity.get("article_sha256") == digest
    )
    identity_pass = bool(
        identity_current
        and identity
        and identity.get("verdict") == "PASS"
    )
    if not identity_pass:
        reasons.append("identity_not_current_pass")
    return {
        "lang": lang,
        "article_sha256": digest,
        "editorial": "PASS" if editorial_pass else "FAIL",
        "identity": "PASS" if identity_pass else "FAIL",
        "reader": "PASS" if reader_pass else "FAIL",
        "editorial_current": editorial_current,
        "identity_current": identity_current,
        "reader_current": reader_current,
        "evaluation_current": (
            editorial_current and identity_current and reader_current
        ),
        "ready": editorial_pass and identity_pass and reader_pass,
        "reasons": reasons,
    }


def _route_form(run_dir: Path) -> str:
    route = _read_json(run_dir / "gates" / "topic-route.json")
    editorial_form = route.get("editorial_form") if route else None
    if editorial_form not in EDITORIAL_FORMS:
        raise QualitySelfHealError("current topic route has no valid editorial_form")
    return str(editorial_form)


def _history(run_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    paths = sorted(
        (run_dir / "gates").glob("quality-self-heal-attempt-*.json"),
        key=lambda path: path.name,
    )
    previous_hash: str | None = None
    for index, path in enumerate(paths, start=1):
        if path.is_symlink() or not path.is_file():
            raise QualitySelfHealError("quality attempt receipt is not regular")
        value = _read_json(path)
        if not isinstance(value, dict):
            raise QualitySelfHealError("quality attempt receipt is malformed")
        if (
            value.get("run_id") != run_dir.name
            or value.get("attempt") != index
            or value.get("previous_receipt_sha256") != previous_hash
            or value.get("receipt_sha256") != _receipt_hash(value)
        ):
            raise QualitySelfHealError("quality attempt receipt chain is invalid")
        languages = value.get("quality")
        if not isinstance(languages, dict) or any(
            not isinstance(languages.get(lang), dict)
            or not re.fullmatch(
                r"[0-9a-f]{64}", str(languages[lang].get("article_sha256", ""))
            )
            for lang in ("ja", "en")
        ):
            raise QualitySelfHealError("quality attempt draft hash is invalid")
        snapshots = value.get("receipt_snapshots")
        if not isinstance(snapshots, dict) or set(snapshots) != {"ja", "en"}:
            raise QualitySelfHealError("quality receipt snapshots are missing")
        for lang in ("ja", "en"):
            record = languages[lang]
            snapshot = snapshots.get(lang)
            if not isinstance(snapshot, dict) or set(snapshot) != {
                "editorial", "reader", "identity"
            }:
                raise QualitySelfHealError("quality receipt snapshot set is invalid")
            directory = run_dir / "gates" / f"quality-attempt-{index}"
            if directory.is_symlink() or not directory.is_dir():
                raise QualitySelfHealError("quality receipt snapshot directory is invalid")
            filenames = {
                "editorial": f"editorial-{lang}.json",
                "reader": f"reader-testing-gate-{lang}.terminal.json",
                "identity": f"identity-{lang}.json",
            }
            for kind, filename in filenames.items():
                path = directory / filename
                if (
                    path.is_symlink()
                    or not path.is_file()
                    or not re.fullmatch(r"[0-9a-f]{64}", str(snapshot[kind]))
                    or _sha256(path) != snapshot[kind]
                ):
                    raise QualitySelfHealError("quality receipt snapshot is tampered")
                observed = _read_json(path)
                if observed is None or observed.get("article_sha256") != record.get("article_sha256"):
                    raise QualitySelfHealError("quality receipt snapshot article hash mismatch")
        rows.append(value)
        previous_hash = value["receipt_sha256"]
    return rows


def validate_force_receipt(run_dir: Path | str, drafts: dict[str, Path]) -> bool:
    """Recompute the exact five-attempt force boundary before advisory publish."""
    run_dir = Path(run_dir)
    current = _read_json(run_dir / "gates" / "quality-self-heal.json")
    if not (
        isinstance(current, dict)
        and current.get("action") == "force_publish_advisory"
        and current.get("force_publish_after_iterations") == MAX_ITERATIONS
        and current.get("publication_policy") == "continuous"
        and current.get("run_id") == run_dir.name
        and current.get("attempt") == MAX_ITERATIONS
    ):
        return False
    try:
        history = _history(run_dir)
    except QualitySelfHealError:
        return False
    if len(history) != MAX_ITERATIONS or history[-1] != current:
        return False
    final_quality = current.get("quality")
    if not isinstance(final_quality, dict):
        return False
    for lang in ("ja", "en"):
        draft = Path(drafts[lang])
        record = final_quality.get(lang)
        if (
            draft.is_symlink()
            or not draft.is_file()
            or not isinstance(record, dict)
            or record.get("article_sha256") != _sha256(draft)
            or record.get("identity") != "PASS"
        ):
            return False
    return True


def _feedback_consumption(run_dir: Path) -> dict[str, Any] | None:
    state = run_dir / "gates" / "quality-feedback-recovery-state.json"
    if not state.is_file() or state.is_symlink():
        return None
    scripts = Path(__file__).resolve().parent
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from quality_feedback_recovery import (  # pylint: disable=import-outside-toplevel
        validate_consumption,
    )

    return validate_consumption(run_dir)


def assess(run_dir: Path, drafts: dict[str, Path]) -> dict[str, Any]:
    """Choose freeze, one reroute, or a terminal freeze block."""

    if set(drafts) != {"ja", "en"}:
        raise QualitySelfHealError("drafts must contain ja and en")
    editorial_form = _route_form(run_dir)
    publication_policy = os.environ.get("ARTICLE_PUBLICATION_POLICY", "strict")
    if publication_policy not in {"strict", "continuous"}:
        raise QualitySelfHealError("ARTICLE_PUBLICATION_POLICY must be strict or continuous")
    quality = {
        lang: language_quality(run_dir, lang, Path(drafts[lang]))
        for lang in ("ja", "en")
    }
    feedback = _feedback_consumption(run_dir)
    consumption = run_dir / "gates" / "quality-feedback-consumption.json"
    consumption_sha256 = (
        _sha256(consumption)
        if consumption.is_file() and not consumption.is_symlink()
        else None
    )
    fingerprint = hashlib.sha256(
        json.dumps(
            {
                "editorial_form": editorial_form,
                "drafts": {
                    lang: quality[lang]["article_sha256"]
                    for lang in ("ja", "en")
                },
                "quality": quality,
                "quality_feedback_consumption_sha256": consumption_sha256,
                "publication_policy": publication_policy,
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    history = _history(run_dir)
    if history and history[-1].get("fingerprint") == fingerprint:
        return history[-1]
    if len(history) >= MAX_ITERATIONS:
        raise QualitySelfHealError("quality iteration budget exhausted")

    failed_languages = [
        lang for lang in ("ja", "en") if not quality[lang]["ready"]
    ]
    reroutes = [row for row in history if row.get("action") == "reroute"]
    form_not_changed = bool(
        reroutes
        and reroutes[-1].get("forbidden_editorial_form") == editorial_form
    )
    rerouted_drafts_not_changed = bool(
        reroutes
        and any(
            (
                (
                    reroutes[-1].get("quality", {}).get(lang, {})
                    if isinstance(reroutes[-1].get("quality"), dict)
                    else {}
                ).get("article_sha256")
                == quality[lang]["article_sha256"]
            )
            for lang in ("ja", "en")
        )
    )
    reroute_needs_evaluation = bool(
        reroutes
        and not form_not_changed
        and not rerouted_drafts_not_changed
        and any(
            not quality[lang]["evaluation_current"]
            for lang in ("ja", "en")
        )
    )
    identity_safe = all(
        quality[lang]["identity"] == "PASS" for lang in ("ja", "en")
    )
    iteration = len(history) + 1
    if failed_languages and iteration >= MAX_ITERATIONS and identity_safe:
        action = "force_publish_advisory"
    elif form_not_changed:
        action = "block_freeze"
    elif rerouted_drafts_not_changed:
        action = "block_freeze"
    elif not failed_languages:
        action = (
            "ready_to_freeze"
            if feedback is None or feedback.get("status") == "PASS"
            else "block_freeze"
        )
    elif reroute_needs_evaluation:
        action = "evaluate_reroute"
    elif len(reroutes) < MAX_REROUTES:
        action = "reroute"
    else:
        action = "block_freeze"

    decision: dict[str, Any] = {
        "version": CURRENT_VERSION,
        "run_id": run_dir.name,
        "attempt": len(history) + 1,
        "action": action,
        "fingerprint": fingerprint,
        "editorial_form": editorial_form,
        "failed_languages": failed_languages,
        "reroutes_used": len(reroutes),
        "quality": quality,
        "publication_policy": publication_policy,
    }
    attempt = len(history) + 1
    decision["receipt_snapshots"] = _snapshot_receipts(run_dir, attempt, quality)
    if action == "force_publish_advisory":
        decision.update(
            {
                "force_publish_after_iterations": MAX_ITERATIONS,
                "quality_advisory": True,
                "reason": "quality_iteration_limit_reached",
            }
        )
    if action == "reroute":
        decision.update(
            {
                "forbidden_editorial_form": editorial_form,
                "required_changes": ["editorial_form", "outline"],
                "reroutes_used": len(reroutes) + 1,
            }
        )
    elif action == "evaluate_reroute":
        decision.update(
            {
                "reason": "reroute_not_evaluated_on_current_artifacts",
                "required_evaluations": [
                    "editorial",
                    "identity",
                    "reader",
                ],
            }
        )
    elif form_not_changed:
        decision["reason"] = "editorial_form_not_changed"
    elif rerouted_drafts_not_changed:
        decision["reason"] = "rerouted_drafts_not_changed"
    elif (
        not failed_languages
        and feedback is not None
        and feedback.get("status") != "PASS"
    ):
        decision["reason"] = "quality_feedback_not_consumed"
        decision["quality_feedback_reason"] = feedback.get("reason", "unknown")

    gates = run_dir / "gates"
    decision["previous_receipt_sha256"] = (
        history[-1].get("receipt_sha256") if history else None
    )
    decision["receipt_sha256"] = _receipt_hash(decision)
    _atomic_write(
        gates / f"quality-self-heal-attempt-{decision['attempt']}.json",
        decision,
    )
    _atomic_write(gates / "quality-self-heal.json", decision)
    return decision


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("assess",))
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--draft-ja", required=True, type=Path)
    parser.add_argument("--draft-en", required=True, type=Path)
    args = parser.parse_args()
    decision = assess(
        args.run_dir,
        {"ja": args.draft_ja, "en": args.draft_en},
    )
    print(json.dumps(decision, ensure_ascii=False, separators=(",", ":")))
    if decision["action"] in {"ready_to_freeze", "force_publish_advisory"}:
        return 0
    if decision["action"] == "evaluate_reroute":
        return 76
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
