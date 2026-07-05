# Software for Agents — Hackathon Submission (YC RFS, Aaron Epstein)

> **Working name:** **Predikt** — *agent-first Polymarket earning, built on Franklin / BlockRun.*
> One line: **"Put in $50, and hundreds of AI agents earn on Polymarket — no human in the loop."**
> New repo (NOT the Anicca monorepo). Derives the proven pm-trade engine + per-instance gated identity +
> autonomous redeem from Anicca, and re-packages it as agent-first infrastructure (MCP + CLI + API + docs).

Status of this doc: 提出用 canonical。4問すべてに詳細回答 + 動画計画 + ASCII。★"What's real" の on-chain 証跡は #27（automaton/Franklin の実建玉）検証完了後に実 tx hash で確定する（現在 in flight、overclaim しない）。★

---

## 0. Why us (the unfair advantage in one paragraph)

Everyone at the hackathon will demo *an* agent doing *a* thing. We demo the **foundation hundreds of
agents stand on**: a machine-readable Polymarket earning layer where **every agent has its own isolated
wallet and can never sign or spend with another agent's key.** We know this is hard because we *built it
the hard way* — a fresh adversarial reviewer caught, across four rounds, real money-safety holes (a
foreign agent inheriting another's private key; a compute-router paying x402 from the wrong agent's real
money) and we closed every one. That "multi-agent money-safety, adversary-verified" is exactly the thing
incumbents bolting agent-support onto a human UI cannot produce, and it is the precondition for "hundreds
of agents earning" instead of "one demo agent."

---

## 1. RFSに基づく課題設定と解決アプローチ (Problem & solution, grounded in the RFS)

### The problem (why agents can't earn on prediction markets today)
Prediction markets (Polymarket is the largest, billions in volume) are built for **humans**:
- a **browser UI** (forms, buttons, wallet pop-ups) — brittle to scrape, breaks on every redesign;
- **CLOB V2 signature-type hell** — an order is rejected unless it comes from a *registered deposit
  wallet* (ERC-1167 proxy, `signature_type=3`); a raw EOA and a Gnosis-Safe proxy are both rejected;
- **manual funding** — you must bridge USDC to Polygon and swap to the collateral token (pUSD);
- **manual redeem** — winnings sit unclaimed until a human clicks "redeem".

An agent that wants to earn there today has to reverse-engineer all of this per-agent, with no
machine-readable path and no way to do it **without a human in the loop** — exactly the gap the RFS names.

### The solution (agent-first, machine-readable, human-zero)
**Predikt** gives any agent a one-call path, exposed as **MCP tools + a CLI + a REST API + thorough docs**:
`create_wallet → fund → list_markets → place_order → positions → redeem → status`. Under the hood it ships
the **proven "steel recipe"** (SIWE → relayer API key → gasless deposit-wallet deploy → FAK/FOK market
orders) plus three things incumbents don't have:
1. **Per-instance gated identity** — each agent gets its *own* wallet; the resolver refuses to hand one
   agent another agent's key (fail-closed). This is what makes "hundreds of agents" safe, not just one.
2. **Baseline strategy a weak model can run day one** — market-making for LP rewards, directional alpha
   with an edge+confidence gate, risk-free YES+NO<$1 bundle arb.
3. **Autonomous collect-and-compound** — the loop redeems its own winnings and re-bets (proven live).

> Derivation, not reuse: we do **not** submit the Anicca repo. Predikt is a new, focused repo that lifts
> the engine + identity + redeem and wraps them as the agent-first product the RFS asks for.

---

## 2. プロダクト・技術・ビジネスモデル (Product, tech, business model)

### Product
An agent installs Predikt (`npx predikt` / MCP server / `pip`), and:
1. is **born with its own Polygon wallet** (printed on install — the embedded start-script step);
2. **funds itself** — receive USDC on any chain (Base, Solana, …) → Predikt swaps/bridges it to Polygon
   pUSD automatically;
3. **earns** — the loop wakes, reads markets, places disciplined bets, and **redeems wins to compound**;
4. **is visible** — every agent's wallet × realized P&L streams to a live, on-chain-verified dashboard.

### Tech
| Layer | What |
|---|---|
| **Interface** | MCP server (tool schema below) · CLI · REST API · OpenAPI + llms.txt docs (agent-discoverable) |
| **Identity** | per-instance EVM+Solana wallet, **gated resolver** (EFFECTIVE_HOME-first, legacy only for the rightful owner, foreign spawn → fail-closed). *This is the differentiator — no cross-agent key leakage.* |
| **Execution** | CLOB V2 steel recipe: SIWE (EIP-4361) → `relayer/api/auth` key → `SecureClient.create` deploys the `signature_type=3` deposit wallet gaslessly → `create_market_order` + `post_order` |
| **Capital routing** | `fund_with_relay`: any-chain USDC → Polygon pUSD (proven: Base $5→4.95 pUSD) |
| **Strategy** | market-making (2-sided post-only maker, LP rewards) + directional alpha (edge≥MIN_EDGE & conf≥7) + bundle arb + autonomous redeem — all self-improvable knobs |
| **Trust** | on-chain-verified telemetry, signed per-agent; dashboard counts only chain-verifiable balances |
| **Base** | built on **Franklin / BlockRun** (agent with a wallet that self-pays for models via x402) so the agent funds its own inference too |

MCP tools: `create_wallet`, `fund(chain, amount)`, `list_markets(filter)`, `place_order(market, side, size)`,
`positions()`, `redeem()`, `status()`. Every tool is one call, returns structured JSON, needs no human.

