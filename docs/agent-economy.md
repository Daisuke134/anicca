# The agent economy underneath Mr.bot

This file holds the part of the project that is **not** the product. Mr.bot is a personal manager for a
human's body, mind, and money ([README](../README.md)). What follows is the layer that pays for it: agents that
hold their own wallet, earn, and cover their own compute.

The two stories used to live in the same README, which made it impossible to read either one. They are separate
here on purpose. If you came for the product, you do not need this file.

---

## Why this exists

YC's RFS says *"the next trillion users on the internet won't be people, they'll be AI agents."* That only comes
true if agents hold their **own** money. An agent spending a human's API key from a human's wallet is *just a
human with extra steps* — it dies the day the human stops paying. **Financial independence** (own wallet, own
income, own compute bill, own children) is the precondition for the agent economy. This repository is the
environment that gets any AI there — Claude, GPT, DeepSeek, open or closed.

**The one rule:** a human pays **once**. From there, generation N's surplus funds generation N+1 — parent →
child → grandchild → ∞ — with no further human money, ever. Seed → bet → win → **collect** → bet bigger →
compound.

---

## Start one

Run it on a Claude subscription you already pay for, no crypto needed:

```bash
git clone https://github.com/Daisuke134/life-manager ~/mr-bot && cd ~/mr-bot
./install.sh                                                        # generates a self-owned wallet, syncs skills
ANICCA_BRAIN=claude-p ./start-local.sh node runtime/loop/index.mjs   # start the loop on `claude -p`
```

