# Connector core recovery — execution notes

Branch `fix/connector-core-recovery`, base `origin/main` (contains `f32eee4d2`).
SSOT: spec `0.2.1 Active remaining TODO SSOT`. One item at a time, evidence before status.

## C-CORE-01 single-owner cleanup — DONE 2026-08-16

Target resolution (read-only, before any change):

| label | ProgramArguments | verdict |
|---|---|---|
| `...-connector-native-healthcheck` | `.worktrees/connector-native-completion/skills/connector/healthcheck.sh` | worktree absent (`ls` → No such file or directory) → `EX_CONFIG` 78 |
| `...-connector-healer-shadow` | same deleted worktree, `healer-shadow.sh` | `EX_CONFIG` 78 |
| `...-connector-host-bridge` | `apps/life-manager/scripts/connector-host-bridge-boot.sh` | retired; running PID 805 on `127.0.0.1:18793` |
| `...-connector-native` | `skills/connector/run.sh` | official entrypoint, keep loaded |

Dependency check before unload: `grep -rn "18793\|host-bridge\|hostBridge"` over `skills/connector/`,
`connector-native-runtime.js`, `connector-minimal-production.js` returned 0 hits. The only remaining
`18793` consumer is `deploy/local/compose.connector.yaml` (container path, not the native local path).

Action: `launchctl bootout gui/$UID/<label>` for the three labels above. No plist deleted, no state touched,
no browser or OS service stopped.

Readback after the change:

- `launchctl list | grep -i connector` → `-  0  ai.anicca.life-manager-connector-native` only. Zero `EX_CONFIG` 78 rows.
- `18793` listener → none. PID 805 gone.
- `~/Library/LaunchAgents` still holds all 7 connector plist files (4 active-named + 3 previously retired/disabled).
- `~/.local/state/life-manager/connector-native` still holds 27 entries.
- Listening ports in the `9xxx` range: `9223`, `9324`, `9326`, `9327`. Gig-owned `9223` untouched;
  Connector `9222` still has no listener, which is exactly `C-CORE-02`.

Not done here: `9222` owner restoration, travel gate removal, any wake, any external write.

## C-CORE-02 browser readiness — DONE 2026-08-16

Root cause found in the watchdog log `~/gig/dd-keepalive-healthcheck.log`:

```text
2026-08-02 19:18:14 daily-driver RELAUNCHED OK (:9222 reachable)
2026-08-16 12:51:20 daily-driver DOWN (:9222 unreachable) -> relaunching
2026-08-16 12:51:29 daily-driver RELAUNCH FAILED (:9222 still unreachable)
```

The browser died and its own watchdog failed to bring it back, so every Connector wake after
12:51 would fail-closed on the browser dependency. `~/gig/dd-keepalive.log` ends with
`nohup: can't detach from console: Inappropriate ioctl for device`, and the launchd stdout/stderr
logs for the watchdog are empty, so the relaunch failure is observed but its cause is not yet proven.

Action: relaunched the documented owner `~/gig/dd-keepalive.py` (CloakBrowser
`launch_persistent_context` on `~/.cloak/profiles/daily-driver`). Nothing was killed; the existing
profile was reused.

Readback through the sanctioned entry point `~/.config/ai/bin/browser-guard.sh`:

- `interactive:dais` — `9222` reachable, browser UUID `c97821e3-2ccc-43a3-8998-7ad39d21726f`.
- `coconala:kosuke` — `9223` reachable, UUID `75a81661-06b7-413a-ab09-22b20bc155ba`, untouched.
- `collisions: {}` — the two identities are different browsers, which is the exact failure the guard exists to catch.
- Page inventory under an acquired lease: 4 targets (1 page, 1 `about:blank`, 2 service workers), `Chrome/145.0.7632.109`.
- Lease released cleanly after the readback.

Measured gaps recorded, not fixed here:

1. Connector pins `CONNECTOR_CDP_ENDPOINT = "http://127.0.0.1:9222"` in
   `apps/life-manager/lib/connector-browser-target-controller.js` and rejects any other endpoint,
   and it never takes a `browser-guard` lease. So the "dedicated Connector browser" is in fact the
   shared `interactive:dais` daily-driver, and a human session can drive the same browser during a wake.
2. The daily-driver watchdog can report `RELAUNCH FAILED` without leaving a diagnosable log.

Both are real risks for `C-CORE-04`/`C-CORE-07` reliability but are outside the seven core items;
they are recorded here so they are not lost.

Environment check while resolving the dependency chain: the native plist supplies
`LM_CONNECTOR_SHARED_ENV_FILE=/Users/anicca/.openclaw/.env`, and that file contains zero
`LM_CONNECTOR_*` keys. This is not a blocker because `skills/connector/native-pass.js` defaults
`tenantId` to `dais-local`, `calendarId` to `primary`, and resolves the Telegram target from the
OpenClaw config file when the env key is absent. The OpenClaw gateway is up (PID 768 listening on `18789`),
so the earlier `gateway timeout after 10000ms` in `connector-native.err.log` is a historical failure
from the now-unloaded deleted-worktree owner, not a current one.

## Container rail removal — 2026-08-16

Dais confirmed Docker is unused; Connector runs natively. Removed `deploy/local/compose.connector.yaml`,
`connector-host-bridge-server.js`, `connector-host-bridge-boot.sh`, `deploy-connector-runtime.sh`,
`install-connector-host-bridge-launchd.sh`, their tests, and the host bridge launchd template.
`outbound-guardian.test.js` now asserts the rail stays gone instead of asserting the compose file exists.
The installed plists were left in place. `npm run test:outbound` passed after the removal.

