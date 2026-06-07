# Heartbeat Task Engine — single control plane, no per-project crons

**Author**: Anicca (BP-driven from existing openclaw ops infra + Dais 2026-06-07 verbatim directive)
**Date**: 2026-06-07
**Sister specs**:
- `2026-06-07-larry-reelclaw-truth-correction-design.md` — T1-T15 marketing fixes (= will be consumed by heartbeat as P0 tasks)
- `2026-06-07-daily-article-engine-design.md` — T16 article engine (= will be one task type heartbeat consumes)
**Constitution**: HARD RULE #-3 (BP follow only), HARD RULE 0.24 (no dry run), HARD RULE 0.26 (no Dais loop).

## North star (= Dais directive verbatim)

> "The heartbeat just tracks everything into a task list. If it is an error, then they'll basically go put it up on the issues of the Anitra DICE… The heartbeat just goes do that one by one with each heartbeat. Every heartbeat, they're going to go finish one."

→ ONE heartbeat = ONE task done. No per-project crons. Errors → GitHub issues on `Daisuke134/anicca-dais` (= private backup repo, already live with 4 P0 issues). Morning Gmail to Dais summarizes yesterday + today.

## Existing infrastructure (= confirmed via local search 2026-06-07)

| component | location | status |
|---|---|---|
| ops-heartbeat skill | `~/.openclaw/skills/ops-heartbeat/SKILL.md` | ✓ exists, generates proposals + steps |
| anicca-heartbeat cron | `openclaw cron list → 0 3,9,15,21 * * * Asia/Tokyo` | ✓ exists, fires 4×/day (6h) |
| heartbeat_state.json | `~/.openclaw/workspace/ops/heartbeat_state.json` | ✓ |
| proposals.json | `~/.openclaw/workspace/ops/proposals.json` | ✓ |
| steps.json | `~/.openclaw/workspace/ops/steps.json` | ✓ (mission-worker reads here) |
| tasks.json | `~/.openclaw/workspace/ops/tasks.json` | ✓ (has cron_doctor_report + failed_cron_brief) |
| mission-worker | `~/.openclaw/workspace/ops/mission-worker/` | ✓ executor |
| anicca-dais repo | `github.com/Daisuke134/anicca-dais` | ✓ private, has_issues=True, 4 open P0 |
| auto-issue mechanism | (= Anicca itself or cron-manager skill) | ✓ confirmed live by 4 existing issues |

→ ★ 9 / 9 既存 ★. Spec just consolidates how they connect.

## BP citation

| BP | source | identical follow |
|---|---|---|
| ops-heartbeat skill `SKILL.md` | verbatim local | task pull + steps.json write + Slack #metrics post |
| anicca-dais 4 existing issues | `gh issue list -R Daisuke134/anicca-dais` | label scheme: `ai-ready, P0, cron:<name>` |
| Dais directive "one heartbeat one task" | conversation 2026-06-07 17:00 | Phase 3 picks exactly 1, no batch |
| Dais directive "morning Gmail yesterday + today" | same | Phase 5 new cron 07:00 JST |
| Dais directive "no per-project cron" | same | T17c deletes 10 article-daily + future similar |

## Architecture

