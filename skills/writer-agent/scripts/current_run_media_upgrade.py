#!/usr/bin/env python3
"""Crash-safe one-time upgrade of an imported exact7 canonical media package."""

from __future__ import annotations

import argparse
import copy
import fcntl
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
from canonical_media import attach_media_contract, validate_media_contract  # noqa: E402
from publication_remote import probe  # noqa: E402
from publication_resume import validate_receipt_evidence  # noqa: E402


ARTICLE_PAIRS = (
    "note/ja",
    "devto/en",
    "substack/ja",
    "substack/en",
    "x-article/ja",
    "x-article/en",
)
LEDGER_EVIDENCE_KEYS = (
    "verified",
    "public_id",
    "published_at",
    "stable_target",
    "artifact_sha256",
    "language",
    "content_verified",
    "asset_hashes",
    "asset_urls",
    "asset_proofs",
    "native_asset_count",
    "asset_verified",
    "eyecatch_verified",
    "body_media_verified",
    "cover_verified",
    "source",
    "readback_source",
    "destination_identity",
    "identity_verified",
    "identity_source",
    "table_media_verified",
    "table_asset_proofs",
)


class MediaUpgradeRefused(RuntimeError):
    """The package or fresh public readback is not safe to migrate."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _atomic_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("wb") as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    _atomic_bytes(
        path,
        (
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        ).encode(),
    )


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise MediaUpgradeRefused(f"invalid JSON: {path}") from error
    if not isinstance(value, dict):
        raise MediaUpgradeRefused(f"JSON object required: {path}")
    return value


def _ledger_rows(path: Path) -> list[dict[str, Any]]:
    try:
        rows = [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    except (OSError, json.JSONDecodeError) as error:
        raise MediaUpgradeRefused("publication ledger is invalid") from error
    if any(not isinstance(row, dict) for row in rows):
        raise MediaUpgradeRefused("publication ledger rows must be objects")
    return rows


def _pair_for_row(state: dict[str, Any], row: dict[str, Any]) -> str | None:
    for pair in ARTICLE_PAIRS:
        entry = state["pairs"][pair]
        if (
            row.get("run_id") == state["run_id"]
            and row.get("topic_id") == state["topic_id"]
            and row.get("platform") == entry["platform"]
            and row.get("lang") == entry["lang"]
            and row.get("published") is True
        ):
            return pair
    return None


def upgrade_current_run(
    state_path: Path,
    ledger_path: Path,
    *,
    probe_fn: Callable[[str, str, dict[str, Any]], dict[str, Any]] = probe,
    validate_fn: Callable[[dict[str, Any], str, str, dict[str, Any]], None] = (
        validate_receipt_evidence
    ),
) -> dict[str, Any]:
    state_path = Path(state_path)
    ledger_path = Path(ledger_path)
    run_dir = state_path.parent.parent
    state_backup_path = state_path.with_name(f"{state_path.name}.bak")
    journal_path = state_path.parent / "canonical-media-upgrade.json"
    recovered_prepared_at: str | None = None
    if journal_path.is_file():
        journal = _read_json(journal_path)
        if journal.get("status") == "committed":
            state = _read_json(state_path)
            for lang in ("ja", "en"):
                draft = Path(state["drafts"][lang]["path"])
                validate_media_contract(draft.read_text(encoding="utf-8"))
                if sha256(draft) != state["drafts"][lang]["sha256"]:
                    raise MediaUpgradeRefused("committed canonical draft changed")
            return {"status": "already-committed", "journal": str(journal_path)}
        if journal.get("status") == "prepared":
            backup = Path(str(journal.get("backup_dir", "")))
            expected_backup = state_path.parent / "canonical-media-upgrade.backup"
            if backup.resolve(strict=False) != expected_backup.resolve(strict=False):
                raise MediaUpgradeRefused("prepared upgrade backup path is invalid")
            restore = (
                (backup / "article-ja.md", run_dir / "article-ja.md"),
                (backup / "article-en.md", run_dir / "article-en.md"),
                (backup / "publication-state.json", state_path),
                (backup / "publication-state.json.bak", state_backup_path),
                (backup / "articles.jsonl", ledger_path),
            )
            if any(not source.is_file() for source, _destination in restore):
                raise MediaUpgradeRefused("prepared upgrade backup is incomplete")
            for source, destination in restore:
                _atomic_bytes(destination, source.read_bytes())
            recovered_prepared_at = utc_now()
            journal.update(
                status="recovered",
                recovered_prepared_at=recovered_prepared_at,
            )
            _atomic_json(journal_path, journal)

    state = _read_json(state_path)
    if not state_backup_path.is_file():
        raise MediaUpgradeRefused("publication state backup is missing")
    if state.get("run_dir") != str(run_dir) or state.get("run_id") != run_dir.name:
        raise MediaUpgradeRefused("publication state is outside its canonical run")
    if state.get("pairs", {}).get("zenn-article/ja", {}).get("status") == "live":
        raise MediaUpgradeRefused("terminal exact8 package is immutable")
    if any(state.get("pairs", {}).get(pair, {}).get("status") != "live" for pair in ARTICLE_PAIRS):
        raise MediaUpgradeRefused("all six article receipts must already be live")

    drafts: dict[str, Path] = {}
    old_hashes: dict[str, str] = {}
    new_bytes: dict[str, bytes] = {}
    candidate = copy.deepcopy(state)
    temporary_paths: list[Path] = []
    try:
        for lang in ("ja", "en"):
            descriptor = state.get("drafts", {}).get(lang, {})
            draft = Path(str(descriptor.get("path", "")))
            if draft != run_dir / f"article-{lang}.md" or not draft.is_file():
                raise MediaUpgradeRefused(f"{lang} canonical draft path is invalid")
            current_hash = sha256(draft)
            if current_hash != descriptor.get("sha256"):
                raise MediaUpgradeRefused(f"{lang} canonical draft already changed")
            drafts[lang] = draft
            old_hashes[lang] = current_hash
            upgraded = attach_media_contract(draft.read_text(encoding="utf-8"))
            encoded = upgraded.encode()
            new_bytes[lang] = encoded
            temporary = state_path.parent / f".article-{lang}.media-upgrade"
            _atomic_bytes(temporary, encoded)
            temporary_paths.append(temporary)
            candidate["drafts"][lang] = {
                "path": str(temporary),
                "sha256": hashlib.sha256(encoded).hexdigest(),
            }

        evidence_by_pair: dict[str, dict[str, Any]] = {}
        for pair in ARTICLE_PAIRS:
            entry = state["pairs"][pair]
            observed = probe_fn(pair, str(entry["target"]), candidate)
            if (
                observed.get("status") != "live"
                or observed.get("verified") is not True
                or observed.get("live_url")
                != entry.get("receipt", {}).get("live_url")
            ):
                raise MediaUpgradeRefused(
                    f"fresh public readback is not live for {pair}"
                )
            validate_fn(candidate, pair, observed["live_url"], observed)
            evidence_by_pair[pair] = observed

        recorded_at = utc_now()
        for lang in ("ja", "en"):
            candidate["drafts"][lang]["path"] = str(drafts[lang])
        for pair, evidence in evidence_by_pair.items():
            candidate["pairs"][pair]["receipt"] = {
                "live_url": evidence["live_url"],
                "evidence": evidence,
                "recorded_at": recorded_at,
            }
        new_hashes = {
            lang: candidate["drafts"][lang]["sha256"] for lang in ("ja", "en")
        }
        candidate["canonical_media_upgrade"] = {
            "version": 1,
            "upgraded_at": recorded_at,
            "old_draft_sha256": old_hashes,
            "new_draft_sha256": new_hashes,
            "fresh_readback_pairs": list(ARTICLE_PAIRS),
        }

        rows = _ledger_rows(ledger_path)
        matched: dict[str, int] = {pair: 0 for pair in ARTICLE_PAIRS}
        for row in rows:
            pair = _pair_for_row(state, row)
            if pair is None:
                continue
            matched[pair] += 1
            evidence = evidence_by_pair[pair]
            for key in LEDGER_EVIDENCE_KEYS:
                if key in evidence:
                    row[key] = evidence[key]
                else:
                    row.pop(key, None)
            row["canonical_media_revalidated_at"] = recorded_at
        if any(count != 1 for count in matched.values()):
            raise MediaUpgradeRefused(
                "ledger must contain exactly one row for each live article pair"
            )
        ledger_bytes = "".join(
            json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
            for row in rows
        ).encode()

        backup = state_path.parent / "canonical-media-upgrade.backup"
        backup.mkdir(parents=True, exist_ok=True)
        for source, name in (
            (drafts["ja"], "article-ja.md"),
            (drafts["en"], "article-en.md"),
            (state_path, "publication-state.json"),
            (state_backup_path, "publication-state.json.bak"),
            (ledger_path, "articles.jsonl"),
        ):
            destination = backup / name
            if not destination.exists():
                shutil.copyfile(source, destination)
        journal = {
            "version": 1,
            "status": "prepared",
            "run_id": state["run_id"],
            "prepared_at": recorded_at,
            "old_draft_sha256": old_hashes,
            "new_draft_sha256": new_hashes,
            "backup_dir": str(backup),
            "fresh_readback": {
                pair: evidence_by_pair[pair]["live_url"] for pair in ARTICLE_PAIRS
            },
        }
        if recovered_prepared_at is not None:
            journal["recovered_prepared_at"] = recovered_prepared_at
        _atomic_json(journal_path, journal)
        for lang in ("ja", "en"):
            _atomic_bytes(drafts[lang], new_bytes[lang])
        _atomic_bytes(ledger_path, ledger_bytes)
        _atomic_json(state_path, candidate)
        _atomic_json(state_backup_path, candidate)
        journal.update(status="committed", committed_at=utc_now())
        _atomic_json(journal_path, journal)
        return {
            "status": "committed",
            "journal": str(journal_path),
            "old_draft_sha256": old_hashes,
            "new_draft_sha256": new_hashes,
            "fresh_readback_pairs": list(ARTICLE_PAIRS),
        }
    finally:
        for temporary in temporary_paths:
            temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--publication-state", required=True, type=Path)
    parser.add_argument("--ledger", required=True, type=Path)
    args = parser.parse_args()
    state_path = args.publication_state.resolve(strict=True)
    state_root = state_path.parent.parent.parent.parent
    publication_lock = state_root / ".article-daily.lockdir"
    try:
        publication_lock.mkdir()
    except FileExistsError as error:
        raise MediaUpgradeRefused("shared publication lock is busy") from error
    lock_path = state_path.parent / f".{state_path.name}.lock"
    try:
        with lock_path.open("a+") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            result = upgrade_current_run(state_path, args.ledger.resolve(strict=True))
    finally:
        publication_lock.rmdir()
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except MediaUpgradeRefused as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        raise SystemExit(2)
