# SDD ledger — plan: docs/superpowers/plans/2026-08-26-life-manager-cloud-on-time-core.md

Spec authority: docs/superpowers/specs/2026-08-26-life-manager-cloud-on-time-core-design.md
Start commit: a570ed078
Baseline: focused Life Manager suite 175/175 PASS.

## Pre-flight conflict and interface scan

| Tasks | Producer → consumer / internal agreement | Finding and ruling |
|---|---|---|
| 1 | structured itinerary → Task 2 provider adapter | Clean: Task 2 consumes Task 1 output and retains the duration adapter. |
| 1 ↔ 3 | nullable route facts → reminder formatter | Clean: Task 3 may render only fields produced by Task 1. |
| 2 ↔ 3 | event-anchored route/cache → claimed reminder | Clean: Task 3 consumes a route or degrades to event-only. |
| 2 ↔ 8 | travel server routes → legacy route retirement | Clean: Task 8 may retire only legacy identity/payment authority, not provider routes. |
| 3 ↔ 4 | reminder organ → scheduler orchestration | Clean: Task 4 calls Task 3 behind an independent error boundary. |
| 3 ↔ 7 | notification consent → reminder eligibility | Clean: server-owned opt-in gates reminder delivery. |
| 4 ↔ 7 | call organ → explicit call consent | Clean: Task 7 may set consent only on an explicit step; Task 4 requires exact true. |
| 5 ↔ 6 | Telegram session → Calendar consent | Clean: Task 6 derives uid from Task 5's verified session. |
| 5 ↔ 7 | WebApp entry → onboarding UI/API | Clean: Task 7 reuses panel auth established by Task 5. |
| 5 ↔ 8 | Telegram identity → legacy identity retirement | Clean: Task 8 removes query/local browser authority after Task 5 exists. |
| 6 ↔ 7 | Calendar ACTIVE state → onboarding progression | Clean: Task 7 consumes ACTIVE-only server state. |
| 6 ↔ 8 | Composio session consent → Google/Supabase retirement | Clean: Task 8 preserves Composio and removes only browser login authority. |
| 7 ↔ 8 | server-owned state/Stripe boundary → legacy retirement | Clean: Task 8 enforces, rather than replaces, Task 7 authority. |
| 1 | tests/implementation/files agree internally | Clean. |
| 2 | tests/implementation/files agree internally | Clean. |
| 3 | tests/implementation/files agree internally | Clean. `travel.js` export change is explicitly limited to claim helpers. |
| 4 | tests/implementation/files agree internally | Clean. |
| 5 | tests/implementation/files agree internally | Clean. |
| 6 | tests/implementation/files agree internally | Clean. Existing Composio integration is mandatory. |
| 7 | tests/implementation/files agree internally | Clean. No new persistence layer is permitted. |
| 8 | tests/implementation/files agree internally | Clean. Landing subset changes stay contract-tested from Life Manager. |
| 9 | verification/deployment steps agree internally | Clean. External observations remain open unless actually read back. |
| Operational 0 | balance/top-up/call acceptance agree internally | Clean. Portal balance and exact charge precede payment; recovery/reset prohibited. |

## Task 1 review loop

- Task 1 implementer: `/root/transit_parser`
- Task 1 base: `a570ed0782fa6762e92a08bab29d2d7b0b846c6d`
- Task 1 implementation: `d0dbbdfd54bc18442dca52a0d801b29be2084928`
- Task 1 review R0: fix-first — High: missing/invalid timezone was converted to UTC and fabricated anchored timestamps. Medium: invalid Gregorian dates rolled into another date.
- Task 1 Ruling: both findings are valid spec defects, not plan conflicts. Anchored parsing must fail closed to `null`; unanchored legacy duration parsing must retain its numeric projection without invented timestamp facts.
- Task 1 fix round 1 base: `d0dbbdfd54bc18442dca52a0d801b29be2084928`
- Task 1 fix round 1: `7342e04b5` — focused 13/13, related 33/33, mutation proof restored.
- Task 1 re-review R1: APPROVED — original High/Medium findings resolved; scoped 33/33 PASS.
- Task 1: complete

## Task 2 review loop

