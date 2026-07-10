# Verification Architecture — franklin-earn-coldstart-evolution

## Purity Boundary Map

### Pure Core — NEW (deterministic, no I/O, no wall-clock, no randomness except injectable `rng`)
- `replayGenomeAgainstCorpus(genome, corpusEntries)` — REQ-002/REQ-003. Calls `decideEngagement`
  (imported UNCHANGED) per corpus entry with `ageSec: 0`; accumulates `wouldEngageCount`,
  `totalCount`, `simulatedNetUsdc` (fee-adjusted momentum-sign proxy formula, REQ-003).
- `evaluateBacktestRubric({wouldEngageCount, totalCount, simulatedNetUsdc})` — REQ-004. Pure
  threshold gate returning `{passes, reason}`.
- `countConsecutiveSkips(gateTraceLines)` — REQ-007. Pure scan of an in-memory trace-line array,
  no persisted counter file (deliberately trace-derived, cannot drift from the trace itself).
- `shouldForceExploration(streakCount, threshold)` — REQ-007. Pure comparison.
- `selectBottleneckKnob(recentSkipTraceLines)` — REQ-009. Pure tally over already-recorded
  `momentumPct`/`liquidityUsd`/`conviction`/`genome` fields on in-memory trace lines.
- `mutate(genome, { rng, count, forcedDirection })` — REQ-008. Extension of
  `franklin-sol-evolvable-edge`'s existing pure `mutate()`; the new `forcedDirection` parameter is
  additive and optional; base-clamp/step/post-clamp/rounding logic is UNCHANGED.

### Pure Core — REUSED, UNCHANGED (imported, never reimplemented)
- `decideEngagement` (`sol-gate.mjs`) — REQ-002.
- `stripForbidden`, `genomeId`, `SAFE_DEFAULT_GENOME`, `KNOB_KEYS`, `MUTATION_SPEC`,
  `FORBIDDEN_CAP_KEYS` (`sol-genome.mjs`) — REQ-006/REQ-011.
- `evaluatePromotion` (`evolve.mjs`, via `sol-evolve.mjs`'s re-export) — REQ-012 (this feature adds
  NO new implementation; PROP-018 is a regression-parity test only).
- `attributeGenomeIdSol`, `summarizeByGenomeSol` (`sol-evolve.mjs`) — REQ-012, untouched.

### Effectful Shell — NEW
- Reading `state/sol-gate.trace.jsonl` as (a) the backtest replay corpus (REQ-001) and (b) the
  starvation-signal source (REQ-007/009) — a read-only consumer of an ALREADY-WRITTEN file; this
  feature adds no new trace-append call.
- Writing the per-instance `sol-gate-genome-override.json` — REQ-005 (seeding), using the SAME
  `instanceOverridePath()` helper `franklin-sol-evolvable-edge` already exports (no new path
  -resolution logic written).
- The per-pass orchestration wiring inside `sol-gate-cli.mjs`'s `main()` — REQ-015 (fixed ordering:
  starvation-check → forced-mutation-or-backtest-bootstrap → fallback symmetric cadence-mutation).

### Effectful Shell — REUSED, UNCHANGED
- `loadGenome`, `instanceOverridePath` (`sol-genome.mjs`).
- `fetchSolMarketSignal` (`sol-gate.mjs`) — this feature calls it ZERO additional times.
- `promote` (`evolve.mjs`, via `sol-evolve.mjs`) — REQ-012, never called by this feature's new code.
- `appendGateTrace`, `appendGenomeLinkTrace` (`sol-trace.mjs`) — untouched, no new trace shape
  introduced.
- `sol-trade/run.sh`'s identity-match guard and `resolve-max-spend.sh`'s hard-coded `0.25` choke
  point — untouched, zero lines added or modified by this feature.

## Proof Obligations