```
                     ┌────────────────────────────────────────┐
                     │ TASK SOURCES (= heartbeat reads ALL):   │
                     │                                          │
                     │  1. anicca-dais open issues             │
                     │     (gh api → labels: P0/P1, ai-ready)  │
                     │  2. ~/.openclaw/workspace/ops/tasks.json│
                     │  3. ~/.openclaw/workspace/ops/steps.json│
                     │  4. project specs' "Verification" rows  │
                     │     (parsed from current PR spec)        │
                     │                                          │
                     │ Merged into ONE in-memory priority queue│
                     └──────────────────┬─────────────────────┘
                                        ▼
       ┌──────────────────────────────────────────────────────┐
       │ Cron schedule (= already live, just renamed):         │
       │                                                        │
       │   anicca-heartbeat       0 3,9,15,21 * * *  (every 6h) │
       │   anicca-morning-gmail   0 7 * * *           (07:00 JST│
       │                                                  daily)│
       └──────────────────────────────────────────────────────┘
                                        ▼
       ┌──────────────────────────────────────────────────────┐
       │ Heartbeat tick (= 6h):                                │
       │   1. Load all 4 task sources, merge, sort by priority │
       │   2. Pick TOP 1 task                                  │
       │   3. Dispatch to relevant skill via mission-worker:    │
       │       issue label "cron:X" → fix-cron skill            │
       │       T-prefix → respective spec skill                 │
       │       article = anicca-article-engine                  │
       │       larry/reelclaw = larry skill, reelclaw skill     │
       │   4. On success: gh issue close (if was issue), update │
       │      heartbeat_state.json "completed", Slack ping      │
       │   5. On failure: gh issue create -R Daisuke134/anicca-│
       │      dais --label "ai-ready,P0,<context>" --body X    │
       └──────────────────────────────────────────────────────┘
                                        ▼
       ┌──────────────────────────────────────────────────────┐
       │ Morning Gmail tick (= 07:00 JST):                     │
       │   Subject: "Anicca morning report YYYY-MM-DD"          │
       │   Body:                                                │
       │     Yesterday (last 24h from heartbeat_state.json):    │
       │       ✓ T2 Larry JA v1 hook+bg fix                    │
       │       ✓ Fixed cron error: substack-en                  │
       │       ✓ Posted article "Vending-Bench reveals…"        │
       │     Today's queue (top 5 from merged sources):         │
       │       P0 T1 Postiz registry rebuild                    │
       │       P0 T2 Larry EN v1 fix                            │
       │       P0 T7 bbox quality gate                          │
       │       P1 T16d Inaugural article                        │
       │       P1 T16e README AGI mission                       │
       │     Errors needing Dais attention:                      │
       │       (= anicca-dais issues labeled needs-dais-input)   │
       │   Recipient: keiodaisuke@gmail.com via `gog gmail send` │
       └──────────────────────────────────────────────────────┘
```

## ★ Persona of heartbeat (= what voice / what tone) ★

The heartbeat does NOT post articles itself. It DISPATCHES the article-engine skill which writes as Daisuke. The heartbeat's own outputs (= Slack #metrics + morning Gmail to Dais) are written as **Anicca speaking to Dais directly**, like a smart executive assistant:

```
Morning Gmail body example (English, but JA is fine):

Hi Dais,

昨日やったこと (= last 24h):
  ✓ Larry JA v1 fix shipped — new male-face bg + メンタルが勝手に安定する hook
    + auto_music on. First post hit @anicca.jpx 16:30 JST.
  ✓ Fixed cron error anicca-article-daily-substack-en (closed #4 on
    anicca-dais)
  ✓ Posted today's article "Why Vending-Bench is a mirror for AGI alignment"
    to Dev.to + Zenn + Substack EN + note + aniccaai.com/blog (5/5)

今日やる予定 (= today's queue, top 5):
  P0 T1 Postiz registry rebuild (= fix 10 ID↔handle lies)
  P0 T2 Larry EN v1 same-style fix
  P0 T7 bbox quality gate to stop text overflow
  P1 T16e Update Daisuke134/anicca README with AGI Buddhist mission
  P1 T17c Delete 10 obsolete article-daily-* crons after T16a engine live

Items needing your input:
  (none today — autonomous ok)

— Anicca
```

## Sub-tasks (T17)

| sub | task | depends on |
|---|---|---|
| T17a | Extend `~/.openclaw/skills/ops-heartbeat/SKILL.md` Phase 1 with ONE new gh-api call: `gh issue list -R Daisuke134/anicca-dais --label ai-ready --state open --json number,title,labels,body`. Merge into same queue the skill already builds. Existing SKILL.md description verbatim: `閉ループ ops のハートビート。proposals/steps を評価し次の step を生成する` — extension is one new source, no architectural rewrite. (Reviewer I5 fix.) | — |
| T17b | Build `~/.openclaw/skills/anicca-morning-gmail/` skill + register cron `0 7 * * * Asia/Tokyo`. | T17a |
| T17c | Delete 10 obsolete article crons by VERBATIM name (reviewer C1 fix): `anicca-article-daily-audit`, `anicca-article-daily-blog`, `anicca-article-daily-devto`, `anicca-article-daily-note`, `anicca-article-daily-substack-en`, `anicca-article-daily-substack-ja`, `anicca-article-daily-whitelist-learn`, `anicca-article-daily-zenn`, `anicca-article-self-improve`, `zenn-backlog-deploy`. | **T16a in article spec MUST land and verify-pass first** (reviewer C5+I6 fix) — heartbeat must dispatch the thesis-brief + reuse anicca-article-daily skill successfully BEFORE the old daily crons disappear, otherwise an article-day gap occurs. |
| T17d | mission-worker dispatch table at `~/.openclaw/workspace/ops/dispatch.json`. Map issue labels (e.g. `cron:anicca-article-daily-zenn`) and task prefixes (`T1`→larry-reelclaw, `T16`→anicca-thesis-brief + anicca-article-daily, `T17`→ops-heartbeat) to invocations. | T17a |
| T17e | Migrate spec tasks into anicca-dais issues. **MUST follow T1** (reviewer C5 fix): migrating before Postiz registry truth would encode stale handle labels into issue body. After T1 lands, `gh issue create` per task with `--label "ai-ready,<priority>,spec:<spec-filename>"` + body = task description + verification clause. | T1 (truth-correction), T17a |
| T17f | Slack #metrics post format standardization in ops-heartbeat Phase 4 output: `✓ <task-id> <title> done — <outcome-1-line>` on success; `✗ <task-id> <title> failed: <reason> → issue #<N> on anicca-dais` on failure. | T17a |

