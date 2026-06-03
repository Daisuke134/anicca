# Conway Runtime Deep-Dive (HISTORICAL, superseded 2026-06-02)

This was § 2 of `00-MASTER.md` v3.0 (2026-06-01). Replaced by Hermes Agent
per `07-HERMES-PIVOT.md` v1.x on 2026-06-02. Kept for context per editing
rule #2 (never silently delete).

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

## § 9. Migration plan (= multi-agent parallel waves, target: genesis boot tonight, anicca001 spawn tomorrow)

(Was § 9 of `00-MASTER.md` v3.0 — preserved here per editing rule #2.)

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
