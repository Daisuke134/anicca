# Verified Demonstration — Risk Register Action Planner

## Concrete input

```text
Project: Northstar checkout launch
Target launch: 2026-10-15
Review date: 2026-09-08
Scoring scale: Low / Medium / High

Known risks:
1. The payment vendor has not approved our production account. If approval slips,
   we may miss the launch date. Likelihood: High. Impact: High. Owner: Nina.
   Current mitigation: Nina sent the required compliance documents on 2026-08-29.
2. Load testing has not started because the staging dataset is incomplete. This may
   delay performance sign-off. Impact: Medium. No likelihood, owner, trigger, or
   mitigation has been agreed.

Assumption: Marketing can move the campaign by up to one week.
Decision: The team will not launch without payment-vendor approval.
```

## Actual output

### Risk register

| ID | Risk statement | Supplied evidence | Likelihood | Impact | Trigger | Mitigation | Contingency | Owner | Review date |
|---|---|---|---|---|---|---|---|---|---|
| R-01 | If payment-vendor approval slips, Northstar checkout launch may miss 2026-10-15. | Production account not approved; Nina sent compliance documents on 2026-08-29. | High | High | `[TRIGGER TBD]` | Continue the supplied compliance-document follow-up. | `[PROPOSED — OWNER CONFIRMATION NEEDED]` Decide whether to move launch after the approval status is known. | Nina | 2026-09-08 |
| R-02 | If the staging dataset remains incomplete, performance sign-off may be delayed. | Load testing has not started because the staging dataset is incomplete. | `[LIKELIHOOD TBD]` | Medium | `[TRIGGER TBD]` | `[PROPOSED — OWNER CONFIRMATION NEEDED]` Set a dataset-completion checkpoint before scheduling load testing. | `[CONTINGENCY TBD]` | `[OWNER TBD]` | 2026-09-08 |

### Assumptions and open questions

- Assumption: Marketing can move the campaign by up to one week.
- Open question: What status or date counts as a payment-vendor escalation trigger?
- Open question: Who owns completing the staging dataset, and by when?
- Open question: What likelihood should R-02 use under the team's stated scale?

### Next review agenda

1. Review R-01 first because its supplied likelihood and impact are both High and it directly affects the launch target.
2. Assign the missing owner, likelihood, trigger, and mitigation for R-02 before treating it as an agreed action plan.
3. Confirm whether the marketing assumption can serve as an approved contingency; it is currently an assumption, not a decision.

### Decision log

| Decision | Status |
|---|---|
| The team will not launch without payment-vendor approval. | Supplied decision |

## Verification notes

- Every factual statement in the output is traceable to the concrete input.
- Missing fields remain explicitly marked instead of being invented.
- The two action suggestions are labeled proposed, so they are not represented as agreed work.
- No project system, current status, forecast, external source, or automated action is claimed.