- Task 2 implementer: `/root/transit_wiring`
- Task 2 base: `7342e04b58cdab6ac8d1126b03323c194d90489e`
- Task 2 implementation: `026f59296920ebc31ece325cbe021b32683aaac1`
- Task 2 review R0: fix-first — High: Transit timeout never settles/falls back. High: scheduler drops `call_time_zone`. Medium: fallback wrapper issues two Google HTTP calls. Medium: default argument hides missing anchor from explicit test clock.
- Task 2 Ruling: all four findings are valid. AC-14 `Google route call 1` means one external HTTP route request, not one wrapper invocation. The new structured fallback uses one Google transit request; the pre-existing dual-provider helper remains only for unrelated legacy compatibility.
- Task 2 Ruling: the plan omitted `scheduler.js` from Task 2, but AC-11 requires the production user timezone path. Add `scheduler.js` and the existing daily journey contract test to this fix; this keeps the slice at three production files and does not broaden product scope.
- Task 2 fix round 1 base: `026f59296920ebc31ece325cbe021b32683aaac1`
- Task 2 fix round 1: `e377afddd428214988eb2b529311a9f5a229e184` — focused 69/69 and four mutation checks restored.
- Task 2 re-review R1: fix-first — High: production `fillTravel → directionsMinutes` still forces dual Google HTTP fallback, observed four HTTP calls for two failed Transit legs.
- Task 2 Ruling: the old dual-provider max test conflicts with binding AC-14 and yields to the spec. `directionsMinutes` must be a true structured-route projection; add production `fillTravel` HTTP-count coverage.
- Task 2 fix round 2 base: `e377afddd428214988eb2b529311a9f5a229e184`
- Task 2 fix round 2: `65c4a4fabbe82cce724fa67b4800fd9412f908c7` — focused 70/70 and legacy-dual mutation detected.
- Task 2 re-review R2: APPROVED — production failed Transit uses one Google Directions request per leg, accepted Transit uses zero, Routes API zero.
- Task 2: complete

## Task 3 execution

- Task 3 base: `65c4a4fabbe82cce724fa67b4800fd9412f908c7`
- Task 3 implementer `/root/travel_reminder` produced the RED test (`MODULE_NOT_FOUND`) but no production change after repeated bounded status checks; interrupted before any commit.
- Task 3 takeover implementer: `/root/travel_reminder_takeover`; inherits the uncommitted RED test and the same brief without scope change.
- Task 3 Ruling: inherited RED fixtures contradicted AC-19. A past-event fixture used `START - 1` while `START` was one hour after `NOW`; change to `NOW - 1`. Physical due fixture must be start = now + route 5m + buffer 5m + T5 = 15m. Online due fixture must be start = now + T5. This corrects tests, not product behavior.
- Task 3 implementation: `5685ca8aa` — focused 10/10, related 84/84, escape/release mutations detected.
- Task 3 review R0: fix-first — High: Supabase-unconfigured reminder bypasses durable claim. Medium: start-only event selection breaks post-start catch-up. Medium: Calendar interpreter online truth is dropped from event projection.
- Task 3 Ruling: all findings are valid. Add `events.js` to this fix because it is the canonical Calendar event projection and AC-19 cannot be satisfied by guessing online state in the reminder.
- Task 3 fix round 1 base: `5685ca8aa`
- Task 3 fix round 1: `9daeb7684` — focused 25/25, related 84/84, three mutations detected.
- Task 3 re-review R1: APPROVED — Supabase fail-closed, 10-minute post-start boundary, and Calendar online projection verified.
- Task 3: complete

## Task 4 review loop

- Task 4 base: `9daeb7684042d1691e471b260f1548b35e5f109d`
- Task 4 implementer: `/root/scheduler_reminder`
- Task 4 implementation: `b65f70f47` — call/reminder isolation wiring; focused 47/47 and three mutations detected.
- Task 4 review R0: fix-first — High: never-resolving call blocks Inngest reminder. High: never-resolving reminder blocks later organs for the same user. Medium: call logs leak Calendar title when notifications are disabled. Medium: scheduler emits a duplicate incomplete reminder receipt.
- Task 4 Ruling: all findings are valid acceptance defects. Reuse the existing per-user timeout for the call boundary, add a bounded reminder boundary, redact event text from wake logs, and retain only the canonical reminder receipt.
- Task 4 fix round 1 base: `571868b0b`
- Task 4 fix round 1: `22386d785` — focused 50/50, related 87/87, network-blocked 69/69, and four mutations detected; verification report `15170a560`.
- Task 4 re-review R1: APPROVED — Inngest call hang, same-user reminder hang, notification-off privacy, and single canonical receipt verified.
- Task 4: complete

## Task 5 review loop

- Task 5 base: `bbb0571bb`
- Task 5 implementer: `/root/telegram_onboarding_entry`
- Task 5 Ruling: `startReply` was dead production code; add `server.js` so the real exact `/start` webhook and GET `/panel/onboarding` use the existing panel-auth boundary. Preserve legacy `onboardLink` until Task 8.
- Task 5 implementation: `511b0e5b8`; strict malformed-origin fix `fb71c3e5e`; verification reports `459fbf456` and `880e8bb18`; focused 48/48.
- Task 5 review R0: fix-first — Medium: explicit Telegram `{ok:false}` was unobserved while webhook acknowledged. Low: `/start-foo` and `/start?` opened onboarding.
- Task 5 Ruling: preserve webhook HTTP 200 to avoid Telegram update replay, but require `sent.ok===true` and surface only a generic failure. Enforce the exact Telegram `/start` command boundary and block punctuation lookalikes from legacy free-text onboarding.
- Task 5 fix round 1: `f3cb316d3`; verification report `f08c0a592`; focused 48/48 with three mutations detected.
- Task 5 re-review R1: APPROVED — real HTTP valid/start-payload/exact-bot, punctuation negative, explicit rejection privacy, existing panel auth 44/44, and no unauthorized session writes verified.
- Task 5: complete

