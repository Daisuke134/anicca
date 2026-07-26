# 10e — merge guard machinery (fixture + real-PR verified, nothing merged)

Atomic 10e is split: **this leg builds the guard machine and proves it on real PRs**. The live
unmanned merge/deploy of a real error-fix PR is a later measured leg. **Merge, deploy, provider
mutation and issue closure remain zero.**

## What exists

| file | role |
|---|---|
| `apps/life-manager/lib/dev-merge-guard.js` | the pipeline + every gate decision, deps-injected |
| `apps/life-manager/scripts/dev-merge-guard.js` | CLI entry (`--pr`, `--review-cmd`, `--ledger`, `--dry-run`) |
| `apps/life-manager/lib/dev-merge-guard.test.js` | 56 tests: gates, edge cases, rollback, ledger chain, lock, self-deny |
| `apps/life-manager/lib/dev-merge-guard-runtime.test.js` | 5 tests: CLI wiring, no schedule enabled |

Stages run in order and the **first** failure is a hard stop with an honest verdict. **Review and
the tripwire come before the test suite**, because the suite executes the PR's own code:

| # | stage | passes only when |
|---|---|---|
| 1 | `eligibility` | PR open, base `main`, branch `feature/lm-dev-<issue>` or `fix/…`, author allowlisted, mergeable, every changed path allowlisted |
| 2 | `review` | fresh adversary returns `{"verdict":"pass"}`; anything else (incl. unparseable, `"PASS"`, missing) is FAIL |
| 3 | `blocked_actions` | no added line introduces outreach / payment / wallet-transfer calls |
| 4 | `tests` | `npm test` **and** `npm run eval` exit 0 in a throwaway worktree of the PR head, installed with `npm ci --ignore-scripts` |
| 5 | `merge` | squash merge + `--match-head-commit`, then a readback proving state `MERGED` and a 40-hex merge sha |
| 6 | `deploy_health` | redeploy → `/health` ok within bound → a **new** deployment id whose `meta.commitHash` equals the merge sha |

The whole run holds an O_EXCL lockfile next to the ledger (stale after 30 min); a second concurrent
runner exits `locked` and writes no row.

Path rules: allow `apps/life-manager/{lib,test,scripts}/**`; deny `.github/**`, any `migration(s)/`
segment, any `.env*`, `docs/superpowers/specs/**` (Dais-owned), `skills/**`, everything else.
`apps/life-manager/package.json` is **conditional**, resolved by parsing the file at both refs:
`dependencies` must be byte-identical, `devDependencies` additive only, and only the
`test`/`pretest` script lines may change. A runtime dep add, a dep version bump, a devDep removal
or bump, a new `postinstall`, or any other manifest field change all refuse. A manifest that cannot
be read at **either** ref refuses (`package_json:unreadable`) rather than comparing two empties.

**The guard cannot be modified by what it guards.** `apps/life-manager/{lib,scripts}/dev-merge-guard*`
and whatever file `--review-cmd` resolves to (by realpath, at runtime) are denied at eligibility,
so the two-PR takeover — PR 1 weakens the gate, PR 2 walks through it — dies at stage one. Changes
to the guard require a human-merged PR.

The changed-file list is `git diff --name-status -M <base>...<headOid>` at the fetched head, and the
reviewed diff is `git diff <base>...<headOid>` from the same pinned commit. `gh pr view --json files`
truncates at 100 entries and collapses renames to the new path, and `gh pr diff` follows a branch the
author can move after the reviewer has spoken; both are kept only as a recorded cross-check.

