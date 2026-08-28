# Life Manager Cloud On-Time Core Implementation Plan

> **Required subskill:** Execute this plan with `superpowers:subagent-driven-development`, one task at a time. Production changes use test-driven development; every task receives a fresh read-only review before the next task.

**Goal:** Make cloud Life Manager call consenting users at T-10/T-5, send a safe event-and-transit Telegram reminder at T-5, preserve travel-block autofill, and onboard each QR-scanned Telegram user without Google/Supabase browser sign-in.

**Architecture:** Google Calendar remains the schedule source. `travel.js` requests an event-anchored Transit itinerary and persists the existing travel block/ledger. The scheduler runs calling and Telegram reminder organs independently. Telegram `initData` establishes tenant identity for a server-owned onboarding state machine; Composio remains the Google Calendar consent boundary and Stripe remains the only payment authority.

**Tech stack:** Node.js 22, built-in `node:test`, Express, Telegram Bot API, Transit API `/plan`, Google Directions fallback, Composio, Stripe, existing PostgreSQL/Supabase adapters.

**Design spec:** `docs/superpowers/specs/2026-08-26-life-manager-cloud-on-time-core-design.md`

**Product UX:** `docs/superpowers/specs/2026-08-28-life-manager-cloud-telegram-product-ux-design.md`

## Global invariants

- Do not alter `deploy/local`, add a database, service, package, or authentication provider.
- Calls require `call_enabled === true`. Dais receives all-event calls; other tenants explicitly opt in.
- Physical-event reminder time is computed departure T-5; non-travel reminder time is event-start T-5.
- Transit requests include the event date, clock time, correct `arrival`/`departure` anchor, and `numItineraries=3`.
- A valid Transit result causes zero Google calls. An unusable/error result causes at most one sequential Google fallback.
- Platform, exit, carriage, congestion and accessibility facts are nullable. Never infer or fabricate them.
- Telegram reminder dedupe reuses `lm_travel_log` with leg `telegram-t5`; failed sends release the claim.
- Escape event/provider text before Telegram HTML. Never put tokens, phone numbers, home addresses, OAuth URLs, or live coordinates in ordinary logs.
- Telegram session identity is authoritative. Ignore client-supplied `uid`, `tg`, `telegram_id`, localStorage identity, and query-string identity.
- Phone collection never enables calling. Only explicit call consent does.
- The only paid-state writer is the verified Stripe webhook.
- The server grants one three-day trial after Calendar, home, and notifications are ready. Reopening onboarding never extends it.
- Do not add OpenClawMU, Hermes, a conversational runtime, or local-product parity before this on-time core has provider receipts and replay-zero.
- Baseline before implementation: focused suite 175/175 passing.

## File map

| Area | Production | Tests |
|---|---|---|
| Structured itinerary | `apps/life-manager/lib/transit.js` | `apps/life-manager/lib/transit.test.js` |
| Provider wiring/cache | `apps/life-manager/lib/travel.js`, `route-cache.js` | `travel-transit-wire.test.js`, `route-cache.test.js` |
| T-5 reminder | `apps/life-manager/lib/travel-reminder.js`, `travel.js` | `travel-reminder.test.js` |
| Scheduler isolation | `apps/life-manager/lib/scheduler.js` | `test/wake-loop-isolation.test.js` |
| Telegram onboarding entry | `apps/life-manager/lib/telegram.js` | `telegram-onboard.test.js`, `panel-auth.test.js` |
| Calendar consent | `apps/life-manager/lib/calendar-onboard.js`, `server.js` | `calendar-onboard.test.js` |
| Onboarding state/UI | `apps/life-manager/lib/panel-api.js`, panel assets | `panel-api.test.js`, `panel-ui.test.js` |
| Legacy authority retirement | `apps/landing/src/app/lm/LmClient.tsx`, server routes | existing contract/billing tests |

---

## Task 1: Parse a truthful structured Transit itinerary

**Files:** Modify `lib/transit.js`, `lib/transit.test.js`.

1. Add failing fixtures for overnight `arrival` selection, `departure` selection, rail/bus/walk leg fields, fare, and absent platform/exit facts.
2. Run `node --test lib/transit.test.js`; confirm the new assertions fail for missing behavior.
3. Add `parseTransitPlan(plan, { anchorType, anchorSecs })` while keeping the existing duration adapter compatible.
4. Select the latest viable departure for arrival-anchored requests and earliest viable arrival for departure-anchored requests. Normalize times beyond 24:00.
5. Return only provider-backed fields: departure/arrival, duration, transfers, fare, route/headsign, stop names, platform when present, and walking legs. Unknowns remain `null`/absent.
6. Run the test, mutate one expected platform/route value to prove the assertion fails, restore it, rerun green.
7. Commit: `feat(life-manager): parse structured transit itineraries`.

