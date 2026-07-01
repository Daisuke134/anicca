"""Phase 2a RED — sprint-4 (d) recipe-6-actions grep/AST invariants.

PROP-I1-no-restart-cmd-map-called, PROP-I2-never-raises,
PROP-I3-no-slot-state-writes, PROP-I4-scaffold-set-empty-or-noop-only.
"""
from __future__ import annotations
import ast
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
STEP3_RECIPE = REPO_ROOT / "skills" / "_shared" / "lib" / "step3_recipe.py"


def test_I1_no_restart_cmd_map_called_from_non_restart_path():
    """PROP-I1: only the tmux_dead+restart branch uses default_restart_cmd_map."""
    src = STEP3_RECIPE.read_text()
    # cmd_map is a parameter — allowed. But default_restart_cmd_map only used in
    # the existing restart branch; grep for its literal usage outside there.
    # The 6 new wires MUST NOT reference cmd_map beyond the existing restart.
    # We enforce by grepping for cmd_map inside kill_server/send_keys/login/
    # npm_install/git_checkout/escalate_via_bot2bot branch bodies.
    for action in ("kill_server", "send_keys", "login", "npm_install",
                   "git_checkout", "escalate_via_bot2bot"):
        # Locate action block: `if action == "<action>":` … next `elif`/`if action`
        m = re.search(rf'if action == "{action}"', src)
        assert m, f"missing branch for {action}"
        start = m.start()
        # Look at next 30 lines of the branch
        chunk = src[start:start + 3000]
        # No cmd_map lookup in this branch
        assert "cmd_map" not in chunk.split("\n\n")[0], (
            f"PROP-I1 violation: {action} references cmd_map"
        )


def test_I2_never_raises_ast_guard():
    """PROP-I2: every subprocess.run call in step3_recipe.py is wrapped in try/except.
    """
    tree = ast.parse(STEP3_RECIPE.read_text())
    # Collect all subprocess.run call nodes
    run_calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if (isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "subprocess"
                    and node.func.attr == "run"):
                run_calls.append(node)
    assert len(run_calls) > 0, "no subprocess.run call found — expected 6 wires"

    # For each subprocess.run, verify it's inside a Try block ancestor
    for call in run_calls:
        parent_try_found = False
        # Walk up the tree
        for parent in ast.walk(tree):
            if isinstance(parent, ast.Try):
                # Check call is inside this Try's body
                for stmt in ast.walk(parent):
                    if stmt is call:
                        parent_try_found = True
                        break
            if parent_try_found:
                break
        assert parent_try_found, (
            f"PROP-I2 violation: subprocess.run at line {call.lineno} "
            f"not inside try/except"
        )


def test_I3_no_slot_state_writes():
    """PROP-I3: none of the 6 wires write under loops/<slot>/."""
    src = STEP3_RECIPE.read_text()
    # grep for any string literal or fstring targeting loops/<slot>/
    for pat in [r"loops/\{", r'"loops/', r"'loops/", r"\.jsonl", r"\.sentinel"]:
        # Allow appearance in comments only; look for actual references
        # in string literals.
        matches = re.findall(pat, src)
        assert not matches, (
            f"PROP-I3 violation: pattern {pat!r} found in step3_recipe.py "
            f"({len(matches)} occurrences)"
        )


def test_I4_scaffold_set_empty_or_noop_only():
    """PROP-I4: SCAFFOLD_DEFERRED_ACTIONS is empty OR {'noop'}."""
    src = STEP3_RECIPE.read_text()
    m = re.search(r"SCAFFOLD_DEFERRED_ACTIONS[^=]*=\s*frozenset\(\{([^}]*)\}\)", src)
    if m is None:
        # Also accept: SCAFFOLD_DEFERRED_ACTIONS: FrozenSet[str] = frozenset()
        assert "SCAFFOLD_DEFERRED_ACTIONS" in src, "constant missing"
        assert re.search(r"SCAFFOLD_DEFERRED_ACTIONS[^=]*=\s*frozenset\(\)", src) is not None, (
            "PROP-I4: SCAFFOLD_DEFERRED_ACTIONS must be empty frozenset or {noop}"
        )
        return
    body = m.group(1)
    entries = [e.strip().strip('"').strip("'") for e in body.split(",") if e.strip()]
    assert set(entries).issubset({"noop"}), (
        f"PROP-I4 violation: SCAFFOLD_DEFERRED_ACTIONS has non-noop entries: {entries}"
    )


def test_execute_recipe_signature_has_anicca_home():
    """FIND-002 fix: execute_recipe gains anicca_home kwarg."""
    tree = ast.parse(STEP3_RECIPE.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "execute_recipe":
            arg_names = [a.arg for a in node.args.kwonlyargs] + [a.arg for a in node.args.args]
            assert "anicca_home" in arg_names, (
                f"execute_recipe signature must include anicca_home kwarg; "
                f"got: {arg_names}"
            )
            return
    raise AssertionError("execute_recipe function not found")