## Task 6 review loop

- Task 6 base: `03442db73`
- Task 6 implementer: `/root/calendar_onboarding_consent`
- Task 6 Ruling: reuse existing panel session, OAuth-state table/claim callback, Composio helpers, and derive the compatible 43-character state as a session-scoped HMAC; no second OAuth/store.
- Task 6 implementation: `4f0c87d10`; session-renewal fix `a9c385cad`; reports `ffcb9837d` and `29353ecec`; focused 62/62.
- Task 6 review R0: fix-first — exact provider enabled truth was permissive; repeated/concurrent start created duplicate state/link; missing dedicated HMAC secret fell back to service key; session renewal was initially dropped.
- Task 6 Ruling: expand to the existing OAuth-state store interface and one additive migration. Enforce one live state per uid/chat/provider atomically, fail closed without an explicit session secret, and require `enabled===true`.
- Task 6 fix round 1: `9b1f0585e`; report `d716b2d4d`; focused 68/68 and related panel/auth 42/42.
- Task 6 re-review R1: fix-first — binding could change after initial scope assertion but before provider/state effects because the atomic RPC did not revalidate/lock the current Telegram binding.
- Task 6 Ruling: provider status is read-only first; then the RPC revalidates exact uid/chat under `FOR SHARE` and claims state; only then may provider mutation/link run.
- Task 6 fix round 2: `31898fc55`; report `be4364c77`; six boundary mutations detected.
- Task 6 re-review R2: APPROVED — rebind gives 401/state0/provider0, concurrent start gives 200+409/state1/link1, exact enabled/renewal/secret/callback regressions verified; 69/69 + 42/42 PASS.
- Task 6: complete (production migration apply/readback remains Task 9)

## Task 7 review loop

- Task 7A base: `e68dca565`
- Task 7A implementer: `/root/task7a_onboarding_api`
- Task 7A implementation: `67d56e9a1` — session-scoped state/transition RPC, phone/call consent and Stripe-only paid boundary; focused API/auth/billing 51/51 PASS.
- Task 7A review R0: fix-first — High: a new QR actor remained `unknown_actor`; High: onboarding read a stale Calendar marker instead of exact Composio status; High: the scheduler cohort excluded phone-less paid users and the legacy onboarding loop rewrote their stage; High: payment skip made later checkout unreachable. Medium: path-action POST accepted array/primitive JSON.
- Task 7A Ruling: all five findings are valid acceptance defects. Split the fix to preserve the three-production-file slice rule. R1A owns verified actor provisioning, provider-truth synchronization, malformed-body rejection and unpaid-dashboard checkout reachability. R1B owns phone-less scheduler inclusion and legacy stage non-regression. The existing signed Telegram initData remains the only actor authority; the existing Stripe webhook remains the only paid writer.
- Task 7A fix R1A: `2520e573a` — new actor provisioning, Calendar truth synchronization, strict JSON shape and unpaid-dashboard checkout; focused 74/74 PASS.
- Task 7A R1A review: fix-first — High: POST synchronized Calendar in a separate committed RPC before invalid/out-of-order transition rejection, violating zero-write and leaving a TOCTOU window. Medium: the verified Telegram profile name was discarded for every new actor.
- Task 7A Ruling: validate action/payload before provider work, then combine provider-status synchronization and transition in one SQL transaction so rejection rolls back both. Carry the bounded HMAC-verified profile name only as display data into a new claim RPC; actor id remains the sole identity key and an existing non-empty name is immutable.
- Task 7A fix R1A round 2: `87f6a6a73`; v2 fixture updates `26bfc4f3b`, `96c3195db` — atomic Calendar-sync transition, Telegram profile display data, and truthful new-actor session tests; expanded 94/94 PASS.
- Task 7A R1A final review: APPROVED — invalid/stale HMAC RPC0, new actor provisioning, same-actor resume, cross-actor isolation, replay 409, provider-truth sync, conflict rollback, unpaid checkout and Stripe-only paid boundary verified. Production PostgreSQL migration execution/concurrency remains Task 9.
- Task 7A fix R1B: `f07379956` — phone-less paid/comped users enter the scheduler cohort and legacy onboarding preserves canonical done; focused 117/117 PASS.
- Task 7A R1B review: fix-first — High: stale `call_enabled=true` with no phone reached `placeCall({to:null})` after cohort widening. Medium: an unconditional done guard also preserved incomplete legacy unpaid rows after comp expiry.
- Task 7A Ruling: hard-gate both batch and direct call paths on strict stored E.164 plus exact call consent. Payment remains intentionally skippable, so preserve unpaid done only when the actual server-owned core prerequisites (home and notifications) are present; incomplete legacy done continues through its prior pay/comp rules.
- Task 7A fix R1B round 1: `2dc2ffef2`; direct-webhook fix `7a8e51188` — strict E.164 + consent call gates, phone-less runtime cohort, core-ready legacy separation and canonical done webhook no-op.
- Task 7A R1B final review: APPROVED — phone-less travel/reminder reachability, batch/direct/Inngest call0 without valid phone, valid-call preservation, done no-op and browser-task paid+done verified. Changed-core suite 72/72 PASS. The unchanged browser-task HTTP fixture still lacks the pre-existing required `binding_commitment`; Task 9 owns full-suite fixture reconciliation.
- Task 7A: complete (production migrations and real PostgreSQL concurrency/readback remain Task 9)
- Task 7B implementation: `1809e7d9b` — Telegram-native `/panel/onboarding`, exact two-path auth return allowlist, server-step rendering, safe Calendar/Stripe links, and executable 375px action contracts; focused 96/96 PASS.
- Task 7B review R0: fix-first — High: verified Calendar consent returned to `/panel` and interrupted Calendar → home. Medium: device-code exchange lost the onboarding return path; AC-31 location fallback copy was absent; onboarding POST sent but did not enforce idempotency receipts.
- Task 7B Ruling: derive callback return only from authenticated server onboarding state, preserve only the exact two panel paths across device exchange, add truthful live-location fallback copy, and reuse tenant-scoped command receipts before provider/transition work.
- Task 7B fix R1: `270f6d519` — server-state callback continuation, fixed device allowlist, AC-31 copy, and receipt claim/replay/conflict/pending/failed handling; focused 101/101 PASS.
- Task 7B final review: APPROVED — callback failure/dashboard behavior, malicious device return values, current-location non-claim, and zero-repeat idempotency effects verified. Expanded six-file suite 135/135 PASS; syntax and diff checks PASS.
- Task 7B: complete (production deployment and clean-actor E2E remain Task 9)

