"""Phase 2a RED — sprint-4 (d) recipe-6-actions.

Unit tests with monkeypatched subprocess.run for the 6 wires:
kill_server, escalate_via_bot2bot, send_keys (keys + flow), login,
npm_install, git_checkout.

Maps to PROP-A1/A2/B1/C1/C2/C3 + timeout/fail-soft PROPs.
"""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path
import types

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "skills" / "_shared"))

from lib.step3_recipe import execute_recipe, SEND_KEYS_FLOW_MAP, NPM_INSTALL_FLOW_MAP  # noqa


class _FakeCP:
    def __init__(self, rc=0, stdout="", stderr=""):
        self.returncode = rc
        self.stdout = stdout
        self.stderr = stderr


def _capture_run(monkeypatch, ret=None, raises=None):
    calls = []
    def fake(cmd, *a, **kw):
        calls.append({"cmd": cmd, "kwargs": kw})
        if raises is not None:
            raise raises
        return ret if ret is not None else _FakeCP(rc=0)
    monkeypatch.setattr(subprocess, "run", fake)
    return calls


# ─── REQ-A1 kill_server ───────────────────────────────────────────
def test_A1_kill_server_invokes_tmux(monkeypatch):
    calls = _capture_run(monkeypatch, _FakeCP(rc=0))
    r = execute_recipe(
        recipe={"action": "kill_server", "params": {}},
        issue_kind="tmux_server_corrupted",
        slot="gig", cmd_map={}, timeout=5,
    )
    assert r["ok"] is True
    assert r["status"] == "kill_server-ok"
    assert calls[0]["cmd"][:2] == ["tmux", "kill-server"]


def test_A1_kill_server_rc_fail(monkeypatch):
    _capture_run(monkeypatch, _FakeCP(rc=2))
    r = execute_recipe(
        recipe={"action": "kill_server", "params": {}},
        issue_kind="tmux_server_corrupted",
        slot="gig", cmd_map={}, timeout=5,
    )
    assert r["ok"] is False
    assert "kill_server-failed-rc2" in r["status"]


def test_A1_kill_server_timeout(monkeypatch):
    _capture_run(monkeypatch, raises=subprocess.TimeoutExpired("tmux", 5))
    r = execute_recipe(
        recipe={"action": "kill_server", "params": {}},
        issue_kind="tmux_server_corrupted",
        slot="gig", cmd_map={}, timeout=5,
    )
    assert r["ok"] is False
    assert r["status"] == "kill_server-failed-timeout"


# ─── REQ-A2 escalate_via_bot2bot ───────────────────────────────────
def test_A2_escalate_invokes_bot2bot(monkeypatch, tmp_path):
    script = tmp_path / "skills" / "_shared" / "bot2bot.sh"
    script.parent.mkdir(parents=True)
    script.write_text("#!/bin/bash\nexit 0\n")
    script.chmod(0o755)
    calls = _capture_run(monkeypatch, _FakeCP(rc=0))
    r = execute_recipe(
        recipe={"action": "escalate_via_bot2bot", "params": {"reason": "backoff-cap"}},
        issue_kind="backoff", slot="gig", cmd_map={},
        anicca_home=str(tmp_path), timeout=30,
    )
    assert r["ok"] is True
    assert r["status"] == "escalate-ok"
    assert str(script) in calls[0]["cmd"]


def test_A2_escalate_missing_script_fail_soft(monkeypatch, tmp_path):
    _capture_run(monkeypatch, _FakeCP(rc=0))
    r = execute_recipe(
        recipe={"action": "escalate_via_bot2bot", "params": {"reason": "x"}},
        issue_kind="backoff", slot="gig", cmd_map={},
        anicca_home=str(tmp_path),  # no bot2bot.sh
    )
    assert r["ok"] is True
    assert r["status"] == "escalate-no-script-continue"


def test_A2_escalate_timeout_caught(monkeypatch, tmp_path):
    script = tmp_path / "skills" / "_shared" / "bot2bot.sh"
    script.parent.mkdir(parents=True)
    script.write_text("#!/bin/bash\nsleep 60\n")
    script.chmod(0o755)
    _capture_run(monkeypatch, raises=subprocess.TimeoutExpired("bot2bot.sh", 30))
    r = execute_recipe(
        recipe={"action": "escalate_via_bot2bot", "params": {"reason": "x"}},
        issue_kind="backoff", slot="gig", cmd_map={},
        anicca_home=str(tmp_path),
    )
    assert r["ok"] is False
    assert r["status"] == "escalate-failed-timeout"


