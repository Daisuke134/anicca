# Pinnacle Edge Coverage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lock the behaviour of `pinnacle_edge.py` behind tests — above all a regression test for the dead-code bug that made it silently incapable of ever reporting an edge — then measure, on the real APIs, whether a Pinnacle-vs-Polymarket edge actually exists.

**Architecture:** The scanner takes the whole Polymarket board from the free, unmetered Gamma API (paginated, since Gamma silently caps `limit` at 100), then spends The Odds API's metered credits only on the three sports Polymarket demonstrably lists. Two safety gates stand between a raw price difference and a reported opportunity: `is_prematch` (an in-play or settled game makes the two sources incomparable) and `max_edge` (a 30-point "edge" between two liquid, professionally-watched markets is evidence of bad data, not of opportunity). Every failure path yields "no opportunity" rather than a guess.

**Tech Stack:** Python 3, stdlib only (`urllib`, `json`, `datetime`, `difflib`). Tests: pytest, no network — every fetch is injected.

**Spec:** `docs/superpowers/specs/2026-07-12-pinnacle-edge-coverage-design.md`

**Existing conventions (follow them):** tests live flat in the skill dir as `test_*.py`, are bare pytest functions, never touch the network or a wallet, and run with `python3 -m pytest test_x.py -q`. See `test_no_naked.py` for the house style.

---

### Task 1: Lock the odds arithmetic

The no-vig conversion is what turns a bookmaker's *price* into a *probability estimate*. If it is wrong, every edge downstream is wrong, and it will be wrong quietly.

**Files:**
- Create: `/Users/anicca/anicca/skills/earn/polymarket-trade/test_pinnacle_edge.py`
- Under test: `/Users/anicca/anicca/skills/earn/polymarket-trade/pinnacle_edge.py` (already implemented)

- [ ] **Step 1: Write the failing test**

Create the file with exactly this content:

```python
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
```

- [ ] **Step 2: Run the test to verify it passes against the existing implementation**

```bash
cd /Users/anicca/anicca/skills/earn/polymarket-trade
python3 -m pytest test_pinnacle_edge.py -q
```

Expected: `6 passed`. These lock behaviour that already exists — if any FAILS, the arithmetic is wrong and that is the finding; fix `pinnacle_edge.py`, not the test.

- [ ] **Step 3: Commit**

```bash
cd /Users/anicca/anicca
git add skills/earn/polymarket-trade/test_pinnacle_edge.py
git commit -m "test(pinnacle-edge): lock the no-vig arithmetic

A bookmaker's price is not a probability until the vig is removed; every edge
downstream is computed from this, so it fails loudly (ValueError) rather than
quietly on bad input."
```

---

### Task 2: Regression-test the dead-code bug — the most important task here

`find_edges` had `out.append(...)` indented underneath a `continue`, so it was unreachable: the function could not return an edge under any input, and reported "no edge" forever while looking perfectly healthy. Nothing caught it. A test that asserts a qualifying edge is actually **returned** is the one test that would have.

**Files:**
- Modify: `/Users/anicca/anicca/skills/earn/polymarket-trade/test_pinnacle_edge.py`

- [ ] **Step 1: Write the failing test**

Append to `test_pinnacle_edge.py`:

```python
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
```

- [ ] **Step 2: Run it**

```bash
cd /Users/anicca/anicca/skills/earn/polymarket-trade
python3 -m pytest test_pinnacle_edge.py -q
```

Expected: `8 passed`. If `test_a_qualifying_edge_is_actually_returned` FAILS, the dead-code bug is still live — re-check that `out.append(...)` in `find_edges` sits at the same indent level as `edge = fair_p - price`, not inside the `continue` branch.

- [ ] **Step 3: Commit**

```bash
cd /Users/anicca/anicca
git add skills/earn/polymarket-trade/test_pinnacle_edge.py
git commit -m "test(pinnacle-edge): regression-test the dead-code bug

out.append() had been indented under a continue, so find_edges was structurally
incapable of returning an edge -- and reported 'no edge found' forever, looking
healthy the whole time. Asserting that a qualifying edge is actually RETURNED is
the assertion that would have caught it."
```

---

### Task 3: Test the two gates that stop us buying a fake edge

The first live run surfaced a "+97,147% edge": McKinney at a Polymarket price of $0.0005 against a Pinnacle fair value of 48.6%. It was not an edge. The fight had already started, the market had watched him lose and repriced to ~0, while Pinnacle's line still showed the pre-fight number. Buying it loses 100% of the stake, every time.

**Files:**
- Modify: `/Users/anicca/anicca/skills/earn/polymarket-trade/test_pinnacle_edge.py`

- [ ] **Step 1: Write the failing test**

Append:

```python
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
```

- [ ] **Step 2: Run it**

```bash
cd /Users/anicca/anicca/skills/earn/polymarket-trade
python3 -m pytest test_pinnacle_edge.py -q
```

Expected: `15 passed`.

