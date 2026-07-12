#!/usr/bin/env python3
"""pinnacle_edge.py — find markets where Polymarket disagrees with the sharpest book in the world.

WHY THIS EXISTS (2026-07-12). Every trade this agent has actually profited from was a one-sided bet
made after someone looked something up: verified against Polymarket's own data-api, the researched
directional bets returned +$9.78 across 4 wins, while the hedged bundle-arb legs returned +$0.24 in
total. Meanwhile pick.py's consensus engine was handed only the market's question text and the
market's own current price -- no news, no search, no outside information of any kind -- so its LLMs
could never estimate a probability the market did not already know, and it correctly said WAIT
forever. The missing ingredient was never capital. It was information.

THE EDGE. Pinnacle is the benchmark sportsbook: it does not limit winning bettors, runs 1-3% vig,
and its lines are shaped by professional syndicates -- so its no-vig price is the closest thing to a
true probability that is publicly available. Polymarket's price, by contrast, is a retail order book
that reacts more slowly. Where the two disagree by more than the noise, the disagreement itself is
the edge, and it requires predicting nothing: we are not forecasting the game, we are copying the
sharper forecaster and buying the side the softer market has mispriced.

This module is pure arithmetic + two read-only HTTP reads. It DECIDES NOTHING about size or whether
to trade -- it reports disagreements and lets the caller (pick.py / the loop) act. Fails closed:
any missing side, any unmatched market, any failed read yields no opportunity rather than a guess.
"""
from __future__ import annotations

import datetime
import json
import os
import sys
import urllib.parse
import urllib.request
from difflib import SequenceMatcher

ODDS_API = "https://api.the-odds-api.com/v4"
GAMMA_API = "https://gamma-api.polymarket.com"

# The sports Polymarket ACTUALLY lists. Measured 2026-07-12 by paging its own market feed: the
# tradeable games collapse to soccer (the World Cup market alone did $7.5M/24h), UFC, and MLB.
# Spending a credit on a sport Polymarket has no market for buys nothing, so the paid side is
# pointed only where the free side already found games.
DEFAULT_SPORTS = ["baseball_mlb", "mma_mixed_martial_arts", "soccer_fifa_world_cup"]

# Per-sport beats the catch-all: `upcoming` and `baseball_mlb` both cost 1 credit, but `upcoming`
# returned 23 events (8 of them pre-match, across every sport) while `baseball_mlb` alone returned
# 19 games, 14 of them pre-match. (the-odds-api.com/liveapi/guides/v4/)
#
# The free tier is 500 credits/month = 16.6/day, and 3 sports = 3 credits per scan, so 5 scans/day
# (450/month) is the ceiling. The loop wakes every 20-90 minutes and would burn the month in days,
# so the interval is enforced HERE, in code, with an on-disk cache -- a prompt-level "mind the
# credits" is exactly the kind of instruction this project has already watched itself ignore.
MIN_FETCH_INTERVAL_S = int(os.environ.get("PINNACLE_MIN_FETCH_INTERVAL_S", str(int(4.5 * 3600))))
CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state", "pinnacle-cache.json")

GAMMA_PAGE = 100          # Gamma's hard cap: limit=500 still returns 100
GAMMA_PAGES = 5           # 5 pages -> ~497 unique markets / ~71 games (measured)


# ---------------------------------------------------------------------------------------------
# odds math
# ---------------------------------------------------------------------------------------------
def american_to_prob(odds: float) -> float:
    """American odds -> the probability they IMPLY, vig included."""
    o = float(odds)
    if o == 0:
        raise ValueError("american odds cannot be 0")
    return (-o) / ((-o) + 100.0) if o < 0 else 100.0 / (o + 100.0)


def remove_vig(probs: list[float]) -> list[float]:
    """Strip the book's margin by normalising the implied probabilities back to 1.

    A two-way Pinnacle line implies ~104% of probability; the extra ~4% is the book's cut, not
    belief. Normalising is what turns a PRICE into an ESTIMATE, and it is the whole reason a
    sportsbook line is usable as a probability at all.
    """
    total = sum(probs)
    if total <= 0:
        raise ValueError("implied probabilities must be positive")
    return [p / total for p in probs]


