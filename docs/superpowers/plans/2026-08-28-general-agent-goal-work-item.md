# General Agent Goal to WorkItem Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert one active explicit Mr.bot goal into one immutable, reference-only runtime WorkItem without adding a graph engine or causing an external effect.

**Architecture:** Reuse `intent-graph.js` to validate that the supplied goal is active and explicit, then reuse `runtime-job-store.js` to produce the canonical job shape. The adapter carries only an opaque goal reference; it never copies the goal statement, chooses a provider, ranks opportunities, or executes an application.

**Tech Stack:** Node.js 22, CommonJS, `node:test`, existing `intent-graph.js`, existing `runtime-job-store.js`.

## Global Constraints

- Do not modify Coconala code, state, browser, owner, tests, or documentation.
- Do not add margin, ranking, allocation, local/cloud parity, self-funding, provider logic, a scheduler, a database, or a graph framework.
- Semantic judgment remains model-owned. This adapter performs validation and bookkeeping only.
- The runtime job uses `effectClass: "none"`, `effectKey: null`, and `maxAttempts: 1`; GA-04 owns any later external-effect transition.
- The job stores `goal_ref` only. The goal statement, provenance evidence, credentials, and personal data must not enter `input_refs`.
- Change two code/test files, with about 80 total lines as the soft target.

---

### Task 1: Map one active explicit goal to the existing runtime job contract

**Files:**
- Create: `apps/mr-bot/lib/goal-work-item.js`
- Test: `apps/mr-bot/lib/goal-work-item.test.js`

**Interfaces:**
- Consumes: one existing `IntentEntry` accepted by `buildGraph([goal])`, plus `nowMs: number`.
- Produces: `buildGoalWorkItem(goal, nowMs) -> Readonly<RuntimeJob>` using the existing `buildRuntimeJob(...)` return shape.
- Constants: `LOOP_ID = "mr-bot.manager"`, `CAPABILITY = "general-agent.work"`.

- [x] **Step 1: Write the failing contract test**

Create `apps/mr-bot/lib/goal-work-item.test.js`:

```js
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { buildGoalWorkItem } = require("./goal-work-item.js");

const NOW_MS = Date.parse("2026-08-28T00:00:00.000Z");

function goal(overrides = {}) {
  return {
    id: "goal-1",
    uid: "tenant-1",
    kind: "explicit_goal",
    statement: "Apply to one permitted paid opportunity",
    provenance: {
      source: "user_message",
      evidence: "private-message-ref",
      observedAt: "2026-08-27T00:00:00.000Z",
    },
    confidenceTier: "explicit",
    confidence: 0.9,
    expiresAt: null,
    status: "active",
    supersedes: null,
    ...overrides,
  };
}

test("one active explicit goal becomes one reference-only effect-free WorkItem", () => {
  const workItem = buildGoalWorkItem(goal(), NOW_MS);
  assert.deepEqual(workItem, {
    job_id: "goal:goal-1",
    tenant_id: "tenant-1",
    loop_id: "mr-bot.manager",
    capability: "general-agent.work",
    effect_class: "none",
    effect_key: null,
    input_refs: { goal_ref: "intent-entry://tenant-1/goal-1" },
    max_attempts: 1,
  });
  assert.equal(Object.isFrozen(workItem), true);
  assert.doesNotMatch(JSON.stringify(workItem), /permitted paid opportunity|private-message-ref/);
});

test("inactive or non-goal entries cannot become WorkItems", () => {
  assert.throws(() => buildGoalWorkItem(goal(), undefined), /observation time/i);
  assert.throws(
    () => buildGoalWorkItem(goal({ expiresAt: "2026-08-27T00:00:00.000Z" }), NOW_MS),
    /active explicit goal/i,
  );
  assert.throws(
    () => buildGoalWorkItem(goal({ kind: "repeated_preference" }), NOW_MS),
    /active explicit goal/i,
  );
});
```

- [x] **Step 2: Run the focused test and verify RED**

Run:

```bash
node --test apps/mr-bot/lib/goal-work-item.test.js
```

Expected: FAIL because `goal-work-item.js` does not exist.

- [x] **Step 3: Implement the minimum pure adapter**

Create `apps/mr-bot/lib/goal-work-item.js`:

```js
"use strict";

const { buildGraph, effectiveEntries } = require("./intent-graph.js");
const { buildRuntimeJob } = require("./runtime-job-store.js");

const LOOP_ID = "mr-bot.manager";
const CAPABILITY = "general-agent.work";

function buildGoalWorkItem(goal, nowMs) {
  if (!Number.isFinite(nowMs)) throw new Error("WorkItem observation time is required");
  const active = effectiveEntries(buildGraph([goal]), nowMs);
  if (active.length !== 1 || active[0].kind !== "explicit_goal") {
    throw new Error("WorkItem requires one active explicit goal");
  }
  const entry = active[0];
  return buildRuntimeJob({
    jobId: `goal:${entry.id}`,
    tenantId: entry.uid,
    loopId: LOOP_ID,
    capability: CAPABILITY,
    effectClass: "none",
    effectKey: null,
    inputRefs: {
      goal_ref: `intent-entry://${encodeURIComponent(entry.uid)}/${encodeURIComponent(entry.id)}`,
    },
    maxAttempts: 1,
  });
}

module.exports = { LOOP_ID, CAPABILITY, buildGoalWorkItem };
```

- [x] **Step 4: Run focused and adjacent contract tests**

Run:

```bash
node --test \
  apps/mr-bot/lib/goal-work-item.test.js \
  apps/mr-bot/lib/intent-graph.test.js \
  apps/mr-bot/lib/runtime-job-store.test.js
git diff --check
```

Expected: all Node tests PASS, failures 0, and `git diff --check` exits 0.

- [x] **Step 5: Commit and push the code slice**

```bash
git add apps/mr-bot/lib/goal-work-item.js \
  apps/mr-bot/lib/goal-work-item.test.js
git commit -m "feat(mr-bot): map goals to work items"
git push
```

### Primary-only closeout

After Step 4 evidence is fresh, the primary agent changes only the GA-02 row in
`docs/superpowers/specs/2026-08-01-dais-mr-bot-five-phase-execution-spec.md` from `TODO` to `DONE` and records the focused test count. It does not begin GA-03 in the same slice.

Run:

```bash
git diff --check
node --test \
  apps/mr-bot/lib/goal-work-item.test.js \
  apps/mr-bot/lib/intent-graph.test.js \
  apps/mr-bot/lib/runtime-job-store.test.js
```

Then commit and push the measured state update:

```bash
git add docs/superpowers/specs/2026-08-01-dais-mr-bot-five-phase-execution-spec.md
git commit -m "docs(mr-bot): close goal work item"
git push
```
