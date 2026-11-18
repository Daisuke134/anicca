# Intervention delivery measurement (MG-06)

The existing Mixpanel pipeline emits `intervention_delivered` when the onboarding
words finish revealing, a home card is displayed, or iOS reports a delivered
notification. Notification Center deliveries still present when the app becomes
active are also reconciled. Receipt/open/reconciliation and preview-to-home
carryover reuse the existing delivery ID and emit once per assignment, including
across relaunches. Ordinary repeat views remain `affirmation_viewed` events.

| Event | Measurement fields |
| --- | --- |
| `nudge_decision_made` | `delivery_id`, `message_id`, `candidate_ids`, `assigned_probability`, existing policy/reason fields |
| `intervention_delivered` | `delivery_id`, `message_id`, `candidate_ids`, `assigned_probability`, `source`, `delivered_at` (Unix milliseconds), `assignment_metadata_available` |
| `notification_received`, `notification_opened` | Existing fields plus `delivery_id` |

Candidate IDs are captured from the final eligible ranked pool at selection time,
not recomputed at delivery and not truncated to the 12-card home deck. Existing
selection probabilities and selection behavior are preserved. Candidate IDs and
probabilities survive storage in `ManagerBenchCase.stimulus`; old records remain
decodable. No message text or personal answers are added to delivery events.

## Notification sender boundary — outstanding

This checkout contains no APNs sender or `notification_sent` emitter. Consequently
this change cannot update that event. The sender must emit `notification_sent`
with its occurrence's `delivery_id`, and put the same ID in the APNs payload.
The payload must also contain the chosen `quoteId` and the actual assignment's
`candidate_ids` and `assigned_probability`, either at the top level or inside
`decision_point.stimulus`. The latter uses the existing ManagerBench case schema.

The app never substitutes a uniform probability for missing sender metadata.
Legacy/incomplete payloads emit an empty candidate list, omit an unknown or invalid
probability, and set `assignment_metadata_available` to false. These events must
be excluded from propensity-weighted analysis. A sender deployment is required
before MG-06 can be considered complete end to end.

Silent background deliveries removed before the app can observe them are not
observable through these app callbacks. Delivery receipt coverage therefore must
not be interpreted as the total number of sends. No receipt is labelled as a send.

## Verification

XCTest coverage in `PersonalizationPhase1Tests` checks greedy/exploratory candidate
sets, cooldown exclusion and preview carryover. `ManagerBenchCaseTests` checks
wire keys, persistence, legacy decode, analytics fields and missing/invalid
probabilities. Run these with the app's macOS/Xcode test target; Linux has neither
Swift nor Xcode installed in the assigned environment.
