# TECH PLAY Production Factory and Router Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Superpowers test-driven-development. Sol owns plan/review/verification/commit; Luna owns the exact two production-factory files.

**Goal:** Make the existing production connector dependency graph route TECH PLAY discovery, cache, direct action, deterministic Browser Harness fallback, and registered readback through the already-shipped workflow.

**Architecture:** Extend the current explicit provider branches. Import `createTechPlayDiscoveryWorkflow`, add `techplay_registration_v1`, validate the optional workflow, and select it for the same six router operations as the existing providers. The production factory creates the default workflow with the shipped audit callback and passes the same instance to both Browser Harness and router. Keep unknown providers fail-closed and keep private profile resolution unchanged.

**Files / soft target:**

- Modify `apps/mr-bot/lib/connector-minimal-production.js` — about 20–35 LOC.
- Modify `apps/mr-bot/lib/connector-minimal-production.test.js` — about 60–110 LOC.

## Grounding

- Node.js CommonJS modules: <https://nodejs.org/api/modules.html#modules-commonjs-modules> — reuse the file's existing `require`/`module.exports` structure.
- Public provider-router searches show explicit unknown-provider rejection and injected provider implementations; this repository's reviewed explicit branch is the authoritative reusable rung.
- Japanese dependency-injection search did not reveal a closer reusable implementation; no registry/framework/package is justified.
- Existing Eventbrite/Doorkeeper router and default-Harness tests define the exact local integration contract.

## Contract

- [x] RED: router rejects `techplay`, factory cannot install the workflow, and default Browser Harness cannot receive TECH PLAY registered readback.
- [x] Import `createTechPlayDiscoveryWorkflow` and add exact cache identity `techplay_registration_v1`.
- [x] Accept optional TECH PLAY workflow only with `discoverCandidates`, `runDirectAction`, and `readProviderState`; unknown providers remain rejected.
- [x] Route discovery, cache replay, direct action, fallback, readback, and repaired-action save through the same TECH PLAY workflow and private-free cache metadata.
- [x] The default factory creates TECH PLAY with `now` and `operations.recordTechPlayDiscoveryAudit`, then passes the same instance to Browser Harness and router.
- [x] Default Harness final action accepts only the injected workflow's registered readback; external proposer remains unused for the deterministic TECH PLAY final control.
- [x] Existing private form profile wiring is reused; no TECH PLAY-specific credential/profile field is added.
- [x] Run focused/full production tests, Harness and TECH PLAY workflow adjacent tests, syntax, diff check, mutation proof, and fresh Sol review.
- [x] Do not change audit implementation, evidence, Calendar, native order, launchd, or perform a real application.
