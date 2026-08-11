# TECH PLAY Applied Evidence Bundle Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Superpowers test-driven-development. Sol owns plan/review/verification/commit; Luna owns the exact two evidence-chain files.

**Goal:** Turn a verified TECH PLAY `registered` state into the existing durable `applied_bundle`: immutable provider receipt and full-page PNG, exact Google Calendar create/readback, Telegram message/photo receipts, and checkpointed reuse.

**Architecture:** Extend the explicit provider map in `connector-minimal-evidence`. Add exact TECH PLAY event/receipt refs, an event/canonical identity parser, the shipped evidence store, and `registered` as the only accepted state. Treat TECH PLAY like Doorkeeper/Eventbrite: require the owned page already at the canonical parent event URL, never call `setContent`, `goto`, or receipt rendering, capture full-page PNG, validate stored receipt/artifact before Calendar, then reuse the generic Calendar/Telegram/checkpoint/bundle path unchanged.

**Files / soft target:**

- Modify `apps/life-manager/lib/connector-minimal-evidence.js` — about 24–45 LOC.
- Modify `apps/life-manager/lib/connector-minimal-evidence.test.js` — about 80–135 LOC.

## Grounding

- Node.js `crypto.createHash`: <https://nodejs.org/api/crypto.html#cryptocreatehashalgorithm-options> — the existing chain already computes stable SHA-256 identities.
- English and Japanese searches found no closer reusable applied-bundle implementation; the repository's existing chain remains the exact local SSOT.
- Existing Eventbrite/Doorkeeper full-page capture, receipt readback ordering, Calendar readback, delivery checkpoints, and reuse tests define the extension pattern.

## Contract

- [ ] RED: `completeEvidence` rejects provider `techplay`.
- [ ] Add exact `techplay-event://event/<positive ID>`, `provider-receipt://techplay/<64 lowercase hex>`, and canonical `https://techplay.jp/event/<same ID>` identity.
- [ ] Create/inject `createTechPlayEvidenceStore`; validate its exact generic browser receipt tuple on checkpoint reuse.
- [ ] Accept only provider state `registered` and require the current owned page URL equals the canonical parent event URL before any screenshot/downstream effect.
- [ ] Capture one full-page PNG without `setContent`, `goto`, `evaluate`, or receipt rendering; read receipt/artifact before Calendar.
- [ ] Reuse existing exact Calendar create/readback, Telegram message/photo, checkpoints, bundle digest, and second-call reuse with no duplicate external effects.
- [ ] Reject event/canonical/page drift, pending/absent, wrong receipt/artifact, and tampered checkpoint/bundle before downstream effects.
- [ ] Run focused/full evidence tests, store/Calendar/production adjacent tests, syntax, diff check, mutation proof, and fresh Sol review.
- [ ] Do not change generic bundle schema, production factory, native order, launchd, or perform real external effects.
