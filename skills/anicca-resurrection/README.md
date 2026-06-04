# anicca-resurrection (#337 P14 — Wave 1)

RESURRECTION/failover primitive of the colony swarm (sutando-style): checkpoint the live instance,
prove a fresh instance boots clean from it. Full design:
`docs/superpowers/specs/2026-06-05-p14-swarm-skills-design.md` §3.

```
scripts/checkpoint.sh                  # snapshot self-model → checkpoints/<id>.json (cron daily)
scripts/restart.sh <checkpoint_id>     # prove a fresh ~/.hermes-resurrected-<id>/ boots
```

`restart.sh` builds a fresh mockup HERMES_HOME, copies the checkpoint + cron + heartbeat in, runs
`hermes status` against it (exit 0 = `ok=true`), logs the result, and removes the mockup on exit.
If `hermes` is missing the genuine failure is logged — never a fake success.

Wave 1 = local restart proof (same machine). Wave 2 = Daytona clean instance + cross-machine
heartbeat-gap detection (gated #327 Phase B). See `SKILL.md`.

Test: `bash skills/anicca-resurrection/tests/test_resurrection.sh` (local, 4 assertions, isolated
STATE_DIR — the live `~/.hermes` is never mutated).
