# Connector Eventbrite closed production router 19E Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development and subagent-driven-development. Luna writes production/tests; Sol reviews, integrates, and updates the SSOT.

**Goal:** Route the reviewed Eventbrite workflow through the existing production factory/router on the same owned page, without enabling native provider order or Eventbrite Browser Harness actions yet.

**Ponytail decision:** Reuse the existing Doorkeeper optional-workflow pattern. No generic provider registry/refactor, no operations/audit persistence, no Harness controls, no native list, no evidence schema, and no live wake in this slice.

**Estimated change:** 2 existing files. `connector-minimal-production.js` 15–30 LOC; matching test 45–90 LOC.

## Ownership and contracts

- Modify only `apps/mr-bot/lib/connector-minimal-production.js` and `apps/mr-bot/lib/connector-minimal-production.test.js`.
- Import `createEventbriteScriptFirstWorkflow`; add workflow version `eventbrite_registration_v1`.
- `createProductionProviderRouter` accepts an optional Eventbrite workflow, validates the same three methods, and routes discovery/cache/direct/fallback/readback/save-repair metadata with provider `eventbrite` and the Eventbrite version.
- `createMinimalProductionDependencies` creates the default Eventbrite workflow with the shared `now`. Until the next audit-persistence slice, its `onDiscoveryAudit` uses `operations.recordEventbriteDiscoveryAudit || (() => {})`.
- Inject Eventbrite into the provider router. Do not add Eventbrite to the default Browser Harness workflow options in this slice; an injected Harness stub may prove the router fallback boundary only.
- Native `DEFAULT_PROVIDERS` remains unchanged, so official wakes cannot reach partially wired Eventbrite.
- No browser/session/target, Calendar, provider, evidence, Telegram, state, launchd, or schedule effect.

## TDD task

1. Add RED tests that route an injected Eventbrite workflow through discovery, cached action, direct action, injected fallback, parent readback, and repaired-cache metadata on one exact page, with no private candidate fields copied into cache metadata.
2. Add a factory-injection RED showing Eventbrite discovery receives the supplied page/calendar and opens no browser rail.
3. Implement only the optional workflow/version/router/factory wiring.
4. Run focused minimal production, Eventbrite workflow, Doorkeeper/Meetup adjacent tests, syntax, `git diff --check`, exact two-file scope. Commit without amend and push for fresh Sol review.

## Completion gate

Fresh review Critical/Important 0, Sol independent GREEN on the stable branch, SSOT/result update, and remote push. Official Eventbrite audit remains blocked until audit persistence, Harness action/readback, and native order are separately reviewed.

## Result

Luna changed only the production router/factory and its focused test. The two new tests were RED 0/2 against the unwired router, then GREEN with production 17/17, Eventbrite workflow 11/11, and Doorkeeper/Meetup 27/27. The production diff is +19 LOC and the test diff +58 LOC, both within plan targets. Eventbrite now has optional validation, versioned cache metadata, all closed router paths, and default/injected factory construction.

Fresh Sol review reports SHIP with Critical/Important 0. Sol independently repeated the stable production/provider/native set at 63/63 plus syntax, whitespace, exact two-file scope, and remote implementation equality. Reviewed commit `0ecd49b70` is integrated. Native provider order, default Browser Harness, audit persistence, evidence, browser, and live state remain unchanged.
