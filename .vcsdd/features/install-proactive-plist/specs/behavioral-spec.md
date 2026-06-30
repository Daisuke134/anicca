---
feature: install-proactive-plist
mode: lean
sprint: 1
language: python
created: 2026-07-01
parent_spec: docs/superpowers/specs/2026-07-01-proactive-loop-architecture-and-cleanup-design.md
---

# Behavioral Specification — install-proactive-plist (sprint-3 #30)

## 1. Purpose

`install-proactive-plist.sh <slot>` generates a per-slot launchd plist from the
canonical template (= architecture spec §3) and loads it. Idempotent. Used by
sprint-3 #27 (gig migration) + sprint-3 #28 (5 remaining slots).

## 2. Out of scope

- Does NOT migrate the slot's run.sh (that is sprint-3 #31).
- Does NOT modify menu.json / tasks / state — only installs the launchd job.
- Does NOT touch the existing `<slot>-core-healthcheck.plist` (= belt-suspenders).
- Does NOT pick the cadence — fixed at 300 s (= 5 min) per architecture spec.

## 3. Requirements (EARS)

### Group A — Plist generation

- **REQ-A1**: WHEN invoked as `install-proactive-plist.sh <slot>`, THE SCRIPT
  SHALL emit a plist at the absolute path
  `/Users/<unix-uid-name>/Library/LaunchAgents/ai.anicca.<slot>-proactive.plist`
  (= `$HOME` expanded at install-time, NOT a literal `$HOME` token) whose
  contents match the canonical template in architecture spec §3.
- **REQ-A2**: THE PLIST `ProgramArguments` SHALL be exactly
  `["/bin/bash", "<ANICCA_HOME>/skills/_shared/proactive-loop.sh", "<slot>"]`
  where `<ANICCA_HOME>` is resolved at install-time by the SCRIPT to its own
  enclosing repo root (= `git rev-parse --show-toplevel` of the script's own
  realpath dir). The spec PINS the canonical install location as
  `/Users/operator/anicca/` (= the OSS framework repo, NOT `~/anicca-project`).
  If the resolved repo root does not match the pin, the SCRIPT SHALL exit
  non-zero with stderr "anicca repo root mismatch: expected /Users/operator/anicca,
  got <X>" (= prevents accidental install from a worktree or sibling clone).
- **REQ-A2a**: `Label`, `StartInterval`, `RunAtLoad` SHALL be exactly
  `ai.anicca.<slot>-proactive`, `300`, `false` respectively.
- **REQ-A3**: THE PLIST SHALL set `StandardOutPath` and `StandardErrorPath` to
  ABSOLUTE expanded paths `/Users/<uid>/.openclaw/logs/<slot>-proactive.out`
  and `.../.err` (= `$HOME` resolved at install-time, since launchd does NOT
  expand `$HOME` in plist values — confirmed by parent architecture spec §3
  L117-118 which uses the literal absolute path).
- **REQ-A4**: WHEN the slot argument contains any character outside
  `[a-z0-9_-]` OR is empty OR exceeds 32 chars, THE SCRIPT SHALL:
  (i) emit the validation error to stderr, (ii) exit non-zero,
  (iii) HAVE NOT touched the filesystem under `~/Library/LaunchAgents/` or
  `~/.openclaw/logs/` (= mtimes unchanged) AND HAVE NOT called `launchctl`
  (= no bootout/bootstrap attempted).
  Validation MUST run as the FIRST executable step after argument parsing,
  BEFORE any `mkdir`, file write, or `launchctl` call. The validation step
  MAY itself shell out to `python3 -m lib.plist_render validate` (= a
  read-only subprocess with no fs/launchctl side-effects); this read-only
  subprocess invocation is part of the validation step, not a violation of
  the ordering rule (= FIND-004 clarification).

### Group B — Idempotent install

- **REQ-B1**: WHEN the plist already exists with identical content, THE SCRIPT
  SHALL exit 0 silently (= no rewrite, no churn).
- **REQ-B2**: WHEN the plist exists with DIFFERENT content (= template changed),
  THE SCRIPT SHALL rewrite it, then `launchctl bootout` (if loaded) and
  `launchctl bootstrap` to pick up the new template.
- **REQ-B3**: WHEN the plist does not exist, THE SCRIPT SHALL write it AND
  `launchctl bootstrap gui/<uid>` to load it.
