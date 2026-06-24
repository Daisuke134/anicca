# HARD-3 — Stripe lifecycle = billing source of truth (Life Manager / apps/life-call)

Status: SPEC (2026-06-24). Part of `2026-06-21-life-manager-LAUNCH-ORDER.md` item 4. Builder = main agent
(me); verifier = fresh `vcsdd:vcsdd-adversary`. NO-MOCK E2E with Stripe CLI `stripe listen`/`trigger`.

## 0. Why
Life Manager is a pooled multi-tenant web SaaS ($20/mo). The sweeper (HARD-2) calls only users where
`lm_users.paid=is.true` (`scheduler.js:42`). Today `paid` has NO writer wired to billing. HARD-3 makes
**Stripe the single source of truth for `paid`**: a verified, idempotent webhook drives provision /
suspend / deprovision. apps/api's old Stripe was removed in v1.5.0 (RevenueCat for iOS); this is a NEW,
separate Stripe integration for the life-call web SaaS — do not touch the iOS/RevenueCat path.

## 1. BP (cited — Stripe official docs)
Source: https://docs.stripe.com/billing/subscriptions/webhooks (Firecrawl 2026-06-24).
- **Source of truth = the subscription `status`, not individual events.** "Make sure that your integration
  properly monitors and handles transitions between the subscription statuses." Statuses:
  - `trialing`, `active` → "you can safely provision your product" → **paid=true**.
  - `past_due` → "notify the customer directly and ask them to update their payment details" → keep access
    during grace (Stripe keeps retrying) + **dunning notice**; do NOT revoke yet.
  - `canceled`, `unpaid`, `incomplete_expired` → "revoke access to your product" → **paid=false**.
  - `incomplete` → not yet paid → **paid=false** (no access until first payment).
- **Events to handle**: `checkout.session.completed` (link customer↔uid + first provision),
  `customer.subscription.created|updated|deleted`, `invoice.paid`, `invoice.payment_failed` (dunning).
- **Verify signature**: `stripe.webhooks.constructEvent(rawBody, sig, endpointSecret)` — "verify that
  incoming events are from Stripe." Invalid signature → reject, do not process.
- **Idempotency**: Stripe retries deliver duplicates and can arrive **out of order**. Dedup by `event.id`.
  Because order isn't guaranteed, on each subscription event the handler reads `status` from the event's
  `data.object` (the status at event time) AND guards staleness with `current_period_end` /
  `subscription.id` so a late-arriving older event can't downgrade a newer state.

## 2. Data model (new migration `2026-06-24-hard3-stripe-billing.sql`)
- `lm_users` add columns (all nullable, default-safe):
  - `stripe_customer_id text` (unique), `stripe_subscription_id text`,
  - `plan_status text` (mirrors Stripe subscription.status: trialing|active|past_due|canceled|unpaid|incomplete|incomplete_expired|null),
  - `current_period_end timestamptz` (staleness guard).
  - `paid boolean` ALREADY EXISTS — remains the entitlement gate the sweeper reads. Webhook is its ONLY writer.
- `lm_stripe_events` (idempotency ledger): `event_id text PRIMARY KEY`, `type text`, `received_at timestamptz default now()`.
  RLS enabled (service-role only). Claim = INSERT; 23505 unique-violation (409) = already processed → skip.

## 3. Endpoint (apps/life-call/server.js — raw http, like /api/inngest)
- `POST /api/stripe/webhook`:
  1. Read RAW body (constructEvent needs the exact bytes — no JSON.parse first).
  2. `constructEvent(raw, req.headers['stripe-signature'], STRIPE_WEBHOOK_SECRET)`. Fail → 400, no side effect.
  3. **Fail-closed** (like inngestServeAllowed): if NOT dev and `STRIPE_WEBHOOK_SECRET` missing → 503.
  4. Claim `event.id` in `lm_stripe_events` (INSERT). 409 → return 200 (already processed, idempotent).
  5. Dispatch by `event.type` → `applyBilling(...)` (pure-ish: computes the target lm_users patch).
  6. Unknown type → 200 ack, no-op.
  7. Any DB/throw after claim → 500 so Stripe retries (and the claim is rolled back / re-claimable: claim
     AFTER signature+parse but the side-effecting write must be idempotent; on failure delete the claim so
     the retry re-processes — claim-then-unclaim-on-failure, mirroring C-H1 `claimAsk`/`unclaimAsk`).

