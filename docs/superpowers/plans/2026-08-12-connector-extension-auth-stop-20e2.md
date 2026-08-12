# Connector extension auth stop 20E2 implementation plan

> **Execution:** Ponytail `full` limits this slice to the existing extension seam. Implement only with Superpowers TDD. Sol plans/verifies/updates SSOT/commits/pushes; Luna edits production/tests; fresh Sol reviews correctness.

**Goal:** Make a configured extension workflow's exact `auth_required` readback a terminal safe failure, with no login-page observation, proposal, operation, private resolution, or retry.

**Architecture:** Change only `createProductionBrowserHarness.runFallback`. For the configured extension provider, perform an independent provider readback before the first browser step; exact `auth_required` returns `{status:"failed", safe_reason:"auth_required", repaired_actions:[]}`. After any successful candidate action, if independent extension readback returns `auth_required`, latch the terminal reason. The next adapter boundary returns a synthetic empty observation and no proposal, performs no action, and the Harness maps the adapter failure to the same safe reason while preserving only already-performed repaired actions. Built-in providers and extension registered/pending proof remain unchanged.

**Ponytail size gate:**

- Modify `apps/life-manager/lib/connector-production-browser-harness.js` — about 12–25 production LOC.
- Modify `apps/life-manager/lib/connector-production-browser-harness.test.js` — about 45–80 test LOC.
- Exact two files; no adapter module change, new abstraction/dependency, provider wiring, private value, cache, evidence, Calendar, native order, or schedule effect.

## Task 1 — TDD terminal auth safety

**RED:** Prove a pre-existing extension login state causes readback 1 and all observe/propose/operate/resolve 0. Prove candidate action followed by auth readback performs that action exactly once, then observe/propose/operate/resolve 0 additional times and returns `auth_required`; registered/pending behavior and non-extension behavior remain unchanged.

**GREEN:** Add only a per-run auth latch around the existing extension workflow. Run focused Harness extension tests plus full Harness/adapter adjacent suites, syntax, and diff checks; record RED/GREEN before fresh review.
