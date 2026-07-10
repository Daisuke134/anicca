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
- `runtime/loop/index.mjs:440-456` + `runtime/loop/earn-detect.mjs:23-50` — `classifyEarnResult(wakeId,
  earnLedgerPath, isProfitableFn)` already reads `earn-ledger.jsonl`, finds the line keyed by
  `line.wake === wakeId` (never last-line position), and returns `{ profitable, earnLine }`; `earnLine ===
  null` means **no realized economic result was recorded for this wake** — this is the existing,
  skill-agnostic primitive this feature reuses to detect a no-op earn pick (REQ-506).
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
  **separate, wider, purely-additive** predicate (`isEarnActionSlot`, REQ-502) for router-menu purposes
  only — `isEarnSlot` itself is NOT modified (it is relied on elsewhere, `index.mjs:450`, for ledger
  profitability attribution, and changing its contract is out of scope and would risk regressing that
  unrelated behavior).
- `skills/registry.json` — single source of truth for live/declared status and per-slot `risk`/`summary`.
  Relevant earn-action slots today (status `"live"`): `yield`, `hl_trade`, `x402_sell`, `token_launch`,
  `economy/gig`, `economy/lending`, `earn/clip`, `earn/clip-producer`, `earn/video`, `earn/sol-trade`,
  `earn/polymarket-trade`. Utility/exploration slots explicitly **excluded** from the router's mandatory
  menu: `report`, `cook`, `self/spawn`, `self/spawn-child`, `self/issue-dev`, `self/coordinate`,
  `economy/ubi`, `earn/audit` (status `"declared"`, not live), `earn/_probe` (status `"declared"`), `earn`
  (retired placeholder, status `"declared"`).
- `skills/earn/sol-trade/run.sh:28-41` — the **identity-match guard idiom** this feature's Franklin-gate
  reuses verbatim (REQ-501): derive `OWN_WALLET` via `runtime/wallet-address-solana.mjs` under the current
  `ANICCA_HOME`, derive `CLI_WALLET` under `ANICCA_HOME="$HOME/.blockrun"`, and only proceed when they are
  equal and non-empty. Fail-closed (empty/mismatched → do not proceed) is the existing convention.
- `skills/self/earning-health.py` — the existing barren-loop detector. It explicitly (by design,
  docstring lines 12-22) treats a long run of `action:"live-pass"` WAITs inside sol-trade as **healthy**
  (a legitimate sub-agent judgment call), and only a run of identical `action:"skip"` reasons as barren.
  This feature does not change that detector's semantics; it operates one layer up (the router's own
  MUST-pick-a-realized-action-or-reroute layer, REQ-506/REQ-507), and its own escalation (REQ-508) is
  additive to, not a replacement for, `earning-health.py`.

## 2. Purity Boundary Analysis (summary; full map in verification-architecture.md)

- **Pure core (new)**: menu assembly, earn-action classification, no-realized-action detection, reroute
  bounding, MUST-ACT prompt/tool-definition construction — all deterministic transforms over
  already-loaded data (registry, ctx, earn-ledger line), no I/O, mirrors the existing purity split
  (`context.mjs`, `prompt.mjs`, `tier.mjs`, `catalog-gate.mjs`, `earn-slot.mjs` are pure today).
- **Effectful shell (extended, not replaced)**: `runtime/loop/index.mjs`'s wake loop (the reroute retry
  orchestration, ledger appends, escalation writes), the identity-derivation subprocess calls
  (`wallet-address-solana.mjs` under two `ANICCA_HOME` values, exactly as `sol-trade/run.sh` already
  does), and the unchanged skill execution + money-safety guards inside each skill's own `run.sh`.

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

### REQ-504: `sleep` tool is withheld on an always-act-engaged wake
**EARS**: WHEN always-act mode is engaged for a wake THE SYSTEM SHALL build the tool definitions for that
wake WITHOUT the `sleep` tool (`runtime/loop/prompt.mjs::SLEEP_TOOL`) — the only callable tool is
`run_skill`, with its `slot` enum constrained to REQ-503's filtered earn-action menu.
**Edge Cases**:
- A model response that nonetheless attempts `slot: "sleep"` or any slot outside the enum (a
  spec/tool-contract violation by the model, not the harness) is rejected the same way an invalid enum
  value is already rejected today, and is treated as a no-tool-call outcome for REQ-505's purposes.
**Acceptance Criteria**:
- `getToolDefinitions` (or its always-act variant) called with always-act engaged returns a tool array of
  length 1 (`run_skill` only), whose `slot.enum` equals REQ-503's filtered menu.

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

