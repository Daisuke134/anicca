# 11a real calendar care-detection evidence

## Result

Atomic 11a is done at L3 by wiring the existing `care-detector.js` to the current managed Google
Calendar account. The runtime fetches only `id/start/end`; event title, location, account identity,
user identity, and notes never enter the detector receipt or repository evidence.

Three privacy-safe care-history queries are measured against real provider data:

| Care history | Real event count | Detector result |
|---|---:|---|
| haircut | 5 | no candidate |
| health check | 3 | no candidate |
| clinic | 2 | one `personal-cadence-overdue` candidate |

The one detection is based only on the user's own two-event interval:

- care type: `clinic`
- reason: `personal-cadence-overdue`
- personal interval: `9` days
- elapsed beyond personal interval: `469` days
- source Google Calendar event IDs:
  `89ll4pq50l499alj2njcosqdhc`, `sg08fnoe37loddogdp4ov8ub8s`

This is a visit-gap observation, not a diagnosis, recommendation, or booking. No message,
calendar mutation, email, call, or provider write occurs.

## TDD and verification

- Missing runtime adapter: RED `0/1`.
- Runtime adapter plus existing detector: GREEN `7/7`.
- Duplicate event IDs across search terms count once.
- Malformed/future events are discarded; zero or one real visit never flags.
- Closed output excludes title, summary, location, diagnosis, and `lastVisitMs`.
- Full `npm test`: exit `0`.
- Evals: calendar `21/21`, late `12/12`, context `12/12`, score `27/27`, intent `18/18`,
  mental `15/15`, physical `12/12`.
- Panel privacy: `api=177`, `browser=63`, `recipes=19`, `channels=9`.
- Changed-path gitleaks and added-line secret/PII scans: zero.

## Best-practice sources

- NICE, [Dental checks: intervals between oral health reviews](https://www.nice.org.uk/guidance/cg19/chapter/Recommendations):
  recall should be “tailored to meet his or her needs” based on assessed risk. The detector
  therefore derives cadence only from the user's history and never installs a universal interval.
- Google Calendar API, [Events: list](https://developers.google.com/workspace/calendar/api/v3/reference/events/list):
  “Returns events on the specified calendar.” The L3 adapter reads the connected provider rather
  than a fixture.
- European Commission, [How much data can be collected?](https://commission.europa.eu/law/law-topic/data-protection/rules-business-and-organisations/principles-gdpr/how-much-data-can-be-collected_en):
  data should be “adequate, relevant, and limited to what is necessary.” Only provider id and start
  time cross the adapter boundary.
