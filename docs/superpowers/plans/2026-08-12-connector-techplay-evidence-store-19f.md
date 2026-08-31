# TECH PLAY Immutable Evidence Store Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Superpowers test-driven-development. Sol owns plan/review/verification/commit; Luna owns the exact two evidence-store files.

**Goal:** Give TECH PLAY the same private, content-addressed, tamper-evident PNG receipt store already used by browser-based providers.

**Architecture:** Add one thin wrapper around `createBrowserProviderEvidenceStore`. Pin provider `techplay`, exact event refs `techplay-event://event/<positive ID>`, exact receipt refs `provider-receipt://techplay/<64 lowercase hex>`, and a provider-specific collision message. Reuse every atomic-write, hash, tenant, timestamp, PNG, readback, and file-mode invariant unchanged.

**Files / soft target:**

- Modify `apps/mr-bot/lib/connpass-evidence-store.js` — about 8–12 LOC.
- Modify `apps/mr-bot/lib/connpass-evidence-store.test.js` — about 35–60 LOC.

## Grounding

- Node.js `fs.renameSync` / `fs.writeFileSync`: <https://nodejs.org/api/fs.html#fsrenamesyncoldpath-newpath> — the existing local atomic writer already uses exclusive temporary creation and rename.
- Public search for immutable provider receipts found this repository's existing hashed evidence-store implementation as the closest exact reusable source.
- Japanese search for tamper-evident SHA-256 evidence confirms hashing conventions but no closer implementation; local reviewed generic store wins.
- Existing Eventbrite/Doorkeeper wrappers and tests define the exact provider extension pattern.

## Contract

- [x] RED: `createTechPlayEvidenceStore` is unavailable.
- [x] Add only a thin generic-store wrapper and export it.
- [x] Accept only `techplay-event://event/<positive ID>` and return only `provider-receipt://techplay/<64 lowercase hex>` plus the shared object ref.
- [x] Record/read the exact receipt tuple and PNG; tenant path is private, files are `0600`, refs contain no tenant/private values.
- [x] Wrong event identity, wrong receipt provider/hash, receipt tuple tampering, and artifact tampering fail closed.
- [x] Run focused/full evidence-store tests, syntax, diff check, mutation proof, and fresh Sol review.
- [x] Do not change generic store behavior, production factory, Calendar, applied-bundle chain, native order, launchd, or perform external effects.
