"""Reward-market discovery + scoring — sync port of poly-maker's
src/polymaker/catalog/{gamma.py,scanner.py,scoring.py} (MIT,
warproxxx/poly-maker). Upstream is async httpx; this port is sync
`requests` to match this skill's existing style (market_maker.py,
bundle_arb.py, pick.py all use `requests`, not httpx/asyncio).

Two live, no-auth Polymarket endpoints do all the work:
  Gamma API  https://gamma-api.polymarket.com/markets   — market metadata,
             best bid/ask, liquidity/volume, reward band (min size / max
             spread), fee schedule. No auth.
  CLOB API   https://clob.polymarket.com/sampling-markets — the reward-
             eligible markets' actual daily USDC reward RATE (not on
             Gamma). No auth.

Bookkeeping only: fetch, parse, filter (binary + accepting orders +
rewards>0), score by estimated reward/rebate income. Which market is
"best" is a ranking by real numbers pulled live — no hardcoded market/slug,
no LLM judgment needed here (this is deterministic scoring over fetched
facts, same category as pick.py's MIN_LIQUIDITY/MIN_ODDS filters).
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass

import requests

GAMMA_HOST = "https://gamma-api.polymarket.com"
CLOB_HOST = "https://clob.polymarket.com"
USDC_ADDRESS = "0x2791bca1f2de4661ed88a30c99a7a9449aa84174"


@dataclass(frozen=True, slots=True)
class TokenMeta:
    token_id: str
    outcome: str


@dataclass(frozen=True, slots=True)
class MarketMeta:
    condition_id: str
    question: str
    slug: str
    yes: TokenMeta
    no: TokenMeta
    tick_size: float
    neg_risk: bool
    min_order_size: float
    rewards_min_size: float
    rewards_max_spread: float
    rewards_daily_rate: float
    maker_fee_bps: int
    taker_fee_bps: int
    fees_enabled: bool
    rebate_rate: float
    end_date_iso: str | None
    event_id: str | None
    best_bid: float
    best_ask: float
    liquidity_num: float
    volume_num: float
    volume_24hr: float

    @property
    def price_decimals(self) -> int:
        t = self.tick_size
        n = 0
        while t < 1 and n < 6:
            t *= 10
            n += 1
        return n


@dataclass(frozen=True, slots=True)
class MarketScore:
    condition_id: str
    reward_density: float  # est. reward $/day per our two-sided quote size
    rebate_potential: float  # est. daily rebate $ pool available to makers
    spread: float
    extremity: float  # 0 = mid ~0.5 (good), 1 = near 0/1 (bad payoff asymmetry)
    score: float


def _json_list(value) -> list:
    """clobTokenIds / outcomes arrive as JSON-encoded strings on Gamma."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def fetch_reward_rates(clob_host: str = CLOB_HOST, timeout: float = 20.0, max_pages: int = 50) -> dict[str, float]:
    """{condition_id: daily USDC reward rate}, from CLOB /sampling-markets
    (the reward-eligible markets; the rate isn't published on Gamma)."""
    rates: dict[str, float] = {}
    cursor = ""
    for _ in range(max_pages):
        r = requests.get(f"{clob_host}/sampling-markets", params={"next_cursor": cursor}, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        for m in data.get("data", []):
            cid = m.get("condition_id")
            rate = 0.0
            for ri in (m.get("rewards") or {}).get("rates") or []:
                if str(ri.get("asset_address", "")).lower() == USDC_ADDRESS:
                    rate = float(ri.get("rewards_daily_rate", 0) or 0)
                    break
            if cid:
                rates[cid] = rate
        cursor = data.get("next_cursor") or ""
        if not cursor or cursor == "LTE=":  # documented end sentinel
            break
    return rates


def parse_market(raw: dict, reward_rates: dict[str, float] | None = None) -> MarketMeta | None:
    """Gamma market dict -> MarketMeta, or None if unusable (not binary /
    not accepting orders / malformed)."""
    try:
        if not raw.get("acceptingOrders", False):
            return None
        token_ids = _json_list(raw.get("clobTokenIds"))
        outcomes = _json_list(raw.get("outcomes"))
        if len(token_ids) != 2 or len(outcomes) != 2:
            return None  # only binary markets

        condition_id = raw["conditionId"]
        rate_map = reward_rates or {}
        fee = raw.get("feeSchedule") or {}
        taker_rate = float(fee.get("rate", 0.0) or 0.0)

        event_id = None
        events = raw.get("events") or []
        if events:
            event_id = str(events[0].get("id")) if events[0].get("id") is not None else None

        return MarketMeta(
            condition_id=condition_id,
            question=raw.get("question", ""),
            slug=raw.get("slug", ""),
            yes=TokenMeta(str(token_ids[0]), str(outcomes[0])),
            no=TokenMeta(str(token_ids[1]), str(outcomes[1])),
            tick_size=float(raw.get("orderPriceMinTickSize", 0.001) or 0.001),
            neg_risk=bool(raw.get("negRisk", False)),
            min_order_size=float(raw.get("orderMinSize", 5) or 5),
            rewards_min_size=float(raw.get("rewardsMinSize", 0) or 0),
            rewards_max_spread=float(raw.get("rewardsMaxSpread", 0) or 0),
            rewards_daily_rate=float(rate_map.get(condition_id, 0.0)),
            maker_fee_bps=0,  # V2: makers pay zero
            taker_fee_bps=int(round(taker_rate * 10000)),
            fees_enabled=bool(raw.get("feesEnabled", False)),
            rebate_rate=float(fee.get("rebateRate", 0.0) or 0.0),
            end_date_iso=raw.get("endDate"),
            event_id=event_id,
            best_bid=float(raw.get("bestBid", 0) or 0),
            best_ask=float(raw.get("bestAsk", 0) or 0),
            liquidity_num=float(raw.get("liquidityNum", 0) or 0),
            volume_num=float(raw.get("volumeNum", 0) or 0),
            volume_24hr=float(raw.get("volume24hrClob") or raw.get("volume24hr") or 0),
        )
    except (KeyError, ValueError, TypeError):
        return None


def _mid(m: MarketMeta) -> float:
    if m.best_bid > 0 and m.best_ask > 0:
        return (m.best_bid + m.best_ask) / 2.0
    return 0.5


def reward_density(m: MarketMeta, quote_size_usdc: float = 100.0) -> float:
    """Est. reward $/day if we hold ~quote_size two-sided in-band, scaled by
    our share of the market's existing liquidity (ranking signal, not an
    absolute forecast — real payout depends on live competition)."""
    if m.rewards_daily_rate <= 0 or m.rewards_max_spread <= 0:
        return 0.0
    liq = max(m.liquidity_num, quote_size_usdc)
    our_share = min(1.0, quote_size_usdc / liq)
    return m.rewards_daily_rate * our_share


def rebate_potential(m: MarketMeta) -> float:
    """Est. daily maker-rebate POOL for the market (whole-market, not our
    share): daily_fees = vol24 * fee_rate * (1 - mid); pool = fees * rebate_rate."""
    if not m.fees_enabled or m.rebate_rate <= 0 or m.taker_fee_bps <= 0:
        return 0.0
    vol24 = m.volume_24hr
    if vol24 <= 0:
        return 0.0
    fee_rate = m.taker_fee_bps / 10000.0
    mid = _mid(m)
    daily_fees = vol24 * fee_rate * (1.0 - mid)
    return round(daily_fees * m.rebate_rate, 2)


def extremity(m: MarketMeta) -> float:
    mid = _mid(m)
    return min(1.0, abs(mid - 0.5) / 0.5)


def score_market(m: MarketMeta, quote_size_usdc: float = 100.0) -> MarketScore:
    rd = reward_density(m, quote_size_usdc)
    rp = rebate_potential(m)
    ext = extremity(m)
    spread = max(0.0, m.best_ask - m.best_bid) if (m.best_bid and m.best_ask) else 1.0

    ref = quote_size_usdc
    our_share = min(0.5, ref / max(m.liquidity_num, ref))
    income = rd + rp * our_share
    penalty = (1.0 - 0.5 * ext) * (1.0 / (1.0 + spread * 20.0))
    viability = min(1.0, m.liquidity_num / 2000.0)
    return MarketScore(
        condition_id=m.condition_id,
        reward_density=round(rd, 3),
        rebate_potential=round(rp, 3),
        spread=round(spread, 4),
        extremity=round(ext, 3),
        score=round(income * penalty * viability, 4),
    )


def iter_markets(
    *,
    gamma_host: str = GAMMA_HOST,
    tag_id: str | None = None,
    min_liquidity: float = 0.0,
    min_volume_24hr: float = 0.0,
    limit: int = 100,
    max_pages: int = 25,
    timeout: float = 20.0,
):
    """Yield raw active/open Gamma market dicts, offset-paginated."""
    offset = 0
    for _ in range(max_pages):
        params = {
            "limit": limit,
            "offset": offset,
            "active": "true",
            "closed": "false",
            "order": "volume24hr",
            "ascending": "false",
        }
        if tag_id:
            params["tag_id"] = tag_id
            params["related_tags"] = "true"
        if min_liquidity > 0:
            params["liquidity_num_min"] = min_liquidity
        if min_volume_24hr > 0:
            params["volume_num_min"] = min_volume_24hr

        r = requests.get(f"{gamma_host}/markets", params=params, timeout=timeout)
        if r.status_code in (400, 422):
            return  # Gamma's end-of-pagination signal, not an error
        r.raise_for_status()
        batch = r.json()
        if not batch:
            return
        for m in batch:
            yield m
        if len(batch) < limit:
            return
        offset += limit


def resolve_tag_id(slug: str, gamma_host: str = GAMMA_HOST, timeout: float = 20.0) -> str | None:
    try:
        r = requests.get(f"{gamma_host}/tags/slug/{slug}", timeout=timeout)
        r.raise_for_status()
        return str(r.json()["id"])
    except (requests.RequestException, KeyError, ValueError):
        return None


def scan_reward_markets(
    *,
    tag_slug: str | None = None,
    min_liquidity: float = 1000.0,
    min_volume_24hr: float = 0.0,
    rewards_only: bool = True,
    quote_size_usdc: float = 100.0,
    max_pages: int = 25,
) -> list[tuple[MarketMeta, MarketScore]]:
    """Fetch, parse, filter, score. Returns [(MarketMeta, MarketScore), ...]
    sorted by score descending — the ranked reward-market shortlist.

    This is the REAL live call this task's spec requires (§1①): actual
    Gamma + CLOB REST, actual live reward rates, no fixture/mock data.
    """
    reward_rates = fetch_reward_rates()
    tag_id = resolve_tag_id(tag_slug) if tag_slug else None

    kept: list[tuple[MarketMeta, MarketScore]] = []
    for raw in iter_markets(tag_id=tag_id, min_liquidity=min_liquidity, min_volume_24hr=min_volume_24hr, max_pages=max_pages):
        meta = parse_market(raw, reward_rates)
        if meta is None:
            continue
        if rewards_only and meta.rewards_daily_rate <= 0:
            continue
        kept.append((meta, score_market(meta, quote_size_usdc)))

    kept.sort(key=lambda pair: pair[1].score, reverse=True)
    return kept
