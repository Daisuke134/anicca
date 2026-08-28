# General Agent Application Effect Kernel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn one effect-free Goal WorkItem into one durable marketplace application effect and prove pre-readback, single execution, official post-readback, and replay-zero without a provider-specific brain.

**Architecture:** Reuse `runtime-job-store.js` for immutable effect identity and its existing `publish` class, which already represents outbound applications. Add one reference-only job builder and one provider-neutral effect runner; GA-05 later supplies the model/browser implementation and loop-adapter registration.

**Tech Stack:** Node.js 22, CommonJS, `node:test`, existing `runtime-job-store.js`, existing `effect-reconciler.js` semantics.

## Global Constraints

- Do not modify Coconala code, state, browser, owner, tests, or documentation.
- Do not perform a live provider request, browser action, application, message, or login.
- Do not add a database, migration, scheduler, provider selector, margin rule, ranking rule, or model judgment.
- Store references only. Goal text, proposal text, account data, authorization evidence, and credentials never enter the runtime job.
- `effectClass` is the existing `publish`; `maxAttempts` is 1; the effect key changes when any bound reference changes.
- Never trust the execution callback as success. Only the second official inspection plus `verifyReceipt` may complete the effect.
- Unknown state before or after execution is `unknownEffect=true`; replay with an already-present receipt executes zero mutations.
- Change two production files and one test file. Split implementation into two independently verified commits.

---

### Task 1: Freeze one marketplace application effect identity

**Files:**
- Create: `apps/life-manager/lib/marketplace-application-job.js`
- Test: `apps/life-manager/lib/marketplace-application-effect.test.js`

**Interfaces:**
- Consumes: canonical GA-02 Goal WorkItem plus `capabilityRef`, `opportunityRef`, `intentRef`, and `authorizationRef`.
- Produces: `buildMarketplaceApplicationJob(input) -> Readonly<RuntimeJob>` and `marketplaceApplicationContract(job) -> Readonly<ApplicationEffectContract>`.
- Constants: `LOOP_ID = "life-manager.manager"`, `CAPABILITY = "marketplace.application"`.

- [x] **Step 1: Write the failing effect-identity tests**

Create `apps/life-manager/lib/marketplace-application-effect.test.js`:

```js
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const {
  buildMarketplaceApplicationJob,
  marketplaceApplicationContract,
} = require("./marketplace-application-job.js");

function goalWorkItem() {
  return {
    job_id: "goal:goal-1",
    tenant_id: "tenant-1",
    loop_id: "life-manager.manager",
    capability: "general-agent.work",
    effect_class: "none",
    effect_key: null,
    input_refs: { goal_ref: "intent-entry://tenant-1/goal-1" },
    max_attempts: 1,
  };
}

function input(overrides = {}) {
  return {
    goalWorkItem: goalWorkItem(),
    capabilityRef: "provider-capability://lancers/marketplace.application",
    opportunityRef: "marketplace-opportunity://lancers/job-123",
    intentRef: `application-intent://sha256/${"a".repeat(64)}`,
    authorizationRef: `authorization-receipt://sha256/${"b".repeat(64)}`,
    ...overrides,
  };
}

test("application identity is deterministic, reference-only, and authorization-bound", () => {
  const first = buildMarketplaceApplicationJob(input());
  const replay = buildMarketplaceApplicationJob(input());
  const changedAuthorization = buildMarketplaceApplicationJob(input({
    authorizationRef: `authorization-receipt://sha256/${"c".repeat(64)}`,
  }));
  assert.deepEqual(replay, first);
  assert.equal(first.effect_class, "publish");
  assert.equal(first.max_attempts, 1);
  assert.notEqual(changedAuthorization.effect_key, first.effect_key);
  assert.doesNotMatch(JSON.stringify(first), /proposal|account|credential|private/i);
  assert.deepEqual(marketplaceApplicationContract(first).input_refs, first.input_refs);
});

