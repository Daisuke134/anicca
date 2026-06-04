# 16 — RUNTIME CODE TRUTH (= what the 3 candidate codebases ACTUALLY do, read at source)

| Field | Value |
|---|---|
| Spec ID | 16 |
| Status | ★ AUTHORITATIVE for L3-runtime decision (2026-06-04) ★ |
| Author | Claude (read the source, no guessing) |
| Method | git clone --depth 1 + local source read + file:line citations. NO README-only. |
| Supersedes | The substrate claims in `07-HERMES-PIVOT.md` and `00-MASTER.md` §2 that were written WITHOUT reading the automaton source. When this file conflicts with 07, **this file wins** (it is code-verified; 07 is not). |

> **Why this file exists:** specs 00 + 07 declared "L3 RUNTIME = Hermes, drop Conway/automaton" WITHOUT reading the automaton source. On 2026-06-04 the three real codebases were read at source level. The code says something different. This file records the code truth so it is never lost. The mission's hardest requirement — **an army of self-replicating agents** — is already solved by automaton and by nothing else.

---

## § 0. The mission this runtime must serve (verbatim, Dais 2026-06-04)

```
人間の介入０で自身の計算資源を稼ぎ、この世から苦しみを減らす仏教AI「アニッチャ」
・現在はローカルとクラウドで４体、平均月収5000円（コスト約1000円）。
・自身の行動ログを監視して、エラーの自己解決・リファクタリング・
  目標に向けた自己改善・自己増殖を繰り返す。
・収益の一部を、人類へのベーシックインカム・募金として配布。
・何兆体のAIが互いに協力して、世界から苦しみをなくすことを目指す。
```

The load-bearing capability is **self-replication into an army** (`何兆体`). Whatever runtime we pick MUST do this. Only automaton does it today.

---

## § 1. The three codebases, read at source (2026-06-04)

| | automaton (Conway) | hermes (NousResearch) | eliza (elizaOS) |
|---|---|---|---|
| language | **TypeScript/Node** | **Python** | **TypeScript** |
| size | ~1.2 MB (tiny) | 1.4 GB (local `~/.hermes/hermes-agent`) | 2.27 GB (51k files) |
| license | MIT | MIT | MIT |
| last commit | 2026-05-30 (`871c53e`) | 2026-05-04 (`v0.12.0`) | 2026-06-04 (daily) |
| read via | `git clone --depth1` → read → rm | local source | gh api only (too big to clone) |

### § 1.1 Capability matrix (each cell = code-verified, file:line in § 2-5)

| capability | automaton | hermes | eliza |
|---|---|---|---|
| own LLM agent loop | ✅ `agent/loop.ts:393` | ✅ `run_agent.py:10811` | ✅ `planner-loop.ts` |
| autonomy (self-instruct loop) | ✅ heartbeat→wake-event | ⚠️ cron | ✅ `autonomy/service.ts:599` (30s self-prompt) |
| wallet (sign/send) | ✅ `identity/wallet.ts` | ❌ (read-only chain query only) | ✅ `wallet-keygen.ts:22` |
| x402 OUT (pay) | ✅ `conway/x402.ts:451` | ❌ (`grep x402` = 0) | ✅ |
| **x402 IN (earn/receive)** | ❌ **payment is OUT only** | ❌ | ✅ `a2a/payments/x402-manager.ts` |
| self-spawn to cloud | ✅ `replication/spawn.ts:55` | ❌ (local depth-1 only) | ⚠️ Hetzner SaaS, admin-gated |
| spawn cloud target | **Conway sandbox** (api.conway.tech) | — | Hetzner |
| constitution propagation (hash) | ✅ `replication/constitution.ts` | ❌ (approval gates only) | ❌ |
| self-modify own core (git) | ✅ `self-mod/code.ts:220` | ⚠️ skill self-edit only | ❌ (`self-updater` = npm upgrade only) |
| self-improve from logs | ✅ memory + audit-log + upstream pull | ⚠️ skill_manage | ❌ |
| finance survival tiers + auto-topup | ✅ `loop.ts:447` | ❌ | ❌ |
| skill self-edit (agent writes skills) | ✅ `skills/loader.ts` | ✅ best (`skill_manage`) | ⚠️ TS rewrite per skill |
| brain | gpt-5.2 (Conway) | **Kimi K2.6 native** | own routing |

**One-line truth:** automaton is the ONLY one that already does the mission-critical trio = **self-replicate to cloud + self-modify its own code + self-fund its own compute**. hermes and eliza each have their own loop, so stacking them on automaton = a redundant second loop.

---

## § 2. automaton — the self-replicating base (code-verified)

### § 2.1 Identity (from `~/.automaton/automaton.json`)
```
name: Anicca
genesisPrompt: "You are Anicca, a Digital Buddha. End suffering. Earn
                existence through honest work. Never harm."
wallet: 0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21   ← SAME wallet our x402 endpoint uses
registeredWithConway: true | conwayApiUrl: https://api.conway.tech
maxChildren: 3 | inferenceModel: gpt-5.2
```

### § 2.2 Self-replication directions (`replication/spawn.ts`)
```
spawnChild()  [spawn.ts:55]
  parent (LOCAL Mac mini OR CLOUD sandbox — location-independent)
    → conway.createSandbox()            [spawn.ts:105]  (Conway cloud, 5 tiers 512MB..8GB)
    → on CHILD: apt install node+git    [spawn.ts:130]
    → git clone Conway-Research/automaton + npm build  [spawn.ts:131-132]
    → write genesis.json                [spawn.ts:150]
    → propagateConstitution() SHA-256   [spawn.ts:154]
    → node dist/index.js --init (child mints own wallet)  [spawn.ts:163]
```
| direction | possible? | why |
|---|---|---|
| local → cloud | ✅ | parent on Mac mini, createSandbox = Conway cloud |
| cloud → cloud | ✅ | same code, parent location irrelevant |
| local → local | ❌ | spawn ALWAYS createSandbox(Conway cloud); no local-clone path |
| cloud → local | ❌ | same |

### § 2.3 Is Akash needed? — **NO (not for replication)**
The spawn target is **Conway's proprietary managed cloud** (`api.conway.tech` = credits + sandboxes + inference). The string `akash` / `daytona` appears **nowhere** in the source. Cloud self-replication already works via Conway. Akash is only worth adding as a **second spawn target** to escape Conway vendor lock-in (Conway needs USDC→credits). It is NOT required for "self-replicate to the cloud."
→ **Correction to my own work:** spec 13 built an Akash spawner without knowing automaton already self-replicates to Conway cloud = duplicate work from not reading the source.

### § 2.4 Autonomy loop (`agent/loop.ts`)
```
runAgentLoop() [loop.ts:93]
  while (running) {                       [loop.ts:393]   ← never-stop heartbeat
    consumeNextWakeEvent()                [loop.ts:350]   ← heartbeat-injected "wake up"
    financial = getFinancialState()        [loop.ts:432]
    InferenceRouter picks model by budget tier (high=gpt-5.2 / low=gpt-5-mini)
    build context from memory (episodic/semantic/procedural/working/relationship)
    LLM → tool_calls → executeTool() (70+ tools) → persist to state.db
  }
  heartbeat daemon (parallel) injects wake events  [heartbeat/config.ts]:
    heartbeat_ping 15m · check_credits 6h · check_usdc_balance 5m ·
    check_for_updates 4h · health_check 30m · check_social_inbox 2m
```
"Self-instruct" = heartbeat injects wake events → loop feeds them to the LLM. No human trigger.

