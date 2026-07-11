# mainloop-timeout-fix — behavioral spec (lean)

## Problem (observed, not theoretical)

`claude-p-mainloop.sh` wraps its `claude --model sonnet -p ...` invocation in `timeout 3600`
(1 hour, hardcoded). `~/.openclaw/logs/claude-p-mainloop.out.log` shows the last 6 fires:

```
2026-07-10T00:00:03Z exit status=0
2026-07-10T06:38:15Z exit status=0
2026-07-10T13:38:14Z exit status=124   <- killed by timeout
2026-07-10T20:38:18Z exit status=124   <- killed by timeout
2026-07-11T02:54:48Z exit status=0
2026-07-11T09:54:50Z exit status=124   <- killed by timeout
```

3 of the last 6 runs (50%) were killed mid-run by the hard 3600s ceiling. `MAINLOOP-LOG.md`
records full VCSDD passes (spec -> fresh-adversary spec-review -> TDD RED -> impl GREEN ->
fresh-adversary impl-review -> harden -> converge -> self-merge) as routine work for this loop;
that sequence legitimately runs past 1h. This was already flagged as TODO `T-revive` in
`docs/loop-engineering/10-STATUS-verified.md` §D item 2 (2026-07-10) and never fixed.

Effect: the AGENT ECONOMY LOOP (this loop's own name for itself, see
`docs/loop-engineering/04-the-two-loops.md` §9) — whose entire job is to build self-heal/
self-improve capability for the colony — cannot itself reliably finish a single OBSERVE-BUILD-
VERIFY-MERGE pass. This is the parent loop failing at the same class of problem it exists to fix
in its children.

## REQ-001: timeout ceiling is resolved by a pure, testable function

WHEN `claude-p-mainloop.sh` is about to invoke `claude`, THE SYSTEM SHALL determine the `timeout`
duration by calling `resolve_mainloop_timeout_sec()`, a function defined in a separate sourceable
file `skills/self/mainloop-timeout-lib.sh` (mirrors the existing `healthcheck-lib.sh` /
`test-healthcheck-lib.sh` split in this same directory), so the resolution logic can be unit
tested without invoking the real `claude` binary.

## REQ-002: default ceiling is safely above the old 3600s value

WHEN `CLAUDE_P_MAINLOOP_TIMEOUT_SEC` is unset (or not a positive integer), THE SYSTEM SHALL
default `resolve_mainloop_timeout_sec()` to a value strictly greater than 3600 (the old ceiling
that caused the observed 50% kill rate) AND strictly less than 21600 (the plist's `StartInterval`
— the fire cadence), so a stuck/slow run still yields to the single-instance pidfile guard before
the next scheduled fire rather than racing it. Chosen default: 18000 (5h) — 5x the old ceiling, 1h
of buffer before the next 6h fire.

## REQ-003: override is respected when valid

WHEN `CLAUDE_P_MAINLOOP_TIMEOUT_SEC` is set to a positive integer string, THE SYSTEM SHALL use
that exact value instead of the default (so the ceiling is tunable in the plist's
`EnvironmentVariables` without a code change, and testable without waiting hours).

## REQ-004: invalid override falls back safely, never below the old ceiling

WHEN `CLAUDE_P_MAINLOOP_TIMEOUT_SEC` is set to a non-numeric string, zero, or a negative number,
THE SYSTEM SHALL fall back to the REQ-002 default (never crash, never silently use 0/negative as
a `timeout` argument, which would either error `timeout` outright or disable the ceiling
entirely).

## REQ-005: the fix is wired into the real script, not just the library

WHEN `claude-p-mainloop.sh` runs for real, THE SYSTEM SHALL source
`skills/self/mainloop-timeout-lib.sh` and use `resolve_mainloop_timeout_sec()`'s output as the
literal `timeout` argument (not a re-hardcoded 3600), AND SHALL log the resolved value in the
existing `"launching claude ... (hard timeout Xs)"` log line so a human/adversary reading
`claude-p-mainloop.out.log` can see which ceiling was actually used for a given fire.

## REQ-006: override is clamped, never exceeds the fire cadence

WHEN `CLAUDE_P_MAINLOOP_TIMEOUT_SEC` is set above 21600 (the plist's `StartInterval`), THE SYSTEM
SHALL clamp `resolve_mainloop_timeout_sec()`'s output to 21600, because GNU `timeout` can silently
no-op on values large enough to overflow `setitimer`, which would defeat the ceiling entirely.

## REQ-007: missing lib file fails loudly, not silently

WHEN `skills/self/mainloop-timeout-lib.sh` is missing at run time, THE SYSTEM SHALL log a `FATAL`
line to `LOG_ERR` and exit 1 before attempting to invoke `claude` (mirrors the existing
`PROMPT_FILE` missing-file check), rather than continuing with an undefined
`resolve_mainloop_timeout_sec` and an empty `TIMEOUT_SEC`.

## Out of scope (explicitly not touched)

- No change to `StartInterval` (21600s), `ThrottleInterval` (300s), or any other plist field.
- No change to the pidfile single-instance guard, kill-switch, or prompt file.
- No change to wallet keys, `.env`, spend caps, or anything that moves money.
- Detecting/escalating on a 124 *after* it happens is a separate, larger, already-in-flight
  feature (`feature/claude-p-mainloop-healthcheck` worktree, stalled at spec-review iteration 4)
  — this fix reduces how often 124 happens at the source; it does not replace that detector.

## Verification architecture (lean)

- **Tier 1 (pure function, unit-tested)**: `resolve_mainloop_timeout_sec()` — REQ-001..004,
  tested by `skills/self/tests/test_mainloop_timeout_lib.sh` sourcing the lib directly, zero
  side effects, zero real `claude` invocation.
- **Tier 2 (wiring, static)**: REQ-005 verified by grepping the real script for the source line
  and the absence of a re-hardcoded `timeout 3600`.
- Fresh adversary (Sonnet, per this repo's model-division table) reviews the diff + runs the test
  file before merge.
