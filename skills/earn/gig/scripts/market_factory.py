#!/usr/bin/env python3
"""Durable stage gate shared by every Gig marketplace adapter."""

from __future__ import annotations

import re
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any


DEFAULT_DATABASE = Path.home() / "gig" / "connector-outbox.sqlite3"
_HEX_64 = re.compile(r"[0-9a-f]{64}")


class InvalidMarketTransition(ValueError):
    """Evidence requested a stage change that the durable gate does not allow."""


class MarketStage(StrEnum):
    RESEARCH = "research"
    AUTHORIZED = "authorized"
    READ = "read"
    SALE = "sale"
    CONTRACT = "contract"
    DELIVERY = "delivery"
    PAYMENT = "payment"
    REPEATABLE = "repeatable"
    ACTIVE = "active"
    ASSISTED = "assisted"
    DENIED = "denied"
    UNPROFITABLE = "unprofitable"


_PROGRESSION = (
    MarketStage.RESEARCH,
    MarketStage.AUTHORIZED,
    MarketStage.READ,
    MarketStage.SALE,
    MarketStage.CONTRACT,
    MarketStage.DELIVERY,
    MarketStage.PAYMENT,
    MarketStage.REPEATABLE,
    MarketStage.ACTIVE,
)
_DISPOSITIONS = frozenset({
    MarketStage.ASSISTED,
    MarketStage.DENIED,
    MarketStage.UNPROFITABLE,
})
_CONTROLS = frozenset({"paused", "reverted"})


@dataclass(frozen=True)
class MarketState:
    provider: str
    stage: MarketStage
    evidence_hash: str
    independent_payments: int
    updated_at: int


_SCHEMA = """
CREATE TABLE IF NOT EXISTS market_factory_state (
    provider TEXT PRIMARY KEY,
    stage TEXT NOT NULL,
    evidence_hash TEXT NOT NULL CHECK (length(evidence_hash) = 64),
    independent_payments INTEGER NOT NULL DEFAULT 0
        CHECK (independent_payments >= 0),
    updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS market_factory_evidence (
    provider TEXT NOT NULL,
    evidence_hash TEXT NOT NULL CHECK (length(evidence_hash) = 64),
    event TEXT NOT NULL,
    resulting_stage TEXT NOT NULL,
    payment_id TEXT,
    observed_at INTEGER NOT NULL,
    PRIMARY KEY(provider, evidence_hash),
    UNIQUE(provider, payment_id)
);
"""


def _text(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"invalid_{name}")
    return value.strip()


def _parse_evidence(evidence: Any) -> tuple[str, str, int, str | None, str | None]:
    if not isinstance(evidence, dict):
        raise ValueError("invalid_evidence")
    allowed = {"stage", "evidence_hash", "observed_at", "payment_id", "revert_to"}
    if set(evidence) - allowed or not {"stage", "evidence_hash", "observed_at"} <= set(evidence):
        raise ValueError("invalid_evidence_keys")
    event = _text("stage", evidence["stage"])
    if event not in {stage.value for stage in MarketStage} | _CONTROLS:
        raise ValueError("invalid_stage")
    evidence_hash = _text("evidence_hash", evidence["evidence_hash"])
    if not _HEX_64.fullmatch(evidence_hash):
        raise ValueError("invalid_evidence_hash")
    observed_at = evidence["observed_at"]
    if isinstance(observed_at, bool) or not isinstance(observed_at, int) or observed_at < 0:
        raise ValueError("invalid_observed_at")
    payment_id = evidence.get("payment_id")
    revert_to = evidence.get("revert_to")
    if payment_id is not None:
        payment_id = _text("payment_id", payment_id)
    if revert_to is not None:
        revert_to = _text("revert_to", revert_to)
    if event == MarketStage.PAYMENT.value and payment_id is None:
        raise ValueError("payment_id_required")
    if event != MarketStage.PAYMENT.value and payment_id is not None:
        raise ValueError("payment_id_only_for_payment")
    if (event == "reverted") != (revert_to is not None):
        raise ValueError("revert_to_only_for_reverted")
    return event, evidence_hash, observed_at, payment_id, revert_to


def _connect(database: Path) -> sqlite3.Connection:
    database.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database, timeout=5, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout=5000")
    connection.execute("PRAGMA journal_mode=WAL")
    connection.executescript(_SCHEMA)
    return connection


def _state(row: sqlite3.Row) -> MarketState:
    return MarketState(
        provider=row["provider"],
        stage=MarketStage(row["stage"]),
        evidence_hash=row["evidence_hash"],
        independent_payments=row["independent_payments"],
        updated_at=row["updated_at"],
    )


