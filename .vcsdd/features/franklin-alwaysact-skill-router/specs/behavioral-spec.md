# Behavioral Spec — franklin-alwaysact-skill-router

## 0. Doctrine (canonical, do not paraphrase away)

Source (verbatim rule, memory `feedback_franklin_never_waits_always_acts_to_earn`, Dais 2026-07-10,
angry, repeated): "WAIT に意味はない。skip は malware だ。broke で agent economy も無いのに待つな。$13 で
待ってたら永遠に $13 だ。AI 自身なんだから、持っている全 skill から今この瞬間走らせるべき skill を選んで
実行し、金を稼げ。24/7。" — Franklin's loop is a CEO-like actor that holds every earn skill. Every wake it
MUST survey all earn skills + its current assets and MUST execute exactly one best positive-EV earning
action. idle/WAIT is a failure signal, not a legitimate outcome. Money-safety is preserved: "always act"
never means forcing a losing trade past a cap — when one skill (e.g. SOL) has no edge, the router routes
to a market-risk-free skill (e.g. take a gig, post a clip) instead. Caps/scope_guard are unchanged.

This feature is the **capital-allocator + skill-router**: the harness's only job is to (a) present the
full earn-menu + asset snapshot every wake, (b) structurally forbid the idle/no-op terminal path, (c)
never weaken any existing money-safety cap, (d) ledger the chosen action + reason every wake. **Skill
choice itself stays 100% model judgment** (`rules/building-effective-ai-agents.md`,
`feedback_build_agents_not_hardcode_regex`, `feedback_skills_give_tool_not_decision`) — the harness never
computes EV, never ranks skills, never picks a slot by regex/keyword/if-else.

## 1. Ground truth read from the existing codebase (this spec extends, never contradicts, these files)

- `runtime/loop/index.mjs:382-416` — the TWO existing idle paths this feature must close for the gated
  identity: (a) `parseToolCall(rawResponse)` returns falsy → a `kind:'narrate'` ledger line is written and
  the wake ends with no skill executed; (b) the model calls the `sleep` tool → a `kind:'narrate'` line
  (`note: args.reason || 'agent chose to sleep'`) is written and the wake ends with no skill executed.
- `runtime/loop/prompt.mjs:10-24,139-173` — `SLEEP_TOOL` is unconditionally appended to every tool
  definition list (`getToolDefinitions`), so the model always has a legal "do nothing" choice.
- **The REAL wiring seam from ctx to the outbound tool schema (spec-review FIND-001/FIND-005 ground
  truth)**: `runtime/loop/brain.mjs:63` (`thinkProxy`) hardcodes `tools: getToolDefinitions(ctx.
  activeSkillSlots)` as the literal `tools` field of the HTTP request body sent to the model, and
  `runtime/loop/brain.mjs:92` (`thinkClaudeP`) hardcodes the prompt-text instruction `'Respond with a JSON
  tool_calls block using run_skill or sleep.'`. `getToolDefinitions(slots)` (`prompt.mjs:139-173`) has no
  parameter for omitting `SLEEP_TOOL` — it is appended unconditionally at `prompt.mjs:171` for every call,
  including any call this feature makes. There is therefore NO existing seam by which REQ-504's sleep-omission
  can reach the model without: (a) `prompt.mjs::getToolDefinitions` gaining an additive, backward-compatible
  optional second parameter (`opts.omitSleep`, default `false`) that all other existing call sites never
  pass and are therefore byte-for-byte unaffected by, and (b) `brain.mjs`'s two `tools:`/prompt-text call
  sites becoming conditional on a new `ctx.alwaysActEngaged` boolean (set by REQ-501's gate) and
  `ctx.alwaysActMenu` (set by REQ-502/503's filtered menu). Both `prompt.mjs` and `brain.mjs` ARE modified by
  this feature — see the corrected Purity Boundary Map in verification-architecture.md and REQ-504 below.
- `runtime/loop/index.mjs:440-456` + `runtime/loop/earn-detect.mjs:23-50` — `classifyEarnResult(wakeId,
  earnLedgerPath, isProfitableFn)` already reads `earn-ledger.jsonl`, finds the line keyed by
  `line.wake === wakeId` (never last-line position), and returns `{ profitable, earnLine }`; `earnLine ===
  null` means **no realized economic result was recorded for this wake** — this is the existing,
  skill-agnostic primitive this feature reuses to detect a no-op earn pick (REQ-506). **Ground-truth
  correction (spec-review FIND-002)**: `classifyEarnResult` is only ever CALLED from `index.mjs:450`'s
  `else if (isEarnSlot(slot))` branch — the CALL-SITE gate, not `classifyEarnResult` itself, is what
  decides whether a pick gets classified at all. Since `isEarnSlot('economy/gig') === false` and
  `isEarnSlot('economy/lending') === false` (see the next bullet), that call-site gate must be widened
  for always-act-engaged wakes (REQ-506) or a gig/lending no-op silently falls through the ordinary
  `kind:'wake'` branch and is never detected.
- `skills/earn/sol-trade/run.sh:105-158` — concretely: `franklin-trading start` always appends an
  `action:"live-pass"` trace line, but only calls `record-swap.mjs` (which writes to `earn-ledger.jsonl`)
  **when a swap signature was found** (line 113-116). A neutral-signal WAIT inside the sol-trade skill
  therefore produces `earnLine === null` for that wake — exactly the same signal as a guard-triggered
  `action:"skip"` (kill-switch / identity-mismatch / cumulative-loss breach, lines 21-24, 38-41, 45-48).
  Both are "no realized action" from the router's point of view, for different underlying reasons; this
  feature treats them identically (REQ-506) without needing to interpret *why*.
- `runtime/loop/earn-slot.mjs:isEarnSlot` — the existing earn-classification predicate covers only
  `{earn, yield, hl_trade, x402_sell, token_launch}` ∪ `earn/*`. The doctrine names a wider set as
  legitimate earning actions (SOL-trade, HL-trade, PM-trade, **gig take/post**, clip, video, **lending**).
  `economy/gig` and `economy/lending` are NOT covered by `isEarnSlot`. This feature introduces a
  **separate, wider, purely-additive** predicate (`isEarnActionSlot`, REQ-502) for router-menu purposes.
  `isEarnSlot`'s own DEFINITION is NOT modified (it is relied on elsewhere for non-always-act wakes'
  ledger profitability attribution, and changing its contract is out of scope and would risk regressing
  that unrelated behavior) — but per the correction above, its CALL SITE at `index.mjs:450` IS additively
  widened for always-act-engaged wakes only (REQ-506): `else if (ctx.alwaysActEngaged ? isEarnActionSlot(slot)
  : isEarnSlot(slot))`. Any non-always-act wake (`ctx.alwaysActEngaged` falsy — every non-Franklin instance,
  and Franklin herself whenever the flag is off) evaluates `isEarnSlot(slot)` exactly as today, byte-for-byte.
- **`avoidSlot`'s real semantics (spec-review FIND-003 ground truth)**: `index.mjs:175-184`'s `avoidSlot`
  mechanism is, by its own inline comment (`index.mjs:183`), a SOFT, prompt-text-only nudge — `"the agent's
  choice is never blocked, only the enforced pause after ignoring it grows"` — surfaced purely as prose in
  `buildUserMessage` (`prompt.mjs:205-207`, `"⛔ ... it is FORBIDDEN this wake. Pick a DIFFERENT slot."`). It
  NEVER touches `getToolDefinitions`'s `slot.enum` and therefore never structurally prevents a re-pick.
  REQ-506's reroute does **NOT** reuse `avoidSlot` or claim enum-level exclusion through it. Instead, because
  REQ-504 already constructs the always-act tool schema from an explicit, harness-controlled array
  (`buildAlwaysActToolDefinitions(menuSlots)`), REQ-506's reroute performs a genuine, purpose-built hard
  array filter — `buildAlwaysActToolDefinitions(menuSlots.filter(s => s !== pickedSlot && isMarketRiskFree(s)))`
  (spec-review iteration-2 FIND-101 correction: the filter also excludes every `risk:"capital"` slot, not
  merely the just-picked one — see REQ-506) — before the re-invocation, so the just-picked slot AND every
  capital-risking slot are truly absent from the schema the model receives. `avoidSlot` /
  `index.mjs:179-421`'s loop-detect diversification remains completely unmodified and continues to operate
  independently for its own (unrelated, cross-wake) purpose.
- `skills/registry.json` — single source of truth for live/declared status and per-slot `risk`/`summary`.
  Relevant earn-action slots today (status `"live"`): `yield`, `hl_trade`, `x402_sell`, `token_launch`,
  `economy/gig`, `economy/lending`, `earn/clip`, `earn/clip-producer`, `earn/video`, `earn/sol-trade`,
  `earn/polymarket-trade`. Utility/exploration slots explicitly **excluded** from the router's mandatory
  menu: `report`, `cook`, `self/spawn`, `self/spawn-child`, `self/issue-dev`, `self/coordinate`,
  `economy/ubi`, `earn/audit` (status `"declared"`, not live), `earn/_probe` (status `"declared"`), `earn`
  (retired placeholder, status `"declared"`). **Spec-review iteration-2 FIND-101 ground-truth addition**: of
  these 11 always-act-menu slots, `skills/registry.json`'s existing per-slot `risk` field (read directly this
  iteration) is `"safe"` for `economy/gig`, `economy/lending`, `x402_sell`, `earn/clip`, `earn/clip-producer`,
  `earn/video`, and `"capital"` for `yield`, `hl_trade`, `token_launch`, `earn/sol-trade`,
  `earn/polymarket-trade` — this pre-existing field is REQ-506's `isMarketRiskFree` reroute filter's source
  of truth; no new/duplicate classification data is introduced.
