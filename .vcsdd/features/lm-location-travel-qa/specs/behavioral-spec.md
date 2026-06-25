# Behavioral Spec — Life Manager location resolution + travel-time blocks (EARS)

Feature: `lm-location-travel-qa` (strict). SUT: apps/life-call `lib/ask.js` (agentResolveLocation, askTick),
`lib/travel.js` (fillTravel, travelDecision, directionsMinutes), `lib/wake-filter.js` (shouldWake),
`scheduler.js` (travelTick 30min, askTickAll 20min). The MODEL judges via prompt+tools — NO hardcoded
regex for judgment. Paid product → must run autonomously for ALL users.

## A. Location classification (agentResolveLocation → online | filled | ask)
- REQ-01 WHEN an event's title names a public landmark and the location field is empty (e.g. "東京スカイ
  ツリーで打ち合わせ"), the system SHALL web-search the landmark and RESOLVE its real address (kind=filled),
  and SHALL NOT ask the user. [the Skytree email bug]
- REQ-02 WHEN the title names a real shop/venue (e.g. "スタバ新宿南口店"), the system SHALL resolve its
  address (filled).
- REQ-03 WHEN the title is a company/office commute (e.g. "MUIT 出社"), the system SHALL resolve the
  company's office building address (filled).
- REQ-04 WHEN the title names a school/institution with a room name (e.g. "[NAIST] 情報科学大講義室"), the
  system SHALL resolve the institution's campus address (filled).
- REQ-05 WHEN the title indicates an online/remote/phone/video event (オンライン/Zoom/Meet/Teams/電話/
  リモート/ビデオ通話), the system SHALL classify it NO-TRAVEL (online) and SHALL NOT create a block or ask.
- REQ-06 WHEN the title is an online meeting with a named person (e.g. "三島さんとオンラインミーティング"),
  the system SHALL classify NO-TRAVEL (online) and SHALL NOT ask where it is.
- REQ-07 WHEN the event is a personal routine with no external venue (Sleep / Running / Meditation /
  remote Day-job), the system SHALL classify NO-TRAVEL (online) and SHALL NOT ask.
- REQ-08 WHEN the title is a vague external activity tied to a person with no findable venue (e.g.
  "Lunch with Mai", "1on1"), the system SHALL classify ASK.
- REQ-09 WHEN the location is one only the user knows (e.g. "おばあちゃんの家"), the system SHALL ASK the
  user via their connected channel (Telegram else email).
- REQ-10 WHEN the location field is already set and geocodable (e.g. "渋谷ヒカリエ"), the system SHALL use
  it directly without re-asking.
- REQ-11 WHEN the location field is a room name or a URL, the system SHALL resolve the real address (filled)
  or, if a URL/online, classify NO-TRAVEL — never route a URL.
- REQ-12 WHEN a venue name is ambiguous, the system SHALL use the user's home city as disambiguation context.
- REQ-13 The system SHALL behave identically for English and Japanese titles.

## B. Travel-time block creation (fillTravel)
- REQ-14 WHEN an event must be travelled to, the system SHALL insert a GO `[Travel] 🚆` block at head-out
  time = event_start − travel_minutes − buffer.
- REQ-15 WHEN an event must be travelled to, the system SHALL ALSO insert a RETURN `[Travel] 🚆` block at
  event_end lasting the travel time back home (venue → home). **[CURRENTLY UNIMPLEMENTED — gap]**
- REQ-16 WHEN the previous event ends ≤90 min before and at a real venue, the origin SHALL be that previous
  venue (back-to-back), else home.
- REQ-17 WHEN the destination is an airport/flight, the buffer SHALL be 60–180 min (not the default 15).
- REQ-18 IF the computed leave time is already in the past, the system SHALL NOT create a block.
- REQ-19 The system SHALL NOT create a second [Travel] block for an event that already has one (dedup).
- REQ-20 WHEN origin == destination (home→home / same-location), the system SHALL NOT create a block.
- REQ-21 The system SHALL fill ALL must-travel events across today + the next 7 days each run.
- REQ-22 The system SHALL compute travel as max(transit, traffic-aware drive) (never-late bias).

