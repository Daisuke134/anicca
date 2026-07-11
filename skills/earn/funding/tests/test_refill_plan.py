import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.refill_plan import (  # noqa: E402
    GAS_FILL_MIN_DELIVERED_PCT,
    GAS_MAX_FEE_PCT,
    GAS_PER_INVOCATION_USD_CAP,
    GAS_RESERVE_USD,
    GAS_STEP,
    MAX_FEE_PCT,
    NATIVE_ETH_BASE,
    PER_INVOCATION_USD_CAP,
    RESERVE_USD,
    STEP,
    AmountDecision,
    FeeDecision,
    assert_own_citizen_row,
    build_refill_plan,
    evaluate_native_delivery,
    evaluate_relay_fee,
    has_unresolved_pending,
    is_valid_evm_address,
    select_refill_amount,
)


# --- select_refill_amount (REQ-003 / PROP-001,002,003) ---


def test_select_refill_amount_below_reserve_refuses():
    d = select_refill_amount(balance_usd=4.99)
    assert d.allowed is False
    assert d.amount_usd == 0.0


def test_select_refill_amount_exact_reserve_refuses():
    d = select_refill_amount(balance_usd=5.00)
    assert d.allowed is False


def test_select_refill_amount_between_reserve_and_cap_uses_headroom():
    d = select_refill_amount(balance_usd=9.00)  # headroom = 4.00, below the 6.50 cap
    assert d.allowed is True
    assert d.amount_usd == 4.00


def test_select_refill_amount_at_exact_cap_boundary():
    d = select_refill_amount(balance_usd=11.50)  # headroom = 6.50, exactly the cap
    assert d.allowed is True
    assert d.amount_usd == 6.50


def test_select_refill_amount_above_cap_clips_to_cap():
    d = select_refill_amount(balance_usd=13.02)  # Franklin's actual balance at spec time
    assert d.allowed is True
    assert d.amount_usd == PER_INVOCATION_USD_CAP


def test_select_refill_amount_never_exceeds_cap_property():
    for balance in [5.01, 6, 8, 11.5, 20, 100, 1000]:
        d = select_refill_amount(balance_usd=balance)
        assert d.amount_usd <= PER_INVOCATION_USD_CAP


def test_select_refill_amount_never_dips_below_reserve_property():
    for balance in [5.01, 6, 8, 11.5, 20, 100]:
        d = select_refill_amount(balance_usd=balance)
        assert balance - d.amount_usd >= RESERVE_USD - 1e-9


def test_select_refill_amount_explicit_request_below_ceiling_honored():
    d = select_refill_amount(balance_usd=20.0, requested_usd=2.0)
    assert d.allowed is True
    assert d.amount_usd == 2.0


def test_select_refill_amount_explicit_request_above_ceiling_clipped():
    d = select_refill_amount(balance_usd=13.02, requested_usd=100.0)
    assert d.allowed is True
    assert d.amount_usd == PER_INVOCATION_USD_CAP


def test_select_refill_amount_explicit_request_would_break_reserve_clipped():
    d = select_refill_amount(balance_usd=6.0, requested_usd=5.0)  # headroom is only 1.00
    assert d.allowed is True
    assert d.amount_usd == 1.00


def test_select_refill_amount_zero_or_negative_requested_refused():
    assert select_refill_amount(balance_usd=20.0, requested_usd=0).allowed is False
    assert select_refill_amount(balance_usd=20.0, requested_usd=-3).allowed is False


def test_select_refill_amount_never_negative_property():
    for balance in [-5, 0, 3, 4.999, 5, 5.0001, 20]:
        d = select_refill_amount(balance_usd=balance)
        assert d.amount_usd >= 0.0


def test_select_refill_amount_bad_balance_type_fails_closed():
    d = select_refill_amount(balance_usd="oops")
    assert d.allowed is False
    assert d.amount_usd == 0.0


# --- evaluate_relay_fee (REQ-004 / PROP-004) ---


def test_evaluate_relay_fee_within_cap_allowed():
    d = evaluate_relay_fee(in_usd=6.50, out_usd=6.20)  # fee ~4.6%
    assert d.allowed is True


def test_evaluate_relay_fee_exactly_at_cap_allowed():
    d = evaluate_relay_fee(in_usd=100.0, out_usd=92.0)  # exactly 8%
    assert d.allowed is True
    assert round(d.fee_pct, 6) == MAX_FEE_PCT


