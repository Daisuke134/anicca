# Verification Architecture — franklin-alwaysact-skill-router

## Purity Boundary Map

- **Pure Core** (new module(s), e.g. `runtime/loop/always-act-router.mjs`, deterministic, no I/O,
  formally/property verifiable — mirrors the existing purity split of `context.mjs`, `prompt.mjs`,
  `tier.mjs`, `catalog-gate.mjs`, `earn-slot.mjs`):
  - `isEarnActionSlot(name)` — REQ-502: `isEarnSlot(name) || DOCTRINE_EARN_ACTIONS.has(name)` where
    `DOCTRINE_EARN_ACTIONS = {'economy/gig', 'economy/lending'}` is a fixed, doctrine-derived,
    non-inferred set (bookkeeping data, not judgment — same category as `catalog-gate.mjs`'s injected
    `riskTagOf`/`alwaysAvailableOf` classifiers).
  - `assembleAlwaysActMenu({ registry, activeSkillSlots, catalogFilterFn, balanceUsdc,
    reserveThresholdUsdc, riskTagOf, alwaysAvailableOf, hasOpenRiskPositionOf })` — REQ-502/503: pure
    composition of `liveSlotNames`-equivalent filtering + `isEarnActionSlot` + `filterCatalog`
    (`catalog-gate.mjs`, injected as a function reference, never re-implemented).
  - `buildAlwaysActToolDefinitions(menuSlots)` — REQ-504: `getToolDefinitions`-shaped output, `sleep`
    tool omitted, `slot.enum = menuSlots`.
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

