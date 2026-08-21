# Agent Economy Treasury Policy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every future money-moving adapter one deterministic reserve, session-cap, and graduation policy.

**Architecture:** A pure policy module consumes already-read balances and cost summaries. It does not sign, broadcast, fetch prices, or read environment variables. Signer and compute adapters will call this module before any external effect.

**Tech Stack:** Node.js ESM, `node:test`.

**Spec:** `docs/superpowers/specs/2026-08-21-agent-economy-design.md`

## Global Constraints

- Invalid, missing, negative, or non-finite money inputs fail closed.
- `spendable = max(0, liquid - reserve - committed liabilities)`.
- A spend requires a finite positive session cap and cannot cross the reserve floor.
- Graduation requires 30-day external realized net >= 1.5x compute+shelter, >=30 days liquid runway, and zero human-paid inference.
- This module never initiates an external side effect.

---

### Task 1: Implement the pure treasury policy

**Files:**
- Create: `skills/agent-economy/lib/treasury-policy.mjs`
- Test: `skills/agent-economy/lib/treasury-policy.test.mjs`

**Interfaces:**
- Produces: `computeSpendable`, `authorizeSpend`, and `graduationGate`.

- [ ] **Step 1: Write the failing tests**

  Cover exact spendable arithmetic, reserve-floor rejection, session-cap rejection, malformed-input rejection, a passing graduation gate, human-paid-inference rejection, and insufficient coverage/runway rejection.

- [ ] **Step 2: Run the focused test to verify it fails**

  Run: `node --test skills/agent-economy/lib/treasury-policy.test.mjs`
  Expected: FAIL because the policy module does not exist.

- [ ] **Step 3: Implement the smallest pure policy**

  Implement the three named functions with finite-number validation, no filesystem/network imports, and explicit reason strings.

- [ ] **Step 4: Run focused and syntax tests**

  Run: `node --test skills/agent-economy/lib/treasury-policy.test.mjs`, `node --check skills/agent-economy/lib/treasury-policy.mjs`, and `git diff --check`.
  Expected: all focused tests pass.

- [ ] **Step 5: Commit and push**

  Run: `git add skills/agent-economy/lib/treasury-policy.mjs skills/agent-economy/lib/treasury-policy.test.mjs docs/superpowers/plans/2026-08-21-agent-economy-treasury-policy.md && git commit -m "feat: add agent economy treasury policy" && git push`

### Task 2: Reuse the policy at the existing TaskMarket spend boundary

**Files:**
- Modify: `skills/earn/taskmarket/taskmarket-work.mjs`
- Test: `skills/earn/taskmarket/taskmarket-work.test.mjs`

**Interfaces:**
- Consumes: `authorizeSpend()` and the existing `$0.25` float / `$0.14` daily limits.
- Produces: `imageSpendDecision()` and the same fail-closed TaskMarket behavior with one shared policy implementation.

- [ ] **Step 1: Write the failing `imageSpendDecision` assertions**

  Assert an allowed `$0.07` image at `$1.00` balance, reserve-floor rejection at `$0.30`, and session-cap rejection after `$0.10` daily spend.

- [ ] **Step 2: Run `node --test skills/earn/taskmarket/taskmarket-work.test.mjs` and observe the missing export**

- [ ] **Step 3: Import `authorizeSpend`, export `imageSpendDecision`, and replace the duplicate float/daily checks**

- [ ] **Step 4: Run the nine TaskMarket tests plus the seven treasury-policy tests**

- [ ] **Step 5: Commit and push**

  Run: `git add skills/earn/taskmarket/taskmarket-work.mjs skills/earn/taskmarket/taskmarket-work.test.mjs docs/superpowers/plans/2026-08-21-agent-economy-treasury-policy.md && git commit -m "fix: route taskmarket spend through treasury policy" && git push`
