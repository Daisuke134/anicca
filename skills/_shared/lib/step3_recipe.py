"""STEP 3 recipe action executor.

Per sprint-3 #33 spec REQ-R1..R4. Sprint-3 ships ONLY the `tmux_dead → restart`
path. All other Issue.kind / recipe.action combinations are scaffold-deferred
to sprint-4 with explicit log lines (never crash, never silently noop).

Critical invariant (FIND-001 fix / parent INV-P1): `stale` Issues also emit
recipe.action='restart' from health_check_v2 — but a stale tick on a HEALTHY
tmux must NOT restart it. We gate on Issue.kind=='tmux_dead' explicitly.
"""
from __future__ import annotations
import subprocess
from typing import Optional, FrozenSet

# REQ-R3: the 7 non-restart actions health_check_v2 currently emits + noop.
# Cross-referenced against skills/_shared/lib/health_check_v2.py:97-107.
SCAFFOLD_DEFERRED_ACTIONS: FrozenSet[str] = frozenset({
    "kill_server",
    "send_keys",
    "login",
    "npm_install",
    "git_checkout",
    "escalate_via_bot2bot",
    "noop",
})


def execute_recipe(
    *,
    recipe: dict,
    issue_kind: str,
    slot: str,
    cmd_map: dict,
    timeout: int = 30,
) -> dict:
    """Returns {ok, status}. NEVER raises (tick continues either way)."""
    action = recipe.get("action", "noop")

    # REQ-R1a (FIND-001 critical): stale + restart → suppress, INV-P1 preserved.
    if action == "restart" and issue_kind == "stale":
        return {"ok": True, "status": "stale-suppressed-INV-P1"}

    # REQ-R1: real restart ONLY for tmux_dead.
    if action == "restart" and issue_kind == "tmux_dead":
        cmd = cmd_map.get(slot)
        if not cmd:
            # REQ-R4: unknown slot → scaffold-deferred
            return {"ok": True, "status": f"restart-no-cmd-for-{slot}-scaffold-deferred-sprint-4"}
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            if r.returncode == 0:
                return {"ok": True, "status": "restart-ok"}
            return {"ok": False, "status": f"restart-failed-rc{r.returncode}"}
        except subprocess.TimeoutExpired:
            return {"ok": False, "status": "restart-failed-timeout"}
        except (OSError, FileNotFoundError) as e:
            return {"ok": False, "status": f"restart-failed-{type(e).__name__}"}

    # REQ-R3: enumerated scaffold-deferred set
    if action in SCAFFOLD_DEFERRED_ACTIONS:
        return {"ok": True, "status": f"{action}-scaffold-deferred-sprint-4"}

    # Catch-all: unknown future action — log + continue, no crash.
    return {"ok": True, "status": f"unknown-{action}-scaffold-deferred-sprint-4"}


# REQ-R4: per-slot restart command lookup. Used by the dispatcher.
def default_restart_cmd_map(anicca_home: str) -> dict:
    """Returns the canonical per-slot restart command lookup table.

    sprint-3 ships gig only; sprint-4 adds clip/affiliate/bounty etc. as
    each slot migrates to proactive-loop.
    """
    return {
        "gig": ["bash", f"{anicca_home}/skills/earn/gig/gig-cli.sh", "--restart"],
    }
