"""RED phase — self-improve-real-ledger, Group RL-GATE (realized ledger data gates promotion,
REQ-RL7-13/RL13a) and Group RL-EVAL (honest data_source tagging, REQ-RL14/RL15).

Traces to behavioral-spec.md Groups RL-GATE/RL-EVAL, EDGE-RL1/RL3/RL4; verification-
architecture.md PROP-RL-GATE1-6, PROP-RL-GATE-NONE, PROP-RL-EVAL1/EVAL2.

`gate_math.realized_window_split`/`is_worsening_trend`/`realized_trend_blocks`/`data_realism_gap`,
`lib.promotion_history` (new file), `promote_gate.decide_promotion`'s `realized_gate` parameter,
`promote_gate_run`'s escalation-writing helper, and `ledger_reader.confirmed_net_series` all do NOT
exist yet at RED-phase time. Imports of not-yet-existing symbols are deferred into each test
function so one missing attribute fails only that test, mirroring test_ledger_resolution.py's
convention.
"""
import os
import re
import subprocess
from unittest import mock

import evaluator
from conftest import patched_baseline_code, write_candidate_with_fixtures
from lib import gate_math


# ============================================================================
# REQ-RL8 — realized_window_split
# ============================================================================


def test_realized_window_split_even_row_count_splits_at_midpoint():
    rows = [(110.0, 1.0), (120.0, 2.0), (160.0, 3.0), (170.0, 4.0)]

    result = gate_math.realized_window_split(rows, window_start_ts=100.0, window_end_ts=200.0)

    assert result["row_count"] == 4
    assert result["first_half_net_usd"] == 3.0
    assert result["second_half_net_usd"] == 7.0
    assert result["window_net_usd"] == 10.0


def test_realized_window_split_odd_row_count_splits_at_midpoint():
    rows = [(110.0, 1.0), (120.0, 2.0), (140.0, 3.0), (160.0, 4.0), (180.0, 5.0)]

    result = gate_math.realized_window_split(rows, window_start_ts=100.0, window_end_ts=200.0)

    assert result["row_count"] == 5
    assert result["first_half_net_usd"] == 6.0  # 110,120,140 (< midpoint 150)
    assert result["second_half_net_usd"] == 9.0  # 160,180 (>= midpoint 150)
    assert result["window_net_usd"] == 15.0


def test_realized_window_split_excludes_rows_outside_the_window():
    rows = [
        (90.0, 1000.0),  # before window_start_ts — must never count
        (110.0, 1.0),
        (170.0, 2.0),
        (250.0, 1000.0),  # at/after window_end_ts — must never count
    ]

    result = gate_math.realized_window_split(rows, window_start_ts=100.0, window_end_ts=200.0)

    assert result["row_count"] == 2
    assert result["window_net_usd"] == 3.0


# ============================================================================
# REQ-RL9/RL10 — is_worsening_trend / realized_trend_blocks truth table
# ============================================================================


def test_is_worsening_trend_is_strictly_less_than():
    assert gate_math.is_worsening_trend(first_half_net_usd=10.0, second_half_net_usd=5.0) is True
    assert gate_math.is_worsening_trend(first_half_net_usd=5.0, second_half_net_usd=5.0) is False
    assert gate_math.is_worsening_trend(first_half_net_usd=5.0, second_half_net_usd=10.0) is False


def test_realized_trend_blocks_8_combination_truth_table():
    # (window_net_usd, worsening, sufficient) -> expected blocks. blocks = sufficient AND
    # window_net_usd < 0.0 AND worsening (REQ-RL10).
    cases = [
        (-1.0, True, True, True),
        (-1.0, True, False, False),
        (-1.0, False, True, False),
        (-1.0, False, False, False),
        (1.0, True, True, False),
        (1.0, True, False, False),
        (1.0, False, True, False),
        (1.0, False, False, False),
    ]
    for window_net_usd, worsening, sufficient, expected in cases:
        got = gate_math.realized_trend_blocks(window_net_usd, worsening, sufficient)
        assert got == expected, (window_net_usd, worsening, sufficient, expected, got)


# ============================================================================
# REQ-RL11 — data_realism_gap
# ============================================================================


def test_data_realism_gap_case_a_fixture_claims_edge_reality_shows_none():
    assert gate_math.data_realism_gap(
        mean_backtest_net_usd=5.0, mean_realized_net_per_row=0.0, sufficient=True
    ) is True
    assert gate_math.data_realism_gap(
        mean_backtest_net_usd=5.0, mean_realized_net_per_row=-2.0, sufficient=True
    ) is True