## C. Ask channel + reply
- REQ-23 WHEN ASK and the user linked Telegram, the system SHALL ask via Telegram and patch the location
  from the webhook reply.
- REQ-24 WHEN ASK and no Telegram, the system SHALL ask by email and patch the location from the Re: reply.
- REQ-25 The system SHALL re-attempt RESOLVE on every tick (a past ask SHALL NOT permanently block a fill);
  it SHALL dedup only the ask SEND (never email/Telegram the same event twice).
- REQ-26 The system SHALL NOT double-ask an event already asked and awaiting reply.

## D. Determinism (non-functional)
- REQ-27 The SAME event over N runs SHALL yield the SAME classification (online/filled/ask). Target ≥9/10
  stable per case. [bounds the Skytree run-to-run variance — the #1 risk]

## E. Voice call (boundary)
- REQ-28 WHEN a wake call connects, Charon SHALL speak first, address the user by name, in the user's
  language (EN/JA).
- REQ-29 The system SHALL place TWO escalating calls — at T−10 (firm) and T−5 (harsh) before DEPARTURE — until
  the user moves (Dais 2026-06-25: "just call me 10 min before and 5 min before, that's it"; the T−15 call is removed).
- REQ-30 The outbound Charon audio SHALL be audible to the caller (not silent).

## F. Scheduling layer (HARD-2 — Inngest durable scheduler)
- REQ-31 The system SHALL run a durable cron SWEEPER per pass (wake every 1 min, travel every 30 min, ask
  every 20 min) that lists paid users and FAN-OUTS exactly one event per user (`lm/wake.user` etc.), each
  carrying ONLY `{ uid }` (no phone/tokens/PII); the per-user function SHALL re-fetch the row by uid.
- REQ-32 Each per-user function SHALL set Inngest `concurrency: { key: "event.data.uid" }` so two jobs for
  the SAME user run serially (no double-dial/block/ask), while different users run in parallel.
- REQ-33 SINGLE-WRITER: the in-process setInterval loops and the Inngest sweepers SHALL NEVER both write.
  The sweepers SHALL no-op (no fan-out) unless `LIFE_RUN_LOOPS="false"`; when "false" the in-process loops
  are off and the sweepers are the sole writer. Per-user idempotency is additionally guaranteed by the
  C-H1 atomic claims (lm_wake_log / lm_travel_log / lm_ask_log), so any accidental double-run cannot double-act.
- REQ-34 The `/api/inngest` route SHALL FAIL CLOSED: in production (no `INNGEST_DEV=1`) it SHALL refuse to
  serve (HTTP 503) unless `INNGEST_SIGNING_KEY` is set; in dev (`INNGEST_DEV=1`) it serves without a key.

## G. Billing lifecycle (HARD-3 — Stripe = source of truth for lm_users.paid)
- REQ-35 `POST /api/stripe/webhook` SHALL verify the Stripe signature via `constructEvent` over the RAW body;
  an invalid/missing signature SHALL be rejected (400) with NO billing side effect.
- REQ-36 The webhook SHALL be idempotent: each `event.id` is processed at most once (claim in
  `lm_stripe_events`, 201/409); a duplicate delivery returns 200 without re-applying.
- REQ-37 On `checkout.session.completed` the system SHALL link `stripe_customer_id` + `stripe_subscription_id`
  to the uid from `client_reference_id` and provision (paid=true).
- REQ-38 On `customer.subscription.created|updated|deleted` the system SHALL set `paid`/`plan_status` from the
  subscription `status`: `active`/`trialing`/`past_due` → paid=true; `canceled`/`unpaid`/`incomplete`/
  `incomplete_expired` → paid=false. (Stripe BP: source of truth is the status, not the event type.)
- REQ-39 The system SHALL order events by the EVENT's `created` timestamp (stored as `stripe_event_at`): an
  event whose `created` is older than the last applied is stale and SHALL be skipped. `created` (not
  `current_period_end`) is the key — an immediate cancel can carry a LOWER period_end than the prior active
  event, so a period_end key would wrongly drop the downgrade and keep a canceled user paid (FIND-002).
- REQ-40 WHEN a subscription becomes `past_due`, the system SHALL keep access (grace) and send ONE dunning
  notice via the connected channel (Telegram else logged/email); it SHALL NOT revoke on past_due.
- REQ-41 The `/api/stripe/webhook` route SHALL FAIL CLOSED in production (no `STRIPE_DEV=1`) when
  `STRIPE_WEBHOOK_SECRET` is absent (503), mirroring the Inngest serve guard.
- REQ-42 `lm_users.paid` SHALL have exactly ONE writer (the Stripe webhook) and the HARD-2 sweeper SHALL
  remain its only reader; on a write failure the claim is released (unclaim) so Stripe's redelivery re-applies.

## H. Per-tenant isolation (HARD-4)
- REQ-43 A failure while processing ONE tenant SHALL NOT prevent the other tenants from being processed in the
  same tick. The in-process loops (tick/travelTick/askTickAll) route each per-user call through
  `forEachUserSafe` (catch + per-uid log + continue), which ALSO applies a per-user TIMEOUT (default 90s) so a
  HANG — not just a throw/rejection — is bounded and cannot stall the others (FIND-002). A malformed user row
  (missing uid) SHALL be contained, not fatal. The production Inngest path additionally isolates each user as
  a separate, parallel function run. Tests SHALL drive the PUBLIC loops (not just the helper) to prove routing.
- REQ-44 Per-user data SHALL be keyed per tenant (Composio connected account by uid; `accountId =
  u.gmail_account_id`; unipile email cache by per-user accountId). App-level creds (COMPOSIO_API_KEY,
  unipile/telegram tokens) are shared infra; NO per-user secret is stored or shared mutably across tenants.

## I. Location memory — C3 ask→remember (PHASE C / PC-1)
- REQ-45 WHEN an event needs a location and a NON-STALE remembered place exists for its phrase (lm_user_places,
  `updated_at` within the TTL = `LM_PLACE_TTL_DAYS`, default 90), the system SHALL autofill from memory and SHALL
  NOT ask the user OR call the resolution model. A memory OLDER than the TTL is ignored → the event is asked
  again → the answer upserts/refreshes it (FIND-002: a permanent pin would make a changed venue un-correctable).
- REQ-46 WHEN the user answers a location ask (Telegram reply OR email reply), the system SHALL REMEMBER
  (uid, phrase, address) so a future event with the SAME phrase autofills without asking again.
- REQ-47 The recall/remember phrase key SHALL be a DETERMINISTIC normalization of the event summary
  (lowercase, collapsed whitespace, trim) — bookkeeping, not a judgment. Memory is keyed per (uid, phrase)
  and upserts (no duplicate rows per user+phrase).
- REQ-48 (C4 determinism) The SAME event SHALL classify into the spec's expected kind ≥9/10 over N≥10 runs
  (temperature 0); `scripts/phase-c-eval.js` (real Gemini, no-mock) measures this per canonical case at N=10,
  threshold ≥90%. EXCEPTION — a GENUINELY ambiguous solo activity that could be home-based OR at a venue (a
  bare "Morning run": run from home = no-travel, run at a track = travel) may defensibly hedge to ASK; such a
  case is marked `soft` (its real % is reported but does not gate), because PC-1 memory makes a single ask
  harmless (asked once → remembered → never repeated). The CLEAR routines (Sleep, 瞑想), all calls/online, all
  filled, and all ask cases remain STRICT ≥90%.
- REQ-49 The RETURN [Travel] block (REQ-15) is implemented (`returnDecision` + travel-return tests) — the
  earlier "UNIMPLEMENTED gap" note is closed.
