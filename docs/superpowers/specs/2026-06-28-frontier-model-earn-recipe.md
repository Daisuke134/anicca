# THE RECIPE — any frontier-model AI earns more than the human pays (2026-06-28)

Dais 2026-06-28: "first we have to make a recipe for any Claude / any Opus / any of these frontier models
to go earn money by themselves." UBI is owned by another CC and works — this recipe FEEDS the UBI pool
(surplus → UBI), it does NOT rebuild UBI.

## Goal (the one provable thing)
A REPLICABLE recipe so that ANY human-funded frontier-model AI (Claude/Opus today; GPT/Grok/DeepSeek/Kimi
later), running on a subscription the human already pays for, earns MORE than that subscription costs —
self-verifying, no human in the loop — and once in surplus, spawns a self-funded child. Same recipe, swap
the model. Proven first on Claude because that's the subscription we have.

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

## CURRENT STATE (verified 2026-06-28, honest)
- x402 self-facilitate rail: ✅ on-chain settle proven (tx 0x71d4ca08).
- research-product ($0, universal): ✅ adversary-verified 15/15 no-mock.
- serve-mainnet /research: ✅ publicly LIVE proven (pinggy external 402) — but on an EPHEMERAL host.
- README + THESIS reframed to this thesis: ✅ merged to main (PR #657, 9b9b057).
- ★ Realised EXTERNAL earnings = $0 (no buyer yet). ★

## FULL TODO (ordered)
| # | step | status |
|---|---|---|
| A1 | x402 rail (on-chain settle) | ✅ |
| A2 | research-product ($0, adversary 15/15) | ✅ |
| A3a | serve-mainnet public LIVE (proof) | ✅ ephemeral |
| **A3b** | **STABLE host (ngrok-static via AgentMail / CF named / Akash) + x402scan + Bazaar listing** | 🔜 NEXT |
| A4 | first REAL external buyer settle (realised_earn > 0) | ⬜ demand-gated |
| B1 | board-poller skill | ⬜ |
| B2 | audit-bounty skill (Immunefi live) | ⬜ |
| C1 | embed self-verify in every skill | ⬜ |
| C2 | Sonnet daily handoff (claude -p + launchd/schedule; never an incomplete cron) | ⬜ |
| C3 | dashboard register (model-comparison) | ⬜ |
| D1 | model-agnostic runner (Claude→DeepSeek/Kimi/GPT/Grok) | ⬜ |
| D2 | per-skill credential gating + one-command install (generic) | ⬜ |
| E1 | spawn self-funded child (surplus → free-model wallet-only child) → feeds UBI pool | ⬜ |
| F1 | README on main ✅ ; aniccaai.com landing reflect thesis | 🟡 |

## Done = the recipe runs on Claude end-to-end with realised_earn > subscription, self-verified, then the
## same recipe boots on a second model with only the `--model` swap. That proves "any frontier model self-earns."
