# self-heal-allslots — Behavioral Spec (lean VCSDD, P3)

Generalizes the barren-earning detector (`earning-health.py::is_fresh_but_barren`, currently wired
ONLY to `earn/sol-trade` via `sol-trade-healthcheck.sh`) into a single registry-driven script that
iterates every REQUIRED earn slot: `economy/gig`, `hl_trade`, `x402_sell`, `token_launch`,
`earn/polymarket-trade`, `earn/clip`, `earn/video` (plus `earn/sol-trade` for parity/regression).

## Purity boundary

- **Pure core (reused, unmodified)**: `skills/self/earning-health.py::is_fresh_but_barren` — takes
  a list of trace-line dicts, returns bool. No I/O. Already has its own test file
  (`skills/self/tests/test_earning_health.py`, 9/9 green) — NOT touched by this feature.
- **Pure-ish core (new)**: the registry-loading + per-slot row derivation is pure JSON->rows
  transformation (no side effects beyond reading the registry file itself, which is treated as
  input data, mirroring how `sol-trade-healthcheck.sh` treats its trace file as input data).
- **Effectful shell (new)**: `skills/self/earning-health-allslots.sh` — reads the registry file,
  tails each instrumented slot's trace file, calls `self-fix.sh` on a confirmed BARREN verdict,
  writes an escalation marker + log lines. Mirrors `sol-trade-healthcheck.sh`'s existing shell
  exactly, generalized to loop over N slots instead of being hardcoded to one.

## Requirements

### REQ-AS-001: Registry-driven slot iteration
**EARS**: WHEN `earning-health-allslots.sh` runs THE SYSTEM SHALL read a JSON registry
(`skills/self/earning-health-registry.json`, or `$EARNHC_REGISTRY` override) listing every earn
slot to check, and evaluate EVERY entry in it — no slot silently skipped, no slot hardcoded outside
the registry.
**Edge Cases**:
- Registry file missing: log `no registry at <path>` and exit 0 (never crash a launchd tick).
- Registry file present but empty `slots: []`: loop body runs zero times, exits 0 cleanly.
**Acceptance Criteria**:
- A registry with N slots produces exactly N per-slot log lines (or per-slot no-op) per run.

### REQ-AS-002: Instrumented slot uses the SAME pure barren check, unmodified
**EARS**: WHEN a registry entry has `instrumented: true` AND its trace file exists THE SYSTEM SHALL
tail the trace, pipe it through the SAME `earning-health.py is-barren <minRun>` used by
`sol-trade-healthcheck.sh` (never a forked/rewritten copy of the predicate), and treat a `true`
result as BARREN.
**Edge Cases**:
- Trace file does not exist yet (slot deployed but never run here): log "no trace file", no-op —
  never fabricate a verdict from absent data.
- Trace has fewer than `minRun` lines: `is_fresh_but_barren` itself returns False (existing,
  untouched behavior) — surfaced as "OK".
**Acceptance Criteria**:
- A trace of `minRun` identical-reason `action:"skip"` lines → BARREN.
- A trace ending in ANY `action != "skip"` line (a real live-pass/decision) → NOT barren, regardless
  of how many skip lines precede it.

