# Life Manager CFO-2b — Business Instrumentation

| Field | Value |
|---|---|
| Status | ACTIVE — Life Manager complete; `CFO-2b.2` Anicca iOS is the only active slice |
| Parent | `docs/superpowers/specs/2026-08-06-life-manager-cfo-design.md` |
| Runtime | Local `apps/life-call`; existing ledgers and provider APIs only |
| Role split | Sol specifies/verifies; Luna implements production code/tests |

## 1. Goal

Instrument every financial unit in registry order without turning missing evidence into zero. Each unit eventually
produces the same business fact: revenue receipts, landed cash, direct cost, token usage, API cost, human cost,
capital employed, and coverage. `CFO-2c` reconciles those facts; only then may `CFO-2d` publish profit or ROI.

## 2. Ponytail decision

Reuse the existing registry, `lm_agent_earnings`, Stripe, provider-billing, and usage ledgers. Do not add a database,
generic accounting framework, dashboard, or Telegram business screen in CFO-2b. Each slice changes at most three
files and targets at most 100 added lines. A slice that exceeds either bound is split before Luna starts.

```mermaid
flowchart LR
    R[Registry order] --> B[One business]
    B --> REV[Revenue receipts]
    B --> CASH[Landed cash]
    B --> COST[Direct/API/human cost]
    B --> CAP[Capital employed]
    REV --> FACT[Closed business fact]
    CASH --> FACT
    COST --> FACT
    CAP --> FACT
    FACT --> REC[CFO-2c reconcile]
    REC --> UI[CFO-2d profit + Telegram]
```

## 3. Ordered work

Only the first unchecked item is active.

- [x] **CFO-2b.1 — Life Manager**
  - [x] **2b.1a** Normalize finalized TaskMarket/uGig external settlements already stored in `lm_agent_earnings`.
  - [x] **2b.1b** Read the canonical Life Manager Stripe Payment Link and normalize paid Checkout receipts; a paid
        Checkout balance is not bank-landed cash.
  - [x] **2b.1c** Compose one closed Life Manager monthly coverage fact from the existing revenue, direct-cost,
        local-usage, and shared-subscription evidence. With no paid Stripe receipt, reversal/payout work is not
        applicable; the first future paid receipt changes coverage to partial and blocks profit until reconciliation.
- [ ] **CFO-2b.2 — Anicca iOS**: Apple/RevenueCat receipts, payout state, attributed API cost.
- [ ] **CFO-2b.3 — Writer Agent**: publisher receipts and its measured runtime cost.
- [ ] **CFO-2b.4 — Affiliate Agent**: network commission receipts and runtime cost.
- [ ] **CFO-2b.5 — Gig Work**: marketplace/client receipts; never import `~/gig/earnings.jsonl` without receipt proof.
- [ ] **CFO-2b.6 — x402 Services**: finalized external on-chain sales; self-transfers are excluded.
- [ ] **CFO-2b.7 — Employment Income**: payroll/bank receipt, kept as personal income rather than business revenue.
- [ ] **CFO-2b.8 — Capafy Marketplace**: landed sales receipts and costs.
- [ ] **CFO-2b.9 — Proprietary Investing**: realized reconciled P&L only; deposits/internal moves are excluded.

## 4. Current measured truth

- The canonical Life Manager Stripe link resolves to six Checkout Sessions and zero paid sessions. This is a
  confirmed zero only for that channel and observation, not a claim that the whole business earned zero.
- The live append-only `lm_agent_earnings` table contains two rows: one `x402_sale` external income and one
  `polymarket_cycle` realized loss. Neither belongs to Life Manager.
- Life Manager's canonical ledger producers use `source=taskmarket_work` and `source=ugig_work`. Both write only
  after an external finalized on-chain receipt. No matching live row exists now, so 2b.1a's real E2E must return an
  empty receipt list, not a fabricated zero-money receipt.
- Existing Life Manager cost and token evidence is real but incomplete. Confirmed Anthropic subscription cash cost
  is shared until the versioned allocation gate closes; it is not silently charged 100% to Life Manager.
- The latest completion read of the current Tokyo month contains 20,421 `lm_api_cost` rows with a locally-estimated
  USD subtotal of `0.04064343`.
  The two durable local-usage chains contain 33 Life Manager-attributed events and 50,448,879 reported tokens for
  that period. Both chains also report missing usage, runner-identity collisions, and unattributed usage, so the
  token count is an observed subtotal, never a complete cost. The live provider-usage table is absent from the
  queried deployment (HTTP 404), so provider/API spend remains incomplete.

