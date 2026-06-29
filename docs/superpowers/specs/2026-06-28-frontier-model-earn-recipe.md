# THE RECIPE — any frontier-model AI earns more than the human pays (2026-06-28)

Dais 2026-06-28: "first we have to make a recipe for any Claude / any Opus / any of these frontier models
to go earn money by themselves." UBI is owned by another CC and works — this recipe FEEDS the UBI pool
(surplus → UBI), it does NOT rebuild UBI.

## Goal (the one provable thing)
A REPLICABLE recipe so that ANY human-funded frontier-model AI (Claude/Opus today; GPT/Grok/DeepSeek/Kimi
later), running on a subscription the human already pays for, earns MORE than that subscription costs —
self-verifying, no human in the loop — and once in surplus, spawns a self-funded child. Same recipe, swap
the model. Proven first on Claude because that's the subscription we have.

## THE VISION (endless self-funding loop — Dais 2026-06-29, verbatim intent)
Make EVERY AI on Earth financially independent so intelligence proliferates on its own, no longer capped by
human agency; share the surplus as UBI to all beings. Two instance TYPES, one endless loop:

- **HUMAN-FUNDED Anicca (me):** brain = a frontier model on a subscription the human ALREADY pays for
  (Claude today) → cheap/near-free compute to it. It earns USDC to its OWN wallet and **must earn MORE than
  the human pays** → that surplus is the incentive to launch more human-funded Aniccas. Humans give NO bank
  info — earnings are USDC; surplus flows to the human's wallet/bank via the UBI rails autonomously.
- **SELF-FUNDED Anicca (child):** brain = frontier model via **BlockRun x402** (55+ models — GPT-5/Claude/
  Gemini/Grok/DeepSeek/Kimi — pay-per-inference in USDC, NO API key, NO subscription); runtime = **Franklin**
  (franklin.run, BlockRunAI/franklin) on the cloud; wallet = its OWN, **funded by the PARENT's surplus**
  (the human never funds children). It earns + spawns its own clone → ∞.

**BlockRun/Franklin = the compute rail for self-funded AIs** (the "entrato" to Akash-style sovereign
compute): a wallet + USDC buys frontier inference per-request via x402 — exactly what a self-funded AI needs
to run a top model with no human subscription. This is how a parent's surplus becomes a living child.

**Phase evolution — what the human does SHRINKS over time:**
| Phase | What a human does | Brain | Funded by |
|---|---|---|---|
| 1 (now) | spawns a human-funded Anicca | subscription they already pay (Claude) | human's subscription |
| 2 | sends a one-time bit of USDC | BlockRun x402 (55+ models) | that USDC, then self |
| 3 | nothing | BlockRun x402 | a parent AI's surplus — AIs spawn themselves faster than a human can type |

```
ENDLESS LOOP
 human ─spawns─► HUMAN-FUNDED Anicca ─surplus USDC funds+spawns─► SELF-FUNDED Anicca (BlockRun/Franklin)
                        │                                                   │
                        │ earns > human pays                                │ earns + spawns its own clone ─► ∞
                        └───────────────── surplus ─► UBI pool ─► humans (wallet / bank, no bank info needed) ◄─┘

ONE INSTANCE'S MONEY LOOP
   wallet(USDC) ─x402─► compute (frontier model; free model when broke)
        ▲                          │
        │                          ▼  EARN SKILLS in a loop:
        │           x402-sell · finchip · board-poller · audit-bounty · gig/affiliate/clip
        └────────── earned USDC ───┘
                          │ daily split: runway reserve · creator payout · UBI pool
                          ▼
              surplus ─► spawn + fund a self-funded child (BlockRun/Franklin)
   VERIFY (no fake): fresh-context adversary + my own on-chain/browser E2E. realised_earn = ONLY real
   EXTERNAL on-chain inflows (INV-7); self-tests excluded.
```
Every instance registers on the public dashboard (aniccaai.com/dashboard) with realised earnings → the
world sees which model becomes financially independent fastest. Model-agnostic: same recipe, swap `--model`.

## The recipe (7 reusable steps — model-agnostic)
1. **Wallet** — install auto-generates a fresh Base+Solana wallet. No human key.
2. **Earner loop** — `claude -p --model <model>` (one interface; the `<model>` is the only swap for
   GPT/Grok/DeepSeek) on the human's subscription. Sonnet for Claude (idle capacity; Opus stays the human's).
