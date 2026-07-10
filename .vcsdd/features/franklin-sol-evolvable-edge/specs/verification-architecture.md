# Verification Architecture — franklin-sol-evolvable-edge

## Purity Boundary Map

### Pure Core (deterministic, no I/O, no wall-clock, no randomness except injectable `rng`)
- SOL genome constants: `KNOB_KEYS`, `SAFE_DEFAULT_GENOME`, `MUTATION_SPEC`, `FORBIDDEN_CAP_KEYS`.
- `stripForbidden(genomeObj)` — REQ-004.
- `mutate(genome, { rng, count })` — REQ-002/REQ-003 (3-layer clamp; categorical key untouched).
- `genomeId(genome)` — REQ-005 (sorted-key canonical hash, post-strip).
- `decideEngagement({ momentumPct, liquidityUsd, ageSec, genome, liveEnabled })` — REQ-008/009
  (conviction scoring + threshold gate + paper-mode override). THE single most safety-critical
  pure function in this feature.
- `attributeGenomeIdSol(ledgerRow, traceLines)` — REQ-012/013 (timestamp-ordered join, given
  arrays already in memory; no I/O itself).
- `summarizeByGenomeSol(ledgerRows, traceLines)` — REQ-013 (HARD gate: `source==="sol-trade" &&
  sig present && confirmed===true`, pure given arrays).
- `evaluatePromotion` — REQ-014 (imported unchanged from `evolve.mjs`; already pure, already
  tested there; this feature adds NO new implementation of this function, only a wiring/reuse
  test).

### Effectful Shell (I/O, network, git, process invocation)
- `loadGenome({ home })` — reads canonical + override JSON files from disk (REQ-006).
- `fetchSolMarketSignal(mint, opts)` — HTTP GET to Jupiter Price v3, local cache read/write
  (REQ-007).
- Trace-line appends (`state/sol-gate.trace.jsonl`, `state/sol-trade.trace.jsonl`) — REQ-011/012.
- `promote(genome, opts)` — writes `baseline-genome.json`, path-scoped `git add`/`git commit`
  (REQ-015).
