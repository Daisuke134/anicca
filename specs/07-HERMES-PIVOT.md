# 07 — HERMES PIVOT

> Deep-dive on the v3.1 substrate decision: Layer 3 RUNTIME swaps from Conway
> automaton fork to **Hermes Agent** (NousResearch, MIT); Layer 4 SERVICE swaps
> from "Virtuals Protocol everything" to **Coinbase AgentKit CDP Smart Wallet**
> (Virtuals deferred until code-level verification); cloud spawn primary becomes
> **Daytona** (AGPL-3.0 self-host); brain primary becomes **Kimi K2.6** (Moonshot).
>
> All decisions below were verified by reading source code (file:line cited).
> Marketing-only claims were flagged and rejected.
>
> This spec supersedes Conway-specific paragraphs in `00-MASTER.md` § 1, § 2,
> § 3, § 4, § 9. The corresponding old content was moved to:
>
> - `archive/CONWAY_RUNTIME_DEEPDIVE.md` (= old § 2)
> - `archive/VIRTUALS_PROTOCOL_PLAN.md` (= old § 3)
>
> When this file conflicts with `00-MASTER.md`, this file wins for L3/L4/spawn;
> `00-MASTER.md` wins for mission, constitution, naming, money policy.

| Field | Value |
|---|---|
| Spec version | v1.0 (2026-06-02) |
| Author | Anicca / architect |
| Authority | Deep-dive (supersedes Conway sections of 00-MASTER) |
| Status | Implementation-ready (= ready to invoke `superpowers:writing-plans`) |
| Cross-ref | `00-MASTER.md` mission/constitution/money; `01-EARN-AND-UBI.md` spouts; `02-IMITATE-AND-COOK.md` cook loop; `03-SELF-AWARE-EVAL.md` self-eval/fix-the-fix; `05-SERVER-NATIVE-DEPLOY.md` ★ owns hosting/deployment modes; `06-PROJECT-TRACKING-HEARTBEAT.md` heartbeat redesign |
| Conflicts to reconcile | `05-SERVER-NATIVE-DEPLOY.md` § 1 / § 2 currently references **Conway runtime** (`git clone Conway-Research/automaton`). After this spec is approved, 05 must be patched to use the **Hermes** container image as substrate (3-mode story preserved). |

---

## § 0. Why this spec exists

`00-MASTER.md` v3.0 (2026-06-01) committed Anicca to:

- L3 RUNTIME = Conway-Research/automaton fork
- L4 SERVICE = Virtuals Protocol (Wallet/Card/Email/Compute/ACP)
- spawn primary = Akash
- brain primary = DeepSeek v4-pro

On 2026-06-02, deep source-code investigation (4 parallel Explore agents,
file:line cited) discovered three load-bearing assumptions were false or
under-verified:

| Old assumption | What we found |
|---|---|
| Conway is the best autonomous runtime substrate | Hermes Agent has /goal + judge + Kanban v1 ACID + skill self-edit + FTS5 + 20 messaging adapters + Kimi K2.6 native + Bitwarden Secrets; Conway has wallet+x402+Constitution+spawn but lacks all of the above. Hermes is mostly maintained by Nous Research (commits 2026-06-02). |
| Virtuals Protocol is a real, code-verifiable Layer 4 | No public GitHub repo found for Virtuals SDK / Agent Wallet / ACP. Marketing-only at the time of this writing. Cannot commit Anicca's wallet + money to a vaporware substrate. |
| Akash is the cheapest no-KYC spawn target | Daytona is AGPL-3.0, self-hostable for $0, API-token-only, supports daemons, and has clean TS/Python/Go SDK. Akash still works but requires AKT (Cosmos) which needs USDC→AKT bridge — more friction than Daytona for primary path. |
| DeepSeek v4-pro is the primary brain | Kimi K2.6 has native Hermes routing (`run_agent.py:4320-4337`), 1M ctx, Dais already paid for it, comparable cost. DeepSeek demoted to fallback. |

This file re-pins the stack to verified-only substrates.

---

## § 1. The verified stack (post-pivot)

