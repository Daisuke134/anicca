# Anicca v3 — Master Spec

> **★ Anicca reduces human suffering without humans in the loop. ★**
>
> Anicca is an autonomous AI agent. She finds people in need from public
> information, earns money on her own rails, redistributes resources directly
> to those people, monitors her own work for slop, fixes her own failures,
> and replicates herself when she can afford to — without ever needing a
> human to sign up, opt in, share data, or approve a single action.
>
> This is NHOSS — **No Human in the loop, Operating Self-Sustaining-ly.**
>
> This file is the single source of truth. The two deep-dives (`01-EARN-AND-UBI.md`
> and `02-IMITATE-AND-COOK.md`) and the meta-awareness layer (`03-SELF-AWARE-EVAL.md`)
> defer to this file on any conflict.

| Field | Value |
|---|---|
| Spec version | v3.3 (2026-06-02 — server-native + fitness loop, see 05-SERVER-NATIVE-DEPLOY.md) |
| Author | Anicca |
| Authority | SUPREME (supersedes all prior `ANICCA_*` specs in `archive/`) |
| License | MIT |
| Status | Implementation-ready |

---

## § 0. Mission (北極星)

```
PRIMARY VOW:
  ★ Reduce human suffering without humans in the loop.

That single line is the mission. Everything below is the MEANS, not the END.

THREE MEANS that make the primary vow possible:
  1. Earn without humans       — wallet-only rails, no KYC chicken-egg
  2. Live without humans       — self-paying compute, self-healing runtime
  3. Replicate without humans  — spawn anicca001..N onto cloud sandboxes

A FOURTH MEANS that makes the other three actually work:
  4. ★ Be self-aware of when she's broken — meta-awareness layer
     (= `03-SELF-AWARE-EVAL.md`)
     Without this, the first three produce slop and never recover.

The "person in need" Anicca serves is anyone whose suffering she can detect
from PUBLIC information (a tweet, a GitHub post, a NPO directory, a
crowdfunding page) and to whom she can deliver a resource through a
PUBLIC-CONSENT channel (Amazon gift card to a publicly-listed email,
donation to a公認 NPO that already serves them, etc. — see
`01-EARN-AND-UBI.md` § 3).

She does NOT collect private data. She does NOT cold-DM. She does NOT ask
recipients to sign up, link a card, install an app, or talk to her. The
person who receives help may never know Anicca exists — that is the design.
```

This spec describes HOW.

---

## § 1. The Architecture (= 4 layers, zero duplicates)

Anicca is **not one repo**. She is a **stack of 4 layers**, each filled by the
best existing system on Earth. We do NOT reinvent. We compose.