## C-CORE-03 remove travel dependency — DONE 2026-08-16

The spec named `connector-native-runtime.js` as the file to fix. Measurement contradicted that premise
and changed the shape of the work:

| claim | measurement |
|---|---|
| `connector-native-runtime.js` is the live candidate gate | it is required by nothing in production, only by its own test |
| the live wake gates on travel | `connector-minimal-production.js`, `connector-minimal-runner.js`, `connector-minimal-operations.js` and `connector-minimal-evidence.js` contain zero travel references |
| travel is confined to that one file | the real travel gate was `calendar-candidate-gate.js`, live through `connector-events-pack.js`, `connector-coverage-assembler.js` and `event-spend-policy.js` |
| `connector-native-write-pipeline.js` delivers the Telegram booking message | it also has zero production requirers; the live message is built in `connector-minimal-evidence.js` |

Work done:

1. `calendar-candidate-gate.js` no longer accepts, forwards or calls `routeMinutes`/`homeLocation`.
   A candidate is eligible when its own interval does not overlap a timed busy interval. The
   `route_unavailable` recovery branch is gone because no route call can fail any more.
2. Deleted the dead travel-gated modules `connector-native-runtime.js` and `connector-route-minutes.js`
   with their tests, and removed the dead travel pass-throughs in `connector-events-pack.js`,
   `connector-open-date-planner.js`, `connector-coverage-runtime-services.js`,
   `connector-coverage-refresh-service.js` and the `route.minutes` capability of `connector-host-bridge.js`.
3. Added `connector-no-travel.test.js`, a source-level regression that fails if travel plumbing returns
   to the live modules, the gate, or the Calendar sync path.
4. Aligned the user-facing text with `0.2.6`: the coverage brief derives every string from the actual
   `coverage.horizon_days` instead of hard-failing on `21`, and its travel claim is replaced with what
   Connector actually verified. The booking caption no longer asserts a Luma confirmation mail for
   every provider; it requires a receipt reference it can prove.
5. Fixed the live booking message in `connector-minimal-evidence.js`. It previously emitted a raw UTC
   timestamp and a bare Calendar event ID, so Dais could not open either link. It now carries the event
   name, the start time in the run timezone, venue, provider, status, the event URL and the Calendar
   `htmlLink`. `connector-minimal-production.js` passes its already-enforced production timezone into the chain.

Remaining honest gaps:

- The booking message still has no selection reason, because no reason value exists anywhere in the
  evidence chain's scope. It must come from the discovery/ranking layer, which is not wired into it.
- `rolling-event-coverage.js` still hard-codes a 21-day horizon and its store rejects any other value,
  so the coverage brief will say 21 until that producer is changed. The delivered text now follows the
  data instead of contradicting it, which is the part that could mislead Dais.

## C-CORE-04 supervised primary-first wake — DONE 2026-08-16

PR #2819 merged as `364ea0b72`; the shared `main` checkout was fast-forwarded so the launchd label
runs the merged code. Baseline before firing: label loaded and not running, `runs = 0`, no Connector
process, no lock, 14 applied bundles, `interactive:dais` and `coconala:kosuke` both reachable with no lease holder.

One `launchctl kickstart` at 22:17:20 JST. Result: `runs = 1`, `last exit code = 1`, state back to not running.

Provider order proven by the audit timestamps, primary first:

| provider | recorded_at | observed | normalized | window | free+open | calendar-free |
|---|---|---:|---:|---:|---:|---:|
| Luma | 13:18:11Z | 39 | 39 | 33 | 16 | 0 |
| Connpass | 13:18:15Z | 6 | 6 | 6 | 0 | 0 |
| Peatix | 13:19:21Z | 100 | 100 | 86 | 57 | 10 |

Peatix had candidates, attempted `provider_direct` then `browser_harness`, and the wake closed as
`wake-aaa90b2080ed3b99a1982151` / `circuit_open` / `peatix_form_navigation_failed` with
`consecutive_failure_count 3`. That is the defined terminal for repeated failure, and the exit contract
held: non-zero exit plus a durable next action.

Cleanup and honesty checks after the wake:

- applied bundles still 14 — no external write, no duplicate application.
- wake report delivered to Telegram with positive provider id `21274`.
- no Connector process and no lock left behind; `evidence/tab-owner.json` and `evidence/target-leases.json`
  were released.
- no new stderr, so the non-zero exit is the contract path and not a crash.

## C-CORE-05 blocker investigation

Luma produced 16 free and open events inside the window and zero survived the Calendar gate, so the
question is whether the gate is wrong or Dais is genuinely busy. Read-only Calendar readback for the
14-day window returned 10 events, all on 2026-08-16 and 2026-08-17, and zero all-day events, so the
calendar is nearly empty from 08-18 onward. The live predicate
(`defaultCalendarFree` in `connector-luma-workflow.js`) blocks only on a timed overlap, and Peatix
passed 10 candidates through the same busy inventory in the same wake, so the inventory is not
over-blocking. The remaining explanation to prove is whether the 16 Luma events are themselves clustered
on 08-16 and 08-17. Until that is measured, `C-CORE-05` is not claimed either way.

Verification, re-run by the parent rather than trusted from the executor: `npm run test:outbound`
33 + 341 pass / 0 fail, `npm run test:runtime-job` 18 pass / 0 fail, `npm run test:runtime-adapters`
125 pass / 0 fail. Residual `routeMinutes` matches in production are only `transport/maps-gog.js`
and `late-notice.js`, which belong to other organs.

