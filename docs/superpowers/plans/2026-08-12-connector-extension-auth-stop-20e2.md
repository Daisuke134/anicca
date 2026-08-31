# Connector extension auth stop 20E2 implementation plan

> **Execution:** Ponytail `full` limits this slice to the existing extension seam. Implement only with Superpowers TDD. Sol plans/verifies/updates SSOT/commits/pushes; Luna edits production/tests; fresh Sol reviews correctness.

**Goal:** Make a configured extension workflow's exact `auth_required` readback a terminal safe failure, with no login-page observation, proposal, operation, private resolution, or retry.

**Architecture:** Change only `createProductionBrowserHarness.runFallback`. The adapter must validate page/websocket/expected-state/max-step scope before any extension workflow readback. On the adapter's first logical observe, perform the independent extension readback before any real DOM inspection; exact `auth_required` latches the terminal reason and returns a synthetic empty observation/no proposal. After any successful candidate action, the same independent readback can latch `auth_required`. The Harness maps the adapter failure to the terminal safe reason while preserving only already-performed repaired actions. Built-in providers and extension registered/pending proof remain unchanged.

**Ponytail size gate:**

- Modify `apps/mr-bot/lib/connector-production-browser-harness.js` — about 12–25 production LOC.
- Modify `apps/mr-bot/lib/connector-production-browser-harness.test.js` — about 45–80 test LOC.
- Exact two files; no adapter module change, new abstraction/dependency, provider wiring, private value, cache, evidence, Calendar, native order, or schedule effect.

## Task 1 — TDD terminal auth safety

**RED:** Prove a pre-existing extension login state causes readback 1 and all observe/propose/operate/resolve 0. Prove candidate action followed by auth readback performs that action exactly once, then observe/propose/operate/resolve 0 additional times and returns `auth_required`; registered/pending behavior and non-extension behavior remain unchanged.

**GREEN:** Add only a per-run auth latch around the existing extension workflow. Run focused Harness extension tests plus full Harness/adapter adjacent suites, syntax, and diff checks; record RED/GREEN before fresh review.

**Review correction:** Invalid adapter scope (`page`, websocket, expected state, or max steps) must reject before extension readback. Add a regression proving readback/inspect/propose/operate/resolve all remain zero for invalid inputs; do not duplicate or weaken adapter validation.
