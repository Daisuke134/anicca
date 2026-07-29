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
_FALLBACK_EVENT = re.compile(
    rf"coconala:fallback:v1:(?P<thread>{_EVENT_COMPONENT}):"
    r"(?P<sent_at>0|[1-9][0-9]*):(?P<ordinal>0|[1-9][0-9]*):sha256_v1:(?P<digest>[0-9a-f]{64})"
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


def coconala_initial_contact_event_key(order_id: str) -> str:
    """Build an order-scoped initial seller-contact identity."""
    order = _event_component("order_id", order_id)
    return f"coconala:initial-contact:v1:{order}"


def validate_coconala_event_key(event_key: str, thread_id: str) -> str:
    """Validate supported event grammar and its binding to the target thread."""
    if not isinstance(event_key, str) or len(event_key) > 500:
        raise ValueError("invalid event_key")
    expected_thread = _event_component("thread_id", thread_id)
    for pattern in (_MESSAGE_EVENT, _FALLBACK_EVENT):
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
    last_sender TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS connector_one_active_thread
ON connector_actions(platform, thread_id)
WHERE state IN ('pending','claimed','intent_ready','reconcile_pending');
CREATE UNIQUE INDEX IF NOT EXISTS connector_one_blocked_thread
ON connector_actions(platform, thread_id) WHERE state = 'blocked';

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

CREATE TABLE IF NOT EXISTS connector_slots (
    platform TEXT PRIMARY KEY,
    action_id INTEGER,
    owner TEXT,
    fencing_token INTEGER NOT NULL DEFAULT 0,
    lease_until INTEGER NOT NULL DEFAULT 0
);
"""


class ConnectorOutbox:
    """Deterministic Coconala event, intent, lease, and reconcile state."""

    def __init__(self, database: Path, manifest: Path = DEFAULT_MANIFEST):
        self.database = Path(database)
        self.manifest_path = Path(manifest)
        self.database.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

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
                    if "rejection_code" not in intent_columns:
                        connection.execute(
                            "ALTER TABLE connector_intents ADD COLUMN rejection_code TEXT"
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
        if not re.fullmatch(r"[A-Za-z0-9._:/-]{1,500}", text):
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
        parsed = urlsplit(str(value or ""))
        valid_path = re.fullmatch(r"/(?:mypage/direct_message|talkrooms)/[A-Za-z0-9_-]+", parsed.path)
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

    def pending_action_for_thread(self, thread_id: str) -> dict[str, Any] | None:
        """Return the one claimable action bound to a thread, if present."""
        thread_id = self._require_key("thread_id", thread_id)
        with closing(self._connect()) as connection:
            row = connection.execute(
                """SELECT * FROM connector_actions
                   WHERE platform='coconala' AND thread_id=? AND state='pending'
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
                         SELECT first_event.event_key
                           FROM connector_events first_event
                          WHERE first_event.action_id=a.action_id
                          ORDER BY first_event.observed_at,first_event.event_key
                          LIMIT 1
                     )
                   WHERE a.platform='coconala' AND a.state='pending'
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

    def reconciliation_action_for_thread(self, thread_id: str) -> dict[str, Any] | None:
        """Return bounded intent metadata for one delivery-unknown thread."""
        thread_id = self._require_key("thread_id", thread_id)
        with closing(self._connect()) as connection:
            row = connection.execute(
                """SELECT a.*,i.outgoing_hash,i.origin_at AS intent_origin_at,
                          i.click_started_at,i.executor_quiesced_at,i.rejection_code
                   FROM connector_actions a
                   JOIN connector_intents i
                     ON i.action_id=a.action_id AND i.revision=a.revision
                   WHERE a.platform='coconala' AND a.thread_id=?
                     AND a.state='reconcile_pending' AND i.state='reconcile_pending'
                   ORDER BY a.action_id LIMIT 1""",
                (thread_id,),
            ).fetchone()
            return self._dict(row)

    def reconciliation_actions(self) -> list[dict[str, Any]]:
        """Return every durable delivery-unknown action independent of inbox projection."""
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """SELECT a.*,i.outgoing_hash,i.origin_at AS intent_origin_at,
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
                   ORDER BY a.created_at,a.action_id"""
            ).fetchall()
            return [dict(row) for row in rows]

    def enqueue(
        self, *, event_key: str, thread_id: str, thread_url: str, observed_at: int
    ) -> dict[str, Any]:
        """Atomically deduplicate an event and coalesce it onto one active thread action."""
        manifest = self._manifest()
        platform = manifest["connector"]
        observed_at = self._require_timestamp("observed_at", observed_at)
        thread_id = self._require_key("thread_id", thread_id)
        event_key = validate_coconala_event_key(event_key, thread_id)
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
            active = connection.execute(
                """SELECT * FROM connector_actions
                   WHERE platform=? AND thread_id=?
                     AND state IN ('pending','claimed','intent_ready','reconcile_pending')""",
                (platform, thread_id),
            ).fetchone()
            blocked = connection.execute(
                "SELECT * FROM connector_actions WHERE platform=? AND thread_id=? AND state='blocked'",
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
        with self._write() as connection:
            slot = connection.execute(
                "SELECT * FROM connector_slots WHERE platform = ?", (platform,)
            ).fetchone()
            if slot is None:
                raise ConnectorDisabled("connector slot missing")
            if slot["action_id"] is not None:
                if (
                    action_id is not None
                    and int(slot["action_id"]) == int(action_id)
                    and int(slot["lease_until"]) <= now
                ):
                    return None
                raise ConnectorBusy("connector browser slot is owned until explicitly released")
            if slot["lease_until"] > now:
                raise ConnectorBusy("connector browser slot is leased")
            parameters: list[Any] = [platform]
            action_filter = ""
            if action_id is not None:
                action_filter = " AND action_id = ?"
                parameters.append(action_id)
            candidate = connection.execute(
                f"""SELECT * FROM connector_actions
                    WHERE platform = ?
                      AND state = 'pending'
                      {action_filter}
                    ORDER BY created_at, action_id LIMIT 1""",
                parameters,
            ).fetchone()
            if candidate is None:
                return None
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
            return dict(self._action(connection, candidate["action_id"]))

    def prepare_intent(
        self,
        action_id: int,
        *,
        owner: str,
        fencing_token: int,
        outgoing_body: str,
        now: int,
        origin_at: int | None = None,
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
            else:
                connection.execute(
                    """INSERT INTO connector_intents
                       (action_id,revision,outgoing_hash,owner_id,fencing_token,state,created_at,origin_at)
                       VALUES(?,?,?,?,?,'prepared',?,?)""",
                    (action_id, action["revision"], digest, owner, fencing_token, now, origin_at),
                )
            connection.execute(
                "UPDATE connector_actions SET state='intent_ready',updated_at=? WHERE action_id=?",
                (now, action_id),
            )
            return dict(self._intent(connection, action_id, action["revision"]))

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
                       WHERE platform=? AND thread_id=? AND state='blocked'""",
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
            successor = None
            if intent["rejection_code"] in SERVER_REJECTION_CODES:
                successor = connection.execute(
                    """SELECT * FROM connector_actions
                       WHERE platform=? AND thread_id=? AND state='blocked'
                         AND action_id<>?""",
                    (action["platform"], action["thread_id"], action_id),
                ).fetchone()
                if successor is None:
                    connection.execute(
                        """UPDATE connector_actions
                           SET state='blocked',owner=NULL,lease_until=0,updated_at=?
                           WHERE action_id=? AND state='reconcile_pending'""",
                        (observed_at, action_id),
                    )
                else:
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
                           SET state='pending',revision=revision+1,owner=NULL,lease_until=0,
                               updated_at=?
                           WHERE action_id=? AND state='reconcile_pending'""",
                        (observed_at, action_id),
                    )
            else:
                connection.execute(
                    """UPDATE connector_actions
                       SET state='pending',revision=revision+1,owner=NULL,lease_until=0,updated_at=?
                       WHERE action_id=? AND state='reconcile_pending'""",
                    (observed_at, action_id),
                )
            self._release_slot(connection, action_id)
            reconciled = dict(self._action(connection, action_id))
            if (
                intent["rejection_code"] in SERVER_REJECTION_CODES
                and successor is not None
            ):
                reconciled["new_event_reactivated"] = True
            return reconciled
