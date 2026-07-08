# Behavioral Spec — franklin-funding-loop

## Context (grounded, verified 2026-07-08)

Spec of record for the ROLE this feature plays: `~/anicca-project/docs/loop-engineering/11-parent-funding-loop.md`
(§1 loop shape, §3 money-safety rails, §4 Done), `12-the-ladder-and-proactive.md` (proactive =
loop + goal, not a fixed cron script), `05-coordination-with-agent-economy.md` §6 (funding model:
**claude-p is the ONLY funder**, no treasury, no automaton participation, Franklin is the sole
recipient today).

**What already exists and MUST be reused, not reimplemented** (verified live 2026-07-08):
- `~/anicca/skills/earn/funding/` — the withdraw→bridge→send MECHANISM (PM deposit wallet →
  0x810f Polygon → relay.link bridge → BF9v Solana → Franklin 8Fpqd Solana), with its own
  money-safety rails already implemented and adversary-PASS'd
  (`skills/earn/funding/MONEY-SAFETY-VERDICT.md`): recipient identity verification
  (`lib/identity.py`), per-transfer/daily/cumulative caps (`lib/caps.py::check_caps`, config
  `per_transfer_usd_cap: 12.0`, `daily_usd_cap: 15.0`, `cumulative_usd_cap: 50.0`), reserve
  protection (`lib/caps.py::reserve_protected_amount`, `config.json: reserve_usd: 5.0`),
  on-chain-confirm-before-record (`lib/erc20.py`/`lib/solana_rpc.py`), a kill-switch
  (`lib/kill_switch.py`, `touch KILL` in `skills/earn/funding/`), and an append-only ledger
  (`lib/ledger.py` → `~/anicca/skills/earn/state/funding-ledger.jsonl`). `run.py` chains all
  three mechanism steps and stops at the first non-`ok` step. **This feature calls `run.py` with
  a decided amount; it does NOT reimplement withdraw/bridge/send, caps, identity checks, or the
  ledger writer.** Commit history confirms the one open money-safety finding from the adversary
  verdict (Finding A — post-broadcast confirm calls not wrapped in try/except, "not yet safe to
  leave unattended or on a schedule") was already closed before this feature starts
  (`git log --oneline` in `skills/earn/funding/`: `a3ecb0a`, `095a23d fix(funding): close
  money-safety adversary findings A/C, raise caps for D2 seed` — `withdraw.py`, `bridge.py`, and
  `send_to_franklin.py` all now wrap their post-broadcast confirm calls in `try:`). A real $9.95
  seed already reached Franklin end-to-end on 2026-07-08 (`funding-ledger.jsonl`, `sig:
  3K8Ff3Jik...`, `status: sent`).
- `~/anicca/skills/self/claude-p-mainloop.sh` + `ai.anicca.claude-p-mainloop.plist` — the
  ALREADY-ADOPTED pattern for "a launchd job wakes claude-p (a real Claude agent session, NOT a
  bespoke script that itself calls some LLM API) on a schedule to make judgment calls with no
  human in the loop": kill-switch file checked FIRST, pidfile single-instance guard (macOS has no
  `flock(1)`), a prompt file read via `"$(cat "$PROMPT_FILE")"` (never inlined in a
  double-quoted string — avoids the backtick/command-substitution footgun), `timeout 3600 claude
  --model claude-sonnet-5 --dangerously-skip-permissions -p "..."`. This feature's DECIDE step
  (REQ-003) is genuine agent (LLM) judgment — per `~/.claude/rules/building-effective-ai-agents.md`
  ("no hardcoded judgment, the model decides") — and the already-adopted, already-proven mechanism
  for that in this exact repo is this pattern, not a new bespoke API-calling script. Copying it
  whole (not combining it with the *different*, Franklin-instance-owned
  `skills/_shared/proactive-loop.sh` slot-dispatch mechanism, which is a different actor/wallet
  context — Franklin's own instance loop, not claude-p's) is the correct "copy one winner whole"
  choice (`feedback_never_combine_copy_one_winner_whole`).
- `~/anicca/skills/_shared/lib/solana-verify.mjs::usdcBalance(wallet, opts)` — Franklin's live
  Solana USDC balance read (already unit-tested, already reused by the sibling
  `franklin-loop-revival` feature for the exact same wallet `8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9`).
