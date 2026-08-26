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
