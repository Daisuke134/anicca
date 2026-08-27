# Agent Economy Order 4 Reconciliation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reconcile the already-settled BlockRun failure exactly once, consume its outside-revenue funding while preserving the reserve, and clear ambiguity only after strict Base-USDC evidence joins.

**Architecture:** Reuse the existing strict `verifyEvmReceipt`, append-only compute journal lock, and `authorizeEarnedSpend` policy. The reconciler reads the durable intent, validates its selected revenue receipt and reserve, verifies the exact on-chain Transfer tuple, appends one `failed_output` compute receipt under the original idempotency key, then removes the intent/funding locks; any verification or append failure leaves both locks intact. Status reads the instance-scoped compute journal and counts `cost_usdc`.

**Tech Stack:** Node.js ESM, `node:test`, filesystem JSONL, existing JSON-RPC verifier

**Spec:** `docs/superpowers/specs/2026-08-21-agent-economy-design.md`

## Global Constraints

- Work only on `feat/agent-economy-implementation` in the specified linked worktree and push only its matching origin branch.
- No new paid request, signer, secret, prompt persistence, human credential, or bootstrap/internal/self-pay revenue.
- Exact live tuple: Base `8453`, canonical USDC, tx `0x1b31ef383fae0078a24adcfa1f78fe0eefd390bc2b02fdb25c558498032e2774`, log `29`, payer `0x810f6d61f7606deee2657d3083e150a222bc29c5`, payee `0xe9030014f5dae217d0a152f02a043567b16c1abf`, amount `2000` atomic.
- Failure truth remains HTTP `429`, provider code `FREE_MODEL_FAILED`, no usable output, cost `0.002` USDC, reserve `0.001` USDC.

---

### Task 1: Exactly-once failed settlement reconciliation

**Files:**
- Modify: `runtime/compute-proxy/compute-receipt.mjs`
- Create: `runtime/compute-proxy/__tests__/failed-settlement-reconciliation.test.mjs`
- Modify: `skills/agent-economy/status.mjs`
- Modify: `skills/agent-economy/status.test.mjs`

**Interfaces:**
- Consumes: existing intent directory, funding lock, canonical revenue journal, `verifyEvmReceipt(expectedTuple)`.
- Produces: `reconcileFailedComputeSettlement(options) -> { appended, duplicate, receipt }`; one append-only `receipt_type=compute`, `outcome=failed_output` row with no prompt/output body.

- [x] **Step 1: Write the failing tests**

Add tests that create a real temporary intent/funding lock and revenue journal, inject a complete strict verifier result, and assert: one `0.002` failed-output row; original idempotency/funding IDs; no output body; both locks removed only after append; replay appends zero; another intent cannot spend the same receipt past the `0.001` reserve. Add a second test whose verifier returns `verified:false` and assert no journal plus both locks unchanged. Extend status behavior to count `cost_usdc` from the instance compute journal.

- [x] **Step 2: Run RED**

Run: `node --test runtime/compute-proxy/__tests__/failed-settlement-reconciliation.test.mjs skills/agent-economy/status.test.mjs`

Expected: FAIL because `reconcileFailedComputeSettlement` and `cost_usdc` status support do not exist.

- [x] **Step 3: Write the minimal implementation**

Reuse `authorizeEarnedSpend`, `verifyEvmReceipt`, `appendComputeReceipt`, and current JSONL/lock helpers. Validate the intent's `transport_started` state, canonical payer and funding IDs, reserve authorization, exact chain tuple, positive HTTP failure classification, missing output, and transaction uniqueness. Append before removing locks. On a matching replay, re-verify chain evidence, return the stored row, and remove recreated stale locks without appending.

- [x] **Step 4: Run GREEN and mutation checks**

Run: `node --test runtime/compute-proxy/__tests__/failed-settlement-reconciliation.test.mjs skills/agent-economy/status.test.mjs skills/agent-economy/lib/treasury-policy.test.mjs`

Expected: all tests PASS. Mentally mutate tx/log/amount/payer/payee, funding ID, reserve, append order, and output classification; at least one test must fail for each load-bearing mutation.

- [x] **Step 5: Primary live reconciliation and replay**

The primary calls the exported reconciler against the live instance using the exact tuple above and the existing strict RPC verifier, reads back the single redacted row, verifies both ambiguity locks are absent, verifies status cost `0.002`, recreates no payment, and reruns reconciliation to prove append zero. No implementer changes live state.

- [x] **Step 6: Review, spec update, commit, and push**

Fresh read-only Sol review checks spec compliance, chain binding, append ordering, replay-zero, funding consumption, reserve preservation, and secret/prompt exclusion. The primary updates the one-way execution table/evidence, runs the relevant suites, commits, fetches, and pushes only `origin/feat/agent-economy-implementation`.