def test_data_realism_gap_case_a_does_not_fire_when_backtest_itself_non_positive():
    assert gate_math.data_realism_gap(
        mean_backtest_net_usd=0.0, mean_realized_net_per_row=0.0, sufficient=True
    ) is False


def test_data_realism_gap_case_b_implausible_jump_over_real_per_trade_edge():
    assert gate_math.data_realism_gap(
        mean_backtest_net_usd=5.0, mean_realized_net_per_row=1.0, sufficient=True, multiple=3.0
    ) is True


def test_data_realism_gap_case_b_boundary_is_strict_greater_than():
    assert gate_math.data_realism_gap(
        mean_backtest_net_usd=3.0, mean_realized_net_per_row=1.0, sufficient=True, multiple=3.0
    ) is False


def test_data_realism_gap_never_fires_when_insufficient_regardless_of_other_inputs():
    assert gate_math.data_realism_gap(
        mean_backtest_net_usd=5.0, mean_realized_net_per_row=0.0, sufficient=False
    ) is False
    assert gate_math.data_realism_gap(
        mean_backtest_net_usd=50.0, mean_realized_net_per_row=1.0, sufficient=False, multiple=3.0
    ) is False


# ============================================================================
# REQ-RL7 / REQ-RL18 / spec-review F-4 — decide_promotion's realized_gate parameter
# ============================================================================


def _eligible_assessment(tmp_path):
    # Same edit as test_adversary_disapprove.py::_good_candidate — a genuine selection change
    # against the committed baseline that clears every deterministic gate.
    from lib import promote_gate

    code = patched_baseline_code(
        ('config.get("min_edge", 0.25)', 'config.get("min_edge", 0.26)'),
        ('config.get("max_stake", 12.0)', 'config.get("max_stake", 10.0)'),
    )
    candidate_path = write_candidate_with_fixtures(tmp_path, code)
    assessment = promote_gate.assess_candidate(candidate_path)
    assert assessment["eligible_for_adversary_review"] is True  # precondition sanity check
    return assessment


def _unresolved_realized_gate():
    return {
        "resolved": False,
        "resolution_source": "unresolved_no_file_context",
        "ledger_path": "",
        "row_count": 0,
        "sufficient": False,
        "window_net_usd": 0.0,
        "first_half_net_usd": 0.0,
        "second_half_net_usd": 0.0,
        "worsening": False,
        "trend_blocks": False,
        "realism_gap_blocks": False,
        "window_start_ts": 0.0,
        "window_end_ts": 0.0,
    }


def test_resolved_false_blocks_promotion_unconditionally_even_with_adversary_pass(tmp_path):
    from lib import promote_gate

    assessment = _eligible_assessment(tmp_path)

    decision = promote_gate.decide_promotion(
        assessment, "PASS", realized_gate=_unresolved_realized_gate()
    )

    assert decision["promote"] is False


def test_gate_none_vacuous_pass_vs_unconditional_block_side_by_side(tmp_path):
    """spec-review F-4: the SAME assessment+adversary-PASS inputs must produce promote:True with
    realized_gate=None (REQ-RL18 vacuous pass) and promote:False with realized_gate={"resolved":
    False, ...} (REQ-RL7 unconditional block) — one test, two assertions, no ambiguity."""
    from lib import promote_gate

    assessment = _eligible_assessment(tmp_path)

    decision_vacuous = promote_gate.decide_promotion(assessment, "PASS", realized_gate=None)
    decision_blocked = promote_gate.decide_promotion(
        assessment, "PASS", realized_gate=_unresolved_realized_gate()
    )

    assert decision_vacuous["promote"] is True
    assert decision_blocked["promote"] is False


# ============================================================================
# REQ-RL12 / EDGE-RL3 — lib.promotion_history.last_promotion_ts
# ============================================================================


