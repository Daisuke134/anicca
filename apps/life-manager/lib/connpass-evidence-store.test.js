"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const {
  createConnpassEvidenceStore,
  createMeetupEvidenceStore,
  createDoorkeeperEvidenceStore,
} = require("./connpass-evidence-store.js");

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

test("Meetup wrapper stores exact event receipt and private immutable artifacts", async (t) => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "meetup-evidence-"));
  t.after(() => fs.rmSync(directory, { recursive: true, force: true }));
  const png = Buffer.alloc(5_000, 0x63);
  Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]).copy(png);
  const store = createMeetupEvidenceStore({ dataDir: directory });
  const refs = await store.record({
    tenantId: "meetup-test", eventRef: "meetup-event://event/101",
    observedAt: "2026-08-11T01:02:03.000Z", screenshot: png,
  });
  assert.match(refs.external_receipt_ref, /^provider-receipt:\/\/meetup\/[0-9a-f]{64}$/);
  const receipt = await store.readExternalReceipt("meetup-test", refs.external_receipt_ref);
  assert.deepEqual(receipt, {
    kind: "provider_response", provider_id: refs.external_receipt_ref.split("/").at(-1),
    observed_at: "2026-08-11T01:02:03.000Z", event_ref: "meetup-event://event/101",
    artifact_sha256: refs.artifact_ref.split("/").at(-1),
  });
  const root = path.join(directory, "tenants", "meetup-test", "outbound", "meetup");
  const receiptFile = path.join(root, "provider-receipts", `${refs.external_receipt_ref.split("/").at(-1)}.json`);
  const artifactSha = refs.artifact_ref.split("/").at(-1);
  const artifactFile = path.join(root, "artifacts", `${artifactSha}.json`);
  const objectFile = path.join(directory, "objects", "sha256", artifactSha);
  for (const file of [receiptFile, artifactFile, objectFile]) assert.equal(fs.statSync(file).mode & 0o777, 0o600, file);
  assert.deepEqual(await store.readArtifact("meetup-test", refs.artifact_ref), png);
  assert.equal(JSON.stringify(refs).includes("meetup-test"), false);
});

test("Meetup receipt tuple and artifact tampering fail closed", async (t) => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "meetup-evidence-hardening-"));
  t.after(() => fs.rmSync(directory, { recursive: true, force: true }));
  const png = Buffer.alloc(5_000, 0x64); Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]).copy(png);
  const store = createMeetupEvidenceStore({ dataDir: directory });
  const refs = await store.record({ tenantId: "meetup-test", eventRef: "meetup-event://event/101", observedAt: "2026-08-11T01:02:03.000Z", screenshot: png });
  const artifactSha = refs.artifact_ref.split("/").at(-1); const providerId = refs.external_receipt_ref.split("/").at(-1);
  const root = path.join(directory, "tenants", "meetup-test", "outbound", "meetup");
  const receiptFile = path.join(root, "provider-receipts", `${providerId}.json`);
  const markerFile = path.join(root, "artifacts", `${artifactSha}.json`);
  const objectFile = path.join(directory, "objects", "sha256", artifactSha);
  const receipt = JSON.parse(fs.readFileSync(receiptFile, "utf8"));
  fs.writeFileSync(receiptFile, `${JSON.stringify({ ...receipt, event_ref: "meetup-event://event/102" })}\n`);
  await assert.rejects(store.readExternalReceipt("meetup-test", refs.external_receipt_ref));
  fs.writeFileSync(receiptFile, `${JSON.stringify(receipt)}\n`);
  fs.writeFileSync(markerFile, `${JSON.stringify({ sha256: "a".repeat(64) })}\n`);
  await assert.rejects(store.readArtifact("meetup-test", refs.artifact_ref));
  fs.writeFileSync(markerFile, `${JSON.stringify({ sha256: artifactSha })}\n`);
  fs.writeFileSync(objectFile, Buffer.concat([png, Buffer.from("tamper")]));
  await assert.rejects(store.readArtifact("meetup-test", refs.artifact_ref));
});

test("Doorkeeper wrapper stores exact event receipt and private immutable artifacts", async (t) => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "doorkeeper-evidence-"));
  t.after(() => fs.rmSync(directory, { recursive: true, force: true }));
  const png = Buffer.alloc(5_000, 0x65);
  Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]).copy(png);
  const store = createDoorkeeperEvidenceStore({ dataDir: directory });
  const refs = await store.record({
    tenantId: "doorkeeper-test", eventRef: "doorkeeper-event://event/101",
    observedAt: "2026-08-12T01:02:03.000Z", screenshot: png,
  });
  assert.match(refs.external_receipt_ref, /^provider-receipt:\/\/doorkeeper\/[0-9a-f]{64}$/);
  const receipt = await store.readExternalReceipt("doorkeeper-test", refs.external_receipt_ref);
  assert.deepEqual(receipt, {
    kind: "provider_response", provider_id: refs.external_receipt_ref.split("/").at(-1),
    observed_at: "2026-08-12T01:02:03.000Z", event_ref: "doorkeeper-event://event/101",
    artifact_sha256: refs.artifact_ref.split("/").at(-1),
  });
  const root = path.join(directory, "tenants", "doorkeeper-test", "outbound", "doorkeeper");
  const artifactSha = refs.artifact_ref.split("/").at(-1);
  const files = [
    path.join(root, "provider-receipts", `${refs.external_receipt_ref.split("/").at(-1)}.json`),
    path.join(root, "artifacts", `${artifactSha}.json`),
    path.join(directory, "objects", "sha256", artifactSha),
  ];
  for (const file of files) assert.equal(fs.statSync(file).mode & 0o777, 0o600, file);
  assert.deepEqual(await store.readArtifact("doorkeeper-test", refs.artifact_ref), png);
  assert.equal(JSON.stringify(refs).includes("doorkeeper-test"), false);
});

test("Doorkeeper wrapper rejects wrong event identity and receipt tuple tampering", async (t) => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "doorkeeper-evidence-hardening-"));
  t.after(() => fs.rmSync(directory, { recursive: true, force: true }));
  const png = Buffer.alloc(5_000, 0x66);
  Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]).copy(png);
  const store = createDoorkeeperEvidenceStore({ dataDir: directory });
  await assert.rejects(store.record({
    tenantId: "doorkeeper-test", eventRef: "doorkeeper-event://event/0",
    observedAt: "2026-08-12T01:02:03.000Z", screenshot: png,
  }));
  const refs = await store.record({
    tenantId: "doorkeeper-test", eventRef: "doorkeeper-event://event/101",
    observedAt: "2026-08-12T01:02:03.000Z", screenshot: png,
  });
  const providerId = refs.external_receipt_ref.split("/").at(-1);
  const file = path.join(directory, "tenants", "doorkeeper-test", "outbound", "doorkeeper", "provider-receipts", `${providerId}.json`);
  const receipt = JSON.parse(fs.readFileSync(file, "utf8"));
  fs.writeFileSync(file, `${JSON.stringify({ ...receipt, event_ref: "doorkeeper-event://event/102" })}\n`);
  await assert.rejects(store.readExternalReceipt("doorkeeper-test", refs.external_receipt_ref));
});