- **REQ-B4**: THE SCRIPT SHALL be safe to call N times in a row producing
  exactly one loaded job (= "idempotent install").

### Group C — Verification

- **REQ-C1**: AFTER successful install, THE SCRIPT SHALL run
  `launchctl print gui/<uid>/ai.anicca.<slot>-proactive` and exit non-zero if
  the job is not in `state = running` (when due) or `state = waiting` (between
  ticks). I.e. confirm the job is actually loaded, not just written to disk.
- **REQ-C2**: THE SCRIPT SHALL print a one-line summary on stdout:
  `installed ai.anicca.<slot>-proactive (plist=<path>, interval=300s)`.

### Group D — No-human-touch (REQ-J8 inherited)

- **REQ-D1**: THE SCRIPT SHALL NOT call `osascript`, `terminal-notifier`,
  Telegram, Slack, Touch-ID prompts, or any human-targeted side-effect.
- **REQ-D2**: THE SCRIPT SHALL NOT request elevated privileges (= no `sudo`).

### Group E — Existing-plist conflict guard

- **REQ-E1**: WHEN any LaunchAgent labelled `ai.anicca.<other-slot>-*`
  (= a sibling job, including but not restricted to `<slot>-core-healthcheck`)
  is loaded in launchd before THIS SCRIPT runs, THAT SAME sibling job SHALL
  remain loaded at the SAME path after THIS SCRIPT exits 0 (= INV-6 of
  architecture spec). The test asserts path-identity via `launchctl print`
  `path =` (= a bootout-then-rebootstrap to the same path STILL counts as
  path-identity preserved; the test does NOT require PID identity because
  the sibling may not be currently running). To make this verifiable in CI
  even without a real core-healthcheck loaded, the test SHALL bootstrap a
  controlled minimal sibling job before invoking THIS SCRIPT (= FIND-003 fix
  to remove the skip-when-absent escape hatch).
- **REQ-E2**: WHEN a plist labeled `ai.anicca.<slot>-proactive` is already
  loaded from a path DIFFERENT than the one this script will write, THE SCRIPT
  SHALL detect the collision by parsing the `path =` line of
  `launchctl print gui/<uid>/ai.anicca.<slot>-proactive`, comparing it to the
  canonical install path, and if they differ, `launchctl bootout gui/<uid>
  ai.anicca.<slot>-proactive` BEFORE writing the new plist. The detection
  algorithm: (i) `launchctl print` returns 0 → service exists; (ii) grep the
  output for `^	path = (.+)$`; (iii) trim whitespace; (iv) if the grepped
  path != canonical install path → call bootout (= prevents two LAYER A
  plists per slot, INV-6).

## 4. Edge cases

| EDGE | Trigger | Expected behavior |
|---|---|---|
| E1 | `$HOME/Library/LaunchAgents/` does not exist | mkdir -p, then proceed |
| E2 | `$HOME/.openclaw/logs/` does not exist | mkdir -p before launchctl bootstrap |
| E3 | invoked with no slot arg | exit non-zero, stderr "Usage: install-proactive-plist.sh <slot>" |
| E4 | invoked with slot = "gig; rm -rf /" | exit non-zero per REQ-A4 (injection guard) |
| E5 | launchctl bootstrap fails (= launchd disagreement) | print stderr error, exit non-zero, do NOT leave a half-loaded job |
| E6 | called from non-Darwin (= Linux test env) | exit 2 with stderr "Darwin only" (= don't generate broken plist on Linux) |
| E7 | called twice in parallel for the same slot | second invocation sees identical disk content per REQ-B1 and exits 0 — no race |

## 5. Non-functional requirements

- **NFR-1**: Pure shell + standard macOS utilities (`/bin/bash`,
  `/usr/bin/launchctl`, `plutil`, `xxd`/`shasum`). No Python dependency.
- **NFR-2**: Total wall-time < 1 s per invocation (= safe to call from STEP 3
  health-check recipe if a job goes missing).
- **NFR-3**: Stderr goes to stderr; stdout reserved for the REQ-C2 summary so
  callers can grep stdout for the one summary line.

## 6. Traceability hooks

- REQ-A1..A4, REQ-B1..B4, REQ-C1..C2, REQ-D1..D2, REQ-E1..E2 each map to a test.
- EDGE E1..E7 each map to a fixture.
- 15 requirements + 7 edge cases = 22 test scenarios minimum.