## 4. State machine — `lib/billing.js` (pure `entitlementFor(status) → {paid, plan_status}`)
| Stripe subscription.status | paid | action |
|---|---|---|
| `trialing`, `active` | true | PROVISION (sweeper now calls them) |
| `past_due` | true | keep access (grace) + send dunning notice (Telegram else email) |
| `incomplete` | false | not yet active |
| `canceled`, `unpaid`, `incomplete_expired` | false | DEPROVISION (sweeper stops) |
| (unknown/missing) | false | fail-safe: no access |
- `entitlementFor` is a PURE function (the testable core; NO hardcoded judgment — it's a fixed Stripe
  state→entitlement table, not an LLM decision, so deterministic code is correct here per the agent rules).
- The customer↔uid mapping: `checkout.session.completed` carries `client_reference_id` (= our uid) and
  `customer`; store both. Subsequent subscription events arrive keyed by `customer` → look up the uid by
  `stripe_customer_id`. If no row maps (orphan event) → log + 200 (can't provision an unknown user).
- Staleness guard: apply a subscription event only if its `current_period_end` ≥ the stored one OR the
  subscription id differs (new sub) — protects against out-of-order delivery downgrading a fresher state.

## 5. Provision / suspend / deprovision (the writes)
- PROVISION: `lm_users` set `paid=true, plan_status, stripe_customer_id, stripe_subscription_id, current_period_end`.
- SUSPEND (past_due): `paid=true, plan_status='past_due'` + dunning notice (reuse `lib/notify.js` channel).
- DEPROVISION: `paid=false, plan_status=<canceled|unpaid|...>`. Sweeper's `paid=is.true` filter excludes them
  on the next pass — no extra code in the scheduler (entitlement is read-through).

## 6. Requirements (EARS) — append to behavioral-spec.md §G
- REQ-35 The system SHALL expose `POST /api/stripe/webhook` that verifies the Stripe signature via
  `constructEvent`; an invalid/missing signature SHALL be rejected (400) with NO billing side effect.
- REQ-36 The webhook SHALL be idempotent: each `event.id` is processed at most once (claim in
  `lm_stripe_events`; a duplicate delivery returns 200 without re-applying).
- REQ-37 On `checkout.session.completed` the system SHALL link `stripe_customer_id` + `stripe_subscription_id`
  to the uid from `client_reference_id` and provision per the subscription status.
- REQ-38 On `customer.subscription.created|updated|deleted` the system SHALL set `paid`/`plan_status` from
  the subscription `status` per the §4 table (active/trialing→paid; canceled/unpaid/incomplete*→unpaid).
- REQ-39 The system SHALL apply a subscription event only when it is not stale (its `current_period_end` ≥
  the stored value, or a different subscription id), so out-of-order deliveries cannot downgrade fresher state.
- REQ-40 WHEN a subscription becomes `past_due`, the system SHALL keep access (grace) and send ONE dunning
  notice via the user's connected channel (Telegram else email); it SHALL NOT revoke on past_due.
- REQ-41 The `/api/stripe/webhook` route SHALL FAIL CLOSED in production (no dev flag) when
  `STRIPE_WEBHOOK_SECRET` is absent (503), mirroring the Inngest serve guard.
- REQ-42 `paid` SHALL have exactly ONE writer (the Stripe webhook); the sweeper SHALL remain its only reader.

## 7. Verification (no-mock)
- Unit: `entitlementFor` table (every status), claim/unclaim idempotency, staleness guard, signature-fail
  rejection, fail-closed prod guard, orphan-customer no-op.
- E2E (Stripe CLI, test mode): `stripe listen --forward-to localhost:PORT/api/stripe/webhook` +
  `stripe trigger checkout.session.completed` / `customer.subscription.updated` /
  `customer.subscription.deleted` → assert the lm_users row flips paid true→…→false in the test DB, and a
  duplicate redelivery (`stripe events resend <id>`) does NOT double-apply. Then fresh adversary gate.

## 8. Out of scope (later)
- The Stripe Checkout PAGE / pricing object creation (that's the buy flow, D-1/D-2). HARD-3 is the LIFECYCLE
  (webhook→entitlement). A test price/checkout is used only to drive E2E.
- Stripe native Entitlements API (`entitlements.active_entitlement_summary.updated`) — the status→paid map is
  the proven, simpler equivalent; can adopt Entitlements later without changing the sweeper.

## 9. Files
- NEW: `apps/life-call/lib/billing.js`, `apps/life-call/lib/billing.test.js`,
  `apps/life-call/migrations/2026-06-24-hard3-stripe-billing.sql`.
- EDIT: `apps/life-call/server.js` (mount `/api/stripe/webhook` + fail-closed guard),
  `apps/life-call/package.json` (add `stripe` dep), behavioral-spec.md (§G REQ-35..42).
- Branch: `feature/hard3-stripe` → PR → main (matching HARD-1/HARD-2).

## 10. Adversary findings resolved (2026-06-24)
- **FIND-001 (dual-writer, critical)** — discovery: a PRE-EXISTING `apps/landing/netlify/functions/lm-stripe-webhook.js`
  was the LIVE Stripe-registered writer of `lm_users.paid` (verified-live 2026-06-21), subscribed to only 2
  events (checkout.session.completed + customer.subscription.deleted) — so it could never do past_due/grace/
  dunning, and it wrote bare `paid` with no customer_id/plan_status/idempotency/staleness. RESOLUTION: life-call
  is the billing home (it owns the data + the sweeper = architectural BP). The landing stopgap is DELETED →
  single writer = life-call `applyBilling`. (Other repo "paid" refs are readers: scheduler.js `paid=is.true`
  filter, telegram-reply.js select; landing `webhook.js` writes a different product's `subscribers`/`buyers`.)
- **FIND-002 (immediate-cancel dropped, critical)** — staleness re-keyed from `current_period_end` → the
  EVENT's `created` (stored `stripe_event_at`). An immediate cancel (lower period_end, later created) now applies.
- **FIND-003** — checkout gates on `payment_status` ('paid'/'no_payment_required' → provision; else link paid=false).
- **FIND-005** — `readRawBody` returns a Buffer (no utf8 chunk-split corruption) for constructEvent.
- **FIND-004** — `applyBilling` now has unit tests (checkout paid/unpaid, sub provision/deprovision/stale/orphan,
  past_due+dunning, unknown-type, patch-failure-throws). FIND-006 — unclaim-fail logs a RECONCILE marker.
- Verified: 98 unit tests + no-mock E2E 11/11 (incl. the FIND-002 immediate-cancel case) + fail-closed 503.

## 11. LIVE cutover runbook (deploy step, AFTER merge — touches live Stripe config; only 1 paid user, link still sandbox)
1. Merge HARD-3 → main → Railway auto-deploys life-call (route `/api/stripe/webhook` goes live at
   `https://life-call-production.up.railway.app`). Netlify redeploys landing without the stopgap webhook.
2. Create a Stripe webhook endpoint → `https://life-call-production.up.railway.app/api/stripe/webhook` with
   events: checkout.session.completed, customer.subscription.created|updated|deleted, invoice.payment_failed.
   Set its signing secret as `STRIPE_WEBHOOK_SECRET` on life-call Railway (live) — life-call serves the route
   only when the secret is present (REQ-41). Verify a Stripe test event delivers 200.
3. Delete the OLD Stripe endpoint (`aniccaai.com/.netlify/functions/lm-stripe-webhook`) so no duplicate.
4. E2E: a real $20/mo checkout (sandbox first, then live link …2880v on go-live) → life-call webhook → paid=true.
