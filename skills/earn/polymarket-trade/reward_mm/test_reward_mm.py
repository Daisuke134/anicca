#!/usr/bin/env python3
"""Tests for reward_mm — the poly-maker port (SKILL.md "REWARD-MM" section).

Pure-logic tests (estimators/regime/quoting/risk/scoring) never touch the
network. `test_live_gamma_scan_returns_real_reward_markets` and
`test_live_book_fetch_returns_real_data` DO hit the real, public,
no-auth Polymarket Gamma/CLOB REST APIs (same endpoints market_maker.py /
bundle_arb.py already call) — this is the "real Gamma API" proof the task
spec requires, not a fixture. No wallet, no key, no order is ever placed
by anything in this test file or the modules it imports.

Run: python3 -m pytest reward_mm/test_reward_mm.py -q
     (skips the two live tests with -m "not live" if offline)
"""
import time

import pytest

from reward_mm.book import BookView, fetch_book, microprice
from reward_mm.estimators import Ewma, FlowEstimator, MarkoutTracker, VolEstimator
from reward_mm.gamma_scan import (
    MarketMeta,
    TokenMeta,
    parse_market,
    reward_density,
    scan_reward_markets,
    score_market,
)
from reward_mm.profiles import DEFAULT, THIN_BOOK, profile_for
from reward_mm.quoting import QuoteInputs, compute_fair_value, construct_quotes, round_to_tick
from reward_mm.regime import Regime, RegimeInputs, RegimeMachine, RegimeParams
from reward_mm.risk import RiskConfig, RiskManager


# ── estimators ──────────────────────────────────────────────────────────


def test_ewma_seeds_on_first_observation():
    e = Ewma(halflife_s=10.0)
    assert not e.ready
    v = e.update(0.5, ts=0.0)
    assert v == 0.5
    assert e.ready


def test_ewma_decays_toward_new_value_over_time():
    e = Ewma(halflife_s=10.0)
    e.update(0.0, ts=0.0)
    v = e.update(1.0, ts=10.0)  # exactly one halflife later
    assert abs(v - 0.5) < 1e-9  # half decayed toward the new value


def test_ewma_decay_to_ages_out_silently():
    e = Ewma(halflife_s=10.0)
    e.update(1.0, ts=0.0)
    v = e.decay_to(10.0)
    assert abs(v - 0.5) < 1e-9


def test_vol_estimator_zero_when_flat():
    v = VolEstimator(short_halflife_s=10.0, long_halflife_s=100.0)
    v.update(0.5, ts=0.0)
    v.update(0.5, ts=1.0)
    v.update(0.5, ts=2.0)
    assert v.short == 0.0
    assert v.long == 0.0


def test_vol_estimator_positive_on_movement():
    v = VolEstimator(short_halflife_s=10.0, long_halflife_s=100.0)
    v.update(0.5, ts=0.0)
    v.update(0.6, ts=1.0)
    assert v.short > 0.0


def test_flow_estimator_z_sign_matches_aggressor():
    f = FlowEstimator(halflife_s=60.0)
    f.update("BUY", 10.0, ts=0.0)
    assert f.z > 0
    f2 = FlowEstimator(halflife_s=60.0)
    f2.update("SELL", 10.0, ts=0.0)
    assert f2.z < 0


def test_markout_tracker_positive_when_price_moves_in_our_favor():
    m = MarkoutTracker(horizon_s=100.0, ewma_halflife_s=1000.0)
    m.record_fill("BUY", fv_at_fill=0.5, ts=0.0)  # we bought at 0.5
    m.evaluate(fv_now=0.5, ts=50.0)  # not due yet
    assert m.toxicity == 0.0  # nothing resolved yet
    m.evaluate(fv_now=0.6, ts=101.0)  # price rose -> good for a buyer
    assert m.markout > 0
    assert m.toxicity == 0.0  # positive markout -> zero toxicity


def test_markout_tracker_toxicity_when_picked_off():
    m = MarkoutTracker(horizon_s=100.0, ewma_halflife_s=1000.0)
    m.record_fill("BUY", fv_at_fill=0.5, ts=0.0)
    m.evaluate(fv_now=0.4, ts=101.0)  # price fell after we bought -> adverse
    assert m.markout < 0
    assert m.toxicity > 0


# ── regime ──────────────────────────────────────────────────────────────


def _regime_params(**overrides):
    base = dict(event_jump_ticks=6.0, event_cooloff_s=30.0, trend_flow_z=1.8, trend_vol_ratio=3.0, reduce_only_hours=24.0, halt_before_hours=2.0)
    base.update(overrides)
    return RegimeParams(**base)


