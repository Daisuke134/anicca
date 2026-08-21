# Agent Economy Action Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent malformed model tool output and stale slots from consuming agent-economy wakes.

**Architecture:** `parseToolCall` rejects a `run_skill` wrapper without an explicit slot. The ordinary loop then checks the selected slot against the current registry-filtered menu before spawning any skill. Invalid selections are ledgered as `invalid_slot` and sleep; they never reach a filesystem path lookup.

**Tech Stack:** Node.js ESM, `node:test`.

**Spec:** `docs/superpowers/specs/2026-08-21-agent-economy-design.md`

## Global Constraints

- Existing valid `run_skill`, `sleep`, nested args, and text-mode parsing behavior remains unchanged.
- An invalid or missing slot never executes a child process.
- The current wake menu is the only allowlist; no model-provided slot becomes trusted by itself.
- Every new ledger kind is truthful and non-profitable.

---

### Task 1: Reject malformed wrapper calls and guard the execution wire

**Files:**
- Modify: `runtime/loop/parse-tool-call.mjs`
- Modify: `runtime/loop/slot-allowlist.mjs`
- Modify: `runtime/loop/index.mjs`
- Modify: `runtime/loop/package.json`
- Test: `runtime/loop/__tests__/parse-tool-call.test.mjs`
- Test: `runtime/loop/__tests__/slot-allowlist.test.mjs`

**Interfaces:**
- Consumes: parsed `{slot,args}` and `eligibleSkillSlots` from the existing registry/catalog gate.
- Produces: `isAllowedSlot(slot, allowedSlots): boolean`; `invalid_slot` ledger records for rejected ordinary wakes.

- [ ] **Step 1: Write the failing parser and allowlist tests**

  Add a `parseToolCall` fixture whose function name is `run_skill` but whose arguments contain no `slot`; assert the result is `null`. Add `isAllowedSlot` fixtures for `x402_sell` in the menu, `run_skill` outside the menu, an empty slot, and an empty menu.

- [ ] **Step 2: Run the focused tests and observe the RED result**

  Run: `node --test runtime/loop/__tests__/parse-tool-call.test.mjs runtime/loop/__tests__/slot-allowlist.test.mjs`
  Expected before implementation: the parser test reports `{slot:"run_skill"}` instead of `null`, and the allowlist file reports that `isAllowedSlot` is not exported.

- [ ] **Step 3: Implement the parser rejection and pre-spawn wire guard**

  In `parse-tool-call.mjs`, require an explicit non-empty `slot` only when the wrapper function is `run_skill`; preserve direct-tool fallback for `sleep`. Export `isAllowedSlot` from `slot-allowlist.mjs`. In `index.mjs`, after the existing `sleep` branch and before `runSkillWithKillRef`, append `{kind:"invalid_slot",slot,...}` and sleep when the slot is absent from `eligibleSkillSlots`.

- [ ] **Step 4: Run focused and neighboring tests**

  Run: `node --test runtime/loop/__tests__/parse-tool-call.test.mjs runtime/loop/__tests__/slot-allowlist.test.mjs`, `npm run test:unit` from `runtime/loop`, `node --check runtime/loop/index.mjs`, and `git diff --check`.
  Expected: focused tests pass; any unrelated pre-existing failures in the broader live harness are reported separately and do not change the focused acceptance result.

- [ ] **Step 5: Commit and push**

  Run: `git add runtime/loop/parse-tool-call.mjs runtime/loop/slot-allowlist.mjs runtime/loop/index.mjs runtime/loop/package.json runtime/loop/__tests__/parse-tool-call.test.mjs runtime/loop/__tests__/slot-allowlist.test.mjs docs/superpowers/plans/2026-08-21-agent-economy-action-contract.md && git commit -m "fix: reject invalid agent economy slots" && git push`