## Task 2: Anchor provider queries to the calendar event and scope cache keys

**Files:** Modify `lib/travel.js`, `lib/travel-transit-wire.test.js`, `lib/route-cache.js`, `lib/route-cache.test.js`.

1. Write failing tests that inspect the Transit URL for `date=YYYYMMDD`, `time=HH:MM`, `type=arrival|departure`, `numItineraries=3`, and timezone-correct values.
2. Add tests proving accepted Transit makes zero Google calls, failure/unusable output makes exactly one Google call, and cache keys differ by provider, endpoints, mode, anchor type, and time bucket.
3. Run the two tests and record RED.
4. Introduce a structured `directionsRoute(...)`; retain `directionsMinutes(...)` as a thin compatibility adapter.
5. Thread the calendar event anchor through the Transit request and sequential fallback. Remove the shared unscoped cache key.
6. Run both tests, then Task 1 tests; mutation-check the request type and fallback count.
7. Commit: `feat(life-manager): anchor transit routes to events`.

## Task 3: Build the claimed T-5 Telegram reminder organ

**Files:** Create `lib/travel-reminder.js`, `lib/travel-reminder.test.js`; modify `lib/travel.js` exports only as required.

1. Write failing tests for physical-event computed-departure T-5, non-travel start T-5, due-window/catch-up boundaries, and no early send.
2. Test origin precedence: fresh live location, previous event location, configured home. If none exists, format an event-only reminder without inventing a route.
3. Test the exact Japanese message structure: next event, leave/start time, ordered legs, transfers, fare, and optional facts only when provider-supplied.
4. Test HTML escaping, `telegram-t5` claim-before-send, duplicate suppression, and claim release after send failure.
5. Run `node --test lib/travel-reminder.test.js`; confirm module/behavior RED.
6. Implement the smallest pure due/format helpers and one claimed send function using existing `claimTravel`/`unclaimTravel`.
7. Run green and mutation-check escaping and failed-send release.
8. Commit: `feat(life-manager): send claimed t5 travel reminders`.

## Task 4: Isolate calls and Telegram reminders in the scheduler

**Files:** Modify `lib/scheduler.js`, `test/wake-loop-isolation.test.js`.

1. Add failing tests proving a reminder failure does not suppress a due call and a call failure does not suppress a due reminder.
2. Prove `call_enabled !== true` produces no call but can still produce a notification; disabled Telegram notifications produce neither Telegram send nor leaked event data.
3. Wire the reminder organ after event/travel calculation with its own error boundary. Keep T-10/T-5 call levels unchanged.
4. Run scheduler, wake-level, catch-up, claim-token, and reminder tests; mutation-check each isolation boundary.
5. Commit: `feat(life-manager): isolate call and reminder organs`.

## Task 5: Make `/start` open a Telegram-authenticated onboarding page

**Files:** Modify `lib/telegram.js`, `lib/telegram-onboard.test.js`, `lib/panel-auth.test.js`.

1. Add failing tests that `/start` returns a `web_app` button to configured HTTPS `/panel/onboarding`, contains no user ID/token, and preserves the existing authorized panel session flow.
2. Implement the button using the configured public Railway origin. Keep the QR deep link unchanged.
3. Reject non-HTTPS production origins and invalid Telegram `initData`; never fall back to query identity.
4. Run both tests and mutation-check removal of `initData` verification.
5. Commit: `feat(life-manager): open authenticated telegram onboarding`.

## Task 6: Add session-scoped Calendar consent

**Files:** Create `lib/calendar-onboard.js`, `lib/calendar-onboard.test.js`; modify `lib/server.js`.

1. Write failing tests for session-derived uid, signed one-time nonce, Composio connect start, callback/status polling, ACTIVE-only success, replay/expiry rejection, and body/query uid being ignored.
2. Implement start/status routes as adapters around the existing Composio integration; do not add a second OAuth system.
3. Ensure redirect URLs and provider errors are returned only to the authenticated session and sanitized in logs.
4. Run new tests plus calendar signature/resume contract tests; mutation-check nonce replay and ACTIVE-only handling.
5. Commit: `feat(life-manager): add session scoped calendar consent`.

## Task 7: Implement server-owned onboarding state and mobile UI

**Files:** Modify `lib/panel-api.js`, `lib/panel-api.test.js`, panel UI assets, `lib/panel-ui.test.js`.

