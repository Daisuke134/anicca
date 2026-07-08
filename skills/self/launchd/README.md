# skills/self/launchd/

launchd plists for `skills/self/`-level periodic scripts (not tied to one earn loop's own
`launchd/` dir — those live next to their loop, e.g. `skills/earn/clip/launchd/`).

| plist | runs | schedule | REQ |
|---|---|---|---|
| `ai.anicca.verify-loops-audit.plist` | `verify-loops-audit.sh` | every 6h (`StartInterval` 21600s) | REQ-LV-042/103 |
| `ai.anicca.cadence-deadline-check.plist` | `cadence-deadline-check.sh` | daily at 21:05 JST (`StartCalendarInterval` Hour=21 Minute=5) | REQ-LV-102 |
| `ai.anicca.runtime-loop-healthcheck.plist` | `healthcheck-runtime-loop.sh` (checks all 4 targets: a3cdd4/franklin/pm-earner/founder-proxy) | every 5min (`StartInterval` 300s) | REQ-LV-050/051 |

`ai.anicca.cadence-deadline-check.plist` uses `StartCalendarInterval` (fixed wall-clock time),
NOT `StartInterval` (rolling relative time) — REQ-LV-102's "escalate if today's Cadence Contract
is unmet by 21:00 JST" MUST fire at a guaranteed, fixed time. Piggy-backing this check on
`verify-loops-audit.sh`'s own 6h rolling `StartInterval` was tried first and found broken
(iteration-3 adversary review, F-ITER3-1): depending on the launchd-load-time offset, the 6h
schedule's four daily ticks can land entirely outside the `[21:00,24:00)` window for roughly half
of all possible offsets — meaning the escalation would go permanently, silently unevaluated on
some days. `cadence-deadline-check.sh` is copy+tweaked from the existing
`ai.anicca.cfo-daily.plist`/`ai.anicca.agentmail-nudge.plist` `StartCalendarInterval` pattern.
`verify-loops-audit.sh` still calls `cadence-deadline-check.sh` once per its own 6h pass too, as a
harmless redundant safety net (the per-loop-per-day marker file makes a second call on the same
JST day a no-op).

`ai.anicca.runtime-loop-healthcheck.plist`'s 300s interval satisfies REQ-LV-050's "at or below the
smallest per-target staleness threshold" bar (a3cdd4's 20min threshold is the smallest of the 4;
300s = 5min is well under it, so a DEAD/STALE target is caught on the very next tick rather than
waiting up to a full threshold window).

## Install (orchestrator step, run after merge)

```bash
cp skills/self/launchd/ai.anicca.cadence-deadline-check.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/ai.anicca.cadence-deadline-check.plist

cp skills/self/launchd/ai.anicca.runtime-loop-healthcheck.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/ai.anicca.runtime-loop-healthcheck.plist
```

## Verify (REQ-LV-051)

```bash
launchctl list | grep ai.anicca.cadence-deadline-check
launchctl list | grep ai.anicca.runtime-loop-healthcheck
```

Should each print a line with the job's PID (or `-` between ticks/before the next scheduled fire,
which is normal for both `StartInterval` and `StartCalendarInterval` jobs — see
`healthcheck-runtime-loop.sh`'s own `hrl_classify()` docstring: PID `-` between runs is NOT a fault
for an interval-type job, only for a `KeepAlive` one).

## Uninstall

```bash
launchctl unload ~/Library/LaunchAgents/ai.anicca.cadence-deadline-check.plist
rm ~/Library/LaunchAgents/ai.anicca.cadence-deadline-check.plist

launchctl unload ~/Library/LaunchAgents/ai.anicca.runtime-loop-healthcheck.plist
rm ~/Library/LaunchAgents/ai.anicca.runtime-loop-healthcheck.plist
```
