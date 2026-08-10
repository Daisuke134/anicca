# Connector existing-bundle disposition Item 13A plan

## Goal

Read back one exact existing applied bundle for the current provider event, revalidate its provider receipt/artifact and current Calendar event, and return an explicit `reused` disposition without rendering evidence or sending Telegram again. New evidence completion returns `created`. This gives the runner a trustworthy Item 13 continuation signal without changing runner behavior in this slice.

## Current evidence

- Item 12 is pushed at `d4bc308cc`; checkpoint-aware recovery is idempotent only after the new provider/message/photo checkpoint files exist.
- Production state contains three mode-0600 exact-schema bundles: two Luma and one Peatix. The Peatix bundle's `created_at`, provider receipt `observed_at`, event ref, and artifact SHA match, and its Calendar/Telegram IDs are positive.
- The accepted Peatix bundle predates Item 12 checkpoints. Without exact bundle adoption, the next wake would recapture evidence and resend a photo before the runner can distinguish an already-complete event.
- Existing provider stores expose receipt/artifact readback, Calendar has private canonical-URL idempotency readback, `stableJson` defines the bundle digest, and mode-0600/symlink validators already exist.

## Ponytail full gate

- Item 13 is split into 13A evidence disposition, 13B runner continuation, and 13C official foreground wake. Only 13A is active now.
- Reuse the existing applied bundle schema, provider store readers, artifact signature/SHA checks, Calendar find/readback, stable digest, and path guards. Add no migration script, DB, index, queue, service, transport, browser action, schedule, or runner change.
- Do not trust a local bundle alone. Reuse requires exact schema/file digest, one matching provider/event, provider receipt identity, raw artifact bytes/signature/SHA, and one current Calendar ID/URL match.
- Do not create Item 12 checkpoints from a legacy bundle in this slice. Exact readback on each invocation is smaller and avoids a second mutable migration authority.
- The returned disposition is runtime metadata only; the immutable persisted bundle schema remains unchanged.

## Implementation slice

Luna owns only:

1. `apps/life-manager/lib/connector-minimal-evidence.test.js`
2. `apps/life-manager/lib/connector-minimal-evidence.js`

Soft target: 2 files; production +70–120 LOC; tests +70–120 LOC. No runner production/test edit.

### RED

1. A mode-0600 legacy exact bundle with no Item 12 checkpoints is found by provider/event, its provider receipt and raw artifact are validated, current Calendar is independently read, and the chain returns the same bundle ID with `completion_disposition: reused`.
2. Legacy reuse invokes page render/screenshot/provider record/Telegram/bundle write zero times and leaves bundle file bytes/count unchanged.
3. A newly completed event returns `completion_disposition: created`; its next invocation returns `reused` with the same immutable bundle and zero Telegram resend.
4. Wrong filename/digest/schema/provider/event/status/receipt/artifact/positive IDs/timestamps, invalid PNG, multiple matching bundles, bundle file or parent symlink, and current Calendar missing/duplicate/ID-URL mismatch fail closed before reuse or Telegram.
5. Unrelated valid bundles do not match the current event. The scan is bounded and rejects non-regular, oversized, or unexpected bundle entries.
6. The persisted bundle never gains runtime disposition and retains its exact schema/privacy contract.
7. Existing partial checkpoint recovery and first-pass Luma/Peatix behavior remain unchanged.

### GREEN

- Read at most a bounded number of exact `<64hex>.json` files below `applied-bundles`, with state-root containment, component/file `lstat`, mode 0600, and size bounds.
- Recompute the bundle digest from its exact core and require filename, `bundle_id`, and digest equality. Validate every field with existing provider/event/ref/artifact/Calendar/positive-ID/instant authorities.
- Select exact provider/event/status only; zero match continues the Item 12 path, one match enters reuse validation, more than one fails closed.
- Validate the referenced provider receipt and artifact bytes using the same deterministic receipt identity as Item 12.
- Always independently read current Calendar by canonical URL hash and require exactly the stored event ID/URL before returning the persisted bundle plus runtime `completion_disposition: reused`.
- When the normal Item 12 path writes a new bundle, return runtime `completion_disposition: created`; on its next call the exact bundle reader returns `reused`.

## Verify

- Focused evidence suite; minimal runner, minimal production, Peatix workflow/store/Harness, native entrypoint; changed-file syntax; `git diff --check`.
- Fresh Sol review for bundle digest/schema authority, scan bounds, unrelated/corrupt file handling, provider/artifact identity, Calendar freshness, privacy, symlink/root escape, duplicate bundle ambiguity, and zero delivery/provider Submit paths.
- Update SSOT, commit, and push. Item 13 remains open until 13B runner continuation and 13C official wake prove Submit zero continuation and a positive durable every-wake Telegram receipt. Keep schedule unloaded.
