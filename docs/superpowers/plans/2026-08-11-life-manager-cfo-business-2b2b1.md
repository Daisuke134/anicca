# CFO-2b.2b1 — Signed Apple Finance Detail Row

> **Execution:** Sol owns spec/plan/verification. Luna alone writes production code and tests. Follow Superpowers
> TDD: RED, smallest GREEN, fresh review, real read-only E2E, commit/push.

**Goal:** Normalize one allowlisted Anicca Apple Finance Detail sale or return into exact signed Partner Share without
claiming Apple payout, MUFG arrival, current-period completeness, profit, or FX conversion.

**Ponytail:** Extend the existing Anicca module and test only. No parser, file/API reader, dependency, helper file,
state, scheduler, DB, UI, or Telegram change. Soft target 40 production + 40 test = 80 gross additions; hard maximum
two files and 100 additions.

**Measured source:** `asc finance reports --help` defines `FINANCE_DETAIL` as the Z1-only detailed Apple fiscal
report with transaction and settlement dates. The downloaded reports have signed `Extended Partner Share`; observed
returns already have negative quantity and total, so a second sign reversal would falsify money.

---

## Task 1: Pure Apple finance row boundary

**Files**

- Modify: `apps/life-call/lib/cfo-anicca-ios-earning.js`
- Modify: `apps/life-call/lib/cfo-anicca-ios-earning.test.js`

### Step 1 — RED

Import the absent `normalizeAniccaIosAppleFinanceRow` from the existing module and add these exact fixtures:

```js
const appleSale = {
  fiscal_month: "2026-10", row_ordinal: 1, transaction_date: "07/06/2026",
  settlement_date: "07/06/2026", apple_identifier: "6769264298",
  sku: "ai.anicca.app.ios.monthly.b", quantity: "1", partner_share_decimal: "425",
  extended_partner_share_decimal: "425", currency: "JPY", sale_or_return: "S"
};
const appleReturn = {
  fiscal_month: "2026-07", row_ordinal: 7, transaction_date: "04/01/2026",
  settlement_date: "04/02/2026", apple_identifier: "6755320744",
  sku: "ai.anicca.app.ios.annual", quantity: "-1", partner_share_decimal: "17.39",
  extended_partner_share_decimal: "-17.39", currency: "GBP", sale_or_return: "R"
};
```

The first exact result is:

```js
{
  schema_version: 1,
  financial_unit_id: "anicca_ios",
  source_ledger: "apple_finance_detail",
  source_event_id: "apple_finance_detail:0cb21fcae317766dd43dfb5c",
  channel_id: "apple_app_store_anicca",
  fiscal_month: "2026-10",
  transaction_date: "2026-07-06",
  settlement_date: "2026-07-06",
  receipt_kind: "sale",
  quantity: "1",
  unit_partner_share_decimal: "425",
  amount: { decimal: "425", currency: "JPY" },
  recognition_status: "apple_finance_reported_partner_share",
  payout_status: "unknown",
  bank_landed_status: "unknown",
  evidence_status: "apple_finance_detail"
}
```

The return is the same closed shape with source hash `45b5a38ea1dfaebea1498b70`, fiscal/date fixture values,
`receipt_kind="return"`, quantity `-1`, unit share `17.39`, and amount `-17.39 GBP`. Assert exact key sets, input
unchanged, repeated hash equality, result/amount frozen, no raw Apple ID/SKU/title/developer/vendor/customer/promo/
order/region sentinel in output, fixed error, or logs.

One compact `null` table covers a wholly unregistered Apple-ID/SKU pair. One compact failure table covers partial or
crossed registered identity; bad/unsafe ordinal; malformed fiscal month; impossible/reversed dates; zero, unsafe, or
sign-inconsistent quantity; malformed/negative/zero unit share; malformed/zero/wrong-sign extended share; exact
multiplication mismatch; bad currency/S-R; missing/extra/symbol/accessor/custom-prototype/transparent/throwing Proxy.
Every failure must match only `^cfo_anicca_ios_earning_invalid:apple_finance_row$`, remain silent, and not mutate input.

Run from `apps/life-call`:

```bash
node --test lib/cfo-anicca-ios-earning.test.js
```

Expected RED: missing export/function assertion only.

### Step 2 — smallest GREEN

Add exactly one export. Do not refactor or change the existing RevenueCat function.

```js
function normalizeAniccaIosAppleFinanceRow(row) { /* exact contract */ }
module.exports = { normalizeAniccaIosRevenueCatEvent, normalizeAniccaIosAppleFinanceRow };
```

Implementation order:

1. In one fixed-error `try/catch`, reject null/array/proxy/custom prototype. Require exact eleven own enumerable string
   data keys except `row_ordinal`, which is a positive safe integer. Reject symbols, extras, missing keys, accessors,
   reflection failure, and overlong strings before regex/BigInt/Date work.
2. Use this exact frozen allowlist: app `6755129214/anicca-ios-001`; subscriptions
   `6755320744/ai.anicca.app.ios.annual`, `6755320627/ai.anicca.app.ios.monthly`,
   `6762049696/ai.anicca.app.ios.yearly.b`, `6769264298/ai.anicca.app.ios.monthly.b`,
   `6762049888/ai.anicca.app.ios.weekly.b`, `6762320930/ai.anicca.app.ios.yearly.retention`, and
   `6758591116/Anicca`. Return `null` only when both ID and SKU are wholly unregistered. Any one-sided/cross-pair
   recognition fails closed.
3. Define `row_ordinal` as the 1-based position among all original report data rows before Anicca filtering, excluding
   the three metadata rows, header, and footer; the later parser must preserve it unchanged. Require that integer to
   be 1–1,000,000; exact fiscal regex `^[0-9]{4}-(0[1-9]|1[0-2])$`; ten-digit Apple ID;
   and SKU regex `^[A-Za-z0-9._-]{1,128}$` before the pair decision. Validate real `MM/DD/YYYY` dates by UTC calendar
   components, require transaction <= settlement, and return only
   `YYYY-MM-DD`. Validate fiscal `YYYY-MM`, but do not reinterpret it as a calendar transaction month.
4. Without `Number`, require quantity `^-?[1-9][0-9]{0,15}$`; unit share
   `^(?:0|[1-9][0-9]{0,15})(?:\.[0-9]{1,8})?$`; and Extended share
   `^-?(?:0|[1-9][0-9]{0,15})(?:\.[0-9]{1,8})?$`. Leading plus/zero, exponent, whitespace, more digits/scale,
   numeric values, and negative zero fail; provider trailing fractional zeros are preserved. Parse signed decimal
   numerator/scale with `BigInt`.
   Require positive nonzero unit share; nonzero signed quantity/extended amount; S has positive quantity/extended and
   R has negative quantity/extended; prove exact equality across scales:
   `unitNumerator × quantity × 10^extendedScale === extendedNumerator × 10^unitScale`.
5. Hash the exact pipe-joined sequence `apple_finance_detail` plus the eleven input values in documented key order;
   retain 24 hex and prefix `apple_finance_detail:`. Build/freeze exactly the documented 16-key output and nested
   two-key amount. Do not return an input object or identifier.
6. Catch everything and throw a new fixed `Error("cfo_anicca_ios_earning_invalid:apple_finance_row")`; never log,
   retry, mutate, convert currency, infer payout/bank cash, or perform I/O.

Run focused until GREEN.

### Step 3 — verification

```bash
node --check lib/cfo-anicca-ios-earning.js
node --check lib/cfo-anicca-ios-earning.test.js
node --test lib/cfo-anicca-ios-earning.test.js
npm run test:cfo
npm test
git diff --check
```

Enforce exact two changed files and at most 100 gross additions from commit `98f46bb71`. Luna stops instead of adding
a parser/reader, changing package registration, or modifying the completed RevenueCat contract.

### Step 4 — real read-only E2E (Sol)

In memory only, read the four already-downloaded completed FINANCE_DETAIL files. Validate metadata/header/footer only
enough to produce the exact eleven safe projections; never print or persist vendor, title, developer, other-app row,
country, customer price, promo, order, region, Apple ID, or SKU. Pass all 18 Anicca projections through the committed
normalizer and require exact unique opaque IDs, signed multiplication, privacy, and grouped totals:

- fiscal 2026-07: 12 rows; JPY 7,326; GBP -14.50; USD 28;
- fiscal 2026-08: 3 rows; JPY 9,472;
- fiscal 2026-09: 2 rows; JPY 1,184;
- fiscal 2026-10: 1 row; JPY 425.

Print only those counts/totals and fixed `payout_status=unknown`, `bank_landed_status=unknown`, `profit_claimed=false`.
Any mismatch fails; it is never rewritten to zero.

### Step 5 — close

Fresh Sol reviews the exact two-file diff. Critical/Important findings return to the same Luna. Sol reruns gates and
real E2E, updates spec evidence, commits/pushes code and docs, sends one deduped `Codex:::` Telegram milestone with
verified messageId, marks 2b.2b1 complete, and makes the complete-report parser 2b.2b2 the sole active item.
