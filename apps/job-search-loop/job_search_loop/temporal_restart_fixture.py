"""Durable effect ledger used by the pinned Temporal restart fixture."""

from __future__ import annotations

import sqlite3
from pathlib import Path


def record_activity_effect(database_path: str | Path, effect_key: str) -> bool:
    """Record an activity attempt and apply its external effect at most once."""
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS activity_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                effect_key TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS activity_effects (
                effect_key TEXT PRIMARY KEY
            )
            """
        )
        connection.execute(
            "INSERT INTO activity_attempts (effect_key) VALUES (?)", (effect_key,)
        )
        cursor = connection.execute(
            "INSERT OR IGNORE INTO activity_effects (effect_key) VALUES (?)",
            (effect_key,),
        )
        connection.commit()
        return cursor.rowcount == 1


def effect_counts(database_path: str | Path, effect_key: str) -> tuple[int, int]:
    """Return (durable effects, attempts) for one idempotency key."""
    with sqlite3.connect(database_path) as connection:
        effects = connection.execute(
            "SELECT COUNT(*) FROM activity_effects WHERE effect_key = ?", (effect_key,)
        ).fetchone()[0]
        attempts = connection.execute(
            "SELECT COUNT(*) FROM activity_attempts WHERE effect_key = ?", (effect_key,)
        ).fetchone()[0]
    return effects, attempts