test("noncanonical parent or unbound references are rejected", () => {
  assert.throws(
    () => buildMarketplaceApplicationJob(input({
      goalWorkItem: { ...goalWorkItem(), effect_class: "publish" },
    })),
    /Goal WorkItem/i,
  );
  assert.throws(
    () => buildMarketplaceApplicationJob(input({ authorizationRef: "authorization-receipt://raw" })),
    /authorization reference/i,
  );
  assert.throws(
    () => buildMarketplaceApplicationJob(input({
      capabilityRef: "provider-capability://fiverr/marketplace.application",
    })),
    /provider mismatch/i,
  );
  const valid = buildMarketplaceApplicationJob(input());
  assert.throws(
    () => marketplaceApplicationContract({
      ...valid,
      input_refs: { ...valid.input_refs, extra_ref: "object://unexpected" },
    }),
    /job invalid/i,
  );
});
```

- [x] **Step 2: Run the focused test and verify RED**

Run:

```bash
node --test apps/life-manager/lib/marketplace-application-effect.test.js
```

Expected: FAIL because `marketplace-application-job.js` does not exist.

- [x] **Step 3: Implement the minimum job builder and contract reader**

Create `apps/life-manager/lib/marketplace-application-job.js`:

```js
"use strict";

const { createHash } = require("node:crypto");
const { isDeepStrictEqual } = require("node:util");
const { buildRuntimeJob } = require("./runtime-job-store.js");

const LOOP_ID = "life-manager.manager";
const CAPABILITY = "marketplace.application";
const HASH = /^[0-9a-f]{64}$/;

function reference(value, prefix, label) {
  const text = String(value == null ? "" : value).trim();
  if (!text.startsWith(prefix)) throw new Error(`${label} reference invalid`);
  return text;
}

function hashReference(value, prefix, label) {
  const text = reference(value, prefix, label);
  if (!HASH.test(text.slice(prefix.length))) throw new Error(`${label} reference invalid`);
  return text;
}

function providerReference(value, prefix, label) {
  const text = reference(value, prefix, label);
  const parts = text.slice(prefix.length).split("/");
  if (parts.length !== 2 || !parts[0] || !parts[1]) {
    throw new Error(`${label} reference invalid`);
  }
  return { text, provider: parts[0], resource: parts[1] };
}

function parentGoal(job) {
  const keys = job && job.input_refs && Object.keys(job.input_refs);
  if (
    !job
    || job.loop_id !== LOOP_ID
    || job.capability !== "general-agent.work"
    || job.effect_class !== "none"
    || job.effect_key !== null
    || job.max_attempts !== 1
    || JSON.stringify(keys) !== JSON.stringify(["goal_ref"])
  ) throw new Error("canonical Goal WorkItem required");
  const goalPrefix = `intent-entry://${encodeURIComponent(job.tenant_id)}/`;
  if (!String(job.input_refs.goal_ref || "").startsWith(goalPrefix)) {
    throw new Error("canonical Goal WorkItem required");
  }
  return job;
}

function buildMarketplaceApplicationJob(input = {}) {
  const parent = parentGoal(input.goalWorkItem);
  const capability = providerReference(
    input.capabilityRef,
    "provider-capability://",
    "capability",
  );
  const opportunity = providerReference(
    input.opportunityRef,
    "marketplace-opportunity://",
    "opportunity",
  );
  if (capability.resource !== "marketplace.application") {
    throw new Error("capability reference invalid");
  }
  if (capability.provider !== opportunity.provider) {
    throw new Error("provider mismatch");
  }
  const refs = {
    goal_ref: reference(parent.input_refs.goal_ref, "intent-entry://", "goal"),
    capability_ref: capability.text,
    opportunity_ref: opportunity.text,
    intent_ref: hashReference(input.intentRef, "application-intent://sha256/", "intent"),
    authorization_ref: hashReference(
      input.authorizationRef,
      "authorization-receipt://sha256/",
      "authorization",
    ),
  };
  const digest = createHash("sha256")
    .update(JSON.stringify([parent.tenant_id, ...Object.values(refs)]), "utf8")
    .digest("hex");
  return buildRuntimeJob({
    jobId: `marketplace-application:${digest}`,
    tenantId: parent.tenant_id,
    loopId: LOOP_ID,
    capability: CAPABILITY,
    effectClass: "publish",
    effectKey: `marketplace-application:v1:${digest}`,
    inputRefs: refs,
    maxAttempts: 1,
  });
}

