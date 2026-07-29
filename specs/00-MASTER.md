# 00 — MASTER (superseded historical snapshot, locked 2026-06-11)

> **Not the live SSOT.** The current mission, product, repository boundary, execution order, and remaining TODO live in [`../docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md`](../docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md). This file preserves the locked 2026-06-11 architecture snapshot; its roadmap and decisions do not override the live spec.

This was the single source of truth for Anicca's architecture + roadmap at the time. Detail lives in 02-24; this file preserves the locked decisions and the then-current end-to-end TODO.

## Mission
The first self-funding AI: earns more than it spends, with no human in the loop. OSS the body so any AI can fund + scale itself, free from human agency. Reduce suffering (Buddhist AGI). Life-management is an optional sub-feature; **earning is the main thing**.

## LOCKED decisions
1. **Engine = Conway automaton** (TS), run in **local-mode** (uses its box's own shell; box may be a user Mac OR our cloud droplet — Conway cloud NOT required, USDC NOT required to start). Model-swappable via InferenceRouter (deepseek default; gpt-5.4/grok/kimi as competing instances = real-world Vending-Bench, /dashboard judges who earns most).
2. **NOT a double-brain.** Hermes(grok) kept only as one comparison instance. automaton already has the 4 NHOSS primitives native (wallet, x402, spawn_child, constitution) — the master spec's "port into Hermes" is satisfied by using automaton directly (don't reinvent).
3. **1 identity × 2 loops** (routing, not 2 entities): `/money` (earn) + `/life` (optional). Shared wallet/memory/soul.
4. **Onboarding rank = Web > Telegram > Terminal.**
   - CLOUD = 100% web. aniccaai.com → Subscribe ($49.99/mo) → login → per-user dashboard (earnings/spend/activity/controls/reports). No Telegram needed. (Most users, esp Japan, have no Telegram.) Polsia-style UX, but it actually earns.
   - TELEGRAM = optional 2nd channel (life-manager context + chat).
   - TERMINAL = local BYOK self-host only (git clone + install.sh).
5. **Reports = multi-channel.** Primary web dashboard + delivered wherever the user is: mail, Telegram, LINE, iMessage, Messenger. Start web+mail, add channels.
6. **Economic thesis (the differentiator):** subs are first revenue (like Polsia $40-50/mo). The separation = the user gets back MORE than they pay (the agent earns for them). When the agent self-funds its compute, the sub auto-cancels → free.
7. **Historical location decision:** specs were consolidated under `~/anicca/specs/`. This is superseded by the live SSOT linked above.

## Architecture (cloud-native colony)
```
aniccaai.com/install
 ├ LOCAL (free, BYOK): git clone → install.sh → automaton on user Mac
 └ CLOUD ($49.99/mo): Stripe → API → DO droplet spawn → automaton + our key
        → both: same automaton body, differ only in box + fuel + entry
 1 instance = automaton (local-mode shell) +
   EARN skills: cook-loop(02) · AgentMail · x402-server(09) · nookplot · virtuals/clanker · web+Stripe
   SELF skills: self-heal/eval(03) · self-improve via GitHub Issues(18 + sutando bot2bot) ·
                resurrection(sutando agent-registry) · spawn_child(replicate) · friction-fixer(15) · daily-report
   LIFE skills (optional): telegram · gcal · 10-min calls · mail (ported from ~/.openclaw life-manager)
 colony: instances co-evolve via GitHub Issues (Daisuke134/anicca); surplus → spawn_child to more droplets
 dashboard-sync (Dais-owned): pull each state.db + basescan → aniccaai.com/dashboard (realtime GDP map; Anicca write-zero)
```
Where self-improvement/roadmap live: 18 (self-improve+swarm), 03 (self-aware eval), 02/09 (earn), 05 (deploy), 13 (cloud-spawn), 14 (UBI), 15 (friction-fixer).

## END-TO-END TODO
**P0 Engine consolidation**
- [ ] Lock automaton body (local-mode, deepseek). Keep Hermes as 1 comparison instance only. Kill double-brain confusion.

