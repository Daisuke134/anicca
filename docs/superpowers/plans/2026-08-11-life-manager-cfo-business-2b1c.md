# Life Manager Monthly Business Coverage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce one privacy-safe monthly Life Manager business fact from existing revenue, API-cost, token-usage, and shared-subscription evidence without inventing profit.

**Architecture:** Extend the existing pure Life Manager earning module with one synchronous composer. It copies only allowlisted scalar evidence into a recursively frozen result; all aggregation, provider calls, persistence, scheduling, Telegram UI, pricing, and allocation stay outside this slice.

**Tech Stack:** Node.js CommonJS, `node:test`, `node:assert/strict`; no new dependency, database, service, or file.

## Global Constraints

- Ponytail full: reuse the existing module/test; exactly two modified files and at most 100 gross additions.
- Sol plans and verifies; Luna writes production code and tests using strict RED → GREEN TDD.
- Input has exactly seven documented keys. Output contains no raw receipt, provider/customer/account ID, prompt, model output, wallet, email, URL, or secret.
- Unknown is never zero. Profit and ROI are always null in this instrumentation slice.
- On-chain-only receipts require no Stripe reversal work; a future paid Stripe receipt with unresolved reversal coverage must produce partial coverage and `stripe_reversal_unknown`.
- Invalid input throws only `cfo_life_manager_earning_invalid:business_coverage`; no log, retry, clock, environment, network, or storage effect.

## File map and soft target

- Modify `apps/life-call/lib/cfo-life-manager-earning.test.js`: two compact tests, **about 45 additions**.
- Modify `apps/life-call/lib/cfo-life-manager-earning.js`: composer and export, **about 45 additions**.
- Total soft target: **2 files / 90 additions**; hard gate: **2 files / 100 additions**.

---

### Task 1: Compose the closed monthly coverage fact

**Files:**
- Modify: `apps/life-call/lib/cfo-life-manager-earning.test.js`
- Modify: `apps/life-call/lib/cfo-life-manager-earning.js`

**Interfaces:**
- Consumes: `composeLifeManagerBusinessCoverage({ period_start, period_end, earning_ledger, stripe, direct_api_cost, token_usage, shared_subscription })`.
- Produces: one recursively frozen Life Manager fact containing period, revenue coverage/count, three cost evidence blocks, null human/capital/profit/ROI, and sorted coverage exceptions.

- [ ] **Step 1: Write the failing current-month test**

Import `composeLifeManagerBusinessCoverage`, assert it is a function, and call it with this exact fixture:

```js
const current = {
  period_start: "2026-07-31T15:00:00.000Z", period_end: "2026-08-31T15:00:00.000Z",
  earning_ledger: { status: "covered", receipt_count: 0 },
  stripe: { schema_version: 1, financial_unit_id: "life_manager_saas", channel_id: "stripe_life_manager", status: "covered", receipt_count: 0, zero_value_paid_count: 0, reversal_coverage_status: "unknown", receipts: [], evidence_status: "provider_reported" },
  direct_api_cost: { status: "partial", event_count: 20408, estimated_usd: "0.04064343" },
  token_usage: { status: "partial", event_count: 33, total_tokens: 50448879, coverage_exceptions: ["missing_usage", "runner_identity_collision", "unattributed_usage"] },
  shared_subscription: { status: "confirmed_shared_unallocated", amount_minor: "22000", currency: "USD" }
};
```

Assert the exact result below, recursive freeze, input immutability, and absence of `SECRET`, IDs, prompts, wallets,
emails, URLs, or raw rows:

```js
{
  schema_version: 1, financial_unit_id: "life_manager_saas",
  period: { start: current.period_start, end: current.period_end, time_zone: "Asia/Tokyo" }, status: "partial",
  revenue: { coverage_status: "covered_registered_channels", gross_receipt_count: 0, reversal_coverage_status: "not_applicable_no_receipts", landed_cash_coverage_status: "not_applicable_no_receipts" },
  cost: {
    direct_api: { coverage_status: "partial", event_count: 20408, estimated_usd: "0.04064343", evidence_status: "locally_estimated" },
    token_usage: { coverage_status: "partial", event_count: 33, total_tokens: 50448879, evidence_status: "runtime_reported_subtotal" },
    shared_subscription: { coverage_status: "confirmed_shared_unallocated", observed_amount: { minor: "22000", currency: "USD" }, allocated_amount: null },
    human: { coverage_status: "unknown", amount: null }
  },
  capital: { coverage_status: "unknown", amount: null }, profit: null, roi: null,
  coverage_exceptions: ["capital_unknown", "direct_api_cost_partial", "human_cost_unknown", "missing_usage", "runner_identity_collision", "shared_subscription_unallocated", "token_usage_partial", "unattributed_usage"]
}
```

- [ ] **Step 2: Write the compact fail-closed test**

Use a table inside one test. First set `earning_ledger.receipt_count=1` while Stripe remains empty; assert receipt
count `1`, reversal `not_applicable_no_stripe_receipts`, and landed cash `confirmed_agent_wallet`. Then use this exact
positive Stripe collection and assert receipt count `1`, reversal `unknown`, landed cash `partial`,
`stripe_reversal_unknown` present, and profit/ROI null. Move the same receipt outside the monthly period and assert it
is excluded from the monthly count and does not trigger reversal coverage:

