# Connector evidence photo key 21B plan

**Goal:** Bind every registration-evidence photo send to a deterministic provider-idempotency key so a new OS process can replay the boundary without a duplicate Telegram photo.

**Architecture:** Reuse the evidence chain's already-validated `canonicalUrlSha256`, which also owns Calendar and bundle identity. Pass exact `connector-evidence-photo:<64 lowercase hex>` to the Item21A Gateway photo transport. Do not add a receipt store, retry loop, or second identity.

**Ponytail scope:** exact 2 files.

- `apps/mr-bot/lib/connector-minimal-evidence.js`: add one `idempotencyKey` option to the existing `sendPhoto` call.
- `apps/mr-bot/lib/connector-minimal-evidence.test.js`: RED/GREEN the exact deterministic key, distinct message/photo namespaces, no URL/private value in the key, and unchanged checkpoint/bundle behavior.

**Estimated production change:** 1–3 LOC. **Estimated test change:** 15–35 LOC.

**Verification:** focused evidence tests, outbound guardian tests, syntax checks, `git diff --check`, fresh Sol review. No real provider, Calendar, or Telegram effect in this slice.

**Deferred to 21C:** separate Node OS processes and durable fake external ledgers prove provider registration, evidence receipt/artifact, Calendar, Telegram message/photo, and final bundle resume with effect count exactly one.
