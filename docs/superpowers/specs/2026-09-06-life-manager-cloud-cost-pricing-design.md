# Life Manager Cloud cost・pricing・legacy cleanup design

status: COST TRACK ACTIVE — implemented independently, one atom at a time
owner: Dais / Life Manager Cloud
scope: provider cost control, tenant usage metering, Stripe packaging decision, Cloud daily-runtime cleanup

## 0. Ordering and exclusions

- The remote Cloud product agent owns `CLOUD-01` through `CLOUD-08` in
  `2026-08-28-life-manager-cloud-telegram-product-ux-design.md`. This cost track runs independently
  and does not edit, reorder, or wait for that checklist. If the Cloud agent requests verification,
  this track may inspect its tests and evidence read-only without taking over its implementation.
- Do not use ElizaOS, replace the Life Manager runtime, stop Telegram/Calendar/routing, or modify
  local loops and Alpaca worktrees.
- Do not change Stripe prices before per-tenant production usage is measured. Existing Stripe remains
  the only payment authority.
- A file is not deleted merely because its name says legacy. Require production reference zero,
  registry/owner zero, tests proving the replacement, and provider replay-zero where effects exist.

## 1. Measured incident baseline

Google Cloud billing account `017949-09509F-6A3FB6` reports July 2026 subtotal JPY 28,568 and
August subtotal JPY 78,306: +JPY 49,738, +174.1%, 2.741x. August service totals were Geocoding
JPY 40,095, Gemini API JPY 13,444, Directions JPY 9,549, Routes JPY 7,924, Places JPY 5,054,
and Vertex AI JPY 2,227.

The dominant Maps credential was `lateness-directions`. Monitoring attributed approximately 21,524
Directions 4xx responses and 22,751 Geocoding 4xx responses to it in August. Railway `life-call`
boot logs showed the standalone scheduler owner and all daily loops active. GCP Cloud Run and Cloud
Scheduler were not competing owners. Therefore the incident was repeated paid failure work in the
single active Railway scheduler, not legitimate one-user demand and not a second Cloud deployment.

The billing account now has a non-blocking JPY 35,000 monthly budget with current-spend alerts at
50%, 75%, 90%, and 100%. Provider quotas remain unchanged because a blind cap can remove required
Calendar travel behavior.

## 2. Exact code findings

1. `apps/life-manager/migrations/2026-07-04-lm-route-cache.sql` creates `lm_route_cache`, but the
   production construction in `apps/life-manager/lib/travel.js` supplies only `new Map()` to
   `makeRouteCache`. No production code reads or writes `lm_route_cache`. A process restart loses all
   accepted route cache entries.
2. `apps/life-manager/lib/route-cache.js` stores only non-null results. A provider 4xx, timeout, or
   no-route result returns null and is retried on the next eligible tick. This matches the measured
   paid-failure pattern.
3. The 30-minute travel loop and 60-second Telegram reminder loop both use `directionsRoute`; without
   a durable store they cannot reliably reuse one accepted or failed result across restarts/owners.
4. `scheduler.js` and `inngest/functions.js` are not two independent business implementations:
   Inngest imports the per-user functions from `scheduler.js`, and `maybe-start-loops.js` owns their
   mutual-exclusion predicate. Retain both until one deployment mode is formally retired.
5. `routesDriveMinutes` / `directionsMinutesGoogle` are no longer on the default production fallback,
   consistent with Routes charges disappearing after the free-transit-first release. They remain
   explicit compatibility/test seams; assess deletion only after `CLOUD-02` timing acceptance.

## 3. Pricing decision before Stripe mutation

The launch recommendation is a hybrid subscription, not raw provider-cost pass-through:

| Plan | Monthly price | Included product usage | Overage behavior |
|---|---:|---|---|
| Free | JPY 0 | Calendar connection, settings, cached route display, up to 20 successful managed actions/month, no optional phone | Keep read/settings/cached results available; ask to upgrade for new paid actions |
| Plus | **JPY 4,980** | Core daily Telegram/Calendar automation and 500 successful managed actions/month | Offer prepaid 100-action pack for JPY 980; never count internal retries or provider failures |
| Pro | JPY 9,800 | 2,000 successful managed actions, optional phone allowance, priority/high-cost AI | Additional prepaid packs; explicit warning before high-cost media/agent work |

`successful managed action` is the customer-facing value metric. Internal polling, cache hits,
retries, 4xx/5xx, duplicate suppression, and provider reconciliation cost zero customer credits.
Track actual vendor cost separately for margin control.

JPY 4,980 is provisional until the beta records two to four weeks of normalized per-tenant cost. The
release gate is p95 monthly direct cost at or below JPY 1,000 for Plus (at least 80% gross margin before
support and fixed overhead). If it exceeds that boundary, reduce provider waste or lower included
high-cost actions; do not silently degrade Calendar, Telegram, or cached daily behavior.

## 4. Free operation boundary

Everything cannot be guaranteed free while Life Manager pays commercial LLM, Maps, telephone, hosting,
and payment fees. A sustainable free tier is possible by keeping its marginal paid work bounded:

- use Google Maps monthly free SKU caps only as a shared safety buffer, never as an unlimited promise;
- free transit first, durable accepted-route cache, and bounded negative cache before Google fallback;
- deterministic code before LLM and small models before expensive models;
- no optional phone or video generation in Free;
- cached/read/settings behavior remains available after the action allowance is exhausted;
- referral/sponsor credits can fund extra actions, but never hide provider cost or promise permanent
  unlimited use.