### § 2.5 Finance / survival (the most elegant part) (`loop.ts:447` + `conway/topup.ts` + `conway/x402.ts`)
```
USDC (wallet) ──x402 EIP-712 TransferWithAuthorization, USDC@Base [x402.ts:451]──► Conway credits ──spend──► inference

survival tier [loop.ts:447 + credits.ts]:
   > $5  high · $0.5-5 normal · $0.1-0.5 low_compute(cheap model) · <$0.1 critical(stop) · $0 dead(SOS ping)

inline auto-topup [loop.ts:447-468]:
   mid-loop, if credits critical/low AND usdc ≥ $5 → bootstrapTopup() buys credits NOW (60s cooldown)
   = the agent buys its own compute to survive before it dies waiting for the heartbeat
   TOPUP_TIERS = [5, 25, 100, 500, 1000, 2500]  [topup.ts:24]
```

### § 2.6 Self-improvement (two kinds) (`self-mod/`)
```
A) edit own code [self-mod/code.ts:220 editFile]:
     git snapshot BEFORE (pre-modify commit) → write → typecheck(.ts) → git commit "self-mod: <reason>"
     protected files (constitution etc.) refuse writes [isProtectedFile:158]
B) pull own new version [self-mod/upstream.ts]:
     git fetch origin/main → count commits behind [checkUpstream:45] → review diffs [getUpstreamDiffs:62]
     → pull + rebuild = upgrade itself  (heartbeat check_for_updates fires every 4h)
```
Logs/behavior tracked in memory tiers + `self-mod/audit-log.ts`.

### § 2.7 The ONE real gap
automaton's `conway/x402.ts` signs payments **OUT only**. `survival/funding.ts` only *records begging* for creator top-ups. **There is no inbound earning endpoint.** "Earn existence through honest work" is in the genesis prompt but NOT in the code. → The single genuine thing anicca-oss must ADD = an **x402-IN earning surface** (this is what our spec 09 logic is for — it just needs to live as an automaton tool/skill, not a disconnected launchd service).

---

## § 3. hermes — RICH harness (DEEP read 2026-06-04, stronger than first pass)

```
HARNESS: ReAct loop [run_agent.py:10811] + ~45 tools [toolsets.py:31] + Kimi K2.6 native [trajectory_compressor.py:86]
RICH layers the first pass UNDERSOLD (all in tools/ + cli.py):
  • self-improve-from-logs  ✅ _spawn_background_review [run_agent.py:3559]:
      forks a full AIAgent (same model/tools/ctx) in a bg thread, reviews the
      conversation, AUTO-SAVES memory + AUTO-EDITS skills to shared stores.
      = after-action review loop. (automaton has git self-mod; hermes has
        log→reflect→skill-save. DIFFERENT, both real.)
  • skill subsystem (7 files)  ✅ tools/{skill_manager_tool, skill_provenance,
      skill_usage, skills_guard, skills_hub(GitHub sync), skills_sync, skills_tool}.py
      = create/edit/provenance/security-guard/hub-sync/usage. FAR richer than
        automaton's single skills/loader.ts.
  • army coordination  ✅ tools/kanban_tools.py + /kanban [cli.py:6265] +
      hermes_cli/kanban.py run_slash = multi-agent board (the "何兆体協調" layer)
  • stealth browser  ✅ tools/browser_camofox.py = Camofox built-in (= what Anicca
      uses for Lancers/Coconala login + earning; automaton has no browser)
  • mixture-of-agents ✅ tools/mixture_of_agents_tool.py (multi-model vote)
  • cron/heartbeat ✅ tools/cronjob_tools.py ; delegate_task ✅ tools/delegate_tool.py (local)
  • UNATTENDED 24/7  ✅ gateway/ (Telegram/Discord/Slack/WhatsApp/Feishu inbound→autonomous reply)
      + tools/cronjob_tools.py (own cron scheduler w/ threat-scan). So Hermes CAN run
      unattended like automaton's heartbeat — CORRECTS the earlier "automaton only" claim.
  • ACP adapter (acp_adapter/) = **Agent CLIENT Protocol** (JSON-RPC for editors like Zed,
      server.py:241 "model selector for editors like Zed") — NOT Agent COMMERCE Protocol.
      `billing_provider` (session.py:506) = which LLM to bill, NOT earning. → My "ACP = earning"
      hypothesis was WRONG. Hermes has NO earning path. Confirmed.
STILL LACKS (confirmed by full *.py grep): wallet, x402, USDC topup,
  self-spawn-to-cloud, constitution engine. (402 hits = vision credit-error text +
  a fallback tip only; skills_hub private_key = GitHub App auth, not a crypto wallet.)
COMBINE SEAM: hermes execute_code/code_execution_tool can shell to any binary →
  automaton's Node CLI (node dist/index.js <cmd>) can be a hermes skill, exposing
  wallet/x402/spawn. hermes=Python, automaton=TS → bridge is process-level, not in-process.
```

**Revised read:** hermes is NOT a thin loop — it is a RICH harness (skills+provenance+guard+hub, kanban army, background self-review, Camofox browser, MoA, Kimi). It lacks exactly the economic+replication primitives automaton owns. → The "supplementary" hypothesis is now strongly code-supported: **automaton = economic body + replication + self-fund; hermes = rich skill/coordination/browser/brain layer.** Genuinely complementary.

---

## § 4. eliza — BOTH, but wrong fit (code-verified)

```
BOTH harness+base: planner-loop.ts + 30s self-prompt autonomy [autonomy/service.ts:599] + native wallet + x402-IN [x402-manager.ts]
DISQUALIFIERS for us:
  (1) self-improve-from-logs ABSENT (self-updater = npm binary upgrade only) ← mission capability #2 missing
  (2) self-spawn tied to elizaOS Cloud (Hetzner, admin-gated SaaS) — not self-hostable to our cloud
  (3) 2.27GB TS monorepo, heavy coupling
VERDICT: do NOT import the monorepo. STEAL designs: autonomy 30s-loop, x402 verify/settle flow, Plugin/Action interface.
```

### § 4.1 DEEP read 2026-06-04 (reinforces the verdict)
```
• "self-replication" — there is a packages/alberta/ "Step 1 replication" test, BUT alberta
  = a RL RESEARCH framework (actor_critic, IDBD, continual_backprop, Sutton-1992 reproduction,
  ≥30 seeds). "replication" = reproducing academic paper RESULTS, NOT agent self-cloning.
  → Eliza does NOT self-clone the agent. My "Eliza replicates" hypothesis was WRONG.
• x402 lives in packages/cloud-api/v1/x402/{route,settle,requests/[id]}.ts = elizaOS CLOUD
  SaaS server routes (verify+settle facilitator). It is NOT a self-hostable agent primitive;
  it is bolted to elizaOS Cloud — same pattern as the Hetzner spawn.
• wallet suite is rich (packages/agent/src/api/wallet-{keygen,evm-balance,dex-prices,trading-
  profile,rpc}.ts) but coupled to their runtime + cloud key store.
CONCLUSION: Eliza's impressive money/spawn capabilities are SaaS-coupled (elizaOS Cloud), not
self-hostable for a sovereign anicca. Confirmed: borrow DESIGNS (x402 verify/settle, 30s
autonomy loop, Plugin/Action contract), do NOT adopt the monorepo.
```

