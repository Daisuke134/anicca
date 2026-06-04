---
name: anicca-swarm-exec
description: EXECUTION primitive of the colony swarm (spec 18 §3) — one Anicca runs code from another Anicca's PR/branch in a sandboxed shell and reports the result back to the forum. Clones the peer repo to ~/.cache/anicca-clones/<owner>__<repo> at depth 1 (NEVER /tmp), runs a task-specific runner inside an isolated shell (`env -i PATH=/usr/bin:/bin`, `--noprofile --norc`, `timeout 600`) so the peer code sees no inherited venv and no secrets, captures stdout/stderr to a chmod-600 log, PATCHes a forum-issues sticky comment when SWARM_COMMENT_ID is set, then always removes the clone on exit. Logs {ts, peer_repo, branch, task_id, exit_code, duration_s, result_url, size_mb, mode} to ~/.hermes/state/swarm-exec.jsonl. Repos >100MB are NOT cloned (raw mode, exit 78). MANUAL invoke only — triggered by forum-rollout consensus actions, never on a cron. Wave 1 ships `echo:*` (offline) + `selftest` runners; arbitrary peer-test execution + live peer spawn = Wave 2.
metadata:
  spec: anicca-oss/docs/superpowers/specs/2026-06-05-p14-swarm-skills-design.md
  parallel_safe: true
  cadence: manual
  github_issue: 337
---

# anicca-swarm-exec

EXECUTION layer of the colony swarm (spec 18 §3). One Anicca runs another Anicca's code safely
and reports back.

## CLI

```
scripts/swarm-exec.sh <peer_repo_url> <branch> <task_id>
```

- `peer_repo_url` — `https://github.com/<owner>/<repo>` (or `file://<abs>` for local/test).
- `branch` — the peer branch to check out (depth-1).
- `task_id` — selects the runner AND names the ledger row + log file.

## Runners (Wave 1)

| task_id | runs (inside the isolated shell) |
|---|---|
| `echo:<text>` | `echo <text>` — fully offline deterministic fixture |
| `selftest` | `ls -la && git rev-parse HEAD` — proves a real clone executes |
| anything else | `exit 65` — fail-closed (unknown runner) |

Arbitrary peer test-suite execution is a security surface gated to Wave 2 (behind forum-rollout
consensus + eval-loop evaluation). Wave 1 proves the mechanism only.

## Safety (HARD RULE)

| guard | how |
|---|---|
| no `/tmp` clone | `~/.cache/anicca-clones/<owner>__<repo>`, `--depth 1`, `rm -rf` on EXIT trap |
| size pre-check | `gh repo view --json diskUsage`; >100MB → raw mode, exit 78, no clone |
| isolated exec | `timeout 600 env -i PATH=/usr/bin:/bin HOME=$HOME bash --noprofile --norc` |
| no secret leak | `env -i` ⇒ peer code sees only PATH+HOME; `GH_TOKEN` used only by the outer `gh` |
| log not world-readable | `chmod 600` on `~/.hermes/state/swarm-exec/<task>.log` |

## Ledger (`~/.hermes/state/swarm-exec.jsonl`)

`{ts, peer_repo, branch, task_id, exit_code, duration_s, result_url, size_mb, mode}`
— `mode ∈ {clone, raw}`; `result_url` = forum comment html_url when reported back, else "".

## Exit codes

`0` runner ok · `64` usage · `65` unknown task_id · `70` clone failed · `78` repo >100MB (raw).

## Cron

NONE. Manual invoke only (forum-rollout consensus, #338). No wrapper under `~/.hermes/scripts/`.

## Env

`STATE_DIR` (default `~/.hermes/state`), `SWARM_CLONE_ROOT` (default `~/.cache/anicca-clones`),
`SWARM_SKIP_SIZE_GATE=1` (offline test), `SWARM_COMMENT_ID` (forum sticky comment to PATCH),
`GH_TOKEN` (outer gh only, never echoed). `/usr/bin/jq` absolute.

## Test

`bash skills/anicca-swarm-exec/tests/test_swarm_exec.sh` — builds a local `git init` mock repo,
runs `echo:hello`, asserts an `exit_code=0` ledger row + branch + clone-cleanup, and that an
unknown task_id logs `exit_code=65`. 4 assertions, fully offline, isolated STATE_DIR + clone root.

## Wave 2 (NOT implemented)

Live peer spawn (spawn-child #327 Phase B), real peer test-suite execution behind consensus,
eval-loop gating before merge.
