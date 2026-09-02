#!/usr/bin/env python3
"""Reclaim disk once a gig project's transaction is done, never before.

WHY: GigaFile-sourced buyer material cannot be re-downloaded, so `source/` and
`work/` are kept for the whole lifetime of a project. But once
`transaction_state == "取引完了"` (transaction complete) there is nothing left
to revise -- the buyer can no longer request changes -- and those two dirs are
pure disk pressure (measured 2026-08-08: one 納品確認待ち project alone holds
15G of `source/`, and disk was down to 9G free). `artifacts/`, `evidence/`,
`delivery/`, `state.json`, `events.jsonl` are untouched: they are cheap and
are the durable record.

SAFETY (fail-closed): any transaction_state other than "取引完了" -- including
納品確認待ち (awaiting buyer confirmation, buyer can still ask for a redo),
取引中 (in progress), a missing key, a missing/unparsable state.json -- is
skipped. One project's bad state.json must never stop the scan of the rest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path

COMPLETE_STATE = "取引完了"
RECLAIM_DIRS = ("source", "work")
ARTIFACT_DIRS = ("artifacts", "delivery", "deliverables")
IMMUTABLE_ROOT_PARTS = frozenset((".cloak", ".openclaw"))
IMMUTABLE_ROOT_NAMES = frozenset(("memory", "state"))
ACTIVE_FIELDS = frozenset("active revision subscription shared_ref shared_refs".split())
SHARED_FIELDS = frozenset(("shared_ref", "shared_refs"))
CONTRACT_GUARD_FIELDS = frozenset(
    "active revision subscription shared_ref shared_refs official_readback "
    "official_readback_status readback readback_status payment payment_status "
    "payment_received paid lesson lesson_status lesson_complete work_state "
    "queue_class next_action acceptance_status current_acceptance_status "
    "talkroom_state terminal_state formal_delivery formal_delivery_confirmed "
    "buyer_visible buyer_agreement_observed buyer_reply_after_artifact_observed "
    "buyer_feedback_pending_artifact artifact_ready_pending_browser "
    "buyer_formal_delivery_hold".split()
)
TRUE_TERMINAL_FIELDS = frozenset(
    "formal_delivery formal_delivery_confirmed buyer_visible "
    "buyer_agreement_observed buyer_reply_after_artifact_observed "
    "official_readback payment_received paid lesson_complete".split()
)
FALSE_TERMINAL_FIELDS = frozenset(
    "buyer_feedback_pending_artifact artifact_ready_pending_browser "
    "buyer_formal_delivery_hold".split()
)
UNCERTAIN_NONE_FIELDS = frozenset(
    "official_readback official_readback_status readback readback_status "
    "payment payment_status payment_received paid lesson lesson_status "
    "lesson_complete".split()
)
TERMINAL_MARKERS = frozenset("accepted cancelled closed complete completed confirmed "
                             "delivered done expired finalized inactive none not_required "
                             "paid received recorded settled verified 完了 確認済み 支払済み "
                             "受取済み 不要 なし".split())


def _project_ids_already_cleaned(ledger_path: Path) -> set[str]:
    """Idempotency: a project already recorded as cleaned writes no new row."""
    done: set[str] = set()
    if not ledger_path.exists():
        return done
    try:
        with ledger_path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                pid = row.get("project_id")
                if pid:
                    done.add(pid)
    except OSError:
        pass
    return done


def _dir_bytes(path: Path) -> int:
    total = 0
    for current, dirs, files in os.walk(path, onerror=lambda _e: None):
        dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(current, d))]
        for name in files:
            try:
                total += os.lstat(os.path.join(current, name)).st_size
            except OSError:
                continue
    return total


def _remove_dir(path: Path) -> int:
    """Rename-then-delete so a kill mid-removal leaves reapable trash, not a
    half-deleted dir that looks intact."""
    size = _dir_bytes(path)
    trash = path.with_name(f"{path.name}.janitor-trash.{os.getpid()}")
    try:
        os.rename(path, trash)
    except OSError:
        return 0
    shutil.rmtree(trash, ignore_errors=True)
    return size


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _prune_authorized_duplicates(project_dir: Path, *, dry_run: bool) -> dict:
    """Remove only byte-identical old packages named by an owner receipt."""
    receipt_path = project_dir / "context" / "owner-authorized-cleanup.json"
    result = {"deleted": [], "bytes_freed": 0}
    if not receipt_path.is_file():
        return result
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if (
        receipt.get("version") != 1
        or receipt.get("authority") != "account_owner_instruction"
        or receipt.get("disposition") != "retain_latest_package_remove_old_work_and_video"
        or receipt.get("remove_old_versions") is not True
    ):
        return result
    project_root = project_dir.resolve()
    retained = Path(str(receipt.get("retained_path", ""))).resolve()
    if project_root not in retained.parents or retained.is_symlink() or not retained.is_file():
        return result
    retained_bytes = receipt.get("retained_bytes")
    retained_sha = str(receipt.get("retained_sha256", "")).lower()
    if retained.stat().st_size != retained_bytes or len(retained_sha) != 64:
        return result
    if _sha256(retained) != retained_sha:
        return result

    candidates = []
    for dirname in ARTIFACT_DIRS:
        root = project_dir / dirname
        if not root.is_dir():
            continue
        for candidate in root.rglob("*"):
            if (
                candidate == retained
                or candidate.is_symlink()
                or not candidate.is_file()
                or candidate.suffix != retained.suffix
            ):
                continue
            if candidate.stat().st_size == retained_bytes and _sha256(candidate) == retained_sha:
                candidates.append(candidate)
    for candidate in candidates:
        result["deleted"].append(str(candidate.relative_to(project_dir)))
        result["bytes_freed"] += candidate.stat().st_size
        if not dry_run:
            candidate.unlink()
    return result


def _immutable_root_reason(projects_root: Path) -> str | None:
    try:
        resolved = projects_root.resolve()
    except OSError:
        return "projects_root_unresolvable"
    if resolved.name in IMMUTABLE_ROOT_NAMES or any(
        part in IMMUTABLE_ROOT_PARTS for part in resolved.parts
    ):
        return "immutable_store_root"
    return None


def _metadata_is_terminal(field: str, value: object) -> bool:
    if value is None or value == "":
        return field not in CONTRACT_GUARD_FIELDS
    if isinstance(value, bool):
        if field in ACTIVE_FIELDS:
            return not value
        if field in TRUE_TERMINAL_FIELDS:
            return value
        if field in FALSE_TERMINAL_FIELDS:
            return not value
        return False
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if field in {"payment_received", "paid"}:
            return value > 0
        return value == 0
    if isinstance(value, (list, tuple, set)):
        return not value
    if field in SHARED_FIELDS:
        return False
    if isinstance(value, dict):
        if not value:
            return field not in CONTRACT_GUARD_FIELDS
        for key in ("status", "state", "complete"):
            if key in value:
                value = value[key]
                break
        else:
            return False
    normalized = value.strip().casefold() if isinstance(value, str) else ""
    if field in {"transaction_state", "talkroom_state"}:
        return normalized == COMPLETE_STATE.casefold()
    if field in UNCERTAIN_NONE_FIELDS and normalized == "none":
        return False
    if field in {"acceptance_status", "current_acceptance_status"} and normalized == "pass":
        return True
    return normalized in TERMINAL_MARKERS


def _contract_reclaim_reason(state: dict) -> str | None:
    observed_states = [
        state.get(field) for field in ("transaction_state", "talkroom_state")
        if state.get(field) not in (None, "", "unknown")
    ]
    if COMPLETE_STATE not in observed_states:
        return "transaction_not_complete"
    if any(value != COMPLETE_STATE for value in observed_states):
        return "transaction_state_conflict"
    # Once both independently stored marketplace state fields say 取引完了, stale
    # workflow flags (pending feedback, next_action, work_state) cannot reopen the
    # room and must not retain regenerable source/work forever. Shared references
    # remain a real filesystem ownership constraint and still fail closed.
    for field in SHARED_FIELDS:
        if field in state and not _metadata_is_terminal(field, state[field]):
            return f"contract_guard:{field}"
    return None


def _contains_shared_reference(path: Path) -> bool:
    try:
        for current, dirs, files in os.walk(path, followlinks=False):
            for name in dirs:
                if (Path(current) / name).is_symlink():
                    return True
            for name in files:
                candidate = Path(current) / name
                if candidate.is_symlink() or candidate.lstat().st_nlink > 1:
                    return True
    except OSError:
        return True
    return False


def scan(projects_root: Path, ledger_path: Path, *, dry_run: bool) -> dict:
    already_cleaned = _project_ids_already_cleaned(ledger_path)
    summary = {
        "scanned": 0,
        "cleaned": 0,
        "skipped": 0,
        "errors": 0,
        "bytes_freed": 0,
        "dry_run": dry_run,
        "would_clean": [],
        "artifacts_cleaned": 0,
        "artifact_bytes_freed": 0,
    }
    if not projects_root.is_dir():
        return summary
    immutable_reason = _immutable_root_reason(projects_root)
    if immutable_reason:
        summary["errors"] = 1
        print(f"project_janitor: refusing {projects_root}: {immutable_reason}", file=sys.stderr)
        return summary

    for project_dir in sorted(projects_root.iterdir()):
        if not project_dir.is_dir():
            continue
        state_path = project_dir / "state.json"
        if not state_path.is_file():
            continue
        summary["scanned"] += 1
        project_id = project_dir.name
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
            reclaim_reason = _contract_reclaim_reason(state)
            if reclaim_reason:
                summary["skipped"] += 1
                continue

            artifact_result = _prune_authorized_duplicates(project_dir, dry_run=dry_run)
            if artifact_result["deleted"]:
                summary["artifacts_cleaned"] += 1
                summary["artifact_bytes_freed"] += artifact_result["bytes_freed"]
                summary["bytes_freed"] += artifact_result["bytes_freed"]
                if not dry_run:
                    artifact_ledger = ledger_path.with_name("artifact-janitor.jsonl")
                    artifact_record = {
                        "ts": int(time.time()),
                        "project_id": project_id,
                        **artifact_result,
                    }
                    artifact_ledger.parent.mkdir(parents=True, exist_ok=True)
                    with artifact_ledger.open("a", encoding="utf-8") as handle:
                        handle.write(json.dumps(artifact_record, ensure_ascii=False) + "\n")

            if project_id in already_cleaned:
                continue  # source/work already recorded; artifact pruning still ran above

            targets = [
                project_dir / name
                for name in RECLAIM_DIRS
                if (project_dir / name).exists()
            ]
            if not targets:
                continue  # already clean (e.g. cleaned manually) -- no ledger row
            if any(_contains_shared_reference(target) for target in targets):
                summary["skipped"] += 1
                continue

            if dry_run:
                bytes_would_free = sum(_dir_bytes(t) for t in targets)
                summary["would_clean"].append(
                    {
                        "project_id": project_id,
                        "deleted": [t.name for t in targets],
                        "bytes_freed": bytes_would_free,
                    }
                )
                summary["cleaned"] += 1
                summary["bytes_freed"] += bytes_would_free
                continue

            deleted = []
            bytes_freed = 0
            for target in targets:
                bytes_freed += _remove_dir(target)
                deleted.append(target.name)

            record = {
                "ts": int(time.time()),
                "project_id": project_id,
                "deleted": deleted,
                "bytes_freed": bytes_freed,
                "transaction_state": state.get("transaction_state") or state.get("talkroom_state"),
            }
            ledger_path.parent.mkdir(parents=True, exist_ok=True)
            with ledger_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")

            summary["cleaned"] += 1
            summary["bytes_freed"] += bytes_freed
        except Exception as exc:  # noqa: BLE001 -- one bad project must not stop the scan
            summary["errors"] += 1
            print(f"project_janitor: skipping {project_id}: {exc}", file=sys.stderr)
            continue

    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    default_root = Path(os.environ.get("GIG_STATE_DIR", str(Path.home() / "gig")))
    parser.add_argument(
        "--projects-root",
        type=Path,
        default=Path(os.environ.get("GIG_PROJECTS_ROOT", str(default_root / "projects"))),
    )
    parser.add_argument(
        "--ledger",
        type=Path,
        default=Path(os.environ.get("GIG_JANITOR_LEDGER", str(default_root / "janitor.jsonl"))),
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    summary = scan(args.projects_root, args.ledger, dry_run=args.dry_run)
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
