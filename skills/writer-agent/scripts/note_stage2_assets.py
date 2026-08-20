#!/usr/bin/env python3
"""Resolve note body diagrams from canonical publication media."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Callable


class NoteStage2AssetError(ValueError):
    """Canonical note body media is missing or contradictory."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_mermaid_images(
    manifest: dict,
    work_dir: Path,
    publication_state_path: str,
    render_remote: Callable[[str, Path], None],
) -> list[str]:
    """Return upload-ready paths; managed runs use hash-bound canonical assets."""

    mermaids = manifest.get("mermaids") or []
    if not isinstance(mermaids, list):
        raise NoteStage2AssetError("manifest mermaids must be a list")
    if not mermaids:
        return []

    if publication_state_path:
        state_path = Path(publication_state_path)
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
            run_dir = Path(state["run_dir"]).resolve()
            body_assets = state["media"]["body_assets"]
        except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise NoteStage2AssetError(
                "managed note staging requires readable canonical media state"
            ) from exc
        if not isinstance(body_assets, list) or len(body_assets) != len(mermaids):
            raise NoteStage2AssetError(
                "canonical body asset count must equal mermaid count"
            )
        resolved: list[str] = []
        for row in body_assets:
            try:
                path = Path(row["path"])
                expected = str(row["sha256"])
                candidate = path.resolve()
            except (KeyError, TypeError) as exc:
                raise NoteStage2AssetError(
                    "canonical body asset row is incomplete"
                ) from exc
            if (
                path.is_symlink()
                or not candidate.is_file()
                or not candidate.is_relative_to(run_dir)
                or _sha256(candidate) != expected
            ):
                raise NoteStage2AssetError(
                    "canonical body asset path or hash mismatch"
                )
            resolved.append(str(candidate))
        return resolved

    work_dir.mkdir(parents=True, exist_ok=True)
    rendered: list[str] = []
    for index, source in enumerate(mermaids, 1):
        path = work_dir / f"fig{index}.png"
        render_remote(str(source), path)
        if not path.is_file() or path.stat().st_size == 0:
            raise NoteStage2AssetError("remote mermaid render produced no image")
        rendered.append(str(path))
    return rendered
