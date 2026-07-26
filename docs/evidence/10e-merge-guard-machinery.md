# 10e — merge guard machinery (fixture + real-PR verified, nothing merged)

Atomic 10e is split: **this leg builds the guard machine and proves it on real PRs**. The live
unmanned merge/deploy of a real error-fix PR is a later measured leg. **Merge, deploy, provider
mutation and issue closure remain zero.**

## What exists

| file | role |
|---|---|
| `apps/life-manager/lib/dev-merge-guard.js` | the pipeline + every gate decision, deps-injected |
| `apps/life-manager/scripts/dev-merge-guard.js` | CLI entry (`--pr`, `--review-cmd`, `--ledger`, `--dry-run`) |
| `apps/life-manager/lib/dev-merge-guard.test.js` | 34 tests: gates, edge cases, rollback, ledger shape |
| `apps/life-manager/lib/dev-merge-guard-runtime.test.js` | 5 tests: CLI wiring, no schedule enabled |

Stages run in order and the **first** failure is a hard stop with an honest verdict:

| # | stage | passes only when |
|---|---|---|
| 1 | `eligibility` | PR open, base `main`, branch `feature/lm-dev-<issue>` or `fix/…`, author allowlisted, mergeable, every changed path allowlisted |
| 2 | `tests` | `npm test` **and** `npm run eval` exit 0 in a throwaway worktree of the PR head |
| 3 | `review` | fresh adversary returns `{"verdict":"pass"}`; anything else (incl. unparseable, `"PASS"`, missing) is FAIL |
| 4 | `blocked_actions` | no added line introduces outreach / payment / wallet-transfer calls |
| 5 | `merge` | squash merge + `--match-head-commit`, then a readback proving state `MERGED` and a 40-hex merge sha |
| 6 | `deploy_health` | redeploy → `/health` ok within bound → a **new** deployment id whose `meta.commitHash` equals the merge sha |

Path rules: allow `apps/life-manager/{lib,test,scripts}/**`; deny `.github/**`, any `migration(s)/`
segment, any `.env*`, `docs/superpowers/specs/**` (Dais-owned), `skills/**`, everything else.
`apps/life-manager/package.json` is **conditional**, resolved by parsing the file at both refs:
`dependencies` must be byte-identical, `devDependencies` additive only, and only the
`test`/`pretest` script lines may change. A runtime dep add, a dep version bump, a devDep removal
or bump, a new `postinstall`, or any other manifest field change all refuse.

Every stage emits a record in a sha256 hash chain seeded from the run id, so a ledger row cannot be
edited after the fact without `verifyStageChain` noticing.

## Railway rollback — what the CLI actually supports (verified 2026-07-27, railway 5.28.0)

| claim | verified how | result |
|---|---|---|
| `railway redeploy` can target an old deployment | `railway redeploy --help` | **No.** Only `-s -e -p -y --json --from-source`. No id argument. |
| `railway deployment` has a rollback subcommand | `railway deployment --help` | **No.** Only `list`, `up`, `redeploy`. |
| the API can roll back | `railway api search deploymentRollback` | **Yes.** `Mutation.deploymentRollback(id: String!): Boolean!` — "Rolls back to a deployment." |
| a deployment advertises rollback-ability | `railway api search canRollback` | **Yes.** `Deployment.canRollback: Boolean!` |

So rollback is implemented as `railway api` + that mutation, gated on the pre-merge deployment's
`canRollback`. When Railway says `canRollback: false` the guard does **not** pretend: it opens an
automatic revert PR of the merge commit, alerts, and records that production is still on the bad
commit until the revert lands. Live readback of the current production deployment
(`8d962a6f-c7dd-4b21-9d6f-68c07135f5b1`, commit `1faec3e6…`) reports `canRollback: true`.

## Ledger

Appended to `$LM_DEV_GUARD_LEDGER`, default `~/.life-manager/state/dev-guard-runs.jsonl`, mode 0600.
This file is 10f's Day-N evidence source. One row per run, 16 fields: `schema_version, run_id, pr,
started_at, finished_at, duration_ms, verdict, stopped_at_stage, stop_reason, stages_passed,
stages_failed, stages, merge_sha, deploy_id, health, rollback`.

## Measured

| run | result |
|---|---|
| `node --test lib/dev-merge-guard*.test.js` | 39/39 pass, 0 fail |
| full `npm test` | exit 0 |
| real CLI vs **PR #1092** | `stopped` at `eligibility` — `branch_name,not_mergeable,path_allowlist,package_json:dependencies_changed`; real denials `docs/superpowers/specs/…` (`deny:spec`), `execution-notes.md`, `docs/evidence/…`. No merge. |
| real CLI vs **PR #1094** (`--dry-run`) | passed `eligibility, tests, review, blocked_actions` on live data; stopped at `merge` with `dry_run`. The `tests` stage really ran the suite + all 7 evals (100%) in a throwaway worktree of `feature/lm-dev-1090`, exit 0. Pre-merge rollback target read live from Railway. No merge, no deploy. |

The PR #1094 run also caught a real defect: GitHub answers `mergeable: UNKNOWN` on the first read of
a PR it has not recomputed since the last push, which made the guard refuse a genuinely mergeable
PR. The guard now retries that read (bounded) instead of turning GitHub's laziness into a false
refusal — and still refuses honestly if it stays UNKNOWN.

## Not in this leg

No cron, no launchd, no schedule is enabled — 10f owns re-enabling the daily run. Nothing was
merged, deployed or closed.
