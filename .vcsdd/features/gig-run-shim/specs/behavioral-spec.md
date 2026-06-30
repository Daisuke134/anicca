---
feature: gig-run-shim
mode: lean
sprint: 1
language: python
created: 2026-07-01
parent_spec: docs/superpowers/specs/2026-07-01-proactive-loop-architecture-and-cleanup-design.md
---

# Behavioral Specification — gig-run-shim (sprint-3 #31)

## 1. Purpose

`skills/earn/gig/run.sh` is the main-loop entrypoint for the `earn/gig` slot.
Sprint-3 #31 augments it (= the "shim") to be a coexistence-aware status emitter:

- Existing behavior preserved (= read `~/gig/{applied,earnings}.jsonl`, emit
  status JSON to stdout, ensure tmux core alive via `gig-cli.sh`).
- NEW: observability of LAYER B (= proactive-loop on `~/loops/gig/`).
  Status JSON gains read-only fields summarising LAYER B health so the
  main loop can spot a stale or absent proactive-loop without writing
  ANYTHING under `~/loops/`.

## 2. Out of scope

- Does NOT modify `gig-cli.sh` (= LAYER C tmux core).
- Does NOT install or remove launchd plists (= sprint-3 #30 does that).
- Does NOT write `~/loops/gig/*` (= INV-4 invariant).
- Does NOT change main-loop classifier expectations: the status JSON keeps
  ALL existing keys (`source`, `task`, `funding`, `earn_usdc`, `cost_usdc`,
  `jpy_earned`, `applied_total`, `core`, `wake`, `note`).

## 3. Requirements (EARS)

### Group S — Status augmentation

- **REQ-S1**: WHEN run.sh executes, THE STATUS JSON SHALL retain all existing
  keys verbatim (backward compatibility for main-loop classifier consumers).
- **REQ-S2**: THE STATUS JSON SHALL gain a new `proactive_loop` object key
  with at minimum: `{installed: bool, last_pass_ts: int|null,
  last_pass_step: str|null, build_log_passes: int}`.
- **REQ-S3**: `installed` = true iff
  `~/Library/LaunchAgents/ai.anicca.gig-proactive.plist` exists AND
  `launchctl print gui/<uid>/ai.anicca.gig-proactive` returns rc=0.
- **REQ-S4**: `last_pass_ts` and `last_pass_step` derive from
  `~/loops/gig/state/core-status.json` if it exists, else null.
- **REQ-S5**: `build_log_passes` = count of `## ` lines in
  `~/loops/gig/build_log.md` if it exists, else 0.

### Group I — Invariant adherence

- **REQ-I1** (= parent INV-4): THE SHIM SHALL NOT write ANY file under
  `~/loops/gig/` during execution. Verified by stat-mtime snapshot
  before/after.
- **REQ-I2** (= parent INV-1): THE SHIM SHALL NOT stop / kill /
  `tmux kill-session` the LAYER C tmux core. The only `gig-cli.sh`
  invocations remain: idempotent start (no args) + `--status` read.
- **REQ-I3** (= parent INV-P1): THE SHIM SHALL behave correctly when
  `~/loops/gig/` does not yet exist (= pre-#27 migration state) — all
  observability fields degrade gracefully to null/0/false.

### Group D — No-human-touch (REQ-J8 inherited)

- **REQ-D1**: THE SHIM SHALL NOT call osascript / terminal-notifier /
  Telegram / Slack / Twilio / sudo / SecKeychain / find-generic-password.
- **REQ-D2**: THE SHIM SHALL NOT request elevated privileges.

## 4. Edge cases

| EDGE | Trigger | Expected behavior |
|---|---|---|
| E1 | `~/loops/gig/` does not exist | observability fields = {installed: false, last_pass_ts: null, last_pass_step: null, build_log_passes: 0}; status JSON still emitted normally |
| E2 | `~/loops/gig/state/core-status.json` exists but malformed JSON | last_pass_ts = null, last_pass_step = null; do NOT crash |
| E3 | `~/loops/gig/build_log.md` exists but empty | build_log_passes = 0 |
| E4 | `launchctl` not available (= non-Darwin, unlikely but defensive) | installed = false, status JSON still emitted |
| E5 | Plist file on disk BUT not loaded in launchd | installed = false (= requires BOTH disk AND launchctl print rc=0) |
| E6 | gig-cli.sh missing / fails | preserve current behavior (`|| true`); status JSON emitted with core="" |

## 5. Non-functional requirements

- **NFR-1**: Total added wall-time < 100ms (= run.sh is on the main-loop hot path).
- **NFR-2**: No new external dependencies; only stdlib + standard macOS utilities.
- **NFR-3**: Reads only — no writes anywhere outside what current run.sh already does.

## 6. Traceability

8 requirements + 6 edge cases = 14 minimum test scenarios. Unit tests on a
PURE helper `lib/proactive_observe.py` (cross-platform); 1 integration test
on Darwin that runs the actual shim and parses its JSON output.
