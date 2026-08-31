"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const { resolveDataRoot, resolveRuntimePaths } = require("./runtime-paths.js");

test("resolves local runtime directories beneath Mr.bot-owned absolute roots", () => {
  const env = {
    LM_MODE: "local",
    LM_DATA_DIR: "/var/lib/mr-bot",
    LM_CACHE_DIR: "/var/cache/mr-bot",
  };

  assert.deepEqual(resolveRuntimePaths(env), {
    dataDir: "/var/lib/mr-bot",
    cacheDir: "/var/cache/mr-bot",
    objectDir: "/var/lib/mr-bot/objects",
    receiptDir: "/var/lib/mr-bot/receipts",
    logDir: "/var/lib/mr-bot/logs",
  });
});

test("cloud mode uses the same runtime path contract", () => {
  assert.deepEqual(resolveRuntimePaths({
    LM_MODE: "cloud",
    LM_DATA_DIR: "/srv/mr-bot/data",
    LM_CACHE_DIR: "/srv/mr-bot/cache",
  }), {
    dataDir: "/srv/mr-bot/data",
    cacheDir: "/srv/mr-bot/cache",
    objectDir: "/srv/mr-bot/data/objects",
    receiptDir: "/srv/mr-bot/data/receipts",
    logDir: "/srv/mr-bot/data/logs",
  });
});

test("fails closed when mode is unset or unsupported", () => {
  assert.throws(
    () => resolveRuntimePaths({
      LM_DATA_DIR: "/var/lib/mr-bot",
      LM_CACHE_DIR: "/var/cache/mr-bot",
    }),
    /LM_MODE/,
  );
  assert.throws(
    () => resolveRuntimePaths({
      LM_MODE: "hybrid",
      LM_DATA_DIR: "/var/lib/mr-bot",
      LM_CACHE_DIR: "/var/cache/mr-bot",
    }),
    /LM_MODE/,
  );
});

test("rejects missing or relative runtime roots", () => {
  assert.throws(
    () => resolveRuntimePaths({
      LM_MODE: "local",
      LM_DATA_DIR: "state",
      LM_CACHE_DIR: "/var/cache/mr-bot",
    }),
    /LM_DATA_DIR.*absolute/i,
  );
  assert.throws(
    () => resolveRuntimePaths({
      LM_MODE: "local",
      LM_DATA_DIR: "/var/lib/mr-bot",
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
    "/Users/operator/mr-bot-v0/state",
    "/srv/mr-bot/allowed/../../profitable-claude/cache",
  ];

  for (const candidate of forbidden) {
    assert.throws(
      () => resolveRuntimePaths({
        LM_MODE: "local",
        LM_DATA_DIR: candidate,
        LM_CACHE_DIR: "/var/cache/mr-bot",
      }),
      /legacy runtime root/i,
      candidate,
    );
  }
});

test("resolveDataRoot prefers LM_DATA_DIR and falls back to the portable state root", () => {
  assert.equal(
    resolveDataRoot({ LM_DATA_DIR: "/var/lib/mr-bot" }),
    "/var/lib/mr-bot",
  );
  assert.equal(
    resolveDataRoot({ HOME: "/Users/operator" }),
    "/Users/operator/.local/state/mr-bot",
  );
});

test("resolveDataRoot fails closed on relative overrides and legacy roots", () => {
  assert.throws(
    () => resolveDataRoot({ LM_DATA_DIR: "state" }),
    /absolute/i,
  );
  assert.throws(
    () => resolveDataRoot({ LM_DATA_DIR: "/Users/operator/.openclaw/state" }),
    /legacy runtime root/i,
  );
  assert.throws(
    () => resolveDataRoot({ HOME: "/srv/anicca" }),
    /legacy runtime root/i,
  );
});

test("allows a username named anicca when the runtime is outside the legacy anicca repository", () => {
  assert.equal(resolveRuntimePaths({
    LM_MODE: "local",
    LM_DATA_DIR: "/Users/operator/Library/Application Support/Mr.bot",
    LM_CACHE_DIR: "/Users/operator/Library/Caches/Mr.bot",
  }).dataDir, "/Users/operator/Library/Application Support/Mr.bot");
});
