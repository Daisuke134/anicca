# P14 — swarm-exec + predict + resurrection (#337) — Design Spec

| Field | Value |
|---|---|
| Spec ID | P14 design |
| Status | Implementation-ready (Wave 1) |
| Author | swarm-skills-impl (teammate, team nhoss-phase1) |
| GitHub issue | #337 |
| Depends on | spec 18 §3 (swarm exec/predict/resurrect), spec 16 (Hermes runtime), 00-MASTER row 13 |
| Authoritative for | the 3 intra-colony swarm skills (Wave 1 scope) |
| Worktree | `.worktrees/p14-swarm-skills/` on `feat/p14-swarm-skills` |

> Anicca-as-a-colony needs three primitives that nobody has fully cracked (spec 18 §3):
> **EXECUTION** (one Anicca runs another's code), **PREDICTION** (rehearse a costly action
> before paying for it), **RESURRECTION** (revive a dead instance from a checkpoint). This spec
> delivers the **Wave 1** (local, dry-run, single-machine) version of all three as sibling
> Hermes skills, following the merged `self-manage` / `forum-issues` conventions.

---

## § 0. Scope boundary (Wave 1 ⟺ Wave 2)

| Capability | Wave 1 (THIS spec, implemented) | Wave 2 (documented, NOT implemented) |
|---|---|---|
| swarm-exec | clone peer PR depth-1 → run a task-runner in an isolated shell → log + PATCH a forum sticky comment → cleanup | live peer **spawn** (depends #327 Phase B + Daytona region + wallet>$0) |
| predict | testable-claim validation → record stake (dry-run, no chain) → resolve expired claims via evidence script → **mock** pot distribution | real on-chain stake via `wallet_lib.send_usdc()` (depends #324-wave2 + wallet ≥$5) |
| resurrection | local checkpoint → restart proof against a fresh `~/.hermes-resurrected-<sha>/` mockup, `hermes status` exit 0 → cleanup | Daytona-based clean instance + cross-machine heartbeat-gap detection (depends #327 Phase B) |

Wave 2 is **explicitly out of scope** and gated. No real money moves, no real instance spawns,
no real Daytona calls in this spec. Anti-goal: do not implement Wave 2 "just because the hook is
there" (00-MASTER §11).

---

## § 1. skill: `anicca-swarm-exec`

**One Anicca runs code from another Anicca's PR/branch in a sandboxed shell and reports back.**

### § 1.1 CLI

```
scripts/swarm-exec.sh <peer_repo_url> <branch> <task_id>
```

- `peer_repo_url` — e.g. `https://github.com/Daisuke134/anicca-oss` (https form; owner/repo parsed from it).
- `branch` — the peer branch to check out.
- `task_id` — selects a task-specific runner (see § 1.3) AND names the log/jsonl row.

### § 1.2 Steps (HARD RULE compliant)

```
1. parse owner/repo from peer_repo_url
2. SIZE GATE: `gh repo view <owner>/<repo> --json diskUsage` → KB → MB.
   if size_mb > 100  → DO NOT clone. Set mode="raw" (Wave 1: log size-exceeded, skip run,
                       exit_code=78). [HARD RULE #-1: large repo → gh api 1-file fetch, never clone]
   else              → mode="clone".
3. CLONE (mode=clone only): `git clone --depth 1 --branch <branch> <repo>
                            ~/.cache/anicca-clones/<owner>__<repo>`  (NOT /tmp — HARD RULE)
4. ISOLATED RUN: `timeout 600 env -i PATH=/usr/bin:/bin HOME=$HOME bash --noprofile --norc -c '
       cd <clonedir> && pwd && git log -1 --oneline && bash <runner_for_task_id>
   '`  → no inherited venvs, hard 600s cap.
5. CAPTURE: stdout+stderr → ~/.hermes/state/swarm-exec/<task_id>.log (chmod 600).
6. REPORT BACK: PATCH a forum-issues sticky comment if SWARM_COMMENT_ID is set:
       gh api --method PATCH repos/<owner>/<repo>/issues/comments/<id> -f body="<summary>"
   (no comment id → skip the PATCH, still log locally — manual-invoke path).
7. CLEANUP: rm -rf ~/.cache/anicca-clones/<owner>__<repo>  (always, even on failure — trap).
8. LEDGER: append ~/.hermes/state/swarm-exec.jsonl:
       {ts, peer_repo, branch, task_id, exit_code, duration_s, result_url, size_mb, mode}
```

### § 1.3 Task-runner mapping

`task_id` maps to a runner command via a small case table in `_lib.sh::swarm_runner_for`. Wave 1
ships two:

| task_id pattern | runner | purpose |
|---|---|---|
| `selftest` | `bash skills/<x>/tests/test_*.sh` discovery is too broad — Wave 1 runs `ls -la && git rev-parse HEAD` | smoke proof the clone + isolated shell works |
| `echo:*` | `echo "<rest>"` | deterministic test fixture (offline) |
| anything else | `printf 'no runner for task_id=%s\n' "$task_id"; exit 65` | fail-closed (unknown runner) |

> Rationale for the minimal runner set: Wave 1's job is to prove the **mechanism** (clone →
> isolated exec → report → cleanup), not to run arbitrary peer test suites (that is a security
> surface gated to Wave 2 with consensus). `echo:*` gives a fully-offline deterministic test;
> `selftest` proves a real clone executes.

### § 1.4 Safety

- **No `/tmp` clone** — `~/.cache/anicca-clones/<owner>__<repo>/`, `--depth 1`, removed on EXIT trap.
- **Size pre-check** before clone; >100MB → raw mode (no clone), exit 78.
- **Isolated shell** — `env -i PATH=/usr/bin:/bin` strips inherited venv/PATH; `--noprofile --norc`
  prevents the peer code from sourcing the operator's profile.
- **Time cap** — `timeout 600`.
- **Log chmod 600** — peer stdout may echo anything; not world-readable.
- **No secrets in env** — `env -i` means the runner sees only `PATH` + `HOME`; `GH_TOKEN` is used
  only by the outer `gh` calls, never passed into the isolated shell.

### § 1.5 Cron

**Manual invoke only** (triggered by forum-rollout consensus actions, #338). NO cron registered.
A wrapper `~/.hermes/scripts/swarm-exec.sh` is NOT created in Wave 1 (no scheduled fire).

---

## § 2. skill: `anicca-predict` (MiroFish-style outcome wager)

**Rehearsal/wager layer: record a testable claim + stake, resolve it after the deadline.**

### § 2.1 CLI

```
scripts/predict.sh <claim_text> <stake_usdc_str>     # open a prediction
scripts/resolve.sh                                    # resolve all expired open predictions
```

### § 2.2 `predict.sh` steps

```
1. VALIDATE testability: the claim MUST contain BOTH
     (a) an explicit metric token   — regex: number OR one of {first|paid|contract|views|USDC|$|%|≥|>=}
     (b) an explicit deadline token — regex: one of {within|by|before|in N (h|hours|d|days)|deadline}
   if either is missing → reject (exit 64, log nothing to predictions.jsonl).
2. DEADLINE: parse "within N (h|d)" / "in N (h|d)" → deadline_ts = now + N units.
   if no parseable horizon → default 48h (and require the deadline token from step 1).
3. RECORD ~/.hermes/state/predictions.jsonl:
     {prediction_id=sha256(claim+ts)[:16], ts, claim, stake_usdc, deadline_ts, status:"open"}
   (Wave 1: stake is RECORDED only — no on-chain transfer.)
```

### § 2.3 `resolve.sh` steps

```
For each row with status=="open" AND deadline_ts <= now:
  1. evidence script = ~/.hermes/state/predict-evidence/<prediction_id>.sh  (claim-specific, optional)
  2. if present + executable: run it (timeout 60). Its stdout MUST be exactly "won" or "lost"
        → set status accordingly + resolved_ts.
     else (no script): status="unresolved", resolved_ts=now.
  3. POT (Wave 1 MOCK): append ~/.hermes/state/predict-pot.jsonl
        {ts, prediction_id, status, stake_usdc, payout:"mock", note:"wave1-no-transfer"}
  4. rewrite predictions.jsonl with the updated row (latest-wins via full-file rewrite, atomic temp).
```

> Wave 2 hook (documented, not built): step 3 calls `wallet_lib.send_usdc(winner_addr, pot)` —
> gated on #324-wave2 + wallet ≥$5 + constitution-guard pass. The `wallet_lib` chokepoint is the
> only sanctioned path (it refuses if the keystore derives to the wrong address).

### § 2.4 Schema (predictions.jsonl)

| field | type | notes |
|---|---|---|
| prediction_id | string(16 hex) | sha256(claim + ts)[:16] |
| ts | ISO-8601 Z | open time |
| claim | string | the testable claim |
| stake_usdc | string | recorded only in Wave 1 |
| deadline_ts | int (unix) | now + horizon |
| status | enum | `open` → `won`/`lost`/`unresolved` |
| resolved_ts | int (unix) | set on resolve |

### § 2.5 Cron

`predict` resolve loop: `hermes cron create "every 360m" --name anicca-predict --script
anicca-predict.sh --no-agent`. The wrapper execs `resolve.sh` (NOT `predict.sh` — opening a
prediction is a deliberate act, resolving is the recurring sweep).

---

## § 3. skill: `anicca-resurrection` (sutando-style checkpoint restart)

**Checkpoint the live instance; prove a fresh instance boots clean from that checkpoint.**

### § 3.1 CLI

```
scripts/checkpoint.sh                       # write a checkpoint of the live instance
scripts/restart.sh <checkpoint_id>          # prove a fresh ~/.hermes-resurrected-<sha>/ boots
```

### § 3.2 `checkpoint.sh` steps

```
1. GATHER self-model (best-effort, never fail the whole checkpoint on one missing field):
     model              = `hermes model 2>/dev/null` last model token  (fallback "unknown")
     profile            = `hermes profile current` OR HERMES profile env  (fallback "genesis")
     last_skill_run     = last ts across ~/.hermes/state/*.jsonl heartbeat-ish logs
     last_decision      = last line of ~/.hermes/state/self-manage-decisions.jsonl (or "none")
     hermes_config_sha  = sha256 of ~/.hermes/cron/jobs.json
     anicca_oss_sha     = `git -C <repo> rev-parse HEAD`
2. id = sha256(model+profile+anicca_oss_sha+ts)[:16]
3. WRITE ~/.hermes/state/checkpoints/<id>.json (chmod 600):
     {checkpoint_id, ts, model, profile, last_skill_run, last_decision,
      hermes_config_sha, anicca_oss_sha}
4. LEDGER append ~/.hermes/state/resurrection.jsonl:
     {ts, op:"checkpoint", checkpoint_id, anicca_oss_sha}
```

### § 3.3 `restart.sh <checkpoint_id>` steps (Wave 1 = local restart PROOF)

```
1. READ ~/.hermes/state/checkpoints/<checkpoint_id>.json  (fail 66 if missing).
2. FRESH HOME: mkdir ~/.hermes-resurrected-<checkpoint_id>/ (mockup clean HERMES_HOME).
3. COPY essential state into the mockup:
     - checkpoints/<id>.json          (so the resurrected instance knows its lineage)
     - cron/jobs.json                 (its scheduled work)
     - state/heartbeat.jsonl (if any) (last known liveness)
4. PROVE BOOT: HERMES_HOME=<mockup> hermes status   (timeout 60)
     exit 0 → resurrection OK; non-zero → FAILED (log + non-zero exit).
   [HARD RULE #-1: hermes status IS the available proof tool; if it is not installed we log the
    genuine error verbatim, we do not pretend success.]
5. LEDGER append ~/.hermes/state/resurrection.jsonl:
     {ts, op:"restart", checkpoint_id, resurrected_home, status_exit, ok:(exit==0)}
6. CLEANUP: rm -rf ~/.hermes-resurrected-<checkpoint_id>/  (EXIT trap, always).
```

> Wave 2 hook (documented, not built): step 2-4 target a **Daytona clean sandbox** instead of a
> local mockup dir, and a peer detects the heartbeat gap before calling restart. Gated on #327
> Phase B (Daytona region + wallet).

### § 3.4 Cron

`resurrection` checkpoint loop: `hermes cron create "every 1440m" --name anicca-resurrection
--script anicca-resurrection.sh --no-agent`. The wrapper execs `checkpoint.sh` (daily checkpoint
creation only — NO auto-restart; restart is a deliberate failover act, never on a timer in Wave 1).

---

## § 4. Shared conventions (mirrors self-manage / forum-issues)

| Concern | Decision |
|---|---|
| jq | `/usr/bin/jq` (absolute) |
| state dir | `${STATE_DIR:-$HOME/.hermes/state}` (overridable for tests) |
| temp files | under `$STATE_DIR/.tmp-*.$$`, never `/tmp` |
| ids | `printf '%s' "$x" | /usr/bin/shasum -a 256 | cut -c1-16` |
| DRY_RUN=1 | predict/resurrection skip side effects (no chain even as mock-only when set; resurrection skips the real `hermes status`) |
| secrets | `GH_TOKEN` from env, never echoed; isolated shell gets `env -i` |
| logs | chmod 600 on `swarm-exec/<task>.log` + `checkpoints/<id>.json` |
| repo root resolution | `$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)` walk to skills/ then repo (worktree-safe) |

Each skill ships: `SKILL.md`, `README.md`, `scripts/_lib.sh`, the CLI scripts above, and
`tests/test_<skill>.sh`. Cron wrappers (predict, resurrection) are real files under
`~/.hermes/scripts/` (Hermes v0.12.0 traversal guard requires real files, not symlinks). Symlinks
`~/.hermes/skills/<skill> -> /Users/anicca/anicca-oss/skills/<skill>` register the skills.

---

## § 5. Test plan (TDD — RED before GREEN, all offline)

| skill | test | assertions |
|---|---|---|
| swarm-exec | `tests/test_swarm_exec.sh` | (1) `echo:hello` runner produces a `swarm-exec.jsonl` row with exit_code=0; (2) the row's task_id + branch match; (3) `~/.cache/anicca-clones/...` is empty after (cleanup proven); (4) unknown task_id → exit_code=65 logged. Uses a **local file:// mock repo** built in the test (git init + one commit) so no network. |
| predict | `tests/test_predict.sh` | (1) a non-testable claim ("things will be good") → exit 64, no jsonl row; (2) a testable claim ("earn-lancers gets first paid contract within 2h", "$1") → one `open` row with a 16-hex id; (3) `resolve.sh` with an injected evidence script returning "won" → row flips to `won` + a `predict-pot.jsonl` mock row; (4) `resolve.sh` on an expired claim with no evidence script → `unresolved`. Deadline forced via env `PREDICT_NOW_OVERRIDE`. |
| resurrection | `tests/test_resurrection.sh` | (1) `checkpoint.sh` writes a `checkpoints/<id>.json` with the 7 required keys; (2) a `resurrection.jsonl` `checkpoint` row exists; (3) `restart.sh <id>` creates the mockup, runs `hermes status`, logs a `restart` row with `ok` boolean; (4) the `~/.hermes-resurrected-<id>/` dir is gone after (cleanup proven). All under an isolated `STATE_DIR`; the real heartbeat/cron are never mutated. |

Tests isolate `STATE_DIR` to a temp dir, build their own fixtures, and assert cleanup. The
resurrection test calls real `hermes status` against a **mockup HERMES_HOME** (read-only proof, no
mutation of the live `~/.hermes`).

---

## § 6. Deviations from spec 18 / 00-MASTER (justified)

| Deviation | Why |
|---|---|
| swarm-exec ships only `selftest` + `echo:*` runners, not arbitrary peer test execution | Wave 1 proves the mechanism; running arbitrary peer code is a security surface gated to Wave 2 + consensus (spec 18 §3 EXECUTION is the colony-parallelism target, not an open RCE). |
| predict resolution is single-instance (no peer comparison) | 00-MASTER #337 says "an Anicca peer compares actual outcome" — Wave 1 has no live peer (genesis ×1), so resolution uses a local claim-specific evidence script. Peer comparison = Wave 2 (needs ≥2 live instances, #328 colony). |
| resurrection restarts on the SAME machine into a fresh `~/.hermes` mockup | spec 18 §3 RESURRECTION targets cross-machine failover; that needs a 2nd host (Daytona, #327 Phase B). Wave 1 = local restart proof per the task description. |
| no real money / no real spawn / no real Daytona | spec 18 + 00-MASTER row 13 + task: Wave 2 gated on #324-wave2, #327 Phase B, wallet ≥$5. |

---

## § 7. Wave 2 (DOCUMENTED, NOT IMPLEMENTED)

- **swarm-exec Wave 2**: live peer spawn (spawn-child #327), real peer test-suite execution behind
  forum-rollout consensus, result evaluated by `eval-loop` before merge.
- **predict Wave 2**: real stake via `wallet_lib.send_usdc()`, peer-comparison resolution, on-chain
  pot distribution. Gated #324-wave2 + wallet ≥$5 + constitution-guard.
- **resurrection Wave 2**: Daytona clean instance, cross-machine heartbeat-gap detection (peer polls
  `~/.hermes/state/heartbeat.jsonl` of a sibling, revives on gap). Gated #327 Phase B.
