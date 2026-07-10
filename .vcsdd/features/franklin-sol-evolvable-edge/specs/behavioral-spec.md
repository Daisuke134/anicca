# Behavioral Spec — franklin-sol-evolvable-edge (C1: Franklin's SOL rail evolvable, earnings-gated edge)

**Status**: Phase 1a (behavioral spec). Approach B (fresh grounding finding, 2026-07-10): a NEW local
pre-gate harness that runs BEFORE `franklin-trading start`. Approach A (tune the CLI's own flags) is
CONFIRMED INFEASIBLE — `franklin-trading@0.2.4 start --help` exposes no strategy knobs, only
`-m/--model --trust --max-spend -p/--prompt --from -r/--resume -c/--continue`.

## Provenance (copy+tweak, do not reinvent)

This spec structurally mirrors the PROVEN, live, adversary-hardened PM #19 EVOLVE mechanism:
- `~/anicca/skills/earn/lib/genome.mjs` (KNOB_KEYS / SAFE_DEFAULT_GENOME / MUTATION_SPEC /
  FORBIDDEN_CAP_KEYS / stripForbidden / loadGenome / mutate / genomeId / toExportLines /
  shouldMutateThisPass).
- `~/anicca/skills/earn/lib/evolve.mjs` (readTrace / buildGenomeIndex / attributeGenomeId /
  summarizeByGenome / evaluatePromotion / promote / runEvolve), spec
  `docs/superpowers/specs/2026-07-05-evolve-earnings-gated-self-improve-design.md`.
- `~/anicca/skills/earn/polymarket-trade/run.sh:69-138` (#19 EVOLVE wiring: load_genome →
  env knobs → pick.py; caps hard-overridden AFTER genome eval, at a single choke point).

Every REQ below states explicitly which PM artifact it mirrors. Where SOL's real field names/shape
differ from PM's (confirmed by reading `sol-trade/lib/record-swap.mjs`), this spec calls the
difference out explicitly rather than silently assuming PM's names carry over.

## Grounded empirical finding (used to fix REQ-007's design — verified 2026-07-10, not assumed)

`curl https://lite-api.jup.ag/price/v3?ids=<mint>` (no API key, no signup) returned, live, HTTP 200:
```json
{"So11111111111111111111111111111111111111112":{"createdAt":"2024-06-05T08:55:25.527Z",
"liquidity":668904234.36,"usdPrice":79.03,"blockId":431926834,"decimals":9,"priceChange24h":2.66}}
```
This is a genuinely FREE (no paid dependency, no key) Solana market-data source providing
`usdPrice`, `priceChange24h` (fixed 24h window — NOT a configurable "momentum window"; the design
doc's original "momentum-window" knob idea is DROPPED because the free source has no configurable
window), and `liquidity` (an aggregate USD liquidity figure). It has **no per-quote freshness/asOf
field** of its own (`createdAt` is the TOKEN's creation date, not the quote time) — see REQ-007 for
how staleness is therefore defined (locally, not from the API payload).

## Purity Boundary Analysis (summary — full map in verification-architecture.md)

- **Pure core**: genome knob table + defaults + mutation ranges + forbidden-cap stripping;
  `genomeId()`; the engage-decision scoring function (`decideEngagement`); the SOL-specific
  earnings-attribution join (`attributeGenomeIdSol`, REQ-012b, TIMESTAMP-ONLY nearest-preceding
  match — NOT a market/task-field match, `summarizeByGenomeSol`, REQ-013, summing `row.net_usdc`
  win-OR-loss); the promotion gate (`evaluatePromotion`, REUSED verbatim from `evolve.mjs`, never
  reimplemented).
- **Effectful shell**: reading/writing the per-instance genome override file; the Jupiter Price v3
  HTTP fetch; trace-line appends; the canonical baseline-genome git commit (`promote()`, REUSED
  verbatim from `evolve.mjs`, never reimplemented — REQ-015); invoking `franklin-trading start`;
  the identity-match guard's wallet derivation.

## Requirements

### REQ-001: SOL genome knob definition + safe defaults
**Mirrors**: `genome.mjs` KNOB_KEYS + SAFE_DEFAULT_GENOME.
**EARS**: THE SYSTEM SHALL define a SOL_GATE genome consisting of exactly five knobs:
`SOL_GATE_MIN_MOMENTUM_PCT` (default 2.0), `SOL_GATE_MIN_LIQUIDITY_USD` (default 1000000),
`SOL_GATE_MIN_CONVICTION` (default 6), `SOL_GATE_MAX_STALENESS_SEC` (default 300), and
`SOL_GATE_WATCHLIST` (default `"So11111111111111111111111111111111111111112"`, the wrapped-SOL
mint — matching the EXISTING sol-trade PROMPT's "liquid token (SOL, major)" scope, not invented).
**Edge Cases**:
- Unknown extra key present in a genome object: MUST be ignored/dropped wherever the genome is
  read for export, never silently passed through to an engage decision.
**Acceptance Criteria**:
- `SAFE_DEFAULT_GENOME` (SOL variant) contains exactly these 5 keys with the stated default values.
- None of the 5 keys collides with `FORBIDDEN_CAP_KEYS` (REQ-004).

### REQ-002: Numeric-knob mutation ranges with 3-layer clamp
**Mirrors**: `genome.mjs` `MUTATION_SPEC` + `mutate()`'s base-clamp / post-step-clamp /
post-rounding-clamp defense-in-depth.
**EARS**: WHEN the harness explores a new generation THE SYSTEM SHALL mutate 1-2 of the four
NUMERIC knobs only, each by its own fixed step in a randomly chosen direction, clamped to a fixed
`[min, max]` range BEFORE stepping, AFTER stepping, and AFTER rounding:
- `SOL_GATE_MIN_MOMENTUM_PCT`: step 0.5, range [0.5, 8.0], 1 decimal.
- `SOL_GATE_MIN_LIQUIDITY_USD`: step 250000, range [100000, 5000000], 0 decimals.
- `SOL_GATE_MIN_CONVICTION`: step 1, range [3, 10], 0 decimals.
- `SOL_GATE_MAX_STALENESS_SEC`: step 60, range [60, 900], 0 decimals.
**Edge Cases**:
- A genome fed into `mutate()` that already carries an out-of-range value (malformed override
  file, or repeated mutation-of-a-mutation across many passes) MUST be re-anchored into range
  BEFORE stepping, so no excursion can compound outward across generations.
- `mutate()` MUST return a NEW object; it MUST NOT mutate its input argument (coding-style.md).
**Acceptance Criteria**:
- For every numeric knob and every random seed, the mutated value always lands within
  `[min, max]` inclusive.
- `SOL_GATE_WATCHLIST` and any `FORBIDDEN_CAP_KEYS` are NEVER selected by the mutation pool.

### REQ-003: Categorical watchlist knob is carried but never mutated
**Mirrors**: `genome.mjs`'s treatment of `EARN_CONSENSUS_MODELS` (categorical, carried in the
genome, exported, but excluded from `MUTATION_SPEC` because swapping the model/token roster is a
judgment/scope call, not a numeric-knob nudge).
**EARS**: THE SYSTEM SHALL carry `SOL_GATE_WATCHLIST` through `loadGenome`/`genomeId`/export
unchanged by mutation, until a future spec explicitly widens `mutate()`'s scope.
**Edge Cases**:
- An instance override file that sets `SOL_GATE_WATCHLIST` to an empty string or a malformed mint
  list MUST fail closed to the SAFE_DEFAULT watchlist (never an empty eligible universe silently
  treated as "everything").
**Acceptance Criteria**:
- `mutate()` output's `SOL_GATE_WATCHLIST` value is byte-identical to its input's for every call.

### REQ-004: Money-safety caps are permanently outside the genome
**Mirrors**: `genome.mjs` `FORBIDDEN_CAP_KEYS` + `stripForbidden()` (defense-in-depth: stripped
from baseline, override, AND mutated output, even from a maliciously/accidentally crafted file).
**EARS**: THE SYSTEM SHALL define `FORBIDDEN_CAP_KEYS = ["SOL_TRADE_MAX_SPEND"]` for the SOL genome
and SHALL strip these keys from every genome object the module ever produces (canonical baseline
read, instance override read, merged load, and every mutated output), regardless of whether an
on-disk file (legitimately or maliciously) contains them.
**Edge Cases**:
- A genome-override file on disk that sets `SOL_TRADE_MAX_SPEND` MUST have that key silently
  dropped by every read path — it MUST NOT reach `toExportLines()` or any shell `eval`.
- Any future per-pass spend/position/order-size cap introduced for the SOL rail MUST be added to
  `FORBIDDEN_CAP_KEYS` in the same commit that introduces it — the genome module's knob list and
  the cap list MUST remain disjoint at all times (structural invariant, not a one-time check).
**Acceptance Criteria**:
- `stripForbidden(anyObjectIncludingSOL_TRADE_MAX_SPEND)` never contains `SOL_TRADE_MAX_SPEND` in
  its output, for every input including adversarially crafted ones.

### REQ-005: Deterministic content-hash genome id
**Mirrors**: `genome.mjs` `genomeId()` (sorted-keys canonical JSON, sha256, 12-char slice, hashed
AFTER forbidden-cap stripping so cap presence/absence can never change a genome's identity).
**EARS**: THE SYSTEM SHALL compute a genome's id as a deterministic content hash of its
(forbidden-cap-stripped) knob values, independent of key insertion order.
**Edge Cases**:
- Two genome objects with identical knob values but different key ordering MUST produce the same id.
- A genome differing only in a forbidden-cap key's presence/value MUST produce the same id as the
  same genome without that key.
**Acceptance Criteria**:
- `genomeId(g1) === genomeId(g2)` whenever `stripForbidden(g1)` deep-equals `stripForbidden(g2)`
  modulo key order; different knob values MUST produce different ids (collision-resistant hash).

### REQ-006: Per-instance genome load, fail-closed to safe defaults
**Mirrors**: `genome.mjs` `loadGenome()` + `instanceOverridePath()` (ANICCA_HOME-gated, canonical
baseline merged with the instance's own current-generation override, override wins per-key, never
throws).
**EARS**: WHEN the SOL pre-gate starts a pass THE SYSTEM SHALL load the SOL genome as: the
canonical SOL baseline (or SAFE_DEFAULT_GENOME if the canonical file is missing/malformed) merged
with THIS instance's own override file at
`$ANICCA_HOME/skills/earn/state/sol-gate-genome-override.json` (override wins per-key), with the
result always passed through `stripForbidden` (REQ-004).
**Edge Cases**:
- Canonical baseline file missing, empty, or containing invalid JSON: fall back to
  SAFE_DEFAULT_GENOME — never throw, never crash the pass.
- Instance override file missing: baseline alone is used (equivalent to an empty override).
- `ANICCA_HOME` unset: resolve to `$HOME/.anicca` exactly like `genome.mjs`'s existing convention
  (never fall back to a shared/ambient path — see REQ-016 for the full identity-safety statement).
**Acceptance Criteria**:
- `loadGenome()` never throws for any combination of missing/malformed canonical + override files.
- Override keys strictly win over baseline keys; keys absent from both come from
  SAFE_DEFAULT_GENOME.

### REQ-007: Free Solana market-signal fetch, fail-closed, locally-bounded staleness
**New component (no PM analog)** — grounded on the empirical finding above.
**EARS**: WHEN the SOL pre-gate evaluates a watchlist mint THE SYSTEM SHALL fetch
`usdPrice`, `priceChange24h`, and `liquidity` from the free, unauthenticated Jupiter Price v3
endpoint (`https://lite-api.jup.ag/price/v3?ids=<mint>`, overridable via env for testing) with a
bounded timeout (MUST NOT exceed 8 seconds), and SHALL cache the last successful fetch (value +
local wall-clock timestamp) per mint under this instance's own state directory.
**EARS (staleness)**: BECAUSE the endpoint's payload carries no per-quote freshness field
(`createdAt` is the token's creation date, not the quote time — verified empirically), IF a fresh
fetch fails (network error, non-200, timeout, malformed JSON) THE SYSTEM SHALL fall back to the
last locally-cached snapshot for that mint ONLY IF its LOCAL fetch timestamp is no older than
`SOL_GATE_MAX_STALENESS_SEC`; otherwise THE SYSTEM SHALL treat the mint as having no usable signal
this pass (fail-closed to "skip", not to a guessed/zero value).
**Edge Cases**:
- No cached snapshot exists yet (cold start) and the live fetch fails: skip this mint this pass,
  no crash, no fabricated signal.
- `priceChange24h` or `liquidity` missing/null/NaN in the response: treat as no usable signal,
  skip this mint this pass.
- Multiple mints in `SOL_GATE_WATCHLIST`: each is fetched/cached independently; one mint's failure
  MUST NOT block evaluation of the others.
**Acceptance Criteria**:
- The fetch function never throws to its caller; every failure path returns a typed "no signal"
  result that `decideEngagement` (REQ-008) treats as "skip".
- A fresh, successful fetch is ALWAYS preferred over a cached snapshot, regardless of the cached
  snapshot's age.

### REQ-008: Pure engage-decision function
**Mirrors, in ROLE, the "exploration knob → threshold gate" pattern of PM's MIN_EDGE/MIN_CONF**
(pick.py's own env-driven thresholds), reimplemented as a local deterministic scoring function
because there is no external CLI knob surface to feed (see grounding finding, top of this doc).
**EARS**: GIVEN a momentum percentage, a liquidity figure (USD), an age-of-signal indicator, and
the current genome, THE SYSTEM SHALL compute:
- `momentum_component = min(5, (abs(momentumPct) / genome.SOL_GATE_MIN_MOMENTUM_PCT) * 5)`
- `liquidity_component = min(5, (liquidityUsd / genome.SOL_GATE_MIN_LIQUIDITY_USD) * 5)`
- `conviction = momentum_component + liquidity_component` (range 0-10)
- `wouldEngage = (abs(momentumPct) >= genome.SOL_GATE_MIN_MOMENTUM_PCT) AND
  (liquidityUsd >= genome.SOL_GATE_MIN_LIQUIDITY_USD) AND
  (conviction >= genome.SOL_GATE_MIN_CONVICTION)`
This function MUST be pure (no I/O, no randomness, no wall-clock read) and MUST be the SAME
function regardless of which genome (baseline or any mutant) is passed in — see REQ-018.
**Edge Cases**:
- `momentumPct === 0` (flat market): `wouldEngage` MUST be false (zero clears no positive
  threshold).
- Negative `momentumPct` (bearish move): magnitude (`abs`) is what's compared against the
  threshold — direction/side is NOT this function's decision (HARD #0, REQ-010).
- `liquidityUsd` or `momentumPct` is `NaN`/`Infinity`/non-numeric: `wouldEngage` MUST be false
  (fail-closed, never a NaN comparison silently evaluating true).
**Acceptance Criteria**:
- For any genome and any finite, well-formed inputs, `wouldEngage` is true if and only if all
  three threshold conditions hold simultaneously (property-testable).

### REQ-009: Dev-safety default — paper/observe-only until explicit live enablement
**New, MUST clause required by the task's money-safety constraints (stronger than PM, which has no
dev/live split because PM's genome only ever touches an already-live, already-capped path).**
**EARS**: THE SYSTEM SHALL read a live-enablement flag `SOL_GATE_LIVE_ENABLE` from the environment.
WHILE `SOL_GATE_LIVE_ENABLE` is unset or not exactly `"1"`, THE SYSTEM SHALL treat the FINAL
`engage` decision as `false` UNCONDITIONALLY, regardless of `wouldEngage` (REQ-008) — i.e. the
pre-gate places NO live trades in this mode. THE SYSTEM SHALL still compute and record (REQ-011)
`wouldEngage`, `conviction`, and the genome used, for later offline evaluation and genome-tuning
validation (shadow visibility, zero live side effect).
**Edge Cases**:
- `SOL_GATE_LIVE_ENABLE` set to any value other than exactly `"1"` (e.g. `"true"`, `"yes"`, `"0"`,
  empty string) MUST be treated identically to unset — fail closed to paper mode, never a loose
  truthy-string match.
**Acceptance Criteria**:
- With `SOL_GATE_LIVE_ENABLE` unset, `engage` is `false` for every input, including inputs where
  `wouldEngage` would be `true`.
- Only `SOL_GATE_LIVE_ENABLE === "1"` AND `wouldEngage === true` AND staleness-not-exceeded
  (REQ-007) together yield `engage === true`.

### REQ-010: Descriptive-only signal context — HARD #0 preserved
**Mirrors**: `genome.mjs`'s own header comment / `pick.py`'s env docstring — "this file NEVER
decides which market/side to bet" (HARD #0, unchanged, non-negotiable).
**EARS**: IF the pre-gate's `engage` decision is true AND it passes its observed signal
(`momentumPct`, `liquidityUsd`, `conviction`, mint) into `franklin-trading start`'s context (e.g.
appended to `-p/--prompt`), THE SYSTEM SHALL pass ONLY raw observed numeric/descriptive fields —
NEVER a directive string containing a side, an action verb ("buy"/"sell"/"long"/"short"), a size,
or an instruction to trade. Which market/side/size to trade remains `franklin-trading`'s own
internal model-debate judgment, exactly as today.
**Edge Cases**:
- The pre-gate's `SOL_GATE_WATCHLIST` narrows the ELIGIBLE universe (WHETHER to even attempt this
  pass, and on which mint(s) a signal was observed) — it MUST NOT be read by
  `franklin-trading start` as a command to trade that specific mint.
**Acceptance Criteria**:
- Any payload the pre-gate contributes to `franklin-trading`'s invocation contains no token
  matching `/\b(buy|sell|long|short|swap now|execute)\b/i` as an instruction (schema-level check:
  the contributed fields are a fixed set of numeric/string OBSERVATION fields only, never free text
  framed as a command).

### REQ-011: Every-pass gate-decision trace recording
**Mirrors**: `polymarket-trade/run.sh`'s `"action":"genome"` trace line (records genome_id +
resolved knob values every pass, whether or not that pass bets).
**EARS**: WHEN the SOL pre-gate evaluates a pass (paper or live) THE SYSTEM SHALL append one
structured JSONL trace line recording: timestamp, `genome_id`, the full resolved genome (all 5
knobs), `mode` (`"paper"` or `"live"`), `decision` (`"engage"` or `"skip"`), `wouldEngage`,
`conviction`, `momentumPct`, `liquidityUsd`, and the mint evaluated — to a new trace file
(`state/sol-gate.trace.jsonl`, sibling of the existing `state/sol-trade.trace.jsonl`).
**Edge Cases**:
- Trace-file write failure (disk full, permissions) MUST NOT crash or exit-nonzero the pass —
  fail-soft, same convention as every other trace append in this codebase.
**Acceptance Criteria**:
- Every pass, engaged or not, paper or live, produces exactly one gate trace line.

### REQ-012: Engaged-pass genome_id linkage for later attribution
**Mirrors**: `pick.py`'s genome_id recorded at BET time, joined at REDEEM time by `evolve.mjs`
(spec §2.3 "genome id を bet 時に記録し、resolve/redeem 時に紐付ける").
**EARS**: WHEN the pre-gate's decision is `engage === true` AND `franklin-trading start` is
subsequently invoked for that pass, THE SYSTEM SHALL record the SAME `genome_id` (and full genome
values) into `state/sol-trade.trace.jsonl` (the existing sol-trade trace file), timestamped at or
before the pass's `live-pass` trace line, so a later offline join (REQ-013/014) can attribute a
realized swap's P&L to the genome that was active when the pass that produced it ran.
**Edge Cases**:
- `franklin-trading start` is invoked but never produces a confirmed swap this pass (WAIT/no-fill):
  the genome_id linkage line still exists; it simply never gets joined to any realized-P&L row
  (REQ-013's join is null-safe by construction).
**Acceptance Criteria**:
- For every pass where `engage === true`, a `"genome"`-shaped trace line with that pass's
  `genome_id` exists in `sol-trade.trace.jsonl` with a timestamp ≤ the pass's own live-pass line.

### REQ-012b: `attributeGenomeIdSol` join algorithm — timestamp-nearest-preceding match, NO market/task key
**Mirrors, with CORRECTED join key**: `evolve.mjs`'s `attributeGenomeId()` (evolve.mjs:86-97), which
joins a PM redeem ledger row to a preceding `"trade"` trace line by `t.market === ledgerRow.task`.
THIS KEY DOES NOT APPLY TO SOL: `record-swap.mjs:19` hardcodes `task = "jupiter swap round-trip"` as
a FIXED CONSTANT for every swap this instance ever records — it carries no per-mint/per-pass
discriminator, so a market/task-field match would either match EVERY genome-linked trace line or
NONE, never the correct one.
**EARS**: THE SYSTEM SHALL implement `attributeGenomeIdSol(ledgerRow, traceLines)` as a PURE
function that, GIVEN a confirmed sol-trade ledger row and the full `sol-trade.trace.jsonl` array,
returns the `genome_id` of the MOST RECENT genome-linked trace line (REQ-012's linkage line,
`action === "genome"`, `genome_id` present) whose timestamp is LESS THAN OR EQUAL TO the ledger
row's timestamp — TIMESTAMP ORDERING ALONE, with NO market/task/mint-field comparison of any kind.
IF no such preceding line exists, THE SYSTEM SHALL return `null` (unattributed; mirrors REQ-013's
"counts toward NO genome").
**Rationale (why timestamp-only is sufficient, not merely convenient)**: `sol-trade/run.sh` runs
single-slot, non-overlapping passes (Edge Case Catalog, "Concurrent passes") — each pass writes AT
MOST ONE genome-linked trace line before it can produce AT MOST ONE confirmed swap. Therefore at
most one pass's genome-linked line can ever be the nearest preceding line to a given swap's
timestamp without a LATER pass's OWN genome-linked line being even closer — "most recent preceding"
is unambiguously the pass that produced this swap, with no cross-pass ambiguity possible under this
rail's single-slot execution model.
**Edge Cases**:
- Two or more genome-linked trace lines precede the same swap's timestamp (e.g. several WAIT/
  no-fill passes ran between mutations before this pass's swap confirmed): THE SYSTEM SHALL select
  the one with the LARGEST timestamp (nearest preceding), never the earliest, never an average/
  blend across genomes.
- A genome-linked trace line's timestamp EXACTLY equals the ledger row's timestamp: treated as "at
  or before" (`<=`), matching REQ-012's own "timestamped at or before" contract.
- No genome-linked trace line precedes the swap at all (e.g. trace file truncated/lost, or a swap
  somehow confirmed with no prior pass — should not occur but MUST be defended): returns `null`,
  counted toward no genome (REQ-013).
- Multiple DIFFERENT genome_ids appear across the trace (a mutation/promotion boundary crossed one
  or more times): each swap independently resolves to whichever genome_id's linkage line was
  nearest-preceding AT THAT SWAP's OWN timestamp — a later swap under a NEW genome_id MUST NOT be
  misattributed to an OLDER genome_id merely because both lines exist in the same trace array.
**Acceptance Criteria**:
- Given a trace containing >= 2 genome-linked lines with DIFFERENT genome_ids at different
  timestamps, and >= 2 confirmed swap rows interleaved between them (with at least one intervening
  no-fill pass), `attributeGenomeIdSol` returns, for EACH swap, the genome_id of the linkage line
  most recently preceding THAT swap's OWN timestamp (not the first, not the last, not a fixed one)
  — verified by an explicit multi-pass property test (PROP-012b), not merely an existence check.

### REQ-013: Earnings-gate summarization — real confirmed SOL swaps only
**Mirrors, with CORRECTED field names**: `evolve.mjs`'s `summarizeByGenome` HARD 0.24 gate ("only
on-chain-confirmed redeem rows count"). PM's implementation checks `row.tx` (present) and
`row.status === "0x1"` (EVM receipt-status convention) — THIS DOES NOT APPLY TO SOL. Reading
`sol-trade/lib/record-swap.mjs` confirms the actual SOL earn-ledger row shape has NO `tx` field and
NO `status` field; it has `sig` (the Solana signature string) and `confirmed: true` (boolean, set
only after `sigStatus()` RPC-confirms the transaction).
**EARS**: THE SYSTEM SHALL count a ledger row toward a genome's realized P&L IF AND ONLY IF ALL OF:
`row.source === "sol-trade"`, `typeof row.sig === "string" && row.sig.length > 0`, AND
`row.confirmed === true`. Rows failing any of these conditions (including any future paper/
simulated SOL row, or a row from a different source) MUST NEVER be counted, and MUST NEVER
contribute to any genome's promotion eligibility.
**EARS (accumulation field — MUST)**: For each row satisfying the filter above, THE SYSTEM SHALL
accumulate `Number(row.net_usdc || 0)` — the WIN-OR-LOSS net field that `_shared/lib/ledger.mjs`'s
`deriveLine()` computes and stores on EVERY ledger row as `round(earn_usdc - cost_usdc)`, verified
present on sol-trade rows regardless of source — into that row's attributed genome's
`realized_usdc`, mirroring `evolve.mjs`'s `summarizeByGenome` line-for-line
(`entry.realized_usdc = ... + Number(row.net_usdc || 0)`, evolve.mjs:115). THE SYSTEM SHALL NEVER
sum `row.earn_usdc` alone — `earn_usdc` is a WIN-ONLY component (`record-swap.mjs:44`: `delta > 0 ?
delta : 0`, always `0` for a losing swap) — summing it would let a net-losing genome appear
artificially profitable and clear REQ-014's net-positive promotion floor with real losses hidden.
**Edge Cases**:
- A row with `confirmed: false` or missing `confirmed` (should not occur per `record-swap.mjs`'s
  own contract, but MUST be defensively excluded if it ever does) — excluded.
- A row with `source !== "sol-trade"` (e.g. a future new SOL-adjacent source) — excluded unless a
  future spec explicitly adds it here.
- A confirmed row whose swap cannot be attributed to any genome (no preceding
  `"genome"`-linked trace line at or before its timestamp, `attributeGenomeIdSol`, REQ-012b) —
  counts toward NO genome (never silently folded into baseline), mirroring `attributeGenomeId`'s
  `null` behavior.
- A genome whose ONLY counted rows are net-negative (`net_usdc < 0` on every row): its summed
  `realized_usdc` MUST be negative, and MUST NOT clear REQ-014's net-positive floor.
**Acceptance Criteria**:
- A synthetic ledger containing a mix of `sig`+`confirmed:true` rows, `confirmed:false` rows, and
  rows from other sources yields a summary that includes ONLY the first category.
- A synthetic ledger containing (for the SAME genome_id) one WIN row (`net_usdc: +0.5`) and one LOSS
  row (`net_usdc: -0.3`) yields `realized_usdc === 0.2` for that genome_id — the SUMMED NUMERIC
  VALUE, not merely row membership; an implementation that sums `earn_usdc` instead would yield
  `0.5` and MUST fail this criterion.

### REQ-014: Promotion gate — reused verbatim from evolve.mjs, never reimplemented
**Mirrors**: `evolve.mjs`'s `evaluatePromotion()` — this function is already rail-agnostic (it
operates purely on a `genome_id → {realized_usdc, redeem_count}` summary Map plus a
`baselineId`/`mutantId`/`minRedeems`, with no PM-specific field names inside its body).
**EARS**: THE SYSTEM SHALL import and reuse `evaluatePromotion()` from `evolve.mjs` unchanged for
the SOL rail's promotion decision — a mutant genome is promotion-eligible only when (a) it has
`>= minRedeems` (K, default 3, env-overridable) chain-verified realized SOL swaps (REQ-013's
summary), (b) it is itself net-positive (`realized_usdc > 0`), AND (c) its realized P&L exceeds
`max(baseline_realized_usdc, 0)`. A NEW copy of this pure decision logic MUST NOT be hand-written
for SOL.
**Edge Cases**:
- Cold start (zero confirmed SOL swaps for any genome other than baseline): no mutant ever reaches
  `minRedeems`; the gate returns "no promotion" for every candidate — this is the expected, normal
  state until real swap volume accumulates (see design doc's "capital cold-start" section).
- A mutant that merely loses LESS than baseline (e.g. baseline -$5, mutant -$2) MUST NOT promote
  (net-positive floor, `evaluatePromotion`'s existing HARD 0.24 behavior, unchanged).
**Acceptance Criteria**:
- Given a synthetic summary reproducing evolve.mjs's own existing test fixtures (mutant net-
  positive and beating baseline with `>= K` redeems → promote; mutant net-positive but `< K`
  redeems → no promote; mutant losing less than a losing baseline → no promote), the SOL wiring
  produces IDENTICAL promote/no-promote verdicts to calling `evolve.mjs`'s function directly
  (proves no drift/reimplementation).

### REQ-015: Promotion writes the canonical SOL baseline + path-scoped commit — reused verbatim from evolve.mjs, never reimplemented
**Mirrors**: `evolve.mjs`'s `promote()` (evolve.mjs:169-195; writes `baseline-genome.json`,
`git add`+`git commit` scoped to that single path only, so a promotion can never sweep unrelated
changes into its commit — this exact hardening was itself an adversary MUST-FIX in the PM feature,
spec §"検証ログ"). `promote()` is ALREADY parameterized by `canonicalPath`/`cwd` — it is rail-agnostic
in exactly the same sense `evaluatePromotion` is (REQ-014).
**EARS**: WHEN REQ-014's gate returns `promote: true` THE SYSTEM SHALL write the winning genome's
knob values to the SOL rail's canonical baseline file
(`~/anicca/skills/earn/sol-trade/baseline-genome.json`) and `git commit` ONLY that path, with a
message identifying the new genome id and the chain-verified basis for promotion.
**EARS (reuse mandate — MUST, same rationale as REQ-014)**: THE SYSTEM SHALL perform this
write-and-commit by calling `evolve.mjs`'s exported `promote(genome, { canonicalPath, cwd })`
UNCHANGED, passing the SOL rail's own `canonicalPath`
(`~/anicca/skills/earn/sol-trade/baseline-genome.json`) — a NEW, hand-written copy of this
git-commit-scoping logic MUST NOT be authored for SOL, mirroring REQ-014's identical
no-reimplementation mandate for `evaluatePromotion`. This is not a stylistic preference: a
hand-rolled SOL-specific git-commit implementation diverging from the proven one (e.g. a stray
`git add -A`, or a missing `-c user.name=`/`user.email=` breaking in a cron/CI environment lacking
git identity config) is EXACTLY the bug class that was itself a prior PM-feature adversary MUST-FIX
— reintroducing a fresh, untested reimplementation of already-hardened git-commit logic is
disallowed for the same reason it was disallowed for PM.
**Edge Cases**:
- The commit MUST use `git commit -- <canonical-baseline-path>` (pathspec-scoped), never a bare
  `git commit -a` or `git add -A`, so concurrent unrelated changes elsewhere in the shared `~/anicca`
  checkout are never swept into a promotion commit — GUARANTEED by construction because this is
  `evolve.mjs::promote()`'s own existing, already-hardened, already-tested behavior, not a
  freshly-written pathspec that a SOL-specific implementation could get wrong.
**Acceptance Criteria**:
- After a promotion, `git show --stat HEAD` for the promotion commit touches exactly one file: the
  SOL canonical baseline-genome.json.
- The SOL promotion wiring's `promote` reference is the SAME function object imported from
  `evolve.mjs` (`import { promote } from ".../evolve.mjs"`), NOT a local reimplementation — verified
  by PROP-015b, an import-identity test mirroring PROP-014's pattern (`fn.toString() ===` the
  imported function's own source, or a reference-equality/mock-call-count check on the imported
  binding).

### REQ-016: Identity safety — per-instance, ANICCA_HOME-gated, never cross-instance
**Mirrors**: `resolve-identity.mjs`'s fail-closed pattern (see
`anicca-spawn-identity-resolution-fix`) AND `sol-trade/run.sh`'s existing IDENTITY-MATCH GUARD
(only the instance owning `~/.blockrun` — Franklin — may proceed; every other instance halts).
**EARS**: THE SYSTEM SHALL resolve the SOL genome's instance-override path from `ANICCA_HOME`
(explicit env, else `$HOME/.anicca`) exactly like `genome.mjs`'s existing
`instanceOverridePath()`, and SHALL NEVER read or write another instance's override file. THE
SYSTEM SHALL preserve the EXISTING `sol-trade/run.sh` identity-match guard unchanged (own-wallet
vs `~/.blockrun`-derived wallet must match, else skip before touching the CLI at all) — the new
pre-gate MUST run strictly AFTER that guard, never before or in place of it.
**Edge Cases**:
- A spawn with a different `ANICCA_HOME` attempting to read/mutate Franklin's SOL genome override
  file MUST fail closed to that spawn's OWN (separate, empty) override path — never cross-read.
