# macOS Loop Control Plane — TODO 3 read-only CLI

`bin/lm-loop` now exposes read-only `doctor`, `status`, and `watch` commands
backed by the schema-v2 registry. The wrapper works from outside the repository
working directory. No launchd lifecycle mutation exists in this slice.

## Focused contract

- `status` reports launchd state, PID, last exit, installed release, configured
  provider route, event provider/profile, last pass, terminal result, effect
  status, next cadence, and blocker as separate fields.
- PID presence and exit code never synthesize a business PASS or verified
  effect. Missing uniform events remain `last_terminal_result=null` and
  `effect_status=unknown`.
- `watch` re-reads the same live sources every two seconds. Tests prove a new
  event envelope changes terminal/effect fields without changing runtime truth.
- `doctor` validates the registry and reports unmanaged label candidates and
  missing repository entrypoints. It exits nonzero while either exists.

The focused read-only suite has five tests: runtime/effect separation,
doctor gap reporting, no-event truth, watch event updates, and repo-independent
wrapper execution.

## Live readback

| Command | Result |
|---|---|
| `bin/lm-loop doctor` | exit 1; 172 registry entries, 58 unmanaged candidates, 82 missing entrypoints |
| `bin/lm-loop status all` | 172 rows; 42 running, 130 loaded-idle; real time 0.10 s |
| `LM_LOOP_WATCH_ONCE=1 bin/lm-loop watch all` | 172 rows |
| `bin/lm-loop status fundraiser` | loaded-idle, last exit 78, installed legacy release `48c54b52`, no event/effect claim |

All 172 rows currently have `effect_status=unknown` because TODO 6 has not yet
installed the uniform event boundary. This is expected negative evidence, not
a success inference. The doctor gaps prevent `apply` from being introduced as
available before entrypoint migration and unmanaged-label reconciliation.

