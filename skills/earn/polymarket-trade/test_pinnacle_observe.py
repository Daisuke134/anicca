#!/usr/bin/env python3
"""Tests for pinnacle_observe.py -- the OBSERVATION-ONLY wrapper run.sh calls each pass.

NEVER touches the network -- every fetch is injected (same convention as test_pinnacle_edge.py).
Ground truth for what these tests guard: docs/loop-engineering/30-pinnacle-edge-measurement.md
found 0 comparable games in the first live measurement -- so "0 comparable" MUST still produce a
logged line (that absence is itself the data point), and betting must stay switched off until
PINNACLE_LIVE exists as a real, separate feature.

Run: python3 -m pytest test_pinnacle_observe.py -q
"""
import json
from pathlib import Path

import pytest

import pinnacle_edge as pe
import pinnacle_observe as po

FUTURE = "2099-01-01T00:00:00Z"
import datetime
FUTURE_TS = datetime.datetime(2098, 12, 31, tzinfo=datetime.timezone.utc).timestamp()


def pin_event(home, away, home_price, away_price, commence=FUTURE):
    return {
        "home_team": home, "away_team": away,
        "sport_key": "baseball_mlb", "commence_time": commence,
        "bookmakers": [{
            "key": "pinnacle",
            "markets": [{"key": "h2h", "outcomes": [
                {"name": home, "price": home_price},
                {"name": away, "price": away_price},
            ]}],
        }],
    }


def pm_market(question, outcomes, prices, game_start=FUTURE):
    return {
        "question": question, "enableOrderBook": True,
        "conditionId": "0xabc", "clobTokenIds": '["1","2"]',
        "outcomes": json.dumps(outcomes), "outcomePrices": json.dumps([str(p) for p in prices]),
        "gameStartTime": game_start,
    }


def fake_pm(markets):
    def fetch_pm():
        return markets
    return fetch_pm


def fake_pin_budgeted(events, cached=False):
    def fetch_pin_budgeted(sports, api_key, now_ts):
        return events, cached
    return fetch_pin_budgeted


@pytest.fixture
def obs_path(tmp_path, monkeypatch):
    p = tmp_path / "pinnacle-observations.jsonl"
    monkeypatch.setattr(po, "OBSERVATIONS_PATH", str(p))
    return p


def _read_lines(path):
    if not Path(path).exists():
        return []
    return [json.loads(ln) for ln in Path(path).read_text().splitlines() if ln.strip()]


# ---- 0 comparable games must still be logged (this IS the finding) --------
def test_zero_comparable_games_still_writes_one_line(obs_path):
    obs = po.observe(
        "FAKEKEY", now_ts=FUTURE_TS,
        fetch_pm=fake_pm([]), fetch_pin_budgeted=fake_pin_budgeted([]),
    )
    po.append_observation(obs, path=str(obs_path))

    lines = _read_lines(obs_path)
    assert len(lines) == 1
    rec = lines[0]
    assert "ts" in rec
    assert rec["funnel"]["pinnacle_events"] == 0
    assert rec["funnel"]["pinnacle_prematch"] == 0
    assert rec["funnel"]["pm_markets"] == 0
    assert rec["funnel"]["matched"] == 0
    assert rec["funnel"]["comparable"] == 0
    assert rec["edges"] == []
    assert rec["odds_from_cache"] is False


# ---- a real edge is found -> it lands in the jsonl -------------------------
def test_a_found_edge_is_written_to_jsonl(obs_path):
    pin = [pin_event("Cincinnati Reds", "Chicago Cubs", 310, -410)]
    pm = [pm_market("Chicago Cubs vs. Cincinnati Reds",
                    ["Chicago Cubs", "Cincinnati Reds"], [0.855, 0.145])]

    obs = po.observe(
        "FAKEKEY", now_ts=FUTURE_TS,
        fetch_pm=fake_pm(pm), fetch_pin_budgeted=fake_pin_budgeted(pin),
    )
    po.append_observation(obs, path=str(obs_path))

    lines = _read_lines(obs_path)
    assert len(lines) == 1
    rec = lines[0]
    assert rec["funnel"]["matched"] == 1
    assert rec["funnel"]["comparable"] == 1
    assert len(rec["edges"]) == 1
    assert rec["edges"][0]["buy_outcome"] == "Cincinnati Reds"


