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
- ◐ 6.1 automaton article — DONE as a FREE-only story, ships NOW. Canonical = docs/articles/2026-06-11-automaton-jp.md
       (worktree ~/.cache/anicca-article-wt, branch docs/frank-article). NOT automaton-pays-for-itself.md (STALE).
       Real numbers in it: そのまま×無料=$0 / そのまま×有料(GPT-5.5)=$0 burned ~$17 / 改造(道具)×無料=+$0.1676 (hl close, on-chain).
       Premium-with-tools is NOT run (Dais 2026-06-23: do NOT fund premium, keep free glm-4.7). Remaining = PUBLISH ORDER below.
- ☐ 6.2 takeoff article — our definition of takeoff (self-funding + self-spawning, no human), citing
       lesswrong + ai-2027, + the UBI vision
- ☐ 6.3 block 6-3 — per-tool realised earnings table once Phase 2 has real numbers

---

## RIGHT NOW — updated 2026-06-23 (DECISION: do NOT fund premium; keep FREE glm-4.7; PUBLISH the JP article NOW)
Premium experiment (PHASE 3.3 / B2) = DEFERRED, not a blocker. The article is a complete free-only story.
PUBLISH JP FULLY first, THEN translate to EN. Ordered next actions:
1. **Article final QA** — 音読 + de-slop the whole piece; resolve [6]①② residual 全角ダッシュ with Dais (EDITOR PROTOCOL); every link → HTTP 200.
2. **Visuals** — [2]/[3]/[4] 🎨 diagrams + thumbnail via the keiodaisuke ChatGPT subscription's **gpt-image** (NO API key; skywork.ai chatgpt-image method).
3. **Publish JP** across media: note → Zenn → Substack(JA) → X Article → TikTok image. Record each live URL (HTTP 200).
4. **Demo video** → YouTube → URL.
5. **THEN EN**: full translate → dev.to → X Article → TikTok image.
6. **Cloud for the launch claim 'クラウド3体・ローカル1体'** (PHASE 4): cloud = the real takeoff substrate; local can't self-spawn (disk-bound), cloud scales infinitely. Fix the genesis/cloud repo so the RIGHT anicca version spins up on Akash; get ≥3 cloud instances LIVE + on the dashboard BEFORE claiming '3体'.
7. **Verify EVERY launch-copy claim is TRUE** (instance count, dashboard live, UBI cron actually sends, self-* crons real) → post the **LAUNCH announcement** with the article URL + YouTube URL.

MONEY TRUTH: realised earned = **+$0.1676** (hl-trade close, on-chain verified). HL $8.94 = deposited capital, NOT earnings.
AUTONOMY: earn actions done by anicca ITSELF (buffer + close-in-profit in runtime/loop/prompt.mjs + earn-detect.mjs).
I (Claude, type-2) only FIX the system + MONITOR + write/publish the article.