## 5. OSS decision

Reviewed current source from `openmeterio/openmeter`, `BerriAI/litellm`, and `unkeyed/unkey`.

- OpenMeter provides event metering, entitlements, credits, and billing, but its full stack is beta and
  duplicates existing Supabase/Stripe authority. Do not add it for launch.
- LiteLLM provides LLM virtual keys, spend tracking, budgets, and caching, but it cannot meter Maps,
  Telegram, or telephone value consistently. Do not add an AI gateway before the existing call sites
  have one usage contract.
- Unkey provides API-key analytics and durable rate limits, but Life Manager's public product is
  Telegram/tenant based, not a customer API. Do not add it now.
- Reuse the event/entitlement concepts: append a tenant-scoped usage event to the existing Supabase
  ledger and report accepted aggregate usage to Stripe's official usage meter. No new billing engine.

Sources:

- Stripe usage-based billing: https://docs.stripe.com/billing/subscriptions/usage-based
- Google Maps SKU pricing/free caps: https://developers.google.com/maps/billing-and-pricing/pricing
- Gemini API pricing: https://ai.google.dev/gemini-api/docs/pricing
- OpenMeter: https://github.com/openmeterio/openmeter
- LiteLLM: https://github.com/BerriAI/litellm
- Unkey: https://github.com/unkeyed/unkey
- Reclaim pricing: https://reclaim.ai/pricing
- Motion pricing: https://www.usemotion.com/pricing
- Sunsama pricing: https://www.sunsama.com/pricing

## 6. Ordered TODO owned by this track

This track owns these atoms in the exact order below while the remote Cloud product agent separately
owns `CLOUD-01` through `CLOUD-08`. Finish and integrate one cost atom before starting the next.

1. **COST-01 — observe (DONE):** add one tenant/provider/feature usage-event contract and dashboard
   query; record success, cache hit, failure class, provider units, and estimated direct cost without
   secrets. Integrated by PR #4282. Production RPC readback returned HTTP 200 and 17 natural Maps
   usage events for 2026-09-06 UTC: Directions failure 5 / USD 0.025 estimated, Geocoding failure
   5 / USD 0.025, and Geocoding success 7 / USD 0.035. The estimates are provider list-price
   accounting events, not a replacement for the Google Cloud invoice.
2. **COST-02 — stop paid failure replay (DONE):** wire `lm_route_cache` to production, add bounded
   negative cache for deterministic 4xx/no-route and short backoff for timeout/5xx, and prove a later
   valid route can recover. PRs #4291 and #4298 integrated the durable store and the production-observed
   raw-address fallback gap. Focused route/travel tests passed 135/135; a fresh-process test proves zero
   additional provider calls during the 30-minute deterministic-failure TTL and recovery after expiry.
   Production build `342aaf07f` returned HTTP 200, wrote 4 natural success rows and 5 natural
   `google/no_route` negative rows with TTL 1800 seconds, and the next readback kept paid Directions
   failures at 5 (zero increase). Network/5xx uses a 120-second backoff. Raw addresses are represented
   only by opaque SHA-256 cache scopes and are not persisted.
3. **COST-03 — one route fact (DONE):** travel block, Telegram reminder, and optional call reuse one
   event/version-scoped route result. Exact event ID、schedule、endpoints、go/return purpose changes
   invalidate it. PR #4419 merged as `d69b21ee5773f4629a15d226008be7095d68cf02`; focused
   current-main route/travel/reminder/wake verification passed 129/129 and Railway health serves that SHA.
4. **COST-04 — owner and spend guard:** prove exactly one Cloud scheduler owner, add tenant/provider
   daily circuit breakers that preserve cached/read/settings behavior, and alert before rejection.
5. **COST-05 — beta unit economics:** run two to four weeks, calculate p50/p95 direct cost per active
   tenant and per successful managed action, then confirm or revise JPY 4,980 before Stripe mutation.
6. **COST-06 — Stripe meter:** map only successful managed actions to the existing Stripe customer,
   add allowance/credit-pack behavior, test duplicate/replay/refund boundaries, then request the
   separately authorized real payment proof.
7. **CLEAN-01 — compatibility retirement:** after `CLOUD-02`, prove whether old Routes Pro helpers and
   legacy Directions compatibility seams have production callers. Delete only zero-reference seams
   and their now-invalid tests/comments.
8. **CLEAN-02 — runtime retirement:** after the chosen Cloud scheduler mode has natural production
   receipts, retire the unused alternate host adapter/registration surface without deleting shared
   per-user business functions.
9. **CLEAN-03 — final census:** run source reference, deployment entrypoint, loop registry, provider
   traffic, migration, and secret-free receipt checks; record retained owners and deletion evidence.

## 7. Acceptance

- Normal Calendar/Telegram/cached daily behavior remains available at every plan boundary.
- One user action produces at most one accepted billable provider result per event version and purpose.
- Deterministic 4xx/no-route repeats produce zero additional paid calls during the negative-cache TTL.
- Internal failures and retries never consume customer allowance or enter Stripe usage.
- Plus p95 direct monthly cost is at most JPY 1,000 before enabling the JPY 4,980 Stripe price.
- No local loop, Alpaca state/worktree, ElizaOS component, or unrelated production route is modified.