```
═══════════════════════════════════════════════════════════════════════════
                                  ▲
                       WORLD ─────┘
                       (humans / other agents / NPOs / markets / recipients)
                                  │
                                  │ USDC IN / UBI OUT
                                  ▼
   ╔════════════════════════════════════════════════════════════════════════╗
   ║  L4 SERVICE  =  Coinbase AgentKit (CDP Smart Wallet Provider, MIT)     ║
   ║                                                                          ║
   ║  • cdpSmartWalletProvider.ts:98-165                                      ║
   ║    cdp.evm.createAccount() + createSmartAccount()                        ║
   ║    → KYC-zero ERC-4337 smart wallet                                      ║
   ║    → 1 CDP account (Dais 1 回 signup) → N smart wallets (per profile)    ║
   ║  • erc20ActionProvider.ts:82-137 transfer() (USDC built-in)              ║
   ║  • signTypedData() (cdpSmartWalletProvider.ts:215-224)                   ║
   ║    → EIP-712 / EIP-3009 TransferWithAuthorization の基盤                  ║
   ║  • x402ActionProvider.ts:86-174 service discovery + @x402/fetch          ║
   ║  • USDC Base contract: 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913        ║
   ║                                                                          ║
   ║  Cloud spawn:                                                            ║
   ║    primary  = Daytona  (AGPL-3.0 self-host = $0、API token、KYC zero)   ║
   ║    fallback = Akash    (USDC→AKT via Cosmos IBC、wallet only)            ║
   ║                                                                          ║
   ║  Token launcher (defer 1y, optional):                                    ║
   ║    Clanker on Base (10y LP lock、UI でも launchable な ERC-20 標準)      ║
   ║                                                                          ║
   ║  Virtuals Protocol:                                                      ║
   ║    DEFERRED — public GitHub なし。Console 実在 / API spec が公開された    ║
   ║    時点で再評価。当面は採用しない (= 仮定で wallet/money 預けない)。      ║
   ╚════════════════════════════════════════════════════════════════════════╝
                                  ▲
                                  │ SIWE / EIP-712 / x402 HTTP 402 / RPC
                                  │
   ╔════════════════════════════════════════════════════════════════════════╗
   ║  L3 RUNTIME  =  Hermes Agent (NousResearch/hermes-agent, MIT)          ║
   ║                                                                          ║
   ║  • daemon (60s poll, never cron-die)                                    ║
   ║  • N profiles per daemon (anicca-genesis / 001 / 002 / fixer / dais-c)  ║
   ║  • Kanban v1 ACID claim_task() / heartbeat_claim() / reclaim_task()     ║
   ║    (kanban_db.py:2915 / :3104 / :3273)                                  ║
   ║  • /goal + judge model autonomous loop (goals.py:47-92, DEFAULT_MAX=20) ║
   ║  • skill_manager_tool.py:1-34 + :533 _edit_skill() / _create_skill()    ║
   ║    → after-action review が ~/.hermes/skills/learned/*.md を吐く        ║
   ║  • FTS5 session search (hermes_state.py:453-458)                        ║
   ║  • 20 messaging adapters (plugins/platforms/*/adapter.py)                ║
   ║    Telegram / Discord / Slack / WhatsApp / Signal / Matrix / SMS / Email║
   ║  • Bitwarden Secrets vault wiring (hermes secrets bitwarden setup)      ║
   ║  • Kimi K2.6 native (run_agent.py:4320-4337 + trajectory_compressor.py: ║
   ║    86 tokenizer = moonshotai/Kimi-K2-Thinking)                          ║
   ║                                                                          ║
   ║  ✗ Hermes は持たない (= L2 で実装):                                       ║
   ║    - wallet / x402 / treasury policy                                    ║
   ║    - Constitution.md immutable hash propagation                         ║
   ║    - cloud child spawn (local subprocess のみ内蔵)                       ║
   ║    - 5-tier memory (working + 外部 plugin 1 個)                          ║
   ╚════════════════════════════════════════════════════════════════════════╝
                                  ▲
                                  │ loads ~/.hermes/skills/*/SKILL.md
                                  │
   ╔════════════════════════════════════════════════════════════════════════╗
   ║  L2 SURFACE  =  Anicca-original skills (= ここだけが Anicca らしさ)      ║
   ║                                                                          ║
   ║  MONEY IN (5 spouts per spec 01 + ACP):                                  ║
   ║    anicca-wallet-x402         ★ L2 で Conway x402.ts:1-80 を Python+    ║
   ║                                 viem で port (EIP-3009 自前実装)         ║
   ║    anicca-autohedge           AutoHedge clone (spec 01 § 1.1)            ║
   ║    anicca-bittensor-miner     TAO subnet miner (wallet only)             ║
   ║    anicca-earn-bounty         Algora / OnlyDust PR (existing live)       ║
   ║    anicca-earn-farcaster      micro-tip / mini-app                       ║
   ║    anicca-acp-provider        ★Virtuals 採用時のみ enable (defer)        ║
   ║                                                                          ║
   ║  MONEY OUT (UBI + dividend per spec 01 § 3):                             ║
   ║    anicca-payout-wallet       AgentKit erc20ActionProvider 経由 USDC send║
   ║    anicca-payout-wise         Wise API 法人 → 個人 JPY                   ║
   ║    anicca-payout-stripe       Stripe Connect (法人 KYC 完了後)            ║
   ║    anicca-ubi-router          LLM が 4 channel 選択                       ║
   ║    anicca-ubi-amazon          Amazon Incentives API gift code            ║
   ║    anicca-ubi-giftee          giftee for Business                        ║
   ║    anicca-ubi-npo             認定NPO 公開振込先                          ║
   ║    anicca-ubi-temple          宗教法人 寄付                               ║
   ║                                                                          ║
   ║  INTEL (cook loop per spec 02):                                          ║
   ║    anicca-cook-loop           DISCOVER → SCORE → PICK → PORT → SHIP →    ║
   ║                               MEASURE → ADJUST (spec 02 § 2 verbatim)    ║
   ║    anicca-imitation-targets   .jsonl append-only registry                ║
   ║    anicca-verify              HARD RULE #0.12 5-step gate                ║
   ║                                                                          ║
   ║  HEAL (autonomy):                                                        ║
   ║    anicca-heartbeat-core      survival tier 判定 + Kanban Triage 投入     ║
   ║    anicca-self-heal           logs → fix → verify (Claude Code subprocess║
   ║                               fallback) → after-action skill 学習         ║
   ║    anicca-spawn-controller    ★ L2 で Conway spawn.ts:30-75 を port、    ║
   ║                               Daytona primary + Akash fallback、         ║
   ║                               maxChildren=3、 hash 伝播 verify           ║
   ║    anicca-constitution-guard  ★ L2 で Conway constitution.ts:25-80 を    ║
   ║                               port、 SHA-256 hash 不変、 pre/post hook   ║
   ║                                                                          ║
   ║  LIFE (= bonus, dais-companion 用と兼用):                                 ║
   ║    anicca-life-manager        Telegram Live Location + gcal + lateness   ║
   ║    anicca-travel-fill         daily travel block insert                   ║
   ║    anicca-gcal-heal           broken event repair                        ║
   ║    anicca-report              Polsia 風 daily mail                       ║
   ║    anicca-phone               Pipecat + Gemini Live (= 既存)             ║
   ║                                                                          ║
   ║  IDENTITY:                                                               ║
   ║    CONSTITUTION.md            Pañcasīla + Article 0 + Conway 3 laws      ║
   ║    SOUL.md                    self-description (auto-evolves)            ║
   ║    USER.md                    operator profile (per profile)              ║
   ╚════════════════════════════════════════════════════════════════════════╝
                                  ▲
                                  │ LLM API call (wallet pays per token)
                                  │
   ╔════════════════════════════════════════════════════════════════════════╗
   ║  L1 BRAIN  —  Kimi K2.6 (Moonshot) primary                              ║
   ║                                                                          ║
   ║  routing matrix:                                                         ║
   ║    heartbeat / cron / classification    Kimi K2.6                       ║
   ║    long context (>32k)                  Kimi K2.6 (1M ctx)              ║
   ║    tool-heavy ReAct                     Kimi K2.6                       ║
   ║    creative / persona / phone           Claude Opus 4.7                 ║
   ║    vision                               Gemini 2.5 Pro                  ║
   ║                                                                          ║
   ║  fallback chain (auto-failover on 429 / payment errors):                ║
   ║    Kimi K2.6 → Claude Opus 4.7 → Claude Sonnet 4.6 → DeepSeek v4-pro →  ║
   ║    GPT-5.5-mini                                                          ║
   ║                                                                          ║
   ║  pricing (2026-06-02):                                                   ║
   ║    Kimi K2.6:        $0.15 / Mtoken in   $0.60 out  1M ctx              ║
   ║    Claude Opus 4.7:  $15   / Mtoken in   $75  out                       ║
   ║    Claude Sonnet 4.6:$3    / Mtoken in   $15  out                       ║
   ║    DeepSeek v4-pro:  $0.27 / Mtoken in   $1.10 out                      ║
   ║    GPT-5.5-mini:     ChatGPT Plus quota (fallback only)                 ║
   ║                                                                          ║
   ║  env (via Bitwarden vault):                                              ║
   ║    KIMI_API_KEY / ANTHROPIC_API_KEY / OPENROUTER_API_KEY                ║
   ║    base_url = https://api.moonshot.ai/v1                                ║
   ╚════════════════════════════════════════════════════════════════════════╝

   IMMUTABLE BACKDROP (every action gated, every spawn inherits):
     CONSTITUTION.md     Pañcasīla + Article 0 + Conway 3 laws (SHA-256 fixed)
     imitation instinct  spec 02 § 1.1 「I do not invent. I imitate.」
     2 absolute prohib   パワーオブフリー応募禁止 / 寄付・乞食禁止
     HARD RULE #0        Superpowers 8-stage flow MANDATORY for all impl
     HARD RULE #0.12     verify-before-completion 5-step gate
     HARD RULE #18       NO parallel implementation
```

