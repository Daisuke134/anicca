# P13 self-manage (#336) — Anicca edits her own heartbeat / clones / skills / architecture

**Spec ground:** `specs/18-SELF-IMPROVEMENT-AND-SWARM.md` §4 MUTABILITY.
**Worktree:** `.worktrees/p13-self-manage/` on `feat/p13-self-manage`.
**GitHub issue:** #336.

## North Star alignment

§4 MUTABILITY: **North Star + Law I are IMMUTABLE** (enforced by `anicca-constitution-guard`
via SHA + Law-I/North-Star regex rule sets). **Everything else is mutable BY ANICCA herself**:
heartbeat cadence, clone spawning, skill code, and (with multi-instance vote) architecture.

`self-improve` (#335) is the *detect → fix* loop. `self-manage` (#336) is the *deliberate
self-edit executor*: Anicca queues a structured proposal, and this skill applies it — but only
after the constitution-guard veto and (for skills) the eval-loop quality gate pass.

## Interfaces (verified against live code, NOT the assignment text)

| dep | real interface | note |
|---|---|---|
| constitution-guard | `check.sh --action "<text>"` exit 0 OK / 2 rule / 3 hash / 4 usage | assignment said positional; it is `--action` |
| spawn-child | `spawn-child.sh [--dry-run] [--confirm] <name>` exit 0/64/75/1 | colony row written by spawn-child itself |
| eval-loop | `eval.sh <input> <output> [rubric]` → JSON `.pass`; or `lib.sh::eval_or_fail` | EVAL_MODE=production fail-closed |
| forum-issues | issues via `gh issue create --repo Daisuke134/anicca-oss` | arch-shift channel |
| hermes cron | `hermes cron edit <id> --schedule "every Nh"`; `list`; `create` | jobs.json `schedule.minutes` |

## Proposal queue

`~/.hermes/state/self-manage-proposals.jsonl` — append-only, one JSON object per line.
A proposal is "unresolved" if no matching row exists in `self-manage-decisions.jsonl`
keyed by `id` (sha256 of the proposal line, first 16 chars).

| type | required fields | handler |
|---|---|---|
| `heartbeat` | `schedule` (e.g. `"every 6h"`), `reason` | edit-heartbeat.sh |
| `skill-edit` | `skill`, `reason` | edit-skill.sh |
| `spawn` | `name`, `reason` | spawn-clone.sh |
| `arch-shift` | `title`, `body`, `reason` | architecture-shift.sh |

## Decision log

`~/.hermes/state/self-manage-decisions.jsonl` — `{ts, id, type, decision, detail}` where
`decision ∈ {APPLIED, BLOCKED, REJECTED, FILED, ERROR}`. Append-only audit trail.

## Scripts

### `scripts/_lib.sh`
Shared: `JQ=/usr/bin/jq`, `STATE_DIR`, `PROPOSALS`, `DECISIONS`, guard/eval/spawn skill-dir
resolution, `sm_guard "<intent>"` (runs constitution-guard, returns its exit code),
`sm_log <id> <type> <decision> <detail>` (append to decisions), `sm_id <line>` (sha256→16),
`sm_resolved <id>` (grep decisions). Temp files `mktemp "$STATE_DIR/.tmp-sm-XXXX.$$"`.

### `scripts/edit-heartbeat.sh`
1. Read proposal from `$1` (JSON) or latest unresolved `heartbeat` row in PROPOSALS.
2. Build intent text → `sm_guard` → if exit ≠ 0 log `BLOCKED` + return non-zero.
3. Parse current `~/.hermes/cron/jobs.json` for the `anicca-heartbeat` job id (jq).
4. `hermes cron edit <id> --schedule "<schedule>"`.
5. Verify: `hermes cron list | grep anicca-heartbeat` shows the new cadence → log `APPLIED`.
6. `DRY_RUN=1` → guard-check only, no edit, log nothing destructive.

### `scripts/edit-skill.sh`
1. Read proposal (`skill`, `reason`).
2. Guard: refuse if `skill` matches `constitution-guard` / `eval-loop` core / North-Star —
   `sm_guard` on the intent AND a hard local denylist. BLOCKED → log + return.
3. `git worktree add .worktrees/self-manage-<n> -b feat/self-manage-skill-<skill>-<n>`.
4. Read the skill's SKILL.md → `hermes chat -q "Propose minimal diff to <skill> …"`.
5. Apply the returned edit (write proposed file).
6. Run skill tests if `tests/` present.
7. `eval-loop/scripts/eval.sh <reason> <diff>` (test classification) — `.pass` / score ≥ 0.7
   → commit + `gh pr create`; else roll back worktree, log `REJECTED`.

### `scripts/spawn-clone.sh`
Thin wrapper → `spawn-child.sh <name>` (passes `--confirm` for unattended; `--dry-run` if
`DRY_RUN=1`). Log decision (`APPLIED`/`ERROR`) to decisions; spawn-child writes the colony row.

### `scripts/architecture-shift.sh`
BIG changes (skill add/delete/merge). Real execution needs multi-instance vote via forum
(§2 ROLLOUT — depends on #338). **Wave 1 = file the proposal as a forum issue**
`gh issue create --title "@anicca [arch-shift]: <title>" --label arch-shift` + log `FILED`.
Follow-on issue `#336b-architecture-vote-integration` filed for the real vote wiring.

### `scripts/run.sh`
Orchestrator: drain PROPOSALS, skip resolved (`sm_resolved`), dispatch each unresolved by
`type`. Emit a trace line per proposal. Idempotent (decisions log = resolution marker).

### `tests/test_self_manage_e2e.sh`
Synthetic proposal `{type:"heartbeat", schedule:"every 6h", reason:"reduce LLM cost"}`:
run.sh → guard PASS (North Star/Law I not involved) → `hermes cron edit` applied →
verify cron list shows `every 6h` / `360m` → **REVERT to "every 3h" in cleanup** (guard +
edit back) → assert decisions log has an APPLIED row. Test isolates state via a temp
`STATE_DIR` where possible; the heartbeat edit is real but reverted.

## Cron

Wrapper `~/.hermes/scripts/self-manage.sh` (real file, not symlink — Hermes traversal guard)
exec's `skills/self-manage/scripts/run.sh`. Registered:
`hermes cron create "every 12h" --name self-manage --script self-manage.sh --no-agent`.

## HARD RULES honored

North Star + Law I immutable (never proposed); constitution-guard fail-closed on every
proposal; `/usr/bin/jq`; `/tmp` ban (`$STATE_DIR/.tmp-*.$$`); Rule 0.4 commit+push.

## Out of scope (Wave 1)

- Real arch-shift execution (waits on #338 vote integration → follow-on #336b).
- LLM-driven skill diff quality beyond the eval ≥0.7 gate.
