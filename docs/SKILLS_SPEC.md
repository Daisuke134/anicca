# SKILLS_SPEC — Anicca Skills / Cron / Self-Improvement SSOT

> Index of the agent's skill+cron architecture. Per memory HARD RULE #1 this file is kept current on any skill/cron/design change. Operational runtime state lives in `~/.openclaw`; the authoritative living design doc is linked per section.

---

## Anicca-as-Bengt v1 — heartbeat-native self-improving agent

**Status:** v1 built; heartbeat LIVE @3h; behaviorally UNPROVEN until ≥3 real beats verified (gate = task #15).

**Canonical living spec (source of truth, updated every change):**
`~/.openclaw/workspace/specs/2026-05-17-anicca-as-bengt-v1-spec.md` (in the public `anicca-products` ops repo). This section is the discoverable summary; the canonical spec has the full audit log, source citations, and task list.

### Goal
Turn Anicca from a ~200-cron command-executor into a goal-driven autonomous agent that reads its own Slack/logs, decides its own work, fixes its own failures, watches its own budget, replicates, and is gated by a Buddhist Five-Precepts Constitution — so Dais is a monthly framework-evaluator + credential-lender + precept-arbiter, never a daily bottleneck.

### Layer stack (top governs all below; read top→down every beat)

| Layer | Artifact | Role |
|-------|----------|------|
| L0 North Star | memory HARD RULE #0 | end suffering · money=tool · spend reduce⊕earn else KILL · distribution compounds |
| L1 五戒 Constitution | `~/.openclaw/workspace/CONSTITUTION.md` (0444) | 不殺生/不偸盗/不邪淫/不妄語/不飲酒 · violation→repentance-continue (NOT fail-stop) |
| L2 SOUL MISSION | `~/.openclaw/workspace/SOUL.md` | automaton-pattern system prompt: "you are alive, you decide" + 6-step loop + You CAN/CANNOT + authority gate |
| L3 attention | `~/.openclaw/workspace/ops/steps.json` | todo.md attention queue (always[]/ranked[]/one_time[]) |
| L3 ledgers | `ops/roi-ledger.json` · `ops/improvement-archive.json` · `ops/cron-tiers.json` | realized $/token PDCA · DGM self-improve archive · cron Tier2/Tier3 map |
| L4 skills | `~/.openclaw/skills/` | recipes the loop calls (below) |
| L5 cron | `~/.openclaw/cron/jobs.json` | Tier2 metronomes only; Tier3 judgment folded into the loop |

### Skills (loop-called recipes, not crons)

| Skill | Role |
|-------|------|
| `budget-watcher` | self-CFO life-meter; automaton 5-tier (high/normal/low_compute/critical/dead-grace) + 1hr grace + balance-cache; never fail-stop |
| `slack-feedback-reader` | inner loop: detect failing cron → DGM self-improve (read archive → ≥2 variants → eval-gate before keep else revert) → repentance-continue |
| `anicca-director` | refills steps.json ranked[] daily (loop-called) |
| `anicca-framework-eval` | self-timed framework health + soul-reflection alignment + ROI product-kill |
| `opportunity-scout` | loop-called value-opportunity search → queue to steps.json (never a cron) |

### Self-improvement model (sourced, no originals)
- automaton (Conway) — system-prompt pattern, 5-tier survival, replication, self-mod audit
- DGM (Sakana Darwin Gödel Machine) + SICA — archive + open-ended exploration + eval-gate-before-keep + "read what failed first"
- Reflexion / Anthropic Constitutional AI / Zen 懺悔 / Azure self-preservation — violation = repentance-continue, never terminate
- pskoett 2-loop — inner (fix in-beat) + outer (.learnings durable rules)

### Distribution / replication (v2, gated on v1 proven)
- One `anicca.sh` installer, `--harness=` flag → OpenClaw / Claude Code (`/loop`+launchd) / Codex / Hermes; Paperclip = fleet layer above
- BYOK wizard (downloader's own ChatGPT-Plus login OR API key + money; NO USDC/wallet yet — Conway path is future)
- Replication = automaton `src/replication/spawn.ts` ported; child = own remote host funded by real earnings, dies if can't pay (Darwinian); concrete VPS-provider recipe = task #42 (the one unimplemented piece)

See the canonical spec for the full 46-task list, ordering, and source-code audit.
