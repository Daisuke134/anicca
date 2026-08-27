#!/usr/bin/env python3
"""Pure-logic tests for self_critique.py. Never touches the real decision log or the real
self-improve evaluator harness — promote_gate wiring is tested with a monkeypatched loader so a
unit test run can never trigger a real (slow, backtest-dependent) evaluation.

Run: python3 -m pytest test_self_critique.py -q     (or: python3 test_self_critique.py)
"""
import self_critique as sc


def _rec(action, pnl_cum=None, naked=False, kill_reason=None, pick_reason=None):
    r = {"action": action}
    if kill_reason:
        r["reason"] = kill_reason
    if pnl_cum is not None:
        r["pnl"] = {"cumulative_realized_usdc": pnl_cum, "today_realized_usdc": 0}
    if naked:
        r["market_maker"] = {"reason": "naked leg detected", "naked_leg_warning": True}
    if pick_reason:
        r["pick"] = {"reason": pick_reason}
    return r


def test_summarize_counts_actions_and_naked_warnings():
    records = [
        _rec("no_trade", pnl_cum=1.0, naked=True, pick_reason="no-candidate"),
        _rec("no_trade", pnl_cum=1.0, pick_reason="no-candidate"),
        _rec("skip", kill_reason="kill-switch active: frozen"),
    ]
    out = sc.summarize(records)
    assert out["cycles"] == 3
    assert out["action_counts"]["no_trade"] == 2
    assert out["action_counts"]["skip"] == 1
    assert out["naked_leg_warning_count"] == 1
    assert out["kill_switch_skip_count"] == 1


def test_summarize_daily_guard_trip_counted():
    records = [_rec("skip", kill_reason="daily-loss-limit-breached: today_net=-5.00")]
    out = sc.summarize(records)
    assert out["daily_guard_trip_count"] == 1


def test_loss_pattern_insufficient_data_below_threshold():
    records = [_rec("no_trade", pnl_cum=1.0) for _ in range(5)]
    out = sc.find_loss_preceding_reasons(records)
    assert out["sufficient_data"] is False
    assert "insufficient history" in out["verdict"]


def test_loss_pattern_no_losses_with_enough_data():
    records = [_rec("no_trade", pnl_cum=float(i)) for i in range(25)]  # monotonically increasing
    out = sc.find_loss_preceding_reasons(records)
    assert out["sufficient_data"] is True
    assert out["losses_observed"] == 0


def test_loss_pattern_detects_drop_and_attributes_reason():
    records = [_rec("no_trade", pnl_cum=float(i)) for i in range(24)]
    records.append(_rec("no_trade", pnl_cum=10.0, pick_reason="bought a loser"))  # index 23->24 drop context
    # force a real drop at the very last step, with a known prior reason
    records[-2]["pick"] = {"reason": "bought a loser"}
    records[-1]["pnl"]["cumulative_realized_usdc"] = records[-2]["pnl"]["cumulative_realized_usdc"] - 5.0
    out = sc.find_loss_preceding_reasons(records)
    assert out["sufficient_data"] is True
    assert out["losses_observed"] >= 1
    assert "bought a loser" in out["preceding_reasons"]


def test_propose_threshold_change_rejects_unknown_param():
    out = sc.propose_threshold_change("NOT_A_REAL_KNOB", 1, 2, "because")
    assert out["accepted"] is False


def test_propose_threshold_change_accepts_known_param_but_never_applies():
    out = sc.propose_threshold_change("MIN_EDGE", 0.15, 0.12, "5 no_trades at 0.14 that would have won")
    assert out["accepted"] is True
    assert "not applied" in out["status"].lower()


def test_submit_candidate_uses_real_promote_gate_api(monkeypatch):
    calls = {}

    class FakeGate:
        @staticmethod
        def assess_candidate(candidate_path, config=None):
            calls["candidate_path"] = candidate_path
            calls["config"] = config
            return {"eligible_for_adversary_review": False, "stage1_pass": False}

    monkeypatch.setattr(sc, "_load_promote_gate", lambda: FakeGate)
    out = sc.submit_candidate_for_gate_assessment("/fake/candidate.py")
    assert out["eligible_for_adversary_review"] is False
    assert calls["candidate_path"] == "/fake/candidate.py"


def test_build_report_flags_naked_leg_and_insufficient_data():
    records = [_rec("no_trade", pnl_cum=1.0, naked=True, pick_reason="no-candidate")]
    report = sc.build_report(records)
    assert any("naked" in r.lower() for r in report["recommendations"])
    assert any("insufficient" in r.lower() for r in report["recommendations"])
    assert report["note"].startswith("No threshold was changed")


if __name__ == "__main__":
    import sys
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            if "monkeypatch" in fn.__code__.co_varnames[: fn.__code__.co_argcount]:
                print(f"SKIP {fn.__name__} (needs pytest monkeypatch fixture, run via pytest)")
                continue
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {fn.__name__}: {e}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed (pytest recommended for full coverage)")
    sys.exit(1 if failed else 0)