- `ANICCA_HOME` unset AND `$HOME` not Franklin's: the existing identity-match guard already halts
  before the CLI is touched; the new pre-gate inherits this by running after it, not by
  reimplementing the check.
**Acceptance Criteria**:
- For two distinct `ANICCA_HOME` values, `instanceOverridePath(homeA) !== instanceOverridePath(homeB)`,
  and loading the genome under `homeA` never reflects a value written under `homeB`.

### REQ-017: SOL_TRADE_MAX_SPEND hard-overridden after genome eval; scope_guard unweakened
**Mirrors**: `polymarket-trade/run.sh`'s single choke-point hard-override
(`export MAX_BET_SIZE=2` etc., unconditionally, AFTER genome eval, so nothing above — genome or a
pre-set env var — can ever override it).
**EARS**: THE SYSTEM SHALL harden `sol-trade/run.sh`'s existing `MAX_SPEND="${SOL_TRADE_MAX_SPEND:-0.25}"`
soft-default into a hard, unconditional override AT THE SAME CHOKE POINT, positioned immediately
AFTER the SOL pre-gate's genome eval and BEFORE `franklin-trading start` is invoked, so a
genome-derived or otherwise pre-set `SOL_TRADE_MAX_SPEND` env var can never win. THE SYSTEM SHALL
NOT modify, weaken, reorder around, or bypass the existing `earn-guard.mjs` cumulative-loss check,
the identity-match guard, or any adversary-established scope_guard in this or any other earn skill.
**Edge Cases**:
- A genome-override file that somehow contains `SOL_TRADE_MAX_SPEND` (already impossible per REQ-004's
  structural exclusion, but defended here too as belt-and-suspenders) MUST have zero effect on the
  actual `--max-spend` value passed to `franklin-trading start`.
