"""SplitDataLoader for the writing-craft SkillOpt env.

Items come from build_dataset.py's split files (real writing-corpus rows,
each with a cached, framing-stripped `subject` -- see build_dataset.py's
module docstring for why the real title is never the rollout prompt seed).
`_normalize` maps that split-file shape to the item shape rollout/adapter
expect; nothing here calls a model.
"""
from __future__ import annotations

import json
from pathlib import Path

from skillopt.datasets.base import SplitDataLoader


def _normalize(raw: dict, fallback_split: str | None = None) -> dict:
    """One split-file row -> one task item.

    `subject` (build_dataset.py's derived, framing-stripped line) is what
    the rollout hands the target model as the writing prompt's seed.
    `reference_title` is the REAL title -- kept on the item for the
    scorer's own-row-exclusion check and for humans reading the rollout
    log, and it must never be placed in the text sent to the target
    model (see writing/rollout.py). task_type is `lang` so per-language
    slices are visible to get_task_types().

    `split` (T15 wall-clock follow-up): "train"|"val"|"test", the signal
    writing/rollout.py uses to pick TRAIN_OPPONENTS vs GATE_OPPONENTS.
    Prefers the value build_dataset.py already stamped onto the row;
    falls back to `fallback_split` (the directory name the caller loaded
    this row from) for split files written before that field existed, so
    an old file does not silently lose the distinction."""
    return {
        "id": str(raw["id"]),
        "subject": raw["subject"],
        "reference_title": raw["title"],
        "lang": raw.get("lang", "en"),
        "metric_primary": raw.get("metric_primary", 0),
        "task_type": raw.get("lang", "en"),
        "split": raw.get("split") or fallback_split,
    }


class WritingDataLoader(SplitDataLoader):
    """Load title-writing corpus rows from a JSON file inside each split dir."""

    def load_split_items(self, split_path: str) -> list:
        json_files = sorted(Path(split_path).glob("*.json"))
        if not json_files:
            raise FileNotFoundError(f"No .json file found in {split_path}")
        with json_files[0].open(encoding="utf-8") as f:
            raw_items = json.load(f)
        fallback_split = Path(split_path).name
        return [_normalize(item, fallback_split) for item in raw_items]
