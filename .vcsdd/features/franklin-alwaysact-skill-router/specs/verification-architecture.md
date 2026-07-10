# Verification Architecture — franklin-alwaysact-skill-router

## Purity Boundary Map

**Spec-review iteration-1 correction (FIND-001/FIND-002/FIND-003/FIND-005)**: the original map below
understated where the real implementation diff lands. Three existing modules that were previously described
as "unmodified" or not mentioned at all ARE additively modified by this feature — `runtime/loop/prompt.mjs`
(stays Pure Core, gains an additive parameter), `runtime/loop/brain.mjs` (stays Effectful Shell, its
`tools:`/prompt-text lines become conditional), and `runtime/loop/index.mjs:450`'s classify call-site gate
(stays Effectful Shell, its condition is additively widened). This is the AUTHORITATIVE, corrected map.

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
  - `noRealizedAction(earnLine)` — REQ-506: `earnLine === null` (trivial pure predicate over
    `classifyEarnResult`'s already-computed return value; `classifyEarnResult` itself stays in the
    effectful shell, unmodified, `earn-detect.mjs`).
  - `nextRerouteState({ attemptsUsed, maxAttempts, lastOutcome })` — REQ-505/506/511: pure bounded-retry
    state machine (`{ shouldRetry: boolean, excludeSlot: string|null, exhausted: boolean }`) — the single
    shared counter enforcing REQ-511's ≤2 ceiling.
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
    reprompt/reroute retry loop (calls `think()` up to REQ-511's bound), calling
    `classifyEarnResult`/`appendHarnessFailure`/`safeAppend` (all pre-existing, unmodified). **REQ-506/
    FIND-002 correction — ADDITIVELY MODIFIED, not unmodified**: the classify call-site gate at
    `index.mjs:450` changes from `else if (isEarnSlot(slot))` to `else if (ctx.alwaysActEngaged ?
    isEarnActionSlot(slot) : isEarnSlot(slot))` — a non-always-act `ctx` evaluates `isEarnSlot(slot)`
    exactly as today. **REQ-506/FIND-003 correction**: the reroute re-invocation builds its tool schema via
    `buildAlwaysActToolDefinitions(menuSlots.filter(x => x !== pickedSlot))` — a genuine hard array filter
    over the pure-core menu — NOT the soft `avoidSlot` field (`index.mjs:179-421`), which stays completely
    unmodified and independent of this feature. **REQ-512**: appends `kind:'always_act_not_engaged'`/
    `kind:'always_act_go_live'` ledger lines (new, additive `kind` values reusing `formatRecord`/`safeAppend`
    unmodified).
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
| PROP-507a (money-safety-critical) | For every slot `s` in an arbitrary generated menu, given a mocked brain returning `run_skill({slot:s, args:A})` for arbitrary `A`, the harness executes exactly `(s, A)` — no substitution, no ranking, no filtering by `A`'s content | 1 | true | fast-check (menu × args generator) |
| PROP-507b (static) | The pure-core module source contains no `RegExp`/`.match(`/`.test(` call and no `if (args.` / `switch (slot)`-style branching keyed on model-chosen `args`/`slot` CONTENT (branching on registry bookkeeping fields like `status`/`risk` is allowed and expected) | 0 | true | grep-based CI check (documented, not a formal tool) |
| PROP-508a | Both bounds exhausted → ledger `kind` is never `'wake'`/`'narrate'` and `profitable` is never `true` | 2 | true | vitest/jest exhaustive-case |
| PROP-509a (money-safety-critical) | This feature's implementation diff touches none of: `skills/earn/*/run.sh`, `skills/earn/*/lib/resolve-max-spend.sh`, `skills/_shared/lib/earn-guard.mjs`, `catalog-gate.mjs` threshold constants | 0 | true | `git diff --stat` CI check against an explicit path allowlist |
| PROP-509b (money-safety-critical) | Reroute triggered by a real guard-block (fixture: guard returns `skip`) selects a DIFFERENT slot on retry and never re-invokes the SAME slot with a relaxed/bypassed guard | 2 | true | vitest/jest integration (unmodified guard modules + fixtures) |
| PROP-510a | New ledger fields present on both first-pick-resolved and after-reroute/reprompt-resolved paths; `redactPrivateKeyPatterns` applied before append | 1 | true | vitest/jest |
| PROP-511a (money-safety-critical) | Adversarial mock brain (always no-tool-call OR always no-realized-action) → total `think()` calls per wake ≤ 2, for ALL adversarial sequences up to a bounded exploration depth | 1 | true | fast-check (bounded exhaustive) |
| PROP-512a (closes FIND-004) | A Franklin-identity wake with the flag unset/malformed appends `kind:'always_act_not_engaged'` with `reason` ∈ `{flag_unset, flag_malformed}` on EVERY such wake (not conditioned on go-live having happened); the one-time flag-flip operational action appends `kind:'always_act_go_live'` exactly once | 1 | true | vitest/jest |
| PROP-512b (closes FIND-004) | `isPostGoLiveRegression`/`is_fresh_but_barren`-sibling detector: (a) `always_act_not_engaged` lines with no preceding `always_act_go_live` line never trigger regression-detected; (b) `always_act_go_live` followed by ≥`minRun` consecutive `always_act_not_engaged` lines DOES trigger it; (c) a single `always_act_not_engaged` line surrounded by successfully-engaged wakes after go-live does NOT trigger it | 1 | true | fast-check / pytest (mirrors `earning-health.py`'s own test style) |

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
  the gig/lending classify-gate widening (PROP-506c — closes FIND-002) and the empty-enum reroute terminal
  case (PROP-506d — closes FIND-003), the exhausted-bound truthful-record (PROP-508a), and the
  money-safety-critical guard-block reroute (PROP-509b) — these get EXHAUSTIVE case tables, not random
  sampling, because the state spaces are small and the cost of a missed case (a silent idle wake, a
  silently-still-present sleep tool, an unclassified gig/lending no-op, or a guard bypass) is exactly the
  failure this feature exists to prevent.
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
- `verification/always-act-reroute.property.test.mjs` — runs PROP-505a, 506a/b/c/d, 511a with adversarial
  mock-`think()` sequences, including the `economy/gig`/`economy/lending` classify-gate-widening cases
  (PROP-506c, closes FIND-002) and the empty-enum terminal case (PROP-506d, closes FIND-003).
- `verification/always-act-nojudgment.property.test.mjs` — runs PROP-507a (menu × args generator) +
  PROP-507b (grep check, invoked as a subprocess assertion from the test file so it participates in the
  same test run/report).
- `verification/always-act-moneysafety.test.mjs` — runs PROP-509a (diff-path allowlist) and PROP-509b
  (guard-block integration fixture) — these two are the money-safety-critical gate this feature must
  never regress; CI treats a failure here as blocking regardless of mode (lean or strict).
- `verification/always-act-observability.test.mjs` — runs PROP-512a (go-live/not-engaged ledger `kind`
  lines) and PROP-512b (the post-go-live regression detector, mirroring `earning-health.py`'s own test
  style) — closes spec-review FIND-004.
