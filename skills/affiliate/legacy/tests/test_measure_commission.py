"""Unit tests for measure_commission (PURE, no subprocess/CDP). Run: python3 test_measure_commission.py
Dummy amazon_report_fn/ledger_record_fn are injected -- no real browser/node call happens here.
Reference: docs/superpowers/specs/2026-07-05-affiliate-bounty-state-machine-design.md §2/§5.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from measure_commission import measure_commission  # noqa: E402

NOW = 1_700_000_000  # fixed epoch


def _tmp_watermark():
    fd, path = tempfile.mkstemp()
    os.close(fd)
    os.remove(path)  # measure_commission must handle a non-existent watermark file
    return path


def test_first_ever_check_no_commission():
    wm = _tmp_watermark()
    recorded = []
    r = measure_commission(wm, recorded.append, NOW,
                            lambda: {"commission_jpy": 0, "asof": "2026-07-05 12:00 JST", "ordered_items": 0})
    assert r["status"] == "new-month-baseline"
    assert recorded == []


def test_first_ever_check_with_commission_records_it():
    wm = _tmp_watermark()
    recorded = []
    r = measure_commission(wm, recorded.append, NOW,
                            lambda: {"commission_jpy": 500, "asof": "2026-07-05 12:00 JST", "ordered_items": 1})
    assert r["status"] == "new-month-baseline-recorded"
    assert len(recorded) == 1
    assert recorded[0]["amount_jpy"] == 500
    assert recorded[0]["source"] == "amazon_report"
    assert recorded[0]["report_date"] == "2026-07-05"
    assert recorded[0]["report_export_id"]  # non-empty


def test_same_month_no_change():
    wm = _tmp_watermark()
    recorded = []
    measure_commission(wm, recorded.append, NOW,
                        lambda: {"commission_jpy": 500, "asof": "2026-07-05 12:00 JST", "ordered_items": 1})
    r = measure_commission(wm, recorded.append, NOW + 3600,
                            lambda: {"commission_jpy": 500, "asof": "2026-07-05 13:00 JST", "ordered_items": 1})
    assert r["status"] == "no-change"
    assert len(recorded) == 1  # only the first call recorded anything


def test_same_month_increase_records_delta_only():
    wm = _tmp_watermark()
    recorded = []
    measure_commission(wm, recorded.append, NOW,
                        lambda: {"commission_jpy": 500, "asof": "2026-07-05 12:00 JST", "ordered_items": 1})
    r = measure_commission(wm, recorded.append, NOW + 3600,
                            lambda: {"commission_jpy": 800, "asof": "2026-07-05 13:00 JST", "ordered_items": 2})
    assert r["status"] == "recorded"
    assert r["delta_jpy"] == 300
    assert len(recorded) == 2
    assert recorded[1]["amount_jpy"] == 300  # delta, not the cumulative 800


def test_month_rollover_records_new_month_value_not_cross_month_delta():
    """The critical GATE 1 round-3 fix: month-boundary must not compute (new - old_month_baseline)."""
    wm = _tmp_watermark()
    recorded = []
    measure_commission(wm, recorded.append, NOW,
                        lambda: {"commission_jpy": 300, "asof": "2026-07-31 23:00 JST", "ordered_items": 1})
    r = measure_commission(wm, recorded.append, NOW + 3600,
                            lambda: {"commission_jpy": 500, "asof": "2026-08-01 09:00 JST", "ordered_items": 1})
    assert r["status"] == "new-month-baseline-recorded"
    assert len(recorded) == 2
    assert recorded[1]["amount_jpy"] == 500  # the new month's own value, NOT 500-300=200


def test_error_from_amazon_report_is_surfaced_not_crashed():
    wm = _tmp_watermark()
    recorded = []
    r = measure_commission(wm, recorded.append, NOW, lambda: {"error": "not logged in"})
    assert r["status"] == "error"
    assert recorded == []


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
