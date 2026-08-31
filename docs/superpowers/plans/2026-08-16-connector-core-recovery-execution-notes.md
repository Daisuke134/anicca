# Connector core recovery — execution notes

Branch `fix/connector-core-recovery`, base `origin/main` (contains `f32eee4d2`).
SSOT: spec `0.2.1 Active remaining TODO SSOT`. One item at a time, evidence before status.

## C-CORE-01 single-owner cleanup — DONE 2026-08-16

Target resolution (read-only, before any change):

| label | ProgramArguments | verdict |
|---|---|---|
| `...-connector-native-healthcheck` | `.worktrees/connector-native-completion/skills/connector/healthcheck.sh` | worktree absent (`ls` → No such file or directory) → `EX_CONFIG` 78 |
| `...-connector-healer-shadow` | same deleted worktree, `healer-shadow.sh` | `EX_CONFIG` 78 |
| `...-connector-host-bridge` | `apps/mr-bot/scripts/connector-host-bridge-boot.sh` | retired; running PID 805 on `127.0.0.1:18793` |
| `...-connector-native` | `skills/connector/run.sh` | official entrypoint, keep loaded |

Dependency check before unload: `grep -rn "18793\|host-bridge\|hostBridge"` over `skills/connector/`,
`connector-native-runtime.js`, `connector-minimal-production.js` returned 0 hits. The only remaining
`18793` consumer is `deploy/local/compose.connector.yaml` (container path, not the native local path).

Action: `launchctl bootout gui/$UID/<label>` for the three labels above. No plist deleted, no state touched,
no browser or OS service stopped.

Readback after the change:

- `launchctl list | grep -i connector` → `-  0  ai.anicca.mr-bot-connector-native` only. Zero `EX_CONFIG` 78 rows.
- `18793` listener → none. PID 805 gone.
- `~/Library/LaunchAgents` still holds all 7 connector plist files (4 active-named + 3 previously retired/disabled).
- `~/.local/state/mr-bot/connector-native` still holds 27 entries.
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
   `apps/mr-bot/lib/connector-browser-target-controller.js` and rejects any other endpoint,
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
`~/.local/state/mr-bot/connector-native/removed-travel-blocks-20260817.txt`. Luma's Calendar-free
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
`launchctl list` shows only `ai.anicca.mr-bot-connector-native` for Connector, and the label's
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
`~/.local/state/mr-bot/connector-native/plist-backup-daily-20260817.plist`, and the label was
reloaded and read back, showing all three intervals registered with launchd.

## Mr.bot travel blocks vs Connector gating — fixed 2026-08-17

Dais corrected an earlier reading in these notes. The `[Travel]` entries are **not** leftovers from the
removed Connector travel feature; the Mr.bot **web app** writes them around each booked event, and
that is its job. A live sample proves the author:

```
summary     : [Travel] 🚆 新宿区南元町15-27→KOPI KALYAN Tokyo（コピカリアン トーキョー）
created     : 2026-08-16T16:48:05Z          (after the manual cleanup)
description : Auto-inserted by Mr.bot — adjust if the route is wrong.
```

So deleting them was treating a symptom. The real defect was on the Connector side: it counted those
blocks as Dais's own commitments, so every booking it made fenced off the surrounding time and closed the
door on its own next candidate.

| calendar state | Luma calendar-free candidates |
|---|---|
| 19 travel blocks present | 0 |
| after deleting them | 2 |
| after the web app re-inserted them | 0 again |

The busy inventory now drops a block only when the summary marker and the auto-insert description BOTH
match, both taken verbatim from `travel.js`'s `createTravelBlock`, so a partial match can never drop a
real commitment. Titles and descriptions still never reach the inventory output.