def test_evaluate_relay_fee_just_over_cap_refused():
    d = evaluate_relay_fee(in_usd=100.0, out_usd=91.99)  # 8.01%
    assert d.allowed is False


def test_evaluate_relay_fee_out_exceeds_in_never_refuses_on_fee():
    d = evaluate_relay_fee(in_usd=6.50, out_usd=6.60)
    assert d.allowed is True


def test_evaluate_relay_fee_zero_in_usd_refused():
    d = evaluate_relay_fee(in_usd=0, out_usd=0)
    assert d.allowed is False


def test_evaluate_relay_fee_missing_fields_refused():
    d = evaluate_relay_fee(in_usd=None, out_usd=None)
    assert d.allowed is False


# --- assert_own_citizen_row (REQ-002 / PROP-005) ---

FRANKLIN_ROW = {
    "id": "Franklin",
    "walletAddress": {
        "solana": "8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9",
        "evm": "0x3EcCAD24794ca298D25378E9902A251322ea8749",
    },
}
FRANKLIN2_ROW = {
    "id": "Franklin2",
    "walletAddress": {
        "solana": "HyJHSfTkLjpmqeY4FEbnSjM4DfUh9ELGchHqgFDBkrcX",
        "evm": "0xe7747Fd899D8987821Bb4CB3D6aDf22565F87ce9",
    },
}


def test_assert_own_citizen_row_matches_correct_row():
    m = assert_own_citizen_row(
        citizens=[FRANKLIN_ROW, FRANKLIN2_ROW],
        derived_solana_pubkey=FRANKLIN_ROW["walletAddress"]["solana"],
    )
    assert m.ok is True
    assert m.citizen_id == "Franklin"
    assert m.base_address == FRANKLIN_ROW["walletAddress"]["evm"]


def test_assert_own_citizen_row_no_match_refuses():
    m = assert_own_citizen_row(
        citizens=[FRANKLIN_ROW, FRANKLIN2_ROW],
        derived_solana_pubkey="SomeUnrelatedPubkeyThatMatchesNoRow1111",
    )
    assert m.ok is False
    assert m.base_address is None


def test_assert_own_citizen_row_never_cross_instance():
    # A key derived to Franklin2's own address must NEVER resolve to Franklin's Base address.
    m = assert_own_citizen_row(
        citizens=[FRANKLIN_ROW, FRANKLIN2_ROW],
        derived_solana_pubkey=FRANKLIN2_ROW["walletAddress"]["solana"],
    )
    assert m.base_address == FRANKLIN2_ROW["walletAddress"]["evm"]
    assert m.base_address != FRANKLIN_ROW["walletAddress"]["evm"]


def test_assert_own_citizen_row_ambiguous_multiple_matches_refuses():
    duplicate = dict(FRANKLIN_ROW)
    m = assert_own_citizen_row(
        citizens=[FRANKLIN_ROW, duplicate],
        derived_solana_pubkey=FRANKLIN_ROW["walletAddress"]["solana"],
    )
    assert m.ok is False


def test_assert_own_citizen_row_malformed_rows_ignored_not_crashed():
    m = assert_own_citizen_row(
        citizens=[{"id": "broken"}, FRANKLIN_ROW],
        derived_solana_pubkey=FRANKLIN_ROW["walletAddress"]["solana"],
    )
    assert m.ok is True
    assert m.citizen_id == "Franklin"


def test_assert_own_citizen_row_empty_pubkey_refuses():
    m = assert_own_citizen_row(citizens=[FRANKLIN_ROW], derived_solana_pubkey="")
    assert m.ok is False


def test_assert_own_citizen_row_missing_evm_address_refuses():
    row = {"id": "Ghost", "walletAddress": {"solana": "GhostPubkey1111111111111111111111111111"}}
    m = assert_own_citizen_row(citizens=[row], derived_solana_pubkey="GhostPubkey1111111111111111111111111111")
    assert m.ok is False
    assert m.base_address is None


# --- has_unresolved_pending (REQ-005 / PROP-006) ---


def test_has_unresolved_pending_empty_ledger_false():
    assert has_unresolved_pending(ledger_rows=[], step=STEP) is False


