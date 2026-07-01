---
feature: recipe-6-actions
mode: lean
sprint: 1
language: python
created: 2026-07-01
parent_goal: GOAL-sprint-4-M1-M2.md — feature (d)
---

# Behavioral Specification — recipe-6-actions (sprint-4 (d))

## 1. Purpose

Currently `execute_recipe` (skills/_shared/lib/step3_recipe.py) real-wires only
`action == "restart" and issue_kind == "tmux_dead"`. All other 6 actions
(`kill_server`, `send_keys`, `login`, `npm_install`, `git_checkout`,
`escalate_via_bot2bot`) return a `"<action>-scaffold-deferred-sprint-4"` string
with **zero side-effect**. Sprint-4 (d) real-wires them while preserving
INV-P1 (never restart LAYER C except on `tmux_dead`).

## 2. Out of scope

- Does NOT change `restart` behavior (INV-P1 unchanged).
- Does NOT introduce new Issue kinds — the 10 in health_check_v2 stay.
- Does NOT modify `default_restart_cmd_map` — it's the restart map, not the
  recipe map.
- `login` action: the ACTUAL login flow (camofox + gmail OTP) is out of scope
  for this feature; the sprint-4 wire invokes an EXISTING `login-service.sh`
  script if present, else logs the intent and returns `deferred-no-script`.

## 3. Requirements (EARS)

### Group A — Actions with SAFE side-effects (invoke unconditionally when triggered)

- **REQ-A1** (`kill_server`): WHEN `issue_kind == "tmux_server_corrupted"`
  AND `action == "kill_server"`, THE FUNCTION SHALL invoke
  `tmux kill-server` via subprocess with a 5 s timeout. Return
  `{ok: True, status: "kill_server-ok"}` on rc=0; else
  `{ok: False, status: "kill_server-failed-rc<N>"}` or
  `{ok: False, status: "kill_server-failed-timeout"}`. INV-1 is
  preserved iff the trigger requires `tmux_server_corrupted` (server
  is already dead / broken → killing it is legitimate; LAYER C
  tmux session is already gone).

- **REQ-A2** (`escalate_via_bot2bot`): WHEN `action == "escalate_via_bot2bot"`,
  THE FUNCTION SHALL invoke `skills/_shared/bot2bot.sh` with args
  `--slot <slot> --reason <recipe.params.reason>`. If the script exits 0,
  return `{ok: True, status: "escalate-ok"}`; else
  `{ok: False, status: "escalate-failed-rc<N>"}`. If the script is missing,
  return `{ok: True, status: "escalate-no-script-continue"}` (fail-soft —
  side effect optional, tick MUST continue).

### Group B — Actions that use `send_keys` to LAYER C tmux (via tmux send-keys)

- **REQ-B1** (`send_keys`): WHEN `action == "send_keys"`, THE FUNCTION SHALL
  invoke `tmux send-keys -t "<slot>-cli" -- <keys>` and, if `params.enter`
  is truthy, also `tmux send-keys -t "<slot>-cli" Enter`. The tmux target
  name comes from the caller's `slot` argument suffixed with `-cli` (matching
  LAYER C tmux naming). Return `{ok: True, status: "send_keys-ok"}` on rc=0,
  else `{ok: False, status: "send_keys-failed-rc<N>"}`. INV-1 preserved:
  `send-keys` does NOT restart the session.

### Group C — Actions with EXTERNAL side-effects (best-effort, fail-soft)

- **REQ-C1** (`login`): WHEN `action == "login"`, THE FUNCTION SHALL check
  for `skills/_shared/login-service.sh`. If present, invoke with
  `--flow <recipe.params.flow>` and a 60 s timeout. Return
  `{ok: True, status: "login-ok"}` on rc=0. If missing, return
  `{ok: True, status: "login-no-script-deferred"}`. Fail-soft (never crash).

- **REQ-C2** (`npm_install`): WHEN `action == "npm_install"`, THE FUNCTION
  SHALL run `npm install` in ANICCA_HOME with a 90 s timeout. Return
  `{ok: True, status: "npm_install-ok"}` on rc=0. Else
  `{ok: False, status: "npm_install-failed-rc<N>"}`. INV-1 preserved.

- **REQ-C3** (`git_checkout`): WHEN `action == "git_checkout"`, THE FUNCTION
  SHALL invoke `git -C <anicca_home> checkout <recipe.params.target>` with
  a 30 s timeout. Return `{ok: True, status: "git_checkout-ok"}` on rc=0;
  else `{ok: False, status: "git_checkout-failed-rc<N>"}`. INV-4 preserved:
  we do NOT modify slot state; we checkout a code branch.

### Group I — Invariants preserved

- **REQ-I1** (INV-P1): NO real-wired action invokes `restart` or
  `default_restart_cmd_map`. The `restart` action still ONLY runs for
  `issue_kind == "tmux_dead"` (existing gate unchanged).
- **REQ-I2**: `execute_recipe` NEVER raises — every subprocess failure is
  caught and returned as `{ok: False, status: ...}`. The tick continues.
- **REQ-I3** (INV-4): NO action writes to slot state (`~/loops/<slot>/`) —
  they act on tmux / npm / git / bot2bot exclusively.
- **REQ-I4**: `SCAFFOLD_DEFERRED_ACTIONS` in step3_recipe.py SHALL be emptied
  (or reduced to just `noop`) because all 6 actions are now real-wired.

## 4. Edge cases

| EDGE | Trigger | Expected |
|---|---|---|
| E1 | subprocess timeout | fail-soft with `-timeout` status |
| E2 | subprocess FileNotFoundError | fail-soft with `-{Error}` status |
| E3 | `params` missing | apply reasonable default (e.g. `keys=""`, target="main"), never crash |
| E4 | slot name has special chars | tmux send-keys handles via `--` delimiter |
| E5 | `escalate_via_bot2bot` script missing | fail-soft `escalate-no-script-continue`; tick MUST continue |
| E6 | `login` script missing | fail-soft `login-no-script-deferred`; tick MUST continue |

## 5. NFR

- **NFR-1**: no new external deps; only subprocess + existing bash scripts.
- **NFR-2**: total added wall-time bounded by explicit per-action timeouts
  (60 + 30 + 30 + 5 + 90 + 30 = 245 s worst case, but only ONE action fires
  per tick per REQ-P0 highest-priority selection).
- **NFR-3**: fail-soft everywhere — a broken action never prevents the next
  tick from running.
