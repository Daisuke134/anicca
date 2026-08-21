# Agent Economy Money Truth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reconcile delayed EVM receipts without rewriting the append-only earn ledger and expose only verified external realized revenue to the economy policy.

**Architecture:** Keep `skills/_shared/lib/ledger.mjs` and `skills/earn/lib/reconcile.mjs` as the existing write and wallet-anchor paths. Add a pure receipt joiner plus an append-only `receipt-reconciliations.jsonl` sidecar keyed by transaction hash. A missing or failed receipt remains unverified and never becomes revenue.

**Tech Stack:** Node.js ESM, `node:test`, injected fetch, JSONL append-only state.

**Spec:** `docs/superpowers/specs/2026-08-21-agent-economy-design.md`

## Global Constraints

- Existing ledger rows are never rewritten or deleted.
- `external:true` is necessary but not sufficient; a verified receipt is required.
- Self-payments, swaps, tests, returned principal, and unverified rows do not enter external realized net.
- Receipt RPC errors fail closed and remain retryable.
- Reconciliation is idempotent by transaction hash.

---

### Task 1: Join delayed receipts into an external-revenue summary

**Files:**
- Create: `skills/agent-economy/lib/money-truth.mjs`
- Test: `skills/agent-economy/lib/money-truth.test.mjs`
- Create: `skills/agent-economy/reconcile-receipts.mjs`

**Interfaces:**
- Consumes: earn-ledger rows and `{tx,status}` reconciliation rows.
- Produces: `reconcilePendingReceipts(rows, fetchReceipt)`, `summarizeRealizedRevenue(rows, corrections)`, and `receiptKey(row)`.

- [ ] **Step 1: Write the failing tests**

  Cover a pending external row with `status:"null"` becoming verified after an injected `0x1` receipt, an unavailable receipt remaining unverified, self/test/internal rows staying excluded, and duplicate tx corrections collapsing to one result.

- [ ] **Step 2: Run the focused test to verify it fails**

  Run: `node --test skills/agent-economy/lib/money-truth.test.mjs`
  Expected: FAIL because the module does not exist.

- [ ] **Step 3: Implement the pure joiner and summary**

  Implement only the named functions. Use a tx-keyed map, preserve the original row, and classify a row as external only when `external:true`, `net_usdc > 0`, and the EVM status is `0x1` (or the existing confirmed Solana/Hyperliquid proof shape is present).

- [ ] **Step 4: Run the focused test to verify it passes**

  Run: `node --test skills/agent-economy/lib/money-truth.test.mjs`
  Expected: PASS with zero failures.

- [ ] **Step 5: Verify the CLI against an empty ledger without network side effects**

  Run: `node skills/agent-economy/reconcile-receipts.mjs /tmp/missing-ledger.jsonl /tmp/missing-corrections.jsonl`
  Expected: one JSON result with zero attempts and zero verified revenue.

- [ ] **Step 6: Commit and push**

  Run: `git add skills/agent-economy/lib/money-truth.mjs skills/agent-economy/lib/money-truth.test.mjs skills/agent-economy/reconcile-receipts.mjs docs/superpowers/plans/2026-08-21-agent-economy-money-truth.md && git commit -m "feat: reconcile delayed external revenue receipts" && git push`