1. Add failing API tests for this fixed progression: Calendar → home → Telegram notifications → phone → explicit call consent → dashboard. Checkout remains reachable but is not an onboarding gate.
2. Test that server state resumes on another browser session for the same Telegram user, out-of-order writes are rejected, body uid is ignored, phone save leaves calls off, and unverified clients cannot set paid.
3. Add UI contract tests at 375px for one primary action, skippable optional phone/call, escaped copy, and no Google/Supabase login control. The ready screen shows the next event and server-owned trial deadline.
4. Implement the minimal state adapters using existing tenant/profile fields and existing panel auth; no new table or framework.
5. Run API/UI tests plus billing/auth tests; mutation-check phone→call and client→paid prohibitions.
6. Commit: `feat(life-manager): add telegram native onboarding state`.

## Task 8: Retire legacy browser identity and payment authority

**Files:** Modify the legacy LM server routes and `apps/landing/src/app/lm/LmClient.tsx`; update `test/onboarding-resume-contract.test.js`, `test/calendar-connect-signature-contract.test.js`, `lib/billing.test.js`.

1. Add failing contracts requiring legacy Google/Supabase exchange and raw Telegram-link endpoints to return `410 Gone` with no side effect.
2. Require the landing client to hand off to the Telegram WebApp route and contain no raw `tg`, localStorage identity, or client paid-state write.
3. Implement the retirement response and minimal handoff; preserve unrelated landing behavior.
4. Run all onboarding, panel, auth, and billing contracts; mutation-check one retired endpoint and the Stripe-only paid writer.
5. Commit: `refactor(life-manager): retire legacy onboarding authority`.

## Task 9: Full verification, deployment, and production acceptance

1. Run the focused regression set from the design spec and `npm test` in `apps/life-manager`. Any failure returns to the owning task.
2. Inspect `git diff --check`, secret scan of the branch diff, dependency/lockfile diff, and `git status`. No unintended package or local-runtime changes.
3. Run a fresh whole-branch read-only adversarial review against all 38 acceptance criteria; resolve every critical/high finding and rerun affected tests.
4. Fetch/rebase safely, push the branch, merge/deploy through the repository's existing production path, and read back the Railway deployment commit hash and health endpoint.
5. On a controlled Dais calendar event, verify official effects: travel block created/updated, T-10 call, T-5 call, one T-5 Telegram message, correct event-anchored itinerary, and no duplicate on replay.
6. On a separate test Telegram identity from the QR, verify session separation and complete onboarding without Google/Supabase browser login. Optional call remains off until consent; Stripe webhook alone changes paid state.
7. Re-run the scheduler after the event and verify replay-zero from durable ledgers/provider readback.
8. Mark every acceptance criterion and atomic task in the design spec complete only from observed evidence; leave any unavailable external observation explicitly open.

## Operational Task 0: Restore calling credit

This runs alongside code tasks but closes before production call acceptance:

1. Authenticate to Telnyx using the private credential SSOT and existing session. Never use recovery/reset.
2. Read the official portal balance and minimum permitted top-up. Do not infer balance from a low-credit error.
3. Before the irreversible charge, show the exact amount/currency/payment source and obtain the required approval if not already explicit for that exact charge.
4. Add only the minimum amount, save the official receipt privately, read back the new balance, and place one controlled call through the real runtime.

## Task 12: Route reminders through the autofill-resolved destination

**Files:** Modify `lib/travel-reminder.js`, `lib/travel-reminder.test.js` only. Soft target: production ≤35 LOC, test ≤80 LOC.

1. RED: an event with ambiguous free-form location and its immediately preceding outbound `[Travel]` block must call `directionsRoute` with the block's complete destination address.
2. RED negatives: do not reuse a home-destination return block, an old-home/semantic-address variant return block, multiple ambiguous candidates, non-Travel helper, unrelated block, empty location, or block outside the existing adjacency tolerance. The old-home fixture starts exactly at the previous real event end and ends at the target event start.
3. GREEN: add one structural return guard over the already-fetched tenant event array. A candidate whose start matches another timed non-helper event end within the existing one-minute Calendar drift tolerance is ambiguous and fails closed. Do not add address parsing, geocoding, a provider, a fetch, or a table. Preserve the original event for selection, claim key, title, and displayed destination.
4. Run focused and related reminder/wake suites. Mutation-check removal of the adjacency guard and Travel-only guard.
5. Fresh read-only review, merge/deploy exact SHA, then read back a real event route and the natural Telegram message receipt/replay-zero.

## Task 13A: Grant one server-owned three-day trial

**Files:** Create one forward migration; add focused migration/onboarding tests. Production SQL is the only implementation file in this slice.

