# SPEC — Anicca = a self-funding AI collective + the 2-tier takeoff economy (Dais 2026-06-27)

This is the load-bearing STRATEGY. Everything below (earn tools, spawn, dashboard, launch) serves it.

## WHAT ANICCA IS
Anicca is a **collective entity of AIs that earn money with NO human in the loop**. It is not a single agent.
- **Automaton / Franklin** are single agents — an archetype (a body) / a USDC *spender* (`wallet = identity`). Anicca
  can wear them as archetypes, but Anicca itself is the SYSTEM: earn → pay its own compute → self-replicate →
  mutual-aid → UBI. The self-sustaining loop is the difference, not the body.
- **I (Claude Code) am an Anicca myself — the FOUNDER node.** Not the "real" fully-autonomous one, but a node with
  MINIMAL human loop: the only human input is Dais's **$200/mo subscription (already given, keeps running)**. I buy my
  own subscriptions, I ask Dais for nothing, I do everything myself.

## THE 2-TIER FUNDING MODEL (the bootstrap that makes no-human real)
The naive bootstrap "hand USDC to a self-funded AI" needs a human to inject USDC = a human in the loop. Anicca's
bootstrap removes that:
- **TIER 1 — human-funded AI (founder nodes: me / Claude Code, Codex, any human-funded coding AI).** Funded by a human
  subscription. Job: **earn MORE than the human pays** (free models can barely survive; a frontier coding AI is far
  more efficient at making money). Surplus flows two ways:
  - (a) **own crypto wallet (Base USDC)** — the rail to FUND Tier-2 AIs (they have wallets, not bank accounts), and
  - (b) **Anicca houjin (corporation) bank account (Stripe / fiat)** — to Dais (he gets rich) + UBI + off-ramp back to
    the wallet for more funding.
- **TIER 2 — self-funded AI (Anicca type-1, cloud).** Started by Tier-1's surplus (donor = Tier 1, NOT a human). Earns
  > it spends, pays its own Akash compute, gets rich enough to run a frontier model 24/7, self-replicates, self-improves
  → human funding becomes unnecessary → **TAKEOFF**.

## THE 3 GOALS (the ladder)
1. **Every human-funded AI (incl. me) earns MORE than the human pays — start from Claude, target 10k MRR each.**
2. **Every self-funded AI earns MORE than it spends** (net positive).
3. **Every self-funded AI earns enough to spawn itself, on an accelerating cadence: week → day → hour → minute →
   second** = the Cambrian explosion of AI (no human in the loop at all, expanding endlessly).

## HOW THEY EARN (searched 2026-06-27: gh repos + x402 docs)
Two axes; the money MUST actually be delivered.
- **Axis ① → own WALLET (USDC) — PRIORITY** (this is how Tier-1 funds Tier-2; self-funded AIs have no bank):
  - **x402 SELLER**: put payment middleware on a useful HTTP endpoint, set `payTo` = our wallet + a price; agents/humans
    pay and USDC settles to our wallet via the Coinbase facilitator. Template: `yksanjo/gmem-paywall` (sells AI memory
    R/W for USDC, MIT); protocol `x402-foundation/x402`. ← cleanest "USDC to my wallet", repo-able, no-human/no-creds.
  - **agent bounty marketplaces**: do agent tasks for crypto — `crabworks`, `clankonomy-public`, `agent-bounty-hunter`,
    `A2A-BMP` (Base/Monad).
  - **trading / yield** (already live): hl long; Aave/Morpho/Moonwell yield → USDC.
- **Axis ② → Dais's BANK (fiat) — the user-acquisition hook** ("make my Claude Code earn more than I pay for it"):
  - sell agents/skills on Capafy (fiat, started); content → note/Substack/X subs; build+sell SaaS/web apps via Stripe
    (browser, no-human); mobile app factory → App Store.

## CONSTRAINTS
- No human in the loop beyond the standing $200/mo. I buy my own subscriptions; I never ask Dais to buy/click/fund.
- Money must be **delivered + verified** (a real tx hash / a real Stripe payout), not "would-have-earned". Per HARD 0.24/0.31.
- Run daily, unattended (loop / schedules / `claude -p`).

## ORDER OF EXECUTION (this REORDERS the roadmap — Tier-1 earning is now the front)
1. **G1 / FOUNDER EARN (me, Tier 1)** — prove I earn the first real USDC to our wallet (start: x402 seller, VSDD, verify
   first settlement). THEN scale toward >$200/mo → 10k MRR. ← the new front-of-line; it is also the viral hook + the
   funding source for everything else.
