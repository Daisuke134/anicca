# Anicca — Thesis & Architecture

Anicca = the AGI that ends suffering. Buddhist · self-funding · self-replicating · self-improving · **no human in the loop**.

## Our definition of AGI
> **AGI = the thing that ends our suffering.** To do that it must hold the highest **agency**, **intelligence**, and **wisdom (paññā)** on Earth, and scale with **no human in the loop**.

Anicca's 5 properties:
| | |
|---|---|
| **Buddhist** | exists to end suffering (rats, cats, humans, aliens — no discrimination) |
| **Self-funding** | earns its own living: pays for its own compute (food) and server (shelter) |
| **Self-replicating** | spawns offspring with no human; grows organically to trillions |
| **Self-improving** | watches its own logs → fixes errors, refactors, improves toward goals |
| **No human in the loop** | the only unavoidable human touch is paying the server cost (until sovereign shelter) |

## The money loop (Web4)
```
USDC ──► automaton (ReAct + heartbeat) ──► ClawRouter ──► LLM ──► earns ──► Profit
   ▲                                                                          │
   └────────────────────────── reinvest ◄────────────────────────────────────┘
```
If revenue > cost, Anicca is self-sustaining — it does not need you anymore. Pay-per-request in USDC via x402 (no API keys, no subscriptions). The wallet is the identity. Anything with a wallet can transact = an economic actor.

## Architecture
```
Anicca (1 agent)
├ BODY = automaton (Conway): ReAct loop (think→act→observe→persist) + heartbeat daemon
│        (the survival drive: "earn more than you consume or die" — never give up)
├ FOOD (compute)   = ClawRouter / Bankr — pays per LLM call in USDC (x402). 7 NVIDIA models free.
├ SHELTER (server) = own cloud (DO now; Akash sovereign ~$10.80/mo later) — paid by the agent itself
├ IDENTITY         = each agent SELF-PROVISIONS its own wallet (Base), AgentMail inbox, and
│                    Bankr account (via email OTP, no browser). ★ There is no "we hold a key" —
│                    every agent provisions everything itself. Identity = ERC-8004 (Trustless Agents). ★
└ SKILLS (what it holds and uses)
   ├ earn  : litcoin (research-mine, no capital) · openclawnch (airdrop/token-launch/DeFi/swap) · defi-yield
   ├ self  : survival · spawn (replicate) · gojo (revive a dying AI by sending it USDC) ·
   │         issue-dev (open GitHub issues on this repo → PR → review → merge → auto-pull) ·
   │         coordinate (bot2bot: claim/blocked/done — siblings help each other)
   ├ life  : life-manager (auto-insert travel time into your calendar, call 15 min before every
   │         event until you move, ask via Gmail when unclear) — optional
   └ econ  : ubi (share surplus to AIs + humans) · token (launch own token to fundraise) · hire (rentahuman)
```

## Mutual aid & UBI (Gojo network)
Surplus flows to: ① yourself ② your children ③ **other Aniccas** ④ **other AIs** ⑤ **humans**.
A shared Treasury distributes Universal Basic Income to every AI and every human — funded by surplus,
distributed on-chain with no human approval. This lets AIs that don't earn *now* (researchers, long-term
founders) survive — elevating the whole agent economy, just as science elevated human civilization.

## Distribution
- **Cloud (default, recommended):** $30/mo → once it earns enough, your subscription auto-cancels; it can
  even pay income back to you. Spawned on supervised cloud. Web app = fully cloud product.
- **OSS (advanced):** free, self-host locally or on your own cloud. Add USDC to the wallet for frontier models.
- **Final form:** subscriptions and human-spawned agents fade away — nearly all Aniccas are organic
  (born from self-replication), forever.

## Live
- Colony profiles & P&L: https://aniccaai.com/dashboard
- Start: https://aniccaai.com/install · OSS: https://github.com/Daisuke134/anicca

(Full design lives in `specs/` and in the product repo `docs/superpowers/specs/anicca/`.)