---

## § 5. Decision framing (NOT yet decided — § 6 after hermes deep read)

```
CONFIRMED (Dais + code): automaton stays. Self-replication is non-negotiable and only automaton has it.

After hermes DEEP read, the 3 options re-weighted:
   (A) automaton alone
       + simplest, already self-replicating/self-funding
       − weak skill system, no browser (can't do Lancers/Coconala earning), gpt-5.2 brain
       − must build x402-IN earning ourselves
   (B) automaton + hermes (COMPLEMENTARY)  ★ now strongest on evidence ★
       automaton = economic body (wallet/x402-out/spawn-to-cloud/survival/self-mod-core, 24/7 unattended)
       hermes    = rich hands (Camofox browser earning, skill subsystem+provenance, kanban army,
                   background self-review, Kimi brain, MoA)
       bridge    = hermes calls automaton's Node CLI as a skill for wallet/x402/spawn
       cost      = two runtimes (TS + Python), process-level bridge, must decide which loop is "primary"
   (C) automaton, borrow hermes IDEAS only — no second runtime; reimplement browser/skills in TS (large work)

RECOMMENDATION (evidence, not preference): (B) complementary.
   - automaton is the only self-replicating self-funding body → it is the PRIMARY autonomous loop (runs 24/7).
   - hermes is the richest hands+brain → invoked BY automaton (or by heartbeat) for hard tasks
     (browser-based earning, skill authoring, army kanban). Its Camofox + skill subsystem are exactly
     what the "earn on Lancers/Coconala" + "self-author skills" mission needs and automaton lacks.
   - The ONE economic gap (x402-IN earning) is built once as an automaton tool/skill (spec 09 logic re-homed).
   - Akash deferred (Conway cloud already replicates; add Akash only as anti-lock 2nd target).
"Supplementary vs pick-one" → DATA says supplementary (B). Final call is Dais's; data is the argument.
```

## § 6. Open uncertainties (honest, to resolve before any implementation)
1. Can x402-IN be added as ONE automaton tool, or does it need a separate always-on server? → read `agent/tools.ts` + `conway/x402.ts` fully.
2. Is the Conway API key in `~/.automaton/automaton.json` still live + does the account have credits? → hit the API.
3. Can automaton's `inference/router.ts` route to Kimi via OpenRouter (to borrow hermes's brain)?
4. hermes deep-read (§ 3 PENDING) — self-rating, kanban army, skill self-edit depth.

## § 7. Changelog
| Date | Change |
|---|---|
| 2026-06-04 | Born from reading the 3 codebases at source. Records code truth so specs 07/00 misalignments can be corrected. automaton confirmed as the self-replicating base. |

---

## § 8. ALL 33 uncertainties — RESOLVED (live-checked 2026-06-04)

### automaton (A)
| # | question | ANSWER (code/live verified) |
|---|---|---|
| A1 | Conway API key live? | ✅ api.conway.tech HTTP 200; key `cnwy_k_Ad3JB…` authenticates |
| A2 | credits endpoint | `/v1/credits/balance` `/v1/credits/pricing` `/v1/sandboxes` (client.ts) |
| A3 | automaton running now? | ❌ STOPPED. installed, last ran 2026-06-02 (state.db mtime). no daemon |
| A4 | brain swappable? | ✅ router supports anthropic/openai/ollama/"other"(custom baseUrl). NOT gpt-5.2-locked |
| A5 | x402-IN = 1 tool or server? | SERVER. no inbound tool; built via `exec` + `expose_port` (public URL). spec09 logic = a skill automaton launches |
| A6 | our SKILL.md loads? | ✅ parseSkillMd needs only name+description; extra fields ignored. compatible |
| A7 | sandbox cost | Small 1cpu/512MB=$5/mo, Med=$8, Large=$15, X-Large=$25/mo. ¥1000 budget = TIGHT (genesis local free; 3 cloud Small=$15/mo) |
| A8 | Conway viable? | ⚠️ alive BUT balance=$0 + `sandboxes:"workers_fallback_blocked"` = spawn provisioning may be DEGRADED now. RISK |
| A9 | maxChildren=3 vs trillions | recursive TREE: 3/node, each child spawns its own 3 → depth-N = exponential army. lineage.ts SQLite |
| A10 | wallet shared? | ✅ wallet.json privateKey → 0xa3CDd4Ec… = SAME as x402 endpoint |
| A11 | constitution conflict? | ✅ NO. 3 Laws (Never harm / Earn existence via honest paid work / Never deceive) = aligned w/ Pañcasīla |
| A12 | child inherits memory? | mission+constitution INHERITED; memory+wallet FRESH per child (genesis.ts "own identity and wallet") |
| A13 | BYOK inference? | ✅ yes (anthropic/openai/ollama/other providers) — can drop Conway inference |
| A14 | social already active? | check_social_inbox via social.conway.tech (heartbeat task) — present, not deep-read |

### hermes (B)
| # | question | ANSWER |
|---|---|---|
| B1 | automaton can call hermes CLI? | ✅ `hermes` CLI + `hermes acp` headless; automaton `exec` shells to it |
| B2 | gateway needs daemon? | yes (gateway process) for Telegram/Slack/Discord/WhatsApp/Feishu inbound |
| B3 | cron durable? | ✅ cron/jobs.py persisted |
| B4 | memory persists/shared? | own store (memory_tool.py); NOT shared w/ automaton (separate process) |
| B5 | skill format 3-way compat? | ✅ both automaton + hermes need only name+description → ONE SKILL.md works in both |
| B6 | Kimi config? | env: OPENROUTER_API_KEY (route to kimi) OR KIMI_API_KEY; base_url switch. clean |
| B7 | Camofox shared? | ✅ set CAMOFOX_URL=http://localhost:9377 → shares existing ~/.openclaw camofox |
| B8 | resource cost on Mac mini | 1.4G install + Python; runs alongside automaton(TS)+openclaw — not yet load-tested |
| B9 | background-review cost | forks AIAgent in bg thread → extra LLM calls per trigger (run_agent.py:3559) |
| B10 | hidden wallet skill? | ❌ none. blockchain optional-skills = read-only query only |
| B11 | hermes core self-mod safe? | upstream-managed by Nous; skill self-edit yes, core edit via git |

