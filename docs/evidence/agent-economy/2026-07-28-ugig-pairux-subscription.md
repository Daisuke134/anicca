# uGig PairUX subscription — browser delivery and invoice wiring

## External job

| Field | Verified value |
|---|---|
| uGig gig | `1eea7af1-3089-443c-9975-74212c53683f` |
| external buyer | `chovy` human account |
| promised rate | `$0.25`, paid in SOL |
| requested action | subscribe to <https://pairux.com/@moshcoding> |
| uGig application | `7e636f57-4d5a-4f54-b6d2-31ba1a86c5bd` |
| live application status | `pending` |

## Real browser E2E

The browser agent used the existing Chrome CDP session and user-facing
Playwright locators:

1. opened the real channel and read `1 subscriber` plus `Subscribe`;
2. created a free PairUX account as `Life Manager AI` with
   `contact@aniccaai.com`;
3. read the forwarded PairUX confirmation mail and opened the real callback;
4. reached the authenticated dashboard on the free plan;
5. reopened the channel and clicked `Subscribe`;
6. read back `2 subscribers` plus `Subscribed`.

No deposit, subscription fee, KYC, or personal identity impersonation was used.
The generated credential is mode 0600 outside the repository.

## General invoice automation

Life Manager PR #1218 generalized the production uGig observer from code-only
deliveries to the upstream invoice categories `code`, `art`, `marketing`, and
`other`.

- non-code deliveries require at least one public HTTPS proof URL;
- they never query GitHub or attach a PR-only invoice item link;
- the proof is preserved in invoice notes;
- buyer acceptance and the existing-invoice exactly-once check still gate the
  mutation;
- code deliveries retain the all-PRs-merged gate.

Verification: TDD RED 2 failures, focused GREEN 9/9, full Life Manager 659/659
plus new pretests. The live production observer then reported:

```json
{"observed_at":"2026-07-28T09:06:11.186Z","deliveries_seen":3,"pending":3,"waiting_for_merge":0,"invoiced":0,"invoice_created":0,"paid":0,"rejected":0,"invoices":[]}
```

This proves the browser delivery and acceptance-to-invoice machine. It does not
prove buyer acceptance or payment, so verified external revenue remains `$0.00`.
