# Verification Architecture — franklin-alwaysact-skill-router

## Purity Boundary Map

**Spec-review iteration-1 correction (FIND-001/FIND-002/FIND-003/FIND-005)**: the original map below
understated where the real implementation diff lands. Three existing modules that were previously described
as "unmodified" or not mentioned at all ARE additively modified by this feature — `runtime/loop/prompt.mjs`
(stays Pure Core, gains an additive parameter), `runtime/loop/brain.mjs` (stays Effectful Shell, its
`tools:`/prompt-text lines become conditional), and `runtime/loop/index.mjs:450`'s classify call-site gate
(stays Effectful Shell, its condition is additively widened). This is the AUTHORITATIVE, corrected map.

**Spec-review iteration-2 correction (FIND-101/FIND-102/FIND-103)**: three further corrections land in this
revision — (1) REQ-506's reroute filter gains a `risk:"safe"`-only constraint (`isMarketRiskFree`, sourced
from the registry's existing `risk` field, not a new classification source) so a capital-risking slot is
never offered as a reroute target (FIND-101); (2) REQ-511's ceiling is restated unambiguously as at most 1
extra `think()` call beyond baseline (2 total), matching `nextRerouteState`'s `maxAttempts = 1` and
PROP-511a verbatim (FIND-102); (3) a new pure guard + Effectful Shell modification (REQ-513) makes
`index.mjs`'s real `if (slot === 'sleep')` dispatch (`index.mjs:402-416`) reject a fabricated
`slot:'sleep'`/off-menu pick while always-act is engaged, closing a structural bypass of the entire
always-act mechanism (FIND-103).

**Spec-review iteration-3 correction (FIND-201)**: `isRejectableSleepOrOffMenu`'s second argument is
corrected from the static, wake-level `ctx.alwaysActMenu` to a per-attempt `currentOfferedSlots` value — a
local variable in `index.mjs`'s retry loop, set to `ctx.alwaysActMenu` for the baseline attempt and to
REQ-506's narrower risk-free-filtered array for a reroute attempt. Without this correction, a model
re-emitting the just-excluded slot `s` (or any `risk:"capital"` slot) during a REQ-506 reroute would pass
REQ-513's guard (both remain members of the full `ctx.alwaysActMenu`) and reach real skill execution,
silently reopening FIND-101's money-safety fix at the dispatch layer. The guard itself remains a pure
function; only its second argument's source changes.

