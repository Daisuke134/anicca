"""PROP-R1, PROP-R1a, PROP-R2, PROP-R3, PROP-R4 unit tests for lib.step3_recipe.

execute_recipe(recipe, issue_kind, slot, cmd_map, timeout) returns a
{ok, status} dict. Subprocess is invoked only when issue_kind=='tmux_dead'
AND recipe['action']=='restart'.
"""
from __future__ import annotations
from pathlib import Path
import pytest

from lib.step3_recipe import execute_recipe, SCAFFOLD_DEFERRED_ACTIONS


# ─── PROP-R1: restart only when tmux_dead ─────────────────────────
def test_restart_invokes_subprocess_for_tmux_dead(tmp_path):
    cmd_log = tmp_path / "cmd-log.txt"
    fake_cmd = tmp_path / "fake-restart.sh"
    fake_cmd.write_text(f"#!/bin/bash\necho \"$@\" > {cmd_log}\nexit 0\n")
    fake_cmd.chmod(0o755)
    r = execute_recipe(
        recipe={"action": "restart", "params": {}},
        issue_kind="tmux_dead",
        slot="gig",
        cmd_map={"gig": ["bash", str(fake_cmd), "--restart"]},
        timeout=5,
    )
    assert r["ok"] is True
    assert "restart-ok" in r["status"]
    assert cmd_log.exists()
    assert "--restart" in cmd_log.read_text()


# ─── PROP-R1a: stale + restart → suppressed (NO subprocess) ───────
def test_stale_restart_is_suppressed(tmp_path):
    cmd_log = tmp_path / "cmd-log.txt"
    fake_cmd = tmp_path / "fake-restart.sh"
    fake_cmd.write_text(f"#!/bin/bash\necho INVOKED > {cmd_log}\nexit 0\n")
    fake_cmd.chmod(0o755)
    r = execute_recipe(
        recipe={"action": "restart", "params": {}},
        issue_kind="stale",
        slot="gig",
        cmd_map={"gig": ["bash", str(fake_cmd), "--restart"]},
        timeout=5,
    )
    assert r["ok"] is True  # graceful = the tick proceeds
    assert r["status"] == "stale-suppressed-INV-P1"
    assert not cmd_log.exists(), "PROP-R1a violation: subprocess invoked on stale"


# ─── PROP-R2: rc != 0 → logged, no crash ───────────────────────────
def test_restart_failure_logged_no_crash(tmp_path):
    fake_cmd = tmp_path / "fail.sh"
    fake_cmd.write_text("#!/bin/bash\nexit 78\n")
    fake_cmd.chmod(0o755)
    r = execute_recipe(
        recipe={"action": "restart", "params": {}},
        issue_kind="tmux_dead",
        slot="gig",
        cmd_map={"gig": ["bash", str(fake_cmd)]},
        timeout=5,
    )
    assert r["ok"] is False
    assert "rc78" in r["status"]


def test_restart_timeout_logged(tmp_path):
    fake_cmd = tmp_path / "slow.sh"
    fake_cmd.write_text("#!/bin/bash\nsleep 10\n")
    fake_cmd.chmod(0o755)
    r = execute_recipe(
        recipe={"action": "restart", "params": {}},
        issue_kind="tmux_dead",
        slot="gig",
        cmd_map={"gig": ["bash", str(fake_cmd)]},
        timeout=1,  # < 10s sleep
    )
    assert r["ok"] is False
    assert "timeout" in r["status"]


# ─── PROP-R3: all 7 sprint-4 actions scaffold-deferred ────────────
@pytest.mark.parametrize("action", [
    "kill_server", "send_keys", "login", "npm_install",
    "git_checkout", "escalate_via_bot2bot", "noop",
])
def test_sprint4_actions_no_subprocess(action, tmp_path):
    cmd_log = tmp_path / "cmd-log.txt"
    fake_cmd = tmp_path / "shouldnt-run.sh"
    fake_cmd.write_text(f"#!/bin/bash\necho INVOKED > {cmd_log}\n")
    fake_cmd.chmod(0o755)
    r = execute_recipe(
        recipe={"action": action, "params": {}},
        issue_kind="tmux_dead",  # even for tmux_dead issue, non-restart = scaffold
        slot="gig",
        cmd_map={"gig": ["bash", str(fake_cmd)]},
        timeout=5,
    )
    assert r["ok"] is True
    assert "scaffold-deferred-sprint-4" in r["status"]
    assert action in r["status"]
    assert not cmd_log.exists()


# ─── PROP-R3 catch-all: unknown action ─────────────────────────────
def test_unknown_action_caught(tmp_path):
    r = execute_recipe(
        recipe={"action": "future_action_xyz", "params": {}},
        issue_kind="tmux_dead",
        slot="gig",
        cmd_map={"gig": ["bash", "/dev/null"]},
        timeout=5,
    )
    assert r["ok"] is True
    assert "unknown" in r["status"]
    assert "scaffold-deferred-sprint-4" in r["status"]


# ─── PROP-R4: unknown slot → no subprocess ────────────────────────
def test_unknown_slot_scaffold_deferred(tmp_path):
    r = execute_recipe(
        recipe={"action": "restart", "params": {}},
        issue_kind="tmux_dead",
        slot="unknown-slot-xyz",
        cmd_map={},  # no entry
        timeout=5,
    )
    assert r["ok"] is True
    assert "restart-no-cmd" in r["status"]
    assert "unknown-slot-xyz" in r["status"]


def test_scaffold_deferred_actions_constant_is_7_set():
    # Sanity: the constant matches the spec's 7-action set exactly.
    assert SCAFFOLD_DEFERRED_ACTIONS == frozenset({
        "kill_server", "send_keys", "login", "npm_install",
        "git_checkout", "escalate_via_bot2bot", "noop",
    })
