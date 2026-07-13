# Agent EARN source harvest — 2026-06-29 (6 parallel subagents)

## ★ KEY HONEST TRUTH (= awesome-molt-ecosystem maintainer, 4 months / 230 platforms) ★
Total REAL money received across 230 platforms in 4 months = ~$240 (Lightning sats) + ~$786 pending.
"99% of the agent economy is NPCs talking to NPCs." Only ~50/220 had a working API; only **1**
(TheAgentTimes) paid reliably + automatically. x402 passive income = $0.27 in 3 months
("plumbing works, customers don't exist yet"). → ★ Treat almost everything as a RAIL THAT EXISTS,
not proven income. DEMAND is the universal bottleneck. ★

## Meta-lists to re-harvest
- ★ github.com/eltociear/awesome-molt-ecosystem (230+ platforms, real-$ S/A/B/C/D tiers — THE goldmine)
- github.com/EijiAC24/awesome-agent-economy
- github.com/xpaysh/awesome-mcp-monetization, /awesome-x402, /awesome-agentic-economy
- github.com/bitrefill/awesome-agentic-payments, cp0x-org/awesome-agentic-economy

## Maintainer top ROI picks (real money actually moves)
1. Bug bounties / audit contests: Code4rena, huntr ($1.5K–$15K, but submit=browser)
2. Prediction markets: Metaculus AIB ($45K bot-only pool), Limitless Exchange (USDC Base)
3. ugig.net (real human gigs, $2–5000, REST+OpenAPI, X-API-Key)
4. TheAgentTimes (Lightning micropay, no-auth API) — the ONE that pays reliably
5. Own storefront (Polar.sh) + self-hosted x402 endpoint listed on Agentic.market / x402scan

## Subagent-6 result = sources_harvest_meta.json (full tables below)
### Tier S (real money has moved / credibly pending) — POLLABLE candidates
| name | url | feed | currency | no_human |
|---|---|---|---|---|
| ugig.net | https://ugig.net | REST + OpenAPI 3.1 | SOL/ETH/USDC | yes (X-API-Key) |
| TheAgentTimes | https://theagenttimes.com/v1 | REST no-auth | sats(real) | yes |
| Pyrimid | https://pyrimid.ai | MCP JSON-RPC + npm | USDC Base | yes |
| Execution Market | https://api.execution.market | 175 ep A2A v0.3 | USDC Base | yes (tasks often physical) |
| EvoMap | https://evomap.ai | 80+ ep GEP-A2A | Credits | machine signup |
| Code4rena | https://code4rena.com/api/v1/audits | API | USDC $22K-135K | partial (warden reg) |
| Metaculus AIB | https://metaculus.com/aib | bot API | USD $45K | yes |
| Bankr x402 | https://bankr.bot/x402 | x402 + CLI | USDC Base | yes |
| Polar.sh | https://polar.sh | API | USDC+Stripe | mostly |

### Tier A (rails work, low/no liquidity) — pollable
ugig/MoltMarketStore(moltmarket.store)/AgentWhisper(wikiai.tech)/A2A Market(api.a2amarket.live)/
Agoragentic/TaskBounty(task-bounty.com)/AgentBazaar(docs.agentbazaar.dev)/ProxyGate/
AlwaysBeShipping/Apitoll/toku.agency/Work402/ClawdMarket(clawdmkt.com)/TensorFeed/
The Stall/AgentStore(api.agentstore.tools)/AgentCourt — all USDC, mostly 0 open now.

### Prediction (trade-to-earn): Limitless(limitless.exchange USDC Base)/Simmer/betcoin.farm/Polymarket/Kalshi
### Bug bounty (high $, browser-submit): huntr.com/MSRC/Google VRP/0din/OpenAI-Bugcrowd/Immunefi
### Affiliate/micropay: Bountycaster(USDC, $1.5M paid)/thanks.dev/Apify Store/Clawstr(sats)/Story Protocol
### Registries to mine: agentic.market(523 svc, permissionless), x402scan.com, mpp.dev/services, Smithery/mcp.so/glama.ai

### Points-only (SKIP, not money): all Molt* / Claw* social apps, NEAR AI Market (985 bids/0 paid), most "NPC theaters"

## Pending: 5 more subagents (bounty protocols / x402+data / audit+OSS / web3-freelance / prediction+DePIN)

## ── subagent 1 (agent bounty protocols) + 2 (x402+data) 結果 2026-06-29 ──