def test_has_unresolved_pending_resolved_pending_false():
    rows = [
        {"step": STEP, "status": "pending", "tx_hash": "sig1"},
        {"step": STEP, "status": "sent", "tx_hash": "sig1"},
    ]
    assert has_unresolved_pending(ledger_rows=rows, step=STEP) is False


def test_has_unresolved_pending_unresolved_true():
    rows = [{"step": STEP, "status": "pending", "tx_hash": "sig2"}]
    assert has_unresolved_pending(ledger_rows=rows, step=STEP) is True


def test_has_unresolved_pending_ignores_other_steps():
    rows = [{"step": "withdraw", "status": "pending", "tx_hash": "sigX"}]
    assert has_unresolved_pending(ledger_rows=rows, step=STEP) is False


def test_has_unresolved_pending_untracked_pending_blocks():
    rows = [{"step": STEP, "status": "pending"}]  # no tx_hash at all
    assert has_unresolved_pending(ledger_rows=rows, step=STEP) is True


def test_has_unresolved_pending_order_independent():
    rows = [
        {"step": STEP, "status": "sent", "tx_hash": "sig3"},
        {"step": STEP, "status": "pending", "tx_hash": "sig3"},
    ]
    assert has_unresolved_pending(ledger_rows=rows, step=STEP) is False


def test_has_unresolved_pending_failed_terminal_also_resolves():
    rows = [
        {"step": STEP, "status": "pending", "tx_hash": "sig4"},
        {"step": STEP, "status": "failed", "tx_hash": "sig4"},
    ]
    assert has_unresolved_pending(ledger_rows=rows, step=STEP) is False


# --- build_refill_plan (PROP-007) ---


def test_build_refill_plan_no_mutation_of_extra():
    extra = {"note": "x"}
    cap_decision = AmountDecision(True, "within caps", 3.0)
    plan = build_refill_plan(
        sender_solana="Sender111",
        recipient_base="0xRecipient",
        amount_usd=3.0,
        balance_usd=13.02,
        cap_decision=cap_decision,
        extra=extra,
    )
    assert plan["amount_usd"] == 3.0
    assert plan["note"] == "x"
    assert extra == {"note": "x"}  # calling build_refill_plan must not mutate the caller's dict


def test_build_refill_plan_includes_fee_fields_when_given():
    cap_decision = AmountDecision(True, "within caps", 3.0)
    fee_decision = FeeDecision(True, "within fee cap", 4.5)
    plan = build_refill_plan(
        sender_solana="Sender111",
        recipient_base="0xRecipient",
        amount_usd=3.0,
        balance_usd=13.02,
        cap_decision=cap_decision,
        fee_decision=fee_decision,
    )
    assert plan["fee_pct"] == 4.5
    assert plan["fee_allowed"] is True


def test_build_refill_plan_fee_fields_none_when_omitted():
    cap_decision = AmountDecision(False, "no headroom", 0.0)
    plan = build_refill_plan(
        sender_solana="Sender111",
        recipient_base="0xRecipient",
        amount_usd=0.0,
        balance_usd=4.99,
        cap_decision=cap_decision,
    )
    assert plan["fee_pct"] is None
    assert plan["fee_allowed"] is None


# --- Gas-ETH mode caps (REQ-GAS-001..005) -- select_refill_amount/evaluate_relay_fee are
# already generic pure functions, reused here with the gas-mode literals instead of new pure
# functions (only the constants differ). ---


def test_gas_cap_constants_are_smaller_and_never_weaken_usdc_mode():
    assert GAS_PER_INVOCATION_USD_CAP == 3.00
    assert GAS_RESERVE_USD == 3.00
    assert GAS_MAX_FEE_PCT == 12.0
    assert GAS_STEP == "franklin_gas_eth_refill"
    assert GAS_STEP != STEP
    assert NATIVE_ETH_BASE == "0x0000000000000000000000000000000000000000"


def test_select_refill_amount_gas_mode_at_exact_cap_boundary():
    # headroom = 6.44 - 3.00 = 3.44, above the 3.00 cap -> clips to the cap
    d = select_refill_amount(
        balance_usd=6.44, reserve_usd=GAS_RESERVE_USD, per_invocation_cap_usd=GAS_PER_INVOCATION_USD_CAP
    )
    assert d.allowed is True
    assert d.amount_usd == GAS_PER_INVOCATION_USD_CAP


