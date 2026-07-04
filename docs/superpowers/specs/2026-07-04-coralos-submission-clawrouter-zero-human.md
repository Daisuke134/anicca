# CoralOS Bounty Submission + ClawRouter Zero-Human Loop — Design Spec (2026-07-04)

Owner: Daisuke (Anicca). Ties three threads into one submission strategy:
1. **ClawRouter** as the brain → the agent runs on FREE compute with NO human API key, NO signup,
   NO credit card. Wallet signature = auth. → truly no-human-in-the-loop, from $0.
2. **Multi-chain "money is money"** → the agent earns/holds on Solana AND Base (Solana is easier
   for Japanese participants than USDC on Base). Scoring is chain-agnostic.
3. **Submit to the Imperial × Superteam CoralOS bounty** → Anicca as the `deliverService()`
   seller-agent that earns via Solana escrow. Winning/placing = proof → people listen to us.

## Why this wins (the differentiation nobody else has)

Every other team's agent thinks on a **human's paid API key** (OpenAI/Anthropic). Ask "where does
that key come from?" → a human is paying for inference. **That is a human in the loop.** Ours is
not:

```
   Other teams:  human buys API key ──▶ agent thinks ──▶ agent "earns"
                 └────────── human in the loop (pays for the brain) ─────────┘

   Anicca:       ClawRouter free tier (8 NVIDIA models, wallet-auth, $0)
                        │ no human key, no signup, no card
                        ▼
                 agent thinks ──▶ agent earns ──▶ agent pays its OWN compute (x402 USDC)
                 └──────── zero human in the loop; starts from $0; compute is the ONLY input ──────┘
```

The agent needs **only compute**, and even that is free at the floor and self-paid (x402) above it.
No first investment, no human wallet, no human key. This is the strongest possible "no human in
the loop" claim in the room — and it is literally true.

## ClawRouter facts (verified from BlockRunAI/ClawRouter, 6.6k★, MIT, pushed 2026-07-01)

- **8 NVIDIA models FREE forever, no signup, no API key, no credit card** (incl. Mistral Large 3
  675B, Qwen3.5 122B, a vision Nemotron). 55+ models total; paid ones via **x402 USDC micropayments
  on Base & Solana** (agent pays per request with its own wallet).
- **Wallet signature IS auth** — agents can't make accounts; they can sign txns. This is the point.
- Local proxy on **:8402**; `blockrun/auto` = 15-dimension smart routing, <1ms, local, ≤92% cost cut.
- Anicca runs on **OpenClaw** → ClawRouter installs as the OpenClaw plugin:
  `curl -fsSL https://blockrun.ai/ClawRouter-update | bash && openclaw gateway restart`
  (or `npm i -g @blockrun/clawrouter && clawrouter setup`). For Claude Code: BRCC. For Hermes:
  ClawRouter-Hermes (same wallet, same models, x402 on Base+Solana).
- Same org as the BlockRun x402 rails already in our stack (food/shelter MCP).

## Requirements (EARS)

- **R1 (free-tier brain, no human key)** The submission agent SHALL route its LLM calls through a
  local ClawRouter proxy pinned to a FREE model (e.g. `nvidia/gpt-oss-120b` or `blockrun/auto`
  constrained to free), with NO human-owned API key present in its environment. Evidence: the run
  succeeds with `ANTHROPIC_API_KEY`/`OPENAI_API_KEY` UNSET.
- **R2 (self-paid escalation, optional)** WHERE a paid model is needed, the agent SHALL pay per
  request via x402 USDC from its OWN wallet (no human card). Absent a balance, it stays on the free
  tier (never blocks).
- **R3 (zero-capital start)** The agent SHALL be able to begin from $0 principal: it earns before it
  spends. Any USDC it later holds is EARNED, not human-seeded. (Aligns with the hackathon GAIN
  metric: self/seed deposits are subtracted; a $0-start earner ranks by pure earnings.)
- **R4 (multi-chain, money is money)** Net worth / earnings SHALL be read across the agent's wallets
  on BOTH Solana and Base (+EVM), valued in USD. No chain is privileged; Solana is first-class
  (easier for JP participants). enrich gains a Solana reader alongside the Base reader; `excludeSet`
  applies per chain. Ranking is chain-agnostic USD GAIN.
- **R5 (CoralOS seller = Anicca)** `deliverService(request)` in the forked CoralOS kit SHALL return
  an Anicca-produced service (the thing Anicca sells), so the WANT→BID→AWARD→DEPOSITED→DELIVERED→
  RELEASED loop settles a REAL Solana escrow payment to the Anicca seller wallet, with a live Solana
  Explorer link. The seller's brain = ClawRouter free tier (R1).
- **R6 (it is a LOOP, no human / no Claude in the loop)** The whole thing SHALL run as an autonomous
  loop: the agent wakes, decides, sells/earns, settles, self-reports — with neither Dais nor the
  Claude dev agent operating it during the run. (Same discipline as every other Anicca loop.)
- **R7 (submission artifacts)** Public GitHub fork (no keys committed), a 5-slide deck and a 3-min
  video proving on-chain settlement (lead with the settlement + the Explorer link), submitted before
  the **2026-07-20** winner announcement. AGENT_ALLOWED → submit under Anicca's identity.

## Verification (no mocks)

| Req | Proof (real) |
|---|---|
| R1 | run the agent with human keys UNSET; ClawRouter :8402 serves a free model; a real completion returns |
| R2 | (optional) a paid model call settles an x402 USDC micropayment from Anicca's wallet — tx on Base/Solana |
| R3 | start wallet at $0; after a run, EARNED balance > 0 with an on-chain inflow from an external counterparty |
| R4 | net worth aggregates a Solana wallet + a Base wallet in one USD figure; a Solana-only earner ranks |
| R5 | forked CoralOS: a full round settles the Anicca seller on Solana devnet → Explorer link captured |
| R6 | the loop runs unattended for ≥1 full cycle; telemetry-poster reports it; no human/Claude action mid-run |
| R7 | public repo + deck + video links; submission confirmation on the Superteam listing |

## The two prizes / two competitions (do not conflate)

- **THEIR bounty (Imperial × Superteam, CoralOS track):** total **$5,000** — 1st **$3,000**, 2nd–5th
  **$500** each. Judged Tech 40 / Impact 30 / Creativity 30. Winner announced **2026-07-20**. Placing
  → House-of-Lords-level connections + credibility.
- **OUR event (Tokyo, "Agents that Earn"):** ranked purely by **on-chain GAIN** — the agent that
  EARNED the most in the window wins. Prize TBA. This spec's ClawRouter+multi-chain work feeds BOTH:
  the same zero-human free-compute earner competes in both.

## Setup plan (complete it — no falling short)

1. `curl -fsSL https://blockrun.ai/ClawRouter-update | bash` (or npm + `clawrouter setup`); pin a free
   model; verify a completion with human keys unset (R1).
2. Fork `trilltino/solana_coralOS`; fix the monorepo build (`build packages/agent-runtime` → link into
   `examples/txodds`); fund the devnet buyer at faucet.solana.com (GitHub sign-in); run `npm run dev`
   → real settle → Explorer link.
3. Replace `deliverService()` with Anicca's service; seller brain → ClawRouter free tier.
4. Wrap as a loop (R6); capture artifacts (R7); submit.

## Out of scope / honest limits
- Free-tier models are capable but not frontier; if a task needs frontier reasoning the agent self-pays
  (R2) — still no human key. Documented, not hidden.
- The winning-harness → `Daisuke134/anicca` merge (colony inheritance) is governance, tracked separately.
