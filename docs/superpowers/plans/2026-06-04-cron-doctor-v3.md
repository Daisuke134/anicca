# Cron-doctor v3 Implementation Plan

**Goal:** End-to-end ship R-1, R-2, R-3, R-10, R-12 with TDD per HARD RULE #0.

**Architecture:** new skill `anicca-credit-monitor`, new helpers `last_fire.py` + `cfo_sync.py`, extend `phases.py` with L8 + L3 multi-provider patterns, 3 GH issue docs, 2 new OpenClaw crons (`anicca-credit-monitor` daily, `anicca-cfo-sync` monthly).

**Tech Stack:** Python 3 stdlib + bash + curl + openclaw CLI.

---

## File map

| File | Action | What |
|---|---|---|
| `~/.openclaw/skills/anicca-credit-monitor/SKILL.md` | Create | docs |
| `~/.openclaw/skills/anicca-credit-monitor/scripts/check.sh` | Create | multi-provider probe |
| `~/.openclaw/skills/anicca-cron-doctor/scripts/helpers/last_fire.py` | Create | L8 watchdog |
| `~/.openclaw/skills/anicca-cron-doctor/scripts/helpers/cfo_sync.py` | Create | R-12 reconcile |
| `~/.openclaw/skills/anicca-cron-doctor/scripts/tests/test_last_fire.py` | Create | unit test |
| `~/.openclaw/skills/anicca-cron-doctor/scripts/tests/test_cfo_sync.py` | Create | unit test |
| `~/.openclaw/skills/anicca-cron-doctor/scripts/phases.py` | Modify | add L8 + L3 patterns |
| `~/.openclaw/skills/anicca-cron-doctor/scripts/format_report.py` | Modify | L8 line |
| `~/anicca-project/docs/issues/openclaw-payload-model-ignored.md` | Create | issue draft |
| `~/anicca-project/docs/issues/openclaw-refusal-classified-as-success.md` | Create | issue draft |
| `~/anicca-project/docs/issues/openclaw-jobs-json-hot-reload-race.md` | Create | issue draft |
| `~/.openclaw/cron/jobs.json` | Modify (via CLI) | 2 new crons |

## Task 1: credit-monitor skill + cron

- [ ] Write SKILL.md
- [ ] Write check.sh (multi-provider probe, Slack post)
- [ ] chmod +x
- [ ] Run standalone; verify Slack `:moneybag:` post arrives
- [ ] `openclaw cron add` with daily 09:00 JST schedule
- [ ] `openclaw cron run` to verify wraps via cron-bash.sh

## Task 2: L8 last-fire watchdog

- [ ] Write test_last_fire.py with cases: fresh / stale / never-fired / cron expr parse
- [ ] Run RED
- [ ] Implement last_fire.py (`parse_interval_hours(cron_expr)`, `is_stale(state, expected_h, now_ms)`, `phase_l8(...)`)
- [ ] Run GREEN
- [ ] Wire into phases.py main() + add report key
- [ ] Wire into format_report.py
- [ ] Verify L8 line in Slack

## Task 3: L3 multi-provider patterns (R-2)

- [ ] Extend `REFUSAL_PATTERNS` in phases.py with 4 new regex
- [ ] Add unit case in test_cron_edit (or new test) confirming pattern hits
- [ ] Run doctor; if any 24h Slack message matches new pattern, that cron refires

## Task 4: cfo_sync helper

- [ ] Write test_cfo_sync.py with cases: missing CFO dir → safe-skip, present → reconcile
- [ ] Run RED
- [ ] Implement cfo_sync.py with `reconcile(cfo_data_dir, revenue_critical_path) -> dict`
- [ ] Run GREEN
- [ ] Add new OpenClaw cron `anicca-cfo-sync` monthly 1st 05:00 JST that runs `python3 -c "from helpers.cfo_sync import main; main()"` via dispatcher

## Task 5: R-10 issue drafts

- [ ] Create `~/anicca-project/docs/issues/openclaw-payload-model-ignored.md`
- [ ] Create `~/anicca-project/docs/issues/openclaw-refusal-classified-as-success.md`
- [ ] Create `~/anicca-project/docs/issues/openclaw-jobs-json-hot-reload-race.md`
- [ ] Each has Summary / Repro / Expected / Actual / Proposed fix sections

## Task 6: E2E run #1

- [ ] `bash ~/.openclaw/skills/anicca-cron-doctor/scripts/run.sh`
- [ ] Read JSON line: L1, L2, L3, L4, L5, L7, **L8** keys present
- [ ] Slack message has L8 line
- [ ] Run `~/.openclaw/skills/anicca-credit-monitor/scripts/check.sh` standalone
- [ ] Slack `:moneybag:` per provider

## Task 7: Fix anything broken in run #1

- [ ] If any phase fails, debug and patch

## Task 8: E2E run #2 (idempotency)

- [ ] Same commands as Task 6
- [ ] Confirm git_sync committed=False
- [ ] Confirm refusal-streak.json unchanged

## Task 9: Commit + push (both repos)

- [ ] cd ~/.openclaw && git add ... && commit && push
- [ ] cd ~/anicca-project && git add docs/issues docs/superpowers && commit && push

## Task 10: Final status to Dais

- [ ] Slack `:white_check_mark: v3 shipped — R-1/R-2/R-3/R-10/R-12 end-to-end + tests + Slack verified + pushed`
