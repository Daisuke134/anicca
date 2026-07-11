# Behavioral Spec — franklin-alwaysact-skill-router

> **MAINTENANCE NOTE (2026-07-11, mechanical citation audit)**: Line-number citations in this document
> are pinned to commit `f3c27de9` + the mechanical citation-audit fix that follows it (see Changelog).
> Every `index.mjs:<N>` / `prompt.mjs:<N>` / `brain.mjs:<N>` / `run.sh:<N>` citation below was
> independently re-verified against the real files at that commit (grep for the literal quoted
> code/comment string, never re-read from memory of where it "should" be) — see
> `.vcsdd/features/franklin-alwaysact-skill-router/evidence/citation-audit-2026-07-11.md` for the full
> audit table. **Re-audit mechanically after any further code change** — a Phase 2b/2c edit that inserts
> or removes lines anywhere above a cited line silently invalidates that citation without changing the
> underlying claim's truth, exactly as happened 3 times running across converge iterations 1→2→3
> (FIND-001..007).

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

- **(converge doc-sync 2026-07-11 mechanical citation audit correction)** `runtime/loop/index.mjs:533-546`
  (no-tool-call) and `index.mjs:551-564` (sleep) — the TWO existing idle paths this feature must close for
  the gated identity: (a) `parseToolCall(rawResponse)` returns falsy → a `kind:'narrate'` ledger line is
  written and the wake ends with no skill executed (`index.mjs:533-546`); (b) the model calls the `sleep`
  tool → a `kind:'narrate'` line (`note: args.reason || 'agent chose to sleep'`) is written and the wake
  ends with no skill executed (`index.mjs:551-564`, the `note:` field literally at `index.mjs:559`).
- **(converge doc-sync 2026-07-11 correction)** `runtime/loop/prompt.mjs:10-24` (`SLEEP_TOOL` object
  literal) `,144-180` (`getToolDefinitions`) — `SLEEP_TOOL` is unconditionally appended (`prompt.mjs:178`)
  to every tool definition list (`getToolDefinitions`), so the model always has a legal "do nothing" choice.
- **The REAL wiring seam from ctx to the outbound tool schema (spec-review FIND-001/FIND-005 ground
  truth; converge doc-sync 2026-07-11 line-number correction)**: `runtime/loop/brain.mjs:66` (`thinkProxy`,
  inside the function starting at `brain.mjs:48`) hardcodes `tools: getToolDefinitions(ctx.
  activeSkillSlots)` as the literal `tools` field of the HTTP request body sent to the model, and
  `runtime/loop/brain.mjs:100-102` (`thinkClaudeP`, function starting at `brain.mjs:89`) hardcodes the
  prompt-text instruction ternary whose with-sleep branch (`brain.mjs:102`) reads `'Respond with a JSON
  tool_calls block using run_skill or sleep.'`. `getToolDefinitions(slots)` (`prompt.mjs:144-180`) has no
  parameter for omitting `SLEEP_TOOL` — it is appended unconditionally at `prompt.mjs:178` for every call,
  including any call this feature makes. There is therefore NO existing seam by which REQ-504's sleep-omission
  can reach the model without: (a) `prompt.mjs::getToolDefinitions` gaining an additive, backward-compatible
  optional second parameter (`opts.omitSleep`, default `false`) that all other existing call sites never
  pass and are therefore byte-for-byte unaffected by, and (b) `brain.mjs`'s two `tools:`/prompt-text call
  sites becoming conditional on a new `ctx.alwaysActEngaged` boolean (set by REQ-501's gate) and
  `ctx.alwaysActMenu` (set by REQ-502/503's filtered menu). Both `prompt.mjs` and `brain.mjs` ARE modified by
  this feature — see the corrected Purity Boundary Map in verification-architecture.md and REQ-504 below.
- **(converge doc-sync 2026-07-11 correction — this bullet cited the wrong `index.mjs` range for two
  converge iterations running, undiscovered until this mechanical sweep: `index.mjs:440-456` is actually
  the bootstrap-reserve `hasOpenRiskPositionOf`/`filterCatalog` block, unrelated to `classifyEarnResult`)**
  `runtime/loop/earn-detect.mjs:23-50` — `classifyEarnResult(wakeId,
  earnLedgerPath, isProfitableFn)` already reads `earn-ledger.jsonl`, finds the line keyed by
  `line.wake === wakeId` (never last-line position), and returns `{ profitable, earnLine }`; `earnLine ===
  null` means **no realized economic result was recorded for this wake** — this is the existing,
  skill-agnostic primitive this feature reuses to detect a no-op earn pick (REQ-506). **Ground-truth
  correction (spec-review FIND-002; converge doc-sync 2026-07-11 re-correction, see FIND-005)**:
  `classifyEarnResult` is CALLED from TWO structurally separate call sites, in two separate functions —
  `index.mjs:598`'s `} else if (isEarnSlot(slot)) {` branch inside the legacy `runOneWake` (unconditional,
  never reads `ctx.alwaysActEngaged`, unreachable for an always-act-engaged wake because of the
  `index.mjs:516-518` early return), and `index.mjs:754`'s `else if (isEarnActionSlot(slot)) {` branch
  inside the dedicated `runAlwaysActWake` — the CALL-SITE gate, not `classifyEarnResult` itself, is what
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
  that unrelated behavior) — but per the correction above, its CALL SITES (`index.mjs:598` legacy,
  `index.mjs:754` always-act — converge doc-sync 2026-07-11 correction, see FIND-005) ARE additively
  widened for always-act-engaged wakes only (REQ-506): `index.mjs:754`'s `else if (isEarnActionSlot(slot))`
  inside `runAlwaysActWake` REPLACES `index.mjs:598`'s `else if (isEarnSlot(slot))` for that codepath (the
  two are separate call sites in separate functions, never a single in-place ternary — see REQ-506). Any
  non-always-act wake (`ctx.alwaysActEngaged` falsy — every non-Franklin instance,
  and Franklin herself whenever the flag is off) evaluates `isEarnSlot(slot)` at `index.mjs:598` exactly as
  today, byte-for-byte, because `index.mjs:516-518`'s early return never diverts it into `runAlwaysActWake`.
- **`avoidSlot`'s real semantics (spec-review FIND-003 ground truth; converge doc-sync 2026-07-11 line-number
  correction, see FIND-006)**: `index.mjs:296`'s `let avoidSlot = null;` declaration (intro comment at
  `index.mjs:294-295`) mechanism is, by its own inline comment (`index.mjs:302`), a SOFT, prompt-text-only
  nudge — `"the agent's choice is never blocked, only the enforced pause after ignoring it grows"` —
  surfaced purely as prose in `buildUserMessage` (`prompt.mjs:212-214`, the FORBIDDEN text literally on
  `prompt.mjs:213`: `"⛔ ... it is FORBIDDEN this wake. Pick a DIFFERENT slot."`). It
  NEVER touches `getToolDefinitions`'s `slot.enum` and therefore never structurally prevents a re-pick.
  REQ-506's reroute does **NOT** reuse `avoidSlot` or claim enum-level exclusion through it. Instead, because
  REQ-504 already constructs the always-act tool schema from an explicit, harness-controlled array
  (`buildAlwaysActToolDefinitions(menuSlots)`), REQ-506's reroute performs a genuine, purpose-built hard
  array filter — `buildAlwaysActToolDefinitions(menuSlots.filter(s => s !== pickedSlot && isMarketRiskFree(s)))`
  (spec-review iteration-2 FIND-101 correction: the filter also excludes every `risk:"capital"` slot, not
  merely the just-picked one — see REQ-506) — before the re-invocation, so the just-picked slot AND every
  capital-risking slot are truly absent from the schema the model receives. `avoidSlot` /
  `index.mjs:293-425`'s loop-detect diversification block (state declared `293-305`, the
  isLooping-triggered set/sleep block `405-425`) remains completely unmodified and continues to operate
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
  docstring lines 14-22 — spec-review iteration-4 citation correction; lines 12-13 are general
  doctrine-framing prose, not the skip-vs-live-pass mechanism definition itself) treats a long run of
  `action:"live-pass"` WAITs inside sol-trade as **healthy**
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
  bounding, MUST-ACT prompt/tool-definition construction, AND — **spec-review iteration-4 FIND-301
  correction** — the SINGLE `attemptsUsed ∈ {0, 1}` attempt-state machine (`nextRerouteState`) that is the
  SOLE arbiter of every REQ-505/506/513 retry/reroute/escalation branch decision (never `currentOfferedSlots`
  array identity, which lives in the pure core only as a per-attempt VALIDITY input to
  `isRejectableSleepOrOffMenu`, with no branch-selection role) — all deterministic transforms over
  already-loaded data (registry, ctx, earn-ledger line), no I/O, mirrors the existing purity split
  (`context.mjs`, `prompt.mjs`, `tier.mjs`, `catalog-gate.mjs`, `earn-slot.mjs` are pure today).