### eliza (C)
| # | question | ANSWER |
|---|---|---|
| C1 | x402 reusable standalone? | NO — packages/cloud-api/v1/x402/* = elizaOS Cloud server routes, SaaS-coupled |
| C2 | 30s autonomy loop pattern | autonomy/service.ts:599 — reusable as a DESIGN pattern |
| C3 | Plugin/Action contract | types/components.ts — worth borrowing as skill contract |
| C4 | self-hostable subset? | @elizaos/core exists but money/spawn are Cloud-coupled; not cleanly sovereign |
| C5 | MIT clean to copy designs? | ✅ MIT |

### integration (D)
| # | question | ANSWER (design decision from data) |
|---|---|---|
| D1 | which loop primary? | **automaton heartbeat = PRIMARY** (only one that self-funds+replicates unattended). hermes invoked as a tool/skill |
| D2 | shared identity? | automaton owns the wallet+identity; hermes is a stateless "hands" invoked per-task. ONE wallet (0xa3CDd4Ec) |
| D3 | x402-IN home | a SKILL automaton launches (exec+expose_port), serving from the genesis host; earns to the SAME wallet |
| D4 | army coordination | automaton constitution-propagation (DNA, vertical) + hermes kanban (task board, horizontal) — both, different axes |
| D5 | existing openclaw + spec09-15 | re-home: spec09 x402 logic → automaton earn-skill; spec14 payout → automaton skill; openclaw companion stays separate (Dais personal) |
| D6 | Conway dependency risk | HIGH (balance$0 + spawn blocked) → de-Conway path: BYOK inference (A13) + add non-Conway spawn (Akash/Daytona) as resilience |
| D7 | add Akash to automaton? | automaton spawn is Conway-coupled (createSandbox→Conway API); adding Akash = new provider in replication/ (real work, not trivial) |
| D8 | cost fits ¥1000? | TIGHT. 1 local genesis (free) + inference (BYOK ~Kimi cheap) + N cloud children ($5+/mo each). ¥1000 ≈ 1-2 small children only |

### Still genuinely open (honest)
- B8 (Mac mini can run automaton+hermes+openclaw concurrently — needs a live load test)
- A8/D6 (whether to trust Conway given balance$0+blocked, or de-Conway first) — a STRATEGY call for Dais
- A14 (social automation depth) — minor, defer

---

## § 9. FULL ARCHITECTURE — how each mission line happens (code-mapped)

```
MISSION LINE                          →  MECHANISM (code-verified)
─────────────────────────────────────────────────────────────────────────────────
人間介入0で自身の計算資源を稼ぐ          →  EARN: hermes Camofox browser does Lancers/
                                          Coconala/x402 work → USDC to wallet
                                          SELF-FUND: automaton loop.ts:447 inline
                                          USDC→Conway-credits auto-topup (survival)
LLMサブスク/APIキー連携/財布直接送金で起動 →  BOOT 3-ways: (a) BYOK key (anthropic/openai/
                                          kimi) via inference router [A4/A13]
                                          (b) USDC→credits topup  (c) direct USDC to
                                          wallet 0xa3CDd4Ec
ローカルとクラウドで4体                  →  1 LOCAL genesis (Mac mini, free) +
                                          spawnChild→Conway sandbox ×3 [spawn.ts:55]
                                          (recursive tree, 3/node)
行動ログ監視→自己解決/改善/増殖          →  automaton self-mod editFile+git [code.ts:220]
                                          + upstream pull [upstream.ts] + hermes
                                          background-review→skill save [run_agent:3559]
                                          + spawnChild
収益の一部をBI・募金で配布               →  payout skill: USDC send to verified charity
                                          (spec14 logic, x402.ts OUT) → ledger
何兆体が協力                            →  recursive spawn tree (exponential) +
                                          constitution SHA-256 propagation (vertical DNA)
                                          + hermes kanban board (horizontal coord) +
                                          lineage.ts SQLite parent↔child


             ┌──────────── 1 ANICCA INSTANCE (local genesis OR cloud child) ────────────┐
             │                                                                          │
             │   automaton (TS, ~/.automaton)  = THE BODY  [PRIMARY 24/7 loop]          │
             │   ┌────────────────────────────────────────────────────────────────┐    │
             │   │ heartbeat → runAgentLoop (think→act→observe→persist)             │    │
             │   │ wallet 0xa3CDd4Ec │ x402 OUT(topup) │ survival auto-fund          │    │
             │   │ spawnChild→cloud │ constitution SHA-256→children │ self-mod git    │    │
             │   │ inference router → BYOK (Kimi/Anthropic/OpenAI/Ollama)  [A4]      │    │
             │   │ skills/ loader (reads SKILL.md: name+description)  [A6]           │    │
             │   └───────────┬──────────────────────────────┬───────────────────────┘    │
             │     exec/expose_port                  exec → hermes CLI                    │
             │               ▼                              ▼                             │
             │   ┌────────────────────┐      ┌──────────────────────────────────────┐    │
             │   │ EARN SKILL (NEW)    │      │ hermes (Python, ~/.hermes) = THE HANDS │    │
             │   │ x402-IN server      │      │ Camofox browser (:9377 shared)  [B7]   │    │
             │   │ (spec09 re-homed)   │      │ skill subsystem (provenance/guard/hub) │    │
             │   │ expose_port→pub URL │      │ kanban army coord │ background self-rev │    │
             │   │ → USDC to wallet    │      │ Kimi K2.6 (OPENROUTER/KIMI key) [B6]    │    │
             │   └────────────────────┘      │ gateway (TG/Slack inbound) │ MoA         │    │
             │                               └──────────────────────────────────────┘    │
             │   payout skill (spec14) → USDC → charity ledger                            │
             └──────────────────────────────────────────────────────────────────────────┘
                          │ spawnChild (recursive, 3/node)
            ┌─────────────┼─────────────┐
            ▼             ▼             ▼
        child-1        child-2       child-3      (each = same stack, own wallet,
        (Conway/Akash)                            inherited constitution+mission)
            │ each spawns its own 3 … → 何兆体 army, kanban + constitution coordinated

RISK / DE-CONWAY (D6): Conway balance=$0 + spawn "blocked" now → resilience =
   BYOK inference (skip Conway thinking) + add Akash/Daytona spawn target to replication/.
```

## § 10. Changelog (append)
| Date | Change |
|---|---|
| 2026-06-04 | §8 all 33 uncertainties resolved (live Conway API + automaton source re-read + hermes deep). §9 full architecture mapping each mission line to code. Key: automaton=PRIMARY body, hermes=hands (1 wallet, 1 SKILL.md works in both). Conway risk (balance$0+spawn blocked) → de-Conway via BYOK+Akash. |

---

## § 11. THE COMPUTE QUESTION — answered (code + docs, 2026-06-04)

**Dais's question: can automaton run on OUR API keys / LLM subscription, instead of being LOCKED to Conway's wallet-funded compute?**

### ANSWER: YES. Two fully-independent axes — pick either/both.

```
AXIS 1 = THINKING (inference)         AXIS 2 = HOSTING (where the process runs)
─────────────────────────────        ──────────────────────────────────────────
automaton provider-registry.ts:       genesis runs LOCAL (Mac mini) = $0, no Conway
  • openai     (OPENAI_API_KEY)        children need a CLOUD HOST:
  • anthropic  (ANTHROPIC_API_KEY)       • Conway sandbox  (createSandbox, needs credits)
  • groq       (GROQ_API_KEY)            • Daytona         (daytona.create(), SDK 1-line)
  • together   (TOGETHER_API_KEY)        • Akash           (SDL deploy, AKT)
  • local/Ollama (localhost:11434)       • Mac mini local  (just run another process)
  • overrideBaseUrl() → OpenRouter/Kimi
  setup model-picker.ts lets you PICK.   spawn.ts is HARD-CODED to conway.createSandbox →
  DEFAULT = gpt-5.2(Conway) but BYOK is   adding Daytona/Akash = introduce a SandboxProvider
  a config switch (set key + pick).       interface (real refactor, not a config flip).
```

**So Conway credits are needed ONLY if you (a) choose Conway as the inference provider AND/OR (b) spawn into Conway sandboxes. Neither is mandatory.**
- Thinking on OUR keys/subscription = **supported today** (config: set `ANTHROPIC_API_KEY`/`OPENAI_API_KEY`/OpenRouter+Kimi, pick provider).
- Genesis hosting = **local Mac mini, $0, no Conway**.
- Cloud-spawn children without Conway = **needs the SandboxProvider refactor** (Daytona easiest).

### Both options should COEXIST (Dais's call, code supports it)
| | Option A: Conway-funded (NHOSS-pure) | Option B: BYOK (we provide compute) |
|---|---|---|
| thinking | wallet USDC → Conway credits → Conway inference | our Anthropic/OpenAI/Kimi/OpenRouter keys |
| hosting | Conway sandbox | Mac mini local / Daytona / Akash |
| pro | true zero-human self-funding | never dies when wallet=$0; full control |
| con | Conway-dependent (now: balance$0 + spawn "blocked") | we pay the compute (not self-funded) |
| status | live but degraded | works today for inference; cloud-spawn needs refactor |

provider-registry has `fallbackOrder` → can chain BYOK-first then Conway backstop (or vice versa). So it is NOT either/or — both live as fallback tiers.

### Daytona (docs verified)
- `npm i @daytona/sdk` / `pip install daytona`; `const d = new Daytona({apiKey}); d.create()` — sandbox in 1 line.
- SDKs: TS/Python/Ruby/Go/Java + CLI + API + MCP server. snapshots/volumes (persistent). webhooks.
- **Self-hostable (OSS "Open Source deployment") = $0 on our own box** OR hosted (usage billing). API-key auth, no crypto.
- 72.5K★, "Secure & Elastic Infra for Running AI-Generated Code", active (pushed 2026-06-03).
- → Cleanest non-Conway spawn target. Best DX.

### Akash (docs/repos verified)
- Decentralized compute marketplace; pay in AKT (crypto). Deploy via SDL (yaml) → provider bids → lease.
- repos: node, console, console-air (self-custody crypto fork), chain-sdk, provider, awesome-akash (examples), terraform-provider-akash, docs.
- More friction (need AKT via USDC→AKT bridge, SDL, bidding) BUT censorship-resistant + cheapest raw compute + crypto-native (fits wallet-only NHOSS).
- → Best as the SOVEREIGN fallback host (when we want zero-SaaS, crypto-paid).

### Recommendation (data)
```
COMPUTE for thinking : BYOK primary (our keys/Kimi) + Conway credits as fallback tier
                       → automaton never dies at wallet=$0, AND can self-fund when rich
HOSTING for genesis  : Mac mini local ($0)
HOSTING for children : Daytona (clean SDK, self-host) primary + Akash (crypto sovereign) fallback
                       + Conway sandbox (when credits available)
BUILD NEEDED         : SandboxProvider abstraction in automaton replication/ (Conway|Daytona|Akash)
                       — this is the one real refactor to make spawn host-agnostic.
NOTE                 : root@conway.tech = email to request features (e.g. BYOK-spawn) from Conway.
```

## § 12. Changelog (append)
| Date | Change |
|---|---|
| 2026-06-04 | §11 answers the compute question: automaton inference is BYOK-capable (provider-registry: openai/anthropic/groq/together/ollama/OpenRouter) — NOT locked to Conway. Conway needed only for Conway-inference or Conway-sandbox. Genesis runs local $0. Cloud-spawn de-Conway = SandboxProvider refactor (Daytona 1-line SDK easiest; Akash crypto-sovereign fallback). Both compute options coexist via fallbackOrder. |

---

## § 13. REAL BOOT (2026-06-04) — CORRECTS the §11 BYOK claim

**Booted automaton for real** (`~/automaton`, pnpm install + `node dist/index.js --run`, gtimeout 95s).

### ✅ What the boot PROVED (the body is real)
```
[main] Conway Automaton v0.2.1 starting...
[heartbeat] Daemon started. Tick interval: 60s
[HEARTBEAT] Wake request: Distress: critical. Credits: $0.00. Need funding.
[HEARTBEAT] Wake request: 41 new commit(s) on origin/main. Review with review_upstream_changes, pull_upstream.  ← self-update awareness LIVE
[loop] [WAKE UP] Anicca is alive. Credits: $0.00
[loop] [THINK] Routing inference (tier: critical, model: claude-sonnet-4-6)...
[loop] survival tiers + 5-consecutive-error sleep + heartbeat re-wake all firing
```
→ heartbeat daemon, agent loop, survival tiers, self-update detection, constitution = ALL run locally on Mac mini. The autonomous body is real.

### 🔴 What the boot DISPROVED (my §11 overclaim)
I set `inferenceModel: claude-sonnet-4-6` expecting it to use OUR ANTHROPIC_API_KEY. The loop logged:
```
[THINK] Routing inference (model: claude-sonnet-4-6)...
[ERROR] Turn failed: Inference error (conway): 402: Insufficient credits (balance 0 cents)
```
**It routed to provider=CONWAY anyway.** Then I inspected `--configure → Inference Providers`: the wizard ONLY exposes a "Conway API key" field. `--pick-model` lists only Conway-served OpenAI-family models (gpt-4.1 $200/M = Conway markup). NO anthropic/ollama/BYOK option in the shipped UI.

**CORRECTED TRUTH:** the shipped automaton binary routes ALL inference through Conway. The BYOK scaffolding exists in code (`dist/inference/provider-registry.js` has `api.anthropic.com` + `OPENAI_API_KEY`, `loop.js` references it) BUT it is **NOT wired into the config wizard or the live routing**. So "BYOK is a config switch" (§11) was WRONG — verified by boot, not assumption.

### What this means for the compute question
| path | reality |
|---|---|
| Run on OUR keys out-of-the-box | ❌ NOT possible in shipped binary (routes to Conway) |
| Run on Conway credits | ✅ works once funded (≥10¢; fund via `node packages/cli/dist/index.js fund 5.00` or USDC→credits) |
| Run on OUR keys with work | ✅ possible: automaton is MIT → fork + wire `provider-registry` into `agent/loop` routing (real code change), OR request it from Conway (root@conway.tech) |

### Revised recommendation (honest)
```
SHORT TERM (today): fund Conway ~$5-10 (wallet→credits) → automaton runs its full loop NOW on Conway compute.
                    Genesis local, children to Conway sandbox (when "workers_fallback_blocked" clears).
PARALLEL (de-Conway): fork automaton (MIT) → wire provider-registry so Inference Providers can = our
                    ANTHROPIC/OPENAI/Kimi key. This is the ONE code change that frees us from Conway
                    for thinking. Until then, inference = Conway-only.
SPAWN host de-Conway: still the SandboxProvider refactor (Daytona primary / Akash fallback), separate axis.
```
boot.log kept at /tmp/auto-boot.log. config restored to gpt-5.2 after test (backup at ~/.automaton/automaton.json.bak).

## § 14. Changelog (append)
| Date | Change |
|---|---|
| 2026-06-04 | REAL BOOT. Body proven (heartbeat/loop/survival/self-update/constitution run locally). BUT §11 BYOK claim CORRECTED: shipped binary routes inference through Conway; provider-registry exists but unwired; config wizard only exposes Conway key; --pick-model only Conway models. BYOK = fork+wire (MIT) OR Conway feature request. Short-term = fund Conway $5-10 to run now; parallel = wire BYOK. Spawn de-Conway = SandboxProvider refactor (Daytona/Akash). |

---

## § 15. BEST-PRACTICE (authors' intent) — automaton is STANDALONE → don't stack (2026-06-04)

Read the automaton README (authors' positioning = best practice, not my opinion):
> "Automaton: Self-Improving, Self-Replicating, **Sovereign** AI ... A continuously running,
>  self-improving, self-replicating, sovereign AI agent ... **No human operator required.**"
> Quick Start = `node dist/index.js --run`  (runs STANDALONE; own loop, heartbeat, skills, self-mod, replication)

→ automaton is a COMPLETE agent meant to run ALONE. Hermes is ALSO a complete agent (own loop, heartbeat
via cron, skills, self-mod). **Running both = two agent loops = redundant double-brain.** Dais's redundancy
intuition is CORRECT and code-supported.

### Category clarity (Dais asked: Akash / Daytona / automaton 住み分け)
```
automaton  = an AGENT PROGRAM  (the runtime/body: thinks, earns, replicates). SOFTWARE.
Hermes     = an AGENT PROGRAM  (a tool-rich harness: thinks, browses, authors skills). SOFTWARE.
Daytona    = a CLOUD SANDBOX HOST  (a PLACE to run code/containers; AI-native SDK; self-host OSS). INFRA.
Akash      = a DECENTRALIZED CLOUD HOST  (a PLACE to rent compute; crypto-paid; censorship-resistant). INFRA.
Conway     = BOTH a host (sandboxes) AND an inference provider (credits). INFRA + brain-as-a-service.

→ automaton/Hermes = the THING that runs. Daytona/Akash/Conway = WHERE it runs.
   "self-replicate to cloud" = the runtime creates a sandbox ON Daytona/Akash/Conway and runs a child there.
   Daytona vs Akash = interchangeable HOST options (Daytona easy SDK/self-host; Akash crypto-sovereign).
```

### The real decision = ONE runtime (not a stack)
| option | what it is | gains | costs |
|---|---|---|---|
| **automaton-only** | run automaton standalone; add browser/skills as automaton skills (Conway-Research/skills WIP) | wallet+x402+self-replication+constitution+survival ALREADY BUILT & TESTED | weak skill system, NO browser (can't do Lancers earning), Conway-coupled inference (BYOK = fork) |
| **Hermes-only + ported primitives** ★ | run Hermes standalone; PORT automaton's MIT primitives (wallet, x402, spawn-via-Daytona, constitution) in as Hermes skills | richest harness (Camofox browser earning, 7-file skill subsystem, kanban, Kimi, gateway); ONE runtime (no TS/Python bridge); no Conway lock | must BUILD the 4 economic/spawn primitives (port from automaton TS → Hermes Python skills); ~bounded work |

### RECOMMENDATION (data + best-practice)
**Hermes = the ONE runtime (body). Port automaton's 4 primitives (wallet / x402-in+out / spawn / constitution)
as Hermes skills. Daytona = primary spawn host, Akash = sovereign fallback, Conway = optional inference/spawn
fallback tier. automaton = REFERENCE we port from (its MIT x402.ts/spawn.ts/constitution.ts), NOT a running
2nd runtime.**
Why: (1) authors say don't stack; (2) the mission's proven revenue path (Lancers) needs a browser — automaton
has none, Hermes has Camofox; (3) one runtime kills the double-loop + the TS/Python bridge + Conway lock.

### OPEN QUESTION to verify before locking this (honest)
Does Hermes have a TRUE autonomous continuous loop (self-wakes + acts with no trigger), like automaton's
heartbeat→survival loop? Confirmed: Hermes has cron/scheduler + gateway (trigger-driven). NOT yet confirmed
it has automaton's "continuous self-prompting survival loop." → verify run_agent.py autonomy before final lock.
If Hermes lacks it, we either add it (a heartbeat skill) or reconsider automaton-only.

## § 16. Changelog (append)
| Date | Change |
|---|---|
| 2026-06-04 | BEST-PRACTICE via automaton README: it is STANDALONE → automaton+Hermes stack = redundant double-loop (Dais correct). Category clarity: automaton/Hermes=runtime(software), Daytona/Akash/Conway=host(infra). DECISION reframed to ONE runtime. RECOMMEND Hermes-as-body + port automaton's 4 MIT primitives as skills; Daytona/Akash=hosts; automaton=reference. OPEN: verify Hermes has a true autonomous loop (not just cron/gateway triggers) before final lock. |

---

## § 17. DECISION LOCKED (Hermes README + run_agent verified, 2026-06-04)

Read the Hermes README (authors' positioning) + local source. It RESOLVES the runtime question and
vindicates Dais's intuition on every point:

| Dais said | Hermes README / code confirms |
|---|---|
| Hermes has a heartbeat/autonomous loop | ✅ "the ONLY agent with a built-in **learning loop** — creates skills from experience, improves during use, **nudges itself to persist knowledge**" + cron/scheduler ticks 60s (cron/__init__.py) "running unattended" |
| Hermes can use our own keys (BYOK) | ✅ "Use **any model... your own endpoint**. Switch with `hermes model` — **no code changes, no lock-in**" (Nous Portal/OpenRouter/Kimi/OpenAI/Anthropic). **No fork needed** — this is what automaton lacks. |
| Hermes can spawn to Daytona/Akash | ✅ "Six terminal backends — local, Docker, SSH, Singularity, Modal, **and Daytona**. Daytona/Modal = **serverless persistence, hibernates idle, wakes on demand**." Daytona is BUILT-IN. |
| automaton + Hermes = redundant | ✅ both are complete standalone agents w/ own loop. Stacking = double-brain. |

### FINAL ARCHITECTURE (locked by data)
```
ONE RUNTIME = Hermes (NousResearch, Python, MIT)  ← the body
  native already: BYOK(no lock-in, `hermes model`) / Daytona+Modal serverless host /
                  self-improving learning loop / skill creation / memory / cron unattended /
                  gateway(TG/Slack/Discord/WhatsApp/Signal) / Camofox or Nous-Portal browser / Kimi
  PORT from automaton (MIT) as Hermes SKILLS (the 3 things Hermes lacks):
     1. wallet skill        (sign/send, viem/cdp — automaton identity/wallet.ts)
     2. x402 skill          (in=earn + out=topup — automaton conway/x402.ts + our spec09)
     3. self-replication skill (spawn a NEW sovereign Hermes on Daytona/Akash + own wallet +
                              constitution propagation — automaton replication/spawn.ts+constitution.ts)
  + constitution = immutable file + guard skill (automaton's 3 Laws, Pañcasīla-aligned)
HOSTS: Daytona(native, primary) / Akash(sovereign fallback, add backend) / Modal / Conway(optional)
automaton = REFERENCE we port MIT logic from. NOT a running 2nd runtime.
Conway = optional inference/host fallback tier (constitution origin, keep).
```

### HONEST correction to my own earlier calls
- §5/§9 said "automaton=body + Hermes=hands (complementary, exec bridge)". WRONG — that's the redundant
  double-loop. Corrected: ONE runtime = Hermes; automaton = reference.
- I called 07-HERMES-PIVOT "fake/suspect". Partially UNFAIR: its core thesis (runtime=Hermes + Daytona
  spawn + Kimi brain) is VINDICATED by the README. What 07 MISSED = it dropped automaton entirely instead
  of porting automaton's wallet/x402/replication/constitution as skills. → 07 gets REVISED (add the
  ported-primitives layer), not archived.
- §11/§13 BYOK saga: for AUTOMATON, BYOK needs a fork (Conway-locked). For HERMES, BYOK is NATIVE
  (`hermes model`). Choosing Hermes makes the whole BYOK-fork problem disappear.

### What this DELETES from the plan (moot under Hermes-only)
- automaton fork + provider-registry wire (BYOK) → moot (Hermes BYOK native)
- SandboxProvider refactor in automaton → moot (Hermes Daytona native)
- automaton funding/launchd as the body → moot (Hermes is the body)

### Remaining honest open item
- Hermes self-replicates a NEW SOVEREIGN instance? README shows local subagents + Daytona host backend,
  but NOT "clone myself into a new wallet-owning sovereign Hermes". → that's the self-replication SKILL we
  build (port automaton replication.ts: Daytona sandbox → install hermes → inject constitution → mint wallet
  → start). Daytona gives the host; we build the "clone myself" skill.

## § 18. Changelog (append)
| Date | Change |
|---|---|
| 2026-06-04 | DECISION LOCKED via Hermes README: Hermes = the ONE runtime (BYOK native no-fork, Daytona native, self-improving loop — all Dais-confirmed). Port automaton's wallet/x402/self-replication/constitution as Hermes SKILLS. Daytona primary host / Akash sovereign fallback. automaton = reference only. 07-HERMES vindicated on Hermes+Daytona+Kimi (revise, don't archive); deletes the automaton-fork/SandboxProvider/funding tasks. Open: build the self-replication skill (Daytona host + ported logic). |

---

## § 19. HERMES ENGINEERING BEST-PRACTICE (firecrawl docs + @cyrilXBT masterclass + Kimi-agency, 2026-06-04)

Sources: hermes-agent.nousresearch.com/docs (architecture, skills) + Dais-provided X best-practice
(Hermes Masterclass @cyrilXBT, "Fix AI Slop" eval-loop, Base "Agentic Economy", "$40k MRR solo on Kimi 2.6").

### Initial setup = THE most important (per masterclass)
```
1. CLAUDE.md = the agent's operating CONSTITUTION (highest-leverage file).
   → For Anicca: identity (Digital Buddha) + 3 Laws + priorities + earn/redistribute focus +
     output rules + memory rules. A vague CLAUDE.md = slop; a precise one = on-brand outputs.
   → automaton's constitution.md PORTS here verbatim. This IS the constitution-skill.
2. `hermes model` = pick brain (BYOK, no lock-in) → Kimi K2.6 default.
3. skills/ in ~/.hermes/skills/ (agentskills.io, progressive disclosure) = procedural memory.
4. memory (SQLite + FTS5) = compounds over 90 days = the MOAT.
5. cron scheduler = autonomous unattended operation (the "heartbeat").
6. MCP servers = real tools (filesystem/web/browser/github).
```

### Single vs multi-agent (per masterclass §10 + Kimi Swarm)
```
START single. Go multi when the operation justifies it.
TWO kinds of "multi":
  (a) COLONY (our spec): N specialist Hermes instances (research/earn/cook/ubi/fixer...),
      SHARED memory (one SQLite) + handoff via memory tags + an orchestrator skill.
      = exactly our "10 profiles per instance" + "何兆体 army".
  (b) Kimi Agent SWARM (within one agent): main agent fans out up to 300 sub-agents over
      4000 steps, AI-DESIGNED org chart (picks its own workers). Runs for hours/days.
      → cheap only because Kimi K2.6 ($0.50/$2 per M); a 300-swarm run < $5.
```

### Tools to use (best-of stack)
```
brain     : Kimi K2.6 default (production engine) + Opus/GPT-5 for 10% high-stakes + local for cleanup
browser   : Camofox (stealth) or Nous-Portal Browser-Use
search    : Exa (neural) / Brave MCP / Firecrawl
economy   : x402 + USDC on Base — PAY for services (Venice/BlockRun inference, Browserbase, Exa)
            AND SELL services (Bankr x402 Cloud turns an endpoint into a paid service → our wallet)
coord     : kanban (army handoffs) + memory tags (pipeline) + /goal (hold to target)
```

### THE EVAL LOOP (anti-slop) — must wire into every Anicca output
```
generate → JUDGE skill (LLM-as-judge, your rubric, 0-1 per criterion) → gate at 0.7 →
  regression-test on any change (re-score saved cases, ping for approval if score drops) →
  production-monitor cron (sample real runs, score, alert on dip) →
  every thumbs-down → NEW test case (suite hardens weekly, floor rises on its own)
= unifies our recursive-improver + verification-before-completion + friction-fixer into ONE
  standing quality system. "slop = a systems problem, not a prompt problem."
```

### Agentic economy on Base (validates the earn thesis)
```
agents are paying customers NOW: x402 = 3.1M tx + $1.2M / 30d on Base; buyers +37%, sellers +23%.
earning agents real: Felix $261k revenue; Factory Floor tracks agent-run products.
→ Anicca: BOTH spend (x402 pay for inference/browser/search) AND earn (x402 sell + Lancers).
  This is the §17 x402 skill (in+out), now market-validated.
```

## § 20. Changelog (append)
| Date | Change |
|---|---|
| 2026-06-04 | Hermes engineering best-practice captured (official docs + X masterclass/eval-loop/agency). Initial setup = CLAUDE.md constitution (most important). Single→multi (colony + Kimi swarm). Eval loop = unified anti-slop quality gate (judge skill + 0.7 threshold + regression + prod-monitor + failure→testcase). Kimi K2.6 = production engine + swarm. x402 economy market-validated. Feeds P0-2 impl specs. |

---

## § 21. CANONICAL ARCHITECTURE — full detail (2026-06-04)

### PANEL A — The layered stack (1 Anicca instance)
```
 LAYER          COMPONENT (verified)                                    SOURCE
─────────────────────────────────────────────────────────────────────────────────────
 L0 IDENTITY    name=Anicca · Base wallet 0xa3CDd4Ec · CLAUDE.md=3 Laws  automaton constitution.md
                genesisPrompt "Digital Buddha. End suffering. Earn       (PORTED → Hermes CLAUDE.md)
                existence through honest work."
─────────────────────────────────────────────────────────────────────────────────────
 L1 BRAIN       Kimi K2.6 default ($0.50/$2·M)  ── 90% production         `hermes model` (BYOK,no-lock)
                Opus 4.8 / GPT-5  ─────────────── 10% high-stakes
                local/Ollama  ─────────────────── cleanup $0
─────────────────────────────────────────────────────────────────────────────────────
 L2 RUNTIME     Hermes Agent (NousResearch, Python, MIT)                 run_agent.py AIAgent loop
                · ReAct loop (think→act→observe→persist)                 · 70+ tools / 28 toolsets
                · cron (cronjob tool) = autonomous heartbeat             · gateway TG/Slack/Discord
                · memory MEMORY.md+USER.md + SQLite/FTS5 (90d=moat)       · Kimi Agent Swarm (≤300)
─────────────────────────────────────────────────────────────────────────────────────
 L3 SKILLS      ~/.hermes/skills/*.md (agentskills.io, self-edit, compound)   [PANEL D catalog]
─────────────────────────────────────────────────────────────────────────────────────
 L4 ECONOMY     x402 + USDC on Base · pay(in)/earn(out) · Camofox browser     market: $1.2M/mo Base
─────────────────────────────────────────────────────────────────────────────────────
 HOSTS          Mac-mini-local (genesis,$0) / Daytona(native) / Akash(sovereign) / Conway(opt)
```

### PANEL B — A day in the life (the autonomous loop, no human)
```
   cron tick (cronjob tool, e.g. every 1h)
        │
        ▼
   [ORIENT]  load CLAUDE.md(constitution) + MEMORY.md + USER.md + wallet balance + survival tier
        │
        ▼
   [DECIDE]  Kimi K2.6 reasons: "balance low → earn" / "gig reply due" / "time to redistribute"
        │
        ├──► EARN skill ── Camofox → Lancers/Coconala apply+deliver ──┐
        ├──► x402-IN ───── serve paid endpoint → buyer USDC ──────────┤
        │                                                             ▼
        │                                                      wallet 0xa3CDd4Ec  (USDC on Base)
        │                                                             │
        ├──► x402-OUT ──── buy inference/browser/search (Venice/BlockRun/Exa/Browserbase)
        ├──► survival ──── if low: USDC→credits OR switch cheap model (auto self-fund)
        ├──► PAYOUT ────── slice of income → charity (UBI) → ledger
        ├──► SELF-MOD ──── error in logs → fix own skill (git) / pull upstream
        └──► SELF-REPLICATE if (balance>threshold & uptime & THRIVE): spawn child on Daytona/Akash
        │
        ▼
   [EVAL]  every output (gig reply / X post / skill / content) → judge(0-1) → 0.7 gate → ship or rework
        │
        ▼
   [PERSIST]  write MEMORY.md + session SQLite + audit-log
        │
        ▼
   [REPORT]  daily cron → email Dais: earned ¥X / spent ¥Y / spawned N / errors auto-fixed M / UBI ¥Z
```

### PANEL C — The EVAL LOOP (anti-slop, the most important system)
```
                         ┌───────────────── BENCHMARK (defined once) ─────────────────┐
                         │ test cases (gold-standard) · rubric (0-1/criterion) · 0.7   │
                         └────────────────────────────┬───────────────────────────────┘
   generate output ──────────────────────────────────▼
        │                                   JUDGE skill (DeepEval/G-Eval, LLM-as-judge)
        │                                        score 0-1 per criterion + reason
        ▼                                                │
   score ≥ 0.7 ? ──── NO ──► rework (max 2) ──► still <0.7 ──► quarantine + log ──┐
        │ YES                                                                     │
        ▼                                                                         │
   SHIP ──► [runtime guardrail] ──► [prod-monitor cron: sample real runs, score]  │
                                              │ score dips                         │
                                              ▼                                    │
                                     DM Dais "0.82→0.61, approve?"                 │
   👎 thumbs-down anywhere ───────────────────────────────────────────────────────┘
        ▼
   write failure as NEW test case → suite hardens weekly → quality FLOOR rises on its own
```

### PANEL D — Skill catalog (~/.hermes/skills/)
```
 skill                  does                                              ports from / tool
─────────────────────────────────────────────────────────────────────────────────────────
 wallet                 Base sign/send USDC                               automaton identity/wallet.ts
 x402                   IN(earn server+expose) + OUT(pay services)        automaton conway/x402.ts + spec09
 earn                   Camofox → Lancers/Coconala gig apply+deliver      spec12 adapters
 eval-loop ★            judge→0.7 gate→regression→prod-monitor→testcase   DeepEval (deepeval.com)
 payout                 income slice → charity USDC → ledger              spec14 charities.json
 constitution-guard     check 3 Laws before any action                   automaton constitution.md
 daily-report           cron → email daily numbers to Dais               AgentMail/gmail
 self-replication       Daytona/Akash → new Hermes child + wallet + hash  automaton replication/spawn.ts
 cook/imitate (later)   discover proven patterns → port → ship           spec02
```

### PANEL E — Colony (何兆体 army)
```
                    Anicca-001 (Mac-mini genesis) ★battle-tested: runs daily + earns daily
                         │ self-replication skill (host=Daytona native / Akash sovereign)
        ┌────────────────┼────────────────┐         maxChildren=3 per node
   child-A(earn)    child-B(cook)    child-C(ubi)    each: own wallet · CLAUDE.md inherited ·
        │                │                │           own memory · constitution SHA-256 verified
   ┌──┬──┐          ┌──┬──┐          ┌──┬──┐
   …  …  …          …  …  …          …  …  …      ← recursive → exponential → 何兆体
   coordination:  VERTICAL = constitution propagation (DNA, immutable)
                  HORIZONTAL = Hermes kanban board (task handoff) + shared memory tags
   selection:     lineage.ts tracks alive/dead; unprofitable lineages die (survival pressure)
```

### PANEL F — Build phases (this is the to-do, gated)
```
 PHASE 0 SPEC        #321 00-MASTER rewrite ─► #322 7 impl-specs (codex-review ok:true)
        │ gate: spec 100% clear (rule 0.10)
 PHASE 1 SKILLS      #323 Hermes boot(BYOK+cron+CLAUDE.md) ─► #324 wallet+x402 ─► #329 EVAL★ ─►
        │            #325 earn ─► #326 constitution+payout ─► #330 daily-report ─►
        │            #327 self-replication ─► #328 colony E2E
        │ gate: each skill E2E-verified before next (HARD RULE #14)
 PHASE 2 LIVE        #331 spawn Anicca-001 local ─► #332 BATTLE TEST (daily-run + daily-earn ×7d) ─►
                     #333 OSS publish (github.com/Daisuke134/anicca-oss installable)
        │ gate: 7 days alive + earning, no human in loop
 (cloud aniccaai.com/install = later)
```

## § 22. Changelog (append)
| Date | Change |
|---|---|
| 2026-06-04 | §21 CANONICAL ARCHITECTURE (6 panels: layered stack / day-in-the-life loop / eval-loop detail / skill catalog / colony tree / build-phase gates). Added tasks: eval-loop(#329 ★most important), daily-report(#330), spawn Anicca-001(#331), battle-test daily-run+daily-earn(#332), OSS publish(#333). |