def test_regime_quiet_by_default():
    rm = RegimeMachine()
    inp = RegimeInputs(now=0.0, tick=0.01, fv=0.5, prev_fv=0.5, vol_ratio=1.0, flow_z=0.0, inventory_util=0.0, hours_to_end=100.0)
    assert rm.decide(inp, _regime_params()) == Regime.QUIET


def test_regime_halted_when_risk_halt():
    rm = RegimeMachine()
    inp = RegimeInputs(now=0.0, tick=0.01, fv=0.5, prev_fv=0.5, vol_ratio=1.0, flow_z=0.0, inventory_util=0.0, hours_to_end=100.0, risk_halt=True)
    assert rm.decide(inp, _regime_params()) == Regime.HALTED


def test_regime_halted_near_end_date():
    rm = RegimeMachine()
    inp = RegimeInputs(now=0.0, tick=0.01, fv=0.5, prev_fv=0.5, vol_ratio=1.0, flow_z=0.0, inventory_util=0.0, hours_to_end=1.0)
    assert rm.decide(inp, _regime_params(halt_before_hours=2.0)) == Regime.HALTED


def test_regime_event_on_fv_jump_then_cooloff():
    rm = RegimeMachine()
    # prev_fv=0.50, fv=0.56, tick=0.01 -> jump = 6 ticks >= event_jump_ticks(6)
    inp_jump = RegimeInputs(now=0.0, tick=0.01, fv=0.56, prev_fv=0.50, vol_ratio=1.0, flow_z=0.0, inventory_util=0.0, hours_to_end=100.0)
    assert rm.decide(inp_jump, _regime_params()) == Regime.EVENT
    # still inside the cooloff window immediately after
    inp_after = RegimeInputs(now=5.0, tick=0.01, fv=0.56, prev_fv=0.56, vol_ratio=1.0, flow_z=0.0, inventory_util=0.0, hours_to_end=100.0)
    assert rm.decide(inp_after, _regime_params()) == Regime.EVENT
    # past the cooloff window, back to normal evaluation
    inp_later = RegimeInputs(now=100.0, tick=0.01, fv=0.56, prev_fv=0.56, vol_ratio=1.0, flow_z=0.0, inventory_util=0.0, hours_to_end=100.0)
    assert rm.decide(inp_later, _regime_params()) == Regime.QUIET


def test_regime_reduce_only_at_inventory_cap():
    rm = RegimeMachine()
    inp = RegimeInputs(now=0.0, tick=0.01, fv=0.5, prev_fv=0.5, vol_ratio=1.0, flow_z=0.0, inventory_util=1.0, hours_to_end=100.0)
    assert rm.decide(inp, _regime_params()) == Regime.REDUCE_ONLY


def test_regime_trending_on_flow_z():
    rm = RegimeMachine()
    inp = RegimeInputs(now=0.0, tick=0.01, fv=0.5, prev_fv=0.5, vol_ratio=1.0, flow_z=2.5, inventory_util=0.0, hours_to_end=100.0)
    assert rm.decide(inp, _regime_params(trend_flow_z=1.8)) == Regime.TRENDING


# ── quoting ─────────────────────────────────────────────────────────────


def test_round_to_tick_clamps_and_snaps():
    assert round_to_tick(0.4567, tick=0.01, decimals=2, up=False) == 0.45
    assert round_to_tick(0.4567, tick=0.01, decimals=2, up=True) == 0.46
    assert round_to_tick(-1.0, tick=0.01, decimals=2, up=False) == 0.01  # clamped above 0


def test_compute_fair_value_clamped_and_nudged():
    fv = compute_fair_value(microprice=0.5, flow_z=1.0, tick=0.01, weight=0.5)
    assert fv > 0.5  # positive flow nudges FV up
    fv_extreme = compute_fair_value(microprice=0.999, flow_z=10.0, tick=0.01)
    assert fv_extreme < 1.0  # clamped below 1-tick


def _sample_market(*, tick=0.01, rewards_max_spread=4.5, rewards_min_size=20.0, min_order_size=5.0) -> MarketMeta:
    return MarketMeta(
        condition_id="0xabc",
        question="Test market?",
        slug="test-market",
        yes=TokenMeta("yes-token", "Yes"),
        no=TokenMeta("no-token", "No"),
        tick_size=tick,
        neg_risk=False,
        min_order_size=min_order_size,
        rewards_min_size=rewards_min_size,
        rewards_max_spread=rewards_max_spread,
        rewards_daily_rate=50.0,
        maker_fee_bps=0,
        taker_fee_bps=500,
        fees_enabled=True,
        rebate_rate=0.25,
        end_date_iso=None,
        event_id=None,
        best_bid=0.49,
        best_ask=0.51,
        liquidity_num=10000.0,
        volume_num=50000.0,
        volume_24hr=1000.0,
    )


