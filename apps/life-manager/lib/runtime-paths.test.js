"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const { resolveRuntimePaths } = require("./runtime-paths.js");

test("resolves local runtime directories beneath Life Manager-owned absolute roots", () => {
  const env = {
    LM_MODE: "local",
    LM_DATA_DIR: "/var/lib/life-manager",
    LM_CACHE_DIR: "/var/cache/life-manager",
  };

  assert.deepEqual(resolveRuntimePaths(env), {
    dataDir: "/var/lib/life-manager",
    cacheDir: "/var/cache/life-manager",
    objectDir: "/var/lib/life-manager/objects",
    receiptDir: "/var/lib/life-manager/receipts",
    logDir: "/var/lib/life-manager/logs",
  });
});

test("cloud mode uses the same runtime path contract", () => {
  assert.deepEqual(resolveRuntimePaths({
    LM_MODE: "cloud",
    LM_DATA_DIR: "/srv/life-manager/data",
    LM_CACHE_DIR: "/srv/life-manager/cache",
  }), {
    dataDir: "/srv/life-manager/data",
    cacheDir: "/srv/life-manager/cache",
    objectDir: "/srv/life-manager/data/objects",
    receiptDir: "/srv/life-manager/data/receipts",
    logDir: "/srv/life-manager/data/logs",
  });
});

test("fails closed when mode is unset or unsupported", () => {
  assert.throws(
    () => resolveRuntimePaths({
      LM_DATA_DIR: "/var/lib/life-manager",
      LM_CACHE_DIR: "/var/cache/life-manager",
    }),
    /LM_MODE/,
  );
  assert.throws(
    () => resolveRuntimePaths({
      LM_MODE: "hybrid",
      LM_DATA_DIR: "/var/lib/life-manager",
      LM_CACHE_DIR: "/var/cache/life-manager",
    }),
    /LM_MODE/,
  );
});

test("rejects missing or relative runtime roots", () => {
  assert.throws(
    () => resolveRuntimePaths({
      LM_MODE: "local",
      LM_DATA_DIR: "state",
      LM_CACHE_DIR: "/var/cache/life-manager",
    }),
    /LM_DATA_DIR.*absolute/i,
  );
  assert.throws(
    () => resolveRuntimePaths({
      LM_MODE: "local",
      LM_DATA_DIR: "/var/lib/life-manager",
    }),
    /LM_CACHE_DIR.*absolute/i,
  );
});

test("rejects legacy execution roots and traversal into them", () => {
  const forbidden = [
    "/Users/operator/.openclaw/state",
    "/Users/operator/profitable-claude/state",
    "/Users/operator/anicca/state",
    "/srv/anicca/state",
    "/Users/operator/life-manager-v0/state",
    "/srv/life-manager/allowed/../../profitable-claude/cache",
  ];

  for (const candidate of forbidden) {
    assert.throws(
      () => resolveRuntimePaths({
        LM_MODE: "local",
        LM_DATA_DIR: candidate,
        LM_CACHE_DIR: "/var/cache/life-manager",
      }),
      /legacy runtime root/i,
      candidate,
    );
  }
});

test("allows a username named anicca when the runtime is outside the legacy anicca repository", () => {
  assert.equal(resolveRuntimePaths({
    LM_MODE: "local",
    LM_DATA_DIR: "/Users/operator/Library/Application Support/Life Manager",
    LM_CACHE_DIR: "/Users/operator/Library/Caches/Life Manager",
  }).dataDir, "/Users/operator/Library/Application Support/Life Manager");
});
