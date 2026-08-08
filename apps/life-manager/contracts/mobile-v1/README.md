# Life Manager mobile v1 — Gate 3 contract

These JSON files are the frozen decoder contract for the native demo and authenticated mobile
backend. They are fixtures for Node and Swift contract tests; they are not runtime seed data and
must never be used as a production success fallback.

## Surface

The router base path is `/api/mobile/v1`. The active private demo restores a pre-connected
Calendar session and starts at `GET /bootstrap`; it has no user-facing OAuth screen or paywall.
The session start/exchange shapes remain frozen for the authenticated backend boundary and future
reconnection work.

| Method | Path | Auth | Idempotency | Purpose |
| --- | --- | --- | --- | --- |
| POST | `/session/calendar/start` | none | required | Create one-use Calendar consent state |
| POST | `/session/exchange` | none | required | Exchange a validated callback for mobile tokens |
| POST | `/session/refresh` | refresh token | required | Rotate the refresh family |
| DELETE | `/session` | bearer | required | Revoke the current mobile session |
| GET | `/bootstrap` | bearer | n/a | Read server-derived user, Calendar, locale, and analysis state |
| PATCH | `/profile` | bearer | required | Save allowlisted profile, phone, call, locale, and timezone fields |
| POST | `/analysis` | bearer | required | Run `initial` or `manual_refresh` next-event analysis |
| GET | `/chat?cursor=<opaque>` | bearer | n/a | Read the durable chronological outbox page |
| POST | `/questions/{id}/reply` | bearer | required | Apply and resume a question answer |
| POST | `/calls/test` | bearer | required | Place an explicitly confirmed test call |
| PUT | `/devices/apns` | bearer | required | Register or transfer one APNs token |
| DELETE | `/devices/apns` | bearer | required | Remove the authenticated tenant's APNs token |
| DELETE | `/account` | bearer | required | Clean up providers and delete the account |

Every mutation rejects a client `uid`, `userId`, `tenantId`, `ownerId`, or `scopeUid`. The server
derives the tenant from the validated identity/session. Repeating an idempotency key with the same
payload replays the original result; the same key with a different payload is a conflict with no
side effect.

## Analysis and route

Analysis terminates in exactly one of `route_ready`, `needs_information`, `no_upcoming_event`,
`route_unavailable`, or `failed`. A terminal result always carries one durable message and an
opaque next cursor. `needs_information` is the honest missing-origin path; the client sends the
answer back in a later API slice instead of parsing Calendar fields locally.

For the private demo, the real active/most-recent physical Calendar event (`Shipathon Roppongi`)
is the route origin and the new event location (`Tokyo Tower`) is the destination. The contract
contains no coordinates or Core Location data. Route values are provider facts: unsupported
precision remains `null` or is omitted, and entrance/exit/best-car/crowding claims are absent.
The backend owns any exactly-once Calendar travel-block write under the analysis idempotency key;
these fixtures do not claim that a write occurred.

## Durable semantic chat

The outbox stores a monotonic sequence, stable message ID, semantic key, structured arguments, and
separate Calendar-authored `userContent`. Generated prose is projected into the requested locale at read time;
`semantic-outbox.json` deliberately has no final `text` field. Cursor values are opaque and are
never decoded or reset by the client. Manual refresh is a new idempotent `POST /analysis`, followed
by a cursor fetch; it must not duplicate an existing message.

Account deletion returns an opaque `deletionCapability` in the public response. Generic idempotency
receipts never persist that capability or access/refresh tokens in plaintext; token-bearing replay
payloads are short-lived encrypted envelopes.

## Explicitly outside this Gate 3 contract

Late notice, scheduler, cost-guard state, Core Location, TestFlight/App Store, and production
deployment/provider/migration execution belong to later gates or other owners. Staging verification
is planned only after code review; this fixture directory contains no live staging evidence.