Every stage emits a record in a sha256 hash chain seeded from the run id, and **rows chain to each
other** (`prev` = sha256 of the previous row's `record_hash`, genesis constant for the first). Each
run verifies the tail before writing and alerts on a mismatch. Honest limit: the hash is public and
the file is runner-writable, so this is tamper-**evident** against casual editing/truncation, not
tamper-proof; the upgrade is an HMAC keyed off-runner (noted in the source, not implemented).

## What this guard is not

The `tests` stage runs the PR's own suite on the runner, which is arbitrary code execution by
construction — a test file *is* code. Three things bound the blast radius: review-first ordering,
the path allowlist, and self-deny. `npm ci --ignore-scripts` removes install hooks. **None of that
is a sandbox.** Real isolation (container/VM, no network, no credentials, no write access to this
repo) is **not implemented** and is future work.

## Railway rollback — what the CLI actually supports (verified 2026-07-27, railway 5.28.0)

| claim | verified how | result |
|---|---|---|
| `railway redeploy` can target an old deployment | `railway redeploy --help` | **No.** Only `-s -e -p -y --json --from-source`. No id argument. |
| `railway deployment` has a rollback subcommand | `railway deployment --help` | **No.** Only `list`, `up`, `redeploy`. |
| the API can roll back | `railway api search deploymentRollback` | **Yes.** `Mutation.deploymentRollback(id: String!): Boolean!` — "Rolls back to a deployment." |
| a deployment advertises rollback-ability | `railway api search canRollback` | **Yes.** `Deployment.canRollback: Boolean!` |

So rollback is implemented as `railway api` + that mutation, gated on the pre-merge deployment's
`canRollback`. When Railway says `canRollback: false` — **or when the mutation itself answers
`false`** — the guard does **not** pretend: it opens an automatic revert PR of the merge commit,
alerts, and records that production is still on the bad commit until the revert lands. The verdict
is derived from what the rollback actually achieved: `rolled_back` only on a real remedy,
`rollback_failed` when both the platform rollback and the revert PR failed. Live readback of the
current production deployment (`8d962a6f-c7dd-4b21-9d6f-68c07135f5b1`, commit `1faec3e6…`) reports
`canRollback: true`.

Alerts route to the admin Telegram chat (`LM_ADMIN_TELEGRAM_CHAT_ID` via `LM_TELEGRAM_BOT_TOKEN`),
falling back to stderr only when the bot is unconfigured or the send fails — an unattended runner's
stderr is functionally `/dev/null`, and "a revert PR is waiting for a human" has to reach a phone.

## Ledger

Appended to `$LM_DEV_GUARD_LEDGER`, default `~/.life-manager/state/dev-guard-runs.jsonl`, mode 0600.
This file is 10f's Day-N evidence source. One row per run, `schema_version: 2`, 20 fields:
`schema_version, run_id, pr, started_at, finished_at, duration_ms, verdict, stopped_at_stage,
stop_reason, stages_passed, stages_failed, stages, merge_sha, deploy_id, health, rollback,
post_merge_error, ledger_check, prev, record_hash`.

Everything after a successful merge is wrapped so a throw still writes the row: `post_merge_error`
carries the failure and the verdict becomes `merged_unverified`. A merge that happened must never go
unrecorded.

## Measured

| run | result |
|---|---|
| `node --test lib/dev-merge-guard*.test.js` | 61/61 pass, 0 fail |
| full `npm test` | exit 0 (1012 assertions across 40 sub-suites) |
| real CLI vs **PR #1092** | `stopped` at `eligibility` — `branch_name,not_mergeable,path_allowlist,package_json:dependencies_changed`; real denials `docs/superpowers/specs/…` (`deny:spec`), `execution-notes.md`, `docs/evidence/…`. No merge. |
| real CLI vs **PR #1094** (`--dry-run`) | passed `eligibility, tests, review, blocked_actions` on live data; stopped at `merge` with `dry_run`. The `tests` stage really ran the suite + all 7 evals (100%) in a throwaway worktree of `feature/lm-dev-1090`, exit 0. Pre-merge rollback target read live from Railway. No merge, no deploy. *(Recorded before the review-first reorder; the stage set is the same, the order is now `eligibility, review, blocked_actions, tests`.)* |

The PR #1094 run also caught a real defect: GitHub answers `mergeable: UNKNOWN` on the first read of
a PR it has not recomputed since the last push, which made the guard refuse a genuinely mergeable
PR. The guard now retries that read (bounded) instead of turning GitHub's laziness into a false
refusal — and still refuses honestly if it stays UNKNOWN.

## Not in this leg

No cron, no launchd, no schedule is enabled — 10f owns re-enabling the daily run. Nothing was
merged, deployed or closed.