**Acceptance Criteria**:
- With `SOL_TRADE_MAX_SPEND` set in the environment to an attacker-chosen value BEFORE the pre-gate
  runs, the value actually passed to `franklin-trading start --max-spend` is the hard-coded cap,
  not the attacker's value.

### REQ-018: No evolved CODE in the money path — only gated numeric thresholds
**Mirrors**: the design doc's Hard Constraint #3 and the self-improve-real-ledger safety
separation already established for PM (evolvable unit = numeric knobs, never live decision code).
**EARS**: THE SYSTEM SHALL implement the pre-gate's decision logic (`decideEngagement`, REQ-008)
as FIXED, reviewed, non-evolved source code. Evolution (mutation, REQ-002) SHALL ONLY ever produce
new numeric KNOB VALUES consumed as data by this fixed function — it SHALL NEVER generate, alter,
select among, or dynamically evaluate (`eval`, `new Function`, dynamic `import()` of a
genome-supplied path, etc.) any CODE path in the engage decision or the trade-invocation path.
**Edge Cases**:
- A malicious/malformed genome value (e.g. a string where a number is expected) fed into
  `decideEngagement` MUST be handled by REQ-008's NaN/non-numeric fail-closed behavior — it MUST
  NOT be able to reach any code-execution sink.
**Acceptance Criteria**:
- Static/source-contract test: no occurrence of `eval(`, `new Function(`, or a genome-value-derived
  dynamic `import()`/`require()` anywhere in the pre-gate's decision or invocation code path
  (mirrors the existing "source contract" test pattern already used elsewhere in `skills/earn`,
  e.g. `execute-yield.mjs`'s deposit-guard wiring test).

## Non-Functional Requirements

- **Performance**: the pre-gate's market-data fetch MUST NOT exceed an 8-second timeout per mint;
  a full pass's pre-gate evaluation (all watchlist mints) MUST NOT add more than ~10s to the
  existing `sol-trade/run.sh` pass budget (the existing pass already runs under a 600s
  `franklin-trading start` timeout).
- **No new paid dependency**: the ONLY new external call this feature introduces is the free,
  unauthenticated Jupiter Price v3 endpoint (empirically verified above) — no API key, no signup,
  no billing account.
- **No secrets**: the pre-gate reads no private key material; it is a read-only market-data
  consumer plus a local genome/trace read-writer.
- **Fail-soft**: no failure mode in this feature (fetch error, malformed genome, trace-write
  failure, git-commit failure during a promotion attempt that later fails) may crash or
  exit-nonzero the calling `sol-trade/run.sh` pass — every failure degrades to "skip"/"no
  promotion", consistent with every other guard in this codebase.

## Edge Case Catalog (cross-cutting, beyond per-REQ edge cases above)

- **No market data available**: Jupiter endpoint unreachable and no usable cache → skip pass,
  gate trace line still recorded with `decision: "skip"`, `reason: "no-signal"`.
- **Cold-start / zero swaps**: promotion gate (REQ-014) simply never fires; this is expected and
  MUST NOT be treated as an error state.
- **Malformed genome file** (on disk, canonical or override): fail-closed to SAFE_DEFAULT_GENOME
  (REQ-006), never a thrown exception.
- **Cross-instance attempt**: a non-Franklin instance's `ANICCA_HOME` resolves to its own,
  separate, empty override path; it never sees or affects Franklin's genome (REQ-016). The
  pre-existing identity-match guard in `sol-trade/run.sh` already halts non-Franklin instances
  before the CLI is even touched.
- **Malicious/symlinked state path**: the genome override path and trace paths are constructed
  from `ANICCA_HOME`/fixed relative segments only, never from genome-supplied or otherwise
  attacker-influenced path fragments — no path-traversal surface is introduced by this feature.
- **Concurrent passes**: trace-file appends use the same fail-soft `fs.appendFileSync`-style
  convention already used throughout `skills/earn` (no new locking primitive introduced; this
  matches the existing single-cron-slot-at-a-time operating assumption for `earn/sol-trade`).

## Open Questions for Spec Review

1. **Exact default numeric thresholds** (`SOL_GATE_MIN_MOMENTUM_PCT=2.0`,
   `SOL_GATE_MIN_LIQUIDITY_USD=1000000`, `SOL_GATE_MIN_CONVICTION=6`,
   `SOL_GATE_MAX_STALENESS_SEC=300`) are NEW design choices (unlike PM's MIN_EDGE=0.15, which
   mirrored an ALREADY-EXISTING `pick.py` env default). There is no prior in-repo number to copy
   for the SOL rail. These defaults are conservative but genuinely invented for this spec and
   SHOULD be scrutinized in spec-review, not treated as ground truth.
2. **Jupiter Price v3 endpoint long-term stability**: verified live/reachable/free during this
   design session (2026-07-10) via direct curl; this spec does NOT claim knowledge of its rate
   limits, SLA, or ToS beyond "responded 200 with the documented shape when queried directly."
   Implementation phase (2a/2b) MUST re-verify reachability and MUST implement REQ-007's fail-closed
   behavior precisely because this dependency's long-term availability is not guaranteed.
