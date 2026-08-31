# GA-05 Bounded Specialist Runtime Implementation Plan

**Goal:** Reuse the existing browser step loop and `agent-runner` so one specialist job has real step, time, token, heartbeat, cancellation, and structured-result boundaries before the first marketplace canary.

**Architecture:** Keep the model effect-free at the decision boundary: one `agent-runner` call chooses one allowlisted action, deterministic browser code performs it, and provider readback decides completion. The outer adapter owns the hard step/deadline boundary and propagates cancellation; `runtime-up.js` continues to own the durable job lease heartbeat and GA-04 continues to own exactly-once effect/readback semantics.

**Non-goals:** No live marketplace submission, provider-specific planner, new scheduler/database/framework, Coconala change, margin allocator, or claim that a model-authored success is an official receipt.

### Task 1: Generalize the existing bounded browser step loop

**Files:**
- Modify: `apps/mr-bot/lib/connector-browser-harness-adapter.js`
- Modify: `apps/mr-bot/lib/connector-browser-harness-adapter.test.js`
- Modify: `apps/mr-bot/lib/connector-production-browser-harness.js` (preserve the event-only expected-state fence)

1. Add failing tests for a generic `application_present` expected state, per-step heartbeat, parent cancellation, and a hard elapsed-time boundary.
2. Preserve the existing maximum ten actions and allowlist.
3. Pass one composed abort signal to observation, model decision, action, and readback calls.
4. Return only bounded structured terminal results: completed, `agent_step_limit`, `time_limit`, or `cancelled`.
5. Run the focused adapter test.

### Task 2: Make the existing local agent-runner bridge cancellable and budgeted

**Files:**
- Modify: `apps/mr-bot/lib/connector-luna-judgment.js`
- Modify: `apps/mr-bot/lib/connector-luna-judgment.test.js`

1. Add failing tests showing the bridge passes an explicit runner timeout, read-only mode, token-budget environment, and abort signal.
2. Replace the production synchronous child call with an awaited child process. Keep the existing injected synchronous test seam.
3. Rely on `agent_runner.py` for schema validation, provider timeout, evidence containment, token ledger, and provider-child signal forwarding.
4. Run the focused runner test.

### Task 3: Wire bounds into the existing action proposer

**Files:**
- Modify: `apps/mr-bot/lib/connector-production-browser-harness.js`
- Modify: `apps/mr-bot/lib/connector-production-browser-harness.test.js`

1. Add a failing assertion that each decision call receives the step signal and one explicit token budget.
2. Pass the adapter signal, read-only mode, timeout, and per-step token scope to `runLocalAgentRunner`.
3. Run the focused proposer and adapter tests, then the adjacent marketplace effect/runtime worker tests.

### Close GA-05

After all focused checks are green, update only the GA-05 row in the canonical execution spec with the measured guarantees and test count. Fetch, inspect the diff, commit each coherent slice, push the task branch, and read back PR #3018. Do not start GA-10 in the same commit.