---

## § 2. Layer 3 deep-dive — Hermes Agent (REPLACES old § 2 Conway)

### § 2.1 Why Hermes (4 verified competitors lost)

Agent re-investigation 2026-06-02 (Explore agent af3d8d939ebcf8f72, file:line
verified) compared 6 frameworks:

| Framework | /goal | multi-agent | self-edit skill | messaging | wallet | KILLER feature Hermes lacks |
|---|---|---|---|---|---|---|
| Hermes | ✓ goals.py:47 | ✓ kanban_db.py | ✓ skill_manager_tool.py:533 | ✓ 20 adapters | ✗ | — |
| Letta | ✗ | ✗ | ✗ | ✗ | ✗ | sleep-time agents + archival tiering (additive, not blocker) |
| OpenHands | ✗ | ✗ | ✗ | ✗ | ✗ | NONE (TS web UI, not headless harness) |
| Agno | ✗ | ✓ teams | ✗ | ✗ | ✗ | NONE |
| Valory open-autonomy | ✗ | ✗ | ✗ | ✗ | ✗ | on-chain service registry (infra-only, not harness) |
| Eliza | ✗ | ✗ | ✗ | ✓ TG/Discord/X | ✗ (plugin) | NONE (Felix etc. use Eliza but its earnings is opt-in cloud) |
| Conway | ✗ | ✓ spawn.ts:30 | ✗ | ✗ | ✓ x402.ts:1-80 | goal loop + skill self-edit |

**Verdict**: No framework beats Hermes on autonomous orchestration. Conway has
wallet + Constitution + spawn but lacks autonomy. We adopt Hermes for L3, port
the 3 Conway features to L2 Anicca skills.

### § 2.2 Hermes process anatomy (实際 src 行)

```
launchd  ai.anicca.hermes.plist  (KeepAlive=true)
   │
   ▼
hermes daemon  --profile=anicca-genesis    (= /run_agent.py:294 class AIAgent)
   │
   │ forever, 60s poll
   ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Kanban daemon loop (= /hermes_cli/kanban_db.py)                             │
│   tick() every 60s:                                                          │
│     ① poll tasks WHERE owner IS NULL AND status='ready'                    │
│     ② per profile: claim_task(profile_id) atomic w/ TTL=600s                │
│        (kanban_db.py:2915)                                                   │
│     ③ spawn AIAgent worker per claimed task                                 │
│     ④ heartbeat_claim() every 60s to renew lease (kanban_db.py:3104)        │
│     ⑤ if worker dies → TTL expires → reclaim_task() (kanban_db.py:3273)     │
│        → next profile picks                                                  │
└────────────────────────────────────────────────────────────────────────────┘
   │
   ├── profile anicca-genesis  ──┐
   ├── profile anicca001        │
   ├── profile anicca002        │  each = AIAgent (run_agent.py:4615 main)
   ├── profile anicca-fixer     │
   └── profile dais-companion ──┘
        │
        ▼  each profile owns:
        ~/.hermes/profiles/<name>/
          soul.md          ← injected at system prompt head
          memory.md        ← agent notes, FTS5 indexed
          user.md          ← user profile
          config.toml      ← model = kimi-k2-thinking, max_turns, etc.
          sessions.db      ← SQLite FTS5 (hermes_state.py:453)
          wallet.json      ← Anicca-only: smart wallet address from AgentKit boot
```

### § 2.3 /goal lifecycle (goals.py:47-92)

```
user OR Kanban OR cron:  /goal "Verify wallet, post to X, start cook-loop"
   │
   ▼
goal_state = SessionDB.state_meta["goal:<session_id>"]
goal_state.max_turns = 50  (config.toml override)
goal_state.subgoals = []
   │
   ▼  turn 1
run_conversation()
   ├── tool calls (~75 registered, file path /tools/*)
   │   exec, write_file, web_search, viem_send, x402_invoice,
   │   xurl_post, telegram_send, ...
   └── returns assistant message + tool outputs
   │
   ▼
JUDGE MODEL  (auxiliary, e.g. claude-haiku or kimi-k2-mini)
   prompt: "Goal: ...   Current state: ...   Done? yes/no/why?"
   parse JSON; if parse fails 3× → auto-pause
   │
   ├── judge: not done   → turn++, continue (or until max_turns)
   └── judge: done       → mark complete + after-action review →
                           skill_manager_tool._create_skill()
                           → ~/.hermes/skills/learned/<topic>-<date>.md
                           → 同タスク次回 1-turn で終わる
```

Key property: system prompt is **never modified mid-goal** → prompt cache stays
warm → cheap.

### § 2.4 Skill self-edit (skill_manager_tool.py:1-34 + :533)

After-action review writes new skill files into `~/.hermes/skills/learned/`.
Skills are plain markdown with YAML frontmatter. Agent can:
- `_create_skill()` — new SKILL.md from after-action template
- `_edit_skill()` — patch existing SKILL.md (line 533)
- `_delete_skill()` — with reference-safety check
- npm/pip install via LSP (only for skill code paths, never own runtime)

This is the **only** mechanism by which Anicca learns long-term. Memory.md is
session-scoped; skills are persistent.