def test_select_refill_amount_gas_mode_below_reserve_refuses():
    d = select_refill_amount(
        balance_usd=2.99, reserve_usd=GAS_RESERVE_USD, per_invocation_cap_usd=GAS_PER_INVOCATION_USD_CAP
    )
    assert d.allowed is False
    assert d.amount_usd == 0.0


def test_select_refill_amount_gas_mode_never_exceeds_gas_cap_property():
    for balance in [3.01, 4, 6, 6.44, 100]:
        d = select_refill_amount(
            balance_usd=balance,
            reserve_usd=GAS_RESERVE_USD,
            per_invocation_cap_usd=GAS_PER_INVOCATION_USD_CAP,
        )
        assert d.amount_usd <= GAS_PER_INVOCATION_USD_CAP
        assert balance - d.amount_usd >= GAS_RESERVE_USD - 1e-9


def test_evaluate_relay_fee_gas_mode_exactly_at_12pct_allowed():
    d = evaluate_relay_fee(in_usd=3.00, out_usd=2.64, max_fee_pct=GAS_MAX_FEE_PCT)  # exactly 12%
    assert d.allowed is True
    assert round(d.fee_pct, 6) == GAS_MAX_FEE_PCT


def test_evaluate_relay_fee_gas_mode_just_over_12pct_refused():
    d = evaluate_relay_fee(in_usd=3.00, out_usd=2.639, max_fee_pct=GAS_MAX_FEE_PCT)  # ~12.03%
    assert d.allowed is False


def test_evaluate_relay_fee_gas_mode_within_usdc_mode_default_would_refuse():
    # 10% fee: refused under the USDC-mode default 8% cap, but allowed under gas mode's 12% cap
    # -- confirms the two modes' caps are genuinely independent, never accidentally shared.
    assert evaluate_relay_fee(in_usd=3.00, out_usd=2.70).allowed is False  # default MAX_FEE_PCT=8
    assert evaluate_relay_fee(in_usd=3.00, out_usd=2.70, max_fee_pct=GAS_MAX_FEE_PCT).allowed is True


def test_has_unresolved_pending_gas_step_ignores_usdc_step_rows():
    rows = [{"step": STEP, "status": "pending", "tx_hash": "sigX"}]
    assert has_unresolved_pending(ledger_rows=rows, step=GAS_STEP) is False


# --- is_valid_evm_address (REQ-GAS-002: recipient is required, never a default) ---
# FIND-003 (impl iteration-3): returns the NORMALIZED (stripped, lower-cased) address string on
# success, `None` on any failure -- never a bare bool -- so callers can bind the SAME normalized
# value everywhere downstream instead of re-using the original, possibly-unstripped candidate.


def test_is_valid_evm_address_accepts_well_formed_address_returns_lowercased():
    assert (
        is_valid_evm_address("0x1F5b17f41524B02a4ee4d99D4158c86C942e43f3")
        == "0x1f5b17f41524b02a4ee4d99d4158c86c942e43f3"
    )


def test_is_valid_evm_address_strips_and_lowercases_whitespace_padded_address():
    """FIND-003 regression: the exact validate-vs-use mismatch this finding closed -- a
    whitespace-padded candidate must validate AND return the stripped/lowercased form, never
    the original padded string."""
    assert (
        is_valid_evm_address("  0x1F5b17f41524B02a4ee4d99D4158c86C942e43f3\n")
        == "0x1f5b17f41524b02a4ee4d99d4158c86c942e43f3"
    )


def test_is_valid_evm_address_rejects_none():
    assert is_valid_evm_address(None) is None


def test_is_valid_evm_address_rejects_empty_string():
    assert is_valid_evm_address("") is None


def test_is_valid_evm_address_rejects_missing_0x_prefix():
    assert is_valid_evm_address("1F5b17f41524B02a4ee4d99D4158c86C942e43f3") is None


def test_is_valid_evm_address_rejects_wrong_length():
    assert is_valid_evm_address("0x1234") is None


def test_is_valid_evm_address_rejects_non_hex_characters():
    assert is_valid_evm_address("0x" + "z" * 40) is None


def test_is_valid_evm_address_rejects_non_string_type():
    assert is_valid_evm_address(0x1234) is None


# --- evaluate_native_delivery (REQ-GAS-004: independent eth_getBalance-delta verification --
# native ETH has no ERC-20 Transfer log, so the delta itself is the tx-specific evidence) ---


