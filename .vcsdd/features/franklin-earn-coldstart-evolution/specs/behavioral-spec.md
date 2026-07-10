# Behavioral Spec — franklin-earn-coldstart-evolution (autonomous-witness① path: escape Franklin's earn cold-start trap)

**Status**: Phase 1a (behavioral spec). This feature builds ON TOP of the already-implemented,
already-live `franklin-sol-evolvable-edge` (sol-genome.mjs / sol-gate.mjs / sol-gate-cli.mjs /
sol-evolve.mjs / sol-trace.mjs — all read and cited below). It does NOT re-implement or replace
any of that machinery; it ADDS a self-improvement harness on top of it that closes the specific
trap diagnosed in `docs/loop-engineering/14-cold-start-escape-BP.md`.

## Provenance (copy+tweak, do not reinvent — harness-not-cook)

This spec is the VCSDD-formalized version of the exact, ranked, file:line-cited diagnosis and fix
plan already written in `docs/loop-engineering/14-cold-start-escape-BP.md` ("Franklin cold-start へ
の copy+tweak"). Every mechanism below cites its source repo file:line. **The harness evolves
numeric knob values only — it never hand-writes or hardcodes a trading strategy** (kill-phrase
"harness or cook?", memory `feedback_build_the_harness_not_do_their_work.md`; regex/if-else
judgment is forbidden per `rules/building-effective-ai-agents.md` — every new function below is
either pure deterministic bookkeeping/arithmetic over already-recorded data, or a pass-through
composition of EXISTING, unchanged, proven functions).

### Our own trap, confirmed live (2026-07-10, not assumed)

- `skills/earn/lib/evolve.mjs:27,132-137` — `DEFAULT_MIN_REDEEMS=3` (K). `evaluatePromotion`
  refuses promotion below K on-chain-verified redeems. Verified live: `skills/earn/state/earn-ledger.jsonl`
  currently has **zero** `source==="sol-trade"` rows (`grep -c` on the real state file, 2026-07-10) —
  Franklin's SOL genome has never once produced a chain-confirmed swap, so `redeem_count` is
  permanently `0` for every mutant and the K-gate can never open.
- `skills/earn/sol-trade/lib/sol-genome.mjs:182` — `mutate()`'s direction is a **symmetric coin-flip**
  (`direction = rng() < 0.5 ? -1 : 1`) drawn fresh every `SOL_GATE_GENOME_MUTATE_EVERY` (default 5)
  passes. With ~50% chance of tightening a threshold further each mutation, the existing exploration
  mechanism cannot durably walk in one direction — it cannot escape starvation on its own.
- `skills/earn/sol-trade/lib/sol-gate-cli.mjs:121-132` — every pass **already, unconditionally**
  computes and appends `wouldEngage`/`conviction`/`momentumPct`/`liquidityUsd` to
  `state/sol-gate.trace.jsonl` (REQ-011 of `franklin-sol-evolvable-edge`), whether or not that pass
  engages. This near-miss data exists today and is currently dead — nothing downstream reads it.

### Cited fixes (repo file:line, cloned + read directly in this session, not from memory)

| Mechanism | Source | Verified file:line (read directly, 2026-07-10) |
|---|---|---|
| (a) Backtest-bootstrap (exploration/confirmation split) | `mq545/polyevolve` | `ARCHITECTURE.md:1-40` — EXPLORATION (unlimited, $0, offline, not believed) vs CONFIRMATION (forward, rubric-gated, only then believed) |
| (b) Asymmetric/forced exploration, non-greedy parent bias | `algorithmicsuperintelligence/openevolve` | `openevolve/database.py:1288-1326` — `_sample_parent()` dispatches to `_sample_exploration_parent()`/`_sample_exploitation_parent()`/`_sample_random_parent()` by ratio, and `_sample_exploration_parent()` explicitly copies the best/random program into an EMPTY island rather than leaving it starved |
| (b) Non-greedy, probabilistic low-scorer selection | `jennyzzt/dgm` | `DGM_outer.py:83-89` (`method == 'score_prop'`): `scores = [sigmoid(10*(score-0.5))]`, `probabilities = scores/sum(scores)`, `random.choices(commits, probabilities, ...)` — low scorers stay selectable, never zeroed out |
| (b) Hard, deterministic starvation penalty | `tarsyang/quantevolve` | `quantevolve/evaluation/quant_evaluator.py:284-287` — `if num_trades < 2: combined_score = min(combined_score, -50.0)` (a "never-trade" genome is penalized, not merely ignored) |
| (c) Near-miss-as-data (don't discard 0-score attempts) | `algorithmicsuperintelligence/openevolve` | `openevolve/evaluator.py:265,296` — failed/degenerate evaluations are kept in the population as `{"error": 0.0}` rather than discarded |

## Honest framing (from ch14, restated — do not overclaim)

No cloned repo closes a live-capital, rare-reward-event, self-modifying trading loop end-to-end —
PolyEvolve's own README states "Paper predictions only – no live trading." **This spec does not
claim to solve durable live trading edge.** It claims something narrower and verifiable: it removes
the STRUCTURAL deadlock (a genome that has never traded can never accumulate the K on-chain
redeems required to ever be evaluated at all) using the same two primitives (offline replay
pre-filtering + non-greedy/forced exploration) every cited repo actually uses to avoid exactly this
deadlock in its own domain.

## What this feature is NOT allowed to touch (money-safety, restated from
`franklin-sol-evolvable-edge`'s own HARD constraints — unchanged, non-negotiable)

1. `SOL_TRADE_MAX_SPEND` / `resolve-max-spend.sh`'s hard-coded `0.25` choke point
   (`sol-trade/run.sh` REQ-017) — this feature adds ZERO lines to that file and ZERO lines to
   `resolve-max-spend.sh`.
2. `SOL_GATE_LIVE_ENABLE` semantics (`sol-gate.mjs::isLiveEnabled`, REQ-009) — untouched. A
   starvation-loosened or backtest-seeded genome can compute `wouldEngage=true`, but `engage`
   remains `liveEnabled === true AND wouldEngage === true` — a genome this feature seeds can NEVER
   place a live trade unless the operator has separately set `SOL_GATE_LIVE_ENABLE=1`, exactly as
   today.
3. `evaluatePromotion`/`promote` (`skills/earn/lib/evolve.mjs`, reused verbatim by
   `sol-evolve.mjs`) — the ONLY path that ever writes `skills/earn/sol-trade/baseline-genome.json`
   remains gated SOLELY on chain-verified realized SOL P&L (`row.sig` present, `row.confirmed===true`,
   summed `net_usdc`). This feature MUST NEVER call these functions with backtest-derived (REQ-002/
   REQ-003 — count/diversity tallies, NEVER a P&L estimate) or starvation-bookkeeping data, and MUST
   NEVER write `baseline-genome.json` through any other path.
4. `record-swap.mjs`'s `external:false`-by-construction invariant (FIND-004: a same-wallet Jupiter
   swap proves nothing about external revenue) — this feature does not touch `record-swap.mjs`.
5. `earn-guard.mjs` cumulative-loss check and the existing identity-match guard in
   `sol-trade/run.sh` — unweakened, unreordered, untouched.
6. The evolvable unit stays numeric knobs/signals only — `decideEngagement` (`sol-gate.mjs`, REQ-008,
   REQ-018) remains fixed, reviewed, non-evolved source code forever; nothing in this feature
   generates, selects among, or dynamically evaluates code.

## Purity Boundary Analysis (summary — full map in verification-architecture.md)

- **Pure core (new)**: `replayGenomeAgainstCorpus` (returns a count/diversity tally, NEVER a P&L
  estimate), `evaluateBacktestRubric`, `countConsecutiveSkips`, `selectBottleneckKnob` (excludes
  `no-signal`/null-momentum lines before tallying), `mutate()`'s new `forceKnob`/`forcedDirection`
  extension (all take already-in-memory data — corpus arrays, trace-line arrays, a genome object —
  and never perform I/O, randomness beyond an injectable `rng`, or a wall-clock read).
- **Pure core (reused, unchanged)**: `decideEngagement` (`sol-gate.mjs`), `mutate`'s existing
  symmetric path, `genomeId`, `stripForbidden`, `evaluatePromotion` (`evolve.mjs`).
- **Effectful shell (new)**: reading the trace corpus as the backtest corpus and the starvation
  signal source, via a CHANGED, now `ANICCA_HOME`-gated `GATE_TRACE_PATH` resolution (REQ-013 —
  iteration-1's claim this was already gated was false); writing the per-instance
  `sol-gate-genome-override.json` (seeding, not promoting); the per-pass orchestration wiring
  inside `sol-gate-cli.mjs`'s `main()`.
- **Effectful shell (reused, unchanged)**: `loadGenome`, `fetchSolMarketSignal`,
  `instanceOverridePath` (the override WRITE target — already `ANICCA_HOME`-gated), `promote`
  (`evolve.mjs`), all trace appends, `sol-trade/run.sh`'s identity-match guard and
  `resolve-max-spend.sh` choke point.

## Requirements

### REQ-001: Historical replay corpus — the existing gate-trace file, no new dependency
**Mirrors**: ch14 mechanism (a)/(c), `polyevolve/ARCHITECTURE.md:1-40`'s "offline, $0, unlimited"
exploration corpus + `openevolve/evaluator.py:265`'s "keep near-miss data, don't discard it."
**EARS**: THE SYSTEM SHALL treat the ALREADY-RECORDED `sol-gate.trace.jsonl` lines (the path itself
resolved per REQ-013 — `ANICCA_HOME`-gated, NOT the `__dirname`-derived shared-checkout path
iteration-1 incorrectly assumed was already safe; `action==="sol-gate"`, appended every pass
regardless of engage/skip per REQ-011 of `franklin-sol-evolvable-edge`) as the backtest replay
corpus — a genuinely free historical dataset of real Jupiter Price v3 momentum/liquidity snapshots,
requiring NO new paid dependency and NO new network call. Each corpus entry contributes
`{momentumPct, liquidityUsd}` (from the trace line's own recorded fields).
**Edge Cases**:
- Corpus has fewer than `SOL_BACKTEST_MIN_SAMPLES` (default 20) entries: backtest-bootstrap MUST
  skip this cycle entirely (fail-closed to "no candidate seeded", never a degenerate replay over a
  handful of points).
- A trace line missing `momentumPct`/`liquidityUsd`, or with a non-finite value: excluded from the
  corpus (defensive filter), never coerced to 0.
- The trace file is missing or unparseable: corpus is empty; bootstrap skips this cycle (same as
  the small-corpus case).
**Acceptance Criteria**:
- A synthetic trace file with N well-formed lines yields a corpus of exactly N entries; malformed
  lines are excluded and do not throw.

### REQ-002: Pure backtest replay — reuses `decideEngagement` unchanged
**Mirrors**: ch14 mechanism (a) — "replay historical SOL price/liquidity offline through the SAME
decideEngagement/conviction fn."
**EARS**: THE SYSTEM SHALL implement `replayGenomeAgainstCorpus(genome, corpusEntries)` as a PURE
function that, for each corpus entry, calls `decideEngagement` (imported UNCHANGED from
`sol-gate.mjs`, never reimplemented) with `momentumPct`/`liquidityUsd` from that entry, `ageSec: 0`
(the corpus entry represents a real market snapshot AT capture time — REQ-007's live-fetch
staleness concern does not apply to historical replay fidelity, since the momentum/liquidity values
being replayed are themselves the values that were actually fetched fresh at capture time), and
`genome` = the candidate under test; it reads only `outcome.wouldEngage` and `outcome.conviction`
from each call (never `outcome.engage`, which depends on `liveEnabled` and is irrelevant to "would
this genome have wanted to trade"). Returns `{wouldEngageCount, totalCount,
distinctWouldEngageSignatures}` (the last per REQ-003 — a diversity tally, NEVER a P&L estimate).
**Edge Cases**:
- An empty corpus array: returns `{wouldEngageCount: 0, totalCount: 0,
  distinctWouldEngageSignatures: 0}`, never throws, never divides by zero downstream (REQ-004 must
  treat `totalCount===0` as an automatic rubric fail).
**Acceptance Criteria**:
- For a fixed corpus and genome, `replayGenomeAgainstCorpus`'s per-entry `wouldEngage` calls are
  IDENTICAL (fixture-parity, import-identity) to calling `decideEngagement` directly with the same
  arguments — proves no reimplementation drift (PROP-002).

### REQ-003: Backtest diversity accounting — distinct would-engage market signatures (NO simulated P&L)
**DELETES a prior, spec-review-rejected "simulated P&L" formula (FIND-001, iteration-1) — not
weakened, REMOVED ENTIRELY.** That formula credited a corpus entry's TRAILING 24h `momentumPct`
(`sol-gate-cli.mjs:114`, itself already-elapsed at capture time) as though it were a FORWARD
realized return of a hypothetical swap entered at that same snapshot — backward-looking, and
near-tautological given `decideEngagement`'s own `SOL_GATE_MIN_MOMENTUM_PCT` range (`[0.5, 8.0]`,
`sol-genome.mjs:51`) always exceeds `SOL_BACKTEST_FEE_PCT`'s `0.4` default, so the formula's sign
was 100% determined by `momentumPct`'s own sign regardless of genome quality — a fake/dry-run
backtest P&L this project's own Test-Money Safety Rule (below) and money-safety conventions reject.
No successor P&L constant, formula, or estimate of any kind is introduced by this requirement.
**Mirrors**: ch14 mechanism (a)'s "rubric(十分な would-engage 数・非退化)" — concretized as
non-degenerate COUNT (REQ-004's `wouldEngageCount`/ratio clauses, unchanged) AND non-degenerate
DIVERSITY (this requirement) — never a P&L estimate.
**EARS**: THE SYSTEM SHALL implement `replayGenomeAgainstCorpus`'s (REQ-002) diversity tally as
follows: for each corpus entry where that entry's per-entry `wouldEngage===true`, THE SYSTEM SHALL
compute a signature string `` `${momentumPct}:${liquidityUsd}` `` from that entry's own recorded
`momentumPct`/`liquidityUsd` fields and add it to an in-memory `Set`; `distinctWouldEngageSignatures`
is that `Set`'s final size — the count of DISTINCT market snapshots (never a repeated identical
snapshot, e.g. from a stale-cache period producing many consecutive identical trace lines, counted
more than once) among the would-engage subset. This is PURE bookkeeping (a `Set` cardinality over
already-recorded fields) — it makes NO claim about profit, loss, fill price, or realized return of
any kind.
**Edge Cases**:
- Two corpus entries with numerically IDENTICAL `momentumPct` AND `liquidityUsd` (e.g. two
  consecutive passes during a cached/stale-signal period): contribute only ONE signature to the
  `Set` (correct dedup, not double-counted as diversity).
- Zero would-engage entries: `distinctWouldEngageSignatures` is `0` (REQ-004 already fails the
  rubric on `wouldEngageCount < SOL_BACKTEST_MIN_ENGAGE` in this case; this value is never divided
  or used unsafely).
**Acceptance Criteria**:
- Given a corpus with a KNOWN set of would-engage entries, some sharing identical
  `{momentumPct, liquidityUsd}` pairs and some distinct, `distinctWouldEngageSignatures` matches the
  EXACT count of unique pairs (Set-cardinality assertion, not an approximation) (PROP-003).

### REQ-004: Backtest rubric gate — non-degenerate COUNT AND DIVERSITY (no P&L clause)
**Mirrors**: ch14 mechanism (a)'s "rubric(十分な would-engage 数・非退化) を通った genome" +
`quantevolve/evaluation/quant_evaluator.py:284-287`'s `num_trades < 2` degenerate-penalty pattern
(inverted here into a positive non-degeneracy gate rather than a score penalty, because this
harness's gate is binary pass/fail, not a continuous fitness score).
**EARS**: THE SYSTEM SHALL implement `evaluateBacktestRubric({wouldEngageCount, totalCount,
distinctWouldEngageSignatures})` as a PURE function returning `{passes: boolean, reason: string}`.
`passes` is `true` if and only if ALL of: `totalCount > 0`, `wouldEngageCount >=
SOL_BACKTEST_MIN_ENGAGE` (default 5 — a genome that would rarely have engaged is not meaningfully
evaluated by so few samples), `wouldEngageCount / totalCount <= SOL_BACKTEST_MAX_ENGAGE_RATIO`
(default 0.8 — a genome that engages on almost every sample is degenerate, indistinguishable from
"always trade," and MUST NOT be rewarded merely for gaming the count floor), AND
`distinctWouldEngageSignatures >= SOL_BACKTEST_MIN_DISTINCT_SIGNATURES` (default 3 — the
would-engage subset MUST span at least this many genuinely distinct market snapshots; a genome that
only "passes" by matching a handful of would-engage entries that are all the SAME repeated/stale
snapshot is degenerate in a way COUNT alone cannot catch, and MUST NOT be rewarded — REQ-003's
diversity tally, NEVER a P&L estimate, per spec-review FIND-001's rejection of the prior
simulated-P&L formula). This is a NON-DEGENERATE COUNT-AND-DIVERSITY gate ONLY — it contains NO P&L
term, NO profit estimate, NO simulated trade of any kind.
**Edge Cases**:
- `totalCount === 0` (empty corpus reached this function somehow): `passes: false`, reason
  `"empty-corpus"` — never a division producing `NaN`/`Infinity`.
- `distinctWouldEngageSignatures === SOL_BACKTEST_MIN_DISTINCT_SIGNATURES` exactly (boundary):
  `passes` MAY be `true` if every other clause also holds — this is an inclusive `>=` floor (a
  count-based non-degeneracy check, not a strict P&L sign check).
**Acceptance Criteria**:
- For randomized `{wouldEngageCount, totalCount, distinctWouldEngageSignatures}` triples, `passes`
  is true if and only if all four conditions hold simultaneously (property-testable, PROP-004).

### REQ-005: Backtest-bootstrap seeds the EXPLORATION override ONLY — NEVER the canonical baseline (HARD)
**Mirrors**: `polyevolve/ARCHITECTURE.md:1-40`'s exploration/confirmation split, mapped onto THIS
codebase's existing distinction between `sol-gate-genome-override.json` (the per-instance
CURRENT-GENERATION candidate the live wake-cycle actually loads and tries, already the write target
of `sol-gate-cli.mjs`'s `maybeMutateGenome`, `franklin-sol-evolvable-edge` FIND-001) and
`baseline-genome.json` (the canonical, chain-verified-promoted genome, written ONLY by `evolve.mjs`'s
`promote()`).
**EARS**: WHEN a candidate genome clears REQ-004's rubric (`passes: true`) THE SYSTEM SHALL write
that candidate's (forbidden-cap-stripped, REQ-011) knob values to THIS instance's own
`sol-gate-genome-override.json` — the SAME file and SAME per-instance-override mechanism
`franklin-sol-evolvable-edge` already uses for its cadence-triggered symmetric mutation — becoming
the NEXT genome the live wake-cycle's pre-gate actually loads and evaluates against real-time
market data. THE SYSTEM SHALL NEVER, under any condition, write to
`skills/earn/sol-trade/baseline-genome.json`, and SHALL NEVER call `evaluatePromotion` or `promote`
with backtest-derived data (REQ-012).
**EARS (rationale, non-normative but load-bearing for spec-review)**: this is SEEDING, not
PROMOTING — it changes WHICH genome the live wake-cycle tries next (raising the probability that a
real pass actually engages and eventually accumulates the K on-chain redeems REQ-014-of-the-sibling-
spec requires), never WHICH genome is the trusted, chain-verified-promoted baseline. It causes zero
live side effect beyond what the EXISTING cadence-mutation mechanism already causes (REQ-009 of
`franklin-sol-evolvable-edge`'s "zero live side effect" guarantee is preserved: `engage` still
requires `SOL_GATE_LIVE_ENABLE==="1"` regardless of which candidate is currently loaded).
**Edge Cases**:
- Multiple candidates clear the rubric in the same bootstrap cycle: THE SYSTEM SHALL seed the ONE
  with the HIGHEST `distinctWouldEngageSignatures` (most market diversity in its would-engage set —
  the strongest non-degeneracy signal this feature computes, REQ-003); ties on THAT broken by the
  HIGHEST `wouldEngageCount`; further ties broken by candidate-generation order (the FIRST candidate
  drawn by REQ-006's `mutate()` sequence this cycle wins — deterministic, reproducible, requires no
  P&L estimate; this deliberately does NOT mirror `evolve.mjs`'s own chain-verified-`realized_usdc`
  winner selection, since no chain-verified number exists at backtest time).
- No candidate clears the rubric: no write occurs this cycle; the existing override (or baseline)
  remains active, unchanged — this is the expected, normal outcome, not an error.
**Acceptance Criteria**:
- Across an exhaustive fixture set of many rubric-passing scenarios, the ONLY file path ever
  targeted for a write by the backtest-bootstrap code path is `sol-gate-genome-override.json`;
  `baseline-genome.json` is never opened for writing by this code path under any fixture (PROP-005).
- `evaluatePromotion`/`promote` (spied/mocked imports) are never invoked by the backtest-bootstrap
  code path, for any fixture (PROP-006).

### REQ-006: Backtest candidates drawn from the EXISTING mutation pool only
**Mirrors**: REQ-018's "no evolved code" + `franklin-sol-evolvable-edge`'s existing `MUTATION_SPEC`
knob/step/range table (unchanged, not widened by this feature).
**EARS**: THE SYSTEM SHALL generate backtest candidate genomes by calling `sol-genome.mjs`'s
EXISTING, UNCHANGED `mutate()` around the currently-loaded genome (baseline+override), drawing
`SOL_BACKTEST_CANDIDATES_PER_CYCLE` (default 5) candidates per bootstrap cycle, each passed through
`stripForbidden` (REQ-011) before replay (REQ-002) and before any write (REQ-005). THE SYSTEM SHALL
NOT introduce a new knob, a new mutation range, or a new step size beyond what
`franklin-sol-evolvable-edge`'s `MUTATION_SPEC` already defines.
**Edge Cases**:
- All `SOL_BACKTEST_CANDIDATES_PER_CYCLE` candidates fail the rubric: no seed occurs this cycle
  (same as REQ-005's "no candidate clears" case).
**Acceptance Criteria**:
- Every backtest candidate's knob keys are a subset of `KNOB_KEYS` (`sol-genome.mjs`); none contain
  a `FORBIDDEN_CAP_KEYS` entry (verified by PROP-007).

### REQ-007: Deterministic starvation signal — `countConsecutiveSkips`, trace-derived, no separate counter file
**Mirrors**: ch14 mechanism (b)'s "starvation signal（N 連続 skip / redeem_count が M pass 0 のまま）
検知時" — implemented here as a PURE function over the ALREADY-EXISTING trace data (deliberately NOT
a new persisted counter file, unlike `shouldMutateThisPass`'s cadence counter — a trace-derived
count can never drift out of sync with the trace it's derived from, which a SEPARATE persisted
counter could).
**EARS**: THE SYSTEM SHALL implement `countConsecutiveSkips(gateTraceLines)` as a PURE function that
scans `gateTraceLines` from the MOST RECENT entry backward, counting consecutive lines with
`decision === "skip"`, and stops (returns the count so far) at the first line with
`decision === "engage"` or at the start of the array. THE SYSTEM SHALL implement
`shouldForceExploration(streakCount, threshold = SOL_GATE_STARVATION_THRESHOLD)` (default threshold
20) as a PURE function returning `streakCount >= threshold`.
**Edge Cases**:
- Empty trace array: `countConsecutiveSkips` returns `0` (no starvation signal from an empty
  history — never crashes, never treats "no data" as "starved").
- The most recent line is `decision === "engage"`: returns `0` immediately (REQ-010's reset).
- A trace line missing a `decision` field: treated as neither skip nor engage — the scan stops
  there (conservative: an unparseable line does not extend a streak past ambiguous data).
**Acceptance Criteria**:
- For randomized decision sequences, `countConsecutiveSkips` equals EXACTLY the number of trailing
  `"skip"` entries before the first `"engage"` (or the array start) — property-testable (PROP-008).

### REQ-008: Forced-loosen direction + bottleneck-knob targeting — deterministic, self-limited to the starved state
**Mirrors**: ch14 mechanism (b) — "mutation direction を loosen 方向に強制" — implemented as a
per-knob DIRECTION TABLE (deterministic bookkeeping over already-known threshold semantics from
`decideEngagement`'s own formula, `sol-gate.mjs:62-84` — NOT a judgment call): for the three
knobs where a LOWER value makes `wouldEngage` easier to satisfy (`SOL_GATE_MIN_MOMENTUM_PCT`,
`SOL_GATE_MIN_LIQUIDITY_USD`, `SOL_GATE_MIN_CONVICTION`), "loosen" = `direction: -1`; for
`SOL_GATE_MAX_STALENESS_SEC`, where a HIGHER value makes `wouldEngage` easier to satisfy (more
cached data becomes usable), "loosen" = `direction: +1` — PLUS a deterministic knob-restriction
mechanism (spec-review FIND-002 fix): WHICH knob is mutated during a starvation-forced pass MUST be
the identified bottleneck knob (REQ-009), not a random pool pick. Iteration-1's REQ-008 only
controlled DIRECTION while leaving `mutate()`'s existing random pool-index draw free to select ANY
of the 4 knobs, so REQ-009's bottleneck identification had no guaranteed effect on WHICH knob was
actually mutated — this revision closes that gap.
**EARS**: THE SYSTEM SHALL extend `sol-genome.mjs`'s `mutate(genome, opts)` with TWO NEW, OPTIONAL,
BACKWARD-COMPATIBLE parameters: `opts.forceKnob` (a single knob key string, or `undefined`) and
`opts.forcedDirection` (a `{ [knobKey]: -1 | 1 }` table).
- WHEN `opts.forceKnob` is a valid member of `MUTATION_SPEC`'s pool, THE SYSTEM SHALL BYPASS the
  existing random knob-count draw AND the existing random pool-index draw ENTIRELY for this call,
  and mutate EXACTLY that one knob (`chosen = [forceKnob]`, `n = 1`) — GUARANTEEING the caller's
  identified knob, and ONLY that knob, is the one mutated.
- WHEN `opts.forceKnob` is `undefined`, `null`, or NOT a member of `MUTATION_SPEC`'s pool
  (malformed/adversarial input): falls back to the EXISTING random knob-count-and-pool-index
  selection, UNCHANGED (fail-open to the PROVEN default behavior, never a crash on a bad key).
- WHEN `opts.forcedDirection` is provided AND contains an entry for the (now possibly
  `forceKnob`-restricted) chosen knob, THE SYSTEM SHALL use that knob's forced direction INSTEAD OF
  the existing `rng() < 0.5 ? -1 : 1` coin-flip for that knob ONLY.
- Every other aspect of `mutate()` (base-clamp, step size, post-step clamp, post-rounding clamp)
  MUST remain byte-identical to the existing implementation, for EVERY call — INCLUDING
  `forceKnob`-restricted calls (only WHICH knob(s) are selected and their DIRECTION are ever
  affected by the new parameters; the clamp/step arithmetic itself never changes).
- WHEN BOTH `opts.forceKnob` and `opts.forcedDirection` are `undefined` (the default, as in every
  existing call site today), `mutate()` MUST behave EXACTLY as it does today (regression-safety,
  PROP-011).
**Edge Cases**:
- `opts.forcedDirection` provided but empty (`{}`) or missing an entry for the chosen knob: falls
  back to the existing symmetric coin-flip for that knob (fail-open, never a crash on a partial
  table) — unchanged from before.
- `opts.forceKnob` provided but NOT one of `MUTATION_SPEC`'s 4 numeric knob keys (e.g. a typo, a
  `FORBIDDEN_CAP_KEYS` entry, or `SOL_GATE_WATCHLIST`): treated as absent — falls back to the
  existing random pool-index selection (fail-open, same convention as a malformed `forcedDirection`
  table; NEVER silently mutates a forbidden/categorical key).
**Acceptance Criteria**:
- WHILE starved (REQ-007's `shouldForceExploration` true) AND `selectBottleneckKnob` (REQ-009)
  returns a non-null knob key, calling `mutate(genome, { forceKnob: thatKnob, forcedDirection })`
  mutates EXACTLY that knob — for EVERY injected `rng` value spanning the FULL domain the OLD
  unconstrained random-index draw would have used (property test constructed so an `rng` sequence
  that would have picked a DIFFERENT knob under the OLD pool-index logic still yields ONLY the
  forced knob under the new logic — proves `forceKnob` actually CONSTRAINS selection, not merely
  correlates with it — PROP-010, strengthened) — and that knob's direction matches REQ-008's fixed
  loosen-direction table.
- A property sweep asserts: for EVERY `rng` seed, WHEN `forceKnob` is supplied, NO knob other than
  `forceKnob` is EVER the one mutated (PROP-019 — the explicit negative assertion FIND-002 required:
  this test is constructed to FAIL against a naive implementation that accepts `forceKnob` as a
  parameter but still falls through to the existing random pool-index selection).
- WHILE NOT starved (no `forceKnob`/`forcedDirection` passed), `mutate()`'s output distribution and
  clamp behavior are UNCHANGED from `franklin-sol-evolvable-edge`'s existing, already-adversary
  -hardened implementation (PROP-011 re-runs that feature's own existing fixtures unchanged).

### REQ-009: Near-miss-driven bottleneck-knob selection during forced exploration
**Mirrors**: ch14 mechanism (c) + `openevolve/evaluator.py:265`'s "don't discard near-miss data" —
concretized here as: WHICH knob gets the forced-loosen this generation is decided by counting which
of the three threshold sub-conditions most often blocked `wouldEngage` across recent near-miss
(skip) trace lines, rather than a uniformly random knob pick from the pool — PLUS REQ-001's own
"exclude malformed/missing-field lines, never coerce to 0" precedent (spec-review FIND-004 fix),
applied here to `no-signal` lines in the tally scan.
**EARS**: THE SYSTEM SHALL implement `selectBottleneckKnob(recentSkipTraceLines)` as a PURE
function that FIRST filters `recentSkipTraceLines` to EXCLUDE any line where `reason === "no-signal"`
OR `momentumPct` is `null`/non-finite (`sol-gate-cli.mjs:112-131`: a data-outage skip — e.g. a
Jupiter API failure, `best === null` — carries NO evidence about which genome threshold actually
blocked engagement; coercing `null`/`Math.abs(null)` to `0` in JS would spuriously fail ALL THREE
sub-conditions for every such line, contaminating the tally with data-outage noise rather than
genuine near-misses). For each REMAINING trace line (the most recent `N` — default 20 — genuine,
non-`no-signal` `decision === "skip"` lines from `sol-gate.trace.jsonl`), THE SYSTEM SHALL
determine, using ONLY that line's own recorded `momentumPct`/`liquidityUsd`/`conviction`/`genome`
fields (already logged by REQ-011 of `franklin-sol-evolvable-edge`, no new field/recording added),
which of the three `wouldEngage` sub-conditions (`abs(momentumPct) >= genome.SOL_GATE_MIN_MOMENTUM_PCT`,
`liquidityUsd >= genome.SOL_GATE_MIN_LIQUIDITY_USD`, `conviction >= genome.SOL_GATE_MIN_CONVICTION`)
evaluated `false`, increments a per-knob fail-tally for EACH such false sub-condition (a single
skip line can increment more than one tally if more than one condition failed), and returns the
knob key with the HIGHEST fail-tally — this is the `knob` value REQ-015's orchestration passes as
REQ-008's new `opts.forceKnob` (spec-review FIND-002 fix: the returned knob is now GUARANTEED, not
merely advisory, to be the one `mutate()` actually mutates). Ties are broken by fixed key order
(`SOL_GATE_MIN_MOMENTUM_PCT`, `SOL_GATE_MIN_LIQUIDITY_USD`, `SOL_GATE_MIN_CONVICTION` — in that
declared order; `SOL_GATE_MAX_STALENESS_SEC` is never a `selectBottleneckKnob` candidate because it
is not one of `decideEngagement`'s three `wouldEngage` sub-conditions).
**Edge Cases**:
- `recentSkipTraceLines` is empty, OR every line is excluded by the no-signal/null-momentum filter
  above (e.g. an entire API-outage window): returns `null` — the caller (REQ-015's orchestration)
  MUST pass `forceKnob: undefined` to REQ-008's `mutate()`, falling back to its existing
  uniform-random knob pick for the forced mutation in this case (never crash, never guess a knob
  with zero genuine evidence).
- All three tallies are zero after filtering (e.g. every remaining genuine skip line failed only on
  the staleness re-check, which is outside `selectBottleneckKnob`'s three-condition scope): returns
  `null`, same fallback as above.
- A mix of `no-signal` lines and genuine near-miss lines in the same window: the `no-signal` lines
  contribute ZERO tally increments (filtered before scanning); the returned bottleneck knob is
  determined SOLELY by the genuine lines, unaffected by how many `no-signal` lines were interspersed.
**Acceptance Criteria**:
- Given a synthetic fixture where `liquidityUsd` fails in 18 of 20 GENUINE lines and the other two
  sub-conditions fail in fewer lines, `selectBottleneckKnob` returns `SOL_GATE_MIN_LIQUIDITY_USD`
  (PROP-012). Given an exactly-tied fixture, the fixed key-order tie-break is deterministic and
  reproducible.
- Given a fixture that INTERLEAVES a large number of `reason==="no-signal"`/`momentumPct: null`
  lines (which, unfiltered, would spuriously fail all three sub-conditions every time) among the
  SAME 20 genuine lines as above, `selectBottleneckKnob` STILL returns `SOL_GATE_MIN_LIQUIDITY_USD`
  — identical to the no-`no-signal`-lines fixture, proving the filter neutralizes their contribution
  entirely rather than merely diluting it (PROP-012, no-signal-exclusion fixture, spec-review
  FIND-004).

### REQ-010: Starvation is self-terminating — resets on the first engage, never a permanent bias
**Mirrors**: ch14 mechanism (b)'s "最低1回 trade が出たら対称 random に戻す" — forced exploration is
an emergency escape valve, never a replacement for the existing, proven symmetric mutation.
**EARS**: THE SYSTEM SHALL treat starvation as resolved the instant `countConsecutiveSkips`
(REQ-007) evaluates to `0` (i.e., the most recent gate-trace line has `decision === "engage"`).
Immediately upon resolution, THE SYSTEM SHALL revert to `mutate()`'s ORIGINAL, fully symmetric
coin-flip behavior (no `forceKnob`, no `forcedDirection`) for every subsequent cadence-triggered
mutation, until a NEW starvation streak independently re-crosses `SOL_GATE_STARVATION_THRESHOLD`.
**Edge Cases**:
- A starvation-forced mutation itself is what CAUSES the next pass to engage (the loosened genome
  now clears real market data): the VERY NEXT cadence-triggered mutation after that engage MUST be
  symmetric, not forced — starvation bias MUST NOT compound indefinitely once it has done its job.
**Acceptance Criteria**:
- `countConsecutiveSkips` on a trace ending in an `"engage"` line, no matter how long the PRIOR skip
  streak was, returns `0` (PROP-013).

### REQ-011: Money-safety caps stay permanently outside every new code path (restated, extends `franklin-sol-evolvable-edge` REQ-004)
**HARD, non-negotiable.**
**EARS**: THE SYSTEM SHALL pass every backtest candidate (REQ-006), every starvation-forced mutant
(REQ-008), and every write target (REQ-005) through `sol-genome.mjs`'s EXISTING, UNCHANGED
`stripForbidden()` before replay and before any file write. `FORBIDDEN_CAP_KEYS`
(`["SOL_TRADE_MAX_SPEND"]`) MUST NEVER appear in any genome object this feature's code EVER
produces, reads back, or writes, under any input including adversarially crafted ones. This
feature adds ZERO new forbidden-cap keys and ZERO new write paths for `SOL_TRADE_MAX_SPEND`;
`resolve-max-spend.sh`'s hard-coded `0.25` choke point in `sol-trade/run.sh` is untouched.
**Edge Cases**:
- A malformed/adversarial trace line or corpus entry that somehow contains a `SOL_TRADE_MAX_SPEND`
  key: excluded/stripped at every read boundary (REQ-001's corpus parse, REQ-006's candidate
  generation), never propagated into a replay or a write.
**Acceptance Criteria**:
- An exhaustive property sweep across `mutate()`'s symmetric output, `mutate()`'s
  `forceKnob`/forced-direction output, and every backtest candidate object asserts
  `FORBIDDEN_CAP_KEYS` absent in 100% of cases (PROP-015 — this is the single highest-priority
  proof obligation in this feature).

### REQ-012: Promotion to the canonical baseline stays chain-verified-only — unchanged, unmodified
**HARD, non-negotiable. Mirrors and restates `franklin-sol-evolvable-edge` REQ-014/REQ-015 (which
this feature does not modify) + `record-swap.mjs`'s `external:false`-by-construction invariant
(FIND-004, also unmodified).**
**EARS**: THE SYSTEM SHALL make ZERO changes to `evaluatePromotion`, `promote` (both imported
UNCHANGED from `evolve.mjs`), `sol-evolve.mjs`'s `runEvolveSol`, `attributeGenomeIdSol`,
`summarizeByGenomeSol`, or `record-swap.mjs`. The ONLY promotion path to
`skills/earn/sol-trade/baseline-genome.json` remains: `>= minRedeems` on-chain-verified
(`row.sig` present, `row.confirmed === true`) SOL swaps, summed `net_usdc`, net-positive, beating
baseline — real money, real signature, real confirmation, exactly as `franklin-sol-evolvable-edge`
already implements. Backtest-derived rubric metrics (`wouldEngageCount`/`totalCount`/
`distinctWouldEngageSignatures`, REQ-002/REQ-003 — count/diversity only, NEVER a P&L estimate) and
starvation-bookkeeping data (REQ-007-010) MUST NEVER be passed into `evaluatePromotion`'s `summary`
map, MUST NEVER set or
influence any genome's `redeem_count`, and MUST NEVER be interpreted anywhere in this feature's
code as "realized" or "confirmed."
**Edge Cases**:
- A backtest-bootstrap-seeded genome LATER accumulates real chain-verified swaps through normal
  live operation: at THAT point it is evaluated by the EXISTING, UNCHANGED `evaluatePromotion` gate
  exactly like any other genome — this feature merely increases the PROBABILITY that a seeded
  genome reaches that point sooner, never changes the gate itself.
**Acceptance Criteria**:
- Calling `evaluatePromotion`/`promote` (via `sol-evolve.mjs`'s `runEvolveSol`) on the SAME
  chain-verified fixtures used by `franklin-sol-evolvable-edge`'s own tests produces IDENTICAL
  verdicts before and after this feature is implemented (PROP-018 — regression parity, proves zero
  drift to the money-gate).

### REQ-013: Identity safety — the trace-corpus READ path MUST become ANICCA_HOME-gated (HARD, corrects a false claim from iteration-1)
**HARD, non-negotiable — spec-review FIND-003 fix.**
**Mirrors**: `franklin-sol-evolvable-edge` REQ-016 (`instanceOverridePath`, ANICCA_HOME-gated,
fail-closed, never cross-instance) — applied here to a path that TODAY is NOT gated that way.
**Ground truth (corrects iteration-1's false claim)**: `instanceOverridePath()` (the WRITE target,
`sol-genome.mjs:91-94`) is genuinely `ANICCA_HOME`-gated today. The TRACE-CORPUS READ path this
feature is built on (`GATE_TRACE_PATH`, `sol-gate-cli.mjs:34-38`) is NOT: it resolves as
`path.join(__dirname, "..", "..", "state", "sol-gate.trace.jsonl")` — derived from the CODE'S OWN
on-disk checkout location, not from `ANICCA_HOME`. In a shared-checkout/per-instance-state layout
(this repo's own convention for shared skill code, memory
`feedback_earn_identity_resolve_per_instance_gate_on_anicca_home.md`), this is a SHARED path
regardless of which `ANICCA_HOME` an instance sets — iteration-1's REQ-013 incorrectly claimed both
the read and write sides were already gated.
**EARS**: THE SYSTEM SHALL CHANGE `sol-gate-cli.mjs`'s trace-path resolution (used by BOTH the
corpus-read, REQ-001, and the starvation-signal scan, REQ-007/REQ-009) so that, UNLESS the operator
has explicitly set the `SOL_GATE_TRACE_PATH` env var (which, when set, continues to take HIGHEST
precedence — an explicit operator override, unchanged), the trace file path is resolved via THE
SAME `ANICCA_HOME`-gated convention `instanceOverridePath()` already uses: explicit `ANICCA_HOME`
env, else `$HOME/.anicca`, joined with the SAME relative segments
(`skills/earn/state/sol-gate.trace.jsonl`) `instanceOverridePath()` already uses for the override
file — NEVER the current `__dirname`-derived shared-checkout path. THE SYSTEM SHALL resolve the
override WRITE target (REQ-005) the SAME way, as it already does today (unchanged, `PROP-017`).
THE SYSTEM SHALL introduce NO new global/shared state file. OUT OF SCOPE: `STATE_DIR`, `CACHE_DIR`,
and `SOL_TRADE_TRACE_PATH` (`sol-gate-cli.mjs:37,39-40`) belong to `franklin-sol-evolvable-edge` and
are NOT touched by this fix — only `GATE_TRACE_PATH`'s resolution changes.
**Edge Cases**:
- A spawn with a different `ANICCA_HOME` running this feature's code: reads its OWN, separate,
  empty trace file (post-fix) and writes its OWN, separate override file — never Franklin's, on
  EITHER side.
- The existing `SOL_GATE_TRACE_PATH` env var is explicitly set (an operator-chosen path, e.g. for a
  test harness): THAT explicit value is used verbatim, exactly as today — this fix changes ONLY the
  DEFAULT (no-env-var) resolution, never the explicit-override escape hatch.
**Acceptance Criteria**:
- For two distinct `ANICCA_HOME` values (neither setting `SOL_GATE_TRACE_PATH`), this feature's
  trace-READ path resolves to two distinct paths, and a trace line appended under one is NEVER
  visible/readable under the other (PROP-020 — NEW, the read-path counterpart to PROP-017's
  write-path proof, spec-review FIND-003).
- For two distinct `ANICCA_HOME` values, the override WRITE target ALSO resolves to two distinct
  paths, and a write under one is never visible under the other, unchanged (PROP-017, restated).

### REQ-014: No evolved CODE in any new module — restated from `franklin-sol-evolvable-edge` REQ-018
**HARD, non-negotiable.**
**EARS**: THE SYSTEM SHALL implement `replayGenomeAgainstCorpus`, `evaluateBacktestRubric`,
`countConsecutiveSkips`, `selectBottleneckKnob`, and the `mutate()` extension as FIXED, reviewed,
non-evolved source code. This feature's mutation/bootstrap machinery SHALL ONLY EVER produce new
numeric KNOB VALUES consumed as data by the EXISTING, UNCHANGED `decideEngagement` — it SHALL NEVER
generate, alter, select among, or dynamically evaluate (`eval`, `new Function`, a genome-supplied
dynamic `import()`/`require()`) any code path in the decision or invocation path.
**Edge Cases**:
- A malicious/malformed genome value (string where a number is expected) reaching
  `replayGenomeAgainstCorpus`: handled by `decideEngagement`'s EXISTING NaN/non-numeric fail-closed
  behavior — never a code-execution sink.
**Acceptance Criteria**:
- Static source-contract test: no occurrence of `eval(`, `new Function(`, or a genome-value-derived
  dynamic `import()`/`require()` anywhere in this feature's new module(s) (PROP-016, mirrors the
  existing source-contract test pattern already used elsewhere in `skills/earn`).

### REQ-015: Orchestration wiring, cadence, and starvation-priority precedence
**New wiring component — composes existing + new pure functions; decides nothing itself beyond
fixed ordering.**
**EARS**: THE SYSTEM SHALL invoke, from within `sol-gate-cli.mjs`'s existing per-pass `main()`
(fail-soft — any failure in this feature's new code degrades to "no seed this pass," NEVER crashes
or exit-nonzeros the calling pass, same convention as every other guard in this file), in this
FIXED order every pass:
1. Compute `countConsecutiveSkips` over the current `sol-gate.trace.jsonl` tail (path per REQ-013).
2. IF `shouldForceExploration` is true: compute `selectBottleneckKnob` (REQ-009) over the current
   recent-skip window, then call `mutate(currentGenome, { forceKnob: thatResult ?? undefined,
   forcedDirection: REQ-008's fixed loosen-direction table })` — GUARANTEEING (REQ-008's
   `forceKnob` semantics, spec-review FIND-002 fix) that WHEN `selectBottleneckKnob` identifies a
   bottleneck, THAT knob (and only that knob) is the one mutated; WHEN it returns `null` (REQ-009's
   empty/all-zero-tally edge case), `forceKnob` is omitted and `mutate()` falls back to its existing
   uniform-random pool pick, with `forcedDirection` still governing whichever knob that random pick
   happens to select — and seed the result as the new override (REQ-005's write mechanism). THIS
   TAKES PRIORITY over step 3 this pass (the emergency escape valve pre-empts the opportunistic path
   when both would otherwise fire the same pass).
3. ELSE, on the EXISTING `SOL_GATE_GENOME_MUTATE_EVERY` cadence (unchanged from
   `franklin-sol-evolvable-edge`): opportunistically run a backtest-bootstrap cycle (REQ-001-006)
   and seed a rubric-passing candidate if one exists; OTHERWISE fall back to the EXISTING symmetric
   cadence-mutation (unchanged behavior, REQ-008's regression guarantee).
**Edge Cases**:
- Both a starvation trigger and a rubric-passing backtest candidate exist in the same pass: the
  starvation-forced mutation is written; the backtest candidate is computed but discarded this pass
  (PROP-014 verifies this precedence explicitly).
- Any step throws (corpus read failure, malformed data): degrades to "no seed this pass," pre-gate
  continues with whatever genome was already loaded — never blocks or crashes the pass.
**Acceptance Criteria**:
- A synthetic fixture engineered to satisfy BOTH triggers simultaneously results in the STARVED
  mutation (not the backtest candidate) being written to the override file (PROP-014).
- A synthetic fixture where `selectBottleneckKnob` deterministically identifies a specific
  bottleneck knob AND the injected `rng` would, under the OLD unconstrained pool-index logic, have
  selected a DIFFERENT knob: the knob actually written to the override file is the IDENTIFIED
  BOTTLENECK knob, never the rng-implied alternate (PROP-019, orchestration-level confirmation of
  REQ-008's guarantee).

## Non-Functional Requirements

- **No new paid dependency, no new network call**: the backtest corpus (REQ-001) is built entirely
  from ALREADY-RECORDED local trace data; this feature calls Jupiter Price v3 zero additional
  times beyond what `franklin-sol-evolvable-edge` already calls.
- **Fail-soft**: no failure mode in this feature (corpus parse error, empty corpus, all-candidates-
  fail-rubric, trace-write failure) may crash or exit-nonzero the calling `sol-trade/run.sh` pass —
  every failure degrades to "no seed this pass," consistent with every other guard in this codebase.
- **Zero live side effect beyond the existing cadence-mutation mechanism**: this feature changes
  WHICH genome is loaded next; it NEVER changes whether `SOL_GATE_LIVE_ENABLE` is honored (REQ-009
  of `franklin-sol-evolvable-edge`, untouched) or what `SOL_TRADE_MAX_SPEND` resolves to (REQ-017,
  untouched).
- **No new secrets, no new wallet access**: this feature reads only local trace/genome files; it
  performs no network calls, no key derivation, no signing.

## Test-Money Safety Rule (MUST — governs Phase 2a/2b test authoring)

Tests for this feature MUST use synthetic, in-memory fixtures ONLY:
- Backtest replay tests (REQ-001-006) use HAND-CONSTRUCTED or property-generated corpus arrays
  (`{momentumPct, liquidityUsd}` objects), NEVER a real network fetch to Jupiter Price v3 and NEVER
  the real, live `state/sol-gate.trace.jsonl` file (a temp/fixture trace file only).
- Starvation tests (REQ-007-010) use HAND-CONSTRUCTED or property-generated trace-line arrays,
  NEVER the real live trace file.
- Promotion-parity tests (REQ-012/PROP-018) reuse `franklin-sol-evolvable-edge`'s OWN existing
  fixtures for `evaluatePromotion`/`promote`, executed against a TEMP git repository (mirrors
  PROP-015's existing "temp git repo, `git show --stat`" test method) — NEVER the real
  `skills/earn/sol-trade/baseline-genome.json` file, NEVER a real `git commit` against this repo's
  actual history.
- No test in this feature MAY perform a real Solana swap, a real Jupiter API call, or a real git
  commit outside an isolated temp directory. A test that requires network or wallet access to pass
  is itself a spec violation (REQ-002/REQ-005's purity requirements) and MUST be rewritten with
  injected/mocked dependencies before Phase 2a is considered complete.

## Edge Case Catalog (cross-cutting, beyond per-REQ edge cases above)

- **Cold start remains possible in the short run**: this feature does not GUARANTEE a trade fires —
  it removes the STRUCTURAL deadlock (never-tried genomes can never accumulate K) by increasing the
  probability that the genome actually tried next is one that would plausibly engage. A run of bad
  luck (thin market, no momentum) can still produce zero trades for a while; this is expected, not
  an error.
- **Corpus contamination across genome generations**: the trace corpus (REQ-001) contains entries
  captured under MANY different past genomes (baseline and various mutants), not just the CURRENT
  candidate's own history — `replayGenomeAgainstCorpus` deliberately re-evaluates EVERY corpus
  entry's raw `momentumPct`/`liquidityUsd` against the CANDIDATE genome's OWN thresholds (not the
  genome that was active when that entry was captured), which is the correct backtest semantics
  (asking "would THIS candidate have engaged on THIS observed market data," independent of what
  genome happened to be active at capture time).
- **Concurrent passes**: this feature follows the SAME single-slot, non-overlapping pass assumption
  already documented in `franklin-sol-evolvable-edge`'s Edge Case Catalog — no new locking
  primitive introduced.
- **Malicious/symlinked state path**: all paths constructed from `ANICCA_HOME`/fixed relative
  segments only, never from genome-supplied or corpus-supplied data — no new path-traversal surface.

## Open Questions for Spec Review

1. **All numeric defaults below are NEW design choices with no prior in-repo number to copy**
   (same situation as `franklin-sol-evolvable-edge`'s own Open Question #1 for its threshold
   defaults): `SOL_BACKTEST_MIN_SAMPLES=20`, `SOL_BACKTEST_MIN_ENGAGE=5`,
   `SOL_BACKTEST_MAX_ENGAGE_RATIO=0.8`, `SOL_BACKTEST_MIN_DISTINCT_SIGNATURES=3` (REQ-004's
   diversity floor, replacing the spec-review-rejected `SOL_BACKTEST_FEE_PCT`/
   `SOL_BACKTEST_UNIT_NOTIONAL_USD` P&L constants — FIND-001, deleted entirely, no successor P&L
   constant introduced), `SOL_BACKTEST_CANDIDATES_PER_CYCLE=5`, and
   `SOL_GATE_STARVATION_THRESHOLD=20`. They are conservative but genuinely invented for this spec
   and SHOULD be scrutinized in spec-review.
2. **RESOLVED (spec-review iteration-1, FIND-001, 2026-07-10)**: the original REQ-003 proposed a
   "momentum-sign-as-realized-direction" simulated-P&L proxy. Spec review found it mathematically
   near-tautological (given `decideEngagement`'s own momentum-threshold range always exceeds the
   fee constant) and backward-looking (crediting an already-elapsed trailing 24h move as a forward
   return) — a fake/dry-run P&L this project's own conventions reject. REQ-003 was REWRITTEN to the
   conservative fallback this Open Question had already anticipated: gate REQ-004's rubric on
   `wouldEngageCount`/`totalCount` non-degeneracy AND `distinctWouldEngageSignatures` diversity
   ALONE — no P&L formula, no P&L constant, of any kind, anywhere in this spec.
3. **Exact module file locations** (e.g. `skills/earn/sol-trade/lib/sol-backtest.mjs`,
   `skills/earn/sol-trade/lib/sol-starvation.mjs`) are an implementation-phase decision, not fixed
   by this spec — MUST follow the existing per-instance/ANICCA_HOME conventions and MUST NOT touch
   any file under `skills/earn/polymarket-trade/` (rail isolation, same mandate as the sibling spec).

## Embedded VCSDD Task List (ordered — do not skip a phase)

1. `vcsdd-spec-review` — fresh-context adversary reviews this behavioral-spec.md +
   verification-architecture.md; PASS requires 0 blocking findings. Iteration-1 findings
   (FIND-001..004) are resolved as of this revision: REQ-003's simulated-P&L formula DELETED
   entirely (Open Question #2, now RESOLVED — replaced with a count/diversity-only rubric),
   REQ-008/REQ-009's bottleneck-knob targeting made deterministic (`forceKnob`, never a random pool
   pick under starvation), REQ-013's trace-READ path corrected to require `ANICCA_HOME`-gating
   (iteration-1's claim it was already gated was false), REQ-009's tally scan excludes `no-signal`/
   null-momentum lines. Particular scrutiny remains warranted on REQ-005/REQ-012's "never touches
   baseline-genome.json" boundary (the single most safety-critical claim in this feature).
2. `vcsdd-tdd` (Phase 2a, RED) — write tests for every REQ/PROP pair in
   verification-architecture.md; confirm new tests FAIL and the existing
   `franklin-sol-evolvable-edge` regression suite (its own `__tests__/`) still PASSES unchanged
   before any implementation line is written.
3. `vcsdd-impl` (Phase 2b, GREEN) — implement the minimum code to pass; `mutate()`'s
   `forceKnob`/`forcedDirection` extension MUST be additive-only (existing call sites unchanged);
   REQ-013's `GATE_TRACE_PATH` fix in `sol-gate-cli.mjs` MUST NOT widen scope to `STATE_DIR`/
   `CACHE_DIR`/`SOL_TRADE_TRACE_PATH`; confirm the FULL existing `franklin-sol-evolvable-edge` test
   suite still passes unchanged (zero regression) alongside all new tests passing.
4. Phase 2c (refactor) — extract/clarify without touching REQ-012's promotion boundary or any test
   assertion.
5. `vcsdd-adversary` — fresh-context Opus adversary reviews the implementation against BOTH specs;
   MUST specifically attempt to find a path by which this feature could write
   `baseline-genome.json`, weaken `SOL_TRADE_MAX_SPEND`/`SOL_GATE_LIVE_ENABLE`, or leak a
   `FORBIDDEN_CAP_KEYS` entry into a written genome — 0 blocking findings required to proceed.
6. `vcsdd-harden` — Tier 2 property-test hardening pass (fast-check) on every money-safety-critical
   PROP (see verification-architecture.md's Tier 2 list), especially
   PROP-010/PROP-015/PROP-018/PROP-019/PROP-020.
7. `vcsdd-converge` — confirm all 4 dimensions (spec, test, impl, verification) agree; only then is
   this feature eligible to actually run live (still gated, as always, behind operator-set
   `SOL_GATE_LIVE_ENABLE=1` — this feature changes nothing about that gate).
