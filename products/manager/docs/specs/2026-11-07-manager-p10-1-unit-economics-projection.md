# Manager P10-1｜Verified Unit Economics Projection v0.1

**Status:** 2026-11-07 research specification, NOT production release or financial source of truth.
**Owner:** existing Manager curriculum SSOT (ROADMAP_STATUS_JA.md). Existing operational SSOT: docs/superpowers/specs/2026-09-25-life-manager-unified-ssot.md. This document must not replace either.
**Primary unit:** eligible goal-level work_item_id, not LLM call or billing row.

## Architecture / reuse decision

Build an optional **read-only projection** that joins existing authority/trace/receipt/independent-readback events with finance-provider invoices/accounting, rate-card snapshots and human-assistance logs. No second ledger of authoritative revenue. Reuse runtime/contracts/common-record.schema.json, runtime/loop, products/manager/manager_core/{authority,outbox,reconcile,verifier,audit}. Do not mutate production systems, credentials or subscriptions.

## Evidence tiers

- RECONCILED: source invoice/payment/refund/accounting entry and provider cost bill reconciled, with reference hash and as-of.
- OBSERVED: authoritative individual trace/usage or assistance event exists but invoice reconciliation pending.
- ESTIMATED: model list price or internally allocated rate applied to measured usage, explicitly dated.
- UNKNOWN: missing or ambiguous; do not coerce to 0.
- SYNTHETIC: self-authored demo; must never be counted as Anicca real business evidence.

An income row requires a credible revenue-recognition reference, not only an agent claim or an email receipt. A human benefit row requires independent outcome measurement; never infer from sales or tokens.

## Contracts

| Record | Required fields | Invariants |
|---|---|---|
| work_item | tenant_id, work_item_id, eligibility, created_at, subject_safe_id, goal_type, policy_version | one objective; user data minimized |
| attempt | work_item_id, attempt_id, trace_id, started_at, finished_at, outcome_state | attempts may be multiple; task unique |
| inference_usage | attempt_id, provider_request_id, model_id, prompt_tokens, output_tokens, cached_tokens, unit_price_version, currency, occurrence timestamp | tokens not revenue; cached subset not double counted |
| cost_event | event_id, provider_event_id, work_item_id, cost_class, currency, amount_minor, source_ref, evidence_tier, occurred_at, recorded_at | no silent duplicates, known zero != unknown |
| revenue_event | event_id, work_item_id, invoice_or_accounting_ref, recognized_period, amount_minor, currency, kind, evidence_tier | booked != collected; refunds/reversals explicit |
| human_assist | event_id, work_item_id, actor_category, reason, human_seconds, hourly_rate_ref, monetary_cost, source_ref | include rescue, edits, obligatory safety review |
| outcome | work_item_id, status, observation_source_ref, independently_verified_at, comparator_id optional, benefit_state, harm_state | receipt != verified success; UNKNOWN allowed |
| reconciliation | provider, period, source_snapshot, matched_total, unmatched_total, currency, as_of | unmatched remain visible |

Money: store minor units as integer; prefer arbitrary-precision decimal for FX/fees; no floating-point rounding. Conversion: preserve original currency, FX source, rate_date and separately converted currency. Allocation: shared expenses assigned by documented basis; sum of allocations + UNALLOCATED = raw billed expense.

## Accounting vs operational projections

Operational direct cost: model, tools, job-specific infra, retry/recovery, fees, direct customer assistance. Contribution margin = recognized net revenue minus attributable variable costs, excluding fixed expenses explicitly not allocated. Report company-level operating profit separately from period ledger. FOCUS BilledCost vs EffectiveCost are not interchangeable, and the FOCUS specification is for technology cost normalization, not a full financial revenue ledger.

## No-human-loop claim test

A claimed autonomous success needs: independently verified outcome, complete assistance instrumentation, permission/consent, no blocked required safety step, unambiguous eligibility. Report unassisted_verified_success_rate and human_rescue_rate along with human_assist_seconds and cost. If assistance telemetry is missing, state UNKNOWN. Record external vendor human work if it contributes to task completion. Do not remove legally required oversight to optimize the metric.

## Required gates / tests

- Reject duplicate event_id and duplicate provider_event_id, including repeated ingestion.
- Reject negative amounts unless explicitly modeled as refunds/reversals and linked to prior entry; reject different-currency arithmetic without FX.
- Unlinked charges remain UNALLOCATED, not deleted.
- If cost or revenue coverage is incomplete, CM status = INCOMPLETE, not a verified profit figure.
- Never report successful task from provider send receipt alone; independent readback or validated objective metric required.
- Counterfactual impact requires randomized/equivalent baseline where appropriate; descriptive CM does not establish caused impact.
- NO_ACTION, failure, timeout and abandoned tasks remain in eligible cost denominator.
- Consent-restricted personal/health data excluded from analytics projection; reference salted pseudonymous IDs rather than raw content.

## Phase 10 continuation

P10-2: exploration budgets, opportunity costs and value-of-information.
P10-3: authority, privacy, audit, override, stop and redress.
P10-4: repeatable operations, revenue reconciliation, financial sustainability.

## Primary sources

- https://www.finops.org/framework/capabilities/unit-economics/
- https://focus.finops.org/docs/specification/v1-3/columns/billed-cost/
- https://focus.finops.org/docs/specification/v1-3/columns/effective-cost/
- https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-token-metrics.md
- https://cloud.google.com/transform/the-kpis-that-actually-matter-for-production-ai-agents
- https://stripe.com/revenue-recognition
- https://airc.nist.gov/airmf-resources/playbook/measure/
