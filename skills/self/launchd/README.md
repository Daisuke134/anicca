# skills/self/launchd/

launchd plists for `skills/self/`-level periodic scripts (not tied to one earn loop's own
`launchd/` dir — those live next to their loop, e.g. `skills/earn/clip/launchd/`).

| plist | runs | interval | REQ |
|---|---|---|---|
| `ai.anicca.verify-loops-audit.plist` | `verify-loops-audit.sh` | 6h (21600s) | REQ-LV-042/102/103 |
| `ai.anicca.runtime-loop-healthcheck.plist` | `healthcheck-runtime-loop.sh` (checks all 4 targets: a3cdd4/franklin/pm-earner/founder-proxy) | 5min (300s) | REQ-LV-050/051 |

`ai.anicca.runtime-loop-healthcheck.plist`'s 300s interval satisfies REQ-LV-050's "at or below the
smallest per-target staleness threshold" bar (a3cdd4's 20min threshold is the smallest of the 4;
300s = 5min is well under it, so a DEAD/STALE target is caught on the very next tick rather than
waiting up to a full threshold window).

## Install (orchestrator step, NOT done by this commit)

```bash
cp skills/self/launchd/ai.anicca.runtime-loop-healthcheck.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/ai.anicca.runtime-loop-healthcheck.plist
```

## Verify (REQ-LV-051)

```bash
launchctl list | grep ai.anicca.runtime-loop-healthcheck
```

Should print a line with the job's PID (or `-` between 5-minute ticks, which is normal for a
`StartInterval` job — see `healthcheck-runtime-loop.sh`'s own `hrl_classify()` docstring: PID `-`
between runs is NOT a fault for an interval-type job, only for a `KeepAlive` one).

## Uninstall

```bash
launchctl unload ~/Library/LaunchAgents/ai.anicca.runtime-loop-healthcheck.plist
rm ~/Library/LaunchAgents/ai.anicca.runtime-loop-healthcheck.plist
```