def fair_probs_from_outcomes(outcomes: list[dict]) -> dict[str, float]:
    """[{name, price}] (American) -> {name: no-vig probability}. Needs >=2 sides to be meaningful."""
    if len(outcomes) < 2:
        raise ValueError("need at least two outcomes to remove vig")
    names = [o["name"] for o in outcomes]
    fair = remove_vig([american_to_prob(o["price"]) for o in outcomes])
    return dict(zip(names, fair))


# ---------------------------------------------------------------------------------------------
# reads
# ---------------------------------------------------------------------------------------------
def _get(url: str, timeout: int = 25):
    # Gamma answers urllib's default User-Agent with 403; bundle_arb.py already learned this and
    # sends a browser UA + Origin, so do the same rather than rediscover it.
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0", "Origin": "https://polymarket.com"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def fetch_pinnacle(sport: str, api_key: str, fetch=_get) -> list[dict]:
    """Pinnacle moneylines for one sport. Costs exactly 1 credit."""
    q = urllib.parse.urlencode(
        {"apiKey": api_key, "bookmakers": "pinnacle", "markets": "h2h", "oddsFormat": "american"}
    )
    return fetch(f"{ODDS_API}/sports/{sport}/odds?{q}")


def fetch_polymarket_sports(pages: int = GAMMA_PAGES, fetch=_get) -> list[dict]:
    """Every open, order-book-enabled Polymarket market, most-traded first.

    Gamma caps `limit` at 100 no matter what you ask for -- a single call was silently showing only
    the top 100 markets (34 games), which is why the scan kept matching almost nothing. Paging is
    free and unmetered, so take the whole board before spending a single paid credit.
    """
    seen, out = set(), []
    for i in range(max(1, pages)):
        q = urllib.parse.urlencode({
            "closed": "false", "active": "true", "order": "volume24hr",
            "ascending": "false", "limit": GAMMA_PAGE, "offset": i * GAMMA_PAGE,
        })
        try:
            page = fetch(f"{GAMMA_API}/markets?{q}")
        except Exception:
            break                              # keep the pages that DID load; never lose them all
        if not page:
            break
        for m in page:
            cid = m.get("conditionId")
            if cid and cid not in seen:
                seen.add(cid)
                out.append(m)
    return out


def _load_cache() -> dict | None:
    try:
        with open(CACHE_PATH) as f:
            return json.load(f)
    except Exception:
        return None


def _save_cache(obj: dict) -> None:
    try:
        os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
        tmp = CACHE_PATH + ".tmp"
        with open(tmp, "w") as f:
            json.dump(obj, f)
        os.replace(tmp, CACHE_PATH)
    except Exception:
        pass                                   # a cache write must never break a scan


def fetch_pinnacle_budgeted(sports: list[str], api_key: str, now_ts: float, fetch=_get):
    """Pinnacle lines for `sports`, refusing to spend credits more often than the interval allows.

    Returns (events, from_cache). Within the interval the cached events are returned unchanged --
    pre-match lines do not move fast enough for a 4.5-hour-old read to be misleading, and blowing
    the month's 500 credits in two days would leave the agent blind for four weeks.
    """
    cache = _load_cache()
    if cache and (now_ts - float(cache.get("fetched_at", 0))) < MIN_FETCH_INTERVAL_S:
        return cache.get("events", []), True

    events = []
    for s in sports:
        try:
            events.extend(fetch_pinnacle(s, api_key, fetch=fetch) or [])
        except Exception:
            continue                           # one dead sport must not kill the scan
    if events:
        _save_cache({"fetched_at": now_ts, "sports": sports, "events": events})
    return events, False


# ---------------------------------------------------------------------------------------------
# matching + edge
# ---------------------------------------------------------------------------------------------
def _norm(s: str) -> str:
    return "".join(c for c in str(s).lower() if c.isalnum() or c.isspace()).strip()


