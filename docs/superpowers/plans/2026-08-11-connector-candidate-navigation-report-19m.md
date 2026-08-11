# Connector candidate-navigation safe-report plan

## Goal

Make a before-deadline candidate navigation timeout a bounded safe candidate failure instead of an uncaught wake, preserving every-wake reporting and exact owned-page cleanup without provider Submit.

## Measured live failure

- Official wake `wake-8f883c25e400a12b505e4b23` completed Calendar, Luma, Connpass, and Peatix discovery, then one Peatix candidate navigation failed after 30,029 ms.
- The error escaped `runMinimalConnectorWake`: exit 2, report/delivery delta 0, bundle delta 0, Meetup audit 0. Action history durably recorded only `navigate/browser_rail/failed`.
- The Connector-owned target was closed and process/active lease returned to zero. The four current CDP pages are unrelated opener-free Coconala pages, not Connector orphans, and must not be closed.

## Ponytail full gate

- Reuse the existing candidate loop, `action`, consecutive failure counter, circuit breaker, `finish`, and `finally` cleanup.
- Add no retry loop, browser target, provider rule, error store, raw exception text, URL log, state schema, schedule, or timeout change.
- Change only runner production/test. A failed navigation performs no provider readback, cache, direct action, Harness, evidence, or external registration effect.

## Luna implementation slice

Luna owns only:

1. `apps/life-manager/lib/connector-minimal-runner.test.js`
2. `apps/life-manager/lib/connector-minimal-runner.js`

Soft target: 2 files; production +10–18 LOC; tests +35–55 LOC.

### RED

1. One before-deadline candidate navigation throw records one failed navigate action, performs no readback/Submit for that candidate, and continues to the next candidate on the same owned page.
2. Three before-deadline candidate navigation throws produce exactly one `circuit_open / candidate_navigation_failed` report with failure count 3, no fourth candidate, and cleanup once.
3. No raw error or candidate URL appears in history/report.
4. A navigation throw that crosses the wake deadline remains exactly `circuit_open / wake_deadline` with one report and cleanup.
5. Successful navigation, discovery failure, evidence created/reused, and ordinary direct/Harness paths remain unchanged.

### GREEN

- Catch only the candidate `browserRail.navigate` action boundary.
- If the deadline is reached, return the existing `wake_deadline` terminal path.
- Otherwise increment the bounded failure count once, set the safe reason `candidate_navigation_failed`, circuit-open at the configured maximum, or continue to the next candidate.
- Never call readback, cache, direct, Harness, evidence, or save-repair for the failed candidate.

## Verification

- Focused runner RED/GREEN, then runner + operations + production + evidence + Peatix/Meetup router/Harness adjacent suites.
- `node --check`, `git diff --check`, fresh Sol correctness review.
- Sol fast-forwards reviewed code, updates SSOT, pushes both branches, then runs one schedule-unloaded official wake. Acceptance is positive every-wake report on repeated navigation failure or safe continuation to Peatix/Meetup, with process/lease cleanup and no Connector orphan target.
