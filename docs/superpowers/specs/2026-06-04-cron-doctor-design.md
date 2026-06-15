# Spec: anicca-cron-doctor (sub-spec of cron-rat-proof-architecture)

| meta | value |
|---|---|
| parent spec | `docs/superpowers/specs/2026-06-04-cron-rat-proof-architecture-design.md` |
| date | 2026-06-04 |
| skill path | `~/.openclaw/skills/anicca-cron-doctor/` |
| cron path | launchd plist `~/Library/LaunchAgents/ai.anicca.cron-doctor.plist`, 03:00 JST nightly |

## Why

Phase A migrated 2 crons (wallet, bounty). Phase D = doctor automates the remaining 232 + ongoing detection of:
- new "Read SKILL.md" prompt drift
- new refusal pattern in Slack
- per-cron streak monitoring
- auto-launchd-escalation for repeated failures

Without the doctor, every prompt drift = a manual investigation cycle.

## Six phases (= L1 thru L6)

| Phase | Detection | Action | Output |
|---|---|---|---|
| L1 prompt lint | `payload.message` matches `r"Read ~/\.openclaw/skills/([^/]+)/SKILL\.md and execute"` | rewrite to `bash $HOME/.openclaw/skills/_dispatcher/scripts/cron-codex.sh <skill>` via `openclaw cron edit --message` | `L1_fixed=N` + list |
| L2 path lint | `payload.kind=agentTurn` + `sessionTarget=isolated` + skill has `scripts/run.sh` with no LLM dependency (= grep no `claude\|openai\|api.anthropic`) → classify as "pure data fetch" | flag for migration to launchd (= staged, requires Dais OK first time per cron type) | `L2_flagged=N` + list, NO auto-action without Dais sign-off |
| L3 refusal detector | Slack #metrics last 24h conversations.history search for `unknown MCP\|実行環境.*ない\|shell tool.*ない\|実行できません\|実行経路.*到達できません` | for each match, parse cron id from message, `openclaw cron run <id>` (re-fire) | `L3_retried=N` + list |
| L4 streak monitor | track per-cron refusal count in `~/.openclaw/skills/anicca-cron-doctor/data/refusal-streak.json` | log only; alerts on streak>=3 | `L4_alerted=N` |
| L5 hard escalate | streak >= 5 on revenue-critical cron (= list in `data/revenue-critical.json`) | generate launchd plist using template `templates/launchd.plist.tmpl`, bootstrap, disable OpenClaw cron | `L5_migrated=N` + list |
| L6 report | aggregate L1-L5 | Slack post to #metrics + write `data/reports/YYYY-MM-DD.json` | 1 message |

## Idempotency requirements (= MUST)

- L1 rewrite: must be no-op on already-correct prompts (= grep `_dispatcher/scripts/cron-codex.sh` before edit)
- L3 re-fire: must skip if same cron was already retried in last 1h (avoid loop)
- L5 launchd migrate: must skip if `~/Library/LaunchAgents/ai.anicca.<name>.plist` already exists
- L6 report: emits even when all counts are 0 (= heartbeat proof)

## Output (= Slack post format)

```
:stethoscope: cron-doctor 2026-06-04 03:00 JST
  L1 prompt lint     fixed=3 skipped=59
  L2 path lint       flagged=12 (review queue)
  L3 refusal retry   retried=2
  L4 streak monitor  alerted=0
  L5 hard escalate   migrated=0
  L6 next run        2026-06-05 03:00 JST
```

## Verification

| AC | 判定 |
|---|---|
| AC-D1 | `bash scripts/run.sh --dry-run` 出力で L1-L6 phase 全部走る + count を JSON で返す |
| AC-D2 | `bash scripts/run.sh` 1 回目で当面 L1 violators (62 件) を全部修正、 2 回目は 0 件 (= idempotent 証明) |
| AC-D3 | Slack #metrics に L6 report が来る |
| AC-D4 | launchd plist 登録、 次 03:00 JST schedule |

## Dependencies

- bash, jq, curl, python3 (built-in)
- openclaw CLI (`openclaw cron edit/get/run`)
- `~/.openclaw/.env::SLACK_BOT_TOKEN` (= chat.postMessage)
- `~/.openclaw/skills/_dispatcher/scripts/cron-codex.sh` (= L1 rewrite target)
