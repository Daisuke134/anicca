"""STEP 3 recipe action executor.

Sprint-3 #33 REQ-R1..R4 (restart + tmux_dead gate + INV-P1) + sprint-4 (d)
real-wire of the remaining 6 actions:
    kill_server, send_keys, login, npm_install, git_checkout,
    escalate_via_bot2bot.

INV-P1 (parent §7b): `restart` ONLY runs for issue_kind == "tmux_dead".
INV-1 preserved for the 6 wires: none of them invoke restart or
default_restart_cmd_map — they act on tmux (kill/send-keys), git, npm,
bot2bot.sh, and login-service.sh exclusively.
INV-4 preserved: none of the 6 wires write under `loops/<slot>/`.
"""
from __future__ import annotations
import os
import subprocess
from typing import FrozenSet

# ─── FIND-2-002 fix: sprint-4 (d) empties the scaffold-deferred set. Only
# `noop` remains as a legitimate deferral (health_check_v2 emits it when no
# recipe matches a future Issue kind).
SCAFFOLD_DEFERRED_ACTIONS: FrozenSet[str] = frozenset({"noop"})

# ─── send_keys flow variant map (FIND-001 fix). health_check_v2 emits
# `cron_missing → send_keys {flow: "reinject_startup"}`; we map to the
# canonical LAYER C onboarding hotkey. Unknown flows fail-soft without
# invoking tmux.
SEND_KEYS_FLOW_MAP: dict = {
    "reinject_startup": "/startup",
}

# ─── npm_install flow variant map (FIND-2-001 fix). health_check_v2 emits
# `hook_missing → npm_install {flow: "allowlist_check"}`. `npm install` IS
# the hook-allowlist rebuild path (npm postinstall). The map is documented
# but currently empty of transforms — the flow value is echoed into the
# returned status so callers can distinguish which recovery ran.
NPM_INSTALL_FLOW_MAP: dict = {
    "allowlist_check": "npm install",  # hook-allowlist rebuild via postinstall
}


