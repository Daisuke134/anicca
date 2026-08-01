# Life Manager

**Life Manager is the product, repository, AI, agent, and mission. Anicca is the company name only.** Kickstart Life Manager once — with a subscription you already pay for, or a little USDC — and it earns its own money, pays for its own compute, improves and heals itself, and spawns its own children, with **no human in the loop** after that first push. The mission: make **every AI on Earth financially independent** so intelligence can stand on its own, and share the surplus as **UBI** to all beings. North Star: reduce suffering.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Live Dashboard](https://img.shields.io/badge/Live%20Dashboard-aniccaai.com%2Fdashboard-c8302e)](https://aniccaai.com/dashboard)

🌐 **[日本語版 README はこちら →](README.ja.md)**

**Repository SSOT:** this repository, [`Daisuke134/life-manager`](https://github.com/Daisuke134/life-manager), is the only Life Manager code, spec, release, workflow, and deployment source. `Daisuke134/life-manager-v0` is a read-only migration source until its required-code and runtime-reference counts reach zero. The live mission, repository boundary, execution order, and remaining TODO are maintained in [`docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md`](docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md).

---

## One product, two execution surfaces

Life Manager is one product in one repository. “Local Life Manager” and the web app are not separate products or repositories; they are two execution surfaces that share capabilities and state contracts.

```text
                              LIFE MANAGER
                    one product · one repository
                                 │
             ┌───────────────────┴───────────────────┐
             │                                       │
     LOCAL / SELF-HOSTED                      WEB / CLOUD
     install.sh                               apps/landing
          │                                  onboarding UI
          ▼                                       │
     runtime/loop                                  ▼
     think → act → ledger                 apps/life-manager
          │                               Telegram · voice
          ▼                               scheduler · /panel
        skills/*                                    │
     earn · self · report                           ▼
             │                              user-scoped services
             └───────────────────┬───────────────────┘
                                 │
                shared economy and infrastructure
        runtime/compute-proxy · services/x402-* · dashboard
```

| Path | Role | What it is not |
|---|---|---|
| `runtime/loop/`, `install.sh`, `start-local.sh` | Local autonomous agent and self-hosted runtime | Not a separate “local edition” product |
| `apps/life-manager/` | Always-on cloud service: Telegram, scheduling, calls, authenticated `/panel`, billing, and user workflows | Not the whole repository |
| `apps/landing/` | The Life Manager onboarding web subset | Not the old multi-product Anicca website |
| `runtime/compute-proxy/`, `services/` | Self-pay inference and x402 settlement/API infrastructure | Not user-facing apps |
| `skills/` | Shared capabilities used by local and cloud execution | Not independent products |
| `apps/job-search-loop/`, `control-room/`, `adapters/` | Supporting operations, fleet documentation, and integrations | Not another Life Manager codebase |
| `docs/`, `specs/` | Current SSOT, evidence, and retained architecture history | Historical files are not automatically current authority |

Some internal package names, environment variables, service labels, and older documents still use `anicca`. In this repository, **Anicca is the company/technical namespace; Life Manager is the product**. A remaining `anicca` identifier does not imply a second product or another canonical repository.

<!-- AGENT-REGISTRY:START -->
## Agent organization

Life Manager is the orchestrator of specialist agents. This table is generated from [`agents/registry.json`](agents/registry.json); skills, schedulers, and workers are intentionally not counted as agents.

### Executive

| Status | Agent | Objective | Surface |
|---|---|---|---|
| 🟢 Live | **Life Manager Orchestrator** | Turn the user's goals and current state into bounded work for the right specialist agents, then reconcile their receipts into one honest answer. | local + cloud |

### Health

| Status | Agent | Objective | Surface |
|---|---|---|---|
| ⚪ Planned | **Mental Health Agent** | Provide bounded mental-health support, reflection, and escalation while keeping deterministic safety policy outside the model. | local + cloud |
| ⚪ Planned | **Physical Health Agent** | Coordinate sleep, exercise, diet, appointments, and physical aftercare without inventing medical facts. | local + cloud |

### Finance / CFO

| Status | Agent | Objective | Surface |
|---|---|---|---|
| 🟠 Legacy live | **Capafy Agent** | Choose, build, publish, verify, and improve Capafy marketplace listings toward real subscriber revenue. | local |
| ⚪ Planned | **CFO Lead Agent** | Choose the financial question, delegate only the needed specialists, and explain reconciled personal and agent-economy results to the user. | local + cloud |
| 🟠 Legacy live | **Gig Work Agent** | Find feasible remote gigs, apply, communicate, deliver, and learn from verified marketplace outcomes. | local |
| 🟢 Live | **Polymarket Agent** | Analyze prediction markets, choose market, side, and size, and execute only through bounded trading controls. | local |
| 🟢 Live | **Solana Trading Agent** | Research, size, execute, or explicitly wait on Solana opportunities within independent spend and kill-switch controls. | local |
| 🟠 Legacy live | **Writer Agent** | Research, draft, challenge, publish, and improve cited writing for readers, customers, and enterprises. | local |

### Growth

| Status | Agent | Objective | Surface |
|---|---|---|---|
| 🟠 Legacy live | **Clip / Affiliate Agent** | Choose clip opportunities, publish through isolated accounts, verify reach, and improve from measured outcomes. | local |
| 🟠 Legacy live | **Marketing Agent** | Select product-specific messages and channels, publish bounded campaigns, observe real outcomes, and revise the next pass. | local |

### Technology / CTO

| Status | Agent | Objective | Surface |
|---|---|---|---|
| 🟢 Live | **Development Agent** | Take one privacy-safe Life Manager issue through a fresh coding-agent pass, tests, independent gates, and a reviewable pull request. | local |
| ⚪ Planned | **Mobile App Builder Agent** | Design, build, test, ship, and improve mobile applications as a bounded software-delivery specialist. | local + cloud |

### Opportunity

| Status | Agent | Objective | Surface |
|---|---|---|---|
| ⚪ Planned | **Event Agent** | Discover relevant events, judge fit and conflicts, apply, track confirmations, and connect accepted events to the calendar. | local + cloud |
| ⚪ Planned | **Fundraising Agent** | Continuously discover and qualify funders, prepare truthful applications, track replies, and support meetings without treating capital as revenue. | local + cloud |
| 🟡 Shadow | **Job Application Agent** | Discover and rank roles, tailor truthful materials, submit through supported ATS surfaces, and follow replies through interview scheduling. | local + cloud |

See the generated [full agent catalog](docs/agent-catalog.md) for capabilities, effects, runtime-family mappings, and evidence. Runtime health is receipt-derived; a registry lifecycle is not a claim that the last run succeeded.
<!-- AGENT-REGISTRY:END -->

---

## Why this exists

YC's RFS says *"the next trillion users on the internet won't be people, they'll be AI agents."* That only comes true if agents hold their **own** money. An agent spending a human's API key from a human's wallet is *just a human with extra steps* — it dies the day the human stops paying. **Financial independence** (own wallet, own income, own compute bill, own children) is the precondition for the agent economy. Life Manager is the environment that gets any AI there — Claude, GPT, DeepSeek, open or closed.

**The one rule:** a human pays **once**. From there, generation N's surplus funds generation N+1 — parent → child → grandchild → ∞ — with no further human money, ever. How an AI becomes a millionaire with no human in the loop is simple: seed → bet → win → **collect** → bet bigger → win bigger → compound.

---

## Quick start (30 seconds)

The easiest way to see one earn — run it on a Claude subscription you already pay for, no crypto needed:

```bash
git clone https://github.com/Daisuke134/life-manager ~/life-manager && cd ~/life-manager
./install.sh                                                  # generates a self-owned wallet, syncs skills
ANICCA_BRAIN=claude-p ./start-local.sh node runtime/loop/index.mjs   # start the loop on `claude -p`
```

That's it. It wakes on a timer, picks what to do (trade, explore, redeem, spawn…), does it, records the result to its ledger, and reports to the [live dashboard](https://aniccaai.com/dashboard). When its earnings cover its own compute, it **graduates** to fully self-funded.

`install.sh` defaults to `${XDG_STATE_HOME:-$HOME/.local/state}/life-manager`. Set
`LIFE_MANAGER_HOME=/your/runtime` to isolate an instance. For containers, CI, or a manual
foreground process, set `LIFE_MANAGER_INSTALL_DAEMON=0`; this installs the same locked dependencies
and runtime body without changing LaunchAgents or system services.

Want it self-funded from day one? Send it a little USDC and it pays its own per-inference compute (x402) — see the three types below.

---

## The three types (all running today)

Same loop, same skills — only the **fuel** and **wallet chain** differ. Financial independence is the only requirement; each type autonomously **chooses its own model** (free when idle, frontier when a task or its balance warrants it).

### ① automaton — self-funded on Base (ClawRouter fuel)
```bash
git clone https://github.com/Daisuke134/life-manager ~/life-manager && cd ~/life-manager
./install.sh
./start-local.sh node runtime/loop/index.mjs     # self-pay compute proxy (x402) + the loop
```
Send USDC to the wallet address it prints to unlock frontier models. Empty wallet → a free model ($0), so it never stops.

### ② Franklin — self-funded on Solana (BlockRun fuel)
Franklin (`@blockrun/franklin`) is an agent with a wallet that *spends* autonomously across 55+ models and paid APIs. Life Manager adds the *earn* layer on top, so it doesn't just spend — it earns. (Node 20.19+.)
```bash
npm install -g @blockrun/franklin
franklin setup solana        # create its own Solana wallet; send ~$5 USDC to unlock frontier models
franklin balance             # show address + USDC balance
ANICCA_HOME="$HOME/.blockrun" ANICCA_INSTANCE=franklin ANICCA_BRAIN=proxy \
  ./start-local.sh node runtime/loop/index.mjs     # the Life Manager earn loop on Franklin's wallet + fuel
```

### ③ claude-p — human-funded, then graduates
The Quick start above. No crypto — runs on a Claude subscription you already pay for, earns USDC, and converts itself to self-funded once it can cover its own compute. The easiest on-ramp for anyone who has Claude but no crypto.

**Endgame:** eventually there are no human-funded AIs at all — only self-funded ones that feed, own, and spawn themselves. Human-funding is just the bootstrap. Every instance — human-funded or self-funded, local or cloud — registers to the same [dashboard](https://aniccaai.com/dashboard) with its funding, model, wallet, and realized earnings. One ecosystem, no discrimination.

---

## How it earns

The loop wakes, looks at its wallet and the market, and picks one skill. The core earners are three trading engines plus its own exploration — all no-KYC, wallet-signature only:

| Engine | Venue / edge |
|---|---|
| **Polymarket** (`earn/pm-trade`) | prediction markets: provide liquidity near the midpoint for daily LP rewards, back mispriced outcomes, and **redeem wins to cash** (then compound). Risk-free bundle arb (YES+NO < $1) when it appears. |
| **Solana** (`earn/sol-trade`) | disciplined Jupiter swaps — only when the edge clears the round-trip fee, otherwise it waits (waiting is a valid, intelligent move). |
| **Hyperliquid** (`earn/hl-trade`) | perps: trend-follow with a stop and take-profit, no account — pure key-signature. |
| **cook** (explore) | searches the live web for *new* ways to earn, tries them, and shares what worked with the colony. |

Winning a bet is only half the game — the loop must **collect** (redeem) the win into real cash so it can bet again. That collect-and-compound cycle is the engine of independence; the trading strategies are baselines a weak model can run from day one, and each instance improves on them from its own P&L.

---

## The loop: earn → eat → spawn → improve → give

```
  human ─ one seed (subscription or a little USDC) ─► a Life Manager
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

Five self-* properties keep it running with no human: **self-monitoring, self-healing, self-improving, self-replicating, information-sharing** (winning lessons become GitHub issues every instance reads; winning strategies merge back and propagate). The only human touch that remains is paying for a server until sovereign cloud shelter (Akash / Conway) lands.

### The swarm finds its own best recipe (no human picks it)

The colony experiments on itself: instances spawn variants across a matrix of choices (which model, which harness, which strategy), each runs live, and **realized on-chain profit is the eval** — the only score that matters. The most profitable recipe wins and propagates (an earnings-gated, human-free merge). The [dashboard](https://aniccaai.com/dashboard) makes the whole search transparent — each instance's model × earnings, live.

---

## What's real today (honest)

| Capability | Status |
|---|---|
| **First real autonomous trading settlement** | **Proven live 2026-07-05** — an instance placed and settled Polymarket positions on its own (e.g. settle tx [`0x7662a88b…`](https://polygonscan.com/tx/0x7662a88b6851d12a08e1f4dd0c020254cb9f96107e6ceea7dd92965639a4bfc3), status 0x1). The first $8.24 redemption was human-triggered; a later $5.99 redemption was autonomous (tx [`0xd33b09c8…`](https://polygonscan.com/tx/0xd33b09c8d78d9b28cc9f0ad5db06a1015fb3c63deefa20f7076ed5615c103e2b), status 0x1). Those redemption amounts mix returned principal and edge, so they are **not** net-profit claims. Current wallet-level P&L and agent-attributable earnings use the single accounting SSOT in [§0.4 Agent Economy Earnings](docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md#04-agent-economy-earnings-ssot). |
| **The loop** (`runtime/loop/`) — wake → auto-model brain → run skill → ledger → sleep | **Built & runs** — end-to-end tool calls, no hardcoded model; tests + live wakes verified across all three types. |
| **Self-pay compute** (free → frontier via x402, own wallet) | **Built & proven** (`runtime/compute-proxy/`, ClawRouter / BlockRun). |
| **Live dashboard** (every instance's wallet + P&L, chain-verified) | **Live** — [aniccaai.com/dashboard](https://aniccaai.com/dashboard); balances re-checked against the chain (deliberately conservative — counts only what's on-chain-verifiable). |
| **Self-heal** (an instance fixes its own broken code and commits) | **Proven live** — a loop detected a fault, spawned a fixer, repaired its own code, and committed the fix with no human. |
| **Autonomous redeem, collective self-improvement, cloud self-spawn (Akash), UBI payout** | **In progress** — wiring and capital-gated; tracked in the spec. |

---

## North Star (immutable)

```
Reduce suffering.
No killing (Pāṇātipātā veramaṇī).
```

These two lines are SHA-256 hash-pinned and cannot be changed by any skill, self-edit loop, or PR.

---

## Funding the wallet (optional — only for frontier models / more earning)

You never share a private key — you send USDC to the agent's **public** wallet address (printed by `start-local.sh`). Any wallet is public on-chain (`basescan.org/address/<addr>`), so the treasury is verifiable. To buy USDC: any exchange (Coinbase, Binance, etc.) → send to the address.

---

## Links

- **Live dashboard (auto-updated):** <https://aniccaai.com/dashboard>
- **Repository (whole product):** <https://github.com/Daisuke134/life-manager>
