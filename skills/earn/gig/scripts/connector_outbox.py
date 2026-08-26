#!/usr/bin/env python3
"""Pure SQLite outbox for Coconala reply intents.

This module does not drive a browser or call a model.  It persists only event
identity, immutable outgoing hashes, leases, state, and bounded verification
facts.  Every write transaction begins with ``BEGIN IMMEDIATE`` so concurrent
processes observe one writer-serialized decision.
"""

from __future__ import annotations

import hashlib
import fcntl
import json
import os
import re
import sqlite3
import unicodedata
from contextlib import closing, contextmanager
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlsplit


DEFAULT_MANIFEST = Path(__file__).resolve().parents[1] / "config" / "connectors" / "coconala.json"


class OutboxError(RuntimeError):
    pass


class ConnectorDisabled(OutboxError):
    pass


class ConnectorBusy(OutboxError):
    pass


class StaleFence(OutboxError):
    pass


class InvalidTransition(OutboxError):
    pass


class ImmutableIntent(OutboxError):
    pass


class ConsistencyWindowOpen(OutboxError):
    pass


class ExecutorStillActive(OutboxError):
    pass


def normalize_outgoing_body(value: str) -> str:
    """Return the canonical text used for a v1 Coconala outgoing hash."""
    if type(value) is not str:
        raise TypeError("body must be a string")
    normalized = unicodedata.normalize("NFC", value).replace("\r\n", "\n")
    normalized = re.sub(r"[^\S\r\n]+", " ", normalized)
    return normalized.strip()


def outgoing_sha256(value: str) -> str:
    return hashlib.sha256(normalize_outgoing_body(value).encode("utf-8")).hexdigest()


_EVENT_COMPONENT = r"[A-Za-z0-9._-]{1,128}"
_MESSAGE_EVENT = re.compile(
    rf"coconala:message:v1:(?P<thread>{_EVENT_COMPONENT}):(?P<message>{_EVENT_COMPONENT})"
)
_INBOX_EVENT = re.compile(
    rf"coconala:inbox:v1:(?P<thread>{_EVENT_COMPONENT}):"
    r"sha256_v1:(?P<identity>[0-9a-f]{64})"
)
_FALLBACK_EVENT = re.compile(
    rf"coconala:fallback:v1:(?P<thread>{_EVENT_COMPONENT}):"
    r"(?P<sent_at>0|[1-9][0-9]*):(?P<ordinal>0|[1-9][0-9]*):sha256_v1:(?P<digest>[0-9a-f]{64})"
)
_ESTIMATE_EVENT = re.compile(
    rf"coconala:estimate:v1:(?P<thread>{_EVENT_COMPONENT}):(?P<request>{_EVENT_COMPONENT})"
)
_INITIAL_CONTACT_EVENT = re.compile(
    rf"coconala:initial-contact:v1:(?P<order>{_EVENT_COMPONENT})"
)


def _event_component(name: str, value: str) -> str:
    if type(value) is not str:
        raise TypeError(f"{name} must be a string")
    text = value.strip()
    if not re.fullmatch(_EVENT_COMPONENT, text):
        raise ValueError(f"invalid {name}")
    return text


def coconala_message_event_key(thread_id: str, message_id: str) -> str:
    """Build a typed event identity from a platform message ID."""
    thread = _event_component("thread_id", thread_id)
    message = _event_component("message_id", message_id)
    return f"coconala:message:v1:{thread}:{message}"


def coconala_inbox_event_key(thread_id: str, identity_sha256: str) -> str:
    """Build a typed, thread-bound identity for one observed inbox card."""
    thread = _event_component("thread_id", thread_id)
    if type(identity_sha256) is not str or not re.fullmatch(
        r"[0-9a-f]{64}", identity_sha256
    ):
        raise ValueError("invalid identity_sha256")
    return f"coconala:inbox:v1:{thread}:sha256_v1:{identity_sha256}"


def coconala_fallback_event_key(
    *, thread_id: str, buyer_sent_at: int, ordinal: int, raw_body: str
) -> str:
    """Build a fallback identity while retaining only a normalized body hash."""
    thread = _event_component("thread_id", thread_id)
    if type(buyer_sent_at) is not int or buyer_sent_at < 0:
        raise ValueError("invalid buyer_sent_at")
    if type(ordinal) is not int or ordinal < 0:
        raise ValueError("invalid ordinal")
    normalized_body = normalize_outgoing_body(raw_body)
    if not normalized_body:
        raise ValueError("fallback body normalizes to empty")
    digest = hashlib.sha256(normalized_body.encode("utf-8")).hexdigest()
    return (
        f"coconala:fallback:v1:{thread}:{buyer_sent_at}:{ordinal}:"
        f"sha256_v1:{digest}"
    )


def coconala_estimate_event_key(thread_id: str, buyer_request_identity: str) -> str:
    """Build a typed, thread-bound identity for one requested estimate."""
    thread = _event_component("thread_id", thread_id)
    request = _event_component("buyer_request_identity", buyer_request_identity)
    return f"coconala:estimate:v1:{thread}:{request}"


def coconala_initial_contact_event_key(order_id: str) -> str:
    """Build an order-scoped initial seller-contact identity."""
    order = _event_component("order_id", order_id)
    return f"coconala:initial-contact:v1:{order}"


def validate_coconala_event_key(event_key: str, thread_id: str) -> str:
    """Validate supported event grammar and its binding to the target thread."""
    if not isinstance(event_key, str) or len(event_key) > 500:
        raise ValueError("invalid event_key")
    expected_thread = _event_component("thread_id", thread_id)
    for pattern in (_MESSAGE_EVENT, _INBOX_EVENT, _FALLBACK_EVENT, _ESTIMATE_EVENT):
        match = pattern.fullmatch(event_key)
        if match is not None:
            if match.group("thread") != expected_thread:
                raise ValueError("event_key does not identify thread_id")
            return event_key
    if _INITIAL_CONTACT_EVENT.fullmatch(event_key) is not None:
        return event_key
    raise ValueError("invalid event_key")


SERVER_REJECTION_CODES = frozenset({
    "submit_rejected_external_contact",
    "submit_rejected_message_validation",
    "submit_rejected_sending_unavailable",
    "submit_rejected_other_validation",
    "submit_rejected_no_validation",
})


# --- C1b blocked-revive contract -------------------------------------------
# A ``blocked`` action used to leave that state ONLY when a NEW inbound event
# arrived on the same thread (``enqueue``).  A buyer who never writes again left
# the action dead forever (live: 6 threads blocked since 2026-07-22).  The revive
# path below is time-driven instead of event-driven: exponential backoff keyed off
# ``updated_at``, a per-rejection-code attempt cap, and a dead-letter terminus.
#
# Floor = 1800s: the reply queue calls a thread SLA-breached at origin+30min, so
# retrying faster than that window cannot recover the SLA, it only burns clicks.
# Ceiling = 86400s: the pass wakes hourly, so a daily floor still re-touches every
# living conversation, and a thread silent for a day is a cold lead, not an outage.
BLOCKED_REVIVE_BASE_SECONDS = 1800
BLOCKED_REVIVE_MAX_SECONDS = 86400
# Attempt caps are per rejection_code because the codes mean different things:
# a platform-side send outage is transient (retry pays), a content rejection is
# not (only a rewrite pays, and two rewrites are already generous).
BLOCKED_REVIVE_ATTEMPT_CAPS: dict[str, int] = {
    "submit_rejected_sending_unavailable": 8,
    "submit_rejected_external_contact": 2,
    "submit_rejected_message_validation": 2,
    "submit_rejected_other_validation": 3,
    "submit_rejected_no_validation": 3,
}
# rejection_code NULL = the click failed without the platform saying why.
BLOCKED_REVIVE_DEFAULT_ATTEMPT_CAP = 5
# Anti-burn invariant.  Every superseded revision is one burned browser click and
# one burned composer call.  Live measurement: 50 of 51 delivered replies took 1
# revision and the 51st took 2, while the runaway thread reached 36 revisions with
# zero verified deliveries.  12 = 6x the observed healthy maximum: high enough that
# no honest conversation trips it, low enough that a runaway dies in hours.
MAX_REVISIONS_PER_ACTION = 12
# How long a just-revived action yields the single browser tab to fresh inquiries.
# Bounds the starvation both ways: fresh work always goes first, but a resurrection
# waits at most this long even under a continuous stream of new buyers.
REVIVE_DEPRIORITY_SECONDS = 86400


def blocked_revive_delay_seconds(attempts: int) -> int:
    """Return the exponential backoff a blocked action waits before attempt N+1."""
    if type(attempts) is not int or isinstance(attempts, bool) or attempts < 0:
        raise ValueError("attempts must be a non-negative integer")
    if attempts >= 64:
        return BLOCKED_REVIVE_MAX_SECONDS
    return min(BLOCKED_REVIVE_BASE_SECONDS << attempts, BLOCKED_REVIVE_MAX_SECONDS)


def blocked_revive_attempt_cap(rejection_code: str | None) -> int:
    """Return the bounded number of automatic revives allowed for one cause."""
    if rejection_code is None:
        return BLOCKED_REVIVE_DEFAULT_ATTEMPT_CAP
    return BLOCKED_REVIVE_ATTEMPT_CAPS.get(
        str(rejection_code), BLOCKED_REVIVE_DEFAULT_ATTEMPT_CAP
    )


SCHEMA = """
CREATE TABLE IF NOT EXISTS connector_actions (
    action_id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,
    thread_id TEXT NOT NULL,
    thread_url TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('pending','claimed','intent_ready','reconcile_pending','blocked','replied')),
    revision INTEGER NOT NULL DEFAULT 1 CHECK (revision >= 1),
    owner TEXT,
    fencing_token INTEGER NOT NULL DEFAULT 0,
    lease_until INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    verified_thread_url TEXT,
    verified_outgoing_hash TEXT,
    seller_sent_at INTEGER,
    last_sender TEXT,
    revived_at INTEGER,
    dlq_at INTEGER
);
-- connector_one_active_thread / connector_one_blocked_thread are NOT declared
-- here. Their predicate references dlq_at, and `CREATE UNIQUE INDEX IF NOT
-- EXISTS` only short-circuits when the index already exists -- when it does not,
-- SQLite resolves the predicate and raises `no such column: dlq_at` against a
-- database whose ALTER has not run yet. That raise would happen inside
-- __init__, i.e. OUTSIDE the caller's best-effort guard, and would isolate the
-- reply lane. The migration block in _initialize() is the SINGLE source of truth
-- for both indexes: it runs unconditionally, after the columns exist, for fresh
-- and pre-existing databases alike, inside the same transaction.

CREATE TABLE IF NOT EXISTS connector_events (
    event_key TEXT PRIMARY KEY,
    action_id INTEGER NOT NULL REFERENCES connector_actions(action_id),
    platform TEXT NOT NULL,
    thread_id TEXT NOT NULL,
    observed_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS connector_intents (
    action_id INTEGER NOT NULL REFERENCES connector_actions(action_id),
    revision INTEGER NOT NULL CHECK (revision >= 1),
    outgoing_hash TEXT NOT NULL CHECK (length(outgoing_hash) = 64),
    -- Only estimate intents may retain their canonical structured terms.  Normal
    -- message intents remain hash-only so customer prose never enters durable
    -- receipts or normal-lane projections.
    outgoing_body TEXT,
    owner_id TEXT NOT NULL,
    fencing_token INTEGER NOT NULL CHECK (fencing_token > 0),
    state TEXT NOT NULL CHECK (state IN ('prepared','reconcile_pending','verified','superseded')),
    created_at INTEGER NOT NULL,
    origin_at INTEGER,
    click_started_at INTEGER,
    executor_quiesced_at INTEGER,
    executor_quiesced_by TEXT CHECK (executor_quiesced_by IN ('owner','supervisor')),
    rejection_code TEXT,
    superseded_at INTEGER,
    PRIMARY KEY(action_id, revision)
);

CREATE TABLE IF NOT EXISTS provider_effect_intents (
    effect_key TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    account_key TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    action TEXT NOT NULL,
    payload_hash TEXT NOT NULL CHECK (length(payload_hash) = 64),
    authorization_hash TEXT NOT NULL CHECK (length(authorization_hash) = 64),
    state TEXT NOT NULL CHECK (state IN ('prepared','reconcile_pending')),
    reconciliation_state TEXT NOT NULL DEFAULT 'not_started'
        CHECK (reconciliation_state IN ('not_started','reconcile_unknown','verified')),
    connects_pre INTEGER,
    connects_pre_hash TEXT,
    payload_body TEXT,
    proposal_id TEXT,
    connects_post INTEGER,
    readback_hash TEXT,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    UNIQUE(provider, account_key, resource_id, action, payload_hash)
);

CREATE TABLE IF NOT EXISTS provider_capacity_reservations (
    effect_key TEXT PRIMARY KEY REFERENCES provider_effect_intents(effect_key),
    provider TEXT NOT NULL,
    account_key TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    contract_id TEXT,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS connector_slots (
    platform TEXT PRIMARY KEY,
    action_id INTEGER,
    owner TEXT,
    fencing_token INTEGER NOT NULL DEFAULT 0,
    lease_until INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS connector_dlq (
    action_id INTEGER PRIMARY KEY REFERENCES connector_actions(action_id),
    thread_id TEXT NOT NULL,
    reason TEXT NOT NULL,
    unresolved_attempts INTEGER NOT NULL,
    moved_at INTEGER NOT NULL
);

-- E6b consecutive-failure bookkeeping.  The detector is a fresh process every
-- 300s, so an in-memory counter can never see "the same failure twice", which
-- means the streak has to be as durable as the queue it guards.  One row per
-- thread, because a streak is by definition consecutive: a second error class
-- replaces the first rather than accumulating beside it.
-- Never put a semicolon in a comment here: SCHEMA is executed by splitting the
-- whole string on the statement separator, so one inside a comment cuts the
-- next CREATE in half and every fresh database fails to open.
CREATE TABLE IF NOT EXISTS connector_failure_streaks (
    platform TEXT NOT NULL,
    thread_id TEXT NOT NULL,
    error_class TEXT NOT NULL,
    consecutive INTEGER NOT NULL CHECK (consecutive >= 1),
    action_id INTEGER,
    first_at INTEGER NOT NULL,
    last_at INTEGER NOT NULL,
    PRIMARY KEY(platform, thread_id)
);
"""