def _init_git_repo_with_promotion_commits(tmp_path, commit_specs):
    """commit_specs: list of (unix_ts, subject) tuples, applied in order. Real git init/commit,
    not mocked — cheap and fully hermetic (mirrors PROP-RL-GATE5's own documented method)."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@self-improve-real-ledger.local"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "self-improve-real-ledger tests"], cwd=tmp_path, check=True)

    strategy_dir = tmp_path / "strategies"
    strategy_dir.mkdir(exist_ok=True)
    strategy_path = strategy_dir / "pm_backtest_strategy.py"

    for i, (ts, subject) in enumerate(commit_specs):
        strategy_path.write_text(f"# revision {i}\n")
        subprocess.run(["git", "add", "--", str(strategy_path)], cwd=tmp_path, check=True)
        date_str = f"{int(ts)} +0000"
        env = dict(os.environ, GIT_AUTHOR_DATE=date_str, GIT_COMMITTER_DATE=date_str)
        subprocess.run(
            ["git", "commit", "-q", "-m", subject, "--", str(strategy_path)],
            cwd=tmp_path, check=True, env=env,
        )
    return str(strategy_path)


def test_last_promotion_ts_returns_the_latest_matching_commits_timestamp(tmp_path):
    from lib import promotion_history

    strategy_path = _init_git_repo_with_promotion_commits(
        tmp_path,
        [
            (1_700_000_000, "feat(self-improve): promote candidate aaa111"),
            (1_700_000_500, "chore: unrelated commit touching the same path"),
            (1_700_001_000, "feat(self-improve): promote candidate bbb222"),
        ],
    )

    result = promotion_history.last_promotion_ts(strategy_path, cwd=str(tmp_path))

    assert result == 1_700_001_000


def test_last_promotion_ts_returns_none_when_no_promotion_commit_exists(tmp_path):
    from lib import promotion_history

    strategy_path = _init_git_repo_with_promotion_commits(
        tmp_path, [(1_700_000_000, "chore: initial commit, never promoted")]
    )

    result = promotion_history.last_promotion_ts(strategy_path, cwd=str(tmp_path))

    assert result is None


# ============================================================================
# REQ-RL13 — escalation record written BEFORE decide_promotion returns its block
# ============================================================================


def test_realized_gate_escalation_json_written_with_documented_keys(tmp_path):
    from lib import promote_gate_run

    synthetic_gate = {
        "resolved": True,
        "resolution_source": "anicca_home_env",
        "ledger_path": "/tmp/fake/earn-ledger.jsonl",
        "row_count": 8,
        "sufficient": True,
        "window_net_usd": -12.5,
        "first_half_net_usd": -2.0,
        "second_half_net_usd": -10.5,
        "worsening": True,
        "trend_blocks": True,
        "realism_gap_blocks": False,
        "window_start_ts": 1_700_000_000.0,
        "window_end_ts": 1_700_100_000.0,
    }

    promote_gate_run.write_realized_gate_escalation(
        run_dir=str(tmp_path), realized_gate=synthetic_gate, candidate_path="fake/candidate.py"
    )

    escalation_path = tmp_path / "realized_gate_escalation.json"
    assert escalation_path.is_file()

    import json

    written = json.loads(escalation_path.read_text(encoding="utf-8"))
    assert written["candidate_path"] == "fake/candidate.py"
    assert written["window_net_usd"] == -12.5
    assert written["worsening"] is True
    assert written["realism_gap_blocks"] is False
    assert "reason" in written and isinstance(written["reason"], str) and len(written["reason"]) > 0


# ============================================================================
# REQ-RL14/RL15 — honest data_source tagging
# ============================================================================


def test_evaluate_data_source_flips_but_combined_score_stays_identical():
    with mock.patch("lib.ledger_reader.confirmed_net_series") as mocked:
        mocked.return_value = [(1.0, 1.0)] * 3  # below MIN_REALIZED_ROWS_FOR_TREND (6)
        result_low = evaluator.evaluate(evaluator.BASELINE_PATH)

    with mock.patch("lib.ledger_reader.confirmed_net_series") as mocked:
        mocked.return_value = [(1.0, 1.0)] * 6  # at MIN_REALIZED_ROWS_FOR_TREND
        result_high = evaluator.evaluate(evaluator.BASELINE_PATH)

    assert result_low["data_source"] == "fixture"
    assert result_high["data_source"] == "fixture+realized-crosscheck"
    assert result_low["combined_score"] == result_high["combined_score"]


def test_no_bare_data_source_equals_real_literal_anywhere_in_self_improve():
    """REQ-RL15 honesty invariant, disclosed in sprint-1.md CRIT-005: this is a permanent
    CI-style safety net and is EXPECTED TO ALREADY PASS in the RED baseline (nothing asserts the
    forbidden literal yet, since REQ-RL14 isn't implemented) — not a proof a gap currently
    exists. Excludes tests/ (this file's own regex source text would otherwise self-match) and
    evidence/ (frozen historical candidate snapshots, not live harness code)."""
    self_improve_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pattern = re.compile(r'data_source' + r'.*==.*"real"')
    hits = []
    for root, _, files in os.walk(self_improve_dir):
        if "/tests" in root.replace(os.sep, "/") or "/evidence" in root.replace(os.sep, "/"):
            continue
        for fn in files:
            if not fn.endswith(".py"):
                continue
            path = os.path.join(root, fn)
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
            if pattern.search(text):
                hits.append(path)
    assert hits == []
