// FIND-003 fix (REQ-305 edge case): pending-registry-append.js -- a durable, retryable queue for a
// transient citizens.json append failure. Reuses ledger.js's own generic (file,row) read/append
// primitives (mirrors shelter-cost-ledger.test.js's own thin-wrapper test precedent).
const { test } = require("node:test");
const assert = require("node:assert/strict");
const os = require("node:os");
const fs = require("node:fs");
const path = require("node:path");
const {
  readPendingRegistryAppends,
  queuePendingRegistryAppend,
  resolvePendingRegistryAppend,
  deriveOutstandingRegistryAppends,
} = require("../pending-registry-append.js");

function tmpFile() {
  return path.join(fs.mkdtempSync(path.join(os.tmpdir(), "anicca-pending-registry-append-")), "pending-registry-appends.jsonl");
}

test("readPendingRegistryAppends returns [] when the file does not exist", () => {
  const f = path.join(os.tmpdir(), "definitely-missing-" + Date.now(), "pending-registry-appends.jsonl");
  assert.deepEqual(readPendingRegistryAppends(f), []);
});

test("queuePendingRegistryAppend then readPendingRegistryAppends round-trips one pending row", () => {
  const f = tmpFile();
  queuePendingRegistryAppend(f, {
    childId: "anicca-c001",
    citizenRecord: { id: "anicca-c001" },
    citizensRegistryFile: "/some/citizens.json",
    queuedMs: 1720000000000,
    error: "ENOTDIR: not a directory",
  });
  const rows = readPendingRegistryAppends(f);
  assert.equal(rows.length, 1);
  assert.equal(rows[0].child_id, "anicca-c001");
  assert.equal(rows[0].status, "pending");
  assert.deepEqual(rows[0].citizen_record, { id: "anicca-c001" });
});

test("deriveOutstandingRegistryAppends returns a queued entry that has no later resolved row", () => {
  const f = tmpFile();
  queuePendingRegistryAppend(f, { childId: "anicca-c001", citizenRecord: { id: "anicca-c001" }, citizensRegistryFile: "/c.json", queuedMs: 1, error: "e" });
  const outstanding = deriveOutstandingRegistryAppends(readPendingRegistryAppends(f));
  assert.equal(outstanding.length, 1);
  assert.equal(outstanding[0].child_id, "anicca-c001");
});

test("deriveOutstandingRegistryAppends excludes an entry once resolvePendingRegistryAppend appends its resolved row (last-row-wins)", () => {
  const f = tmpFile();
  queuePendingRegistryAppend(f, { childId: "anicca-c001", citizenRecord: { id: "anicca-c001" }, citizensRegistryFile: "/c.json", queuedMs: 1, error: "e" });
  resolvePendingRegistryAppend(f, "anicca-c001");
  const outstanding = deriveOutstandingRegistryAppends(readPendingRegistryAppends(f));
  assert.equal(outstanding.length, 0, "a resolved entry must never be re-surfaced as outstanding");
});

test("deriveOutstandingRegistryAppends tracks multiple children independently, one entry per child_id (never per raw row)", () => {
  const f = tmpFile();
  queuePendingRegistryAppend(f, { childId: "anicca-c001", citizenRecord: { id: "anicca-c001" }, citizensRegistryFile: "/c.json", queuedMs: 1, error: "e" });
  queuePendingRegistryAppend(f, { childId: "anicca-c002", citizenRecord: { id: "anicca-c002" }, citizensRegistryFile: "/c.json", queuedMs: 2, error: "e" });
  resolvePendingRegistryAppend(f, "anicca-c001");
  const outstanding = deriveOutstandingRegistryAppends(readPendingRegistryAppends(f));
  assert.equal(outstanding.length, 1);
  assert.equal(outstanding[0].child_id, "anicca-c002");
});