### REQ-506: A picked earn slot with no realized economic result triggers a bounded same-wake reroute
**EARS**: WHEN always-act mode is engaged AND the model picks a slot from the earn-action menu AND that
slot's execution completes (any exit code) AND `classifyEarnResult(wakeId, earnLedgerPath,
isProfitableFn).earnLine === null` (`runtime/loop/earn-detect.mjs`, unmodified — this is true for both a
guard-triggered `action:"skip"` and a sub-agent's own neutral-signal WAIT with no ledger line, per §1)
THE SYSTEM SHALL treat this as "no realized action this wake" and re-invoke the brain exactly once more,
with the just-picked slot temporarily excluded from the enum (reusing the existing `avoidSlot`
diversification mechanism, `index.mjs:179-421`) so the model must choose a DIFFERENT earn-menu slot,
bounded to `MAX_REROUTES = 1`.
**Edge Cases**:
- A slot execution that DOES write an earn-ledger line for this wake (`earnLine !== null`) — whether
  `profitable` is `true` or `false` (a real, recorded loss still counts as a realized economic action, not
  a no-op) — is accepted immediately; no reroute.
- The rerouted second pick ALSO produces `earnLine === null`: the bound is exhausted — proceed to REQ-508
  (truthful record + escalate), never a third same-wake attempt.
- The menu has exactly one remaining slot after excluding the first pick (e.g. reserve-filtered down to
  one): the model is still re-prompted with that reduced (possibly single-member) enum; if it is forced to
  repick the same slot because none other qualifies, `avoidSlot`'s existing "only clears when a DIFFERENT
  slot is picked" semantics naturally surfaces this as still-unresolved, falling through to REQ-508.
- This reroute is NEVER triggered by a slot execution that itself errors/times out (`skillResult.timedOut`
  / `skillResult.notFound` / non-zero exit for a NON-earn-guard reason) in a way that bypasses REQ-508's
  existing `appendHarnessFailure` mechanism (`index.mjs:458-475`) — that mechanism is unmodified and fires
  independently.
**Acceptance Criteria**:
- A unit test with a fixture earn-ledger containing no line for `wakeId` after executing the first-picked
  slot asserts a second `think()` call occurs with that slot excluded from the enum, and if the second
  pick's ledger fixture DOES contain a matching line, the wake terminates there (no third call).

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
**EARS**: THE SYSTEM SHALL bound the total extra model calls added by always-act enforcement to at most 2
per wake beyond the baseline single `think()` call (REQ-505's 1 reprompt + REQ-506's 1 reroute — these are
mutually exclusive triggers within a single wake pass in the common case, so the practical worst case is 1
extra call, not 2, but the hard ceiling asserted by tests is 2), so a pathological model response pattern
can never turn one wake into an unbounded retry loop or unbounded spend.
**Edge Cases**:
- Both a no-tool-call AND a subsequent no-realized-action could theoretically compound; the bound is
  enforced as a single shared counter across both mechanisms within one wake, not two independent budgets.
**Acceptance Criteria**:
- A property test with an adversarial mocked brain that ALWAYS returns no-tool-call or ALWAYS returns a
  slot with no realized ledger line asserts total `think()` calls for that wake never exceed 2.

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
4. Phase 2a (RED) — write tests for REQ-501..REQ-511 against not-yet-existing pure functions
   (`isEarnActionSlot`, `assembleAlwaysActMenu`, `buildAlwaysActToolDefinitions`,
   `noRealizedAction`/reroute-bound helpers) + an index.mjs-level integration test harness with mocked
   `think()`/registry/earn-ledger — confirm all new tests FAIL, confirm regression baseline (existing
   `earn-slot.mjs`, `catalog-gate.mjs`, `context.mjs`, `prompt.mjs`, `earn-detect.mjs` test suites) still
   PASS.
5. Phase 2b (GREEN) — implement the pure core module(s) + wire the effectful shell changes into
   `index.mjs`/`brain.mjs`/`prompt.mjs` (additive, gated by REQ-501's identity+flag check so non-Franklin
   wakes are byte-for-byte unaffected) — minimum code to pass, no premature optimization.
6. Phase 2c — refactor for clarity/duplication only; tests stay green; no new features.
7. Sprint contract (strict mode) — write `contracts/sprint-1.md` mapping CRIT-* to REQ-501..REQ-511
   before Phase 3 adversarial review.
8. Phase 3 — fresh-context adversary implementation review (Opus 4.8 per model-division table), blocking 0.
9. Phase 5 — verification harnesses in `verification/` executing the Tier 1/2 property obligations from
   verification-architecture.md.
10. `vcsdd-converge` — confirm all 4 dimensions (spec/test/impl/verification) agree; only then flip
    Franklin's live config flag (REQ-501(b)) — a separate, explicit, logged operational action, out of
    this feature's own test scope but gated by this feature's own default-OFF flag.
