"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const { createConnpassEvidenceStore } = require("./connpass-evidence-store.js");

test("atomically stores and reads one Connpass PNG receipt without identity data", async (t) => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "connpass-evidence-"));
  t.after(() => fs.rmSync(directory, { recursive: true, force: true }));
  const png = Buffer.alloc(5_000, 0x61);
  Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]).copy(png);
  const store = createConnpassEvidenceStore({ dataDir: directory });
  const refs = await store.record({
    tenantId: "dais-local", eventRef: "connpass-event://event/101",
    observedAt: "2026-08-06T01:02:03.000Z", screenshot: png,
  });
  assert.match(refs.external_receipt_ref, /^provider-receipt:\/\/connpass\/[0-9a-f]{64}$/);
  assert.equal((await store.readExternalReceipt("dais-local", refs.external_receipt_ref)).kind, "provider_response");
  assert.deepEqual(await store.readArtifact("dais-local", refs.artifact_ref), png);
  assert.equal(JSON.stringify(refs).includes("dais-local"), false);
});