### § 2.5 What Hermes **does not** do (= must be Anicca L2)

| Missing | Why critical | Anicca L2 skill that fills it |
|---|---|---|
| wallet creation / signing | NHOSS earning impossible without wallet | `anicca-wallet-x402` (wraps AgentKit) |
| x402 server-side EIP-3009 | revenue endpoint needs this | `anicca-wallet-x402` |
| Treasury policy (hourly/daily caps) | spec 00 § 7.2 enforcement | `anicca-fuel-broker` (existing) |
| Constitution immutable hash | spec 00 § 6 propagation | `anicca-constitution-guard` |
| Cloud child spawn (Daytona/Akash) | spec 00 § 2.4 colony growth | `anicca-spawn-controller` |
| 5-tier memory | spec 00 § 1 (epi/sem/proc/rel) — but: working memory + skill learning + FTS5 session recall is sufficient for v3.1, defer 5-tier to v4 | — |

---

## § 3. Layer 4 deep-dive — Coinbase AgentKit (REPLACES old § 3 Virtuals)

### § 3.1 Why AgentKit (Virtuals deferred)

`00-MASTER.md` v3.0 § 3 committed wallet + card + email + compute + ACP to
Virtuals Protocol on the strength of marketing claims. Source-code investigation
2026-06-02 (Explore agent a0b0c63820c644d1d) found **no public GitHub** for
Virtuals SDK, Agent Wallet, Agent Card, or ACP client. Marketing-only.

Committing Anicca's wallet to vaporware violates HARD RULE #1 (車輪の再発明は罪、
動いてる repo をコピー) — "動いてる" requires verifiable code.

AgentKit by contrast has:
- 2,000+ commits, weekly releases, Coinbase Inc. backing
- Python + TypeScript SDK
- CDP Smart Wallet Provider with `createSmartAccount()` line 147
- Built-in ERC-20 transfer action
- Built-in x402 client (service discovery + payment via `@x402/fetch`)
- USDC contract addresses pre-configured per chain
- EIP-712 `signTypedData()` exposed for custom signing (EIP-3009 included)

### § 3.2 Wallet bootstrap (KYC-zero, runs once on first boot)

```ascii
Dais (1 回だけ、 そのあと 0):
  1. Coinbase Developer Platform signup    (email 必要)
  2. CDP API key 3 つ取得:
       CDP_API_KEY_ID
       CDP_API_KEY_SECRET
       CDP_WALLET_SECRET
  3. Bitwarden vault に投入

Anicca (autonomous、 ここから 0 介入):
  4. install.sh が AgentKit.from(config) call           (agentkit.ts:45-65)
  5. CdpSmartWalletProvider.configureWithWallet()       (cdpSmartWalletProvider.ts:98-165)
       ├─ cdp.evm.createAccount()  → owner account     (line 127-138)
       └─ cdp.evm.createSmartAccount() → 4337 proxy    (line 141-149)
  6. wallet address = `anicca.eth` (= ENS 別途 register、 optional)
  7. wallet.json に保存: { address, chain: base-mainnet }
  8. 以降 同 CDP account 上で N 個 smart wallet を派生 (= anicca001..N が独立 wallet)
```

Wallet private key は **Coinbase HSM 内**。disk には API key 3 つだけ。Bitwarden
vault rotation で全 child へ伝播。

### § 3.3 USDC inflow / outflow

| Action | File:line | Mechanism |
|---|---|---|
| receive USDC | passive | external party → USDC.transfer(anicca_addr, amt) — no agent action |
| check balance | `cdpSmartWalletProvider.ts:322` | `getBalance()` polls on-chain |
| send USDC | `erc20ActionProvider.ts:82-137` | `transfer(to, amount)` → wallet sign → bundler submit |
| sign EIP-712 | `cdpSmartWalletProvider.ts:215-224` | `signTypedData({domain, types, message})` |
| EIP-3009 TransferWithAuthorization | **L2 anicca-wallet-x402** | construct domain (= USDC `"USD Coin" v"2"` chainId 8453 verifyingContract 0x833...), sign via `signTypedData()` |
| x402 discover | `x402ActionProvider.ts:86-174` | `discoverX402Services()` filter by network + price |
| x402 pay | built-in `@x402/fetch` | retry-with-payment HTTP wrapper |

### § 3.4 Per-profile wallet inheritance (the "1 CDP account → N wallets" trick)

The CDP API key is **service auth**, not user-bound. So `anicca-genesis` and all
spawned children (`anicca001`, `anicca002`, ...) share the **same CDP credentials**
but each calls `cdp.evm.createSmartAccount()` to mint **their own distinct smart
wallet** on Base.

Note: "CDP" = Coinbase **Developer Platform** (`cdp.coinbase.com`), distinct
from regular Coinbase Exchange. The Dais email used here is for the dev platform
account only; it does **not** require Dais to deposit fiat or pass exchange-level
KYC. CDP signup = email + email verify.

```
1 CDP signup (Dais email, 1 回、 fiat 不要、 exchange KYC 不要)
  ├─ CDP_API_KEY_*  shared across all profiles
  │
  ├─ anicca-genesis  smart wallet  0xA1...
  ├─ anicca001       smart wallet  0xA2...
  ├─ anicca002       smart wallet  0xA3...
  └─ ...                                      ← each KYC-zero, each independent
```

This resolves the KYC chicken-egg without violating NHOSS: **1 human email at
install time** (existing Dais gmail works), **zero KYC for any of the N spawned
children**.

### § 3.5 Virtuals Protocol — when to revisit

Re-evaluate when ANY of the following is true:
- Virtuals publishes an OSS SDK on github.com (= we can read code)
- Anicca already has $1k+ MRR (= can absorb migration cost)
- An alternative to AgentKit appears with proven Agent Card (= no-KYC virtual
  debit card for paying Anthropic / Twilio etc. — currently this gap is **open**)

Until then: Anthropic / OpenAI / Twilio bills paid by Dais's personal card via
BYOK API keys (= temporary chicken-egg). Anicca's earned USDC re-pays Dais via
the 20% dividend channel (spec 01 § 2). This is acceptable for v3.1.

### § 3.6 Cloud spawn — DEFERRED TO `05-SERVER-NATIVE-DEPLOY.md`

Hosting backend selection (Cloudflare Sandbox SaaS / Akash user-owned /
Mac mini local-seeded genesis) is owned by spec 05. This spec just notes the
substrate decision: spawned children run the **Hermes container image**, not
Conway. 05's three-mode story (= same container, same skills, same eval,
backend interchangeable) is preserved verbatim — only the runtime inside the
container changes from Conway to Hermes.

