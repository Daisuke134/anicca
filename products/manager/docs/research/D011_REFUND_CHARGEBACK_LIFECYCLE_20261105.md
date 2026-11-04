# D011 — Refund / chargeback lifecycle must not be counted as settled income (2026-11-05 JST)

**Canonical progress source:** `products/manager/docs/roadmap/tasks.json` on `research/manager-product-r006-20261020`. D011 remains `todo`; this increment does not satisfy the original requirement for independently verified receipt/provider identity. H005 remains `blocked`. No personal data, private payment account, provider credentials, live API, message, transfer, or external operation was used.

## Imozuru: question → hypotheses → counterexample → falsification

**Question:** Can a public opportunity record that once says `settled` be treated as received income when a later refund, partial refund, or chargeback exists?

**Unsafe hypothesis H0:** Yes. A single `settled` claim is sufficient; later reversals can be ignored or netted from the original amount without inspecting a separately linked adjustment record.

**Counterexample from first-party platform documentation:** Open Collective describes a refund as a new transaction group related to the original contribution; the original contribution transactions are marked `REFUNDED`, while related refund transactions are marked `REFUND`. Its refund guide also distinguishes provider-backed refunds from manual ledger-only refunds: marking a manual contribution refunded in the ledger does not itself move money.

**Falsifiable narrow rule H1:** Any declared lifecycle state indicating a refund request, refund failure, partial/full refund, chargeback, or chargeback reversal must produce an explicit review state and must not contribute a declared received amount in this preflight. A partial refund is not arithmetically netted unless a separately authenticated adjustment chain, exact amount, currency, original transaction identity, ordering and finality are independently verified. The present product does not implement that provider verification.

## Primary sources checked

1. Open Collective, *Contributions in the Ledger* (current official documentation), sections “Refunded Contributions” and “Disputed Contributions”: https://documentation.opencollective.com/advanced/ledger/contributions-in-the-ledger . It documents separate original/refund transaction groups, refund transaction links, and dispute outcomes. This is a platform-specific accounting example, not a universal ledger standard.
2. Open Collective, *Processing Refunds* (current official documentation): https://documentation.opencollective.com/fiscal-hosts/processing-refunds . In particular, lines 23–40 distinguish automatic provider-backed refunds from manual refunds that only reverse the ledger entry and require an off-platform return of funds. Therefore a public ledger label alone cannot prove cash movement.
3. Stripe, *Retrieve an event* / event types: https://docs.stripe.com/api/events/retrieve . Stripe documents separate events including `charge.refunded` (including partial refunds), `refund.created`, `refund.updated` and `refund.failed`. A single original charge-success event is not the complete lifecycle. The source does not imply that Manager has Stripe credentials or has verified any transaction.

## Implementation

- `manager_core/opportunity_outcomes.py`: added explicit lifecycle values `refund_pending`, `refund_failed`, `partially_refunded`, `refunded`, `chargeback`, and `chargeback_reversed`. All map to `SETTLEMENT_ADJUSTMENT_REQUIRES_REVIEW`; no declared receipt amount is returned.
- `manager_core/opportunity_receipt_portfolio.py`: emits `RECEIPT_ADJUSTMENT_REQUIRES_REVIEW` for these states and keeps the portfolio `REVIEW_REQUIRED`; income counting remains disabled.
- `tests/test_opportunity_outcomes.py`: six synthetic adjustment-state cases assert no declared received amount and `income_status=NOT_VERIFIED`.
- `tests/test_opportunity_receipt_portfolio.py`: the same six cases assert `REVIEW_REQUIRED`, no income counting, no independent payment verification and a null verified amount.
- `docs/roadmap/tasks.json`: records this increment on D011 while preserving `status=todo`.

## Verification boundary

These are synthetic state-machine regression cases, not live payment tests. The new labels are generic Manager review categories, not an assertion that all payment providers share identical lifecycle semantics. `chargeback_reversed` remains review-required because the model has no authenticated provider event chain, settlement finality or account-level readback.

**Research:** first-party documentation review and a conservative state model. **Simulation:** synthetic test fixtures only. **Field effect:** none measured. No income, beneficiary improvement, or reduction in human/animal suffering is claimed.

## Latest pre-change hosted CI readback

At branch HEAD `bcabc82dca0f5fad49765d784e015d5143e4e626` (2026-11-03 23:39:41 UTC), the latest branch workflows were Independent Offline Research #324 **success**, EBA v0 Open Benchmark #93 **success**, and Phase06 Digital Environment #230 **failure**. Phase06's failure was the previously documented Playwright 1.56.1 browser dependency installation incompatibility on `ubuntu26.04-x64`; it is not counted as green. New workflow runs for this increment must be read back separately.

## Safety and remaining acceptance

- No actual public payment, payout, personal bank account, or beneficiary identity was retrieved.
- No money was sent, requested, or moved; no third-party credentials were used.
- No Life Manager runtime, main branch, or personal data was modified.
- D011 remains `todo` until a lawful public receipt is independently authenticated against the provider/settlement source and any refund, dispute, chargeback, reversal and fees are reconciled. A platform ledger record is not automatically recipient bank receipt.
- H005 remains blocked. No HeartSteps study-day information or original paper values were inferred.