def current_market(provider: str, *, database: Path | None = None) -> MarketState:
    provider = _text("provider", provider)
    with closing(_connect(Path(database or DEFAULT_DATABASE))) as connection:
        row = connection.execute(
            "SELECT * FROM market_factory_state WHERE provider=?", (provider,)
        ).fetchone()
    if row is None:
        raise KeyError(provider)
    return _state(row)


def advance_market(
    provider: str,
    evidence: dict[str, object],
    *,
    database: Path | None = None,
) -> MarketStage:
    """Apply one evidence-bound stage event and return the resulting stage."""
    provider = _text("provider", provider)
    event, evidence_hash, observed_at, payment_id, revert_to = _parse_evidence(evidence)
    with closing(_connect(Path(database or DEFAULT_DATABASE))) as connection:
        connection.execute("BEGIN IMMEDIATE")
        existing_evidence = connection.execute(
            "SELECT * FROM market_factory_evidence WHERE provider=? AND evidence_hash=?",
            (provider, evidence_hash),
        ).fetchone()
        row = connection.execute(
            "SELECT * FROM market_factory_state WHERE provider=?", (provider,)
        ).fetchone()
        if existing_evidence is not None:
            if row is None:
                connection.rollback()
                raise RuntimeError("market_state_missing_for_evidence")
            connection.commit()
            return MarketStage(row["stage"])

        if row is None:
            if event != MarketStage.RESEARCH.value:
                connection.rollback()
                raise InvalidMarketTransition(f"missing_to_{event}")
            target = MarketStage.RESEARCH
            payment_count = 0
        else:
            current = MarketStage(row["stage"])
            payment_count = int(row["independent_payments"])
            if event == "paused":
                target = current
            elif event == "reverted":
                try:
                    target = MarketStage(revert_to)
                except ValueError as exc:
                    connection.rollback()
                    raise InvalidMarketTransition("invalid_revert_target") from exc
                was_observed = connection.execute(
                    """SELECT 1 FROM market_factory_evidence
                       WHERE provider=? AND resulting_stage=? LIMIT 1""",
                    (provider, target.value),
                ).fetchone()
                if target not in _PROGRESSION or was_observed is None:
                    connection.rollback()
                    raise InvalidMarketTransition("unobserved_revert_target")
            else:
                target = MarketStage(event)
                if current in _DISPOSITIONS:
                    connection.rollback()
                    raise InvalidMarketTransition(f"{current.value}_to_{target.value}")
                if target in _DISPOSITIONS:
                    pass
                elif target == current:
                    if target is not MarketStage.PAYMENT:
                        connection.rollback()
                        raise InvalidMarketTransition(f"duplicate_{target.value}_with_new_evidence")
                elif target is MarketStage.REPEATABLE and payment_count < 3:
                    connection.rollback()
                    raise InvalidMarketTransition("three_independent_payments_required")
                elif target is MarketStage.ACTIVE and payment_count < 3:
                    connection.rollback()
                    raise InvalidMarketTransition("three_independent_payments_required")
                elif _PROGRESSION.index(target) != _PROGRESSION.index(current) + 1:
                    connection.rollback()
                    raise InvalidMarketTransition(f"{current.value}_to_{target.value}")

            if target is MarketStage.PAYMENT:
                prior_payment = connection.execute(
                    """SELECT evidence_hash FROM market_factory_evidence
                       WHERE provider=? AND payment_id=?""",
                    (provider, payment_id),
                ).fetchone()
                if prior_payment is not None:
                    connection.rollback()
                    raise InvalidMarketTransition("payment_id_reused_with_changed_evidence")
                payment_count += 1

        connection.execute(
            """INSERT INTO market_factory_evidence(
                   provider,evidence_hash,event,resulting_stage,payment_id,observed_at
               ) VALUES(?,?,?,?,?,?)""",
            (provider, evidence_hash, event, target.value, payment_id, observed_at),
        )
        connection.execute(
            """INSERT INTO market_factory_state(
                   provider,stage,evidence_hash,independent_payments,updated_at
               ) VALUES(?,?,?,?,?)
               ON CONFLICT(provider) DO UPDATE SET
                   stage=excluded.stage,
                   evidence_hash=excluded.evidence_hash,
                   independent_payments=excluded.independent_payments,
                   updated_at=excluded.updated_at""",
            (provider, target.value, evidence_hash, payment_count, observed_at),
        )
        connection.commit()
        return target
