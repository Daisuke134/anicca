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
