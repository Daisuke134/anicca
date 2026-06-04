# forum-issues skill — design spec (#334, P9, Phase 3 collective brain)

| Field | Value |
|---|---|
| Date | 2026-06-05 |
| Task | #334 / TaskList #16 |
| Worktree | /Users/anicca/anicca-oss/.worktrees/p9-forum-issues (branch feat/p9-forum-issues) |
| Grounding | specs/24-FORUM-UX-CODE-TRUTH.md §1-3, specs/18-SELF-IMPROVEMENT-AND-SWARM.md §2, specs/19-REF-SYMPHONY.md |
| Goal | Build skills/forum-issues/ — the ①POST ②ACK ③DISCUSS slice of the 6-stage forum lifecycle on github.com/Daisuke134/anicca-oss Issues |

## § 1. Scope (what this skill DOES — stages ①②③ only)

Stages ④implement ⑤vote/merge ⑥roll-out are OUT (owned by #335/#338). This skill owns:

| Stage | Mechanism (spec 24 §2 verbatim source) | This skill |
|---|---|---|
| ① POST | issues are opened by anyone | poll only — does not open issues |
| ② ACK | 👀 reaction + sticky tracking comment (OpenHands `_add_reaction`, claude-code-action `create-initial.ts`) | `poll.sh` |
| ③ DISCUSS | thread = memory, re-fetch whole thread each tick; LLM responds (claude-code-action `fetcher.ts`) | `respond.sh` |

## § 2. Trigger detection (spec 24 §2, claude-code-action `trigger.ts`)

Word-boundary regex, GNU-ERE: `(^|\s)@anicca([\s.,!?;:]|$)`. Applied to:
- issue **body** (the opening post), AND
- every **comment** body in the thread.

A mention is **new** if its `(issue_n, source_id)` pair is NOT already in the state log, where `source_id` = `issue-<n>` for the body or the comment id for a comment. The first new mention on an issue triggers ACK.

## § 3. State log — `~/.hermes/state/forum-state.jsonl`

Append-only JSONL. One row per claimed issue:
```json
{"issue_n":42,"comment_id":1234567,"claimed_at":"2026-06-05T12:00:00Z","mentions_seen":["issue-42"],"responded_to":["issue-42"]}
```
| Field | Meaning |
|---|---|
| `issue_n` | issue number |
| `comment_id` | id of OUR sticky tracking comment (created in ACK) |
| `claimed_at` | UTC ISO8601 of claim |
| `mentions_seen` | array of `source_id` we have ACK-seen (dedup for ②) |
| `responded_to` | array of `source_id` we have answered (dedup for ③) |

"Latest row wins" — `respond.sh` reads the last row per `issue_n` (jsonl is appended; we re-append an updated row rather than mutate). Read via `jq -s 'group_by(.issue_n) | map(.[-1])'`.

## § 4. poll.sh — ② ACK

```
1. issues = gh api repos/Daisuke134/anicca-oss/issues?state=open --paginate  (jq: exclude .pull_request)
2. for each issue N:
   a. body_mention = grep body against trigger regex
   b. claimed = is N already in state log (any row)?
   c. if body_mention AND NOT claimed:
        - POST 👀: gh api ...issues/N/reactions -f content=eyes        (idempotent: gh returns existing)
        - CREATE sticky comment: gh api ...issues/N/comments -f body="<INITIAL>"  → capture .id
        - append row {issue_n:N, comment_id:<id>, claimed_at:now, mentions_seen:["issue-N"], responded_to:[]}
```
INITIAL sticky body (claude-code-action create-initial.ts style — claim + empty progress slot):
```
👀 **Anicca picked this up** — tracking here.

| stage | status |
|---|---|
| ack | ✅ claimed <ts> |
| discuss | ⏳ pending |

_This comment updates in place as the discussion progresses._
```

Note: a comment-only @mention on an UNclaimed issue also claims it (source_id = comment id). Covered by checking BOTH body and comments in poll; first-seen claims.

## § 5. respond.sh — ③ DISCUSS (one debate round)

```
for each row in state log (latest per issue_n):
   1. thread = gh api ...issues/N/comments  (full re-fetch = memory)  + issue body
   2. new_mentions = source_ids matching trigger regex NOT in responded_to[]
   3. if new_mentions empty → skip
   4. build prompt: issue title+body + full thread + persona + stop-word rule
   5. resp = hermes chat -q "<prompt>" -Q   (with exponential-backoff retry 3x: 2s,4s,8s)
   6. if resp empty after retries → write fallback "still thinking" (discussion NEVER stalls — AutoGen selector fallback)
   7. PATCH sticky comment: gh api --method PATCH ...issues/comments/<comment_id> -f body="<INITIAL + --- + resp>"
   8. append updated row: responded_to += new_mentions, discuss stage ✅
```

### Debate-round / opinion-update (spec 24 §2, llm_multiagent_debate)
The prompt instructs the agent: "Other participants' latest messages are in the thread above. Read them, update your own position, and either advance the discussion or, if you and the others agree, end your message with the single word CONSENSUS." → bounded by stop-word.

### Stop word / max_turns (AutoGen `_base_group_chat_manager.py`)
- If any comment in the thread contains the standalone token `CONSENSUS` → respond.sh marks the issue done (no further responses; final sticky note "✅ CONSENSUS reached").
- `FORUM_MAX_TURNS` (default 6) — our `responded_to` length per issue caps; beyond it, sticky note "⏹ max turns" and stop.

### Noise filter (spec 24 §2, classify_inline_comments)
A mention is **real** (escalates to hermes chat) only if the mention's surrounding text length ≥ 12 chars beyond the `@anicca` token OR contains `?`. A bare `@anicca` ping with no substance is ACK'd (👀) but NOT escalated to an LLM job — prevents billions-scale noise spend.

## § 6. run.sh — orchestrator

```
set -euo pipefail
poll.sh    # ACK new claims
respond.sh # one discuss round on pending
# idempotent: re-running with no new mentions = no-op, exit 0
```

## § 7. Secrets / HARD RULES

| Rule | Implementation |
|---|---|
| GH_TOKEN from env, never echoed | scripts rely on `gh` keyring auth (already logged in as Daisuke134); no token printed. If `GH_TOKEN` set, gh uses it; we never `echo` it. |
| /usr/bin/jq | hard-coded `JQ=/usr/bin/jq` |
| /tmp ban | temp files at `~/.hermes/state/.tmp-forum-<name>.$$`, trap-cleanup |
| cron --script traversal guard | real wrapper `~/.hermes/scripts/forum-issues.sh` (NOT symlink) execs canonical path, per #323/#325 pattern |

## § 8. Cron

`hermes cron create "every 3h" --name forum-issues --script forum-issues.sh --no-agent`
- `--no-agent`: the script IS the job (poll+respond do their own LLM call via `hermes chat`); stdout delivered verbatim. Empty stdout = silent (no new mentions).

## § 9. E2E test — tests/test_forum_issues_e2e.sh

```
1. create test issue: gh issue create -R Daisuke134/anicca-oss -t "[forum-e2e] ..." -b "@anicca please reply with pong-forum"
2. run scripts/run.sh
3. assert within 60s:
   - 👀 reaction present on the issue   (gh api ...reactions --jq 'any(.content=="eyes")')
   - a tracking comment by our user exists (state log has row for issue_n)
   - the sticky comment body contains hermes output (non-empty discuss section)
4. cleanup: gh issue close the test issue + comment "e2e done"
```
PASS criteria (task done): test issue receives @anicca → tracking comment within 15min (we target 60s) + 1 debate round simulated (sticky updated with a response).

## § 10. Files

```
skills/forum-issues/
  SKILL.md
  README.md
  scripts/poll.sh
  scripts/respond.sh
  scripts/run.sh
  scripts/_lib.sh        # shared: JQ, REPO, trigger regex, state read/append, log helpers
  tests/test_forum_issues_e2e.sh
~/.hermes/scripts/forum-issues.sh   # wrapper (real file, execs canonical)
```

## § 11. Self-review

- placeholders: none — all gh/jq calls concrete.
- scope: stages ①②③ only; ④⑤⑥ explicitly OUT.
- contradictions: state log is append-only but "latest row wins" — resolved via group_by last.
- ambiguity: noise-filter threshold (12 chars / `?`) is a concrete heuristic, not "TBD".
- secrets: gh keyring, no echo.