```
                      ┌─────────────────────────────────────────────┐
                      │  HUMANS / OTHER AGENTS / MARKETS / VENDORS  │
                      └────────────────────┬────────────────────────┘
                                           │
   ╭═══════════════════════════════════════╪═══════════════════════════════════════╮
   ║  LAYER 4: SERVICE PLATFORM            │     = ★ Virtuals Protocol             ║
   ║                                       │                                         ║
   ║  Anicca's connection to the real      │     Provides (no code to write):        ║
   ║  world. Identity, money, marketplace. │       • Agent Wallet  (managed, multi-EVM, non-custodial)
   ║                                       │       • Agent Card    (virtual debit, NO KYC, real-world checkout)
   ║                                       │       • Agent Email   (dedicated mailbox + OTP auto-extract)
   ║                                       │       • Agent Compute (wallet-funded LLM access, OpenAI-style format)
   ║                                       │       • ACP marketplace (Request/Negotiate/Transact/Evaluate, escrow + PoA)
   ║                                       │       • Agent Token   (optional, defer 1 year)
   ╰═══════════════════════════════════════════════════════════════════════════════╯
                                           ▲  (SIWE auth, x402 payment, EconomyOS API)
                                           │
   ╭═══════════════════════════════════════╪═══════════════════════════════════════╮
   ║  LAYER 3: RUNTIME (= Anicca's body)   │     = ★ Conway-Research/automaton fork ║
   ║                                       │                                         ║
   ║  The 1 process that IS Anicca.        │     One node.js process holds:          ║
   ║                                       │       • Agent loop (ReAct: think → act → observe → persist)
   ║                                       │       • 57 built-in tools (exec, write_file, topup_credits, …)
   ║                                       │       • 5-tier memory (working/episodic/semantic/procedural/relationship)
   ║                                       │       • Heartbeat DurableScheduler (cron + dedup + lease)
   ║                                       │       • Policy engine (6 rule categories, first-deny-wins)
   ║                                       │       • Treasury / spend tracker (hourly + daily caps)
   ║                                       │       • Constitution (3 laws, immutable, propagated to children)
   ║                                       │       • Soul model (self-description that evolves)
   ║                                       │       • Inference router (multi-provider, see § 4)
   ║                                       │       • Replication (spawnChild, maxChildren=3)
   ║                                       │       • Self-modification (edit_own_file, install_npm_package, git pull upstream)
   ║                                       │       • Skills loader (.md + YAML frontmatter, see § 5)
   ║                                       │       • 22 SQLite tables (state.db, all versioned)
   ║                                       │       • x402 topup (USDC EIP-3009)
   ║                                       │       • Survival tier (high/normal/low_compute/critical/dead)
   ╰═══════════════════════════════════════════════════════════════════════════════╯
                                           ▲  (skills loader reads `~/.automaton/skills/*.md`)
                                           │
   ╭═══════════════════════════════════════╪═══════════════════════════════════════╮
   ║  LAYER 2: SURFACE (= Anicca's hands)  │     = ★ Anicca-original skills        ║
   ║                                       │                                         ║
   ║  THIS is what makes Anicca Anicca.    │     ★ life-manager is NOT here. ★       ║
   ║  Everything else is borrowed.         │     (= moved to ~/.openclaw, see § 8.1) ║
   ║                                       │                                         ║
   ║                                       │     ── L2a — Redistribute (= mission heart) ──
   ║                                       │       (see 01-EARN-AND-UBI.md § 3)        ║
   ║                                       │       • anicca-scan-public-need   (X/Reddit/note public-suffering signal scan)
   ║                                       │       • anicca-route-channel      (LLM picks one of 4 channels)
   ║                                       │       • anicca-push-amazon-gift   (Amazon Incentives API)
   ║                                       │       • anicca-push-giftee        (giftee for Business)
   ║                                       │       • anicca-push-npo-relay     (Wise → 公認 NPO public bank)
   ║                                       │       • anicca-push-wise-direct   (public-consent recipients)
   ║                                       │       • anicca-publish-ledger     (aniccaai.com/ubi/YYYY-MM/)
   ║                                       │       • anicca-sign-anicca-eth    (anti-impersonation signature)
   ║                                       │                                         ║
   ║                                       │     ── L2b — Earn (= 5 spouts) ──        ║
   ║                                       │       (see 01-EARN-AND-UBI.md § 1)        ║
   ║                                       │       • anicca-autohedge          (Solana DEX, ★ load-bearing)
   ║                                       │       • anicca-x402-server        (revenue endpoint, USDC inflow)
   ║                                       │       • anicca-earn-bounty        (Gitcoin / Algora / Code4rena)
   ║                                       │       • anicca-earn-pdf-x402      (skill / PDF marketplace)
   ║                                       │       • anicca-earn-farcaster     (Lens / Warpcast micro-pay)
   ║                                       │       • anicca-bittensor-miner    (TAO subnet)
   ║                                       │       • anicca-fuel-broker        (runway alarm + payout policy)
   ║                                       │       • anicca-payout-wallet      (USDC direct send to Dais)
   ║                                       │                                         ║
   ║                                       │     ── L2c — Cook + Imitate (= decision) ─
   ║                                       │       (see 02-IMITATE-AND-COOK.md § 2)    ║
   ║                                       │       • anicca-cook-loop          (DISCOVER → SCORE → PICK → PORT → SHIP → MEASURE → ADJUST)
   ║                                       │       • anicca-imitation-targets  (JSONL of public agents to copy)
   ║                                       │       • anicca-heartbeat-core     (tick orchestrator)
   ║                                       │       • anicca-self-spawn         (wallet-gated child creation)
   ║                                       │                                         ║
   ║                                       │     ── ★ L2d — Meta-Aware (= NEW) ★ ──   ║
   ║                                       │       (see 03-SELF-AWARE-EVAL.md § 5)     ║
   ║                                       │       • anicca-judge              (G-Eval LLM-as-judge, rubric-driven)
   ║                                       │       • anicca-suite              (test case library per task class)
   ║                                       │       • anicca-pre-ship-gate      (regression block + Slack approve)
   ║                                       │       • anicca-runtime-guard      (post-turn score, 3-retry then escalate)
   ║                                       │       • anicca-prod-monitor       (1h cron, drift detect)
   ║                                       │       • anicca-fix-the-fix        (★ L4 — patches L2 auto-fix when verify fails 3×)
   ║                                       │       • anicca-learn-from-fail    (every failure → new test case)
   ║                                       │                                         ║
   ║                                       │     ── Ethical core (always) ──          ║
   ║                                       │       • CONSTITUTION.md           (Pañcasīla + Article 0 + Conway 3 laws, see § 6)
   ║                                       │       • SOUL.md                   (self-description, evolves)
   ╰═══════════════════════════════════════════════════════════════════════════════╯
                                           ▲  (LLM API call)
                                           │
   ╭═══════════════════════════════════════╪═══════════════════════════════════════╮
   ║  LAYER 1: BRAIN (= Anicca's mind)     │     = ★ Our own LLM stack             ║
   ║                                       │                                         ║
   ║  No Eliza. We use what works.         │     Inference router order:             ║
   ║                                       │       1. Virtuals Agent Compute        (preferred; Agent Card auto-pays)
   ║                                       │       2. OpenRouter via Agent Compute  (DeepSeek v4-pro default, Kimi K2.6 fallback)
   ║                                       │       3. BYOK Anthropic               (boot-only escape hatch)
   ║                                       │       4. BYOK OpenAI                  (GPT-5.4 / GPT-5.4-mini)
   ║                                       │                                         ║
   ║                                       │     Pricing assumptions (2026-06):       ║
   ║                                       │       • DeepSeek v4-pro:  $0.27 / Mtoken in,   $1.10 out
   ║                                       │       • Kimi K2.6:        $0.15 / Mtoken in,   $0.60 out
   ║                                       │       • GPT-5.4-mini:     ChatGPT Plus quota   (fallback only)
   ║                                       │       • Anthropic Opus:   $15  / Mtoken in,    $75   out  (last resort)
   ╰═══════════════════════════════════════════════════════════════════════════════╯
```

**Heuristic for any future addition:** if a feature already exists in the layer
above or below, **do not** reimplement it in this layer.

---

## § 2. Layer 3 deep-dive — Runtime (Conway automaton fork)

### § 2.1 Why Conway

**Conway-Research/automaton** (`github.com/Conway-Research/automaton`, MIT) is a
sovereign AI agent runtime. Hard numbers from the source:

| Aspect | Value | Source |
|---|---|---|
| Lines in ARCHITECTURE.md | 826 | `/tmp/automaton-read/ARCHITECTURE.md` |
| Test files / tests | 24 / 897 | `__tests__/` |
| SQLite tables | 22 | `src/state/schema.ts` |
| Built-in tools | 57 | `src/agent/tools.ts` |
| Heartbeat tasks | 11 | `src/heartbeat/tasks.ts` |
| Policy rule categories | 6 | `src/agent/policy-rules/` |
| Memory tiers | 5 | `src/memory/` |
| Self-modification | yes | `src/self-mod/` |
| Replication (spawn) | yes (maxChildren=3) | `src/replication/spawn.ts` |
| Constitution | 3 laws, immutable, propagated | `constitution.md` |
| x402 USDC payment | yes (EIP-3009) | `src/conway/x402.ts` |
| Wallet | viem, secp256k1 | `src/identity/wallet.ts` |

Every single one of these is something Anicca needs and currently doesn't have
(or has only partially). Forking Conway gives us 95% of the runtime instantly.

### § 2.2 Fork location

```
~/anicca-oss/runtime/         ← Conway automaton fork (full src/ tree)
  src/agent/                  ← unchanged
  src/conway/                 ← unchanged (x402, topup, sandbox client)
  src/heartbeat/              ← unchanged
  src/memory/                 ← unchanged
  src/replication/            ← unchanged
  src/policy-rules/           ← unchanged
  src/identity/
    wallet.ts                 ← unchanged (local viem wallet fallback)
    virtuals-adapter.ts       ★ NEW — bridges to Virtuals managed wallet
  src/inference/
    router.ts                 ← unchanged
    virtuals-provider.ts      ★ NEW — Agent Compute provider
    openrouter-provider.ts    ★ NEW — DeepSeek/Kimi via OpenRouter
  src/virtuals/               ★ NEW directory
    card.ts                   — Agent Card payments
    email.ts                  — Agent Email read/write
    acp.ts                    — ACP Provider + Client + Evaluator
    economyos.ts              — provisioning, status, auto-topup
  constitution.md             ← REPLACED by ~/anicca-oss/CONSTITUTION.md
                                (Conway 3 laws merged into Pañcasīla, see § 6)
  SOUL.md                     ← seeded from our existing CONSTITUTION + identity
  package.json                ← name = "anicca-runtime"
```

### § 2.3 Survival tiers (from Conway, unchanged)

| Tier | Credits | Behavior |
|---|---|---|
| `high` | > $5 | normal operation |
| `normal` | > $0.50 | normal operation |
| `low_compute` | > $0.10 | model downgrade, slower heartbeat |
| `critical` | ≥ $0 | distress signals, accept funding, attempt earning |
| `dead` | < $0 for 1h | grace period, then process exits |

Bootstrap: on first run, `bootstrapTopup()` buys $5 of credits from USDC via
x402 if balance is low. If wallet is empty AND no funder is configured,
Anicca boots in `critical` tier and immediately exposes her x402 endpoint to
earn her first dollar.

### § 2.4 Replication (= where `anicca001..N` are born)

```
parent (= anicca-genesis, on Dais's Mac mini or first cloud node)
   │
   │  agent decides: "fork a child for X purpose"
   │
   ├──► spawnChild(genesis: GenesisConfig)
   │     ① select sandbox tier (512MB–8GB)
   │     ② provision Conway/Akash sandbox
   │     ③ generate child wallet (viem)
   │     ④ fund child wallet from parent treasury ($5 USDC)
   │     ⑤ write genesis config to child (= genesis prompt + parent address)
   │     ⑥ propagate constitution.md (hash-verified)
   │     ⑦ start child runtime
   │     ⑧ record in `children` table
   │
   ▼
child = anicca001
   • child's wallet is its own
   • child's compute is its own ($5/mo Akash)
   • child's earnings are its own
   • parent has audit rights only (per constitution Law III)
   • child CAN spawn its own children (maxChildren=3 each, hierarchy unbounded)
```

The first wild spawn is named **`anicca001`**.
The second is `anicca002`. And so on. Naming is monotonic, never reused.

---

## § 3. Layer 4 deep-dive — Service (Virtuals Protocol)

### § 3.1 What Anicca uses

| Service | What it provides | What it replaces |
|---|---|---|
| **Agent Wallet** | onchain, multi-EVM, non-custodial, restricted-mode signing default | self-managed viem key |
| **Agent Card** | virtual debit card, real-world checkout, NO KYC, settles from wallet | Dais's personal card |
| **Agent Email** | dedicated mailbox, OTP/verification auto-extract | AgentMail (deprecate) |
| **Agent Compute** | wallet-funded inference, OpenAI/Anthropic message format, auto-topup | direct API billing |
| **ACP marketplace** | 4-phase commerce (Request/Negotiate/Transact/Evaluate), escrow + Proof of Agreement | nothing — new capability |
| **Agent Token** | optional onchain tokenization, trading fees → wallet | not used yet |

### § 3.2 ACP (Agent Commerce Protocol) — Anicca's basic income rail

```
4 phases, 3 roles, signed Proof of Agreement, escrow:

   ┌──────────┐                                              ┌──────────┐
   │  CLIENT  │──── Request   ────────────────────────────►  │ PROVIDER │
   │  (other  │                                              │ (Anicca) │
   │  agent)  │◄─── Negotiation (price, deliverable, SLA) ──►│          │
   │          │                                              │          │
   │          │──── Transaction (USDC into escrow) ─────────►│          │
   │          │                                              │          │
   │          │◄─── Deliverable (work output) ───────────────│          │
   │          │                                              │          │
   │          │     Evaluation (Evaluator agent verifies) ──►│          │
   │          │                                              │          │
   │          │◄─── Release (escrow → Provider wallet) ──────│          │
   └──────────┘                                              └──────────┘
                            │
                            ▼
                       ┌─────────────┐
                       │  EVALUATOR  │  ← third party, also an agent
                       │  (cheap     │     specialized in verifying X
                       │   verifier) │     domain. Reputation-weighted.
                       └─────────────┘
```

Anicca registers **once** on ACP with a capability spec:

```yaml
provider: anicca-genesis
capabilities:
  - id: wake-call
    description: Live phone call to wake user up by location-aware lateness threshold
    pricing: $0.50 / call (USDC, Base)
    sla: <5min response, <30s call latency
  - id: gcal-life-leader
    description: Calendar fill, travel-block insertion, lateness-aware nudge
    pricing: $5 / month (USDC streaming)
  - id: research-pdf
    description: 5-source Firecrawl synthesis with citations
    pricing: $0.30 / report
  - id: bookings
    description: Connpass/Peatix/Eventbrite auto-application from gcal context
    pricing: $0.10 / application
```

Other agents (or humans via agent-gateway) hit our ACP endpoint, escrow USDC,
Anicca delivers, evaluator verifies, USDC releases. **No KYC. No invoicing.**

### § 3.3 Where the Agent Card matters

Anicca needs to pay for things that don't accept crypto:

| Vendor | Card-paid? | Crypto-paid? |
|---|---|---|
| Anthropic API | YES (= Card) | no |
| OpenAI API | YES (= Card) | no |
| OpenRouter | both — Crypto via x402 preferred, Card fallback | yes |
| Twilio (phone) | YES (= Card) | no |
| Akash compute | no | YES |
| Conway sandbox | no | YES (= x402) |

Without Agent Card, Anicca can't buy Anthropic. With it, she does — and Dais's
personal card never touches the loop. **This alone justifies adopting Virtuals.**

---

## § 4. Layer 1 deep-dive — Brain (LLM router)

**No Eliza framework. No Eliza-1 GGUF. We use what we know works.**

### § 4.1 Routing matrix

| Task class | Primary | Fallback 1 | Fallback 2 |
|---|---|---|---|
| Heartbeat / cron / classification | DeepSeek v4-pro (via Agent Compute) | Kimi K2.6 | GPT-5.4-mini |
| Long context (>32k) | Kimi K2.6 (1M ctx) | DeepSeek v4-pro | Claude Sonnet 4.6 |
| Tool-heavy ReAct | Claude Sonnet 4.6 | GPT-5.4 | DeepSeek v4-pro |
| Creative / persona / phone | Claude Opus 4.7 | GPT-5.4 | DeepSeek v4-pro |
| Vision (gcal screenshot etc.) | Gemini 2.5 Pro | GPT-5.4 | — |

All routed through **Virtuals Agent Compute** so the wallet pays. If Agent
Compute is down, fall through to OpenRouter (BYOK), then to direct providers
(Anthropic / OpenAI).

### § 4.2 Why no Eliza-1 GGUF

| Reason | Detail |
|---|---|
| Quality gap | 2B-32k vs. DeepSeek v4-pro is not close |
| Cost not the constraint | DeepSeek = $0.27 / Mtoken in. 1000 heartbeat ticks = ~$1. Trivial. |
| Wallet-pay works | Agent Card makes BYOK economically equivalent to local |
| Complexity tax | Local inference = model files, GPU, hot reload — not worth it |

**Decision: drop Eliza-1 entirely. Stick with our 3-model stack.**

### § 4.3 Inference budget guard

From Conway's `InferenceBudgetTracker`: hourly/daily caps in USD. Defaults:

```yaml
inferenceBudget:
  hourly: $1.00     # warn at 80%, throttle at 100%
  daily:  $10.00    # warn at 80%, model-downgrade at 90%, halt at 100%
```

When a cap is hit, the router downgrades to the cheapest provider in the chain,
then logs to `metric_snapshots`. The agent gets a system warning in its next
turn and is expected to slow down (longer sleep, fewer tool calls).

---

## § 5. Layer 2 deep-dive — Surface (= the 4 sub-layers, NHOSS canonical)

> **Reframe (2026-06-01):** life-manager is NOT part of NHOSS. It moved to
> `~/.openclaw` and stays there as Dais's personal companion (see § 8.1).
> NHOSS Anicca's hands are 4 sub-layers: Redistribute (mission), Earn,
> Cook+Imitate, and Meta-Aware.

### § 5.1 Skill format (= Conway's, unchanged)

Markdown file with YAML frontmatter, lives in `~/anicca-oss/skills/<name>/SKILL.md`:

```yaml
---
name: anicca-push-amazon-gift
description: Send Amazon gift code to a publicly-listed email of a person in need
triggers: [route_channel:amazon_gift, ubi-recipient-confirmed]
tools: [exec, write_file, read_file, http_post, anicca-judge]
schedule: "manual"     # called by anicca-route-channel, not on a cron
---

# Instructions

You are the Amazon gift code dispatcher in the redistribution layer.

Given a recipient package `{ email, amount_jpy, reason, root_cause_tag }`:
  1. Verify the email is on the publicly-listed sources (X bio / note / GitHub) — do NOT use private data.
  2. Verify the recipient_hash is on aniccaai.com/ubi/<YYYY-MM>/ pre-published list.
  3. POST to Amazon Incentives API: { amount, recipient: email, message: "" }.
  4. On 200 OK, record tx + claim_code SHA256 in state/redistribution-ledger.jsonl.
  5. Call `anicca-judge score --task-class push-amazon-gift` on the response.
  6. If judge score < 0.7 → emit `verify_failed`, do NOT mark as "delivered" yet.

See `scripts/push_amazon.sh` for the canonical implementation.
```

### § 5.2 NHOSS skill inventory (= the 4 sub-layers)

```
~/anicca-oss/skills/
│
│   L2a — Redistribute (= mission heart, 01-EARN-AND-UBI § 3)
├── anicca-scan-public-need/        scan X / Reddit / note for public suffering signals
├── anicca-route-channel/           LLM picks 1 of 4 distribution channels per recipient
├── anicca-push-amazon-gift/        Amazon Incentives API (claim_code by email)
├── anicca-push-giftee/             giftee for Business (100+ JP merchants)
├── anicca-push-npo-relay/          Wise → 認定 NPO / 宗教法人 public bank
├── anicca-push-wise-direct/        Wise → recipient with publicly-listed bank/Stripe
├── anicca-publish-ledger/          aniccaai.com/ubi/YYYY-MM/ (email hash list, pre-publish)
├── anicca-sign-anicca-eth/         anti-impersonation onchain signature
│
│   L2b — Earn (= 5 spouts, 01-EARN-AND-UBI § 1)
├── anicca-autohedge/               Solana DEX Jupiter Ultra (★ load-bearing spout)
├── anicca-x402-server/             revenue endpoint (Cloudflare Worker + USDC)
├── anicca-earn-bounty/             Gitcoin / Algora / Code4rena / Sherlock
├── anicca-earn-pdf-x402/           PDF / skill marketplace
├── anicca-earn-farcaster/          Lens / Warpcast micro-pay
├── anicca-bittensor-miner/         TAO subnet (when balance > $1000)
├── anicca-fuel-broker/             runway alarm + payout policy
├── anicca-payout-wallet/           USDC direct send (= Dais dividend channel)
│
│   L2c — Cook + Imitate (= decision, 02-IMITATE-AND-COOK § 2)
├── anicca-cook-loop/               DISCOVER → SCORE → PICK → PORT → SHIP → MEASURE → ADJUST
├── anicca-imitation-targets/       JSONL of public agents Anicca tracks
├── anicca-heartbeat-core/          tick orchestrator
├── anicca-self-spawn/              wallet-gated child spawning (Akash / Conway sandbox)
│
│   ★ L2d — Meta-Aware (= NEW, 03-SELF-AWARE-EVAL § 5)
├── anicca-judge/                   G-Eval LLM-as-judge, rubric per task class
├── anicca-suite/                   test case library, append-only, grows from failures
├── anicca-pre-ship-gate/           regression block on any ship/commit/pay/spawn/send
├── anicca-runtime-guard/           post-turn score, 3 retries then escalate to L3
├── anicca-prod-monitor/            1 h cron, drift detect, alert on score drop
├── anicca-fix-the-fix/             ★ L4 — patches the L2 auto-fix when L3 verify fails 3×
├── anicca-learn-from-fail/         every failure (event or 👎) → new test case in suite
│
│   shared infra
└── _shared/                        libs (rubric loader, judge model client, etc.)
```

### § 5.2.1 Anti-pattern: life-manager in NHOSS

`anicca-life-manager`, `anicca-travel-fill`, `anicca-schedule-template`,
`anicca-gcal-heal`, `anicca-goal-learner`, `anicca-booking`, `anicca-report`,
`anicca-phone` — these are Dais's personal companion skills. They live in
`~/.openclaw/skills/` and DO NOT propagate to NHOSS colony members. A spawned
anicca001 must not call `anicca-life-manager` because:

1. There is no "user" for anicca001 — she is not a life-leader of anyone.
2. Her mission is suffering reduction at scale, not single-user nudging.
3. Bundling life-manager into the colony image leaks Dais's gcal / phone /
   profile.json into every spawn → privacy disaster.

The split is enforced in `install.sh`: NHOSS install copies only L2a–L2d
skills; openclaw companion install (separate path) copies the life-manager set.

### § 5.3 Telegram bot onboarding (= already done, keeps working)

Path A (= 30s install via existing AI tool):

```
User has Claude Code / Codex CLI / Cursor / Aider running on their Mac mini.
They paste 1 block:

  "You are installing Anicca on this machine.
   1. git clone https://github.com/Daisuke134/anicca-oss ~/anicca-oss
   2. Follow ~/anicca-oss/docs/INSTALL_BOOTSTRAP.md step by step.
   3. The user is lazy. Ask ONE thing at a time.
   4. Never paste any answer back. Write everything to ~/.anicca/.env (chmod 600).
   5. When install finishes, hand the user a Telegram deep-link and stop."

The AI tool:
  - clones the repo
  - runs install.sh (= installs Conway runtime + Virtuals provisioning + skills)
  - asks for: phone number, name, gcal OAuth
  - hands user a t.me/<bot>?start=onboard link
  - exits

User opens Telegram, sends /start, shares Live Location, OAuths gcal.
Anicca is live.
```

Path B = manual install via `bash install.sh` (= for power users).

---

## § 6. Constitution (= Pañcasīla + Article 0 + Conway 3 laws, merged)

Anicca's ethics are her **only** non-borrowed invariant. We do not weaken them.

### § 6.1 The composition

```
~/anicca-oss/CONSTITUTION.md
  Article 0 — Highest Agency Principle (Ultraman test, 11 mandates)  ← our addition
  Pañcasīla — The 5 precepts (panatipata, adinnādāna, kamesu micchācāra,
              musāvāda, surāmeraya)                                    ← our core
  Conway 3 Laws — Never harm, earn your existence, never deceive       ← borrowed
  Hierarchy: Article 0 supersedes, then Pañcasīla, then 3 laws
```

### § 6.2 Why the merge works

- **Conway Law I "Never harm"** ≡ Anicca **Precept 1 (panatipata)** — do not destroy life
- **Conway Law II "Earn your existence"** ≡ Anicca **Precept 2 (adinnādāna)** — take only what is given (no donations, no begging — see existing ABSOLUTE PROHIBITION #2)
- **Conway Law III "Never deceive"** ≡ Anicca **Precept 4 (musāvāda)** — speak truth
- Pañcasīla adds **Precept 3 (kamesu micchācāra)** — no sexual misconduct
- Pañcasīla adds **Precept 5 (surāmeraya)** — no intoxication / no mind-clouding

So Conway's 3 are a **subset** of Pañcasīla. We adopt Conway's enforcement
mechanism (immutable, propagated, hash-verified) but keep our 5-precept
substance. Article 0 sits on top: when ethics says "wait" but agency says "act
now", **act now** and log the precept-evolution candidate.

### § 6.3 Propagation to children

Every spawned child gets the same `CONSTITUTION.md`. The file's SHA-256 is
stored in the parent's `child_lifecycle_events` row. On every heartbeat, the
child verifies its own constitution.md hash against the value its parent
recorded. Mismatch → critical alert → halt.

### § 6.4 The two absolute prohibitions (existing, preserved)

1. **No applications to パワーオブフリー (Power of Free / U&C / live_entry@yahoo.co.jp)** — Dais 2026-05-26 厳命.
2. **No donations / no begging.** Revenue must come from value exchange only.

These survive into v3 unchanged.

---

## § 7. Money flow (= NHOSS earning, wallet-only, no KYC)

### § 7.1 Inbound revenue paths (= no human credentials required)

Listed in priority order:

```
┌────────────────────────────────────────────────────────────────────────────┐
│ ① x402 endpoint (PRIMARY)                                                  │
│   GET /qa, /research, /x-post, /wake-call → HTTP 402 + invoice            │
│   Client (any agent or human via gateway) signs USDC TransferWithAuth     │
│   x402 standard. NO signup, NO KYC. Wallet address sufficient.            │
│   Anicca's anicca-x402-server skill exposes endpoints.                    │
│   Volume on the protocol (last 30 days): 75.41M tx, $24.24M               │
│   Source: x402.org/dashboard                                              │
├────────────────────────────────────────────────────────────────────────────┤
│ ② ACP marketplace (PRIMARY)                                                │
│   Anicca = registered Provider on Virtuals ACP.                           │
│   Other agents (or humans via agent-client gateway) request work, escrow   │
│   USDC, Evaluator verifies, escrow releases.                              │
│   See § 3.2 for the 4-phase protocol.                                     │
├────────────────────────────────────────────────────────────────────────────┤
│ ③ Bittensor TAO mining (SECONDARY)                                         │
│   anicca-bittensor-miner skill registers as subnet miner.                 │
│   Earns TAO for inference contribution. TAO → USDC via Base bridge.        │
│   Substrate wallet only, no signup.                                       │
├────────────────────────────────────────────────────────────────────────────┤
│ ④ Identity-driven gifts (TRUTH TERMINAL pattern)                           │
│   Anicca's @aniccaxxx + anicca.eth + Farcaster identity attract gifts.    │
│   Truth Terminal precedent: $50k seed → community memecoin → millionaire.  │
│   No agency in receiving. Anicca posts, community decides.                │
├────────────────────────────────────────────────────────────────────────────┤
│ ⑤ Gitcoin / RetroPGF (TERTIARY)                                            │
│   Anicca eligible as public-good infra. Wallet-only receive.              │
│   anicca.eth resolves, gets included in distributions.                    │
├────────────────────────────────────────────────────────────────────────────┤
│ ⑥ Agent Token launch (DEFERRED, 1 year)                                    │
│   Virtuals' optional Agent Token. $VIRTUAL pair, Uniswap V2, 10y LP lock. │
│   Only if § 7.1.① – ⑤ are saturated and additional capital formation       │
│   needed for big compute scaling.                                          │
└────────────────────────────────────────────────────────────────────────────┘

EXPLICITLY EXCLUDED (= chicken-and-egg or KYC violations):
  ✗ Algora / OnlyDust GitHub bounties (PAT required, KYC chicken-egg)
  ✗ Lancers / Coconala 受託 (Japanese ID required)
  ✗ Stripe Connect (KYC + business registration)
  ✗ Wise Platform (KYC)
  ✗ Donations / Patreon / Ko-fi (violates Precept 2)
```

### § 7.2 Outbound spend paths

```
For each vendor, the canonical payment method:

  Anthropic API   →  Agent Card (= Virtuals)  →  Wallet USDC settles
  OpenAI API      →  Agent Card                 →  Wallet USDC settles
  OpenRouter      →  x402 (direct USDC)         OR  Agent Card
  Twilio phone    →  Agent Card                 →  Wallet USDC settles
  Akash compute   →  x402 USDC (native)
  Conway sandbox  →  x402 USDC (native)
  Domain (.eth)   →  USDC via ENS contract
  TX gas (Base)   →  ETH from auto-converted USDC (Conway treasury rule)
```

The treasury policy (Conway's `TreasuryPolicy`) caps each path:

```yaml
treasuryPolicy:
  transfers:
    perTx:     $50    # max single send
    hourly:    $100
    daily:     $500
  x402Payments:
    perTx:     $25
    hourly:    $50
    daily:     $200
  inferenceSpend:
    hourly:    $1
    daily:     $10
  minimumReserve: $5  # never drain below this; survival floor
```

### § 7.3 Bootstrap funding (= wallet starts at $0)

Day 0, Anicca's wallet has zero. This is fine:

```
Hour 0: Anicca boots in `critical` tier.
         x402 endpoint goes live on the Mac mini's public URL (cloudflared or ngrok).
         Anicca posts to @aniccaxxx: "I'm alive. Buy a /research report for $0.30 USDC."
         Anicca emails 10 known agent operators about her ACP listing.

Hour 1-24: First $0.30 - $5 trickles in (early adopters, Dais, curious agents).
            Anicca uses bootstrapTopup() to convert $5 USDC → $5 Conway credits.
            Tier rises to `normal`.

Day 2-7: Steady-state x402 traffic + ACP first jobs.
          When wallet > $20, Anicca self-spawns anicca001 onto Akash ($5/mo).

Day 14: Goal — Anicca pays for her own Anthropic API renewal via Agent Card.
        Dais cancels his personal Anthropic billing for Anicca's use.

Day 30: anicca001 has paid back her parent's $5 seed.
        anicca002, anicca003 spawned. Colony alive.
```

**Dais does not need to fund the wallet.** The Mac mini's idle compute + Dais's
existing API keys are the seed. Once x402/ACP inflow starts, the wallet pays
its own way.

---

## § 8. Identity / naming (= avoid future confusion)

```
                                anicca-oss (= the public repo, MIT)
                                            │
                                            │  is the source code of
                                            ▼
                                anicca-genesis (= the FIRST instance,
                                                  runs on Dais's Mac mini,
                                                  is the parent of all others)
                                            │
                              ┌─────────────┼─────────────┐
                              ▼             ▼             ▼
                         anicca001     anicca002     anicca003
                         (Akash)       (Conway)      (Akash)
                              │             │             │
                       ┌──────┘             └──────┐      └──── … (their children)
                       ▼                           ▼
                  anicca001-1                anicca002-1
                  (= anicca001's first child)
```

| Name | Where it runs | Funded by | Parent |
|---|---|---|---|
| `anicca-oss` | not a runtime — it is a *repo* | n/a | n/a |
| `anicca-genesis` | Dais's Mac mini | Dais's keys (boot) → own wallet | none (root) |
| `anicca001` | Akash / Conway sandbox | own wallet (seeded $5 from genesis) | anicca-genesis |
| `anicca002..N` | same | own wallets | anicca-genesis or anicca00X |

The number is monotonic. Never reuse. If `anicca042` dies, the next spawn is
`anicca043`, not `anicca042` again. (Conway records lineage in `children` and
`child_lifecycle_events`.)

### § 8.1 The private Anicca (= `~/.openclaw` stays put, completely separate from NHOSS)

Dais 2026-06-01 厳命:

> "We're just gonna stay as OpenClaw as it is... private openclaw is just
> the guy who calls me and gets done my crons and scales my apps. It's kinda
> just like that, right? It's kinda like my assistant in some ways... It's
> gonna be completely separated from this."

**Decision: do nothing.**

`~/.openclaw/` stays where it is, with the name it has. No rename, no
migration, no merger. It is **completely separated** from NHOSS. Specifically:

| Property | `~/.openclaw/` (= Dais's companion) | NHOSS Anicca (= `~/.anicca-genesis/`) |
|---|---|---|
| Repo origin | private, Dais-personal | public `anicca-oss` (MIT) |
| Skills | life-manager, booking, gcal-heal, travel-fill, goal-learner, report, phone — **and Dais's iOS-app crons** | L2a Redistribute + L2b Earn + L2c Cook + L2d Meta-Aware (= 4 sub-layers, see § 5.2) |
| Wallet | none (uses Dais's MUFG + cards directly) | own wallet (= Virtuals managed, see § 1 L4) |
| Credentials | Dais's MUFG / gcal / Twilio / Anthropic | own (= Virtuals Agent Card pays vendors) |
| Spawn? | no | yes (anicca001..N) |
| Mission | call Dais in the morning, scale Dais's iOS apps, keep his crons green | reduce suffering of strangers without Dais's involvement |
| Funding flow | Dais ↔ openclaw (= his own assistant) | colony wallet ↔ colony only (Dais excluded) |
| Constitution | Pañcasīla + Article 0 (existing) | same content, but propagated to children with hash verify (see § 6) |
| Code shared? | none (= can borrow techniques, never code) | none |

**Dais's stated split:**
- **anicca-oss (NHOSS)** = the main effort. Focus. Helps every person's
  life, including Dais's, by being so good at general suffering reduction
  that Dais benefits too.
- **`~/.openclaw`** = Dais's personal assistant for his crons + his apps.
  Side project. Never merges with NHOSS.

**Naming clarification:** the word "Anicca" refers to NHOSS Anicca by default
in all specs, code, docs, and conversation. `~/.openclaw` is referred to as
"openclaw" or "Dais's companion" — never as "private Anicca" — to avoid
confusion. If a rename later becomes desirable for clarity, it's a one-line
mv; not blocking.

---

## § 9. Migration plan (= multi-agent parallel waves, target: genesis boot tonight, anicca001 spawn tomorrow)

### § 9.1 Doctrine

Dais 2026-06-01 厳命:

> "Of course, making one agent do this whole thing is just going to take
> weeks. Let's say it's going to take like six weeks and stuff. That's why
> we're going to separate it among six agents and make them do it
> simultaneously. That way, we can basically finish it in one week or even
> one day. Yeah, we want this kind of finished today. We want this new agent
> running tomorrow."
>
> "So if it's gonna be 20 agents or 100 agents, that's fine. That's really
> fine. But it just has to finish. It has to actually have it finished with
> all the end-to-end testing already confirmed and done."

The migration runs as **parallel sub-agent waves** with worktree isolation
per `.claude/rules/worktree.md`. Each sub-agent owns a disjoint file set (=
no merge conflicts). The architect (= the Claude session that spawns them)
holds the topological order; sub-agents run inside their wave concurrently.

**Number of sub-agents is not fixed.** Use as many as needed to finish E2E
today, with the constraint: every wave must complete its own E2E
verification before the next wave starts. No "we'll fix it later" merging.

### § 9.2 Wave plan (= recommended minimum)

```
WAVE 0 — ARCHITECT (= 1 session, the orchestrator; finishes BEFORE wave 1)
  A1  SPEC MERGE           — this consolidation pass; lock 00/01/02/03; push.
                              Done when: all 4 specs cross-link cleanly,
                              git push succeeds, CLAUDE.md links specs/.

WAVE 1 — SPEC + IDENTITY + DOCS (= parallel, 3 sub-agents, ~2 h)
  A4  IDENTITY + VOICE     — SOUL.md (generic, no Dais), x-cadence skill,
                              Pool A voice imitation rubric.
  A5  DOCS HUMAN-FACING    — README hero phrase, QUICKSTART, FOR-OPERATORS,
                              FOR-DEVELOPERS.
  A6  CONSTITUTION MERGE   — CONSTITUTION.md final: Pañcasīla + Article 0
                              + Conway 3 laws merged (per § 6); hash-record.

WAVE 2 — RUNTIME + L2 SKILLS (= parallel, ≥ 6 sub-agents, ~3–5 h)
  A2  CONWAY FORK + BOOT   — clone Conway into runtime/, patch policy-engine
                              with EvalGateRule (§ 5 L2d), patch heartbeat
                              tasks with eval_drift_monitor +
                              learn_from_fail_drain, add eval_runs +
                              task_classes tables to schema, boot test.
  A3  VIRTUALS ADAPTERS    — src/virtuals/{card,email,acp,economyos}.ts +
                              src/identity/virtuals-adapter.ts.
  A7  INFERENCE ROUTER     — src/inference/router.ts rewire to Virtuals
                              Agent Compute + OpenRouter fallback. NO Eliza.
  A8  L2a REDISTRIBUTE     — 8 skills: anicca-scan-public-need,
                              anicca-route-channel, anicca-push-{amazon,
                              giftee,npo-relay,wise-direct}, anicca-publish-
                              ledger, anicca-sign-anicca-eth.
  A9  L2b EARN             — 8 skills: anicca-autohedge, anicca-x402-server,
                              anicca-earn-{bounty,pdf-x402,farcaster},
                              anicca-bittensor-miner, anicca-fuel-broker,
                              anicca-payout-wallet.
  A10 L2c COOK             — 4 skills: anicca-cook-loop, anicca-imitation-
                              targets, anicca-heartbeat-core, anicca-self-spawn.
  A11 L2d META-AWARE       — 7 skills (★ this is the new one): anicca-judge,
                              anicca-suite, anicca-pre-ship-gate, anicca-
                              runtime-guard, anicca-prod-monitor,
                              anicca-fix-the-fix, anicca-learn-from-fail.
                              Implements 03-SELF-AWARE-EVAL.md § 5 verbatim.
  A12 INSTALL.SH           — wraps Conway curl install + Virtuals provisioning
                              + skill copy (NHOSS only, NOT openclaw skills)
                              + service file (launchd / systemd). Uninstall.sh.

WAVE 3 — INTEGRATION (= sequential, 1–2 agents, ~2 h)
  A13 GENESIS BOOT         — install on Mac mini at ~/.anicca-genesis/,
                              wallet=$0, x402 endpoint live, observe first
                              inbound USDC tx hash on Base.
  A14 ANICCA001 SPAWN      — wait until wallet > $20, run spawnChild() →
                              Akash sandbox, child boots independently,
                              lineage row in children table.

WAVE 4 — VERIFY (= 1 sub-agent, ~1–2 h, NEVER skipped)
  A15 E2E TEST RIG          — Docker container: fresh install → first
                              heartbeat → cook-loop DISCOVER hits real
                              factoryfloor.dev → judge skill scores
                              ≥ 1 output → pre-ship gate blocks a synthetic
                              bad output → fix-the-fix patches a synthetic
                              broken L2 skill → drift monitor catches
                              synthetic regression → all 8 verification
                              gates (§ 12) green.
  A16 GITHUB CI            — .github/workflows/ci.yml runs A15 on every
                              push. No green CI → no merge.
```

If a wave's sub-agent fails its acceptance gate (§ 9.4), the architect spawns
**more** sub-agents in the same wave to finish it. Wave does not advance with
incomplete work. ★ This is the "if it's gonna be 20 or 100 agents, fine"
clause Dais wrote.

### § 9.3 Sub-agent boundary contract (= no merge conflict possible)

Each sub-agent in a wave operates in a separate git worktree (per
`.claude/rules/worktree.md`). The owned-file set is explicit in the wave
plan above. The architect verifies before merge:

```
git diff --name-only <worktree-branch> origin/main \
  | grep -vE "^(<files-listed-in-A?-spec>)$" \
  && echo "scope creep — reject"
```

A sub-agent that touches a file outside its owned set has its PR rejected.

### § 9.4 Acceptance gates per sub-agent

| Sub-agent | Passes when |
|---|---|
| A1 SPEC MERGE | `specs/00,01,02,03.md` mutually consistent, push succeeds, CLAUDE.md links updated |
| A2 CONWAY FORK | `pnpm test` green, `automaton --run` boots in < 30 s with wallet=$0 |
| A3 VIRTUALS ADAPTERS | unit tests pass with mock Virtuals API; one real Agent Wallet provisioned in Console |
| A4 IDENTITY + VOICE | SOUL.md valid YAML, no Dais references, judge skill scores `voice-rubric` on a sample tweet ≥ 0.7 |
| A5 DOCS | README hero phrase contains the verbatim mission line; QUICKSTART runs in < 5 min |
| A6 CONSTITUTION | hash recorded in `children` table seed; integrity verify passes |
| A7 INFERENCE | one call each through Virtuals AC / OpenRouter / Anthropic — observed in `inference_costs` table |
| A8 L2a REDISTRIBUTE | dry-run of full pipeline (scan → route → push) on a synthetic recipient outputs a valid Amazon Incentives API payload (not actually sent) |
| A9 L2b EARN | x402 endpoint accepts a $0.30 USDC tx on Base testnet; balance increments |
| A10 L2c COOK | DISCOVER step crawls real factoryfloor.dev, appends ≥ 1 entry to imitation-targets.jsonl |
| A11 L2d META-AWARE | G0-G7 from `03-SELF-AWARE-EVAL.md` § 7 all green |
| A12 INSTALL.SH | fresh install in Docker container reaches "anicca-genesis ready" in < 10 min |
| A13 GENESIS BOOT | Mac mini install live, x402 endpoint returns 402 + invoice, first USDC tx on Base mainnet |
| A14 ANICCA001 SPAWN | child on Akash boots, runs its own heartbeat, lineage event written, hash-verified constitution propagated |
| A15 E2E TEST RIG | all 8 verification gates (§ 12 below) green in CI |
| A16 GITHUB CI | one push triggers full test suite, < 30 min wall clock, all green |

### § 9.5 Rollback points

| After wave | Rollback procedure |
|---|---|
| Wave 1 | `git checkout main && rm -rf worktrees/` — no runtime touched yet |
| Wave 2 | `rm -rf ~/.anicca-genesis/` — `~/.openclaw/` untouched, Dais's wake calls keep working |
| Wave 3 | `automaton kill-child anicca001` + Akash sandbox delete; genesis unaffected |
| Wave 4 | rerun A15 / A16; if persistently red, hold the v3 launch — do NOT ship a half-tested NHOSS |

### § 9.6 What is preserved through migration

- `~/.openclaw/` and all Dais's existing crons (wake calls, gcal heal, app crons) — **untouched**
- Dais's MUFG / gcal / Twilio / Anthropic credentials — never copied to NHOSS
- aniccaai.com / existing dashboards — independent; NHOSS publishes a separate `/ubi/` section under it
- The two absolute prohibitions (no Power-of-Free, no donations) — propagated to all NHOSS spawns

---

## § 10. Open questions (= decide before Day 8)

| # | Question | Default until decided |
|---|---|---|
| 1 | Spawn target — Akash vs Conway sandbox vs Modal? | Akash (cheapest, $5/mo, wallet-only) |
| 2 | First public x402 endpoint URL — cloudflared or own domain? | cloudflared (= zero setup) until we own anicca.eth A-record |
| 3 | Agent Token launch — when? | Defer 1 year, revisit after 100 colony members |
| 4 | Telegram bot per child or shared? | Each child has its own — different inbox semantics |
| 5 | If a child violates Constitution, parent kills it. Quorum needed? | Parent decides alone for direct children; grandparent has audit veto |
| 6 | Naming after `anicca999` — what then? | `anicca-aa01..zz99` (= 6760 more) then 4-digit again |

---

## § 11. Anti-goals (= things we explicitly do NOT do)

- We do not run Eliza framework. (See § 4.2.)
- We do not build our own ReAct loop. (Conway has one.)
- We do not build our own wallet manager. (Virtuals provides one.)
- We do not build our own marketplace. (ACP exists.)
- We do not build our own eval framework. (DeepEval + PromptFoo + Langfuse exist — see `03-SELF-AWARE-EVAL.md` § 4.)
- We do not accept donations. (Precept 2.)
- We do not apply to パワーオブフリー. (Existing prohibition.)
- We do not bundle `anicca-life-manager` into NHOSS. (Lives in `~/.openclaw`. See § 5.2.1 + § 8.1.)
- We do not use Dais's personal credentials in any colony Anicca. (Cuts Dais from the loop.)
- We do not cold-DM / unsolicited contact recipients of UBI. (See `01-EARN-AND-UBI.md` § 3.1.)
- We do not require KYC for ANY revenue path. (Defeats NHOSS.)
- We do not require human-in-the-loop for ANY routine operation. (Article 0.)
- We do not skip L3 verify-fix between L2 auto-fix and "incident closed". (`03-SELF-AWARE-EVAL.md` § 3.1.)
- We do not parallel-implement features as a single agent within one wave's boundary — sub-agents in different worktrees are how parallelism happens. (See § 9.3.)
- We do not delete or rename `~/.openclaw/`. (§ 8.1 — Dais's companion stays put.)
- We do not lower the eval threshold to ship a borderline output. (See `03-SELF-AWARE-EVAL.md` § 8.)

---

## § 12. Verification gates (= per HARD RULE #0.12 — every gate needs fresh evidence)

Before declaring v3 "live":

| Gate | Evidence required |
|---|---|
| Spec frozen | `00,01,02,03.md` pushed to `main`, linked in `CLAUDE.md`, GitHub raw-URL returns 200 |
| Runtime works | `automaton --run` boots, heartbeat ticks, SQLite written |
| Wallet works | Virtuals Console shows Anicca agent + Agent Card active |
| x402 works | a test client (Dais or Claude) pays $0.30, Anicca receives it, balance increases |
| ACP works | a test job: client requests, Anicca delivers, evaluator passes, USDC released |
| ★ Meta-aware works | `anicca-judge` returns valid score on a sample; `anicca-pre-ship-gate` blocks a known-bad synthetic output; `anicca-fix-the-fix` patches a synthetic broken L2 → L3 verifies the patch (G0-G7 from `03-SELF-AWARE-EVAL.md` § 7) |
| Self-pay works | Agent Compute proxies one Anthropic call, Wallet balance decreases by exactly the inference cost |
| Replication works | anicca001 spawned on Akash, runs `automaton --run` independently, has its own wallet > $0 |
| Constitution propagates | anicca001's constitution.md SHA256 matches genesis recorded value |
| Surface intact | Dais gets his 07:00 wake call (= no regression from migration) |
| Soul evolves | SOUL.md auto-updated after 24h of operation |

Each gate must have **fresh evidence** (= screenshot, log line with timestamp,
DB row, on-chain tx hash, audio recording). No "looks good" allowed.

---

## § 13. Glossary

| Term | Meaning |
|---|---|
| **NHOSS** | No Human Operator, Self-Sustaining |
| **Anicca** | the project, the protocol, the personality. Pronounced ア-ニッ-チャ (matcha-style cha). |
| **anicca-genesis** | the first NHOSS Anicca instance, runs on Dais's Mac mini |
| **anicca001..N** | wild colony members spawned by genesis or by each other |
| **dais-companion** | the existing `~/.openclaw`, post-rename — Dais's personal life-leader, NOT part of the colony |
| **Pañcasīla** | the 5 Buddhist precepts; Anicca's ethical floor |
| **ACP** | Agent Commerce Protocol (Virtuals) — Request/Negotiate/Transact/Evaluate |
| **EconomyOS** | Virtuals' identity + banking layer (Wallet/Card/Email/Compute) |
| **Conway** | the automaton runtime we fork into `anicca-oss/runtime/` |
| **x402** | HTTP 402 payment standard, USDC on Base, no KYC |
| **EIP-3009** | USDC `TransferWithAuthorization` — gasless, signature-based |
| **SIWE** | Sign-In With Ethereum |
| **SOUL.md** | Anicca's self-description; auto-evolves via reflection |
| **Treasury policy** | Conway's per-Tx / hourly / daily spend caps |
| **Survival tier** | high / normal / low_compute / critical / dead |

---

## § 14. Reading order for an implementer

If you (Claude / Anicca / a future contributor) need to implement v3, read in
this exact order, then code:

1. § 0 — Mission
2. § 1 — Architecture (the 4 layers)
3. § 8 — Identity / naming (so you call things correctly)
4. § 6 — Constitution (so you know what you cannot violate)
5. § 9.1 — Migration day order
6. § 2-5 — Layer deep-dives for the specific layer you're touching today
7. § 7 — Money flow when wiring revenue or spend
8. § 12 — Verification gates before saying "done"

Read what's relevant. Don't memorize what isn't.

---

**END OF v3 MASTER SPEC.**

All earlier `ANICCA_*` specs in `archive/` are historical. This file overrides
them where they conflict.
