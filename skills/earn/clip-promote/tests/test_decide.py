"""Unit tests for the PURE clip-promote state machine. Run: python3 -m pytest -q (or python3 test_decide.py)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from decide import decide  # noqa: E402

NOW = 1_700_000_000  # fixed epoch for deterministic DEAD_ZERO_HOURS math


def test_empty_or_idle_selects():
    assert decide(None, NOW) == "SELECT"
    assert decide({}, NOW) == "SELECT"
    assert decide({"phase": "idle"}, NOW) == "SELECT"
    assert decide({"phase": "STALLED"}, NOW) == "SELECT"
    assert decide({"phase": "RECORD"}, NOW) == "SELECT"  # after a DONE, free the slot


def test_linear_pipeline():
    assert decide({"phase": "SELECT"}, NOW) == "SELECT"
    assert decide({"phase": "CLIP"}, NOW) == "CLIP"
    assert decide({"phase": "POST"}, NOW) == "POST"
    assert decide({"phase": "SUBMIT"}, NOW) == "SUBMIT"


def test_measure_keeps_measuring_when_accepted_and_not_ended():
    s = {"phase": "MEASURE", "submit_status": "accepted", "views": 0, "posted_at": NOW - 3600}
    assert decide(s, NOW) == "MEASURE"  # 1h in, 0 views = legitimate early-zero


def test_measure_rejected_submission_stalls():
    assert decide({"phase": "MEASURE", "submit_status": "rejected"}, NOW) == "STALLED"


def test_dead_zero_hours_boundary():
    # just BEFORE 48h with 0 views → still measuring
    s = {"phase": "MEASURE", "submit_status": "accepted", "views": 0, "posted_at": NOW - (48 * 3600 - 60)}
    assert decide(s, NOW) == "MEASURE"
    # AT/after 48h with 0 views → stalled (honest dead discriminator)
    s2 = {"phase": "MEASURE", "submit_status": "accepted", "views": 0, "posted_at": NOW - 48 * 3600}
    assert decide(s2, NOW) == "STALLED"
    # past 48h but views>0 → keep measuring (it IS earning views)
    s3 = {"phase": "MEASURE", "submit_status": "accepted", "views": 5, "posted_at": NOW - 100 * 3600}
    assert decide(s3, NOW) == "MEASURE"


def test_campaign_ended_with_balance_withdraws():
    s = {"phase": "MEASURE", "submit_status": "accepted", "campaign_ended": True, "withdrawable_usdc": 0.5, "views": 100, "posted_at": NOW - 3600}
    assert decide(s, NOW) == "WITHDRAW"
    # ended but zero withdrawable → keep measuring (nothing to claim yet)
    s2 = dict(s); s2["withdrawable_usdc"] = 0
    assert decide(s2, NOW) == "MEASURE"


def test_withdraw_then_record():
    assert decide({"phase": "WITHDRAW"}, NOW) == "WITHDRAW"  # no sig yet
    assert decide({"phase": "WITHDRAW", "sig": "52RZ...sig"}, NOW) == "RECORD"


def test_unknown_phase_is_safe_select():
    assert decide({"phase": "garbage"}, NOW) == "SELECT"


if __name__ == "__main__":
    import traceback
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn(); print(f"  ok  {fn.__name__}")
        except Exception:
            failed += 1; print(f"  FAIL {fn.__name__}"); traceback.print_exc()
    print(f"\n{len(fns)-failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
