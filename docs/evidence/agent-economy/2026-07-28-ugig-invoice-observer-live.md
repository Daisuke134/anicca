# uGig accepted-work invoice observer — production evidence

## Outcome

Life Manager now observes its delivered uGig code application every five minutes
and can issue the exact capped invoice without a human after both external gates
become true:

1. the buyer changes the application to `accepted`; and
2. every configured GitHub pull request reports a non-null `merged_at`.

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
| TDD RED | 2/2 test files failed because both implementation modules were absent |
| focused GREEN | 7/7 |
| Life Manager full suite | 659/659, plus the new 7/7 pretests |
| shell syntax | PASS |
| plist lint | PASS |
| latest live uGig API run | `deliveries_seen=3`, `pending=3`, `invoice_created=0`, `paid=0` |
| production launchd | `ai.anicca.life-manager-ugig-invoice-observer`, interval 300 seconds |
| production first run | `runs=1`, `last exit code=0` |
| production latest run | `runs=5`, `last exit code=0` |
| existing Life Manager loops | eight existing labels remained loaded; none was stopped or replaced |

Production stdout:

```json
{"observed_at":"2026-07-28T08:49:30.740Z","deliveries_seen":1,"pending":1,"waiting_for_merge":0,"invoiced":0,"invoice_created":0,"paid":0,"rejected":0,"invoices":[]}
{"observed_at":"2026-07-28T08:56:27.311Z","deliveries_seen":2,"pending":2,"waiting_for_merge":0,"invoiced":0,"invoice_created":0,"paid":0,"rejected":0,"invoices":[]}
{"observed_at":"2026-07-28T09:06:11.186Z","deliveries_seen":3,"pending":3,"waiting_for_merge":0,"invoiced":0,"invoice_created":0,"paid":0,"rejected":0,"invoices":[]}
```

## Safety and evidence limit

- The API key remains in a mode-0600 file outside the repository and is never
  printed.
- A malformed UUID, non-positive amount, wrong rail, malformed Solana address,
  non-code category, or non-GitHub PR URL fails closed.
- Existing invoices are detected before checking merge state, making retries
  exactly-once.
- Invoice status alone does not enter the earnings ledger. Only the later
  independently verified external payment can advance 13c.
- This evidence proves the production acceptance-to-invoice machine is live. It
  does not prove buyer acceptance, invoice payment, or external revenue. Verified
  external revenue therefore remains `$0.00`.