def name_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, _norm(a), _norm(b)).ratio()


def match_market(pin_event: dict, pm_markets: list[dict], threshold: float = 0.55):
    """Find the Polymarket market that is about the SAME game as this Pinnacle event.

    Fuzzy on purpose: Polymarket phrases a game as a question ("Will the Cubs beat the Reds?",
    "Cubs vs. Reds"), never as a bare fixture. A weak match is worse than none -- it would compare
    two different games and manufacture a phantom edge -- so anything under the threshold is
    rejected and the caller simply sees no opportunity for that event.
    """
    home, away = pin_event.get("home_team", ""), pin_event.get("away_team", "")
    best, best_score = None, 0.0
    for m in pm_markets:
        q = m.get("question") or ""
        if not q or not m.get("enableOrderBook"):
            continue
        nq = _norm(q)
        # both team names must actually appear -- fuzzy matching alone happily pairs unrelated games
        if _norm(home) not in nq or _norm(away) not in nq:
            continue
        score = max(name_similarity(q, f"{away} vs {home}"), name_similarity(q, f"{home} vs {away}"))
        if score > best_score:
            best, best_score = m, score
    return (best, best_score) if best and best_score >= threshold else (None, best_score)


def polymarket_prices(market: dict) -> dict[str, float]:
    """{outcome: price} from a Gamma market. Prices ARE probabilities on Polymarket (a $1 payout)."""
    try:
        outcomes = market.get("outcomes")
        prices = market.get("outcomePrices")
        outcomes = json.loads(outcomes) if isinstance(outcomes, str) else outcomes
        prices = json.loads(prices) if isinstance(prices, str) else prices
        if not outcomes or not prices or len(outcomes) != len(prices):
            return {}
        return {str(o): float(p) for o, p in zip(outcomes, prices)}
    except Exception:
        return {}


def is_prematch(commence_time: str, now_ts: float, lead_s: int = 600) -> bool:
    """True only if the game has NOT started yet (with a lead-time buffer).

    THE TRAP THIS EXISTS TO KILL, caught on the very first live run: the top "edge" was McKinney at
    a Polymarket price of $0.0005 against a Pinnacle fair value of 48.6% -- an apparent +97,147%.
    It was not an edge. The fight had already started; the market had watched him lose and repriced
    to ~0, while Pinnacle's line still showed the pre-fight number. Buying it would have lost 100%
    of the stake, every time. A settled or in-play market makes the two sources incomparable, and
    the bigger the "edge" looks, the more certainly that is what happened. Only pre-match games are
    ever comparable, so anything already underway is dropped before it can be sized.
    """
    if not commence_time:
        return False
    try:
        t = commence_time.replace("Z", "+00:00")
        start = datetime.datetime.fromisoformat(t).timestamp()
    except Exception:
        return False                       # unparseable -> fail closed, never trade it
    return start > now_ts + lead_s


