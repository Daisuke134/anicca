# Connector Native Write Integration Plan

> **Execution:** Use superpowers:executing-plans one task at a time with RED → GREEN → regression → commit/push.

**Goal:** Make the default Mac mini Connector pass select one grounded event with Luna and run the existing verified RSVP → Calendar → coverage → Telegram pipeline.

**Architecture:** The native entrypoint supplies only bounded runtime configuration. The runtime reads the tenant-bound profile, collects verified Luma and all-calendar inventories, asks the Luna adapter for preference and goal/serendipity rankings, applies deterministic Calendar/spend gates, selects only the first verified runnable candidate, and hands that candidate to `runNativeConnectorWrite`. Luna never attests external effects; the write pipeline remains the sole effect verifier.

## Task 1: Runtime composition contract

**Files:**
- Modify: `apps/mr-bot/lib/connector-native-runtime.js`
- Test: `apps/mr-bot/lib/connector-native-runtime.test.js`

- [x] Add a failing test proving the configured pass reads a verified profile, invokes Luna exactly once, gates the selected date, and passes one inventory-backed candidate to the write pipeline.
- [ ] Add failing tests proving no candidate, failed Luna judgment, failed Calendar gate, or failed spend gate never invokes the write pipeline.
- [x] Implement the smallest opt-in composition using existing validators and dependency seams.
- [x] Preserve the current read-only result when write configuration is absent so diagnostics remain safe.

## Task 2: Native entrypoint configuration

**Files:**
- Modify: `skills/connector/native-pass.js`
- Test: `skills/connector/native-pass.test.js`

- [ ] Add failing tests for owner-bounded `LM_CONNECTOR_PROFILE_PATH`, `LM_CONNECTOR_LUNA_EVIDENCE_DIR`, Telegram target, Calendar coverage URL, home location, and route adapter configuration.
- [ ] Require write configuration as one complete set; reject partial effect configuration.
- [ ] Pass no bot token or raw credential through returned/logged runtime results.

## Task 3: Verification and handoff

- [ ] Run focused native runtime/entrypoint/Luna/write tests.
- [ ] Run `npm run test:outbound` and canonical native entrypoint tests.
- [ ] Run `git diff --check` and secret/path scans on changed files.
- [ ] Update the master spec with exact RED/GREEN evidence.
- [ ] Commit and push before starting Gmail/QR Task 6.

## Completion boundary

This slice proves executable composition with trusted test seams. It does not claim a live registration; the separate live-E2E TODO requires real provider, Calendar readback, Telegram message ID, and Gmail/QR lineage.