## Task 8 review loop

- Task 8 base: `9cb4221ec`
- Task 8 implementer: `/root/task7a_onboarding_api`
- Task 8 implementation: `5cafd6936` — all five legacy `lm-onboard` actions return effect-free JSON 410; `/lm` is a fixed Telegram handoff; the 595-line shadow client is deleted.
- Task 8 execution correction: the implementer initially wrote four owned paths in the dirty main checkout. Work stopped; those exact four paths were transferred with patches to the canonical worktree and restored to main HEAD with `git diff --exit-code` proof. No other main changes were touched.
- Task 8 review R0: APPROVED — 210 method/payload probes return 410/fetch0, active `/lm` authority scan is empty, deleted client import0, and Railway Calendar/Stripe webhook production files are unchanged. Focused 130/130 parent suite and 115/115 reviewer suite PASS; syntax, diff, dependency and secret checks PASS.
- Task 8: complete (production Netlify/Railway readback remains Task 9)

## Task 9 integration, migration, and production release

- Integration fixes: `b18baeeb5` corrected Japanese domestic phone normalization and PostgreSQL-deparsed 21-day constraint detection; `b649071fe` removed phone-shaped static fixtures without changing runtime values.
- Migration release fix: `6d169fd3e` renamed onboarding core so lexical order is OAuth → core → reachability and made the 28-day coverage migration a complete no-op when its optional table is absent.
- Database validation: production Supabase accepted all four migrations inside `BEGIN … ROLLBACK`; the optional-table-present path also created the historical table, upgraded to eight 28-day constraints, asserted them, and rolled back.
- Database apply: the four migrations committed in one production transaction. Management API readback confirmed seven functions, service-role execution, anon denial, the live OAuth-scope unique index, and unchanged absence of the optional coverage table.
- Final verification: focused phone/migration suite 93/93 PASS; migration suite 70/70 PASS; full `npm test` PASS; 60-commit gitleaks scan found zero leaks; added PII findings are zero; `git diff --check` PASS.
- Fresh adversarial review: final production code and migration R2 both `ship`, Critical/Important/Minor findings zero.
- Canonical release: PR `Daisuke134/life-manager#2899` merged as `d9b5274150ce957804b1c63c2a0540b77fcf8495`. GitHub Deployments reports Railway `Anicca / production` success for that exact SHA; public `/health` is HTTP 200 JSON.
- Landing release: the live Netlify owner was still `Daisuke134/anicca-products`, so only the canonical three-file subset was synced in PR `#398`, merged as `ccd062ac0dbff85f3afda4ffbd797615b288d72f`. Immutable Netlify deploy `6a8f657d48fd9afdfb22dcb8` was restored to production. All five legacy actions return JSON 410; the public page has three fixed Telegram deep links and zero query/browser-storage authority markers.
- QR readback: the live `/life-manager` page preserves the 116×116 QR and exact adjacent deep link `https://t.me/LifeManagerBotbot?start=lp`; prior clean decode evidence remains valid and the deployed payload source is unchanged.
- Dais tenant production repair: exact Telegram-bound tenant count was one; the existing E.164 phone, paid, Calendar, home, notifications, automation, timezone, language, and completed onboarding read back valid. A single transaction changed only `wake_policy` to `all-events` and `call_enabled` to true; post-write readback returned both true.
- Operational status: Telnyx authentication is at the Authenticator-code screen. No top-up or call was attempted without the current six-digit code and exact portal minimum readback.
- Remaining acceptance: real Transit provider route; clean Telegram actor onboarding and cross-actor isolation; Telnyx minimum top-up with exact approval; controlled Calendar event with travel block, T-10/T-5 calls, T-5 Telegram route; replay-zero provider readback.

