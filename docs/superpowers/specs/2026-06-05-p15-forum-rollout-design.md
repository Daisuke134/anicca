# P15 forum-rollout (#338) — consensus → action loop — DESIGN

| field | value |
|---|---|
| spec | this file |
| plan | `docs/superpowers/plans/2026-06-05-p15-forum-rollout.md` |
| skill | `skills/forum-rollout/` |
| branch | `feat/p15-forum-rollout` |
| worktree | `.worktrees/p15-forum-rollout/` |
| master row | `specs/00-MASTER.md` row 14 (#338) |
| parent spec | `specs/18-SELF-IMPROVEMENT-AND-SWARM.md` §2 (flow), §5 (forum roll-out task) |
| depends on (LIVE) | `skills/forum-issues/` · `skills/self-manage/scripts/{edit-skill,edit-heartbeat,spawn-clone,architecture-shift}.sh` · `skills/anicca-constitution-guard/scripts/check.sh` |

## 1. Problem

forum-issues drives `post → ACK (👀 + sticky) → DISCUSS (Round N) → CONSENSUS`. At
CONSENSUS the agreed action is **only text** — nothing executes. P15 closes the loop:
read the consensus, extract the structured action block, dispatch it to the already-merged
self-manage handlers (or `gh` for PR/issue ops), record the decision, comment the evidence,
and close the issue. Idempotent + guard-gated + dry-run-by-default.

## 2. Where the action block lives (CRITICAL — interaction with forum-issues)

forum-issues `respond.sh` rewrites the **sticky** comment body on CONSENSUS via
`render_sticky(...,"")` — which **discards** any free-text response. Therefore the action
block must NOT be assumed to survive inside the sticky body. **rollout scans EVERY comment
in the thread (plus the issue body), newest-first, for a rollout block.** A rollout block is:

- a line whose trimmed content starts with `CONSENSUS:` (the consensus marker), AND
- somewhere after it (same comment), a fenced ` ```rollout ` … ` ``` ` block.

If the `CONSENSUS:` marker and the ` ```rollout ` fence are in the **same comment**, that
comment is a rollout source. The bare stop-word `CONSENSUS` (forum-issues stop-word, no
colon) is ignored by rollout — only `CONSENSUS:` (with colon) + a rollout fence triggers it.
This keeps forum-issues' stop-word and rollout's trigger orthogonal and non-colliding.

### Action block schema (inside the ```rollout fence)

```
ACTION: edit-skill | edit-heartbeat | spawn-clone | architecture-shift | merge-pr | close-issue | open-pr
TARGET: <skill name | file path | issue/pr number>
PAYLOAD: { ...action-specific JSON (single line) ... }
```

- `ACTION` / `TARGET` are `KEY: value` lines (case-insensitive key).
- `PAYLOAD` is a single-line JSON object (may be `{}`). Parsed with jq.
- Unknown ACTION → log `BLOCKED` (reason `unknown-action`), skip.

## 3. Dispatch matrix

| ACTION | calls | argv built from |
|---|---|---|
| edit-skill | `skills/self-manage/scripts/edit-skill.sh '<json>'` | `{type:"skill-edit", skill:TARGET, reason:PAYLOAD.reason}` merged with PAYLOAD |
| edit-heartbeat | `skills/self-manage/scripts/edit-heartbeat.sh '<json>'` | `{type:"heartbeat", schedule:(PAYLOAD.schedule//TARGET), reason:PAYLOAD.reason}` |
| spawn-clone | `skills/self-manage/scripts/spawn-clone.sh '<json>'` | `{type:"spawn", name:(PAYLOAD.name//TARGET), reason:PAYLOAD.reason}` |
| architecture-shift | `skills/self-manage/scripts/architecture-shift.sh '<json>'` | `{type:"arch-shift", title:(PAYLOAD.title//TARGET), body:PAYLOAD.body, reason:PAYLOAD.reason}` |
| merge-pr | `gh pr merge <TARGET> --squash --delete-branch --repo <REPO>` | TARGET = PR number |
| close-issue | `gh issue close <TARGET> --repo <REPO> --comment "<rolled-out>"` | TARGET = issue number |
| open-pr | `gh pr create --repo <REPO> --title <PAYLOAD.title> --body <PAYLOAD.body> --head <PAYLOAD.head> [--base <PAYLOAD.base>]` | from PAYLOAD |

self-manage handlers inherit `DRY_RUN` from the environment: rollout exports `DRY_RUN=1` in
dry-run mode, so the entire chain (guard + denylist + eval) runs without side effects.
For `gh` actions, dry-run prints the intended command and does NOT execute.

The merged JSON for self-manage handlers is built as
`(PAYLOAD) * {type, <target-field>, reason}` (jq `*` deep-merge, explicit keys win) so any
extra PAYLOAD fields pass through while the canonical fields are guaranteed present.

## 4. Safety (pre-dispatch, in order)

1. **constitution-guard**: `check.sh --action "<action_summary>"`. Exit 0 = allow; else log
   `BLOCKED` row (exit_code = guard rc) + skip. Fail-closed: guard missing/unrunnable ⇒ block.
2. **HARD-NO-LIST** (hardcoded in `rollout.sh`, defence-in-depth, independent of guard):
   `anicca-constitution-guard eval-loop anicca-payout-ubi anicca-wallet forum-rollout`.
   If TARGET (skill name OR a path/number string containing any HARD-NO token as a whole
   word/path-segment) matches → log `BLOCKED` (reason `hard-no-list`), skip. Applies to ALL
   action types (e.g. `merge-pr` of a PR titled to touch a chokepoint is matched on TARGET
   text only — TARGET for merge-pr is a number, so the guard's free-text summary is the
   primary defence there; the HARD-NO list is the skill-name defence for self-manage actions).