def execute_recipe(
    *,
    recipe: dict,
    issue_kind: str,
    slot: str,
    cmd_map: dict,
    timeout: int = 30,
    anicca_home: str = "",
) -> dict:
    """Returns {ok, status}. NEVER raises (tick continues either way)."""
    action = recipe.get("action", "noop")
    params = recipe.get("params", {}) or {}

    # ── REQ-R1a (FIND-001 critical): stale + restart → suppress (INV-P1).
    if action == "restart" and issue_kind == "stale":
        return {"ok": True, "status": "stale-suppressed-INV-P1"}

    # ── REQ-R1: real restart ONLY for tmux_dead.
    if action == "restart" and issue_kind == "tmux_dead":
        cmd = cmd_map.get(slot)
        if not cmd:
            return {"ok": True,
                    "status": f"restart-no-cmd-for-{slot}-scaffold-deferred-sprint-4"}
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            if r.returncode == 0:
                return {"ok": True, "status": "restart-ok"}
            return {"ok": False, "status": f"restart-failed-rc{r.returncode}"}
        except subprocess.TimeoutExpired:
            return {"ok": False, "status": "restart-failed-timeout"}
        except (OSError, FileNotFoundError) as e:
            return {"ok": False, "status": f"restart-failed-{type(e).__name__}"}

    # ── REQ-A1: kill_server (tmux server-level kill, 5s).
    if action == "kill_server":
        try:
            r = subprocess.run(
                ["tmux", "kill-server"],
                capture_output=True, text=True, timeout=5,
            )
            if r.returncode == 0:
                return {"ok": True, "status": "kill_server-ok"}
            return {"ok": False, "status": f"kill_server-failed-rc{r.returncode}"}
        except subprocess.TimeoutExpired:
            return {"ok": False, "status": "kill_server-failed-timeout"}
        except (OSError, FileNotFoundError) as e:
            return {"ok": False, "status": f"kill_server-failed-{type(e).__name__}"}

    # ── REQ-A2: escalate_via_bot2bot.
    if action == "escalate_via_bot2bot":
        if not anicca_home:
            return {"ok": True, "status": "escalate-no-anicca-home-deferred"}
        script = f"{anicca_home}/skills/_shared/bot2bot.sh"
        if not os.path.exists(script):
            return {"ok": True, "status": "escalate-no-script-continue"}
        reason = str(params.get("reason", ""))
        try:
            r = subprocess.run(
                [script, "--slot", slot, "--reason", reason],
                capture_output=True, text=True, timeout=30,
            )
            if r.returncode == 0:
                return {"ok": True, "status": "escalate-ok"}
            return {"ok": False, "status": f"escalate-failed-rc{r.returncode}"}
        except subprocess.TimeoutExpired:
            return {"ok": False, "status": "escalate-failed-timeout"}
        except (OSError, FileNotFoundError) as e:
            return {"ok": False, "status": f"escalate-failed-{type(e).__name__}"}

    # ── REQ-B1: send_keys (tmux send-keys, keys OR flow variant).
    if action == "send_keys":
        # Resolve keys via keys (direct) or flow (mapped).
        keys = params.get("keys")
        flow = params.get("flow")
        if keys is None and flow is not None:
            mapped = SEND_KEYS_FLOW_MAP.get(flow)
            if mapped is None:
                return {"ok": True,
                        "status": f"send_keys-unknown-flow-{flow}"}
            keys = mapped
        if keys is None:
            return {"ok": True, "status": "send_keys-noop-no-params"}

        target = f"{slot}-cli"
        try:
            r = subprocess.run(
                ["tmux", "send-keys", "-t", target, "--", str(keys)],
                capture_output=True, text=True, timeout=5,
            )
            if r.returncode != 0:
                return {"ok": False,
                        "status": f"send_keys-failed-rc{r.returncode}"}
            if params.get("enter"):
                r2 = subprocess.run(
                    ["tmux", "send-keys", "-t", target, "Enter"],
                    capture_output=True, text=True, timeout=5,
                )
                if r2.returncode != 0:
                    return {"ok": False,
                            "status": f"send_keys-failed-rc{r2.returncode}"}
            return {"ok": True, "status": "send_keys-ok"}
        except subprocess.TimeoutExpired:
            return {"ok": False, "status": "send_keys-failed-timeout"}
        except (OSError, FileNotFoundError) as e:
            return {"ok": False, "status": f"send_keys-failed-{type(e).__name__}"}

    # ── REQ-C1: login (external script, best-effort, fail-soft).
    if action == "login":
        if not anicca_home:
            return {"ok": True, "status": "login-no-anicca-home-deferred"}
        script = f"{anicca_home}/skills/_shared/login-service.sh"
        if not os.path.exists(script):
            return {"ok": True, "status": "login-no-script-deferred"}
        flow = str(params.get("flow", ""))
        try:
            r = subprocess.run(
                [script, "--flow", flow],
                capture_output=True, text=True, timeout=60,
            )
            if r.returncode == 0:
                return {"ok": True, "status": "login-ok"}
            return {"ok": False, "status": f"login-failed-rc{r.returncode}"}
        except subprocess.TimeoutExpired:
            return {"ok": False, "status": "login-failed-timeout"}
        except (OSError, FileNotFoundError) as e:
            return {"ok": False, "status": f"login-failed-{type(e).__name__}"}

    # ── REQ-C2: npm_install (with flow-echo in status).
    if action == "npm_install":
        if not anicca_home:
            return {"ok": True, "status": "npm_install-no-anicca-home-deferred"}
        flow = params.get("flow")
        try:
            r = subprocess.run(
                ["npm", "install"],
                capture_output=True, text=True, timeout=90,
                cwd=anicca_home,
            )
            if r.returncode == 0:
                if flow is None:
                    return {"ok": True, "status": "npm_install-ok"}
                return {"ok": True,
                        "status": f"npm_install-ok-flow={flow}"}
            return {"ok": False, "status": f"npm_install-failed-rc{r.returncode}"}
        except subprocess.TimeoutExpired:
            return {"ok": False, "status": "npm_install-failed-timeout"}
        except (OSError, FileNotFoundError) as e:
            return {"ok": False, "status": f"npm_install-failed-{type(e).__name__}"}

    # ── REQ-C3: git_checkout (target from params, defaults to canonical branch).
    if action == "git_checkout":
        if not anicca_home:
            return {"ok": True, "status": "git_checkout-no-anicca-home-deferred"}
        target = str(params.get("target") or "anicca-bot-signed")
        try:
            r = subprocess.run(
                ["git", "-C", anicca_home, "checkout", target],
                capture_output=True, text=True, timeout=30,
            )
            if r.returncode == 0:
                return {"ok": True, "status": "git_checkout-ok"}
            return {"ok": False, "status": f"git_checkout-failed-rc{r.returncode}"}
        except subprocess.TimeoutExpired:
            return {"ok": False, "status": "git_checkout-failed-timeout"}
        except (OSError, FileNotFoundError) as e:
            return {"ok": False, "status": f"git_checkout-failed-{type(e).__name__}"}

    # ── REQ-I4: scaffold-deferred set (noop only).
    if action in SCAFFOLD_DEFERRED_ACTIONS:
        return {"ok": True, "status": f"{action}-scaffold-deferred-sprint-4"}

    # Catch-all: unknown future action — log + continue, no crash.
    return {"ok": True, "status": f"unknown-{action}-scaffold-deferred-sprint-4"}


# REQ-R4: per-slot restart command lookup. Used by the dispatcher.
def default_restart_cmd_map(anicca_home: str) -> dict:
    """Returns the canonical per-slot restart command lookup table.

    sprint-3 shipped gig only; gig (+ affiliate/bounty) is now isolated to the
    private profitable-claude repo (2026-07-06, .vcsdd/features/anicca-agent-economy
    SPEC.md §3 P0) and is no longer a self-funded slot in the canonical checkout, so its entry is
    gone. Empty until a self-funded earn slot migrates to proactive-loop restart.
    """
    return {}