def test_evaluate_native_delivery_full_delivery_verified():
    d = evaluate_native_delivery(
        balance_before_wei=0, balance_after_wei=1_000_000_000_000_000, expected_wei=1_000_000_000_000_000
    )
    assert d.verified is True
    assert d.delivered_wei == 1_000_000_000_000_000


def test_evaluate_native_delivery_at_exact_85_pct_floor_verified():
    expected = 1_000_000_000_000_000
    delivered = int(round(expected * 0.85))
    d = evaluate_native_delivery(
        balance_before_wei=0, balance_after_wei=delivered, expected_wei=expected
    )
    assert d.verified is True


def test_evaluate_native_delivery_just_under_85_pct_refused():
    expected = 1_000_000_000_000_000
    delivered = int(round(expected * 0.84))
    d = evaluate_native_delivery(
        balance_before_wei=0, balance_after_wei=delivered, expected_wei=expected
    )
    assert d.verified is False


def test_evaluate_native_delivery_zero_delta_refused():
    d = evaluate_native_delivery(balance_before_wei=5_000, balance_after_wei=5_000, expected_wei=1_000)
    assert d.verified is False
    assert d.delivered_wei == 0


def test_evaluate_native_delivery_negative_delta_refused():
    """An unrelated concurrent outflow during the same window must never be misread as a fill."""
    d = evaluate_native_delivery(balance_before_wei=5_000, balance_after_wei=4_000, expected_wei=1_000)
    assert d.verified is False
    assert d.delivered_wei == -1_000


def test_evaluate_native_delivery_unrelated_small_inflow_below_threshold_refused():
    """A tiny unrelated inflow (e.g. dust) must not be mistaken for the real fill."""
    d = evaluate_native_delivery(balance_before_wei=0, balance_after_wei=1, expected_wei=1_000_000_000_000_000)
    assert d.verified is False


def test_evaluate_native_delivery_non_int_input_fails_closed():
    d = evaluate_native_delivery(balance_before_wei="oops", balance_after_wei=100, expected_wei=100)
    assert d.verified is False
    assert d.delivered_wei == 0


def test_evaluate_native_delivery_bool_input_fails_closed():
    # bool is technically an int subclass in Python -- must be explicitly rejected, mirroring
    # select_refill_amount's/evaluate_relay_fee's existing isinstance(..., bool) guards.
    d = evaluate_native_delivery(balance_before_wei=True, balance_after_wei=100, expected_wei=100)
    assert d.verified is False


def test_evaluate_native_delivery_zero_expected_wei_refused():
    """FIND-002 (impl iteration-3, CRITICAL): expected_wei == 0 must be a REFUSAL, not a
    silent bypass of the 85% floor. Before this fix, `min_required` was hard-coded to 0
    whenever expected_wei <= 0, so ANY positive delta -- even 1 wei -- verified as True."""
    d = evaluate_native_delivery(balance_before_wei=0, balance_after_wei=1, expected_wei=0)
    assert d.verified is False
    assert "positive" in d.reason.lower()


def test_evaluate_native_delivery_negative_expected_wei_refused():
    """FIND-002: same bypass, negative variant (e.g. a malformed relay-quote sign flip)."""
    d = evaluate_native_delivery(
        balance_before_wei=0, balance_after_wei=1_000_000, expected_wei=-1
    )
    assert d.verified is False
    assert "positive" in d.reason.lower()


def test_evaluate_native_delivery_zero_expected_wei_refused_even_with_large_delta():
    """The FIND-002 bypass was reachable with ANY positive delta, not just tiny ones --
    confirm a large, otherwise-plausible-looking delivery is still refused when expected_wei
    itself is degenerate (there is nothing to verify the delta AGAINST)."""
    d = evaluate_native_delivery(
        balance_before_wei=0, balance_after_wei=5_000_000_000_000_000, expected_wei=0
    )
    assert d.verified is False


def test_evaluate_native_delivery_default_pct_matches_constant():
    expected = 1_000_000_000_000_000
    just_under_default = int(round(expected * (GAS_FILL_MIN_DELIVERED_PCT / 100))) - 1
    d = evaluate_native_delivery(
        balance_before_wei=0, balance_after_wei=just_under_default, expected_wei=expected
    )
    assert d.verified is False
