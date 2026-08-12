# Connector auth-required provider continuation 20F3 implementation plan

> **Execution:** Ponytail `full` rejects a driver-host change because the production minimal rail is already host-neutral and owner-fenced. This slice changes only runner control flow with Superpowers TDD. Sol plans/verifies/updates SSOT/commits/pushes; Luna edits production/tests; fresh Sol reviews Critical/Important.

**Goal:** Treat an independently verified Browser Harness `auth_required` as terminal for only the current provider, then continue the next provider on the same owned session/target/page without counting candidate failures or retrying more candidates on the auth-blocked provider.

**Architecture:** In the provider loop, when fallback returns exact `{status:"failed", safe_reason:"auth_required"}`, latch provider-auth exhaustion. Do not retry another candidate, do not increment consecutive failures, do not cache/save/evidence, and break only the candidate loop so the existing next-provider `about:blank` navigation runs on the same owned rail. Other safe failures, effect_unknown, and circuit breaker semantics remain unchanged.

**Ponytail size gate:** modify `connector-minimal-runner.js` about 4–10 LOC and test about 55–85 LOC, exact two files.

## Task 1 — TDD same-rail continuation

RED: provider A has at least three candidates; first fallback returns auth_required; prove provider A fallback exact1, remaining candidates 0, consecutive failures stay 0, provider B discovery/action occurs on exact same session/target/page, and no cache-save/evidence for A. GREEN minimum latch/break. Also prove non-auth failed fallback still increments/circuits as before. Run runner tests, syntax/diff, fresh review.