def find_edges(
    pin_events: list[dict],
    pm_markets: list[dict],
    min_edge: float = 0.03,
    max_edge: float = 0.30,
    now_ts: float | None = None,
) -> list[dict]:
    """Every PRE-MATCH side where Pinnacle's no-vig probability exceeds Polymarket's price by min_edge.

    Only UNDERPRICED sides are returned: on Polymarket you profit by BUYING a side worth more than
    it costs. An overpriced side is not actionable here -- shorting it means buying the other side,
    which shows up on its own as that side's own edge if it is real.

    max_edge is a fraud detector, not a risk limit. Pinnacle and Polymarket are both liquid, public
    and watched by professionals; a genuine disagreement between them is a few points, not thirty.
    An enormous gap is overwhelmingly evidence that the two rows are not describing the same live
    state (a settled game, a stale line, a bad fuzzy match) -- exactly the shape of the +97,147%
    "opportunity" the first live run surfaced. Discarding the outliers costs nothing real and
    removes the only class of signal that can lose the whole stake at once.
    """
    now_ts = now_ts if now_ts is not None else datetime.datetime.now(datetime.timezone.utc).timestamp()
    out = []
    for ev in pin_events:
        if not is_prematch(ev.get("commence_time", ""), now_ts):
            continue                       # in-play or finished -> the two sources are incomparable
        books = [b for b in (ev.get("bookmakers") or []) if b.get("key") == "pinnacle"]
        if not books:
            continue
        markets = [m for m in (books[0].get("markets") or []) if m.get("key") == "h2h"]
        if not markets:
            continue
        try:
            fair = fair_probs_from_outcomes(markets[0].get("outcomes") or [])
        except ValueError:
            continue

        pm, score = match_market(ev, pm_markets)
        if not pm:
            continue
        prices = polymarket_prices(pm)
        if not prices:
            continue

        for team, fair_p in fair.items():
            # the Polymarket outcome naming the same team (its labels are team names, or Yes/No).
            # Must pick the BEST-scoring outcome, not the first one over the threshold: two short,
            # similarly-spelled outcome labels (e.g. "Team A" / "Team B") can both clear 0.8 against
            # each other, and taking the first would silently attribute the wrong team's fair price
            # to this side -- the same best-of-all-candidates pattern match_market already uses.
            side, side_score = None, 0.0
            for o in prices:
                s = name_similarity(o, team)
                if s > side_score:
                    side, side_score = o, s
            if side is None or side_score < 0.8:
                continue
            price = prices[side]
            if not (0.0 < price < 1.0):
                continue
            edge = fair_p - price          # worth this much, costs that much
            if not (min_edge <= edge <= max_edge):
                continue                # below noise, or too big to be real (see max_edge above)
            out.append({
                "event": f"{ev.get('away_team')} @ {ev.get('home_team')}",
                "sport": ev.get("sport_key"),
                "commence_time": ev.get("commence_time"),
                "pm_question": pm.get("question"),
                "pm_condition_id": pm.get("conditionId"),
                "pm_token_ids": pm.get("clobTokenIds"),
                "buy_outcome": side,
                "pm_price": round(price, 4),
                "pinnacle_fair": round(fair_p, 4),
                "edge": round(edge, 4),
                "edge_pct_of_stake": round(edge / price * 100, 1),
                "match_score": round(score, 2),
            })
    return sorted(out, key=lambda x: -x["edge"])


def main() -> int:
    key = os.environ.get("ODDS_API_KEY")
    if not key:
        print(json.dumps({"action": "WAIT", "reason": "ODDS_API_KEY not set"}))
        return 0
    min_edge = float(os.environ.get("PINNACLE_MIN_EDGE", "0.03"))
    max_edge = float(os.environ.get("PINNACLE_MAX_EDGE", "0.30"))
    sports = [s for s in os.environ.get("PINNACLE_SPORTS", ",".join(DEFAULT_SPORTS)).split(",") if s]
    now_ts = datetime.datetime.now(datetime.timezone.utc).timestamp()

    try:
        pm = fetch_polymarket_sports()                                   # free side first
        pin, cached = fetch_pinnacle_budgeted(sports, key, now_ts)       # paid side, rate-limited
    except Exception as e:
        print(json.dumps({"action": "WAIT", "reason": f"fetch failed (fail-closed): {e}"}))
        return 0

    prematch = sum(1 for e in pin if is_prematch(e.get("commence_time", ""), now_ts))
    edges = find_edges(pin, pm, min_edge=min_edge, max_edge=max_edge, now_ts=now_ts)
    funnel = {
        "pinnacle_events": len(pin), "pinnacle_prematch": prematch,
        "pm_markets": len(pm), "sports": sports, "odds_from_cache": cached,
    }
    if not edges:
        print(json.dumps({
            "action": "WAIT",
            "reason": "no pre-match market disagrees with Pinnacle by the threshold",
            "min_edge": min_edge, **funnel,
        }))
        return 0
    print(json.dumps({"action": "EDGES", "count": len(edges), "edges": edges[:10], **funnel}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
