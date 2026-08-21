# Agent Economy Revenue Lane Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Put the already-verified TaskMarket work adapter on the resident agent-economy menu while retaining x402 as the passive seller lane.

**Architecture:** Reuse `skills/earn/taskmarket/run.sh` and its official TaskMarket readback gates. Only the release declaration changes: the new resident loop allowlist exposes `earn/taskmarket`, `x402_sell`, `report`, and `cook`. No new image generator, marketplace client, or trading strategy is created.

**Tech Stack:** Existing Node.js TaskMarket adapter, TOML loop declaration, plistgen regression test.

**Spec:** `docs/superpowers/specs/2026-08-21-agent-economy-design.md`

## Global Constraints

- One wake selects at most one TaskMarket job.
- TaskMarket quote cap, daily cap, float floor, official submission readback, and award observer remain unchanged.
- No capital-risk trading slot is added to the resident allowlist.
- x402 remains available but its catalog is not changed by this slice.

---

### Task 1: Expose the existing TaskMarket lane in the release-backed menu

**Files:**
- Modify: `loops/agent-economy/loop.toml`
- Modify: `test/agent-economy-control-plane.test.mjs`
- Test: `skills/earn/taskmarket/taskmarket-work.test.mjs`

**Interfaces:**
- Consumes: registry slot `earn/taskmarket` and existing `skills/earn/taskmarket/run.sh` contract.
- Produces: generated `ANICCA_SLOT_ALLOWLIST=earn/taskmarket,x402_sell,report,cook`.

- [ ] **Step 1: Write the failing plist assertion**

  Extend the existing generated-plist test to assert the exact four-entry `ANICCA_SLOT_ALLOWLIST`.

- [ ] **Step 2: Run the control-plane test to verify it fails**

  Run: `node --test test/agent-economy-control-plane.test.mjs`
  Expected: FAIL because the declaration does not yet define `ANICCA_SLOT_ALLOWLIST`.

- [ ] **Step 3: Add the allowlist declaration**

  Set `ANICCA_SLOT_ALLOWLIST = "earn/taskmarket,x402_sell,report,cook"` in `loops/agent-economy/loop.toml`. Do not add `yield`, `hl_trade`, `token_launch`, or other capital-risk slots.

- [ ] **Step 4: Run focused and adapter tests**

  Run: `node --test test/agent-economy-control-plane.test.mjs skills/earn/taskmarket/taskmarket-work.test.mjs`, `npm run test:install`, `npm run test:oss`, and `git diff --check`.
  Expected: 1 control-plane test plus 8 TaskMarket tests pass; install and OSS suites pass.

- [ ] **Step 5: Commit and push**

  Run: `git add loops/agent-economy/loop.toml test/agent-economy-control-plane.test.mjs docs/superpowers/plans/2026-08-21-agent-economy-revenue-lane.md && git commit -m "feat: expose taskmarket work lane" && git push`

