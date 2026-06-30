---
feature: proactive-step6-act
mode: lean
sprint: 1
language: python
created: 2026-07-01
parent_spec: docs/superpowers/specs/2026-07-01-proactive-loop-architecture-and-cleanup-design.md
---

# Behavioral Specification — proactive-step6-act (sprint-3 #33)

## 1. Purpose

Wire STEP 6 (= ACT) and STEP 3 (= health recipe action) of
`proactive-loop-dispatch.py` from scaffold to real action — without violating
INV-1 / INV-4 / INV-P1.

Currently:
- STEP 6 picks the highest-ROI menu item but only writes `picked: <name>` to
  build_log.md (= scaffold).
- STEP 3 builds a HealthSnapshot, computes a recipe via
  `dispatch_highest_priority`, but only writes `step=3-recipe-<action>` to
  core-status.json (= scaffold).

Sprint-3 #33 makes both real:
- STEP 6 ACT: write a task descriptor to `~/loops/<slot>/tasks/<ts>-<name>.json`
  that LAYER C (`<slot>-cli.sh` tmux core) can dequeue.
- STEP 3 recipe execution: when recipe.action == "restart", invoke
  `<slot>-cli.sh --restart` (= the only LAYER C-permitted side-effect, since
  Sutando-pattern tmux cores ARE meant to be restartable when dead).

## 2. Out of scope

- Does NOT modify `<slot>-cli.sh` itself. The "real" handling of tasks/ items
  is the existing tmux core's claude-prompt; sprint-3 #33 ships the
  ENQUEUE side. The DEQUEUE side is a follow-up spec (= tmux core gains a
  task-watcher loop) outside this sprint.
- Does NOT add new recipe actions beyond `restart` (the other recipes
  `send_keys`, `escalate_via_bot2bot`, `noop` remain scaffolds for now;
  sprint-3 #33 wires `restart` only).
- Does NOT touch the existing INV-4 contract: STEP 6 writes ONLY under
  `~/loops/<slot>/`, not anywhere else.

## 3. Requirements (EARS)

### Group T — Tasks/ enqueue (STEP 6 real ACT)

- **REQ-T1**: WHEN STEP 5 picks a menu item, THE DISPATCHER SHALL write a
  task descriptor JSON file at `<slot_dir>/tasks/<unix_ts>-<sanitized_name>.json`.
- **REQ-T2**: THE TASK DESCRIPTOR SHALL contain at minimum:
  `{schema_version: 1, pass_id, ts, picked: <item dict>, budget,
  proactive_loop_origin: "step6-act", slot}`.
- **REQ-T3**: THE filename `<sanitized_name>` SHALL be the menu item's
  `name` field passed through a `[a-z0-9_-]` sanitizer (= drop other chars).
- **REQ-T4**: THE DISPATCHER SHALL NOT enqueue if a task with the SAME
  pass_id already exists (= idempotent re-tick safety).
- **REQ-T5**: AFTER successful enqueue, build_log.md `outcome` SHALL change
  from "scaffold-pick-recorded" to "enqueued:<filename>" (no rollback if write
  later fails; the file is the source of truth).

### Group R — STEP 3 recipe action (real restart)

- **REQ-R1**: WHEN STEP 3 computes recipe.action == "restart", THE DISPATCHER
  SHALL invoke the per-slot restart command. For slot "gig" that command is
  `bash <ANICCA_HOME>/skills/earn/gig/gig-cli.sh --restart` (= the documented
  Sutando-pattern restart entrypoint).
- **REQ-R2**: THE restart invocation SHALL be subprocess.run with timeout=30s
  + capture_output=True; failures (rc != 0, timeout) are logged to
  core-status.json as `step=3-recipe-restart-failed-<reason>` and the tick
  continues (= do not abort the whole pass on health-fix failure).
- **REQ-R3**: WHEN recipe.action is anything OTHER than "restart" (= "noop",
  "send_keys", "escalate_via_bot2bot"), THE DISPATCHER SHALL log
  `step=3-recipe-<action>-scaffold-deferred-sprint-4` and CONTINUE without
  side-effect (= sprint-3 #33 ships restart only).
- **REQ-R4**: THE restart command per slot SHALL be resolved via a lookup
  table `RESTART_CMD_BY_SLOT` keyed on slot name; unknown slots fall back to
  the scaffold-deferred path (REQ-R3).

### Group I — Invariants

- **REQ-I1** (= parent INV-1 / INV-P1): The ONLY LAYER C side-effect THE
  DISPATCHER MAY perform is the per-slot `--restart` command (which the core
  itself documents as the recover-from-dead path). No `tmux kill`, no
  `--stop`, no `--kill`. Static grep over the dispatcher SHALL find 0 hits.
- **REQ-I2** (= parent INV-4): All writes from STEP 6 SHALL be confined to
  `<slot_dir>/tasks/` + `<slot_dir>/build_log.md`. Verified by mtime snapshot.
- **REQ-I3** (= no-human-touch / REQ-J8): THE DISPATCHER MUST NOT call
  osascript / Telegram / Slack / Twilio / sudo / SecKeychain / Touch-ID.

## 4. Edge cases

| EDGE | Trigger | Expected behavior |
|---|---|---|
| E1 | `<slot_dir>/tasks/` does not exist | mkdir -p, then write |
| E2 | menu item `name` is empty | enqueue with `unnamed-<ts>` filename |
| E3 | task file already exists (= same pass_id) | skip enqueue + log "enqueue-skipped-dup" |
| E4 | restart subprocess times out (30s) | log "step=3-recipe-restart-failed-timeout"; continue |
| E5 | restart subprocess exits non-zero | log "step=3-recipe-restart-failed-rc<N>"; continue |
| E6 | recipe.action == "noop" | NO subprocess; log scaffold-deferred; continue |
| E7 | slot has no entry in RESTART_CMD_BY_SLOT | log scaffold-deferred; continue |
| E8 | enqueue write fails (= disk full) | log "step=6-enqueue-failed-<exc>"; build_log records the failure outcome; tick exits 0 (= do not crash the whole proactive-loop) |

## 5. Non-functional

- **NFR-1**: STEP 6 + STEP 3 added wall-time < 200ms each (= proactive-loop
  is on a 5-min cron and other steps already exist; budget is generous).
- **NFR-2**: No new external dependencies.
- **NFR-3**: All file writes use atomic temp+rename pattern OR direct write
  (small task files; OS-level atomicity at the inode boundary suffices).

## 6. Traceability

10 REQ + 8 EDGE = 18 minimum test scenarios. Unit tests on a PURE helper
`enqueue_task_descriptor(slot_dir, descriptor)` cross-platform; restart
invocation tested via subprocess shim (LAUNCHCTL_BIN-style pattern but
keyed `RESTART_CMD_BIN` per slot).
