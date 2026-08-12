# Connector KokuchPro native order 20F4 implementation plan

> **Execution:** Ponytail `full` leaves one required production change. Use Superpowers TDD. Sol plans/verifies/updates SSOT/commits/pushes; Luna edits production/tests; fresh Sol reviews Critical/Important.

**Goal:** Append KokuchPro to the official native wake provider order after TECH PLAY.

**Architecture:** Change the frozen `DEFAULT_PROVIDERS` to exact `luma → connpass → peatix → meetup → doorkeeper → eventbrite → techplay → kokuchpro`. No other config, timeout, failure threshold, agent steps, runner, factory, browser, evidence, schedule, or state change.

**Ponytail size gate:** `skills/connector/native-pass.js` production 1 LOC and `skills/connector/test/native-entrypoint.test.js` about 4 LOC, exact 2 files.

## Task 1 — TDD exact order

RED updates every native contract expectation to exact eight-provider order. GREEN appends one token. Run native entrypoint, minimal production/runner adjacent, syntax/diff, fresh review. Only after acceptance may Sol run the official loaded/unloaded launchd entrypoint as foreground production wake and observe real continuation/cleanup.
