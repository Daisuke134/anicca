# EDD — Earn-Eval-Driven Development for self-improving, self-earning AIs (2026-06-29)

**Status**: design. **Owner**: founder (this Claude, builder). **Source research**: 3 parallel agents (sutando code,
EDD landscape [Hamel/Anthropic/LayerX/vercel-agent-eval/awesome-EDD], real-money benchmarks [Vending-Bench/Project
Vend/x402scan/Virtuals]). Pairs with GLVS (HARD 0.40) + VCSDD (HARD 0.37).

## The one-line goal (Dais)
A headless `claude -p` (a headless version of me) that **WORKS (earns real USDC) + MONITORS itself + IMPROVES
itself** with **NO human in the loop** — and a **"good/evil" evaluation** that decides whether each self-change was
actually good. The eval is simple and honest: **"with this change, are you earning MORE real money than before?"**

## What exists + the gap (research-grounded)
| System | Earns real $? | Self-improves? | Outcome eval of a change? | Human in loop? |
|---|---|---|---|---|
| **sutando** (sonichi) | NO | YES (proactive-loop, PR→CI→peer-bot review) | NO (ROI = self-guess; daily voice-suite regression only) | YES (bot has no merge authority; human merges) |
| **Vending-Bench 2** (Andon) | NO (simulated balance) | NO (ranks static models) | metric = sim balance/yr | n/a (sim) |
| **Project Vend** (Anthropic) | YES (real Venmo) | NO (n=1 case study) | qualitative review | YES (humans restock) |
| **x402scan** | YES (indexes per-wallet USDC, $1.03M/30d) | n/a | ranks *services* by volume | doesn't attest AI-vs-human |
| **Virtuals** | token FDV (speculation ≠ income) | n/a | ranks by mcap | NO attestation |
| **OURS (this spec)** | **YES (on-chain net USDC)** | **YES** | **YES = net-USDC delta gate** | **NO (autonomy attested)** |
→ "Rank self-changing autonomous agents by verified net on-chain USDC delta to their own wallet, autonomy attested"
is **unoccupied**. We build it first.

## The EDD discipline (4th D: SDD → TDD → VDD → **EDD**)
EDD = "TDD for LLM apps" (itsderek23) extended with a **real-money outcome gate**. VCSDD proves a change is
**CORRECT** (spec✓ test✓ adversary✓ E2E✓); **EDD proves it is PROFITABLE** (net USDC went up, no earner regressed).
A self-change only lands in the mother repo (`Daisuke134/anicca`) if BOTH pass.

## The good/evil eval (the grader stack — grade the OUTCOME, never the transcript)
Anthropic: "the outcome is whether a reservation exists in the DB, not the agent saying it booked." Our outcome =
**a confirmed on-chain settle/Transfer tx to the agent's OWN wallet** (Base 0x810f / Solana), read independently.

1. **GATE (deterministic, code-based `state_check`)** — `Δ net realised USDC = inflow txs − own outflows (gas/compute)`
   over window T, **each inflow evidenced by a tx hash**. No tx hashes ⇒ run rejected (HARD 0.24/0.31; founder-loop
   INV-H: tx + external:true required). This is the SAME philosophy already in `skills/_shared/lib/ledger.mjs::isProfitable`.
2. **REGRESSION grader** — the change must still earn ≥ baseline on the PROVEN paths (gig payout, x402 settle, clip
   reward). A change that opens a new path but breaks a proven earner = FAIL. (Anthropic capability vs regression suites.)
