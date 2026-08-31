# TECH PLAY Google Calendar Canonical URL Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Superpowers test-driven-development. Sol owns plan/review/verification/commit; Luna owns the exact two Calendar transport files.

**Goal:** Allow a successfully applied TECH PLAY event to be written to Google Calendar with its exact canonical source URL and fixed source title.

**Architecture:** Extend only `connectorCanonicalUrl`. Accept exactly `https://techplay.jp/event/<positive ID>` and return source title `TECH PLAY`. Preserve the raw-equals-canonical gate so credentials, port, HTTP, query, fragment, trailing slash, case drift, and non-event paths are rejected before the injected `gog` runner executes.

**Files / soft target:**

- Modify `apps/mr-bot/lib/transport/calendar-gog.js` — about 7–12 LOC.
- Modify `apps/mr-bot/lib/transport/transport-gog.test.js` — about 30–55 LOC.

## Grounding

- Google Calendar Events insert: <https://developers.google.com/workspace/calendar/api/v3/reference/events/insert> — Calendar creation accepts event metadata; the local `gog` adapter already sends source URL/title.
- English search for canonical Calendar source URLs found no closer implementation than this repository's transport.
- Japanese search for event source URLs found no reusable stricter parser; existing provider branches are the authoritative pattern.
- Existing Doorkeeper/Eventbrite positive and reject-before-run tests define the exact local contract.

## Contract

- [x] RED: exact TECH PLAY canonical URL is rejected.
- [x] Accept only `https://techplay.jp/event/<positive ID>` and emit fixed source title `TECH PLAY`.
- [x] Send the same exact URL as description and source URL with the existing idempotency property.
- [x] Reject HTTP, host/case drift, credentials, explicit port, zero/non-numeric ID, query, fragment, trailing slash, join/confirm/list/search/non-event paths before `gog` run.
- [x] Existing providers and malformed-input guards remain unchanged.
- [x] Run focused/full transport tests, syntax, diff check, mutation proof, and fresh Sol review.
- [x] Do not change generic canonicalization, evidence chain/store, factory/router, native order, launchd, or perform a real Calendar mutation.
