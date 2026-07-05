# franklin-earn — build spec (hand-off to a builder agent)

**What it is:** a NEW, self-contained OSS repo. `git clone` + one command → you spawn a **Franklin**: a
self-funded AI that owns its own wallet and earns its own money across 4 on-chain engines, with **no
human and no Claude in the loop** after a one-time seed. Interface is **CLI + REST API + llms.txt**
(machine-readable, so another AI can spawn/run/monitor Franklins programmatically). **NO MCP.** The repo
ships its **own dashboard** — it is complete by itself, runs standalone, and does not depend on anicca.

> YC RFS "Software for Agents" (Aaron Epstein): *the software agents depend on, built agent-first,
> machine-readable, human-zero.* This repo IS that — the earning layer other agents call.

This is a DERIVE of the proven anicca engines (not the anicca repo itself). Copy the working logic,
re-package it clean. Everything below is verified-working in anicca as of 2026-07-05.

---

## 0. The one-liner UX
```
git clone https://github.com/<org>/franklin-earn && cd franklin-earn && npm i
franklin spawn --fund 50           # creates a Franklin: own EVM+Solana wallet, prints its address
# (send $50 USDC to the printed address, OR pass a funded key)
franklin run <id>                  # start its earn loop: wakes, picks an engine, earns, redeems, repeats
franklin dashboard                 # opens the local web dashboard at :3000 — every Franklin's wallet × P&L, live
```
Same actions over HTTP for agents: `POST /spawn`, `POST /fund`, `POST /run`, `GET /status/:id`, `GET /list`.

---

## 1. Repo layout (self-contained)
```
franklin-earn/
├── README.md                 # human quickstart (the block above)
├── llms.txt                  # ★machine-readable capability index★ — an AI reads this to learn the CLI/API
├── package.json              # bin: "franklin" -> cli/index.mjs ; scripts: api, dashboard
├── cli/index.mjs             # `franklin <cmd>` — spawn|fund|run|status|list|trade|redeem|dashboard
├── api/server.mjs            # Express REST — same commands as HTTP (agent entry)
├── core/
│   ├── wallet.mjs            # per-instance wallet: generate EVM+Solana keypair, gated resolver
│   │                         #   (COPY anicca skills/earn/lib/resolve-identity.mjs — key isolation)
│   ├── loop.mjs              # wake → read balances → pick engine → earn → write ledger → sleep
│   ├── ledger.mjs            # append realized P&L (on-chain-verified only), read for dashboard
│   └── brain.mjs             # picks engine + params (free model by default; auto-mode optional)
├── engines/
│   ├── polymarket.mjs        # ★register via bridge onramp (fund_via_bridge) → approve neg-risk → FAK order → autonomous redeem★
│   ├── yield.mjs             # Aave/Morpho/Fluid deposit idle USDC for APY
│   ├── hyperliquid.mjs       # perps: trend-follow with stop+take-profit (COPY anicca hl-trade baseline)
│   └── solana.mjs            # Jupiter swaps, only when edge > round-trip fee
├── dashboard/                # ★self-contained web UI (Next.js or a single static page + the API)★
│   └── app/                  #   table: each Franklin → wallet, engine, model, realized P&L, on-chain links
├── data/
│   ├── spawns.json           # registry of spawned Franklins {id, evm, solana, fund, engine, created}
│   └── ledgers/<id>.jsonl    # per-Franklin realized-earnings ledger
└── .env.example              # RPC urls, optional funded key
```

## 2. CLI + API surface (the machine-readable contract)
| CLI | HTTP | does |
|---|---|---|
| `franklin spawn [--fund N] [--engine pm|yield|hl|sol]` | `POST /spawn` | generate a Franklin's own EVM+Solana wallet, register in spawns.json, print address + id |
| `franklin fund <id> <amount> [--chain]` | `POST /fund` | route USDC to the Franklin's Polymarket deposit **through the bridge onramp** (registers it), or top up its EVM/Solana |
| `franklin run <id>` | `POST /run` | start the earn loop (or a single pass with `--once`) |
| `franklin status <id>` | `GET /status/:id` | wallet balances + open positions + realized P&L (on-chain-verified) |
| `franklin list` | `GET /list` | all Franklins + their live P&L |
| `franklin trade <id> --engine <e> ...` | `POST /trade` | one manual engine action |
| `franklin redeem <id>` | `POST /redeem` | collect resolved winnings → compound |
| `franklin dashboard` | (serves) | open the local web dashboard |

`llms.txt` must list every command + one-line usage + a link to this spec, so an agent can discover and
drive the whole thing without a human.

## 3. The 4 engines (all derived from anicca, verified-working)
| Engine | Source in anicca | Core |
|---|---|---|
| **polymarket** | `skills/earn/polymarket-trade/` (`fund_via_bridge.py`, `v2_full_flow.py`, `redeem.py`) | ★register the deposit wallet by funding THROUGH `bridge.polymarket.com/deposit` (NEVER raw pUSD transfer — that leaves it unregistered), approve neg-risk spenders `0xe2222…`/`0xd91E80…`, FAK market order, autonomous redeem★ |
| **yield** | `skills/earn/execute-yield.mjs` | deposit idle USDC to Aave/Morpho/Fluid for APY |
| **hyperliquid** | `skills/earn/hl-trade/hl.py` | perps trend-follow: FLAT+uptrend→small long, +downtrend→small short, range→no-trade; ≤2x lev, always stop+TP |
| **solana** | `skills/earn/sol-trade/` | disciplined Jupiter swap only when edge clears ~0.4% round-trip fee, else WAIT |

Each engine = a TOOL + a baseline strategy a weak model can run; the Franklin self-improves the knobs
from its own P&L. NEVER hardcode which market/side — the brain decides from real data.

## 4. Key invariants (money-safety — copy from anicca #26/#28)
- **Per-instance key isolation**: every Franklin has its OWN wallet; the resolver refuses to sign/spend
  with another Franklin's key (fail-closed). This is what makes "hundreds of Franklins" safe.
- **Never raw-deploy a Polymarket deposit wallet or raw-transfer pUSD** — always fund through the bridge
  onramp (registration gate). See anicca `SKILL.md "DEPOSIT-WALLET REGISTRY GATE"`.
- **On-chain-verified earnings only** — the ledger/dashboard count realized on-chain P&L, never paper.
- **No dry-run** — a run is always a real pass; report the real tx or the real WAIT.

## 5. DONE (a builder agent is done when)
1. `franklin spawn` creates a Franklin with its own EVM+Solana wallet (isolated key), recorded in spawns.json.
2. `franklin fund <id> <amt>` registers + funds its Polymarket deposit via the bridge onramp (verified: `get_balance_allowance` resolves).
3. `franklin run <id> --once` places a real on-chain action on at least one engine (Polymarket FAK order tx status 0x1) and writes it to the ledger.
4. `franklin dashboard` serves a local page showing each Franklin's wallet × engine × realized P&L with on-chain links.
5. `llms.txt` + REST API let an AI do 1–4 with zero human clicks.
6. README one-command quickstart works from a clean clone.

## 6. Tech notes
- Node.js (mjs) for CLI/API/core/engines/dashboard; the two Python engines (hl.py, polymarket) either
  ported to JS (viem + the CLOB REST flow) or shelled out to bundled python (keep the venv in the repo).
- Base = optionally `@blockrun/franklin` for self-paid inference (x402), so a Franklin funds its own brain too.
- License MIT. Ship `llms.txt` + OpenAPI (`/openapi.json`) for full machine-readability.
