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
VERDICT: do NOT import the monorepo. STEAL designs: autonomy 30s-loop, x402-manager (cleanest x402-IN ref), Plugin/Action interface.
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