def test_construct_quotes_produces_two_sided_bids_that_sum_below_one():
    meta = _sample_market()
    view = BookView(best_bid=0.49, best_ask=0.51, bid_depth=100.0, ask_depth=100.0)
    inp = QuoteInputs(
        meta=meta,
        regime=Regime.QUIET,
        fv=0.5,
        vol_short=0.0,
        toxicity=0.0,
        yes_view=view,
        no_view=view,
        profile=DEFAULT,
    )
    quotes = construct_quotes(inp)
    assert len(quotes) == 2
    by_token = {q.token_id: q for q in quotes}
    assert by_token["yes-token"].side == "BUY"
    assert by_token["no-token"].side == "BUY"
    assert by_token["yes-token"].post_only is True
    # the canonical reward-farming property: both legs are bids that sum < 1
    assert by_token["yes-token"].price + by_token["no-token"].price < 1.0
    # sizes respect the exchange minimum
    assert by_token["yes-token"].size >= meta.min_order_size
    assert by_token["no-token"].size >= meta.min_order_size


def test_construct_quotes_empty_when_halted_or_event():
    meta = _sample_market()
    view = BookView(best_bid=0.49, best_ask=0.51, bid_depth=100.0, ask_depth=100.0)
    for regime in (Regime.HALTED, Regime.EVENT):
        inp = QuoteInputs(meta=meta, regime=regime, fv=0.5, vol_short=0.0, toxicity=0.0, yes_view=view, no_view=view, profile=DEFAULT)
        assert construct_quotes(inp) == []


def test_construct_quotes_spread_clamped_to_reward_band_in_quiet():
    # a wide computed half-spread (from vol/toxicity) should be clamped down to
    # the reward band. Empty book (no resting bid to join) isolates the pure
    # delta calculation from the separate "join the touch" placement rule.
    meta = _sample_market(tick=0.001, rewards_max_spread=2.0)  # 2% band
    empty_view = BookView(best_bid=None, best_ask=None, bid_depth=0.0, ask_depth=0.0)
    inp = QuoteInputs(
        meta=meta, regime=Regime.QUIET, fv=0.5, vol_short=0.05, toxicity=0.02,  # would otherwise blow the spread way out
        yes_view=empty_view, no_view=empty_view, profile=DEFAULT,
    )
    quotes = construct_quotes(inp)
    assert len(quotes) == 2
    for q in quotes:
        # price should stay within reward-band distance of 0.5 (half-spread clamped to the 2% band)
        assert abs(q.price - 0.5) <= 0.02 + 0.005


def test_construct_quotes_inventory_skew_reduces_add_size_on_long_side():
    meta = _sample_market()
    view = BookView(best_bid=0.49, best_ask=0.51, bid_depth=100.0, ask_depth=100.0)
    flat = construct_quotes(QuoteInputs(meta=meta, regime=Regime.QUIET, fv=0.5, vol_short=0.0, toxicity=0.0, yes_view=view, no_view=view, profile=DEFAULT))
    long_yes = construct_quotes(
        QuoteInputs(meta=meta, regime=Regime.QUIET, fv=0.5, vol_short=0.0, toxicity=0.0, yes_view=view, no_view=view, profile=DEFAULT, pos_yes_size=150.0)
    )
    flat_yes_size = next(q.size for q in flat if q.token_id == "yes-token")
    long_yes_size = next((q.size for q in long_yes if q.token_id == "yes-token"), 0.0)
    assert long_yes_size < flat_yes_size  # already long YES -> add less/no more YES


# ── risk ────────────────────────────────────────────────────────────────


def test_risk_manager_kills_on_daily_loss():
    risk = RiskManager(cfg=RiskConfig(daily_loss_kill_usdc=10.0))
    risk.reset_day()
    risk.note_fill("BUY", price=0.5, size=100.0)  # spend $50
    risk.update_mark("tok", 0.0)  # mark the position to worthless -> big paper loss
    risk.set_position("tok", size=100.0, avg_price=0.5)
    halted, reason = risk.global_halt()
    assert halted is True
    assert "daily_loss" in reason