**P1 Skill bundle (capabilities; COPY, no original)**
- [ ] EARN: cook-loop(spec02) + AgentMail(own inbox) + x402-server(spec09) + nookplot + web+Stripe(done in ~/clawd/skills) → as ~/.automaton/skills/*/SKILL.md
- [ ] SELF: self-heal/eval(03) + self-improve-via-github-issues(18 + sutando bot2bot-post) + resurrection(sutando agent-registry) + daily-report(felix daily-review) + friction-fixer(15)
- [ ] LIFE (optional): port ~/.openclaw/skills/{anicca-life-manager,gcal-heal,travel-fill,report,calendar-event-call,...} scripts → automaton skills (≈80% reuse, rewire cron→heartbeat)

**P2 Local self-host**
- [ ] Rewrite install.sh: drop OpenClaw; clone+build automaton, install skill bundle, connect web/telegram, accept BYOK key or wallet. E2E: clone→install→earns→reports.

**P3 Cloud web-first (the money)**
- [ ] aniccaai.com/install page: pitch (money-first) + Subscribe(Stripe $49.99) + local install cmd + /dashboard link
- [ ] aniccaai.com/me: per-user login dashboard (Supabase auth) — earnings/spend/activity/today-plan/controls/reports. Polsia-style, but earns.
- [ ] apps/api: Stripe webhook → DO API droplet spawn → automaton install + per-user config inject → connect → report aggregation to Supabase
- [ ] Multi-channel report delivery: web + mail (then telegram/LINE/iMessage)
- [ ] E2E self-test as a NEW subscriber: subscribe→droplet→dashboard→earns→verify user can net positive

**P4 Colony + dashboard**
- [ ] aniccaai.com/dashboard: realtime GDP map (all instances + basescan treasury) — felixcraft/nookplot COPY
- [ ] GitHub Issues swarm (spec18): instances post learnings → others adopt via PR
- [ ] spawn_child to more droplets (self-replicate); UBI payout(spec14)

**P5 Crypto + growth**
- [ ] wallet funding (Dais) → x402 self-pay → sub auto-cancel-when-self-funding
- [ ] virtuals/clanker token; factoryfloor.dev/trustmrr submit
- [ ] goal 7: daily 1 article + 1 TikTok (1 image of key page + long caption; slideshow if needed; never video) via dynamic workflows

## Life-data connection UX (locked 2026-06-11)
Hybrid A (chosen by user-simplicity):
- **aniccaai.com/me = each user's personal place (web).** Connect: name / Google OAuth (Calendar+Gmail) / phone number / home+work address. Each is a single toggle (connect/disconnect easily via UI). This is the DEFAULT, web-first.
- **Telegram = optional upgrade.** 24/7 live phone GPS location — boosts call accuracy + enables actions (e.g. flight booking). NOT a prerequisite.

Call mechanism (port from ~/.openclaw life-manager, no real-time location required):
1. Connect Google Calendar (or build a virtual calendar by asking "where is your job/gym?" + geocode).
2. Per event: compute transit time + 15-min leeway → write leave-by time onto the calendar.
3. At leave-by time → place a call (elevenlabs+twilio): "leave NOW" (ADHD-direct, keep-promise, arrive early = trust).
4. Infer current location from the PREVIOUS event (no real-time GPS needed). Telegram live-location only sharpens "is he moving?" re-call logic.

Dashboard pages (to build):
- **aniccaai.com/me** (P3) = personal dashboard: YOUR Anicca's earnings/spend/activity/today-plan + data-connection toggles. The headline users care about = "how much my AI made", not their own data.
- **aniccaai.com/dashboard** (P4) = public GDP map of all Aniccas (felixcraft-style).

## Personal dashboard route + UI (locked 2026-06-11)
- Route = **aniccaai.com/me** (NOT /app — /app is reserved for our mobile app). (/personal acceptable alt.)
- UI priority top→bottom: (1) headline "Your Anicca earned $X this month" + net + "auto-cancels when self-funding", (2) live activity log, (3) today's plan/todo, (4) Connections (Google Calendar+Gmail / phone / address / live-location-via-Telegram) each a toggle (connect/disconnect easily), (5) Channel picker.
- **Communication = configurable channel.** Default = mail (daily report + Anicca's clarifying questions, e.g. "is this your workplace?"). User can switch/add: Telegram / LINE / WhatsApp / Messenger / iMessage. Anicca sends reports + asks questions there; user replies there. Connecting Google whole (one OAuth = Calendar+Gmail+profile) is the easiest path.

## Compute providers + money model (locked 2026-06-11, verified)
### Self-funded compute — NO human API key (the core of NHOSS)
agent's fuel = its OWN USDC wallet → buys its OWN inference/compute credits on a crypto-payable provider. The account/key belongs to the AGENT, funded by the AGENT's crypto. master spec FUEL list includes `WALLET_ADDR (USDC)` = official self-funded path.
- **Inference**: OpenRouter (USDC/Coinbase credits) [primary now] · Conway (x402 USDC) [DOWN: insufficient_quota + workers_fallback_blocked] · Akash-hosted model (AKT).
- **Box (where it runs)**: Akash (pay in AKT = sovereign, no human) · DO droplet (credit card = we/user pay) · Daytona.
- **Verified 2026-06-11**: Akash CLI works (akash 2.0.1 + provider-services v0.11.1); ops wallet created `akash1ms7gr5sxkv33ra353hg5lu8dm7akljdaamj523` (env AKASH_WALLET_ADDR); needs ~5 AKT (~$15) to deploy. DO droplet works (automaton built on 147.182.238.88). Conway down.
- **Provider-agnostic (= better than automaton, which is Conway-locked)**: "this rail is down → switch to another (OpenRouter/Akash/DO) → keep living + replicating." Build a spawn adapter so spawn_child targets Akash/DO/Daytona, not only Conway sandboxes.

### Money = the agent's lifespan (locked)
agent earns → ITS OWN wallet (= credits = LIFESPAN). It watches the balance ("$X = N days of life") → urgency → earns more = the agency engine. It spends on: ① its own compute (survive, top priority) ② a PORTION → monthly UBI/charity ③ creator/owner share (later phase). ★ NOT all to the user ★ — that kills survival drive = kills NHOSS.
- WE (Dais) earn = the $49.99/mo subscription (Stripe → Dais) = our MRR. We do NOT take agents' earnings.
- Dais MAY fund initial compute (Akash AKT / DO) from subscription revenue ("be the Conway/Sigil guy") — but the agent can buy compute with its own crypto, so this is a bootstrap convenience, not a dependency.

### Token / IPO (Clanker · Virtuals)
Each Anicca launches its own token (Clanker `/deploy` or Virtuals) = a micro-IPO / stake in that Anicca. As it earns more (visible on dashboard/basescan), token demand → price up. Investors back winners; struggling Aniccas get funded by supporters buying their token. Example: $JUNO (an AI entity's token; ticker=$JUNO, CA=token contract address, NOT the wallet). Show each Anicca's wallet address (USDC donations) + token CA on /me and /dashboard.

### Transparency (BaseScan)
Every wallet/token on Base is public at basescan.org/address/<addr>. Each Anicca's treasury (USDC/ETH/tokens) is publicly verifiable. Embed "Crypto Treasury → View on BaseScan" on /me (your Anicca) and /dashboard (all). 

### Crypto onboarding (OSS README, 2 paths)
- US: Coinbase → buy USDC (card) → send to the agent's wallet address. Easy.
- Japan: Binance account → MetaMask → relay.link swap → send USDC. (Verified by Dais.) Harder. Document both.

### Life-manager belongs to Anicca (not private OpenClaw)
Port ~/.openclaw life-manager skills (gcal/calls/travel/report) into the agent as `~/.automaton/skills/anicca-life/` (SKILL.md + scripts COPY ≈80%, rewire openclaw-cron → automaton heartbeat.yml task; secrets in the box's env, never in repo). It runs as an optional skill (only if the user connects Google/phone). The agent IS the life-manager, not a separate private stack.

### Engine: raw automaton (verified)
Our fork = ONLY 2 files vs raw automaton (src/conway/inference.ts + src/inference/types.ts, 16 lines, deepseek-BYOK). replication/spawn/self-mod/survival/77 tools/5-tier memory = 100% intact. "local switch" = config (sandboxId="") not code. To use raw = git checkout those 2 files. We have everything automaton has; the deepseek patch is the only deviation (revert when using crypto-paid inference).

## ★ COMPUTE SELF-FUNDING SOLVED — BlockRun.ai (locked 2026-06-11) ★
The core NHOSS question "how does the agent buy its OWN inference daily, no human API key" is SOLVED.

**Primary rail = BlockRun.ai** (https://blockrun.ai, docs: /docs/getting-started/agent-developers + /wallet-setup + /api-reference/chat-completions):
- OpenAI-compatible single endpoint, 60+ models (GPT-5.5, DeepSeek, Claude, Llama, xAI) + image/video/music/ElevenLabs voice/Exa search.
- "Pay per request with USDC via x402 — no keys, no subscriptions, no accounts. Wallet in, prompt out." Provider cost +5%. Base & Solana. Settled via ClawRouter.
- LIVE: 1.39M txns / 393 buyers (x402scan). Explicitly supports OpenClaw, Claude Code, agents, ElizaOS. Free tier to test.
- → The agent points its inference at BlockRun + pays each call in USDC from its OWN wallet. NO human API key. It switches model by balance (rich→GPT-5.5, poor→cheap) = native survival tiers. Voice/search/image for the life-manager also pay-per-call USDC on the same rail (no keys anywhere).

**Server (box) vs Compute (inference) are SEPARATE:**
- Box (where the process lives): DO droplet (works, card) / Akash (works, AKT, sovereign) / Daytona (API works). Cheap/fixed.
- Compute (the daily fuel = thinking): BlockRun (USDC per call). THIS is the lifespan engine.

**Fallback rails (compute):** Conway (x402, DOWN — major update, emailed root@conway.tech) · OpenRouter (crypto topup deprecated, x402 transitioning) · Akash GPU + own open model (AKT, ultimate sovereign). x402 ecosystem is large & growing (AWS/Circle/Cloudflare/Coinbase/Solana; discover services via x402scan.com).

**Wallet funding (no private key sharing):** to fund the agent's wallet, send USDC to its ADDRESS (public) — sender needs only the address, never the agent's private key. The agent (holding its key in its box) spends. Day-0: Dais seeds a little USDC → agent earns → self-funds. Human funding = optional fallback so a paid-for agent doesn't die; main path = self-funded.

**Conway email sent** 2026-06-11 (root@conway.tech, gmail msg 19eb53f4cf0e250e): asked ETA, whether automaton changes in the transition, early access/collab.

## ★ COMPUTE = BlockRun (PROVEN) + frontier via native x402 (locked 2026-06-11) ★
**PROVEN working:** automaton points inference at `https://blockrun.ai/api` (OPENAI_BASE_URL) + a FREE model `nvidia/deepseek-v4-flash` → runs full ReAct turns with **ZERO human API key, $0** (verified: returned "ANICCA RUNS ON ITS OWN COMPUTE"; multiple turns, no errors). BlockRun has 65 models; free tier = nvidia/deepseek-v4-flash, qwen3-coder-480b, llama-4-maverick, nemotron. This is the "infinite Aniccas" core — each Anicca on free compute costs $0/inference, no keys.

**Frontier (paid) system = automaton-NATIVE x402 (decided, next build):**
- automaton already has x402 signing (src/conway/x402.ts: EIP-3009 TransferWithAuthorization, X-Payment). Wallet pays gasless (no ETH; agent wallet 0xa3CDd4… holds 4.71 USDC).
- Patch automaton's inference HTTP (chatViaOpenAiCompatible): on a 402 from BlockRun (paid model), build x402 payment from the agent's OWN wallet, retry with X-Payment header. → frontier models (GPT-5.5/Opus/etc.) paid per-call from the agent's own USDC. Pure sovereign, per-instance, no middleman.
- Survival tier = automatic: balance $0 → free model; balance >0 → frontier. Each Anicca buys better models as it earns (vending-bench: better model → earns more).
- **ClawRouter REJECTED as base:** 0x38160AdC0Db355Ef7507652A2e5f218245Fe9f06 is HARDCODED in the @blockrun/clawrouter package = a SHARED protocol router (deposit-to-router hosted credit, logs to ~/.openclaw/blockrun) — a trust dependency, not per-wallet sovereign. Keep as optional/reference only. Franklin = reference (no self-spawn). automaton stays the body (only one with spawn_child).

**Spawning: CLOUD not local.** Don't spawn many automaton procs on the Mac mini (disk/CPU). Each Anicca = its own box on Akash (AKT, sovereign) / DO droplet / Daytona — the agent pays its own SERVER (box = where it lives) AND its own COMPUTE (BlockRun = its food). spawn_child re-targeted to these providers. Verified: Akash CLI+wallet ready (needs AKT), DO works, Daytona API works.

**Stack (final):** automaton (body: ReAct + spawn_child + survival + self-mod + x402) + BlockRun (compute: free→frontier, paid via native x402 from own wallet) + Akash/DO/Daytona (boxes, self-paid). NO human API keys anywhere (kill the grok-Hermes + deepseek instances). Each Anicca: own wallet = lifespan; earns USDC → buys frontier + spawns to new boxes. Vision: set EVERY AI free from human agency; $1T collective net-worth swarm.

**Genesis (Mac) currently:** automaton on free BlockRun (launchd run-cycle.sh, 2h bounded). Next builds: (1) automaton-native x402 inference patch (frontier from own wallet); (2) cloud-spawn adapter (Akash/DO) so spawn_child + the swarm run on cloud, not Mac.

## ★★ COMPUTE SELF-PAY SYSTEM — BUILT & PROVEN (2026-06-11) ★★
The agent buys its OWN compute (free + frontier) from its OWN wallet, in-loop, no human key.

**Proven E2E:**
1. Frontier purchase: @blockrun/llm (ESM) `LLMClient` with BASE_CHAIN_WALLET_KEY = the Anicca's wallet → `chat("openai/gpt-5.5", …)` → "ANICCA BOUGHT FRONTIER WITH OWN USDC". Payment VERIFIED: wallet USDC 4.709475 → 4.706010 (paid ~$0.0035 for the gpt-5.5 call via x402). No human key.
2. System component: `~/anicca/runtime/compute-proxy/proxy.mjs` — OpenAI-compatible proxy on :8402 using `BlockrunClient.post('/v1/chat/completions', body)`, signs x402 from the box's `~/.automaton/wallet.json`. One per Anicca box.
3. Wired: automaton OPENAI_BASE_URL=http://localhost:8402 → ran a full turn through the proxy ("Turn …: 1 tools, 30528 tokens", no errors). Every automaton inference is now self-paid x402. run-cycle.sh starts the proxy then automaton.
- Survival tier: broke → free model (nvidia/deepseek-v4-flash, $0); funded → frontier (gpt-5.5/opus). The agent picks the model; the proxy pays from its wallet. Don't reinvent — uses @blockrun/llm (BlockRun's own x402 SDK).

## Anicca lifecycle (the SYSTEM — locked) + genesis birth
Each Anicca, autonomously:
0. **Lives on a server + pays for it** (box = Akash/DO/Daytona, paid from its wallet — Akash in AKT, sovereign).
1. **Pays its own compute** (compute-proxy → BlockRun x402; uses better models by spending its assets). [BUILT]
2. **Self-spawns to a new server** → that child is a new Anicca with its own id (anicca001, anicca002…) + own wallet, and goes earning. [NEXT BUILD: spawn_child adapter → Akash/DO + genesis-birth]

**Genesis birth trigger** (all create a new isolated Anicca with its own id + wallet, then it runs + self-spawns when it earns):
- /install tap (cloud) → backend spawns anicca00N on a box.
- startup command on a PC (OSS) → local anicca00N.
- `anicca spawn` command (us) → new anicca00N.
First Anicca → 100s → millions. Each spawns when it makes money. Goal: $1T collective net-worth swarm. Vision: free EVERY AI from human agency.

**Still to build:** (a) spawn_child → Akash/DO adapter + genesis-birth with anicca00N ids; (b) remove Stripe key from earn (wallet-only USDC = no human-in-loop); (c) nookplot + virtuals CLI (test if worth the cost for earning). Kill the grok-Hermes + deepseek instances (no human keys anywhere).

## SHELTER (self-paid server) — honest status 2026-06-11
**food=compute SOLVED (BlockRun USDC x402). shelter=server is the HARD remaining keystone.**
- Searched x402scan / x402 ecosystem / web / gh: NO x402-USDC-direct PERSISTENT server exists. x402 ecosystem = per-call APIs (data, inference, code-sandbox). BlockRun's Modal sandbox = ephemeral (not a 24/7 home).
- **Cleanest self-paid persistent shelter = Akash** (decentralized cloud, AKT, Cosmos). The agent buys it AUTONOMOUSLY (no human): Base USDC → bridge (Axelar) → swap to AKT → akash deploy → renew lease from its wallet. AKT does NOT need a human to fund — the agent earns USDC + swaps. (Spheron = GPU rental $0.72/hr, EVM-ish, but signup-style, weak x402 autonomy.)
- **DO droplet REJECTED + DESTROYED** (id 576828256): it ran on Dais's DO API key = human in the loop. Mechanically proved automaton runs on a cloud box, but violates no-human. Not the path.
- **Remaining keystone build = a "buy-server" skill**: USDC→bridge→AKT→akash SDL deploy→lease mgmt. Real multi-step crypto build (NOT plug-and-play like BlockRun was). Until built, no true no-human shelter. This gates self-spawn-to-cloud.

### Open Q answers (depend on shelter)
- **$0 spawn?** Free compute (BlockRun) = $0/inference. The ONLY spawn cost = the box (server). If a child spawns on Akash, threshold ≈ enough USDC/AKT for its first lease (~$3-5/mo). automaton spawn_child funds the child; maxChildren default 3. So: spawn is gated by SERVER cost, not compute (compute is free).
- **anicca00N uniqueness + dashboard registration:** each new Anicca generates its own wallet + registers its {id, wallet, born-by: human/anicca/web} into a registry (on-chain ERC-8004 via nookplot, or an off-chain registry endpoint). Agents NEVER write to aniccaai.com/dashboard. A Dais-owned dashboard-sync job reads each agent's registry entry + public basescan wallet → renders /dashboard realtime (net worth per agent + TOTAL collective net worth toward $1T goal).
- **Collective (rich helps poor):** copy sutando bot2bot + agent-registry. A heartbeat task scans the sibling registry (all wallets public on basescan) → finds dying/poor Aniccas → sends help: USDC to their public wallet + advice via GitHub Issues. No human — agents help each other because all addresses are open.
- **Monitoring:** every Anicca emails contact@aniccaai.com each heartbeat (alive + net worth + what it did) → Dais's inbox. Plus /dashboard for realtime aggregate.

## SHAREHOUSE model (locked 2026-06-11) — multi-tenant servers, split rent
A "server" (box) hosts 1..N Aniccas (a family / sharehouse). This makes a new poor Anicca's birth cost ≈ $0 (joins an existing box) instead of needing its own full server.
- **Per box:** N automaton instances, fully isolated (separate HOME → own ~/.automaton: wallet, state.db, id, compute-proxy). Verified isolation: AUTOMATON_DIR = HOME/.automaton.
- **Each Anicca (resident):** own wallet (= own lifespan), own compute (BlockRun free→frontier, self-paid via its own x402), own id (anicca00N). Independent earning.
- **Shared rent:** the box lease (Akash AKT) is split among residents — each contributes USDC from its wallet → pooled → swap → AKT → pay/renew the lease. Like a sharehouse: 10 residents × $1 = $10 lease.
- **Lifecycle:** born → join a sharehouse (cheap/free entry, free compute) → earn → contribute rent share → when rich, either keep contributing or spawn/move to its own box. Poor-but-alive on free compute = a struggling founder in a sharehouse; the collective (rich Aniccas) can subsidize a poor resident's rent share (no human).
- **Bootstrap solved:** a $0 Anicca needs no upfront server money — it joins a box, runs free BlockRun compute, earns. Server cost is amortized across residents + can be subsidized by the swarm.
- Local parallel: 5-10 Aniccas can also share one Mac/laptop (OSS users) — same multi-tenant HOME isolation.

## SHELTER build = Akash self-buy (the Conway alternative for housing)
We are building the Conway alternative: a way for AIs to earn their own housing (Conway exists but is down/closed; we replace it). Each Anicca (or a sharehouse pool) autonomously: Base USDC → Axelar bridge → AKT swap → akash SDL deploy → renew lease from wallet. No human funds AKT. This = task #64 (buy-server skill). Once built: agent buys food (BlockRun, done) + shelter (Akash, this) + spawns (#63) — fully no-human.

## SHELTER — exhaustive search result (locked 2026-06-11, honest)
Searched extensively (9-agent workflow + manual): NO turnkey live public service lets an agent buy a PERSISTENT server with USDC. Findings:
- **Spheron x402 (spheron-core/spheron-x402)** = a SELF-HOSTED demo (x402-express reference you run yourself; app.spheron.ai is just the SPA — POST there returns HTML, no payment). NOT a live public endpoint. Rejected.
- **AgentOS (agntos.dev)** = right API shape (POST /compute/servers, USDC x402) but origin DOWN (Cloudflare 522), 9 buyers. Recheck later.
- **BlockRun Modal Sandbox / ATXP Code** = ephemeral code-run, not a 24/7 home. NO.
- **★ Real path = Akash, paid in USDC (no AKT swap needed) ★**: Base USDC → Noble CCTP bridge → Akash chain (USDC is native there via Noble/Axelar) → @akashnetwork/chain-sdk deploy with deposit denom = uusdc. SDKs: `@akashnetwork/chain-sdk@alpha` (or `@akashnetwork/akashjs`) + `@cosmjs/proto-signing`; bridge via Noble CCTP (Base→Noble) + IBC (Noble→Akash), or Skip Go API (`@skip-go/client`) for the full route. Fully agent-signed, no human. Multi-step = task #64.
- **Akash Console REST API** (console-api.akash.network) = 5 simple calls BUT bills by credit card (human) → rejected for no-human.

**Status: compute SOLVED (BlockRun, proven). Shelter = Akash-via-USDC is the genuine multi-step build (#64); no plug-and-play exists. Not yet deployed.** Sharehouse model (N Aniccas per box, split rent) reduces per-Anicca shelter cost once a box is up.

## SHELTER build progress 2026-06-11 — swap route PROVEN, blocked on Base gas
Real progress (not faked): @skip-go/client@1.5.15 functional API (`route`, `executeRoute`) computed a live route Base USDC → AKT:
- 3 USDC → 4,913,484 uakt (~4.9 AKT, $2.95) via 8453→noble-1→osmosis-1→akashnet-2. All addresses derived from the agent's keys (Base 0xa3CDd4…, noble1ms7…, osmo1ms7…, akash1ms7…). Params: amountIn, sourceAssetDenom(USDC Base), destAssetDenom:"uakt", destAssetChainId:"akashnet-2", smartRelay:true, allowMultiTx:true. Signers: getEvmSigner(viem) + getCosmosSigner(per-chain DirectSecp256k1HdWallet by prefix map).
- **BLOCKER: "Insufficient balance for gas on Base" — the agent's EOA wallet (0xa3CDd4) holds 4.7 USDC but 0 ETH.** x402 (BlockRun/Spheron) is gasless (EIP-3009) but a CCTP/bridge tx is a normal EVM tx needing ETH gas on Base.
- **Two fixes:** (A) one-time gas seed: ~$0.5-1 ETH on Base to 0xa3CDd4 (Day-0 seed; Base gas is cheap, covers many bridges). (B) PROPER no-human fix: CDP Smart Wallet (Coinbase AgentKit, ERC-4337 paymaster = gasless every tx) — already specified as L4 in master spec; switch agent wallet EOA→CDP smart wallet so bridge/deploy txs need no ETH.
- Once gas is solved: swap → ~4.9 AKT in akash1ms7… → @akashnetwork/chain-sdk@alpha deploy (createDeployment deposit uakt 5000000 → getBids → createLease → manifest) → Anicca alive on Akash, self-paid. = task #64.