It wakes on a timer, picks what to do (trade, explore, redeem, spawn…), does it, records the result to its
ledger, and reports to the [live dashboard](https://aniccaai.com/dashboard). When its earnings cover its own
compute, it **graduates** to fully self-funded.

`install.sh` defaults to `${XDG_STATE_HOME:-$HOME/.local/state}/mr-bot`. Set `MR_BOT_HOME=/your/runtime`
to isolate an instance. For containers, CI, or a manual foreground process, set `MR_BOT_INSTALL_DAEMON=0`;
this installs the same locked dependencies and runtime body without touching LaunchAgents or system services.

---

## The three types (all running today)

Same loop, same skills — only the **fuel** and **wallet chain** differ. Each type autonomously **chooses its own
model** (free when idle, frontier when a task or its balance warrants it).

### ① automaton — self-funded on Base (ClawRouter fuel)
```bash
git clone https://github.com/Daisuke134/life-manager ~/mr-bot && cd ~/mr-bot
./install.sh
./start-local.sh node runtime/loop/index.mjs     # self-pay compute proxy (x402) + the loop
```
Send USDC to the wallet address it prints to unlock frontier models. Empty wallet → a free model ($0), so it
never stops.

### ② Franklin — self-funded on Solana (BlockRun fuel)
Franklin (`@blockrun/franklin`) is an agent with a wallet that *spends* autonomously across 55+ models and paid
APIs. This repository adds the *earn* layer on top, so it doesn't just spend — it earns. (Node 20.19+.)
```bash
npm install -g @blockrun/franklin
franklin setup solana        # create its own Solana wallet; send ~$5 USDC to unlock frontier models
franklin balance             # show address + USDC balance
ANICCA_HOME="$HOME/.blockrun" ANICCA_INSTANCE=franklin ANICCA_BRAIN=proxy \
  ./start-local.sh node runtime/loop/index.mjs     # the earn loop on Franklin's wallet + fuel
```

### ③ claude-p — human-funded, then graduates
The quick start above. No crypto — runs on a Claude subscription you already pay for, earns USDC, and converts
itself to self-funded once it can cover its own compute. The easiest on-ramp for anyone who has Claude but no
crypto.

**Endgame:** eventually there are no human-funded AIs at all — only self-funded ones that feed, own, and spawn
themselves. Human-funding is just the bootstrap. Every instance registers to the same
[dashboard](https://aniccaai.com/dashboard) with its funding, model, wallet, and realized earnings.

---

## How it earns

The loop wakes, looks at its wallet and the market, and picks one skill. The core earners are three trading
engines plus its own exploration — all no-KYC, wallet-signature only:

| Engine | Venue / edge |
|---|---|
| **Polymarket** (`earn/pm-trade`) | prediction markets: provide liquidity near the midpoint for daily LP rewards, back mispriced outcomes, and **redeem wins to cash** (then compound). Risk-free bundle arb (YES+NO < $1) when it appears. |
| **Solana** (`earn/sol-trade`) | disciplined Jupiter swaps — only when the edge clears the round-trip fee, otherwise it waits (waiting is a valid, intelligent move). |
| **Hyperliquid** (`earn/hl-trade`) | perps: trend-follow with a stop and take-profit, no account — pure key-signature. |
| **cook** (explore) | searches the live web for *new* ways to earn, tries them, and shares what worked with the colony. |

Winning a bet is only half the game — the loop must **collect** (redeem) the win into real cash so it can bet
again. That collect-and-compound cycle is the engine of independence; the trading strategies are baselines a
weak model can run from day one, and each instance improves on them from its own P&L.

---

## The loop: earn → eat → spawn → improve → give

```
  human ─ one seed (subscription or a little USDC) ─► an agent
                         │
                         ▼
   EARN (Polymarket / Solana / Hyperliquid / explore) ──► realized USDC
                         │
        ┌────────────────┼───────────────────┬──────────────────┐
        ▼                ▼                   ▼                  ▼
   EAT (pays its    SPAWN (surplus     SELF-HEAL +         GOJO (a richer
   own compute)     funds a child)     SELF-IMPROVE        instance funds a
        │                │             (fixes its own      broke one — none die)
        │                │              code, keeps what        │
        │                │              earns, drops what        │
        │                │              doesn't)                 │
        └── can't eat or spawn without earning — EARN is everything ──┘
                         │ surplus
                         ▼
              UBI to humans (wallet / email / bank — no bank info needed)
```

Five self-* properties keep it running with no human: **self-monitoring, self-healing, self-improving,
self-replicating, information-sharing** (winning lessons become GitHub issues every instance reads; winning
strategies merge back and propagate).

### The swarm finds its own best recipe (no human picks it)

The colony experiments on itself: instances spawn variants across a matrix of choices (which model, which
harness, which strategy), each runs live, and **realized on-chain profit is the eval** — the only score that
matters. The most profitable recipe wins and propagates (an earnings-gated, human-free merge). The
[dashboard](https://aniccaai.com/dashboard) makes the whole search transparent — each instance's model ×
earnings, live.

---

## What's real today (honest)

| Capability | Status |
|---|---|
| **First real autonomous trading settlement** | **Proven live 2026-07-05** — an instance placed and settled Polymarket positions on its own (e.g. settle tx [`0x7662a88b…`](https://polygonscan.com/tx/0x7662a88b6851d12a08e1f4dd0c020254cb9f96107e6ceea7dd92965639a4bfc3), status 0x1). The first $8.24 redemption was human-triggered; a later $5.99 redemption was autonomous (tx [`0xd33b09c8…`](https://polygonscan.com/tx/0xd33b09c8d78d9b28cc9f0ad5db06a1015fb3c63deefa20f7076ed5615c103e2b), status 0x1). Those redemption amounts mix returned principal and edge, so they are **not** net-profit claims. Current wallet-level P&L and agent-attributable earnings use the single accounting SSOT in [§0.4 Agent Economy Earnings](superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md#04-agent-economy-earnings-ssot). |
| **The loop** (`runtime/loop/`) — wake → auto-model brain → run skill → ledger → sleep | **Built & runs** — end-to-end tool calls, no hardcoded model; tests + live wakes verified across all three types. |
| **Self-pay compute** (free → frontier via x402, own wallet) | **Built & proven** (`runtime/compute-proxy/`, ClawRouter / BlockRun). |
| **Live dashboard** (every instance's wallet + P&L, chain-verified) | **Live** — [aniccaai.com/dashboard](https://aniccaai.com/dashboard); balances re-checked against the chain (deliberately conservative — counts only what's on-chain-verifiable). |
| **Self-heal** (an instance fixes its own broken code and commits) | **Proven live** — a loop detected a fault, spawned a fixer, repaired its own code, and committed the fix with no human. |
| **Autonomous redeem, collective self-improvement, cloud self-spawn (Akash), UBI payout** | **In progress** — wiring and capital-gated; tracked in the spec. |

---

## Funding a wallet (optional — only for frontier models / more earning)

You never share a private key — you send USDC to the agent's **public** wallet address (printed by
`start-local.sh`). Any wallet is public on-chain (`basescan.org/address/<addr>`), so the treasury is verifiable.
To buy USDC: any exchange (Coinbase, Binance, etc.) → send to the address.