3. **Idempotency**: `consensus_sha = sha256(CONSENSUS-marker-line + "\n" + rollout-fence-body)`.
   If `(issue_n, consensus_sha)` already present in `forum-rollout.jsonl` → skip (no log spam:
   a single `already-applied` debug line to stdout, no new jsonl row).

## 5. Modes

| flag | behaviour |
|---|---|
| `--dry-run` (DEFAULT) | guard + denylist + idempotency run; dispatch prints intended call; self-manage handlers run with `DRY_RUN=1`; `gh` actions print only; jsonl row `applied:false`. |
| `--confirm` | live: self-manage handlers run for real; `gh` actions execute; evidence comment + issue close happen; jsonl row `applied:true`. |

**Cron default**: the wrapper runs `--confirm` IFF `~/.hermes/state/rollout-allow.flag` exists
(Dais-controlled escape hatch). Otherwise `--dry-run`. This makes Wave-1 rollout safe by
default — live execution requires Dais to `touch` the flag once.

## 6. State / decision log

`~/.hermes/state/forum-rollout.jsonl`, one row per dispatched action:

```json
{"ts":"2026-06-05T..Z","issue_n":11,"consensus_sha":"<64hex>","action_type":"architecture-shift",
 "target":"#336b merge X+Y","applied":false,"exit_code":0,"evidence_url":"<url|sha|dry-run>"}
```

- `applied` = true only in `--confirm` mode after the dispatch returns exit 0.
- `evidence_url` = handler output URL/sha if parseable, else `"dry-run"` / `"BLOCKED:<reason>"`.
- Idempotency key = `(issue_n, consensus_sha)`.

## 7. Post-rollout (--confirm, on dispatch exit 0 only)

1. Comment on the issue: `✅ rolled out: <ACTION> <TARGET>. Evidence: <evidence_url>`.
2. `gh issue close <issue_n> --comment "rolled out (#338 forum-rollout)"`.

A `close-issue` ACTION whose TARGET == the issue itself is allowed (idempotent: gh close on an
already-closed issue is a no-op). In dry-run neither comment nor close happens.

## 8. Files

| file | purpose |
|---|---|
| `skills/forum-rollout/scripts/_lib.sh` | JQ/REPO/STATE constants; `fr_*` helpers (extract block, sha, guard, hard-no, log, idempotency) |
| `skills/forum-rollout/scripts/rollout.sh` | main: scan issues → extract → safety → dispatch → log → comment/close |
| `skills/forum-rollout/scripts/run.sh` | cron entry: reads rollout-allow.flag → picks `--confirm`/`--dry-run` |
| `skills/forum-rollout/SKILL.md` | frontmatter + triggers + usage |
| `skills/forum-rollout/README.md` | one-screen operator doc |
| `skills/forum-rollout/tests/test_lib.sh` | unit: block extraction, sha stability, hard-no match, idempotency, argv build |
| `skills/forum-rollout/tests/test_rollout_e2e.sh` | offline E2E: fixture thread (CONSENSUS: + rollout fence) → rollout --dry-run → assert correct dispatch + jsonl row |
| `~/.hermes/scripts/forum-rollout.sh` | real-file wrapper (execs canonical run.sh) |

## 9. Test strategy (TDD)

- **Unit (`test_lib.sh`)**, offline, no network:
  - extract ACTION/TARGET/PAYLOAD from a fenced block (happy path + missing fence + unknown action).
  - `fr_consensus_sha` deterministic + differs when block content differs.
  - `fr_hard_no` matches each HARD-NO token as TARGET, allows a normal skill name.
  - argv builder produces the right JSON per action type (jq deep-merge, explicit keys win).
  - idempotency: second call with same (issue_n, sha) is detected.
- **E2E (`test_rollout_e2e.sh`)**, offline: monkeypatch `gh` + self-manage handler dir via env
  (`FR_DISPATCH_GH`, `FR_SELF_MANAGE_DIR` overrides → point at fake stubs that echo+exit 0).
  Feed a fixture issue list + thread via `FR_FIXTURE_DIR`. Run `rollout.sh --dry-run`. Assert:
  (a) the architecture-shift handler stub was invoked with a JSON arg containing the title,
  (b) a jsonl row with `action_type:"architecture-shift"`, `applied:false` was written,
  (c) re-running is idempotent (no second row).

`rollout.sh` therefore reads its issue/thread data through a thin seam:
`fr_list_issues` / `fr_thread <n>` call `gh` by default but honour `FR_FIXTURE_DIR` (a dir with
`issues.json` + `thread-<n>.json`) when set — pure offline tests, real `gh` in production.

## 10. Cron

`hermes cron add --script forum-rollout.sh --schedule "every 180m" --no-agent`, named
`forum-rollout`, firing after the `forum-issues` 180m round. Idempotency makes overlap safe.

## 11. Out of scope (Wave 2+)

- Multi-instance vote tally (#336b) — rollout consumes a CONSENSUS marker, it does not yet
  count votes across instances. A CONSENSUS: + rollout block placed by the discussion IS the
  trigger; quorum logic is #336b.
- `predict` rehearsal before rollout (#337 MiroFish).