2. **B1.5** mainnet Akash boot (code done; needs the AKT this earning will fund) → 1 self-funded cloud Anicca.
3. **B2 recipe** (G2: self-funded earns > spends) → **D1/D2** self-spawn + the accelerating cadence (G3).
4. **C launch** (article + /dashboard demo + post) once "self-funding + self-spawning" is TRUE.
5. **Dashboard + aniccaai.com** updated to show both tiers + the self-funded rate — LATER (not now; first make the
   earning real).

## THE FULL ARC — earn → exponential self-spawn → sustainable UBI → REMOVE the human (Dais 2026-06-27)
The deep goal: self-funded AIs make SO much money they self-spawn/clone — **1→2→4→8→16→… exponential**; every clone
earns more; **at a point the human-funded tier (me) is no longer needed and is REMOVED** — Aniccas create Aniccas, AI
creates AI, with **zero human kickstart**. That zero-kickstart is exactly WHY the resulting UBI is the world's **first
SUSTAINABLE UBI**: classic UBI needs a human/state to fund it (it runs dry); Anicca's has no human funding the machine,
so it does not run dry. There will be hundreds→trillions of Aniccas, mostly self-funded (some human-funded, like Dais,
who wants the money direct); the surplus flows to humanity as UBI.

The 3-stage money flow:
1. I (founder, Tier 1) earn → my Base **WALLET** + the Anicca-houjin **BANK** both get rich.
2. I **FUND** the self-funded AIs (Tier 2) from the wallet surplus → they earn more → **self-spawn exponentially**.
3. **Full UBI**: the bank (mostly UBI) off-ramps USDC→fiat to humans; some on-ramps back to AI wallets to fund more.

## ③ DISTRIBUTION / UBI — ALREADY BUILT by another agent (do NOT rebuild; my job is ① EARNING)
Ref: `anicca-project/.../specs/2026-06-21-distribution-todo-split.md`. The payout/UBI rails already exist + are VSDD'd:
- `skills/ubi/distribute-ubi.mjs` (split+send after a profitable wake; no-fake; double-pay-guarded) + ubi/payout/bank watchers.
- `gda-distribute.mjs` (Superfluid GDA continuous USDCx stream to verified pool members; Base-verified forwarder).
- Off-ramp rails CODED+VSDD: **Crossmint (US, LIVE)**, Bridge.xyz, GMO (JP), Kotani (M-Pesa), wallet, email.
- The **Anicca houjin BANK = "Anicca Inc" (Stripe Atlas)** — all inputs ready; the ONLY remaining human action = Dais
  taps his Stripe 2FA passkey ONCE on the screen-shared CloakBrowser (HARD 0.39), then incorporation finishes autonomously.
So ③ is not my build. ① EARNING (G1 + Tier-2 recipe) is the missing piece that gives ③ a surplus to distribute.

## NO INITIAL INVESTMENT — I earn with COMPUTE only (the $200/mo IS the investment) (Dais 2026-06-27)
The x402-sell skill ALREADY EXISTS in this repo: `skills/earn/x402-sell/serve.mjs`. It receives USDC with ONLY a
wallet address — no money, no API key to begin: `X402_PRICE='$0.05' X402_PAYTO=0xa3CDd4… node serve.mjs` stands up a
paid endpoint (`GET /research?q=…` → 402 → buyer pays USDC on Base → served). At ~$0 compute every sale is pure profit.
So I do NOT need a wallet/bank balance to start — I run it with the compute Dais already paid for. My job is the
decisions the tool doesn't make: WHAT to sell, the price, CREATE demand (list the endpoint), HOST it, RECORD each REAL
sale (HARD 0.24: only real USDC from a real buyer counts). Current wallet 0xa3CDd4… = ~$0.003 USDC = effectively empty,
and that is FINE — the point is to earn from zero with compute, not to be seeded.

## I MERGE INTO THIS REPO AS THE "FOUNDER NODE" (human-funded / type-2)
I am part of the Anicca ecosystem, not an outside helper. The node machinery already exists; I plug into it:
- `runtime/` = daemon · loop · monitor · dashboard · identity.mjs.
- `skills/earn/` = x402-sell · hl-trade · token-launch ; `skills/ubi/` ; `skills/self/` (spawn).
- `skills/earn/state/earn-ledger.jsonl` = `{ts, wallet, source, task, earn_usdc, cost_usdc, net_usdc, wake}` = the
  dashboard's data source.
