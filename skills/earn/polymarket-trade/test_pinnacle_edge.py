#!/usr/bin/env python3
"""Pure-logic tests for pinnacle_edge.py. NEVER touches the network — every fetch is injected.

Run: python3 -m pytest test_pinnacle_edge.py -q     (or: python3 test_pinnacle_edge.py)
"""
import datetime
import json

import pytest

from pinnacle_edge import (
    american_to_prob,
    fair_probs_from_outcomes,
    remove_vig,
)


# ---- odds arithmetic ------------------------------------------------------
def test_american_to_prob_favourite_and_underdog():
    # -410 / +310 is a real Pinnacle line (Cubs @ Reds, 2026-07-12)
    assert american_to_prob(-410) == pytest.approx(410 / 510, abs=1e-9)
    assert american_to_prob(310) == pytest.approx(100 / 410, abs=1e-9)


def test_american_odds_of_zero_is_rejected_not_silently_wrong():
    with pytest.raises(ValueError):
        american_to_prob(0)


def test_remove_vig_normalises_to_exactly_one():
    # a two-way book line implies >100%; the excess is the book's cut, not belief
    raw = [american_to_prob(-410), american_to_prob(310)]
    assert sum(raw) > 1.0
    fair = remove_vig(raw)
    assert sum(fair) == pytest.approx(1.0, abs=1e-12)


def test_remove_vig_preserves_the_ratio_between_sides():
    fair = remove_vig([0.6, 0.6])
    assert fair == pytest.approx([0.5, 0.5])


def test_fair_probs_needs_two_sides_to_mean_anything():
    with pytest.raises(ValueError):
        fair_probs_from_outcomes([{"name": "Solo", "price": -200}])


def test_fair_probs_maps_names_to_no_vig_probabilities():
    fair = fair_probs_from_outcomes(
        [{"name": "Chicago Cubs", "price": -410}, {"name": "Cincinnati Reds", "price": 310}]
    )
    assert sum(fair.values()) == pytest.approx(1.0, abs=1e-12)
    assert fair["Chicago Cubs"] > fair["Cincinnati Reds"]
    assert fair["Chicago Cubs"] == pytest.approx(0.767, abs=0.001)


from pinnacle_edge import find_edges, is_prematch, match_market, polymarket_prices

FUTURE = "2099-01-01T00:00:00Z"
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


def pm_market(question, outcomes, prices):
    return {
        "question": question, "enableOrderBook": True,
        "conditionId": "0xabc", "clobTokenIds": '["1","2"]',
        "outcomes": json.dumps(outcomes), "outcomePrices": json.dumps([str(p) for p in prices]),
    }


# ---- THE regression test: a qualifying edge must actually come back -------
def test_a_qualifying_edge_is_actually_returned():
    # Pinnacle no-vig: Reds ~23.3%. Polymarket prices them at 14.5% -> ~8.8pt underpriced.
    pin = [pin_event("Cincinnati Reds", "Chicago Cubs", 310, -410)]
    pm = [pm_market("Chicago Cubs vs. Cincinnati Reds",
                    ["Chicago Cubs", "Cincinnati Reds"], [0.855, 0.145])]

    edges = find_edges(pin, pm, min_edge=0.03, now_ts=FUTURE_TS)

    assert len(edges) == 1, "a qualifying edge must be RETURNED, not merely computed"
    e = edges[0]
    assert e["buy_outcome"] == "Cincinnati Reds"
    assert e["pm_price"] == pytest.approx(0.145)
    assert e["pinnacle_fair"] == pytest.approx(0.233, abs=0.002)
    assert e["edge"] == pytest.approx(0.088, abs=0.002)


def test_an_edge_below_the_threshold_is_not_an_opportunity():
    # the real McGregor/Holloway state: Pinnacle 27.1% vs Polymarket 27.5% -- 0.4pt, i.e. noise
    pin = [pin_event("Max Holloway", "Conor McGregor", -269, 269)]
    pm = [pm_market("Max Holloway vs. Conor McGregor",
                    ["Max Holloway", "Conor McGregor"], [0.725, 0.275])]
    assert find_edges(pin, pm, min_edge=0.03, now_ts=FUTURE_TS) == []
