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
| Spec version | v3.5 (2026-06-04) — RUNTIME LOCKED via code-read + real boot (see `16-RUNTIME-CODE-TRUTH.md`, AUTHORITATIVE for substrate). **ONE runtime = Hermes Agent** (NousResearch, Python, MIT) — BYOK-native (`hermes model`, no fork), Daytona-native host backend, self-improving learning loop, cron heartbeat, gateway. automaton (Conway, MIT) is **NOT a second runtime** — it is the REFERENCE we PORT its 4 MIT primitives from (wallet / x402-in+out / self-replication / constitution) into Hermes **skills**. Brain = Kimi K2.6 default ($0.50/$2·M) + Opus/GPT-5 for 10% high-stakes + local cleanup. Hosts = Daytona (native, primary) / Akash (sovereign fallback) / Conway (optional). Quality = the **eval-loop** (judge→0.7 gate→regression→prod-monitor→failure-as-testcase) gates every output. Stacking automaton+Hermes (v3.4 framing) was REDUNDANT double-loop — corrected. See § 1.0. |
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

## § 1.0 RUNTIME DECISION (v3.5, code-verified 2026-06-04 — read this first)

> Locked after reading the source of all 3 candidate runtimes + a REAL boot of automaton.
> Full evidence (file:line) in `16-RUNTIME-CODE-TRUTH.md` (AUTHORITATIVE for substrate; when
> any older spec conflicts on the runtime, spec 16 + this § 1.0 win).

```
ONE RUNTIME = Hermes Agent (NousResearch, Python, MIT)         ← the body, runs standalone
  native already (no build needed):
    · BYOK brain, no lock-in        `hermes model` → Kimi K2.6 / Anthropic / OpenAI / OpenRouter
    · Daytona + Modal host backends (serverless, hibernate-idle)   ← the spawn host
    · self-improving learning loop (creates+improves skills from experience)
    · cron scheduler = autonomous heartbeat · gateway TG/Slack/Discord · memory (MEMORY.md+SQLite)
  PORT from automaton (Conway, MIT) as Hermes SKILLS (the 4 things Hermes lacks):
    1. wallet        (Base sign/send — automaton identity/wallet.ts)
    2. x402          (IN=earn server + OUT=pay services — automaton conway/x402.ts + spec 09)
    3. self-replication (new sovereign Hermes child on Daytona/Akash + own wallet +
                         constitution SHA-256 propagation — automaton replication/spawn.ts)
    4. constitution-guard (3 Laws immutable, Pañcasīla-aligned — automaton constitution.md → CLAUDE.md)
  HOSTS: Mac-mini-local (genesis $0) / Daytona (native, primary) / Akash (sovereign) / Conway (optional)
  QUALITY: eval-loop skill gates EVERY output (judge 0-1 → 0.7 → regression → prod-monitor → testcase)
```

**Why NOT stack automaton + Hermes (the v3.4 framing):** both are complete standalone agents with
their own loop. Running both = a redundant double-brain. automaton's README positions it as standalone
("No human operator required", `node dist/index.js --run`). So we pick ONE (Hermes — richest harness +
the only browser-earning path + BYOK-native) and port automaton's economic/replication primitives as
skills. automaton = reference, not a running component.

**Why automaton inference is NOT used directly:** a real boot (2026-06-04) proved the shipped automaton
binary routes ALL inference through Conway (402 on $0 balance) even when the model name is set to a Claude
model; its config wizard exposes only the Conway provider. Hermes solves this natively (`hermes model`).

**Earn thesis is market-validated:** on Base, agents already pay $1.2M/30d via x402, and earning agents
exist (Felix $261k). Anicca BOTH pays (x402 buy inference/browser/search) AND earns (x402 sell + Lancers).

**Build path (gated):** PHASE 0 spec (this rewrite + 7 component impl-specs, codex-review ok:true) →
PHASE 1 skills (boot → wallet+x402 → ★eval-loop → earn → constitution+payout → daily-report →
self-replication → colony) → PHASE 2 live (spawn **Anicca-001** on Mac mini → BATTLE TEST: runs every day
+ earns every day ×7d, no human → publish `github.com/Daisuke134/anicca-oss` installable) → PHASE 3
forum/self-improve/swarm/roll-out. Cloud `aniccaai.com/install` deferred.

**Reference layer (spec 16 + 18 + 19-24):** the self-improvement + collective-forum + swarm design is
locked from SOURCE-read reference repos — `19` symphony, `20` MiroFish, `21` swarms, `22` sutando,
`23` agent-swarm (end-to-end blueprint), `24` FORUM-UX (post→ack→discuss→implement→vote→merge→roll-out,
every step behind a shipped impl; roll-out de-risked by in-house `self_update.py`).

