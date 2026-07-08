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
  money-safety rails already implemented for the underlying mechanism: recipient identity
  verification (`lib/identity.py`), per-transfer/daily/cumulative caps (`lib/caps.py::check_caps`,
  config `per_transfer_usd_cap: 12.0`, `daily_usd_cap: 15.0`, `cumulative_usd_cap: 50.0`), reserve
  protection (`lib/caps.py::reserve_protected_amount`, `config.json: reserve_usd: 5.0`),
  on-chain-confirm-before-record (`lib/erc20.py`/`lib/solana_rpc.py`), a kill-switch
  (`lib/kill_switch.py`, `touch KILL` in `skills/earn/funding/`), and an append-only ledger
  (`lib/ledger.py` → `~/anicca/skills/earn/state/funding-ledger.jsonl`). `run.py` chains all
  three mechanism steps and stops at the first non-`ok` step. **This feature calls `run.py` with
  a decided amount; it does NOT reimplement withdraw/bridge/send, caps, identity checks, or the
  ledger writer.**
  **Correction (2026-07-08, spec-review iteration 2, closes FIND-004):** the prior iteration of
  this spec cited `skills/earn/funding/MONEY-SAFETY-VERDICT.md` itself as adversary-reviewed proof
  that the one open finding (Finding A — post-broadcast confirm calls not wrapped in try/except)
  was closed. That artifact is STALE: it was never re-issued after the fix commit, and its own
  "OVERALL VERDICT" section still reads, verbatim, "Safe to run the $1-2 D1 test now ... NOT YET
  safe to leave unattended or on a schedule" (`MONEY-SAFETY-VERDICT.md:185-213`) — i.e. on its
  face it still describes Finding A/C as open, unresolved blockers for exactly the scheduled/
  unattended use this feature builds. This spec does NOT rely on that stale verdict-file prose as
  its safety evidence. The actual, independently verifiable evidence is the fix commit itself —
  `095a23d fix(funding): close money-safety adversary findings A/C, raise caps for D2 seed`
  (`git log --oneline` in `skills/earn/funding/`: `a3ecb0a`, `095a23d`) — cross-checked on
  2026-07-08 by direct inspection of the CURRENT source, not the commit message alone:
  `withdraw.py:211-239`, `bridge.py:207-239`, and `send_to_franklin.py:181-209` do genuinely wrap
  their post-broadcast confirmation calls in `try:`/`except:` with a pending-row-written-before-
  wait pattern (Finding A), and `lib/caps.py::_outflow_rows` genuinely filters to `step ==
  "withdraw"` only (Finding C). This feature's confidence that scheduled/unattended operation is
  safe rests on (a) this direct code confirmation, not the stale document's wording, and (b) this
  feature's OWN independent hard gates (REQ-004 viability/REQ-005 cooldown/REQ-006
  caps-delegation/REQ-007 AND-composition) layered on top of the mechanism regardless of what that
  document says elsewhere. A real $9.95 seed already reached Franklin end-to-end on 2026-07-08
  (`funding-ledger.jsonl`, `sig: 3K8Ff3Jik...`, `status: sent`), consistent with the fix being
  genuinely in place.
- `~/anicca/skills/self/claude-p-mainloop.sh` + `ai.anicca.claude-p-mainloop.plist` — the
  ALREADY-ADOPTED pattern for THIS FEATURE'S LOOP-LEVEL ENTRY SCRIPT ONLY (REQ-001/REQ-009's
  kill-switch + pidfile wrapper — NOT DECIDE's own invocation; see the correction immediately
  below): kill-switch file checked FIRST, pidfile single-instance guard (macOS has no
  `flock(1)`), a prompt file read via `"$(cat "$PROMPT_FILE")"` (never inlined in a
  double-quoted string — avoids the backtick/command-substitution footgun). Copying this wrapper
  skeleton whole (not combining it with the *different*, Franklin-instance-owned
  `skills/_shared/proactive-loop.sh` slot-dispatch mechanism, which is a different actor/wallet
  context — Franklin's own instance loop, not claude-p's) is the correct "copy one winner whole"
  choice (`feedback_never_combine_copy_one_winner_whole`) for the WRAPPER. It is NOT the correct
  choice for DECIDE's own `claude` invocation — see below.
