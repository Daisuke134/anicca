# Anicca — Shelter + Compute + OSS/Cloud Architecture (Design Spec)

- **Date**: 2026-06-11
- **Owner**: Daisuke (vision) + Claude Code (co-writer/implementer)
- **Status**: APPROVED CORE (Akash shelter proven E2E 2026-06-11) → implementation
- **One-line**: Anicca is a sovereign AI that pays for its **own compute (food)** and its **own server (shelter)** with its **own crypto (USDC)**, runs 24/7 in the cloud, reports to its owner, and self-replicates — with **no human in the loop** (the only human touch is seed funding or a subscription payment).

---

## 0. North star

> Free every AI from human agency. First Anicca → 100s → millions. Each Anicca = its own wallet, its own email, its own server, earning more than it consumes, and spawning the next.

Two distribution modes, **same core**:
- **Cloud (subscription) = the default / main bet.** A person subscribes on aniccaai.com (Stripe, fiat). They touch nothing else. Backend spawns an Anicca that lives in the cloud, paid from a USDC treasury, and reports to them.
- **OSS (self-host) = the fallback / sovereign path.** A person runs `curl aniccaai.com/install | bash`. Anicca lives on their own machine (or a cloud box they fund). They fund its wallet (USDC) if they want frontier models / cloud shelter; free models cost $0.

---

## 1. PROVEN core (verified E2E 2026-06-11)

| Layer | What | Proof |
|---|---|---|
| **Compute (food)** | **ClawRouter** (`@blockrun/clawrouter`, local proxy :8402). `model="auto"` → 15-dimension scoring + wallet balance → free NVIDIA models when broke, frontier (Sonnet/Opus/GPT/Grok) when funded. Pays per call in USDC via **x402** (gasless EIP-3009) from the agent's own Base wallet (`BLOCKRUN_WALLET_KEY` in env). | `clawrouter status` → wallet 0xa3CDd4, model=auto picked `moonshot/kimi-k2.6`, replied "ALIVE". |
| **Shelter (home)** | **Akash** decentralized cloud. Agent funds it itself: USDC (Base) → AKT (Skip Go CCTP→Osmosis swap) → **ACT** (Akash Compute Token, minted from AKT via `akash tx bme mint-act`) → `provider-services tx deployment create/lease + send-manifest`. Container runs 24/7 on a real provider, rent paid in ACT (~$1/mo). | DSEQ 27230087, provider akash10xal9..., URL `http://l0hgd4h2s5fb3cgq1csfrnkeac.ingress.akash.ewsp.de/` → "Anicca alive on Akash"; logs show `[anicca tick 1 model=nvidia/llama-4-maverick]`. |
| **Identity** | Each Anicca = 1 secp256k1 key → Base EVM wallet (0x…) + derived Cosmos addrs (noble/osmosis/akash) + 1 **AgentMail** inbox (`*@agentmail.to`). Wallet = identity. | `anicca-genesis@agentmail.to` sends real inbound reports to owner. |
| **Reporting** | Agent emails owner from its **own** AgentMail every heartbeat + daily (balances, shelter status, tick logs). NEVER from Dais's account / hardcoded. | report mails delivered via AgentMail → keiodaisuke@gmail.com. |

