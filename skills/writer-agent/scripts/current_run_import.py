#!/usr/bin/env python3
"""Import one frozen Writer Engine run into the exact8 repair ledger.

This is a migration boundary, not a publisher. It copies immutable artifacts,
pins the six already-public IDs as repair-required, and registers the two
pending stable targets. It never creates, updates, or deletes remote content.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any


SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
from publication_resume import (  # noqa: E402
    REQUIRED_PAIRS,
    TARGET_KINDS,
    InvariantError,
    PublicationStore,
)
from canonical_media import attach_media_contract  # noqa: E402


RUN_ID = re.compile(r"daily-\d{4}-\d{2}-\d{2}")
ZENN_SLUG = re.compile(r"[a-z0-9_-]{12,50}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _atomic_copy(source: Path, destination: Path) -> None:
    source = source.resolve(strict=True)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if not destination.is_file() or sha256(destination) != sha256(source):
            raise InvariantError(
                f"canonical import target conflicts with frozen artifact: {destination}"
            )
        return
    temporary = destination.with_name(f".{destination.name}.{os.getpid()}.tmp")
    with source.open("rb") as reader, temporary.open("wb") as writer:
        while chunk := reader.read(1024 * 1024):
            writer.write(chunk)
        writer.flush()
        os.fsync(writer.fileno())
    os.replace(temporary, destination)


def _atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _one(
    database: sqlite3.Connection,
    query: str,
    parameters: tuple[Any, ...],
) -> sqlite3.Row:
    rows = database.execute(query, parameters).fetchall()
    if len(rows) != 1:
        raise InvariantError("frozen Writer Engine identity is missing or ambiguous")
    return rows[0]


def _artifact_for_pair(source_run: Path, pair: str) -> Path:
    if pair == "x-post/ja":
        return source_run / "xpost/ja.txt"
    return source_run / f"drafts/{pair.rsplit('/', 1)[1]}.md"


def _target(
    database: sqlite3.Connection,
    run_id: str,
    pair: str,
    row: sqlite3.Row,
    *,
    zenn_slug: str,
) -> str:
    if pair == "zenn-article/ja":
        return zenn_slug
    if pair == "x-post/ja":
        return run_id
    if pair == "x-article/en":
        attempt = _one(
            database,
            "SELECT target FROM publication_attempts WHERE intent_key = ?",
            (f"{run_id}:{pair}",),
        )
        target = str(attempt["target"] or "")
        if not target.startswith("https://x.com/compose/articles/edit/"):
            raise InvariantError("frozen X English draft target is invalid")
        return target
    public_id = str(row["public_id"] or "")
    if pair == "x-article/ja":
        return f"https://x.com/compose/articles/edit/{public_id}"
    return public_id


def import_run(
    writer_database: Path,
    run_id: str,
    state_root: Path,
    headline_source: Path,
    body_diagram_source: Path,
    *,
    zenn_slug: str,
) -> dict[str, Any]:
    if RUN_ID.fullmatch(run_id) is None:
        raise InvariantError("frozen run ID is invalid")
    if ZENN_SLUG.fullmatch(zenn_slug) is None:
        raise InvariantError("stable Zenn slug is invalid")
    writer_database = Path(writer_database).resolve(strict=True)
    state_root = Path(state_root).resolve(strict=False)
    with sqlite3.connect(f"file:{writer_database}?mode=ro", uri=True) as database:
        database.row_factory = sqlite3.Row
        run = _one(
            database,
            "SELECT * FROM daily_runs WHERE run_id = ?",
            (run_id,),
        )
        if (
            run["status"] != "PENDING"
            or run["safety_status"] != "ALLOW"
            or not str(run["topic_card_sha256"] or "")
        ):
            raise InvariantError("frozen run is not an ALLOW pending run")
        source_run = Path(str(run["run_dir"])).resolve(strict=True)
        if source_run.name != run_id:
            raise InvariantError("frozen run directory does not match run ID")
        pairs = database.execute(
            "SELECT * FROM daily_pairs WHERE run_id = ? ORDER BY pair",
            (run_id,),
        ).fetchall()
        if {str(row["pair"]) for row in pairs} != set(REQUIRED_PAIRS):
            raise InvariantError("frozen run does not contain exact8 membership")

        pair_rows = {str(row["pair"]): row for row in pairs}
        for pair in REQUIRED_PAIRS:
            artifact = _artifact_for_pair(source_run, pair).resolve(strict=True)
            if (
                Path(str(pair_rows[pair]["artifact_path"])).resolve(strict=True)
                != artifact
            ):
                raise InvariantError(f"frozen artifact path conflicts for {pair}")
            attempt = _one(
                database,
                (
                    "SELECT artifact_sha256 FROM publication_attempts "
                    "WHERE intent_key = ?"
                ),
                (f"{run_id}:{pair}",),
            )
            if attempt["artifact_sha256"] != sha256(artifact):
                raise InvariantError(f"frozen artifact hash conflicts for {pair}")

        canonical = state_root / "runs" / run_id
        _atomic_copy(source_run / "drafts/ja.md", canonical / "article-ja.md")
        _atomic_copy(source_run / "drafts/en.md", canonical / "article-en.md")
        for lang in ("ja", "en"):
            draft = canonical / f"article-{lang}.md"
            _atomic_text(
                draft,
                attach_media_contract(draft.read_text(encoding="utf-8")),
            )
        _atomic_copy(source_run / "xpost/ja.txt", canonical / "x-post-ja.txt")
        _atomic_copy(Path(headline_source), canonical / "headline-image.png")
        _atomic_copy(Path(body_diagram_source), canonical / "body-diagram.png")

        state_path = canonical / "gates/publication-state.json"
        ledger_path = state_root / "articles.jsonl"
        store = PublicationStore(state_path, ledger_path)
        topic_id = f"writer-engine:{run['topic_card_sha256']}"
        store.initialize(
            run_id,
            canonical,
            topic_id,
            {
                "ja": canonical / "article-ja.md",
                "en": canonical / "article-en.md",
            },
            "ALLOW",
            3,
            x_post=canonical / "x-post-ja.txt",
            headline_image=canonical / "headline-image.png",
            body_assets=[canonical / "body-diagram.png"],
        )

        targets: dict[str, str] = {}
        live_ids: dict[str, str] = {}
        for pair in REQUIRED_PAIRS:
            row = pair_rows[pair]
            target = _target(
                database,
                run_id,
                pair,
                row,
                zenn_slug=zenn_slug,
            )
            targets[pair] = target
            store.register_intent(pair, TARGET_KINDS[pair], target)
            if (
                row["status"] == "LIVE"
                and int(row["published"] or 0) == 1
                and row["reality_gate"] == "PASS"
            ):
                store.register_existing_live(
                    pair,
                    TARGET_KINDS[pair],
                    target,
                    live_url=str(row["live_url"] or ""),
                    public_id=str(row["public_id"] or ""),
                    published_at=str(row["published_at"] or ""),
                )
                live_ids[pair] = str(row["public_id"])
            elif row["status"] != "PENDING" or int(row["published"] or 0):
                raise InvariantError(f"frozen pair status is ambiguous for {pair}")

        receipt = {
            "version": 1,
            "run_id": run_id,
            "topic_id": topic_id,
            "source_database": str(writer_database),
            "source_run_dir": str(source_run),
            "source_runtime": str(run["runtime"] or ""),
            "source_draft_sha256": {
                "ja": sha256(source_run / "drafts/ja.md"),
                "en": sha256(source_run / "drafts/en.md"),
            },
            "source_x_post_sha256": sha256(source_run / "xpost/ja.txt"),
            "media_sha256": {
                "headline": sha256(canonical / "headline-image.png"),
                "body_diagram": sha256(canonical / "body-diagram.png"),
            },
            "protected_live_ids": live_ids,
            "targets": targets,
        }
        receipt_path = canonical / "gates/current-run-import.json"
        _atomic_json(receipt_path, receipt)
    return {
        "status": "IMPORTED",
        "run_id": run_id,
        "run_dir": str(canonical),
        "state_path": str(state_path),
        "ledger_path": str(ledger_path),
        "receipt_path": str(receipt_path),
        "protected_live_ids": live_ids,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--writer-database", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--state-root", required=True, type=Path)
    parser.add_argument("--headline-source", required=True, type=Path)
    parser.add_argument("--body-diagram-source", required=True, type=Path)
    parser.add_argument("--zenn-slug", required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            import_run(
                args.writer_database,
                args.run_id,
                args.state_root,
                args.headline_source,
                args.body_diagram_source,
                zenn_slug=args.zenn_slug,
            ),
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (InvariantError, OSError, sqlite3.Error) as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        raise SystemExit(2)