**Spec-review iteration-4 correction (FIND-301, the class-killing fix)**: iteration-3's REQ-513 fix corrected
`currentOfferedSlots`'s VALUE but left BRANCH SELECTION (does a rejection route into REQ-505's reprompt or
REQ-508's escalation?) keyed on `currentOfferedSlots === ctx.alwaysActMenu` — an "is this the baseline
attempt" test that a REQ-505 reprompt attempt ALSO satisfies (a reprompt never narrows the schema; only a
reroute does), so a fabricated slot on the reprompt attempt was misclassified as baseline, buying an
illegitimate second reprompt (a third `think()` call — the same failure CLASS as FIND-102/FIND-201, its
third instance). This revision removes array-identity-based branch selection ENTIRELY: `nextRerouteState`'s
`attemptsUsed` output (already specified in iteration-1's Pure Core, previously under-used) is now the SOLE
arbiter of every REQ-505/506/511/513 branch decision — `attemptsUsed===0` → one shared retry (reprompt or
reroute, whichever failure type fired); `attemptsUsed===1` → REQ-508 escalation, unconditionally, regardless
of failure type or which array was offered. `currentOfferedSlots`/`isRejectableSleepOrOffMenu` are demoted to
their FIND-201 VALIDITY-check role only. See §2.5 of behavioral-spec.md for the exhaustive 9-row transition
matrix this correction is verified against.

- **Pure Core** (new module(s), e.g. `runtime/loop/always-act-router.mjs`, deterministic, no I/O,
  formally/property verifiable — mirrors the existing purity split of `context.mjs`, `prompt.mjs`,
  `tier.mjs`, `catalog-gate.mjs`, `earn-slot.mjs`):
  - `isEarnActionSlot(name)` — REQ-502: `isEarnSlot(name) || DOCTRINE_EARN_ACTIONS.has(name)` where
    `DOCTRINE_EARN_ACTIONS = {'economy/gig', 'economy/lending'}` is a fixed, doctrine-derived,
    non-inferred set (bookkeeping data, not judgment — same category as `catalog-gate.mjs`'s injected
    `riskTagOf`/`alwaysAvailableOf` classifiers). **REQ-506 correction**: this predicate is also the one
    used at the widened `index.mjs:450` classify call-site — see Effectful Shell below — so `economy/gig`
    and `economy/lending` are classify-eligible, not just menu-eligible.
  - `assembleAlwaysActMenu({ registry, activeSkillSlots, catalogFilterFn, balanceUsdc,
    reserveThresholdUsdc, riskTagOf, alwaysAvailableOf, hasOpenRiskPositionOf })` — REQ-502/503: pure
    composition of `liveSlotNames`-equivalent filtering + `isEarnActionSlot` + `filterCatalog`
    (`catalog-gate.mjs`, injected as a function reference, never re-implemented).
  - `runtime/loop/prompt.mjs::getToolDefinitions(slots, opts)` — REQ-504: **ADDITIVELY MODIFIED, not
    unmodified** (FIND-001/FIND-005 correction). Gains an optional second parameter `opts = { omitSleep:
    false }`; when `omitSleep === true`, `SLEEP_TOOL` (`prompt.mjs:171`) is not appended. Every existing
    call site (which never passes `opts`) is byte-for-byte unaffected — this stays a pure, deterministic
    string/object transform, correctly Pure Core, but is no longer "unmodified."
  - `buildAlwaysActToolDefinitions(menuSlots)` — REQ-504: a thin wrapper —
    `getToolDefinitions(menuSlots, { omitSleep: true })` — reusing the SAME modified `getToolDefinitions`
    that `brain.mjs`'s own `tools:` line calls (see Effectful Shell below), not a parallel, disconnected
    reimplementation. This is what makes PROP-504a's pure-function assertion actually reachable from the
    real outbound wire (PROP-504b).
  - `isMarketRiskFree(slot, riskTagOf)` — REQ-506 (spec-review iteration-2 FIND-101 fix): pure predicate,
    `riskTagOf(slot) === 'safe'`. Reuses the SAME injected `riskTagOf` classifier `assembleAlwaysActMenu`
    already threads from `skills/registry.json`'s per-slot `risk` field (the `isEarnActionSlot` bullet
    above, which names the same injected `riskTagOf`/`alwaysAvailableOf` classifiers) — not a new,
    separate classification data source. REQ-506's reroute filter becomes `menuSlots.filter(x => x !== s &&
    isMarketRiskFree(x, riskTagOf))`. A slot missing the `risk` field entirely evaluates
    `undefined === 'safe'` → `false` — explicitly treated as NOT risk-free (fail-closed, the same convention
    `catalog-gate.mjs` already uses for an untagged slot), not merely an accident of the equality check
    (spec-review iteration-3 non-blocking note).
  - `noRealizedAction(earnLine)` — REQ-506: `earnLine === null` (trivial pure predicate over
    `classifyEarnResult`'s already-computed return value; `classifyEarnResult` itself stays in the
    effectful shell, unmodified, `earn-detect.mjs`).
  - `isRejectableSleepOrOffMenu(slot, currentOfferedSlots)` — REQ-513 (spec-review iteration-2 FIND-103 fix;
    **spec-review iteration-3 FIND-201 fix corrects the second argument**): pure predicate, `slot === 'sleep'
    || !currentOfferedSlots.includes(slot)`. Consumed by `index.mjs`'s real dispatch (Effectful Shell, below)
    immediately after `parseToolCall` resolves a non-null `{slot, args}`, gating whether the existing
    `if (slot === 'sleep')` branch is even reachable and whether skill execution proceeds at all.
    `currentOfferedSlots` is threaded from the retry loop's own per-attempt local variable (FIND-201 fix) —
    equal to `ctx.alwaysActMenu` for the baseline attempt (REQ-504 point 5) and to REQ-506's reroute-filtered
    array for a reroute attempt — **NEVER** the static `ctx.alwaysActMenu` read directly by the guard itself;
    the predicate function stays pure and unchanged in shape, only the caller's choice of which array to pass
    changes per attempt. **(spec-review iteration-4 FIND-301 fix)** This predicate answers ONLY "is `slot`
    valid for THIS attempt" — it has NO branch-selection role and is never consulted to decide "which attempt
    is this" or "which recovery path applies"; that decision belongs EXCLUSIVELY to `nextRerouteState`'s
    `attemptsUsed` output, below.
  - `nextRerouteState({ attemptsUsed, maxAttempts, lastOutcome })` — REQ-505/506/511/513: pure bounded-retry
    state machine (`{ shouldRetry: boolean, excludeSlot: string|null, exhausted: boolean }`) — the single
    shared counter (`maxAttempts = 1`) enforcing REQ-511's ceiling of 2 total `think()` calls per wake
    (1 baseline + at most 1 shared extra-call budget, spec-review iteration-2 FIND-102 fix — not "2 extra").
    **(spec-review iteration-4 FIND-301 fix — this function's role is elevated and made explicit)** Its
    `attemptsUsed` input/tracking IS, EXCLUSIVELY, the arbiter of every retry/reroute/escalation branch
    decision made by REQ-505, REQ-506, and REQ-513 — `attemptsUsed===0` at the moment an invalid outcome
    (no-tool-call, a REQ-513-rejected slot, or a REQ-506 no-realized-action result) is observed means exactly
    one more `think()` call is legitimate (REQ-505's reprompt or REQ-506's reroute, whichever failure type
    applies) and `attemptsUsed` becomes `1`; `attemptsUsed===1` already means REQ-508's escalation fires
    DIRECTLY, unconditionally, regardless of failure type. No code path may re-derive or approximate this
    decision via `currentOfferedSlots`/`ctx.alwaysActMenu` array identity, tool-schema shape, or any other
    proxy — `attemptsUsed` is the ONLY input to branch selection (this was iteration-3's REQ-513 fix's own
    latent bug, FIND-301: it kept `attemptsUsed` implicit and inferred the branch from array identity
    instead, which a REQ-505 reprompt attempt's `currentOfferedSlots` also satisfies since a reprompt never
    narrows the schema).
  - `buildMustActReinforcement(ctx, priorAttempt)` — REQ-505: pure string builder, additive to
    `buildUserMessage`'s existing composition pattern.
  - `buildAlwaysActLedgerFields({ wakeId, slot, args, attemptsUsed, realized })` — REQ-508/510: pure
    record-shaping (the actual append/redact/write stays in the effectful shell, reusing
    `formatRecord`/`safeAppend`/`redactPrivateKeyPatterns` unmodified).
  - `isPostGoLiveRegression(ledgerTail, { minRun })` — REQ-512: pure predicate mirroring
    `skills/self/earning-health.py::is_fresh_but_barren`'s exact contract (no I/O, takes a pre-gathered
    tail) — `true` iff an `always_act_go_live` line is followed by ≥`minRun` consecutive
    `always_act_not_engaged` lines for Franklin's identity with no intervening reset.

- **Effectful Shell** (extended, not replaced):
  - `runtime/loop/index.mjs` — the wake-loop orchestration: identity-gate check (REQ-501, calls
    `wallet-address-solana.mjs` subprocess twice, exactly mirroring `sol-trade/run.sh:35-41`), the
    reprompt/reroute retry loop (calls `think()` up to REQ-511's bound). **(spec-review iteration-4 FIND-301
    fix)** The retry loop maintains exactly ONE local `attemptsUsed` variable (initialized `0`, mirroring
    `nextRerouteState`'s input/output contract) for the whole wake — REQ-505's reprompt call site sets it to
    `1` at the moment the reprompt is invoked, exactly as REQ-506's reroute call site does (below); this
    single variable, never `currentOfferedSlots`/`ctx.alwaysActMenu` identity, is what every subsequent
    invalid-outcome check on either the reprompt attempt or a further outcome consults to pick REQ-505's
    reprompt path vs REQ-508's escalation. `classifyEarnResult`/`appendHarnessFailure`/`safeAppend` (all
    pre-existing, unmodified) are called as before. **REQ-506/
    FIND-002 correction — ADDITIVELY MODIFIED, not unmodified**: the classify call-site gate at
    `index.mjs:450` changes from `else if (isEarnSlot(slot))` to `else if (ctx.alwaysActEngaged ?
    isEarnActionSlot(slot) : isEarnSlot(slot))` — a non-always-act `ctx` evaluates `isEarnSlot(slot)`
    exactly as today. **REQ-506/FIND-003 correction (spec-review iteration-2 FIND-101 further correction)**:
    the reroute re-invocation builds its tool schema via `buildAlwaysActToolDefinitions(menuSlots.filter(x =>
    x !== pickedSlot && isMarketRiskFree(x, riskTagOf)))` — a genuine hard array filter over the pure-core
    menu that ALSO excludes every `risk:"capital"` slot, not only the just-picked one — NOT the soft
    `avoidSlot` field (`index.mjs:179-421`), which stays completely unmodified and independent of this
    feature. **(spec-review iteration-3 FIND-201 fix)** At this exact point — where the reroute's tool
    schema is built — the retry loop also sets its own local `currentOfferedSlots` variable to this SAME
    filtered array (distinct from, and never reassigned back into, `ctx.alwaysActMenu`); this is the value
    REQ-513's guard (below) checks a reroute attempt's response against for VALIDITY only. **(spec-review
    iteration-4 FIND-301 fix)** At this SAME point, the retry loop also sets its own local `attemptsUsed`
    variable to `1` (this reroute call IS the shared budget's one extra call) — `attemptsUsed`, not
    `currentOfferedSlots`, is what any subsequent invalid-outcome check consults to decide reprompt-vs-reroute-
    vs-escalate. **REQ-513 (spec-review iteration-2 FIND-103 fix; iteration-3 FIND-201 fix corrects the
    VALIDITY reference set; iteration-4 FIND-301 fix corrects BRANCH SELECTION) — ADDITIVELY MODIFIED,
    previously unlisted**: `index.mjs:402-416`'s existing `if (slot === 'sleep')` branch becomes conditional
    (`if (slot === 'sleep' && !ctx.alwaysActEngaged)`), and a new guard immediately ahead of skill execution
    rejects (for VALIDITY) a fabricated `slot:'sleep'` or any slot absent from the CURRENT attempt's
    `currentOfferedSlots` (baseline attempt: `ctx.alwaysActMenu`; reroute attempt: the narrower
    risk-free-filtered array set above — **never the static `ctx.alwaysActMenu` once a reroute is in flight**)
    when `ctx.alwaysActEngaged === true`. The rejection's BRANCH is then decided EXCLUSIVELY by the retry
    loop's own `attemptsUsed` local variable (spec-review iteration-4 FIND-301 fix — supersedes iteration-3's
    "baseline attempt vs reroute attempt" framing, which was itself keyed on `currentOfferedSlots` identity):
    `attemptsUsed===0` routes into REQ-505's reprompt path (and sets `attemptsUsed=1`); `attemptsUsed===1`
    routes DIRECTLY into REQ-508's escalation (no third `think()` call is made) — this correctly handles BOTH
    a rejected reroute-attempt response (attemptsUsed was already 1 from the reroute call itself) AND a
    rejected REQ-505 reprompt-attempt response (attemptsUsed was already 1 from the reprompt call itself,
    even though that attempt's `currentOfferedSlots` is array-identical to the baseline's — the FIND-301 fix)
    — a non-always-act `ctx` is completely unaffected, the existing branch fires exactly as today. **REQ-512**: appends
    `kind:'always_act_not_engaged'`/`kind:'always_act_go_live'` ledger lines (new, additive `kind` values
    reusing `formatRecord`/`safeAppend` unmodified).
  - `runtime/loop/brain.mjs::think()` / `thinkProxy()` / `thinkClaudeP()` — **ADDITIVELY MODIFIED, not
    unmodified** (FIND-001/FIND-005 correction — this was the central defect in spec-review iteration-1).
    `thinkProxy`'s `tools:` line (`brain.mjs:63`) becomes `tools: getToolDefinitions(ctx.alwaysActEngaged ?
    ctx.alwaysActMenu : ctx.activeSkillSlots, { omitSleep: ctx.alwaysActEngaged === true })`.
    `thinkClaudeP`'s prompt-text instruction line (`brain.mjs:92`) conditionally drops the sleep mention on
    the same `ctx.alwaysActEngaged` flag. A non-always-act `ctx` (`alwaysActEngaged` falsy — the
    overwhelming majority of all wakes, every non-Franklin instance) produces byte-for-byte identical output
    to today's unconditional call — the function CONTRACT (inputs: `ctx`, `config`; output: raw response)
    is unchanged, only its internal tool-assembly branches conditionally on the new `ctx` fields.
  - Every skill's own `run.sh` (`skills/earn/*/run.sh`, `skills/economy/*`) and its money-safety guards —
    entirely unmodified, out of this feature's write-scope (REQ-509).
  - `skills/self/earning-health.py` — extended additively (a new sibling function alongside
    `is_fresh_but_barren`, mirroring its pure/no-I/O contract) to host the REQ-512 companion regression
    detector's real (non-test) implementation — `is_fresh_but_barren` itself is unmodified.

## Proof Obligations

| ID | Description | Tier | Required | Tool |
|----|-------------|------|----------|------|
| PROP-501a | Identity mismatch (or derivation error/empty) → always-act NOT engaged; `sleep` tool present | 2 | true | vitest/jest exhaustive-case |
| PROP-501b | Identity match + flag unset/malformed → always-act NOT engaged (mirrors `SOL_GATE_LIVE_ENABLE` fail-closed contract) | 2 | true | vitest/jest exhaustive-case |
| PROP-501c | Identity match + flag `"1"` → always-act engaged | 2 | true | vitest/jest |
| PROP-502a | `isEarnActionSlot` = `isEarnSlot ∪ {economy/gig, economy/lending}`, verified by literal-set exhaustion over the CURRENT registry (11-slot menu, REQ-502 acceptance) | 1 | true | fast-check (property) + literal fixture |
| PROP-502b | Menu excludes every non-live registry slot, for ALL registry entries (property over generated registries) | 1 | true | fast-check |
| PROP-502c | Menu excludes `report, cook, self/spawn, self/spawn-child, self/issue-dev, self/coordinate, economy/ubi, earn/audit, earn/_probe, earn` for the current registry | 1 | true | vitest/jest literal |
| PROP-502d | Empty resolved menu → `kind:'router_menu_empty'` + escalation (REQ-508), never a silent `sleep`/`narrate` fallback | 2 | true | vitest/jest exhaustive-case |
| PROP-503a | `balanceUsdc` at-or-above `reserveThresholdUsdc` (boundary-inclusive, mirrors `catalog-gate.mjs::isBelowThreshold`) → full unfiltered menu, for ALL balance/threshold pairs at the boundary | 1 | true | fast-check (boundary sweep) |
| PROP-503b | Below-threshold with an open position for a capital slot → that slot stays in the menu (carve-out preserved) | 2 | true | vitest/jest exhaustive-case |
| PROP-504a | `getToolDefinitions(menu, {omitSleep:true})`/`buildAlwaysActToolDefinitions` never includes a tool named `sleep`, for ANY menu (pure-function level; necessary but not sufficient — see PROP-504b) | 1 | true | fast-check |
| PROP-504b (money-doctrine-critical, closes FIND-001/FIND-005) | The REAL outbound request body assembled by `thinkProxy` (mocked ONLY at the `httpPost` network boundary — real function, real `tools:` line executed) contains no tool named `sleep` when `ctx.alwaysActEngaged===true`, for an arbitrary always-act menu; the same call with `ctx.alwaysActEngaged` falsy DOES include `sleep`, proving the conditional wiring (not just the standalone pure helper) actually governs the wire | 2 | true | vitest/jest integration (mocked HTTP boundary only) |
| PROP-505a | No-tool-call response → exactly 2 `think()` calls total (1 reprompt), never 1, never 3+ | 1 | true | fast-check (adversarial mock sequences) |
| PROP-506a | Picked slot (any `isEarnSlot` member) with `earnLine === null` → exactly one reroute call whose ACTUAL constructed tool schema's `slot.enum` (array-content assertion, not a bookkeeping flag) does not contain that slot — a genuine hard exclusion, not the soft `avoidSlot` prompt nudge | 1 | true | fast-check |
| PROP-506b | Picked slot with `earnLine !== null` (any `profitable` value) → zero reroute calls (immediate accept) | 1 | true | fast-check |
| PROP-506c (closes FIND-002) | `economy/gig` and `economy/lending` picks specifically, under `ctx.alwaysActEngaged===true`, trigger `classifyEarnResult` invocation via the widened `index.mjs:450` call-site condition (`isEarnActionSlot`, not `isEarnSlot`) and `earnLine===null` drives the SAME reroute path as any `isEarnSlot` member — verified against `index.mjs`'s actual branching, never falling through to a silent `kind:'wake'` accept | 2 | true | vitest/jest integration |
| PROP-506d (closes FIND-003's empty-enum edge case) | Always-act menu of size 1 equal to the just-picked slot, with `earnLine===null` → zero additional `think()` calls, immediate REQ-508 escalation (never a forced same-slot re-invocation) | 2 | true | vitest/jest exhaustive-case |
| PROP-506e (money-safety-critical, closes FIND-101) | Reroute target set is filtered to `risk:"safe"` slots only (`isMarketRiskFree`) — for an arbitrary always-act menu containing a mix of `risk:"safe"`/`risk:"capital"` members, the ACTUAL constructed reroute tool schema's `slot.enum` never contains a `risk:"capital"` slot, for ALL such menus (property test), plus a literal fixture asserting `earn/sol-trade`/`hl_trade`/`token_launch`/`earn/polymarket-trade`/`yield` are never valid reroute targets | 2 | true | fast-check + vitest/jest literal |
| PROP-506f (money-safety-critical, closes FIND-101) | Risk-free-filtered reroute set is empty (though the raw excluded-self set is non-empty, e.g. every remaining slot is `risk:"capital"`) → zero additional `think()` calls, immediate REQ-508 escalation — NEVER a fallback into a `risk:"capital"` reroute target | 2 | true | vitest/jest exhaustive-case |
| PROP-506g (money-safety-critical, closes FIND-301's REQ-506 symmetric extension) | A valid slot picked and executed on a REQ-505 REPROMPT attempt (`attemptsUsed` already `1` when the slot was picked) that ALSO produces `earnLine === null` → zero additional `think()` calls (no reroute attempted), immediate REQ-508 escalation — NEVER a reroute merely because the no-op happened to occur on the reprompt attempt rather than the baseline attempt | 2 | true | vitest/jest exhaustive-case |
| PROP-507a (money-safety-critical) | For every slot `s` in an arbitrary generated menu, given a mocked brain returning `run_skill({slot:s, args:A})` for arbitrary `A`, the harness executes exactly `(s, A)` — no substitution, no ranking, no filtering by `A`'s content | 1 | true | fast-check (menu × args generator) |
| PROP-507b (static) | The pure-core module source contains no `RegExp`/`.match(`/`.test(` call and no `if (args.` / `switch (slot)`-style branching keyed on model-chosen `args`/`slot` CONTENT (branching on registry bookkeeping fields like `status`/`risk` is allowed and expected) | 0 | true | grep-based CI check (documented, not a formal tool) |
| PROP-508a | Both bounds exhausted → ledger `kind` is never `'wake'`/`'narrate'` and `profitable` is never `true` | 2 | true | vitest/jest exhaustive-case |
| PROP-509a (money-safety-critical) | This feature's implementation diff touches none of: `skills/earn/*/run.sh`, `skills/earn/*/lib/resolve-max-spend.sh`, `skills/_shared/lib/earn-guard.mjs`, `catalog-gate.mjs` threshold constants | 0 | true | `git diff --stat` CI check against an explicit path allowlist |
| PROP-509b (money-safety-critical) | Reroute triggered by a real guard-block (fixture: guard returns `skip`) selects a DIFFERENT slot on retry and never re-invokes the SAME slot with a relaxed/bypassed guard | 2 | true | vitest/jest integration (unmodified guard modules + fixtures) |
| PROP-510a | New ledger fields present on both first-pick-resolved and after-reroute/reprompt-resolved paths; `redactPrivateKeyPatterns` applied before append | 1 | true | vitest/jest |
| PROP-511a (money-safety-critical) | Adversarial mock brain, ALL orderings of `{no-tool-call, fabricated/off-menu-slot, no-realized-action}` up to 2 attempts (spec-review iteration-4 FIND-301 strengthened coverage — explicitly includes the compound `[no-tool-call, fabricated-slot]` sequence and its `[no-tool-call, valid-pick-with-no-op]` REQ-506 counterpart, not just "always X") → total `think()` calls per wake ≤ 2 (1 baseline + at most 1 shared extra-call budget, spec-review iteration-2 FIND-102 restated ceiling — never 3), AND `attemptsUsed` transitions `0→1` exactly once, for ALL adversarial sequences up to a bounded exploration depth | 1 | true | fast-check (bounded exhaustive) |
| PROP-512a (closes FIND-004) | A Franklin-identity wake with the flag unset/malformed appends `kind:'always_act_not_engaged'` with `reason` ∈ `{flag_unset, flag_malformed}` on EVERY such wake (not conditioned on go-live having happened); the one-time flag-flip operational action appends `kind:'always_act_go_live'` exactly once | 1 | true | vitest/jest |
| PROP-512b (closes FIND-004) | `isPostGoLiveRegression`/`is_fresh_but_barren`-sibling detector: (a) `always_act_not_engaged` lines with no preceding `always_act_go_live` line never trigger regression-detected; (b) `always_act_go_live` followed by ≥`minRun` consecutive `always_act_not_engaged` lines DOES trigger it; (c) a single `always_act_not_engaged` line surrounded by successfully-engaged wakes after go-live does NOT trigger it | 1 | true | fast-check / pytest (mirrors `earning-health.py`'s own test style) |
| PROP-513a (structural, closes FIND-103) | On the BASELINE attempt (`currentOfferedSlots === ctx.alwaysActMenu`), a parsed tool call of exactly `{slot:'sleep', args:{}}` (or any slot absent from `currentOfferedSlots`) fed to the REAL `index.mjs` wake-loop dispatch while `ctx.alwaysActEngaged===true` is REJECTED — no `kind:'narrate'`/idle ledger line is written, no skill execution is attempted, and the wake proceeds into REQ-505's reprompt path (a second `think()` call occurs, bounded by REQ-511); the same input with `ctx.alwaysActEngaged` falsy/absent preserves today's existing `sleep`/narrate behavior byte-for-byte | 2 | true | vitest/jest integration |
| PROP-513b (money-safety-critical, closes FIND-201, scenario a) | Given a REQ-506 reroute in flight whose narrower `currentOfferedSlots` excludes the just-picked slot `s`, a parsed tool call of exactly `{slot: s, args:{}}` fed to the REAL `index.mjs` dispatch during that REROUTE attempt is REJECTED — no skill execution occurs for `s`, no third `think()` call is made, and the wake proceeds DIRECTLY into REQ-508's escalation path (never REQ-505's reprompt) — even though `s` remains a member of the static `ctx.alwaysActMenu` | 2 | true | vitest/jest integration |
| PROP-513c (money-safety-critical, closes FIND-201, scenario b) | The SAME reroute-in-flight setup as PROP-513b with a parsed tool call naming a DIFFERENT `risk:"capital"` slot (still a member of `ctx.alwaysActMenu` but absent from this reroute attempt's `currentOfferedSlots`, e.g. `hl_trade`) is equally REJECTED — no execution, no third `think()` call, direct REQ-508 escalation | 2 | true | vitest/jest integration |
| PROP-513d (regression, closes FIND-201, scenario c) | On the BASELINE attempt (`currentOfferedSlots === ctx.alwaysActMenu`), a parsed tool call naming any valid member of that set EXECUTES normally (no rejection, no escalation) — proving `isRejectableSleepOrOffMenu`'s per-attempt-argument signature introduces no regression to the ordinary accept path | 1 | true | vitest/jest |
| PROP-513e (money-safety-critical, closes FIND-301 — the direct regression test) | Compound sequence: attempt #1 (baseline, `attemptsUsed===0`) returns no tool call → REQ-505 reprompts, `attemptsUsed` becomes `1`; attempt #2 (the REPROMPT, `currentOfferedSlots === ctx.alwaysActMenu`, array-IDENTICAL to attempt #1's) resolves to `{slot:'sleep', args:{}}`. Asserts: no skill execution, exactly 2 `think()` calls total (never 3), the wake proceeds DIRECTLY into REQ-508's escalation (NOT a second reprompt) — proving branch selection is keyed on `attemptsUsed` (`1` at this point), never on `currentOfferedSlots===ctx.alwaysActMenu` (also true at this point, but never consulted for branch selection) | 2 | true | vitest/jest integration |

## Verification Strategy

- **Tier 0** (no formal proof needed — CI/static checks suffice): prompt wording/non-functional strings;
  PROP-507b's grep-based no-regex-branching check; PROP-509a's diff-path allowlist check. These are cheap,
  deterministic, and directly falsifiable by `grep`/`git diff` — no property-test framework adds value.
- **Tier 1** (property tests / fuzzing over the pure core): all `assembleAlwaysActMenu`,
  `isEarnActionSlot`, `noRealizedAction`, `nextRerouteState`, `buildAlwaysActToolDefinitions` obligations
  (PROP-502a/b, 503a, 504a, 505a, 506a/b, 507a, 510a, 511a, 512a/b) — these are pure, small-domain functions
  ideal for `fast-check` (the project's language is JavaScript/`.mjs`; `fast-check` is the JS-ecosystem
  equivalent of `hypothesis`/`kani` named in the template, and is the standard choice already implied by
  this repo's existing pure-function-heavy `runtime/loop/*.mjs` modules — no new exotic dependency).
  PROP-512b's detector mirrors `earning-health.py`'s existing pytest style if implemented as its Python
  sibling, or `fast-check` if implemented as a `.mjs` pure function — Phase 2b decides the host module, the
  contract (pure, no I/O, pre-gathered tail in) is fixed by REQ-512.
- **Tier 2** (lightweight formal methods — exhaustive case enumeration over small finite state spaces):
  the identity-gate (PROP-501a/b/c — 2×2×3 finite combinations of {match/mismatch/error} × {flag
  set/unset/malformed}, fully enumerable, no sampling needed), the empty-menu failure mode (PROP-502d),
  the reserve carve-out (PROP-503b), the REAL outbound-wire wiring-seam assertion (PROP-504b — closes
  FIND-001/FIND-005; small state space: {always-act engaged, not engaged} × {menu contents}, exhaustively
  enumerable, and money-doctrine-critical enough that a sampled property test is not sufficient assurance),
  the gig/lending classify-gate widening (PROP-506c — closes FIND-002), the empty-enum reroute terminal
  case (PROP-506d — closes FIND-003), the risk-free-only reroute filter and its empty-safe-set terminal case
  (PROP-506e/PROP-506f — closes FIND-101), the exhausted-bound truthful-record (PROP-508a), the
  money-safety-critical guard-block reroute (PROP-509b), the REAL wake-loop dispatch rejection of a
  fabricated `sleep`/off-menu pick on the baseline attempt (PROP-513a — closes FIND-103), and the
  money-safety-critical rejection of a re-emitted excluded slot or any other `risk:"capital"` slot during a
  REQ-506 reroute attempt, validated against the per-attempt `currentOfferedSlots` rather than the static
  `ctx.alwaysActMenu` (PROP-513b/PROP-513c — closes FIND-201), the money-safety-critical rejection of a
  fabricated/off-menu slot arriving specifically on a REQ-505 REPROMPT attempt — validated by `attemptsUsed`
  (not `currentOfferedSlots` identity, which is array-identical to the baseline attempt's for a reprompt) —
  never buying an illegitimate third `think()` call (PROP-513e — closes FIND-301), and its REQ-506 symmetric
  counterpart, a no-op result on a slot picked during a REQ-505 reprompt attempt never triggering a further
  reroute (PROP-506g — closes FIND-301's REQ-506 extension) — these get EXHAUSTIVE case tables, not
  random sampling, because the state spaces are small and the cost of a missed case (a silent idle wake, a
  silently-still-present sleep tool, an unclassified gig/lending no-op, a capital-risking reroute target, a
  guard bypass, or an illegitimate third `think()` call) is exactly the failure this feature exists to
  prevent. PROP-513d (Tier 1 — regression only, the baseline-attempt accept path is unaffected by the
  argument-source change) is verified alongside them in the same harness for convenience, though it does not
  itself require exhaustive-case treatment.
- **Tier 3** (strong formal proof): none required. No cryptographic, consensus, or concurrency-critical
  logic is introduced by this feature — the underlying money-safety proofs (`MAX_SPEND` hard-override,
  `earn-guard.mjs` cumulative-loss check, `catalog-gate.mjs`'s own already-shipped proof obligations under
  `anicca-agent-economy`) are REUSED UNCHANGED (REQ-509) and are out of this feature's re-verification
  scope — re-proving them here would be redundant with their own feature's verification, not this one's.

## Test-Money Safety Rule (binding, mirrors behavioral-spec.md §5)

All Tier 1/2 tests inject fixtures for: `registry` (a small in-memory object, never the real
`skills/registry.json` mutated), `earnLedgerPath`/`earnLine` (fixture JSONL strings or pre-parsed
objects, never the real `earn-ledger.jsonl`), identity derivation (a mocked function returning
fixed wallet strings, never a real subprocess spawn of `wallet-address-solana.mjs` against real
`ANICCA_HOME`), and `think()` (a mocked async function returning scripted tool-call sequences, never a
real HTTP call to `OPENAI_BASE_URL` or a real `claude -p` subprocess spawn). PROP-509b is the one
exception permitted to import the REAL (unmodified) `catalog-gate.mjs`/`earn-slot.mjs` pure modules
directly (they are pure and side-effect-free, so importing them is safe) while still using fixture data —
it must never import or execute any `run.sh`, CLI, or network-touching code. PROP-504b is a SECOND, narrower
exception (required to close FIND-001/FIND-005): it is permitted to import and execute the REAL
`runtime/loop/brain.mjs::thinkProxy` (the actual function under test — this is the whole point, testing the
standalone pure helper alone cannot prove the wiring seam), mocking ONLY the module-level `httpPost` network
call (e.g. via dependency injection or module-mock at that single boundary) so no real HTTP request is ever
issued; it must still never spawn `franklin-trading`, touch `~/.blockrun`, or hit a real RPC/x402 endpoint. A
test that spawns `franklin-trading`, reads/writes `~/.blockrun`, or hits a real RPC/x402 endpoint fails
Phase 2a/2b review outright, regardless of its assertions.

## Phase 5 Verification Harness Plan (for later `verification/` phase)

- `verification/always-act-menu.property.test.mjs` — runs PROP-502a/b/c/d, 503a/b as `fast-check`
  properties + literal fixtures.
- `verification/always-act-wire-seam.test.mjs` — runs PROP-504a (pure helper) AND PROP-504b (the REAL
  `thinkProxy` outbound-request-body assertion, mocked only at `httpPost`) — this file is the concrete
  closure of spec-review FIND-001/FIND-005; a green PROP-504a with a red/missing PROP-504b is treated as
  an incomplete implementation, never a pass.
- `verification/always-act-reroute.property.test.mjs` — runs PROP-505a, 506a/b/c/d/e/f/g, 511a, 513a/b/c/d/e
  with adversarial mock-`think()` sequences, including the `economy/gig`/`economy/lending` classify-gate-widening
  case (PROP-506c, closes FIND-002), the empty-enum terminal case (PROP-506d, closes FIND-003), the
  risk-free-only reroute filter + its empty-safe-set terminal case (PROP-506e/f, closes FIND-101), the
  REAL `index.mjs` dispatch rejection of a fabricated `slot:'sleep'`/off-menu pick on the baseline attempt
  (PROP-513a, closes FIND-103), the REAL `index.mjs` dispatch rejection of a re-emitted excluded slot or
  any other `risk:"capital"` slot during a REROUTE attempt, validated against `currentOfferedSlots` rather
  than `ctx.alwaysActMenu` (PROP-513b/c, closes FIND-201), plus the baseline-attempt no-regression check
  (PROP-513d), AND — **spec-review iteration-4 FIND-301 fix** — the compound
  `[no-tool-call, fabricated-slot]` sequence proving branch selection is keyed on `attemptsUsed`, never
  `currentOfferedSlots` identity (PROP-513e), and its REQ-506 symmetric counterpart, a no-op result on a
  REQ-505-reprompt-attempt's valid pick never triggering a further reroute (PROP-506g). This file's test
  suite is required to exercise EVERY row of behavioral-spec.md §2.5's exhaustive 9-row transition matrix,
  not merely the PROP-labeled subset.
- `verification/always-act-nojudgment.property.test.mjs` — runs PROP-507a (menu × args generator) +
  PROP-507b (grep check, invoked as a subprocess assertion from the test file so it participates in the
  same test run/report).
- `verification/always-act-moneysafety.test.mjs` — runs PROP-509a (diff-path allowlist) and PROP-509b
  (guard-block integration fixture) — these two are the money-safety-critical gate this feature must
  never regress; CI treats a failure here as blocking regardless of mode (lean or strict).
- `verification/always-act-observability.test.mjs` — runs PROP-512a (go-live/not-engaged ledger `kind`
  lines) and PROP-512b (the post-go-live regression detector, mirroring `earning-health.py`'s own test
  style) — closes spec-review FIND-004.

## Changelog

- **iteration-4 fix: FIND-301 (branch selection keyed on attempt-state machine, exhaustive transition matrix
  added)**: `nextRerouteState`'s `attemptsUsed` output is elevated to the SOLE arbiter of every
  retry/reroute/escalation branch decision across REQ-505/506/511/513 (Pure Core: `nextRerouteState` bullet
  rewritten; `isRejectableSleepOrOffMenu` demoted to its FIND-201 VALIDITY-check role only, explicitly
  stripped of any branch-selection responsibility). Effectful Shell: `index.mjs`'s retry loop now
  explicitly maintains ONE `attemptsUsed` local variable set by BOTH the REQ-505 reprompt call site and the
  REQ-506 reroute call site (previously only the reroute call site's `currentOfferedSlots` assignment was
  described); REQ-513's dispatch-guard description is rewritten so its VALIDITY check (`currentOfferedSlots`)
  and its BRANCH decision (`attemptsUsed`) are explicitly separated — this closes FIND-301, where iteration-3's
  wording let a REQ-505 reprompt attempt's rejection be misclassified as a fresh baseline attempt (both have
  `currentOfferedSlots === ctx.alwaysActMenu`), buying an illegitimate third `think()` call. New PROP-513e
  (money-safety-critical, the direct FIND-301 regression test) and PROP-506g (money-safety-critical, the
  REQ-506 symmetric extension — a no-op result on a REQ-505-reprompt-attempt's valid pick must also escalate
  directly, never reroute a third time) added to the Proof Obligations table; PROP-511a's adversarial
  coverage description is strengthened to explicitly enumerate ALL orderings of the three failure modes
  (not just "always X"), including both compound sequences. Verification Strategy's Tier 2 list and the
  Phase 5 `always-act-reroute.property.test.mjs` harness plan updated to require coverage of every row in
  behavioral-spec.md §2.5's new exhaustive 9-row transition matrix.
- **iteration-3 fix: FIND-201 (guard validates per-attempt offered set)**: `isRejectableSleepOrOffMenu`'s
  second argument is corrected from the static `ctx.alwaysActMenu` to a per-attempt `currentOfferedSlots`
  value (a local variable in `index.mjs`'s retry loop, set at the same point the per-attempt tool
  definitions are built — `ctx.alwaysActMenu` for the baseline attempt, REQ-506's reroute-filtered array for
  a reroute attempt). Purity Boundary Map updated (Pure Core: `isRejectableSleepOrOffMenu` signature +
  `isMarketRiskFree`'s missing-`risk`-field non-blocking note; Effectful Shell: `index.mjs`'s reroute-schema
  construction point now also sets `currentOfferedSlots`, and a reroute-attempt rejection routes DIRECTLY to
  REQ-508 escalation instead of REQ-505's reprompt). Added PROP-513b (money-safety-critical, closes FIND-201
  scenario a — re-emitted excluded slot rejected), PROP-513c (money-safety-critical, closes FIND-201
  scenario b — different `risk:"capital"` slot rejected), and PROP-513d (regression, closes FIND-201 scenario
  c — baseline-attempt accept path unaffected), all with Phase 5 harness coverage added to
  `verification/always-act-reroute.property.test.mjs`.
- **iteration-2 fixes: FIND-101/102/103** (spec-review iteration-2, this revision):
  - FIND-101: added `isMarketRiskFree` to Pure Core, widened the Effectful Shell reroute-filter description,
    and added PROP-506e/PROP-506f (money-safety-critical, Tier 2) plus their Phase 5 harness coverage.
  - FIND-102: restated `nextRerouteState`'s ceiling as `maxAttempts = 1` / 2-total and clarified PROP-511a's
    description to match REQ-511's rewritten EARS clause — no more "2 extra" ambiguity anywhere in this file.
  - FIND-103: added `isRejectableSleepOrOffMenu` to Pure Core, documented `index.mjs:402-416`'s real
    modification under REQ-513 in the Effectful Shell, and added PROP-513a (Tier 2) plus Phase 5 coverage.