# ---- no ODDS_API_KEY -> silent skip, no crash, no jsonl line --------------
def test_missing_api_key_skips_silently(obs_path, monkeypatch):
    monkeypatch.delenv("ODDS_API_KEY", raising=False)
    monkeypatch.setattr(po, "resolve_odds_api_key", lambda: None)

    rc = po.main()

    assert rc == 0
    assert not Path(obs_path).exists() or _read_lines(obs_path) == []


# ---- pinnacle_edge raising an exception must not crash the pass -----------
def test_fetch_exception_is_fail_soft_not_a_crash(obs_path):
    def boom_pm():
        raise RuntimeError("gamma 500")

    obs = po.observe(
        "FAKEKEY", now_ts=FUTURE_TS,
        fetch_pm=boom_pm, fetch_pin_budgeted=fake_pin_budgeted([]),
    )
    # must return a dict, never raise
    assert isinstance(obs, dict)
    assert obs["funnel"]["pinnacle_events"] == 0
    assert obs["edges"] == []

    # and main() end-to-end must also survive an exception and still exit 0
    po.append_observation(obs, path=str(obs_path))
    lines = _read_lines(obs_path)
    assert len(lines) == 1
    assert "error" in lines[0]


def test_main_end_to_end_survives_exception(obs_path, monkeypatch):
    monkeypatch.setattr(po, "resolve_odds_api_key", lambda: "FAKEKEY")

    def boom_pin_budgeted(sports, api_key, now_ts):
        raise RuntimeError("odds api 500")

    monkeypatch.setattr(pe, "fetch_polymarket_sports", lambda: [])
    monkeypatch.setattr(pe, "fetch_pinnacle_budgeted", boom_pin_budgeted)

    rc = po.main()

    assert rc == 0
    lines = _read_lines(obs_path)
    assert len(lines) == 1
    assert "error" in lines[0]


# ---- ODDS_API_KEY present -> main() fetches (via pe defaults) and writes --
def test_main_writes_a_line_when_key_present(obs_path, monkeypatch):
    monkeypatch.setattr(po, "resolve_odds_api_key", lambda: "FAKEKEY")
    monkeypatch.setattr(pe, "fetch_polymarket_sports", lambda: [])
    monkeypatch.setattr(
        pe, "fetch_pinnacle_budgeted", lambda sports, api_key, now_ts: ([], False)
    )

    rc = po.main()

    assert rc == 0
    lines = _read_lines(obs_path)
    assert len(lines) == 1


# ---- HARD constraint: this module never places an order --------------------
def test_never_imports_or_calls_order_placement():
    # AST-based, not substring: the module's own docstring explains, in English, that it does
    # NOT import place_order.py -- a naive substring search would (and, first try, did) false-
    # positive on that prose. Parsing real import/call statements ignores docstrings/comments
    # entirely and only fails on an ACTUAL `import place_order` or a real order-placing call.
    import ast

    src = Path(po.__file__).read_text()
    tree = ast.parse(src)

    imported_modules = set()
    called_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                called_names.add(func.id)
            elif isinstance(func, ast.Attribute):
                called_names.add(func.attr)

    forbidden_modules = {"place_order", "bundle_arb", "market_maker"}
    forbidden_calls = {"place_order", "post_order", "create_order", "submit_order"}

    bad_imports = imported_modules & forbidden_modules
    bad_calls = called_names & forbidden_calls
    assert not bad_imports, f"pinnacle_observe.py must never import: {bad_imports}"
    assert not bad_calls, f"pinnacle_observe.py must never call: {bad_calls}"
    assert not hasattr(po, "place_order")
