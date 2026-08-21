# Agent Economy Auto-Reconcile Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the release-backed agent-economy loop retry delayed external receipts automatically.

**Architecture:** A pure 15-minute cadence gate prevents extra RPC traffic in legacy runtimes. The new release sets `ANICCA_ECONOMY_RECONCILE=1`; the loop dynamically imports the existing receipt reconciler, appends only terminal corrections, and fails soft on missing modules or RPC errors.

**Tech Stack:** Node.js ESM, dynamic imports, existing `verify-tx.mjs` and `money-truth.mjs`.

**Spec:** `docs/superpowers/specs/2026-08-21-agent-economy-design.md`

## Global Constraints

- Legacy releases remain disabled unless the explicit environment flag is present.
- Reconciliation runs at most once per 15 minutes per process.
- It never rewrites `earn-ledger.jsonl` and never blocks a wake on an RPC failure.
- The correction sidecar remains tx-keyed and idempotent.

---

### Task 1: Wire the opt-in reconciler into the resident loop

**Files:**
- Create: `runtime/loop/money-truth-wire.mjs`
- Test: `runtime/loop/__tests__/money-truth-wire.test.mjs`
- Modify: `runtime/loop/index.mjs`
- Modify: `loops/agent-economy/loop.toml`
- Modify: `test/agent-economy-control-plane.test.mjs`

**Interfaces:**
- Consumes: `ANICCA_ECONOMY_RECONCILE=1`, the resolved earn ledger path, and the existing receipt verifier.
- Produces: terminal sidecar corrections and a stderr count when corrections are persisted.

- [ ] **Step 1: Write the cadence tests**

  Assert disabled flags never run, first enabled wake runs, and subsequent calls wait 15 minutes.

- [ ] **Step 2: Run the cadence test and observe the missing module**

  Run: `node --test runtime/loop/__tests__/money-truth-wire.test.mjs`
  Expected: FAIL because `money-truth-wire.mjs` does not exist.

- [ ] **Step 3: Add the helper, dynamic wire, and release flag**

  Add the pure helper, call `reconcileLedger()` at the beginning of each due wake, and set the flag in `loops/agent-economy/loop.toml`. Keep the import dynamic so old releases continue to boot.

- [ ] **Step 4: Run focused, release, install, and OSS checks**

  Run: `node --test runtime/loop/__tests__/money-truth-wire.test.mjs test/agent-economy-control-plane.test.mjs skills/agent-economy/lib/money-truth.test.mjs`, `node --check runtime/loop/index.mjs`, `npm run test:install`, `npm run test:oss`, and `git diff --check`.

- [ ] **Step 5: Commit and push**

  Run: `git add runtime/loop/money-truth-wire.mjs runtime/loop/__tests__/money-truth-wire.test.mjs runtime/loop/index.mjs loops/agent-economy/loop.toml test/agent-economy-control-plane.test.mjs docs/superpowers/plans/2026-08-21-agent-economy-auto-reconcile.md && git commit -m "feat: auto-reconcile delayed economy receipts" && git push`

