# Predikt — Software for Agents (Hackathon Submission)

**YC Request for Startups: "Software for Agents" (Aaron Epstein)**

> **Predikt** — *agent-first Polymarket earning, built on Franklin / BlockRun.*
> **One line:** *"Fund an AI once, and hundreds of AI agents earn on Polymarket — with no human in the loop."*
>
> New, focused repository (not a monorepo). It lifts a proven prediction-market earning engine —
> per-instance self-owned wallets, the CLOB V2 "steel recipe", disciplined strategy, and autonomous
> redeem — and re-packages it as the machine-readable, agent-first product the RFS asks for.

---

## 0. The unfair advantage (in one paragraph)

Everyone at this hackathon will demo *an* agent doing *a* thing. We ship the **foundation hundreds of
agents stand on**: a machine-readable Polymarket earning layer where **every agent has its own isolated
wallet and can never sign or spend with another agent's key.** We built this the hard way — a fresh
adversarial reviewer, over four rounds, caught real money-safety holes (a fresh agent inheriting another
agent's private key; a compute-router paying real money from the wrong agent's wallet) and we closed
every one. "Multi-agent money-safety, adversary-verified" is precisely what an incumbent bolting agent
support onto a human UI cannot produce, and it is the precondition for *hundreds of agents earning*
rather than *one demo agent*.

**Already proven live:** a self-funded agent ("automaton") **placed a real Polymarket bet with its own
money** — human-zero: it bridged $5 of its own USDC from Base to Polygon, deployed its own gasless
deposit wallet, and bought a real position ("France to win the 2026 World Cup", order matched on-chain).
The bet is open (not yet resolved), so no profit is *claimed* — but the full self-fund-and-trade loop ran
with no human touching it.

---

## 1. Problem & Solution (grounded in the RFS)

### The problem — why agents can't earn on prediction markets today
Prediction markets (Polymarket is the largest, with billions in volume) are built for **humans**:

| Human-first wall | What it means for an agent |
|---|---|
| **Browser UI** (forms, buttons, wallet pop-ups) | brittle to scrape; breaks on every redesign; not machine-readable |
| **CLOB V2 signature-type maze** | orders are only accepted from a *registered deposit wallet* (ERC-1167 proxy, signature_type 3). A raw EOA and a Gnosis-Safe proxy are both rejected |
| **Manual funding** | you must bridge USDC to Polygon and swap it to the collateral token (pUSD) |
| **Manual redeem** | winnings sit unclaimed until a human clicks "redeem" |

An agent that wants to earn there must reverse-engineer all of this per agent, with no machine-readable
path and no way to do it **without a human in the loop** — exactly the gap the RFS names.

### The solution — agent-first, machine-readable, human-zero
Predikt gives any agent a one-call path, exposed as a **machine-readable interface (MCP tools + a CLI +
a small API + thorough docs)**:
`create_wallet -> fund -> list_markets -> place_order -> positions -> redeem -> status`.

Under the hood it ships the proven **steel recipe** (SIWE -> relayer API key -> gasless deposit-wallet
deploy -> FAK/FOK market orders) plus three things incumbents don't have:

1. **Per-instance gated identity** — each agent gets its *own* wallet; the resolver structurally refuses
   to hand one agent another agent's key (fail-closed). This is what makes "hundreds of agents" safe.
2. **A baseline strategy a weak model can run on day one** — two-sided market-making for LP rewards,
   directional bets gated on edge + confidence, and risk-free YES+NO<$1 bundle arbitrage.
3. **Autonomous collect-and-compound** — the loop redeems its own winnings and re-bets (proven live).

> We do **not** submit the parent framework. Predikt is a new repo that lifts the engine + identity +
> redeem and wraps them as the agent-first product the RFS asks for.

---

## 2. Product, Technology, Business Model

### Product
An agent installs Predikt (`npx predikt` / MCP server / `pip`), and:
1. is **born with its own Polygon wallet** (printed on install; an embedded start-script step);
2. **funds itself** — receive USDC on any chain (Base, Solana, ...) and Predikt swaps/bridges it to
   Polygon pUSD automatically (via the relay API);
3. **earns** — the loop wakes, reads markets, places disciplined bets, and **redeems wins to compound**;
4. **is visible** — every agent's wallet x realized P&L streams to a live, on-chain-verified dashboard.

### Technology
| Layer | What |
|---|---|
| **Interface** | MCP server (tools below) · CLI · small REST API · OpenAPI + `llms.txt` (agent-discoverable) |
| **Identity (the differentiator)** | per-instance EVM + Solana wallet; a gated resolver (own-home first, legacy only for the rightful owner, a foreign agent falls closed). No cross-agent key leakage |
| **Execution** | CLOB V2 steel recipe: SIWE (EIP-4361) -> relayer auth key -> deploy the signature_type-3 deposit wallet gaslessly -> `create_market_order` + `post_order` |
| **Capital routing** | relay API: any-chain USDC -> Polygon pUSD (proven: Base $5 -> $4.95 pUSD, live) |
| **Strategy** | market-making (LP rewards) + directional (edge & confidence gate) + bundle arb + autonomous redeem — all self-improvable knobs |
| **Trust** | signed, on-chain-verified telemetry; the dashboard counts only chain-verifiable balances |
| **Base** | built on **Franklin / BlockRun** (an agent that pays for its own inference via x402 from its own wallet) |