- **Effectful shell (extended, not replaced)**: `runtime/loop/index.mjs`'s wake loop (the reroute retry
  orchestration — **its own local `attemptsUsed` variable is the ONLY thing the shell threads to decide
  which of REQ-505/506/508 fires next; `currentOfferedSlots` is threaded separately, purely for REQ-513's
  validity check** — ledger appends, escalation writes, and — spec-review FIND-002 correction; converge
  doc-sync 2026-07-11 line-number correction, see FIND-005 — the classify call-site gate additively widens
  from `index.mjs:598`'s legacy `else if (isEarnSlot(slot))` (inside `runOneWake`, unreachable for an
  engaged wake) to `index.mjs:754`'s `else if (isEarnActionSlot(slot))` (inside `runAlwaysActWake`) — two
  separate call sites in two separate functions, never a single in-place ternary), the identity-derivation subprocess
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
   (`string[]`, REQ-502/503's filtered menu — only populated when `alwaysActEngaged` is true). **Spec-review
   FIND-201 correction**: `ctx.alwaysActMenu` is the STATIC, full-wake menu only — it is NEVER itself the
   reference REQ-513's dispatch guard checks a parsed slot against once a reroute is in flight; see REQ-513's
   `currentOfferedSlots` for the per-attempt reference this fix introduces.
2. `runtime/loop/prompt.mjs::getToolDefinitions(slots, opts)` gains an additive, optional second parameter
   `opts = { omitSleep: false }` (default preserves every existing call site's exact current output,
   byte-for-byte). When `opts.omitSleep === true`, the returned array omits `SLEEP_TOOL` (the pure function
   `buildAlwaysActToolDefinitions(menuSlots)` in the pure core is a thin wrapper:
   `getToolDefinitions(menuSlots, { omitSleep: true })` — NOT a parallel reimplementation).
3. `brain.mjs:66` (`thinkProxy`, converge doc-sync 2026-07-11 line-number correction)'s `tools:` line
   becomes:
   `tools: getToolDefinitions(ctx.alwaysActEngaged ? ctx.alwaysActMenu : ctx.activeSkillSlots, { omitSleep:
   ctx.alwaysActEngaged === true })` — a non-always-act `ctx` (the overwhelming majority of wakes, every
   non-Franklin instance) produces the exact current call, unchanged.
4. `brain.mjs:100-102` (`thinkClaudeP`, converge doc-sync 2026-07-11 line-number correction)'s prompt-text
   instruction ternary conditionally drops the sleep mention (`brain.mjs:102`'s with-sleep branch) when
   `ctx.alwaysActEngaged` is true (`'Respond with a JSON tool_calls block using run_skill.'` instead of
   `'... using run_skill or sleep.'`), so the text-mode brain path is not left silently inconsistent with the
   tool-schema path.
5. **(spec-review FIND-201 fix)** The slot array passed as the FIRST argument to
   `getToolDefinitions`/`buildAlwaysActToolDefinitions` in whichever call site is active for a GIVEN
   `think()` attempt — step 3's `ctx.alwaysActMenu` for the baseline attempt, or REQ-506's
   `menuSlots.filter(...)` for a reroute attempt — IS, by definition, the enum actually offered to the model
   for THAT attempt. `index.mjs`'s retry loop threads this exact same array through as its own local
   `currentOfferedSlots` variable for that attempt (distinct from, and never reassigned back into, the
   static `ctx.alwaysActMenu`), so REQ-513's dispatch guard (below) always validates a parsed response
   against what was ACTUALLY offered for the attempt that produced it — never against the static, full-wake
   `ctx.alwaysActMenu` once a reroute has narrowed the offered schema. **(spec-review iteration-4 FIND-301
   correction — `currentOfferedSlots`'s role is now explicitly bounded)** `currentOfferedSlots` is used
   SOLELY for this per-attempt VALIDITY check (is the parsed `slot` a legal member of what was actually
   offered this attempt) — it plays NO role in deciding WHICH recovery branch (REQ-505's reprompt, REQ-506's
   reroute, or REQ-508's escalation) a rejected/invalid outcome routes into. That branch selection is decided
   EXCLUSIVELY by REQ-511's shared `attemptsUsed` attempt-state, because a REQ-505 reprompt attempt's
   `currentOfferedSlots` is array-IDENTICAL to the baseline attempt's (`ctx.alwaysActMenu`, since a reprompt
   never narrows the schema — only a REQ-506 reroute does) — any rule that tried to infer "is this the
   baseline attempt" from `currentOfferedSlots` identity would misclassify a reprompt attempt as baseline
   (this was iteration-3's own latent bug, FIND-301). See REQ-511/REQ-513 for the corrected, identity-free
   branch-selection rule.
The only callable tool in always-act mode is therefore `run_skill`, with its `slot` enum constrained to
REQ-503's filtered earn-action menu (or, on a reroute attempt, REQ-506's further-narrowed risk-free set).
**Edge Cases**:
- A model response that nonetheless attempts `slot: "sleep"` or any slot outside the enum (a
  spec/tool-contract violation by the model, not the harness — the schema truly does not offer it) is NOT
  auto-rejected by any pre-existing enum-validation step (spec-review FIND-103 correction: no such step
  exists in `index.mjs`'s real wake loop today — `parseToolCall` performs no cross-check against the offered
  `tools` array, and the existing `if (slot === 'sleep')` branch at `index.mjs:551` is a bare string
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

### REQ-505: A no-tool-call (text-only) response is not accepted as the wake's terminal outcome — gated by REQ-511's shared attempt-state, never by array identity (spec-review iteration-4 FIND-301 fix)
**EARS**: WHEN always-act mode is engaged AND `parseToolCall(rawResponse)` returns falsy for a given
`think()` attempt THE SYSTEM SHALL consult REQ-511's shared attempt-state, `attemptsUsed ∈ {0, 1}` — the
SOLE arbiter of every retry/reroute/escalation branch across REQ-505/506/511/513 (spec-review iteration-4
FIND-301 fix; NEVER `currentOfferedSlots`/`ctx.alwaysActMenu` array identity). IF `attemptsUsed === 0` THE
SYSTEM SHALL NOT write the existing `kind:'narrate'` no-op ledger line as the wake's terminal state; instead
it SHALL re-invoke the brain exactly once more within the same wake with a strengthened MUST-ACT
reinforcement message (reusing `buildUserMessage`'s existing steer-composition pattern, appending one
additional directive line), offering the SAME `currentOfferedSlots` the attempt that just returned no tool
call was offered (`ctx.alwaysActMenu` for a baseline-attempt no-tool-call), and set `attemptsUsed = 1`. IF
`attemptsUsed === 1` ALREADY (the shared budget was already spent this wake by an EARLIER retry — a prior
reprompt, a prior reroute, or a prior REQ-513 rejection), THE SYSTEM SHALL NOT re-invoke `think()` for this
outcome; it SHALL proceed DIRECTLY to REQ-508's truthful escalation.
**Edge Cases**:
- The re-prompt also returns no tool call: at that point `attemptsUsed === 1` (the reprompt itself was the
  one shared extra call), so this proceeds DIRECTLY to REQ-508 — never a third silent retry (cost/latency
  bound). This is a specific instance of the general `attemptsUsed===1 → escalate` rule above, not a
  REQ-505-specific rule.
- **(spec-review iteration-4 FIND-301 fix — the finding this revision closes)** The re-prompt itself
  (attempt #2, invoked because attempt #1 had `attemptsUsed===0` and returned no tool call) returns a
  fabricated/off-menu slot (e.g. `slot:'sleep'`) instead of no tool call at all: this is REQ-513's rejection
  case, evaluated at `attemptsUsed===1` (the reprompt already consumed the shared budget), so it routes
  DIRECTLY to REQ-508's escalation — NEVER back into this requirement's reprompt path a second time.
  Iteration-3's revision mis-specified this by branching on whether `currentOfferedSlots === ctx.alwaysActMenu`
  (REQ-513's then-current "is this the BASELINE attempt" test) — a REQ-505 reprompt attempt's
  `currentOfferedSlots` also equals `ctx.alwaysActMenu` (a reprompt never narrows the schema), so that test
  misclassified this exact scenario as a fresh baseline attempt and would have issued a SECOND reprompt (a
  THIRD `think()` call), violating REQ-511. This revision removes ALL array-identity-based branch selection;
  `attemptsUsed` alone decides. See the transition-matrix row "no-tool-call→reprompt→fabricated-slot→ESCALATE"
  (§2.5) and PROP-513e.
- The re-prompt costs one additional model call — this is accepted as intentional harness behavior (bounded
  to 1 total across REQ-505/506/513 combined, per REQ-511's single shared counter), matching this feature's
  money-safety framing (a bounded retry cost is preferable to a wasted, unproductive wake).
**Acceptance Criteria**:
- A unit test with a mocked `think()` that first returns no tool call then a valid `run_skill` call
  asserts exactly 2 `think()` invocations, the second's chosen slot is executed, and `attemptsUsed`
  transitions `0 → 1` at the reprompt.
- A unit test with a mocked `think()` that never returns a tool call asserts exactly 2 `think()`
  invocations total (not more) and the wake ends in REQ-508's escalation path.
- **(spec-review iteration-4 FIND-301 regression test, PROP-513e — see REQ-513/verification-architecture.md)**
  A unit test with a mocked `think()` sequence `[no-tool-call, {slot:'sleep', args:{}}]` (the reprompt
  attempt itself returning a fabricated slot) asserts: (a) exactly 2 `think()` calls total, never 3, (b) no
  skill execution is attempted, (c) the wake proceeds DIRECTLY into REQ-508's escalation, (d) `attemptsUsed`
  is `1` (not `0`) at the moment the fabricated slot is evaluated — proving the reprompt attempt's rejection
  is never misclassified as a fresh baseline attempt merely because its `currentOfferedSlots` also equals
  `ctx.alwaysActMenu`.

### REQ-506: A picked earn slot with no realized economic result triggers a bounded same-wake reroute, via a genuine hard tool-enum exclusion, to a market-risk-free slot only
**EARS**: WHEN always-act mode is engaged AND the model picks a slot `s` from the earn-action menu AND `s`'s
execution completes (any exit code) THE SYSTEM SHALL first determine whether `s` is classify-eligible using
the SAME always-act-gated predicate REQ-502 defines for menu membership — `isEarnActionSlot(s)` (the wider,
additive predicate covering `economy/gig` and `economy/lending` in addition to every `isEarnSlot` member) —
not the narrower `isEarnSlot(s)` that gates classification on a non-always-act wake. Concretely (spec-review
FIND-002 fix; converge doc-sync 2026-07-11 line-number correction, see FIND-005 — the shipped mechanism is
TWO separate call sites, never a single in-place ternary): `index.mjs:754`'s classify call-site condition
inside `runAlwaysActWake`, `else if (isEarnActionSlot(slot))`, is what an always-act-engaged wake reaches
(REPLACING, for that codepath only, `index.mjs:598`'s legacy `else if (isEarnSlot(slot))` inside
`runOneWake`, which stays byte-for-byte unconditional and is unreachable for an engaged wake because of the
`index.mjs:516-518` early return) — so `classifyEarnResult` IS invoked for an `economy/gig` or
`economy/lending` pick on an always-act-engaged wake, exactly as it already is for any `isEarnSlot` member.
THE SYSTEM SHALL then, IF `classifyEarnResult(wakeId, earnLedgerPath, isProfitableFn).earnLine === null`
(`runtime/loop/earn-detect.mjs`, unmodified — true for both a guard-triggered `action:"skip"` and a
sub-agent's own neutral-signal WAIT with no ledger line, per §1), treat this as "no realized action this
wake" and consult REQ-511's shared attempt-state, `attemptsUsed ∈ {0, 1}` (spec-review iteration-4 FIND-301
fix — the SOLE arbiter of every retry/reroute/escalation branch across REQ-505/506/511/513, never
`currentOfferedSlots`/`ctx.alwaysActMenu` array identity). IF `attemptsUsed === 0` THE SYSTEM SHALL
re-invoke the brain exactly once more with a genuine, HARD tool-enum exclusion of BOTH the just-picked slot
AND every capital-risking slot (spec-review iteration-2 FIND-101 fix — the doctrine's own promise, §0:
"routes to a market-risk-free skill ... instead"): `buildAlwaysActToolDefinitions(menuSlots.
filter(x => x !== s && isMarketRiskFree(x)))`, where `isMarketRiskFree(x)` is `riskTagOf(x) === 'safe'`
using the SAME injected `riskTagOf` classifier REQ-502/503's `assembleAlwaysActMenu` already threads from
`skills/registry.json`'s per-slot `risk` field (§1) — not a new, separate classification source, AND set
`attemptsUsed = 1`. Given the current registry (§1), the reroute target set NEVER includes `earn/sol-trade`,
`earn/polymarket-trade`, `hl_trade`, `token_launch`, or `yield` (all `risk:"capital"`) — a capital-risking
slot is never a valid reroute target after a no-edge WAIT, regardless of which slot was just picked
(spec-review FIND-003 fix — REQ-504's own purpose-built, explicit-array tool-definition constructor; this is
NOT the soft, prompt-text-only `avoidSlot` mechanism at `index.mjs:293-425` (converge doc-sync 2026-07-11
line-number correction, see FIND-006), which is untouched and unrelated
— see §1). The just-picked slot AND every capital-risking slot are therefore structurally ABSENT from the
reroute's tool schema, not merely discouraged in prose, so the model cannot re-select either — bounded to
`MAX_REROUTES = 1` (shared with REQ-505's budget per REQ-511). **(spec-review FIND-201 fix)** At the exact
moment this reroute tool schema is built, `index.mjs`'s retry loop sets its own local `currentOfferedSlots`
variable to this SAME `menuSlots.filter(x => x !== s && isMarketRiskFree(x))` array — so REQ-513's dispatch
guard validates the reroute attempt's parsed response against exactly this narrower set (its VALIDITY-check
role only, per REQ-504 point 5's iteration-4 correction), never the static `ctx.alwaysActMenu`; a re-emitted
`s` or any other `risk:"capital"` slot is rejected by REQ-513 even though both remain members of the full
`ctx.alwaysActMenu`. IF `attemptsUsed === 1` ALREADY at the moment this no-realized-action result is detected
(spec-review iteration-4 FIND-301 fix, generalized to REQ-506's own branch — e.g. the slot that just produced
`earnLine === null` was itself picked and executed on a REQ-505 REPROMPT attempt, which already spent the
shared budget) THE SYSTEM SHALL NOT re-invoke `think()` for a reroute; it SHALL proceed DIRECTLY to REQ-508's
truthful escalation — a no-realized-action result is never rerouted more than once total per wake, regardless
of which prior mechanism (a REQ-505 reprompt or an earlier REQ-506 reroute) already spent the shared budget.
**Edge Cases**:
- **(spec-review iteration-4 FIND-301 fix, generalizing FIND-301's fix to REQ-506's own branch)** A valid
  slot picked and executed on a REQ-505 REPROMPT attempt (i.e. `attemptsUsed` was already `1` at the moment
  this slot was picked, because the reprompt itself was the shared budget's one extra call) ALSO produces
  `earnLine === null`: THE SYSTEM SHALL NOT reroute (that would spend a third `think()` call) — it proceeds
  DIRECTLY to REQ-508's escalation. This is symmetric with REQ-505's own FIND-301 edge case (a reprompt
  attempt returning a fabricated slot) — both are instances of the single `attemptsUsed===1 → escalate,
  never a third think()` rule REQ-511 defines. See the transition-matrix row
  "no-tool-call→reprompt(valid pick)→no-op→ESCALATE" (§2.5) and PROP-506g.
- A menu slot missing the `risk` field entirely: `isMarketRiskFree(x)` (`riskTagOf(x) === 'safe'`) evaluates
  `undefined === 'safe'` → `false`, so the slot is treated as NOT risk-free and excluded from reroute
  targets — the same fail-closed convention `catalog-gate.mjs` already uses for an untagged slot (REQ-503's
  "untagged slot ⇒ treated as capital-risking"). This is an explicit design decision, not an accident of the
  equality check (spec-review iteration-3 non-blocking note).
- A slot execution that DOES write an earn-ledger line for this wake (`earnLine !== null`) — whether
  `profitable` is `true` or `false` (a real, recorded loss still counts as a realized economic action, not
  a no-op) — is accepted immediately; no reroute.
- The rerouted second pick ALSO produces `earnLine === null`: `attemptsUsed === 1` already (the reroute
  itself was the shared budget's one extra call) — this is the same general `attemptsUsed===1 → escalate`
  rule above, applied to the reroute-attempt's own outcome — proceed to REQ-508 (truthful record + escalate),
  never a third same-wake attempt.
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
  existing `appendHarnessFailure` mechanism (defined at `index.mjs:1028`, called from
  `runAlwaysActWake`'s own mirrored block at `index.mjs:767` — converge doc-sync 2026-07-11 line-number
  correction, see FIND-007; `index.mjs:458-475` is actually the unrelated bootstrap-reserve
  `filterCatalog` try/catch block) — that mechanism is unmodified and fires independently.
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
- **(spec-review iteration-4 FIND-301 regression test, PROP-506g "no-op-after-reprompt-escalates")** A unit
  test with a mocked `think()` sequence `[no-tool-call, {slot: validEarnSlot, args:{}}]` where the
  reprompt-attempt's valid pick's fixture earn-ledger has NO line for `wakeId` (`earnLine === null`) asserts:
  (a) zero additional `think()` calls (no reroute), (b) the wake proceeds DIRECTLY into REQ-508's escalation,
  (c) `attemptsUsed` is `1` (not `0`) at the moment the no-realized-action result is detected — proving a
  no-op result on the REPROMPT attempt is never rerouted a further time.

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
`appendHarnessFailure` mechanism (defined at `index.mjs:1028`; the escalation call sites this requirement's
own EARS clause describes are `index.mjs:878`/`:914` inside `writeAlwaysActEscalation` — converge doc-sync
2026-07-11 line-number correction, see FIND-007; `index.mjs:458-475` is actually the unrelated
bootstrap-reserve `filterCatalog` try/catch block, unmodified) so the existing self-heal escalation
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
`args`, an `attemptsUsed` field, and whether a realized earn-ledger line was found — reusing the existing
`formatRecord`/`safeAppend`/`LEDGER_PATH` machinery unmodified. **(spec-review iteration-5 notes.md
non-blocking observation #2 fix)** The `attemptsUsed` field ledgers EXACTLY REQ-511's own `attemptsUsed`
state variable, whose ENTIRE domain is `{0, 1}` — it is NEVER a count of total `think()` calls made this
wake (a distinct `{0, 1, 2}`-domain quantity this field does not track). `attemptsUsed === 0` means no
REQ-505 reprompt and no REQ-506 reroute was ever invoked this wake (whether because the baseline pick
resolved immediately, REQ-502 hit its empty-menu terminal case, or REQ-506 hit its empty-reroute-target
terminal case — see Acceptance Criteria below for the two cases where `attemptsUsed === 0` co-occurs with a
non-obvious `think()`-call count); `attemptsUsed === 1` means the SINGLE shared retry budget (a reprompt or
a reroute) was spent this wake, regardless of which of REQ-505/506/513 spent it.
**Edge Cases**:
- Private-key redaction (`redactPrivateKeyPatterns`, PROP-020 in the existing codebase) is applied to this
  new line exactly as it already is to every other ledger line — no new redaction pass, no bypass.
**Acceptance Criteria**:
- A unit test asserts the new ledger fields appear on both the "resolved on first pick" and "resolved
  after reroute/reprompt" paths, and that `redactPrivateKeyPatterns` is applied before append.
- **(spec-review iteration-5 notes.md non-blocking observation #2 fix, literal domain pin)** A unit test
  for REQ-502's empty-menu terminal case (zero `think()` calls made at all) asserts the ledgered
  `attemptsUsed` value is literally `0` — proving the field ledgers `attemptsUsed`, not a `think()`-call
  count, for the one terminal case where the two candidate readings would otherwise diverge from naive
  assumption (a `think()`-call-count reading would expect `0` here too, by coincidence, but the NEXT case
  disambiguates it).
- **(spec-review iteration-5 notes.md non-blocking observation #2 fix, literal domain pin)** A unit test
  for REQ-506's empty-reroute-target terminal case (one baseline `think()` call is made and resolves to a
  valid pick with `earnLine === null`, then the risk-free-filtered reroute set is empty so the
  re-invocation is skipped entirely per REQ-506's own edge case) asserts the ledgered `attemptsUsed` value
  is literally `0` even though exactly ONE `think()` call was actually made — this is the case that
  falsifies the `think()`-call-count reading and confirms the field ledgers `attemptsUsed ∈ {0, 1}`
  exclusively.

### REQ-511: Non-functional — bounded cost and latency, via a SINGLE explicit attempt-state that is the sole arbiter of every retry/reroute/escalation branch (spec-review iteration-4 FIND-301 fix)
**EARS**: THE SYSTEM SHALL track, for every always-act-engaged wake, a SINGLE explicit attempt-state
`attemptsUsed ∈ {0, 1}` (reusing/extending the pure `nextRerouteState({attemptsUsed, maxAttempts})`
state machine defined in the Pure Core, `maxAttempts = 1` — actual shipped signature, no `lastOutcome`
input; converge doc-sync 2026-07-11 correction, FIND-001/FIND-003) that IS, EXCLUSIVELY, the arbiter
of every retry/reroute/escalation branch decision made by REQ-505 (no-tool-call), REQ-506
(no-realized-action), and REQ-513 (fabricated/off-menu slot) within that wake. **(spec-review iteration-4
FIND-301 fix — the class-killing rule)** Branch selection MUST NOT compare `currentOfferedSlots`/
`ctx.alwaysActMenu` array identity, tool-schema shape, or ANY other proxy signal — it compares ONLY
`attemptsUsed`. THE SYSTEM SHALL bound the total extra model calls added by always-act enforcement to at
most 1 per wake beyond the baseline single `think()` call: ANY invalid outcome (a no-tool-call response, a
REQ-513-rejected fabricated/off-menu slot, or a REQ-506 no-realized-action result) encountered while
`attemptsUsed === 0` consumes the ONE shared retry — REQ-505's reprompt (same menu) if the outcome was
no-tool-call or a rejected slot on an attempt that had not yet executed a skill, or REQ-506's reroute
(risk-free-filtered menu) if the outcome was a no-realized-action result after a valid slot's execution —
and sets `attemptsUsed = 1`. ANY invalid outcome encountered while `attemptsUsed === 1` (the shared budget
already spent this wake, REGARDLESS of which prior mechanism spent it — a reprompt, a reroute, or a prior
REQ-513 rejection) proceeds DIRECTLY to REQ-508's truthful escalation — NEVER a third `think()` call, NEVER
further skill execution. Total `think()` calls per wake therefore NEVER exceed 2 (1 baseline + at most 1
shared extra-call budget), for ALL combinations and orderings of failure modes, and a pathological model
response pattern can never turn one wake into an unbounded retry loop or unbounded spend. (spec-review
iteration-2 FIND-102 fix, restated: this is the single, unambiguous ceiling — 2 total, never 3.)
**Edge Cases**:
- Both a no-tool-call AND a subsequent no-realized-action could theoretically compound; the bound is
  enforced as a single shared counter (`nextRerouteState`'s `maxAttempts = 1`) across ALL THREE mechanisms
  (REQ-505/506/513) within one wake, not independent budgets — so the 2-total ceiling is never exceeded
  regardless of which failure mode(s) occur, and once the shared budget's one extra call is spent, no
  further reprompt/reroute is attempted this wake — REQ-508 escalates instead.
- **(spec-review iteration-4 FIND-301 fix)** `attemptsUsed` is a SINGLE counter shared across REQ-505/506/513
  — it is incremented exactly once, at the moment the FIRST retry (of ANY kind: reprompt or reroute) is
  invoked, and never reset within a wake. It is NEVER re-derived from, or compared against,
  `currentOfferedSlots`/`ctx.alwaysActMenu` identity — doing so was iteration-3's own latent bug (FIND-301): a
  REQ-505 reprompt attempt's `currentOfferedSlots` is array-IDENTICAL to the baseline attempt's
  (`ctx.alwaysActMenu`, since a reprompt never narrows the schema — only a reroute does), so any branch rule
  keyed on that identity misclassifies a reprompt attempt's outcome as a fresh baseline outcome, buying an
  illegitimate extra `think()` call. `attemptsUsed` has no such ambiguity because it is incremented
  explicitly, exactly once, by whichever mechanism (REQ-505 or REQ-506) fires first — independent of failure
  type or which array was offered.
**Acceptance Criteria**:
- A property test with an adversarial mocked brain that ALWAYS returns no-tool-call or ALWAYS returns a
  slot with no realized ledger line asserts total `think()` calls for that wake never exceed 2 (1 baseline +
  1 shared-budget extra call), never 3.
- **(spec-review iteration-4 FIND-301, PROP-511a's strengthened coverage)** A property test with an
  adversarial mocked brain exercising ALL orderings of `{no-tool-call, fabricated/off-menu-slot,
  no-realized-action}` across up to 2 attempts (including the compound sequence
  `[no-tool-call, fabricated-slot]` — the FIND-301 scenario, and its REQ-506 symmetric counterpart
  `[no-tool-call, valid-pick-with-no-op]`) asserts `attemptsUsed` transitions `0 → 1` exactly once, at the
  first invalid outcome, and total `think()` calls never exceed 2, for EVERY ordering.

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

### REQ-513: A fabricated `slot:"sleep"` (or any slot not offered THIS attempt) is rejected by the REAL wake-loop dispatch against the PER-ATTEMPT offered set for VALIDITY, and routed by REQ-511's `attemptsUsed` state for BRANCH SELECTION — never by array identity (spec-review FIND-103 fix; FIND-201 fix corrected the validity reference set; FIND-301 fix corrects branch selection)
**EARS**: WHEN always-act mode is engaged (`ctx.alwaysActEngaged === true`) THE SYSTEM SHALL, via the
early-return dispatch that diverts the wake into `runAlwaysActWake` (`index.mjs:516-518`) BEFORE `index.mjs`'s
ordinary `think()`/tool-call-parse flow — including its pre-existing `if (slot === 'sleep')` branch
(`index.mjs:551`, unconditional string check, left untouched by this dispatch) — ever runs, check, for EACH
`think()` attempt inside `runAlwaysActWake`'s own retry loop, immediately ahead of any skill execution: once
`parseToolCall(rawResponse)` resolves a non-null `{ slot, args }` for that attempt, whether `slot === 'sleep'`
OR `slot` is not a member of `currentOfferedSlots` — **the exact slot array that WAS ACTUALLY PASSED to
`getToolDefinitions`/`buildAlwaysActToolDefinitions` for THIS SPECIFIC attempt** (spec-review FIND-201 fix:
the baseline attempt's `currentOfferedSlots` equals `ctx.alwaysActMenu`, per REQ-504 point 5; a REQ-506
reroute attempt's `currentOfferedSlots` equals that reroute's own narrower
`menuSlots.filter(x => x !== s && isMarketRiskFree(x, riskTagOf))` array — **NEVER** the static, full-wake
`ctx.alwaysActMenu`, once a reroute has narrowed the offered schema for that attempt — this is
`currentOfferedSlots`'s ONLY role, per REQ-504 point 5's iteration-4 correction). IF EITHER IS TRUE THE
SYSTEM SHALL NOT execute the resolved `slot` as a skill (`index.mjs:551`'s legacy `sleep`/narrate branch is
never reached by this codepath at all — it lives in a different function and is architecturally unreachable
for an engaged wake, see "Concretely:" below; this guard neither gates nor modifies it). The consequence THEN
branches SOLELY on REQ-511's shared `attemptsUsed` attempt-state (spec-review iteration-4 FIND-301 fix — this
REPLACES iteration-3's "IF this is the BASELINE/REROUTE attempt" framing, which inferred the attempt's
identity from `currentOfferedSlots === ctx.alwaysActMenu`; that inference is REMOVED because a REQ-505
reprompt attempt satisfies the exact same equality and was therefore misclassified — FIND-301):
- IF `attemptsUsed === 0` (the shared extra-call budget not yet spent by ANY prior mechanism this wake), THE
  SYSTEM SHALL treat this exactly as an invalid outcome for REQ-505's bounded-reprompt path and set
  `attemptsUsed = 1` (a stray off-menu/`"sleep"` slot consumes the SAME shared retry budget REQ-511 defines,
  it does not grant an extra attempt).
- IF `attemptsUsed === 1` ALREADY (the shared extra-call budget is spent — by a PRIOR REQ-505 reprompt, a
  PRIOR REQ-506 reroute, or by this being itself the reroute attempt), THE SYSTEM SHALL NOT re-invoke
  `think()` a third time; it SHALL proceed DIRECTLY to REQ-508's truthful escalation.

**(spec-review iteration-4 FIND-301 — why this resolves the finding)** A rejected fabricated/off-menu slot
arriving on a REQ-505 REPROMPT attempt has `currentOfferedSlots === ctx.alwaysActMenu`, IDENTICAL to the
baseline attempt's — but its `attemptsUsed` is `1` (the reprompt itself already incremented it when it was
invoked), so the branch rule above correctly routes it to REQ-508's escalation, never back into REQ-505's
reprompt path a second time. `currentOfferedSlots` identity is never consulted for this decision at all.

**Converge doc-sync 2026-07-11 correction, FIND-002/FIND-003**: this requirement previously described the
wiring mechanism — in its EARS clause above, in this "Concretely:" paragraph, in its Edge Cases bullet below,
and in the cross-cutting Edge Case Catalog (§3) — as the existing `if (slot === 'sleep')` branch being made
conditional in place. That is NOT what was shipped (FIND-002 fixed only this paragraph in the first doc-sync
pass; FIND-003, this iteration, propagates the same correction to the EARS clause and both edge-case
citations so the requirement no longer contradicts itself). See the actual mechanism, restated to match
`runtime/loop/index.mjs`:

Concretely: `index.mjs:516-518` adds an early return — `if (ctx.alwaysActEngaged) { return runAlwaysActWake({
ctx, wakeId, ts, alwaysActMenu }); }` — immediately ahead of the pre-existing `think()`/tool-call-parse flow.
This diverts an always-act-engaged wake into the dedicated `runAlwaysActWake` function BEFORE `index.mjs:551`'s
pre-existing `if (slot === 'sleep')` branch is ever reached; that branch itself stays byte-for-byte
unconditional and unmodified from the pre-feature original — it is simply unreachable for an engaged wake
because of the earlier return, not because it was made conditional. Inside `runAlwaysActWake`'s own per-attempt
retry loop, a new guard immediately ahead of skill execution (`index.mjs:717`, covering both the
fabricated-`"sleep"` case and any other slot excluded from the current attempt) checks
`isRejectableSleepOrOffMenu(slot, currentOfferedSlots)` for VALIDITY, where `currentOfferedSlots` is the retry
loop's own local variable for the CURRENT attempt (never `ctx.alwaysActMenu` read directly). A rejection's
BRANCH is then decided exclusively by the retry loop's own `attemptsUsed` local variable, via
`nextRerouteState({ attemptsUsed, maxAttempts: 1 })` at `index.mjs:718` (REQ-511's shared state) —
`attemptsUsed===0` routes into REQ-505's reprompt handling (and sets `attemptsUsed=1`); `attemptsUsed===1`
routes DIRECTLY into REQ-508's escalation. `isRejectableSleepOrOffMenu` itself has, and needs, NO
branch-selection responsibility — it answers ONLY "is `slot` valid for this attempt", never "which attempt is
this".
**Edge Cases**:
- A non-always-act wake (`ctx.alwaysActEngaged` falsy) is completely unaffected — `index.mjs:516`'s early
  return never fires for it, so the wake falls straight through to `index.mjs:551`'s pre-existing `if (slot
  === 'sleep')` branch exactly as it does today, byte-for-byte; the new guard (`isRejectableSleepOrOffMenu`
  at `index.mjs:717`, inside `runAlwaysActWake`) only activates when `ctx.alwaysActEngaged === true`.
- **(spec-review FIND-201)** A fabricated/off-menu slot arrives on the REROUTE attempt: this is NOT folded
  into a fresh REQ-505 reprompt (that would be a third `think()` call, violating REQ-511's 2-total ceiling) —
  it goes DIRECTLY to REQ-508's truthful escalation. This holds whether the rejected slot is `'sleep'`, a
  slot absent from the full `ctx.alwaysActMenu`, OR — the specific FIND-201 gap this revision closes — the
  just-excluded slot `s` or any other `risk:"capital"` slot that IS still a member of `ctx.alwaysActMenu` but
  was deliberately excluded from THIS reroute attempt's narrower `currentOfferedSlots`.
- **(spec-review FIND-201)** A model re-emits a DIFFERENT `risk:"capital"` slot (not the just-excluded `s`)
  during a reroute attempt — e.g. the reroute narrowed `currentOfferedSlots` to `{economy/gig, earn/clip}`
  but the parsed response names `hl_trade` — this is equally rejected: `hl_trade ∉ currentOfferedSlots` for
  this attempt even though `hl_trade ∈ ctx.alwaysActMenu`. Rejection routes to REQ-508 escalation exactly as
  any other reroute-attempt rejection.
- A weak/free model repeatedly fabricating `slot:"sleep"` across the bounded retry: this consumes the SAME
  ≤1-extra-call shared budget as any other no-tool-call/no-realized-action failure mode (REQ-511) — it
  cannot be used to multiply the number of `think()` calls beyond REQ-511's ceiling.
- **(spec-review iteration-4 FIND-301 — the finding this revision closes)** A fabricated/off-menu slot
  arrives on a REQ-505 REPROMPT attempt (as opposed to a REQ-506 reroute attempt): `currentOfferedSlots` for
  this attempt is array-IDENTICAL to the baseline attempt's (`ctx.alwaysActMenu`, since REQ-505's reprompt
  never narrows the schema) — but `attemptsUsed === 1` already (the reprompt itself was the shared budget's
  one extra call), so this rejection routes DIRECTLY to REQ-508's escalation, NEVER back into REQ-505's
  reprompt path for a second time (which would be a third `think()` call, violating REQ-511's ceiling). This
  is the exact scenario iteration-3's array-identity-keyed branch selection failed to cover — see the
  transition-matrix row "no-tool-call→reprompt→fabricated-slot→ESCALATE" (§2.5).
**Acceptance Criteria**:
- A unit test that feeds a mocked `think()` response which `parseToolCall` resolves to exactly
  `{ slot: 'sleep', args: {} }` on the BASELINE attempt (`currentOfferedSlots === ctx.alwaysActMenu`) while
  `ctx.alwaysActEngaged === true` asserts: (a) the existing `sleep`/narrate ledger line (`kind:'narrate',
  note:'agent chose to sleep'`) is NEVER written, (b) no skill execution is attempted for `slot:'sleep'`, and
  (c) the wake proceeds into REQ-505's reprompt path (a second `think()` call occurs, bounded by REQ-511).
  This is the direct regression test for spec-review FIND-103.
- The SAME test structure with a fabricated slot that is a syntactically valid string but absent from
  `ctx.alwaysActMenu` (e.g. `slot: 'report'`, a real registry slot excluded from the always-act menu by
  REQ-502) asserts identical rejection-and-reprompt behavior.
- A unit test with `ctx.alwaysActEngaged` falsy/absent and `slot: 'sleep'` asserts today's existing behavior
  is preserved byte-for-byte: the `kind:'narrate'` sleep ledger line IS written, no reprompt is triggered.
- **(spec-review FIND-201, scenario a)** A unit test simulates a REQ-506 reroute in flight — the baseline
  attempt picks a `risk:"capital"` slot `s` with `earnLine === null`, the reroute narrows
  `currentOfferedSlots` to the risk-free set excluding `s` — and mocks the REROUTE attempt's `think()`
  response as `parseToolCall` resolving to `{ slot: s, args: {} }` (the model re-emitting the just-excluded
  slot). Asserts: (a) no skill execution occurs for `s`, (b) no third `think()` call is made, (c) the wake
  proceeds directly into REQ-508's escalation path. This is the direct regression test for spec-review
  FIND-201.
- **(spec-review FIND-201, scenario b)** The SAME reroute-in-flight setup with the mocked reroute attempt's
  response instead resolving to a DIFFERENT `risk:"capital"` slot (e.g. `hl_trade`, still a member of
  `ctx.alwaysActMenu` but absent from this reroute's `currentOfferedSlots`) asserts identical
  rejection-and-escalation behavior — no execution, no third `think()` call, REQ-508 escalation.
- **(spec-review FIND-201, scenario c — no-regression)** A unit test asserts the BASELINE attempt, when the
  model picks a valid member of `ctx.alwaysActMenu` (`currentOfferedSlots === ctx.alwaysActMenu` for this
  attempt), executes that skill exactly as it did before this fix — proving the per-attempt signature change
  to `isRejectableSleepOrOffMenu` does not regress the ordinary accept path.
- **(spec-review iteration-4 FIND-301, PROP-513e — the direct regression test for FIND-301)** A unit test
  simulates the exact compound sequence: attempt #1 (baseline, `attemptsUsed===0`) returns no tool call →
  REQ-505 reprompts, `attemptsUsed` becomes `1`; attempt #2 (the REPROMPT, `currentOfferedSlots ===
  ctx.alwaysActMenu`, array-IDENTICAL to attempt #1's) resolves via `parseToolCall` to `{ slot: 'sleep',
  args: {} }`. Asserts: (a) no skill execution occurs, (b) NO third `think()` call is made (exactly 2 total),
  (c) the wake proceeds DIRECTLY into REQ-508's escalation path, NOT a second reprompt — proving branch
  selection is correctly keyed on `attemptsUsed` (which is `1` at this point) and NOT on
  `currentOfferedSlots===ctx.alwaysActMenu` (which is ALSO true at this point but is no longer consulted for
  branch selection at all). This is the direct regression test for spec-review iteration-4 FIND-301.

## 2.5 REQ-511 Attempt-State Transition Matrix (spec-review iteration-4 FIND-301 fix — exhaustive, not illustrative)

This matrix is the AUTHORITATIVE, exhaustive enumeration of every `attempt-1 outcome × attempt-2 outcome`
combination reachable under REQ-511's `attemptsUsed ∈ {0, 1}` attempt-state machine. It supersedes any
prose description of "the baseline attempt" / "the reroute attempt" that could be (mis)read as branching on
`currentOfferedSlots`/`ctx.alwaysActMenu` array identity — the ONLY input to branch selection is
`attemptsUsed`, per REQ-511/REQ-513. Every row is closed by an explicit AC/PROP reference; there is no
reachable attempt-1×attempt-2 combination outside this table.

| # | Attempt-1 outcome (`attemptsUsed` starts `0`) | Attempt-2 outcome (only reachable if attempt-1 was invalid) | `attemptsUsed` trace | Terminal result | AC / PROP ref |
|---|---|---|---|---|---|
| 1 | Valid slot picked, execution completes, `earnLine !== null` (realized action) | — (no attempt-2; nothing to retry) | stays `0` | **EXECUTE** (immediate accept, 1 `think()` call total) | REQ-506 AC "earnLine!==null accept" / PROP-506b |
| 2 | No tool call (`parseToolCall` falsy) | Reprompt (same `ctx.alwaysActMenu`): valid slot picked, `earnLine !== null` | `0 → 1` | **EXECUTE** (via reprompt, 2 `think()` calls total) | REQ-505 AC1 / PROP-505a |
| 3 | No tool call | Reprompt (same `ctx.alwaysActMenu`): fabricated/off-menu slot (e.g. `slot:'sleep'`) — **the FIND-301 scenario** | `0 → 1` (stays `1`, no further increment) | **ESCALATE** (REQ-508, 2 `think()` calls total, never 3) | REQ-505 FIND-301 edge case + AC / REQ-513 FIND-301 edge case + AC / **PROP-513e** |
| 4 | No tool call | Reprompt (same `ctx.alwaysActMenu`): no tool call again | `0 → 1` (stays `1`) | **ESCALATE** (REQ-508, 2 `think()` calls total) | REQ-505 edge case "re-prompt also returns no tool call" / PROP-505a |
| 5 | Valid slot `s` picked, execution completes, `earnLine === null` (no-op) | Reroute (risk-free-filtered menu excluding `s` and every `risk:"capital"` slot): valid safe slot picked, `earnLine !== null` | `0 → 1` | **EXECUTE** (via reroute, 2 `think()` calls total) | REQ-506 AC "reroute enum excludes just-picked+capital slots" / PROP-506a |
| 6 | Valid slot `s` picked, `earnLine === null` | Reroute: model re-emits the just-excluded `s`, or any other `risk:"capital"` slot absent from this reroute's `currentOfferedSlots` (e.g. `hl_trade`) | `0 → 1` (stays `1`) | **ESCALATE** (REQ-508, no execution, no 3rd `think()` call) | REQ-513 FIND-201 scenarios a/b + AC / PROP-513b / PROP-513c |
| 7 | Valid slot `s` picked, `earnLine === null` | Reroute: valid safe slot picked, execution completes, `earnLine === null` AGAIN (also no-op) | `0 → 1` (stays `1`) | **ESCALATE** (REQ-508 — accepted once rerouted, per REQ-511; never a 3rd `think()` call) | REQ-506 edge case "rerouted second pick ALSO produces earnLine===null" / PROP-506f-adjacent exhaustive coverage under PROP-511a |
| 8 | Fabricated/off-menu slot on the very FIRST `think()` call (e.g. `slot:'sleep'`, or a syntactically valid slot absent from `ctx.alwaysActMenu`) | Reprompt (same `ctx.alwaysActMenu`, per REQ-513's baseline-attempt branch): valid slot picked, `earnLine !== null` | `0 → 1` | **EXECUTE** (via reprompt, 2 `think()` calls total) | REQ-513 PROP-513a / REQ-505 AC1 |
| 9 | No tool call | Reprompt (same `ctx.alwaysActMenu`): VALID slot picked, execution completes, but `earnLine === null` (no-op) — **the REQ-506 symmetric extension of FIND-301** | `0 → 1` (stays `1`, no reroute attempted) | **ESCALATE** (REQ-508, no reroute — a 3rd `think()` call would be needed to reroute, which REQ-511 forbids) | REQ-506 FIND-301 generalized edge case + AC / **PROP-506g** |
| 10 | Fabricated/off-menu slot on the very FIRST `think()` call (e.g. `slot:'sleep'`, or a syntactically valid slot absent from `ctx.alwaysActMenu`) | Reprompt (same `ctx.alwaysActMenu`, per REQ-513's baseline-attempt branch): fabricated/off-menu slot AGAIN | `0 → 1` (stays `1`, no further increment) | **ESCALATE** (REQ-508, 2 `think()` calls total, never 3) | REQ-513's generic "attemptsUsed===1 ALREADY... by a PRIOR REQ-505 reprompt, a PRIOR REQ-506 reroute, or by this being itself the reroute attempt" branch rule (REQ-513 EARS, applies identically regardless of the specific fabricated-slot value on attempt-2) / PROP-511a's bounded-exploration sweep |
| 11 | Fabricated/off-menu slot on the very FIRST `think()` call | Reprompt (same `ctx.alwaysActMenu`): no tool call | `0 → 1` (stays `1`) | **ESCALATE** (REQ-508, 2 `think()` calls total, never 3) | REQ-505's generic "consult REQ-511's shared attempt-state... IF attemptsUsed===1 ALREADY... proceed DIRECTLY to REQ-508's truthful escalation" EARS clause (not scoped to which failure type produced `attemptsUsed=1`) / PROP-511a's bounded-exploration sweep |
| 12 | Fabricated/off-menu slot on the very FIRST `think()` call | Reprompt (same `ctx.alwaysActMenu`): VALID slot picked, execution completes, but `earnLine === null` (no-op) | `0 → 1` (stays `1`, no reroute attempted) | **ESCALATE** (REQ-508, no reroute — a 3rd `think()` call would be needed to reroute, which REQ-511 forbids) | REQ-506's generic "the slot that just produced earnLine===null was itself picked and executed on a REQ-505 REPROMPT attempt, which already spent the shared budget... proceed DIRECTLY to REQ-508's truthful escalation" edge case (not scoped to which failure type produced `attemptsUsed=1` on attempt-1) / PROP-506g / PROP-511a's bounded-exploration sweep |

**(spec-review iteration-5 notes.md non-blocking observation #1 fix)** Rows 10-12 close the 3
attempt-1×attempt-2 cells that iteration-5's independent re-derivation found reachable but not given a
dedicated row (all three have attempt-1 = a fabricated/off-menu slot on the very first `think()` call, i.e.
row 8's precursor, crossed with attempt-2 ∈ {fabricated/off-menu again, no tool call, valid-pick-no-op} —
the fourth member of that product, a valid pick with `earnLine !== null`, is already row 8 itself). Every
one of rows 3/4/6/7/9/10/11/12 resolves to the SAME **ESCALATE** pattern because `attemptsUsed===1` at
attempt-2 in every one of them, regardless of which attempt-1 failure type (no-tool-call, fabricated/off-menu
slot, or valid-pick-no-op) produced that `attemptsUsed=1` value — this was already true of the underlying
REQ-505/506/513 requirements before rows 10-12 were added (see iteration-5 notes.md finding #1's own
derivation), so adding these rows is a pure precision fix with no change to any requirement's behavior. The
full attempt-1(3 non-terminal classes) × attempt-2(4 classes) = 12-cell product is now covered by exactly
12 rows (1 terminal attempt-1-only row [1] + 11 two-attempt rows [2-12]): `attemptsUsed` cannot exceed `1`
within a wake (REQ-511), and once `attemptsUsed===1`, EVERY invalid outcome (of any type) terminates in
rows 3/4/6/7/9/10/11/12's shared **ESCALATE** pattern — never a third `think()` call, never further skill
execution. No other attempt-1×attempt-2 combination is reachable.

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
  `slot:"sleep"` or any slot absent from `currentOfferedSlots` despite the schema truly not offering it (a
  realistic risk for weak/free models, per §1's `parse-tool-call.mjs` scavenge-parser evidence) — REQ-513
  rejects it at the REAL `runAlwaysActWake` dispatch point (`isRejectableSleepOrOffMenu` at `index.mjs:717`,
  reached only via the early-return dispatch at `index.mjs:516-518`) and, on the baseline attempt, routes it
  into REQ-505/511's bounded reprompt path; it is NEVER silently honored as an idle/sleep outcome, closing the
  structural bypass that would otherwise defeat REQ-504/505/506's entire purpose.
- **Reroute-attempt fabricated re-pick of an excluded slot** (spec-review iteration-3 FIND-201): during a
  REQ-506 reroute, a model re-emits the just-excluded slot `s` or any other `risk:"capital"` slot that
  remains a member of the static `ctx.alwaysActMenu` but was deliberately excluded from THIS reroute
  attempt's narrower `currentOfferedSlots` — REQ-513's guard checks the per-attempt `currentOfferedSlots`
  (never the static `ctx.alwaysActMenu`) for VALIDITY, and, because `attemptsUsed===1` at this point (the
  reroute already consumed the shared budget — spec-review iteration-4 FIND-301 fix: BRANCH selection is
  `attemptsUsed`, not `currentOfferedSlots`, see §2.5), rejection routes DIRECTLY to REQ-508's truthful
  escalation, never a third `think()` call, never skill execution. This closes the dispatch-layer gap that
  would otherwise have silently reopened FIND-101's money-safety fix at exactly the layer meant to enforce
  it.
- **Reprompt-attempt fabricated/off-menu slot, misclassified as a fresh baseline attempt by array identity**
  (spec-review iteration-4 FIND-301, the third instance of this failure class after FIND-102/FIND-201): a
  model's REQ-505 reprompt attempt (attempt #2, invoked because attempt #1 returned no tool call) returns a
  fabricated `slot:'sleep'` or any off-menu slot instead. This attempt's `currentOfferedSlots` equals
  `ctx.alwaysActMenu`, array-IDENTICAL to attempt #1's baseline value (a reprompt never narrows the schema —
  only a reroute does), so a branch rule that inferred "is this the baseline attempt" from
  `currentOfferedSlots === ctx.alwaysActMenu` (iteration-3's REQ-513 wording) would misclassify this as a
  fresh baseline attempt and issue a SECOND reprompt — a THIRD `think()` call, violating REQ-511's 2-total
  ceiling. This revision removes ALL array-identity-based branch selection: REQ-505/506/511/513 now branch
  EXCLUSIVELY on `attemptsUsed` (`1` at this point, since the reprompt already spent the shared budget), so
  this rejection correctly routes DIRECTLY to REQ-508's escalation. See the exhaustive transition matrix
  (§2.5, row 3) and PROP-513e.
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
   REQ-506 test asserts the REAL `index.mjs:754` call-site widening (converge doc-sync 2026-07-11
   line-number correction, see FIND-005) for `economy/gig`/`economy/lending` AND
   that the reroute enum excludes every `risk:"capital"` slot; the REQ-513 test asserts the REAL
   `runAlwaysActWake` dispatch (`isRejectableSleepOrOffMenu` at `index.mjs:717`) rejects a fabricated
   `slot:'sleep'`/off-menu pick) — confirm all new tests
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

- **converge iter3 fix: mechanical, exhaustive citation-accuracy audit (FIND-005/006/007 + full sweep)**:
  converge iteration-3's fresh-context adversary independently discovered 3 further stale `index.mjs`
  citations (FIND-005: REQ-506's declared single-line `index.mjs:450` classify-gate ternary does not exist
  in the shipped code — the real mechanism is two separate call sites, `index.mjs:598` legacy/unconditional
  inside `runOneWake` and `index.mjs:754` inside `runAlwaysActWake`; FIND-006: `avoidSlot`'s declared
  `index.mjs:175-184`/`:183`/`:179-421` citations are stale by ~113-119 lines — the real declaration is
  `index.mjs:296`, its comment `index.mjs:302`, the consuming block `index.mjs:293-425`; FIND-007: REQ-508's
  EARS clause and REQ-506's Edge Cases bullet both cite `index.mjs:458-475` for `appendHarnessFailure`,
  which is actually the unrelated bootstrap-reserve `filterCatalog` block — the real definition is
  `index.mjs:1028`, call sites `613`/`767`/`878`/`914`), following this feature's now-3-for-3 pattern of a
  targeted fix correctly resolving the NAMED finding without extending the same correction discipline to
  sibling citations of the same underlying fact. This revision performs the ONE mechanical, exhaustive pass
  converge iteration-3's own recommendation asked for: every `index.mjs:<N>`/`prompt.mjs:<N>`/
  `brain.mjs:<N>`/`run.sh:<N>` citation in this file and `verification-architecture.md` was independently
  re-extracted and cross-checked against the CURRENT real file via grep for the literal quoted code/comment
  string (never re-read from memory of where it "should" be) — see
  `.vcsdd/features/franklin-alwaysact-skill-router/evidence/citation-audit-2026-07-11.md` for the full
  58-citation audit table (29 SAME, 29 DRIFTED/REWRITTEN, 0 remaining after this fix). This sweep found 4
  FURTHER stale citations beyond FIND-005/006/007, undiscovered by any prior Phase 3/5/converge pass:
  `index.mjs:382-416` (§1's "TWO existing idle paths" bullet — real locations `index.mjs:533-546`/`551-564`),
  `index.mjs:440-456` (§1's `classifyEarnResult` ground-truth bullet, cited the SAME wrong ~450 zone FIND-005
  already flagged for a different sentence — real call sites `index.mjs:602`/`759`), `prompt.mjs:139-173`/
  `:171` (REQ-504's `getToolDefinitions`/`SLEEP_TOOL`-append citations, drifted ~5-7 lines by the same
  REQ-504 JSDoc-addition that pushed the function body down — real locations `prompt.mjs:144-180`/`178`),
  and `brain.mjs:63`/`:92` (REQ-504's `thinkProxy`/`thinkClaudeP` wiring-seam citations, drifted by the same
  REQ-504 comment-block insertion — real locations `brain.mjs:66`/`100-102`), plus `prompt.mjs:205-207`
  (`avoidSlot`'s soft-nudge prose citation — real location `prompt.mjs:212-214`, text on `:213`). Notably,
  the `brain.mjs:63`/`:92` and `prompt.mjs:139-173`/`:171` citations had been spot-checked and reported
  "ACCURATE"/"matches" by converge iteration-3's own adversary session (`notes-iteration-3.md` Task 2) —
  this mechanical re-grep, not memory-based spot-checking, is what actually catches drift; a "the adversary
  already checked this one" assumption is exactly the gap this fix closes. Also annotates (not rewrites,
  per the historical-record convention this file already uses) the now-FALSE iteration-4 Changelog claim
  that `index.mjs:183`'s `avoidSlot`-comment citation was "independently re-verified against this exact
  HEAD" (FIND-006 — that re-verification was accurate only against the pre-Phase-2b/2c snapshot it was
  actually checked against, not the current HEAD). Documentation-accuracy only — no source/test change;
  183/183 unchanged throughout. A companion second correction note is appended to
  `verification/purity-audit.md` (its "zero deviations" claim, already once-corrected for FIND-001/002, is
  falsified again by FIND-005/006/007 and this sweep's 4 additional findings). See
  `.vcsdd/features/franklin-alwaysact-skill-router/reviews/converge/output/findings/FIND-005.json`,
  `FIND-006.json`, `FIND-007.json`, and `notes-iteration-3.md`.
- **converge iter2 fix: doc-sync FIND-003/004 (REQ-513 EARS clause + all residual stale references,
  exhaustive grep sweep)**: converge iteration-2's fresh-context adversary found the first doc-sync pass
  (FIND-001/002 below) corrected only REQ-513's "Concretely:" paragraph, leaving REQ-513's own EARS clause
  (§REQ-513, most authoritative sentence), its Edge Cases bullet, and the cross-cutting Edge Case Catalog
  (§3) still asserting the disproven "in-place conditional guard before `index.mjs:402-416`'s `if (slot ===
  'sleep')` branch" mechanism as current fact (FIND-003) — an internal self-contradiction within the same
  requirement. This revision propagates the corrected early-return-dispatch mechanism
  (`index.mjs:516-518` → `runAlwaysActWake`, guard `isRejectableSleepOrOffMenu` at `index.mjs:717`, legacy
  `index.mjs:551` branch untouched/unreachable for engaged wakes) to all of REQ-513's own restatements, plus
  one further stale `index.mjs:402-416` citation found by an exhaustive grep sweep (REQ-504's edge case,
  §2). Also applies FIND-004's still-outstanding 9-row → 12-row correction (`specs/verification-architecture.md`
  lines 18-20/42/316/360 and this file's own iteration-4 changelog entry below) that iteration-1's own
  recommendation asked for but the first fix pass did not apply. Documentation-accuracy only — no
  source/test change; 183/183 unchanged throughout. See
  `.vcsdd/features/franklin-alwaysact-skill-router/reviews/converge/output/findings/FIND-003.json` and
  `FIND-004.json`.
- **converge fix: doc-sync FIND-001/002 (declared design synced to shipped implementation, no code
  change)**: Phase 6 convergence review found REQ-513's "Concretely:" paragraph declared the wiring
  mechanism as `index.mjs:402-416`'s existing `if (slot === 'sleep')` branch "becomes conditional"
  (`if (slot === 'sleep' && !ctx.alwaysActEngaged)`). The actual shipped mechanism, confirmed by reading
  `runtime/loop/index.mjs`, is an early-return dispatch at `index.mjs:516-518` into a dedicated
  `runAlwaysActWake` function BEFORE `index.mjs:551`'s branch (left unconditional and unmodified) is ever
  reached. The "Concretely:" paragraph is rewritten above to describe the real mechanism with current line
  numbers. This is a documentation-accuracy fix only — no behavioral defect; PROP-513a/b/c/e all passed
  before and after this correction (183/183). Companion fix (FIND-001, `verification-architecture.md`'s
  `nextRerouteState` signature) applied in that file. See
  `.vcsdd/features/franklin-alwaysact-skill-router/reviews/converge/output/findings/FIND-002.json`.
- **iteration-4 fix: FIND-301 (branch selection keyed on attempt-state machine, exhaustive transition matrix
  added)**: REQ-513's iteration-3 fix rejected a parsed slot using the correct per-attempt
  `currentOfferedSlots` for VALIDITY, but still decided WHICH branch (REQ-505 reprompt vs REQ-508 escalation)
  to take by asking "is this the BASELINE attempt", operationally defined as
  `currentOfferedSlots === ctx.alwaysActMenu` (REQ-504 point 5). A REQ-505 reprompt attempt ALSO satisfies
  that equality (a reprompt never narrows the schema, only a reroute does), so a fabricated slot arriving on
  the reprompt attempt was misclassified as a fresh baseline attempt, buying a SECOND reprompt — a THIRD
  `think()` call, violating REQ-511's 2-total ceiling (the third instance of this failure class, after
  FIND-102 and FIND-201). This revision introduces a SINGLE, explicit attempt-state, `attemptsUsed ∈ {0, 1}`
  (reusing/extending the already-specified `nextRerouteState` pure state machine), as the SOLE arbiter of
  every retry/reroute/escalation branch across REQ-505/506/511/513 — branch selection MUST NOT compare array
  identity, tool-schema shape, or any other proxy; `currentOfferedSlots` is demoted to its FIND-201
  VALIDITY-check role only (is the parsed slot a legal member of what was offered THIS attempt) and plays no
  part in branch selection. REQ-504 point 5, REQ-505, REQ-506, REQ-511, and REQ-513 are all rewritten to this
  rule; REQ-506 gains a symmetric edge case/AC (its own instance of the same class — a valid slot picked and
  executed on a REQ-505 reprompt attempt that ALSO no-ops must escalate directly, never reroute). A new §2.5
  "REQ-511 Attempt-State Transition Matrix" adds an exhaustive 12-row table covering every reachable
  attempt-1×attempt-2 outcome combination, each closed by an explicit AC/PROP reference. New PROP-513e
  (money-safety-critical, the direct FIND-301 regression test) and PROP-506g (the REQ-506 symmetric
  extension) added in verification-architecture.md; PROP-511a's adversarial coverage is restated to
  explicitly include the compound `[no-tool-call, fabricated-slot]` sequence. Two non-blocking iteration-4
  citation drifts are also corrected: `skills/self/earning-health.py`'s docstring citation narrows from
  "lines 12-22" to "lines 14-22" (lines 12-13 are general doctrine-framing prose, not the skip-vs-live-pass
  mechanism definition). (`index.mjs:183`'s citation for `avoidSlot`'s inline comment was independently
  re-verified against this exact HEAD — the quoted text is still at line 183, not line 187 — so that specific
  correction noted in iteration-4's review was NOT applied; ground truth confirms the existing citation is
  accurate.) **[converge doc-sync 2026-07-11 correction, FIND-006: this re-verification claim was accurate
  ONLY as of the pre-Phase-2b/2c snapshot it was checked against at the time iteration-4 was written — it is
  FALSE against the current, post-implementation HEAD. Phase 2b/2c's REQ-501 identity-gate code (inserted
  earlier in the file) shifted `avoidSlot`'s real declaration to `index.mjs:296` and its inline comment to
  `index.mjs:302`, ~113-119 lines below this entry's claimed line 183 (which is now inside
  `queryHlTradeOpenPositions`, unrelated Hyperliquid code). Neither Phase 3's four impl-review iterations,
  Phase 5's purity-audit.md, nor converge iterations 1-2 caught that this self-certified-accurate citation
  had gone stale in the interim. See
  `.vcsdd/features/franklin-alwaysact-skill-router/reviews/converge/output/findings/FIND-006.json` and
  `.vcsdd/features/franklin-alwaysact-skill-router/evidence/citation-audit-2026-07-11.md`.]**
- **iteration-3 fix: FIND-201 (guard validates per-attempt offered set)**: REQ-513's dispatch-level rejection
  guard previously checked a parsed slot against the static, wake-level `ctx.alwaysActMenu` — a model that
  re-emitted the just-excluded slot `s` (or any other `risk:"capital"` slot) during REQ-506's reroute attempt
  would pass the guard (both remain members of the full menu) and reach real skill execution, silently
  reopening FIND-101's money-safety fix at the dispatch layer. REQ-504 gains a new point 5 and REQ-506's EARS
  gains an explicit clause introducing `currentOfferedSlots` — a local variable in `index.mjs`'s retry loop,
  set to `ctx.alwaysActMenu` for the baseline attempt and to REQ-506's narrower risk-free-filtered array for
  a reroute attempt. REQ-513's EARS, edge cases, and acceptance criteria are rewritten so
  `isRejectableSleepOrOffMenu(slot, currentOfferedSlots)` always validates against what was ACTUALLY offered
  for the CURRENT attempt, never the static full-wake menu; a rejection on the reroute attempt (whose shared
  extra-call budget is already spent) now routes DIRECTLY to REQ-508's escalation rather than attempting a
  third `think()` call. New PROP-513b/PROP-513c/PROP-513d added in verification-architecture.md.
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
