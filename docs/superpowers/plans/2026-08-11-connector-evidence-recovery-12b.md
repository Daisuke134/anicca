# Connector Telegram and bundle recovery Item 12B plan

## Goal

Persist and validate the successful Telegram message and photo receipts so a recreated evidence chain sends only the missing delivery, then deterministically writes or reuses exactly one final applied bundle. Compose this with Item 12A so the four provider/Calendar/Telegram interruption boundaries preserve provider Submit zero, Calendar event one, and bundle one.

## Current evidence

- Item 12A is pushed at `3b7aec54d`. Its provider pointer validates the stored receipt and raw PNG, skips page rendering/screenshot/provider record on recovery, and always performs an independent Calendar find/create/readback.
- The current chain sends the message and photo sequentially but persists their positive IDs only in the final bundle. A photo or bundle failure therefore loses the earlier successful Telegram receipt and repeats that delivery on restart.
- The message transport already receives one stable event idempotency key. The photo transport returns a positive provider ID but has no reusable durable receipt in the chain.
- `immutableJson`, the event identity, mode-0600 state, positive message-ID parser, and final bundle schema are existing authorities to reuse.

## Ponytail full gate

- Add no database, queue, retry loop, transport, Telegram API, service, provider abstraction, schedule, or browser action.
- Reuse the Item 12A event identity and checkpoint directory. Add only exact immutable message/photo stage receipts; never store Telegram target, message/caption body, title, venue, attendee, ticket ID, raw PNG, or private profile in them.
- Do not persist a stale Calendar authority. Every invocation still validates provider evidence and independently reads Calendar. A stored delivery receipt is usable only when its exact Calendar event ID/URL and event identity match the current readback.
- Do not change runner continuation in this slice. A completed bundle may return idempotently; continuing to the next candidate is Item 13.
- Preserve external ordering: provider evidence → Calendar independent readback → Telegram message receipt → Telegram photo receipt → immutable bundle.

## Implementation slice

Luna owns only:

1. `apps/life-manager/lib/connector-minimal-evidence.test.js`
2. `apps/life-manager/lib/connector-minimal-evidence.js`

Soft target: 2 files; production +70–120 LOC; tests +90–150 LOC. Reuse the existing checkpoint validation and helpers; no broad evidence-chain rewrite.

### RED

1. Message succeeds and photo fails. A recreated chain validates the message receipt, skips message resend, retries only the photo, and writes one bundle. Message successful effect total one.
2. Message and photo succeed but final bundle write fails. After the filesystem blocker is removed, a recreated chain skips both Telegram calls and writes one bundle with the original positive IDs.
3. A completed chain invoked again validates provider evidence and current Calendar readback, sends neither Telegram artifact, and returns the same bundle ID with bundle file count one.
4. Message failure persists no message/photo checkpoint and writes no bundle. Photo failure persists only the message checkpoint and writes no bundle.
5. Each delivery checkpoint is atomic, mode 0600, exact-schema, identity-bound, and contains no target, message/caption, title, venue, attendee, ticket ID, canonical URL, raw PNG, or private value.
6. Missing message before photo, wrong provider/event/URL hash/artifact/calendar identity, non-positive or unsafe provider IDs, invalid JSON/extra keys, mismatched stage, file/parent symlink, and bundle collision fail before any missing Telegram delivery or bundle write. Provider and Calendar read-only validation remains allowed where required.
7. The full composed interruption matrix proves: provider PNG/ticket checkpoint recovery, Calendar create/readback crash recovery, message-success/photo-failure recovery, and photo-success/bundle-failure recovery. Final totals are external registration one, Calendar create one, durable bundle one, provider Submit zero.
8. Existing first-pass Luma/Peatix complete bundles and every partial-failure no-bundle contract remain unchanged.

### GREEN

- Derive one delivery identity from provider/event/canonical URL hash/provider receipt/artifact SHA. Use fixed message and photo checkpoint paths below the existing checkpoint root and reject symlinked components before reads, sends, or writes.
- Read and exact-validate any message/photo receipt before Calendar. After the mandatory current Calendar readback, require the stored Calendar ID/URL to match before reuse.
- Immediately after a positive message ID, atomically write the message receipt with the first successful Calendar readback timestamp. After a positive photo ID, atomically write the photo receipt bound to the message receipt and artifact identity.
- On recovery, send only an absent stage. A photo receipt without its matching message receipt is invalid.
- Build the final bundle from the stable message checkpoint timestamp and the two positive IDs. If the bundle already exists, require byte-identical immutable content and return the same bundle.
- Assert the final bundle path is state-root-contained and symlink-free before write/reuse.

## Verify

- Focused evidence suite; minimal runner pre-registered Submit-zero regression; minimal production; Peatix workflow/store/Harness; native entrypoint; changed-file syntax; `git diff --check`.
- Fresh Sol review for delivery identity, corrupt receipts, checkpoint ordering, Telegram duplicates, bundle determinism/collision, Calendar freshness, privacy, symlink/root escape, Luma/Peatix non-regression, and absence of provider Submit paths.
- Update SSOT, commit, and push. Mark Item 12 complete only when the full four-boundary composed fixture passes with registration one, Calendar one, bundle one, and Submit zero. Keep production schedule unloaded.