def test_risk_manager_taper_scale_near_cap():
    risk = RiskManager(cfg=RiskConfig(max_market_notional_usdc=100.0, max_total_exposure_usdc=1000.0))
    risk.set_position("yes-token", size=180.0, avg_price=0.5)  # $90 notional, 90% of 100 cap
    risk.update_mark("yes-token", 0.5)
    d = risk.evaluate("yes-token", "no-token")
    assert d.halt is False
    assert d.reduce_only is False
    assert 0.0 < d.size_scale < 1.0  # tapered, not full size


def test_risk_manager_reduce_only_over_market_cap():
    risk = RiskManager(cfg=RiskConfig(max_market_notional_usdc=100.0))
    risk.set_position("yes-token", size=250.0, avg_price=0.5)  # $125 > $100 cap
    risk.update_mark("yes-token", 0.5)
    d = risk.evaluate("yes-token", "no-token")
    assert d.reduce_only is True
    assert d.size_scale == 1.0  # reduce-only means "exit-only", not "no size"


# ── gamma_scan (pure parsing/scoring, synthetic Gamma dict) ─────────────


def _raw_gamma_market(**overrides) -> dict:
    base = {
        "acceptingOrders": True,
        "clobTokenIds": '["111", "222"]',
        "outcomes": '["Yes", "No"]',
        "conditionId": "0xdead",
        "question": "Synthetic test market?",
        "slug": "synthetic-test-market",
        "orderPriceMinTickSize": 0.01,
        "negRisk": False,
        "orderMinSize": 5,
        "rewardsMinSize": 50,
        "rewardsMaxSpread": 4.5,
        "feeSchedule": {"rate": 0.05, "rebateRate": 0.25},
        "feesEnabled": True,
        "endDate": None,
        "events": [],
        "bestBid": 0.49,
        "bestAsk": 0.51,
        "liquidityNum": 5000.0,
        "volumeNum": 20000.0,
        "volume24hr": 500.0,
    }
    base.update(overrides)
    return base


def test_parse_market_rejects_non_binary():
    raw = _raw_gamma_market(outcomes='["A", "B", "C"]')
    assert parse_market(raw) is None


def test_parse_market_rejects_not_accepting_orders():
    raw = _raw_gamma_market(acceptingOrders=False)
    assert parse_market(raw) is None


def test_parse_market_happy_path_with_reward_rate():
    raw = _raw_gamma_market()
    meta = parse_market(raw, reward_rates={"0xdead": 42.0})
    assert meta is not None
    assert meta.rewards_daily_rate == 42.0
    assert meta.yes.token_id == "111"
    assert meta.no.token_id == "222"


def test_reward_density_zero_without_reward_program():
    raw = _raw_gamma_market(rewardsMaxSpread=0)
    meta = parse_market(raw, reward_rates={"0xdead": 42.0})
    assert reward_density(meta) == 0.0


def test_score_market_favors_near_50_50_low_extremity():
    balanced = parse_market(_raw_gamma_market(bestBid=0.49, bestAsk=0.51), reward_rates={"0xdead": 50.0})
    lopsided = parse_market(_raw_gamma_market(bestBid=0.02, bestAsk=0.03, conditionId="0xdead"), reward_rates={"0xdead": 50.0})
    s_balanced = score_market(balanced)
    s_lopsided = score_market(lopsided)
    assert s_balanced.extremity < s_lopsided.extremity
    assert s_balanced.score >= s_lopsided.score


# ── profiles ──────────────────────────────────────────────────────────


def test_profile_for_switches_on_liquidity():
    assert profile_for(10000.0).name == DEFAULT.name
    assert profile_for(100.0).name == THIN_BOOK.name


# ── live integration (real, no-auth Polymarket REST — proves §4 of spec) ─


@pytest.mark.live
def test_live_gamma_scan_returns_real_reward_markets():
    ranked = scan_reward_markets(min_liquidity=500.0, max_pages=3)
    assert len(ranked) > 0
    meta, score = ranked[0]
    assert meta.rewards_daily_rate > 0
    assert 0.0 < meta.tick_size < 1.0
    assert score.score >= 0.0


@pytest.mark.live
def test_live_book_fetch_returns_real_data():
    # a deep, long-lived reward market's YES token (Rihanna-before-GTA6, sampled
    # 2026-07-12) — if this specific market resolves/closes later, this test
    # may need a new token id; the live scan test above is the durable one.
    view = fetch_book("98022490269692409998126496127597032490334070080325855126491859374983463996227")
    assert view.best_bid is not None or view.best_ask is not None
    mp = microprice(view)
    assert 0.0 <= mp <= 1.0