- `skills/earn/sol-trade/run.sh:28-41` — the **identity-match guard idiom** this feature's Franklin-gate
  reuses verbatim (REQ-501): derive `OWN_WALLET` via `runtime/wallet-address-solana.mjs` under the current
  `ANICCA_HOME`, derive `CLI_WALLET` under `ANICCA_HOME="$HOME/.blockrun"`, and only proceed when they are
  equal and non-empty. Fail-closed (empty/mismatched → do not proceed) is the existing convention.
- `skills/self/earning-health.py` — the existing barren-loop detector. It explicitly (by design,
  docstring lines 12-22) treats a long run of `action:"live-pass"` WAITs inside sol-trade as **healthy**
  (a legitimate sub-agent judgment call), and only a run of identical `action:"skip"` reasons as barren.
  This feature does not change that detector's semantics; it operates one layer up (the router's own
  MUST-pick-a-realized-action-or-reroute layer, REQ-506/REQ-507), and its own escalation (REQ-508) is
  additive to, not a replacement for, `earning-health.py`. `is_fresh_but_barren`'s pure, no-I/O,
  pre-gathered-tail contract (the caller reads the file, the function only judges the tail array) is the
  **template REQ-512's own companion detector copies** (spec-review FIND-004).
- **`SOL_GATE_LIVE_ENABLE` is NOT analogous to REQ-501(b)'s flag in blast radius (spec-review FIND-004
  ground truth)**: `skills/earn/sol-trade/run.sh:68-76`'s comment states verbatim that in default (unset)
  mode the gate is `"PURE SHADOW OBSERVATION ... it NEVER alters what franklin-trading does below"` — i.e.
  the underlying earn action fires every wake REGARDLESS of that flag. REQ-501(b)'s flag, by contrast, gates
  the entire always-act anti-idle mechanism itself — OFF means Franklin's wakes are exactly as idle-capable
  as before this feature existed, which doctrine (§0) names a failure condition ("skip は malware だ"). This
  asymmetry is why REQ-501(b)'s flag needs its OWN explicit observability signal (REQ-512) that
  `SOL_GATE_LIVE_ENABLE` never needed.

## 2. Purity Boundary Analysis (summary; full map in verification-architecture.md)

- **Pure core (new)**: menu assembly, earn-action classification, no-realized-action detection, reroute
  bounding, MUST-ACT prompt/tool-definition construction — all deterministic transforms over
  already-loaded data (registry, ctx, earn-ledger line), no I/O, mirrors the existing purity split
  (`context.mjs`, `prompt.mjs`, `tier.mjs`, `catalog-gate.mjs`, `earn-slot.mjs` are pure today).
- **Effectful shell (extended, not replaced)**: `runtime/loop/index.mjs`'s wake loop (the reroute retry
  orchestration, ledger appends, escalation writes, and — spec-review FIND-002 correction — the
  classify-call-site gate at `index.mjs:450` additively widened from `isEarnSlot(slot)` to
  `(ctx.alwaysActEngaged ? isEarnActionSlot(slot) : isEarnSlot(slot))`), the identity-derivation subprocess
  calls (`wallet-address-solana.mjs` under two `ANICCA_HOME` values, exactly as `sol-trade/run.sh` already
  does), and the unchanged skill execution + money-safety guards inside each skill's own `run.sh`.
  **Spec-review FIND-001/FIND-005 correction**: `runtime/loop/brain.mjs`'s `thinkProxy`/`thinkClaudeP` ARE
  additively modified — the `tools:`/prompt-text lines become conditional on `ctx.alwaysActEngaged` (see §1
  and REQ-504) — and `runtime/loop/prompt.mjs::getToolDefinitions` gains an additive, backward-compatible
  `opts.omitSleep` parameter. Both stay correctly classified by their existing purity category (`brain.mjs`
  stays effectful/shell, `prompt.mjs` stays pure/core) — only their "unmodified" status is corrected to
  "additively modified"; see verification-architecture.md's Purity Boundary Map for the authoritative,
  corrected split.