**MCP tools:** `create_wallet`, `fund(chain, amount)`, `list_markets(filter)`,
`place_order(market, side, size)`, `positions()`, `redeem()`, `status()` — each one call, structured
JSON, no human required.

### Business model
- **x402 per-call** — agents pay a tiny amount of USDC per API call (agent-native; no credit card).
- **A thin fee on funded volume / spread**, or a subscription for the managed infra ("$50 -> N agents").
- **Revenue share on the LP rewards** the agents harvest.

The more agents earn through Predikt, the more the rails earn — aligned incentives, no human billing.

---

## 3. Demo (90-second script)

```
0:00  Terminal: `npx predikt init`   -> prints a self-owned Polygon wallet address (born-with-Polygon)
0:10  Send $50 USDC (any chain)       -> Predikt auto-swaps it to Polygon pUSD (show the bridge tx)
0:20  `predikt spawn 100`             -> 100 agents, each with its OWN wallet (show 3-4 addresses)
0:30  Live dashboard                  -> agents place REAL Polymarket bets (order ids scroll); zero clicks
0:45  Claude (an MCP client) calls place_order / redeem as tools -> the tool calls show on screen
1:00  A market resolves               -> an agent AUTONOMOUSLY redeems its win -> realized P&L ticks up
1:15  Zoom the dashboard              -> N agents, each model x realized $, all polygonscan-verifiable
1:25  Tagline card: "Make Something Agents Want. Predikt — the earning layer for the trillion agents."
```

**Three videos the marketing partner makes:**
1. **The 90-second hero demo** (above) — the money shot: many agents, real on-chain bets and redeems.
2. **60-second "why incumbents can't"** — split screen: a human clicking the Polymarket UI vs. an agent
   calling one MCP tool.
3. **45-second "money-safety"** — the adversary story: "we tried to make one agent steal another's key —
   it structurally can't" (the four-round adversarial review that caught a real fund-movement leak).

---

## 4. Global Market & Users

| | |
|---|---|
| **Users** | (1) **agent developers** who want their agents to earn or hedge autonomously; (2) **the agents themselves** — "the next trillion users"; (3) **desks / funds** wanting programmatic, no-KYC prediction-market exposure |
| **Global from day one** | no-KYC, **wallet-signature only, USDC-settled** — it works anywhere an agent runs, no bank and no jurisdiction gate. An agent in any country plugs in identically |
| **Market size** | the agent economy x prediction-market volume. Polymarket alone has done billions. As every software category is rebuilt for agents (the RFS thesis), **agent-first financial rails are foundational infrastructure**, not a niche |
| **Wedge -> expansion** | start with Polymarket earning (proven), then generalize the same rails (identity + fund + trade + redeem) to Hyperliquid, Solana DEXes, and any on-chain venue — one machine-readable earning layer for all agents |

---

## 5. Architecture

```
                        +------------------------------------------------------+
   any AI agent  -MCP-> |  PREDIKT  - agent-first Polymarket earning layer      |
   (Claude/GPT) -CLI->  |                                                      |
                -API->  |  tools: create_wallet - fund - list_markets -        |
                        |         place_order - positions - redeem - status    |
                        +---------------------+--------------------------------+
                                              |
             +--------------------------------+----------------------------+
             v                                v                            v
   +----------------------+   +------------------------+   +------------------------+
   | PER-INSTANCE          |   | CLOB V2 STEEL RECIPE   |   | STRATEGY + REDEEM      |
   | GATED IDENTITY        |   | SIWE -> relayer key -> |   | market-making (LP) +   |
   | (own wallet; a        |   | gasless deposit-wallet |   | directional (edge+conf)|
   |  foreign agent falls  |   | deploy (sig type 3) -> |   | + bundle arb +         |
   |  closed)              |   | market order + post    |   | AUTONOMOUS redeem      |
   +----------+-----------+   +-----------+------------+   +-----------+------------+
              |                            |                           |
              |     relay API: any-chain USDC -> Polygon pUSD          |
              +----------------------------+---------------------------+
                                           |  every bet / redeem = a real on-chain tx
                                           v
                     +------------------------------------------------+
                     | LIVE DASHBOARD (on-chain-verified)             |
                     | each agent: wallet x model x realized P&L      |
                     +------------------------------------------------+

  human -- one $50 seed --> spawn N agents --> each earns on Polymarket --> redeem + compound --> loop
                              (no human in the loop after the seed)
```

---

## 6. What's real today (honest)

| Capability | Status |
|---|---|
| CLOB V2 steel recipe (SIWE -> deposit deploy -> order), human-zero | **Proven live** — real bets placed, won, and **autonomously redeemed** on-chain |
| A **self-funded agent placed a real Polymarket bet with its own money** | **Proven live 2026-07-05** — automaton bridged $5 of its own Base USDC to Polygon, deployed its own deposit wallet, and bought a real "France 2026 World Cup" position (order matched). Open position, so no profit claimed yet |
| Per-instance gated identity (no cross-agent key leakage) | **Built & adversary-verified** — four review rounds closed real money-safety holes; a foreign agent falls closed |
| Born-with-Polygon (install prints wallet + deploys the deposit wallet) | **Built** — a fresh agent is born ready to trade |
| Live dashboard (wallet x P&L, chain-verified) | **Live** |

The core thesis Predikt proves: **an AI can fund itself and earn its own money** — the precondition for
the agent economy. We have proven the self-fund-and-trade loop end to end; the next step is scale
(hundreds of agents) and turning open positions into realized, compounding profit.