- **Effectful Shell** (extended, not replaced):
  - `runtime/loop/index.mjs` — the wake-loop orchestration: identity-gate check (REQ-501, calls
    `wallet-address-solana.mjs` subprocess twice, exactly mirroring `sol-trade/run.sh:35-41`), the
    reprompt/reroute retry loop (calls `think()` up to REQ-511's bound), calling
    `classifyEarnResult`/`appendHarnessFailure`/`safeAppend` (all pre-existing, unmodified).
  - `runtime/loop/brain.mjs::think()` — unmodified; called with different `ctx`/tool-definition inputs
    on the reprompt/reroute path, same function contract.
  - Every skill's own `run.sh` (`skills/earn/*/run.sh`, `skills/economy/*`) and its money-safety guards —
    entirely unmodified, out of this feature's write-scope (REQ-509).

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
| PROP-504a | Always-act tool definitions never include a tool named `sleep`, for ANY menu | 1 | true | fast-check |
| PROP-505a | No-tool-call response → exactly 2 `think()` calls total (1 reprompt), never 1, never 3+ | 1 | true | fast-check (adversarial mock sequences) |
| PROP-506a | Picked slot with `earnLine === null` → exactly one reroute call with that slot excluded from the enum | 1 | true | fast-check |
| PROP-506b | Picked slot with `earnLine !== null` (any `profitable` value) → zero reroute calls (immediate accept) | 1 | true | fast-check |
| PROP-507a (money-safety-critical) | For every slot `s` in an arbitrary generated menu, given a mocked brain returning `run_skill({slot:s, args:A})` for arbitrary `A`, the harness executes exactly `(s, A)` — no substitution, no ranking, no filtering by `A`'s content | 1 | true | fast-check (menu × args generator) |
| PROP-507b (static) | The pure-core module source contains no `RegExp`/`.match(`/`.test(` call and no `if (args.` / `switch (slot)`-style branching keyed on model-chosen `args`/`slot` CONTENT (branching on registry bookkeeping fields like `status`/`risk` is allowed and expected) | 0 | true | grep-based CI check (documented, not a formal tool) |
| PROP-508a | Both bounds exhausted → ledger `kind` is never `'wake'`/`'narrate'` and `profitable` is never `true` | 2 | true | vitest/jest exhaustive-case |
| PROP-509a (money-safety-critical) | This feature's implementation diff touches none of: `skills/earn/*/run.sh`, `skills/earn/*/lib/resolve-max-spend.sh`, `skills/_shared/lib/earn-guard.mjs`, `catalog-gate.mjs` threshold constants | 0 | true | `git diff --stat` CI check against an explicit path allowlist |
| PROP-509b (money-safety-critical) | Reroute triggered by a real guard-block (fixture: guard returns `skip`) selects a DIFFERENT slot on retry and never re-invokes the SAME slot with a relaxed/bypassed guard | 2 | true | vitest/jest integration (unmodified guard modules + fixtures) |
| PROP-510a | New ledger fields present on both first-pick-resolved and after-reroute/reprompt-resolved paths; `redactPrivateKeyPatterns` applied before append | 1 | true | vitest/jest |
| PROP-511a (money-safety-critical) | Adversarial mock brain (always no-tool-call OR always no-realized-action) → total `think()` calls per wake ≤ 2, for ALL adversarial sequences up to a bounded exploration depth | 1 | true | fast-check (bounded exhaustive) |

## Verification Strategy

- **Tier 0** (no formal proof needed — CI/static checks suffice): prompt wording/non-functional strings;
  PROP-507b's grep-based no-regex-branching check; PROP-509a's diff-path allowlist check. These are cheap,
  deterministic, and directly falsifiable by `grep`/`git diff` — no property-test framework adds value.
- **Tier 1** (property tests / fuzzing over the pure core): all `assembleAlwaysActMenu`,
  `isEarnActionSlot`, `noRealizedAction`, `nextRerouteState`, `buildAlwaysActToolDefinitions` obligations
  (PROP-502a/b, 503a, 504a, 505a, 506a/b, 507a, 510a, 511a) — these are pure, small-domain functions ideal
  for `fast-check` (the project's language is JavaScript/`.mjs`; `fast-check` is the JS-ecosystem
  equivalent of `hypothesis`/`kani` named in the template, and is the standard choice already implied by
  this repo's existing pure-function-heavy `runtime/loop/*.mjs` modules — no new exotic dependency).
- **Tier 2** (lightweight formal methods — exhaustive case enumeration over small finite state spaces):
  the identity-gate (PROP-501a/b/c — 2×2×3 finite combinations of {match/mismatch/error} × {flag
  set/unset/malformed}, fully enumerable, no sampling needed), the empty-menu failure mode (PROP-502d),
  the reserve carve-out (PROP-503b), the exhausted-bound truthful-record (PROP-508a), and the
  money-safety-critical guard-block reroute (PROP-509b) — these get EXHAUSTIVE case tables, not random
  sampling, because the state spaces are small and the cost of a missed case (a silent idle wake, or a
  guard bypass) is exactly the failure this feature exists to prevent.
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
it must never import or execute any `run.sh`, CLI, or network-touching code. A test that spawns
`franklin-trading`, reads/writes `~/.blockrun`, or hits a real RPC/x402 endpoint fails Phase 2a/2b review
outright, regardless of its assertions.

## Phase 5 Verification Harness Plan (for later `verification/` phase)

- `verification/always-act-menu.property.test.mjs` — runs PROP-502a/b/c/d, 503a/b as `fast-check`
  properties + literal fixtures.
- `verification/always-act-reroute.property.test.mjs` — runs PROP-505a, 506a/b, 511a with adversarial
  mock-`think()` sequences.
- `verification/always-act-nojudgment.property.test.mjs` — runs PROP-507a (menu × args generator) +
  PROP-507b (grep check, invoked as a subprocess assertion from the test file so it participates in the
  same test run/report).
- `verification/always-act-moneysafety.test.mjs` — runs PROP-509a (diff-path allowlist) and PROP-509b
  (guard-block integration fixture) — these two are the money-safety-critical gate this feature must
  never regress; CI treats a failure here as blocking regardless of mode (lean or strict).
