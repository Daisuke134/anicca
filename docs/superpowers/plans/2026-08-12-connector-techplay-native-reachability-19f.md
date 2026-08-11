# TECH PLAY Native Reachability Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Superpowers test-driven-development. Sol owns plan/review/verification/commit; Luna owns the exact native entrypoint files.

**Goal:** Make the existing official launchd-owned native wake reach TECH PLAY after the six existing providers and grant the exact 15-step deterministic budget required for its form.

**Architecture:** Change only the native invocation constants: append `techplay` to the frozen provider order and set the official `maxAgentSteps` input to `15`. Keep the runner default, provider cursor behavior, failure cap, wake timeout, dependency boundary, CLI, exit codes, and launchd files unchanged.

**Files / soft target:**

- Modify `skills/connector/native-pass.js` — 2 LOC.
- Modify `skills/connector/test/native-entrypoint.test.js` — about 3–8 LOC.

## Grounding

- Node.js process API: <https://nodejs.org/api/process.html#processargv> — the existing CLI/exit boundary remains unchanged.
- Public max-agent-step/provider-order searches show configuration at the caller boundary; this repository's native input is the exact local source of truth.
- Japanese search found no closer reusable implementation; no runtime/provider registry change is justified.
- The shipped TECH PLAY Harness proves its deterministic path is exactly 13 inputs + review + final = 15 actions.

## Contract

- [ ] RED: official native wake omits TECH PLAY and supplies `maxAgentSteps:10`.
- [ ] Exact frozen order is `luma → connpass → peatix → meetup → doorkeeper → eventbrite → techplay`.
- [ ] Official native input supplies exactly `maxAgentSteps:15`.
- [ ] Keep `maxConsecutiveFailures:3`, `maxWakeMs:600000`, no provider cursor, and private-free wake input unchanged.
- [ ] Runner default, production factory, evidence, schedule/plist, CLI, and exit codes remain unchanged.
- [ ] Run focused/full native tests plus production/runner/Harness adjacency, syntax, diff check, mutation proof, and fresh Sol review.
- [ ] Do not load/kickstart launchd or perform external effects in this slice.