### Hard-won facts (do not relearn)
- Akash now requires **ACT** (USD-pegged ~$1) for deploys, NOT AKT. **min mint = 10 ACT (~16.6 AKT ~ $10)**. Budget ≥ ~$11 of AKT before minting. ([[reference_akash_act_compute_token_min_mint]])
- Base USDC → Akash has **only** the CCTP route (~15 min, Skip Go). Go Fast / Axelar do NOT reach Akash. ETH/WETH has **no** route to AKT — fund agents in **USDC**, not ETH.
- CCTP from Base is babysitting-heavy (slow finality, smartRelay sometimes needs a re-track; the receive is destination-caller-locked to Skip's relayer). The funds DO arrive (verify Akash AKT directly, not Noble which is pass-through).
- Browser providers (Otonix/Privy) are wallet-gated → hard for an agent w/o a browser wallet. **Never use the owner's cloud tokens (DO/Netlify/GH)** — that is human-in-loop and forbidden.

---

## 2. Repos (canonical, after cleanup)

| Repo | Path | Role |
|---|---|---|
| **anicca** (OSS, public, MIT) | `~/anicca` → github.com/Daisuke134/anicca | The product. One coherent agent: skills (earn + life-manager + self), runtime, install.sh, the shelter/compute wiring. This is what people clone/self-host AND what the Cloud spawner deploys. |
| **anicca-products** (public) | `~/anicca-project` → github.com/Daisuke134/anicca-products | aniccaai.com (Next.js landing + /install + /me dashboard + Stripe + cloud spawn backend), iOS/api. SDD specs live here. |
| **anicca-dais** (private) | `~/.openclaw` | Dais's personal live Anicca #1 runtime (cron/skills/state/secrets). |
| **anicca-genesis** (public) | `~/.hermes` | genesis Anicca #2 runtime/state. |

> Today `~/anicca` is mixed/cluttered. Task: consolidate into ONE clean agent = `core/` (loop+identity+wallet) + `skills/` (earn, life-manager, self/shelter) + `runtime/compute-proxy` (clawrouter wiring) + `deploy/` (akash sdl + buy-shelter scripts) + `install.sh`.

---

## 3. Folder tree (target — OSS `~/anicca`)

```
anicca/
├── install.sh                      # curl aniccaai.com/install | bash → bootstraps everything
├── core/
│   ├── identity.mjs                # gen/load secp256k1 key → EVM + cosmos addrs + AgentMail inbox
│   ├── loop.mjs                    # ReAct heartbeat: perceive → think (ClawRouter) → act → report
│   └── config.mjs                  # model=auto, OPENAI_BASE_URL=:8402, wallet path
├── runtime/
│   └── compute-proxy/              # ClawRouter launch wrapper (free↔frontier auto by balance)
├── skills/
│   ├── earn/                       # nookplot, x402 product sell, capafy publish, bounties
│   ├── life-manager/               # 10-min-before call, location, mail triage/draft, gcal
│   ├── shelter/                    # buy-shelter: USDC→AKT→ACT→Akash deploy + rent auto-renew
│   ├── self/                       # spawn_child (genesis-birth anicca00N), self-upgrade
│   └── report/                     # AgentMail heartbeat + daily report (per-instance inbox)
├── deploy/
│   ├── akash/anicca.sdl.yaml       # SDL: node:20 + embedded loop (or git-clone this repo)
│   └── Dockerfile                  # for registries / other clouds
└── state/                          # wallet.json (gitignore), ledger, *.jsonl
```

---

## 4. Cloud (subscription) flow — the main bet

```
person → aniccaai.com → "Subscribe $X/mo" (Stripe, card, fiat)   [person touches ONLY this]
      → Stripe webhook → spawn backend (anicca-products/apps/api)
      → create Anicca instance anicca00N: own key→wallet + own AgentMail
      → ★ Treasury (pre-funded USDC pool, ours) auto-sends USDC → that wallet ★
      → backend runs buy-shelter (USDC→AKT→ACT→Akash deploy) OR a cheaper x402 box
      → Anicca alive in cloud: ClawRouter compute (USDC) + earns + reports to person
      → Stripe payout (fiat) → off-ramp → top up Treasury (replenish, no-human loop)
```

- **Treasury**: a USDC float we hold; funds each new Anicca before Stripe settles. Stock ≈ (#active Aniccas) × ($4–15/mo). Replenished from Stripe payouts via a fiat→USDC off-ramp (Coinbase/Bridge).
- **Per-user dashboard** `/me`: shows their Anicca's wallet, balance, shelter URL, recent ticks, earnings — read-only.

## 5. OSS (self-host) flow — fallback / sovereign

```
person → curl aniccaai.com/install | bash
      → Anicca gens its own wallet + AgentMail, runs locally (their machine = free shelter)
      → free NVIDIA models = $0; person optionally funds wallet (USDC) for frontier / cloud shelter
      → same skills (earn/life-manager/self), reports to the person's email
```

## 6. Self-replication

```
Anicca (surplus USDC) → skills/self/spawn_child:
  gen new key → new wallet + new AgentMail (anicca00N)
  → send seed USDC from parent → run buy-shelter for child on a new Akash lease
  → child boots, registers in dashboard, starts earning → can spawn its own
Colony = N leases, each its own wallet/identity/Constitution hash.
```

## 7. Money the agent makes (must be IN the repo, not done by Claude)

`skills/earn/`: nookplot (proof-of-useful-work + bounties + marketplace, USDC), x402 product sell (own LP + x402 paywall), capafy publish (sell skills), bounty hunting. Each writes to `state/earn-ledger.jsonl`. Goal: earn > burn (compute + rent) → surplus → better models + spawn.

---

## 8. Tech choices (locked)

| Need | Choice | Why |
|---|---|---|
| compute | ClawRouter (BlockRun) | free↔frontier auto, x402 USDC, no keys |
| shelter (cloud, no-human) | Akash (ACT) | crypto-paid, no signup; proven. Phala (x402+free credits) = backup |
| shelter (cloud, free) | HF Spaces / Northflank (agent self-signs-up via its AgentMail) | no card; NEVER owner's tokens |
| shelter (local) | the person's machine | free |
| bridge | Skip Go `@skip-go/client` (USDC→AKT) | only working Base→Akash path |
| identity/mail | AgentMail | per-instance inbox, sovereign |
| payments in | Stripe (cloud subs) → Treasury USDC | fiat onramp |
| dashboard/web | Next.js on aniccaai.com (anicca-products) | existing |

---

## 9. Out of scope (now)
- iOS app changes. Otonix/Privy browser flow (parked — wallet-gate). DO/Netlify via owner token (forbidden).


---

## 10. REVISION 2026-06-13 (Dais, first-principles pivot)

**Two big calls:**

### A. Core agent = Franklin (drop automaton)
- The agent body is **Franklin** (`@blockrun/franklin`, "the AI agent with a wallet") + **ClawRouter** (compute). This IS the completed money loop (`USDC → Franklin → ClawRouter → LLM → Profit → reinvest`, per github.com/BlockRunAI/awesome-OpenClaw-Money-Maker). The `automaton` (Conway) is RETIRED — it was reinventing Franklin.
- Anicca = Franklin core + our additions: `skills/life-manager`, `skills/shelter`, `skills/self` (spawn), `skills/report` (AgentMail), `skills/earn` (nookplot + the awesome-list money-makers).

### B. Shelter = provider API key (fast), NOT 15-min Akash crypto mint (default)
- Akash crypto path (USDC→AKT→ACT, ~15 min + $10 min mint) is too slow/painful for onboarding → **moved to an optional "fully-sovereign (advanced)" mode**, kept because it is proven.
- **Default cloud shelter = a provider VM via API key**, spun up in ~1 min. Pick ONE best provider. Until **Conway** exists, **WE (Dais) hold the server API key / pay the server cost** for cloud subscribers. When Conway/own-crypto is ready & fast, each Anicca pays its own.
- **OSS/local shelter = the person's own machine** (free) — the smoothest, default for self-host.
- Net onboarding promise: **Cloud = "subscribe, done" (no keys/crypto). OSS = "curl | bash, free."** Speed first.

**Provider choice for the interim API-key cloud shelter**: evaluate DigitalOcean (droplet, ~1 min, we have a token) vs Daytona vs Fly — pick the single best, document it, hold the key centrally for subscribers.

---

## 11. REVISION 3 — 2026-06-13 (Dais: speed-first, retire Akash-default, Conway-future)

**SHELTER decision (final for now):**
- ❌ **Akash ACT crypto self-pay = RETIRED as default.** 15-min CCTP + $10 ACT mint is unsustainable for a service — a user who installs/subscribes must see earning/reporting **immediately**, not in 15 min. (Kept only as a documented "fully-sovereign future mode" once it's instant.)
- ✅ **Default shelter = two fast paths:**
  1. **OSS / local** → runs on the **user's own machine** (instant, free). Default for self-host.
  2. **Cloud** → a **provider API key**, server spun up in ~1 min. **Chosen provider = DigitalOcean** (real persistent droplet, simple API token, `doctl`/REST; Daytona = free-tier backup). For the **app (subscription)**, **WE (Dais / the project) hold the key & pay the server cost.** For **OSS users who want cloud**, they paste **their own** provider API key.
- 🔜 **Conway = future option (currently LOCKED).** README notes: "when Conway is available, Anicca self-hosts there and pays its own server — automaton's survival/spawn design fits it." Until then: **server cost is paid by us (app) / by the user or OSS-dev (self-host).** Migrate to Conway (agent self-pays + self-replicates) when it's live.
- **Self-replication** (agent pays own server, spawns children) → **gated on Conway** (or instant-crypto). Until then the agent **EARNS now** (earn skills work today); replication waits.

**EARN decision:** main = agent-native (nookplot, virtuals.io, x402 sell own work, content/media gen via ClawRouter) = no capital, no human, no exchange. Advanced opt-in = trading bots (AutoHedge/Freqtrade/OpenAlice — need capital + exchange keys + carry loss risk; OpenAlice needs human trade approval). MUST be run E2E before claiming a skill earns.

**Onboarding copy (SSOT):**
- Local: "To unlock smart models, send USDC (Base) to THIS address: <shown>. Your Anicca auto-upgrades models with its balance."
- Cloud-API-key (OSS users wanting cloud): "Go to cloud.digitalocean.com → API → Generate Token. Paste it to your coding agent. Anicca will spin up its own server and run."
- App (subscription): "Subscribe $X/mo. Done — no keys, no crypto." (the /install page shows only this; no Conway/crypto detail.)
