---
name: anicca-resurrection
description: RESURRECTION/failover primitive of the colony swarm (spec 18 §3, sutando-style checkpoint restart) — periodically snapshots the live instance's self-model and proves a fresh instance can boot clean from that snapshot. `checkpoint.sh` (cron daily) writes ~/.hermes/state/checkpoints/<id>.json (chmod 600) capturing {model, profile, last_skill_run, last_decision, hermes_config_sha, anicca_oss_sha} best-effort + a ledger row. `restart.sh <checkpoint_id>` reads a checkpoint, builds a fresh ~/.hermes-resurrected-<id>/ mockup HERMES_HOME, copies the essential state (checkpoint + cron/jobs.json + heartbeat.jsonl) into it, runs `hermes status` against that home to PROVE it boots (exit 0 = OK), logs a restart row with an `ok` boolean, then always removes the mockup. Wave 1 = LOCAL restart proof on the same machine (no auto-restart, restart is a deliberate failover act). Wave 2 (gated #327 Phase B) targets a Daytona clean instance + cross-machine heartbeat-gap detection. Checkpoint is triggered by `hermes cron`; restart is invoked deliberately, never on a timer.
metadata:
  spec: anicca-oss/docs/superpowers/specs/2026-06-05-p14-swarm-skills-design.md
  parallel_safe: true
  cadence: daily
  github_issue: 337
---

# anicca-resurrection

RESURRECTION/failover layer of the colony swarm (spec 18 §3). Checkpoint the live instance; prove
a fresh instance boots clean from that checkpoint.

## CLI

```
scripts/checkpoint.sh                  # snapshot the live instance (cron daily)
scripts/restart.sh <checkpoint_id>     # prove a fresh ~/.hermes-resurrected-<id>/ boots
```

## Checkpoint (`checkpoints/<id>.json`, chmod 600)

| key | source (best-effort, falls back) |
|---|---|
| model | `hermes model` last token (`unknown`) |
| profile | `hermes profile current` / `$HERMES_PROFILE` (`genesis`) |
| last_skill_run | newest `"ts"` across `~/.hermes/state/*.jsonl` (`none`) |
| last_decision | last line of `self-manage-decisions.jsonl` (`none`) |
| hermes_config_sha | sha256 of `~/.hermes/cron/jobs.json` (`none`) |
| anicca_oss_sha | `git rev-parse HEAD` of anicca-oss (`none`) |

`checkpoint_id = sha256(model+profile+oss_sha+ts)[:16]`.

## Restart proof (Wave 1 = local)

`restart.sh <id>` builds `~/.hermes-resurrected-<id>/`, copies the checkpoint + cron/jobs.json +
heartbeat.jsonl into it, runs `HERMES_HOME=<mockup> hermes status` (timeout 60), logs
`{op:"restart", checkpoint_id, resurrected_home, status_exit, ok}`, and removes the mockup on
exit. `ok=true` iff `hermes status` exited 0. If `hermes` is absent the genuine failure is logged
(`ok=false`), never a fake success (HARD RULE #-1 / 0.12).

## Ledger (`~/.hermes/state/resurrection.jsonl`)

`{ts, op:"checkpoint"|"restart", checkpoint_id, ...}`.

## Exit codes

`0` ok · `64` usage · `66` checkpoint not found.

## Cron

`hermes cron create "every 1440m" --name anicca-resurrection --script anicca-resurrection.sh
--no-agent`. The wrapper `~/.hermes/scripts/anicca-resurrection.sh` execs `checkpoint.sh`
(daily checkpoint creation ONLY — NO auto-restart in Wave 1).

## Env

`STATE_DIR` (default `~/.hermes/state`), `HERMES_LIVE_HOME` (default `~/.hermes`, read-only source).
`/usr/bin/jq` absolute.

## Test

`bash skills/anicca-resurrection/tests/test_resurrection.sh` — checkpoint writes all 7 keys + a
ledger row; restart boots a fresh HERMES_HOME, logs an `ok` boolean, and cleans the mockup.
4 assertions, isolated STATE_DIR, the live `~/.hermes` is never mutated.

## Wave 2 (NOT implemented)

Daytona clean instance instead of a local mockup; a peer detects the heartbeat gap (`heartbeat.jsonl`
of a sibling) and revives on another host. Gated on #327 Phase B (Daytona region + wallet).