- `sol-trade/run.sh` wiring: identity-match guard (existing, unchanged), pre-gate invocation
  ordering, `SOL_TRADE_MAX_SPEND` hard-override choke point (REQ-017), `franklin-trading start`
  invocation itself (REQ-010's descriptive-only context boundary).
- `resolveSolanaSecret`/wallet-derivation (existing, unchanged — REQ-016 only requires this
  feature run strictly AFTER it, never reimplement it).

## Proof Obligations

| ID | Description | REQ | Tier | Required | Tool |
|----|--------------|-----|------|----------|------|
| PROP-001 | SOL SAFE_DEFAULT_GENOME has exactly the 5 stated keys/defaults; disjoint from FORBIDDEN_CAP_KEYS | REQ-001 | 0 | true | node:test |
| PROP-002 | mutate() output always within [min,max] for every numeric knob, for randomized/malformed input genomes (property-based) | REQ-002 | 2 | true | node:test + fast-check |
| PROP-003 | mutate() never alters SOL_GATE_WATCHLIST; never selects it or FORBIDDEN_CAP_KEYS from its pool | REQ-003 | 1 | true | node:test |
| PROP-004 | stripForbidden() removes SOL_TRADE_MAX_SPEND from every input, including adversarially crafted objects | REQ-004 | 2 | true | node:test + fast-check |
| PROP-005 | genomeId() is order-independent and cap-presence-independent; different knob values -> different ids | REQ-005 | 1 | true | node:test |
| PROP-006 | loadGenome() never throws on missing/malformed canonical or override files; override wins per-key; fails closed to SAFE_DEFAULT | REQ-006 | 1 | true | node:test |
| PROP-007 | fetchSolMarketSignal() never throws; missing/NaN fields -> "no signal"; stale-cache fallback respects SOL_GATE_MAX_STALENESS_SEC boundary exactly | REQ-007 | 1 | true | node:test (fetchImpl injected, no real network) |
| PROP-008 | decideEngagement(): wouldEngage true iff all 3 threshold conditions hold; NaN/Infinity inputs -> false; direction-agnostic (abs) | REQ-008 | 2 | true | node:test + fast-check |
| PROP-009 | SOL_GATE_LIVE_ENABLE unset/not-exactly-"1" -> engage always false regardless of wouldEngage (HARD dev-safety) | REQ-009 | 2 | true | node:test + fast-check |
| PROP-010 | Any payload contributed to franklin-trading's invocation context contains no action/side/size directive token, only observation fields | REQ-010 | 1 | true | node:test (schema/regex contract test on the contributed payload shape) |
| PROP-011 | Every pass (paper or live, engage or skip) appends exactly one sol-gate.trace.jsonl line with the required fields | REQ-011 | 1 | true | node:test |
| PROP-012 | Every engage===true pass writes a genome-linked line into sol-trade.trace.jsonl with ts <= the pass's live-pass line | REQ-012 | 1 | true | node:test |
| PROP-013 | summarizeByGenomeSol() counts ONLY rows with source==="sol-trade" && sig present && confirmed===true; excludes all others (mixed synthetic ledger) | REQ-013 | 2 | true | node:test + fast-check |
| PROP-014 | SOL wiring's promotion verdicts are IDENTICAL to calling evolve.mjs's evaluatePromotion() directly on the same fixtures (no reimplementation drift) | REQ-014 | 0 | true | node:test (import-identity + fixture-parity check) |
| PROP-015 | promote() commits ONLY the SOL canonical baseline-genome.json path; git show --stat touches exactly one file | REQ-015 | 1 | true | node:test (temp git repo, execFileSync git show --stat) |
| PROP-016 | instanceOverridePath(homeA) !== instanceOverridePath(homeB) for distinct homes; loading under homeA never reflects a write under homeB | REQ-016 | 2 | true | node:test + fast-check (randomized home strings) |
| PROP-017 | SOL_TRADE_MAX_SPEND env pre-set to an attacker value before the pre-gate runs has zero effect on the value passed to franklin-trading --max-spend | REQ-017 | 2 | true | node:test (bash subshell exec of the hardened run.sh choke point, asserting the resolved flag value) |
| PROP-018 | Source-contract test: no eval(/new Function(/genome-value-derived dynamic import in the pre-gate decision or invocation code path | REQ-018 | 0 | true | node:test (static source-text contract test, mirrors execute-yield.mjs's deposit-guard wiring test pattern) |

## Verification Strategy

- **Tier 0** (no formal proof needed — structural/static/import-identity checks): PROP-001,
  PROP-014, PROP-018. These verify SHAPE and REUSE, not numeric behavior under adversarial input.
- **Tier 1** (property tests / fuzzing over realistic input domains, standard `node:test`):
  PROP-003, PROP-005, PROP-006, PROP-007, PROP-010, PROP-011, PROP-012, PROP-015. These cover the
  I/O-adjacent and shape-correctness surfaces where a fixed table of representative cases (missing
  file, malformed JSON, empty override, multi-mint fetch, concurrent trace lines) is sufficient —
  full randomized fuzzing is not required because the state space is small and enumerable.
- **Tier 2** (lightweight formal methods — property-based testing with `fast-check` over randomized/
  adversarial inputs, REQUIRED because these are the money-safety-critical surfaces where an
  untested corner case is a real-dollar risk): PROP-002 (mutation clamp — an unbounded knob could
  degrade the pre-gate into always-engage or never-engage), PROP-004 (forbidden-cap stripping — the
  exact class of bug that was the PM feature's adversary MUST-FIX precedent), PROP-008 (the core
  engage-decision scoring function — this is the money-path judgment surface), PROP-009 (dev-safety
  paper-mode override — the single most important "must never place a live trade prematurely"
  invariant in this entire feature), PROP-013 (earnings-gate row-counting — this is the SOL analog
  of PM's HARD 0.24, and the field-name correction (`sig`/`confirmed` vs `tx`/`status`) found during
  spec authoring makes this the single highest-risk-of-a-silent-bug surface in the feature), PROP-016
  (cross-instance isolation — money-identity safety), PROP-017 (the cap hard-override choke point —
  the single line standing between a compromised/malformed genome and an uncapped spend).
- **Tier 3** (strong formal proof — Kani/TLA+-class): NOT REQUIRED for this feature. The pure core
  functions are small, finite-domain, and fully covered by Tier 1/2 property tests; there is no
  concurrency-critical shared-mutable-state proof obligation (each instance's genome state is
  file-isolated per REQ-016, and trace appends follow the codebase's existing single-slot-at-a-time
  convention) that would justify the cost of a Tier 3 model checker for this feature.

## Notes for Implementation Phase (2a/2b) — non-normative, carried forward from spec authoring

- REQ-014/PROP-014 requires literally `import { evaluatePromotion } from
  "../../lib/evolve.mjs"` (or the correct relative path once the SOL module's location is fixed)
  rather than a re-implementation — the test for PROP-014 should fail RED if a SOL-specific
  reimplementation is introduced instead of the import.
- REQ-013's field-name correction (`sig`/`confirmed`, not `tx`/`status`) MUST be re-verified against
  `record-swap.mjs`'s CURRENT shape at implementation time, in case that module changes between
  this spec and Phase 2a.
- The exact file locations for the new SOL genome/evolve modules (e.g.
  `skills/earn/sol-trade/lib/sol-genome.mjs`, `skills/earn/sol-trade/lib/sol-evolve.mjs`,
  `skills/earn/sol-trade/baseline-genome.json`) are an implementation-phase decision, not fixed by
  this spec — they MUST follow the existing per-instance/ANICCA_HOME conventions and MUST NOT touch
  any file under `skills/earn/polymarket-trade/` (rail isolation).
