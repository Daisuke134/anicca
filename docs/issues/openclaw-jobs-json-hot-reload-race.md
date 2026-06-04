# OpenClaw cron: direct edits to `jobs.json` get clobbered by gateway hot-reload race

## Summary

Editing `~/.openclaw/cron/jobs.json` directly while the gateway is
running causes the changes to be silently overwritten on the next
internal save. The only safe edit path is through
`openclaw cron edit <id>`, which routes through the gateway and avoids
the race.

## Repro

1. Gateway is running (`launchctl list ai.openclaw.gateway`).
2. Edit `jobs.json` directly, e.g. flip a job's
   `sessionTarget: "isolated"` → `"main"` and `payload.kind: "agentTurn"` → `"systemEvent"` with a Python script:
   ```bash
   python3 -c "import json; d=json.load(open('~/.openclaw/cron/jobs.json')); ... ; json.dump(d, open('~/.openclaw/cron/jobs.json','w'))"
   ```
3. Verify on disk: change is present.
4. `openclaw cron list` — change is NOT reflected.
5. A few seconds later, re-read `jobs.json` from disk — change has been
   reverted to the gateway's in-memory state.

## Expected

Either:
- Gateway watches `jobs.json` mtime and reloads, OR
- Gateway warns operator that direct edits are unsupported.

## Actual

Gateway holds the canonical state in memory and writes back without
checking on-disk diffs. The reload event we observed restored an older
state hash from `~/.openclaw/logs/config-health.json::lastKnownGood`.

Concrete repro: 2026-06-04 20:21 JST, attempted to flip two crons via
direct json edit + gateway restart. After restart `openclaw cron list`
showed the original `sessionTarget: isolated`. Backup confirms both files
had the same mtime but identical 275913 bytes — gateway wrote back.

## Proposed fix

1. Add a chokidar/fsevents watcher on `~/.openclaw/cron/jobs.json` in
   `dist/cron-CDKfq4vO.js`. On mtime change, re-read + merge with the
   in-memory state (last-write-wins per cron id), then re-arm scheduler.
2. As a defensive backstop, log `cron: detected external edit to
   jobs.json; reloading` so operators can see what happened.
3. Document in the operator guide that direct edits are supported as
   long as the file is rewritten atomically (write to `.tmp` + rename).

## Impact

This race is the reason `anicca-cron-doctor` had to add a
`helpers/cron_edit.py` wrapper that delegates to `openclaw cron edit`
even for batch operations. Direct-edit batch jobs (e.g. our R-4 context-
preserving migration of 48 crons) had to be re-run multiple times in our
session before changes stuck.

Reference: anicca-products spec
`docs/superpowers/specs/2026-06-04-cron-rat-proof-architecture-design.md` §4 risks
+ commit `33db01b8f` (`[cron-doctor] auto-state` had to be backed by gateway-safe edits).
