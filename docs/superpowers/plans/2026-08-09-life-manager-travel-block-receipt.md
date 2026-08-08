# Life Manager iOS — real Travel block receipt implementation plan

## Goal

Make mobile analysis create exactly one real outbound `[Travel]` event in the authenticated user's primary Google Calendar, prove it by exact provider read-back, expose an honest localized chat receipt, and make the receipt assertable in the English/Japanese Maestro demo.

This plan begins from `feat/lm-ios-integration-final` after the real Composio OAuth repair. A route card, fixture, mock provider, local-only event, or successful HTTP create without read-back is not completion.

## Frozen provider decision

Composio's normal `GOOGLECALENDAR_CREATE_EVENT` does not accept a caller-specified Google event ID in either the configured base tool version or the latest inspected version. Marker/list recovery alone is not strict exactly-once under concurrent or delayed read-back.

Use Composio Proxy Execute with the exact stored `connected_account_id` to call Google Calendar directly:

- `GET /calendar/v3/calendars/primary/events/{provider_event_id}` before every create attempt.
- `POST /calendar/v3/calendars/primary/events` with a deterministic caller-generated `id`.
- After POST 2xx, timeout, 5xx, or 409, repeat the exact GET.
- Confirm only when ID, private marker, and canonical payload hash match.

`provider_event_id = "lm" + hex(HMAC-SHA256(server_secret, uid + NUL + calendar_id + NUL + source_event_id + NUL + leg))`.

The ID and marker contain no title, address, email, account ID, or other user content. The server secret is required and never returned or logged.

## Slice A — durable exactly-once core

Soft target: 6–10 production/test files, 350–550 changed LOC. If the migration and adapter exceed this target, keep the SQL/RPC and provider adapter in separate commits but do not weaken the state machine.

Owned files:

- new `apps/life-manager/migrations/2026-08-09-lm-travel-block-state.sql`
- new `apps/life-manager/lib/mobile-travel-block.js`
- `apps/life-manager/lib/transport/calendar-composio.js`
- `apps/life-manager/lib/mobile-store.js`
- new `apps/life-manager/test/mobile-travel-block.test.js`
- affected migration/store/transport contract tests

Migration rules:

- Preserve `UNIQUE(uid,event_key,leg)`.
- Add `status`, `calendar_id`, `analysis_key`, `payload_hash`, `marker`, `provider_event_id`, `provider_etag`, `claim_token`, `claim_worker_id`, `claim_acquired_at`, `lease_expires_at`, `create_started_at`, `provider_observed_at`, `confirmed_at`, `attempt_count`, `last_error_code`, and `updated_at`.
- Existing rows become `legacy_terminal`; they are never recreated because their provider state cannot be proven.
- Add partial unique indexes for `(uid, calendar_id, provider_event_id)` and `(uid, calendar_id, marker)`, plus `(status, lease_expires_at)`.
- Add service-role-only RPCs: `claim_lm_travel_block`, `mark_lm_travel_create_started`, `confirm_lm_travel_block`, `release_lm_travel_claim`, and `block_lm_travel_collision`.
- RPCs use row locking and claim-token fencing. Active leases return busy. Stale leases rotate token. A stale worker cannot confirm or release a newer claim.
- A semantic row with the same payload and another analysis key reuses the operation. A different payload returns `analysis_conflict` and causes zero provider writes.

Provider algorithm:

1. Claim the semantic `(uid,event_key,leg)` operation.
2. Exact GET the deterministic event ID.
3. If GET matches ID, marker, and payload hash, confirm without create.
4. If GET is 404, atomically mark `creating`; only then POST the deterministic event.
5. After every POST outcome, exact GET again.
6. Matching GET confirms; 409 plus a different marker/payload becomes `blocked_collision`; unresolved GET releases only the lease and preserves `creating` for recovery.
7. 403, 429, or 5xx from the initial GET causes zero create calls.

Required RED/GREEN tests:

- deterministic ID stability, allowed alphabet/length, and tuple separation;
- two concurrent workers produce one claim token and one provider create;
- stale reclaim rotates the token and rejects stale confirm/release;
- crash before create recovers to one create;
- crash after provider success recovers with GET and zero additional create;
- timeout and 409 converge through GET;
- mismatched 409 becomes collision and never generates another ID;
- different analysis key/same payload reuses one operation; different payload conflicts;
- go/return and different source events remain independent;
- provider side effect is unreachable before `mark_create_started` succeeds;
- provider 2xx without exact read-back never becomes success;
- pre-migration rows remain terminal and are not recreated;
- raw provider/account/user content does not enter claim/error logs.

## Slice B — mobile analysis and semantic outbox

