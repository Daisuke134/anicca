"use strict";

const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const path = require("node:path");
const { test } = require("node:test");

const {
  runBrowserAuthTenantIsolationE2E,
} = require("./browser-auth-tenant-isolation-e2e.js");

const RAW = {
  uidA: "browser-auth-e2e-private-tenant-a",
  uidB: "browser-auth-e2e-private-tenant-b",
  markerA: "a".repeat(64),
  markerB: "b".repeat(64),
};

function fixture({ crossRead = true } = {}) {
  const calls = [];
  const saved = new Map();
  const deps = {
    identities() {
      return [
        { uid: RAW.uidA, marker: RAW.markerA },
        { uid: RAW.uidB, marker: RAW.markerB },
      ];
    },
    hashMarker(marker) {
      return marker === RAW.markerA ? "1".repeat(64) : "2".repeat(64);
    },
    async removeStale() {
      calls.push(["removeStale"]);
      return 0;
    },
    async upsert({ uid, marker }) {
      calls.push(["upsert", uid]);
      const contextHash = uid === RAW.uidA ? "3".repeat(64) : "4".repeat(64);
      saved.set(uid, { contextHash, marker });
      return { contextHash };
    },
    async readFresh({ uid }) {
      calls.push(["readFresh", uid]);
      const row = saved.get(uid);
      return {
        contextHash: row.contextHash,
        markerHash: deps.hashMarker(row.marker),
      };
    },
    async crossReadFails({ sourceUid, targetUid }) {
      calls.push(["crossReadFails", sourceUid, targetUid]);
      return crossRead;
    },
    async ciphertextPlaintextHits({ markers }) {
      calls.push(["ciphertextPlaintextHits", markers.length]);
      return 0;
    },
    async cleanup({ uids }) {
      calls.push(["cleanup", uids.length]);
      for (const uid of uids) saved.delete(uid);
      return uids.length;
    },
    async count({ uids }) {
      calls.push(["count", uids.length]);
      return [...saved.keys()].filter((uid) => uids.includes(uid)).length;
    },
    async close() {
      calls.push(["close"]);
    },
  };
  return { calls, deps };
}

test("runtime image allowlists the tenant isolation production entrypoint", () => {
  const dockerignore = readFileSync(path.join(__dirname, "..", ".dockerignore"), "utf8");
  assert.match(dockerignore, /^!scripts\/browser-auth-tenant-isolation-e2e\.js$/m);
});

test("two encrypted tenant contexts survive fresh-process reads without cross-read or plaintext leakage", async () => {
  const { calls, deps } = fixture();

  const result = await runBrowserAuthTenantIsolationE2E({ deps });

  assert.deepEqual(result, {
    tenant_count: 2,
    origin: "https://example.com",
    context_hashes: ["3".repeat(64), "4".repeat(64)],
    fresh_process_reads: 2,
    distinct_contexts: true,
    cross_read_zero: true,
    ciphertext_plaintext_hits: 0,
    cleanup_count: 2,
    post_cleanup_rows: 0,
  });
  assert.deepEqual(
    calls.map(([name]) => name),
    [
      "removeStale",
      "upsert",
      "upsert",
      "readFresh",
      "readFresh",
      "crossReadFails",
      "crossReadFails",
      "ciphertextPlaintextHits",
      "cleanup",
      "count",
      "close",
    ],
  );
  assert.doesNotMatch(
    JSON.stringify(result),
    new RegExp(`${RAW.uidA}|${RAW.uidB}|${RAW.markerA}|${RAW.markerB}`),
  );
});

test("a failed cross-tenant boundary still removes both controlled rows and closes the database", async () => {
  const { calls, deps } = fixture({ crossRead: false });

  const failure = await runBrowserAuthTenantIsolationE2E({ deps }).then(
    () => null,
    (error) => error,
  );

  assert.equal(failure.message, "browser auth tenant isolation unavailable");
  assert.equal(failure.code, "CROSS_READ");
  assert.equal(calls.filter(([name]) => name === "cleanup").length, 1);
  assert.equal(calls.find(([name]) => name === "cleanup")[1], 2);
  assert.deepEqual(calls.at(-1), ["close"]);
});
