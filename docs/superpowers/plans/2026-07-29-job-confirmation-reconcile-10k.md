# JOB-CONFIRMATION-RECONCILE-10K: Late Authoritative Confirmation

**Goal:** Turn a matching, authoritative application-received email into a
durable `submit_unknown → submitted` reconciliation without clicking submit
again, then send the exact recorded resume through the existing at-most-once
Telegram document path.

**Observed gap:** The live ledger contains one Ashby `submit_unknown`. The inbox
classifies application confirmations, but neither its prompt nor deterministic
driver can upgrade that terminal uncertainty when a later receipt arrives. A
30-day read-only Gmail search found four broad-query candidates but no BJAK
confirmation; the known Ex-ture confirmation belongs to an already-submitted
application. Therefore the implementation can be completed locally now, while
the real Ashby upgrade remains truthfully waiting for an external receipt.

## Evidence and adopted practices

| Decision | Source | Core quote |
|---|---|---|
| Reconcile from a later authoritative completion event instead of repeating the client action | [Stripe — Verify payment status](https://docs.stripe.com/payments/payment-intents/verifying-status) | “クライアント側でフルフィルメントを開始するのではなく、Webhook を使用して `payment_intent.succeeded` イベントを監視し、その完了を非同期で処理します。” |
| Use the Gmail message ID as the external dedupe key | [Gmail API — Message](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages) | “The immutable ID of the message.” |
| Record the dedupe key and all state mutations atomically | [AWS Builders' Library — Making retries safe with idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) | “the process that combines recording the idempotent token and all mutating operations related to servicing the request must meet the properties for an atomic, consistent, isolated, and durable (ACID) operation.” |

Three direct English/Japanese job-confirmation searches and two generalized
event-reconciliation searches returned no reusable job-application
implementation. `crwl` also failed because its Playwright browser is absent.
The official Stripe, Gmail, and AWS contracts above are the closest applicable
event/idempotency practices; the implementation copies those principles.

## TDD execution

- [x] RED: prove a late confirmation cannot yet atomically promote all ledger
  rows and dedupe the immutable Gmail message ID.
- [x] GREEN: add a private confirmation receipt table and the single ACID
  `submit_unknown → submitted` transition.
- [x] RED/GREEN: accept only post-intent, explicit confirmation text whose
  company, role, and sender domain match exactly one uncertain application.
- [x] Run deterministic reconciliation before the model inbox pass; acknowledge
  only successfully reconciled threads.
- [x] Run the existing resume delivery after reconciliation so the exact PDF is
  sent once through Telegram.
- [x] Run all 174 job-loop and 10 runner tests plus OSS verification.
- [ ] Update the design spec, push, pass all GitHub checks, merge, sync the
  canonical checkout, and kick the existing inbox LaunchAgent.
- [ ] Prove the live no-receipt pass is healthy and records no false promotion;
  keep the real Ashby promotion gate waiting for an external confirmation.
