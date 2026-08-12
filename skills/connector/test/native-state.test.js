"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const {
  acquireLock,
  generateOwnerToken,
  heartbeat,
  readHealth,
  releaseLock,
} = require("../lib/native-state.js");

test("owner tokens come from the dedicated native state boundary", () => {
  const token = generateOwnerToken({ randomUUID: () => "12345678-1234-4234-8234-123456789abc" });
  assert.equal(token, "12345678-1234-4234-8234-123456789abc");
  assert.match(token, /^[A-Za-z0-9._-]{16,200}$/);
});

function stateDir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "connector-native-state-"));
}

function options(directory, overrides = {}) {
  return {
    stateDir: directory,
    token: "owner-token-1234567890",
    pid: 4242,
    now: "2026-08-02T01:00:00.000Z",
    staleMs: 60_000,
    isProcessAlive: () => true,
    ...overrides,
  };
}

test("a live owner blocks a concurrent Connector pass", () => {
  const directory = stateDir();
  try {
    assert.deepEqual(acquireLock(options(directory)), { status: "acquired" });
    assert.deepEqual(acquireLock(options(directory, { token: "other-owner-token-123456" })), {
      status: "busy",
    });
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});

test("only a dead stale owner is reaped and a different owner cannot release its lock", () => {
  const directory = stateDir();
  try {
    assert.deepEqual(acquireLock(options(directory, {
      token: "dead-owner-token-1234567",
      pid: 999999,
      now: "2026-08-02T00:00:00.000Z",
      isProcessAlive: () => false,
    })), { status: "acquired" });

    assert.deepEqual(acquireLock(options(directory, {
      now: "2026-08-02T01:00:01.000Z",
      isProcessAlive: (pid) => pid !== 999999,
    })), { status: "acquired" });
    assert.deepEqual(releaseLock({
      stateDir: directory,
      token: "other-owner-token-123456",
    }), { status: "not_owner" });
    assert.deepEqual(releaseLock({
      stateDir: directory,
      token: "owner-token-1234567890",
    }), { status: "released" });
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});

test("a stale reaper returns busy rather than deleting a contender's newly acquired lock", () => {
  const directory = stateDir();
  try {
    assert.deepEqual(acquireLock(options(directory, {
      token: "dead-owner-token-1234567",
      pid: 999999,
      now: "2026-08-02T00:00:00.000Z",
      isProcessAlive: () => false,
    })), { status: "acquired" });

    let contender;
    const reaper = acquireLock(options(directory, {
      token: "outer-reaper-token-123456",
      pid: 4243,
      now: "2026-08-02T01:00:01.000Z",
      isProcessAlive: () => {
        contender = acquireLock(options(directory, {
          token: "contender-owner-token-123",
          pid: 4244,
          now: "2026-08-02T01:00:01.000Z",
          isProcessAlive: () => false,
        }));
        return false;
      },
    }));

    assert.deepEqual(contender, { status: "acquired" });
    assert.deepEqual(reaper, { status: "busy" });
    assert.deepEqual(releaseLock({
      stateDir: directory,
      token: "contender-owner-token-123",
    }), { status: "released" });
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});

test("heartbeat records liveness without retaining an owner token", () => {
  const directory = stateDir();
  try {
    assert.deepEqual(acquireLock(options(directory)), { status: "acquired" });
    assert.deepEqual(heartbeat(options(directory, {
      stage: "worker_started",
      now: "2026-08-02T01:00:05.000Z",
    })), { status: "updated" });

    const health = readHealth({
      stateDir: directory,
      now: "2026-08-02T01:00:10.000Z",
      staleMs: 60_000,
    });
    assert.deepEqual(health, {
      heartbeat: { status: "fresh", stage: "worker_started" },
      lock: { status: "held" },
    });
    const stateText = fs.readFileSync(path.join(directory, "heartbeat.json"), "utf8");
    assert.equal(stateText.includes("owner-token-1234567890"), false);
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});
