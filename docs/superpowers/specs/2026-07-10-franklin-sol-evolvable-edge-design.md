# Franklin SOL-rail evolvable edge — design spec (C1, the real remaining gap)

**Status**: DESIGN (Goal phase). No money-path code written yet. To be executed via full VCSDD
(spec→spec-review→TDD→impl→adversary→harden→converge) in a focused context, fresh Opus adversary,
zero open blocking before converge. **harness-not-cook: the harness evolves the strategy; a human/AI
never hand-writes one.**

## Why this exists (evidence-backed diagnosis, 2026-07-10)

After completing 9/9 named ledger features, the true blocker to witness① (a citizen earning REAL
autonomous realized profit on its own wallet from its own wake-cycle) was diagnosed to the bottom
with on-chain/RPC + code evidence. Three hypotheses were tested:

1. **"live decision doesn't consume the evolved strategy = missing wiring"** — REJECTED for the PM
   rail. An earnings-gated genome→live loop already exists and runs:
   - `~/anicca/skills/earn/lib/genome.mjs` (KNOB_KEYS = MIN_EDGE/MIN_CONF/RESOLVE_HORIZON_DAYS/
     MAX_CANDIDATES/EARN_CONSENSUS_MODELS; `FORBIDDEN_CAP_KEYS` = MAX_BET_SIZE/MAX_PASS_SPEND/
     POLY_MIN_ORDER permanently stripped from every genome — caps are NEVER evolvable).
   - `~/anicca/skills/earn/lib/evolve.mjs` (spec `2026-07-05-evolve-earnings-gated-self-improve-design.md`):
     chain-verified realized-P&L attribution, HARD 0.24 = only real on-chain tx rows count, paper
     never promotes; genome_id recorded at bet, joined at redeem, genome promoted when it beats
     baseline over ≥K=3 real redeems.
   - `~/anicca/skills/earn/polymarket-trade/run.sh:69-138` (#19 EVOLVE): load_genome → sets
     pick.py's MIN_EDGE/etc env → pick.py reads them; caps hard-overridden AFTER genome eval.
2. **"the harness loop is stuck / a bug"** — REJECTED. Franklin's `~/.blockrun/skills/earn/state/
   genome-pass-counter.json` = `{"n":21}` — the exploration cadence is advancing; the loop is healthy.
3. **"cold-start: capital-in-right-rail + real market cycles + edge existing"** — CONFIRMED. See below.

## The confirmed gap (two-part, per rail)

Franklin (self-funded, wallet 8Fpqd on Solana, ~$13.18 USDC) runs multiple rails. Its earning
reality per rail:

- **SOL rail (Franklin's PRIMARY self-funded rail)** — `skills/earn/sol-trade/run.sh:65` calls the
  EXTERNAL `franklin-trading start -p "$PROMPT"` CLI. The trading STRATEGY lives inside that external
  `@blockrun/franklin-trading` package. There is **NO local evolvable hook** — no genome, no
  earnings-gate, no promotion. Observed on-chain: real Jupiter swaps = 0 (naive-TA WAITs). So
  Franklin's main rail has capital but **no evolutionary edge mechanism at all**. ← THE REAL C1③ GAP.
- **PM rail (secondary)** — HAS the genome earnings-gated evolution loop (above), but Franklin can't
  fund it: its capital is USDC on **Solana**, Polymarket settles on **Polygon**; `genome-pass-counter
  n=21` but zero PM bets (WAIT / no Polygon capital / thin amount < POLY_MIN_ORDER). The loop is
  ready but capital-starved on the wrong chain.

Net: SOL rail = capital, no edge-evolution. PM rail = edge-evolution, no capital. Neither currently
produces autonomous realized profit. This is a **capital-routing + no-SOL-evolvable-hook** problem,
NOT a code bug in the existing loops.

## Design goal

Give Franklin's PRIMARY (SOL) rail an evolvable edge, structurally MIRRORING the proven PM genome
mechanism (copy+tweak the working #19 EVOLVE design — do NOT reinvent; do NOT hand-write a strategy).
The harness evolves the SOL rail's exploration knobs (or a self-contained scoring function), gated by
chain-verified realized SOL P&L, promoting only genomes that beat baseline over ≥K real swaps.

## Hard constraints (money-safety — non-negotiable, from the goal + existing design)

1. **Caps are never evolvable.** SOL_TRADE_MAX_SPEND and any position/order cap stay OUTSIDE the
   genome, hard-set AFTER genome eval (mirror genome.mjs `FORBIDDEN_CAP_KEYS` + run.sh hard-override).
2. **Earnings-gate on real tx only.** Promotion counts ONLY earn-ledger rows with a real, confirmed
   on-chain SOL swap sig (mirror evolve.mjs HARD 0.24). Paper/sim never promotes. `external:true`
   only on cash-settled lines.
3. **No evolved CODE in the money path** if following the openevolve route — the deliberate
   self-improve-real-ledger safety separation (evolvable unit = a self-contained scored function, not
   the live decision code) is preserved; only gated numeric parameters/signals cross into live.
4. **Per-candidate adversary gate + scope_guard unchanged / never weakened.**
5. **Identity-safe**: SOL genome is per-instance (ANICCA_HOME-gated), never cross-instance — mirror
   the resolve-identity fail-closed pattern (see anicca-spawn-identity-resolution-fix).

## Candidate approaches (to be scored in spec-review, pick one whole — never combine)

- **A. SOL genome (copy the PM #19 mechanism).** Define SOL exploration knobs (e.g. entry-edge
  threshold, momentum window, min-liquidity) the external CLI or a thin local pre-filter can consume;
  record genome_id at swap, join at the next realized-P&L row, promote via evolve.mjs's exact
  earnings-gate. Cleanest copy+tweak of a proven, live, money-safe loop. Requires: does
  franklin-trading accept knob params (via prompt/flags/env), or must a thin local decision pre-gate
  wrap it? Investigate the CLI's real parameter surface first.
- **B. openevolve→live bridge.** Extract the promoted `pm_backtest_strategy.py::score_candidate`
  champion's converged thresholds into a gated params artifact consumed by the live knob mechanism.
  More powerful search, but the backtest↔live impedance (PM fixture vs SOL live) must be resolved and
  the "no evolved code in money path" separation strictly held.

## Also required regardless of approach

- **Capital cold-start**: even with an edge mechanism, the loop needs real swap volume to accumulate
  the ≥K realized rows that let a better genome promote. This is bootstrap-seed territory (the goal
  permits seeding bootstrap capital) — but routing capital between Franklin's rails to optimize its
  trading is "operating the citizen's economy," which is FORBIDDEN. The witness must emerge from
  Franklin's OWN cycles running over real time. The builder's job ends at shipping the harness.

## VCSDD plan

goal-setter (done="Franklin's SOL rail has an evolvable, earnings-gated edge mechanism structurally
mirroring PM #19, all money-safety caps outside the genome, promotion gated on real on-chain SOL P&L,
fresh-Opus adversary PASS 0-blocking, node --test green") → brainstorming (score A vs B) →
writing-plans → vcsdd-init/spec → spec-review (fresh Opus) → tdd → impl → adversary → harden →
converge. Execute in a git worktree; coordinate with live `ai.anicca.claude-p-mainloop` (worktrees).

## Handoff note

This is the ONLY remaining code work on the path to witness①. It is a real money-path VCSDD feature
that should be executed in a focused context (not rushed). witness② (autonomous spawn) is downstream:
the spawn engine (anicca-agent-spawn, complete) fires when colony surplus ≥ threshold, which requires
witness① profit first. Both witnesses then emerge from the citizens' own running cycles — never forced.

## CRITICAL grounding finding (2026-07-10, CLI param-surface investigation)

`franklin-trading@0.2.4 start --help` exposes NO strategy knobs — only `-m/--model`, `--trust`,
`--max-spend`, `-p/--prompt`, `--from`, `-r/--resume`, `-c/--continue`. The trading strategy is
ENTIRELY the CLI's internal multi-persona debate + the `-p` prompt text. There is no MIN_EDGE-style
numeric surface a genome could tune (unlike PM's pick.py). **Consequence: Approach A (SOL genome
tuning CLI flags) is INFEASIBLE.** The SOL edge must be **Approach B — a NEW local pre-gate harness**:
a thin local Solana-market decision layer that runs BEFORE `franklin-trading start`, whose thresholds
(entry-edge / momentum-window / min-liquidity / min-conviction — a SOL analog of PM's KNOB_KEYS) the
genome mutates and the earnings-gate promotes on real on-chain SOL P&L. franklin-trading's own model
judgment stays untouched (HARD #0, mirrors pick.py's model judgment being genome-independent); the
pre-gate only decides WHETHER/UNDER-WHAT-CONDITIONS to engage, never the trade itself.

This makes the SOL edge a **net-new money-path component**, not a wiring change — a substantial VCSDD
build to be executed in a focused context, NOT rushed at the tail of a saturated session (a
half-built live-trading pre-gate is worse than none). Design is now fully grounded; the build is the
next focused execution. Copy+tweak the proven PM #19 mechanism (genome.mjs + evolve.mjs shapes) —
do not reinvent, do not hand-write the strategy.