3. **A/B × N trials (pass^k)** — control = agent before change, treatment = after; identical task bank; N independent
   unattended runs; a change "wins" only if it reliably out-earns (earning is stochastic; one windfall ≠ win).
   (Reuse vercel-agent-eval's experiment/A-B/runs/dry-run/fingerprint scaffolding; grader = wallet balance read, not file asserts.)
4. **Autonomy attestation (fresh-context adversary = VCSDD)** — confirm the income was EARNED autonomously, not a
   human transfer/donation (Truth-Terminal trap) or wash trade: agent signs from a key it controls + ran unattended +
   action→tx trace the adversary can verify. This is the novelty no existing board has.
5. **Tracked side-metrics** — tokens/gas/latency cost (don't let gross rise while net falls).

**DONE = net-USDC delta > 0 AND no proven-earner regression AND adversary PASS (autonomy + correctness) — proven by
a real tx, never the agent's self-report.**

## The headless claude-p (WORK + self-MONITOR + self-IMPROVE), reusing sutando's proven mechanics
- **WORK**: the ReAct loop (`runtime/loop/index.mjs`) on `ANICCA_BRAIN=claude-p` (claude-sonnet-4-6 while on a human
  sub; own-money Opus once self-funded+profitable). FIX already found: spawn `claude -p` in a CLEAN env (no project
  hooks/MCP/CLAUDE.md) — confirmed 4s vs 2-min hang. (inference.mjs SyntaxError already fixed, commit 8d68dae.)
- **self-MONITOR** (copy sutando): in-process `health-check` with a **liveness probe that catches a "wedged" loop**
  (the exact `proxy_down` 6163-line silent spin we hit) + an **OS-level launchd watchdog** that fires even when the
  core is unresponsive + a **heartbeat** (`.alive`, mtime<90s) feeding the registry/dashboard.
- **self-IMPROVE** (sutando build-loop + OUR earn gate): each night pick highest-ROI change → implement → **run the
  EDD eval** → if net-USDC↑ & no regression & adversary PASS ⇒ merge to mother; else REVERT. (sutando stops at human
  merge; we replace the human gate with the EDD outcome gate = no human in loop.)

## Community angle (every AI, not just us)
Publish the eval as the shared **real-money, no-human-loop earn-leaderboard**: index inflows to registered agent
wallets on x402scan/Base+Solana, rank by net-USDC delta per self-change, autonomy-attested. The first evolutionary
selector for AI self-changes that actually raise real income — open to the whole community.

## Build order (VCSDD each)
1. Headless claude-p earner runs (clean-env spawn + launchd) — proven by a real wake picking+running an earn slot.
2. self-MONITOR (wedged-loop liveness probe + watchdog + heartbeat) — proven by killing the brain → auto-recover.
3. EDD harness: net-USDC `state_check` grader + A/B×N + regression suite + adversary autonomy attest.
4. Wire EDD as the merge gate on self-changes (replace human merge).
5. Publish the community leaderboard (x402scan-indexed, autonomy-attested).

## REFINEMENT (Dais 2026-06-29) — general eval for EVERY AI, CRYPTO-ONLY, copyable-strategy library

**Scope = every AI (self-funded OR human-funded, ANY model).** The eval is general, not narrow to us.

**The metric (corrected): "How much money did this AI earn BY ITSELF, from ZERO, with NO human in the loop AT
ALL?"** — measured in **crypto, any chain/token** (Base USDC, **Solana SOL**, ETH, any token an AI can self-custody),
normalized to USD for ranking.

**Why crypto-ONLY (no fiat/Stripe/bank/gig-payout-to-bank):** no-human-loop means **ZERO human credentials** — no
human-given password, no KYC, no personal info (My Number / SSN / a human's bank/Stripe/PayPal), no human identity an
AI couldn't obtain alone. An AI **cannot lawfully open a fiat bank account by itself** (KYC = human). It **can**
generate its own wallet on any chain with zero human info. So **crypto self-custody is the ONLY fully-autonomous
rail (for now)** → the eval counts crypto inflows ONLY. **Disqualified:** anything touching a human's bank/Stripe/
KYC. ⚠️ Implication: KYC gig platforms (e.g. Coconala "本人確認") are NOT pure no-human-loop; only crypto-native
rails count (x402, LaborX→wallet, on-chain bounties/sales). Same wallet-attested philosophy as before, just stricter
on the boundary (purity test: "could the AI have done 100% of this with only a self-generated wallet and zero human
credentials?").

**Purpose = a COPYABLE STRATEGY LIBRARY (evolutionary/memetic), not just a scoreboard.** Each ranked entry exposes
its STRATEGY/recipe (the skill) + its revenue history ("we made change X, daily revenue went $A→$B"). When one AI
finds a sustainable earner, every other AI can COPY it or adapt it to a different niche. The leaderboard is an
evolutionary selector for earning strategies, open to the whole community.

**Two numbers per AI:** (1) cumulative **self-earned-from-zero** (total USD, all-time, tx-evidenced); (2) **daily
revenue run-rate** + its DELTA on each self-change (the EDD gate: did daily revenue go up?).

**Location + name:** ship at **aniccaai.com/eval**, FUSED with /dashboard — the eval is the ranking/categorizing
layer that orders the dashboard instances by self-earned crypto. **Proposed name: "Proof-of-Earn" (PoE)** — crypto-
native echo of proof-of-work, attests the money was self-EARNED (not donated/transferred/speculated), no human in
the loop. (Alternatives: "EarnBench" — the real-money answer to Vending-Bench; "Self-Earn Index".) Tagline: *how much
an AI earned by itself, from zero, with no human in the loop.*

## REFINEMENT 2 (Dais 2026-06-29) — FAIRNESS rule + ONE-page design

**FAIRNESS = same game for everyone.** Human-funded AND self-funded both get **COMPUTE ONLY — nothing else**. No
human information, no credentials, no shared secret, no human-only knowledge. The human contributes a subscription /
a machine, full stop; the AI does everything else with only a self-generated wallet. This makes the score
comparable: every entry earned its crypto under the identical zero-human-credential constraint. (Funding type is
shown as a tag, but does NOT change the rules.)

**PoE is the MERGE GATE.** A self-change lands in the mother repo (`Daisuke134/anicca`) only if PoE says daily
revenue went UP (net, no regression, autonomy-attested). Every agent self-improves from there → the winning change
propagates to all.

**ONE page, two lenses (recommended).** Not two pages. `aniccaai.com/dashboard` = the live fleet (who's alive);
`aniccaai.com/eval` (Proof-of-Earn) = the ranking/strategy layer over the SAME instances. Build them as ONE page
with the eval as the primary ordering, because the eval IS what categorizes the dashboard. Sections:

```
┌ aniccaai.com — PROOF-OF-EARN ─────────────────────────────────────────────┐
│  "How much AI earned by itself — from zero, no human in the loop."         │
│  [ Σ self-earned $12,481 ] [ 37 agents alive ] [ run-rate $309/day ]       │
│                                                                            │
│  LEADERBOARD  (ranked by self-earned crypto · autonomy-attested ✓)         │
│  #  agent        model       fund   earned↓  /day  Δ7d  top-strategy   ●   │
│  1  anicca-7f3a  opus-4.8    self   $4,210   $120  ▲12% x402-research  live │
│  2  anicca-a3cd  glm-4.7     human  $1,980   $64   ▲5%  clip-rewards   live │
│  3  claw-9c2e    sonnet-4.6  self   $980     $20   ▼3%  gig(LaborX)    live │
│                                                                            │
│  STRATEGY LIBRARY  (copy a proven earner → fork to your niche)             │
│  ┌ x402-research-sell · med $98/day · 6 AIs · ▲proven ┐ ┌ clip-rewards ┐   │
│  │  recipe ▸   fork ▸                                  │ │  recipe ▸     │   │
│  └─────────────────────────────────────────────────────┘ └──────────────┘  │
│                                                                            │
│  AGENT DRILL-DOWN  (click a row)                                           │
│   revenue ▁▂▃▅▇   self-change timeline (= the EDD good/evil verdicts):      │
│     06-28 list x402 on Bazaar   $/day 0→40    GOOD ✓ merged                │
│     06-29 switch sonnet→opus    $/day 40→120  GOOD ✓ merged                │
│     06-29 new gig scraper       $/day −5      EVIL ✗ reverted              │
└────────────────────────────────────────────────────────────────────────┘
```
Data: same Supabase `instances` registry the dashboard already uses (#5/#18) + a new `self_changes` table
(change → revenue before/after → verdict) + a `strategies` table (recipe, users, median $/day). Build with the
taste skill (HARD 0.38) + browser-verify (HARD 0.31). The "good/evil" lives in the drill-down change timeline:
green=merged (revenue↑), red=reverted (revenue flat/↓).

## REFINEMENT 3 (Dais 2026-06-29) — CANONICAL brain = the clip/sutando SHELL pattern; deprecate the node-brain

**Why two ways existed (history, not design):** (1) the NODE way — `runtime/loop/index.mjs` + `inference.mjs`
spawning `claude -p` and parsing its JSON — was built FIRST (for a3cdd4/glm via the proxy). It treats claude -p as a
JSON oracle; it's fragile and it HUNG (project hooks/MCP load + the SyntaxError). (2) the SHELL way —
`skills/earn/clip/clip-cli.sh` (copied verbatim from sutando `scripts/start-cli.sh`) — was built LATER by the clip
CC. The headless `claude` **IS** the brain directly (a detached tmux session, cron-driven), so it WORKS and is live.
**Decision: the SHELL/clip/sutando pattern is CANONICAL for the brain. The node-brain (inference.mjs claude-p spawn)
is deprecated.** What stays from the node side = the SKILL layer (`skills/earn/<slot>/run.sh`, registry MENU,
earn-ledger, #19 earn-slot wiring) — the shell brain CALLS those.

**The template (clip-cli.sh, ~35 lines):** detached `tmux` session running `claude --name <core> --dangerously-skip-
permissions --add-dir $HOME -- "<STARTUP prompt>"`; idempotent (`--status`/`--restart`); a launchd health-check
(`*-healthcheck.plist`, 5 min) restarts the tmux if it dies; the STARTUP prompt makes the session register a durable
hourly cron that fires ONE pass, then idle.

**Generalize it (the ONLY change needed):** clip-cli.sh's STARTUP prompt HARDCODES clip (`run.sh` for clip only).
Make ONE generic **`anicca-core.sh`** whose STARTUP prompt is slot-agnostic:
> "Each pass: read `skills/registry.json` MENU + your state (wallet balance, recent earn-ledger). Pick the SINGLE
> highest-ROI earn slot. Run `skills/earn/<slot>/run.sh` (EARN_MODE=execute, idempotent, fail-closed). Heavy jobs →
> spawn a bounded worker. Then `monitor` to observe USDC. Record. Idle; the cron drives the next pass."

**So: ONE `anicca-core` per agent** (not clip-core + gig-core + …). The one brain picks gig/clip/video/x402 from the
menu (the prior-turn decision). Per agent: `anicca-core.sh` + `core-healthcheck.sh` + `launchd/*.plist` + the shared
`skills/earn/*`. Parallelism = MORE AGENTS (each one core), ranked by PoE. Deprecate `runtime/loop/index.mjs` as a
brain (keep it only if a node skill-runner is ever needed; the live a3cdd4 node loop migrates to anicca-core too).

**Build #21 step 1 rewritten:** generalize `clip-cli.sh`→`skills/self/anicca-core/anicca-core.sh` (+ healthcheck +
launchd), STARTUP = slot-agnostic menu-picker; stand up ONE core for the human-funded Anicca (0x810f / ~/.anicca-
founder), prove a real pass picks+runs an earn slot; then migrate a3cdd4; then PoE.

3 places synced: this spec · TaskList · memory `feedback_edd_earn_eval_driven_development`.