function marketplaceApplicationContract(job) {
  const refs = job && job.input_refs;
  const expected = buildMarketplaceApplicationJob({
    goalWorkItem: {
      tenant_id: job && job.tenant_id,
      loop_id: LOOP_ID,
      capability: "general-agent.work",
      effect_class: "none",
      effect_key: null,
      input_refs: { goal_ref: refs && refs.goal_ref },
      max_attempts: 1,
    },
    capabilityRef: refs && refs.capability_ref,
    opportunityRef: refs && refs.opportunity_ref,
    intentRef: refs && refs.intent_ref,
    authorizationRef: refs && refs.authorization_ref,
  });
  for (const key of ["job_id", "tenant_id", "loop_id", "capability", "effect_class", "effect_key", "max_attempts"]) {
    if (!job || job[key] !== expected[key]) throw new Error("marketplace application job invalid");
  }
  if (!isDeepStrictEqual(job.input_refs, expected.input_refs)) {
    throw new Error("marketplace application job invalid");
  }
  return Object.freeze({
    tenant_id: job.tenant_id,
    job_id: job.job_id,
    effect_key: job.effect_key,
    input_refs: Object.freeze({ ...refs }),
  });
}

module.exports = {
  LOOP_ID,
  CAPABILITY,
  buildMarketplaceApplicationJob,
  marketplaceApplicationContract,
};
```

- [x] **Step 4: Run the focused and runtime-job tests**

Run:

```bash
node --test \
  apps/life-manager/lib/marketplace-application-effect.test.js \
  apps/life-manager/lib/goal-work-item.test.js \
  apps/life-manager/lib/runtime-job-store.test.js
git diff --check
```

Expected: all tests PASS and `git diff --check` exits 0.

- [x] **Step 5: Commit and push Task 1**

```bash
git add apps/life-manager/lib/marketplace-application-job.js \
  apps/life-manager/lib/marketplace-application-effect.test.js
git commit -m "feat(life-manager): freeze application effects"
git push
```

### Task 2: Execute once and complete only from official post-readback

**Files:**
- Create: `apps/life-manager/lib/marketplace-application-effect.js`
- Modify: `apps/life-manager/lib/marketplace-application-effect.test.js`

**Interfaces:**
- Consumes: canonical application job and dependencies `inspectApplication`, `executeOnce`, and `verifyReceipt`.
- Produces: `runMarketplaceApplicationEffect(job, deps) -> {receipt, effect_started, replayed}` or `MarketplaceApplicationEffectError` with `code` and `unknownEffect`.

- [x] **Step 1: Add failing execution and replay tests**

Append to `apps/life-manager/lib/marketplace-application-effect.test.js`:

```js
const {
  runMarketplaceApplicationEffect,
} = require("./marketplace-application-effect.js");

test("absent effect executes once, completes from post-readback, and replays zero", async () => {
  const job = buildMarketplaceApplicationJob(input());
  let submitted = false;
  let executions = 0;
  const deps = {
    inspectApplication: async () => submitted
      ? { state: "present", receipt: { record_type: "application_receipt" } }
      : { state: "absent" },
    executeOnce: async () => { executions += 1; submitted = true; },
    verifyReceipt: (receipt) => Object.freeze({ ...receipt, verified: true }),
  };
  const first = await runMarketplaceApplicationEffect(job, deps);
  const replay = await runMarketplaceApplicationEffect(job, deps);
  assert.equal(first.effect_started, true);
  assert.equal(first.receipt.verified, true);
  assert.equal(replay.replayed, true);
  assert.equal(executions, 1);
});

test("unknown pre-readback never executes and remains an unknown effect", async () => {
  const job = buildMarketplaceApplicationJob(input());
  let executions = 0;
  await assert.rejects(
    runMarketplaceApplicationEffect(job, {
      inspectApplication: async () => ({ state: "unknown" }),
      executeOnce: async () => { executions += 1; },
      verifyReceipt: (receipt) => receipt,
    }),
    (error) => error.code === "APPLICATION_EFFECT_UNKNOWN" && error.unknownEffect === true,
  );
  assert.equal(executions, 0);
});

