# Connector Eventbrite discovery and eligibility 19E Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development and subagent-driven-development. Luna writes production/tests; Sol reviews, integrates, live-verifies, and updates the SSOT.

**Goal:** Add a fail-closed Eventbrite workflow that discovers canonical Tokyo events, accepts only free/open/in-person candidates in the current 14-day window, applies Calendar conflict filtering, and emits the existing privacy-safe five-count audit.

**Measured sources:** Eventbrite's official [`Tokyo free events`](https://www.eventbrite.com/d/japan--tokyo/free--events/) page exposes 20 `data-testid="search-event"` cards in the measured response. Each exact event anchor carries `data-event-id`, `data-event-location`, `data-event-paid-status`, and a tracked `www.eventbrite.com/e/...` URL; the same event appears through repeated card links and therefore requires canonical query removal plus event-ID dedupe. Measured detail pages expose JSON-LD whose type can be `SocialEvent`, attendance mode is the Schema.org offline/online URL, and offers can be `AggregateOffer` with `lowPrice`, `highPrice`, `priceCurrency`, `availability: "InStock"`, and an exact event URL. The public registration control is `data-testid="conversion-bar-checkout-button"` with exact label `Get tickets`. One measured zero-price listing advertises a paid door price in body copy, so zero JSON-LD alone is not sufficient.

GitHub code search across current Eventbrite listing selectors, JSON-LD `AggregateOffer`, and `data-testid="search-event"` found only broad third-party scrapers; none implements this Connector's canonical identity, free/open, body-price, Calendar, and privacy-audit contracts. Reuse the existing Doorkeeper workflow structure inside this repository instead of importing a scraper or adding a dependency.

**Architecture:** Add one provider-local workflow module and one focused test. Reuse the existing candidate shape, Tokyo-day window logic, exact Calendar overlap/idempotent coverage semantics, safe stage errors, direct-action safe failure, strict parent readback statuses, and five-count audit shape. Do not wire Eventbrite into production routing or click checkout in this slice.

**Estimated change:** 2 new files. Production soft target 220–300 LOC; test soft target 220–320 LOC. If the required production contract exceeds 320 LOC, stop and return a measured split rather than adding abstractions or changing shared files.

## Exact contracts

- Listing URL is exactly `https://www.eventbrite.com/d/japan--tokyo/free--events/`; one owned page and no new target/session.
- Accept only exact HTTPS `www.eventbrite.com/e/<slug>-tickets-<numeric-id>` or `www.eventbrite.com/e/<numeric-id>` paths. Remove query/hash and dedupe by numeric ID. Reject other Eventbrite TLDs/hosts and malformed/mismatched IDs.
- Listing parser reads exact `[data-testid="search-event"]` roots and their `a.event-card-link[data-event-id][href]`; broad `article`, arbitrary anchors, or class-substring fallbacks are forbidden.
- Detail identity requires the JSON-LD event URL and any identifier present to bind to the same canonical URL/event ID. Accept `Event` or `SocialEvent` only.
- Candidate interval must be valid and start within `[Tokyo today, Tokyo today + 14 days)`. Require offline attendance and Tokyo address/location.
- All offer bounds must be numeric zero. Accept `Offer.price == 0` or `AggregateOffer.lowPrice == 0 && highPrice == 0`; require `InStock` in either compact or Schema.org URL form and exact canonical offer URL. Currency is recorded only as evidence of the source and does not turn zero into paid.
- Require exactly one visible exact `Get tickets` control. Reject sold-out/cancelled/waitlist/error markers and any body/control money marker, including door price, participation fee, payment required, yen or currency-symbol amount.
- Calendar blocks unrelated timed overlap and permits only exact Connector idempotent coverage, matching current providers.
- `onDiscoveryAudit` receives only `discovered_count`, `within_window_count`, `eligible_count`, `calendar_free_count`, `selected_count`; no title, URL, event ID, or private data.
- `runDirectAction` returns `{ status: "failed", safe_reason: "eventbrite_direct_requires_harness" }` and performs no click.
- `readProviderState` is strict and fail-closed: exact canonical page/link identity plus one unambiguous completion marker may return `registered`; an exact visible `Get tickets` view with no unsafe marker may return `absent`; everything ambiguous/unsafe returns `unavailable`. No auth, form fill, checkout, cache, evidence, or shared-router changes in this slice.

## Task 1 — RED

1. Add focused fixtures for repeated tracked listing links, exact canonicalization, other-TLD rejection, mismatched ID rejection, `SocialEvent`/`AggregateOffer`, online/non-Tokyo/out-of-window/paid/door-price/sold-out/duplicate-control rejection, Calendar overlap, five-count privacy, direct-action zero-click, and strict readback.
2. Run only the new focused test and record the expected module-not-found or missing-contract RED.

## Task 2 — GREEN

1. Implement the provider-local workflow with no dependency and no shared-file edit.
2. Run the focused test, then adjacent Doorkeeper/Meetup workflow tests, syntax checks, and `git diff --check`.
3. Confirm exact two-file ownership, commit without amend, push the implementation branch, and hand the commit to fresh Sol review.

## Completion gate for this slice

Fresh review reports Critical 0 / Important 0; Sol independently reproduces focused and adjacent GREEN; reviewed code is integrated into the stable Connector branch and pushed. Official wake remains zero until the next production-wiring slice is reviewed.