```js
{ ...current.stripe, receipt_count: 1, receipts: [{ source_event_id: "stripe_checkout:s1", occurred_at: "2026-08-11T01:02:03.000Z", amount: { minor: "2000", currency: "USD" }, recognition_status: "gross_inflow_unreconciled", landed_cash_status: "confirmed_stripe_balance", bank_landed_status: "unknown", evidence_status: "provider_reported" }] }
```

Then cover: extra top-level key containing `SECRET_SENTINEL`; a mid-month/non-consecutive/equal period; negative or
unsafe counts/tokens; non-canonical decimal; shared `amount_minor` values `"0"` and `"22.00"`; wrong
financial unit/channel/status; mismatched Stripe `receipt_count`; unsorted/unknown/duplicate token exception; wrong
subscription currency/status. Every invalid case must throw exactly
`cfo_life_manager_earning_invalid:business_coverage`, leak no sentinel, mutate no input, and produce no log.

- [ ] **Step 3: Run RED**

Run:

```bash
cd /Users/anicca/anicca-project/.worktrees/cfo-4d1-finalize/apps/life-call
node --test lib/cfo-life-manager-earning.test.js
```

Expected: FAIL because `composeLifeManagerBusinessCoverage` is missing.

- [ ] **Step 4: Implement the minimum composer**

Add one function to the existing module and export it. Reuse `data`, `fail`, and a tiny recursive freeze helper. Check
exact top-level/nested keys before reading values; accept only plain data properties. Require canonical UTC timestamps
representing Tokyo midnight on the first day of consecutive months. With `offset=9*60*60*1000`, shift the start by
`offset`, require UTC day `1` and time `00:00:00.000`, construct the next UTC month-first from the shifted year/month,
subtract `offset`, and require that ISO string to equal `period_end`. Require safe non-negative integers,
`/^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$/` for estimated USD, `/^[1-9][0-9]*$/` for the confirmed subscription minor
amount, and the exact shared status. `earning_ledger.status` and Stripe collection `status` are exactly `covered`;
both cost statuses accept only `covered` or `partial`.
The Stripe collection requires exactly these nine keys and fixed values:

```js
{
  schema_version: 1, financial_unit_id: "life_manager_saas", channel_id: "stripe_life_manager",
  status: "covered", receipt_count: <safe non-negative integer>, zero_value_paid_count: <safe non-negative integer>,
  reversal_coverage_status: "unknown" | "covered", receipts: <dense ordinary array>,
  evidence_status: "provider_reported"
}
```

Require `receipts.length===receipt_count`. Each receipt has exactly the seven top-level keys shown in Step 2's
positive fixture, and its nested `amount` has exactly two keys;
require `source_event_id` to match `stripe_checkout:[A-Za-z0-9_]+`, canonical UTC `occurred_at`, canonical
positive integer `amount.minor`, uppercase ISO-3 `amount.currency`, and the fixed values
`gross_inflow_unreconciled`, `confirmed_stripe_balance`, `unknown`, and `provider_reported`. Token exceptions are a
sorted unique dense ordinary array containing only `missing_usage`, `runner_identity_collision`, or
`unattributed_usage`.

Derive only:

```js
const periodStripeReceipts = input.stripe.receipts.filter(receipt => receipt.occurred_at >= input.period_start && receipt.occurred_at < input.period_end);
const totalReceipts = input.earning_ledger.receipt_count + periodStripeReceipts.length;
const hasStripeReceipts = periodStripeReceipts.length > 0;
const exceptions = ["capital_unknown", "human_cost_unknown", "shared_subscription_unallocated"];
if (input.direct_api_cost.status !== "covered") exceptions.push("direct_api_cost_partial");
if (input.token_usage.status !== "covered") exceptions.push("token_usage_partial");
exceptions.push(...input.token_usage.coverage_exceptions);
if (hasStripeReceipts && input.stripe.reversal_coverage_status !== "covered") exceptions.push("stripe_reversal_unknown");
exceptions.sort();
```

Zero receipts make reversal and landed-cash coverage `not_applicable_no_receipts`. If only on-chain earning receipts
exist, reversal is `not_applicable_no_stripe_receipts` and landed cash is `confirmed_agent_wallet`. Any Stripe receipt
uses Stripe reversal status and landed cash `partial`. Overall status is `complete` only when
`exceptions.length===0`; with the fixed current human, capital, and shared-allocation unknowns this slice therefore
returns `partial`. Never calculate profit or ROI.

- [ ] **Step 5: Run GREEN and regression gates**

Run from `apps/life-call`:

```bash
node --test lib/cfo-life-manager-earning.test.js
npm run test:cfo
npm test
node -c lib/cfo-life-manager-earning.js
git diff --check
```

Expected: all tests and syntax pass; diff check is clean.

- [ ] **Step 6: Prove scope and hand back for review**

Run from the worktree root:

```bash
git diff --numstat 4ba765dff -- apps/life-call/lib/cfo-life-manager-earning.js apps/life-call/lib/cfo-life-manager-earning.test.js
git diff --name-only 4ba765dff
```

Expected: exactly the two planned files and at most 100 gross additions. Do not commit; Sol owns final verification,
the real read-only E2E, spec evidence, commit, and push.