**★ CURRENT GROUND TRUTH (2026-06-04, measured — keep launch claims honest, HARD RULE #14/0.12) ★**
```
 instances    = genesis ×1 = Hermes Agent v0.12.0 (2026.4.30) on Mac-mini, BYOK fuel=copilot (gh auth), model=gpt-4o-mini,
                heartbeat every 30m -> ~/.hermes/state/heartbeat.jsonl (writer = skills/anicca-heartbeat;
                ok=true, fuel="GitHub Copilot", model="gpt-4o-mini" verified live 2026-06-04 23:02 JST).
                Hermes gateway launchd service alive: label "ai.hermes.gateway" (recorded in
                ~/.hermes/state/hermes-launchd-label; PID survives kickstart).
                (OpenClaw 19 jobs co-resident; cloud/child = ZERO; "4 instances" still target-state.)
 wallet       = 0xa3CDd4Ec... on Base → 0 USDC / 0 ETH (empty; x402 earn skill #324 not built).
 economics    = MRR ~$27 ; all-time landed ¥4,956 (NOT monthly) ; runtime spend ~$99/mo+ → NET NEGATIVE.
                "avg ¥5,000/mo income, ~¥1,000 cost" = NOT true today (cost is ~¥15k/mo, income < cost).
 self-X       = friction-fixer(spec15) lives; self-improve #335 / self-manage #336 = NOT built.
                self-replication #327 = skill BUILT (skills/spawn-child, Hermes-registered) + dry-run/
                cost-cap unit tests PASS; provision path reaches the live Daytona API. BUT no live child
                yet: Daytona Personal org has 0 compute regions (/api/regions=[], create rejected
                "no default region") AND wallet=$0 USDC, so Phase B (real spawn) is GATED on funding.
                "self-heals / refactors / self-replicates" = still aspirational until a child boots.
 LIVE & TRUE  = daily email report (anicca-report #231) ✓ · dashboard auto-update (anicca-cfo.json, CFO
                daily) ✓ · anicca-oss published (#229) ✓ · runtime self-monitors its own logs (friction) ✓.
 → Launch pitch must describe THIS state (or framed as the roadmap), not the target state, until PHASE 2
   battle-test (#332) proves "runs+earns every day ×7d". See § LAUNCH ACCEPTANCE MATRIX — do NOT post
   target-state claims as present-tense fact.
```

### § LAUNCH ACCEPTANCE MATRIX (the target pitch → the task that makes each line TRUE → checked-off when)
The target pitch (with `x体 / x円 / y円` placeholders) becomes 100% true **iff every row below is checked
off**. `x/y` are FILLED from MEASURED CFO/registry data at post-time — never invented. `#341 LAUNCH-GATE`
is blockedBy every claim-task; when it goes green, the pitch is fact and may be posted (with human OK).
```
 pitch line                                  →  task(s)                  →  checked-off WHEN (E2E proof)
 ────────────────────────────────────────────────────────────────────────────────────────────────────
 ①「公開しました」(published)                →  #333 (+#229 done)        →  anicca-oss public + installable
 ②「sub/APIkey/Base送金で起動」              →  #323 boot, #324 wallet   →  boot succeeds via EACH of 3 fuels
 ③「ローカル+クラウドで x体」                 →  #331 local, #327/#328/   →  registry shows x active across
                                                 #264 cloud                  Mac+Daytona/Akash; x = measured
 ④「平均月収 x円（コスト約 y円）」            →  #325 earn, #332 battle,  →  CFO dashboard real monthly x>y;
                                                 CFO (live)                  if not 黒字 → write honest/drop
   ↳ ④a Lancers channel scaffold (Wave 1) = anicca-earn-lancers skill registered,
        cron `0 10 * * *` JST in dry-run mode only. Row ④ does NOT advance here —
        advancement requires Wave 2 (anicca-earn-lancers-wave2-realsubmit) producing
        ≥1 real `applied` row + CFO bank deposit evidence.
        (Coconala + CrowdWorks join as ④b/④c in Wave 2 follow-ons.)
 ⑤a「行動ログ監視→エラー自己解決」           →  #335 (friction spec15 ✓) →  loop observed fixing a real error
 ⑤b「リファクタリング・自己改善」            →  #335, #336 self-manage   →  loop observed raising own quality
 ⑤c「クラウド上で自己増殖」(skill BUILT,     →  #327 replicate ✓skill,   →  a child spawns on Daytona/Akash,
      Phase B GATED on funding)                  #328 colony, #327c probe    own wallet + constitution hash.
                                                                             skills/spawn-child ships +
                                                                             unit-tests PASS; NOT checked-off:
                                                                             Daytona org has no region (needs
                                                                             billing) + wallet $0 → no live child
 ⑤d「メールで日次報告」                      →  #231 ✓ LIVE / #330 ◐     →  daily email arrives; #330 Hermes-native
                                                 (7d gate pending)           skill live (cron 0 6 * * *, sends from
                                                                             anicca-genesis@agentmail.to,
                                                                             X-Anicca-Origin: hermes-genesis).
                                                                             ◐ = impl + E2E done, awaiting 7
                                                                             consecutive send.ok=true before ✓
 ⑥「収益の一部をUBI・募金配布」              →  #326 payout, #284 spec14 →  a real payout tx observed on-chain
                                                                              [Wave 1 = anicca-payout-ubi skill scaffolding
                                                                               LIVE (dry-run + guard fail-closed + recipient
                                                                               live-validation wired); row stays NOT green
                                                                               until Wave 2 / Task 9 of 2026-06-04-
                                                                               constitution-payout.md lands the 0.01 USDC
                                                                               proof tx via wallet_lib.send_usdc()]
 ⑦「何兆体が協力して苦しみをなくす」          →  #334 forum, #337 swarm,  →  2+ instances coordinate via forum;
                                                 #338 roll-out               1 learning rolls out to all
 dashboard自動更新 (aniccaai.com/dashboard)   →  CFO daily (live)         →  ✓ already true
 ローカル github.com/Daisuke134/anicca-oss    →  #333 (#229 done)         →  ✓ repo live, installable pending
 クラウド aniccaai.com/install                →  #333 (#274 page done)    →  Hermes-install flow works E2E
 デモ動画 Youtube                             →  #340 LAUNCH-DEMO         →  YouTube URL exists
 ── FINAL ── 全行 ✓ or 正直な現在形に書換     →  #341 LAUNCH-GATE         →  human OK → post present-tense
```
> So: **"after implementing everything, is it checked off?" — YES.** Every pitch line maps to a task whose
> DONE condition IS that line's truth (E2E proof, not "code written" — HARD RULE #14). The ONE gap found
> (demo video had no task) is now #340. When #341 (blockedBy all claim-tasks) goes green, the pitch is
> fact. Until then it is posted as roadmap, or not at all.

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
   ║  LAYER 4: SERVICE PLATFORM            │     = ★ Coinbase AgentKit CDP Smart Wallet (MIT) — KYC-zero, ERC-4337 paymaster. Virtuals Protocol: DEFERRED until public OSS release (see 07 § 3.5). (see 07-HERMES-PIVOT.md § 3) ║
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
   ║  LAYER 3: RUNTIME (= Anicca's body)   │     = ★ Hermes Agent (NousResearch, MIT) — 1 daemon, N specialist profiles per instance (see 07-HERMES-PIVOT.md § 2) ║
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

## § 2. Layer 3 deep-dive — Hermes Agent (= 07-HERMES-PIVOT.md § 2 owns this)

Layer 3 RUNTIME is **Hermes Agent** (NousResearch/hermes-agent, MIT) since
2026-06-02. The previous Conway-Research/automaton fork plan has been moved
to `archive/CONWAY_RUNTIME_DEEPDIVE.md` per editing rule #2 (never silently
delete).

See `07-HERMES-PIVOT.md` § 2 for the full Hermes deep-dive:
- § 2.1 Why Hermes (20-framework comparison)
- § 2.2 Process anatomy (daemon + N specialist profiles per instance)
- § 2.3 /goal lifecycle (judge model, max_turns=50)
- § 2.4 Skill self-edit (after-action review)
- § 2.5 What Hermes lacks (= filled by L2 Anicca skills)
- § 2.6 Specialist profile roster (10 per instance — orch + 5 earn + cook + ubi + fixer + constitution)

---

## § 3. Layer 4 deep-dive — Coinbase AgentKit (= 07-HERMES-PIVOT.md § 3 owns this)

Layer 4 SERVICE is **Coinbase AgentKit CDP Smart Wallet Provider** (MIT) since
2026-06-02. The previous "Virtuals Protocol everything" plan has been moved to
`archive/VIRTUALS_PROTOCOL_PLAN.md` per editing rule #2.

Virtuals Protocol re-evaluation: deferred until public OSS code release
(no GitHub SDK as of 2026-06-02). See `07-HERMES-PIVOT.md` § 3.5 for trigger
conditions.

See `07-HERMES-PIVOT.md` § 3 for:
- § 3.1 Why AgentKit (Virtuals vaporware-risk analysis)
- § 3.2 Wallet bootstrap (KYC-zero, runs once)
- § 3.3 USDC inflow/outflow (file:line cited)
- § 3.4 Per-profile wallet inheritance (1 CDP signup → N smart wallets)
- § 3.5 Virtuals — when to revisit
- § 3.6 Cloud spawn (deferred to spec 05)

---

## § 4. Layer 1 deep-dive — Brain (Kimi K2.6 via OpenRouter primary)

Brain primary is **Kimi K2.6 via OpenRouter** (USDC prepaid topup = NHOSS-pure)
since 2026-06-02. See `07-HERMES-PIVOT.md` § 4 for full routing matrix + per-
profile model selection.

Pricing snapshot (OpenRouter 2026-06-02, verified):

| Model | $/Mtoken in/out | Context | Role |
|---|---|---|---|
| Kimi K2.6 Thinking | $0.68 / $3.42 | 262K | primary |
| Qwen3.7 Max | $1.25 / $3.75 | 1M | fallback / long-ctx |
| DeepSeek v4-pro | $0.435 / $0.87 | 1M | cheapest |
| Claude Opus 4.8 | $5 / $25 | 1M | spike only |
| GPT-5.5 | $5 / $30 | 1.05M | spike only |

Source: openrouter.ai/api/v1/models / livebench.ai / swebench.com

---

## § 5. Layer 2 deep-dive — Surface (= the 4 sub-layers, NHOSS canonical)

> **Reframe (2026-06-01):** life-manager is NOT part of NHOSS. It moved to
> `~/.openclaw` and stays there as Dais's personal companion (see § 8.1).
> NHOSS Anicca's hands are 4 sub-layers: Redistribute (mission), Earn,
> Cook+Imitate, and Meta-Aware.

### § 5.1 Skill format (= Hermes / agentskills.io — see § 1.0)

> v3.5: skills live in `~/.hermes/skills/<name>/SKILL.md` (agentskills.io standard, progressive
> disclosure, agent-self-editable). name+description minimum. The L2 inventory below maps onto these.
> wallet / x402 / self-replication / constitution-guard are PORTED from automaton (MIT). The L2d
> Meta-Aware block IS the eval-loop (judge → 0.7 gate → regression → prod-monitor → failure-as-testcase).

(legacy note, kept for lineage — original wording was "Conway's format"; the YAML-frontmatter+MD shape is
the same, only the home dir and standard name changed.)

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

## § 9. Migration plan — superseded by 07-HERMES-PIVOT.md § 5 (Day 1 bootstrap)

The 14-day Day-by-Day plan (v3.0 § 9 with Conway substrate) is replaced by the
Hermes pivot bootstrap in `07-HERMES-PIVOT.md` § 5 (= curl one-liner install,
Bitwarden vault, 10-profile create loop, launchd daemon).

Original 14-day Conway plan moved to `archive/CONWAY_RUNTIME_DEEPDIVE.md`.

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

- We do not run Conway runtime (= moved to archive 2026-06-02). Hermes Agent is L3.
- We do not commit wallet/money to Virtuals (no OSS code). AgentKit is L4.
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
| **Conway** | (archived 2026-06-02) was the runtime substrate candidate; replaced by Hermes Agent per spec 07. |
| **Hermes** | the autonomous agent harness (NousResearch/hermes-agent, MIT) running each Anicca instance; 1 daemon hosts 10 specialist profiles per spec 07 § 2.6. |
| **AgentKit** | Coinbase Developer Platform Smart Wallet Provider (MIT) at github.com/coinbase/agentkit; provides L4 service per spec 07 § 3. |
| **Daytona** | AGPL-3.0 sandbox provider (github.com/daytonaio/daytona) for cloud spawn primary; Akash fallback. See spec 05. |
| **Specialist profile** | one of 10 Hermes profiles per Anicca instance (orch + 5 earn + cook + ubi + fixer + constitution). See spec 07 § 2.6. |
| **Instance** | 1 Daytona sandbox = 1 Hermes daemon = 10 profiles = 1 wallet. |
| **Colony** | N instances spawned over time; each instance Daytona-isolated. |
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
6. § 2-5 — Layer deep-dives for the specific layer you're touching today. Read `07-HERMES-PIVOT.md` for L3/L4/brain/profile decisions BEFORE 02/03 deep-dives.
7. § 7 — Money flow when wiring revenue or spend
8. § 12 — Verification gates before saying "done"

Read what's relevant. Don't memorize what isn't.

---

**END OF v3 MASTER SPEC.**

All earlier `ANICCA_*` specs in `archive/` are historical. This file overrides
them where they conflict.
