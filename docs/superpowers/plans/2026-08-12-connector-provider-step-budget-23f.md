# Connector Item 23F — provider-specific fallback step budget

## Goal

Preserve TECH PLAY's verified 15-step review/final flow while ensuring every generic Browser Harness invocation stays within its hard 10-step contract.

## Ponytail scope

- Production: `apps/mr-bot/lib/connector-minimal-production.js`, one routing clamp, estimated 2–6 LOC.
- Tests: `apps/mr-bot/lib/connector-minimal-production.test.js`, one normal-provider and one TECH PLAY routing assertion, estimated 20–40 LOC.
- Do not change the runner's single wake budget, provider order, Harness validators, TECH PLAY final-effect semantics, or circuit thresholds.

## TDD and verification

1. RED: call the production router with native `maxSteps: 15`; prove a normal provider receives exactly 10 while TECH PLAY receives exactly 15.
2. GREEN: clamp only the generic route at the production composition boundary.
3. Run focused production/router/native tests, full Connector tests, security gates, syntax, and diff check.
4. Fresh Sol review must confirm both limits and no final-effect weakening.

