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
  const receipt = await store.readExternalReceipt("dais-local", refs.external_receipt_ref);
  assert.deepEqual(receipt, {
    kind: "provider_response", provider_id: refs.external_receipt_ref.split("/").at(-1),
    observed_at: "2026-08-06T01:02:03.000Z", event_ref: "connpass-event://event/101",
    artifact_sha256: refs.artifact_ref.split("/").at(-1),
  });
  const markerFile = path.join(directory, "tenants", "dais-local", "outbound", "connpass", "artifacts", `${refs.artifact_ref.split("/").at(-1)}.json`);
  assert.deepEqual(Object.keys(JSON.parse(fs.readFileSync(markerFile, "utf8"))), ["sha256"]);
  assert.deepEqual(await store.readArtifact("dais-local", refs.artifact_ref), png);
  assert.equal(JSON.stringify(refs).includes("dais-local"), false);
});

test("receipt tuple and artifact marker mutations fail closed before reuse", async (t) => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "connpass-evidence-hardening-"));
  t.after(() => fs.rmSync(directory, { recursive: true, force: true }));
  const png = Buffer.alloc(5_000, 0x62); Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]).copy(png);
  const store = createConnpassEvidenceStore({ dataDir: directory });
  const refs = await store.record({ tenantId: "dais-local", eventRef: "connpass-event://event/101", observedAt: "2026-08-06T01:02:03.000Z", screenshot: png });
  const artifactSha = refs.artifact_ref.split("/").at(-1); const providerId = refs.external_receipt_ref.split("/").at(-1);
  const receiptFile = path.join(directory, "tenants", "dais-local", "outbound", "connpass", "provider-receipts", `${providerId}.json`);
  const markerFile = path.join(directory, "tenants", "dais-local", "outbound", "connpass", "artifacts", `${artifactSha}.json`);
  const objectFile = path.join(directory, "objects", "sha256", artifactSha);
  const receipt = JSON.parse(fs.readFileSync(receiptFile, "utf8")); const marker = JSON.parse(fs.readFileSync(markerFile, "utf8"));
  for (const value of [
    { ...receipt, event_ref: "connpass-event://event/102" },
    { ...receipt, artifact_sha256: "a".repeat(64) },
    { ...receipt, observed_at: "2026-08-06T01:02:03Z" },
    { ...receipt, extra: true },
    Object.fromEntries(Object.entries(receipt).filter(([key]) => key !== "event_ref")),
  ]) {
    fs.writeFileSync(receiptFile, `${JSON.stringify(value)}\n`);
    await assert.rejects(store.readExternalReceipt("dais-local", refs.external_receipt_ref));
  }
  fs.writeFileSync(receiptFile, `${JSON.stringify(receipt)}\n`);
  for (const value of [
    { ...marker, event_ref: receipt.event_ref }, { sha256: "a".repeat(64) }, {},
  ]) {
    fs.writeFileSync(markerFile, `${JSON.stringify(value)}\n`);
    await assert.rejects(store.readArtifact("dais-local", refs.artifact_ref));
  }
  fs.writeFileSync(markerFile, `${JSON.stringify(marker)}\n`); fs.writeFileSync(objectFile, Buffer.concat([png, Buffer.from("tamper")]));
  await assert.rejects(store.readArtifact("dais-local", refs.artifact_ref));
});
