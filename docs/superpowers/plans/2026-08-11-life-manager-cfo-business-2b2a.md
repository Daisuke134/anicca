# CFO-2b.2a — RevenueCat Gross Receipt Boundary

> **Execution:** Sol owns this plan/spec/verification. Luna alone writes production code and tests. Follow
> Superpowers TDD: observe RED, make the smallest GREEN, run the gates, then return for fresh Sol review.

**Goal:** Turn existing production Anicca App Store purchase/renewal webhook evidence into closed, privacy-safe,
provider-reported gross receipts without claiming Apple proceeds, payout, bank cash, refund coverage, or profit.

**Ponytail:** One pure function, no new dependency, database, reader, scheduler, state, abstraction, or UI. Reuse
Node `crypto`, `Date`, CommonJS, and the existing CFO test script. Exactly three files; soft target 45 production +
45 test + 1 registration = 91 gross additions, hard maximum 100.

**Source truth:** RevenueCat says `INITIAL_PURCHASE` is a new subscription, `RENEWAL` is a renewed/resubscribed
subscription, and `price_in_purchased_currency` may be unknown, zero for a free trial, or negative for a refund:
https://www.revenuecat.com/docs/integrations/webhooks/event-types-and-fields. Therefore this slice records only a
positive provider gross observation. Apple Finance Detail and MUFG reconciliation remain later gates.

---

## Task 1: Normalize one safe RevenueCat projection

**Files**

- Create: `apps/life-call/lib/cfo-anicca-ios-earning.js`
- Create: `apps/life-call/lib/cfo-anicca-ios-earning.test.js`
- Modify: `apps/life-call/package.json`

### Step 1 — RED

Add the new test file and register it once at the end of `test:cfo`. Import
`normalizeAniccaIosRevenueCatEvent`; the first focused run must fail because the module/export is absent.

The exact positive fixtures are:

```js
const initial = {
  provider_event_id: "evt_initial_123", event_type: "INITIAL_PURCHASE", environment: "PRODUCTION",
  store: "APP_STORE", product_id: "ai.anicca.app.ios.monthly.b", price_decimal: "500", currency: "JPY",
  purchased_at_ms: "1786410123000"
};
const renewal = {
  provider_event_id: "evt_renewal_456", event_type: "RENEWAL", environment: "PRODUCTION",
  store: "APP_STORE", product_id: "ai.anicca.app.ios.monthly", price_decimal: "4.99", currency: "GBP",
  purchased_at_ms: "1786507506000"
};
```

Assert the first result is deep-equal to this exact 13-key object and the renewal differs only in the fixture-derived
source/time/kind/amount fields:

```js
{
  schema_version: 1,
  financial_unit_id: "anicca_ios",
  source_ledger: "revenuecat_subscription_events",
  source_event_id: "revenuecat_subscription:3ee7ac0b2376a0d43980bd2d",
  channel_id: "apple_app_store_anicca",
  occurred_at: "2026-08-11T01:02:03.000Z",
  receipt_kind: "initial_purchase",
  amount: { decimal: "500", currency: "JPY" },
  recognition_status: "provider_reported_gross",
  cash_status: "unknown",
  apple_payout_status: "unavailable",
  refund_coverage: "unknown",
  evidence_status: "provider_reported"
}
```

Also assert both outputs and nested amounts are frozen, both inputs are unchanged, the same provider ID always gives
the same opaque ID, and no raw provider ID/product/secret sentinel occurs in `JSON.stringify(result)`.

In one compact table, assert `null` for a zero/zero-decimal price, `SANDBOX`, `TEST_STORE`, `CANCELLATION`, and a
non-Anicca product. In one compact failure table, assert only
`^cfo_anicca_ios_earning_invalid:invalid_input$` for negative/exponent/numeric/overlong price, lowercase/bad
currency, unsafe/noncanonical time, missing/extra key, malformed provider ID, non-plain/accessor/symbol/proxy shape.
Trap `console.log/error/warn` across the table and assert zero calls and no sentinel in any error.

Run:

```bash
cd apps/life-call
npm ci
node --test lib/cfo-anicca-ios-earning.test.js
```

Expected RED: missing module or missing export only.

### Step 2 — smallest GREEN

Implement one export only:

```js
function normalizeAniccaIosRevenueCatEvent(row) { /* exact contract below */ }
module.exports = { normalizeAniccaIosRevenueCatEvent };
```

Contract order:

1. Inside one `try`, require an ordinary plain object with exactly the eight named string data properties. Reject
   arrays, symbols, extras, missing keys, custom prototype, accessor, or reflection failure before reading values.
2. Bound strings before regex work: provider ID 1–128 `[A-Za-z0-9_-]`, event/environment/store/currency at most 32,
   product 1–128 `[A-Za-z0-9._-]`, price 1–32, time 1–16. Any malformed value throws the fixed error.
3. After structural/type validation, return `null` when environment/store/type/product is not the eligible exact
   combination. For eligible rows require canonical price
   `^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$`; an all-zero value returns `null`, otherwise require uppercase ISO-3 currency.
4. Require canonical positive decimal-millisecond time, convert only after `Number.isSafeInteger`, and require the
   resulting Date to be finite. Hash `revenuecat_subscription:${provider_event_id}` with SHA-256 and retain 24 hex.
5. Build exactly the documented 13-key result. Freeze the two-key amount, then freeze the result. Never include
   `product_id`, raw event ID, commission estimate, customer/transaction/subscriber fields, or any input object.
6. Catch every boundary/reflection/conversion failure and throw a newly-created fixed
   `Error("cfo_anicca_ios_earning_invalid:invalid_input")`; never log, retry, mutate, or return the original error.

Run the focused test again. Expected GREEN: all tests pass.

### Step 3 — verification gates

Run from `apps/life-call`:

```bash
node --check lib/cfo-anicca-ios-earning.js
node --check lib/cfo-anicca-ios-earning.test.js
node --test lib/cfo-anicca-ios-earning.test.js
npm run test:cfo
npm test
git diff --check
```

Then enforce scope from the pre-slice commit: exact changed paths are the three listed files and gross additions are
at most 100. Luna stops and reports instead of adding a helper, dependency, reader, second export, or fourth file.

### Step 4 — real read-only E2E (Sol)

After review, Sol queries Railway production in `BEGIN READ ONLY` using only the eight safe JSONB projections for
production App Store initial/renewal events, feeds every projected row to the committed normalizer, and prints only:
receipt count, ignored count, counts and decimal sums grouped by event kind/currency, fixed status values, and a
boolean privacy check. No raw row, provider ID, product/customer/transaction/subscriber field, or secret is printed or
persisted. Current observed comparison target is 21 positive receipts: initial JPY 4 / 5,100; renewal JPY 14 / 22,100;
renewal GBP 2 / 34.98; renewal USD 1 / 39.99. A mismatch fails the gate; it is never rewritten into zero.

### Step 5 — close

Fresh Sol reviews only the three-file diff for money truth, fixed-error privacy, immutability, tests, and scope. Any
Critical/Important finding goes back to the same Luna. When clean, Sol updates the spec acceptance/evidence, commits
and pushes code and docs, sends a `Codex:::` Telegram milestone with verified messageId, marks 2b.2a complete, and
makes 2b.2b the sole active item.
