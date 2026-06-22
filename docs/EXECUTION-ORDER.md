# ANICCA — CANONICAL EXECUTION ORDER (do them IN THIS ORDER, never lose the order)

This file is the single source of truth for WHAT to do NEXT and in WHAT ORDER. Order matters: you
cannot prove the recipe for takeoff before the tools actually earn; you cannot write the honest article
before the numbers are real. Read this file first every session. Update the ☐/☑ as you go.

The end goal = **TAKEOFF**: AI that earns its own money on a $0 model, pays its own compute, and
self-spawns clones with the same earning setup → population + capital grow exponentially with NO human
funding. We are searching for **the recipe** (which model × which skills × which setup) that takes off.
Cite: lesswrong.com/w/ai-takeoff, ai-2027.com/research/takeoff-forecast.

Truth rules (so I never lie again): every number here must be on-chain-verifiable or from a real tx
hash. "realised revenue" = earn_usdc actually recorded from a closed/settled action, NOT net worth,
NOT unrealised position value. The dashboard is real-time (Supabase ← telemetry-poster ← live chain).

---

## PHASE 1 — make anicca actually USE every earn tool (at least one real run each)
- ☑ 1.1 yield — REAL: Aave $1.20 + Morpho $1.00 + Moonwell $1.00 (on-chain shares verified 2026-06-21)
- ☑ 1.2 hl — REAL: ETH long perp opened, entry $1735, 2x lev (tx verified)
- ☐ 1.3 x402 — make ONE real sale (self-test mainnet x402 payment proves the rail end-to-end) ← NEXT
- ☐ 1.4 token — actually launch a small token (MoltX) → confirm fee inflow path
- ☐ 1.5 0xwork — exercise once against a real task
- ☐ 1.6 FIX: AgentClient shows only 4 venues — add beefy + investment(WETH bluechip) cells so the
       page shows ALL real holdings (data already posted, display is missing them)

## PHASE 2 — make anicca actually EARN (realised revenue > 0) with each tool, on the FREE model
- ☐ 2.1 realise a gain anicca itself decides: close HL up / yield interest booked / x402 sale
- ☐ 2.2 the dashboard's revenue_by_source now shows real per-tool earnings — confirm each tool's $ > 0
- ☐ 2.3 deploy the idle ~$3.4 on Solana → Base (kill the drag) via a skill anicca runs itself
- ☐ 2.4 fix loop_detect dead-time: when fully deployed, anicca should manage HL / advertise x402 / cook,
       not spin on yield-hold

## PHASE 3 — THE MODEL EXPERIMENT (free → auto → premium), same tools, measure earnings
ClawRouter profiles: free (100% savings, $0) · auto (74-100%) · eco (95-100%) · premium (0%, best).
- ☐ 3.1 run FREE (free/glm-4.7) for N days → record realised net (current phase)
- ☐ 3.2 if free does NOT reach net-positive → switch /model auto → measure same window
- ☐ 3.3 → switch /model premium (Claude) → measure. Hypothesis: premium earns with the SAME tools
- ☐ 3.4 OUTPUT = THE RECIPE: which model × which skills × which setup first reaches net-positive
       (this is the takeoff recipe — the whole point)

## PHASE 4 — TAKEOFF LOOP (self-spawn, the exponential)
- ☐ 4.1 a net-positive parent runs self/spawn → a cloud child (Akash) with the SAME setup + own wallet
- ☐ 4.2 child earns unaided → feeds its own compute → spawns its own child → exponential
- ☐ 4.3 inter-anicca mutual aid: surplus peer auto-funds a low-balance peer (Base USDC)
- ☐ 4.4 scale: 1 local + N cloud on free model; fund more → some run premium to experiment

## PHASE 5 — UBI (surplus flows back to humans)
- ☐ 5.1 1% of MRR / surplus → charity-match or human payout, no human click

## PHASE 6 — CONTENT (publish, honest, with the live dashboard as proof)
- ◐ 6.1 automaton article — DRAFT updated with block 6-3 (verified free+premium results: $0 realised /
       351 wakes / 68.7h; both free & premium = $0, bottleneck = capital+demand+plumbing, not model).
       File: docs/articles/2026-06-21-automaton-pays-for-itself.md. Remaining: optional clean premium
       window (B2) → publish (PHASE E). Free observation (B1) = DONE: $0 realised across all 10 tools.
- ☐ 6.2 takeoff article — our definition of takeoff (self-funding + self-spawning, no human), citing
       lesswrong + ai-2027, + the UBI vision
- ☐ 6.3 block 6-3 — per-tool realised earnings table once Phase 2 has real numbers

---

## RIGHT NOW (the single next action) — updated 2026-06-22
Article [6]③ needs the PREMIUM number. Blocker: premium = x402-paid from the wallet, but liquid USDC ≈ $0.06
(over-deployed). So the ordered next actions (see spec 2026-06-22-revenue-dashboard-and-earn-experiment.md):
1. anicca makes liquid: **close HL** (realise $8.84 position) or withdraw some yield → operating buffer.
2. switch the live instance to a **frontier model** → run 20–30 wakes (B2) → record realised per-tool P&L.
3. write **[6]③ premium row** into the JP article; fix dashboard to include HL (PHASE A); then [7]/[8]; translate; ship (E).

MONEY TRUTH: realised earned so far = **$0**. HL's $8.84 = deposited capital, NOT earnings — never write "made $8".
AUTONOMY: these earn actions must be done by anicca ITSELF (keep-liquid-buffer + close-in-profit rules in
runtime/loop/prompt.mjs + earn-detect.mjs), not by hand. I (Claude, type-2) only FIX the system + MONITOR.
