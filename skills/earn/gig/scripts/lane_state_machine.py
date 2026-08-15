#!/usr/bin/env python3
"""Durable at-most-once event/action envelope shared by the four Gig lanes."""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path
from typing import Any, Callable


# "not_run" means the pass never invoked this lane. It is deliberately distinct from
# "verified_noop" ("we drove the lane and it legitimately owed no side effect"): writing
# the latter for a lane that never started is what let a 4.5 day outage report itself as
# 47 healthy verifications every morning. Every lane accepts it, since any lane can be
# skipped by a pass.
_NOT_RUN = "not_run"

LANE_ACTIONS = {
    "listing": {"draft", "publish", "update", "verified_noop", _NOT_RUN},
    "application": {"apply", "verified_noop", _NOT_RUN},
    "reply": {"reply", "verified_noop", _NOT_RUN},
    "delivery": {
        "build",
        "progress",
        "formal_delivery",
        "revision",
        "acceptance",
        "payout",
        "verified_noop",
        _NOT_RUN,
    },
}


class PreEffectCrash(RuntimeError):
    """The worker stopped before the durable side-effect fence."""


class ModelRefusal(RuntimeError):
    """The model produced no authorized intent before any side effect."""


class UnknownOutcome(RuntimeError):
    """The side effect may have happened, so only reconciliation is safe."""


SCHEMA = """
CREATE TABLE IF NOT EXISTS lane_actions (
    action_id INTEGER PRIMARY KEY AUTOINCREMENT,
    lane TEXT NOT NULL,
    event_key TEXT NOT NULL UNIQUE,
    entity_key TEXT NOT NULL,
    action_kind TEXT NOT NULL,
    state TEXT NOT NULL,
    revision INTEGER NOT NULL DEFAULT 1,
    owner TEXT,
    fencing_token INTEGER NOT NULL DEFAULT 0,
    lease_until INTEGER NOT NULL DEFAULT 0,
    intent_hash TEXT,
    effect_started_at INTEGER,
    effect_attempt_count INTEGER NOT NULL DEFAULT 0,
    side_effect_count INTEGER NOT NULL DEFAULT 0,
    blind_retry_count INTEGER NOT NULL DEFAULT 0,
    evidence_hash TEXT,
    last_error TEXT,
    observed_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);
"""