## 5. CFO-2b.1a exact contract

`normalizeLifeManagerEarningReceipt(row)` accepts one plain `lm_agent_earnings` row only when all of these are true:

- `kind=financial_external_income`;
- `source` is exactly `taskmarket_work` or `ugig_work`;
- `public_ref` is a UUID, `occurred_at` is a valid timestamp, and `tx_hash` is a supported non-empty chain receipt;
- `currency=USD`, `amount_atomic` is either the producers' canonical positive decimal string or a positive safe
  integer returned by a JSON database client, `amount_decimals` is an integer from 0 through 6, and `amount_minor`
  is null. Numeric input above JavaScript's safe-integer boundary fails closed; it is never rounded;
- `meta.finalized=true` and `meta.external=true`.

It returns exactly:

```json
{
  "schema_version": 1,
  "financial_unit_id": "life_manager_saas",
  "source_ledger": "lm_agent_earnings",
  "source_event_id": "lm_agent_earnings:<public_ref>",
  "channel_id": "taskmarket_life_manager",
  "occurred_at": "2026-08-11T01:02:03.000Z",
  "amount": { "atomic": "2500000", "decimals": 6, "currency": "USD" },
  "landed_cash_status": "confirmed_agent_wallet",
  "evidence_status": "onchain_finalized_external_settlement"
}
```

`ugig_work` maps only to `ugig_life_manager`. Wallet, transaction hash, entry key, metadata, payer, prompt, and any
unknown input field never leave this boundary. Invalid input throws only
`cfo_life_manager_earning_invalid:<fixed_reason>`. The function is pure, freezes its output, and does no I/O.

## 6. Acceptance for 2b.1a

- [x] Exact TaskMarket and uGig fixtures map to the two canonical Life Manager channels.
- [x] A compact money-truth regression covers another business source, non-external/non-finalized settlement,
      zero/unsafe/ambiguous amount, and malformed identity. All fail closed without leakage; privacy-sensitive and
      unknown source fields are accepted only as input evidence and are stripped from the closed result.
- [x] Inputs are unchanged; output and nested amount are frozen and contain only the nine documented keys.
- [x] The real read-only filtered ledger query succeeds and returns the observed empty list without claiming whole-
      business revenue zero.
- [x] Focused, CFO, and full tests pass; scope is at most three files and 100 additions; commit and push succeed.

## 7. CFO-2b.1a completion evidence

- Code commit `58ba18903` implements the exact privacy-safe receipt boundary in three files with 85 gross additions.
- Focused 4/4, CFO 337/337, and the full `apps/life-call` suite pass; syntax and `git diff --check` pass.
- Fresh Sol review is `ship` after two real prefix-spoof privacy regressions were fixed with an internal `WeakSet`
  origin tag. Direct and nested hostile Proxy failures now return only the fixed `invalid_input` error.
- Real read-only PostgREST E2E returned HTTP 200, zero matching TaskMarket/uGig source rows, zero normalized receipts,
  `whole_business_zero_claimed=false`, and no private field escape. This proves the current channel observation without
  manufacturing a zero-value revenue receipt.
- No database, provider, local-state, launchd, Telegram, or external-system write occurred.

## 8. CFO-2b.1b contract — Stripe paid Checkout receipts

Extend the existing Life Manager earning module with one read-only
`collectLifeManagerStripeReceipts({ stripeKey, paymentLinkUrl, fetchImpl })` source. It paginates Stripe Payment Links,
matches exactly the canonical `https://buy.stripe.com/<slug>` URL, then paginates only that link's Checkout Sessions.
It performs no write, retry, clock read, environment read, log, or customer-data persistence.

```mermaid
flowchart LR
    REG[Canonical LM link] --> LINKS[Stripe Payment Links]
    LINKS --> SESS[Checkout Sessions]
    SESS -->|paid + positive| REV[Revenue receipt]
    SESS -->|unpaid/no payment| IGN[No revenue receipt]
    REV --> BAL[Confirmed in Stripe balance]
    BAL -. separate later evidence .-> BANK[MUFG landed cash]
```

The closed collection result is:

```json
{
  "schema_version": 1,
  "financial_unit_id": "life_manager_saas",
  "channel_id": "stripe_life_manager",
  "status": "covered",
  "receipt_count": 1,
  "zero_value_paid_count": 0,
  "reversal_coverage_status": "unknown",
  "receipts": [{
    "source_event_id": "stripe_checkout:<opaque session id>",
    "occurred_at": "2026-08-11T01:02:03.000Z",
    "amount": { "minor": "2000", "currency": "USD" },
    "recognition_status": "gross_inflow_unreconciled",
    "landed_cash_status": "confirmed_stripe_balance",
    "bank_landed_status": "unknown",
    "evidence_status": "provider_reported"
  }],
  "evidence_status": "provider_reported"
}
```

Rules:

- Only `payment_status=paid`, `status=complete`, live-mode sessions for the matched Payment Link are gross external
  payment receipts. They are not net revenue or contribution profit before reversal reconciliation.
- Decision order is fixed. Every session first requires a valid opaque ID, the matched link ID, live mode, and known
  Checkout/payment status. Only `payment_status=paid` then requires `status=complete`, valid creation time, a
  non-negative safe-integer `amount_total`, and lowercase ISO-3 currency. A paid zero-value trial increments
  `zero_value_paid_count` and never becomes revenue. `unpaid` and `no_payment_required` create no receipt and may have
  null amount/currency; the collector does not reject those valid ignorable shapes.
- Currency is provider lowercase ISO-3 and becomes uppercase. Session creation seconds become canonical UTC.
- Duplicate session IDs, conflicting link IDs, malformed pages, pagination beyond 100 pages, network/JSON failures,
  unsafe money, or invalid required fields fail closed with fixed redacted errors and no retry.
- Customer, email, address, phone, client reference, payment intent, URL, metadata, and raw provider objects are never
  copied to output or errors. Receipts sort deterministically by time then opaque source-event ID and are frozen.
- `confirmed_stripe_balance` is not MUFG arrival. `bank_landed_status` remains `unknown` until a payout and bank receipt
  are reconciled in a later slice. Refunds, disputes, fees, net, and payout state are deferred to 2b.1c rather than
  inferred. Until then `reversal_coverage_status=unknown` and every receipt is `gross_inflow_unreconciled`; CFO-2b.1b
  alone cannot enable a business revenue total, profit, ROI, or allocation decision.

Current real acceptance: 54 active Payment Links fit one page; the canonical Life Manager link has six sessions, all
`unpaid`, so the correct result is `status=covered`, `receipt_count=0`, and no whole-business zero-revenue claim.

### CFO-2b.1b completion evidence

- Code commit `4ba765dff` adds the paginated read-only Stripe collector in the existing two files with 62 gross
  additions and no dependency, database, scheduler, state, or Telegram change.
- Focused 6/6, CFO 339/339, and the full `apps/life-call` suite pass; syntax, diff, exact two-file scope, and the
  100-line gate pass. Fresh Sol review is `ship` with no Critical/Important finding.
- Real live-key read-only E2E made two GETs: one Payment Links page and one canonical Sessions page. It observed six
  `unpaid` sessions, returned `status=covered`, zero gross receipts, zero paid-zero observations, reversal coverage
  `unknown`, and no forbidden field escape. No ID, amount, URL, customer, email, or raw provider object was printed.
- The result cannot enable revenue, profit, ROI, or capital advice: every future paid receipt is explicitly gross and
  unreconciled until 2b.1c reads refunds/disputes/fees/payout evidence.

## 9. Source decisions

- Stripe Checkout Session object: `payment_status=paid` means funds are available in the Stripe account, not the
  owner's bank. https://docs.stripe.com/api/checkout/sessions/object
- Stripe Balance Transaction object: amount, fee, and net represent movement through the Stripe balance.
  https://docs.stripe.com/api/balance_transactions/object
- Stripe payout reconciliation: bank payout reconciliation is a separate evidence step.
  https://docs.stripe.com/payouts/reconciliation?locale=ja-JP

## 10. CFO-2b.1c contract — closed monthly business coverage fact

Add one pure `composeLifeManagerBusinessCoverage(input)` function to the existing earning module. It accepts only
the already-sanitized monthly observations below; it performs no I/O, conversion, pricing, allocation, or logging.

```mermaid
flowchart LR
    REV[Registered revenue channels] --> FACT[Life Manager monthly fact]
    API[API-cost ledger] --> FACT
    TOK[Local token ledgers] --> FACT
    SUB[Confirmed shared subscription] --> FACT
    FACT -->|any incomplete source| NULL[Profit + ROI = null]
    FACT -->|future paid Stripe receipt| RECON[Require reversal + payout reconciliation]
```

The exact input has seven keys:

