"""Contract tests for the durable provider-neutral Market Factory stage gate."""

from __future__ import annotations

import importlib.util
import sqlite3
import sys
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "market_factory.py"


def _load_module():
    name = "gig_market_factory_test"
    spec = importlib.util.spec_from_file_location(name, MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


market_factory = _load_module()


def _evidence(stage: str, marker: str, **extra: object) -> dict[str, object]:
    return {
        "stage": stage,
        "evidence_hash": marker * 64,
        "observed_at": 1_800_000_000 + ord(marker),
        **extra,
    }


@pytest.fixture
def database(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    path = tmp_path / "connector-outbox.sqlite3"
    monkeypatch.setattr(market_factory, "DEFAULT_DATABASE", path)
    return path


def test_first_research_is_durable_and_exact_replay_is_idempotent(database: Path):
    evidence = _evidence("research", "a")

    assert market_factory.advance_market("upwork", evidence) is market_factory.MarketStage.RESEARCH
    assert market_factory.advance_market("upwork", evidence) is market_factory.MarketStage.RESEARCH

    with sqlite3.connect(database) as connection:
        state = connection.execute(
            "SELECT stage,evidence_hash FROM market_factory_state WHERE provider='upwork'"
        ).fetchone()
        history_count = connection.execute(
            "SELECT COUNT(*) FROM market_factory_evidence WHERE provider='upwork'"
        ).fetchone()[0]
    assert state == ("research", "a" * 64)
    assert history_count == 1


def test_direct_research_to_sale_is_rejected_without_changing_state(database: Path):
    market_factory.advance_market("upwork", _evidence("research", "a"))

    with pytest.raises(market_factory.InvalidMarketTransition, match="research_to_sale"):
        market_factory.advance_market("upwork", _evidence("sale", "b"))

    assert market_factory.current_market("upwork").stage is market_factory.MarketStage.RESEARCH


def test_payment_requires_delivery(database: Path):
    for stage, marker in (("research", "a"), ("authorized", "b"), ("read", "c")):
        market_factory.advance_market("upwork", _evidence(stage, marker))

    with pytest.raises(market_factory.InvalidMarketTransition, match="read_to_payment"):
        market_factory.advance_market(
            "upwork", _evidence("payment", "d", payment_id="payment-1")
        )


def test_active_requires_three_independent_payments(database: Path):
    stages = (
        ("research", "a"),
        ("authorized", "b"),
        ("read", "c"),
        ("sale", "d"),
        ("contract", "e"),
        ("delivery", "f"),
    )
    for stage, marker in stages:
        market_factory.advance_market("upwork", _evidence(stage, marker))
    market_factory.advance_market(
        "upwork", _evidence("payment", "1", payment_id="payment-1")
    )

    with pytest.raises(market_factory.InvalidMarketTransition, match="three_independent_payments"):
        market_factory.advance_market("upwork", _evidence("active", "2"))
    with pytest.raises(market_factory.InvalidMarketTransition, match="three_independent_payments"):
        market_factory.advance_market("upwork", _evidence("repeatable", "2"))

    second = _evidence("payment", "2", payment_id="payment-2")
    assert market_factory.advance_market("upwork", second) is market_factory.MarketStage.PAYMENT
    assert market_factory.advance_market("upwork", second) is market_factory.MarketStage.PAYMENT
    market_factory.advance_market(
        "upwork", _evidence("payment", "3", payment_id="payment-3")
    )
    assert market_factory.advance_market(
        "upwork", _evidence("repeatable", "4")
    ) is market_factory.MarketStage.REPEATABLE
    assert market_factory.advance_market(
        "upwork", _evidence("active", "5")
    ) is market_factory.MarketStage.ACTIVE

    assert market_factory.current_market("upwork").independent_payments == 3


def test_regression_requires_explicit_reverted_control(database: Path):
    for stage, marker in (("research", "a"), ("authorized", "b"), ("read", "c")):
        market_factory.advance_market("fiverr", _evidence(stage, marker))

    with pytest.raises(market_factory.InvalidMarketTransition, match="read_to_authorized"):
        market_factory.advance_market("fiverr", _evidence("authorized", "d"))

    assert market_factory.advance_market(
        "fiverr", _evidence("paused", "e")
    ) is market_factory.MarketStage.READ
    assert market_factory.advance_market(
        "fiverr", _evidence("reverted", "f", revert_to="authorized")
    ) is market_factory.MarketStage.AUTHORIZED


def test_terminal_disposition_cannot_be_reclassified_without_revert(database: Path):
    market_factory.advance_market("telus", _evidence("research", "a"))
    market_factory.advance_market("telus", _evidence("denied", "b"))

    with pytest.raises(market_factory.InvalidMarketTransition, match="denied_to_unprofitable"):
        market_factory.advance_market("telus", _evidence("unprofitable", "c"))


def test_declared_disposition_stages_exist():
    assert {stage.value for stage in market_factory.MarketStage} == {
        "research", "authorized", "read", "sale", "contract", "delivery", "payment",
        "repeatable", "active", "assisted", "denied", "unprofitable",
    }