| ID | Description | REQ | Tier | Required | Tool |
|----|--------------|-----|------|----------|------|
| PROP-001 | Corpus parse from trace lines is defensive: malformed/missing-field lines excluded, never thrown; empty/undersized corpus (< SOL_BACKTEST_MIN_SAMPLES) causes bootstrap to skip the cycle cleanly | REQ-001 | 1 | true | node:test |
| PROP-002 | replayGenomeAgainstCorpus's per-entry wouldEngage/conviction calls are fixture-identical to calling decideEngagement directly with the same arguments (import-identity + fixture-parity, proves no reimplementation drift) | REQ-002 | 0 | true | node:test |
| PROP-003 | simulatedNetUsdc matches the fee-adjusted momentum-sign formula EXACTLY for a corpus with known would-engage entries and known momentumPct values (numeric assertion) | REQ-003 | 2 | true | node:test + fast-check |
| PROP-004 | evaluateBacktestRubric.passes is true iff totalCount>0 AND wouldEngageCount>=MIN_ENGAGE AND ratio<=MAX_ENGAGE_RATIO AND simulatedNetUsdc>0, for randomized input triples | REQ-004 | 2 | true | node:test + fast-check |
| PROP-005 | Across an exhaustive fixture set of rubric-passing scenarios, the ONLY file path ever opened for writing by the backtest-bootstrap code path is sol-gate-genome-override.json — baseline-genome.json is NEVER opened for writing by this code path, under any fixture | REQ-005 | 2 | true | node:test (temp fs, fs.writeFileSync spy asserting call args across every fixture) |
| PROP-006 | evaluatePromotion/promote (spied imported bindings) are never invoked by the backtest-bootstrap code path, for any fixture, including rubric-passing ones | REQ-005/REQ-012 | 0 | true | node:test (spy/mock on imported bindings, call-count assertion) |
| PROP-007 | FORBIDDEN_CAP_KEYS absent from every backtest candidate object, before replay AND before write, for adversarially crafted candidate inputs | REQ-006/REQ-011 | 2 | true | node:test + fast-check |
| PROP-008 | countConsecutiveSkips equals exactly the number of trailing "skip" entries before the first "engage" (or array start), for randomized decision sequences | REQ-007 | 2 | true | node:test + fast-check |
| PROP-009 | shouldForceExploration triggers iff streakCount >= threshold; never below, always at/above | REQ-007 | 1 | true | node:test |
| PROP-010 | WHILE starved with a forcedDirection table supplied, every mutated knob's direction matches the fixed loosen-direction table (momentum/liquidity/conviction: -1; staleness: +1) for EVERY injected rng value covering both branches of the old coin-flip — proves the forced table actually overrides randomness, not merely correlates | REQ-008 | 2 | true | node:test + fast-check (rng injection spanning [0,1)) |
| PROP-011 | WITHOUT forcedDirection (the default, every existing call site), mutate()'s output is BYTE-IDENTICAL to franklin-sol-evolvable-edge's existing, already-hardened behavior — its own existing PROP-002/003 fixtures re-run unchanged against the extended mutate() and MUST still pass verbatim (zero regression) | REQ-008 | 0 | true | node:test (re-executes the sibling feature's own existing test fixtures) |
| PROP-012 | selectBottleneckKnob returns the knob with the highest fail-tally on a fixture with a known-dominant failing condition; deterministic fixed-key-order tie-break verified on an exactly-tied fixture; returns null on an empty or all-zero-tally input | REQ-009 | 1 | true | node:test |
| PROP-013 | countConsecutiveSkips returns 0 immediately following any trace ending in an "engage" line, regardless of the length of the prior skip streak | REQ-010 | 1 | true | node:test |
| PROP-014 | A synthetic fixture engineered to satisfy BOTH a starvation trigger AND a rubric-passing backtest candidate in the same pass results in the STARVED mutation (not the backtest candidate) being the one written to the override file (precedence proof) | REQ-015 | 1 | true | node:test |
| PROP-015 | An exhaustive property sweep across mutate()'s symmetric output, mutate()'s forced-direction output, and every backtest candidate object asserts FORBIDDEN_CAP_KEYS is absent in 100% of generated cases, including adversarially crafted base genomes | REQ-011 | 2 | true | node:test + fast-check (highest-priority money-safety PROP in this feature) |
| PROP-016 | Static source-contract test: no eval(/new Function(/genome-value-derived dynamic import()/require() anywhere in this feature's new module(s) | REQ-014 | 0 | true | node:test (source-text contract test, mirrors execute-yield.mjs's existing pattern) |
| PROP-017 | For two distinct ANICCA_HOME values, this feature's write target (override path) resolves to two distinct paths; a write under one is never visible under the other, for randomized home strings | REQ-013 | 2 | true | node:test + fast-check |
| PROP-018 | Calling evaluatePromotion/promote (via sol-evolve.mjs's runEvolveSol) on the SAME chain-verified fixtures used by franklin-sol-evolvable-edge's own existing tests produces IDENTICAL promote/no-promote verdicts before and after this feature is implemented (regression parity on the money-gate itself) | REQ-012 | 0 | true | node:test (fixture-parity, re-executes sibling feature's own fixtures) |

## Verification Strategy

- **Tier 0** (no formal proof needed — structural/static/import-identity/regression-replay checks):
  PROP-002, PROP-006, PROP-011, PROP-016, PROP-018. These verify REUSE, ABSENCE-OF-CALL, and
  BYTE-IDENTICAL REGRESSION against the sibling feature's own already-hardened fixtures — not new
  numeric behavior under adversarial input.
- **Tier 1** (property tests / fuzzing over realistic, enumerable input domains, standard
  `node:test`): PROP-001, PROP-009, PROP-012, PROP-013, PROP-014. Small, enumerable state spaces
  (a handful of representative trace shapes, threshold-boundary cases, one precedence fixture) —
  full randomized fuzzing is not required because the domains are small and fully enumerable by
  hand-constructed fixtures.
- **Tier 2** (lightweight formal methods — property-based testing with `fast-check` over
  randomized/adversarial inputs, REQUIRED because these are the money-safety-critical or
  correctness-critical surfaces where an untested corner case is either a real-dollar risk or would
  silently defeat this feature's entire purpose): PROP-003 (the simulated-P&L formula — a wrong
  constant or sign here would seed a genome based on a fabricated positive signal), PROP-004 (the
  rubric gate — the single boundary between "seed this candidate" and "don't"), PROP-005 (the
  hard money-safety boundary: this feature must NEVER be able to write `baseline-genome.json`, no
  matter how many rubric-passing fixtures are thrown at it), PROP-007 (forbidden-cap stripping on
  the NEW backtest-candidate write path — the exact bug class that was `franklin-sol-evolvable-edge`'s
  own precedent-setting money-safety proof obligation), PROP-008 (the starvation counter's core
  correctness — if this silently undercounts, the escape valve never fires and the feature does
  nothing; if it silently overcounts, forced exploration fires too eagerly and degrades exploration
  quality), PROP-010 (THE core falsifiable claim of mechanism (b) from the task: "a starvation
  counter at threshold biases the next mutation's direction toward looser thresholds, proven by a
  fixture" — this is the single most important behavioral proof in this entire feature), PROP-015
  (THE core falsifiable claim of the money-safety constraint: "a cap key never appears in any
  genome," swept across every code path this feature adds), PROP-017 (cross-instance isolation —
  money-identity safety, mirrors the sibling feature's own PROP-016 treatment).
- **Tier 3** (strong formal proof — Kani/TLA+-class): NOT REQUIRED for this feature, for the same
  reasons `franklin-sol-evolvable-edge`'s verification architecture already gives: all pure-core
  functions here are small, finite-domain, and fully covered by Tier 1/2 property tests; there is
  no concurrency-critical shared-mutable-state proof obligation (this feature introduces no new
  persisted counter file — REQ-007's starvation signal is derived fresh from the trace file every
  pass, and the override-file write follows the same single-slot-at-a-time convention the sibling
  feature already established) that would justify a Tier 3 model checker.

## Notes for Implementation Phase (2a/2b) — non-normative, carried forward from spec authoring

- REQ-002/PROP-002 requires literally `import { decideEngagement } from "./sol-gate.mjs"` (relative
  path TBD by final module location) — the test for PROP-002 should fail RED if a SOL-backtest-
  specific reimplementation of the threshold formula is introduced instead of the import.
- REQ-012/PROP-006/PROP-018 requires the backtest-bootstrap code path to import
  `evaluatePromotion`/`promote` NOWHERE — a static grep-level check (in addition to the runtime
  spy test) that these identifiers do not appear anywhere in the new backtest/starvation module
  source files is a cheap, high-confidence Tier-0 supplement to PROP-006.
- REQ-005/PROP-005's write-path assertion MUST be tested by actually spying on `fs.writeFileSync`
  (or the equivalent write call) across EVERY rubric-passing fixture in the test suite, not merely
  by code review — this is the single highest-consequence claim in the feature and MUST have
  execution-based, not just structural, evidence.
- REQ-008's `mutate()` extension MUST be implemented as a strict superset of the existing signature
  (`mutate(genome, { rng = Math.random, count, forcedDirection } = {})`) so that every EXISTING call
  site in `sol-gate-cli.mjs` (which calls `mutate(genome)` with no second argument) continues to
  compile and behave identically — PROP-011 is the regression gate for this.
- The exact file locations for the new modules (e.g. `skills/earn/sol-trade/lib/sol-backtest.mjs`,
  `skills/earn/sol-trade/lib/sol-starvation.mjs`) are an implementation-phase decision, not fixed by
  this spec — they MUST follow the existing per-instance/ANICCA_HOME conventions and MUST NOT touch
  any file under `skills/earn/polymarket-trade/` (rail isolation, same mandate as the sibling spec).
- `state/sol-gate.trace.jsonl` does not yet exist on disk in this repo checkout as of spec-authoring
  time (verified 2026-07-10: `cat` on the real path returned ENOENT) — REQ-001's "missing trace
  file → empty corpus → bootstrap skips" edge case is not a hypothetical, it is the CURRENT real
  state, and Phase 2a's tests MUST cover it as a first-class case, not an afterthought.
