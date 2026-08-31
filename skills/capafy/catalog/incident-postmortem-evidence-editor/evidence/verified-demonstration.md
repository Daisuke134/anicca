# Verified demonstration — Incident Postmortem Evidence Editor

## Concrete input

```text
Draft a blameless postmortem. Use only these notes:

- 09:12 JST — Checkout error rate rose after a configuration change.
- 09:18 JST — Support reported customers could not finish checkout.
- 09:24 JST — On-call started rollback.
- 09:31 JST — Rollback completed; checkout errors returned to normal.
- A support spreadsheet contains 42 failed-order reports. Finance has not confirmed the count.
- We do not know why the configuration was accepted.
- Proposed follow-up: add a configuration review. No owner or due date has been chosen.
```

## Actual output

```text
Executive summary
On the supplied timeline, checkout errors rose at 09:12 JST after a configuration
change. Checkout errors returned to normal after rollback completed at 09:31 JST.
Support reported that customers could not finish checkout. The supplied 42 failed-order
reports are unconfirmed by finance and are therefore an estimate, not confirmed impact.

Timeline
| time (JST) | event | evidence status |
|---|---|---|
| 09:12 | Checkout error rate rose after a configuration change. | Confirmed from supplied note |
| 09:18 | Support reported customers could not finish checkout. | Confirmed from supplied note |
| 09:24 | On-call started rollback. | Confirmed from supplied note |
| 09:31 | Rollback completed; checkout errors returned to normal. | Confirmed from supplied note |

Evidence ledger
| item | status | note |
|---|---|---|
| 42 failed-order reports | [UNCONFIRMED] | Reported by support; finance has not confirmed the count. |
| The configuration change caused the errors | [HYPOTHESIS — NEEDS CONFIRMATION] | The notes establish sequence, not causation. |
| Why the configuration was accepted | [UNKNOWN] | No supporting observation was supplied. |

Contributing factors
[HYPOTHESIS — NEEDS CONFIRMATION] The configuration change preceded the error increase.
The supplied notes do not establish why it was accepted or whether another factor contributed.

Follow-ups
| action | owner | due date | success signal |
|---|---|---|---|
| Add a configuration review. | [OWNER TBD] | [DATE TBD] | [SUCCESS SIGNAL TBD] |

Verification checklist
- Confirm the failed-order count with finance.
- Confirm whether the configuration change caused the checkout errors.
- Determine why the configuration was accepted.
- Assign an owner, due date, and measurable success signal to the review follow-up.
```

## Verification notes

- The output preserves all four supplied timestamps and does not add an event.
- It labels the failed-order count as unconfirmed because finance confirmation was absent.
- It does not turn temporal sequence into a confirmed root cause.
- It keeps every unspecified follow-up field visible rather than fabricating an owner, date, or success measure.
- Offline duplicate check: the current catalog contained 10 candidates—academic limitations editor, academic research proposal humanizer, dissertation discussion humanizer, football match analyst, peer review response editor, portfolio tracker, sales objection reply builder, talent review deck writer, user interview synthesizer, and YouTube script writer. None is an incident-postmortem workflow.
- Offline `sales_selector.select_signal` readback, with those 10 local inventory entries and no invented sales fields: `{"ok": true, "signal": "none", "listings": 10, "company_orders": 0}`. The no-signal outcome is why the listing makes no demand or winner claim.
