# Connector Peatix Evidence Store Implementation Plan

> **For Luna:** Use Superpowers test-driven-development. Commit only the two new Peatix evidence-store files.

**Goal:** Persist an immutable tenant-scoped Peatix provider receipt and full-page PNG artifact after exact provider readback, without storing attendee identity.

**Architecture:** Reuse the proven Luma/Connpass content-addressed evidence pattern as a Peatix-specific bounded store. The store hashes the registered-page PNG, derives a deterministic provider receipt ID from tenant/event/time/hash, writes immutable mode-0600 objects below the existing evidence root, and supports independent receipt/artifact readback.

**Tech Stack:** Node.js CommonJS, `node:test`, SHA-256, atomic filesystem rename.

## Ponytail gate

- Copy/tweak the smaller existing Connpass evidence-store contract; do not introduce a database, generic registry, abstraction hierarchy, or migration.
- Accept only `peatix-event://event/<positive-id>` and return only `provider-receipt://peatix/<sha256>` plus `object://sha256/<sha256>`.
- Persist no name, email, cookie, ticket form answer, browser target, raw HTML, URL query, or Telegram value.
- Use tenant-scoped `outbound/peatix`, immutable collision checks, directories 0700, files 0600.
- Do not connect it to production evidence yet and do not touch browser/native order/schedule.
- Plan size: two new files; production target under 115 LOC, tests under 55 LOC.

### Task 1: Add the Peatix evidence store

**Files:**
- Create: `apps/mr-bot/lib/peatix-evidence-store.js`
- Create: `apps/mr-bot/lib/peatix-evidence-store.test.js`

- [ ] Write RED tests for deterministic record/read receipt/read PNG, exact Peatix refs, tenant isolation, immutable collision behavior, invalid event refs, invalid PNG, and private identity absence.
- [ ] Run RED: `node --test apps/mr-bot/lib/peatix-evidence-store.test.js`.
- [ ] Implement the minimum Peatix-specific store using the existing content-addressed layout and atomic write behavior.
- [ ] Run GREEN: `node --test apps/mr-bot/lib/peatix-evidence-store.test.js apps/mr-bot/lib/connpass-evidence-store.test.js apps/mr-bot/lib/luma-evidence-store.test.js`.
- [ ] Run `node --check` and `git diff --check`.
- [ ] Commit `feat(connector): add Peatix evidence store` and push `feature/connector-native-completion`.

After Luna reports RED/GREEN, fresh Sol review verifies tenant/integrity/privacy. Sol then generalizes only the minimal evidence-chain provider switch needed to create the real Peatix `applied_bundle`.
