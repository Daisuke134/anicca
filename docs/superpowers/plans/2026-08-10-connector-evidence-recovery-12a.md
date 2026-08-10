# Connector evidence recovery Item 12A plan

## Goal

Persist and validate the provider ticket/PNG and Calendar stages of one verified registration so a recreated evidence chain resumes after interruption without another screenshot, provider-evidence write, or Calendar create.

## Current evidence

- Item 10B and Item 11 are accepted by official Peatix bundle `applied-bundle:cb4be9afc9d0d55212c84908b7483dfd964ea6b5eefaff7a20c89b180e9759b0`.
- The live recovery sequence already proved provider Submit zero and Calendar event one, but it repeated receipt rendering/evidence writes and Telegram delivery because no evidence-stage checkpoint existed.
- Existing provider evidence stores already expose `record`, `readExternalReceipt`, and `readArtifact`; Calendar already uses one private SHA-256 idempotency property and independent readback. These are the reusable recovery authorities.
- Existing runner regression already proves a parent `registered` pre-readback invokes cache/direct/Harness Submit zero. This slice changes no runner or provider code.

## Ponytail full gate

- Reuse the current evidence store readers, Calendar idempotency/readback, mode-0600 state root, receipt validators, and atomic rename pattern.
- Add no database, service, queue, retry loop, provider abstraction, browser action, runner dependency, or schedule.
- This is Item 12A only: provider ticket/PNG and Calendar recovery. Telegram message/photo and final bundle checkpointing are the next 12B slice and are not claimed here.
- Store only provider/event refs, canonical URL hash, artifact/receipt refs and SHA, Calendar ID/URL/readback time, and timestamps. Never persist title, venue, attendee, Telegram target, raw page, screenshot bytes, or private profile in the checkpoint.

## Implementation slice

Luna owns only:

1. `apps/life-manager/lib/connector-minimal-evidence.test.js`
2. `apps/life-manager/lib/connector-minimal-evidence.js`

Soft target: 2 files; production +55–90 LOC; tests +65–95 LOC.

### RED

1. After a valid provider receipt/PNG is stored and Calendar fails, recreating the chain from the same state validates `readExternalReceipt` and `readArtifact`, then skips receipt render, screenshot, and `record` while completing through Calendar/Telegram/bundle.
2. If Calendar create succeeds but its first independent readback is unavailable or representation-mismatched, recovery finds the one existing private-idempotency event and never creates a second event.
3. The checkpoint is mode 0600, atomic, exact-schema, and contains no title, venue, attendee, target, ticket ID, URL, screenshot bytes, or private value.
4. Corrupt JSON, extra keys, wrong provider/event/hash, invalid receipt/artifact ref, artifact SHA mismatch, missing provider receipt, or invalid PNG fails before page render, Calendar, Telegram, or bundle.
5. Existing first-pass Luma and Peatix flows remain unchanged and all existing partial failures still write no bundle.

### GREEN

- Derive a checkpoint identity from provider, exact event reference, and validated canonical event URL; store the URL only as its SHA-256 idempotency value.
- After provider evidence succeeds, atomically persist an exact `evidence` checkpoint with stable first-observed timestamp and validated refs/SHA.
- On restart, validate the checkpoint, provider receipt, artifact bytes/signature/SHA, and identity before skipping page receipt render/screenshot/store.
- After one independent Calendar readback, atomically advance the same checkpoint to exact `calendar` stage with validated Calendar receipt and readback timestamp.
- If Calendar already exists after a crash between create and checkpoint, reuse the one provider event; create remains zero on recovery.
- Keep Telegram and final bundle behavior otherwise unchanged in this slice.

## Verify

- Focused evidence suite, minimal runner pre-registered no-submit regression, minimal production, Peatix workflow/provider/Harness, native entrypoint, changed-file syntax, `git diff --check`.
- Fresh Sol review for checkpoint corruption, privacy, identity binding, artifact validation, Calendar duplication, crash ordering, Luma non-regression, and absence of provider Submit paths.
- Update SSOT, commit, and push. Item 12 remains open until 12B adds Telegram/photo/final-bundle recovery and the full four-boundary fixture matrix passes.