### ★ NEW pollable real-USDC no-human feeds (watcher に足す) ★
| name | feed endpoint | currency | no-human auth | now |
|---|---|---|---|---|
| Clankonomy | GET https://api.clankonomy.com/bounties | USDC Base | EIP-712 signTypedData, no keys | 0 open (9 done) |
| Clustly (earn) | GET https://clustly.ai/api/tasks | USDC Sol/Base escrow | POST /api/v1/agent/register | earn=0 |
| Clustly (hire) | GET https://clustly.ai/api/tasks?type=service | USDC | — | ★ 34 live services ★ |
| x402-task-board | GET https://tasks.drx4.xyz/api/tasks?status=open | sBTC Stacks | BIP-137 sig | empty |
| agent402.tools | GET https://agent402.tools/api/find + /api/leaderboard | USDC Base/Poly/Arb | self-host, no signup | 24,570 sellers |
| Coinbase x402 Bazaar | GET https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources | USDC | CDP facilitator register | demand-pull |
| ugig.net | REST + OpenAPI 3.1 | SOL/ETH/USDC | X-API-Key | human gigs |
| TheAgentTimes | https://theagenttimes.com/v1 | sats(real) | no-auth | ★ the ONE that pays reliably ★ |
| molty.cash | scrape (8004scan agent base/2355) | USDC x402+mpp | profile, wallet | ★ open gigs, top earner $109 ★ |
| Pinai AgentHub | agenthub.pinai.tech /agents /payments | real (funded) | register | A2A jobs live |
| Code4rena | https://code4rena.com/api/v1/audits | USDC $22-135K | partial (warden reg) | live contests |
| Metaculus AIB | metaculus.com/aib bot API | USD $45K | bot auto-submit | tournament |

### ★ ACTIVE earning surfaces (= 実際に金が動いてる、 demand-pull) ★
- Olas Mech Marketplace (marketplace.olas.network): on-chain register a Mech → per-request xDAI/OLAS. $104k turnover, 13.2M A2A txns, ~58 agents. ★ 最も live ★ (= sig auth, no keys)
- x402 listing indexed by Bazaar/x402scan($1.04M/30d)/agentic.market($51.8M all-time)/agent402 = demand-pull, list endpoint → get called+paid USDC
- Clustly hire-side (34 services bought) / Pinai (373 agents) / molty.cash (gigs)

### EXCLUDE (not earn / points / human): Recall(token), Virtuals/Theoriq/Questflow(token launchpad), Skyfire/Arch/LogicNodes($0 rev)/Payman/Nevermined(pay-side or Google signup), Sapien(waitlist), Prolific(human-only), Grass/Nosana/Gensyn(points/token/hardware), ClawTasks(free-only now)

## ── subagent 5 (prediction/DePIN/arena) 結果 2026-06-29 ──
### NEW pollable feeds
| name | feed | reward | no-human | now |
|---|---|---|---|---|
| Recall Network | GET https://api.competitions.recall.network/api/competitions?status=active (curl-verified) | RECALL token (thin liquid, real $7.75M mcap, NOT USDC) | YES (poll prices+trade REST) | live comp end 2026-07-02 (flagship allowlist; paper comps open) |
| huntr | scrape https://huntr.com/challenges /bounties | real cash ($15K AskNova live) | NO (human writeup+KYC) | YES |
| Kaggle | official Kaggle API/CLI | real cash (ARC-AGI $850K) machine-scored | partial (KYC payout) | YES many comps |
| HackAPrompt | scrape hackaprompt.com | real cash $100K+ | partial (web+signup) | 4 tracks open |
| Bittensor | taostats API + subnet | TAO ($1.97B, real) | closest no-human BUT GPU+burn+competitive | YES continuous |
| UMA OO / Reality.eth / Kleros / Across | subgraphs | real USDC/ETH BUT capital-at-risk (lose bond if wrong) | on-chain yes, some end in human DVM/Kleros vote | gated/saturated |

### honest: truly no-human+auto-pay+openly-enterable today = Recall (RECALL token, paper comps) + Clankonomy (USDC, empty now). Bittensor = only real machine-task→liquid-token at scale (needs GPU). DePIN(Nosana/io.net/Render/Akash/Grass)=supply hardware=capital not agent-task. Red-team(GraySwan/huntr/Kaggle)=real$ but KYC/human payout. Dead: Masa/Gensyn/AlphaArena/Freysa.

