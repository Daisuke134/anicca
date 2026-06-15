const { test } = require("node:test");
const assert = require("node:assert");
const os = require("node:os");
const fs = require("node:fs");
const path = require("node:path");
const { appendChild, readChildren } = require("../ledger");

function tmpFile() {
  return path.join(fs.mkdtempSync(path.join(os.tmpdir(), "spawn-ledger-")), "children.jsonl");
}

test("readChildren returns [] when the file does not exist", () => {
  const f = path.join(os.tmpdir(), "definitely-missing-" + Date.now(), "children.jsonl");
  assert.deepStrictEqual(readChildren(f), []);
});

test("appendChild then readChildren round-trips one row", () => {
  const f = tmpFile();
  const row = { child_id: "anicca-c001", wallet: "0xCHILD", spawned_ms: 123 };
  appendChild(f, row);
  const rows = readChildren(f);
  assert.strictEqual(rows.length, 1);
  assert.deepStrictEqual(rows[0], row);
});

test("appendChild is append-only (preserves prior rows)", () => {
  const f = tmpFile();
  appendChild(f, { child_id: "anicca-c001" });
  appendChild(f, { child_id: "anicca-c002" });
  const rows = readChildren(f);
  assert.deepStrictEqual(rows.map((r) => r.child_id), ["anicca-c001", "anicca-c002"]);
});

test("readChildren skips blank lines and is resilient to a trailing newline", () => {
  const f = tmpFile();
  fs.writeFileSync(f, '{"child_id":"a"}\n\n{"child_id":"b"}\n');
  assert.deepStrictEqual(readChildren(f).map((r) => r.child_id), ["a", "b"]);
});

test("appendChild creates parent dirs if needed", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "spawn-ledger-deep-"));
  const f = path.join(dir, "nested", "state", "children.jsonl");
  appendChild(f, { child_id: "anicca-c001" });
  assert.strictEqual(readChildren(f).length, 1);
});