- [ ] **Step 3: Commit**

```bash
cd /Users/anicca/anicca
git add skills/earn/polymarket-trade/test_pinnacle_edge.py
git commit -m "test(pinnacle-edge): pin the two gates that stop us buying a fake edge

Reproduces the +97,147% 'opportunity' the first live run surfaced -- a fight that
had already been lost, priced at 0 by the market while Pinnacle's line still showed
the pre-fight number. Buying it loses the whole stake. Both the pre-match gate and
the outlier gate now have a test that fails if they are removed."
```

---

### Task 4: Test the free-side pagination

Gamma caps `limit` at 100 regardless of what is requested, so a single call was showing only the top 100 markets (34 games) and the scan was matching almost nothing. Paging is free; losing it silently is the failure mode to guard.

**Files:**
- Modify: `/Users/anicca/anicca/skills/earn/polymarket-trade/test_pinnacle_edge.py`

- [ ] **Step 1: Write the failing test**

Append:

```python
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
```

- [ ] **Step 2: Run it**

```bash
cd /Users/anicca/anicca/skills/earn/polymarket-trade
python3 -m pytest test_pinnacle_edge.py -q
```

Expected: `19 passed`.

- [ ] **Step 3: Commit**

```bash
cd /Users/anicca/anicca
git add skills/earn/polymarket-trade/test_pinnacle_edge.py
git commit -m "test(pinnacle-edge): pin Gamma pagination

Gamma silently caps limit at 100, so one call showed the top 100 markets and 34
games while the board actually holds ~500 and ~71. Paging is free and unmetered;
these tests keep it, keep it deduped, and keep a single failing page from taking
the successful ones down with it."
```

---

### Task 5: Test the credit budget guard

The free tier is 500 credits/month (16.6/day). Three sports = 3 credits per scan, so 5 scans/day is the ceiling. The loop wakes every 20–90 minutes and would burn the month in days, leaving the agent blind for four weeks. A prompt-level "mind the credits" is exactly the kind of instruction this project has watched itself ignore — so the interval is enforced in code.

**Files:**
- Modify: `/Users/anicca/anicca/skills/earn/polymarket-trade/test_pinnacle_edge.py`

- [ ] **Step 1: Write the failing test**

Append:

```python
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
```

- [ ] **Step 2: Run it**

```bash
cd /Users/anicca/anicca/skills/earn/polymarket-trade
python3 -m pytest test_pinnacle_edge.py -q
```

Expected: `23 passed`.

If `test_first_scan_spends_credits_once_per_sport` fails on the `fetch` keyword, check that `fetch_pinnacle_budgeted` threads its `fetch` argument down into `fetch_pinnacle(s, api_key, fetch=fetch)` — the whole test suite depends on every network call being injectable.

- [ ] **Step 3: Commit**

```bash
cd /Users/anicca/anicca
git add skills/earn/polymarket-trade/test_pinnacle_edge.py
git commit -m "test(pinnacle-edge): pin the credit budget guard

500 credits/month over three sports is a hard ceiling of five scans a day, and the
loop wakes every 20-90 minutes -- unguarded, it would spend the month in two days
and then be blind for four weeks. Inside the interval the paid API must not be
touched at all; these tests fail if that guard is ever removed."
```

---

### Task 6: Measure whether the edge actually exists — the honest verdict

Everything above is machinery. This task answers the only question that matters: **on the real APIs, right now, does Polymarket disagree with Pinnacle enough to be worth betting?** The answer may be no, and if it is no, that is the finding — it gets written down, and no money is risked.

**Files:**
- Create: `/Users/anicca/anicca-project/docs/loop-engineering/30-pinnacle-edge-measurement.md`

- [ ] **Step 1: Run the full unit suite one more time**

```bash
cd /Users/anicca/anicca/skills/earn/polymarket-trade
python3 -m pytest test_pinnacle_edge.py -q
```

Expected: `23 passed`. Do not proceed on a red suite.

- [ ] **Step 2: Run the scanner against the live APIs and capture the funnel**

```bash
cd /Users/anicca/anicca/skills/earn/polymarket-trade
rm -f state/pinnacle-cache.json          # force a real fetch for the measurement
export ODDS_API_KEY=$(grep '^ODDS_API_KEY=' /Users/anicca/.anicca-founder/agents/polymarket-agent/.env | cut -d= -f2)
python3 pinnacle_edge.py | python3 -m json.tool
```

Record verbatim: `pinnacle_events`, `pinnacle_prematch`, `pm_markets`, and either the `edges` array or the WAIT reason.

The number to compare against: **before this work, the funnel was 23 Pinnacle events → 8 pre-match → 2 matched to Polymarket → 0 edges.**

- [ ] **Step 3: Measure the real distribution of disagreement**

This is the honest core of the task. It prints the gap for EVERY matched pre-match game, not only the ones over the threshold, so the answer to "is there an edge here at all" is a distribution and not a yes/no:

