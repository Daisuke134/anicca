"use strict";
// HARD-4 per-tenant isolation — a throw while processing ONE tenant must NOT prevent the others from being
// processed in the same in-process tick (matches the Inngest per-user isolation used in production).
// Run: node --test test/tenant-isolation.test.js
const { test } = require("node:test");
const assert = require("node:assert");
const { forEachUserSafe } = require("../scheduler.js");

test("forEachUserSafe: a throwing tenant does NOT stop the others", async () => {
  const processed = [];
  await forEachUserSafe(
    [{ uid: "aaaaaaaaaaaa" }, { uid: "bbbbbbbbbbbb" }, { uid: "cccccccccccc" }],
    "test",
    (u) => { if (u.uid.startsWith("b")) throw new Error("boom"); processed.push(u.uid); },
  );
  assert.deepStrictEqual(processed, ["aaaaaaaaaaaa", "cccccccccccc"], "a and c processed despite b throwing");
});

test("forEachUserSafe: an async rejection for one tenant is contained too", async () => {
  const processed = [];
  await forEachUserSafe(
    [{ uid: "u1" }, { uid: "u2" }, { uid: "u3" }],
    "test",
    async (u) => { if (u.uid === "u2") return Promise.reject(new Error("async boom")); processed.push(u.uid); },
  );
  assert.deepStrictEqual(processed, ["u1", "u3"]);
});

test("forEachUserSafe: all-ok processes every tenant in order", async () => {
  const processed = [];
  await forEachUserSafe([{ uid: "x" }, { uid: "y" }], "test", (u) => { processed.push(u.uid); });
  assert.deepStrictEqual(processed, ["x", "y"]);
});

test("forEachUserSafe: empty list is a no-op (no throw)", async () => {
  await forEachUserSafe([], "test", () => { throw new Error("should not be called"); });
  await forEachUserSafe(null, "test", () => { throw new Error("should not be called"); });
});

test("forEachUserSafe: a malformed user row (no uid) is contained, others continue", async () => {
  const processed = [];
  await forEachUserSafe([{ uid: "ok1" }, null, { uid: "ok2" }], "test",
    (u) => { processed.push(u.uid); }); // null → fn throws on u.uid → contained
  assert.deepStrictEqual(processed, ["ok1", "ok2"]);
});
