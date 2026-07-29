# JOB-BUDGET-HARD-CAP-10J: Conservative Pre-Spend Admission

**Goal:** Prevent the observed job-search daily loop from launching a provider
when the remaining daily allowance cannot cover that pass's configured maximum.

**Root cause:** The live run entered with 231,212 of 262,144 tokens consumed.
`browser-lane-agent.token_reservation` was only 24,576, so admission allowed
231,212 + 24,576. The provider later reported 93,420 chargeable tokens, and
settlement truthfully replaced the estimate, producing 324,632 consumed. The
ledger's arithmetic was correct; the caller passed an estimate that was not an
upper bound.

**Single hypothesis:** For a budget-enabled provider attempt, reserve the whole
configured per-pass limit before launch. Because the observed provider charge
93,420 was below the 98,304 pass limit, this makes the same live state fail
closed before a paid process starts. The smaller task-class reservation remains
only an unbudgeted planning estimate.

## Evidence and adopted practices

| Decision | Source | Core quote |
|---|---|---|
| Treat the live overshoot as the regression fixture | [`2026-07-29-order10i-live-summary.json`](../../evidence/job-search-loop/2026-07-29-order10i-live-summary.json) | “Admission used a reservation smaller than the possible provider-reported charge” |
| Fix the amount supplied to admission, not truthful settlement | [Life Manager token budget ledger](https://github.com/Daisuke134/life-manager/blob/1192807c7b6a2db1f6c1f7fe1d2cfd81df3905c8/runtime/agent-runner/token_budget.py) | `daily_consumed + reservation_tokens > daily_limit` |
| Reserve before executing an agent-owned financial side effect | [AlgoPay SDK](https://github.com/Algodev-Studio/algopay-sdk/blob/fd95a38b156ad1fcb6eda31c02896dd66498503a/python/src/algopay/client.py) | `reservation_tokens = await guards_chain.reserve(context)` |
| A reservation secures the amount before capture | [Stripe manual capture](https://docs.stripe.com/payments/place-a-hold-on-a-payment-method) | “決済のオーソリにより、顧客の支払い方法で金額が確保されて保証されます。” |

Firecrawl search was attempted with three independent English/Japanese queries,
but the agent-owned token returned HTTP 401. GitHub code search, the live
production receipt, and the public Stripe reference supplied the fallback
evidence; no personal account was used.

## TDD execution

- [x] Add a RED subprocess test with 70/100 daily tokens consumed, a 20-token
  task estimate, and a 100-token pass limit; prove the current runner launches
  the paid-provider stub.
- [x] Make budget-enabled admission reserve the 100-token pass maximum; prove
  exit 75, `attempt_count=0`, daily-budget reason, and no provider marker.
- [x] Preserve actual-token settlement and all crash/fallback accounting tests.
- [x] Run all 168 job-loop and 10 agent-runner tests plus OSS verification.
- [ ] Update the design spec, push, pass all GitHub checks, merge, sync the
  canonical checkout, and kick the existing daily LaunchAgent.
- [ ] Prove the post-merge live pass blocks before provider launch and leaves
  the usage ledger unchanged apart from one blocked reservation receipt.
