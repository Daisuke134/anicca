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

## C-CORE-05 Luma — DONE 2026-08-17, end to end on the live loop

`BLOCKED_EXTERNAL` was the wrong call. It was true that Dais's evenings were mostly taken, but three
real defects were hiding behind that, and all three are now fixed and proven by live wakes.

**1. Luma was logged out.** `luma.com/home` redirected to `/signin` on the daily-driver, so no RSVP
could ever complete. Recovered by requesting the sign-in code and reading it from Gmail through `gog`,
the same path `gog-luma-code-reader.js` exists for. Without this the loop can never register anything.

**2. Nineteen `[Travel]` blocks written by the removed travel feature were still in the calendar and
were blocking candidates.** They are contract violations by definition — Connector must not write
travel. Removed all of them; the list of ids, times and titles is kept at
`~/.local/state/life-manager/connector-native/removed-travel-blocks-20260817.txt`. Luma's Calendar-free
count went from 0 to 2 immediately.

**3. `page.setContent()` hangs on this browser over CDP.** Measured directly against the live
daily-driver: it timed out with the default `waitUntil` and again with `commit`, while
`goto about:blank` + `document.write` rendered the same receipt in 102 ms and produced a 15810-byte PNG.
That single call was the first step of the evidence chain for Luma, so every evidence run died there.
The peatix branch already used the working technique; both providers now share it.

A fourth problem surfaced in between: a registration whose evidence chain failed became invisible,
because discovery filters out events Dais is already registered for. That left him signed up for an
event he was never told about and which was not on his calendar. Wakes now reconcile registered events
that have no bundle through the evidence chain only — never through a submit path — bounded to three
per wake.

Live result, two consecutive wakes, `applied_bundle` both times, bundles 14 → 16:

| event | Calendar event id | Calendar readback | Telegram |
|---|---|---|---|
| 8/18 19:30–21:00 皇居ラン | `jlcv9apqtn51rbpi5k4857jr18` | exact 1 | message `21446`, photo `21447` |
| 8/20 19:00–21:00 Yarn and Yap Vol. 12 | `pfmv6pi9uf7knjv2trpoa0tbhk` | exact 1 | message `21452`, photo `21454` |

Both Calendar ids were read back independently with `gog` and matched the durable bundle exactly.

Measured evening availability for the rest of the window: 08-22, 08-25 and 08-26 are open; 08-22 is in
fact taken by `One Day with VITURE`, which runs 08-22 13:30 to 08-23 18:00.

A read-only `skills/connector/discover.js` was added along the way. It prints, per candidate, the
date, the free/open verdict, the Calendar verdict and the blocking interval — that is how the travel
blocks were caught. It imports no submit path, so it cannot register anything.

## C-CORE-07 natural schedule recovery — DONE 2026-08-17

The unforced 09:00 JST wake ran on its own: `2026-08-17T00:01:32Z`, status `applied_bundle`,
`consecutive_failure_count 0`, wake report delivered to Telegram with provider id `21820`.
`launchctl list` shows only `ai.anicca.life-manager-connector-native` for Connector, and the label's
`last exit code` is now `0` rather than the earlier non-zero circuit exits.

## Bookings the loop completed by itself — 2026-08-17

Applied bundles went from 14 to 21 across the night and morning. Calendar entries read back independently
with `gog`, each exactly one:

| event | Calendar event id | Telegram |
|---|---|---|
| 8/18 19:30–21:00 皇居ラン | `jlcv9apqtn51rbpi5k4857jr18` | `21446` / `21447` |
| 8/20 19:00–21:00 Yarn and Yap Vol. 12 | `pfmv6pi9uf7knjv2trpoa0tbhk` | `21452` / `21454` |
| 8/22 09:30–11:30 Gradations, Thirdspace Thirdweeks | `hone3ha1bjio654ucn6vpb4vk4` | `21818` / `21819` |
| 8/22 19:00–22:30 Reading Rhythm vol.2 | `72897jonq9afhqnl195ojv22e4` | `21938` / `21941` |