- `~/anicca/skills/_shared/lib/ledger.mjs::isProfitable(line)` — the single source of truth for
  "a profitable, externally-verified wake" in `~/anicca/skills/earn/state/earn-ledger.jsonl`
  (requires `net_usdc > 0`, not a swap, `external === true`, and a chain-correct confirmed
  receipt). Live-checked 2026-07-08: this ledger currently has zero rows for Franklin's wallet(s)
  (all existing rows are claude-p's own PM wallet `0x904b50d2e214da947d83d6a2d32c4e3ffc17eb74`) —
  Franklin has not yet produced an externally-verified profitable trade. This is a real, current
  fact this feature's OBSERVE step must be able to represent honestly (zero rows is a valid
  observation, not an error).
- `~/anicca/runtime/loop/catalog-gate.mjs::DEFAULT_BOOTSTRAP_RESERVE_USDC` (= 20, i.e.
  `Number(process.env.BOOTSTRAP_RESERVE_USDC) || 20`) — the existing, already-live numeric
  threshold this codebase already uses to decide whether Franklin's balance is large enough to be
  offered `earn/sol-trade` as `alwaysAvailable`. This feature's viability-ceiling hard gate
  (REQ-004) reuses this SAME number as its default (not a newly invented number), defined as this
  feature's OWN config key (since `catalog-gate.mjs` is Node/ESM and this feature's gate
  predicates are Python, colocated with `funding/`'s own Python money-safety modules — no
  cross-language import is attempted; the numeric value is copied once at spec time and is
  independently configurable thereafter).

**What this feature explicitly does NOT do (non-goals)**:
- Does not modify `skills/earn/funding/**` (mechanism + its own money-safety rails are frozen,
  reused as a black-box CLI: `python3 run.py [--amount-usd X]`).
- Does not modify `runtime/loop/catalog-gate.mjs`, `anicca-agent-economy`, `anicca-agent-lending`,
  `anicca-agent-spawn`, or any other instance's wallet/cron/keys.
- Does not introduce a second funder, a treasury, or automaton participation (per
  `05-coordination-with-agent-economy.md` §6 — claude-p is the only funder).
- Does not decide funding by hardcoded regex/threshold classification of "starving" —
  that classification is REQUIRED to be genuine agent (LLM) judgment (REQ-003); only the
  post-judgment BOUNDS (REQ-004/005/006) are deterministic hard gates the agent's judgment cannot
  override.

## Purity Boundary Analysis

- **Pure core** (deterministic, no I/O, unit/property testable): the hard-gate PREDICATE
  functions this feature introduces — a viability-ceiling check (given a live balance and a
  configured floor, returns allowed/blocked + reason), a cooldown check (given the timestamp of
  the most recent confirmed Franklin-received row and a configured cooldown window, returns
  allowed/blocked + reason), and the final fund-authorization boolean (`fund_recommended AND
  viability_ok AND cooldown_ok AND NOT killed` — pure AND over already-computed booleans). None of
  these read the network, the filesystem, or invoke a subprocess themselves — they take plain data
  in and return plain data out, mirroring `skills/earn/funding/lib/caps.py`'s own existing style
  and test convention (`tests/test_caps.py`).
