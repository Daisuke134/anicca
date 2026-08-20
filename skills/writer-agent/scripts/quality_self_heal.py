#!/usr/bin/env python3
"""Bounded editorial/reader quality recovery controller."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
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
MAX_REROUTES = 1
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
        and isinstance(reader.get("payload"), dict)
        and reader["payload"].get("verdict") == "PASS"
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
    for path in sorted(
        (run_dir / "gates").glob("quality-self-heal-attempt-*.json")
    ):
        value = _read_json(path)
        if value:
            rows.append(value)
    return rows


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
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    history = _history(run_dir)
    if history and history[-1].get("fingerprint") == fingerprint:
        return history[-1]

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
    if form_not_changed:
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
        "attempt": len(history) + 1,
        "action": action,
        "fingerprint": fingerprint,
        "editorial_form": editorial_form,
        "failed_languages": failed_languages,
        "reroutes_used": len(reroutes),
        "quality": quality,
    }
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
    if action != "evaluate_reroute":
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
    if decision["action"] == "ready_to_freeze":
        return 0
    if decision["action"] == "evaluate_reroute":
        return 76
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