## Task 10 Telegram T-5 deadline isolation

- Production reproduction: a private no-location Calendar event was created for 07:43 JST and read back from Google with the same event ID. Dedicated wake produced durable T-10 at 07:33:14 and T-5 at 07:38:21; both Telnyx callbacks reached `amd_result=machine`, proving the balance gate and provider call path were live.
- Failure evidence: `lm_travel_log` had zero `telegram-t5` claims through event start, while the monthly Composio ledger read 27,254 calls and selected the 300-second degraded organ interval. There are seven tenants and the organ path processes them serially with a 90-second per-user ceiling.
- Root cause: AC-19 requires a 60-second reminder tick, but Task 4 placed reminder execution inside the degradable, multi-organ, sequential `organsUserOnce` loop. Call timing stayed correct only because wake already has its own fixed 60-second loop.
- Ruling: reuse the existing wake-loop isolation pattern for a dedicated fixed-60-second reminder loop, remove reminder execution from the degradable organ loop, and retain the existing `lm_travel_log/telegram-t5` atomic claim as the single dedupe writer. Cost if wrong: one extra Calendar fetch path per enabled tenant per minute; correctness and user-visible deadline outrank the current Composio degradation policy for this deadline-critical channel.
- Task 10 status: in progress; RED test, minimal implementation, production deploy, Telegram provider receipt, and replay-zero remain.
- Production failure closure: the same event still had zero `telegram-t5` claims at 07:53:19 JST, after the full 15-minute catch-up window. The controlled Google event was then deleted with `deleted=true`; exact-ID readback returned `status=cancelled`.
- Task 10 implementation R0: `847ec41f9` — dedicated reminder user/tick/loop, concurrent per-tenant timeout, old degradable-organ path removal, runtime-gate/server wiring; implementer focused 37/37, related 90/90, Inngest+scheduler 36/36 PASS. Parent fresh combined suite 161/161 PASS; production syntax and diff checks exited zero.
- Task 10 review R0: fix-first — High: `startReminderLoop` schedules the next timer only after the current tick resolves, creating work-duration-plus-60-second drift and permanent halt if `listUsers` hangs. Medium: no deterministic cadence regression covered the slow/hung tick boundary.
- Task 10 Ruling: both findings are valid AC-25 deadline defects. Schedule the next wall-clock start independently of current work, retain close safety, and pin it with a slow/unresolved tick test; durable claim remains the external-effect overlap guard.
- Task 10 fix round 1/5: `4c50e3233` — next 60-second start is reserved before awaiting the current tick; close cancels the reservation and racing callbacks stand down. Focused 38/38 and related 90/90 PASS; production syntax and diff checks exited zero.
- Task 10 re-review R1: ship — drift/permanent-halt High and deterministic-cadence Medium both ADDRESSED; new Critical/High/Medium findings zero.
- Task 10: complete (commits `c002e43e0..4c50e3233`, review clean). Production deploy, Telegram provider receipt, and replay-zero remain acceptance work below.
- Task 10 production E2E after release `ccef9799d`: target 08:40 physical event had Telnyx departure T-10 at 08:03:47 and T-5 at 08:08:58, both `amd_result=machine`. Target `telegram-t5` claims remained zero; all post-deploy `telegram-t5` claims were also zero.
- Task 10 production root cause R2: main retained the fixed in-process loop, but `LIFE_RUN_LOOPS=false` disables every in-process starter and lets the existing every-minute Inngest `sweep-wake` call `wakeUserOnce`. R0 removed reminder from `organsUserOnce` and tests explicitly asserted `wakeUserOnce` reminder effect zero, leaving the Inngest owner mode with no reminder path.
- Task 10 Ruling R2: reuse the existing Inngest every-minute sweep and per-uid concurrency by composing `reminderUserOnce` back into `wakeUserOnce`; do not add another cron/function/queue. In-process runtime remains single-writer because it calls `wakeCallOnce`, `reminderTick`, and `organsUserOnce` directly, never `wakeUserOnce`. Cost if wrong: Inngest mode may add one bounded reminder evaluation per minute; the existing durable `telegram-t5` claim protects repeated external effects.
- Task 10 fix round 2: `2faec285f` — `wakeUserOnce` now runs the existing bounded `reminderUserOnce` once after the bounded call attempt and before later organs. RED was 35/38 with the three expected zero-reminder failures; parent GREEN is focused 38/38 and related Inngest/scheduler/reminder 115/115, with syntax and diff checks clean.
- Task 10 re-review R2: ship — the existing Inngest sweep owns exactly one reminder evaluation per uid/run, the in-process owner remains non-duplicated, call failure/timeout cannot suppress reminder, reminder timeout cannot suppress later organs, and raw Calendar reuse/privacy/atomic claim contracts are unchanged. Reviewer focused tests were 7/7 and the additional composition probe returned one reminder and one later-organ start.
- Task 10 status: code and review complete; exact Railway deployment, production Telegram provider receipt, and replay-zero remain acceptance work.