- **Effectful shell** (I/O, network, process spawn, LLM invocation — this feature's real surface):
  the OBSERVE step (reads Franklin's live Solana balance via `usdcBalance`, reads
  `earn-ledger.jsonl` and `funding-ledger.jsonl` from disk, reads claude-p's own surplus via
  `funding/config.json` + a live PM-wallet-adjacent balance read already performed by `run.py`
  itself); the DECIDE step (a real `claude --model claude-sonnet-5` subprocess invocation — the
  genuine agent-judgment call, REQ-003); the FUND step (`python3
  skills/earn/funding/run.py --amount-usd X`, a real subprocess that moves real money); the LOG
  step (append-only write to `funding-ledger.jsonl`); the kill-switch/pidfile checks (filesystem);
  and the launchd wiring itself (`ai.anicca.franklin-funding-loop.plist`).

## Requirements

### REQ-001: Loop-level wake gating (kill-switch first, single-instance guard)
**EARS**: WHEN the `ai.anicca.franklin-funding-loop` launchd job fires THE SYSTEM SHALL, before
performing ANY OBSERVE read, DECIDE invocation, or FUND action, (a) check a dedicated loop-level
kill-switch file (`~/.anicca/franklin-funding-loop.pause`) and exit 0 immediately if it exists,
logging that the wake was skipped due to the kill-switch, and (b) check a dedicated pidfile
(`~/.openclaw/state/franklin-funding-loop.pid`) and exit 0 immediately (without touching the
pidfile) if a live process already holds it — mirroring
`skills/self/claude-p-mainloop.sh`'s exact ordering and pidfile-liveness-check pattern
(`kill -0 "$OLD_PID"`), reused because macOS ships no `flock(1)` binary.
**Edge Cases**:
- Kill-switch file present: the wake MUST exit before any Solana RPC call, any ledger read, and
  any `claude`/LLM subprocess is spawned — i.e., killed wakes cost nothing (no LLM tokens, no
  network calls), not merely "no fund action".
- Stale pidfile (recorded PID no longer alive): reclaim it (same as
  `claude-p-mainloop.sh`'s "stale pidfile ... reclaiming" branch) rather than blocking forever.
- Both the kill-switch and a live pidfile present simultaneously: kill-switch wins (checked
  first), for the cheapest possible skip.
**Acceptance Criteria**:
- With `~/.anicca/franklin-funding-loop.pause` present, invoking the loop's entry script produces
  no `funding-ledger.jsonl` growth, no new Solana RPC traffic, and no `claude` subprocess spawn,
  and exits 0.
- With the pidfile present and its PID alive (a real long-running placeholder process in tests),
  a second concurrent invocation exits 0 without spawning a second `claude`/`run.py` invocation.

### REQ-002: OBSERVE — read the canonical data snapshot before DECIDE runs
**EARS**: WHEN a wake is not gated out by REQ-001 THE SYSTEM SHALL assemble one OBSERVE snapshot,
read in this order, before the DECIDE step (REQ-003) is invoked:
1. Franklin's live Solana USDC balance, via `skills/_shared/lib/solana-verify.mjs::usdcBalance('8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9')` (the exact reuse pattern already
   established by the sibling `franklin-loop-revival` feature for this same wallet — no second,
   independently-typed Solana balance implementation is written).
2. Franklin's growth signal from `~/anicca/skills/earn/state/earn-ledger.jsonl`, filtered to rows
   whose `wallet` matches a known Franklin wallet, classified with the existing
   `skills/_shared/lib/ledger.mjs::isProfitable(line)` (reused, not reimplemented) — plus
   Franklin's own trading-loop narrative from `~/anicca/skills/earn/state/sol-trade.trace.jsonl`
   (its most recent entries, e.g. `action:"live-pass"` notes), since `sol-trade` does not yet
   write to `earn-ledger.jsonl`.
3. Prior funding history from `~/anicca/skills/earn/state/funding-ledger.jsonl` — specifically the
   timestamp of the most recent row where `step == "send_to_franklin"` and `status == "sent"`
   (used by the cooldown gate, REQ-005) and the full row set (used by `run.py`'s own, unchanged,
   cap/reserve math — REQ-006).
4. claude-p's own available surplus, via `skills/earn/funding/config.json`'s `reserve_usd` /
   `per_transfer_usd_cap` / `daily_usd_cap` / `cumulative_usd_cap` values (read, never edited by
   this feature) — the loop does not independently compute a live PM-deposit-wallet balance itself
   (that live read, and its reserve-aware clipping, is `withdraw.py`'s own job, re-derived live at
   FUND time regardless of what this snapshot shows — see REQ-002's edge cases and REQ-006).
**Edge Cases**:
- Any single read in the snapshot fails (Solana RPC error/timeout, a missing/corrupt ledger file,
  a missing `funding/config.json`): THE SYSTEM SHALL fail closed for THAT wake — skip DECIDE and
  FUND entirely for this wake, log the failure with which read failed, and MUST NOT substitute a
  guessed/default value (never assume "$0 balance" nor "already viable" to route around a failed
  read either would be a fabricated signal).
- `earn-ledger.jsonl` contains zero rows for any Franklin wallet (the current, real, live state as
  of 2026-07-08): THE SYSTEM SHALL represent this as a valid, honest observation ("no
  externally-verified profitable trade yet"), not an error.
- `funding-ledger.jsonl` does not yet exist or contains no `send_to_franklin`/`sent` rows (i.e., no
  prior fund has ever completed): the cooldown gate (REQ-005) treats this as "no cooldown active"
  (nothing to be on cooldown from), not as a failure.
- The OBSERVE snapshot is a point-in-time READ for DECIDE's benefit only. It is NEVER treated as
  the authoritative amount actually available at FUND time — `run.py`'s own live balance
  re-derivation and re-clipping (already implemented, unchanged, REQ-006) is the sole final
  authority on how much can actually move, so a race between this loop and any other consumer of
  the same PM-deposit-wallet surplus (e.g. pm-earner's own ongoing trading) can never cause an
  over-withdrawal — the mechanism itself, not this feature, is what prevents that.
**Acceptance Criteria**:
- A recorded OBSERVE snapshot (surfaced to the DECIDE step, e.g. in the prompt or a structured
  intermediate artifact) contains all four data points above, or an explicit failure marker for
  whichever one could not be read, for every non-gated wake.
- No new Solana RPC call pattern, ledger schema, or config file is introduced by OBSERVE — every
  read in this list is a call into an already-existing function/file.

### REQ-003: DECIDE — genuine agent (LLM) judgment, not a hardcoded classifier
**EARS**: WHEN the OBSERVE snapshot (REQ-002) is available THE SYSTEM SHALL invoke a real LLM
agent session (the `claude --model claude-sonnet-5 --dangerously-skip-permissions` invocation
pattern reused from `claude-p-mainloop.sh`, with a dedicated prompt file for this feature) to
judge, from the snapshot's data, whether Franklin is presently "starving / undergrown" (needs a
seed to avoid being trade-incapable or stalled) or "self-sufficient / growing" (earn signals
positive or trending up, no seed needed — step back), and to produce a recommendation
(`fund_recommended: bool`, `amount_usd: number` if true, and a written reasoning trace). THE
SYSTEM SHALL NOT implement this classification as a fixed numeric threshold, regex, or keyword
rule inside a script — the judgment itself belongs to the agent, per
`~/.claude/rules/building-effective-ai-agents.md` ("no hardcoded judgment, the model decides";
`feedback_build_agents_not_hardcode_regex`). This recommendation is advisory input to REQ-004/005/
006/007's deterministic hard gates, which the agent's recommendation cannot override.
**Edge Cases**:
- The LLM subprocess times out, errors, or produces an unparseable/ambiguous recommendation: THE
  SYSTEM SHALL treat this identically to `fund_recommended: false` for that wake (default =
  step back, per the parent spec's "default は step-back(fund しない)") — never falls back to a
  hardcoded auto-fund default on an ambiguous agent response.
- The agent recommends `fund_recommended: true` with an `amount_usd` that is negative, zero,
  non-numeric, or exceeds the configured `per_transfer_usd_cap`: THE SYSTEM SHALL clip the
  requested amount to, at most, the configured per-transfer cap before it is ever passed toward
  FUND (REQ-007) — defense-in-depth ahead of `run.py`'s own identical cap check, never a second
  path that could exceed it.
- The agent recommends `fund_recommended: true` while Franklin's own reported balance already
  exceeds the viability ceiling: this recommendation is still produced (the agent's own reasoning
  trace is preserved in the log for audit), but REQ-004's hard gate overrides it and no funding
  occurs — the log line distinguishes "agent recommended fund, but viability gate blocked it" from
  "agent recommended step-back".
**Acceptance Criteria**:
- Every non-gated wake produces exactly one recorded DECIDE output (`fund_recommended`,
  `amount_usd` or null, `reasoning`) attributable to a real LLM invocation for that wake (not a
  cached/stale prior decision, not a constant).
- No source file in this feature contains a numeric/regex "is Franklin broke" classifier — a
  review of the implementation (Phase 3 adversary check) confirms the starving/undergrown vs
  self-sufficient/growing judgment is made inside the LLM prompt path, not in a conditional in the
  wrapper script.

### REQ-004: HARD GATE — viability ceiling (agent judgment cannot override)
**EARS**: WHEN Franklin's live Solana USDC balance (REQ-002.1), read at gate-evaluation time, is
greater than or equal to a configured `viability_floor_usd` (default `20`, matching the existing,
already-live `runtime/loop/catalog-gate.mjs::DEFAULT_BOOTSTRAP_RESERVE_USDC` value at
spec-writing time) THE SYSTEM SHALL NOT proceed to FUND (REQ-007) for that wake, REGARDLESS of
DECIDE's (REQ-003) `fund_recommended` value, and SHALL log the skip with reason "already viable"
(step back — over-supply is forbidden, mirroring the parent design's "自立してたら step back"
principle).
**Edge Cases**:
- Balance exactly equal to `viability_floor_usd`: treated as viable (blocks funding) — the
  boundary is inclusive on the "already viable, do not fund" side, the safety-conservative
  direction (never funds when in doubt at the boundary).
- Balance read fails (REQ-002 edge case): the wake already skipped DECIDE/FUND entirely; this gate
  is never reached with a missing/fabricated balance.
- `viability_floor_usd` misconfigured to a negative number or non-numeric value: THE SYSTEM SHALL
  fail closed — treat the gate as "always already viable" (never fund) rather than silently
  falling back to a hardcoded default that could re-enable funding on bad config.
**Acceptance Criteria**:
- A pure predicate function (e.g. `viability_gate(balance_usd, floor_usd) -> {allowed, reason}`)
  exists, is unit-tested with a boundary table (`balance < floor`, `balance == floor`,
  `balance > floor`, non-finite/negative inputs), and is the ONLY code path REQ-007 consults for
  this gate — no duplicate/inline re-check elsewhere.
- Given a live-observed Franklin balance below `viability_floor_usd` (the real state as of
  2026-07-08, ≈$11.63–$21.58 depending on the latest seed's confirmation), the gate returns
  `allowed: true` (does not itself block funding) unless a different gate (REQ-005/006) blocks it.

### REQ-005: HARD GATE — cooldown (agent judgment cannot override)
**EARS**: WHEN the most recent `funding-ledger.jsonl` row with `step == "send_to_franklin"` AND
`status == "sent"` has a timestamp less than a configured `cooldown_hours` (default `24`,
matching the funding skill's own 24h daily-cap accounting window) before the current
gate-evaluation time THE SYSTEM SHALL NOT proceed to FUND (REQ-007) for that wake, REGARDLESS of
DECIDE's `fund_recommended` value, and SHALL log the skip with reason "cooldown active" plus the
remaining cooldown duration.
**Edge Cases**:
- No prior `send_to_franklin`/`sent` row exists at all (first-ever fund, or `funding-ledger.jsonl`
  absent): cooldown is NOT active (nothing to be on cooldown from) — this gate returns `allowed:
  true` by itself in that case.
- Multiple `send_to_franklin`/`sent` rows exist: only the MOST RECENT one's timestamp is used.
- A `pending` (broadcast-but-not-yet-confirmed) `send_to_franklin` row with no later terminal
  `sent`/`failed` row for the same signature: treated conservatively as if a send may complete —
  the cooldown clock still starts from the `pending` row's timestamp (never treated as "no
  cooldown" just because confirmation hasn't resolved yet).
**Acceptance Criteria**:
- A pure predicate function (e.g. `cooldown_gate(last_sent_ts, now_ts, cooldown_hours) ->
  {allowed, reason}`) exists, is unit-tested (no-prior-row case, just-under-window, exactly-at-
  window, well-past-window), and is the ONLY code path REQ-007 consults for this gate.
- Two funding decisions less than `cooldown_hours` apart are never both allowed to reach FUND
  (REQ-007) for the same Franklin wallet.

### REQ-006: HARD GATE — caps and reserve protection delegated to `funding/run.py` (never duplicated, never bypassed)
**EARS**: WHEN FUND (REQ-007) is about to be invoked THE SYSTEM SHALL pass, at most, a proposed
`--amount-usd` value to `skills/earn/funding/run.py` and SHALL treat `run.py`'s own, unchanged,
already-adversary-reviewed cap/reserve/identity logic (`lib/caps.py::check_caps`,
`lib/caps.py::reserve_protected_amount`, `lib/identity.py`, `config.json`) as the FINAL authority
— this feature SHALL NOT reimplement per-transfer/daily/cumulative cap math, reserve math, or
identity verification, and SHALL NOT introduce, request, or use any flag/parameter that bypasses
those checks (none exists in `run.py`/`withdraw.py`/`bridge.py`/`send_to_franklin.py` today, per
`SKILL.md`: "No flag bypasses this check").
**Edge Cases**:
- `run.py` returns `ok: false` at any step (a cap rejection, an identity mismatch, a bridge-fee
  rejection, an RPC failure): THE SYSTEM SHALL treat this as a definitive skip for this wake — it
  MUST NOT retry within the same wake with a smaller amount to "get under the cap" (no
  cap-bypass-by-retry), and MUST NOT treat a partial pipeline success (e.g. withdraw succeeded but
  bridge failed) as a completed fund — `run.py` itself already halts the chain on the first non-ok
  step.
- The kill-switch file inside `skills/earn/funding/` (`skills/earn/funding/KILL`, `lib/kill_switch.py`) is present: `run.py` already refuses to move money; this feature adds NO
  second code path around it. This is a second, independent kill-switch from this feature's own
  loop-level one (REQ-001) — either one alone is sufficient to stop real money movement
  (defense-in-depth).
- claude-p's own configured reserve (`reserve_usd`) would be dipped by the requested amount:
  `withdraw.py`'s own live-balance-based reserve clipping (unchanged) already prevents this; this
  feature does not attempt to compute or override that clipping.
**Acceptance Criteria**:
- A code review (Phase 3 adversary) of this feature's implementation shows zero re-implementation
  of cap arithmetic, reserve arithmetic, or identity-derivation logic — every such check is a call
  into the existing `skills/earn/funding/` modules.
- A recorded `run.py` invocation with an amount that exceeds any configured cap results in an
  `ok: false` result being faithfully recorded as a skip (REQ-008), with no follow-up retry at a
  smaller amount within the same wake.

### REQ-007: FUND — execute only when every gate passes, via the existing mechanism only
**EARS**: WHEN, for a given wake, DECIDE (REQ-003) recommends `fund_recommended: true` AND the
viability gate (REQ-004) returns `allowed: true` AND the cooldown gate (REQ-005) returns `allowed:
true` AND the loop-level kill-switch (REQ-001) is absent THE SYSTEM SHALL invoke `python3
skills/earn/funding/run.py --amount-usd <clipped-amount>` (a REAL, non-`--dry` invocation) exactly
once for that wake, using the amount from REQ-003's recommendation after the REQ-003 clipping
edge case is applied. If ANY of these conditions is false THE SYSTEM SHALL NOT invoke `run.py` in
non-dry mode at all for that wake (default = step back).
**Edge Cases**:
- All gates pass but the resulting real transfer only partially completes (e.g. withdraw+bridge
  succeed, `send_to_franklin` fails): `run.py`'s own existing behavior already records each step's
  real status in `funding-ledger.jsonl`; this feature's LOG step (REQ-008) records the wake's
  DECIDE+gate outcome alongside, but does not fabricate a "fund succeeded" record when the
  mechanism itself reported a failure at any step.
- Multiple wakes in sequence each independently re-evaluate all gates — a wake that funded
  successfully does not disable future wakes' gate evaluation; the cooldown gate (REQ-005) is the
  mechanism that naturally prevents back-to-back funding, not a one-shot "already funded once,
  never again" flag.
**Acceptance Criteria**:
- Given a synthetic/test harness where DECIDE recommends fund AND both hard gates return
  `allowed: true` AND the kill-switch is absent, exactly one `run.py` invocation (non-dry) occurs.
- Given ANY single one of those four conditions is false, zero `run.py` invocations (dry or
  non-dry) occur for FUND — the gate is a strict logical AND, verified by an exhaustive
  truth-table test.

### REQ-008: LOG — every wake records exactly one decision row, structurally isolated from mechanism rows
**EARS**: WHEN a wake completes (whether gated out at REQ-001, skipped at REQ-002's failure path,
stepped back by REQ-003/004/005, or having invoked FUND at REQ-007) THE SYSTEM SHALL append
exactly one structured decision record to `~/anicca/skills/earn/state/funding-ledger.jsonl` (the
SAME ledger the mechanism already writes to, reused as the single audit trail) with a `step` value
reserved exclusively for this feature (e.g. `"loop-decide"`) that is NEVER equal to `"withdraw"`,
`"bridge"`, or `"send_to_franklin"` — the exact three values `lib/caps.py::_outflow_rows` filters
on for cap accounting — so this feature's decision rows can NEVER be counted as a real capital
outflow by the existing, unchanged cap-math code, structurally (not merely by convention).
**Edge Cases**:
- A wake gated out entirely by the kill-switch (REQ-001) still logs a minimal record (timestamp +
  "killed") so an operator can see the loop is alive but paused — this is the ONE exception where
  the record may omit OBSERVE/DECIDE fields (since those steps never ran).
- Any other skip (OBSERVE failure, DECIDE step-back, viability/cooldown gate block) logs the full
  reasoning: which gate blocked (if any), DECIDE's raw recommendation, and the OBSERVE snapshot
  summary — never just "skipped" with no reason.
- A LOG write failure (disk full, permissions) MUST NOT crash silently without any trace — at
  minimum, an error is written to the loop's own stderr log file, mirroring
  `claude-p-mainloop.sh`'s `LOG_ERR` convention.
**Acceptance Criteria**:
- After N wakes with the kill-switch absent, `funding-ledger.jsonl` contains exactly N new rows
  with `step: "loop-decide"` (one per wake, never zero, never more than one per wake).
- Feeding a synthetic ledger containing a `step: "loop-decide"` row with an arbitrarily large
  `amount_usd` through `skills/earn/funding/lib/caps.py::check_caps`'s underlying
  `_outflow_rows` filter shows it is never selected (regression-style test against the REAL,
  unmodified `caps.py` code, not a reimplementation of its filter logic).

### REQ-009: Scheduling — dedicated launchd job, safe defaults, not folded into an existing loop
**EARS**: WHEN this feature is deployed THE SYSTEM SHALL run as its OWN, dedicated launchd job
(`ai.anicca.franklin-funding-loop`, distinct from `ai.anicca.claude-p-mainloop` and from Franklin's
own `ai.anicca.franklin-loop`) with `RunAtLoad=false` (never auto-fires on plist load/machine
boot) and a recurring `StartInterval` (default `21600` seconds = 6h, per the parent spec's "毎
interval（例 6h / daily）"), so that money-moving judgment is isolated in its own auditable,
narrowly-scoped process rather than folded into claude-p's general-purpose colony-maintenance
loop (`claude-p-mainloop`'s own prompt already explicitly forbids it from moving live money) or
into Franklin's own instance loop (a different actor/wallet entirely).
**Edge Cases**:
- Machine reboot: the job does NOT fire immediately (`RunAtLoad=false`) — it waits for its next
  scheduled interval, consistent with `claude-p-mainloop.plist`'s own documented rationale ("never
  auto-fire on load — verified manually then left to its own schedule").
- The job firing while `ai.anicca.claude-p-mainloop` is ALSO mid-run (both are independent,
  separately-guarded processes; REQ-001's pidfile is scoped to THIS feature only and does not
  collide with `claude-p-mainloop.pid`): both may run concurrently without interfering with each
  other, since they touch disjoint pidfiles/kill-switches and (per REQ-006) any real money
  movement is still bounded by `run.py`'s own live cap/reserve re-derivation regardless of which
  process invoked it.
**Acceptance Criteria**:
- `~/Library/LaunchAgents/ai.anicca.franklin-funding-loop.plist` exists, is loaded
  (`launchctl print gui/$(id -u)/ai.anicca.franklin-funding-loop` shows the job), has
  `RunAtLoad=false`, and a `StartInterval` present.
- The job's `ProgramArguments` invoke a script distinct from `claude-p-mainloop.sh` and from
  Franklin's own daemon entry point, with its own `StandardOutPath`/`StandardErrorPath` log files.

## Non-Functional Requirements

- **Autonomy indicator (D5, observational, long-horizon)**: as Franklin's balance/growth trend
  rises over successive wakes, the rate at which REQ-007's FUND path actually executes SHALL trend
  toward zero — this is not independently provable in a unit test (it depends on Franklin's real,
  external economic performance over days/weeks) but MUST be observable from
  `funding-ledger.jsonl`'s `loop-decide` rows over time and is the feature's designed
  self-obsolescence signal (mirrors the parent spec's "自立が進むほど送金発動が0に近づく＝健康の指標").
- **No new spend authority, no new keys**: this feature introduces no new private keys, no new
  wallets, and does not raise any cap/reserve value in `skills/earn/funding/config.json` — any cap
  tuning remains that skill's own, separately-reviewed change.
- **Security**: no secret material (private keys, raw session file contents) may appear in the
  DECIDE prompt, the LLM's response, or any `funding-ledger.jsonl` row this feature writes — only
  public addresses, balances, and reasoning text.
- **Observability**: `funding-ledger.jsonl`'s `loop-decide` rows plus the existing mechanism rows
  are the sole source of truth for verifying Done; no new logging system/format is introduced.
- **Human-zero**: no step in REQ-001 through REQ-009 requires a human approval, prompt, or manual
  trigger during normal operation — the kill-switch file is the only human-operable control, and
  it is a STOP mechanism, not an approval gate.
