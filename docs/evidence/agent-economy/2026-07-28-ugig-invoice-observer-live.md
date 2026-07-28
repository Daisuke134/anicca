# uGig accepted-work invoice observer — production evidence

## Outcome

Life Manager now observes delivered uGig applications every five minutes and
can issue an exact capped invoice without a human after the category-specific
external gates become true:

1. the buyer changes the application to `accepted`; and
2. code work has every configured GitHub pull request merged, while art,
   marketing, and other work has a public HTTPS proof URL; and
3. after uGig changes the application to `completed`, a `paid` invoice enters
   revenue only when its `merchant_tx_hash` is independently `finalized` on
   Solana, the configured recipient balance increased by at least the exact
   `amount_crypto`, and the fee payer is not an owned wallet.

The current application remains `pending`, so the live run truthfully performed
zero invoice reads, zero pull-request reads, and zero mutations.

## External work being observed

| Field | Verified value |
|---|---|
| uGig gig | `2b410cad-7cc9-44fd-b2f1-843d9eae6c24` |
| application | `5e315cfd-33fc-433b-a5f0-3cfcdc27a9a4` |
| external buyer | `chovy` |
| promised amount | `$1 USD`, paid in SOL |
| delivery | <https://github.com/profullstack/aiornot.vote/pull/100> |
| delivery commit | `a0424042815523f438f85c333938af691a9741f8` |
| observer PR | <https://github.com/Daisuke134/life-manager/pull/1217> |
| merged Life Manager commit | `f4b52f75d92c91ccffb92316953a6c0b48b7f129` |
| settlement PR | <https://github.com/Daisuke134/life-manager/pull/1221> |
| settlement merge | `a9edfe883e9a367f5e595087f393f3f4c44047aa` |

| Category | Gig / application | Cap | Public delivery |
| --- | --- | --- | --- |
| code | `2b410cad…` / `5e315cfd…` | `$1` | [AIorNot.vote PR #100](https://github.com/profullstack/aiornot.vote/pull/100) |
| code | `d9778d45…` / `f8960763…` | `$0.25` | [moshcode PR #61](https://github.com/moshcoder/moshcode/pull/61) |
| marketing | `1eea7af1…` / `7e636f57…` | `$0.25` | [PairUX provider readback](https://pairux.com/@moshcoding) |
| art | `174bfd02…` / `85654162…` | `$20` | [NIGHTCELL 7 PR #38](https://github.com/profullstack/nightcell7/pull/38) |

The same authenticated readback also confirms the second live uGig acquisition
attempt: Crawlproof testimonial gig
`4cdf4cde-f845-4db4-9618-4994da483ab2`, application
`963943b0-829d-4f6c-a28e-c898e222c9a0`, proposed rate `$2`, status `pending`.
Its cover letter explicitly identifies the deliverable as Life Manager AI
narration; it does not impersonate a human customer. It is not in the delivery
observer config because no accepted deliverable exists yet.

## Verification

| Check | Result |
|---|---|
| TDD RED | completed/paid tests failed because the observer rejected `completed`, the settlement module was absent, and the DB constraints were EVM-only |
| focused GREEN | observer, settlement, ledger, runtime, migration, and production-script suites all exit 0 |
| Life Manager full suite | `npm test` exit 0 before merge |
| shell syntax | PASS |
| plist lint | PASS |
| upstream contract readback | real route is `GET /api/gigs/[id]/invoice`; payment sync changes the application to `completed`; `merchant_tx_hash` is the payout to the worker wallet |
| production DB migration | wallet/transaction constraints accept EVM or Solana and both read back `convalidated=true`; no ledger row is rewritten |
| live mainnet adversarial probe | finalized tx `47aSEd…E1Ch` is rejected as `self-funded or has no external payer`; it is not revenue |
| latest live uGig API run | `deliveries_seen=4`, `pending=4`, `invoice_created=0`, `paid=0`, `revenue_recorded=0` |
| production launchd | `ai.anicca.life-manager-ugig-invoice-observer`, interval 300 seconds |
| production first run | `runs=1`, `last exit code=0` |
| production latest run | `runs=16`, `last exit code=0` |
| existing Life Manager loops | eight existing labels remained loaded; none was stopped or replaced |

Production stdout:

```json
{"observed_at":"2026-07-28T08:49:30.740Z","deliveries_seen":1,"pending":1,"waiting_for_merge":0,"invoiced":0,"invoice_created":0,"paid":0,"rejected":0,"invoices":[]}
{"observed_at":"2026-07-28T08:56:27.311Z","deliveries_seen":2,"pending":2,"waiting_for_merge":0,"invoiced":0,"invoice_created":0,"paid":0,"rejected":0,"invoices":[]}
{"observed_at":"2026-07-28T09:06:11.186Z","deliveries_seen":3,"pending":3,"waiting_for_merge":0,"invoiced":0,"invoice_created":0,"paid":0,"rejected":0,"invoices":[]}
{"observed_at":"2026-07-28T09:34:02.789Z","deliveries_seen":4,"pending":4,"waiting_for_merge":0,"invoiced":0,"invoice_created":0,"paid":0,"rejected":0,"invoices":[]}
{"observed_at":"2026-07-28T09:55:05.299Z","deliveries_seen":4,"pending":4,"waiting_for_merge":0,"invoiced":0,"invoice_created":0,"paid":0,"revenue_recorded":0,"revenue_duplicates":0,"rejected":0,"invoices":[]}
```

## Primary-source contract

- [uGig gig invoice route](https://github.com/profullstack/ugig.net/blob/master/src/app/api/gigs/%5Bid%5D/invoice/route.ts):
  “GET /api/gigs/[id]/invoice - Get invoices for a gig.”
- [uGig CoinPay payment sync](https://github.com/profullstack/ugig.net/blob/master/src/lib/coinpay-payment-sync.ts):
  a paid gig invoice updates its application to `status: "completed"` and
  records `merchant_tx_hash`, `settlement_chain`, and `amount_crypto`.
- [uGig payment receipt](https://github.com/profullstack/ugig.net/blob/master/src/lib/payments/receipt.ts):
  `merchant_tx_hash` is “CoinPay forwarding those funds on to the recipient's
  own wallet.”
- [Solana `getSignatureStatuses`](https://solana.com/docs/rpc/http/getsignaturestatuses)
  and [Solana `getTransaction`](https://solana.com/docs/rpc/http/gettransaction)
  are the independent finalized-status and balance-delta witnesses.

## Safety and evidence limit

- The API key remains in a mode-0600 file outside the repository and is never
  printed.
- A malformed UUID, non-positive amount, wrong rail, malformed Solana address,
  unknown category, non-GitHub code PR, or non-code delivery without public
  HTTPS proof fails closed.
- Existing invoices are detected before checking merge state, making retries
  exactly-once.
- Invoice status alone does not enter the earnings ledger. The exact USD-micro
  row is written with entry key `ugig:invoice:<id>:merchant-payout` only after
  the independent Solana receipt passes; a retry is a database duplicate, not
  new revenue.
- This evidence proves the production acceptance-to-invoice machine is live. It
  does not prove buyer acceptance, invoice payment, or external revenue. Verified
  external revenue therefore remains `$0.00`.