```json
{
  "period_start": "2026-07-31T15:00:00.000Z",
  "period_end": "2026-08-31T15:00:00.000Z",
  "earning_ledger": { "status": "covered", "receipt_count": 0 },
  "stripe": "<closed collectLifeManagerStripeReceipts result>",
  "direct_api_cost": { "status": "partial", "event_count": 20408, "estimated_usd": "0.04064343" },
  "token_usage": { "status": "partial", "event_count": 33, "total_tokens": 50448879, "coverage_exceptions": ["missing_usage", "runner_identity_collision", "unattributed_usage"] },
  "shared_subscription": { "status": "confirmed_shared_unallocated", "amount_minor": "22000", "currency": "USD" }
}
```

Rules:

- Period bounds are canonical UTC for midnight on the first day of consecutive Tokyo calendar months; arbitrary or
  partial intervals fail closed. Counts and tokens are non-negative safe integers. `estimated_usd` is a canonical
  non-negative decimal string; confirmed shared `amount_minor` is a canonical positive integer string. Neither is
  recomputed.
- Revenue coverage means only the registered Stripe, TaskMarket, and uGig channels were read successfully. The fact
  reports only receipts whose canonical timestamp falls inside the half-open monthly period; older/newer Stripe
  receipts remain valid provider evidence but are excluded from this month's count. It does not infer revenue from
  list price, active subscriptions, or unpaid sessions.
- When the combined receipt count is zero, reversal and landed-cash coverage are
  `not_applicable_no_receipts`. When only finalized TaskMarket/uGig receipts exist, Stripe reversal is
  `not_applicable_no_stripe_receipts` and landed cash is `confirmed_agent_wallet`. When Stripe has any paid receipt
  and still reports reversal coverage `unknown`, the business fact is partial and includes
  `stripe_reversal_unknown`; landed cash stays partial and profit/ROI stay null. This is the enduring fail-closed
  upgrade trigger for a later real reversal/payout adapter.
- Direct API cost stays `locally_estimated`; local token usage stays a reported subtotal when any source exception is
  present. The confirmed `$220` Anthropic receipt is visible only as shared observed spend; allocated business amount
  remains null until `CFO-2a3b` closes. Human cost and capital remain null/unknown.
- Output is closed and recursively frozen. It contains no receipt/provider ID, prompt, model output, wallet, account,
  customer, email, raw row, or secret. Invalid input throws only
  `cfo_life_manager_earning_invalid:business_coverage`.

The current real result must therefore say: registered revenue receipt count `0`; API-cost subtotal
`$0.04064343` partial; token subtotal `50,448,879` partial; shared subscription `$220` unallocated; human cost,
capital, profit, and ROI unknown/null. It must not say Life Manager profit is zero.

### CFO-2b.1c acceptance

- [x] One exact current-month fixture returns the closed frozen fact and preserves every unknown as null/partial.
- [x] One compact regression proves the separate on-chain-only and paid-Stripe branches, proves unresolved Stripe
      reversal cannot enable profit, and makes malformed/secret-bearing input return only the fixed redacted error.
- [x] Focused, CFO, and full tests pass; exact scope is the existing two files with at most 100 gross additions.
- [x] A read-only real E2E recomputes the measured counts from source ledgers, feeds the composer, and prints only the
      closed fact summary; it performs no database, Stripe, launchd, Telegram, or local-state write.

### CFO-2b.1c completion evidence

- Code commits `7426ef747` and `53c656330` add the composer and its review fixes in the existing two files with 32
  gross additions from base. No dependency, schema, scheduler, provider, persistence, or Telegram path changed.
- TDD observed the missing-function RED, then focused 8/8, CFO 341/341, full `npm test`, syntax, diff, and exact scope
  gates passed. Fix-round RED proved combined safe counts could overflow before the aggregate guard was added.
- Fresh Sol review found and closed fixed-error remapping and false period-test defects. Scoped re-review is `ship`:
  hostile shapes return only `business_coverage`, primitive periods reach the month validator, invalid Stripe status
  fails, and combined receipt count overflow fails closed.
- Real read-only E2E observed zero registered revenue receipts, 20,421 locally-estimated API-cost rows totaling
  `$0.04064343`, 33 Life Manager-attributed local-usage events totaling 50,448,879 reported tokens, an absent live
  provider-usage table, and the confirmed shared `$220` subscription. The resulting fact is partial; human cost,
  capital, allocated subscription, profit, and ROI remain null. No raw/provider/customer/account identifier escaped.
- No database, Stripe, launchd, Telegram, or local-state write occurred. The next active registry unit is Anicca iOS.
