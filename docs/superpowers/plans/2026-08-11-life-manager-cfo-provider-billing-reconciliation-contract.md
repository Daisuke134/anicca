# CFO-2a3.1 — Provider Billing Reconciliation Contract Plan

> Workflow: Ponytail full already passed. Execute with Superpowers TDD. Sol plans and verifies; Luna owns all
> production/test/package edits.

**Goal:** Add the smallest pure contract that turns validated Google invoice fields into confirmed provider cost and
reconciles it with a provisional total without deleting, mutating, or falsely upgrading evidence.

**Files and soft targets**

- Create `apps/life-call/lib/cfo-provider-billing-reconciliation.js` — <= 85 added LOC.
- Create `apps/life-call/lib/cfo-provider-billing-reconciliation.test.js` — <= 85 added LOC.
- Modify `apps/life-call/package.json` to register the exact focused test in the explicit `test:cfo` file list — 1 line.

## Task 1: RED

Write three focused tests first:

1. valid JPY invoice normalization plus same-scope reconciliation preserves confirmed and provisional records,
   selects confirmed effective cost, and returns exact `confirmed - provisional` difference;
2. scope and currency mismatch remain unresolved with null difference and do not upgrade the estimate;
3. invalid arithmetic/numeric/identity input fails with only `cfo_provider_billing_invalid:<reason>`, and neither
   success nor failure mutates inputs or leaks sentinel source values.

Run the focused file and record the expected missing-module/contract failure. Do not add more edge-case tests.

## Task 2: GREEN

Implement only:

- `normalizeGoogleCloudInvoice(fields, provenance)`;
- `reconcileProviderBilling(confirmed, provisional)`;
- small internal exact-decimal and validation helpers needed by those two functions.

Use SHA-256 evidence references, exact decimal strings, strict keys, deep-frozen returned records, and redacted stable
errors. The first normalizer accepts the exact Japanese JPY invoice fields frozen in the child spec and verifies
`subtotal + tax = total`. Unresolved reconciliation has `effective = null`; it never promotes one mismatched scope.
Do not add I/O, PDF parsing, Gmail access, storage, OpenTelemetry, DB, scheduler, allocation, or Telegram.

Run the focused test, then `npm run test:cfo`, then full `npm test`.

## Task 3: REVIEW AND CLOSE

Fresh Sol reviewer checks only spec correctness, financial truthfulness, secret leakage, mutation, and unnecessary
scope. Fix required findings through the same Luna. Sol independently reruns syntax, focused test, CFO suite, full
suite, and diff/LOC checks; then updates both CFO specs, commits, pushes, and reports the milestone.
