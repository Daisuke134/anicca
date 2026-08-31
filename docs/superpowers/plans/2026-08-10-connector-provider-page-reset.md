# Connector Provider Page Reset Implementation Plan

> **For Luna:** Use Superpowers test-driven-development. Own only `apps/mr-bot/lib/connector-minimal-runner.js` and `apps/mr-bot/lib/connector-minimal-runner.test.js`. You are not alone in the codebase; preserve and accommodate all other edits.

**Goal:** Prevent a long-running provider discovery from poisoning the next provider while preserving one Connector-owned browser session, target, and page.

**Architecture:** Reuse the existing `browserRail.navigate(owned, url)` boundary. Before every provider after the first, navigate the same verified owned page to `about:blank` as a recorded `navigate/browser_rail` action. Do not open, close, replace, or reconnect the page. Treat reset failure as that provider's discovery failure so the existing consecutive-failure/circuit/report/cleanup path remains authoritative.

**Ponytail full gate:** This is required because dedicated fresh-page and Connpass→Peatix probes succeed while official long-wake Peatix discovery fails. Reuse the existing rail and action recorder; add no service, target, session, retry, timeout, provider-specific branch, or persistent state.

**Soft target:** 2 files, production ≤12 LOC, tests ≤55 LOC. If the test needs more, reduce fixtures rather than introducing helpers.

## Task 1: TDD the exact provider boundary

- [x] Add a RED test proving two providers use one open/session/target/page, with exactly one `about:blank` navigation immediately before the second provider discovery.
- [x] Prove there is no reset before the first provider and no trailing reset after the last provider.
- [x] Add a RED failure test proving a second-provider reset failure records `navigate/browser_rail` failed, does not call that provider discovery, follows the existing failure count/report path, and still closes the exact owned page once.
- [x] Implement the smallest indexed provider loop or first-provider flag; call the existing `action` wrapper and existing rail only.
- [x] Run focused runner tests, then minimal production/native/renderer integration and syntax checks.
- [x] Report RED and GREEN evidence to Sol. Do not commit or push; Sol reviews and integrates.

## Acceptance

The same `owned.page`, `session_id`, and `target_id` are reused. The only new browser operation is `navigate(owned, "about:blank")` between providers. Reset failure cannot trigger discovery, Submit, a new target, or a new session. Cleanup and current-wake reporting remain in the existing parent `finally`/finish flow.
