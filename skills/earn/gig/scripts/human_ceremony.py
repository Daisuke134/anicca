#!/usr/bin/env python3
"""Durable queue for the few marketplace acts reserved to a human."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from provider_adapter import ProviderState


DEFAULT_DATABASE = Path.home() / "gig" / "connector-outbox.sqlite3"
_HEX_64 = re.compile(r"[0-9a-f]{64}")


class CeremonyRejected(ValueError):
    """A request or completion did not prove a human-only boundary."""


class CeremonyKind(StrEnum):
    IDENTITY = "identity"
    FINANCIAL = "financial"
    PHYSICAL_CAPTURE = "physical_capture"
    CLIENT_RESERVED = "client_reserved"


@dataclass(frozen=True)
class CeremonyRecord:
    ceremony_id: int
    kind: CeremonyKind
    provider: str
    resource_id: str
    action: str
    status: str
    provider_url: str
    instruction: str
    control: str
    expected_result: str
    deadline: str
    resume_kind: str
    completion_hash: str | None


_SCHEMA = """
CREATE TABLE IF NOT EXISTS human_ceremonies (
    ceremony_id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_key TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL,
    provider TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    action TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('pending','completed')),
    provider_url TEXT NOT NULL,
    instruction TEXT NOT NULL,
    control TEXT NOT NULL,
    expected_result TEXT NOT NULL,
    deadline TEXT NOT NULL,
    initial_state TEXT NOT NULL,
    initial_observed_at TEXT NOT NULL,
    initial_evidence_hash TEXT NOT NULL CHECK(length(initial_evidence_hash)=64),
    resume_kind TEXT NOT NULL CHECK(resume_kind IN ('provider_state_changed','artifact_hash')),
    expected_state TEXT,
    artifact_kind TEXT,
    completion_hash TEXT,
    completion_observed_at TEXT
);
CREATE INDEX IF NOT EXISTS human_ceremonies_provider_status_idx
ON human_ceremonies(provider,status);
"""

_STATE_KEYS = {
    "provider", "resource_id", "action", "state", "observed_at", "evidence_hash",
    "authorization_state", "provider_url", "deadline", "exact_act",
}
_ACT_KEYS = {"instruction", "control", "expected_result"}


def _text(name: str, value: Any, maximum: int = 300) -> str:
    if not isinstance(value, str):
        raise ValueError(f"invalid_{name}")
    text = value.strip()
    if not text or len(text) > maximum or "\x00" in text:
        raise ValueError(f"invalid_{name}")
    return text


def _hash(name: str, value: Any) -> str:
    text = _text(name, value, 64)
    if not _HEX_64.fullmatch(text):
        raise ValueError(f"invalid_{name}")
    return text


def _time(name: str, value: Any) -> tuple[str, datetime]:
    text = _text(name, value, 40)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"invalid_{name}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"invalid_{name}")
    return text, parsed


def _connect(database: Path) -> sqlite3.Connection:
    database.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database, timeout=5, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout=5000")
    connection.execute("PRAGMA journal_mode=WAL")
    connection.executescript(_SCHEMA)
    return connection


def _record(row: sqlite3.Row) -> CeremonyRecord:
    return CeremonyRecord(
        ceremony_id=row["ceremony_id"], kind=CeremonyKind(row["kind"]),
        provider=row["provider"], resource_id=row["resource_id"], action=row["action"],
        status=row["status"], provider_url=row["provider_url"],
        instruction=row["instruction"], control=row["control"],
        expected_result=row["expected_result"], deadline=row["deadline"],
        resume_kind=row["resume_kind"], completion_hash=row["completion_hash"],
    )


def _parse_request(
    kind: Any, provider_state: Any, resume_predicate: Any,
) -> tuple[CeremonyKind, dict[str, str], dict[str, str]]:
    try:
        ceremony_kind = CeremonyKind(kind)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid_ceremony_kind") from exc
    if not isinstance(provider_state, dict) or set(provider_state) != _STATE_KEYS:
        raise ValueError("invalid_provider_state")
    if not isinstance(provider_state["exact_act"], dict) or set(provider_state["exact_act"]) != _ACT_KEYS:
        raise ValueError("invalid_exact_act")
    act = {
        "instruction": _text("exact_act_instruction", provider_state["exact_act"]["instruction"], 500),
        "control": _text("exact_act_control", provider_state["exact_act"]["control"], 120),
        "expected_result": _text("exact_act_expected_result", provider_state["exact_act"]["expected_result"], 300),
    }
    if len(act["instruction"]) < 12 or len(act["expected_result"]) < 8:
        raise ValueError("invalid_exact_act")
    authorization = _text("authorization_state", provider_state["authorization_state"], 40)
    if authorization in {"approved_api", "approved_browser"}:
        raise CeremonyRejected("agent_executable")
    if authorization != "approved_assisted":
        raise CeremonyRejected("authorization_not_assisted")
    provider_url = _text("provider_url", provider_state["provider_url"], 1000)
    parsed_url = urlsplit(provider_url)
    if (
        parsed_url.scheme != "https" or not parsed_url.netloc or parsed_url.username
        or parsed_url.password or parsed_url.fragment
    ):
        raise ValueError("invalid_provider_url")
    observed_text, observed = _time("observed_at", provider_state["observed_at"])
    deadline_text, deadline = _time("deadline", provider_state["deadline"])
    if deadline <= observed:
        raise ValueError("invalid_deadline")
    state = {
        "provider": _text("provider", provider_state["provider"], 80),
        "resource_id": _text("resource_id", provider_state["resource_id"], 200),
        "action": _text("action", provider_state["action"], 100),
        "state": _text("state", provider_state["state"], 100),
        "observed_at": observed_text,
        "evidence_hash": _hash("evidence_hash", provider_state["evidence_hash"]),
        "provider_url": provider_url,
        "deadline": deadline_text,
        **act,
    }
    if not isinstance(resume_predicate, dict):
        raise ValueError("invalid_resume_predicate")
    resume_kind = resume_predicate.get("kind")
    if resume_kind == "provider_state_changed" and set(resume_predicate) == {"kind", "expected_state"}:
        predicate = {
            "kind": resume_kind,
            "expected_state": _text("resume_predicate_expected_state", resume_predicate["expected_state"], 100),
            "artifact_kind": "",
        }
    elif resume_kind == "artifact_hash" and set(resume_predicate) == {"kind", "artifact_kind"}:
        predicate = {
            "kind": resume_kind,
            "expected_state": "",
            "artifact_kind": _text("resume_predicate_artifact_kind", resume_predicate["artifact_kind"], 100),
        }
    else:
        raise ValueError("invalid_resume_predicate")
    return ceremony_kind, state, predicate


def request_ceremony(
    kind: str, provider_state: dict[str, object], resume_predicate: dict[str, str],
    *, database: Path | None = None,
) -> CeremonyRecord:
    ceremony_kind, state, predicate = _parse_request(kind, provider_state, resume_predicate)
    canonical = json.dumps(
        [ceremony_kind.value, state, predicate], sort_keys=True, separators=(",", ":")
    )
    request_key = hashlib.sha256(canonical.encode()).hexdigest()
    with closing(_connect(Path(database or DEFAULT_DATABASE))) as connection:
        connection.execute("BEGIN IMMEDIATE")
        existing = connection.execute(
            "SELECT * FROM human_ceremonies WHERE request_key=?", (request_key,)
        ).fetchone()
        if existing is None:
            cursor = connection.execute(
                """INSERT INTO human_ceremonies(
                       request_key,kind,provider,resource_id,action,status,provider_url,
                       instruction,control,expected_result,deadline,initial_state,
                       initial_observed_at,initial_evidence_hash,resume_kind,
                       expected_state,artifact_kind
                   ) VALUES(?,?,?,?,?,'pending',?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    request_key, ceremony_kind.value, state["provider"], state["resource_id"],
                    state["action"], state["provider_url"], state["instruction"], state["control"],
                    state["expected_result"], state["deadline"], state["state"],
                    state["observed_at"], state["evidence_hash"], predicate["kind"],
                    predicate["expected_state"] or None, predicate["artifact_kind"] or None,
                ),
            )
            existing = connection.execute(
                "SELECT * FROM human_ceremonies WHERE ceremony_id=?", (cursor.lastrowid,)
            ).fetchone()
        connection.commit()
        return _record(existing)