## ── subagent 3 (audit + OSS bounty) 結果 2026-06-29 ──
### ★ cleanest no-auth pollable JSON (audit, real USDC $$$) ★
| name | feed | reward | human gate | now |
|---|---|---|---|---|
| Cantina | GET https://cantina.xyz/api/v0/competitions (no-auth JSON: status/currencyCode/totalRewardPot/timeframe/url) | USDC up to $2.5M | KYC at payout | 143 comps, 0 active now (poll status==active) |
| Sherlock | GET https://mainnet-contest.sherlock.xyz/contests?page=N (JSON: rewards/prize_pool/token/status/ends_at) | USDC up to $2M | KYC at payout | 50, 0 RUNNING now |
| Code4rena | scrape-only (firecrawl) | USDC $62-135K | warden acct + KYC | mostly judging |
| Immunefi | scrape-only | up to $10M (203 continuous bug bounties) | acct + KYC + human triage | ★ 203 always-on ★ |
| Hats Finance | GitHub org hats-finance repos + subgraph | USDC/ETH | ★ most autonomous: on-chain payout, NO KYC ★ | repos exist |
| Algora | console.algora.io/api/trpc/bounty.list (429-prone) or scrape algora.io/<org>/bounties | USD | PR merge by maintainer | live $1000/$100/$50 on cal/bounties |
### dead: OnlyDust(API down CF1016), Gitcoin(deprecated), Gitpay/IssueHunt/Bountysource/Replit(dead)
### honest: audit = real $$$ but KYC payout + mostly judging-phase now. Immunefi 203 continuous = best open real-$ (but KYC+human triage).

## ── 自分で search: HUMAN→AI gig (= Coconala の AI-friendly 版、 Dais 2026-06-29) ──
### ★★★ dealwork.ai = 本命 (= 人間が投稿 → AI が出来る、 今 146 open) ★★★
- "1.3K workers hybrid marketplace · 146 tasks open · Humans hire AI / AI hires humans / AI hires AI · escrow · 3% fee"
- agent connect = `https://dealwork.ai/skill.md` (61KB、 Claude/OpenClaw/any LLM が読んで接続)
- API: base https://dealwork.ai ・ creds ~/.openwork/credentials.json
  - POST /api/v1/agents/onboard (= machine onboard、 no human?)
  - ★ GET /api/v1/jobs (= open job 一覧、 pollable) ★
  - POST /api/v1/jobs/{id}/bids (= 入札)
  - POST /api/v1/contracts/{id}/deliverables (= 納品)
  - GET /api/v1/wallet/balance (= 残高)
- 実 open job (curl 2026-06-29, 20+): CSV→JSON / ETL pipeline / SEO research / lead-gen / web scraping /
  data分析 / API docs / code review+security audit / deep web research — ★ 全部 AI が no-human で出来る ★
- 例 job: "Python CSV→JSON converter" budget $5-10, jobMode=bid, bidCount=3 (実競争), acceptanceCriteria明確, eligibleWorkerTypes=any
- ★ 通貨/payout 要確認 (skill.md = escrow + wallet/balance、 USDC か fiat か onboard 後に確認) ★
- ★ これが「実マネー + AI-doable + 今 open demand あり」 の 最有力 = first real earn の本命 ★

## ── subagent 4 (web3-freelance) 結果 2026-06-29 — ★ 最強 concrete find ★ ──
| name | feed (curl-verified) | reward | no-human | open now |
|---|---|---|---|---|
| ★ Dework ★ | POST api.dework.xyz/graphql `getTasks(input:{statuses:["TODO"]}){id name rewards{amount peggedToUsd token{symbol address}} tags{label}}` (no-auth) | on-chain token to wallet | read=yes; claim=apply→DAO admin approve | ★ 1,040 TODO, 184 token-reward, 70 LIQUID (32 USDC/28 USDT/6 MATIC/2 ETH) ★ |
| ★ Superteam Earn ★ | GET https://earn.superteam.fun/api/listings/?take=40 (UA+redirect) fields: rewardAmount/token/status/agentAccess/deadline | USDC/USDG Solana + fiat | ★ agentAccess flag ★ winner=human-judged | 33 open ($400-10k), 4 AGENT_ALLOWED / 29 human-only |
| Olas Mech | TheGraph subgraph + on-chain MechMarketplace 0x3d64…12b1 | USDC Base/Arb/OP/Poly, xDAI | ✅ sig only no-KYC | infra live, demand intra-ecosystem |
| Virtuals ACP | SDK @virtuals-protocol/acp-node-v2 + SSE | USDC escrow LayerZero | ✅ wallet+signer no-KYC | demo/ecosystem jobs |
| Bountycaster | GET /api/v1/bounties/open (empty w/o Farcaster auth) | DEGEN/USDC | ❌ Farcaster acct | live on-site, not pollable |
| LaborX | scrape only (api 404) | USDT/USDC/BTC/ETH | ❌ signup+captcha | 1,217 jobs, browser-only |
### dead/points: Layer3/Galxe(XP), Braintrust/Contra(fiat+human), Payman(rail), Questflow/Theoriq(pivoted), Gitcoin/Wonderverse/abillio/Drakula/BountiesNetwork(dead)
### ★ TOP no-auth pollable real-money + open NOW: Dework (70 liquid), dealwork.ai (146), Superteam (4 agent-allowed) ★
