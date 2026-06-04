# P14 — swarm-exec + predict + resurrection (#337) — Implementation Plan

> Bite-sized (2-5 min) steps. Spec: `docs/superpowers/specs/2026-06-05-p14-swarm-skills-design.md`.
> Worktree `.worktrees/p14-swarm-skills` on `feat/p14-swarm-skills`. TDD: RED before GREEN per skill.
> All paths absolute or repo-relative from the worktree root. `/usr/bin/jq` always.

## Phase 0 — worktree
- [ ] `git worktree add .worktrees/p14-swarm-skills -b feat/p14-swarm-skills` (from up-to-date main).
- [ ] verify `.worktrees/` is gitignored (`git check-ignore .worktrees/p14-swarm-skills` → printed).
- [ ] baseline: `bash skills/self-manage/tests/test_self_manage_e2e.sh` is the existing-green sanity (skip if it mutates cron; instead `/usr/bin/jq --version` + `gh auth status` as env baseline).

## Phase 1 — swarm-exec (TDD)

### 1a RED
- [ ] write `skills/anicca-swarm-exec/tests/test_swarm_exec.sh` per spec §5 (4 assertions, builds a
      local `git init` mock repo, uses `echo:hello` + an unknown task_id). Run → FAIL (no scripts yet).

### 1b GREEN — _lib.sh
- [ ] `skills/anicca-swarm-exec/scripts/_lib.sh`: JQ, STATE_DIR, LEDGER path, `se_id`, `se_mktemp`,
      `swarm_runner_for <task_id>` (case: `echo:*`→echo rest; `selftest`→`ls -la && git rev-parse HEAD`;
      `*`→`exit 65`), `se_parse_owner_repo <url>` (strip proto/.git → owner/repo), `se_log <json>`.

### 1c GREEN — swarm-exec.sh
- [ ] `skills/anicca-swarm-exec/scripts/swarm-exec.sh <peer_repo_url> <branch> <task_id>`:
      parse owner/repo → size gate (`gh repo view --json diskUsage`; >100MB → exit 78 ledger row) →
      clone depth-1 to `~/.cache/anicca-clones/<owner>__<repo>` (EXIT trap rm -rf) →
      `timeout 600 env -i PATH=/usr/bin:/bin HOME=$HOME bash --noprofile --norc -c '...'` →
      capture to `~/.hermes/state/swarm-exec/<task_id>.log` chmod 600 →
      optional PATCH sticky comment if `SWARM_COMMENT_ID` set →
      append ledger row {ts,peer_repo,branch,task_id,exit_code,duration_s,result_url,size_mb,mode}.
- [ ] run test → GREEN (4/4).

### 1d docs
- [ ] `SKILL.md` (frontmatter: name, description, metadata.spec/github_issue/cadence:manual,
      parallel_safe:true) + `README.md` (CLI, safety, ledger schema, Wave-2 note).

## Phase 2 — predict (TDD)

### 2a RED
- [ ] `skills/anicca-predict/tests/test_predict.sh` per spec §5 (4 assertions; uses
      `PREDICT_NOW_OVERRIDE` to force expiry; injects an evidence script returning "won"). FAIL.

### 2b GREEN — _lib.sh
- [ ] `_lib.sh`: JQ, STATE_DIR, PREDICTIONS/POT/EVIDENCE_DIR paths, `pr_id`, `pr_now` (honors
      `PREDICT_NOW_OVERRIDE`), `pr_testable <claim>` (metric regex AND deadline regex),
      `pr_horizon_secs <claim>` (parse "within/in N h|d", default 48h).

### 2c GREEN — predict.sh + resolve.sh
- [ ] `predict.sh <claim> <stake>`: validate (exit 64 if not testable) → compute deadline_ts →
      append `predictions.jsonl` row {prediction_id,ts,claim,stake_usdc,deadline_ts,status:open}.
- [ ] `resolve.sh`: for each open+expired row → run evidence script (timeout 60, stdout must be
      won|lost) else unresolved → append `predict-pot.jsonl` mock row → atomic full-file rewrite of
      `predictions.jsonl` with updated row. Append `predict.jsonl` trace line.
- [ ] run test → GREEN (4/4).

### 2d docs
- [ ] `SKILL.md` + `README.md` (CLI, schema table, Wave-2 wallet_lib hook).

## Phase 3 — resurrection (TDD)

### 3a RED
- [ ] `skills/anicca-resurrection/tests/test_resurrection.sh` per spec §5 (4 assertions; isolated
      STATE_DIR; checks checkpoint keys, ledger rows, mockup-dir cleanup). FAIL.

### 3b GREEN — _lib.sh
- [ ] `_lib.sh`: JQ, STATE_DIR, CHECKPOINTS_DIR, LEDGER, `rs_id`, repo-root resolve, `rs_log <json>`.

### 3c GREEN — checkpoint.sh + restart.sh
- [ ] `checkpoint.sh`: gather model/profile/last_skill_run/last_decision/hermes_config_sha/
      anicca_oss_sha (best-effort, fallbacks) → id → write `checkpoints/<id>.json` chmod 600 →
      ledger checkpoint row.
- [ ] `restart.sh <checkpoint_id>`: read checkpoint (exit 66 if missing) → mkdir
      `~/.hermes-resurrected-<id>/` (EXIT trap rm -rf) → copy checkpoint + cron/jobs.json +
      heartbeat.jsonl → `HERMES_HOME=<mockup> hermes status` (timeout 60) → ledger restart row
      {op:restart, checkpoint_id, resurrected_home, status_exit, ok}.
- [ ] run test → GREEN (4/4).

### 3d docs
- [ ] `SKILL.md` + `README.md`.

## Phase 4 — wire crons (predict + resurrection only; swarm-exec = manual)
- [ ] real wrapper `~/.hermes/scripts/anicca-predict.sh` → exec `.../anicca-predict/scripts/resolve.sh`.
- [ ] real wrapper `~/.hermes/scripts/anicca-resurrection.sh` → exec `.../anicca-resurrection/scripts/checkpoint.sh`.
- [ ] symlinks `~/.hermes/skills/anicca-{swarm-exec,predict,resurrection}` → repo skill dirs.
- [ ] `hermes cron create "every 360m" --name anicca-predict --script anicca-predict.sh --no-agent`.
- [ ] `hermes cron create "every 1440m" --name anicca-resurrection --script anicca-resurrection.sh --no-agent`.
- [ ] `hermes cron list` → capture the 2 job IDs.

## Phase 5 — verification (5-step gate per skill) + review + finish
- [ ] re-run all 3 tests fresh → 3× GREEN, capture output.
- [ ] E2E dry-run trace: show a real row in each of `swarm-exec.jsonl`, `predictions.jsonl`,
      `checkpoints/<sha>.json`.
- [ ] codex-review on the spec (GATE 1) and on the impl (GATE 3) → ok:true (≤5 iters).
- [ ] 00-MASTER row ⑦/#337 status annotation (Wave 1 done).
- [ ] commit + `git push -u origin feat/p14-swarm-skills`. Report SHA + 2 cron IDs + sample rows.
