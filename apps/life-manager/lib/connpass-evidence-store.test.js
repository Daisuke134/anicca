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
  createEventbriteEvidenceStore,
  createTechPlayEvidenceStore,
  createKokuchProEvidenceStore,
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

test("Eventbrite wrapper stores exact event receipt and private immutable artifacts", async (t) => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "eventbrite-evidence-"));
  t.after(() => fs.rmSync(directory, { recursive: true, force: true }));
  const png = Buffer.alloc(5_000, 0x67);
  Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]).copy(png);
  const store = createEventbriteEvidenceStore({ dataDir: directory });
  const refs = await store.record({
    tenantId: "eventbrite-test", eventRef: "eventbrite-event://event/1997468673573",
    observedAt: "2026-08-12T01:02:03.000Z", screenshot: png,
  });
  assert.match(refs.external_receipt_ref, /^provider-receipt:\/\/eventbrite\/[0-9a-f]{64}$/);
  const receipt = await store.readExternalReceipt("eventbrite-test", refs.external_receipt_ref);
  assert.deepEqual(receipt, {
    kind: "provider_response", provider_id: refs.external_receipt_ref.split("/").at(-1),
    observed_at: "2026-08-12T01:02:03.000Z", event_ref: "eventbrite-event://event/1997468673573",
    artifact_sha256: refs.artifact_ref.split("/").at(-1),
  });
  const root = path.join(directory, "tenants", "eventbrite-test", "outbound", "eventbrite");
  const artifactSha = refs.artifact_ref.split("/").at(-1);
  const files = [
    path.join(root, "provider-receipts", `${refs.external_receipt_ref.split("/").at(-1)}.json`),
    path.join(root, "artifacts", `${artifactSha}.json`),
    path.join(directory, "objects", "sha256", artifactSha),
  ];
  for (const file of files) assert.equal(fs.statSync(file).mode & 0o777, 0o600, file);
  assert.deepEqual(await store.readArtifact("eventbrite-test", refs.artifact_ref), png);
  assert.equal(JSON.stringify(refs).includes("eventbrite-test"), false);
});

test("Eventbrite wrapper rejects wrong event identity and receipt tuple tampering", async (t) => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "eventbrite-evidence-hardening-"));
  t.after(() => fs.rmSync(directory, { recursive: true, force: true }));
  const png = Buffer.alloc(5_000, 0x68);
  Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]).copy(png);
  const store = createEventbriteEvidenceStore({ dataDir: directory });
  await assert.rejects(store.record({
    tenantId: "eventbrite-test", eventRef: "eventbrite-event://event/0",
    observedAt: "2026-08-12T01:02:03.000Z", screenshot: png,
  }));
  const refs = await store.record({
    tenantId: "eventbrite-test", eventRef: "eventbrite-event://event/1997468673573",
    observedAt: "2026-08-12T01:02:03.000Z", screenshot: png,
  });
  const providerId = refs.external_receipt_ref.split("/").at(-1);
  const file = path.join(directory, "tenants", "eventbrite-test", "outbound", "eventbrite", "provider-receipts", `${providerId}.json`);
  const receipt = JSON.parse(fs.readFileSync(file, "utf8"));
  fs.writeFileSync(file, `${JSON.stringify({ ...receipt, event_ref: "eventbrite-event://event/2" })}\n`);
  await assert.rejects(store.readExternalReceipt("eventbrite-test", refs.external_receipt_ref));
});

test("TECH PLAY wrapper stores exact event receipt and private immutable artifacts", async (t) => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "techplay-evidence-"));
  t.after(() => fs.rmSync(directory, { recursive: true, force: true }));
  const png = Buffer.alloc(5_000, 0x69);
  Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]).copy(png);
  const store = createTechPlayEvidenceStore({ dataDir: directory });
  const refs = await store.record({
    tenantId: "techplay-test", eventRef: "techplay-event://event/999190",
    observedAt: "2026-08-12T01:02:03.000Z", screenshot: png,
  });
  assert.match(refs.external_receipt_ref, /^provider-receipt:\/\/techplay\/[0-9a-f]{64}$/);
  const receipt = await store.readExternalReceipt("techplay-test", refs.external_receipt_ref);
  assert.deepEqual(receipt, {
    kind: "provider_response", provider_id: refs.external_receipt_ref.split("/").at(-1),
    observed_at: "2026-08-12T01:02:03.000Z", event_ref: "techplay-event://event/999190",
    artifact_sha256: refs.artifact_ref.split("/").at(-1),
  });
  const root = path.join(directory, "tenants", "techplay-test", "outbound", "techplay");
  const artifactSha = refs.artifact_ref.split("/").at(-1);
  const files = [path.join(root, "provider-receipts", `${refs.external_receipt_ref.split("/").at(-1)}.json`), path.join(root, "artifacts", `${artifactSha}.json`), path.join(directory, "objects", "sha256", artifactSha)];
  for (const file of files) assert.equal(fs.statSync(file).mode & 0o777, 0o600, file);
  assert.deepEqual(await store.readArtifact("techplay-test", refs.artifact_ref), png);
  assert.equal(JSON.stringify(refs).includes("techplay-test"), false);
});

