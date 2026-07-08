import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.caps import check_caps, reserve_protected_amount  # noqa: E402

CONFIG = {"per_transfer_usd_cap": 5.0, "daily_usd_cap": 10.0, "cumulative_usd_cap": 50.0}
NOW = 1_000_000.0


def test_within_all_caps_allowed():
    d = check_caps(amount_usd=2.0, history=[], config=CONFIG, now_ts=NOW)
    assert d.allowed is True
    assert d.amount_usd == 2.0


def test_non_positive_amount_rejected():
    d = check_caps(amount_usd=0, history=[], config=CONFIG, now_ts=NOW)
    assert d.allowed is False
    d2 = check_caps(amount_usd=-1, history=[], config=CONFIG, now_ts=NOW)
    assert d2.allowed is False


def test_per_transfer_cap_blocks_oversized_amount():
    d = check_caps(amount_usd=5.01, history=[], config=CONFIG, now_ts=NOW)
    assert d.allowed is False
    assert "per-transfer" in d.reason


def test_daily_cap_blocks_when_already_spent_today():
    history = [{"ts": NOW - 100, "amount_usd": 9.0, "status": "sent", "step": "withdraw"}]
    d = check_caps(amount_usd=2.0, history=history, config=CONFIG, now_ts=NOW)
    assert d.allowed is False
    assert "daily cap" in d.reason


def test_daily_cap_ignores_spend_older_than_24h():
    history = [{"ts": NOW - 90000, "amount_usd": 9.0, "status": "sent", "step": "withdraw"}]  # >24h old
    d = check_caps(amount_usd=2.0, history=history, config=CONFIG, now_ts=NOW)
    assert d.allowed is True


def test_daily_cap_ignores_failed_and_dry_rows():
    history = [
        {"ts": NOW - 10, "amount_usd": 9.0, "status": "failed", "step": "withdraw"},
        {"ts": NOW - 10, "amount_usd": 9.0, "status": "dry", "step": "withdraw"},
        {"ts": NOW - 10, "amount_usd": 9.0, "status": "skipped", "step": "withdraw"},
    ]
    d = check_caps(amount_usd=2.0, history=history, config=CONFIG, now_ts=NOW)
    assert d.allowed is True


def test_cumulative_cap_blocks_across_many_days():
    history = [
        {"ts": NOW - (86400 * 10), "amount_usd": 48.0, "status": "sent", "step": "withdraw"},
    ]
    d = check_caps(amount_usd=3.0, history=history, config=CONFIG, now_ts=NOW)
    assert d.allowed is False
    assert "cumulative cap" in d.reason


def test_caps_absent_from_config_means_unlimited():
    d = check_caps(amount_usd=1_000_000, history=[], config={}, now_ts=NOW)
    assert d.allowed is True


# --- Finding C fix (2026-07-08): only the withdraw hop counts as real outflow from claude-p
# capital -- bridge/send_to_franklin 'sent' rows must NOT also consume cap headroom, since
# they move the SAME already-withdrawn money onward, not a second/third fresh outflow. ---


def test_bridge_and_send_sent_rows_do_not_double_count_the_cap():
    # One logical $9 seed produces three 'sent' rows (withdraw, bridge, send_to_franklin),
    # exactly as run.py's pipeline does. Only the withdraw row should count toward the cap --
    # a naive "sum all sent rows" implementation would count this as $27 spent today and
    # wrongly block a further $2 (9*3 + 2 > 10 daily cap), even though real outflow from
    # claude-p capital is only $9.
    history = [
        {"ts": NOW - 100, "amount_usd": 9.0, "status": "sent", "step": "withdraw", "tx_hash": "0xw1"},
        {"ts": NOW - 90, "amount_usd": 9.0, "status": "sent", "step": "bridge", "tx_hash": "0xb1"},
        {"ts": NOW - 80, "amount_usd": 9.0, "status": "sent", "step": "send_to_franklin", "tx_hash": "solsig1"},
    ]
    d = check_caps(amount_usd=1.0, history=history, config=CONFIG, now_ts=NOW)
    assert d.allowed is True


def test_bridge_and_send_only_history_means_zero_prior_outflow():
    # If, hypothetically, the ledger only had bridge/send_to_franklin rows (no withdraw row),
    # they must not count as outflow at all -- withdraw is the only real outflow event. Use a
    # small new amount (<= per-transfer cap) so only the daily/cumulative accounting is under
    # test here, isolated from the per-transfer check.
    history = [
        {"ts": NOW - 100, "amount_usd": 9.0, "status": "sent", "step": "bridge", "tx_hash": "0xb2"},
        {"ts": NOW - 90, "amount_usd": 9.0, "status": "sent", "step": "send_to_franklin", "tx_hash": "solsig2"},
    ]
    d = check_caps(amount_usd=4.9, history=history, config=CONFIG, now_ts=NOW)
    assert d.allowed is True


# --- Finding A fix (2026-07-08): a 'pending' row (broadcast recorded before confirmation
# resolves) must still consume cap headroom, since the money may already have moved. When a
# later 'sent' row for the SAME tx_hash is appended, the pair must count ONCE, not twice. ---


def test_pending_withdraw_row_consumes_cap_headroom():
    history = [
        {"ts": NOW - 10, "amount_usd": 9.0, "status": "pending", "step": "withdraw", "tx_hash": "0xp1"},
    ]
    d = check_caps(amount_usd=2.0, history=history, config=CONFIG, now_ts=NOW)
    assert d.allowed is False
    assert "daily cap" in d.reason


def test_pending_then_sent_same_tx_hash_counts_once():
    # Simulates: pending row written immediately after broadcast, then a terminal 'sent' row
    # for the SAME tx_hash written once confirmation succeeds. Must not double-count as $18.
    history = [
        {"ts": NOW - 10, "amount_usd": 9.0, "status": "pending", "step": "withdraw", "tx_hash": "0xp2"},
        {"ts": NOW - 5, "amount_usd": 9.0, "status": "sent", "step": "withdraw", "tx_hash": "0xp2"},
    ]
    d = check_caps(amount_usd=1.0, history=history, config=CONFIG, now_ts=NOW)
    assert d.allowed is True  # 9 (once) + 1 == 10, exactly at the daily cap, still allowed
    d2 = check_caps(amount_usd=1.01, history=history, config=CONFIG, now_ts=NOW)
    assert d2.allowed is False  # 9 (once) + 1.01 > 10 would exceed it


def test_pending_without_tx_hash_still_counts_individually():
    # amount_usd stays <= the per-transfer cap (5.0) so this isolates the daily-cap check --
    # 8.0 already pending + 3.0 requested exceeds the 10.0 daily cap.
    history = [
        {"ts": NOW - 10, "amount_usd": 8.0, "status": "pending", "step": "withdraw"},
    ]
    d = check_caps(amount_usd=3.0, history=history, config=CONFIG, now_ts=NOW)
    assert d.allowed is False
    assert "daily cap" in d.reason


def test_reserve_protected_amount_never_negative():
    assert reserve_protected_amount(available_usd=3.0, reserve_usd=5.0) == 0.0


def test_reserve_protected_amount_normal_case():
    assert round(reserve_protected_amount(available_usd=19.26, reserve_usd=5.0), 6) == 14.26


def test_reserve_protected_amount_bad_inputs_fail_closed():
    assert reserve_protected_amount(available_usd="oops", reserve_usd=5.0) == 0.0
