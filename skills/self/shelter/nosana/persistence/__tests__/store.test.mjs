// node:test — store.mjs: createLocalFsStore, the injectable test double every other test in this
// directory uses as "the remote". Exercises the interface contract itself (getText/putText/
// putTextWithMerge/close) independent of any merge policy.
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import { createLocalFsStore } from "../store.mjs";

function tmpRoot() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "citizen-state-localfs-test-"));
}

test("createLocalFsStore: getText returns null for a key that has never been written", async () => {
  const store = createLocalFsStore({ rootDir: tmpRoot() });
  assert.equal(await store.getText("nosana/does-not-exist.jsonl"), null);
});

test("createLocalFsStore: putText then getText round-trips the exact text", async () => {
  const store = createLocalFsStore({ rootDir: tmpRoot() });
  await store.putText("nosana/wallet-manifest.json", '{"solanaAddress":"ABC"}\n');
  assert.equal(await store.getText("nosana/wallet-manifest.json"), '{"solanaAddress":"ABC"}\n');
});

test("createLocalFsStore: putText creates nested directories as needed", async () => {
  const store = createLocalFsStore({ rootDir: tmpRoot() });
  await store.putText("a/b/c/d.jsonl", "x\n");
  assert.equal(await store.getText("a/b/c/d.jsonl"), "x\n");
});

test("createLocalFsStore: putText overwrites a previous value", async () => {
  const store = createLocalFsStore({ rootDir: tmpRoot() });
  await store.putText("k", "first\n");
  await store.putText("k", "second\n");
  assert.equal(await store.getText("k"), "second\n");
});

test("createLocalFsStore: putTextWithMerge invokes mergeFn with the current text (null on first write)", async () => {
  const store = createLocalFsStore({ rootDir: tmpRoot() });
  const seen = [];
  await store.putTextWithMerge("k", (current) => {
    seen.push(current);
    return "v1\n";
  });
  await store.putTextWithMerge("k", (current) => {
    seen.push(current);
    return current + "v2\n";
  });
  assert.deepEqual(seen, [null, "v1\n"]);
  assert.equal(await store.getText("k"), "v1\nv2\n");
});

test("createLocalFsStore: rejects a key that tries to escape rootDir", async () => {
  const store = createLocalFsStore({ rootDir: tmpRoot() });
  await assert.rejects(() => store.putText("../escape.json", "x"));
});

test("createLocalFsStore: close() is a safe no-op", async () => {
  const store = createLocalFsStore({ rootDir: tmpRoot() });
  await assert.doesNotReject(() => store.close());
});
