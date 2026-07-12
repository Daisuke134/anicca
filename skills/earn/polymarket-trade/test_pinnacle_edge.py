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


from pinnacle_edge import fetch_polymarket_sports


def fake_gamma(pages):
    """pages: list of lists of markets, served in order. Records the URLs requested."""
    calls = []

    def fetch(url, timeout=25):
        calls.append(url)
        i = len(calls) - 1
        if i >= len(pages):
            return []
        page = pages[i]
        if isinstance(page, Exception):
            raise page
        return page

    fetch.calls = calls
    return fetch


def mkt(cid):
    return {"conditionId": cid, "question": f"q{cid}", "enableOrderBook": True}


def test_pagination_walks_offsets_and_concatenates():
    fetch = fake_gamma([[mkt("a"), mkt("b")], [mkt("c")], []])
    out = fetch_polymarket_sports(pages=3, fetch=fetch)
    assert [m["conditionId"] for m in out] == ["a", "b", "c"]
    assert "offset=0" in fetch.calls[0]
    assert "offset=100" in fetch.calls[1]


def test_duplicate_markets_across_pages_are_deduped():
    fetch = fake_gamma([[mkt("a"), mkt("b")], [mkt("b"), mkt("c")]])
    out = fetch_polymarket_sports(pages=2, fetch=fetch)
    assert [m["conditionId"] for m in out] == ["a", "b", "c"]


def test_an_empty_page_stops_the_walk_early():
    fetch = fake_gamma([[mkt("a")], [], [mkt("never")]])
    out = fetch_polymarket_sports(pages=3, fetch=fetch)
    assert [m["conditionId"] for m in out] == ["a"]
    assert len(fetch.calls) == 2


def test_a_failing_page_keeps_the_pages_that_did_load():
    fetch = fake_gamma([[mkt("a")], RuntimeError("gamma 503"), [mkt("c")]])
    out = fetch_polymarket_sports(pages=3, fetch=fetch)
    assert [m["conditionId"] for m in out] == ["a"], "one bad page must not lose the good ones"


import pinnacle_edge


@pytest.fixture
def tmp_cache(tmp_path, monkeypatch):
    p = tmp_path / "pinnacle-cache.json"
    monkeypatch.setattr(pinnacle_edge, "CACHE_PATH", str(p))
    return p


def counting_odds_fetch(events):
    calls = []

    def fetch(url, timeout=25):
        calls.append(url)
        return events

    fetch.calls = calls
    return fetch


def test_first_scan_spends_credits_once_per_sport(tmp_cache):
    fetch = counting_odds_fetch([pin_event("H", "A", -110, -110)])
    events, cached = pinnacle_edge.fetch_pinnacle_budgeted(
        ["baseball_mlb", "mma_mixed_martial_arts"], "KEY", now_ts=1000.0, fetch=fetch
    )
    assert cached is False
    assert len(fetch.calls) == 2, "one credit per sport, no more"
    assert len(events) == 2


def test_a_second_scan_inside_the_interval_spends_nothing(tmp_cache):
    first = counting_odds_fetch([pin_event("H", "A", -110, -110)])
    pinnacle_edge.fetch_pinnacle_budgeted(["baseball_mlb"], "KEY", now_ts=1000.0, fetch=first)

    second = counting_odds_fetch([pin_event("SHOULD", "NOT", -110, -110)])
    events, cached = pinnacle_edge.fetch_pinnacle_budgeted(
        ["baseball_mlb"], "KEY", now_ts=1000.0 + 60, fetch=second
    )
    assert cached is True
    assert second.calls == [], "inside the interval the paid API must not be touched at all"
    assert events[0]["home_team"] == "H", "the cached lines are served unchanged"


def test_once_the_interval_has_passed_credits_are_spent_again(tmp_cache):
    first = counting_odds_fetch([pin_event("OLD", "A", -110, -110)])
    pinnacle_edge.fetch_pinnacle_budgeted(["baseball_mlb"], "KEY", now_ts=1000.0, fetch=first)

    later = 1000.0 + pinnacle_edge.MIN_FETCH_INTERVAL_S + 1
    second = counting_odds_fetch([pin_event("NEW", "A", -110, -110)])
    events, cached = pinnacle_edge.fetch_pinnacle_budgeted(
        ["baseball_mlb"], "KEY", now_ts=later, fetch=second
    )
    assert cached is False
    assert len(second.calls) == 1
    assert events[0]["home_team"] == "NEW"


def test_one_dead_sport_does_not_kill_the_whole_scan(tmp_cache):
    calls = []

    def fetch(url, timeout=25):
        calls.append(url)
        if "mma" in url:
            raise RuntimeError("odds api 500")
        return [pin_event("H", "A", -110, -110)]

    events, cached = pinnacle_edge.fetch_pinnacle_budgeted(
        ["baseball_mlb", "mma_mixed_martial_arts"], "KEY", now_ts=1000.0, fetch=fetch
    )
    assert len(calls) == 2
    assert len(events) == 1, "the sport that answered must still be scanned"