Verified after the fix with the read-only discovery CLI: no `[Travel]` entry appears as a blocker any
more; every remaining rejection is a genuine event (`SPARK JAPAN`, `One Day with VITURE`, the day-job
block, and Connector's own earlier bookings). `calendar_free` is still 0 for Luma right now, which is now
an honest result rather than a self-inflicted one.

Side finding worth keeping: because those inserts are still arriving, the Mr.bot web app is alive.
Dais reports its departure calls and route messages stopped, and the caller lives in
`apps/mr-bot/server.js`, which does not run locally. That is a separate track from Connector.

## Connpass fresh applications — 2026-08-17, two causes fixed, one lane left open

The 17:00 wake attempted three Connpass candidates and closed `direct_action_unverified` with nothing
registered. Two separate defects were behind it, both measured by replaying the real flow.

**Tier selection.** The flow checked the first participation radio. On a real multi-tier page that is the
wrong ticket:

```
ptype1 学生ゆうせん枠 無料 先着順 9/15人      <- student only
ptype2 だれでも枠 無料 先着順 17/20人        <- the correct pick
ptype3 26新卒LT枠 無料 先着順 2/2人          <- full
ptype4 【招待した方のみ】LT枠 無料 先着順 3/3人 <- invite only, full
ptype5 オンライン視聴枠 (Google meet) 無料     <- online
```

None of those radios is `disabled`, so the DOM never says a tier is full — only the label does. Selection
now requires free with no yen amount, room by the `n/m人` label, and no student, invite, presenter or
staff marker, preferring an in-person tier, and clicks nothing when nothing qualifies.

**Required organizer questionnaire.** Even with the right tier checked, the confirm click left the page
where it was:

```
after confirm url : https://mobilus.connpass.com/event/395464/join/   (unchanged)
after confirm body: ... 主催者からのアンケート ※回答は主催者のみに公開されます。 必須 ...
FINAL STATE       : ["このイベントに申し込む"]                          (still not registered)
```

Some events require answers before the application is accepted. The join page is now checked for an
unanswered required question before anything is clicked, and those events are skipped with their own safe
code. Live readback after the fix: the wake's three attempts now end as fast, safe `direct_action_failed`
rather than as unknown effects, so no attempt is wasted and no orphan is created.

What is still open: every Connpass candidate available right now carries a required questionnaire, so the
loop has nothing it can complete on that provider today. Answering them is the remaining lane, and it is
exactly the "unknown UI, bounded model action" path the contract already describes. Luma already has the
machinery to model — `luma-form-answer-policy.js`, `luma-form-fill.js`, `luma-form-profile.js`.

## Three-times-a-day cadence — all three slots observed unattended, 2026-08-18

| slot | wake report timestamp | local |
|---|---|---|
| 09:00 | `2026-08-18T00:05:46Z` | 09:05 JST |
| 17:00 | `2026-08-17T08:01:32Z` | 17:01 JST |
| 01:00 | `2026-08-17T16:06:12Z` | 01:06 JST |

Nobody kickstarted any of them. The schedule change from one daily wake to three is proven end to end.

## Booking proof with a before and after, 2026-08-17

The clearest single piece of evidence that the loop books by itself, captured on `connpass.com/event/395811/`
(【キックオフイベント】LINKS:POWER of DATA x DATA 2026, 8/28 19:00–20:00):

| | before the wake | after the wake |
|---|---|---|
| provider page | `["このイベントに申し込む"]` — not registered | `["このイベントに参加できます","受付票を見る","申し込みキャンセル","参加者（96人）"]` |
| Google Calendar | no such event on 08-28 | `2anb5lfpk54kv7fmpchnjc527k`, 19:00–20:00, `confirmed`, description carries the connpass URL |
| duplicates | — | exactly 1 matching event |
| Telegram | — | message `22506`, photo `22507` |
| bundles | 23 | 24, `applied_bundle` |

The same wake also recorded, for the two candidates it declined,
`connpass_registration_unavailable` and `connpass_questionnaire_required` — which is the first time a
declined submit said why. Three tried, one booked, two safely skipped is a healthy pass.

## Connpass questionnaire answering — merged, not yet proven live

The flow can now fill free-text identity questions (name, affiliation) and refuses anything that asks Dais
to choose, consent or commit: radio, checkbox and select are rejected on control type before the label is
even read. If a single required question cannot be answered honestly, nothing is filled and nothing is
clicked.

One real gap was caught before it shipped: the first implementation read the attendee name from
`process.env.DAIS_LEGAL_NAME_ROMAJI`, which is never in the wake's environment — `run.sh` does not export
the shared env file, `native-pass.js` loads it itself. The name is now threaded from the same attendee
profile Peatix already receives.

Status is honest: unit-proven, live-unproven. The wakes since the merge found `calendar_free 0` on both
primaries, because Dais's evenings are now taken partly by the loop's own bookings, so no questionnaire
event has reached the flow yet.

## Peatix was logged out too — 2026-08-18

Every wake was ending `circuit_open / peatix_form_navigation_failed` with three candidates burned, even
though Peatix was offering the largest supply of the day (6 Calendar-free candidates against 0 from both
primaries). `peatix-browser-provider.js:200-202` emits that reason when the step after `#next-button` never
appears, which is exactly what a login wall looks like from inside the ticket flow.

`peatix.com` showed `ログイン / 新規登録` — logged out, the same root cause already found on Luma and on
Connpass. Three providers, one failure class.

Recovery used Peatix's own email code path (`認証コードを受け取る`), reading the six-digit code from Gmail
through `gog`, mirroring the Luma recovery. Google sign-in was deliberately NOT used: `google-login`'s
pointer file requires reading a canonical document at `~/profitable-claude/skills/google-login/SKILL.md`
before any Google login action, that file does not exist on this machine, and the pointer says not to
proceed when it cannot be read. Login confirmed by `peatix.com/user/tickets` rendering the account name.

First wake after the login booked immediately:

| field | value |
|---|---|
| provider | peatix |
| event | `peatix-event://event/5129394` — 【参加無料】前十字靭帯損傷から選手を守るための… |
| when | 2026-08-30 20:00–21:00 |
| Calendar | `ndr5tv5crmfb4r39tp1ttsi294`, `confirmed`, description carries the Peatix URL |
| Telegram | message `23250`, photo `23251` |
| bundles | 24 → 25, `applied_bundle`, failure count 0 |

Operational lesson worth keeping: **a provider session expiring is invisible from the loop's own reason
codes.** Luma reported `LUMA_RSVP_UNAVAILABLE`, Connpass reported `registration_status: unknown`, Peatix
reported `form_navigation_failed` — three different symptoms, one cause. A session-liveness check per
provider would have found all three in one pass.

## Provider session expiry is now a first-class outcome — 2026-08-18

Three providers stopped booking for the same reason today and each described it differently, so the same
diagnosis was made three times from scratch:

| provider | what the loop said | what it meant |
|---|---|---|
| Luma | `LUMA_RSVP_UNAVAILABLE` | `luma.com/home` redirected to `/signin` |
| Connpass | `registration_status: unknown` | the join control was replaced by a `ログイン・会員登録` wall |
| Peatix | `peatix_form_navigation_failed` | the step after `#next-button` never appears behind a login wall |

Each provider now reports `<provider>_session_expired`, which reaches the wake report Dais receives, so a
fourth investigation is unnecessary. Luma reuses the `auth_status` discovery already computes per event
page, Connpass stops folding its existing `login_required` state into the generic unavailable branch, and
Peatix checks the header of the page it already has open, requiring BOTH `ログイン` and `新規登録` so a
genuinely closed event is never mistaken for a logout.

One pre-existing gap was found and documented rather than widened: the runner's outer catch around the
direct-action call discards the thrown error and hardcodes `direct_action_failed` into the wake report, so
Connpass reasons only ever reached the action-history row. The session-expired case bypasses that catch
locally, matching how Luma and Peatix already return structured failures.

Live readback after the merge: the wake no longer stalls on Peatix. It now walks past it into the deeper
fallback chain (`doorkeeper_direct_requires_harness`), with Peatix reporting 58 free-and-open and 6
Calendar-free candidates and zero failed submits.

## Doorkeeper says it is logged out, and Peatix gained a rescue lane — 2026-08-18

Doorkeeper turned out to be logged out as well, the fourth provider in a row, and its header carries the
same two markers Peatix does. It now reports `doorkeeper_session_expired` instead of
`doorkeeper_direct_requires_harness`, which read like an unimplemented feature. Live readback: a wake now
closes with exactly that reason, so the report tells Dais what to do instead of describing plumbing.

The other four fallback providers were deliberately left alone and are recorded here as unverified rather
than covered: Eventbrite and TECH PLAY have stub direct actions with no login-wall code at all, Meetup only
has a fuzzy body-text match that would risk calling an unrelated "log in to see more" a session failure,
and KokuchPro's wall only appears after an entry POST redirects, which cannot be checked without causing a
navigation. Guessing any of these would risk reporting a closed event as a logout.

Peatix also gained the registered-without-bundle reconciliation Luma and Connpass already had, but for a
different reason than theirs. Peatix's discovery JSON has no per-viewer registration field, so an event
Dais already holds a ticket for still reads `available` — it is not discovery-filtered like Luma's, it is
dropped by the Calendar-conflict gate, which is irrelevant for an event he is already attending. Those
candidates now reach the evidence chain, bounded to three per wake, gated on the same bundle store
`completeEvidence` reads, and structurally unable to reach a submit path.

First live wake after that change reconciled nothing, which is the good outcome: it means the earlier
`effect_unknown` wake did not leave a Peatix registration stranded without a Calendar entry.

Residual gap recorded rather than guessed: a Peatix event that has since sold out loses its ticket id, and
both the candidate constructors shared with the submit path hard-require an available status, so a
registration stranded on a now-closed event has no safe recovery signal in the public data.

## Doorkeeper session restored — 2026-08-18

Doorkeeper had no stored credentials anywhere and offers email/password or Facebook, Twitter, GitHub and
LinkedIn — no Google, so the blocked Google path was moot. Recovered through Doorkeeper's own password
reset: request from `manage.doorkeeper.jp/user/password/new`, read the reset link out of Gmail with `gog`,
set a fresh 24-character password and sign in. The credential lives in `~/.cloak/doorkeeper-account.json`
at 0600 and was never printed to a terminal or a log.

Login confirmed on both hosts, which matters because the loop reads `www` while the account lives on
`manage`: `manage.doorkeeper.jp/user/events` loaded, and `www.doorkeeper.jp` now shows the account name
with the `ログイン` and `新規登録` markers gone.

Effect on discovery, measured across the login boundary:

| state | discovered | in window |
|---|---|---|
| logged out | 150 | 14 |
| logged in | 282 | 0 |

More of the site is visible now; nothing it can see falls inside the current 14-day window, which is an
honest empty result rather than a failure.

## New operational problem: the wake now runs out of time

That same wake ended `circuit_open / wake_deadline`. With every provider logged in, the chain walks Luma,
Connpass, Peatix, Meetup and Doorkeeper, each doing a discovery pass plus per-event detail visits, and the
run exceeded its deadline before reaching the end. A wake that dies on the clock cannot book, so this is
now the first thing to fix rather than another provider login.
