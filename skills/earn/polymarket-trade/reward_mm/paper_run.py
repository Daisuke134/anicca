#!/usr/bin/env python3
"""paper_run.py — PAPER MODE ONLY. Scans real Polymarket reward markets via
the live Gamma/CLOB REST APIs, picks the top-N by reward/rebate score,
fetches each one's real live order book, computes fair value + a two-sided
post-only quote, and PRINTS the result as JSON.

★ THIS FILE NEVER PLACES AN ORDER. ★ No wallet, no private key, no
signing, no `SecureClient`, no `post_order` call anywhere in this module or
anything it imports. That is a structural guarantee, not just a runtime
flag — grep this file and its imports (estimators/regime/quoting/risk/
book/gamma_scan) for "post_order"/"create_.*_order"/"PRIVATE_KEY" and you
will find none. Going live means the PARENT explicitly writes a NEW
execution module that imports the existing `place_order.py` /
`market_maker.py` machinery and feeds it these quotes — see SKILL.md
"REWARD-MM loop wiring" for the exact steps and the legal caveat that
gates it.

Usage:
    python3 paper_run.py [--top N] [--quote-size USDC] [--tag SLUG] [--min-liquidity USD]

One-shot snapshot caveat: the online estimators (vol/flow/toxicity EWMAs,
the EVENT-regime jump/cooloff state) need a persistent process accumulating
history over time to mean anything. A single process invocation has no
prior fair-value sample and no flow tape, so this run seeds flow_z=0,
vol_short=0, toxicity=0, prev_fv=None — i.e. the FIRST sample of what would,
in a long-running loop, become a real live signal. The quotes printed here
are therefore the "cold start" quote (pure microprice + reward-band-clamped
half-spread, no skew/vol/toxicity adjustment yet) — correct and safe, just
not yet the full adaptive picture a running process builds up.
"""
from __future__ import annotations

import argparse
import json
import sys
import time

from reward_mm.book import BookView, fetch_book, microprice
from reward_mm.gamma_scan import MarketMeta, scan_reward_markets
from reward_mm.profiles import profile_for
from reward_mm.quoting import QuoteInputs, compute_fair_value, construct_quotes
from reward_mm.regime import Regime, RegimeInputs, RegimeMachine, RegimeParams
from reward_mm.risk import RiskManager


def _hours_to_end(end_date_iso: str | None, now_ts: float) -> float | None:
    if not end_date_iso:
        return None
    try:
        from datetime import datetime, timezone

        end = datetime.fromisoformat(end_date_iso.replace("Z", "+00:00"))
        return (end.timestamp() - now_ts) / 3600.0
    except (ValueError, TypeError):
        return None


def quote_one_market(meta: MarketMeta, *, quote_size_usdc: float, risk: RiskManager, now_ts: float) -> dict:
    """Build the paper quote plan for one reward-eligible market. Never
    raises on a fetchable-but-thin book — fails closed to an empty quote
    list with a `reason`."""
    profile = profile_for(meta.liquidity_num)

    yes_view = fetch_book(meta.yes.token_id)
    no_view = fetch_book(meta.no.token_id)

    if yes_view.best_bid is None and yes_view.best_ask is None:
        return {
            "condition_id": meta.condition_id,
            "question": meta.question,
            "slug": meta.slug,
            "quotes": [],
            "regime": Regime.HALTED.value,
            "reason": "no_book_data",
        }

    mp = microprice(yes_view, fallback=meta.best_bid or meta.best_ask or 0.5)
    fv = compute_fair_value(mp, flow_z=0.0, tick=meta.tick_size)  # cold-start: no flow tape yet

    hours_to_end = _hours_to_end(meta.end_date_iso, now_ts)
    regime_machine = RegimeMachine()
    regime_inputs = RegimeInputs(
        now=now_ts,
        tick=meta.tick_size,
        fv=fv,
        prev_fv=None,  # cold-start: no prior sample this run
        vol_ratio=1.0,  # cold-start baseline (neither elevated nor depressed)
        flow_z=0.0,
        inventory_util=0.0,  # paper mode: no held inventory yet
        hours_to_end=hours_to_end,
        market_resolved=False,
        ws_stale=False,
    )
    regime_params = RegimeParams(
        event_jump_ticks=profile.event_jump_ticks,
        event_cooloff_s=profile.event_cooloff_s,
        trend_flow_z=profile.trend_flow_z,
        trend_vol_ratio=profile.trend_vol_ratio,
        reduce_only_hours=profile.reduce_only_hours,
        halt_before_hours=profile.halt_before_hours,
    )
    regime = regime_machine.decide(regime_inputs, regime_params)

    risk_decision = risk.evaluate(meta.yes.token_id, meta.no.token_id)

    quotes = construct_quotes(
        QuoteInputs(
            meta=meta,
            regime=regime,
            fv=fv,
            vol_short=0.0,  # cold-start: VolEstimator needs >=2 samples
            toxicity=0.0,  # cold-start: MarkoutTracker needs resolved fills
            yes_view=yes_view,
            no_view=no_view,
            profile=profile,
            risk_size_scale=risk_decision.size_scale,
        )
    )

    return {
        "condition_id": meta.condition_id,
        "question": meta.question,
        "slug": meta.slug,
        "fair_value_yes": round(fv, 4),
        "microprice_yes": round(mp, 4),
        "regime": regime.value,
        "profile": profile.name,
        "reward_daily_rate_usdc": meta.rewards_daily_rate,
        "reward_min_size": meta.rewards_min_size,
        "reward_max_spread_pct": meta.rewards_max_spread,
        "book": {
            "yes_best_bid": yes_view.best_bid,
            "yes_best_ask": yes_view.best_ask,
            "no_best_bid": no_view.best_bid,
            "no_best_ask": no_view.best_ask,
        },
        "risk_size_scale": risk_decision.size_scale,
        "quotes": [
            {"token_id": q.token_id, "side": q.side, "price": q.price, "size": q.size, "post_only": q.post_only}
            for q in quotes
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Polymarket reward-MM paper-mode scan+quote (no order placement)")
    ap.add_argument("--top", type=int, default=5, help="how many top-scored reward markets to quote")
    ap.add_argument("--quote-size", type=float, default=100.0, help="assumed two-sided quote size USDC, for scoring/sizing")
    ap.add_argument("--tag", type=str, default=None, help="Gamma tag slug filter, e.g. 'politics' (default: no filter)")
    ap.add_argument("--min-liquidity", type=float, default=1000.0, help="Gamma liquidityNum floor")
    args = ap.parse_args()

    now_ts = time.time()
    ranked = scan_reward_markets(
        tag_slug=args.tag,
        min_liquidity=args.min_liquidity,
        quote_size_usdc=args.quote_size,
    )

    risk = RiskManager()
    picks = []
    for meta, score in ranked[: args.top]:
        plan = quote_one_market(meta, quote_size_usdc=args.quote_size, risk=risk, now_ts=now_ts)
        plan["score"] = {
            "reward_density": score.reward_density,
            "rebate_potential": score.rebate_potential,
            "spread": score.spread,
            "extremity": score.extremity,
            "total": score.score,
        }
        picks.append(plan)

    result = {
        "mode": "PAPER — no order placed",
        "scanned_reward_eligible_markets": len(ranked),
        "picked": len(picks),
        "picks": picks,
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