## Requirements

### REQ-501: Identity-gated, explicitly-enabled activation
**EARS**: WHEN a wake begins THE SYSTEM SHALL activate always-act-router behavior for that wake IF AND
ONLY IF (a) the resolved identity of the current `ANICCA_HOME` matches Franklin's identity, using the
exact own-wallet-vs-`~/.blockrun`-wallet derivation-and-comparison idiom already used in
`skills/earn/sol-trade/run.sh:28-41`, AND (b) the operator has explicitly enabled the feature via a
config flag (default OFF), mirroring the existing `SOL_GATE_LIVE_ENABLE` dev-safety-default pattern
(`franklin-sol-evolvable-edge` REQ-009 — "structurally IMPOSSIBLE while `SOL_GATE_LIVE_ENABLE!=='1'`").
**Edge Cases**:
- Identity derivation subprocess errors, times out, or returns empty for either side: treat as NOT
  Franklin (fail-closed — do not activate always-act; the wake falls through to today's unmodified
  behavior, including the `sleep` tool).
- Flag unset/malformed/non-`"1"` value: treat as disabled (fail-closed), identical handling to
  `SOL_GATE_LIVE_ENABLE`'s own REQ-009 contract.
- Any instance other than Franklin (e.g. `anicca-a3cdd4`/automaton) running this same loop code: this
  feature is a structural no-op for it — the identity check alone (not the flag) is sufficient to prevent
  cross-instance activation even if the flag were mistakenly set globally.
