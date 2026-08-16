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
`LM_CONNECTOR_SHARED_ENV_FILE=/Users/operator/.openclaw/.env`, and that file contains zero
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

## C-CORE-05 Luma — BLOCKED_EXTERNAL 2026-08-16

Luma produced 16 free and open events inside the window and zero survived the Calendar gate, so the
question was whether the gate is wrong or Dais is genuinely busy.

A first readback with `gog calendar events list` returned only 10 events, all on 08-16 and 08-17, which
suggested an almost empty calendar and therefore a gate bug. **That reading was wrong and is corrected
here**: it queried the primary calendar only. Rebuilding the inventory exactly as the runtime does
(`inspectGoogleCalendarBusyInventory` over the same 14-day window) returns `calendar_count: 5` and
**103 timed intervals**, including a duplicated daily block from 08:40 to 17:10 JST.

Evening availability, 18:00–22:00 JST, measured from that real inventory:

| date | evening |
|---|---|
| 08-16, 08-17 | free (already past for discovery) |
| 08-18 … 08-24 | busy |
| 08-25 | free |
| 08-26, 08-27 | busy |
| 08-28 | free |
| 08-29 | busy |

The live Luma discovery page `https://luma.com/tokyo?k=p` currently starts at 08-18, so its free and
open events fall on dates whose evenings are genuinely taken. `calendar_free_count: 0` is therefore
**correct behaviour, not a defect**: Connector declined to double-book Dais.

Status `BLOCKED_EXTERNAL`. Counts at the block: Luma observed 39, in-window 33, free and open 16,
Calendar-free 0. Owner: the daily 09:00 native label. Restart condition: a free and open Luma Tokyo
event landing on an evening Dais has open — the next such evenings in this window are 08-25 and 08-28.
Next scheduled check: the next natural 09:00 wake.

## C-CORE-06 Connpass — blocked by a discovery defect, not by the calendar

The same wake recorded Connpass observed 6, in-window 6, free and open 0. Six is not a plausible count
for Tokyo. The runtime discovers from `https://connpass.com/calendar/?ym=<YYYYMM>&prefectures=13`; a
read-only crawl of that exact page exposes **1457 distinct `connpass.com/event/<id>` links** for the
month. So Connector is seeing roughly 0.4% of the listing, and Connpass has never had a fair chance to
produce a candidate.

This is a defect in `connector-connpass-workflow.js`'s binding collection, not an external blocker, and
it must be fixed before `C-CORE-06` can be claimed either way.

Verification, re-run by the parent rather than trusted from the executor: `npm run test:outbound`
33 + 341 pass / 0 fail, `npm run test:runtime-job` 18 pass / 0 fail, `npm run test:runtime-adapters`
125 pass / 0 fail. Residual `routeMinutes` matches in production are only `transport/maps-gog.js`
and `late-notice.js`, which belong to other organs.


## C-CORE-06 Connpass — still open, with a regression I caused and reverted

Sequence of live wakes on the merged code, all one `launchctl kickstart` each, all ending
`circuit_open / peatix_form_navigation_failed`, all leaving applied bundles at 14 (no external write):

| wake | Luma | Connpass | note |
|---|---|---|---|
| `wake-aaa90b20` | 39/33/16/0 | 6/6/6/0/0 | before the date fix |
| `wake-3fc029d9` | 39/33/16/0 | discovery failed 46.0s | date fix live; Connpass now sees real volume and fails |
| `wake-07b2c409` | 39/33/16/0 | failed 23.9s, `provider: connpass`, `safe_reason: provider_discovery_failed` | failure reason now durable |
| `wake-6b15481b` | **failed 30.8s** | failed 25.8s | **regression: the per-row skip change broke Luma** |
| `wake-65f06d99` | 39/33/16/0 | failed 46.3s | after reverting that change; Luma restored |

What the date fix bought: Connpass stopped silently reporting 6 of ~1457 listings. What it exposed:
discovery now fails outright once real volume flows through it.

What I got wrong: I extended the per-row skip treatment to `connector-luma-workflow.js` as well. Luma had
discovered 39 events in three consecutive wakes and failed in the first wake after that change landed, so
the change regressed a working primary provider. I reverted the whole commit rather than debug it live,
merged the revert, and fired another wake to confirm Luma is back to 39/33/16/0. Connpass was already
failing before that change and still fails after it, so the revert cost nothing that worked.

`safe_reason` is still the generic `provider_discovery_failed`, which means the thrown error carries no
code `safeDiscoveryReason` recognises. The per-row normalisation theory is not proven — the executor's
reading found those paths already wrapped in coded stage errors. The next step is to reproduce Connpass
discovery outside a wake against the live page and read the actual error, rather than guess again.

Peatix is unchanged across all five wakes: 10 Calendar-free candidates, three submit attempts, then
`peatix_form_navigation_failed`. It stays `DEFERRED_NON_BLOCKING` per the product contract.

`C-CORE-07` is untouched and cannot be forced honestly: it needs the next natural 09:00 wake or an
equivalent login/reload recovery.
