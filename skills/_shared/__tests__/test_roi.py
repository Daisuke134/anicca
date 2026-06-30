"""PROP-B2-cost-formula (required:true, Tier 1) + PROP-B6-estimate (NOT required).

Spec: behavioral-spec.md REQ-B2 closed-form + per-model rate table (Sonnet/Opus/Haiku/Fable).
Closes FIND-002 critical ambiguity + TRAP-5 token-rich illusion.

Rate table frozen 2026-07-01 in spec; do NOT hard-code rates in tests except for
golden-fixture assertions — pass them in as arguments to keep the test-of-formula
independent of the published rate.
"""
import pytest

from lib.roi import compute_token_cost_jpy  # FAIL until 2b


SPEC_RATES = {
    "sonnet": (3.00, 15.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "opus": (15.00, 75.00),
    "claude-opus-4-7": (15.00, 75.00),
    "claude-opus-4-8": (15.00, 75.00),
    "haiku": (1.00, 5.00),
    "haiku-4-5": (1.00, 5.00),
    "claude-haiku-4-5-20251001": (1.00, 5.00),
    "fable": (3.00, 15.00),
    "claude-fable-5": (3.00, 15.00),
}


def _rates_dict():
    inp = {k: v[0] for k, v in SPEC_RATES.items()}
    out = {k: v[1] for k, v in SPEC_RATES.items()}
    return inp, out


# ── golden fixture from spec ─────────────────────────────────────────
def test_sonnet_1M_in_1M_out_at_FX150_equals_2700_jpy():
    """Spec REQ-B2: (1M in × 3 + 1M out × 15) × 150 FX = 2700.00 JPY."""
    inp, out = _rates_dict()
    cost = compute_token_cost_jpy(
        model_breakdown=[{"model_id": "sonnet", "tokens_in": 1_000_000, "tokens_out": 1_000_000}],
        rates_input=inp,
        rates_output=out,
        fx_usdjpy=150.0,
        token_source="measured",
    )
    assert abs(cost - 2700.00) < 0.01


# ── TRAP-5: never zero for non-zero tokens, every model ──────────────
@pytest.mark.parametrize(
    "model_id",
    ["sonnet", "opus", "haiku", "fable", "claude-opus-4-8", "haiku-4-5"],
)
def test_nonzero_tokens_always_yield_positive_cost(model_id):
    inp, out = _rates_dict()
    cost = compute_token_cost_jpy(
        model_breakdown=[{"model_id": model_id, "tokens_in": 1, "tokens_out": 1}],
        rates_input=inp,
        rates_output=out,
        fx_usdjpy=150.0,
        token_source="measured",
    )
    assert cost > 0


# ── REQ-B2: unknown model raises (no silent zero) ────────────────────
def test_unknown_model_raises_not_silently_zero():
    inp, out = _rates_dict()
    with pytest.raises(Exception):
        compute_token_cost_jpy(
            model_breakdown=[{"model_id": "gpt-5-pro", "tokens_in": 100, "tokens_out": 50}],
            rates_input=inp,
            rates_output=out,
            fx_usdjpy=150.0,
            token_source="measured",
        )


# ── REQ-B2: FX applies to ENTIRE USD total, not just output term ─────
def test_fx_applies_to_full_usd_total():
    inp = {"sonnet": 10.0}
    out = {"sonnet": 10.0}
    cost = compute_token_cost_jpy(
        model_breakdown=[{"model_id": "sonnet", "tokens_in": 1_000_000, "tokens_out": 1_000_000}],
        rates_input=inp,
        rates_output=out,
        fx_usdjpy=100.0,
        token_source="measured",
    )
    # (1×10 + 1×10) × 100 = 2000
    # If FX wrongly only on output term: 1×10 + (1×10×100) = 1010 — that's a bug.
    assert cost == pytest.approx(2000.0, abs=0.01)


# ── mixed-model breakdown sums correctly ─────────────────────────────
def test_mixed_sonnet_opus_breakdown():
    inp, out = _rates_dict()
    cost = compute_token_cost_jpy(
        model_breakdown=[
            {"model_id": "sonnet", "tokens_in": 100_000, "tokens_out": 50_000},
            {"model_id": "opus", "tokens_in": 10_000, "tokens_out": 5_000},
        ],
        rates_input=inp,
        rates_output=out,
        fx_usdjpy=150.0,
        token_source="measured",
    )
    expected_usd = (
        (100_000 / 1_000_000) * 3.0
        + (50_000 / 1_000_000) * 15.0
        + (10_000 / 1_000_000) * 15.0
        + (5_000 / 1_000_000) * 75.0
    )
    assert cost == pytest.approx(expected_usd * 150.0, abs=0.01)


# ── PROP-B6 estimate path 2× penalty ────────────────────────────────
def test_estimated_token_source_doubles_cost():
    inp, out = _rates_dict()
    measured = compute_token_cost_jpy(
        model_breakdown=[{"model_id": "sonnet", "tokens_in": 1_000_000, "tokens_out": 0}],
        rates_input=inp,
        rates_output=out,
        fx_usdjpy=150.0,
        token_source="measured",
    )
    estimated = compute_token_cost_jpy(
        model_breakdown=[{"model_id": "sonnet", "tokens_in": 1_000_000, "tokens_out": 0}],
        rates_input=inp,
        rates_output=out,
        fx_usdjpy=150.0,
        token_source="estimated",
    )
    assert estimated == pytest.approx(measured * 2.0, abs=0.01)
