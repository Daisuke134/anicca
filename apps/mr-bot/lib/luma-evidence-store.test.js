"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const {
  createLumaEvidenceStore,
} = require("./luma-evidence-store.js");

const PNG_SIGNATURE = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);

function png() {
  const bytes = Buffer.alloc(5000, 0x61);
  PNG_SIGNATURE.copy(bytes);
  return bytes;
}

test("records tenant-scoped provider receipt and immutable PNG object", async () => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "luma-evidence-"));
  const store = createLumaEvidenceStore({ dataDir });
  const first = await store.record({
    tenantId: "dais-local",
    eventRef: "luma-event://event/tokyo-agent-night",
    observedAt: "2026-08-01T10:00:00.000Z",
    screenshot: png(),
  });
  const second = await store.record({
    tenantId: "dais-local",
    eventRef: "luma-event://event/tokyo-agent-night",
    observedAt: "2026-08-01T10:00:00.000Z",
    screenshot: png(),
  });

  assert.deepEqual(second, first);
  assert.match(first.external_receipt_ref, /^provider-receipt:\/\/luma\/[0-9a-f]{64}$/);
  assert.match(first.artifact_ref, /^object:\/\/sha256\/[0-9a-f]{64}$/);
  assert.deepEqual(
    await store.readExternalReceipt("dais-local", first.external_receipt_ref),
    {
      kind: "provider_response",
      provider_id: first.external_receipt_ref.split("/").at(-1),
      observed_at: "2026-08-01T10:00:00.000Z",
    },
  );
  assert.deepEqual(await store.readArtifact("dais-local", first.artifact_ref), png());
});

test("refuses cross-tenant receipt reads, invalid PNG, and path-like tenant values", async () => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "luma-evidence-"));
  const store = createLumaEvidenceStore({ dataDir });
  const recorded = await store.record({
    tenantId: "tenant-a",
    eventRef: "luma-event://event/event-a",
    observedAt: "2026-08-01T10:00:00.000Z",
    screenshot: png(),
  });

  await assert.rejects(
    store.readExternalReceipt("tenant-b", recorded.external_receipt_ref),
    /unavailable/i,
  );
  await assert.rejects(
    store.record({
      tenantId: "../tenant-a",
      eventRef: "luma-event://event/event-a",
      observedAt: "2026-08-01T10:00:00.000Z",
      screenshot: png(),
    }),
    /tenant/i,
  );
  await assert.rejects(
    store.record({
      tenantId: "tenant-a",
      eventRef: "luma-event://event/event-a",
      observedAt: "2026-08-01T10:00:00.000Z",
      screenshot: Buffer.alloc(5000),
    }),
    /PNG/i,
  );
});