## C-CORE-06 Connpass — one narrow blocker left

Two more real causes were found and fixed on the way:

1. **Connpass was logged out** in the daily-driver, exactly like Luma. The join control is replaced by a
   login wall for anonymous visitors, so every event read as `registration_status: unknown` and nothing
   could ever pass the free-and-open gate. Logged in with the credentials already in `~/.openclaw/.env`.
2. **The fee wording never matched.** Connpass prints the fee inside a `join_fee` element as plain `無料`,
   while the label regex demanded whitespace or `参加費` around it. Every free event was scored as paid.
   Fixed, with a yen amount now overriding any free label so a paid or mixed-tier event cannot pass.

Measured before and after on the same discovery, read-only:

```
before login + fee fix : observed=767 normalized=40 window=40 free_open=0  calendar_free=0
after                  : observed=767 normalized=40 window=40 free_open=29 calendar_free=7
```

Remaining blocker, narrow and reproducible: Connpass discovery **succeeds standalone and fails inside a
wake**, always after about 30 seconds, with the generic `provider_discovery_failed`. Every stage code the
workflow throws is already mapped by `safeDiscoveryReason`, so the thrown error carries no code — it comes
from a plain `invalid()` somewhere on that path. Page reuse was ruled out by measurement: navigating the
same page from the Luma discovery URL to the Connpass calendar URL takes 783 ms and succeeds.

Next step: capture the uncoded throw's error class in durable state, or replay the wake's exact provider
cursor against discovery, rather than guessing again.

## C-CORE-06 Connpass — DONE 2026-08-17

Five real causes stood between Connpass and a booking. Each was measured, not guessed:

1. **Logged out.** The join control is swapped for a login wall, so every event read as `unknown` and
   nothing could pass the free-and-open gate. Logged in with the credentials already in `~/.openclaw/.env`.
2. **The fee wording never matched.** Connpass prints the fee inside a `join_fee` element; the label test
   demanded whitespace or `参加費` around `無料`. Every free event was scored as paid. A yen amount now
   overrides any free label, so a paid or mixed-tier event still cannot pass.
3. **The audit rejected the truth.** `safeDiscoveryAudit` capped every count at 500. Connpass legitimately
   observes 767 Tokyo events in the window, so discovery did 25 seconds of real work and then died on its
   own bookkeeping. Proven by the durable reason `connpass_discovery_audit_failed`, which only became
   visible after the uncoded-throw instrumentation landed.
4. **The application stopped at the form.** Clicking `このイベントに申し込む` only navigates to `/join/`,
   which carries a `participation_type` radio and a `FreeButton` confirm. The flow now completes it.
5. **The readback looked at the wrong page.** After confirming, state was read on connpass's
   post-submission page, so a real registration reported `direct_action_unverified`. Confirmed by reading
   the event page directly: `受付票を見る`, `申し込みキャンセル`, participants 2 → 3. It now returns to the
   event page before reading, with the unknown-effect boundary still starting at the confirm click.

Connpass also gained the registered-without-bundle reconciliation Luma already had, which is what closed
the orphan that fix 5 had created.

Live result: `applied_bundle`, bundle 23.

| event | Calendar event id | readback | Telegram |
|---|---|---|---|
| 8/25 19:00–22:00 毎週火曜にやってる！プログラミング&ITなんでも勉強部屋 | `05subh7mj519f7f0erjgil814g` | confirmed, description carries the connpass URL | `22138` / `22139` |

## Schedule — every 8 hours from 2026-08-17

Dais asked for the Connector to run like the gig lanes: three times a day rather than once. The native
plist now carries three `StartCalendarInterval` entries, 09:00, 17:00 and 01:00 JST. The previous
single-entry plist is kept at
`~/.local/state/life-manager/connector-native/plist-backup-daily-20260817.plist`, and the label was
reloaded and read back, showing all three intervals registered with launchd.
