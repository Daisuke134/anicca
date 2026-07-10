# Purity Boundary Audit

## Feature: franklin-sol-evolvable-edge | Sprint: 1 | Date: 2026-07-10

Method: read every function named in `specs/verification-architecture.md`'s Purity Boundary Map
directly from the worktree source (`~/anicca/.worktrees/franklin-sol-edge`, commit `42b35c6`) and
grepped each declared-pure function body for `fs.`, `fetch(`, uninjected `Date.now()`/`new Date()`,
and uninjected `Math.random()`. Cross-referenced against the Semgrep scan and PROP-018's automated
source-text contract test.

## Declared Boundaries (from specs/verification-architecture.md)

### Pure Core
- SOL genome constants: `KNOB_KEYS`, `SAFE_DEFAULT_GENOME`, `MUTATION_SPEC`, `FORBIDDEN_CAP_KEYS`
- `stripForbidden(genomeObj)`
- `mutate(genome, { rng, count })`
- `genomeId(genome)`
- `decideEngagement({ momentumPct, liquidityUsd, ageSec, genome, liveEnabled })`
- `attributeGenomeIdSol(ledgerRow, traceLines)`
- `summarizeByGenomeSol(ledgerRows, traceLines)`
- `evaluatePromotion` (imported unchanged from `evolve.mjs`, already pure/tested there)

### Effectful Shell
- `loadGenome({ home })` — disk reads
- `fetchSolMarketSignal(mint, opts)` — HTTP GET + local cache read/write
- Trace-line appends (`sol-gate.trace.jsonl`, `sol-trade.trace.jsonl`)
- `promote(genome, opts)` — writes `baseline-genome.json`, git add/commit (imported unchanged)
- `sol-trade/run.sh` wiring: identity-match guard, pre-gate invocation ordering,
  `SOL_TRADE_MAX_SPEND` hard-override choke point, `franklin-trading start` invocation
- `resolveSolanaSecret`/wallet-derivation (existing, unchanged, out of this feature's scope)

## Observed Boundaries (actual implementation, this session)

| Declared | File:approx line | Observed | Match? |
|---|---|---|---|
| `KNOB_KEYS`/`SAFE_DEFAULT_GENOME`/`MUTATION_SPEC`/`FORBIDDEN_CAP_KEYS` | `sol-genome.mjs:29-58` | `Object.freeze` constants, no I/O | match |
| `stripForbidden` | `sol-genome.mjs:66-70` | spread + delete, no I/O, returns new object | match |
| `mutate` | `sol-genome.mjs:164-193` | pure arithmetic over `rng` param (default `Math.random`, injectable in every call site tested); no `fs`/`fetch`; returns new object | match |
| `genomeId` | `sol-genome.mjs:200-205` | pure `crypto.createHash` over sorted-key JSON, no I/O | match |
| `decideEngagement` | `sol-gate.mjs:51-87` | pure arithmetic/comparisons only, no `fs`/`fetch`/`Date`/`Math.random` | match |
| `attributeGenomeIdSol` | `sol-evolve.mjs:79-89` | pure loop over the two array arguments only; compares `ts` fields exclusively, no market/task/mint field read | match — confirmed additionally by dedicated structural test |
| `summarizeByGenomeSol` | `sol-evolve.mjs:100-114` | pure loop/accumulation over array arguments only, no I/O | match |
| `evaluatePromotion` | `sol-evolve.mjs:34,37` (`import ... from "../../lib/evolve.mjs"`, re-exported) | same function object as `evolve.mjs`'s own (verified by reference-equality test PROP-014), no local reimplementation exists | match |
| `loadGenome` | `sol-genome.mjs:143-152` | reads `canonicalPath` + `instanceOverridePath(home)` via `fs.readFileSync` (through `readJsonSafe`), fails closed on error | match (effectful, as declared) |
| `fetchSolMarketSignal` | `sol-gate.mjs:104-172` | `fetch`/`AbortController` + `fs` cache read/write, bounded timeout, never throws | match (effectful, as declared) |
| Trace-line appends | `sol-trace.mjs:11-59` (`appendGateTrace`/`appendGenomeLinkTrace`) | `fs.appendFileSync` inside try/catch, fail-soft | match (effectful, as declared) |
| `promote` | `sol-evolve.mjs:34,37` (imported, re-exported) | same imported function object as `evolve.mjs`'s own (verified by reference-equality test PROP-015b) | match (effectful, as declared, no reimplementation) |
| `run.sh` wiring | `run.sh:1-159` | identity-match guard (lines 28-37), earn-guard (39-44), SOL pre-gate invocation (77-93), `resolve-max-spend.sh` hard-override (99), `franklin-trading start` (101) — in that order | match |
| `resolve-max-spend.sh` choke point | `lib/resolve-max-spend.sh:1-10` | unconditional `echo "0.25"`, zero env reads, positioned in `run.sh` AFTER genome eval / BEFORE `franklin-trading start` | match |
| `resolveSolanaSecret`/wallet-derivation | out of scope | not touched by any file in this feature's scope (confirmed by diff scope — this audit's file list is exactly the 8 files named in the task, none of which is `resolveSolanaSecret`) | match (untouched, as required) |

### Additional observation: `sol-gate-cli.mjs` (effectful orchestrator, not separately named in the Purity Map but implied by "no new decision logic")

`sol-gate-cli.mjs` composes the pure functions (`loadGenome`, `mutate`, `genomeId`,
`decideEngagement`) with the effectful ones (`fetchSolMarketSignal`, `appendGateTrace`,
`appendGenomeLinkTrace`) inside a single `main()`. Read the full file: it contains no independent
decision logic of its own — every branch (`engage`, `mode`, `decision`) is a direct read of a value
already computed by `decideEngagement` or `isLiveEnabled`. This matches its own doc comment ("No
new decision logic lives in this file") and the Purity Map's implicit classification of it as pure
orchestration wiring, not a hidden pure/effectful boundary violation.

## Mismatches / Drift

**None detected.** Every function classified as Pure Core in the spec is, on direct source
inspection, free of `fs`/`fetch`/uninjected wall-clock/uninjected randomness. Every function
classified as Effectful Shell performs exactly the I/O the spec describes and no more. No hidden
side effects were found in any "pure" function; no pure-looking function secretly does I/O; no
effectful function does undeclared I/O (e.g. `fetchSolMarketSignal` touches only its own cache
directory under this instance's state path, never a shared/ambient path — consistent with
PROP-016's cross-instance isolation guarantee, independently verified by that test).

No evolved-code path exists: `decideEngagement` is the SAME function regardless of which genome
(baseline or mutant) is passed to it — genome data only ever supplies numeric knob VALUES, never
new code, confirmed by PROP-018's static source-text contract (no `eval`/`new Function`/
variable-derived `import()`) and its runtime edge case (a malformed genome value with literal
`"eval('1')"` string content never reaches a code-execution sink — `decideEngagement` just fails
closed via `Number.isFinite` guards).

## Summary

No drift detected between the declared Purity Boundary Map (specs/verification-architecture.md)
and the observed implementation (worktree commit `42b35c6`). All 7 declared pure-core surfaces are
genuinely free of I/O, wall-clock, and non-injectable randomness. All 6 declared effectful-shell
surfaces perform only their declared I/O, no more. No verifier-hostile coupling (no pure function
calls an effectful one; no effectful function embeds hidden decision logic beyond composing already-
tested pure functions). No follow-up required before Phase 6.