```bash
cd /Users/anicca/anicca/skills/earn/polymarket-trade
export ODDS_API_KEY=$(grep '^ODDS_API_KEY=' /Users/anicca/.anicca-founder/agents/polymarket-agent/.env | cut -d= -f2)
python3 - <<'PY'
import datetime, os
from pinnacle_edge import (DEFAULT_SPORTS, fetch_pinnacle_budgeted, fetch_polymarket_sports,
                           fair_probs_from_outcomes, is_prematch, match_market,
                           name_similarity, polymarket_prices)

now = datetime.datetime.now(datetime.timezone.utc).timestamp()
pm = fetch_polymarket_sports()
pin, cached = fetch_pinnacle_budgeted(DEFAULT_SPORTS, os.environ["ODDS_API_KEY"], now)
pre = [e for e in pin if is_prematch(e.get("commence_time", ""), now)]

print(f"pinnacle events {len(pin)} | pre-match {len(pre)} | pm markets {len(pm)} | cached={cached}")
gaps, matched = [], 0
for e in pre:
    m, score = match_market(e, pm)
    if not m:
        continue
    matched += 1
    books = [b for b in e["bookmakers"] if b["key"] == "pinnacle"]
    fair = fair_probs_from_outcomes(books[0]["markets"][0]["outcomes"])
    prices = polymarket_prices(m)
    for team, f in fair.items():
        side = next((o for o in prices if name_similarity(o, team) >= 0.8), None)
        if side is None:
            continue
        gap = f - prices[side]
        gaps.append(gap)
        print(f"  {team:26s} pinnacle {f*100:5.1f}%  polymarket {prices[side]*100:5.1f}%  gap {gap*100:+5.1f}pt")

print(f"\nmatched games: {matched}")
if gaps:
    pos = [g for g in gaps if g > 0]
    print(f"sides measured: {len(gaps)}")
    print(f"max underpricing: {max(gaps)*100:+.1f}pt")
    print(f"sides >= 3pt underpriced: {sum(1 for g in gaps if g >= 0.03)}")
    print(f"mean |gap|: {sum(abs(g) for g in gaps)/len(gaps)*100:.2f}pt")
else:
    print("no matched sides -- nothing to measure")
PY
```

- [ ] **Step 4: Write the measurement down — including a negative result**

Create `/Users/anicca/anicca-project/docs/loop-engineering/30-pinnacle-edge-measurement.md` containing:

1. The funnel, before and after, as measured (not as hoped).
2. The full gap distribution from Step 3, verbatim.
3. A verdict, stated plainly, in one of exactly two forms:
   - **"The edge exists."** Cite the specific games and gaps ≥3pt. Next step: a single $1–3 live bet to test it with real money.
   - **"The edge does not exist at the sizes we can see."** State the measured mean gap and the maximum. Then say so without hedging: Polymarket is efficiently priced against Pinnacle on these markets, this route does not produce an edge for us today, and no money should be risked on it. Note what would change the answer (more sports, more matched games, a different market type) and stop.

A negative result written down honestly is worth more than a positive result talked into existence. The earlier "+29.4% McGregor edge" was exactly the latter: it came from a stale odds line quoted in a news article, and the live Pinnacle number put the real gap at 0.4pt.

- [ ] **Step 5: Commit**

```bash
cd /Users/anicca/anicca-project
git add docs/loop-engineering/30-pinnacle-edge-measurement.md
git commit -m "docs(30): measured verdict on the Pinnacle-vs-Polymarket edge"
git push
```

---

## Self-Review

**Spec coverage:**
- Free-side pagination (spec §設計①) → Task 4
- Paid side pointed only at sports Polymarket lists (spec §設計②) → already in `DEFAULT_SPORTS`; the per-sport credit cost is asserted in Task 5
- Credit budget guard (spec §credit予算ガード) → Task 5
- Pre-match gate + outlier gate (spec §既に実装済みの安全装置) → Task 3
- fail-closed (spec §この設計が守る原則) → Task 3 (unparseable time), Task 4 (failing page), Task 5 (dead sport)
- Verification 1–4 (spec §検証) → Task 6 steps 2–4
- The dead-code regression, which the spec calls out as the bug found → Task 2

**Placeholder scan:** none — every step carries its real code and its real command.

**Type consistency:** `find_edges(pin_events, pm_markets, min_edge, max_edge, now_ts)`, `is_prematch(commence_time, now_ts, lead_s)`, `fetch_polymarket_sports(pages, fetch)`, `fetch_pinnacle_budgeted(sports, api_key, now_ts, fetch) -> (events, from_cache)` are used identically in every task and match the implementation.

**Known coupling to fix if a test fails:** `fetch_pinnacle_budgeted` must pass its injected `fetch` through to `fetch_pinnacle`, and `find_edges`/`is_prematch` must accept an injected `now_ts`. Both are required for a network-free suite; Task 5 Step 2 says so explicitly.
