#!/usr/bin/env python3
"""Choose a safe daily start without creating a second JST-day article.

The launchd wrapper asks this before it allocates a new RUN_TS.  Decisions are based on
durable run/ledger artifacts, never wall-clock proximity to the 06:00 trigger.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


REQUIRED = {
    ("note", "ja"),
    ("zenn-article", "ja"),
    ("devto", "en"),
    ("substack", "ja"),
    ("substack", "en"),
    ("x-article", "ja"),
    ("x-article", "en"),
    ("x-post", "ja"),
}
WITHOUT_ZENN = REQUIRED - {("zenn-article", "ja")}
PENDING_ZENN_STATUSES = {"pending", "live-recorded"}


def run_jst_date(run_id: str) -> str | None:
    if re.fullmatch(r"daily-[0-9]{4}-[0-9]{2}-[0-9]{2}", run_id):
        return run_id.removeprefix("daily-")
    try:
        stamp = datetime.strptime(run_id, "%Y%m%d-%H%M%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return stamp.astimezone(ZoneInfo("Asia/Tokyo")).date().isoformat()


def run_order(run_id: str) -> tuple[datetime, str]:
    """Order mixed daily-* and UTC timestamp IDs by their actual start time."""
    if re.fullmatch(r"daily-[0-9]{4}-[0-9]{2}-[0-9]{2}", run_id):
        local_midnight = datetime.fromisoformat(
            f"{run_id.removeprefix('daily-')}T00:00:00"
        ).replace(tzinfo=ZoneInfo("Asia/Tokyo"))
        return local_midnight.astimezone(timezone.utc), run_id
    stamp = datetime.strptime(run_id, "%Y%m%d-%H%M%S").replace(tzinfo=timezone.utc)
    return stamp, run_id


def ledger_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def validated_live_set(
    rows: list[dict[str, Any]], run_id: str, required: set[tuple[str, str]]
) -> tuple[bool, str | None]:
    scripts = Path(__file__).resolve().parent
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from article_completion import validate_live_set  # pylint: disable=import-outside-toplevel

    exact, _, topic_id = validate_live_set(rows, run_id, required)
    return exact, topic_id


def validate_deferred_artifact(artifact: dict[str, Any], run_id: str, topic_id: str) -> None:
    scripts = Path(__file__).resolve().parent
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    module_path = scripts / "zenn-deferred-control.py"
    spec = importlib.util.spec_from_file_location("article_zenn_deferred_control", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Zenn deferred validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    module.validate_artifact(
        artifact,
        Path.home() / ".openclaw/workspace/zenn-articles",
        run_id,
        topic_id,
    )


def valid_zenn_pending(path: Path, run_id: str, topic_id: str | None) -> bool:
    try:
        artifact = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return False
    shape_valid = bool(
        isinstance(artifact, dict)
        and artifact.get("status") in PENDING_ZENN_STATUSES
        and artifact.get("run_id") == run_id
        and artifact.get("topic_id") == topic_id
        and isinstance(artifact.get("slug"), str)
        and re.fullmatch(r"[a-z0-9_-]{12,50}", artifact["slug"])
        and isinstance(artifact.get("title"), str)
        and artifact["title"].strip()
        and isinstance(artifact.get("markdown_file"), str)
        and artifact["markdown_file"]
        and isinstance(artifact.get("handed_off_at"), str)
        and artifact["handed_off_at"]
        and artifact.get("live_url") == f"https://zenn.dev/anicca/articles/{artifact['slug']}"
    )
    if not shape_valid or topic_id is None:
        return False
    try:
        validate_deferred_artifact(artifact, run_id, topic_id)
    except Exception:
        return False
    return True


def publication_plan(state_path: Path, ledger_path: Path) -> dict[str, Any]:
    scripts = Path(__file__).resolve().parent
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from publication_resume import PublicationStore  # pylint: disable=import-outside-toplevel

    return PublicationStore(state_path, ledger_path).plan()


def generation_resume_plan(run_dir: Path, ledger_path: Path) -> dict[str, Any]:
    scripts = Path(__file__).resolve().parent
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from article_generation_state import resume_decision  # pylint: disable=import-outside-toplevel

    return resume_decision(
        run_dir,
        run_dir.name,
        run_dir / "article-daily-prompt.txt",
        ledger_path,
    )


def _regular_json(path: Path) -> dict[str, Any] | None:
    if path.is_symlink() or not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return None
    return value if isinstance(value, dict) else None


def _quality_failure_feedback(
    gates: Path,
    run_id: str,
    language_quality: dict[str, Any],
) -> dict[str, Any] | None:
    """Return hash-bound actionable feedback from current terminal receipts."""

    items: list[dict[str, str]] = []
    receipt_sha256: dict[str, str] = {}
    article_sha256: dict[str, str] = {}
    for lang in ("ja", "en"):
        quality = language_quality.get(lang)
        if not isinstance(quality, dict):
            return None
        digest = quality.get("article_sha256")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            return None
        article_sha256[lang] = digest

        editorial_path = gates / f"editorial-{lang}.json"
        reader_path = gates / f"reader-testing-gate-{lang}.terminal.json"
        editorial = _regular_json(editorial_path)
        reader = _regular_json(reader_path)
        if (
            editorial is None
            or editorial.get("article_sha256") != digest
            or reader is None
            or reader.get("article_sha256") != digest
        ):
            return None
        receipt_sha256[f"editorial-{lang}"] = hashlib.sha256(
            editorial_path.read_bytes()
        ).hexdigest()
        receipt_sha256[f"reader-{lang}"] = hashlib.sha256(
            reader_path.read_bytes()
        ).hexdigest()

        if quality.get("editorial") == "FAIL":
            fixes = editorial.get("fixes")
            if not isinstance(fixes, list):
                return None
            editorial_items = [
                value.strip()
                for value in fixes
                if isinstance(value, str) and value.strip()
            ]
            if not editorial_items:
                return None
            items.extend(
                {
                    "id": f"editorial-{lang}-{index}",
                    "lang": lang,
                    "kind": "editorial_fix",
                    "text": text,
                }
                for index, text in enumerate(editorial_items, start=1)
            )

        if quality.get("reader") == "FAIL":
            payload = reader.get("payload")
            questions = (
                payload.get("unanswered_questions")
                if isinstance(payload, dict)
                else None
            )
            if not isinstance(questions, list):
                return None
            reader_items = [
                value.strip()
                for value in questions
                if isinstance(value, str) and value.strip()
            ]
            if not reader_items:
                return None
            items.extend(
                {
                    "id": f"reader-{lang}-{index}",
                    "lang": lang,
                    "kind": "reader_question",
                    "text": text,
                }
                for index, text in enumerate(reader_items, start=1)
            )
    if not items:
        return None
    feedback: dict[str, Any] = {
        "version": 1,
        "source_run_id": run_id,
        "article_sha256": article_sha256,
        "receipt_sha256": receipt_sha256,
        "items": items,
    }
    feedback["feedback_sha256"] = hashlib.sha256(
        json.dumps(
            feedback,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return feedback


def terminal_quality_finished_at(
    run_dir: Path,
    run_id: str,
    rows: list[dict[str, Any]],
) -> tuple[datetime, str, str, dict[str, Any]] | None:
    """Return a trusted terminal timestamp for an unpublished quality block."""
    gates = run_dir / "gates"
    if (gates / "publication-state.json").exists():
        return None
    # A terminal quality block deliberately writes one unpublished `quality`
    # carry-over row so the rejected topic and feedback remain auditable.  That
    # bookkeeping row is not a publication side effect and must not poison the
    # one bounded quality-replacement path.  Any destination row or published
    # row remains fail-closed because it may represent an irreversible remote
    # action even when the publication-state receipt is missing.
    if any(
        row.get("run_id") == run_id
        and (row.get("platform") != "quality" or row.get("published") is True)
        for row in rows
    ):
        return None

    quality = _regular_json(gates / "quality-self-heal.json")
    generation = _regular_json(gates / "generation-state.json")
    route = _regular_json(gates / "topic-route.json")
    if (
        quality is None
        or quality.get("version") != 2
        or quality.get("action") != "block_freeze"
        or int(quality.get("attempt", 0)) < 2
        or generation is None
        or generation.get("version") != 1
        or generation.get("run_id") != run_id
        or generation.get("status") != "provider-returned"
        or route is None
        or not isinstance(route.get("topic_id"), str)
        or not route["topic_id"].strip()
        or not isinstance(route.get("editorial_form"), str)
        or not route["editorial_form"].strip()
    ):
        return None

    language_quality = quality.get("quality")
    if not isinstance(language_quality, dict):
        return None
    for lang in ("ja", "en"):
        record = language_quality.get(lang)
        article = run_dir / f"article-{lang}.md"
        if (
            not isinstance(record, dict)
            or article.is_symlink()
            or not article.is_file()
            or record.get("article_sha256")
            != hashlib.sha256(article.read_bytes()).hexdigest()
            or record.get("evaluation_current") is not True
            or record.get("identity_current") is not True
            or record.get("ready") is not False
            or (
                record.get("editorial") != "FAIL"
                and record.get("reader") != "FAIL"
            )
        ):
            return None
    feedback = _quality_failure_feedback(gates, run_id, language_quality)
    if feedback is None:
        return None

    repair = _regular_json(gates / "quality-repair-state.json")
    if repair is not None and (
        repair.get("status") != "terminal-blocked"
        or repair.get("return_code") != 0
    ):
        return None

    attempts = generation.get("attempts")
    if not isinstance(attempts, list) or not attempts:
        return None
    final_attempt = attempts[-1]
    if (
        not isinstance(final_attempt, dict)
        or final_attempt.get("status") != "provider-returned"
        or final_attempt.get("return_code") != 0
        or not isinstance(final_attempt.get("finished_at"), str)
    ):
        return None
    try:
        finished = datetime.fromisoformat(
            final_attempt["finished_at"].replace("Z", "+00:00")
        )
    except ValueError:
        return None
    if finished.tzinfo is None:
        return None
    return (
        finished.astimezone(timezone.utc),
        route["topic_id"].strip(),
        route["editorial_form"].strip(),
        feedback,
    )


def decide(state_dir: Path | str, local_date: str) -> dict[str, str]:
    state_dir = Path(state_dir)
    runs_dir = state_dir / "runs"
    ledger = state_dir / "articles.jsonl"
    rows = ledger_rows(ledger)
    if not runs_dir.is_dir():
        return {"action": "new", "reason": "no-same-jst-day-run"}

    run_ids = sorted(
        (
            path.name
            for path in runs_dir.iterdir()
            if path.is_dir() and run_jst_date(path.name) == local_date
        ),
        key=run_order,
        reverse=True,
    )
    if not run_ids:
        return {"action": "new", "reason": "no-same-jst-day-run"}

    # Only the newest same-day run can own today's obligation.  Looking through it to an older
    # exact8 (or starting a third run) would hide a newer partial/ambiguous publication.
    run_id = run_ids[0]
    run_dir = runs_dir / run_id
    exact_eight, _ = validated_live_set(rows, run_id, REQUIRED)
    if exact_eight:
        return {"action": "skip-complete", "run_id": run_id, "reason": "same-jst-day-exact8"}
    exact_seven, topic_id = validated_live_set(rows, run_id, WITHOUT_ZENN)
    pending = run_dir / "gates" / "zenn-deferred.json"
    if exact_seven and valid_zenn_pending(pending, run_id, topic_id):
        return {
            "action": "skip-zenn-worker",
            "run_id": run_id,
            "reason": "same-jst-day-exact7-valid-pending",
        }

    state_path = run_dir / "gates" / "publication-state.json"
    if state_path.is_file() and not state_path.is_symlink():
        try:
            plan = publication_plan(state_path, ledger)
        except Exception:  # an unreadable/ambiguous irreversible state must never create a new article
            return {"action": "block-incomplete", "run_id": run_id, "reason": "same-jst-day-state-invalid"}
        if plan.get("resumable") is True:
            return {
                "action": "skip-pending-worker",
                "run_id": run_id,
                "reason": "same-jst-day-owned-by-pending-worker",
            }
        return {
            "action": "block-incomplete",
            "run_id": run_id,
            "reason": f"same-jst-day-not-resumable:{plan.get('reason', 'unknown')}",
        }

    generation = generation_resume_plan(run_dir, ledger)
    if generation.get("resumable") is True:
        if generation.get("status") == "interrupted-safe":
            reason = "same-jst-day-prepublication-interruption"
        elif generation.get("status") == "uninitialized-safe":
            reason = "same-jst-day-prepublication-uninitialized"
        else:
            reason = "same-jst-day-prepublication-provider-failure"
        return {
            "action": "resume-generation",
            "run_id": run_id,
            "reason": reason,
        }
    quality_terminal = terminal_quality_finished_at(run_dir, run_id, rows)
    if quality_terminal is not None:
        (
            quality_finished,
            forbidden_topic_id,
            forbidden_editorial_form,
            quality_failure_feedback,
        ) = quality_terminal
        if len(run_ids) >= 2:
            return {
                "action": "block-incomplete",
                "run_id": run_id,
                "reason": "same-jst-day-quality-replacement-limit",
            }
        replacement_id = quality_finished.strftime("%Y%m%d-%H%M%S")
        if run_jst_date(replacement_id) != local_date:
            return {
                "action": "block-incomplete",
                "run_id": run_id,
                "reason": "same-jst-day-quality-terminal-time-mismatch",
            }
        return {
            "action": "new-quality-replacement",
            "run_id": replacement_id,
            "replaced_run_id": run_id,
            "forbidden_topic_id": forbidden_topic_id,
            "forbidden_editorial_form": forbidden_editorial_form,
            "quality_failure_feedback": quality_failure_feedback,
            "reason": "same-jst-day-terminal-quality-block",
        }
    return {"action": "block-incomplete", "run_id": run_id, "reason": "same-jst-day-unclassified-run"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-dir", required=True)
    parser.add_argument("--local-date", required=True)
    args = parser.parse_args()
    print(json.dumps(decide(Path(args.state_dir), args.local_date), separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
