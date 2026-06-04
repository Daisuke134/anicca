# forum-issues implementation plan (#334, P9)

Spec: docs/superpowers/specs/2026-06-05-forum-issues-design.md

## Task 1 — _lib.sh (shared helpers)
File: skills/forum-issues/scripts/_lib.sh
- `JQ=/usr/bin/jq`, `REPO=Daisuke134/anicca-oss`, `STATE_DIR=${STATE_DIR:-$HOME/.hermes/state}`, `STATE=$STATE_DIR/forum-state.jsonl`
- `TRIGGER='(^|\s)@anicca([\s.,!?;:]|$)'`
- `forum_has_trigger <text>` → grep -Eq
- `forum_is_real <text>` → real if >12 chars after @anicca OR contains `?`
- `forum_claimed <n>` → row exists in STATE for issue_n
- `forum_rows_latest` → `jq -s 'group_by(.issue_n)|map(.[-1])'`
- `forum_append <json>` → append line to STATE (mkdir -p first)
- temp via `mktemp "$STATE_DIR/.tmp-forum-XXXX.$$"` + trap cleanup
Test: source + `forum_has_trigger "hey @anicca?"` → 0; `forum_has_trigger "email@aniccaai"` → 1.

## Task 2 — poll.sh (ACK)
File: skills/forum-issues/scripts/poll.sh
- list open issues (exclude .pull_request), for each unclaimed with body OR comment trigger: 👀 + sticky comment + append row.
Test (RED→GREEN): mock via function override OR live test in E2E.

## Task 3 — respond.sh (DISCUSS one round)
File: skills/forum-issues/scripts/respond.sh
- for each latest row: re-fetch thread, find new real mentions not in responded_to, CONSENSUS/max_turns guard, hermes chat with backoff, PATCH sticky, append updated row.

## Task 4 — run.sh
File: skills/forum-issues/scripts/run.sh — poll.sh then respond.sh, set -euo pipefail.

## Task 5 — SKILL.md + README.md
Hermes frontmatter (name/description). README: what/how-invoked/state/failure mode.

## Task 6 — wrapper + cron
- ~/.hermes/scripts/forum-issues.sh (real file, exec canonical run.sh)
- hermes cron create "every 3h" --name forum-issues --script forum-issues.sh --no-agent

## Task 7 — E2E test
File: skills/forum-issues/tests/test_forum_issues_e2e.sh — live issue, run, assert 👀 + sticky + response, cleanup.

## Task 8 — verification gate + commit/push
Run E2E, 5-step verify, per-task commits, final push to origin/feat/p9-forum-issues.