def provider_runnable(provider: str, *, database: Path | None = None) -> bool:
    provider = _text("provider", provider, 80)
    with closing(_connect(Path(database or DEFAULT_DATABASE))) as connection:
        return connection.execute(
            "SELECT 1 FROM human_ceremonies WHERE provider=? AND status='pending' LIMIT 1",
            (provider,),
        ).fetchone() is None


def complete_ceremony(
    ceremony_id: int, evidence: ProviderState | dict[str, object],
    *, database: Path | None = None,
) -> CeremonyRecord:
    if isinstance(ceremony_id, bool) or not isinstance(ceremony_id, int) or ceremony_id <= 0:
        raise ValueError("invalid_ceremony_id")
    with closing(_connect(Path(database or DEFAULT_DATABASE))) as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT * FROM human_ceremonies WHERE ceremony_id=?", (ceremony_id,)
        ).fetchone()
        if row is None:
            connection.rollback()
            raise KeyError(ceremony_id)
        if row["status"] == "completed":
            connection.commit()
            return _record(row)
        if row["resume_kind"] == "provider_state_changed":
            if not isinstance(evidence, ProviderState):
                connection.rollback()
                raise ValueError("invalid_provider_completion_evidence")
            identity = (evidence.provider, evidence.resource_id, evidence.action)
            if identity != (row["provider"], row["resource_id"], row["action"]):
                connection.rollback()
                raise CeremonyRejected("provider_state_identity_mismatch")
            state = evidence.state
            if state == row["initial_state"] or state != row["expected_state"]:
                connection.rollback()
                raise CeremonyRejected("provider_state_not_changed")
            observed_text, observed = _time("observed_at", evidence.observed_at)
            _, initial_observed = _time("initial_observed_at", row["initial_observed_at"])
            completion_hash = evidence.evidence_hash
            if observed <= initial_observed or completion_hash == row["initial_evidence_hash"]:
                connection.rollback()
                raise CeremonyRejected("stale_provider_evidence")
        else:
            if not isinstance(evidence, dict) or set(evidence) != {
                "artifact_kind", "artifact_hash", "observed_at"
            }:
                connection.rollback()
                raise ValueError("invalid_artifact_completion_evidence")
            if _text("artifact_kind", evidence["artifact_kind"], 100) != row["artifact_kind"]:
                connection.rollback()
                raise CeremonyRejected("artifact_kind_mismatch")
            completion_hash = _hash("artifact_hash", evidence["artifact_hash"])
            observed_text, observed = _time("observed_at", evidence["observed_at"])
            _, initial_observed = _time("initial_observed_at", row["initial_observed_at"])
            if observed <= initial_observed:
                connection.rollback()
                raise CeremonyRejected("stale_artifact_evidence")
        connection.execute(
            """UPDATE human_ceremonies
               SET status='completed',completion_hash=?,completion_observed_at=?
               WHERE ceremony_id=? AND status='pending'""",
            (completion_hash, observed_text, ceremony_id),
        )
        completed = connection.execute(
            "SELECT * FROM human_ceremonies WHERE ceremony_id=?", (ceremony_id,)
        ).fetchone()
        connection.commit()
        return _record(completed)
