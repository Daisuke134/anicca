# Connector KokuchPro auth readback 20E1 implementation plan

> **Execution:** Ponytail `full` keeps this slice to a read-only provider-state contract. Implement only with Superpowers TDD. Sol owns plan/verification/SSOT/commit/push; Luna owns production/test edits; fresh Sol reviews Critical/Important correctness.

**Goal:** Let the KokuchPro extension workflow distinguish an exact actionable event detail from the exact official login boundary reached for that same candidate, without authenticating or mutating external state.

**Architecture:** Extend only `readProviderState`. On the candidate canonical page, require the measured one-or-two identical POST entry forms bound to `${canonical_url}entry/` and return `absent`. On official `https://www.kokuchpro.com/auth/login/`, require exactly one decoded `continue` equal to the candidate entry path plus one password input and one official POST login form, then return `auth_required`. Every identity, URL, query, DOM-count, redirect, or evaluation ambiguity returns `unavailable`. No click/fill/submit, private value, Harness behavior, factory/router/native order, evidence, Calendar, cache, or schedule changes.

**Ponytail size gate:**

- Modify `apps/mr-bot/lib/connector-kokuchpro-workflow.js` — about 25–45 production LOC.
- Modify `apps/mr-bot/lib/connector-kokuchpro-workflow.test.js` — about 55–90 test LOC.
- Exact two files; no new module, abstraction, dependency, credential path, or external effect.

## Task 1 — TDD the exact auth boundary

**RED:** Add focused tests for canonical `absent`, exact candidate-bound `auth_required`, and fail-closed wrong host/path/port/userinfo/query/continue/candidate, missing-or-duplicate password/login form, malformed/evaluate failure. Prove action methods remain unchanged safe failure.

**GREEN:** Implement the minimum bounded same-page evaluator and URL binding. Run focused KokuchPro, adjacent TECH PLAY, syntax, and diff checks. Record RED/GREEN evidence before fresh review.