### REQ-AS-003: BARREN escalates to self-fix, scoped to that slot, rate-limited
**EARS**: WHEN an instrumented slot is confirmed BARREN THE SYSTEM SHALL invoke
`self-fix.sh <selfFixTarget> <hint>` for THAT slot only (never a different slot's target), and
SHALL NOT re-invoke it again for the same slot within `escalateEveryHrs` (default 24) — mirroring
`sol-trade-healthcheck.sh`'s existing anti-spam marker, generalized per-slot via a
slot-id-derived marker filename so N slots never collide on one shared marker.
**Edge Cases**:
- Two different slots BARREN in the same run: two independent `self-fix.sh` calls, two independent
  markers — never conflated into one.
- Same slot BARREN on back-to-back runs inside the window: second run logs "already escalated",
  does NOT call `self-fix.sh` again.
**Acceptance Criteria**:
- Marker file path is unique per slot id (verified: `earn/slot-a` and `earn/slot-b` produce
  different marker filenames).
- `self-fix.sh` is called with EXACTLY the slot's own `selfFixTarget`, never a hardcoded literal.

### REQ-AS-004: Non-instrumented slot is a DOCUMENTED gap, never a fabricated verdict
**EARS**: WHEN a registry entry has `instrumented: false` THE SYSTEM SHALL log a `NOT-INSTRUMENTED`
line (including the entry's `gapNote`) and SHALL NEVER call `self-fix.sh` for it and SHALL NEVER
log it as `OK` or `BARREN` (both would be a fabricated verdict over data that does not exist).
**Edge Cases**:
- A `gapNote` field is required for every `instrumented:false` entry (honesty: the registry itself
  states WHY a slot isn't covered yet, not just THAT it isn't).
**Acceptance Criteria**:
- `NOT-INSTRUMENTED <slot-id>` appears in the log for every `instrumented:false` entry, on every
  run, with zero `self-fix.sh` invocations attributable to it.

### REQ-AS-005: One launchd job, not N
**EARS**: WHEN this feature is deployed THE SYSTEM SHALL be wired via exactly ONE launchd job
(`ai.anicca.earning-health-allslots`) that runs the ONE generalized script — never one plist per
slot.
**Acceptance Criteria**:
- Exactly one new `.plist` file is added under `skills/self/launchd/`.
- The plist is NOT copied into `~/Library/LaunchAgents/` and NOT `launchctl load`ed by this sprint
  (explicit instruction: Dais reviews first).

### REQ-AS-006: Franklin-scoped detection path (data), documented self-fix graduation gap (fixer)
**EARS**: WHEN the script resolves paths THE SYSTEM SHALL resolve the registry + trace directory
relative to ITS OWN script location (mirrors `sol-trade-healthcheck.sh`'s `SKILL_DIR`-relative
pattern) so a deployed copy (e.g. Franklin's `~/.blockrun`) checks its OWN adjacent state, never a
different instance's hardcoded absolute path baked into shared OSS code.
**Non-functional / documented gap (NOT fixed this sprint, see CHANGELOG.md)**: `self-fix.sh` itself
writes its bookkeeping (`STATE`, `LOG`, `RESULT`, lock files) under `$HOME/.openclaw/{state,logs}`
— that tree is shared across every instance on this single-user Mac Mini (claude-p/Dais's own
OpenClaw store, per `~/anicca-project/CLAUDE.md`'s "ローカル + push 先マップ"), NOT per-instance
`ANICCA_HOME`-scoped. Additionally the fixer it spawns is the Anthropic `claude` CLI, i.e. whichever
Claude Code login is active on this shared macOS user account (today: claude-p's human-funded
Anthropic subscription) — NOT Franklin's own self-funded compute (BlockRun/x402 SOL wallet). So a
Franklin-triggered healthcheck CAN call `self-fix.sh` without claude-p's session running (it is a
fresh detached `tmux`+`claude` spawn, not dependent on an existing process) — but the repair itself
is currently PAID FOR by the human-funded subscription, not Franklin's own economy. Full
independence requires either giving Franklin its own `claude` credential/budget or swapping the
fixer to a self-funded model path.

## Non-functional
- Never modifies `earning-health.py`'s tested pure function.
- Never crashes a launchd tick on missing registry/trace/self-fix.sh (all failure paths degrade to
  a logged no-op, matching `sol-trade-healthcheck.sh`'s existing `set -uo pipefail` + guarded reads).
- Money-safety untouched: this feature only READS trace files and calls `self-fix.sh` (which itself
  already has its own kill-switch/backoff/lock guards) — no new signing key, no new spend path.