test("TECH PLAY wrapper rejects invalid refs, collisions, and receipt or artifact tampering", async (t) => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "techplay-evidence-hardening-"));
  t.after(() => fs.rmSync(directory, { recursive: true, force: true }));
  const png = Buffer.alloc(5_000, 0x6a); Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]).copy(png);
  const store = createTechPlayEvidenceStore({ dataDir: directory });
  const input = { tenantId: "techplay-test", eventRef: "techplay-event://event/999190", observedAt: "2026-08-12T01:02:03.000Z", screenshot: png };
  await assert.rejects(store.record({ ...input, eventRef: "techplay-event://event/0" }));
  const refs = await store.record(input);
  const providerId = refs.external_receipt_ref.split("/").at(-1); const artifactSha = refs.artifact_ref.split("/").at(-1);
  await assert.rejects(store.readExternalReceipt("techplay-test", "provider-receipt://techplay/not-a-hash"));
  await assert.rejects(store.readExternalReceipt("techplay-test", `provider-receipt://eventbrite/${providerId}`));
  const root = path.join(directory, "tenants", "techplay-test", "outbound", "techplay");
  const receiptFile = path.join(root, "provider-receipts", `${providerId}.json`); const markerFile = path.join(root, "artifacts", `${artifactSha}.json`); const objectFile = path.join(directory, "objects", "sha256", artifactSha);
  const receipt = JSON.parse(fs.readFileSync(receiptFile, "utf8")); const marker = JSON.parse(fs.readFileSync(markerFile, "utf8"));
  fs.writeFileSync(receiptFile, `${JSON.stringify({ ...receipt, event_ref: "techplay-event://event/999191" })}\n`);
  await assert.rejects(store.readExternalReceipt("techplay-test", refs.external_receipt_ref)); fs.writeFileSync(receiptFile, `${JSON.stringify(receipt)}\n`);
  fs.writeFileSync(markerFile, `${JSON.stringify({ sha256: "a".repeat(64) })}\n`);
  await assert.rejects(store.readArtifact("techplay-test", refs.artifact_ref)); fs.writeFileSync(markerFile, `${JSON.stringify(marker)}\n`);
  fs.writeFileSync(objectFile, Buffer.concat([png, Buffer.from("tamper")]));
  await assert.rejects(store.readArtifact("techplay-test", refs.artifact_ref));
  await assert.rejects(store.record(input), /Tech Play evidence collision/);
});

test("KokuchPro wrapper stores occurrence evidence and rejects wrong event identity", async (t) => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "kokuchpro-evidence-"));
  t.after(() => fs.rmSync(directory, { recursive: true, force: true }));
  const png = Buffer.alloc(5_000, 0x6b);
  Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]).copy(png);
  const store = createKokuchProEvidenceStore({ dataDir: directory });
  const input = {
    tenantId: "kokuchpro-test",
    eventRef: "kokuchpro-event://event/89a92aac6c9a221ec337481b51c1bbef/3847918",
    observedAt: "2026-08-13T01:02:03.000Z",
    screenshot: png,
  };
  const refs = await store.record(input);
  assert.match(refs.external_receipt_ref, /^provider-receipt:\/\/kokuchpro\/[0-9a-f]{64}$/);
  assert.deepEqual(await store.readExternalReceipt("kokuchpro-test", refs.external_receipt_ref), {
    kind: "provider_response",
    provider_id: refs.external_receipt_ref.split("/").at(-1),
    observed_at: input.observedAt,
    event_ref: input.eventRef,
    artifact_sha256: refs.artifact_ref.split("/").at(-1),
  });
  assert.deepEqual(await store.readArtifact("kokuchpro-test", refs.artifact_ref), png);
  await assert.rejects(store.record({ ...input, eventRef: "kokuchpro-event://event/89a92aac6c9a221ec337481b51c1bbeF/3847918" }));
  await assert.rejects(store.record({ ...input, eventRef: "kokuchpro-event://event/89a92aac6c9a221ec337481b51c1bbef/0" }));
  assert.equal(JSON.stringify(refs).includes("kokuchpro-test"), false);
});