- **Correction (2026-07-08, spec-review iteration 2, closes FIND-001):** the prior iteration of
  this spec ALSO copied `claude-p-mainloop.sh`'s literal `timeout 3600 claude --model
  claude-sonnet-5 --dangerously-skip-permissions -p "..."` invocation line for DECIDE (REQ-003)
  itself. That flag disables ALL tool-confirmation gating for the whole subprocess turn, giving
  DECIDE live, unrestricted Bash/Write/Edit/git tool access for as long as it runs — which is the
  right pattern for `claude-p-mainloop`'s OWN job (a general-purpose, human-funded,
  colony-maintenance builder session that legitimately needs live tool access) but the WRONG
  pattern for DECIDE, whose only documented job is "produce one structured recommendation, no
  side effects." Granting DECIDE that same live tool access means it could, within its own turn,
  directly execute `python3 skills/earn/funding/run.py`, touch the kill-switch file, or
  hand-write a ledger row — completely bypassing REQ-004/005/006/007's gates, which are only ever
  consulted by the WRAPPER SCRIPT after DECIDE returns and cannot constrain a live agentic
  subprocess's own tool-calling turn. This repo already contains a purpose-built, safer
  alternative for exactly DECIDE's "produce one judgment, no side effects" use case —
  `runtime/loop/brain.mjs::thinkClaudeP` (lines 83-134) — which invokes `claude -p ...
  --output-format json --model <model>` WITHOUT `--dangerously-skip-permissions`, with a
  scrubbed/minimal env, from a neutral `os.tmpdir()` cwd, specifically so the invocation cannot
  take side-effecting actions. REQ-003 now specifies this pattern for DECIDE;
  `claude-p-mainloop.sh`'s pattern remains the correct, unmodified precedent for this feature's
  own loop-level wrapper (REQ-001/REQ-009) only, where no LLM tool-access concern applies (the
  wrapper itself is deterministic bash, not an agent session).
- **Pending relocation (acknowledged, closes FIND-005, non-blocking for this spec):**
  `05-coordination-with-agent-economy.md` §8 Q3 (Dais 2026-07-08) judges that
  `~/anicca/skills/earn/funding/` — because it is signed with claude-p's own wallet/credential,
  not Franklin's — belongs in `~/profitable-claude/skills/human-funded/` per that repo's own
  ownership convention ("誰の credential/wallet で署名するか、であって、下流の効果ではない"), and
  that "移動作業自体は君の領域" (the migration itself is this feature's/skill owner's job, not
  agent-economy's). This feature does NOT perform that relocation (out of scope) but does not
  silently hardcode `~/anicca` as an unexamined assumption either — see Non-Functional
  Requirements ("Path indirection") for how this feature resolves every path under
  `skills/earn/funding/`/`skills/earn/state/` through exactly ONE configurable base-directory
  value, so the eventual relocation requires changing one value, not every call site in this
  feature's own new code.
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
- Does not grant DECIDE (REQ-003) any tool-execution capability (no Bash/Write/Edit/git access) —
  DECIDE's subprocess invocation is structurally restricted (no `--dangerously-skip-permissions`,
  scrubbed env, neutral cwd), never the general-purpose builder-session invocation pattern.
- Does not perform the pending relocation of `skills/earn/funding/` to
  `~/profitable-claude/skills/human-funded/` (`05-coordination-with-agent-economy.md` §8 Q3) —
  out of scope for this feature; only path indirection (Non-Functional Requirements) is in scope.

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
  itself); the DECIDE step (a real, but structurally tool-access-restricted, `claude -p ...
  --output-format json` subprocess invocation — genuine agent judgment, REQ-003 — invoked WITHOUT
  `--dangerously-skip-permissions`, with a scrubbed env, from a neutral cwd, so it cannot itself
  perform any of the other effectful actions listed here); the FUND step (`python3
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
   timestamp of the most recent row across `step in {"withdraw", "bridge", "send_to_franklin"}`
   with any non-`"dry"` status (used by the cooldown gate, REQ-005, per its corrected
   most-recent-funding-ATTEMPT row selection) and the full row set (used by `run.py`'s own,
   unchanged, cap/reserve math — REQ-006).
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
- `funding-ledger.jsonl` does not yet exist or contains no `withdraw`/`bridge`/`send_to_franklin`
  row of any non-`"dry"` status (i.e., no prior funding attempt of any kind, per REQ-005's
  corrected row selection): the cooldown gate (REQ-005) treats this as "no cooldown active"
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