# ─── REQ-B1 send_keys ─────────────────────────────────────────────
def test_B1_send_keys_direct_keys(monkeypatch):
    calls = _capture_run(monkeypatch, _FakeCP(rc=0))
    r = execute_recipe(
        recipe={"action": "send_keys", "params": {"keys": "1", "enter": True}},
        issue_kind="trust_dialog", slot="gig", cmd_map={},
    )
    assert r["ok"] is True
    assert r["status"] == "send_keys-ok"
    # First call: send the keys
    assert calls[0]["cmd"][:2] == ["tmux", "send-keys"]
    assert "1" in calls[0]["cmd"]
    # Enter call
    assert any("Enter" in c["cmd"] for c in calls)


def test_B1_send_keys_flow_variant_mapped(monkeypatch):
    calls = _capture_run(monkeypatch, _FakeCP(rc=0))
    r = execute_recipe(
        recipe={"action": "send_keys", "params": {"flow": "reinject_startup"}},
        issue_kind="cron_missing", slot="gig", cmd_map={},
    )
    assert r["ok"] is True
    assert r["status"] == "send_keys-ok"
    # Assert /startup is in the sent keys
    sent = " ".join(str(c) for c in calls[0]["cmd"])
    assert "/startup" in sent


def test_B1_send_keys_unknown_flow_fail_soft(monkeypatch):
    calls = _capture_run(monkeypatch, _FakeCP(rc=0))
    r = execute_recipe(
        recipe={"action": "send_keys", "params": {"flow": "unknown_flow_xyz"}},
        issue_kind="cron_missing", slot="gig", cmd_map={},
    )
    assert r["ok"] is True
    assert r["status"] == "send_keys-unknown-flow-unknown_flow_xyz"
    assert calls == []  # tmux NOT invoked


def test_B1_send_keys_noop_no_params(monkeypatch):
    calls = _capture_run(monkeypatch, _FakeCP(rc=0))
    r = execute_recipe(
        recipe={"action": "send_keys", "params": {}},
        issue_kind="trust_dialog", slot="gig", cmd_map={},
    )
    assert r["ok"] is True
    assert r["status"] == "send_keys-noop-no-params"
    assert calls == []


def test_B1_send_keys_timeout(monkeypatch):
    _capture_run(monkeypatch, raises=subprocess.TimeoutExpired("tmux", 5))
    r = execute_recipe(
        recipe={"action": "send_keys", "params": {"keys": "1"}},
        issue_kind="trust_dialog", slot="gig", cmd_map={},
    )
    assert r["ok"] is False
    assert r["status"] == "send_keys-failed-timeout"


# ─── REQ-C1 login ─────────────────────────────────────────────────
def test_C1_login_invokes_script(monkeypatch, tmp_path):
    script = tmp_path / "skills" / "_shared" / "login-service.sh"
    script.parent.mkdir(parents=True)
    script.write_text("#!/bin/bash\nexit 0\n")
    script.chmod(0o755)
    calls = _capture_run(monkeypatch, _FakeCP(rc=0))
    r = execute_recipe(
        recipe={"action": "login", "params": {"flow": "camofox+gmail_otp"}},
        issue_kind="not_logged_in", slot="gig", cmd_map={},
        anicca_home=str(tmp_path),
    )
    assert r["ok"] is True
    assert r["status"] == "login-ok"


def test_C1_login_missing_script_fail_soft(monkeypatch, tmp_path):
    r = execute_recipe(
        recipe={"action": "login", "params": {"flow": "x"}},
        issue_kind="not_logged_in", slot="gig", cmd_map={},
        anicca_home=str(tmp_path),
    )
    assert r["ok"] is True
    assert r["status"] == "login-no-script-deferred"


def test_C1_login_timeout(monkeypatch, tmp_path):
    script = tmp_path / "skills" / "_shared" / "login-service.sh"
    script.parent.mkdir(parents=True)
    script.write_text("#!/bin/bash\nsleep 999\n")
    script.chmod(0o755)
    _capture_run(monkeypatch, raises=subprocess.TimeoutExpired("login", 60))
    r = execute_recipe(
        recipe={"action": "login", "params": {"flow": "x"}},
        issue_kind="not_logged_in", slot="gig", cmd_map={},
        anicca_home=str(tmp_path),
    )
    assert r["ok"] is False
    assert r["status"] == "login-failed-timeout"


