# Connector Eventbrite hydrated CTA 19E Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development and subagent-driven-development. Luna writes production/tests; Sol reviews and live-verifies.

**Goal:** Make Eventbrite eligibility and absent readback deterministic across the measured SSR `Get tickets` label and hydrated `Reserve a spot` label.

**Measured cause:** Three official Eventbrite details were opened read-only in isolated owned diagnostic pages on CloakBrowser `:9222`. Each had exactly one visible/enabled `data-testid="conversion-bar-checkout-button"` after hydration, and all three labels were exact `Reserve a spot`; the downloaded SSR HTML had exact `Get tickets`. One page was offline, one online, and another offline, so this is a shared CTA hydration variant rather than attendance-specific copy. Diagnostic pages were closed; baseline pages returned to 2 and Connector ledger/current-page intersection was zero.

**Ponytail decision:** Change only the provider-local exact CTA predicate. Permit exactly one visible control whose label is either `Get tickets` or `Reserve a spot`; no fuzzy/substring labels. Reuse the same predicate in eligibility and absent readback. Do not implement checkout or Harness in this slice.

**Estimated change:** 2 files. Production 1–4 LOC; test 4–15 LOC.

## TDD task

- Modify only `apps/mr-bot/lib/connector-eventbrite-workflow.js` and matching test.
- RED: hydrated `Reserve a spot` detail must be eligible and hydrated absent readback must return `absent`; current code rejects both.
- GREEN: one exact helper/predicate accepts `Get tickets|Reserve a spot`; duplicate visible variants, unknown labels, unsafe/body-money markers remain fail-closed.
- Run Eventbrite focused, production/operations adjacent, syntax, diff, exact two-file scope. Commit without amend and push. No browser/live/state effect during implementation.

## Completion gate

Fresh review Critical/Important 0, stable independent GREEN, one read-only diagnostic confirmation with exact-page cleanup, SSOT/result update, and remote push. Native provider order stays unchanged.

## Result

Luna changed only the Eventbrite workflow and focused test. Hydrated `Reserve a spot` was RED 0/1, then exact shared CTA handling produced GREEN. Fresh review found that one exact plus one fuzzy visible checkout control still passed; Luna added a failing mixed-control regression and required total visible checkout controls to be exactly one before applying the literal label predicate.

Final Eventbrite tests are 13/13 and the stable production/operations/Doorkeeper/Meetup combined set is 68/68. Final scoped review reports SHIP with Critical/Important 0; syntax, whitespace, two-file scope, and remote implementation equality pass. Reviewed implementation ends at `d397ff052`.

Post-integration read-only production-workflow diagnostics on a hydrated official page proved exact identity, Tokyo, offline, zero AggregateOffer, InStock, exact offer URL, and one `Reserve a spot` control all pass. Selection then stopped at the independent event-owned overview money marker, as required; checkout/final Submit remained zero. Every diagnostic page was closed, baseline pages returned to two, and current-page/Connector-ledger intersection remained zero.
