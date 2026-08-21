#!/usr/bin/env python3
"""Choose a safe start without replaying an unfinished or published run.

The launchd wrapper asks this before it allocates a new RUN_TS.  Decisions are based on
durable run/ledger artifacts, never wall-clock proximity to the 06:00 trigger.  A completed
run does not reserve the rest of the JST day: the caller may allocate a fresh run identity
for another topic.  Duplicate protection remains bound to the immutable run/topic/artifact
and publisher receipts.
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

from publication_contract import ACTIVE_PAIRS
from publication_contract_resolver import (
    PublicationContractError,
    resolve_publication_contract,
)
from quarantine_invalid_run import QuarantineError, proof


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
ACTIVE_REQUIRED = {
    (pair.split("/", 1)[0], pair.split("/", 1)[1]) for pair in ACTIVE_PAIRS
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


def persisted_publication_contract(run_dir: Path) -> str | None:
    """Read the run's explicit contract before classifying a completed ledger.

    The active-four subset is not evidence that a legacy exact-eight run is
    complete: an old run can have published the same four current destinations
    while its four legacy destinations are still pending.  Missing or malformed
    state therefore stays fail-closed instead of being treated as a new run.
    """

    state = _regular_json(run_dir / "gates" / "publication-state.json")
    if state is None:
        return None
    try:
        return resolve_publication_contract(
            run_dir / "gates" / "publication-state.json",
            run_dir.parent.parent / "articles.jsonl",
            run_dir.name,
            state=state,
        )
    except (PublicationContractError, TypeError, ValueError):
        return None


def _preflight_only_run(run_dir: Path, rows: list[dict[str, Any]], run_id: str) -> bool:
    """Allow a same-day retry when the earlier wake never reached generation.

    A demand-authority miss happens after the wrapper has created the run record and
    consumed the baseline strategy.  That record contains no prompt, draft, gate,
    publication state, or ledger row, so reusing its stable daily id cannot replay an
    external side effect.  Any additional artifact keeps the normal fail-closed
    classification below.
    """

    if run_dir.is_symlink() or not run_dir.is_dir():
        return False
    if any(row.get("run_id") == run_id for row in rows):
        return False
    git_hash = run_dir / "git-hash.txt"
    gates = run_dir / "gates"
    strategy_path = gates / "strategy-consumption.json"
    if (
        git_hash.is_symlink()
        or not git_hash.is_file()
        or gates.is_symlink()
        or not gates.is_dir()
        or strategy_path.is_symlink()
        or not strategy_path.is_file()
    ):
        return False
    strategy = _regular_json(run_dir / "gates" / "strategy-consumption.json")
    if not (
        strategy is not None
        and strategy.get("run_id") == run_id
        and strategy.get("status") == "baseline"
        and strategy.get("versions") == []
    ):
        return False
    # Enumerate every direct descendant rather than only regular files.  A symlink,
    # FIFO, socket, empty nested directory, or unexpected regular file is evidence
    # that the run progressed beyond the harmless preflight boundary.
    if {
        child.name for child in run_dir.iterdir()
    } != {"git-hash.txt", "gates"}:
        return False
    return {
        child.name for child in gates.iterdir()
    } == {"strategy-consumption.json"}


def _exhausted_prepublication_archive(
    state_dir: Path, run_dir: Path, run_id: str, rows: list[dict[str, Any]],
) -> bool:
    """Release a run only after its bounded generation archive is complete.

    A timeout archive can move the immutable prompt and generation state out of
    the run directory.  Once all charged attempts are exhausted, that old run
    cannot be resumed; a new identity is safe only when the run contains no
    publication/ledger row and the latest archive has the complete
    pre-publication artifact set with no symlink or publication-state file.
    """
    for row in rows:
        if row.get("run_id") != run_id:
            continue
        if (
            row.get("published") is True
            or bool(row.get("draft_url"))
            or bool(row.get("live_url"))
            or row.get("state") == "live"
            or row.get("reality_gate") == "PASS"
        ):
            return False
    if run_dir.is_symlink() or not run_dir.is_dir():
        return False
    for path in run_dir.rglob("*"):
        if path.is_symlink():
            return False
        relative = str(path.relative_to(run_dir))
        if path.is_file() and not relative.startswith(
            ("gates/judge-broker/", "gates/.attempts/", "gates/media-candidates/")
        ):
            return False
    archive_parent = state_dir / "interrupted-generation" / run_id
    attempts = sorted(
        (
            path for path in archive_parent.iterdir()
            if path.is_dir() and path.name.startswith("attempt-")
            and path.name.removeprefix("attempt-").isdigit()
        ),
        key=lambda path: int(path.name.removeprefix("attempt-")),
    ) if archive_parent.is_dir() and not archive_parent.is_symlink() else []
    if not attempts:
        return False
    latest = attempts[-1]
    required = (
        "article-en.md", "article-ja.md", "headline-image.png",
        "body-diagram.png", "gates/quality-terminal-en.json",
        "gates/quality-terminal-ja.json",
    )
    if any(
        not (latest / relative).is_file()
        or (latest / relative).is_symlink()
        for relative in required
    ):
        return False
    return not any(
        path.name == "publication-state.json"
        for path in latest.rglob("*")
        if path.is_file() or path.is_symlink()
    )


def _unpublished_quality_audit(row: dict[str, Any]) -> bool:
    state = row.get("state")
    legacy = row.get("platform") == "quality" and row.get("published") is False
    current = bool(
        row.get("platform") is None
        and row.get("lang") in {"ja", "en"}
        and state == "quality-blocked:block_freeze"
        and row.get("published") is False
        and row.get("verified_logged_in") is False
        and row.get("draft_url") is None
        and row.get("live_url") is None
        and isinstance(row.get("topic_id"), str)
        and row.get("topic_id", "").strip()
        and row.get("topic_source") == "paid-demand"
        and isinstance(row.get("editorial_form"), str)
        and row.get("editorial_form", "").strip()
    )
    return legacy or current


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
        and not _unpublished_quality_audit(row)
        for row in rows
    ):
        return None

    terminal_path = gates / "terminal-quality-blocked.json"
    terminal = _regular_json(terminal_path)
    quality_path = gates / "quality-self-heal.json"
    blocker_path = gates / "quality-repair-blocker.json"
    route = _regular_json(gates / "topic-route.json")
    if terminal is not None:
        drafts = terminal.get("drafts")
        if not (
            terminal.get("version") == 1
            and terminal.get("status") == "terminal_quality_blocked"
            and terminal.get("run_id") == run_id
            and terminal.get("publication") in {None, "not_started"}
            and isinstance(drafts, dict)
            and quality_path.is_file()
            and blocker_path.is_file()
            and terminal.get("quality_sha256") == hashlib.sha256(quality_path.read_bytes()).hexdigest()
            and terminal.get("blocker_sha256") == hashlib.sha256(blocker_path.read_bytes()).hexdigest()
            and route
            and terminal.get("topic_id") == route.get("topic_id")
            and terminal.get("editorial_form") == route.get("editorial_form")
            and all(
                (run_dir / f"article-{lang}.md").is_file()
                and not (run_dir / f"article-{lang}.md").is_symlink()
                and drafts.get(lang) == hashlib.sha256((run_dir / f"article-{lang}.md").read_bytes()).hexdigest()
                for lang in ("ja", "en")
            )
            and isinstance(terminal.get("quality_failure_feedback"), dict)
        ):
            return None
        try:
            finished = datetime.fromisoformat(str(terminal["created_at"]).replace("Z", "+00:00"))
        except (KeyError, ValueError):
            return None
        if finished.tzinfo is None:
            return None
        return (
            finished.astimezone(timezone.utc),
            str(terminal["topic_id"]),
            str(terminal["editorial_form"]),
            terminal["quality_failure_feedback"],
        )

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
    failed_languages = quality.get("failed_languages")
    if failed_languages is None:
        # Version-2 historical terminal receipts predate the explicit summary;
        # derive it only from their hash-bound per-language readiness.
        failed_languages = [
            lang
            for lang in ("ja", "en")
            if isinstance(language_quality.get(lang), dict)
            and language_quality[lang].get("ready") is False
        ]
    if (
        not isinstance(failed_languages, list)
        or not failed_languages
        or any(lang not in {"ja", "en"} for lang in failed_languages)
        or len(set(failed_languages)) != len(failed_languages)
    ):
        return None
    failed_set = set(failed_languages)
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
        ):
            return None
        if lang in failed_set:
            if record.get("ready") is not False or (
                record.get("editorial") != "FAIL"
                and record.get("reader") != "FAIL"
            ):
                return None
        elif (
            record.get("ready") is not True
            or record.get("editorial") != "PASS"
            or record.get("reader") != "PASS"
        ):
            return None
    feedback = _quality_failure_feedback(gates, run_id, language_quality)
    if feedback is None:
        return None

    repair = _regular_json(gates / "quality-repair-state.json")
    if repair is not None and (
        repair.get("status") != "terminal-blocked"
        or repair.get("attempts") not in {1, 2}
        or not isinstance(repair.get("return_code"), int)
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

    # Only the newest same-day run can own an unfinished obligation.  Once its
    # persisted contract is complete, return `new` so the wrapper can allocate
    # a fresh run identity for another article today. Looking through a newer
    # partial/ambiguous run would still hide unsafe publication state.
    run_id = run_ids[0]
    run_dir = runs_dir / run_id
    contract = persisted_publication_contract(run_dir)
    exact_eight, _ = validated_live_set(rows, run_id, REQUIRED)
    if contract == "legacy-exact8" and exact_eight:
        return {
            "action": "new",
            "run_id": "",
            "previous_run_id": run_id,
            "reason": "new-after-complete:legacy-exact8",
        }
    # Only an explicit active-four publication state can release the same-day
    # start gate after four receipts.  A legacy exact-eight run with the same
    # four rows is still incomplete and must remain resumable/blocking.
    if contract == "active-four":
        active_four, _ = validated_live_set(rows, run_id, ACTIVE_REQUIRED)
        if active_four:
            return {
                "action": "new",
                "run_id": "",
                "previous_run_id": run_id,
                "reason": "new-after-complete:active-four",
            }
    exact_seven, topic_id = validated_live_set(rows, run_id, WITHOUT_ZENN)
    pending = run_dir / "gates" / "zenn-deferred.json"
    if exact_seven and valid_zenn_pending(pending, run_id, topic_id):
        return {
            "action": "skip-zenn-worker",
            "run_id": run_id,
            "reason": "same-jst-day-exact7-valid-pending",
        }

    # Recompute the immutable invalid-media/no-live proof at every decision.  The
    # optional quarantine receipt is audit evidence only; a hand-written receipt
    # cannot release the gate without this fresh proof.
    try:
        proof(state_dir, run_id)
    except (OSError, QuarantineError):
        pass
    else:
        return {
            "action": "new",
            "run_id": "",
            "previous_run_id": run_id,
            "reason": "same-jst-day-invalid-media-proof",
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
    if _exhausted_prepublication_archive(state_dir, run_dir, run_id, rows):
        return {
            "action": "new",
            "run_id": "",
            "previous_run_id": run_id,
            "reason": "same-jst-day-exhausted-prepublication-archive",
        }
    if _preflight_only_run(run_dir, rows, run_id):
        return {
            "action": "new",
            "run_id": run_id,
            "reason": "same-jst-day-preflight-only-run",
        }
    generation_state = _regular_json(
        run_dir / "gates" / "generation-state.json"
    )
    quality = _regular_json(run_dir / "gates" / "quality-self-heal.json")
    records = quality.get("quality") if quality else None
    quality_reroute = bool(
        generation_state
        and generation_state.get("status") == "provider-returned"
        and quality
        and quality.get("version") == 2
        and quality.get("attempt") == 1
        and quality.get("action") == "reroute"
        and isinstance(records, dict)
        and not any(
            row.get("run_id") == run_id and row.get("published") is True
            for row in rows
        )
        and all(
            (run_dir / f"article-{lang}.md").is_file()
            and not (run_dir / f"article-{lang}.md").is_symlink()
            and records.get(lang, {}).get("article_sha256")
            == hashlib.sha256(
                (run_dir / f"article-{lang}.md").read_bytes()
            ).hexdigest()
            for lang in ("ja", "en")
        )
    )
    if quality_reroute:
        return {
            "action": "resume-generation",
            "run_id": run_id,
            "reason": "same-jst-day-quality-reroute",
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
                "action": "skip-quality-miss",
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
