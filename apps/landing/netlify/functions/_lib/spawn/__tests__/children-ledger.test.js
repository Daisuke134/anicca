const { test, beforeEach, afterEach } = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { readChildren, appendChild, nextChildId } = require("../children-ledger");

let dir, file;
beforeEach(() => {
  dir = fs.mkdtempSync(path.join(os.tmpdir(), "spawn-ledger-"));
  file = path.join(dir, "children.jsonl");
});
afterEach(() => fs.rmSync(dir, { recursive: true, force: true }));

test("readChildren on missing file returns []", () => {
  assert.deepEqual(readChildren(file), []);
});

test("appendChild then readChildren round-trips", () => {
  appendChild(file, { childId: "anicca-c001", childWallet: "0xabc" });
  appendChild(file, { childId: "anicca-c002", childWallet: "0xdef" });
  const rows = readChildren(file);
  assert.equal(rows.length, 2);
  assert.equal(rows[0].childId, "anicca-c001");
  assert.equal(rows[1].childWallet, "0xdef");
});

test("readChildren skips blank lines and tolerates trailing newline", () => {
  fs.writeFileSync(file, '{"childId":"anicca-c001"}\n\n{"childId":"anicca-c002"}\n');
  assert.equal(readChildren(file).length, 2);
});

test("nextChildId starts at 001 on empty", () => {
  assert.equal(nextChildId([], "anicca-c"), "anicca-c001");
});

test("nextChildId is monotonic and gap-safe", () => {
  const children = [{ childId: "anicca-c001" }, { childId: "anicca-c003" }];
  assert.equal(nextChildId(children, "anicca-c"), "anicca-c004");
});

test("nextChildId ignores rows without a parseable suffix", () => {
  const children = [{ childId: "weird" }, { childId: "anicca-c007" }];
  assert.equal(nextChildId(children, "anicca-c"), "anicca-c008");
});

test("appendChild creates parent dir if missing", () => {
  const nested = path.join(dir, "state", "children.jsonl");
  appendChild(nested, { childId: "anicca-c001" });
  assert.equal(readChildren(nested).length, 1);
});