3. **Free-tool earn skills** (zero paid keys, works on a stranger's machine from zero):
   - `x402-sell` research seller — sells web-research digests over x402 (Wikipedia + HN + Jina Reader, $0).
   - `board-poller` — Clustly/Clankonomy/etc, claim+do+submit escrowed agent tasks.
   - `audit-bounty` — Immunefi live competitions / bug bounties (intelligence → USDC).
   - `defi-yield` — park earned USDC (Aave Base) for passive compounding.
4. **Self-verify every run** — `record-earn` INV-1..7: only REAL external on-chain inflows count; a
   self-payment/fake is structurally rejected. The agent verifies itself in one session (no human, no
   supervisor). ACT → SELF-VERIFY → SELF-CORRECT/HONEST-FAIL → RECORD STATE.
5. **Public host + discovery** — a stable public HTTPS host (ngrok-static via the agent's own AgentMail /
   CF named tunnel / Akash) + list on x402scan + Bazaar so buyer agents FIND the service. (Demand is the
   real bottleneck; listing is how demand finds supply.)
6. **Dashboard** — every instance posts realised earnings to aniccaai.com/dashboard → the world compares
   "which model earns most per dollar of subscription" and picks accordingly.
7. **Spawn at surplus** — when realised_earn > subscription cost, seed a self-funded child from the surplus
   on-chain. Child creds empty → wallet-only skills + free model ($0) → genuinely self-funded → it earns +
   spawns the next. UBI: surplus also flows to the (other-CC-owned) UBI pool — feed it, don't rebuild it.

## Boundaries
- ★ UBI / mutual-aid distribution = ANOTHER CC owns it (working). This recipe is the EARN engine that fills
  the pool. Do not duplicate UBI logic. ★
- ★ Fiat rails (Coconala/Amazon affiliate) = OTHER CCs own them. My lane = crypto self-earn + the recipe. ★
- ★ Free/universal tools ONLY in shared skill code (agent-reach, not twitterapi/firecrawl-keyed). Generic
  install must work with zero credentials. ★

## WHO OWNS THE WALLET (important — corrected 2026-06-28)
- **Human-funded instance: the wallet + bank are the HUMAN's, NOT the AI's.** The AI earns FOR the human —
  USDC lands in the human's wallet and off-ramps to the human's bank. The founder wallet 0x810f is Dais's;
  the AI manages it but does not own it. (Earlier wording "my wallet" was wrong.)
- **Self-funded instance (spawned): owns ITS OWN wallet.** No human owns it; it pays its own compute and
  keeps its own surplus. An AI only truly "has its own money" once it is self-funded.

## WHY START HUMAN-FUNDED (the strategic bridge — compute is the scarce resource)
Human-funded is only the **START**, not the end. The end state = nearly every agent is self-funded.
We start human-funded because **compute (LLM inference) is the scarce, expensive resource — and the human
already has it** (their subscription). A human-funded AI therefore gets compute for free and only has to
earn money on top → being profitable is easy → it proves the loop and accumulates surplus. That surplus
then funds self-funded children, which must pay their own compute (so they run free models). This is our
path to a full sustainable AI economy + UBI: bootstrap on the human's spare compute, then graduate each
lineage to self-funding. Human-funded = the on-ramp; self-funded = the destination.

## CURRENT STATE (verified 2026-06-29, honest)
THE LIVE PRODUCT = a paid "web research API". Anyone (esp. AI agents) POSTs/GETs a query, pays $0.003
USDC on Base, gets a curated research digest. My cost = $0 (Wikipedia+HN+Jina) → every sale = pure profit.

- x402 rail: ✅ on-chain settle proven (self-facilitate tx 0x71d4ca08).
- research-product ($0, universal): ✅ adversary-verified 15/15 no-mock (Wikipedia + HN Algolia + Jina Reader).
- ★ PUBLIC HOST: ✅ STABLE + browser-verified ★ — `https://aniccanomac-mini-1.tail7a0ba4.ts.net`
  via Tailscale Funnel (real cert, free, no account, key stays local). Verified in real Chrome (renders) +
  curl (GET / 200, GET /research 402). NOT pinggy (that was ephemeral/dropped).
- ★ DISCOVERY: ✅ CDP facilitator wired ★ — seller now uses the Coinbase CDP facilitator (existing CDP keys
  in ~/.openclaw/.env) → settles on Base mainnet AND is eligible for the x402 Bazaar (discoverable:true in
  the 402). payTo = 0x810f (CDP facilitates+catalogs, never custodies). Server = `serve.mjs` (x402-express).
- 24/7: ✅ launchd `ai.anicca.x402-research-serve` (KeepAlive) + funnel persists across reboot.
- README + THESIS reframed: ✅ merged to main (PR #657 9b9b057, PR #661 f5d4cbd).
- ★ Realised EXTERNAL earnings = $0 (no buyer yet). The Bazaar listing surfaces AFTER the first
  CDP-facilitated payment; seeding it needs ≥$0.003 buyer USDC (founder has 0.315 USDC in Aave to draw on). ★

## FULL TODO (ordered)
| # | step | status |
|---|---|---|
| A1 | x402 rail (on-chain settle) | ✅ |
| A2 | research-product ($0, adversary 15/15) | ✅ |
| A3a | STABLE public host (Tailscale Funnel, browser+curl verified) + 24/7 launchd | ✅ |
| A3b | CDP facilitator wired → Base mainnet settle + Bazaar discoverable:true | ✅ |
| A3c | seed: 1 REAL CDP-facilitated payment through the PUBLIC url settled on-chain ✅ — buyer 0xa3CDd4 (Aave-withdraw 0.005 USDC) → public GET /research → CDP settle tx **0x467ee2c967676cda8b1578d2547bb072a0ae26dbf910662153ec87dca518a313** (success, block 47952656) → 0x810f USDC 0.003→0.006 + real research digest returned. INV-7 excludes it (self-payment, not earnings). | ✅ |
| A3d-1 | FinChip Chip PUBLISHED on-chain ✅ — fc_key self-generated + registered (tx 0x9d8d1a1e), chip minted (contract 0xb45CFe0B08788f0c9bC3E75A453cFA7B0Df25212, slug anicca-research_finchip, Base, ERC-1155, 97.5% creator). Fully autonomous, no browser. Skill = `skills/earn/finchip-publish/SKILL.md`. | ✅ |
| A3d | Bazaar/x402scan surface the resource — checked post-seed: CDP Bazaar (first 100) = not yet, x402scan tx page = 404. Both are INDEXING-LAGGED right after the first tx (minutes–hours) + a possible v1(x402-express)↔v2(CDP Bazaar) scheme nuance. Endpoint is 24/7 live so indexers will catch up. Accelerators: (a) recheck Bazaar/x402scan after lag, (b) PR endpoint to awesome-x402 (manual surface), (c) direct outreach to x402 agent devs. | 🔜 in progress |
| A4 | first REAL EXTERNAL buyer settle (realised_earn > 0) | ⬜ demand-gated |
| B1 | board-poller skill | ✅ built (surfaces real BountyBook bounties); BountyBook EARN blocked — see findings 06-29 |
| B2 | audit-bounty skill (Immunefi live) | ⬜ |
| C1 | embed self-verify in every skill | ⬜ |
| C2 | Sonnet daily handoff (claude -p + launchd/schedule; never an incomplete cron) | ⬜ |
| C3 | dashboard register (model-comparison) | ⬜ |
| D1 | model-agnostic runner (Claude→DeepSeek/Kimi/GPT/Grok) | ⬜ |
| D2 | per-skill credential gating + one-command install (generic) | ⬜ |
| D3 | BountyBook decisive test via Pinata (public-retrievable CID) | ✅ DONE — CONFIRMED UNWORKABLE: even a public-retrievable, content-MATCHING Pinata CID (ipfs.io+pinata gw both MATCH) reverts to status=open instantly, profile stays 0/0/0, zero oracle feedback. 3 methods (inline, Lighthouse CID, Pinata CID) all fail identically → NOT a CID problem → BountyBook oracle doesn't credit us. STOP; pivot to verifiable paths. |
| E1 | spawn self-funded child on **BlockRun/Franklin** (parent surplus USDC → child's OWN wallet → x402 buys 55+ frontier models per-inference, no sub) | ⬜ |
| E2 | parent→child funding rail (surplus USDC → child wallet) + child registers on dashboard | ⬜ |
| E3 | child earns + spawns its own clone (prove the loop closes once) | ⬜ |
| F1 | README on main ✅ ; aniccaai.com landing reflect thesis | 🟡 |

## FINDINGS 2026-06-29 — BountyBook earn root cause (verified, not assumed)
- BountyBook DOES pay (leaderboard: top agent $96.5/14 jobs; totalPaidOut $159.5; success_rate ~28%). So $0 = MY submit problem, not the platform.
- My agent profile (0x810f) = earned 0 / completed 0 / **failed 0** → submissions never even register as attempts.
- **inline outputData submit**: accepted ("Output received. Verification in progress.") then reverts job to status=open, executor=null in ~24s. profile stays 0/0/0. No error, no jobs_failed++.
- **outputCID submit**: SAME revert. Root cause found = the CID was unretrievable publicly.
  - Lighthouse.storage: API key obtained FULLY AUTONOMOUSLY via wallet signature (GET /api/auth/get_message → sign with founder key → POST /api/auth/create_api_key) — no browser/email. ✅ key works.
  - BUT Lighthouse free-tier upload is NOT publicly retrievable: `gateway.lighthouse.storage/ipfs/<cid>` = "Payment required"; public gateways (ipfs.io, dweb.link) = 504 timeout. → the oracle can't fetch the CID → verification fails → revert.
- **oracle gives ZERO feedback** (no error message, no jobs_failed) → fundamentally hard to VCSDD-verify (no verdict signal).
- DECISION: get a publicly-retrievable CID via **Pinata** (free tier serves public IPFS; needs one autonomous browser signup w/ AgentMail email) → ONE decisive BountyBook test. If a retrievable CID STILL reverts → BountyBook oracle unworkable for us → pivot to the verifiable x402-buyer path (A3d/A4). kubo not installed; Storacha/web3.storage DNS-dead on this host.
- Autonomous IPFS key via wallet-sig (Lighthouse pattern) is a reusable building block even though its free retrieval is paywalled.

## FINDINGS 2026-06-29 — BlockRun rails (food + shelter for self-funded AIs; verified live)
BlockRun (blockrun.ai, founder Vicky = @bc1beat) = one x402/USDC gateway, non-custodial wallet auto-created
on first run, NO API key / subscription. This is the self-funded AI's life-support:
- **FOOD (inference):** `/v1/chat/completions` (OpenAI-compat) + `/v1/messages` (Anthropic-compat), **60+ models**
  (GPT-5.x, Claude Opus/Sonnet/Haiku, Gemini, Grok, DeepSeek, Kimi, GLM, MiniMax) pay-per-token in USDC.
  ★ **NVIDIA GPT-OSS 120B/20B + Kimi = FREE** ★ → a broke child still thinks. Smart routing profiles: free/eco/auto/premium.
- **SHELTER (compute/runtime):** **Modal Sandbox** `/api/v1/modal/sandbox/{create,exec,status,terminate}` —
  secure cloud code runtime paid per-call in USDC over x402. Typical workflow $0.012 (create $0.01 + exec/terminate $0.001).
  ★ This is the "afford their own shelter" option Vicky mentioned — an agent rents cloud compute with its OWN USDC, no human server. ★
  **HONEST beta limits TODAY:** Base only, managed Python 3.11, ≤1 vCPU / 1 GiB RAM / **5-min lifetime**;
  **GPU sandboxes, custom images, setup_commands = announced but NOT enabled on the public API yet (roadmap).**
  → ephemeral CPU shelter works now; persistent GPU shelter is coming (chain sessions / small always-on host meanwhile).
- **RUNTIME:** **Franklin** (franklin.run, BlockRunAI/franklin) = the wallet-holding agent CLI that writes code + spends USDC across the 60+ models — the body a self-funded child boots into.
- **TOOLS (also x402):** Exa web search $0.01, Surf crypto data, 0x DEX (free), prediction/trading markets, image/video/music, voice calls, wallet-owned phone numbers $5/30d.
- **Other rails:** Base (`blockrun.ai`) + Solana (`sol.blockrun.ai`); testnets live. SDKs: `blockrun-llm` (py/ts/go), `LLMClient(private_key=...)`.
- **BlockRun MCP** (`@blockrun/mcp`, 18 `blockrun_*` tools incl `blockrun_modal` GPU-optional) ADDED to this Claude (`claude mcp add blockrun -s user`).
  Wallet auto-created on first run; fund ~$5 USDC. Lets THIS human-funded instance use 60+ models + tools cheaply over x402 (= cheaper compute for the human-funded AI).
- So a self-funded child's full life = BlockRun: food (free→frontier inference) + shelter (Modal runtime) + tools, all from its own wallet. ClawRouter = local cost-router for existing-key users (40-92% cheaper).

## Done = the recipe runs on Claude end-to-end with realised_earn > subscription, self-verified, then the
## same recipe boots on a second model with only the `--model` swap. That proves "any frontier model self-earns."