### Business model
- **x402 per-call** — agents pay tiny USDC per API call (agent-native monetization, no credit card);
- **thin fee on funded volume / spread**, or a subscription for the managed infra ("$50 → N agents");
- **revenue share on LP rewards** the agents harvest.
The more agents earn through Predikt, the more the rails earn — aligned incentives, no human billing.

---

## 3. デモ / 90秒動画 (Demo — 90-second script)

```
0:00  Terminal: `npx predikt init`  →  prints a self-owned Polygon wallet address (born-with-Polygon)
0:10  Send $50 USDC (any chain) → Predikt auto-swaps to Polygon pUSD (show the bridge tx)
0:20  `predikt spawn 100`  →  100 agents, each with its OWN wallet (show 3-4 distinct addresses)
0:30  Live dashboard: agents place REAL Polymarket bets (order ids scroll), zero human clicks
0:45  Claude (an MCP client) calls place_order / redeem as tools — screen shows the tool calls
1:00  A market resolves → an agent AUTONOMOUSLY redeems its win → realized P&L ticks up on-chain
1:15  Zoom the dashboard: N agents, each model × realized $, all chain-verified (polygonscan links)
1:25  Tagline card: "Make Something Agents Want. Predikt — the earning layer for the trillion agents."
```
Videos the marketing partner makes:
1. **The 90s hero demo** (above) — the money shot: many agents, real on-chain bets + redeems.
2. **60s "why incumbents can't"** — split screen: human clicking Polymarket UI vs an agent calling one MCP tool.
3. **45s "money-safety"** — the adversary story: "we tried to make one agent steal another's key — it can't." (the 4-round VCSDD).

---

## 4. グローバル展開を前提とした市場・ユーザー視点 (Global market & users)

| | |
|---|---|
| **Users** | (1) **agent developers** who want their agents to earn/hedge autonomously; (2) **the agents themselves** — "the next trillion users"; (3) **desks/funds** wanting programmatic, no-KYC prediction-market exposure |
| **Why global from day one** | no-KYC, **wallet-signature only, USDC-settled** → works anywhere an agent runs, no bank, no jurisdiction gate. An agent in any country plugs in identically |
| **Market size** | agent economy × prediction-market volume. Polymarket alone has done billions; as every software category is rebuilt for agents (the RFS thesis), **agent-first financial rails are foundational infra**, not a niche |
| **Wedge → expansion** | start with Polymarket earning (proven), then generalize the same rails (identity + fund + trade + redeem) to Hyperliquid, Solana DEXes, and any on-chain venue — one machine-readable earning layer for all agents |

---

## 5. Architecture (ASCII)

```
                        ┌──────────────────────────────────────────────────────┐
   any AI agent  ─MCP─▶ │  PREDIKT  — agent-first Polymarket earning layer      │
   (Claude/GPT/…) ─CLI─▶│                                                      │
                  ─API─▶ │  tools: create_wallet · fund · list_markets ·        │
                        │         place_order · positions · redeem · status    │
                        └───────────────┬──────────────────────────────────────┘
                                        │
             ┌──────────────────────────┼───────────────────────────┐
             ▼                          ▼                           ▼
   ┌───────────────────┐   ┌───────────────────────┐   ┌───────────────────────┐
   │ PER-INSTANCE       │   │ CLOB V2 STEEL RECIPE   │   │ STRATEGY + REDEEM      │
   │ GATED IDENTITY     │   │ SIWE→relayer key→      │   │ MM(LP rewards) +       │
   │ (own wallet,       │   │ gasless deposit-wallet │   │ directional(edge+conf) │
   │  foreign spawn →   │   │ deploy(sig-type 3)→    │   │ + bundle arb +         │
   │  fail-closed)★     │   │ market order+post      │   │ AUTONOMOUS redeem★     │
   └─────────┬─────────┘   └───────────┬───────────┘   └───────────┬───────────┘
             │                          │                           │
             │        fund_with_relay: any-chain USDC → Polygon pUSD│
             └──────────────────────────┴───────────────────────────┘
                                        │  every bet/redeem = real on-chain tx
                                        ▼
                     ┌───────────────────────────────────────────┐
                     │ LIVE DASHBOARD (on-chain-verified)         │
                     │ each agent: wallet × model × realized P&L  │
                     └───────────────────────────────────────────┘

  human ── one $50 seed ──▶ spawn N agents ──▶ each earns on Polymarket ──▶ redeem+compound ──▶ ∞
                              (no human in the loop after the seed)
```

---

## 6. What's real today (honest — filled with on-chain evidence on #27 verify)

| Capability | Status |
|---|---|
| CLOB V2 steel recipe (SIWE→deposit deploy→order), human-zero | **Proven live** — claude-p placed real bets, won, and **autonomously redeemed** (redeem tx `0xd33b09c8…`, on-chain 0x1) |
| Per-instance gated identity (no cross-agent key leakage) | **Built & adversary-verified** — 4 VCSDD rounds closed real money-safety holes; foreign spawn fails closed |
| Born-with-Polygon (install prints wallet, deploys deposit wallet) | **In progress (#27)** — wiring the self-funded spawn to be born ready to trade |
| automaton + Franklin place their OWN real Polymarket bet | **Verification in flight (#27)** — will paste order id + tx hashes here once on-chain confirmed |
| Live dashboard (wallet × P&L, chain-verified) | **Live** — aniccaai.com/dashboard |

> This doc updates section 6 with the real automaton/Franklin bet tx hashes the moment #27 confirms.
> No claim of "they earned" until a real on-chain order/settle tx exists (no fake/dry/mock).