## Verification (= HARD RULE 0.24 fire-and-observe — reviewer I4 fix)

- T17a: After extension, manually invoke `bash ~/.openclaw/skills/ops-heartbeat/scripts/run.sh --once-now` (or the entry point in the skill's actual run cmd; check SKILL.md). Observe stdout merged queue contains the 4 anicca-dais issues with correct priority sort. `cat ~/.openclaw/workspace/ops/steps.json | jq '.steps | length'` returns > 0.
- T17b: After T17a verified, invoke `bash ~/.openclaw/skills/anicca-morning-gmail/scripts/run.sh --send-now`. Observe Gmail arrival within 60 seconds at keiodaisuke@gmail.com via `gog gmail search 'subject:Anicca morning report' --max 1 --since today`. Subject contains today's `YYYY-MM-DD`. Body contains "Yesterday" + "Today's queue" sections with at least 1 task each. Cron registration verified by `openclaw cron list --all | grep anicca-morning-gmail` returning the expression `0 7 * * * Asia/Tokyo`.
- T17c: BEFORE deletion, capture the exact set: `openclaw cron list --all --json | jq -r '.jobs[].name' | grep -E "^(anicca-article-daily-(audit|blog|devto|note|substack-en|substack-ja|whitelist-learn|zenn)|anicca-article-self-improve|zenn-backlog-deploy)$"` returns exactly 10 names. AFTER deletion, same command returns 0 lines.
- T17d: `cat ~/.openclaw/workspace/ops/dispatch.json | jq 'keys | length'` returns ≥ 5. `jq '. | to_entries[] | select(.value | type != "string")'` returns empty (= every mapping value is a string skill name).
- T17e: `gh issue list -R Daisuke134/anicca-dais --state open --json number | jq 'length'` returns ≥ 20. Each migrated issue body grep returns `spec:2026-06-07-` matching one of the 3 spec filenames.
- T17f: After invoking heartbeat once with both a success-task and a failing-task (use a known-failing migrated issue for the failure-case test), inspect Slack #metrics via local Slack channel log: assert one message starting `✓ ` and one starting `✗ ` with `→ issue #` reference.

## Cross-spec ordering invariants (= reviewer C5 + I6 consolidation)

| invariant | reason |
|---|---|
| T17a MAY run in parallel with T1 (truth-correction) — no inter-dependency on Postiz registry | T17a only adds issue-source to merged queue, doesn't read handles |
| T17b runs ONLY AFTER T17a | Morning Gmail summarizes heartbeat completed-array which requires heartbeat to be already pulling issues |
| T17c runs ONLY AFTER T16a (article spec thesis-brief skill) is built AND verified by manual fire | Otherwise an article-day gap exists between deleting old daily crons and the heartbeat-dispatched thesis flow being operational |
| T17e MUST follow T1 | Avoid encoding stale Postiz handles in migrated issue bodies |
| T17f runs ONLY AFTER T17a | Output formatter sits inside the extended ops-heartbeat Phase 4 |

## BP-alignment self-score

| BP | identical follow |
|---|---|
| ops-heartbeat existing design | ✓ T17a extends, doesn't reinvent |
| anicca-dais existing auto-issue | ✓ T17e migrates tasks into same scheme |
| Dais "one heartbeat one task" | ✓ Phase 3 picks 1, no batch |
| Dais "morning Gmail yesterday + today" | ✓ T17b new cron 07:00 JST |
| Dais "no per-project cron" | ✓ T17c deletes 10 obsolete |
| Dais "errors → anicca-dais issues" | ✓ already live + Phase 5 standardizes |
| HARD RULE 0.26 (no Dais loop) | ✓ heartbeat resolves errors via auto-issue → fix-cron skill, only escalates true-blocker to Dais via "needs-dais-input" label |

100% BP follow. No invented infrastructure.