# ─── REQ-C2 npm_install ───────────────────────────────────────────
def test_C2_npm_install_flow_consumed(monkeypatch, tmp_path):
    calls = _capture_run(monkeypatch, _FakeCP(rc=0))
    r = execute_recipe(
        recipe={"action": "npm_install", "params": {"flow": "allowlist_check"}},
        issue_kind="hook_missing", slot="gig", cmd_map={},
        anicca_home=str(tmp_path),
    )
    assert r["ok"] is True
    assert r["status"] == "npm_install-ok-flow=allowlist_check"
    assert calls[0]["cmd"][:2] == ["npm", "install"]


def test_C2_npm_install_missing_flow(monkeypatch, tmp_path):
    _capture_run(monkeypatch, _FakeCP(rc=0))
    r = execute_recipe(
        recipe={"action": "npm_install", "params": {}},
        issue_kind="hook_missing", slot="gig", cmd_map={},
        anicca_home=str(tmp_path),
    )
    assert r["ok"] is True
    assert r["status"] == "npm_install-ok"


def test_C2_npm_install_unknown_flow(monkeypatch, tmp_path):
    _capture_run(monkeypatch, _FakeCP(rc=0))
    r = execute_recipe(
        recipe={"action": "npm_install", "params": {"flow": "weird_flow"}},
        issue_kind="hook_missing", slot="gig", cmd_map={},
        anicca_home=str(tmp_path),
    )
    assert r["ok"] is True
    assert r["status"] == "npm_install-ok-flow=weird_flow"


def test_C2_npm_install_timeout(monkeypatch, tmp_path):
    _capture_run(monkeypatch, raises=subprocess.TimeoutExpired("npm", 90))
    r = execute_recipe(
        recipe={"action": "npm_install", "params": {}},
        issue_kind="hook_missing", slot="gig", cmd_map={},
        anicca_home=str(tmp_path),
    )
    assert r["ok"] is False
    assert r["status"] == "npm_install-failed-timeout"


# ─── REQ-C3 git_checkout ──────────────────────────────────────────
def test_C3_git_checkout_invokes_git(monkeypatch, tmp_path):
    calls = _capture_run(monkeypatch, _FakeCP(rc=0))
    r = execute_recipe(
        recipe={"action": "git_checkout", "params": {"target": "anicca-bot-signed"}},
        issue_kind="spawn_drift", slot="gig", cmd_map={},
        anicca_home=str(tmp_path),
    )
    assert r["ok"] is True
    assert r["status"] == "git_checkout-ok"
    assert calls[0]["cmd"][:3] == ["git", "-C", str(tmp_path)]
    assert "anicca-bot-signed" in calls[0]["cmd"]


def test_C3_git_checkout_missing_target_defaults(monkeypatch, tmp_path):
    calls = _capture_run(monkeypatch, _FakeCP(rc=0))
    r = execute_recipe(
        recipe={"action": "git_checkout", "params": {}},
        issue_kind="spawn_drift", slot="gig", cmd_map={},
        anicca_home=str(tmp_path),
    )
    assert r["ok"] is True
    assert "anicca-bot-signed" in calls[0]["cmd"]


def test_C3_git_checkout_timeout(monkeypatch, tmp_path):
    _capture_run(monkeypatch, raises=subprocess.TimeoutExpired("git", 30))
    r = execute_recipe(
        recipe={"action": "git_checkout", "params": {"target": "x"}},
        issue_kind="spawn_drift", slot="gig", cmd_map={},
        anicca_home=str(tmp_path),
    )
    assert r["ok"] is False
    assert r["status"] == "git_checkout-failed-timeout"


# ─── Group C signature — empty anicca_home fail-soft ──────────────
def test_group_C_empty_anicca_home_fail_soft(monkeypatch):
    """PROP-C-no-anicca-home-fail-soft."""
    for action, params in [
        ("login", {"flow": "x"}),
        ("npm_install", {}),
        ("git_checkout", {"target": "x"}),
    ]:
        r = execute_recipe(
            recipe={"action": action, "params": params},
            issue_kind="x", slot="gig", cmd_map={}, anicca_home="",
        )
        assert r["ok"] is True
        assert f"{action}-no-anicca-home-deferred" in r["status"]


# ─── SEND_KEYS_FLOW_MAP + NPM_INSTALL_FLOW_MAP constants ──────────
def test_send_keys_flow_map_has_reinject_startup():
    assert SEND_KEYS_FLOW_MAP["reinject_startup"] == "/startup"


def test_npm_install_flow_map_documented():
    # Just assert the map exists and is a dict; entries are optional.
    assert isinstance(NPM_INSTALL_FLOW_MAP, dict)
