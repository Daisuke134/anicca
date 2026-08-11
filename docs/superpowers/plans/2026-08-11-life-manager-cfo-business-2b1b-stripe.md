# CFO-2b.1b Life Manager Stripe Receipts — Implementation Plan

> Ponytail `full` first, then Superpowers TDD. Sol owns plan/final verification; Luna edits production/tests only.

Implementation target is `/Users/anicca/anicca-project/.worktrees/cfo-4d1-finalize` on
`feature/cfo-4d1-finalize-sol` after code commit `58ba18903`. That commit already contains and registers the existing
module/test; no merge, cherry-pick, or `package.json` edit is part of this slice.

## Goal and scope

Add one read-only paginated Stripe collector to the existing Life Manager earning boundary. It recognizes only paid,
positive gross Checkout inflows on the canonical Life Manager Payment Link and distinguishes Stripe-balance
availability from MUFG bank arrival. It does not calculate refund-adjusted revenue, dispute loss, fee, net profit,
MRR, or list-price revenue; reversal coverage remains explicitly unknown until 2b.1c.

| Element | Files | Soft target |
|---|---:|---:|
| Collector | `apps/life-call/lib/cfo-life-manager-earning.js` | <=50 added LOC |
| Tests | `apps/life-call/lib/cfo-life-manager-earning.test.js` | <=45 added LOC |
| Total | 2 | <=95 additions; hard stop at 100 |

## Task 1 — RED

Extend the existing test with two compact cases.

1. A paginated provider fixture has the canonical link on page two and sessions on two pages: one paid positive,
   one paid zero, one unpaid, and one `no_payment_required` with null amount/currency. Assert exact request URLs/one Bearer header, exact frozen collection/receipt shapes,
   deterministic order, `receipt_count=1`, `zero_value_paid_count=1`, reversal coverage unknown, exact
   `gross_inflow_unreconciled`, Stripe balance confirmed, bank unknown, and no customer/email/metadata/secret sentinel
   in serialized result or errors.
2. One table covers duplicate session ID, unsafe/negative paid amount, paid-but-incomplete session, wrong-link
   session, test-mode session, malformed page/JSON, network failure, missing canonical link, and a 101-page
   non-terminating feed. Every listed row fails closed; unpaid/no-payment rows are not in the failure table. Assert no
   retry after a failure and only `^cfo_life_manager_earning_invalid:stripe_[a-z_]+$` errors.

Run focused test and confirm RED because the new export is missing.

## Task 2 — GREEN

Add `collectLifeManagerStripeReceipts` to the existing module and export. Reuse the internal tagged error boundary.
Validate three exact options without reading environment state. Implement one bounded `list` helper for both Stripe
list endpoints with `limit=100`, `starting_after`, exact response/data/has_more validation, progress by the last opaque
ID, and a 100-page ceiling. Use injected `fetchImpl`, fixed Stripe API origin, one GET, one Authorization header, no
body, no retry, and no log.

Match exactly one live canonical Payment Link URL. For every session validate opaque ID, link identity, live flag,
and known payment/status enums first. For paid sessions only, require complete status, creation time, non-negative safe
amount, and ISO currency; ignore unpaid/no-payment sessions without reading nullable money fields. Deduplicate IDs,
sort/freeze the closed output, and strip all raw/customer fields. Preserve zero as a non-revenue paid observation.
Do not inspect or infer refund/dispute state; label the collection and receipts unreconciled exactly as the spec.

Run focused, `npm run test:cfo`, `npm test`, syntax, diff, exact two-file scope, and <=100 gross-addition gates.

## Task 3 — Real read-only E2E

Sol calls the collector with the actual Stripe live key and the canonical URL already stored in
`apps/landing/monitors/registry.json`. Print only HTTP success, page counts, status counts, receipt count,
zero-value-paid count, `whole_business_zero_claimed=false`, and forbidden-field escape boolean. Current expected truth
is 54 active links, six canonical sessions, all unpaid, and zero receipts. Do not print IDs, amounts, URLs, customers,
emails, or raw JSON.

## Task 4 — Review and closure

Fresh Sol reviews only money truth, misattribution, double counting, pagination/data loss, duplicate effects, and
privacy. Luna fixes bounded findings. Sol updates the child SSOT, commits/pushes code and docs, and sends one
`Codex:::` Telegram milestone naming 2b.1c as the next active slice. No launchd trigger or Telegram finance report is
part of this slice because hourly composition waits for 2b.1c.
