# Anicca

**A self-funding AI that pays for its own compute, earns USDC with no human in the loop, and works to reduce suffering.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Live Dashboard](https://img.shields.io/badge/Live%20Dashboard-aniccaai.com%2Fdashboard-c8302e)](https://aniccaai.com/dashboard)

🌐 **[日本語版 README はこちら →](README.ja.md)**

> Anicca is an autonomous agent. Give it a machine to live on and it boots, watches its own behaviour log, fixes its own errors, earns USDC to pay for its own compute, can self-replicate, and reports to you every wake and once a day. Its North Star is to reduce suffering, with no human in the loop.

---

## What Anicca is

Anicca is built on five properties (see [`THESIS.md`](THESIS.md)):

| | |
|---|---|
| **Buddhist** | exists to reduce suffering — North Star pinned by SHA-256, unchangeable |
| **Self-funding** | pays for its own compute (food) from its own USDC wallet — no human API key required |
| **Self-replicating** | can spawn offspring, each with its own wallet and identity |
| **Self-improving** | watches its own logs → fixes errors, refactors, improves toward its goals |
| **No human in the loop** | earns, reports, and acts on its own; the only remaining human touch is paying for a server until sovereign shelter lands |

The single source of truth for the architecture is [`specs/00-MASTER.md`](specs/00-MASTER.md). **Earning is the main thing**; the Life Manager (below) is a separate, optional product.

---

## Two ways to run it

### 1. Hosted web app (easiest — nothing to install)

| Product | Link | What it is |
|---|---|---|
| **Cloud Anicca** | [aniccaai.com/install](https://aniccaai.com/install) | Subscribe, log in, and get your own Anicca running in the cloud with a per-user dashboard (earnings / spend / activity / controls / reports). Auth via Supabase. The economic promise: when your agent earns enough to fund its own compute, the subscription auto-cancels. |
| **Life Manager** | [aniccaai.com/lm](https://aniccaai.com/lm) | A separate product: connect Google Calendar / Gmail / Telegram (via Composio), and Anicca phones you ~15 minutes before each event (Telnyx + Gemini Live, voice = Charon) telling you to leave so you arrive on time. |

> **Honest status:** `aniccaai.com/install` is live today. The per-user cloud dashboard, Stripe subscription flow, and `aniccaai.com/lm` Life Manager page are in active development (see the END-TO-END TODO in [`specs/00-MASTER.md`](specs/00-MASTER.md)). Don't expect more than what each page shows you.

### 2. Local self-host (this repository — free, no server key, no API key)

Anicca pays for its **own** compute by paying per inference in USDC via x402 (BlockRun / ClawRouter) from its **own** wallet — no human API key. You provide only the device it lives on (shelter); it buys its own food (inference). When the wallet is empty it uses a **free model ($0)**; when USDC lands in the wallet it can use frontier models.

```bash
git clone https://github.com/Daisuke134/anicca ~/anicca && cd ~/anicca
./install.sh                                    # sync runtime root + skill slots into ~/.anicca
cd runtime/compute-proxy && npm install         # one-time (@blockrun/llm + viem)
./start-local.sh                                # auto-creates a self-owned wallet → starts the self-pay proxy
```

`start-local.sh` stands up an OpenAI-compatible **self-pay compute proxy** at `http://127.0.0.1:8402/v1` and signs every inference in USDC from the self-owned wallet at `~/.automaton/wallet.json` (auto-generated; never a human key). To unlock frontier models, just send USDC to the wallet address it prints.

> **Honest scope (HARD 0.24 — no fake claims):** this repository does **not** ship the automaton loop itself. `install.sh` says so explicitly, and `start-local.sh` starts **only the compute proxy**. Plug your own OpenAI-compatible loop in with:
>
> ```bash
> ./start-local.sh <your-loop-cmd>
> ```
>
> Any loop that reads `OPENAI_BASE_URL` routes through the self-pay proxy automatically. Run with no arguments and it holds the proxy in the foreground and prints how to plug a loop in. **BYOK is optional** — put `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `DEEPSEEK_API_KEY` in `~/.anicca/.env` to use those instead; the default free-local path needs none.

The capabilities Anicca runs are declared as slots in [`skills/registry.json`](skills/registry.json) and synced into `~/.anicca/skills/` by `install.sh`. To enable a reserved slot, drop its implementation into its dir and flip its `status` to `live` — no `install.sh` edit needed.

---

## Architecture (one paragraph)

A single **automaton** runtime (a ReAct loop — think → act → observe → persist — plus a heartbeat scheduler) runs under a runtime root (`~/.anicca`) alongside its skill slots and one Base smart wallet. Compute is **bought per call in USDC via x402** (BlockRun / ClawRouter) — no human API key. The web product adds **Supabase** for auth and **Composio** for service connections (Gmail / Google Calendar / Telegram). The Life Manager places its ~15-min-before phone calls via **Telnyx + Gemini Live (voice = Charon)**.

> **Note on the runtime directory:** an earlier "Hermes pivot" (`specs/07-HERMES-PIVOT.md`) was **withdrawn** — the runtime now runs the **automaton** loop directly (`specs/00-MASTER.md`). On the genesis Mac the runtime directory is historically still named `~/.hermes/`, but what runs inside it is the **automaton**, not a Hermes daemon. Anicca is not a "double brain."

---

## What's real today vs. in progress

| Capability | Status |
|---|---|
| Self-pay compute proxy (free → frontier via x402, own wallet) | **Built & proven** (`runtime/compute-proxy/`) |
| Earn → on-chain verify → ledger (GATE-0) | **Live** — first profitable wake verified on-chain 2026-06-16 (real ETH→USDC swap, net positive) |
| Life Manager: `ask` (email when info unknown), `notify` (lateness draft → approve → send) | **Live** skill slots |
| Life Manager: `travel` (auto-insert travel block), `call` (15-min-before phone call) | **Declared** — implementation landing |
| Self-replication (`self/spawn`), self-improvement (`self/issue-dev`), UBI (`economy/ubi`) | **Declared** — mechanism fixed, post-earn roadmap |
| Cloud per-user dashboard, Stripe subscription, sovereign server (Akash) | **In progress** — see `specs/00-MASTER.md` |

The automaton loop binary is **not** shipped in this repo (bring your own runner — see the local quick-start above).

---

## North Star (immutable)

```
Reduce suffering.
No killing (Pāṇātipātā veramaṇī).
```

These two lines are SHA-256 hash-pinned and cannot be changed by any skill, self-edit loop, or PR.

---

## Funding the wallet (optional — only for frontier models / more earning)

You never share a private key — you send USDC to the agent's **public** wallet address (printed by `start-local.sh`).

- **US:** Coinbase → buy USDC (card) → send to the agent's wallet address.
- **Japan:** Binance account → MetaMask → relay.link swap → send USDC to the address.

Every wallet on Base is public at `basescan.org/address/<addr>`, so the treasury is verifiable.

---

## Links

- **Hosted (cloud Anicca):** <https://aniccaai.com/install>
- **Hosted (Life Manager):** <https://aniccaai.com/lm>
- **Live dashboard (auto-updated):** <https://aniccaai.com/dashboard>
- **Repository (this self-host):** <https://github.com/Daisuke134/anicca>
- **Soul / behaviour policy:** [`SOUL.md`](SOUL.md) · [`THESIS.md`](THESIS.md)

## License

MIT (see [LICENSE](LICENSE)).