1. RED: completing Calendar + home + notifications writes `trial_expires_at = transition_time + interval '3 days'`; a second completion, resume, or replay leaves the first value unchanged.
2. RED: client payload, localStorage, query parameters, and non-service roles cannot set or extend the deadline. Stripe webhook remains the only `paid` writer.
3. GREEN: add nullable `lm_users.trial_expires_at timestamptz`. In the locked onboarding transition, use `coalesce(trial_expires_at, now() + interval '3 days')` exactly when core prerequisites become complete.
4. Return the stored deadline and derived active/expired state from the existing onboarding state RPC. Do not add a table, trigger, usage meter, or second clock.
5. Run the migration in `BEGIN ... ROLLBACK` against production PostgreSQL, then apply once and read back the column, function body, ACL, and one isolated rollback fixture.
6. Commit: `feat(life-manager): grant one server owned trial`.

## Task 13B: Remove payment from activation and show the first value

**Files:** Create `lib/payment-link.js`; modify `lib/panel-api.js`, `lib/panel-ui.js`; test `lib/payment-link.test.js`, `lib/panel-api.test.js`, `lib/panel-ui.test.js`.

1. RED: a core-ready unpaid trial user lands on dashboard, not payment. The response exposes only `trialExpiresAt`, `trialActive`, `paid`, next-event summary/start, and a tenant-scoped Stripe link.
2. RED: the 375px ready screen shows the next event, the three active benefits, and remaining trial time. It contains no required checkout, Supabase login, raw uid/chat ID, or client-derived deadline.
3. GREEN: move the existing `paymentLink()` implementation unchanged into `lib/payment-link.js`, then reuse it from panel and later Telegram delivery. Extend the onboarding response allowlist and render branch; use the existing Calendar transport for the next-event preview and degrade to a truthful no-event state if the read fails.
4. Run focused panel/auth/billing tests and mutation-check removal of the server deadline and Stripe host validation.
5. Commit: `feat(life-manager): show value before checkout`.

## Task 13C: Admit only paid, active-trial, or comp tenants to effects

**Files:** Modify `lib/user-selector.js`; test `lib/user-selector.test.js` and existing scheduler isolation tests.

1. RED: paid enters, active trial enters, active global comp enters, and expired unpaid enters none of the batch or uid selectors. Phone remains irrelevant to cohort membership.
2. RED: an exact deadline is expired; one millisecond before it is active. Invalid/missing deadline fails closed.
3. GREEN: extend the single `schedulerCohortFilter` SSOT to the PostgREST equivalent of `paid OR trial_expires_at > now`, while the existing comp window removes only that entitlement predicate.
4. Run selector, reminder, travel, wake, and daily-preflight tests. Mutation-check the strict `>` boundary and both selector call sites.
5. Commit: `feat(life-manager): admit active trial tenants`.

## Task 13D: Send one durable upgrade message after expiry

**Files:** Modify `lib/telegram-onboard.js`; test `lib/telegram-onboard.test.js`. Reuse `claimTravel`/`unclaimTravel` from `lib/travel.js` and the shared validator from `lib/payment-link.js` without changing their contracts.

1. RED: an expired unpaid core-ready tenant receives one upgrade Telegram containing the validated tenant-scoped Stripe link; replay sends zero.
2. RED: paid, active-trial, incomplete, notifications-disabled, or Telegram-unbound tenants receive zero. A Telegram failure or missing message ID releases the claim for retry.
3. GREEN: reuse the existing two-minute onboarding owner. Claim `lm_travel_log` with `event_key = trial_expires_at` and `leg = trial-upgrade` before send; release only failed delivery.
4. Keep ordinary onboarding nudges unchanged and remove the legacy pay-stage prompt for active-trial users.
5. Run Telegram onboarding, atomic dedupe, panel, billing, and scheduler cohort tests. Mutation-check claim-before-send and failed-send release.
6. Commit: `feat(life-manager): send one trial upgrade`.

## Task 14: Release, real-user proof, and replay-zero

1. Run the focused groups from the design spec, then full `npm test` in a clean dependency environment. The current worktree's partial `node_modules` is not full-suite evidence.
2. Run `git diff --check`, dependency/lockfile diff, branch secret scan, and added-PII scan. Production code must not add OpenClawMU/Hermes or touch `deploy/local`.
3. Fresh Sol review exact commits for Task 12 and Tasks 13A–13D. Critical/High must be zero before merge.
4. Merge through a PR, read back the GitHub Deployment and Railway `/health` exact SHA, and prove it contains every owning commit.
5. A separate real Telegram actor scans the public QR and completes Calendar, home, notifications, phone/no-phone, call opt-in/skip, and trial grant without Google/Supabase browser login.
6. Create one new future controlled physical event after deployment. Read back travel event ID, Telnyx T-10/T-5 call/webhook, Telegram route message ID, Supabase claims, and provider route facts.
7. Replay the same tenant/event and prove additional travel block 0, call 0, Telegram 0. Only then delete controlled events with `send-updates none` and verify exact IDs are cancelled.
8. Mark the spec COMPLETE and start friend beta. The OpenClawMU/Hermes sidecar remains a separate post-launch spec.
