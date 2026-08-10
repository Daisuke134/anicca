# CFO-2a3b.1 — Pure Provider Allocation Contract Plan

**Status: COMPLETE.** Luna's two-file TDD implementation passed final Sol verification after one fresh-review fix.

> Workflow: Ponytail full → Superpowers GLVS. Sol owns this plan/spec and final verification. Luna owns all
> production/test edits and implementation commands. The same Luna fixes review findings.

**Goal:** Add one pure exact allocation function to the existing provider-billing reconciliation module. It maps
already-normalized official project rows by an explicit versioned rule, refuses a dimension total that does not equal
the confirmed invoice, and always exposes the exact unallocated remainder.

**Public contract:** `allocateProviderBilling(confirmed, rows, policy)`, with policy exact keys
`{ version, mappings }`, positive-safe-integer `version`, and mapping exact keys `{ project_ref, business_id }`.
Every invalid allocation fails with only `cfo_provider_billing_invalid:invalid_allocation`.

**Not in this slice:** CSV/browser/BigQuery, I/O/state, DB/SQL, scheduler, retry, OTel, Telegram, UI, generic plugin
interfaces, or guessed allocation.

## Size gate

| File | Ownership | Soft target |
|---|---|---:|
| `apps/life-call/lib/cfo-provider-billing-reconciliation.js` | Luna production | <= 55 added LOC |
| `apps/life-call/lib/cfo-provider-billing-reconciliation.test.js` | Luna test | <= 80 added LOC |
| Total | exactly 2 existing files | <= 135 added LOC |

No manifest, lockfile, new file, dependency, or refactor. If the gate cannot hold, Luna stops and reports before code.

## Superpowers GLVS

### Goal

Implement the exact CFO-2a3b.1 contract and nothing after it.

### Loop

1. Add the smallest focused RED cases first: mapped + unmapped + signed rows with exact conservation; then minimum
   money/redaction regressions for mismatch, duplicate mapping, invalid decimal, and hostile shape.
2. Run only the focused test and capture the expected missing-function/behavior RED.
3. Add the pure function in the existing module, reusing its validation/freeze/exact-decimal style. No I/O.
4. Run focused GREEN, then `npm run test:cfo`, `npm test`, `node --check` on both files, `git diff --check`, and LOC.
5. Return exact commands/evidence and no commit/push. Sol performs fresh review, final verification, spec state,
   commit/push, and milestone report.

### Verify

- input total must equal confirmed invoice before mapping;
- exact mapping only by hashed project reference and explicit version;
- deterministic per-business totals and exact unallocated remainder;
- exact signed decimal arithmetic, never `Number`;
- frozen output, unchanged input, stable redacted errors;
- zero third file, I/O, side effect, dependency, or next-slice code.

### State

On pass, mark only CFO-2a3b.1 complete. CFO-2a3b.2 remains first unfinished until a real official dimension source
exists. Do not mark CFO-2a3b complete from fixture-only evidence.

## Completion

- Final diff: production +26/-9, test +37/-1, two existing files only.
- Verification: focused `6/6`, CFO `323/323`, full `npm test`, syntax, diff, and LOC gates passed.
- Fresh review found coercible nested refs/period; the same Luna reproduced it RED and fixed it with strict string
  boundaries. Sol independently reran the final suite. CFO-2a3b.2 is next.