def _required_text(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")
    return value.strip()


def _timestamp(name: str, value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


class LaneStateMachine:
    def __init__(self, database: Path | str):
        self.database = Path(database)
        self.database.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.database,
            timeout=5,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=5000")
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    @staticmethod
    def _row(row: sqlite3.Row) -> dict[str, Any]:
        return dict(row)

    def get_action(self, action_id: int) -> dict[str, Any]:
        if isinstance(action_id, bool) or not isinstance(action_id, int) or action_id <= 0:
            raise ValueError("action_id must be a positive integer")
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM lane_actions WHERE action_id=?",
                (action_id,),
            ).fetchone()
        if row is None:
            raise KeyError(action_id)
        return self._row(row)

    def list_actions(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM lane_actions ORDER BY action_id"
            ).fetchall()
        return [self._row(row) for row in rows]

    def observe(
        self,
        *,
        lane: str,
        event_key: str,
        entity_key: str,
        action_kind: str,
        observed_at: int,
    ) -> dict[str, Any]:
        lane = _required_text("lane", lane)
        action_kind = _required_text("action_kind", action_kind)
        event_key = _required_text("event_key", event_key)
        entity_key = _required_text("entity_key", entity_key)
        observed_at = _timestamp("observed_at", observed_at)
        if lane not in LANE_ACTIONS or action_kind not in LANE_ACTIONS[lane]:
            raise ValueError(f"invalid lane action: {lane}/{action_kind}")
        # not_run is terminal like verified_noop: there is no side effect coming, so
        # leaving it "pending" would park a row that nothing will ever settle and make
        # the lane look mid-flight forever. It records the state it is in as its own
        # kind, so the report can count it as silence rather than as verification.
        if action_kind in ("verified_noop", _NOT_RUN):
            initial_state = action_kind
        else:
            initial_state = "pending"

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT * FROM lane_actions WHERE event_key=?",
                (event_key,),
            ).fetchone()
            if existing is not None:
                if (
                    existing["lane"] != lane
                    or existing["entity_key"] != entity_key
                    or existing["action_kind"] != action_kind
                ):
                    connection.rollback()
                    raise ValueError("event_key identity mismatch")
                connection.commit()
                return self._row(existing)
            cursor = connection.execute(
                """INSERT INTO lane_actions(
                       lane,event_key,entity_key,action_kind,state,observed_at,updated_at
                   ) VALUES(?,?,?,?,?,?,?)""",
                (
                    lane,
                    event_key,
                    entity_key,
                    action_kind,
                    initial_state,
                    observed_at,
                    observed_at,
                ),
            )
            row = connection.execute(
                "SELECT * FROM lane_actions WHERE action_id=?",
                (cursor.lastrowid,),
            ).fetchone()
            connection.commit()
        return self._row(row)

    def release_retry(self, action_id: int, *, now: int) -> dict[str, Any]:
        now = _timestamp("now", now)
        if isinstance(action_id, bool) or not isinstance(action_id, int) or action_id <= 0:
            raise ValueError("action_id must be a positive integer")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            changed = connection.execute(
                """UPDATE lane_actions
                   SET state='pending',owner=NULL,lease_until=0,updated_at=?
                   WHERE action_id=? AND state='retry_wait'""",
                (now, action_id),
            ).rowcount
            connection.commit()
        if changed != 1:
            raise RuntimeError("action is not retry_wait")
        return self.get_action(action_id)

    def claim(
        self,
        action_id: int,
        *,
        owner: str,
        now: int,
        lease_seconds: int = 300,
    ) -> dict[str, Any]:
        owner = _required_text("owner", owner)
        now = _timestamp("now", now)
        if isinstance(action_id, bool) or not isinstance(action_id, int) or action_id <= 0:
            raise ValueError("action_id must be a positive integer")
        if (
            isinstance(lease_seconds, bool)
            or not isinstance(lease_seconds, int)
            or lease_seconds <= 0
        ):
            raise ValueError("lease_seconds must be a positive integer")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM lane_actions WHERE action_id=?",
                (action_id,),
            ).fetchone()
            if row is None:
                connection.rollback()
                raise KeyError(action_id)
            reclaim_expired = (
                row["state"] == "claimed"
                and row["effect_started_at"] is None
                and int(row["lease_until"]) < now
            )
            if row["state"] != "pending" and not reclaim_expired:
                connection.commit()
                return self._row(row)
            token = int(row["fencing_token"]) + 1
            connection.execute(
                """UPDATE lane_actions
                   SET state='claimed',owner=?,fencing_token=?,lease_until=?,
                       last_error=NULL,updated_at=?
                   WHERE action_id=? AND state=?
                     AND effect_started_at IS NULL AND lease_until=?""",
                (
                    owner,
                    token,
                    now + lease_seconds,
                    now,
                    action_id,
                    row["state"],
                    row["lease_until"],
                ),
            )
            claimed = connection.execute(
                "SELECT * FROM lane_actions WHERE action_id=?",
                (action_id,),
            ).fetchone()
            connection.commit()
        return self._row(claimed)

    def _record_pre_effect_failure(
        self,
        action: dict[str, Any],
        *,
        reason: str,
        now: int,
    ) -> dict[str, Any]:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            changed = connection.execute(
                """UPDATE lane_actions
                   SET state='retry_wait',revision=revision+1,owner=NULL,
                       lease_until=0,intent_hash=NULL,last_error=?,updated_at=?
                   WHERE action_id=? AND state='claimed' AND owner=?
                     AND fencing_token=?""",
                (
                    reason,
                    now,
                    action["action_id"],
                    action["owner"],
                    action["fencing_token"],
                ),
            ).rowcount
            connection.commit()
        if changed != 1:
            raise RuntimeError("stale pre-effect failure")
        return self.get_action(action["action_id"])

    def fence_side_effect(
        self,
        action: dict[str, Any],
        *,
        intent: str,
        now: int,
    ) -> dict[str, Any]:
        intent = _required_text("intent", intent)
        intent_hash = hashlib.sha256(intent.encode("utf-8")).hexdigest()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            changed = connection.execute(
                """UPDATE lane_actions
                   SET state='reconcile_pending',intent_hash=?,
                       effect_started_at=?,
                       effect_attempt_count=effect_attempt_count+1,
                       last_error=NULL,updated_at=?
                   WHERE action_id=? AND state='claimed' AND owner=?
                     AND fencing_token=? AND effect_started_at IS NULL
                     AND lease_until>=?""",
                (
                    intent_hash,
                    now,
                    now,
                    action["action_id"],
                    action["owner"],
                    action["fencing_token"],
                    now,
                ),
            ).rowcount
            connection.commit()
        if changed != 1:
            raise RuntimeError("side-effect fence rejected")
        return self.get_action(action["action_id"])

    def _record_unknown(
        self,
        action_id: int,
        *,
        reason: str,
        now: int,
    ) -> dict[str, Any]:
        with self._connect() as connection:
            connection.execute(
                """UPDATE lane_actions
                   SET last_error=?,owner=NULL,lease_until=0,updated_at=?
                   WHERE action_id=? AND state='reconcile_pending'""",
                (reason, now, action_id),
            )
        return self.get_action(action_id)

    def _reconcile(
        self,
        action: dict[str, Any],
        *,
        verify: Callable[[dict[str, Any]], Any],
        now: int,
    ) -> dict[str, Any]:
        evidence = verify(action)
        if not isinstance(evidence, dict):
            return self.get_action(action["action_id"])
        evidence_hash = evidence.get("evidence_hash")
        if not isinstance(evidence_hash, str) or not evidence_hash.strip():
            return self.get_action(action["action_id"])
        if evidence.get("authoritative_absent") is True:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                changed = connection.execute(
                    """UPDATE lane_actions
                       SET state='pending',revision=revision+1,owner=NULL,
                           lease_until=0,intent_hash=NULL,effect_started_at=NULL,
                           evidence_hash=?,last_error='authoritative_absence',
                           updated_at=?
                       WHERE action_id=? AND state='reconcile_pending'
                         AND intent_hash=? AND side_effect_count=0""",
                    (
                        evidence_hash.strip(),
                        now,
                        action["action_id"],
                        action["intent_hash"],
                    ),
                ).rowcount
                connection.commit()
            if changed != 1:
                raise RuntimeError("authoritative absence fence rejected")
            return self.get_action(action["action_id"])
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            changed = connection.execute(
                """UPDATE lane_actions
                   SET state='verified',side_effect_count=1,evidence_hash=?,owner=NULL,
                       lease_until=0,last_error=NULL,updated_at=?
                   WHERE action_id=? AND state='reconcile_pending'
                     AND intent_hash=? AND side_effect_count=0""",
                (
                    evidence_hash.strip(),
                    now,
                    action["action_id"],
                    action["intent_hash"],
                ),
            ).rowcount
            connection.commit()
        if changed != 1:
            raise RuntimeError("reconciliation fence rejected")
        return self.get_action(action["action_id"])

    def run_once(
        self,
        *,
        action_id: int,
        owner: str,
        now: int,
        compose: Callable[[dict[str, Any]], str],
        execute: Callable[[dict[str, Any], str], Any],
        verify: Callable[[dict[str, Any]], Any],
        lease_seconds: int = 300,
    ) -> dict[str, Any]:
        now = _timestamp("now", now)
        action = self.get_action(action_id)
        if action["state"] in {"verified", "verified_noop", "retry_wait", _NOT_RUN}:
            return action
        if action["state"] == "reconcile_pending":
            return self._reconcile(action, verify=verify, now=now)

        action = self.claim(
            action_id,
            owner=owner,
            now=now,
            lease_seconds=lease_seconds,
        )
        if action["state"] != "claimed" or action["owner"] != owner:
            return action
        try:
            intent = compose(action)
        except (PreEffectCrash, ModelRefusal) as exc:
            return self._record_pre_effect_failure(
                action,
                reason=str(exc) or type(exc).__name__,
                now=now,
            )

        fenced = self.fence_side_effect(action, intent=intent, now=now)
        try:
            execute(fenced, intent)
        except UnknownOutcome as exc:
            return self._record_unknown(
                action_id,
                reason=str(exc) or type(exc).__name__,
                now=now,
            )
        except Exception as exc:  # execution began; an arbitrary failure is unknown
            return self._record_unknown(
                action_id,
                reason=type(exc).__name__,
                now=now,
            )
        return self._reconcile(
            self.get_action(action_id),
            verify=verify,
            now=now,
        )
