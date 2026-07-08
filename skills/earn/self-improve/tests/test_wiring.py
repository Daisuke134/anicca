"""RED phase — self-improve-real-ledger, Group RL-WIRE (end-to-end wiring, no orphan
implementation, REQ-RL16/RL17) and REQ-RL13a (the canonical realized_gate schema).

Traces to behavioral-spec.md REQ-RL13a, Group RL-WIRE; verification-architecture.md
PROP-RL-WIRE1/WIRE2.

`lib.promote_gate.compute_realized_gate` does not exist yet, and `promote_gate_run.py`'s three
`decide_promotion` call sites do not pass `realized_gate=` yet — both tests below are EXPECTED TO
FAIL at RED-phase time.
"""
import ast
import os

# --- REQ-RL13a: compute_realized_gate's canonical 13-key schema ---
#
# compute_realized_gate's exact call signature is not pinned by behavioral-spec.md beyond its
# name and the effectful-shell description ("assembles the pure gate_math calls' inputs" over
# "THIS instance's own resolved ledger" + "promotion_history.last_promotion_ts"). This test pins
# a concrete signature for Phase 2b to implement against — mean_backtest_net_usd (REQ-RL11's
# fixture-side comparison input, which only the caller/evaluator knows), `env` (REQ-RL1's
# injection convention, reused here rather than invented fresh), and `repo_cwd` (REQ-RL12's git
# log needs a repo path) — deliberately mirroring existing conventions in this codebase
# (assess_candidate's own `config`/`population_best` optional-parameter style) rather than
# inventing a new one.

REALIZED_GATE_SCHEMA_KEYS = frozenset(
    {
        "resolved",
        "resolution_source",
        "ledger_path",
        "row_count",
        "sufficient",
        "window_net_usd",
        "first_half_net_usd",
        "second_half_net_usd",
        "worsening",
        "trend_blocks",
        "realism_gap_blocks",
        "window_start_ts",
        "window_end_ts",
    }
)