## Task 11 clean Telegram actor production reachability

- Production RED: two isolated, previously absent Telegram actor IDs submitted correctly signed, current initData with the exact Railway origin. The origin gate passed, but both `/api/panel/session/telegram` requests returned 500 `panel_auth_unavailable`; user, session, and replay writes remained zero.
- PostgreSQL reproduction: `BEGIN; SELECT * FROM claim_lm_panel_telegram_init_v2(...); ROLLBACK;` failed with SQLSTATE `42702`, because the `RETURNS TABLE` output variable `uid` conflicts with the unqualified `ON CONFLICT (uid)` target in the first-actor INSERT branch. Existing actors never enter that branch.
- Ruling: do not change global or function-wide `plpgsql.variable_conflict`. Replace the ambiguous arbiter with the existing primary-key constraint name, patch the clean-install migration, and add an ordered replacement migration for production. Preserve deterministic uid, replay, profile-name, and actor-binding behavior.
- Task 11 RED→GREEN: `5b27c5743` replaced the conflict target and added the ordered replacement migration; production rollback then found the second `WHERE uid = bound_uid` ambiguity. Fix round `dad282b6d` qualified the update through alias `u`. Parent related suite is 132/132 PASS and diff/syntax checks are clean.
- Production PostgreSQL rollback: the final additive migration executed against the real schema, a fresh actor returned `claimed` with deterministic uid and preserved profile name, the same hash returned `replayed`, and rollback readback returned both user and replay absent.
- Task 11 fresh review: ship, all severity findings zero. Clean/additive v2 bodies match, migration order/idempotency and service-role-only ACL hold, and replay, actor binding, concurrency, profile immutability, and the legacy 2-arg wrapper are unchanged.
- Task 11 status: code/review complete; merge, production migration apply, two-actor production session/isolation E2E, and exact cleanup remain.
- Task 11 release: PR `#2905` merged as `cebe11224eb7a6701848d8bd236b0f88232bf16a`; GitHub Deployments reports Railway `success` for the exact SHA and life-call health is HTTP 200.
- Task 11 migration apply: the additive replacement committed in one production transaction. Readback is `named_arbiter=true`, `qualified_update=true`, service-role execute true, anon execute false.
- Task 11 production E2E: actor A and B each created a `/panel/onboarding` session with HTTP 200 and distinct deterministic tenant references; exact initData replay returned 409, a fresh A initData resumed A while preserving the first profile name, and hostile cross-actor `uid/tg` query values did not change either session scope. Both states were `calendar`.
- Task 11 cleanup: pre-delete readback was exactly two test users, three current test sessions, and three replay receipts. The first assertion wrapper was rejected before deletion; the exact transaction was then simplified and committed. Final readback is users 0, sessions 0, replays 0.
- Task 11: complete. A real second-person Telegram client QR scan remains the separate final clean-device acceptance item.

## Task 12 resolved destination reuse