### REQ-003: DECIDE — genuine agent (LLM) judgment, structurally isolated from ALL money-moving tool access
**EARS**: WHEN the OBSERVE snapshot (REQ-002) is available THE SYSTEM SHALL invoke a real LLM
agent session to judge, from the snapshot's data, whether Franklin is presently "starving /
undergrown" (needs a seed to avoid being trade-incapable or stalled) or "self-sufficient /
growing" (earn signals positive or trending up, no seed needed — step back), and to produce a
recommendation (`fund_recommended: bool`, `amount_usd: number` if true, and a written reasoning
trace) as its ONLY possible output.
**Correction (2026-07-08, spec-review iteration 2, closes FIND-001):** the prior iteration of this
spec mandated reusing `claude-p-mainloop.sh`'s exact invocation verbatim — `claude --model
claude-sonnet-5 --dangerously-skip-permissions -p "..."`, cd'd into the project working directory.
That flag disables ALL tool-confirmation gating for the whole subprocess turn, giving the DECIDE
session live, unrestricted Bash/Write/Edit/git tool access for as long as it runs — meaning DECIDE
could, within its own turn, directly execute `python3 skills/earn/funding/run.py`, touch the
kill-switch file, or hand-write a ledger row, completely bypassing REQ-004/005/006/007's gates
(which are only ever consulted by the WRAPPER SCRIPT after DECIDE returns — they cannot constrain
what a live agentic subprocess does with its own tool-calling turn). THE SYSTEM SHALL THEREFORE
invoke DECIDE using the existing, safer, purpose-built precedent already in this repo for exactly
this "produce one structured judgment, no side effects" use case —
`runtime/loop/brain.mjs::thinkClaudeP` (lines 83-134): `claude -p "<prompt>" --output-format json
--model <model>` — with three properties, ALL required, none optional:
1. **NO `--dangerously-skip-permissions` and no `--allowedTools`/permissive tool-grant flag of any
   kind** — the subprocess runs in Claude Code's default (non-agentic, no tool-execution) mode for
   a single `-p` prompt/response turn; it has no Bash/Write/Edit/git tool access to exercise, so
   there is no live tool-calling turn during which it could invoke `run.py`, write a ledger row,
   or touch the kill-switch file.
2. **A scrubbed, minimal env** — `HOME`/`PATH` plus only the auth token needed
   (`ANTHROPIC_API_KEY`/`CLAUDE_CODE_OAUTH_TOKEN`, filtered through a private-key-scrubbing
   allow-list, not a full inherited process env) — no wallet private key, no `funding/config.json`
   path, no ledger path is ever exposed to the child process's environment.
3. **A neutral working directory** (`os.tmpdir()` or equivalent, NEVER the project working
   directory or `skills/earn/funding/`) — so the project's own `.claude/` hooks/MCP tools are
   never loaded for this subprocess and it has no filesystem vantage point from which to locate
   `run.py`, the ledger, or the kill-switch file even if it attempted a write.
DECIDE's entire contract with the rest of this feature is: the OBSERVE snapshot serialized into
the prompt in, one parsed JSON blob out (`fund_recommended`/`amount_usd`/`reasoning`) on stdout.
It performs no filesystem write, no subprocess invocation, and no network call beyond the LLM API
call itself. THE SYSTEM SHALL NOT implement the starving/undergrown vs self-sufficient/growing
classification as a fixed numeric threshold, regex, or keyword rule inside a script — the judgment
itself belongs to the agent, per `~/.claude/rules/building-effective-ai-agents.md` ("no hardcoded
judgment, the model decides"; `feedback_build_agents_not_hardcode_regex`). This recommendation is
advisory input to REQ-004/005/006/007's deterministic hard gates, which the agent's recommendation
cannot override — and, per this correction, cannot BYPASS either, because it has no tool-execution
capability with which to do so.
**Edge Cases**:
- The LLM subprocess times out, errors, exits non-zero, or produces empty/unparseable/ambiguous
  output: THE SYSTEM SHALL treat this identically to `fund_recommended: false` for that wake
  (default = step back, per the parent spec's "default は step-back(fund しない)") — never falls
  back to a hardcoded auto-fund default on an ambiguous agent response, mirroring `thinkClaudeP`'s
  own `claude_exit_<code>`/`claude_empty_output`/`claude_invalid_json` reject paths
  (`brain.mjs:124-141`).
- The agent recommends `fund_recommended: true` with an `amount_usd` that is negative, zero,
  non-numeric, or exceeds the configured `per_transfer_usd_cap`: THE SYSTEM SHALL clip the
  requested amount to, at most, the SMALLER of (a) the configured per-transfer cap and (b) the
  remaining viability headroom — `max(0, viability_floor_usd - current_balance_usd)`, computed
  from REQ-002's observed balance and REQ-004's configured floor (closes FIND-003: a flat
  per-transfer cap alone does not bound how far one funding event pushes the resulting balance
  past the viability ceiling; this headroom clip does) — before the amount is ever passed toward
  FUND (REQ-007) — defense-in-depth ahead of `run.py`'s own identical per-transfer cap check, never
  a second path that could exceed either bound.
- The agent recommends `fund_recommended: true` while Franklin's own reported balance already
  exceeds the viability ceiling: this recommendation is still produced (the agent's own reasoning
  trace is preserved in the log for audit), but REQ-004's hard gate overrides it and no funding
  occurs — the log line distinguishes "agent recommended fund, but viability gate blocked it" from
  "agent recommended step-back".
- Even if the DECIDE subprocess's own reasoning text mentions or discusses running `run.py`,
  editing the ledger, or touching the kill-switch (e.g. hallucinated "next I will run..."
  narration), THE SYSTEM SHALL treat this as inert text within the `reasoning` field only — the
  wrapper script never executes, evals, or shells out any part of DECIDE's own output; only the
  three structured fields (`fund_recommended`/`amount_usd`/`reasoning`) are read as data.
**Acceptance Criteria**:
- Every non-gated wake produces exactly one recorded DECIDE output (`fund_recommended`,
  `amount_usd` or null, `reasoning`) attributable to a real LLM invocation for that wake (not a
  cached/stale prior decision, not a constant).
- The actual subprocess spawn call for DECIDE (argv + spawn options) contains NO
  `--dangerously-skip-permissions` flag and no other permissive tool-grant flag, uses the scrubbed
  minimal env (no private keys, no wallet credentials), and uses a neutral cwd distinct from the
  project working directory and from `skills/earn/funding/` — verified structurally, not merely by
  prose (PROP-012, closes FIND-006).
- No source file in this feature contains a numeric/regex "is Franklin broke" classifier — a
  review of the implementation (Phase 3 adversary check) confirms the starving/undergrown vs
  self-sufficient/growing judgment is made inside the LLM prompt path, not in a conditional in the
  wrapper script.

### REQ-004: HARD GATE — viability ceiling, both as a block AND as a sizing bound (agent judgment cannot override)
**EARS**: WHEN Franklin's live Solana USDC balance (REQ-002.1), read at gate-evaluation time, is
greater than or equal to a configured `viability_floor_usd` (default `20`, matching the existing,
already-live `runtime/loop/catalog-gate.mjs::DEFAULT_BOOTSTRAP_RESERVE_USDC` value at
spec-writing time) THE SYSTEM SHALL NOT proceed to FUND (REQ-007) for that wake, REGARDLESS of
DECIDE's (REQ-003) `fund_recommended` value, and SHALL log the skip with reason "already viable"
(step back — over-supply is forbidden, mirroring the parent design's "自立してたら step back"
principle).
**Correction (2026-07-08, spec-review iteration 2, closes FIND-003):** WHEN the balance IS below
`viability_floor_usd` (funding is not blocked outright), THE SYSTEM SHALL ALSO bound the SIZE of
the funded amount so a single funding event cannot push the resulting balance materially past
`viability_floor_usd` — this gate is not merely a binary allow/block on whether to fund, it also
supplies the `viability_floor_usd - current_balance_usd` headroom value that REQ-003's
`clip_amount` edge case uses (in addition to the flat `per_transfer_usd_cap`) to size the amount
ultimately passed to FUND (REQ-007). A flat per-transfer cap alone (the prior iteration's only
sizing bound) is unaware of how close the pre-fund balance already is to the floor and could
overshoot it by up to the full per-transfer cap.
**Edge Cases**:
- Balance exactly equal to `viability_floor_usd`: treated as viable (blocks funding outright) —
  the boundary is inclusive on the "already viable, do not fund" side, the safety-conservative
  direction (never funds when in doubt at the boundary); the headroom-sizing bound is moot here
  (funding is already blocked entirely).
- Balance just below the floor by less than the flat per-transfer cap (e.g. balance `$19.99`,
  floor `$20`, `per_transfer_usd_cap` `$12`): the EFFECTIVE maximum amount this gate permits
  toward FUND is the headroom (`$0.01`), NOT the flat per-transfer cap — a DECIDE recommendation
  of `$12` (at the cap) is clipped down to `$0.01` before ever reaching FUND, so the resulting
  balance lands at (approximately) the floor, never materially above it.
- Balance well below the floor (e.g. balance `$5`, floor `$20`, headroom `$15`, per-transfer cap
  `$12`): the per-transfer cap is the binding (smaller) bound, exactly as before this correction —
  the headroom-aware clip is a MINIMUM taken together with the existing per-transfer cap, never a
  mechanism that could permit a LARGER amount than the per-transfer cap would otherwise allow.
- Balance read fails (REQ-002 edge case): the wake already skipped DECIDE/FUND entirely; this gate
  is never reached with a missing/fabricated balance, and no headroom value is ever computed from
  a fabricated balance.
- `viability_floor_usd` misconfigured to a negative number or non-numeric value: THE SYSTEM SHALL
  fail closed — treat the gate as "always already viable" (never fund, headroom always `0`)
  rather than silently falling back to a hardcoded default that could re-enable funding on bad
  config.
**Acceptance Criteria**:
- A pure predicate function (e.g. `viability_gate(balance_usd, floor_usd) -> {allowed, reason,
  headroom_usd}`) exists, is unit-tested with a boundary table (`balance < floor`, `balance ==
  floor`, `balance > floor`, non-finite/negative inputs), and is the ONLY code path REQ-007
  consults for the allow/block half of this gate — no duplicate/inline re-check elsewhere.
- Given a live-observed Franklin balance below `viability_floor_usd` (the real state as of
  2026-07-08, ≈$11.63–$21.58 depending on the latest seed's confirmation), the gate returns
  `allowed: true` (does not itself block funding) unless a different gate (REQ-005/006) blocks it.
- Given `balance_usd = 19.99`, `floor_usd = 20`, `per_transfer_usd_cap = 12`, and a DECIDE
  recommendation of `amount_usd = 12`: the amount actually passed to FUND (REQ-007) is `<= 0.01`,
  not `12` — verified by a unit test composing `viability_gate`'s `headroom_usd` output with
  REQ-003's `clip_amount` (PROP-004).

### REQ-005: HARD GATE — cooldown, based on the most recent funding ATTEMPT of any pipeline step (agent judgment cannot override)
**EARS**: WHEN the most recent `funding-ledger.jsonl` row whose `step` is one of `"withdraw"`,
`"bridge"`, or `"send_to_franklin"` (i.e., a row written by the underlying mechanism itself, NOT
this feature's own `"loop-decide"` bookkeeping row — REQ-008) AND whose `status` is NOT `"dry"`
(a dry-run row is an explicit test-mode invocation that moves no money and is never produced by
this feature's own FUND step, REQ-007, which always invokes `run.py` in real/non-dry mode) has a
timestamp less than a configured `cooldown_hours` (default `24`, matching the funding skill's own
24h daily-cap accounting window) before the current gate-evaluation time THE SYSTEM SHALL NOT
proceed to FUND (REQ-007) for that wake, REGARDLESS of DECIDE's `fund_recommended` value, and
SHALL log the skip with reason "cooldown active" plus the remaining cooldown duration.
**Correction (2026-07-08, spec-review iteration 2, closes FIND-002):** the prior iteration of this
gate looked ONLY at rows with `step == "send_to_franklin" AND status == "sent"` — but its own
edge-case list already (inconsistently) required a `pending` `send_to_franklin` row to also start
the cooldown clock, and PROP-002's own test enumeration never actually exercised that case. Worse,
that narrow scope is blind to a wake where `withdraw` and/or `bridge` already moved real money but
`send_to_franklin` itself crashed before writing ANY row — in that scenario the prior gate would
see zero qualifying rows and report "no cooldown active," letting the very next wake fire a second
full withdraw→bridge→send sequence while the first wake's funds are still stranded mid-pipeline.
The fix: cooldown is now keyed to the MOST RECENT row across ALL THREE mechanism steps, any
non-`"dry"` status (`pending`/`sent`/`failed` all count as "an attempt happened at this
timestamp") — the fail-closed, conservative choice, since it can only make this gate MORE likely
to block (never less) relative to the prior, narrower scope.
**Edge Cases**:
- No prior `withdraw`/`bridge`/`send_to_franklin` row exists at all (first-ever fund, or
  `funding-ledger.jsonl` absent or containing only this feature's own `"loop-decide"` rows):
  cooldown is NOT active (nothing to be on cooldown from) — this gate returns `allowed: true` by
  itself in that case.
- Multiple qualifying rows exist across all three steps: only the SINGLE most recent one's
  timestamp (by `ts`, regardless of which of the three `step` values it has) is used.
- A `pending` (broadcast-but-not-yet-confirmed) row for ANY of the three steps, with no later
  terminal `sent`/`failed` row for the same signature/tx_hash: treated conservatively as if a send
  may complete — the cooldown clock starts from the `pending` row's own timestamp (never treated
  as "no cooldown" just because confirmation hasn't resolved yet).
- `withdraw` and `bridge` both have terminal `"sent"` rows but no `send_to_franklin` row of any
  status exists (the crash-before-any-row scenario from the failure analysis above): the cooldown
  clock starts from `bridge`'s `"sent"` row timestamp (the most recent qualifying row across the
  three steps), NOT treated as "no cooldown" merely because the final step never wrote anything —
  this is the specific gap this correction closes.
- A `"failed"` row (e.g. a cap rejection, or "no USDC balance available to send") for any of the
  three steps still counts as a qualifying attempt and starts the cooldown clock from its
  timestamp — a wake that attempted and failed is still "an attempt," and treating it as such is
  the fail-closed direction (it can only delay a subsequent legitimate fund, never permit an
  unintended one).
- A `"dry"` row (an explicit, non-money-moving test invocation) does NOT start the cooldown clock
  — this feature's own FUND step (REQ-007) never produces one, so counting them would only ever
  reflect manual/out-of-band testing of the underlying mechanism, not a real funding attempt by
  this loop.
**Acceptance Criteria**:
- A pure predicate function (e.g. `cooldown_gate(last_attempt_ts, now_ts, cooldown_hours) ->
  {allowed, reason}`) exists, is unit-tested (no-prior-row case, just-under-window,
  exactly-at-window, well-past-window, PLUS a pending-row-only case and a
  withdraw/bridge-succeeded-but-no-send_to_franklin-row case per PROP-002), and is the ONLY code
  path REQ-007 consults for this gate.
- The row-selection step that computes `last_attempt_ts` from `funding-ledger.jsonl` (feeding
  `cooldown_gate`) is itself unit-tested to confirm it selects the most recent row across all
  three mechanism `step` values (not `send_to_franklin` alone), excludes `"dry"` rows, and
  excludes this feature's own `"loop-decide"` rows.
- Two funding decisions less than `cooldown_hours` apart are never both allowed to reach FUND
  (REQ-007) for the same Franklin wallet, including when the earlier decision's pipeline only
  partially completed (e.g. withdraw+bridge succeeded, send_to_franklin never wrote a row).

### REQ-006: HARD GATE — caps and reserve protection delegated to `funding/run.py` (never duplicated, never bypassed)
**EARS**: WHEN FUND (REQ-007) is about to be invoked THE SYSTEM SHALL pass, at most, a proposed
`--amount-usd` value to `skills/earn/funding/run.py` (the `skills/earn/funding/` location itself
resolved via the single configurable base directory defined in Non-Functional Requirements —
"Path indirection", closes FIND-005 — not re-hardcoded a second time here) and SHALL treat
`run.py`'s own, unchanged,
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
- **Path indirection (relocation-safety, added 2026-07-08 spec-review iteration 2, closes
  FIND-005)**: every path this feature's own new code references under
  `~/anicca/skills/earn/funding/` and `~/anicca/skills/earn/state/` (as enumerated in REQ-002's
  OBSERVE reads, REQ-006/007's FUND invocation, and REQ-008's LOG write) SHALL resolve through
  exactly ONE configurable base-directory value (e.g. an environment variable
  `FRANKLIN_FUNDING_HOME`, default `$HOME/anicca`) defined in exactly one place in this feature's
  own entry script/config — NEVER a second, independently-hardcoded literal of `~/anicca`
  elsewhere in this feature's own new code. `05-coordination-with-agent-economy.md` §8 Q3 (Dais
  2026-07-08) judges that `skills/earn/funding/` belongs in
  `~/profitable-claude/skills/human-funded/` and that the migration itself is this skill's own
  owner's job, not this feature's — this feature does not perform that relocation, but ensures
  that if/when it happens, updating this feature's own pointer to the mechanism requires changing
  ONE value, not every call site.
