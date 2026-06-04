---
name: anicca-cron-doctor
description: ★ Self-heal for OpenClaw cron fleet. Detect failed/stuck/dry-run crons → produce per-cron repair brief → emit to workspace/tasks.json. Runs hourly at :37 (enabled per #140, content-heartbeat-design 2026-06-04 WS4). Auto-disable handler (anicca-cron-auto-disable, daily 11:3) consumes the brief. Nightly L1-L6 lint + auto-fix (separate run.sh). Detects "Read SKILL.md" prompt drift, refusal strings in Slack, and per-cron failure streaks. Auto-rewrites prompts to direct-bash form, re-fires refused crons, escalates revenue-critical streaks to launchd. Reports nightly to Slack #metrics. Idempotent (= run twice safely).
canonical_doc: ~/.openclaw/docs/superpowers/specs/2026-06-04-anicca-cron-heartbeat-content-design.md
source_inline: workspace/HEARTBEAT.md §3.5 + §3.5.1 (extracted per #141 spec WS5)
metadata:
  type: infra-cron-self-heal
  spec: docs/superpowers/specs/2026-06-04-cron-doctor-design.md
  parent_spec: docs/superpowers/specs/2026-06-04-cron-rat-proof-architecture-design.md
  heartbeat_spec: docs/superpowers/specs/2026-06-04-anicca-cron-heartbeat-content-design.md
  tags: [cron, doctor, self-heal, observe-diagnose]
  cron_schedule: "37 * * * * Asia/Tokyo"
  cron_model: deepseek/deepseek-v4-pro
  brief_output: workspace/tasks.json (JSON-structured)
  cadence_nightly_lint: nightly 03:00 JST via launchd
  idempotent: true
---

# anicca-cron-doctor

## Purpose

Observe + diagnose layer of the self-heal architecture. Per `2026-06-04-anicca-cron-heartbeat-content-design.md` WS4, this skill is the heartbeat (b) chore delegated out — heartbeat no longer inlines the cron-fix steps.

## Cron invocation (anicca-cron-doctor, :37 hourly, deepseek/v4-pro)

The cron runs `bash $HOME/.openclaw/skills/anicca-cron-doctor/scripts/cron-doctor.sh` (existing script) which:
1. Scans `~/.openclaw/cron/runs/*.jsonl` for last-hour error/timeout/false-OK signals
2. Classifies each: 🔴 CRIME / ❌ real / ⚠️ false-ok / ⏳ transient / 💤 stuck
3. Per failed cron, emits a structured brief to `~/.openclaw/workspace/tasks.json` (status:pending) describing the root cause + suggested fix
4. The downstream `anicca-cron-auto-disable` (daily 11:3) consumes the brief and disables crons that meet 3+day dry-run or 7+day silent thresholds.

## Run (nightly lint mode)

```bash
bash $HOME/.openclaw/skills/anicca-cron-doctor/scripts/run.sh           # apply
bash $HOME/.openclaw/skills/anicca-cron-doctor/scripts/run.sh --dry-run # report only
```

## Phases (nightly L1-L6)

| Phase | Purpose | Auto-action |
|---|---|---|
| L1 prompt lint | "Read SKILL.md and execute" → direct-bash via `_dispatcher/cron-codex.sh` | `openclaw cron edit --message` |
| L2 path lint | classify by `payload.kind` + skill content (LLM vs deterministic) | flag-only, no action |
| L3 refusal detector | scan Slack #metrics for refusal strings → re-fire cron | `openclaw cron run <id>` (rate-limited 1/hour per cron) |
| L4 streak monitor | per-cron consecutive refusal count | persist to `data/refusal-streak.json` + alert |
| L5 hard escalate | streak>=5 + revenue-critical → launchd | `launchctl bootstrap` + `openclaw cron disable` |
| L6 report | Slack post + JSON archive | always emitted |

## Files

```
anicca-cron-doctor/
├── SKILL.md (this file)
├── scripts/
│   ├── run.sh                  # nightly orchestrator (L1-L6)
│   └── cron-doctor.sh          # hourly :37 brief emitter
├── data/
│   ├── revenue-critical.json   # list of cron names that auto-escalate at streak 5
│   ├── refusal-streak.json     # per-cron streak counter (read+write each run)
│   └── reports/YYYY-MM-DD.json # daily archive
└── templates/
    └── launchd.plist.tmpl      # template for L5 plist generation
```

---

## Content lifted from HEARTBEAT.md §3.5 + §3.5.1 (verbatim, 2026-06-04 per #141)

> The content below was inlined in `workspace/HEARTBEAT.md` lines 144-220 prior to the
> 2026-06-04 heartbeat picker-only compression (#143). It is preserved here verbatim so the
> heartbeat picker can reference this skill by name instead of re-inlining 77 lines of prose
> every beat. Editing rule: when the canonical HEARTBEAT.md evolves, regenerate this section
> from the source — do NOT edit by hand.

## 3.5 cron 故障の実修復（cron-doctor ブリーフが出たら最優先で・ハードコード禁止）
故障ブリーフの各 cron について順に、文脈を読んで実際に直す:
  1. **summary を読む** → 偽ok か 本物の失敗か判定:
     - 偽ok = summary に投稿URL/「成功」等があり、error は配信(delivery/Message failed)