- Production diagnosis: the real `MUIT 出社 (着席)` event stores free-form `MIRSUBISHI UFJ INFORMATION TECHNOLOGY`; destination geocoding returned `ZERO_RESULTS` and the route was null.
- Existing autofill evidence: the adjacent outbound `[Travel]` block ends at the event start and stores the complete Akasaka destination address. The same production Maps key and home origin returned a Transit journey with real station steps when that address was used.
- Ruling: reuse only the matched outbound Travel block's non-empty location as the route destination. Keep the original event title/location for user-visible reminder text and durable claim identity. Do not add another resolver, provider, table, or fetch.
- Task 12 R0: `71c8e9dc2` passed the related 76/76 suite but failed a parent realistic return-block counterexample: a prior-event Travel block arriving home at the target start was selected as the target destination. Multiple same-start candidates were also not identity-safe because legacy blocks store no source event ID.
- Task 12 ruling: reject home-destination candidates and require exactly one eligible adjacent Travel candidate; zero or multiple candidates fail closed to the original event location.
- Task 12 R1: `a9ab7069c` rejects normalized home-destination helpers and requires exactly one eligible adjacent Travel candidate. The realistic return and multiple-candidate tests were RED before the fix; the related reminder/wake suite is 78/78 PASS after it. Commit is pushed and worktree is clean.
- Task 12 review R2 (fresh read-only Sonnet, 2026-08-27): FIX-FIRST — Critical: cross-event misattribution (a Travel block belonging to a different event 90s away can be the sole adjacency candidate and is reused); High: home equality check misses NFKC drift (full-width digits/dashes let a return block's home address through). Display/claim invariants, privacy logging, and timezone boundaries were attacked and held.
- Task 12 fix round 2: `beb038f9d` — a candidate matching another timed non-helper event's [start-2min,start+1min] window is ambiguous and fails closed; home comparison NFKC-normalizes with dash-class folding. RED first (both counterexamples reproduced), focused 19/19, related suite 80/80 PASS. Pushed.
- Task 12 review R3 (fresh read-only Sol): FIX-FIRST — Critical 0 / High 1 / Medium 0. The cross-event and NFKC examples are closed, but a return block whose destination is an old-home or semantically equivalent home spelling can still pass exact normalized equality and be reused. Display/claim identity, replay safety, privacy, timezone, and prior fixed boundaries held; reviewer focused suites were 59/59 and 19/19 PASS.
- Task 12 ruling R3: address equivalence is not a reliable return discriminator. Add one structural negative: a Travel candidate whose start matches another timed non-helper event end within Calendar drift is a possible return block and must fail closed. No address parser, geocoder, provider, fetch, or table.
- Task 12 status: same Luna implementation lane must add the old-home/semantic-address RED and minimal structural guard; then fresh exact-commit re-review, PR/merge, exact Railway deploy, real route readback, Telegram receipt, and replay-zero remain.
- Task 12 fix round 3: `07d0b3124` — rejects a Travel candidate whose start matches another timed non-helper event end within ±60 seconds. The old-home return fixture was RED with the wrong old-home destination before production code; focused 20/20, related 81/81, and mutation removal FAIL/restored PASS.
- Task 12 review R4 (fresh read-only Sol): ship — spec compliant and Task quality Approved; Critical/Important/Minor findings zero. Original event selection, provider count, display/claim identity, privacy, and timezone boundaries remain unchanged.
- Task 12 code status: complete at `07d0b3124`. Production merge/deploy, physical route/Telegram receipt, and replay-zero remain under finish-plan Tasks 6 and 8.

## Production E2E — controlled event 2026-08-27 evening (deployed SHA 5b06e1ee0)

- Verified 2faec285f (Inngest reminder owner fix) is an ancestor of origin/main; Railway production deployment SHA readback is 5b06e1ee0 (GitHub Deployments, success).
- Focused 78-test suite re-run at session start: 78/78 PASS.
- Controlled no-location event `ah40e31tqlstvk2qvo1e0jt82c` created 20:03–20:13 JST via gog (Google create readback with ID/status=confirmed). T-10 wake claim `…|2026-08-27T20:03:00+09:00|10` called_at 10:53:24Z (19:53:24 JST) amd_result=human — durable Supabase readback. T-5 call and telegram-t5 claim pending observation.
- Spec revision (Dais 2026-08-27): trial-first payment — AC-30 amended, AC-37/38 and Slice 3G added, commit `620a8a8ec`.
- Current Google official readback: controlled events `lnpffie7md7fp0qp5j9hrudkq4` and `ah40e31tqlstvk2qvo1e0jt82c` are past but still `confirmed`. Do not delete until exact T-5/Telegram/replay evidence is reconciled; then delete with `send-updates none` and verify `cancelled`.
- The 2026-08-28 08:40 `MUIT 出社 (着席)` instance is past. Later recurrence instances currently have no location, so they cannot close the resolved-address route acceptance. After deploy, create one new future controlled physical event for the combined provider E2E.
- Current focused Task 12/reminder/wake command is 80/80 PASS. A clean `npm ci` hit local ENOSPC after restoring the declared `canonicalize@1.0.8`; full-suite completion requires a clean dependency environment or CI and must not be inferred from the focused run.

## Telegram-first product UX authority

- Dais approved the launch order: finish the existing on-time core first; add Poke/Town-style free conversation only after friend beta is receipt-bearing.
- Visual product and architecture SSOT: `docs/superpowers/specs/2026-08-28-life-manager-cloud-telegram-product-ux-design.md`.
- Sole active checklist: `docs/superpowers/plans/2026-08-28-life-manager-cloud-on-time-core-finish.md` — structural return guard → server-owned trial → cohort/UI/upgrade → PR/deploy → real actor/event E2E → replay-zero/cleanup.
- OpenClawMU/Hermes is a post-launch conversation sidecar candidate, not the tenant/billing/ledger owner and not an active implementation item.

## Task 13A server-owned trial persistence

- Plan ruling: source-regex migration assertions were rejected as change detectors. The slice uses a disposable real PostgreSQL harness plus an independent production rollback preflight.
- Implementation: `736979c2f` adds nullable `trial_expires_at`, same-signature onboarding RPC replacements, one-time `notifications.enable` grant, dashboard terminal stages, JSON deadline/active fields, preserved tenant lock/scope/ACL, and no `paid` writer. `d8974760d` strengthens the real PostgreSQL evidence.
- TDD/readback: missing-migration RED; local PostgreSQL `grant_once=1 trial_active=1 tenant_scope=1 acl=1 paid_writes=0`; unchanged Node panel/onboarding contracts 34/34.
- Review R0 found two Important evidence gaps (exact three-day window and actual paid-column write tripwire) plus one Minor pre-grant JSON gap. Fix round 1 added server clock bounds, `BEFORE UPDATE OF paid` rejection, and null/false state. Scoped fresh Sol re-review: all addressed, new breakage none, ship.
- Production Supabase rollback-only preflight: exact transaction-timestamp + 3 days, repeat deadline unchanged, tenant/chat isolation, service-role ACL, paid false. Post-rollback official readback is `trial_column_count=0`, `fixture_count=0`, `trial_body_present=false`.
- Task 13A code/preflight status: complete at `d8974760d`. Production migration apply remains intentionally deferred to finish-plan Task 6 immediately before exact-SHA deploy.

## Task 13B value-first panel

- Implementation: `982bd74ce` extracts one tenant-scoped `buy.stripe.com` validator, exposes server-owned trial truth, normalizes legacy ready stages, makes checkout optional/secondary, and adds a truthful optional next-event preview plus ready UI. `e12458c07` fixes review findings.
- TDD: missing-module and four behavior REDs; first GREEN 96/96; fix RED 52/54; final focused panel/auth/billing/payment suite 97/97. Stripe-host and client-deadline mutations were detected.
- Review R0 found two Important defects: helper blocks could enter preview because nonexistent flags were checked, and expired/paid states received false active-trial copy. Fix round 1 reuses `isHelperBlock(summary)` and branches copy only on server `paid`/`trialActive`. Scoped re-review: both addressed, new breakage none, ship.
- Primary verification: 97/97 plus syntax/diff PASS. Task 13B: complete at `e12458c07`; no production migration/deploy/Stripe effect occurred.

## Task 13C trial entitlement cohort

- Implementation: `4ea06aefb` replaces standalone `paid=is.true` with exact PostgREST `paid OR trial_expires_at > server clock`, preserving providers, phone independence, global comp, and one selector SSOT. Plan ruling `df3692ecb` assigns the stale daily-preflight consumer assertion to the slice; `11a6cc993` updates only that test.
- TDD: selector RED 7/11 then GREEN 11/11; `.gt→.gte` mutation detected. Consumer RED 79/80 exposed the retired `paid` query assertion; exact `or` fix produced combined 80/80.
- Fresh Sol review: ship, spec compliant, Critical/Important/Minor zero; PostgREST grammar, exact expiry, comp boundary, Date.now/process.env restoration, two scheduler selectors, and daily-preflight URL were verified.
- Primary verification: selector/daily/wake/reminder suite 80/80 plus syntax/diff PASS. Task 13C: complete at `11a6cc993`; production column/code deploy remains deferred to Task 6.

## Task 13D durable trial upgrade and travel-ledger repair

- Initial implementation `b3dc841bd` added the existing onboarding-owner expiry branch. Fresh Sol R0 found a Critical schema mismatch: production `lm_travel_log.leg` still allowed only `go|return`, so both existing `telegram-t5` and new `trial-upgrade` claims 400. It also found malformed Telegram receipt acceptance and swallowed release failure.
- Plan ruling `9e6b6f323`: retain the existing travel ledger, widen only its exact `leg` CHECK to `go|return|telegram-t5|trial-upgrade`, verify with real PostgreSQL, accept only positive integer Telegram message IDs, make `unclaimTravel` return verified DELETE status, and fail closed to generic reconciliation when release fails.
- Fix round 1 `34187a389`: 4-leg idempotent migration/integration test, verified release boolean, positive-integer receipt, generic reconciliation. PostgreSQL PASS, Node 117/117. Re-review closed Critical/Important findings but required exact-expiry/send-throw regressions.
- Fix round 2 `cd6669dee`: test-only exact millisecond expiry claim→send and send-throw claim→send→unclaim. Focused 7/7, full Task 5 Node matrix 119/119, PostgreSQL PASS. Scoped fresh Sol re-review: both addressed, new breakage none, ship.
- Production Supabase rollback-only leg preflight: existing rows/unique/RLS/other CHECK preserved; four allowed, unknown/duplicate rejected, constraint validated. Post-rollback official readback: fixture 0 and `telegram_t5_allowed=false` restored.
- Task 13D code/preflight status: complete at `cd6669dee`. Both trial and leg migrations remain unapplied until controlled Task 6 release.
