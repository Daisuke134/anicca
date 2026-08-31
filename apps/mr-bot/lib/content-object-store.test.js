"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const {
  importContentObject,
  objectRef,
  resolveContentObject,
} = require("./content-object-store.js");

test("imports immutable bytes by SHA-256 and resolves only a verified content reference", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "lm-objects-"));
  const source = path.join(root, "source.txt");
  const objectDir = path.join(root, "objects");
  fs.writeFileSync(source, "exact caption\n", { mode: 0o600 });

  const imported = importContentObject(source, { objectDir });

  assert.match(imported.ref, /^object:\/\/sha256\/[0-9a-f]{64}$/);
  assert.equal(imported.ref, objectRef(imported.sha256));
  assert.equal(fs.readFileSync(resolveContentObject(imported.ref, { objectDir }), "utf8"), "exact caption\n");
  assert.equal(imported.size_bytes, 14);
});

test("fails closed for traversal, malformed refs, and bytes changed after import", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "lm-objects-"));
  const source = path.join(root, "source.bin");
  const objectDir = path.join(root, "objects");
  fs.writeFileSync(source, "original", { mode: 0o600 });
  const imported = importContentObject(source, { objectDir });
  const stored = resolveContentObject(imported.ref, { objectDir });
  fs.writeFileSync(stored, "tampered", { mode: 0o600 });

  assert.throws(
    () => resolveContentObject(imported.ref, { objectDir }),
    /integrity/i,
  );
  assert.throws(
    () => resolveContentObject("object://sha256/../../private", { objectDir }),
    /reference/i,
  );
  assert.throws(
    () => resolveContentObject("file:///tmp/raw.mp4", { objectDir }),
    /reference/i,
  );
});