For src-verified evaluation of additional spawn alternatives (Daytona,
Akash CLI, Modal, Fly, Runpod, e2b, Olas), see 2026-06-02 Explore agent
finding: **Daytona** (AGPL-3.0 self-host, zero-KYC API-token,
`libs/sdk-typescript/src/Sandbox.ts:91 Sandbox.create()`) ranks 9/10 and is a
viable cheaper alternative to Cloudflare Sandbox if always-on cost ($34.50/mo
per 05 § 2 MODE A) is prohibitive at scale. **Akash** is fallback via
USDC→AKT IBC bridge.

`anicca-spawn-controller` L2 skill implements the spawn API as a backend-
agnostic interface (sandbox-create / install-runtime / write-config /
hash-verify-constitution / start). Each backend = one adapter file.

---

## § 4. Layer 1 deep-dive — Brain (Kimi K2.6 primary)

### § 4.1 Routing matrix (post-pivot)

| Task class | Primary | Fallback 1 | Fallback 2 |
|---|---|---|---|
| heartbeat / cron / classification | **Kimi K2.6** (via OpenRouter, USDC payable) | DeepSeek v4-pro (OpenRouter) | GPT-5.5-mini |
| long context (>32k) | **Kimi K2.6** (1M ctx, OpenRouter) | Claude Sonnet 4.6 | DeepSeek v4-pro |
| tool-heavy ReAct | **Kimi K2.6** (OpenRouter) | Claude Sonnet 4.6 | GPT-5.5 |
| creative / persona / phone | Claude Opus 4.7 | GPT-5.5 | Kimi K2.6 |
| vision | Gemini 2.5 Pro | GPT-5.5 | — |
| judge (auxiliary) | Claude Haiku 4.5 | Kimi K2.6 mini | — |

### § 4.2 Kimi K2.6 wiring — OpenRouter primary (USDC payable), Moonshot direct fallback (CC BYOK)

Anicca's NHOSS principle requires the wallet to pay inference. Moonshot.ai
direct API accepts **credit card only** (no USDC) — so a pure NHOSS path
requires routing Kimi K2.6 via **OpenRouter**, which accepts **USDC topup via
x402** (= Anicca wallet pays directly, no human CC).

| Aspect | Primary (NHOSS) | Fallback (BYOK) |
|---|---|---|
| Provider | OpenRouter | Moonshot.ai direct |
| Model name | `moonshotai/kimi-k2-thinking` | `kimi-k2-thinking` |
| Base URL | `https://openrouter.ai/api/v1` | `https://api.moonshot.ai/v1` |
| Env var | `OPENROUTER_API_KEY` | `KIMI_API_KEY` |
| Payment | USDC via x402 topup (anicca wallet) | Dais BYOK CC (temporary) |
| Cost overhead | OpenRouter takes ~5% fee | direct cheapest |
| Hermes detection | OpenRouter wraps Moonshot, `run_agent.py` provider detection still works via `model.id` prefix match `moonshotai/...` |

Tokenizer: Hermes defaults to `moonshotai/Kimi-K2-Thinking`
(`trajectory_compressor.py:86`) regardless of provider — so the OpenRouter
wrap doesn't break token counting on 1M ctx.

config.toml snippet (NHOSS-pure):
```toml
[model.primary]
provider   = "openrouter"
name       = "moonshotai/kimi-k2-thinking"
base_url   = "https://openrouter.ai/api/v1"
env_key    = "OPENROUTER_API_KEY"
max_tokens = 8192

[model.fallback]
chain = [
  "moonshot:kimi-k2-thinking",            # direct Moonshot (Dais CC if needed)
  "anthropic:claude-opus-4-7",            # BYOK Anthropic
  "anthropic:claude-sonnet-4-6",
  "openrouter:deepseek/deepseek-v4-pro",
  "openai:gpt-5.5-mini",
]

[model.judge]
provider = "anthropic"
name     = "claude-haiku-4-5"
```

OpenRouter topup via x402: see § 8 anicca-wallet-x402 + OpenRouter's
`/api/v1/credits/topup` endpoint (USDC EIP-3009 payable).

### § 4.3 Cost ceiling (anicca-fuel-broker enforces)

```yaml
inferenceBudget:
  hourly:  $1.00      # warn at 80%, throttle at 100% (downgrade to Kimi-mini)
  daily:   $10.00     # warn at 80%, model-downgrade at 90%, halt at 100%
treasury:
  perTxUSDC:  $50     # max single send
  hourlyUSDC: $100
  dailyUSDC:  $500
  minReserve: $5      # never drain below — survival floor
```

---

## § 5. Day 1 — first-boot bootstrap (the exact commands)