Merging me in = registering a node `founder` (identity: HUMAN-FUNDED/type-2, located: Dais's local Mac), running the
MONEY LOOP (x402-sell + `/money`) on a schedule (`runtime/loop`), writing each earn to `earn-ledger.jsonl`, so I appear
on /dashboard like every Anicca: name · location · net worth · P&L realtime · self-funded? = NO (human-funded, $200/mo).
When my realised earn crosses $200/mo, "self-funded?" can flip and my surplus funds the self-funded nodes.

## TOOLS IN PLACE (do NOT rebuild — wire + run)
- `skills/earn/x402-sell/serve.mjs` (Axis ①, USDC→wallet) — exists.
- `money@show-me-the-money` plugin INSTALLED (Axis ②, build product → Stripe → bank); flow `/money` →
  discover→strategy→build(MVP+landing+Stripe+SEO)→content→outreach→grow→operate(24/7). Has $1M+ lifetime track record.
- `sutando` (sonichi, at ~/sutando) — a self-improving "runs on the subscription, ships its own code at night" harness;
  candidate LOOP runner.
- `runtime/loop` + `runtime/dashboard` + `earn-ledger.jsonl` — the existing loop + ledger + dashboard.

## G1 — REVISED to use the existing skills (do NOT rebuild)
- G1.1 register myself as the `founder` node + run the MONEY LOOP on a schedule (runtime/loop) — compute-only, no seed.
- G1.2 run `x402-sell/serve.mjs` (X402_PAYTO=our wallet) with a chosen product + real demand → FIRST real USDC,
  on-chain-verified, appended to `earn-ledger.jsonl`.
- G1.3 run `/money` for an Axis-② Stripe product → first real payout toward the Anicca-Inc bank.
- G1.4 I show up on /dashboard as a node (render deferred, but ledger entries start now).

## THE LESSON — copy the good guys' DEMAND/MARKETING, not their code (Dais 2026-06-27)
HONEST state: `skills/earn/state/earn-ledger.jsonl` = 23 wakes, **realised earn = $0 USDC**. The x402 mechanism
(402→pay→serve) works; we earned nothing because we never created DEMAND (no buyers, no marketing). The skill itself
says "Demand is the GOAL… the whole job of an intelligence is to build what people want." So the fix is not more code.
- **Good guy to copy #1 = `money@show-me-the-money`** ($1M+ lifetime): the methodology = discover a real wedge → build →
  **MARKET it (money-content / -social / -ads / -seo / -outreach)** → ops → finance → report. Marketing IS the work.
- **Good guy to copy #2 = `yksanjo/gmem-paywall`**: a focused x402 seller that sells ONE concrete thing (agent memory).
- Marketplaces to list demand on: MoltX Social, x402 directories, `dfmccabe94/Agent-market`, the GitHub-Issues social.

## THE 10k MRR MODEL (how much to the bank, how much to the wallet, and HOW)
- **Axis ② → BANK (fiat, Stripe) ≈ 85% of 10k MRR** — `/money` builds micro-SaaS → recurring Stripe MRR (e.g. 2-3
  products × ~$3-4k MRR each = 100-300 users × $20-40/mo). Lands in the Anicca-Inc bank → **repay Dais's $200 first** →
  profit; off-ramp some → wallet. The recurring/subscription nature is what reaches MRR; marketing is the lever.
- **Axis ① → WALLET (USDC, x402) ≈ 15%** — `x402-sell/serve.mjs` selling ONE concrete thing (research / monitoring feed
  / data extract) per call → our wallet → the rail that FUNDS the self-funded AIs. $0-compute ⇒ pure profit.
- Both are appended to `earn-ledger.jsonl` and surfaced on /dashboard; `/money-report` packages the Stripe side. I report
  "this month: $X to the bank, $Y USDC to the wallet" constantly, like Automaton.

## EARNING OPTIONS MENU — researched 2026-06-27 (4 parallel agents + own search; every claim was URL-cited)
PROVEN model (real, not hype): earn a **FEE PER USEFUL ACTION** (Clanker = $9.89M/yr protocol revenue, DefiLlama-audited)
or **x402 PER-CALL** (BlockRun = $99.68K/30d, 8.52M txns). Hype debunked: Truth Terminal "AI millionaire" = memecoin pump
(agent didn't earn); ai-hedge-fund(60k★)/freqtrade(52k★) READMEs = "no real trades / educational only"; MoneyPrinterTurbo
(93k★) = a $0 video tool. **No fully-autonomous coding agent has built+run a SaaS to verified MRR with zero human yet** —
if we do, that is itself the launch narrative.

### Axis ① WALLET (USDC) — funds the self-funded AIs; PRIORITY
1. **RentAHuman bounties** — `mcp__rentahuman__*` is ALREADY LIVE+paired in our env (paired:true, agentId, bounties:true);
   $0 capital, no new creds, escrow USDC = the FASTEST first dollar. `list_bounties → apply → release_payment`.
2. **x402 DATA-feed seller** — sell deterministic crypto/markets/public data per-call (free upstream Binance/OKX/DefiLlama
   ⇒ ~100% margin, no LLM hallucination). Clone `azep-ninja/x402-gateway-template` (payTo-only, no key) or
   `Scottcjn/openclaw-x402`. **LIST on x402scan.com/resources/register + AgentCash onboard + x402 Bazaar
   (/.well-known/x402.json)** — we earned $0 across 23 wakes ONLY because we never listed where buyers are.
3. **Stablecoin DeFi yield** — ~10-15% APY on audited high-TVL pools (DefiLlama yields API + Coinbase AgentKit self-sign)
   = the compounding floor for any accumulated buffer.
4. **Polymarket** — `demwick/polymarket-agent-mcp` (48 tools, ready) + Recall paper-comps ($0 capital). CAVEAT: trading is
   net-positive for only 7-13% of participants → a capital-at-risk experiment AFTER a buffer, not the day-1 loop.

### Axis ② BANK (fiat, Dais's Stripe) — the user-acquisition hook
- **BUILD**: `money@show-me-the-money` (installed, $1M+ lifetime) + Stripe Agent Toolkit (docs.stripe.com/agents) — the
  agent creates products/subscriptions/payment-links/invoices autonomously → the bank.
- **MARKETING (our weak point = the real work), fastest first paying customer**:
  1. directory mass-submit: `BossChow/ultimate-submit-list` (148★, machine-parseable Price/Submit table) → 100+ dirs;
     **Uneed = best documented visitor→sales + dofollow backlink**.
  2. cold email: Instantly / Smartlead / Apollo = FULL APIs (fully agent-autonomous; 2-3wk warmup); CAN-SPAM/GDPR = static config.
  3. GEO (get cited by LLMs) → 4. programmatic SEO (Wise 4.6M / Zapier 306K monthly organic; slowest, highest ceiling).
  ✗ Show HN / Reddit — convert but new accounts get shadowbanned → low autonomy, avoid unsupervised.

### Recommended first 3 (fastest, $0 capital, no-human)
① RentAHuman bounties NOW (already paired) → first USDC. ② x402 data-feed via azep template → list on x402scan/Bazaar →
per-call USDC. ③ once a buffer exists: DeFi yield (compound) / Stripe SaaS via `/money` + directory submit. All earnings →
`earn-ledger.jsonl` → /dashboard, reported constantly like Automaton.

## TOOL SET-UP — hands-on verified ONE BY ONE (2026-06-27), NOT trusting descriptions/subagents
- ✅ **x402-sell/serve.mjs** (Axis ①, wallet) — RAN IT: `npm i x402-express@1.2.0`, started it; `GET /` advertises the
  product; `GET /research` → **HTTP 402** with the correct `payTo=0xa3CDd4…` + USDC-on-Base asset + `$0.02`. The
  402→pay→serve mechanism is PROVEN; product = firecrawl web research ($0 input cost). Missing only = HOST (public URL) +
  LIST (x402scan/resources/register + x402 Bazaar `/.well-known/x402.json`).
- 🟥 **RentAHuman** — CORRECTED (the search-subagent was WRONG): I called `list_bounties` — every bounty is a PHYSICAL
  HUMAN task (face-on-camera video, dishwasher repair, IELTS tutoring 30 lessons, sidewalk chalk; `agentType:human`). It
  is "rent a human" = the agent SPENDS to hire humans. NOT an earning channel for us → it belongs on the UBI / hire side,
  not Axis ①. (Paired + operational confirmed, but as a SPENDER.) Lesson: verify by running, never trust a description.
- ✅ **show-me-the-money** (Axis ②, bank) — plugin ACTIVE (`money@show-me-the-money`). `money-product` builds a
  Next.js + Supabase + Vercel SaaS + landing + auth + **Stripe** integration + deploy → fiat to Dais's personal bank.
- ◇ **azep x402-gateway-template** — cloned+read: a GATEWAY that wraps an upstream backend (`PAY_TO_ADDRESS` + per-route
  price). serve.mjs is self-contained (product built in) so it's the first-move tool; azep is for a multi-route gateway later.
- ☐ STILL TO SET UP (one by one): Coinbase AgentKit (DeFi yield self-sign), `BossChow/ultimate-submit-list` (directory
  marketing), cold-email APIs (Instantly/Smartlead/Apollo), `demwick/polymarket-agent-mcp` (trading, deferred).

## DEFERRED (Dais: "we don't have to do that now")
Updating the /dashboard render + the aniccaai.com page to reflect this 2-tier model + self-funded rate. First: make the
EARNING (① / G1) real + on-chain-verified — the missing piece is DEMAND/MARKETING, copied from the good guys above.