def test_compute_realized_gate_returns_exactly_the_req_rl13a_schema(tmp_path):
    import subprocess

    from lib import promote_gate

    # Disposable git repo so last_promotion_ts's internal git-log call has something to run
    # against (EDGE-RL3: zero promotion commits -> window_start_ts = 0.0, per REQ-RL12).
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    (tmp_path / "strategies").mkdir()
    (tmp_path / "strategies" / "pm_backtest_strategy.py").write_text("# seed\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "chore: seed, never promoted"], cwd=tmp_path, check=True)

    result = promote_gate.compute_realized_gate(
        mean_backtest_net_usd=5.0, env={"ANICCA_HOME": str(tmp_path)}, repo_cwd=str(tmp_path)
    )

    assert set(result.keys()) == REALIZED_GATE_SCHEMA_KEYS, (
        f"realized_gate schema drift: extra={set(result.keys()) - REALIZED_GATE_SCHEMA_KEYS}, "
        f"missing={REALIZED_GATE_SCHEMA_KEYS - set(result.keys())}"
    )


# --- PROP-RL-WIRE1: every decide_promotion call site in promote_gate_run.py's own source text
#     carries an explicit realized_gate= keyword argument (no orphan bare-form wiring, REQ-RL17) ---


def test_promote_gate_run_wires_realized_gate_at_every_decide_promotion_call_site():
    self_improve_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    source_path = os.path.join(self_improve_dir, "lib", "promote_gate_run.py")
    with open(source_path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=source_path)

    call_sites = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        is_decide_promotion_call = (
            isinstance(func, ast.Attribute) and func.attr == "decide_promotion"
        ) or (isinstance(func, ast.Name) and func.id == "decide_promotion")
        if is_decide_promotion_call:
            call_sites.append(node)

    assert len(call_sites) >= 1, "expected at least one decide_promotion call site in promote_gate_run.py"

    missing_realized_gate = [
        node.lineno for node in call_sites
        if not any(kw.arg == "realized_gate" for kw in node.keywords)
    ]

    assert missing_realized_gate == [], (
        f"decide_promotion call site(s) at line(s) {missing_realized_gate} omit realized_gate= "
        "(REQ-RL17: no orphan wiring permitted at promote_gate_run.py's production call sites)"
    )


# --- F-1 regression (Phase 3 impl review, iteration 1): promote_gate_run.py's ONE
#     compute_realized_gate call site MUST pass assessment["mean_oos_net_usd"] (REQ-RL11's
#     DOLLAR-scale per-trade mean) as mean_backtest_net_usd=, never assessment["combined_score"]
#     (evaluator.py's unitless Sharpe-like risk-adjusted ratio, 0-10ish, capped 500) ---


def _subscript_key(node) -> object:
    """Extract the string/constant key of an `assessment["some_key"]`-shaped ast.Subscript node,
    across the py3.8 ast.Index wrapper and the py3.9+ direct-Constant slice shapes. Returns None
    for any other node shape (not a plain literal-keyed subscript)."""
    if not isinstance(node, ast.Subscript):
        return None
    slice_node = node.slice
    if isinstance(slice_node, ast.Constant):
        return slice_node.value
    # py3.8 ast.Index wrapper (has its own .value holding the real Constant)
    inner = getattr(slice_node, "value", None)
    if isinstance(inner, ast.Constant):
        return inner.value
    return None


def test_promote_gate_run_computes_realized_gate_from_mean_oos_net_usd_not_combined_score():
    self_improve_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    source_path = os.path.join(self_improve_dir, "lib", "promote_gate_run.py")
    with open(source_path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=source_path)

    call_sites = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        is_compute_realized_gate_call = (
            isinstance(func, ast.Attribute) and func.attr == "compute_realized_gate"
        ) or (isinstance(func, ast.Name) and func.id == "compute_realized_gate")
        if is_compute_realized_gate_call:
            call_sites.append(node)

    assert len(call_sites) >= 1, "expected at least one compute_realized_gate call site in promote_gate_run.py"

    missing_field_sites = []
    wrong_field_sites = []
    for node in call_sites:
        kw = next((kw for kw in node.keywords if kw.arg == "mean_backtest_net_usd"), None)
        if kw is None:
            missing_field_sites.append(node.lineno)
            continue
        key = _subscript_key(kw.value)
        if key != "mean_oos_net_usd":
            wrong_field_sites.append((node.lineno, key))

    assert missing_field_sites == [], (
        f"compute_realized_gate call site(s) at line(s) {missing_field_sites} omit "
        "mean_backtest_net_usd= entirely"
    )
    assert wrong_field_sites == [], (
        f"compute_realized_gate call site(s) at line(s) {wrong_field_sites} pass a field other "
        "than assessment['mean_oos_net_usd'] as mean_backtest_net_usd= (F-1: REQ-RL11 requires the "
        "DOLLAR-scale mean_oos_net_usd, never the unitless combined_score ratio)"
    )


def _seed_realistic_ledger(tmp_path):
    """A resolvable per-instance ledger with 6 confirmed rows (>= gate_math.MIN_REALIZED_ROWS_FOR_
    TREND) at a realistic, small dollar-scale net_usdc average (~$0.25/row) -- the same order of
    magnitude a genuine `mean_oos_net_usd` (REQ-RL11's dollar-scale per-window OOS mean) would
    report, and roughly an order of magnitude below a genuine unitless `combined_score` (Sharpe-
    like ratio, evaluator.py docs it as 0-10ish). Timestamps are anchored to real wall-clock time
    (not a fixed future/past constant) so they always fall inside compute_realized_gate's
    `[window_start_ts=0.0, window_end_ts=time.time())` operating window regardless of when this
    test runs."""
    import json
    import time

    ledger_dir = tmp_path / "skills" / "earn" / "state"
    ledger_dir.mkdir(parents=True)
    ledger_path = ledger_dir / "earn-ledger.jsonl"
    now = time.time()
    net_values = [0.10, 0.20, 0.30, 0.20, 0.30, 0.40]  # sum=1.50, mean=0.25
    rows = [
        {
            "ts": now - 1000 + i * 10,
            "source": "polymarket-redeem",
            "net_usdc": net,
            "external": True,
            "tx": "0xabc",
            "status": "0x1",
        }
        for i, net in enumerate(net_values)
    ]
    ledger_path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return str(ledger_path)


def _seed_never_promoted_repo(tmp_path):
    import subprocess

    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    (tmp_path / "strategies").mkdir()
    (tmp_path / "strategies" / "pm_backtest_strategy.py").write_text("# seed\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "chore: seed, never promoted"], cwd=tmp_path, check=True)


def test_realized_gate_field_sensitivity_correct_vs_wrong_scale(tmp_path):
    """F-1: compute_realized_gate's data_realism_gap comparison is scale-sensitive by design
    (REQ-RL11) -- this test proves it, with the exact representative values the Phase-3 adversary
    finding cited: a genuine dollar-scale mean_oos_net_usd (~$0.30) against a real per-row ledger
    average (~$0.25) does NOT contradict the real track record (no block); the unitless
    combined_score (~2.5, a Sharpe-like ratio, evaluator.py: 0-10ish) fed into the SAME dollar-scale
    comparison DOES look like an implausible >3x jump over the real per-row average and wrongly
    blocks. This is exactly why promote_gate_run.py:239-241's field choice (regression-tested
    above) is not a cosmetic detail."""
    from lib import promote_gate

    _seed_never_promoted_repo(tmp_path)
    _seed_realistic_ledger(tmp_path)
    env = {"ANICCA_HOME": str(tmp_path)}

    result_correct = promote_gate.compute_realized_gate(
        mean_backtest_net_usd=0.3, env=env, repo_cwd=str(tmp_path)
    )
    assert result_correct["sufficient"] is True
    assert result_correct["row_count"] == 6
    assert result_correct["realism_gap_blocks"] is False

    result_wrong = promote_gate.compute_realized_gate(
        mean_backtest_net_usd=2.5, env=env, repo_cwd=str(tmp_path)
    )
    assert result_wrong["realism_gap_blocks"] is True


def test_realized_gate_none_mean_backtest_net_usd_is_safe_and_skips_realism_check_only(tmp_path):
    """F-1 None-safety: compute_realized_gate is called UNCONDITIONALLY at promote_gate_run.py's
    call site, before assess_candidate()'s eligibility check -- and a scope-guard-rejected or
    stage1-failed candidate's assessment reports mean_oos_net_usd=None (promote_gate.py:56,64).
    Feeding None straight into gate_math.data_realism_gap's `float(mean_backtest_net_usd)` would
    raise TypeError. Required behavior (REQ-RL11's own "fixture backtest claims X" framing has no
    meaning when there IS no fixture claim): mean_backtest_net_usd=None must never crash, must
    never fire realism_gap_blocks (the fixture-vs-reality contradiction is undefined, not
    trivially true or false), and must NOT suppress the independent REQ-RL10 trend check -- proven
    here by a ledger with a genuine negative worsening trend that still blocks via trend_blocks."""
    import json
    import time

    from lib import promote_gate

    _seed_never_promoted_repo(tmp_path)

    ledger_dir = tmp_path / "skills" / "earn" / "state"
    ledger_dir.mkdir(parents=True)
    ledger_path = ledger_dir / "earn-ledger.jsonl"
    now = time.time()
    # First half positive, second half more negative -> worsening=True, window_net_usd<0.0 ->
    # realized_trend_blocks fires independently of the (None) realism-gap input.
    net_values = [1.0, 1.0, 1.0, -2.0, -2.0, -2.0]
    rows = [
        {
            "ts": now - 1000 + i * 10,
            "source": "polymarket-redeem",
            "net_usdc": net,
            "external": True,
            "tx": "0xabc",
            "status": "0x1",
        }
        for i, net in enumerate(net_values)
    ]
    ledger_path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    env = {"ANICCA_HOME": str(tmp_path)}

    result = promote_gate.compute_realized_gate(
        mean_backtest_net_usd=None, env=env, repo_cwd=str(tmp_path)
    )

    assert result["realism_gap_blocks"] is False
    assert result["sufficient"] is True
    assert result["worsening"] is True
    assert result["trend_blocks"] is True
