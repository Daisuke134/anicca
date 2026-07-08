# Behavioral Spec — anicca-harness-tooluse-health (VCSDD Phase 1a/1b, lean)

## Problem (grounded in current code + measured ledgers)
`~/anicca/skills/earn/self-improve/evaluator.py`'s `combined_score` is `gate_math.risk_adjusted_score`
over a **backtested historical CSV fixture only** (`evaluate_stage2`, module docstring: "never an LLM
judge's subjective score... never influenced by anything else"). `~/anicca/skills/self/self-improve/lib/ledger_metrics.py`'s
`score_from_rows` is `views`+`earn_usdc/jpy` only. **Grep confirms**: neither `self/self-improve` nor
`earn/self-improve` trees reference `skill_error`, `wake_error`, `exit_code`, or `EACCES` anywhere — the
self-improvement system is structurally blind to whether the tool calls underneath a strategy/loop
actually EXECUTED, as distinct from whether the strategy made money.

Real measured non-clean-wake rate ≈23% across both live wake ledgers (`~/.anicca/state/ledger.jsonl`,
`~/.blockrun/state/ledger.jsonl`), with individual slots as high as 61-71% `skill_error`. The raw
diagnostic signal for WHY is destroyed before persistence: `runtime/loop/index.mjs`'s `safeObservation`
is `.replace(/\s+/g,' ').slice(0, 900)` (line ~447/465 — **corrected, iteration 2, resolves FIND-006:**
this cap was raised from 180 to 900 chars, and the earlier `.slice(0, 500)` intermediate cap at line 447
was raised to 1200, by a prior hygiene fix (task #119), BEFORE this feature's own Phase 1a was written;
this spec's ground-truth text had not been updated to match) — even 900 characters is not enough to see
where in a multi-step fallback chain a skill actually broke.

External grounding (cited, not re-derived): Reflexion (arxiv.org/abs/2303.11366) — verbalize failures
into context, don't discard them; 12-Factor Agents Factor 9 (github.com/humanlayer/12-factor-agents) —
compact errors into context AND maintain a per-tool consecutive-error counter that escalates after ~3
failures rather than looping forever; n8n tool-error-handling (blog.n8n.io/llm-tool-calling-error-handling)
— classify failures by layer, never blend a layer the model can't act on into a report meant for a
different layer; Braintrust agent eval framework (braintrust.dev/articles/ai-agent-evaluation-framework)
— score REASONING/ACTION/END-TO-END separately, never collapse into one number; NVIDIA SLM position
paper (developer.nvidia.com/blog/how-small-language-models-are-key-to-scalable-agentic-ai) — free-tier
models are reliable specifically on narrow, fixed-format subtasks, so a narrow deterministic classifier
over the ALREADY-fixed `kind` enum is the right shape of fix, not a bigger model.

## Ground-truth live code (read before writing any GREEN code)
- `runtime/loop/index.mjs` — `runOneWake()`: THINK failure → `kind:'wake_error'` (no `slot`, brain never
  reached tool selection) at the `catch` around line 351; skill dispatch → `kind` ∈
  `{skill_missing, skill_timeout, skill_error, wake}` (lines 429-441, deterministically derived from
  `skillResult.notFound/timedOut/exitCode` — already fixed-enum bookkeeping, not model judgment);
  `loop_detect` kind (line ~281) already has its OWN consecutive-streak + exponential-backoff mechanism
  (`loopDetectStreak`/`loopDetectSlot`, lines 180-284) — untouched by this feature. **`loop_detect`
  records DO carry a `slot` field** (`formatRecord({..., kind: 'loop_detect', slot: avoidSlot, ...})`,
  line 281 — the just-avoided real skill slot name); confirmed live: 238/1063 `loop_detect` rows in
  `~/.anicca/state/ledger.jsonl` (22%) carry a real slot value (e.g. `x402_sell`/`cook`). R2 MUST
  exclude `kind==='loop_detect'` from its slot-matching subset regardless of this shared `slot` field —
  see R2 and INV-LOOPDETECT-SEPARATE.
- `runtime/loop/ledger-record.mjs::formatRecord` (pure, JSON.stringify+`\n`) and `runtime/loop/ledger.mjs::appendLedgerLine`
  (effectful, `O_APPEND`) — the two primitives this feature reuses verbatim, never reimplements.
- `runtime/loop/env-filter.mjs::redactPrivateKeyPatterns` — already applied to `skillResult.output`
  before it reaches `runOneWake`'s scope (called once inside `runSkillWithKillRef`, once again in step
  10) — this feature's larger-capture side-channel reuses this SAME already-redacted string for the
  `tool_missing`/`tool_timeout`/`tool_logic` branches only, never a new/different redaction pass for
  those. The `brain_transport` branch's `err.message` is **NOT** covered by any existing redaction call
  anywhere upstream (traced into `brain.mjs`'s `thinkProxy`/`thinkClaudeP`/`httpPost`: raw HTTP-response
  body / raw subprocess stderr, never passed through `redactPrivateKeyPatterns`) — R6 below adds the ONE
  new `redactPrivateKeyPatterns(err.message)` call site this feature genuinely introduces.
- `runtime/loop/context.mjs::assembleContext` + `runtime/loop/prompt.mjs` (line ~130:
  `JSON.stringify(ctx.recentLedgerLines, null, 2)`) — the live wake prompt embeds up to 20 WHOLE ledger
  records verbatim. Any new field added directly to `ledger.jsonl` records is a token-budget cost paid
  on EVERY future wake. This is why the fuller diagnostic detail this feature adds must NOT live inside
  `ledger.jsonl`/`result` (INV-NO-PROMPT-REGRESSION below).
- `skills/self/healthcheck-runtime-loop.sh` — the EXISTING self-heal escalation path for
  `runtime/loop/index.mjs` **KeepAlive** instances (`anicca-a3cdd4`/`Franklin`/`claude-p-proxy` — each
  is a `launchctl` `KeepAlive` job reading a `runtime/loop/index.mjs`-produced `ledger.jsonl`, confirmed
  at `healthcheck-runtime-loop.sh:97,99`). `claude-p-pm` (`ai.anicca.pm-earner`) is explicitly OUT of
  this feature's ground truth: its own header comment states "StartInterval 600s, body
  `~/.anicca-founder/agents/polymarket-agent`", and its `check()` invocation
  (`healthcheck-runtime-loop.sh:98`) uses `kind=interval` over
  `earn/polymarket-trade/earner.log` — a plain log file from the polymarket-trade earn skill, not a
  `runtime/loop/index.mjs` KeepAlive wake-loop with a ledger.jsonl; R1-R8 do not apply to it. Its
  `hrl_classify` only judges process-liveness + ledger-file `mtime` staleness — it CANNOT see that a
  process is alive and writing fresh lines every wake while one specific slot fails on every single
  invocation (mtime keeps advancing regardless of `kind`). `skills/self/self-fix.sh` is the detached
  Opus-fixer this and `healthcheck-lib.sh` already invoke (`_selffix()` → `bash self-fix.sh <name> <hint>`)
  — this feature produces the signal a FUTURE caller of that exact same function would consume; it does
  not add a new caller (see R10/Scope).
- `skills/earn/self-improve/evaluator.py` + `skills/self/self-improve/lib/ledger_metrics.py` +
  `skills/self/self-improve/weekly_report.py` — read for the "zero matches" confirmation above; NONE of
  the three is modified by this feature (R9).

## New artifacts this feature introduces (GREEN, Phase 2b)
- `runtime/loop/harness-health.mjs` — pure aggregator (R1-R5).
- `runtime/loop/harness-health-snapshot.mjs` — impure CLI writer (R7).
- New side-channel file `$ANICCA_HOME/state/harness-failures.jsonl` (R6) and derived snapshot
  `$ANICCA_HOME/state/harness-health.json` (R7). Neither is read by `context.mjs`/`prompt.mjs`.
- `skills/self/self-improve/lib/harness_health.py` — Python mirror of R1-R5 (R8).
- `skills/self/self-improve/harness_health_report.py` — thin CLI, the self-improve-consumable surface (R8).

## 1a. Requirements (EARS)

- **R1 (layer classification — pure, deterministic bookkeeping over an already-fixed enum)**
  `classifyLayer(record)` SHALL map `record.kind` (the enum `index.mjs` ALREADY assigns
  deterministically from `exitCode`/`timedOut`/`notFound` — this REQ adds no new judgment) to exactly
  one of: `clean` (`kind` ∈ `{wake, narrate, shutdown}`), `brain_transport` (`kind==='wake_error'`),
  `tool_missing` (`kind==='skill_missing'`), `tool_timeout` (`kind==='skill_timeout'`), `tool_logic`
  (`kind==='skill_error'`). `loop_detect` is explicitly OUT of this mapping (INV-LOOPDETECT-SEPARATE). An
  unrecognized future `kind` value SHALL map to `unknown` (fail-safe, never throw).

- **R2 (per-slot tool-call health — pure)** `computeSlotHealth(records, slot)` SHALL, over only the
  subset of `records` carrying that exact `slot` value **AND** `kind` ∈ `{wake, skill_missing,
  skill_timeout, skill_error}` — `wake_error` never carries a `slot`, R3 covers it separately.
  **`loop_detect` records also carry a `slot` field** (the just-avoided slot, `index.mjs:281`) but SHALL
  be **explicitly excluded** from this subset by a `kind`-membership check regardless of whether their
  `slot` matches (INV-LOOPDETECT-SEPARATE — `loop_detect` already has its own separate
  streak/backoff mechanism and must never be counted as a tool-call outcome for any slot; this exclusion
  is a required filter step, not merely implied by `kind` matching one of the four listed values). The
  function SHALL return `{ slot, wakes, failures, failureRate, consecutiveFailureStreak, lastFailureLayer,
  lastFailureTs, lastFailureWakeId }` where `failures` counts non-`clean`-layer records, `failureRate =
  failures/wakes`, and `consecutiveFailureStreak` = the count of trailing non-`clean` records for that
  slot scanning the chronologically-ordered subset from its END backward, resetting to 0 at the first
  `clean` (`kind==='wake'`) record encountered. A `slot` absent from `records` entirely (after the
  `loop_detect` exclusion) SHALL return `null`.

- **R3 (loop-level brain-transport health — pure, separate from any slot)** `computeBrainTransportHealth(records)`
  SHALL scan ALL `wake_error` records (which never carry `slot` — R1) across the WHOLE ledger and return
  `{ failures, consecutiveFailureStreak, lastFailureTs, lastFailureWakeId }` using the same trailing-streak
  rule as R2, reset by any record whose `kind` ∈ `{wake, narrate}`. Never conflated with any single slot's
  health (a proxy outage is a loop-level condition, not one tool's fault).

- **R4 (whole-ledger report shape — pure)** `computeHarnessHealth(records, { streakThreshold } = {})` SHALL
  return `{ perSlot: { [slot]: <R2 shape & escalate> }, brainTransport: <R3 shape & escalate>, generatedAt }`
  covering every distinct `slot` value present in `records`, where each entry's `escalate` field is R5's
  result for that entry's `consecutiveFailureStreak`. An empty `records` array SHALL return
  `{ perSlot: {}, brainTransport: { failures: 0, consecutiveFailureStreak: 0, ...}, generatedAt }` — never throw.

- **R5 (escalation predicate — pure)** `shouldEscalate(consecutiveFailureStreak, threshold)` SHALL return
  `true` iff `consecutiveFailureStreak >= threshold`. `DEFAULT_STREAK_THRESHOLD` SHALL be
  `Number(process.env.HARNESS_HEALTH_STREAK_THRESHOLD) || 5` (same `Number(process.env.X) || N` idiom
  already used by `catalog-gate.mjs`'s `DEFAULT_BOOTSTRAP_RESERVE_USDC`). This predicate SHALL NOT itself
  invoke any repair action (R10).

- **R6 (failure-detail side-channel — additive, does not touch the live prompt path)** On every wake
  where `classifyLayer` would yield `brain_transport` (the THINK-failure `catch`, ~line 351) or
  `tool_missing`/`tool_timeout`/`tool_logic` (post-dispatch, ~lines 429-471), `runOneWake` SHALL append
  exactly one JSON line to `$ANICCA_HOME/state/harness-failures.jsonl` via the EXISTING
  `appendLedgerLine` primitive (never a new writer): `{ ts, wake_id, slot?, kind, layer, exit_code,
  detail }` where `detail` is built as follows: for `tool_missing`/`tool_timeout`/`tool_logic`,
  `skillResult.output` is the ALREADY-redacted string in scope at that point (passed through
  `redactPrivateKeyPatterns` upstream inside `runSkillWithKillRef` and again at ledger-write time — R6
  reuses this same already-redacted string for these three branches, no new redaction pass needed here);
  for `brain_transport`, `err.message` is **NOT** already redacted anywhere upstream (raw HTTP-response
  body / subprocess-stderr text from `brain.mjs`'s `thinkProxy`/`thinkClaudeP`/`httpPost`) — R6 SHALL
  therefore apply `redactPrivateKeyPatterns(err.message)` itself as a NEW call site for this branch only,
  reusing the SAME existing `env-filter.mjs` function `index.mjs` already imports (never a new/different
  redaction implementation), before any further processing. Both branches' resulting string is then
  whitespace-collapsed and capped at **4000 characters** (vs the existing 900-char `result` field —
  **corrected, iteration 2, resolves FIND-006** — left completely unchanged). `slot` is omitted for `brain_transport` (R1: brain-transport failures precede
  tool selection). A `clean`-layer wake SHALL append NOTHING to this file.

- **R7 (snapshot writer — impure, new script, no cron wiring in this slice)** `runtime/loop/harness-health-snapshot.mjs`
  SHALL, when invoked (`node harness-health-snapshot.mjs`, reading `$ANICCA_HOME` from env exactly as
  `index.mjs` does), read `$ANICCA_HOME/state/ledger.jsonl` via the EXISTING `readLedgerLines`, compute
  R4's `computeHarnessHealth`, and overwrite (not append — this is a derived VIEW, not an event log)
  `$ANICCA_HOME/state/harness-health.json` with the result. A missing/unreadable `ledger.jsonl` SHALL
  produce the R4 empty-ledger shape, never crash. Scheduling this script (launchd/cron cadence) is
  explicitly deferred — same precedent `healthcheck-runtime-loop.sh`'s own header comment already states
  for itself ("NOT wired into cron/launchd by this script — scheduling is a separate, reviewed step").

- **R8 (Python mirror for self-improve consumption — additive, new files only)**
  `skills/self/self-improve/lib/harness_health.py` SHALL expose `classify_layer`, `compute_slot_health`,
  `compute_brain_transport_health`, `compute_harness_health`, `should_escalate` — the R1-R5 rules
  re-implemented in Python (parity fixture-tested, 1b), reusing `ledger_metrics.load_ledger_rows` for
  jsonl parsing (never a new/duplicated jsonl loader). `skills/self/self-improve/harness_health_report.py`
  SHALL be a thin CLI (`python3 harness_health_report.py <ledger_path> [--threshold N]`) printing
  `compute_harness_health`'s JSON — the concrete surface a self-improve consumer (or a future self-fix
  caller) reads. Neither file is imported by, nor changes the return shape of,
  `skills/earn/self-improve/evaluator.py` or `skills/self/self-improve/weekly_report.py` (R9) — those
  operate on a disjoint domain (a frozen backtest fixture; per-EDD-loop outcome ledgers) that does not
  contain wake-loop tool-call data at all.

- **R9 (backward compatibility / non-interference)** None of R1-R8 change: `ledger.jsonl`'s existing
  schema or the 900-char `result` field (**corrected, iteration 2, resolves FIND-006**); `context.mjs`/`prompt.mjs`'s prompt assembly or token footprint;
  `evaluate()`/`evaluate_stage1()`/`evaluate_stage2()`'s `combined_score` computation in
  `skills/earn/self-improve/evaluator.py` (still 100% backtest-derived, per its own documented
  invariant); `weekly_report.py`'s existing `combined_score`/`beats_previous_week` output; or
  `skills/self/healthcheck-runtime-loop.sh`'s existing `hrl_classify`/staleness behavior. All of R1-R8 are
  additive (new files, new optional keys, new side-channel paths).

- **R10 (no auto-action, no trading/strategy judgment — explicit scope boundary)** This feature is
  READ/OBSERVE/RECORD only. `shouldEscalate`'s only observable effect anywhere in this slice is a boolean
  field inside `harness-health.json` / `harness_health_report.py`'s printed JSON. Nothing built in this
  feature calls `skills/self/self-fix.sh`, retries/kills a skill, changes `EARN_MODE`/`EARN_STRATEGY`, or
  alters any promotion/demotion decision in `evaluator.py`. Wiring the escalation flag into an actual
  `self-fix.sh` invocation (a new call site analogous to `healthcheck-runtime-loop.sh`'s existing
  `_selffix()`) is explicit FOLLOW-UP work, out of scope for this slice.

## Invariants
- **INV-NO-JUDGMENT**: R1/R5 are pure bookkeeping over the ALREADY-deterministic `kind` enum
  `index.mjs` itself assigns via if-else on `exitCode`/`timedOut`/`notFound` (not model output free text).
  R6's `detail` is captured VERBATIM for a human/self-fix agent to read and judge root cause — this
  feature never parses or re-classifies that free text itself (would be the banned regex-as-judgment
  anti-pattern per `~/.claude/rules/building-effective-ai-agents.md`).
- **INV-NO-PROMPT-REGRESSION**: `ledger.jsonl`'s `result` field stays at its existing 900-char cap
  (**corrected, iteration 2, resolves FIND-006** — this feature must never shrink it back toward 180, which
  would regress task #119's own prior hygiene fix);
  `context.mjs`/`prompt.mjs` never read `harness-failures.jsonl` or `harness-health.json`. Verified by R6's
  proof obligation asserting `result`'s length/content is byte-identical to pre-feature behavior.
- **INV-LOOPDETECT-SEPARATE**: `loop_detect` already has its own consecutive-streak + exponential
  cooldown (`index.mjs` lines 180-284), untouched. R1-R5's counters cover ONLY
  `{skill_error, skill_timeout, skill_missing}` (reset by `wake`) and `wake_error` (R3, reset by
  `wake`/`narrate`) — never double-counts a `loop_detect` event.
- **INV-NO-AUTOACTION**: see R10.

## Scope
IN: `runtime/loop/harness-health.mjs`, `runtime/loop/harness-health-snapshot.mjs`, the two new additive
append call-sites inside `runtime/loop/index.mjs::runOneWake`, `skills/self/self-improve/lib/harness_health.py`,
`skills/self/self-improve/harness_health_report.py`.
OUT (follow-up, not this slice): launchd/cron scheduling of the snapshot script; a new `self-fix.sh` call
site triggered by `escalate:true`; integrating `harness_health` into `weekly_report.py`'s per-EDD-loop
digest (disjoint ledger domain); any change to `evaluator.py`'s `combined_score`/reward-cap/scope_guard
logic; Franklin (`~/.blockrun`) vs `anicca-a3cdd4` (`~/.anicca`) cross-instance comparison/dashboarding —
both ledgers share the identical schema (same `runtime/loop/index.mjs` codebase) so R1-R8 apply unchanged
to either instance's ledger path without further work, but no dashboard is built here.

## E2E necessity judgment (dev-workflow.md required section)
This is a backend-only observability/instrumentation change with **no UI, no user-facing app surface**
(no iOS/web screen is touched). Maestro/browser E2E is **not applicable** and is skipped for this reason.
Verification is: unit tests over pure functions (R1-R5, R8) + integration tests over real file I/O in a
temp `$ANICCA_HOME` (R6, R7) + a manual run of `harness-health-snapshot.mjs` against a REAL (or a
realistic fixture copy of a) live wake ledger as self-verification evidence, with its output numbers
cross-checked against a manual `jq`/`grep` count over the same file (Phase 3 adversary evidence).

## Done (this slice)
R1-R10 green (unit + integration, both languages) · fresh-context adversary PASS on spec AND impl ·
self-run of `harness-health-snapshot.mjs` against a real/realistic ledger with output numbers manually
cross-checked against `jq`/`grep` counts over the same file.