Soft target: 5–8 production/test files, 250–400 changed LOC.

Owned files:

- `apps/life-manager/lib/mobile-analysis.js`
- `apps/life-manager/lib/mobile-outbox.js`
- `apps/life-manager/lib/mobile-localization.js`
- mobile contract/fixture files
- analysis, localization, semantic-outbox, DAILY-regression, and runtime-contract tests

Contract:

- Keep `chat.route_ready` for the route card.
- Append `chat.travel_block_confirmed` only after provider GET confirmation.
- Append `chat.travel_block_not_added` for `provider_write_failed`, `provider_readback_failed`, `claim_pending`, `budget_denied`, `analysis_conflict`, or `provider_collision`.
- Project a public `semanticKey`; never expose provider owner, connected account ID, claim token, internal idempotency key, or server marker.
- Success args include bounded facts: `status=created|existing`, source event ID, provider event ID, calendar=`primary`, leg, block start/end, timezone, `verification=provider_readback`, and verified timestamp. Event title/location remain `user_content`.
- English and Japanese system copy remain script-clean; user content stays unchanged.
- Existing web DAILY cohort selection is unchanged.

Required RED/GREEN tests:

- `paid=false` and `phone=null` analysis still performs the Calendar operation;
- exact stored Composio owner/account reaches both GET and POST;
- route-ready plus confirmed receipt are durable, ordered, cursor-stable, and deduplicated;
- every failure reason emits no confirmed receipt;
- locale switch re-projects both new semantic keys without duplication;
- existing DAILY create path and late-approval tests remain green.

## Slice C — native receipt UI and Maestro contract

Soft target: 4–7 files, 100–220 changed LOC.

Owned files:

- `ChatMessage.swift`
- `ChatView.swift`
- fixture decoding/presentation tests
- `apps/life-manager-ios/maestro/**`

Contract:

- Decode optional `semanticKey` without changing message ID/cursor behavior.
- Success accessibility ID: `calendar.travelBlock.confirmed.<message-id>`.
- Failure accessibility ID: `calendar.travelBlock.notAdded.<message-id>`.
- No new screen is required; use the existing system bubble and localized copy.
- English/Japanese onboarding flows remain executable. The separate pre-authorized flow may consume the provider-confirmed message ID for deterministic recording.
- Static harness parsing MUST ignore comments so comment-only IDs cannot pass.

Required tests: fixture hashes/decoding, semantic ID mapping, EN/JA localization, full 114+ iOS suite, Maestro static harness, and syntax for every flow.

## Slice D — isolated staging proof

1. Fresh review the integrated diff once. VCSDD and Codex Review are prohibited.
2. Apply the follow-up migration only to the isolated Supabase staging project and read back columns, indexes, RPCs, and service-role-only grants.
3. Deploy only Railway `staging/life-call-staging`; production phone/email/Telegram credentials remain absent.
4. Re-run the exact pre-authorization gate immediately before seeding: the intersection of ACTIVE Google Calendar status, selected primary identity hash, current auth config, and expected provider owner MUST contain exactly one account. Identity-only matching is insufficient and MUST fail closed.
5. Pin that exact owner/account to a newly generated opaque staging-only LM user through `link_lm_mobile_calendar_identity`. Copy no production profile, event, session, or DB row. Seed only demo name/home/locale/timezone, `phone=null`, `calls_enabled=false`, and `paid=false`.
6. Before any provider write, prove the v3.1 exact account GET and primary Calendar read succeed, the mapping join count is one, the source event exists exactly once with a location, and production DB fingerprints/counts are unchanged.
7. Use the real pre-authorized Google Calendar connection with that location-bearing future source event.
8. Call mobile analysis and read chat until both route and provider-confirmed travel IDs appear.
9. Exact GET the deterministic Google event and match provider ID, marker, summary prefix, start/end, timezone, and payload hash.
10. Repeat the same idempotency key, then a new analysis key. Prove one provider event, one semantic claim, and one confirmed outbox receipt.
11. Exercise crash-before-create, crash-after-create, timeout, 409-match, and 409-collision in isolated provider/test seams before declaring exactly-once.
12. Run English/Japanese Maestro and record MP4 only after the provider receipt exists.
13. Cleanup deletes the exact provider event ID and staging DB rows only. It MUST NOT call mobile `/account`, disconnect, disable, revoke, or delete the shared Composio account.

## Stop conditions

- Google passkey/consent may remain a manual external authentication boundary, but it cannot be replaced by a mock connection.
- App Store Connect/TestFlight upload waits for the repaired signed archive, real provider video, and the user's TestFlight trial.
- Any provider result that cannot be read back is an explicit failure, not a success receipt.
