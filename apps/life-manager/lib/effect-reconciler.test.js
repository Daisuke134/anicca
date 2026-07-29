"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { reconcileUnknownEffect } = require("./effect-reconciler.js");

function reconcilingJob(overrides = {}) {
  return {
    job_id: "job-001",
    tenant_id: "tenant-a",
    loop_id: "marketing.anicca.slideshow",
    effect_class: "publish",
    effect_key: "tiktok:anicca:asset-001",
    attempt: 1,
    max_attempts: 3,
    status: "reconciling",
    ...overrides,
  };
}

test("provider proof of presence completes the same attempt with an immutable receipt", async () => {
  const resolutions = [];
  const result = await reconcileUnknownEffect(reconcilingJob(), {
    adapter: {
      inspectEffect: async ({ effectKey }) => ({
        state: "present",
        receipt: {
          provider_id: "post-123",
          url: "https://example.com/post/123",
          checked_effect_key: effectKey,
        },
      }),
    },
    store: {
      resolveReconciliation: async (value) => {
        resolutions.push(value);
        return { status: "completed" };
      },
    },
  });

  assert.equal(result.status, "completed");
  assert.equal(resolutions.length, 1);
  assert.equal(resolutions[0].decision, "present");
  assert.equal(resolutions[0].attempt, 1);
  assert.equal(resolutions[0].receipt.provider_id, "post-123");
});

test("provider proof of absence is the only path that permits a retry", async () => {
  const resolutions = [];
  const result = await reconcileUnknownEffect(reconcilingJob(), {
    adapter: {
      inspectEffect: async () => ({
        state: "absent",
        receipt: { lookup: "provider_not_found" },
      }),
    },
    store: {
      resolveReconciliation: async (value) => {
        resolutions.push(value);
        return { status: "queued" };
      },
    },
  });

  assert.equal(result.status, "queued");
  assert.equal(resolutions[0].decision, "absent");
});

test("unknown provider state stays reconciling and never calls a retry mutation", async () => {
  let mutations = 0;
  const result = await reconcileUnknownEffect(reconcilingJob({
    effect_class: "money",
  }), {
    adapter: {
      inspectEffect: async () => ({ state: "unknown" }),
    },
    store: {
      resolveReconciliation: async () => {
        mutations += 1;
      },
    },
  });

  assert.deepEqual(result, {
    status: "reconciling",
    decision: "unknown",
  });
  assert.equal(mutations, 0);
});

test("reconciler fails closed for a non-effect job or malformed adapter proof", async () => {
  const store = { resolveReconciliation: async () => ({}) };
  await assert.rejects(
    reconcileUnknownEffect(reconcilingJob({ effect_class: "none" }), {
      adapter: { inspectEffect: async () => ({ state: "absent" }) },
      store,
    }),
    /effect class/i,
  );
  await assert.rejects(
    reconcileUnknownEffect(reconcilingJob(), {
      adapter: { inspectEffect: async () => ({ state: "maybe" }) },
      store,
    }),
    /adapter proof/i,
  );
});
