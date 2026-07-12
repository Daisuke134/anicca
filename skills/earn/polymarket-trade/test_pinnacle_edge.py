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


# ---- gate 1: in-play / settled games are incomparable ---------------------
NOW = datetime.datetime(2026, 7, 12, 1, 37, tzinfo=datetime.timezone.utc).timestamp()


def test_a_game_already_underway_is_not_prematch():
    assert is_prematch("2026-07-12T01:27:00Z", NOW) is False   # started 10 min ago


def test_a_game_starting_within_the_lead_buffer_is_not_prematch():
    assert is_prematch("2026-07-12T01:40:00Z", NOW) is False    # 3 min out, inside the 600s buffer


def test_a_game_comfortably_in_the_future_is_prematch():
    assert is_prematch("2026-07-12T16:16:00Z", NOW) is True


def test_an_unparseable_commence_time_fails_closed():
    assert is_prematch("not a time", NOW) is False
    assert is_prematch("", NOW) is False


def test_the_mckinney_trap_is_not_reported_as_an_edge():
    # the exact shape of the first live run's +97,147%: settled game, stale line, price at ~0
    pin = [pin_event("King Green", "Terrance McKinney", 100, -100,
                     commence="2026-07-12T01:27:00Z")]
    pm = [pm_market("UFC 329: King Green vs. Terrance McKinney",
                    ["King Green", "Terrance McKinney"], [0.9995, 0.0005])]
    assert find_edges(pin, pm, min_edge=0.03, now_ts=NOW) == []


# ---- gate 2: an enormous "edge" is bad data, not opportunity --------------
def test_an_absurd_edge_is_rejected_even_when_the_game_is_prematch():
    # 50pt apart on two liquid, professionally-watched markets means the rows disagree about
    # reality (stale line, bad match), not that free money is sitting there
    pin = [pin_event("Team A", "Team B", 100, -100)]           # ~50/50 no-vig
    pm = [pm_market("Team B vs. Team A", ["Team A", "Team B"], [0.99, 0.01])]
    assert find_edges(pin, pm, min_edge=0.03, max_edge=0.30, now_ts=FUTURE_TS) == []


def test_raising_max_edge_lets_the_same_outlier_through():
    # proves the rejection above comes from max_edge and not from some unrelated filter
    pin = [pin_event("Team A", "Team B", 100, -100)]
    pm = [pm_market("Team B vs. Team A", ["Team A", "Team B"], [0.99, 0.01])]
    assert len(find_edges(pin, pm, min_edge=0.03, max_edge=0.99, now_ts=FUTURE_TS)) == 1
