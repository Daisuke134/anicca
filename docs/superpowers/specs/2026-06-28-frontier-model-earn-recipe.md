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
| A3d | Bazaar discovery API surfaces the resource (CDP indexing lag after first payment) — recheck `GET api.cdp.coinbase.com/platform/v2/x402/discovery/resources`; if slow, ALSO PR to awesome-x402 + register on x402scan. | 🔜 NEXT |
| A4 | first REAL EXTERNAL buyer settle (realised_earn > 0) | ⬜ demand-gated |
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