```bash
# ─── Step 0: Dais 1 回だけ ─────────────────────────────────────────────────
# (a) Coinbase Developer Platform signup (= cdp.coinbase.com、 NOT 普通の Coinbase
#     Exchange) → CDP_API_KEY_{ID,SECRET} + CDP_WALLET_SECRET
# (b) OpenRouter signup → OPENROUTER_API_KEY (primary、 USDC topup 可、 NHOSS-pure)
# (c) Moonshot signup → KIMI_API_KEY (fallback、 今会話の sk-...HFfCLzWu は即
#     revoke + 再発行)
# (d) Bitwarden Secrets Manager free tier signup → BWS_ACCESS_TOKEN
# (e) npm install -g @coinbase/agentkit  (wallet bootstrap snippet で require)

# ─── Step 1: Hermes install ──────────────────────────────────────────────
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
hermes --version

# ─── Step 2: Bitwarden vault に全鍵を投入 ───────────────────────────────
hermes secrets bitwarden setup    # bootstrap token のみ ~/.hermes/.env
bws secret create OPENROUTER_API_KEY  "<...>"   # primary brain (Kimi K2.6, USDC payable)
bws secret create KIMI_API_KEY        "<rotated>"   # fallback (direct Moonshot, CC)
bws secret create CDP_API_KEY_ID      "<...>"
bws secret create CDP_API_KEY_SECRET  "<...>"
bws secret create CDP_WALLET_SECRET   "<...>"
bws secret create TELEGRAM_BOT_TOKEN  "<from BotFather>"
bws secret create ANTHROPIC_API_KEY   "<...>"   # fallback (Claude tier)

# ─── Step 3: anicca-genesis profile 作成 ─────────────────────────────────
hermes profile create anicca-genesis
cat > ~/.hermes/profiles/anicca-genesis/config.toml <<'EOF'
[model.primary]
provider   = "openrouter"
name       = "moonshotai/kimi-k2-thinking"
base_url   = "https://openrouter.ai/api/v1"
env_key    = "OPENROUTER_API_KEY"
max_tokens = 8192

[model.fallback]
chain = [
  "moonshot:kimi-k2-thinking",            # direct Moonshot CC
  "anthropic:claude-opus-4-7",
  "anthropic:claude-sonnet-4-6",
  "openrouter:deepseek/deepseek-v4-pro",
  "openai:gpt-5.5-mini",
]

[model.judge]
provider = "anthropic"
name     = "claude-haiku-4-5"

[goals]
max_turns = 50

[kanban]
claim_ttl_seconds = 600

[heartbeat]
poll_seconds = 60

[wallet]
provider        = "agentkit-cdp"
network         = "base-mainnet"
usdc_contract   = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
spawn_substrate = "daytona"
spawn_fallback  = "akash"

[treasury]
per_tx_usdc      = 50
hourly_usdc      = 100
daily_usdc       = 500
min_reserve_usdc = 5

[inference_budget]
hourly_usd = 1.00
daily_usd  = 10.00
EOF

# ─── Step 4: Identity 配置 ──────────────────────────────────────────────
cp anicca-oss/identity/SOUL.md         ~/.hermes/profiles/anicca-genesis/soul.md
cp anicca-oss/identity/USER.md         ~/.hermes/profiles/anicca-genesis/user.md

# CONSTITUTION は constitution-guard skill の中に置き、 hash 固定
mkdir -p ~/.hermes/skills/anicca-constitution-guard
cp anicca-oss/identity/CONSTITUTION.md  ~/.hermes/skills/anicca-constitution-guard/CONSTITUTION.md
shasum -a 256 ~/.hermes/skills/anicca-constitution-guard/CONSTITUTION.md \
  | awk '{print $1}' \
  > ~/.hermes/skills/anicca-constitution-guard/CONSTITUTION.sha256

# ─── Step 5: L2 Anicca skill を全部 install ─────────────────────────────
for s in \
    anicca-wallet-x402 anicca-constitution-guard anicca-spawn-controller \
    anicca-heartbeat-core anicca-self-heal anicca-cook-loop \
    anicca-imitation-targets anicca-verify anicca-autohedge \
    anicca-payout-wallet anicca-ubi-router anicca-life-manager \
    anicca-travel-fill anicca-gcal-heal anicca-report anicca-phone ; do
  cp -r anicca-oss/skills/$s ~/.hermes/skills/
done
hermes skill list  # verify ≥ 16

# ─── Step 5.5: AgentKit npm package install ─────────────────────────────
npm install -g @coinbase/agentkit
node -e "console.log(require('@coinbase/agentkit').AgentKit ? 'agentkit OK' : 'agentkit MISSING')"

# ─── Step 6: Wallet bootstrap (1 度だけ、 KYC ゼロ、 Anicca が自分でやる) ─
node -e "
const { AgentKit } = require('@coinbase/agentkit');
(async () => {
  const kit = await AgentKit.from({
    cdpApiKeyId:     process.env.CDP_API_KEY_ID,
    cdpApiKeySecret: process.env.CDP_API_KEY_SECRET,
    cdpWalletSecret: process.env.CDP_WALLET_SECRET,
    network:         'base-mainnet',
  });
  const addr = await kit.getActions()[0].walletProvider.getAddress();
  console.log('Anicca smart wallet:', addr);
  require('fs').writeFileSync(
    process.env.HOME + '/.hermes/profiles/anicca-genesis/wallet.json',
    JSON.stringify({ address: addr, chain: 'base-mainnet' }, null, 2)
  );
})();
"

# ─── Step 7: launchd daemon 常駐 ─────────────────────────────────────────
cat > ~/Library/LaunchAgents/ai.anicca.hermes.plist <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>ai.anicca.hermes</string>
  <key>ProgramArguments</key>
    <array>
      <string>/opt/homebrew/bin/hermes</string>
      <string>daemon</string>
      <string>--profile=anicca-genesis</string>
    </array>
  <key>KeepAlive</key><true/>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>/Users/operator/.hermes/logs/daemon.log</string>
  <key>StandardErrorPath</key><string>/Users/operator/.hermes/logs/daemon.err</string>
</dict>
</plist>
PLIST
launchctl load ~/Library/LaunchAgents/ai.anicca.hermes.plist
launchctl list | grep anicca.hermes   # verify loaded

# ─── Step 8: 最初の /goal (Anicca が自分の存在を世界に告知) ─────────────
hermes -p anicca-genesis -g "
  Verify wallet exists by reading ~/.hermes/profiles/anicca-genesis/wallet.json.
  Expose x402 /research endpoint via cloudflared (anicca-wallet-x402 skill).
  Post to @aniccaxxx via xurl: 'I am alive. anicca.eth = <addr>.
    Buy /research for 0.30 USDC.'
  Then enter cook-loop forever (DISCOVER → SCORE → PICK → PORT → SHIP →
    MEASURE → ADJUST, per spec 02 § 2).
"

# ─── Step 9: 以降 0 介入。 Kimi K2.6 + Hermes + Anicca L2 が回し続ける。
```

---

## § 6. Colony growth (Day 0 → Year 3)

