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
    history = [{"ts": NOW - 100, "amount_usd": 9.0, "status": "sent"}]
    d = check_caps(amount_usd=2.0, history=history, config=CONFIG, now_ts=NOW)
    assert d.allowed is False
    assert "daily cap" in d.reason


def test_daily_cap_ignores_spend_older_than_24h():
    history = [{"ts": NOW - 90000, "amount_usd": 9.0, "status": "sent"}]  # >24h old
    d = check_caps(amount_usd=2.0, history=history, config=CONFIG, now_ts=NOW)
    assert d.allowed is True


def test_daily_cap_ignores_failed_and_dry_rows():
    history = [
        {"ts": NOW - 10, "amount_usd": 9.0, "status": "failed"},
        {"ts": NOW - 10, "amount_usd": 9.0, "status": "dry"},
        {"ts": NOW - 10, "amount_usd": 9.0, "status": "skipped"},
    ]
    d = check_caps(amount_usd=2.0, history=history, config=CONFIG, now_ts=NOW)
    assert d.allowed is True


def test_cumulative_cap_blocks_across_many_days():
    history = [
        {"ts": NOW - (86400 * 10), "amount_usd": 48.0, "status": "sent"},
    ]
    d = check_caps(amount_usd=3.0, history=history, config=CONFIG, now_ts=NOW)
    assert d.allowed is False
    assert "cumulative cap" in d.reason


def test_caps_absent_from_config_means_unlimited():
    d = check_caps(amount_usd=1_000_000, history=[], config={}, now_ts=NOW)
    assert d.allowed is True


def test_reserve_protected_amount_never_negative():
    assert reserve_protected_amount(available_usd=3.0, reserve_usd=5.0) == 0.0


def test_reserve_protected_amount_normal_case():
    assert round(reserve_protected_amount(available_usd=19.26, reserve_usd=5.0), 6) == 14.26


def test_reserve_protected_amount_bad_inputs_fail_closed():
    assert reserve_protected_amount(available_usd="oops", reserve_usd=5.0) == 0.0