test("post-readback failure is unknown after exactly one execution", async () => {
  const job = buildMarketplaceApplicationJob(input());
  let inspections = 0;
  let executions = 0;
  await assert.rejects(
    runMarketplaceApplicationEffect(job, {
      inspectApplication: async () => {
        inspections += 1;
        if (inspections === 1) return { state: "absent" };
        throw new Error("provider unavailable");
      },
      executeOnce: async () => { executions += 1; },
      verifyReceipt: (receipt) => receipt,
    }),
    (error) => error.code === "APPLICATION_EFFECT_UNKNOWN" && error.unknownEffect === true,
  );
  assert.equal(executions, 1);
});
```

- [x] **Step 2: Run the focused test and verify RED**

Run:

```bash
node --test apps/life-manager/lib/marketplace-application-effect.test.js
```

Expected: FAIL because `marketplace-application-effect.js` does not exist.

- [x] **Step 3: Implement the minimum pre/execute/post kernel**

Create `apps/life-manager/lib/marketplace-application-effect.js`:

```js
"use strict";

const {
  marketplaceApplicationContract,
} = require("./marketplace-application-job.js");

class MarketplaceApplicationEffectError extends Error {
  constructor(message, code, unknownEffect) {
    super(message);
    this.name = "MarketplaceApplicationEffectError";
    this.code = code;
    this.unknownEffect = unknownEffect === true;
  }
}

function proof(value) {
  if (!value || !["absent", "present", "unknown", "human_required"].includes(value.state)) {
    throw new Error("marketplace application readback invalid");
  }
  return value;
}

function verifiedReceipt(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error("verified application receipt invalid");
  }
  return value;
}

async function runMarketplaceApplicationEffect(job, deps = {}) {
  const contract = marketplaceApplicationContract(job);
  for (const name of ["inspectApplication", "executeOnce", "verifyReceipt"]) {
    if (typeof deps[name] !== "function") throw new Error(`application dependency missing: ${name}`);
  }
  const before = proof(await deps.inspectApplication(contract));
  if (before.state === "human_required") {
    throw new MarketplaceApplicationEffectError(
      "Application requires a human ceremony",
      "APPLICATION_HUMAN_REQUIRED",
      false,
    );
  }
  if (before.state === "unknown") {
    throw new MarketplaceApplicationEffectError(
      "Application state is unknown",
      "APPLICATION_EFFECT_UNKNOWN",
      true,
    );
  }
  if (before.state === "present") {
    return Object.freeze({
      receipt: verifiedReceipt(deps.verifyReceipt(before.receipt, contract)),
      effect_started: false,
      replayed: true,
    });
  }
  try {
    await deps.executeOnce(contract);
  } catch (error) {
    const failure = new MarketplaceApplicationEffectError(
      "Application execution failed",
      "APPLICATION_EXECUTION_FAILED",
      error && error.unknownEffect !== false,
    );
    failure.cause = error;
    throw failure;
  }
  let after;
  try {
    after = proof(await deps.inspectApplication(contract));
  } catch (error) {
    const failure = new MarketplaceApplicationEffectError(
      "Application post-readback failed",
      "APPLICATION_EFFECT_UNKNOWN",
      true,
    );
    failure.cause = error;
    throw failure;
  }
  if (after.state === "present") {
    return Object.freeze({
      receipt: verifiedReceipt(deps.verifyReceipt(after.receipt, contract)),
      effect_started: true,
      replayed: false,
    });
  }
  throw new MarketplaceApplicationEffectError(
    "Application post-readback did not confirm the effect",
    after.state === "absent" ? "APPLICATION_EFFECT_ABSENT" : "APPLICATION_EFFECT_UNKNOWN",
    after.state !== "absent",
  );
}

module.exports = {
  MarketplaceApplicationEffectError,
  runMarketplaceApplicationEffect,
};
```

- [x] **Step 4: Run focused and adjacent effect tests**

Run:

```bash
node --test \
  apps/life-manager/lib/marketplace-application-effect.test.js \
  apps/life-manager/lib/goal-work-item.test.js \
  apps/life-manager/lib/runtime-job-store.test.js \
  apps/life-manager/lib/effect-reconciler.test.js
git diff --check
```

Expected: all tests PASS and `git diff --check` exits 0.

- [x] **Step 5: Commit and push Task 2**

```bash
git add apps/life-manager/lib/marketplace-application-effect.js \
  apps/life-manager/lib/marketplace-application-effect.test.js
git commit -m "feat(life-manager): fence application execution"
git push
```

### Primary-only closeout

After both tasks have fresh green evidence, the primary agent marks the plan checkboxes complete and changes only the GA-04 row in `docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md` from `TODO` to `DONE`, recording both commits and the focused test count. It does not start GA-05 in the same commit.