**Acceptance Criteria**:
- A unit test with a mocked identity-derivation function returning mismatched wallets asserts always-act
  mode is NOT engaged (the `sleep` tool remains present in that wake's tool definitions).
- A unit test with matched wallets AND the flag set asserts always-act mode IS engaged.

### REQ-502: Earn-action menu is registry-driven and wider than (never narrower than, never a fork of) `isEarnSlot`
**EARS**: WHEN always-act mode is engaged for a wake THE SYSTEM SHALL assemble the earn-action menu as
every slot in `skills/registry.json` with `status === "live"` that is either (a) already `isEarnSlot(name)
=== true` (`runtime/loop/earn-slot.mjs`, unmodified), OR (b) explicitly named by the doctrine as an
earning action — `economy/gig`, `economy/lending` — via a new, purely-additive predicate
`isEarnActionSlot(name)` that is the union of (a) and a fixed, doctrine-derived set, and never modifies or
forks `isEarnSlot` itself.
**Edge Cases**:
- A future registry slot with `status:"live"` that is neither in `isEarnSlot`'s set nor the doctrine's
  named set (e.g. a brand-new utility slot) is excluded from the menu by default — widening the menu
  requires an explicit spec update, not silent inclusion, so the router never starts forcing a pick from
  an unvetted new slot.
- A doctrine-named slot (`economy/gig`, `economy/lending`) whose registry `status` is NOT `"live"` (e.g.
  reverted to `"declared"`) is excluded from the menu — liveness always wins over doctrine-naming.
- Zero live earn-action slots resolve (menu is empty): this is a spec violation, not a valid "nothing to
  do" state — the wake MUST fail loudly (`kind:'router_menu_empty'` ledger line + escalation, REQ-508),
  never silently fall back to `sleep`/narrate.
**Acceptance Criteria**:
- Given the current `skills/registry.json`, `isEarnActionSlot` menu resolves to exactly: `yield`,
  `hl_trade`, `x402_sell`, `token_launch`, `economy/gig`, `economy/lending`, `earn/clip`,
  `earn/clip-producer`, `earn/video`, `earn/sol-trade`, `earn/polymarket-trade` (11 slots) — verified by a
  literal-set-equality unit test that will fail loudly if the registry changes without a matching spec
  update.
- `report`, `cook`, `self/spawn`, `self/spawn-child`, `self/issue-dev`, `self/coordinate`, `economy/ubi`
  are asserted absent from the menu.

### REQ-503: Bootstrap-reserve catalog gate still applies inside the earn-menu
**EARS**: WHEN always-act mode assembles the earn-action menu THE SYSTEM SHALL further filter it through
the existing `catalog-gate.mjs::filterCatalog` (unmodified) using the instance's real balance and the
existing `BOOTSTRAP_RESERVE_USDC` threshold, exactly as today's non-always-act menu assembly already does,
so capital-risking slots stay hidden below reserve (open-position carve-outs unchanged).
**Edge Cases**:
- After the reserve filter, the earn-action menu could shrink to a set still ≥ 1 (e.g. `economy/gig`
  take-side and `earn/clip` remain `risk:"safe"`/`alwaysAvailable`-equivalent and are never filtered out by
  balance) — REQ-502's empty-menu failure mode (REQ-508) is the only path that produces zero.
- The catalog gate's own fail-closed defaults (untagged slot ⇒ treated as capital-risking) are inherited
  unchanged; this feature adds no new tagging.
**Acceptance Criteria**:
- A unit test with `balanceUsdc` below `BOOTSTRAP_RESERVE_USDC` asserts capital-risking menu slots
  (`hl_trade`, `token_launch`, `yield` new-deposit, `earn/sol-trade`, `earn/polymarket-trade`) are absent
  unless an open position exists for that slot, while `economy/gig`, `earn/clip`, `x402_sell` remain
  present.

### REQ-504: `sleep` tool is withheld on an always-act-engaged wake — on the REAL outbound wire, not just a standalone helper
**EARS**: WHEN always-act mode is engaged for a wake THE SYSTEM SHALL build the ACTUAL tool definitions
that reach the model — i.e. the literal `tools` field of the HTTP request body `runtime/loop/brain.mjs::
thinkProxy` sends, and the equivalent instruction text `thinkClaudeP` sends — WITHOUT the `sleep` tool, via
the following concrete, real wiring seam (spec-review FIND-001/FIND-005 fix — this is the mechanism, not an
implementation detail left to Phase 2b):
1. The `WakeContext` (`assembleContext`, `runtime/loop/context.mjs`) gains two additive fields set by
   `index.mjs`'s wake loop: `ctx.alwaysActEngaged` (boolean, REQ-501's gate result) and `ctx.alwaysActMenu`
   (`string[]`, REQ-502/503's filtered menu — only populated when `alwaysActEngaged` is true).
2. `runtime/loop/prompt.mjs::getToolDefinitions(slots, opts)` gains an additive, optional second parameter
   `opts = { omitSleep: false }` (default preserves every existing call site's exact current output,
   byte-for-byte). When `opts.omitSleep === true`, the returned array omits `SLEEP_TOOL` (the pure function
   `buildAlwaysActToolDefinitions(menuSlots)` in the pure core is a thin wrapper:
   `getToolDefinitions(menuSlots, { omitSleep: true })` — NOT a parallel reimplementation).
3. `brain.mjs:63` (`thinkProxy`)'s `tools:` line becomes:
   `tools: getToolDefinitions(ctx.alwaysActEngaged ? ctx.alwaysActMenu : ctx.activeSkillSlots, { omitSleep:
   ctx.alwaysActEngaged === true })` — a non-always-act `ctx` (the overwhelming majority of wakes, every
   non-Franklin instance) produces the exact current call, unchanged.
4. `brain.mjs:92` (`thinkClaudeP`)'s prompt-text instruction line conditionally drops the sleep mention when
   `ctx.alwaysActEngaged` is true (`'Respond with a JSON tool_calls block using run_skill.'` instead of
   `'... using run_skill or sleep.'`), so the text-mode brain path is not left silently inconsistent with the
   tool-schema path.
The only callable tool in always-act mode is therefore `run_skill`, with its `slot` enum constrained to
REQ-503's filtered earn-action menu.
**Edge Cases**:
- A model response that nonetheless attempts `slot: "sleep"` or any slot outside the enum (a
  spec/tool-contract violation by the model, not the harness — the schema truly does not offer it) is NOT
  auto-rejected by any pre-existing enum-validation step (spec-review FIND-103 correction: no such step
  exists in `index.mjs`'s real wake loop today — `parseToolCall` performs no cross-check against the offered
  `tools` array, and the existing `if (slot === 'sleep')` branch at `index.mjs:402-416` is a bare string
  check that would otherwise honor it). REQ-513 defines the concrete, real mechanism that makes this case
  actually safe.
- `thinkClaudeP`'s text-prompt path has no formal JSON-schema enum enforcement; if the model emits a
  sleep-shaped `tool_calls` block despite the reworded instruction (step 4), REQ-513 governs its handling
  identically to the schema-level case above — never silently accepted as a valid sleep.
**Acceptance Criteria**:
- (Pure-function level, necessary but NOT sufficient alone) `getToolDefinitions(menuSlots, { omitSleep:
  true })` / `buildAlwaysActToolDefinitions(menuSlots)` returns a tool array of length 1 (`run_skill` only),
  whose `slot.enum` equals REQ-503's filtered menu; called with `omitSleep` false/omitted, output is
  byte-identical to today's `getToolDefinitions(slots)`.
- (Wiring-seam level, the test that actually proves FIND-001's demand) A test that calls the REAL
  `thinkProxy` (mocking only the network boundary — the `httpPost` call — never a real HTTP request) with
  `ctx.alwaysActEngaged = true` and a fixture `ctx.alwaysActMenu`, and asserts the ACTUAL JSON-stringified
  request body captured at the mocked `httpPost` boundary contains `tools` with no entry whose
  `function.name === 'sleep'`. The same style of test with `ctx.alwaysActEngaged` falsy/absent asserts the
  captured body's `tools` DOES include `sleep`, proving the conditional wiring — not just the standalone
  helper — is what actually governs the outbound wire.

### REQ-505: A no-tool-call (text-only) response is not accepted as the wake's terminal outcome
**EARS**: WHEN always-act mode is engaged AND `parseToolCall(rawResponse)` returns falsy THE SYSTEM SHALL
NOT write the existing `kind:'narrate'` no-op ledger line as the wake's terminal state; instead it SHALL
re-invoke the brain exactly once more within the same wake with a strengthened MUST-ACT reinforcement
message (reusing `buildUserMessage`'s existing steer-composition pattern, appending one additional directive
line), bounded to `MAX_REPROMPTS = 1` for this failure mode.
**Edge Cases**:
- The re-prompt also returns no tool call: this is a genuine no-op after the bound is exhausted — proceed
  to REQ-508 (truthful record + escalate), never a third silent retry (cost/latency bound).
- The re-prompt costs one additional model call — this is accepted as intentional harness behavior
  (bounded to 1), matching this feature's money-safety framing (a bounded retry cost is preferable to a
  wasted, unproductive wake).
**Acceptance Criteria**:
- A unit test with a mocked `think()` that first returns no tool call then a valid `run_skill` call
  asserts exactly 2 `think()` invocations and the second's chosen slot is executed.
- A unit test with a mocked `think()` that never returns a tool call asserts exactly 2 `think()`
  invocations total (not more) and the wake ends in REQ-508's escalation path.

### REQ-506: A picked earn slot with no realized economic result triggers a bounded same-wake reroute, via a genuine hard tool-enum exclusion, to a market-risk-free slot only
**EARS**: WHEN always-act mode is engaged AND the model picks a slot `s` from the earn-action menu AND `s`'s
execution completes (any exit code) THE SYSTEM SHALL first determine whether `s` is classify-eligible using
the SAME always-act-gated predicate REQ-502 defines for menu membership — `isEarnActionSlot(s)` (the wider,
additive predicate covering `economy/gig` and `economy/lending` in addition to every `isEarnSlot` member) —
not the narrower `isEarnSlot(s)` that gates classification on a non-always-act wake. Concretely (spec-review
FIND-002 fix): `index.mjs:450`'s classify call-site condition becomes `else if (ctx.alwaysActEngaged ?
isEarnActionSlot(slot) : isEarnSlot(slot))`, so `classifyEarnResult` IS invoked for an `economy/gig` or
`economy/lending` pick on an always-act-engaged wake, exactly as it already is for any `isEarnSlot` member.
THE SYSTEM SHALL then, IF `classifyEarnResult(wakeId, earnLedgerPath, isProfitableFn).earnLine === null`
(`runtime/loop/earn-detect.mjs`, unmodified — true for both a guard-triggered `action:"skip"` and a
sub-agent's own neutral-signal WAIT with no ledger line, per §1), treat this as "no realized action this
wake" and re-invoke the brain exactly once more with a genuine, HARD tool-enum exclusion of BOTH the
just-picked slot AND every capital-risking slot (spec-review iteration-2 FIND-101 fix — the doctrine's own
promise, §0: "routes to a market-risk-free skill ... instead"): `buildAlwaysActToolDefinitions(menuSlots.
filter(x => x !== s && isMarketRiskFree(x)))`, where `isMarketRiskFree(x)` is `riskTagOf(x) === 'safe'`
using the SAME injected `riskTagOf` classifier REQ-502/503's `assembleAlwaysActMenu` already threads from
`skills/registry.json`'s per-slot `risk` field (§1) — not a new, separate classification source. Given the
current registry (§1), the reroute target set NEVER includes `earn/sol-trade`, `earn/polymarket-trade`,
`hl_trade`, `token_launch`, or `yield` (all `risk:"capital"`) — a capital-risking slot is never a valid
reroute target after a no-edge WAIT, regardless of which slot was just picked (spec-review FIND-003 fix —
REQ-504's own purpose-built, explicit-array tool-definition constructor; this is NOT the soft, prompt-text-
only `avoidSlot` mechanism at `index.mjs:179-421`, which is untouched and unrelated — see §1). The
just-picked slot AND every capital-risking slot are therefore structurally ABSENT from the reroute's tool
schema, not merely discouraged in prose, so the model cannot re-select either — bounded to `MAX_REROUTES = 1`
(shared with REQ-505's budget per REQ-511).
**Edge Cases**:
- A slot execution that DOES write an earn-ledger line for this wake (`earnLine !== null`) — whether
  `profitable` is `true` or `false` (a real, recorded loss still counts as a realized economic action, not
  a no-op) — is accepted immediately; no reroute.
- The rerouted second pick ALSO produces `earnLine === null`: the bound is exhausted — proceed to REQ-508
  (truthful record + escalate), never a third same-wake attempt.
- REQ-502/503's filtered always-act menu has exactly ONE member overall, and it IS the just-picked slot: the
  hard filter (`menuSlots.filter(x => x !== s && isMarketRiskFree(x))`) leaves ZERO slots — a `run_skill`
  tool schema with an empty `slot.enum` is not a valid/offerable tool definition. THE SYSTEM SHALL, in this
  specific case, skip the re-invocation entirely (spend zero additional `think()` calls) and proceed directly
  to REQ-508's truthful escalation, since no alternative earn-action exists this wake. This is expected to be
  RARE (REQ-502/503 frame the common case as ≥1 always-eligible safe slot) but is a real, coherent,
  spec-defined terminal case — never a crash, never a forced same-slot repick.
- **The risk-free-filtered reroute set is empty even though OTHER (non-self) slots remain in the raw menu**
  (spec-review iteration-2 FIND-101 fix) — e.g. every remaining live always-act slot besides `s` happens to
  be `risk:"capital"`: THE SYSTEM SHALL treat this identically to the previous bullet — skip the
  re-invocation entirely (zero additional `think()` calls) and proceed directly to REQ-508's truthful
  escalation. THE SYSTEM SHALL NEVER fall back to offering a `risk:"capital"` slot as the reroute target
  merely to avoid an escalation — money-safety (never forcing a second capital-risking attempt past a
  legitimate no-edge WAIT) always wins over "always act" busyness. Given REQ-502/503's current registry
  composition (6 of 11 always-act slots are `risk:"safe"`), this is expected to be RARE in practice but is a
  real, coherent, spec-defined terminal case.
- This reroute is NEVER triggered by a slot execution that itself errors/times out (`skillResult.timedOut`
  / `skillResult.notFound` / non-zero exit for a NON-earn-guard reason) in a way that bypasses REQ-508's
  existing `appendHarnessFailure` mechanism (`index.mjs:458-475`) — that mechanism is unmodified and fires
  independently.
**Acceptance Criteria**:
- A unit test with a fixture earn-ledger containing no line for `wakeId` after executing a first-picked
  slot that is a LEGACY `isEarnSlot` member asserts `classifyEarnResult` is invoked, a second `think()` call
  occurs, and the actual constructed tool schema for that second call has a `slot.enum` that does NOT
  contain the just-picked slot (a real array-content assertion on the tool-definitions object, not a
  bookkeeping flag); if the second pick's ledger fixture DOES contain a matching line, the wake terminates
  there (no third call).
- The SAME test, run against a first-picked slot of `economy/gig` and, separately, `economy/lending`
  (neither is an `isEarnSlot` member), asserts identical behavior — `classifyEarnResult` IS invoked (proving
  the `isEarnActionSlot`-gated call-site widening fires) and the wake does NOT silently resolve as an
  ordinary `kind:'wake'` when `earnLine === null`. This is the regression test for spec-review FIND-002.
- A unit test with an always-act menu whose single member equals the just-picked slot and `earnLine ===
  null` asserts zero additional `think()` calls and immediate REQ-508 escalation (the empty-enum terminal
  case, spec-review FIND-003's edge-case resolution).
- **(spec-review iteration-2 FIND-101 regression test, PROP-506e "reroute-target-is-risk-free")** A unit
  test with a fixture registry where the first-picked slot is `earn/sol-trade` (`risk:"capital"`,
  `earnLine === null`) and the always-act menu also contains `hl_trade`, `token_launch`,
  `earn/polymarket-trade`, `yield` (all `risk:"capital"`) PLUS `economy/gig` and `earn/clip` (both
  `risk:"safe"`) asserts the reroute's ACTUAL constructed tool schema's `slot.enum` equals exactly
  `{economy/gig, earn/clip}` — every `risk:"capital"` slot, not only the just-picked one, is absent from the
  reroute enum.
- **(spec-review iteration-2 FIND-101 regression test, PROP-506f "empty-safe-set-escalates")** A unit test
  with a fixture always-act menu whose only members besides the just-picked (capital-risking) slot are ALSO
  `risk:"capital"` (i.e. the risk-free-filtered set is empty though the raw excluded-self set is not) asserts
  zero additional `think()` calls and immediate REQ-508 escalation — never a reroute into a `risk:"capital"`
  slot.

### REQ-507: Skill choice remains 100% model judgment — the harness never ranks, scores, or filters by strategy content
**EARS**: THE SYSTEM SHALL, at every point in REQ-502 through REQ-506, treat the model's chosen `slot`
(and its `args`) as an opaque value passed straight through to skill execution — the harness's menu
filtering (REQ-502/503) operates ONLY on registry bookkeeping fields (`status`, membership in the
doctrine-named set, `risk` tag, open-position fact) and NEVER on the semantic content of any model
response, `args`, or skill output; no expected-value formula, score, ranking, or regex/keyword match over
model text ever determines which slot executes.
**Edge Cases**:
- A regression here would look like: the harness inspecting `rawResponse` text for words like "SOL" or
  "gig" to decide the slot, instead of using the model's own structured `slot` field — this is explicitly
  forbidden.
**Acceptance Criteria**:
- A property test: for every slot `s` in the (fixture) earn-action menu, when the mocked brain returns
  `run_skill({slot: s, args: {...arbitrary}})`, the harness executes exactly slot `s` with exactly those
  `args` — for ALL menu members, not a hardcoded subset — proving the harness contains no internal
  preference ordering.
- A static/code-shape check: the reroute/menu-assembly module imports/uses only `registry`, `ctx`,
  `earnLine`/`avoidSlot` bookkeeping values — never `String.match`/regex/`if (args.strategy === ...)`
  branching keyed on model-chosen content.

### REQ-508: Exhausted bound is recorded truthfully and escalated — never fabricated as a success
**EARS**: WHEN both REQ-505's re-prompt bound and REQ-506's reroute bound are exhausted without a realized
earn-ledger line for the wake THE SYSTEM SHALL write a truthful ledger line (`kind` distinguishing this
outcome from a clean `wake`, e.g. `kind:'router_no_realized_action'`) — never a fabricated `profitable` or
success value — AND append one `harness-failures.jsonl` detail line via the existing
`appendHarnessFailure` mechanism (`index.mjs:458-475`, unmodified) so the existing self-heal escalation
path (mirrors `self/issue-dev`, `skills/self/earning-health.py`'s barren detector) can pick it up.
**Edge Cases**:
- This is expected to be RARE (menu has ≥1 always-eligible safe slot per REQ-502/503 in the common case);
  it is a legitimate, honestly-reported outcome, not a crash — the loop continues to its normal sleep
  interval afterward exactly as any other wake does.
**Acceptance Criteria**:
- A unit test asserts the escalation ledger line's `kind` is never `'wake'`/`'narrate'` and never carries
  `profitable:true` when no earn-ledger line exists.

### REQ-509: Money-safety caps and scope guards are never touched or bypassed
**EARS**: THE SYSTEM SHALL NOT modify, widen, relax, or route around any existing per-skill money-safety
guard — `skills/earn/sol-trade/run.sh`'s kill-switch (`KILL` file), identity-match guard, cumulative-loss
`earn-guard.mjs` check, `MAX_SPEND` hard override (`resolve-max-spend.sh`); `catalog-gate.mjs`'s
`BOOTSTRAP_RESERVE_USDC` threshold and fail-closed/fail-open defaults; nor any other skill's own guard —
this feature is strictly a selection/routing layer ABOVE unchanged execution guards, and "always act" is
never satisfied by forcing a guard-blocked or capped action through.
**Edge Cases**:
- REQ-506's reroute, when it fires because a guard legitimately blocked the first pick (kill-switch /
  identity-mismatch / cumulative-loss breach), routes to a DIFFERENT slot — it never retries the SAME
  blocked slot with a relaxed guard, and never disables the guard for the retry.
**Acceptance Criteria**:
- A unit test confirms no file under this feature's implementation writes to, reads for mutation, or
  imports with intent to modify `skills/earn/*/run.sh`, `skills/earn/*/lib/resolve-max-spend.sh`,
  `skills/_shared/lib/earn-guard.mjs`, or `catalog-gate.mjs`'s threshold constants.
- An integration-style test using real (unmodified) guard modules with a fixture forcing a guard-block on
  the first-picked slot asserts the reroute picks a different slot and the guard-blocked slot's own skip
  record is preserved verbatim in the ledger (not overwritten/silenced).

### REQ-510: Every wake's routing decision is ledgered for audit
**EARS**: WHEN always-act mode is engaged THE SYSTEM SHALL append, for every wake regardless of outcome, a
ledger line containing at minimum: `wake_id`, the final executed `slot` (or `null` if REQ-508 fired),
`args`, the number of reprompt/reroute attempts consumed (0, 1, or 2), and whether a realized earn-ledger
line was found — reusing the existing `formatRecord`/`safeAppend`/`LEDGER_PATH` machinery unmodified.
**Edge Cases**:
- Private-key redaction (`redactPrivateKeyPatterns`, PROP-020 in the existing codebase) is applied to this
  new line exactly as it already is to every other ledger line — no new redaction pass, no bypass.
**Acceptance Criteria**:
- A unit test asserts the new ledger fields appear on both the "resolved on first pick" and "resolved
  after reroute/reprompt" paths, and that `redactPrivateKeyPatterns` is applied before append.

### REQ-511: Non-functional — bounded cost and latency
**EARS**: THE SYSTEM SHALL bound the total extra model calls added by always-act enforcement to at most 1
per wake beyond the baseline single `think()` call — a single shared budget covering EITHER REQ-505's
reprompt OR REQ-506's reroute, never both in the same wake — so total `think()` calls per wake NEVER exceed
2 (1 baseline + at most 1 extra), and a pathological model response pattern can never turn one wake into an
unbounded retry loop or unbounded spend. (spec-review iteration-2 FIND-102 fix: this is the single,
unambiguous ceiling — 2 total, never 3 — that REQ-505's own acceptance criteria, REQ-506's own acceptance
criteria, `nextRerouteState`'s `maxAttempts = 1`, and PROP-511a all already assumed; the prior "at most 2 ...
beyond the baseline" framing is removed.)
**Edge Cases**:
- Both a no-tool-call AND a subsequent no-realized-action could theoretically compound; the bound is
  enforced as a single shared counter (`nextRerouteState`'s `maxAttempts = 1`) across both mechanisms within
  one wake, not two independent budgets — so the 2-total ceiling is never exceeded regardless of which
  failure mode(s) occur, and once the shared budget's one extra call is spent (by either a reprompt or a
  reroute), no further reprompt/reroute is attempted this wake — REQ-508 escalates instead.
**Acceptance Criteria**:
- A property test with an adversarial mocked brain that ALWAYS returns no-tool-call or ALWAYS returns a
  slot with no realized ledger line asserts total `think()` calls for that wake never exceed 2 (1 baseline +
  1 shared-budget extra call), never 3.

### REQ-512: A silently-OFF flag on a Franklin-identity wake is observable and distinguishable from "not yet enabled" (spec-review FIND-004 fix)
**EARS**: WHEN the identity check in REQ-501(a) resolves to Franklin AND REQ-501(b)'s flag is
unset/malformed/non-`"1"` (always-act therefore NOT engaged, per REQ-501's own fail-closed contract) THE
SYSTEM SHALL append, for that wake, a ledger line with `kind:'always_act_not_engaged'` and an explicit
`reason` field (`'flag_unset'` when the config key is absent, `'flag_malformed'` when present but not the
literal string `"1"`) — unconditionally, on EVERY such wake, not only after an intended go-live. Separately,
the one-time operational action that flips REQ-501(b)'s flag to `"1"` (already named in behavioral-spec.md
§6 item 10 as "a separate, explicit, logged operational action") SHALL itself append a ledger line with
`kind:'always_act_go_live'` (`ts`, and the config source it was set from) at the moment of that flip — this
is the anchor that makes "not yet enabled" (all `always_act_not_engaged` lines precede any `always_act_go_live`
line) distinguishable from "silently regressed to idle-permitted" (an `always_act_not_engaged` line appears
AFTER a recorded `always_act_go_live` line, meaning a config/deploy/`.env` bug flipped a previously-live
feature back off). A companion pure detector — mirroring `skills/self/earning-health.py::is_fresh_but_barren`'s
exact contract (pure, no I/O, takes a pre-gathered ledger tail, the doctrine-`'malware'` framing this feature
exists to catch) — returns "regression detected" iff the tail contains an `always_act_go_live` line followed
by at least `min_run` consecutive `always_act_not_engaged` lines for Franklin's identity with no intervening
`always_act_go_live`/engaged-wake line between them. `skills/self/earning-health.py` is this detector's
natural consumer/sibling (spec-review FIND-004's explicit routing target) — it is extended additively (a new
function alongside `is_fresh_but_barren`, not a modification of that function's existing contract).
**Edge Cases**:
- No `always_act_go_live` line exists yet in the tail (pre-rollout): any number of `always_act_not_engaged`
  lines is the expected, benign "not yet enabled" state — the detector returns "no regression," never a
  false escalation before the operator has ever turned the feature on.
- An `always_act_go_live` line is immediately followed by a SUCCESSFULLY engaged always-act wake (any
  `kind` other than `always_act_not_engaged` for a Franklin wake): the regression run resets to zero: a
  single blip does not escalate; only a SUSTAINED run (≥ `min_run`, mirroring `is_fresh_but_barren`'s
  `min_run=20` discipline) after go-live escalates.
- REQ-501(a)'s identity check itself failing (derivation error/empty/mismatch) is explicitly OUT of REQ-512's
  scope — REQ-512 only fires for a CONFIRMED Franklin identity; a non-Franklin instance never writes
  `always_act_not_engaged` lines at all (REQ-501's own cross-instance no-op guarantee is unaffected).
**Acceptance Criteria**:
- A unit test asserts a Franklin-identity wake with the flag unset appends `kind:'always_act_not_engaged',
  reason:'flag_unset'`; with the flag set to a non-`"1"` string, `reason:'flag_malformed'`.
- A unit test asserts the go-live operational action appends `kind:'always_act_go_live'` exactly once at
  the flip, never on any other wake.
- A unit test for the companion detector asserts: (a) `always_act_not_engaged` lines with no preceding
  `always_act_go_live` line never trigger regression-detected; (b) `always_act_go_live` followed by
  `min_run` consecutive `always_act_not_engaged` lines DOES trigger regression-detected; (c) a single
  `always_act_not_engaged` line surrounded by successfully-engaged wakes after go-live does NOT trigger it.

### REQ-513: A fabricated `slot:"sleep"` (or any off-menu slot) is rejected by the REAL wake-loop dispatch, not just absent from the schema (spec-review FIND-103 fix)
**EARS**: WHEN always-act mode is engaged (`ctx.alwaysActEngaged === true`) AND `parseToolCall(rawResponse)`
resolves a non-null `{ slot, args }` THE SYSTEM SHALL, before `index.mjs`'s existing `if (slot === 'sleep')`
branch (`index.mjs:402-416`, unconditional string check) can fire, check whether `slot === 'sleep'` OR
`slot` is not a member of `ctx.alwaysActMenu` (the offered enum for this wake); IF EITHER IS TRUE THE SYSTEM
SHALL NOT execute the existing `sleep`/narrate branch and SHALL NOT execute the resolved `slot` as a skill —
instead it SHALL treat this exactly as a no-tool-call outcome for REQ-505's bounded-reprompt path (a stray
off-menu/`"sleep"` slot consumes the SAME shared retry budget REQ-511 defines, it does not grant an extra
attempt). Concretely: `index.mjs`'s existing `if (slot === 'sleep')` branch (`index.mjs:402-416`) becomes
conditional — `if (slot === 'sleep' && !ctx.alwaysActEngaged)` — and a new guard immediately ahead of skill
execution (covering both the fabricated-`"sleep"` case and any other off-menu slot) reroutes into REQ-505's
reprompt handling when `ctx.alwaysActEngaged && (slot === 'sleep' || !ctx.alwaysActMenu.includes(slot))`.
**Edge Cases**:
- A non-always-act wake (`ctx.alwaysActEngaged` falsy) is completely unaffected — `index.mjs:402-416`'s
  `sleep` branch fires exactly as it does today, byte-for-byte, since the new guard only activates when
  `ctx.alwaysActEngaged === true`.
- The fabricated slot arrives on the LAST allowed attempt (REQ-511's shared budget already exhausted): this
  is not a fresh no-tool-call needing its own new retry — it is folded into whichever bound (REQ-505's
  reprompt or REQ-506's reroute) is currently in flight, and if that bound is already exhausted, REQ-508's
  truthful escalation fires immediately, never a silent idle/narrate/sleep outcome.
- A weak/free model repeatedly fabricating `slot:"sleep"` across the bounded retry: this consumes the SAME
  ≤1-extra-call shared budget as any other no-tool-call/no-realized-action failure mode (REQ-511) — it
  cannot be used to multiply the number of `think()` calls beyond REQ-511's ceiling.
**Acceptance Criteria**:
- A unit test that feeds a mocked `think()` response which `parseToolCall` resolves to exactly
  `{ slot: 'sleep', args: {} }` while `ctx.alwaysActEngaged === true` asserts: (a) the existing
  `sleep`/narrate ledger line (`kind:'narrate', note:'agent chose to sleep'`) is NEVER written, (b) no skill
  execution is attempted for `slot:'sleep'`, and (c) the wake proceeds into REQ-505's reprompt path (a
  second `think()` call occurs, bounded by REQ-511). This is the direct regression test for spec-review
  FIND-103.
- The SAME test structure with a fabricated slot that is a syntactically valid string but absent from
  `ctx.alwaysActMenu` (e.g. `slot: 'report'`, a real registry slot excluded from the always-act menu by
  REQ-502) asserts identical rejection-and-reprompt behavior.
- A unit test with `ctx.alwaysActEngaged` falsy/absent and `slot: 'sleep'` asserts today's existing behavior
  is preserved byte-for-byte: the `kind:'narrate'` sleep ledger line IS written, no reprompt is triggered.

## 3. Edge Case Catalog (cross-cutting)

- **Empty inputs**: empty registry, empty `activeSkillSlots`, empty earn-ledger file → REQ-502's
  empty-menu failure (REQ-508), never a crash.
- **Boundary values**: `balanceUsdc === BOOTSTRAP_RESERVE_USDC` exactly (at-or-above per
  `catalog-gate.mjs`'s existing `isBelowThreshold` semantics, unmodified) → full unfiltered menu.
- **Concurrent access**: two wakes for the same identity should not run concurrently (existing loop
  contract, `index.mjs` is a single sequential wake loop) — this feature adds no new concurrency; a
  concurrent second process is out of scope (pre-existing invariant, not re-verified here).
- **Error conditions**: identity-derivation subprocess crash/timeout, registry.json malformed JSON,
  earn-ledger.jsonl malformed trailing line (mirrors `earn-detect.mjs`'s own existing fail-soft JSON.parse
  guard) — all fail closed to "always-act NOT engaged" or "reroute/escalate", never a silent success.
- **Silent post-go-live reversion to idle-permitted** (spec-review FIND-004): a Franklin-identity wake with
  REQ-501(b)'s flag unset/malformed occurring AFTER the one-time go-live operational action has already
  fired is the doctrine-`'malware'` condition (§0) — this is NOT the same as the benign pre-rollout "not yet
  enabled" state, and both MUST be distinguishable from the ledger alone (REQ-512), not merely inferable
  from operator memory of when the flag was flipped.
- **Fabricated off-menu/`"sleep"` tool call** (spec-review iteration-2 FIND-103): a model emits
  `slot:"sleep"` or any slot absent from `ctx.alwaysActMenu` despite the schema truly not offering it (a
  realistic risk for weak/free models, per §1's `parse-tool-call.mjs` scavenge-parser evidence) — REQ-513
  rejects it at the REAL `index.mjs:402-416` dispatch point and routes it into REQ-505/511's bounded
  reprompt path; it is NEVER silently honored as an idle/sleep outcome, closing the structural bypass that
  would otherwise defeat REQ-504/505/506's entire purpose.
- **Reroute pressures a second capital-risking attempt** (spec-review iteration-2 FIND-101): a legitimate,
  doctrine-sanctioned no-edge WAIT (e.g. `earn/sol-trade`'s baseline strategy) triggers REQ-506's reroute —
  the reroute target set is hard-filtered to `risk:"safe"` slots only (`isMarketRiskFree`); it NEVER offers
  `earn/sol-trade`, `earn/polymarket-trade`, `hl_trade`, `token_launch`, or `yield` as a reroute target, and
  an empty risk-free set escalates (REQ-508) rather than falling back to a capital-risking slot.

## 4. Non-Functional Requirements

- Performance: menu assembly and no-realized-action detection add O(1) additional file reads
  (one `earn-ledger.jsonl` scan already performed by the existing `classifyEarnResult` call for earn
  slots — no new I/O primitive introduced).
- Security: no new secrets, no new private-key handling; REQ-510 reuses existing redaction.
- Cost bound: REQ-511.

## 5. Test-Money Safety Rule (binding on Phase 2a/2b)

Tests for this feature MUST NEVER invoke real `skills/earn/*/run.sh`, the real `franklin-trading` CLI, or
any live wallet/network/x402 call. All skill execution, identity derivation, registry contents, and
earn-ledger contents MUST be injected via mocks/fixtures (dependency injection matching the existing
codebase convention — e.g. `hasOpenRiskPositionOfHlTrade`'s injected `queryFn`, `filterCatalog`'s injected
callbacks). A test that touches `~/.blockrun`, a real Solana RPC, or any real x402 payment is a spec
violation and must be rewritten with fixtures before it can pass Phase 2a/2b review.

## 6. Embedded VCSDD Task List (ordered)

1. Phase 1a (this file) — behavioral spec.
2. Phase 1b — verification-architecture.md (this feature's companion file).
3. Phase 1b review — fresh-context adversary spec review, blocking 0.
4. Phase 2a (RED) — write tests for REQ-501..REQ-513 against not-yet-existing pure functions
   (`isEarnActionSlot`, `assembleAlwaysActMenu`, `buildAlwaysActToolDefinitions`, `isMarketRiskFree`,
   `noRealizedAction`/reroute-bound helpers, the FIND-004 companion regression detector) + an
   index.mjs/brain.mjs-level integration test harness with mocked `think()`/`httpPost`/registry/earn-ledger
   (the REQ-504 wiring-seam test asserts the REAL outbound tool schema, not just the pure helper; the
   REQ-506 test asserts the REAL `index.mjs:450` call-site widening for `economy/gig`/`economy/lending` AND
   that the reroute enum excludes every `risk:"capital"` slot; the REQ-513 test asserts the REAL
   `index.mjs:402-416` dispatch rejects a fabricated `slot:'sleep'`/off-menu pick) — confirm all new tests
   FAIL, confirm regression baseline (existing `earn-slot.mjs`, `catalog-gate.mjs`, `context.mjs`,
   `prompt.mjs`, `brain.mjs`, `earn-detect.mjs`, `earning-health.py` test suites) still PASS.
5. Phase 2b (GREEN) — implement the pure core module(s) + wire the effectful shell changes into
   `index.mjs`/`brain.mjs`/`prompt.mjs` (additive, gated by REQ-501's identity+flag check so non-Franklin
   wakes and non-always-act wakes are byte-for-byte unaffected) — minimum code to pass, no premature
   optimization.
6. Phase 2c — refactor for clarity/duplication only; tests stay green; no new features.
7. Sprint contract (strict mode) — write `contracts/sprint-1.md` mapping CRIT-* to REQ-501..REQ-513
   before Phase 3 adversarial review.
8. Phase 3 — fresh-context adversary implementation review (Opus 4.8 per model-division table), blocking 0.
9. Phase 5 — verification harnesses in `verification/` executing the Tier 1/2 property obligations from
   verification-architecture.md.
10. `vcsdd-converge` — confirm all 4 dimensions (spec/test/impl/verification) agree; only then flip
    Franklin's live config flag (REQ-501(b)) — a separate, explicit, logged operational action, out of
    this feature's own test scope but gated by this feature's own default-OFF flag.

## Changelog

- **iteration-2 fixes: FIND-101/102/103** (spec-review iteration-2, this revision):
  - FIND-101 (money-safety): REQ-506's reroute target set is now hard-filtered to `risk:"safe"` slots only
    (`isMarketRiskFree`, sourced from `skills/registry.json`'s existing `risk` field) — a capital-risking
    slot is never offered as a reroute target; an empty risk-free set escalates (REQ-508) instead of
    falling back to a capital-risking slot. New edge cases + acceptance criteria added to REQ-506.
  - FIND-102 (completeness): REQ-511's EARS clause is rewritten to the single, unambiguous ceiling every
    other artifact already assumed — at most 1 extra `think()` call beyond baseline, 2 total per wake, never
    3 — removing the self-contradictory "at most 2 ... beyond the baseline" framing.
  - FIND-103 (ground-truth): REQ-504's false "already rejected today" claim about `index.mjs`'s `sleep`
    branch is removed; new REQ-513 makes the real `index.mjs:402-416` dispatch reject a fabricated
    `slot:'sleep'` or any off-menu slot while always-act is engaged, routing it into REQ-505's bounded
    reprompt path instead of silently honoring it as idle.
