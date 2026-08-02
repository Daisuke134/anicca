"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const { persistPreparedFence, replaceFence, readFence } = require("./yc-typed-update-store.js");

function fence(overrides = {}) {
  const core = {
    schema_version: 1,
    plan_digest: "a".repeat(64),
    operation_id: "b".repeat(64),
    operation_type: "demo_update",
    payload_digest: "c".repeat(64),
    expected_readback_digest: "c".repeat(64),
    state: "prepared",
    prepared_at: "2026-08-02T09:00:00.000Z",
    effect_attempted_at: null,
    readback_at: null,
    activation_count: 0,
    readback_digest: null,
    ...overrides,
  };
  const { createHash } = require("node:crypto");
  const stable = (value) => {
    if (Array.isArray(value)) return `[${value.map(stable).join(",")}]`;
    if (value && typeof value === "object") return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stable(value[key])}`).join(",")}}`;
    return JSON.stringify(value);
  };
  return { ...core, fence_digest: createHash("sha256").update(stable(core)).digest("hex") };
}

function temporaryPath(t) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "yc-update-store-"));
  t.after(() => fs.rmSync(directory, { recursive: true, force: true }));
  return path.join(directory, "fence.json");
}

test("prepared fence is created exclusively and cannot be prepared twice", (t) => {
  const file = temporaryPath(t);
  const prepared = fence();
  persistPreparedFence(file, prepared);
  assert.deepEqual(readFence(file), prepared);
  assert.throws(() => persistPreparedFence(file, prepared), /already exists/i);
});

test("transition is compare-and-swap bound to the prior fence digest", (t) => {
  const file = temporaryPath(t);
  const prepared = fence();
  const attempted = fence({
    state: "effect_attempted",
    effect_attempted_at: "2026-08-02T09:00:01.000Z",
    activation_count: 1,
  });
  persistPreparedFence(file, prepared);
  replaceFence(file, prepared.fence_digest, attempted);
  assert.deepEqual(readFence(file), attempted);
  assert.throws(() => replaceFence(file, prepared.fence_digest, attempted), /compare-and-swap/i);
  assert.deepEqual(readFence(file), attempted);
});

test("invalid fence is rejected before any file is written", (t) => {
  const file = temporaryPath(t);
  const invalid = { ...fence(), activation_count: 2 };
  assert.throws(() => persistPreparedFence(file, invalid), /YC typed update/i);
  assert.equal(fs.existsSync(file), false);
});