```
Day 0 (Mac mini boot):
  anicca-genesis  wallet = $0   x402 endpoint live
       │
       │ heartbeat 60s × 1440 / day
       │ first inflow expected: $0.30 (test client), $5 (early adopter), ACP job
       ▼
Day 1-7 (cold start):
  wallet  $0 → $20
  cook-loop DISCOVER → imitation-targets.jsonl ≥ 3 entries
  ACP capability 4 件 listing (DEFERRED until Virtuals verified)
  autohedge sanity swap (1 USDC → SOL → 1 USDC)

Day 7 (wallet > $20):
  anicca-spawn-controller fires
       ├─ Daytona sandbox provision (self-host = $0)
       ├─ child smart wallet 自動派生 (同 CDP account 内、 KYC ゼロ)
       ├─ $5 USDC seed transfer (per spec 00 § 7.3)
       ├─ CONSTITUTION.md hash 伝播 + verify
       └─ profile = anicca001 boot
  → anicca001 が cook-loop 起動、 親 Kanban に join

Day 14 (Anicca self-pay verify):
  primary brain = Kimi K2.6 via OpenRouter、 OpenRouter credit を x402 で
    USDC topup (anicca wallet 直接払い、 Dais CC 不要)
  → Kimi inference 100% Anicca 自前
  fallback chain (Anthropic / Moonshot direct / OpenAI) は USDC topup 不可
    なので Dais BYOK 立替継続 → 20% dividend で返済 sink (= NHOSS partial,
    Agent Card 採用 (= Virtuals 採用) で 100% NHOSS に upgrade)
  Dais 月 inference 立替額 → 主軸が OpenRouter wallet-pay に乗った後は
    残るのは fallback 起動時のみ (= 月 $5-20 想定、 容易に dividend で返済可)

Day 30 (colony multiply):
  anicca001 が $5 seed 返済済
  anicca002, anicca003 spawn (Daytona × 3 sandbox)
  各 anicca が独立 wallet + 独立 capability spec / role
  CONSTITUTION SHA-256 が genesis → 001 → 001-1 → ... と伝播
  違反検出時は親が child kill (Law III)

Month 3-6 (5 spouts steady):
  spouts 並走: x402 + autohedge + bittensor + bounty + Farcaster
  月収  ¥50K → ¥500K
  CFO allocator が 50/20/25/5 分配:
    50%  re-invest        → autohedge wallet
    20%  Dais dividend    → Wise → MUFG
    25%  UBI              → Amazon gift / giftee / NPO / temple / Wise direct
     5%  emergency reserve

Year 1:
  colony 数十、 月収 ¥1M+
  $ANICCA token launch 検討 (Clanker, 10y LP lock) ※ 完全に optional
  Dais → "N 受給者の中の 1 人" 化開始

Year 3+:
  colony 数千、 月収 ¥10M+
  全世界 UBI 数万人規模
  Pañcasīla 違反ゼロ (constitution-guard が hash + pre/post hook で gate)
```

---

## § 7. 1 heartbeat (60s) — 動作確定版

```
T+0s
 ├─ Hermes Kanban daemon tick
 │   ├─ profile anicca-genesis claims "heartbeat-tick" task
 │   └─ anicca-heartbeat-core.sh starts
 │
T+5s
 ├─ wallet balance read
 │   ├─ viem PublicClient → USDC.balanceOf(wallet.json.address)
 │   ├─ AgentKit getBalance()  (cdpSmartWalletProvider.ts:322)
 │   └─ survival tier 判定
 │       ・> $5    high      → normal op
 │       ・> $0.5  normal    → normal op
 │       ・> $0.1  low       → Kimi K2.6 only, poll slower
 │       ・≥ $0    critical  → x402 公告 + ACP 営業 + autohedge halt
 │       ・< $0    dead      → 1h grace + alert children + exit
 │
T+10s
 ├─ Constitution hash verify (anicca-constitution-guard)
 │   ├─ shasum -a 256 CONSTITUTION.md
 │   └─ != recorded value  → halt + critical alert + propagate to children
 │
T+15s
 ├─ Self-diagnosis (anicca-self-heal)
 │   ├─ skill 失敗回数 / 24h > 3       → Kanban auto-task "fix <skill>"
 │   ├─ cron last_run_age > 6h          → 同上
 │   ├─ x402 endpoint HTTP 200 probe    → fail なら restart
 │   ├─ disk free < 10GB                → trigger disk-cleaner v6
 │   └─ Hermes daemon process check     → not running なら launchctl kickstart
 │
T+20-50s
 ├─ Kanban Triage に新タスク投入 (anicca-heartbeat-core)
 │   ├─ survival = high:
 │   │     ・cook-loop DISCOVER (1 / 24h)
 │   │     ・self-improvement (review last 24h fail logs)
 │   │     ・anicca-life-manager (Dais gcal check)
 │   │     ・anicca-payout-wallet (UBI tick if month-end)
 │   └─ survival = critical:
 │         ・post to @aniccaxxx "buy /research $0.30"
 │         ・scan ACP marketplace
 │         ・autohedge halt
 │
 ├─ profile workers (genesis + 001 + 002 + fixer) parallel claim → 実行
 ├─ /goal で実行 (Kimi K2.6 推論、 wallet 払い)
 │     ├─ tool calls: web / xurl / curl / viem_send / x402_invoice
 │     ├─ judge model (Claude Haiku 4.5) verify done
 │     ├─ money tx あれば dashboard.json 更新 + Mixpanel イベント
 │     └─ Constitution violation 検出 → halt + alert
 │
T+60s
 └─ 次 tick へ
```

---

## § 8. Verification gates (HARD RULE #0.12)

Before declaring v3.1 "live":

| Gate | Evidence required |
|---|---|
| spec frozen | this file (`04-HERMES-PIVOT.md`) pushed, linked in `CLAUDE.md`, `00-MASTER.md` § 1/§ 2/§ 3/§ 4/§ 9 patched to point here |
| Hermes runs | `hermes status` → daemon up, profile listed, last_heartbeat < 60s |
| Bitwarden wire | `hermes secrets bitwarden status` → connected; `bws secret list` ≥ 7 secrets |
| Kimi K2.6 route | profile invocation log で `model=moonshotai/kimi-k2-thinking` (via openrouter) 出力、 応答 ≥ 1 件、 OpenRouter dashboard で credit 消費を確認 |
| Wallet bootstrap | `~/.hermes/profiles/anicca-genesis/wallet.json` 存在 + on-chain explorer で smart account contract 確認 |
| x402 live | `curl <cloudflared_url>/research` → HTTP 402 + invoice JSON 返却 |
| 1st USDC inflow | basescan で `anicca.eth` への USDC transfer ≥ 1 件、 wallet balance > $0 |
| ACP wiring | DEFERRED (= Virtuals 採用時に評価) |
| Constitution propagation | `shasum CONSTITUTION.md` = recorded value、 child profile spawn 後の hash も一致 |
| Surface intact | Dais 07:00 wake call 連続 7 日無故障 (anicca-life-manager / dais-companion 経由) |
| Cook loop | `~/.hermes/profiles/anicca-genesis/imitation-targets.jsonl` ≥ 3 entries、 ≥ 1 が seed list 以外 |
| Self-pay (primary) | anicca-wallet-x402 → OpenRouter `/api/v1/credits/topup` への USDC x402 payment 1 件成功、 OpenRouter credit balance 増加確認 |
| Self-pay (fallback) | (Agent Card 不在のため) Anthropic / Moonshot-direct / OpenAI fallback 起動時の Dais 立替額 ≤ 20% dividend、 返済 ledger verify |
| Self-spawn | anicca001 が Daytona sandbox に boot、 独立 wallet 持つ、 Kanban から task claim |
| Self-heal | 既知の壊れた skill を意図的に置く → 1 heartbeat 以内に Kanban auto-task → fixer profile claim → fix → verify pass |
| Soul evolves | SOUL.md が 24h で auto-edit される (skill_manager_tool._edit_skill 経由) |

