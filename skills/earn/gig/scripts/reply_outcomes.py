#!/usr/bin/env python3
"""Say which replies led to a purchase, and which are still waiting.

Measured 2026-08-06: replied threads and purchased projects share no ids at all. A reply
goes to DM thread 93000005; when that buyer pays, the work lives under talkroom 90000004.
Comparing the two sets directly reports zero conversions forever, which is exactly what it
did -- 25 replies, 8 purchases, zero overlap.

The bridge is already on disk. A purchased project keeps the DM thread it grew out of, at
projects/<project>/source/dm/thread-<DM_ID>-*.json, so the id that changed at purchase can
be walked backwards.

Pure functions. Reading only; the transcript ledger is append-only and is never rewritten.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any


DM_THREAD_FILENAME = re.compile(r"^thread-(\d+)")


def won_dm_thread_ids(projects_root: Path | str) -> set[str]:
    """DM threads that became paid work.

    A project with no source/dm directory contributed nothing: application-side jobs
    (91000002) are real conversions, but no reply can take credit for them, and crediting
    one would corrupt the dataset this exists to build.
    """
    root = Path(projects_root).expanduser()
    identifiers: set[str] = set()
    try:
        projects = list(root.iterdir())
    except OSError:
        return identifiers
    for project in projects:
        dm_dir = project / "source" / "dm"
        try:
            entries = list(dm_dir.iterdir())
        except OSError:
            continue
        for entry in entries:
            matched = DM_THREAD_FILENAME.match(entry.name)
            if matched:
                identifiers.add(matched.group(1))
    return identifiers


def label_for(thread_id: Any, won_ids: Any) -> str:
    """"won" if this conversation became paid work, otherwise "silent".

    Deliberately not "lost". A buyer who has not answered has not refused, and the wrong
    word here would teach the wrong lesson to whatever reads the dataset later.
    """
    identifiers = won_ids if isinstance(won_ids, (set, frozenset)) else set(won_ids or [])
    return "won" if str(thread_id) in {str(value) for value in identifiers} else "silent"


def label_transcripts(transcripts: Any, won_ids: Any) -> list[dict[str, Any]]:
    """Join labels onto transcript rows without touching the originals.

    The ledger is append-only; rewriting past rows to record an outcome would be editing
    history, and the outcome can change again (a silent buyer may still purchase).
    """
    rows = transcripts if isinstance(transcripts, (list, tuple)) else []
    labelled: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        labelled.append({**row, "outcome": label_for(row.get("talkroom_id"), won_ids)})
    return labelled