class ConnectorOutbox:
    """Deterministic Coconala event, intent, lease, and reconcile state."""

    def __init__(self, database: Path, manifest: Path = DEFAULT_MANIFEST):
        self.database = Path(database)
        self.manifest_path = Path(manifest)
        self.database.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()
        os.chmod(self.database, 0o600)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database, timeout=5, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    def _initialize(self) -> None:
        lock_path = self.database.with_name(f".{self.database.name}.init.lock")
        lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
        os.fchmod(lock_fd, 0o600)
        with os.fdopen(lock_fd, "r+") as lock_handle:
            fcntl.flock(lock_handle, fcntl.LOCK_EX)
            with closing(self._connect()) as connection:
                connection.execute("PRAGMA journal_mode = WAL")
                connection.execute("BEGIN IMMEDIATE")
                try:
                    for statement in SCHEMA.split(";"):
                        if statement.strip():
                            connection.execute(statement)
                    intent_columns = {
                        str(row[1])
                        for row in connection.execute("PRAGMA table_info(connector_intents)")
                    }
                    if "origin_at" not in intent_columns:
                        connection.execute(
                            "ALTER TABLE connector_intents ADD COLUMN origin_at INTEGER"
                        )
                    if "outgoing_body" not in intent_columns:
                        connection.execute(
                            "ALTER TABLE connector_intents ADD COLUMN outgoing_body TEXT"
                        )
                    if "rejection_code" not in intent_columns:
                        connection.execute(
                            "ALTER TABLE connector_intents ADD COLUMN rejection_code TEXT"
                        )
                    provider_columns = {
                        str(row[1])
                        for row in connection.execute("PRAGMA table_info(provider_effect_intents)")
                    }
                    for name, declaration in (
                        ("reconciliation_state", "TEXT NOT NULL DEFAULT 'not_started'"),
                        ("connects_pre", "INTEGER"),
                        ("connects_pre_hash", "TEXT"),
                        ("payload_body", "TEXT"),
                        ("proposal_id", "TEXT"),
                        ("connects_post", "INTEGER"),
                        ("readback_hash", "TEXT"),
                    ):
                        if name not in provider_columns:
                            connection.execute(
                                f"ALTER TABLE provider_effect_intents ADD COLUMN {name} {declaration}"
                            )
                    action_columns = {
                        str(row[1])
                        for row in connection.execute("PRAGMA table_info(connector_actions)")
                    }
                    if "reconcile_attempts" not in action_columns:
                        connection.execute(
                            "ALTER TABLE connector_actions"
                            " ADD COLUMN reconcile_attempts INTEGER NOT NULL DEFAULT 0"
                        )
                    if "revive_attempts" not in action_columns:
                        connection.execute(
                            "ALTER TABLE connector_actions ADD COLUMN revive_attempts"
                            " INTEGER NOT NULL DEFAULT 0 CHECK (revive_attempts >= 0)"
                        )
                    if "revived_at" not in action_columns:
                        # The revive's OWN clock. It is deliberately not
                        # ``updated_at``: see revive_blocked_actions().
                        connection.execute(
                            "ALTER TABLE connector_actions ADD COLUMN revived_at INTEGER"
                        )
                    if "dlq_at" not in action_columns:
                        # Denormalized ``connector_dlq`` membership.  A partial index
                        # predicate cannot reach another table, and the uniqueness
                        # invariants below MUST exclude quarantined rows, otherwise a
                        # dead letter permanently owns its thread's active/blocked slot.
                        connection.execute(
                            "ALTER TABLE connector_actions ADD COLUMN dlq_at INTEGER"
                        )
                    # Reconciler, NOT a one-shot backfill: it runs on EVERY open.
                    # The documented rollback is `git checkout` back to the previous
                    # branch, and the old code dead-letters into connector_dlq without
                    # knowing about dlq_at.  Rolling forward again must repair those
                    # rows, otherwise the quarantine silently re-occupies the thread's
                    # unique slot and the next buyer event raises IntegrityError
                    # forever.  Idempotent, and bounded by the size of connector_dlq.
                    connection.execute(
                        """UPDATE connector_actions
                           SET dlq_at=(SELECT d.moved_at FROM connector_dlq d
                                        WHERE d.action_id=connector_actions.action_id)
                           WHERE dlq_at IS NULL
                             AND action_id IN (SELECT action_id FROM connector_dlq)"""
                    )
                    dlq_columns = {
                        str(row[1])
                        for row in connection.execute("PRAGMA table_info(connector_dlq)")
                    }
                    if "attempts_kind" not in dlq_columns:
                        connection.execute(
                            "ALTER TABLE connector_dlq ADD COLUMN attempts_kind TEXT"
                        )
                        connection.execute(
                            "UPDATE connector_dlq SET attempts_kind='reconcile_attempts'"
                            " WHERE attempts_kind IS NULL"
                        )
                    if "closure" not in dlq_columns:
                        # ``dlq_at`` is mechanically "this row is closed and out of
                        # EVERY projection" -- twelve queries and both partial
                        # unique indexes already filter on it, so it is the only
                        # marker that cannot leak a closed action back into the
                        # lane through a query someone forgot to update.  E6b adds
                        # a second, non-error closure (nothing_to_say) that needs
                        # exactly that removal without claiming a fault, so the
                        # discriminator goes here rather than a parallel table.
                        connection.execute(
                            "ALTER TABLE connector_dlq ADD COLUMN closure TEXT"
                        )
                    connection.execute(
                        "UPDATE connector_dlq SET closure='dlq' WHERE closure IS NULL"
                    )
                    connection.execute(
                        """UPDATE connector_dlq
                           SET closure='nothing_to_say',
                               reason='nothing_to_say:officially_unrepliable:'
                                      || 'submit_rejected_sending_unavailable',
                               attempts_kind='nothing_to_say'
                           WHERE closure='dlq'
                             AND reason='revive_attempts_exhausted:'
                                        || 'submit_rejected_sending_unavailable'"""
                    )
                    # SINGLE source of truth for the thread-uniqueness invariants.
                    # Deliberately not in SCHEMA: the predicate needs dlq_at, which
                    # only exists after the ALTER above. Runs unconditionally so a
                    # fresh database gets them here too.
                    for index_name, predicate in (
                        (
                            "connector_one_active_thread",
                            "state IN ('pending','claimed','intent_ready','reconcile_pending')"
                            " AND dlq_at IS NULL",
                        ),
                        ("connector_one_blocked_thread", "state = 'blocked' AND dlq_at IS NULL"),
                    ):
                        existing = connection.execute(
                            "SELECT sql FROM sqlite_master WHERE type='index' AND name=?",
                            (index_name,),
                        ).fetchone()
                        if existing is not None and "dlq_at" in str(existing[0] or ""):
                            continue
                        # The new predicate is strictly narrower than the old one, so
                        # any data that satisfied the old index satisfies this one.
                        connection.execute(f"DROP INDEX IF EXISTS {index_name}")
                        connection.execute(
                            f"CREATE UNIQUE INDEX {index_name}"
                            f" ON connector_actions(platform, thread_id) WHERE {predicate}"
                        )
                    connection.execute(
                        """UPDATE connector_intents
                           SET origin_at=(SELECT created_at FROM connector_actions
                                          WHERE connector_actions.action_id=connector_intents.action_id)
                           WHERE origin_at IS NULL"""
                    )
                    connection.execute(
                        "INSERT OR IGNORE INTO connector_slots(platform, fencing_token, lease_until) VALUES('coconala', 0, 0)"
                    )
                    connection.commit()
                except BaseException:
                    connection.rollback()
                    raise

    @contextmanager
    def _write(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _manifest(self, *, require_enabled: bool = True) -> dict[str, Any]:
        try:
            value = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ConnectorDisabled("connector manifest unavailable") from error
        rate_limit = value.get("rate_limit") if isinstance(value, dict) else None
        allowed_scope = value.get("allowed_scope") if isinstance(value, dict) else None
        valid = (
            isinstance(value, dict)
            and value.get("connector") == "coconala"
            and value.get("authorization_source") == "user_confirmed"
            and value.get("policy_lookup_at_runtime") is False
            and value.get("terms_lookup_at_runtime") is False
            and value.get("reconciliation_mode") == "authoritative_dom_readback"
            and isinstance(allowed_scope, list)
            and "reply" in allowed_scope
            and isinstance(rate_limit, dict)
            and type(rate_limit.get("max_concurrent_browser_tabs")) is int
            and rate_limit.get("max_concurrent_browser_tabs") == 1
            and type(value.get("max_consistency_window_seconds")) is int
            and value["max_consistency_window_seconds"] > 0
        )
        if not valid:
            raise ConnectorDisabled("connector manifest contract invalid")
        if require_enabled and (value.get("enabled") is not True or value.get("revoked_at") is not None):
            raise ConnectorDisabled("connector disabled or revoked")
        return value

    @staticmethod
    def _dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
        return dict(row) if row is not None else None

    @staticmethod
    def _require_text(name: str, value: str) -> str:
        text = str(value or "").strip()
        if not text or len(text) > 1000:
            raise ValueError(f"invalid {name}")
        return text

    @staticmethod
    def _require_key(name: str, value: str) -> str:
        text = str(value or "").strip()
        if not re.fullmatch(r"[A-Za-z0-9._:/~-]{1,500}", text):
            raise ValueError(f"invalid {name}")
        return text

    @staticmethod
    def _require_timestamp(name: str, value: int) -> int:
        if type(value) is not int or value < 0:
            raise ValueError(f"invalid {name}")
        return value

    @staticmethod
    def _require_positive_integer(name: str, value: int) -> int:
        if type(value) is not int or value <= 0:
            raise ValueError(f"invalid {name}")
        return value

    @staticmethod
    def _require_monotonic(action: sqlite3.Row, timestamp: int) -> None:
        if timestamp < int(action["updated_at"]):
            raise InvalidTransition("lifecycle timestamp precedes the current action state")

    @staticmethod
    def _canonical_thread_url(value: str, expected_thread_id: str | None = None) -> str:
        # A4: job_matching/job_talkroom/<ULID> is the retainer-application thread
        # namespace. It was missing here, not excluded on purpose -- the whitelist
        # simply predates the applied-retainer tab, so every already-submitted
        # retainer application was unreachable by the durable outbox. The message
        # view lives at this path plus /talkroom; the canonical identity is the
        # path without it, so the thread_id check below still holds.
        parsed = urlsplit(str(value or ""))
        valid_path = re.fullmatch(
            r"/(?:mypage/direct_message|talkrooms|mypage/job_matching/job_talkroom)"
            r"/[A-Za-z0-9_-]+",
            parsed.path,
        )
        if parsed.scheme != "https" or parsed.hostname not in ("coconala.com", "www.coconala.com") or not valid_path:
            raise ValueError("invalid thread_url")
        if expected_thread_id is not None and parsed.path.rsplit("/", 1)[-1] != expected_thread_id:
            raise ValueError("thread_url does not identify thread_id")
        return f"https://coconala.com{parsed.path}"

    def _action(self, connection: sqlite3.Connection, action_id: int) -> sqlite3.Row:
        row = connection.execute(
            "SELECT * FROM connector_actions WHERE action_id = ?", (action_id,)
        ).fetchone()
        if row is None:
            raise InvalidTransition("unknown action")
        return row

    def _intent(self, connection: sqlite3.Connection, action_id: int, revision: int) -> sqlite3.Row | None:
        return connection.execute(
            "SELECT * FROM connector_intents WHERE action_id = ? AND revision = ?",
            (action_id, revision),
        ).fetchone()

    def _require_identity_fence(
        self,
        connection: sqlite3.Connection,
        action_id: int,
        owner: str,
        fencing_token: int,
        allowed_states: tuple[str, ...],
    ) -> sqlite3.Row:
        action = self._action(connection, action_id)
        slot = connection.execute(
            "SELECT * FROM connector_slots WHERE platform = ?", (action["platform"],)
        ).fetchone()
        valid = (
            action["owner"] == owner
            and action["fencing_token"] == fencing_token
            and slot is not None
            and slot["action_id"] == action_id
            and slot["owner"] == owner
            and slot["fencing_token"] == fencing_token
        )
        if not valid:
            raise StaleFence("owner or fencing token is stale")
        if action["state"] not in allowed_states:
            raise InvalidTransition(f"state {action['state']} is not allowed")
        return action

    def _require_fence(
        self,
        connection: sqlite3.Connection,
        action_id: int,
        owner: str,
        fencing_token: int,
        now: int,
        allowed_states: tuple[str, ...],
    ) -> sqlite3.Row:
        action = self._require_identity_fence(
            connection, action_id, owner, fencing_token, allowed_states
        )
        slot = connection.execute(
            "SELECT * FROM connector_slots WHERE platform = ?", (action["platform"],)
        ).fetchone()
        if action["lease_until"] <= now or slot["lease_until"] <= now:
            raise StaleFence("owner or fencing token is stale")
        return action

    @staticmethod
    def _release_slot(connection: sqlite3.Connection, action_id: int) -> None:
        connection.execute(
            "UPDATE connector_slots SET action_id = NULL, owner = NULL, lease_until = 0 WHERE action_id = ?",
            (action_id,),
        )

    def _reap_expired_slot(
        self, connection: sqlite3.Connection, slot: sqlite3.Row, *, now: int, reaper: str
    ) -> dict[str, Any]:
        """Reap a slot held past ``lease_until`` (Kleppmann lease + fencing token).

        Expiry is judged independent of caller identity: the slot is released and
        the fencing token is incremented so every write carrying the reaped token
        is rejected by the identity fences.  A pre-click action is requeued as a
        new revision; a click-started action stays in ``reconcile_pending`` for
        the evidence loop -- a reap never fabricates executor quiescence proof.
        The returned record MUST be appended via ``_append_reap_record`` after
        the surrounding transaction commits (silent reaps are forbidden).
        """
        held_action_id = int(slot["action_id"])
        action = self._action(connection, held_action_id)
        if now < int(action["updated_at"]):
            raise ConnectorBusy("expired slot reap timestamp precedes action state")
        if action["state"] in ("claimed", "intent_ready"):
            self._invalidate_pre_click_revision(connection, action, now)
            disposition = "requeued_pending"
        elif action["state"] == "reconcile_pending":
            connection.execute(
                "UPDATE connector_actions SET owner=NULL,lease_until=0,updated_at=? WHERE action_id=?",
                (now, held_action_id),
            )
            disposition = "kept_reconcile_pending"
        else:
            disposition = "slot_released"
        new_fencing_token = int(slot["fencing_token"]) + 1
        connection.execute(
            """UPDATE connector_slots
               SET action_id=NULL,owner=NULL,lease_until=0,fencing_token=?
               WHERE platform=?""",
            (new_fencing_token, slot["platform"]),
        )
        return {
            "reaped_at": now,
            "platform": slot["platform"],
            "action_id": held_action_id,
            "thread_id": action["thread_id"],
            "prior_state": action["state"],
            "disposition": disposition,
            "old_owner": slot["owner"],
            "old_fencing_token": int(slot["fencing_token"]),
            "new_fencing_token": new_fencing_token,
            "expired_lease_until": int(slot["lease_until"]),
            "reaper": reaper,
        }

    def _append_reap_record(self, record: dict[str, Any]) -> None:
        path = self.database.parent / "connector-outbox-reaps.jsonl"
        line = json.dumps(record, ensure_ascii=False, sort_keys=True)
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def _append_closure_record(self, record: dict[str, Any]) -> None:
        """Audit every A21 closure (already_delivered / dlq); silent closures are forbidden."""
        path = self.database.parent / "connector-outbox-closures.jsonl"
        line = json.dumps(record, ensure_ascii=False, sort_keys=True)
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def _append_revive_record(self, record: dict[str, Any]) -> None:
        """Audit every C1b revive decision that changed state; silent revives are forbidden."""
        path = self.database.parent / "connector-outbox-revives.jsonl"
        line = json.dumps(record, ensure_ascii=False, sort_keys=True)
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    @staticmethod
    def _dead_letter(
        connection: sqlite3.Connection,
        action: sqlite3.Row | dict[str, Any],
        *,
        reason: str,
        attempts: int,
        attempts_kind: str,
        now: int,
        closure: str = "dlq",
    ) -> dict[str, Any]:
        """Quarantine one action without fabricating a delivery outcome.

        Azure dead-letter replica shared by every quarantine path: the row keeps
        whatever state it already had (no evidence is invented), ``dlq_at`` takes
        it out of BOTH thread-uniqueness indexes so the quarantine never occupies
        the thread's active/blocked slot, and every projection excludes
        ``connector_dlq`` members so the lane stops touching it instead of
        blind-retrying it.  ``attempts_kind`` discriminates what
        ``unresolved_attempts`` counted (reconcile passes vs revisions vs revives).
        ``closure`` discriminates WHY the row left: ``dlq`` is a fault that needs
        repair, ``nothing_to_say`` is the correct finding that we already spoke
        last and no reply is owed.  Both must leave every projection; only the
        first is an incident, so ``dlq_actions()`` returns only the first.
        The returned record MUST be appended to the closure audit after commit.

        A quarantined action may keep a non-superseded intent, and that is
        deliberate: the intent is the evidence of what was attempted and how far
        it got.  Superseding it here would rewrite that evidence to make the row
        look tidy, which is exactly the kind of fabricated transition this state
        machine refuses.  Nothing reads it afterwards -- every projection filters
        on ``dlq_at``.
        """
        connection.execute(
            """INSERT OR IGNORE INTO connector_dlq
               (action_id,thread_id,reason,unresolved_attempts,moved_at,attempts_kind,closure)
               VALUES(?,?,?,?,?,?,?)""",
            (
                int(action["action_id"]),
                action["thread_id"],
                reason,
                int(attempts),
                now,
                attempts_kind,
                closure,
            ),
        )
        connection.execute(
            "UPDATE connector_actions SET dlq_at=? WHERE action_id=? AND dlq_at IS NULL",
            (now, int(action["action_id"])),
        )
        return {
            "closed_at": now,
            "closure": closure,
            "action_id": int(action["action_id"]),
            "thread_id": action["thread_id"],
            "revision": int(action["revision"]),
            "reason": reason,
            "unresolved_attempts": int(attempts),
            "attempts_kind": attempts_kind,
        }

    def _blocked_revive_candidates(
        self, connection: sqlite3.Connection, now: int
    ) -> list[dict[str, Any]]:
        """Decide, without writing, what each blocked action has earned by ``now``.

        The decision reads only durable state (``updated_at``, ``revive_attempts``,
        ``revision`` and the newest intent's ``rejection_code``), so the read-only
        plan and the write path can never disagree.
        """
        rows = connection.execute(
            """SELECT a.*,
                      (SELECT i.rejection_code FROM connector_intents i
                        WHERE i.action_id=a.action_id
                        ORDER BY i.revision DESC LIMIT 1) AS rejection_code,
                      (SELECT i.state FROM connector_intents i
                        WHERE i.action_id=a.action_id AND i.revision=a.revision
                        LIMIT 1) AS current_intent_state,
                      (SELECT COUNT(*) FROM connector_actions b
                        WHERE b.platform=a.platform AND b.thread_id=a.thread_id
                          AND b.state IN ('pending','claimed','intent_ready','reconcile_pending')
                          AND b.dlq_at IS NULL
                      ) AS active_siblings
                 FROM connector_actions a
                WHERE a.platform='coconala' AND a.state='blocked'
                  AND a.dlq_at IS NULL
                ORDER BY a.updated_at,a.action_id"""
        ).fetchall()
        candidates: list[dict[str, Any]] = []
        for row in rows:
            # Clamp: a corrupt negative counter must not raise and abort the batch.
            attempts = max(0, int(row["revive_attempts"]))
            rejection_code = row["rejection_code"]
            cap = blocked_revive_attempt_cap(rejection_code)
            blocked_at = int(row["updated_at"])
            next_attempt_at = blocked_at + blocked_revive_delay_seconds(attempts)
            current_intent_state = row["current_intent_state"]
            next_revision = int(row["revision"]) + (
                1 if current_intent_state is not None else 0
            )
            if now < blocked_at:
                # A clock that stepped backwards must produce "not yet", never a
                # permanent dead letter.
                decision, reason = "wait", "backoff_open"
            elif attempts >= cap:
                # The block itself is the durable authoritative-absence receipt for
                # the final attempt. Waiting through one more backoff cannot create a
                # new send opportunity; it only leaves terminal work looking active.
                if rejection_code == "submit_rejected_sending_unavailable":
                    decision = "nothing_to_say"
                    reason = f"officially_unrepliable:{rejection_code}"
                else:
                    decision = "dlq"
                    reason = f"revive_attempts_exhausted:{rejection_code or 'unknown'}"
            elif now < next_attempt_at:
                decision, reason = "wait", "backoff_open"
            elif int(row["active_siblings"]) > 0:
                # enqueue() parks a new buyer event on a blocked successor while the
                # predecessor is still in flight (live action 8). Promoting this row
                # would put two rows of one thread in connector_one_active_thread.
                # The predecessor's own reconcile releases the thread; until then the
                # conversation already has a live action, so nothing is lost.
                decision, reason = "skipped", "thread_has_active_action"
            elif next_revision > MAX_REVISIONS_PER_ACTION:
                decision, reason = "dlq", "revision_budget_exhausted"
            elif current_intent_state is not None and current_intent_state != "superseded":
                # The blocked row still owns a live intent: reviving it would
                # resurrect an un-superseded revision.  Left for the reconcile
                # loop; visible in the plan instead of raising and killing the batch.
                decision, reason = "skipped", "current_intent_not_superseded"
            else:
                decision, reason = "revive", "backoff_elapsed"
            candidates.append({
                "action_id": int(row["action_id"]),
                "thread_id": row["thread_id"],
                "revision": int(row["revision"]),
                "next_revision": next_revision,
                "revive_attempts": attempts,
                "attempt_cap": cap,
                "rejection_code": rejection_code,
                "blocked_at": blocked_at,
                "next_attempt_at": next_attempt_at,
                "active_siblings": int(row["active_siblings"]),
                "decision": decision,
                "reason": reason,
            })
        return candidates

    def blocked_revive_plan(self, *, now: int) -> list[dict[str, Any]]:
        """Return the revive decision for every blocked action without mutating anything."""
        now = self._require_timestamp("now", now)
        with closing(self._connect()) as connection:
            return self._blocked_revive_candidates(connection, now)

    def revive_blocked_actions(self, *, now: int) -> dict[str, Any]:
        """Return blocked actions to ``pending`` on backoff, or dead-letter them.

        C1b: without this the ``blocked`` -> ``pending`` edge exists only inside
        ``enqueue``, i.e. only when the buyer sends ANOTHER message.  A silent
        buyer therefore killed the conversation permanently.  Time, not the buyer,
        now drives recovery; the attempt cap and the revision budget keep that
        recovery from becoming the retry burn it is meant to end.

        A revoked or disabled connector returns ``status="connector_disabled"``
        without reviving anything: a revive CREATES new outbound work, so it must
        not resurrect conversations on a connector we are no longer allowed to
        touch.  It returns instead of raising because this runs inside the pass's
        enqueue step, where an exception would isolate the whole reply lane.
        """
        manifest = self._manifest(require_enabled=False)
        now = self._require_timestamp("now", now)
        revived: list[dict[str, Any]] = []
        dead_lettered: list[dict[str, Any]] = []
        closed_without_send: list[dict[str, Any]] = []
        closures: list[dict[str, Any]] = []
        if manifest.get("enabled") is not True or manifest.get("revoked_at") is not None:
            return {
                "revived": revived,
                "dead_lettered": dead_lettered,
                "status": "connector_disabled",
            }
        with closing(self._connect()) as reader:
            # Nothing due means nothing to write. Taking an exclusive transaction
            # anyway would stall the browser reply lane on a shared database every
            # pass AND every 5-minute detector run, for zero state change. This
            # read is advisory only: the authoritative decision is re-taken under
            # the write lock below.
            due = [
                candidate
                for candidate in self._blocked_revive_candidates(reader, now)
                if candidate["decision"] in ("revive", "dlq", "nothing_to_say")
            ]
        if not due:
            return {
                "revived": revived,
                "dead_lettered": dead_lettered,
                "status": "nothing_due",
            }
        with self._write() as connection:
            # Re-read inside BEGIN IMMEDIATE: the decision that is acted on is the
            # one taken under the write lock, so a concurrent pass cannot revive the
            # same row twice. (The UPDATE's `AND state='blocked'` is belt-and-braces
            # on top of that, not the exclusivity mechanism.)
            for candidate in self._blocked_revive_candidates(connection, now):
                decision = candidate["decision"]
                if decision == "revive":
                    # ``updated_at`` is NOT touched, on purpose. It is the evidence
                    # clock: _require_monotonic rejects an observation older than the
                    # last state change, which protects the machine from stale
                    # evidence rewriting newer state. A revive consumes no evidence
                    # and invalidates no observation -- nothing has been composed or
                    # sent for the new revision. Advancing it here made the 5-minute
                    # detector's revive invalidate the hourly pass's in-flight
                    # snapshot (different locks, concurrent processes), so the pass's
                    # own buyer event raised out of enqueue and isolated the lane.
                    # The revive's own clock lives in ``revived_at``.
                    connection.execute(
                        """UPDATE connector_actions
                           SET state='pending',revision=?,owner=NULL,lease_until=0,
                               revive_attempts=revive_attempts+1,revived_at=?
                           WHERE action_id=? AND state='blocked'""",
                        (candidate["next_revision"], now, candidate["action_id"]),
                    )
                    revived.append({
                        **candidate,
                        "revived_at": now,
                        "disposition": "revived",
                        "revision": candidate["next_revision"],
                        "revive_attempts": candidate["revive_attempts"] + 1,
                        "blocked_seconds": max(0, now - candidate["blocked_at"]),
                    })
                elif decision == "dlq":
                    burned_revisions = (
                        candidate["reason"] == "revision_budget_exhausted"
                    )
                    closures.append(self._dead_letter(
                        connection,
                        candidate,
                        reason=candidate["reason"],
                        # The counter and its label must agree: quarantining for a
                        # spent revision budget records revisions, not revives.
                        attempts=(
                            candidate["revision"] if burned_revisions
                            else candidate["revive_attempts"]
                        ),
                        attempts_kind="revision" if burned_revisions else "revive_attempts",
                        now=now,
                    ))
                    dead_lettered.append({
                        **candidate,
                        "revived_at": now,
                        "disposition": "dlq",
                        "blocked_seconds": max(0, now - candidate["blocked_at"]),
                    })
                elif decision == "nothing_to_say":
                    closures.append(self._dead_letter(
                        connection,
                        candidate,
                        reason=f"nothing_to_say:{candidate['reason']}",
                        attempts=candidate["revive_attempts"],
                        attempts_kind="nothing_to_say",
                        now=now,
                        closure="nothing_to_say",
                    ))
                    closed_without_send.append({
                        **candidate,
                        "closed_at": now,
                        "disposition": "nothing_to_say",
                        "blocked_seconds": max(0, now - candidate["blocked_at"]),
                    })
        if not revived and not dead_lettered and not closed_without_send:
            # The advisory read saw work but the locked re-read did not: a
            # concurrent pass or detector took it first. Reporting "applied 0/0"
            # would read as a confident zero, so name what happened.
            return {
                "revived": revived,
                "dead_lettered": dead_lettered,
                "status": "raced",
            }
        # Tradeoff, stated on purpose: state is committed BEFORE the audit line is
        # appended, so a crash between the two loses the jsonl line, never the
        # durable transition. The inverse (audit first) would claim a revive that
        # never happened, which is the failure mode this codebase forbids.
        #
        # For the same reason the append cannot be allowed to rewrite the outcome:
        # a full or read-only ~/gig must not turn a COMMITTED revive into a
        # reported failure with zero counts. The counts stay true and the lost
        # trail gets its own field.
        audit_error: str | None = None
        try:
            for record in revived + dead_lettered:
                self._append_revive_record(record)
            for record in closures:
                self._append_closure_record(record)
        except OSError as error:
            audit_error = repr(error)
        return {
            "revived": revived,
            "dead_lettered": dead_lettered,
            "closed_without_send": closed_without_send,
            "status": "applied",
            "audit_error": audit_error,
        }

    def _invalidate_pre_click_revision(
        self, connection: sqlite3.Connection, action: sqlite3.Row, observed_at: int
    ) -> sqlite3.Row:
        if action["state"] not in ("pending", "claimed", "intent_ready"):
            raise InvalidTransition("action is not pre-click")
        intent = self._intent(connection, action["action_id"], action["revision"])
        if intent is None and action["state"] == "intent_ready":
            raise InvalidTransition("intent_ready action has no immutable prepared intent")
        if intent is not None:
            if intent["state"] != "prepared" or intent["click_started_at"] is not None:
                raise InvalidTransition("pre-click action has an invalid prior intent")
            connection.execute(
                """UPDATE connector_intents SET state='superseded',superseded_at=?
                   WHERE action_id=? AND revision=? AND state='prepared'""",
                (observed_at, action["action_id"], action["revision"]),
            )
        connection.execute(
            """UPDATE connector_actions
               SET state='pending',revision=revision+1,owner=NULL,lease_until=0,updated_at=?
               WHERE action_id=? AND state=? AND revision=?""",
            (observed_at, action["action_id"], action["state"], action["revision"]),
        )
        self._release_slot(connection, action["action_id"])
        return self._action(connection, action["action_id"])

    def get_action(self, action_id: int) -> dict[str, Any]:
        action_id = self._require_positive_integer("action_id", action_id)
        with closing(self._connect()) as connection:
            return dict(self._action(connection, action_id))

    def action_lifecycle_for_event(
        self, event_key: str, thread_id: str
    ) -> dict[str, Any] | None:
        """Return bounded state for one exact event without exposing message text."""
        thread_id = self._require_key("thread_id", thread_id)
        event_key = validate_coconala_event_key(event_key, thread_id)
        with closing(self._connect()) as connection:
            row = connection.execute(
                """SELECT e.platform AS event_platform,
                          e.thread_id AS event_thread_id,
                          a.platform AS action_platform,a.thread_id AS action_thread_id,
                          a.state,a.dlq_at,
                          d.closure AS dlq_closure,d.reason AS dlq_reason,
                          i.rejection_code
                     FROM connector_events e
                     JOIN connector_actions a ON a.action_id=e.action_id
                     LEFT JOIN connector_dlq d ON d.action_id=a.action_id
                     LEFT JOIN connector_intents i
                       ON i.action_id=a.action_id AND i.revision=a.revision
                    WHERE e.event_key=?
                    LIMIT 1""",
                (event_key,),
            ).fetchone()
        if row is None:
            return None
        if (
            row["event_platform"] != "coconala"
            or row["event_thread_id"] != thread_id
            or row["action_platform"] != "coconala"
            or row["action_thread_id"] != thread_id
        ):
            raise InvalidTransition("event metadata does not match thread_id")
        bounded = lambda value: None if value is None else str(value)[:300]
        return {
            "state": str(row["state"]),
            "dlq_at": None if row["dlq_at"] is None else int(row["dlq_at"]),
            "closure": bounded(row["dlq_closure"]),
            "reason": bounded(row["dlq_reason"]),
            "rejection_code": bounded(row["rejection_code"]),
        }

    def pending_action_for_thread(self, thread_id: str) -> dict[str, Any] | None:
        """Return the one claimable action bound to a thread, if present."""
        thread_id = self._require_key("thread_id", thread_id)
        with closing(self._connect()) as connection:
            row = connection.execute(
                """SELECT * FROM connector_actions
                   WHERE platform='coconala' AND thread_id=? AND state='pending'
                     AND dlq_at IS NULL
                     AND NOT EXISTS (
                       SELECT 1 FROM connector_events e
                        WHERE e.action_id=connector_actions.action_id
                          AND e.event_key LIKE 'coconala:estimate:v1:%'
                     )
                   ORDER BY action_id LIMIT 1""",
                (thread_id,),
            ).fetchone()
            return self._dict(row)

    def pending_actions(self) -> list[dict[str, Any]]:
        """Return durable pending actions independent of the current inbox projection."""
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """SELECT a.*,
                          e.event_key,
                          e.platform AS event_platform,
                          e.thread_id AS event_thread_id,
                          e.observed_at AS event_observed_at
                   FROM connector_actions a
                   LEFT JOIN connector_events e
                     ON e.event_key=(
                         SELECT latest_event.event_key
                           FROM connector_events latest_event
                          WHERE latest_event.action_id=a.action_id
                          ORDER BY latest_event.rowid DESC
                          LIMIT 1
                     )
                   WHERE a.platform='coconala' AND a.state='pending'
                     AND a.dlq_at IS NULL
                     AND NOT EXISTS (
                       SELECT 1 FROM connector_events kind_event
                        WHERE kind_event.action_id=a.action_id
                          AND kind_event.event_key LIKE 'coconala:estimate:v1:%'
                     )
                   ORDER BY a.created_at,a.action_id"""
            ).fetchall()
            actions = [dict(row) for row in rows]
        try:
            for action in actions:
                event_key = action.get("event_key")
                event_platform = action.get("event_platform")
                event_thread_id = action.get("event_thread_id")
                if (
                    type(event_key) is not str
                    or type(event_platform) is not str
                    or type(event_thread_id) is not str
                    or event_platform != action["platform"]
                    or event_thread_id != action["thread_id"]
                ):
                    raise ValueError("event metadata does not match action")
                validate_coconala_event_key(event_key, action["thread_id"])
                self._require_timestamp(
                    "event_observed_at", action.get("event_observed_at")
                )
        except (TypeError, ValueError) as error:
            raise InvalidTransition(
                "durable pending action has invalid event identity"
            ) from error
        return actions

    def pending_targeted_actions(self) -> list[dict[str, Any]]:
        """Return pending actions whose newest typed inbox event can be targeted.

        The five-minute queue may append a fallback event after a continuous
        detector has already recorded an inbox identity on the same action.
        Selecting the globally newest event in that case hides the inbox event
        from the direct-thread supervisor, which only accepts exact inbox
        identities.  Keep the general ``pending_actions`` projection unchanged
        for the fallback queue and expose this narrower projection for the
        targeted supervisor.
        """
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """SELECT a.*,
                          e.event_key,
                          e.platform AS event_platform,
                          e.thread_id AS event_thread_id,
                          e.observed_at AS event_observed_at
                   FROM connector_actions a
                   JOIN connector_events e
                     ON e.event_key=(
                         SELECT latest_inbox.event_key
                           FROM connector_events latest_inbox
                          WHERE latest_inbox.action_id=a.action_id
                            AND latest_inbox.event_key LIKE 'coconala:inbox:v1:%'
                          ORDER BY latest_inbox.rowid DESC
                          LIMIT 1
                     )
                   WHERE a.platform='coconala' AND a.state='pending'
                     AND a.dlq_at IS NULL
                     AND NOT EXISTS (
                       SELECT 1 FROM connector_events kind_event
                        WHERE kind_event.action_id=a.action_id
                          AND kind_event.event_key LIKE 'coconala:estimate:v1:%'
                     )
                   ORDER BY a.created_at,a.action_id"""
            ).fetchall()
            actions = [dict(row) for row in rows]
        try:
            for action in actions:
                event_key = action.get("event_key")
                event_platform = action.get("event_platform")
                event_thread_id = action.get("event_thread_id")
                if (
                    type(event_key) is not str
                    or type(event_platform) is not str
                    or type(event_thread_id) is not str
                    or event_platform != action["platform"]
                    or event_thread_id != action["thread_id"]
                ):
                    raise ValueError("event metadata does not match action")
                validate_coconala_event_key(event_key, action["thread_id"])
                if not event_key.startswith("coconala:inbox:v1:"):
                    raise ValueError("targeted action lacks inbox event identity")
                self._require_timestamp(
                    "event_observed_at", action.get("event_observed_at")
                )
        except (TypeError, ValueError) as error:
            raise InvalidTransition(
                "durable targeted action has invalid event identity"
            ) from error
        return actions

    def blocked_targeted_actions(self) -> list[dict[str, Any]]:
        """Return sending-unavailable blocks that a fresh official head can release."""
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """SELECT a.*,e.event_key,i.rejection_code
                     FROM connector_actions a
                     JOIN connector_events e ON e.rowid=(
                       SELECT latest.rowid FROM connector_events latest
                        WHERE latest.action_id=a.action_id
                          AND latest.event_key LIKE 'coconala:inbox:v1:%'
                        ORDER BY latest.rowid DESC LIMIT 1)
                     JOIN connector_intents i ON i.action_id=a.action_id
                       AND i.revision=a.revision
                    WHERE a.platform='coconala' AND a.state='blocked'
                      AND a.dlq_at IS NULL
                      AND i.state='superseded'
                      AND i.rejection_code='submit_rejected_sending_unavailable'
                    ORDER BY a.created_at,a.action_id"""
            ).fetchall()
        return [
            dict(row) for row in rows
            if int(row["revive_attempts"]) < blocked_revive_attempt_cap(
                str(row["rejection_code"]),
            )
        ]

    def revive_sending_available(
        self, action_id: int, *, expected_revision: int, now: int,
    ) -> dict[str, Any]:
        """Release one blocked reply after a fresh official send-available proof."""
        action_id = self._require_positive_integer("action_id", action_id)
        expected_revision = self._require_positive_integer(
            "expected_revision", expected_revision,
        )
        now = self._require_timestamp("now", now)
        with self._write() as connection:
            action = self._action(connection, action_id)
            self._require_monotonic(action, now)
            intent = self._intent(connection, action_id, expected_revision)
            occupied = connection.execute(
                """SELECT 1 FROM connector_actions
                    WHERE platform=? AND thread_id=? AND action_id<>?
                      AND state IN ('pending','claimed','intent_ready','reconcile_pending')
                      AND dlq_at IS NULL LIMIT 1""",
                (action["platform"], action["thread_id"], action_id),
            ).fetchone()
            if (
                action["state"] != "blocked" or action["dlq_at"] is not None
                or int(action["revision"]) != expected_revision
                or intent is None or intent["state"] != "superseded"
                or intent["rejection_code"] != "submit_rejected_sending_unavailable"
                or occupied is not None
            ):
                raise InvalidTransition("blocked sending-available proof is stale")
            connection.execute(
                """UPDATE connector_actions
                   SET state='pending',revision=revision+1,owner=NULL,lease_until=0,
                       revive_attempts=revive_attempts+1,revived_at=?
                   WHERE action_id=? AND state='blocked' AND revision=?""",
                (now, action_id, expected_revision),
            )
            stored = dict(self._action(connection, action_id))
        self._append_revive_record({
            "action_id": action_id, "thread_id": stored["thread_id"],
            "revision": int(stored["revision"]), "revived_at": now,
            "disposition": "official_sending_available",
        })
        return stored

    def reconciliation_action_for_thread(self, thread_id: str) -> dict[str, Any] | None:
        """Return bounded intent metadata for one delivery-unknown thread."""
        thread_id = self._require_key("thread_id", thread_id)
        with closing(self._connect()) as connection:
            row = connection.execute(
                """SELECT a.*,i.outgoing_hash,
                          i.origin_at AS intent_origin_at,
                          i.click_started_at,i.executor_quiesced_at,i.rejection_code
                   FROM connector_actions a
                   JOIN connector_intents i
                     ON i.action_id=a.action_id AND i.revision=a.revision
                   WHERE a.platform='coconala' AND a.thread_id=?
                     AND a.state='reconcile_pending' AND i.state='reconcile_pending'
                     AND a.dlq_at IS NULL
                     AND NOT EXISTS (
                       SELECT 1 FROM connector_events kind_event
                        WHERE kind_event.action_id=a.action_id
                          AND kind_event.event_key LIKE 'coconala:estimate:v1:%'
                     )
                   ORDER BY a.action_id LIMIT 1""",
                (thread_id,),
            ).fetchone()
            return self._dict(row)

    def reconciliation_actions(self) -> list[dict[str, Any]]:
        """Return every durable delivery-unknown action independent of inbox projection."""
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """SELECT a.*,i.outgoing_hash,
                          i.origin_at AS intent_origin_at,
                          i.click_started_at,i.executor_quiesced_at,
                          i.rejection_code,
                          (SELECT e.event_key
                             FROM connector_events e
                            WHERE e.action_id=a.action_id
                            ORDER BY e.observed_at,e.event_key LIMIT 1) AS event_key
                   FROM connector_actions a
                   JOIN connector_intents i
                     ON i.action_id=a.action_id AND i.revision=a.revision
                   WHERE a.platform='coconala'
                     AND a.state='reconcile_pending' AND i.state='reconcile_pending'
                     AND a.dlq_at IS NULL
                     AND NOT EXISTS (
                       SELECT 1 FROM connector_events kind_event
                        WHERE kind_event.action_id=a.action_id
                          AND kind_event.event_key LIKE 'coconala:estimate:v1:%'
                     )
                   ORDER BY a.created_at,a.action_id"""
            ).fetchall()
            return [dict(row) for row in rows]

    def estimate_pending_actions(self) -> list[dict[str, Any]]:
        """Return only requested-estimate pending actions for the estimate lane."""
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """SELECT a.*,e.event_key,e.observed_at AS event_observed_at
                     FROM connector_actions a
                     JOIN connector_events e ON e.action_id=a.action_id
                    WHERE a.platform='coconala' AND a.state='pending'
                      AND a.dlq_at IS NULL
                      AND e.event_key LIKE 'coconala:estimate:v1:%'
                    ORDER BY a.created_at,a.action_id"""
            ).fetchall()
        return [dict(row) for row in rows]

    def estimate_reconciliation_action_for_thread(self, thread_id: str) -> dict[str, Any] | None:
        thread_id = self._require_key("thread_id", thread_id)
        with closing(self._connect()) as connection:
            row = connection.execute(
                """SELECT a.*,i.outgoing_hash,i.outgoing_body,
                          i.origin_at AS intent_origin_at,
                          i.click_started_at,i.executor_quiesced_at,i.rejection_code,
                          e.event_key
                     FROM connector_actions a
                     LEFT JOIN connector_intents i
                       ON i.action_id=a.action_id AND i.revision=a.revision
                     JOIN connector_events e ON e.action_id=a.action_id
                    WHERE a.platform='coconala' AND a.thread_id=?
                      AND a.state='reconcile_pending' AND i.state='reconcile_pending'
                      AND a.dlq_at IS NULL
                      AND e.event_key LIKE 'coconala:estimate:v1:%'
                    ORDER BY a.action_id LIMIT 1""",
                (thread_id,),
            ).fetchone()
            return self._dict(row)

    def estimate_reconciliation_actions(self) -> list[dict[str, Any]]:
        """Return estimate delivery-unknown actions, never normal-message actions."""
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """SELECT a.*,i.outgoing_hash,i.outgoing_body,
                          i.origin_at AS intent_origin_at,
                          i.click_started_at,i.executor_quiesced_at,i.rejection_code,
                          e.event_key
                     FROM connector_actions a
                     JOIN connector_intents i
                       ON i.action_id=a.action_id AND i.revision=a.revision
                     JOIN connector_events e ON e.action_id=a.action_id
                    WHERE a.platform='coconala'
                      AND a.state='reconcile_pending' AND i.state='reconcile_pending'
                      AND a.dlq_at IS NULL
                      AND e.event_key LIKE 'coconala:estimate:v1:%'
                    ORDER BY a.created_at,a.action_id"""
            ).fetchall()
        return [dict(row) for row in rows]

    def verified_estimate_after_request(
        self, thread_id: str, request_sent_at: int,
    ) -> dict[str, Any] | None:
        """Return an officially read-back estimate answering this buyer request."""
        thread_id = self._require_key("thread_id", thread_id)
        request_sent_at = self._require_timestamp("request_sent_at", request_sent_at)
        with closing(self._connect()) as connection:
            row = connection.execute(
                """SELECT a.*,i.outgoing_hash,i.outgoing_body,
                          i.origin_at AS intent_origin_at,i.click_started_at,
                          e.event_key
                     FROM connector_actions a
                     LEFT JOIN connector_intents i
                       ON i.action_id=a.action_id AND i.revision=a.revision
                     JOIN connector_events e ON e.action_id=a.action_id
                    WHERE a.platform='coconala' AND a.thread_id=?
                      AND a.state='replied' AND a.dlq_at IS NULL
                      AND a.seller_sent_at>=?
                      AND (
                        (i.state='verified' AND i.outgoing_body IS NOT NULL)
                        OR (i.action_id IS NULL AND a.verified_outgoing_hash IS NOT NULL)
                      )
                      AND e.event_key LIKE 'coconala:estimate:v1:%'
                      AND NOT EXISTS (
                        SELECT 1 FROM connector_events newer
                           WHERE newer.action_id=e.action_id
                             AND newer.event_key LIKE 'coconala:estimate:v1:%'
                           AND newer.rowid>e.rowid
                      )
                    ORDER BY a.seller_sent_at DESC,a.action_id DESC,
                             e.rowid DESC
                    LIMIT 1""",
                (thread_id, request_sent_at),
            ).fetchone()
            return self._dict(row)

    def enqueue(
        self, *, event_key: str, thread_id: str, thread_url: str, observed_at: int,
        _estimate_only: bool = False,
    ) -> dict[str, Any]:
        """Atomically deduplicate an event and coalesce it onto one active thread action."""
        manifest = self._manifest()
        platform = manifest["connector"]
        observed_at = self._require_timestamp("observed_at", observed_at)
        thread_id = self._require_key("thread_id", thread_id)
        event_key = validate_coconala_event_key(event_key, thread_id)
        is_estimate = _ESTIMATE_EVENT.fullmatch(event_key) is not None
        if _estimate_only and not is_estimate:
            raise ValueError("estimate event key required")
        thread_url = self._canonical_thread_url(thread_url, thread_id)
        with self._write() as connection:
            duplicate = connection.execute(
                """SELECT e.action_id,e.platform,e.thread_id,a.thread_url
                   FROM connector_events e
                   JOIN connector_actions a ON a.action_id=e.action_id
                   WHERE e.event_key=?""",
                (event_key,),
            ).fetchone()
            if duplicate is not None:
                identity_matches = (
                    duplicate["platform"] == platform
                    and duplicate["thread_id"] == thread_id
                    and duplicate["thread_url"] == thread_url
                )
                if not identity_matches:
                    raise OutboxError("duplicate event identity mismatch")
                return dict(self._action(connection, duplicate["action_id"]))
            active_kinds = connection.execute(
                """SELECT DISTINCT
                          CASE WHEN e.event_key LIKE 'coconala:estimate:v1:%'
                               THEN 'estimate' ELSE 'normal' END AS kind
                     FROM connector_events e
                     JOIN connector_actions a ON a.action_id=e.action_id
                    WHERE a.platform=? AND a.thread_id=?
                      AND a.state IN ('pending','claimed','intent_ready','reconcile_pending')
                      AND a.dlq_at IS NULL""",
                (platform, thread_id),
            ).fetchall()
            if any(str(row["kind"]) != ("estimate" if is_estimate else "normal") for row in active_kinds):
                raise OutboxError("estimate_event_conflict")
            active = connection.execute(
                """SELECT * FROM connector_actions
                   WHERE platform=? AND thread_id=?
                     AND state IN ('pending','claimed','intent_ready','reconcile_pending')
                     AND dlq_at IS NULL""",
                (platform, thread_id),
            ).fetchone()
            blocked = connection.execute(
                """SELECT * FROM connector_actions
                   WHERE platform=? AND thread_id=? AND state='blocked'
                     AND dlq_at IS NULL""",
                (platform, thread_id),
            ).fetchone()
            if active is not None:
                self._require_monotonic(active, observed_at)
            if blocked is not None:
                self._require_monotonic(blocked, observed_at)
            has_click_history = active is not None and connection.execute(
                "SELECT 1 FROM connector_intents WHERE action_id=? AND click_started_at IS NOT NULL LIMIT 1",
                (active["action_id"],),
            ).fetchone() is not None
            target = blocked
            if blocked is not None and active is None:
                next_revision = int(blocked["revision"])
                blocked_intent = self._intent(
                    connection, blocked["action_id"], blocked["revision"]
                )
                if blocked_intent is not None:
                    if blocked_intent["state"] != "superseded":
                        raise InvalidTransition(
                            "blocked action has a non-superseded current intent"
                        )
                    next_revision += 1
                connection.execute(
                    """UPDATE connector_actions
                       SET state='pending',revision=?,updated_at=?
                       WHERE action_id=? AND state='blocked'""",
                    (next_revision, observed_at, blocked["action_id"]),
                )
                target = self._action(connection, blocked["action_id"])
            elif blocked is None and active is not None and (
                active["state"] == "reconcile_pending" or has_click_history
            ):
                cursor = connection.execute(
                    """INSERT INTO connector_actions
                       (platform,thread_id,thread_url,state,revision,created_at,updated_at)
                       VALUES(?,?,?,'blocked',1,?,?)""",
                    (platform, thread_id, thread_url, observed_at, observed_at),
                )
                target = self._action(connection, int(cursor.lastrowid))
            elif blocked is None and active is not None:
                target = self._invalidate_pre_click_revision(connection, active, observed_at)
            elif blocked is None and active is None:
                cursor = connection.execute(
                    """INSERT INTO connector_actions
                       (platform,thread_id,thread_url,state,revision,created_at,updated_at)
                       VALUES(?,?,?,'pending',1,?,?)""",
                    (platform, thread_id, thread_url, observed_at, observed_at),
                )
                target = self._action(connection, int(cursor.lastrowid))
            if target is None or target["thread_url"] != thread_url:
                raise OutboxError("active thread URL mismatch")
            action_id = int(target["action_id"])
            connection.execute(
                "INSERT INTO connector_events(event_key,action_id,platform,thread_id,observed_at) VALUES(?,?,?,?,?)",
                (event_key, action_id, platform, thread_id, observed_at),
            )
            connection.execute(
                "UPDATE connector_actions SET updated_at=? WHERE action_id=?",
                (observed_at, action_id),
            )
            return dict(self._action(connection, action_id))

    def enqueue_estimate(
        self, *, event_key: str, thread_id: str, thread_url: str, observed_at: int
    ) -> dict[str, Any]:
        """Ingest an estimate event, replacing only an untouched normal reply."""
        thread_id = self._require_key("thread_id", thread_id)
        event_key = validate_coconala_event_key(event_key, thread_id)
        if not _ESTIMATE_EVENT.fullmatch(event_key):
            raise ValueError("estimate event key required")
        canonical_url = self._canonical_thread_url(thread_url, thread_id)
        normal = self.pending_action_for_thread(thread_id)
        if normal is not None:
            owner = f"estimate-handoff-{thread_id}"
            claimed = self.claim(
                owner=owner, now=observed_at, lease_seconds=30,
                action_id=int(normal["action_id"]),
            )
            if claimed is None:
                raise OutboxError("estimate_event_conflict")
            self.close_nothing_to_say(
                int(claimed["action_id"]), owner=owner,
                fencing_token=int(claimed["fencing_token"]),
                reason="requested_estimate", now=observed_at,
            )
        stored = self.enqueue(
            event_key=event_key, thread_id=thread_id, thread_url=canonical_url,
            observed_at=observed_at, _estimate_only=True,
        )
        if stored.get("state") == "reconcile_pending":
            reconciled = self.estimate_reconciliation_action_for_thread(thread_id)
            if reconciled is not None and reconciled.get("action_id") == stored.get("action_id"):
                return reconciled
        return stored

    def claim(
        self, *, owner: str, now: int, lease_seconds: int, action_id: int | None = None
    ) -> dict[str, Any] | None:
        """Claim one pre-click action and the manifest-limited connector slot."""
        manifest = self._manifest()
        platform = manifest["connector"]
        owner = self._require_text("owner", owner)
        now = self._require_timestamp("now", now)
        lease_seconds = self._require_positive_integer("lease_seconds", lease_seconds)
        if action_id is not None:
            action_id = self._require_positive_integer("action_id", action_id)
        reap_record: dict[str, Any] | None = None
        with self._write() as connection:
            slot = connection.execute(
                "SELECT * FROM connector_slots WHERE platform = ?", (platform,)
            ).fetchone()
            if slot is None:
                raise ConnectorDisabled("connector slot missing")
            if slot["action_id"] is not None:
                if int(slot["lease_until"]) > now:
                    raise ConnectorBusy("connector browser slot is owned until explicitly released")
                reap_record = self._reap_expired_slot(connection, slot, now=now, reaper=owner)
                slot = connection.execute(
                    "SELECT * FROM connector_slots WHERE platform = ?", (platform,)
                ).fetchone()
            elif slot["lease_until"] > now:
                raise ConnectorBusy("connector browser slot is leased")
            # A revived row carries a days-old created_at, so plain FIFO would let
            # resurrections monopolise the single browser tab ahead of every fresh
            # buyer inquiry. Deprioritise them -- but only while the revive is
            # RECENT: after REVIVE_DEPRIORITY_SECONDS the row competes on created_at
            # again, so a sustained stream of fresh inquiries can delay a
            # resurrection by at most that window instead of starving it forever.
            parameters: list[Any] = [now - REVIVE_DEPRIORITY_SECONDS, platform]
            action_filter = ""
            if action_id is not None:
                action_filter = " AND action_id = ?"
                parameters.append(action_id)
            claimed: dict[str, Any] | None = None
            candidate = connection.execute(
                f"""SELECT *, (revived_at IS NOT NULL AND revived_at > ?) AS recently_revived
                    FROM connector_actions
                    WHERE platform = ?
                      AND state = 'pending'
                      AND dlq_at IS NULL
                      {action_filter}
                    ORDER BY recently_revived, created_at, action_id LIMIT 1""",
                parameters,
            ).fetchone()
            if candidate is not None:
                self._require_monotonic(candidate, now)
                fencing_token = int(slot["fencing_token"]) + 1
                lease_until = now + lease_seconds
                connection.execute(
                    """UPDATE connector_actions
                       SET state=?,owner=?,fencing_token=?,lease_until=?,updated_at=? WHERE action_id=?""",
                    ("claimed", owner, fencing_token, lease_until, now, candidate["action_id"]),
                )
                connection.execute(
                    """UPDATE connector_slots
                       SET action_id=?,owner=?,fencing_token=?,lease_until=? WHERE platform=?""",
                    (candidate["action_id"], owner, fencing_token, lease_until, platform),
                )
                claimed = dict(self._action(connection, candidate["action_id"]))
        if reap_record is not None:
            self._append_reap_record(reap_record)
        return claimed

    def prepare_intent(
        self,
        action_id: int,
        *,
        owner: str,
        fencing_token: int,
        outgoing_body: str,
        now: int,
        origin_at: int | None = None,
        store_outgoing_body: bool = False,
    ) -> dict[str, Any]:
        """Persist only an immutable normalized hash before click authorization."""
        self._manifest()
        action_id = self._require_positive_integer("action_id", action_id)
        fencing_token = self._require_positive_integer("fencing_token", fencing_token)
        now = self._require_timestamp("now", now)
        origin_at = self._require_timestamp(
            "origin_at", now if origin_at is None else origin_at
        )
        if origin_at > now:
            raise ValueError("origin_at cannot be after intent creation")
        normalized_body = normalize_outgoing_body(outgoing_body)
        raw_body = outgoing_body
        if not normalized_body:
            raise ValueError("outgoing body normalizes to empty")
        digest = hashlib.sha256(normalized_body.encode("utf-8")).hexdigest()
        with self._write() as connection:
            action = self._require_fence(
                connection, action_id, owner, fencing_token, now, ("claimed", "intent_ready")
            )
            self._require_monotonic(action, now)
            intent = self._intent(connection, action_id, action["revision"])
            if intent is not None:
                if intent["owner_id"] != owner or intent["fencing_token"] != fencing_token:
                    raise StaleFence("immutable intent belongs to another owner fence")
                if intent["outgoing_hash"] != digest:
                    raise ImmutableIntent("intent body cannot change within a revision")
                if int(intent["origin_at"]) != origin_at:
                    raise ImmutableIntent("intent origin cannot change within a revision")
                if store_outgoing_body and intent["outgoing_body"] is None:
                    connection.execute(
                        "UPDATE connector_intents SET outgoing_body=? "
                        "WHERE action_id=? AND revision=? AND outgoing_body IS NULL",
                        (raw_body, action_id, action["revision"]),
                    )
            else:
                connection.execute(
                    """INSERT INTO connector_intents
                       (action_id,revision,outgoing_hash,outgoing_body,owner_id,
                        fencing_token,state,created_at,origin_at)
                       VALUES(?,?,?,?,?,?,'prepared',?,?)""",
                    (
                        action_id, action["revision"], digest,
                        raw_body if store_outgoing_body else None,
                        owner, fencing_token, now, origin_at,
                    ),
                )
            connection.execute(
                "UPDATE connector_actions SET state='intent_ready',updated_at=? WHERE action_id=?",
                (now, action_id),
            )
            return dict(self._intent(connection, action_id, action["revision"]))

    def _provider_effect_values(
        self, intent: Any, authorization: Any,
    ) -> tuple[str, str, str, str, str, str, str]:
        state = getattr(getattr(authorization, "state", None), "value", None)
        receipt_hash = getattr(authorization, "receipt_hash", None)
        if state not in {"approved_api", "approved_browser"}:
            raise ConnectorDisabled("authorization_not_approved")
        authorization_hash = str(getattr(intent, "authorization_hash", ""))
        if (
            not re.fullmatch(r"[0-9a-f]{64}", str(receipt_hash or ""))
            or receipt_hash != authorization_hash
        ):
            raise ConnectorDisabled("authorization_not_approved")
        provider = self._require_key("provider", getattr(intent, "provider", ""))
        account_key = self._require_key("account_key", getattr(intent, "account_key", ""))
        resource_id = self._require_key("resource_id", getattr(intent, "resource_id", ""))
        action = self._require_key("action", getattr(intent, "action", ""))
        effect_key = self._require_key("effect_key", getattr(intent, "effect_key", ""))
        payload_hash = str(getattr(intent, "payload_hash", ""))
        if not re.fullmatch(r"[0-9a-f]{64}", payload_hash):
            raise ValueError("invalid payload_hash")
        return (
            effect_key, provider, account_key, resource_id, action, payload_hash,
            authorization_hash,
        )

    def prepare_provider_effect(
        self, intent: Any, *, authorization: Any, now: int,
        connects_pre: int | None = None,
        connects_pre_hash: str | None = None,
        payload_body: str | None = None,
        capacity_limit: int | None = None,
        active_resource_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Persist one authorization-bound non-Coconala effect before execution."""
        values = self._provider_effect_values(intent, authorization)
        now = self._require_timestamp("now", now)
        supplied = (connects_pre, connects_pre_hash, payload_body)
        if any(value is not None for value in supplied):
            if (
                type(connects_pre) is not int or connects_pre < 0
                or not re.fullmatch(r"[0-9a-f]{64}", str(connects_pre_hash or ""))
                or not isinstance(payload_body, str) or not payload_body
            ):
                raise ValueError("invalid provider pre-effect evidence")
        if (capacity_limit is None) != (active_resource_ids is None):
            raise ValueError("invalid provider capacity evidence")
        if capacity_limit is not None and (
            type(capacity_limit) is not int or capacity_limit < 1
            or not isinstance(active_resource_ids, list)
            or any(not isinstance(item, str) or not item for item in active_resource_ids)
            or len(set(active_resource_ids)) != len(active_resource_ids)
        ):
            raise ValueError("invalid provider capacity evidence")
        with self._write() as connection:
            resource = connection.execute(
                """SELECT * FROM provider_effect_intents
                   WHERE provider=? AND account_key=? AND resource_id=? AND action=?""",
                (values[1], values[2], values[3], values[4]),
            ).fetchone()
            if resource is not None and resource["payload_hash"] != values[5] and values[4] in {"propose", "deliver_milestone"}:
                label = "proposal" if values[4] == "propose" else "milestone delivery"
                raise ImmutableIntent(f"resource already has {label} intent")
            existing = connection.execute(
                """SELECT * FROM provider_effect_intents
                   WHERE provider=? AND account_key=? AND resource_id=?
                     AND action=? AND payload_hash=?""",
                (values[1], values[2], values[3], values[4], values[5]),
            ).fetchone()
            if existing is not None:
                if existing["authorization_hash"] != values[6]:
                    raise ImmutableIntent("authorization hash cannot change")
                if existing["effect_key"] != values[0]:
                    raise ImmutableIntent("effect key cannot change")
                for field, expected in (
                    ("connects_pre", connects_pre),
                    ("connects_pre_hash", connects_pre_hash),
                    ("payload_body", payload_body),
                ):
                    if expected is not None and existing[field] != expected:
                        raise ImmutableIntent(f"provider {field} cannot change")
                return {**dict(existing), "created": False, "reconcile_only": True}
            if capacity_limit is not None:
                for contract_id in active_resource_ids:
                    connection.execute(
                        """DELETE FROM provider_capacity_reservations
                           WHERE provider=? AND account_key=? AND contract_id=?""",
                        (values[1], values[2], contract_id),
                    )
                reserved = connection.execute(
                    """SELECT count(*) FROM provider_capacity_reservations
                       WHERE provider=? AND account_key=?""",
                    (values[1], values[2]),
                ).fetchone()[0]
                if len(active_resource_ids) + int(reserved) >= capacity_limit:
                    raise ConnectorBusy("provider capacity exhausted")
            connection.execute(
                """INSERT INTO provider_effect_intents
                   (effect_key,provider,account_key,resource_id,action,payload_hash,
                    authorization_hash,state,connects_pre,connects_pre_hash,payload_body,
                    created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,'prepared',?,?,?,?,?)""",
                (*values, connects_pre, connects_pre_hash, payload_body, now, now),
            )
            if capacity_limit is not None:
                connection.execute(
                    """INSERT INTO provider_capacity_reservations
                       (effect_key,provider,account_key,resource_id,created_at,updated_at)
                       VALUES(?,?,?,?,?,?)""",
                    (values[0], values[1], values[2], values[3], now, now),
                )
            stored = connection.execute(
                "SELECT * FROM provider_effect_intents WHERE effect_key=?", (values[0],),
            ).fetchone()
            return {**dict(stored), "created": True, "reconcile_only": False}

    def mark_provider_effect_started(
        self, intent: Any, *, authorization: Any, now: int,
    ) -> dict[str, Any]:
        """Close retry permission immediately before a provider mutation."""
        values = self._provider_effect_values(intent, authorization)
        now = self._require_timestamp("now", now)
        with self._write() as connection:
            existing = connection.execute(
                "SELECT * FROM provider_effect_intents WHERE effect_key=?", (values[0],),
            ).fetchone()
            if existing is None:
                raise InvalidTransition("provider effect intent missing")
            if tuple(existing[key] for key in (
                "provider", "account_key", "resource_id", "action", "payload_hash",
                "authorization_hash",
            )) != values[1:]:
                raise ImmutableIntent("provider effect identity changed")
            if existing["state"] == "reconcile_pending":
                return {**dict(existing), "started": False, "reconcile_only": True}
            cursor = connection.execute(
                """UPDATE provider_effect_intents
                   SET state='reconcile_pending',reconciliation_state='reconcile_unknown',updated_at=?
                   WHERE effect_key=? AND state='prepared'""",
                (now, values[0]),
            )
            if cursor.rowcount != 1:
                raise InvalidTransition("provider effect is not prepared")
            stored = connection.execute(
                "SELECT * FROM provider_effect_intents WHERE effect_key=?", (values[0],),
            ).fetchone()
            return {**dict(stored), "started": True, "reconcile_only": False}

    def provider_effect(self, intent: Any) -> dict[str, Any] | None:
        """Read one immutable provider effect without changing retry permission."""
        effect_key = self._require_key("effect_key", getattr(intent, "effect_key", ""))
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT * FROM provider_effect_intents WHERE effect_key=?", (effect_key,),
            ).fetchone()
            return dict(row) if row is not None else None

    def reopen_provider_effect_after_no_effect(
        self, intent: Any, *, authorization: Any, connects_current: int,
        connects_evidence_sha256: str, no_effect_readback_hash: str, now: int,
    ) -> dict[str, Any]:
        """Reopen after absence and the ledger explain every balance change as another effect."""
        values = self._provider_effect_values(intent, authorization)
        now = self._require_timestamp("now", now)
        if (
            type(connects_current) is not int or connects_current < 0
            or not re.fullmatch(r"[0-9a-f]{64}", connects_evidence_sha256)
            or not re.fullmatch(r"[0-9a-f]{64}", no_effect_readback_hash)
        ):
            raise ValueError("invalid provider no-effect evidence")
        with self._write() as connection:
            existing = connection.execute(
                "SELECT * FROM provider_effect_intents WHERE effect_key=?", (values[0],),
            ).fetchone()
            intervening_spend = 0 if existing is None else connection.execute(
                """SELECT COALESCE(SUM(connects_pre-connects_post),0)
                   FROM provider_effect_intents
                   WHERE provider=? AND account_key=? AND effect_key<>?
                     AND reconciliation_state='verified' AND updated_at>?
                     AND connects_pre IS NOT NULL AND connects_post IS NOT NULL""",
                (existing["provider"], existing["account_key"], values[0], existing["updated_at"]),
            ).fetchone()[0]
            if (
                existing is None or existing["state"] != "reconcile_pending"
                or existing["reconciliation_state"] != "reconcile_unknown"
                or existing["proposal_id"] is not None
                or existing["connects_post"] is not None
                or existing["connects_pre"] - intervening_spend != connects_current
            ):
                raise InvalidTransition("provider no-effect readback is inconsistent")
            connection.execute(
                """UPDATE provider_effect_intents
                   SET state='prepared',reconciliation_state='not_started',
                       connects_pre=?,connects_pre_hash=?,readback_hash=?,updated_at=?
                   WHERE effect_key=?""",
                (connects_current, connects_evidence_sha256, no_effect_readback_hash, now, values[0]),
            )
            return dict(connection.execute(
                "SELECT * FROM provider_effect_intents WHERE effect_key=?", (values[0],),
            ).fetchone())

    def verified_provider_resource_ids(self, provider: str, action: str) -> set[str]:
        """Project completed external effects out of an acquisition-ready queue."""
        provider = self._require_key("provider", provider)
        action = self._require_key("action", action)
        with closing(self._connect()) as connection:
            return {
                str(row[0]) for row in connection.execute(
                    """SELECT resource_id FROM provider_effect_intents
                       WHERE provider=? AND action=? AND reconciliation_state='verified'""",
                    (provider, action),
                )
            }

    def verify_provider_effect(
        self, intent: Any, *, proposal_id: str, connects_post: int,
        readback_hash: str, now: int,
    ) -> dict[str, Any]:
        """Record only exact authoritative proposal and Connects readback."""
        effect_key = self._require_key("effect_key", getattr(intent, "effect_key", ""))
        proposal_id = self._require_key("proposal_id", proposal_id)
        if type(connects_post) is not int or connects_post < 0:
            raise ValueError("invalid connects_post")
        if not re.fullmatch(r"[0-9a-f]{64}", str(readback_hash or "")):
            raise ValueError("invalid readback_hash")
        now = self._require_timestamp("now", now)
        with self._write() as connection:
            existing = connection.execute(
                "SELECT * FROM provider_effect_intents WHERE effect_key=?", (effect_key,),
            ).fetchone()
            if existing is None or existing["state"] != "reconcile_pending":
                raise InvalidTransition("provider effect is not awaiting reconciliation")
            expected_identity = tuple(existing[key] for key in (
                "provider", "account_key", "resource_id", "action", "payload_hash",
                "authorization_hash", "effect_key",
            ))
            actual_identity = tuple(getattr(intent, key) for key in (
                "provider", "account_key", "resource_id", "action", "payload_hash",
                "authorization_hash", "effect_key",
            ))
            if expected_identity != actual_identity:
                raise ImmutableIntent("provider effect identity changed")
            connection.execute(
                """UPDATE provider_capacity_reservations
                   SET contract_id=?,updated_at=? WHERE effect_key=?""",
                (proposal_id, now, effect_key),
            )
            if existing["connects_pre"] is None or connects_post > existing["connects_pre"]:
                raise InvalidTransition("provider Connects readback is inconsistent")
            if existing["reconciliation_state"] == "verified":
                expected = (existing["proposal_id"], existing["connects_post"], existing["readback_hash"])
                if expected != (proposal_id, connects_post, readback_hash):
                    raise ImmutableIntent("provider readback cannot change")
                return dict(existing)
            connection.execute(
                """UPDATE provider_effect_intents
                   SET reconciliation_state='verified',proposal_id=?,connects_post=?,
                       readback_hash=?,updated_at=? WHERE effect_key=?""",
                (proposal_id, connects_post, readback_hash, now, effect_key),
            )
            return dict(connection.execute(
                "SELECT * FROM provider_effect_intents WHERE effect_key=?", (effect_key,),
            ).fetchone())

    def supervisor_recover_stopped_owner(
        self,
        action_id: int,
        *,
        expected_owner: str,
        expected_fencing_token: int,
        owner_stopped: bool,
        now: int,
    ) -> dict[str, Any]:
        """Release a stopped executor without treating lease expiry as proof of safety."""
        self._manifest(require_enabled=False)
        action_id = self._require_positive_integer("action_id", action_id)
        expected_fencing_token = self._require_positive_integer(
            "expected_fencing_token", expected_fencing_token
        )
        expected_owner = self._require_text("expected_owner", expected_owner)
        now = self._require_timestamp("now", now)
        if owner_stopped is not True:
            raise InvalidTransition("verified process and browser stop is required")
        with self._write() as connection:
            action = self._action(connection, action_id)
            self._require_monotonic(action, now)
            if action["state"] not in ("claimed", "intent_ready", "reconcile_pending"):
                raise InvalidTransition("action has no recoverable executor ownership")
            slot = connection.execute(
                "SELECT * FROM connector_slots WHERE platform=?", (action["platform"],)
            ).fetchone()
            identity_matches = (
                action["owner"] == expected_owner
                and int(action["fencing_token"]) == int(expected_fencing_token)
                and slot is not None
                and slot["action_id"] == action_id
                and slot["owner"] == expected_owner
                and int(slot["fencing_token"]) == int(expected_fencing_token)
            )
            if not identity_matches:
                raise StaleFence("stopped owner or fencing token does not match")
            intent = self._intent(connection, action_id, action["revision"])
            if action["state"] == "reconcile_pending":
                if intent is None or intent["click_started_at"] is None:
                    raise InvalidTransition("click-started intent missing")
                if now < int(intent["click_started_at"]):
                    raise InvalidTransition("executor quiescence cannot precede click")
                connection.execute(
                    """UPDATE connector_intents
                       SET executor_quiesced_at=?,executor_quiesced_by='supervisor'
                       WHERE action_id=? AND revision=? AND state='reconcile_pending'""",
                    (now, action_id, action["revision"]),
                )
                next_state = "reconcile_pending"
                next_revision = int(action["revision"])
            else:
                if intent is not None and intent["click_started_at"] is not None:
                    raise InvalidTransition("clicked action cannot be requeued")
                next_revision = int(action["revision"])
                if intent is not None:
                    if intent["state"] != "prepared":
                        raise InvalidTransition("pre-click intent is not recoverable")
                    if (
                        intent["owner_id"] != expected_owner
                        or intent["fencing_token"] != expected_fencing_token
                    ):
                        raise StaleFence("immutable intent belongs to another owner fence")
                    connection.execute(
                        """UPDATE connector_intents SET state='superseded',superseded_at=?
                           WHERE action_id=? AND revision=? AND state='prepared'""",
                        (now, action_id, action["revision"]),
                    )
                    next_revision += 1
                next_state = "pending"
            connection.execute(
                """UPDATE connector_actions
                   SET state=?,revision=?,owner=NULL,lease_until=0,updated_at=?
                   WHERE action_id=?""",
                (next_state, next_revision, now, action_id),
            )
            self._release_slot(connection, action_id)
            return dict(self._action(connection, action_id))

    def record_pre_click_failure(
        self, action_id: int, *, owner: str, fencing_token: int, now: int
    ) -> dict[str, Any]:
        """Release a failure proven to occur before click; the same revision may retry."""
        self._manifest(require_enabled=False)
        action_id = self._require_positive_integer("action_id", action_id)
        fencing_token = self._require_positive_integer("fencing_token", fencing_token)
        now = self._require_timestamp("now", now)
        with self._write() as connection:
            action = self._require_identity_fence(
                connection, action_id, owner, fencing_token, ("claimed", "intent_ready")
            )
            self._require_monotonic(action, now)
            intent = self._intent(connection, action_id, action["revision"])
            if intent is None and action["state"] == "intent_ready":
                raise InvalidTransition("intent_ready action has no immutable prepared intent")
            next_revision = int(action["revision"])
            if intent is not None:
                valid_intent = (
                    intent["state"] == "prepared"
                    and intent["click_started_at"] is None
                    and intent["owner_id"] == owner
                    and intent["fencing_token"] == fencing_token
                )
                if not valid_intent:
                    raise InvalidTransition("pre-click failure intent ownership mismatch")
                connection.execute(
                    """UPDATE connector_intents SET state='superseded',superseded_at=?
                       WHERE action_id=? AND revision=? AND state='prepared'""",
                    (now, action_id, action["revision"]),
                )
                next_revision += 1
            connection.execute(
                """UPDATE connector_actions
                   SET state='pending',revision=?,owner=NULL,lease_until=0,updated_at=?
                   WHERE action_id=?""",
                (next_revision, now, action_id),
            )
            self._release_slot(connection, action_id)
            return dict(self._action(connection, action_id))

    def mark_click_started(
        self,
        action_id: int,
        revision: int,
        *,
        owner: str,
        fencing_token: int,
        now: int,
        lease_seconds: int | None = None,
    ) -> dict[str, Any]:
        """CAS the prepared revision into ambiguity before the external click."""
        self._manifest()
        action_id = self._require_positive_integer("action_id", action_id)
        revision = self._require_positive_integer("revision", revision)
        fencing_token = self._require_positive_integer("fencing_token", fencing_token)
        now = self._require_timestamp("now", now)
        if lease_seconds is not None:
            lease_seconds = self._require_positive_integer(
                "lease_seconds", lease_seconds
            )
        with self._write() as connection:
            action = self._require_fence(
                connection, action_id, owner, fencing_token, now, ("intent_ready",)
            )
            self._require_monotonic(action, now)
            if action["revision"] != revision:
                raise InvalidTransition("revision is stale")
            intent = self._intent(connection, action_id, revision)
            if intent is None or now < int(intent["created_at"]):
                raise InvalidTransition("click timestamp precedes immutable intent")
            if intent["owner_id"] != owner or intent["fencing_token"] != fencing_token:
                raise StaleFence("immutable intent belongs to another owner fence")
            renewed_lease_until = (
                now + lease_seconds
                if lease_seconds is not None
                else int(action["lease_until"])
            )
            cursor = connection.execute(
                """UPDATE connector_intents
                   SET state='reconcile_pending',click_started_at=?
                   WHERE action_id=? AND revision=? AND owner_id=? AND fencing_token=?
                     AND state='prepared' AND click_started_at IS NULL""",
                (now, action_id, revision, owner, fencing_token),
            )
            if cursor.rowcount != 1:
                raise InvalidTransition("click already started or intent is not prepared")
            cursor = connection.execute(
                """UPDATE connector_actions
                   SET state='reconcile_pending',lease_until=?,updated_at=?
                   WHERE action_id=? AND state='intent_ready' AND revision=?""",
                (renewed_lease_until, now, action_id, revision),
            )
            if cursor.rowcount != 1:
                raise InvalidTransition("click authorization CAS failed")
            cursor = connection.execute(
                """UPDATE connector_slots SET lease_until=?
                   WHERE platform=? AND action_id=? AND owner=? AND fencing_token=?""",
                (
                    renewed_lease_until,
                    action["platform"],
                    action_id,
                    owner,
                    fencing_token,
                ),
            )
            if cursor.rowcount != 1:
                raise StaleFence("connector slot renewal failed")
            return dict(self._action(connection, action_id))

    def record_delivery_unknown(
        self,
        action_id: int,
        *,
        owner: str,
        fencing_token: int,
        now: int,
        rejection_code: str | None = None,
    ) -> dict[str, Any]:
        """Release the browser slot while keeping a click-started action non-claimable."""
        self._manifest(require_enabled=False)
        action_id = self._require_positive_integer("action_id", action_id)
        fencing_token = self._require_positive_integer("fencing_token", fencing_token)
        now = self._require_timestamp("now", now)
        if rejection_code is not None and rejection_code not in SERVER_REJECTION_CODES:
            raise ValueError("invalid rejection_code")
        with self._write() as connection:
            action = self._require_identity_fence(
                connection, action_id, owner, fencing_token, ("reconcile_pending",)
            )
            self._require_monotonic(action, now)
            intent = self._intent(connection, action_id, action["revision"])
            if intent is None or intent["click_started_at"] is None:
                raise InvalidTransition("click-started intent missing")
            if now < int(intent["click_started_at"]):
                raise InvalidTransition("executor quiescence cannot precede click")
            connection.execute(
                """UPDATE connector_intents
                   SET executor_quiesced_at=?,executor_quiesced_by='owner',
                       rejection_code=?
                   WHERE action_id=? AND revision=? AND state='reconcile_pending'""",
                (now, rejection_code, action_id, action["revision"]),
            )
            connection.execute(
                "UPDATE connector_actions SET owner=NULL,lease_until=0,updated_at=? WHERE action_id=?",
                (now, action_id),
            )
            self._release_slot(connection, action_id)
            return dict(self._action(connection, action_id))

    def _requeue_after_absence(
        self,
        connection: sqlite3.Connection,
        *,
        action: sqlite3.Row,
        intent: sqlite3.Row,
        observed_at: int,
    ) -> tuple[dict[str, Any], dict[str, Any] | None]:
        """Park a proven-absent action: blocked, dead-lettered, or one fresh revision.

        Returns the stored action plus the closure record that MUST be appended to
        the audit after the surrounding transaction commits (``None`` when nothing
        was quarantined).
        """
        action_id = int(action["action_id"])
        successor = None
        if intent["rejection_code"] in SERVER_REJECTION_CODES:
            attempts = max(0, int(action["revive_attempts"]))
            attempt_cap = blocked_revive_attempt_cap(str(intent["rejection_code"]))
            if attempts >= attempt_cap:
                clean_no_send = (
                    intent["rejection_code"]
                    == "submit_rejected_sending_unavailable"
                )
                reason = (
                    f"nothing_to_say:officially_unrepliable:{intent['rejection_code']}"
                    if clean_no_send
                    else f"revive_attempts_exhausted:{intent['rejection_code']}"
                )
                closure = self._dead_letter(
                    connection,
                    action,
                    reason=reason,
                    attempts=attempts,
                    attempts_kind="nothing_to_say" if clean_no_send else "revive",
                    now=observed_at,
                    closure="nothing_to_say" if clean_no_send else "dlq",
                )
                connection.execute(
                    """UPDATE connector_actions
                       SET owner=NULL,lease_until=0,updated_at=? WHERE action_id=?""",
                    (observed_at, action_id),
                )
                self._release_slot(connection, action_id)
                exhausted = dict(self._action(connection, action_id))
                exhausted["revive_attempts_exhausted"] = True
                return exhausted, closure
            successor = connection.execute(
                """SELECT * FROM connector_actions
                   WHERE platform=? AND thread_id=? AND state='blocked'
                     AND action_id<>?
                     AND dlq_at IS NULL""",
                (action["platform"], action["thread_id"], action_id),
            ).fetchone()
            if successor is None:
                connection.execute(
                    """UPDATE connector_actions
                       SET state='blocked',owner=NULL,lease_until=0,updated_at=?
                       WHERE action_id=? AND state='reconcile_pending'""",
                    (observed_at, action_id),
                )
                self._release_slot(connection, action_id)
                return dict(self._action(connection, action_id)), None
        if int(action["revision"]) + 1 > MAX_REVISIONS_PER_ACTION:
            # C1b anti-burn invariant.  Every requeue buys one more browser click
            # and one more composer call; the live runaway thread spent 35 of them
            # and never reached a verified delivery.  Past the budget the action is
            # dead-lettered instead of requeued, so the loop stops paying for the
            # same failure.  A blocked successor (if any) is deliberately left
            # untouched: it is the thread's fresh-budget path.
            closure = self._dead_letter(
                connection,
                action,
                reason="revision_budget_exhausted",
                attempts=int(action["revision"]),
                attempts_kind="revision",
                now=observed_at,
            )
            connection.execute(
                "UPDATE connector_actions SET owner=NULL,lease_until=0,updated_at=? WHERE action_id=?",
                (observed_at, action_id),
            )
            self._release_slot(connection, action_id)
            exhausted = dict(self._action(connection, action_id))
            exhausted["revision_budget_exhausted"] = True
            return exhausted, closure
        if successor is not None:
            successor_intent = connection.execute(
                "SELECT 1 FROM connector_intents WHERE action_id=? LIMIT 1",
                (successor["action_id"],),
            ).fetchone()
            if successor_intent is not None:
                raise InvalidTransition(
                    "blocked successor unexpectedly contains an intent"
                )
            successor_event = connection.execute(
                """SELECT MAX(observed_at) AS latest_event_at
                   FROM connector_events WHERE action_id=?""",
                (successor["action_id"],),
            ).fetchone()
            latest_event_at = (
                None if successor_event is None else successor_event["latest_event_at"]
            )
            if latest_event_at is None:
                raise InvalidTransition("blocked successor has no event")
            latest_event_at = self._require_timestamp(
                "successor_event_observed_at", latest_event_at
            )
            if latest_event_at > observed_at:
                raise InvalidTransition(
                    "authoritative absence predates a blocked successor event"
                )
            connection.execute(
                "UPDATE connector_events SET action_id=? WHERE action_id=?",
                (action_id, successor["action_id"]),
            )
            connection.execute(
                "DELETE FROM connector_actions WHERE action_id=? AND state='blocked'",
                (successor["action_id"],),
            )
        connection.execute(
            """UPDATE connector_actions
               SET state='pending',revision=revision+1,owner=NULL,lease_until=0,updated_at=?
               WHERE action_id=? AND state='reconcile_pending'""",
            (observed_at, action_id),
        )
        self._release_slot(connection, action_id)
        reconciled = dict(self._action(connection, action_id))
        if successor is not None:
            reconciled["new_event_reactivated"] = True
        return reconciled, None

    def reconcile(
        self,
        action_id: int,
        *,
        thread_url: str,
        outgoing_hash: str,
        seller_sent_at: int | None,
        last_sender: str | None,
        observed_at: int,
        authoritative_absent: bool,
    ) -> dict[str, Any]:
        """Apply bounded authoritative presence/absence evidence, never DOM time alone."""
        manifest = self._manifest(require_enabled=False)
        action_id = self._require_positive_integer("action_id", action_id)
        observed_at = self._require_timestamp("observed_at", observed_at)
        if seller_sent_at is not None:
            seller_sent_at = self._require_timestamp("seller_sent_at", seller_sent_at)
        if last_sender not in (None, "buyer", "seller", "system"):
            raise ValueError("invalid last_sender")
        if type(authoritative_absent) is not bool:
            raise ValueError("authoritative_absent must be a boolean")
        with self._write() as connection:
            action = self._action(connection, action_id)
            self._require_monotonic(action, observed_at)
            canonical_thread_url = self._canonical_thread_url(thread_url, action["thread_id"])
            if action["thread_url"] != canonical_thread_url:
                raise InvalidTransition("reconciliation thread URL mismatch")
            if action["state"] == "replied":
                return dict(action)
            if action["state"] in ("pending", "blocked") and authoritative_absent:
                latest = connection.execute(
                    "SELECT * FROM connector_intents WHERE action_id=? ORDER BY revision DESC LIMIT 1",
                    (action_id,),
                ).fetchone()
                if latest is not None and latest["state"] == "superseded" and latest["outgoing_hash"] == outgoing_hash:
                    return dict(action)
            if action["state"] != "reconcile_pending":
                raise InvalidTransition("action is not awaiting reconciliation")
            intent = self._intent(connection, action_id, action["revision"])
            if intent is None or intent["click_started_at"] is None:
                raise InvalidTransition("click-started intent missing")
            evidence_matches = intent["outgoing_hash"] == outgoing_hash
            presence_matches = (
                evidence_matches
                and seller_sent_at is not None
                and int(seller_sent_at) >= int(intent["click_started_at"])
                and int(seller_sent_at) <= int(observed_at)
            )
            if presence_matches:
                connection.execute(
                    "UPDATE connector_intents SET state='verified' WHERE action_id=? AND revision=?",
                    (action_id, action["revision"]),
                )
                connection.execute(
                    """UPDATE connector_actions
                       SET state='replied',owner=NULL,lease_until=0,updated_at=?,
                           verified_thread_url=?,verified_outgoing_hash=?,seller_sent_at=?,last_sender=?
                       WHERE action_id=?""",
                    (
                        observed_at,
                        canonical_thread_url,
                        outgoing_hash,
                        seller_sent_at,
                        last_sender,
                        action_id,
                    ),
                )
                self._release_slot(connection, action_id)
                connection.execute(
                    """UPDATE connector_actions
                       SET state='pending',updated_at=?
                       WHERE platform=? AND thread_id=? AND state='blocked'
                         AND dlq_at IS NULL""",
                    (observed_at, action["platform"], action["thread_id"]),
                )
                return dict(self._action(connection, action_id))
            if not authoritative_absent:
                return dict(action)
            if not evidence_matches:
                raise InvalidTransition("authoritative absence does not identify the active intent")
            if intent["executor_quiesced_at"] is None:
                raise ExecutorStillActive("executor stop or post-attempt completion is not proven")
            quiesced_at = int(intent["executor_quiesced_at"])
            if observed_at < quiesced_at:
                raise InvalidTransition("authoritative absence predates executor quiescence")
            earliest = max(int(intent["click_started_at"]), quiesced_at) + int(
                manifest["max_consistency_window_seconds"]
            )
            if observed_at < earliest:
                raise ConsistencyWindowOpen("authoritative absence arrived before consistency window closed")
            connection.execute(
                """UPDATE connector_intents SET state='superseded',superseded_at=?
                   WHERE action_id=? AND revision=? AND state='reconcile_pending'""",
                (observed_at, action_id, action["revision"]),
            )
            reconciled, burn_closure = self._requeue_after_absence(
                connection, action=action, intent=intent, observed_at=observed_at
            )
            if burn_closure is None:
                return reconciled
        self._append_closure_record(burn_closure)
        return reconciled

    def thread_delivered_hash(self, thread_id: str, outgoing_hash: str) -> bool:
        """Return whether this exact content was already delivered to the thread.

        Stripe idempotent-requests replica: the normalized body hash is the
        idempotency key, and the replied actions of the thread are the key store.
        """
        thread_id = self._require_key("thread_id", thread_id)
        if not re.fullmatch(r"[0-9a-f]{64}", str(outgoing_hash or "")):
            raise ValueError("invalid outgoing_hash")
        with closing(self._connect()) as connection:
            row = connection.execute(
                """SELECT 1 FROM connector_actions
                   WHERE platform='coconala' AND thread_id=?
                     AND state='replied' AND verified_outgoing_hash=?
                   LIMIT 1""",
                (thread_id, str(outgoing_hash)),
            ).fetchone()
            return row is not None

    def note_reconcile_unresolved(self, action_id: int, *, now: int) -> int:
        """Count one reconcile pass that could not resolve delivery-unknown."""
        action_id = self._require_positive_integer("action_id", action_id)
        now = self._require_timestamp("now", now)
        with self._write() as connection:
            action = self._action(connection, action_id)
            self._require_monotonic(action, now)
            if action["state"] != "reconcile_pending":
                raise InvalidTransition(
                    "only delivery-unknown actions accumulate unresolved passes"
                )
            connection.execute(
                """UPDATE connector_actions
                   SET reconcile_attempts=reconcile_attempts+1,updated_at=?
                   WHERE action_id=?""",
                (now, action_id),
            )
            return int(self._action(connection, action_id)["reconcile_attempts"])

    def move_to_dlq(self, action_id: int, *, reason: str, now: int) -> dict[str, Any]:
        """Quarantine an unresolvable delivery-unknown action (dead-letter queue).

        Azure dead-letter pattern replica: a message whose delivery cannot be
        verified is moved aside instead of blind-retried, and the lane moves on.
        The action keeps its ``reconcile_pending`` row (no evidence is fabricated)
        but leaves every reconciliation projection until a human or self-heal
        closes it.
        """
        self._manifest(require_enabled=False)
        action_id = self._require_positive_integer("action_id", action_id)
        reason = self._require_text("reason", reason)
        now = self._require_timestamp("now", now)
        with self._write() as connection:
            action = self._action(connection, action_id)
            self._require_monotonic(action, now)
            if action["state"] != "reconcile_pending":
                raise InvalidTransition("only delivery-unknown actions can be dead-lettered")
            record = self._dead_letter(
                connection,
                action,
                reason=reason,
                attempts=int(action["reconcile_attempts"]),
                attempts_kind="reconcile_attempts",
                now=now,
            )
            connection.execute(
                "UPDATE connector_actions SET owner=NULL,lease_until=0,updated_at=? WHERE action_id=?",
                (now, action_id),
            )
            self._release_slot(connection, action_id)
            stored = dict(self._action(connection, action_id))
        self._append_closure_record(record)
        return stored

    def dlq_actions(self) -> list[dict[str, Any]]:
        """Return quarantined FAULTS for reporting and manual repair.

        Deliberately excludes ``nothing_to_say`` closures: they use the same
        removal mechanism but are a correct outcome, and putting them in the
        repair queue would teach the reader that a healthy lane has a backlog.
        """
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """SELECT d.action_id,d.thread_id,d.reason,d.unresolved_attempts,
                          d.moved_at,d.closure,a.state,a.thread_url,a.revision
                   FROM connector_dlq d
                   JOIN connector_actions a ON a.action_id=d.action_id
                   WHERE COALESCE(d.closure,'dlq')='dlq'
                   ORDER BY d.moved_at,d.action_id"""
            ).fetchall()
            return [dict(row) for row in rows]

    def closed_actions(self, *, closure: str | None = None) -> list[dict[str, Any]]:
        """Return every action removed from the queue, faults and clean closures alike."""
        query = (
            """SELECT d.action_id,d.thread_id,d.reason,d.unresolved_attempts,
                      d.moved_at,COALESCE(d.closure,'dlq') AS closure,
                      d.attempts_kind,a.state,a.thread_url,a.revision
               FROM connector_dlq d
               JOIN connector_actions a ON a.action_id=d.action_id"""
        )
        parameters: tuple[Any, ...] = ()
        if closure is not None:
            query += " WHERE COALESCE(d.closure,'dlq')=?"
            parameters = (self._require_text("closure", closure),)
        query += " ORDER BY d.moved_at,d.action_id"
        with closing(self._connect()) as connection:
            return [dict(row) for row in connection.execute(query, parameters).fetchall()]

    def close_nothing_to_say(
        self,
        action_id: int,
        *,
        owner: str,
        fencing_token: int,
        reason: str,
        now: int,
    ) -> dict[str, Any]:
        """Close a claimed action that has nothing to answer.

        ``buyer-last`` was raised as ``ValueError`` at the composition boundary,
        which made the lane's bulkhead park the action back in ``pending`` and try
        again five minutes later, forever (412 consecutive runs on thread
        93000007).  "We already spoke last" is not a failure, it is the answer.

        The closure deliberately does NOT touch ``state``, ``seller_sent_at`` or
        ``verified_outgoing_hash``: nothing was sent, so claiming ``replied``
        would fabricate a delivery and would poison ``thread_delivered_hash``.
        It only removes the action from every projection via ``dlq_at`` with a
        non-fault closure kind, so the NEXT buyer message on the same thread
        enqueues a fresh action instead of colliding with this one.
        """
        self._manifest(require_enabled=False)
        action_id = self._require_positive_integer("action_id", action_id)
        fencing_token = self._require_positive_integer("fencing_token", fencing_token)
        reason = self._require_text("reason", reason)
        now = self._require_timestamp("now", now)
        with self._write() as connection:
            action = self._require_identity_fence(
                connection, action_id, owner, fencing_token, ("claimed",)
            )
            self._require_monotonic(action, now)
            intent = self._intent(connection, action_id, action["revision"])
            if intent is not None and intent["state"] != "superseded":
                # Composition runs before prepare_intent, so a live intent at this
                # revision means the caller is somewhere else in the lifecycle and
                # this closure would erase a real send attempt.
                raise InvalidTransition(
                    "nothing-to-say closure requires a pre-intent claim"
                )
            record = self._dead_letter(
                connection,
                action,
                reason=f"nothing_to_say:{reason}",
                attempts=0,
                attempts_kind="nothing_to_say",
                now=now,
                closure="nothing_to_say",
            )
            connection.execute(
                """UPDATE connector_actions
                   SET state='pending',owner=NULL,lease_until=0,updated_at=?
                   WHERE action_id=?""",
                (now, action_id),
            )
            self._release_slot(connection, action_id)
            stored = dict(self._action(connection, action_id))
        self._append_closure_record(record)
        return stored

    def requeue_closed_action(
        self, action_id: int, *, now: int, require_no_intent: bool = False,
    ) -> dict[str, Any]:
        """Bring a closed action back into the queue without hand-editing sqlite.

        The recovery path for BOTH closure kinds: a human who fixed the cause, or
        a later code fix that wants its victims retried.  Refuses when the thread
        already has a live action, because un-quarantining into an occupied
        uniqueness slot is what makes the partial indexes raise IntegrityError on
        the next buyer event.
        """
        self._manifest(require_enabled=False)
        action_id = self._require_positive_integer("action_id", action_id)
        now = self._require_timestamp("now", now)
        if type(require_no_intent) is not bool:
            raise ValueError("require_no_intent must be boolean")
        with self._write() as connection:
            action = self._action(connection, action_id)
            closed = connection.execute(
                "SELECT * FROM connector_dlq WHERE action_id=?", (action_id,)
            ).fetchone()
            if closed is None and action["dlq_at"] is None:
                raise InvalidTransition("action is not closed")
            if require_no_intent and connection.execute(
                "SELECT 1 FROM connector_intents WHERE action_id=? LIMIT 1", (action_id,)
            ).fetchone() is not None:
                raise InvalidTransition("automatic requeue requires no prior intent")
            occupied = connection.execute(
                """SELECT 1 FROM connector_actions
                   WHERE platform=? AND thread_id=? AND action_id<>?
                     AND state IN ('pending','claimed','intent_ready','reconcile_pending')
                     AND dlq_at IS NULL LIMIT 1""",
                (action["platform"], action["thread_id"], action_id),
            ).fetchone()
            if occupied is not None:
                raise InvalidTransition("thread already has a live action")
            connection.execute("DELETE FROM connector_dlq WHERE action_id=?", (action_id,))
            connection.execute(
                """UPDATE connector_actions
                   SET dlq_at=NULL,state='pending',owner=NULL,lease_until=0,updated_at=?
                   WHERE action_id=?""",
                (max(now, int(action["updated_at"])), action_id),
            )
            connection.execute(
                """DELETE FROM connector_failure_streaks
                   WHERE platform=? AND thread_id=?""",
                (action["platform"], action["thread_id"]),
            )
            stored = dict(self._action(connection, action_id))
        self._append_closure_record({
            "closed_at": now,
            "closure": "requeued",
            "action_id": action_id,
            "thread_id": stored["thread_id"],
            "revision": int(stored["revision"]),
            "reason": str(closed["reason"]) if closed is not None else "dlq_at_only",
            "prior_closure": (
                str(closed["closure"] or "dlq") if closed is not None else "dlq"
            ),
        })
        return stored

    def thread_failure_streak(self, thread_id: str) -> dict[str, Any] | None:
        """Return the durable consecutive-failure streak for one thread."""
        thread_id = self._require_key("thread_id", thread_id)
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT * FROM connector_failure_streaks WHERE platform='coconala' AND thread_id=?",
                (thread_id,),
            ).fetchone()
            return self._dict(row)

    def clear_thread_failure_streak(self, thread_id: str) -> bool:
        """Forget the streak because this thread got through without raising."""
        thread_id = self._require_key("thread_id", thread_id)
        with self._write() as connection:
            cursor = connection.execute(
                "DELETE FROM connector_failure_streaks WHERE platform='coconala' AND thread_id=?",
                (thread_id,),
            )
            return cursor.rowcount > 0

    def record_thread_failure(
        self,
        *,
        thread_id: str,
        error_class: str,
        now: int,
        dead_letter_after: int,
    ) -> dict[str, Any]:
        """Count one CONSECUTIVE same-class failure, and quarantine at the bound.

        Consecutive, not lifetime: 412 identical exceptions in a row is a message
        that cannot succeed, while three scattered over a week is a lane doing its
        job against a flaky site.  A different error class replaces the streak
        rather than extending it, and any pass that does not raise clears it
        (``clear_thread_failure_streak``).

        Counting and quarantining happen in ONE transaction so two detector
        processes cannot both read "N-1" and both decide they are the Nth.
        """
        manifest = self._manifest(require_enabled=False)
        platform = manifest["connector"]
        thread_id = self._require_key("thread_id", thread_id)
        error_class = self._require_text("error_class", error_class)[:200]
        now = self._require_timestamp("now", now)
        dead_letter_after = self._require_positive_integer(
            "dead_letter_after", dead_letter_after
        )
        record: dict[str, Any] | None = None
        with self._write() as connection:
            existing = connection.execute(
                "SELECT * FROM connector_failure_streaks WHERE platform=? AND thread_id=?",
                (platform, thread_id),
            ).fetchone()
            action = connection.execute(
                """SELECT * FROM connector_actions
                   WHERE platform=? AND thread_id=? AND dlq_at IS NULL
                   ORDER BY CASE state WHEN 'pending' THEN 0 WHEN 'blocked' THEN 1
                                       ELSE 2 END, action_id
                   LIMIT 1""",
                (platform, thread_id),
            ).fetchone()
            action_id = int(action["action_id"]) if action is not None else None
            if existing is not None and str(existing["error_class"]) == error_class:
                consecutive = int(existing["consecutive"]) + 1
                first_at = int(existing["first_at"])
            else:
                consecutive = 1
                first_at = now
            connection.execute(
                """INSERT INTO connector_failure_streaks
                   (platform,thread_id,error_class,consecutive,action_id,first_at,last_at)
                   VALUES(?,?,?,?,?,?,?)
                   ON CONFLICT(platform,thread_id) DO UPDATE SET
                     error_class=excluded.error_class,
                     consecutive=excluded.consecutive,
                     action_id=excluded.action_id,
                     first_at=excluded.first_at,
                     last_at=excluded.last_at""",
                (platform, thread_id, error_class, consecutive, action_id, first_at, now),
            )
            result: dict[str, Any] = {
                "thread_id": thread_id,
                "error_class": error_class,
                "consecutive": consecutive,
                "action_id": action_id,
                "first_at": first_at,
                "dead_lettered": False,
                "reason": None,
                "not_dead_lettered_because": None,
            }
            if consecutive < dead_letter_after:
                return result
            if action is None:
                result["not_dead_lettered_because"] = "no_live_action"
                return result
            if str(action["state"]) not in ("pending", "blocked"):
                # 'claimed'/'intent_ready' means an owner still holds the fence and
                # 'reconcile_pending' is already bounded by reconcile_attempts;
                # quarantining either from here would forge a transition behind a
                # live participant's back.
                result["not_dead_lettered_because"] = f"state:{action['state']}"
                return result
            if now < int(action["updated_at"]):
                # This runs inside the lane's failure handler; a clock that went
                # backwards must not turn one failure into an exception storm.
                result["not_dead_lettered_because"] = "clock_precedes_action"
                return result
            reason = f"consecutive_failures:{error_class}"
            record = self._dead_letter(
                connection,
                action,
                reason=reason,
                attempts=consecutive,
                attempts_kind="consecutive_failures",
                now=now,
                closure="dlq",
            )
            connection.execute(
                "UPDATE connector_actions SET owner=NULL,lease_until=0,updated_at=? WHERE action_id=?",
                (now, action_id),
            )
            self._release_slot(connection, action_id)
            connection.execute(
                "DELETE FROM connector_failure_streaks WHERE platform=? AND thread_id=?",
                (platform, thread_id),
            )
            result["dead_lettered"] = True
            result["reason"] = reason
            result["thread_url"] = str(action["thread_url"])
            result["revision"] = int(action["revision"])
        if record is not None:
            self._append_closure_record(record)
        return result

    def close_paid_handoff(self, thread_id: str, *, observed_at: int) -> list[dict[str, Any]]:
        """Remove every unfinished pre-purchase action after an official purchase.

        The caller owns the fresh marketplace proof.  Intents are deliberately
        preserved as attempted-send evidence; paid ownership only removes these
        actions from Negotiate projections and releases any held thread slot.
        """
        self._manifest(require_enabled=False)
        thread_id = self._require_key("thread_id", thread_id)
        observed_at = self._require_timestamp("observed_at", observed_at)
        records: list[dict[str, Any]] = []
        with self._write() as connection:
            actions = connection.execute(
                """SELECT * FROM connector_actions
                   WHERE platform='coconala' AND thread_id=? AND dlq_at IS NULL
                     AND state IN ('pending','claimed','intent_ready','reconcile_pending','blocked')
                   ORDER BY action_id""",
                (thread_id,),
            ).fetchall()
            for action in actions:
                self._require_monotonic(action, observed_at)
                records.append(self._dead_letter(
                    connection, action, reason="nothing_to_say:paid_handoff",
                    attempts=0, attempts_kind="nothing_to_say",
                    now=observed_at, closure="nothing_to_say",
                ))
                connection.execute(
                    """UPDATE connector_actions
                       SET owner=NULL,lease_until=0,updated_at=? WHERE action_id=?""",
                    (observed_at, int(action["action_id"])),
                )
                self._release_slot(connection, int(action["action_id"]))
        for record in records:
            self._append_closure_record(record)
        return records

    def close_already_delivered(
        self,
        action_id: int,
        *,
        outgoing_hash: str,
        seller_sent_at: int | None,
        last_sender: str | None = "seller",
        observed_at: int,
        thread_url: str | None = None,
        owner: str | None = None,
        fencing_token: int | None = None,
    ) -> dict[str, Any]:
        """Close an action whose exact outgoing content is already in the thread.

        Stripe idempotent-requests replica: when the idempotency key (the
        normalized body hash) is already delivered, return the prior outcome
        instead of sending again.  Fenced (``intent_ready``) callers are the
        pre-send guard; unfenced callers must be reconciling delivery-unknown.
        """
        self._manifest(require_enabled=False)
        action_id = self._require_positive_integer("action_id", action_id)
        observed_at = self._require_timestamp("observed_at", observed_at)
        if seller_sent_at is not None:
            seller_sent_at = self._require_timestamp("seller_sent_at", seller_sent_at)
        if last_sender not in (None, "buyer", "seller", "system"):
            raise ValueError("invalid last_sender")
        if not re.fullmatch(r"[0-9a-f]{64}", str(outgoing_hash or "")):
            raise ValueError("invalid outgoing_hash")
        with self._write() as connection:
            if owner is not None:
                action = self._require_identity_fence(
                    connection,
                    action_id,
                    owner,
                    self._require_positive_integer("fencing_token", fencing_token),
                    ("intent_ready",),
                )
            elif thread_url is not None:
                action = self._action(connection, action_id)
                canonical_url = self._canonical_thread_url(thread_url, action["thread_id"])
                if action["thread_url"] != canonical_url:
                    raise InvalidTransition("already-delivered thread URL mismatch")
                if action["state"] not in ("pending", "reconcile_pending"):
                    raise InvalidTransition(
                        "already-delivered action is not closeable"
                    )
            else:
                action = self._action(connection, action_id)
                if action["state"] != "reconcile_pending":
                    raise InvalidTransition(
                        "unfenced already-delivered closure requires delivery-unknown state"
                    )
            self._require_monotonic(action, observed_at)
            intent = self._intent(connection, action_id, action["revision"])
            if intent is not None and intent["outgoing_hash"] != outgoing_hash:
                raise InvalidTransition(
                    "already-delivered evidence does not identify the active intent"
                )
            if intent is None and action["state"] != "pending":
                raise InvalidTransition("already-delivered closure requires the active intent")
            if intent is not None and intent["state"] == "prepared":
                connection.execute(
                    """UPDATE connector_intents SET state='superseded',superseded_at=?
                       WHERE action_id=? AND revision=? AND state='prepared'""",
                    (observed_at, action_id, action["revision"]),
                )
            elif intent is not None and intent["state"] == "reconcile_pending":
                connection.execute(
                    "UPDATE connector_intents SET state='verified' WHERE action_id=? AND revision=?",
                    (action_id, action["revision"]),
                )
            elif intent is not None:
                raise InvalidTransition("already-delivered closure requires an active intent")
            connection.execute(
                """UPDATE connector_actions
                   SET state='replied',owner=NULL,lease_until=0,updated_at=?,
                       verified_thread_url=?,verified_outgoing_hash=?,seller_sent_at=?,last_sender=?
                   WHERE action_id=?""",
                (
                    observed_at,
                    action["thread_url"],
                    outgoing_hash,
                    seller_sent_at,
                    last_sender,
                    action_id,
                ),
            )
            self._release_slot(connection, action_id)
            connection.execute(
                """UPDATE connector_actions
                   SET state='pending',updated_at=?
                   WHERE platform=? AND thread_id=? AND state='blocked'
                     AND dlq_at IS NULL""",
                (observed_at, action["platform"], action["thread_id"]),
            )
            connection.execute(
                "DELETE FROM connector_dlq WHERE action_id=?", (action_id,)
            )
            # connector_dlq is the ledger, dlq_at is its index-visible mirror:
            # un-quarantining must clear both or the partial indexes go stale.
            connection.execute(
                "UPDATE connector_actions SET dlq_at=NULL WHERE action_id=?", (action_id,)
            )
            record = {
                "closed_at": observed_at,
                "closure": "already_delivered",
                "action_id": action_id,
                "thread_id": action["thread_id"],
                "revision": int(action["revision"]),
                "outgoing_hash": outgoing_hash,
                "prior_state": action["state"],
                "seller_sent_at": seller_sent_at,
            }
            stored = dict(self._action(connection, action_id))
        self._append_closure_record(record)
        return stored