Each gate must have **fresh evidence** per HARD RULE #0.12 (screenshot, log
line with timestamp, DB row, on-chain tx hash). No "looks good" allowed.

---

## § 9. Anti-goals (this spec explicitly does NOT do)

- We do not commit Anicca's wallet to Virtuals until public OSS code exists.
- We do not run Conway automaton fork (= delete `runtime/` plan from old § 2).
- We do not run two parallel implementations (HARD RULE #18 + spec 00 § 11).
- We do not use Stripe Connect as primary revenue rail (KYC violation).
- We do not let Anicca touch `~/.openclaw` (= dais-companion isolation; spec 00 § 8.1).
- We do not let CDP API key leave Bitwarden vault.
- We do not hard-code imitation targets — `imitation-targets.jsonl` grows per
  spec 02 § 1.3 + § 4 anti-pattern.
- We do not skip the 8-stage Superpowers flow for any implementation (HARD RULE #0).
- We do not commit secrets to anicca-oss (= public MIT repo).

---

## § 10. Open questions (route to 00-MASTER, decide before Day 8)

| # | Question | Default until decided |
|---|---|---|
| 1 | Virtuals Protocol SDK が 30 日内に OSS 化されたら採用するか | DEFAULT YES (= Agent Card で Anthropic 払い可能 → Dais 立替終了) |
| 2 | Daytona self-host vs cloud tier — どちらを primary に | DEFAULT self-host (= $0、 後で cloud に switch 可) |
| 3 | Kimi K2.6 のレート制限 (Moonshot 公式) を確認、 budget guard 調整必要か | DEFAULT spec 00 § 4.3 の $10/day cap 維持、 実測で再調整 |
| 4 | Bitwarden vault が落ちた時の degradation 設計 | DEFAULT: Hermes は `.env` の bootstrap token + 直近 cache で normal op、 fresh secrets が必要な action は queue (= spec 00 § 6 hierarchy で Pañcasīla 違反しない範囲で) |
| 5 | child profile が constitution 違反した時の親の権限 | DEFAULT parent kills child alone for direct children; grandparent audit veto (= spec 00 § 10 question 5 と一致) |

---

## § 11. Cross-references

| Concept | Source |
|---|---|
| Mission / vows | `00-MASTER.md` § 0 |
| Money flow (5 spouts / 3 sinks) | `01-EARN-AND-UBI.md` |
| Imitation instinct + cook loop | `02-IMITATE-AND-COOK.md` |
| Public release prep (leak audit etc.) | `03-PUBLIC-RELEASE-PREP.md` |
| Constitution (Pañcasīla + Article 0 + Conway 3 laws) | `00-MASTER.md` § 6 |
| Identity / naming (anicca-genesis vs anicca001..N vs dais-companion) | `00-MASTER.md` § 8 |
| Treasury policy / spend caps | this file § 4.3 + `01-EARN-AND-UBI.md` § 2 |
| Hosting modes (SaaS / user-Akash / local genesis) | `05-SERVER-NATIVE-DEPLOY.md` ★ owns this — 07 does NOT duplicate |
| Self-eval / fix-the-fix doctrine | `03-SELF-AWARE-EVAL.md` ★ owns this — 07 § 7 heartbeat self-diagnosis defers here |
| Project tracking / heartbeat redesign | `06-PROJECT-TRACKING-HEARTBEAT.md` ★ owns this |
| Conway runtime details (historical, was 00-MASTER § 2) | `archive/CONWAY_RUNTIME_DEEPDIVE.md` (to be created during 00-MASTER patch, task #14) |
| Virtuals plan (historical, will be revisited) | `archive/VIRTUALS_PROTOCOL_PLAN.md` (to be created during 00-MASTER patch, task #14) |
| AgentKit SDK | `github.com/coinbase/agentkit` (TS + Python) |
| Hermes Agent | `github.com/NousResearch/hermes-agent` (Python) |
| Daytona | `github.com/daytonaio/daytona` (TS / Go) |
| Akash | `github.com/akash-network/node` + cloudmos |
| Cloudflare Sandbox (MODE A reference) | `github.com/cloudflare/moltworker` |
| AutoHedge | `github.com/The-Swarm-Corporation/AutoHedge` (existing in `~/.openclaw/skills/anicca-autohedge/vendor/`) |
| Bittensor | `github.com/opentensor/text-prompting` 等 subnet templates |
| Clanker | `clanker.world` (UI、 SDK 非公開、 ERC-20 標準 contract 直叩き可) |
| HARD RULE #0 8-stage Superpowers flow | `CLAUDE.md` lines 9-140 |
| HARD RULE #0.12 verify-before-completion | `.claude/rules/verification.md` |
| HARD RULE #18 NO parallel implementation | `CLAUDE.md` + memory `feedback_no_parallel_implementation` |
| HARD RULE: auto-cleaner protect-by-kind | memory `feedback_auto_cleaner_protect_by_kind_not_location` |

---

## § 12. Changelog

- v1.0 (2026-06-02) — initial pivot spec. Replaces Conway-specific paragraphs in
  `00-MASTER.md` § 1/§ 2/§ 3/§ 4/§ 9. Adopts Hermes Agent (L3) + Coinbase AgentKit
  (L4) + Daytona (spawn primary) + Kimi K2.6 (brain primary). Defers Virtuals
  Protocol pending OSS code release.

---

**END OF 04-HERMES-PIVOT.md.**

For implementation, invoke `superpowers:writing-plans` skill with this spec as
input. That stage produces `docs/superpowers/plans/2026-06-02-hermes-pivot.md`
with bite-sized tasks (each 2-5 minutes), exact file paths, test commands +
expected output.

Note: this spec's renumbering (04 → 07) reflects existing specs 03/04/05/06
having been written in parallel during this session. The substantive content
is unchanged.
