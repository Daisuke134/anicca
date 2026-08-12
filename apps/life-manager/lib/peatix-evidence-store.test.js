"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");
const zlib = require("node:zlib");

const { createPeatixEvidenceStore } = require("./peatix-evidence-store.js");

const PNG = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
function crc32(bytes) {
  let crc = 0xffffffff;
  for (const byte of bytes) { crc ^= byte; for (let bit = 0; bit < 8; bit += 1) crc = (crc >>> 1) ^ ((crc & 1) ? 0xedb88320 : 0); }
  return (crc ^ 0xffffffff) >>> 0;
}
function chunk(type, data) {
  const body = Buffer.concat([Buffer.from(type), data]); const result = Buffer.alloc(body.length + 8);
  result.writeUInt32BE(data.length); body.copy(result, 4); result.writeUInt32BE(crc32(body), body.length + 4); return result;
}
function readChunk(bytes, wanted) {
  for (let offset = PNG.length; offset < bytes.length;) {
    const length = bytes.readUInt32BE(offset); const type = bytes.subarray(offset + 4, offset + 8).toString("ascii");
    if (type === wanted) return { offset, length, data: bytes.subarray(offset + 8, offset + 8 + length), crcOffset: offset + 8 + length };
    offset += 12 + length;
  }
  throw new Error(`missing ${wanted}`);
}
function replaceChunk(bytes, wanted, data) {
  const found = readChunk(bytes, wanted);
  return Buffer.concat([bytes.subarray(0, found.offset), chunk(wanted, data), bytes.subarray(found.offset + 12 + found.length)]);
}
function ihdr(width, height) {
  const header = Buffer.alloc(13); header.writeUInt32BE(width); header.writeUInt32BE(height, 4); header[8] = 8; header[9] = 6; return header;
}
function png() {
  const raw = Buffer.alloc((128 * 4 + 1) * 128);
  for (let i = 0; i < raw.length; i += 1) raw[i] = i % 513 === 0 ? 0 : (i * 73 + 19) & 0xff;
  return Buffer.concat([PNG, chunk("IHDR", ihdr(128, 128)), chunk("IDAT", zlib.deflateSync(raw, { level: 0 })), chunk("IEND", Buffer.alloc(0))]);
}

test("Peatix evidence is deterministic, tenant-scoped, immutable, and identity-free", async () => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "peatix-evidence-"));
  try {
    const store = createPeatixEvidenceStore({ dataDir });
    const input = {
      tenantId: "tenant-a", eventRef: "peatix-event://event/5075819",
      observedAt: "2026-08-10T01:02:03.000Z", screenshot: png(),
      name: "Private Name", email: "private@example.test", ticket_id: "6536845",
    };
    const first = await store.record(input);
    assert.deepEqual(await store.record(input), first);
    assert.match(first.external_receipt_ref, /^provider-receipt:\/\/peatix\/[0-9a-f]{64}$/);
    assert.match(first.artifact_ref, /^object:\/\/sha256\/[0-9a-f]{64}$/);
    assert.deepEqual(await store.readExternalReceipt("tenant-a", first.external_receipt_ref), {
      kind: "provider_response", provider_id: first.external_receipt_ref.split("/").at(-1),
      observed_at: input.observedAt,
    });
    assert.deepEqual(await store.readArtifact("tenant-a", first.artifact_ref), input.screenshot);
    await assert.rejects(store.readExternalReceipt("tenant-b", first.external_receipt_ref), /unavailable/i);
    await assert.rejects(store.readExternalReceipt("TENANT-A", first.external_receipt_ref), /unavailable/i);
    await assert.rejects(store.readExternalReceipt(" tenant-a ", first.external_receipt_ref), /unavailable/i);
    await assert.rejects(store.readArtifact("tenant-b", first.artifact_ref), /unavailable/i);
    await assert.rejects(store.record({ ...input, tenantId: "TENANT-A" }), /unavailable/i);
    const receipt = path.join(dataDir, "tenants", "tenant-a", "outbound", "peatix", "provider-receipts", `${first.external_receipt_ref.split("/").at(-1)}.json`);
    assert.doesNotMatch(fs.readFileSync(receipt, "utf8"), /Private Name|private@example\.test|6536845/);
    assert.equal(fs.statSync(receipt).mode & 0o777, 0o600);
    const hash = first.artifact_ref.split("/").at(-1);
    const marker = path.join(dataDir, "tenants", "tenant-a", "outbound", "peatix", "artifacts", `${hash}.json`);
    assert.deepEqual(Object.keys(JSON.parse(fs.readFileSync(marker, "utf8"))), ["sha256"]);
    const receiptBytes = fs.readFileSync(receipt, "utf8");
    for (const [field, value] of [["event_ref", "peatix-event://event/999"], ["observed_at", "2026-08-10T01:02:04.000Z"], ["artifact_sha256", "0".repeat(64)]]) {
      const receiptValue = JSON.parse(receiptBytes); receiptValue[field] = value;
      fs.writeFileSync(receipt, `${JSON.stringify(receiptValue)}\n`);
      await assert.rejects(store.readExternalReceipt("tenant-a", first.external_receipt_ref), /unavailable/i);
    }
  } finally { fs.rmSync(dataDir, { recursive: true, force: true }); }
});

test("Peatix evidence rejects invalid refs and PNGs and detects immutable collisions", async () => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "peatix-evidence-"));
  try {
    const store = createPeatixEvidenceStore({ dataDir });
    const input = { tenantId: "tenant-a", eventRef: "peatix-event://event/1", observedAt: "2026-08-10T01:02:03.000Z", screenshot: png() };
    const flippedCrc = png(); flippedCrc[readChunk(flippedCrc, "IHDR").crcOffset] ^= 1;
    const corruptIdat = png(); const idat = readChunk(corruptIdat, "IDAT");
    const invalidIdat = replaceChunk(corruptIdat, "IDAT", Buffer.alloc(idat.length, 0xff));
    const wrongLength = replaceChunk(png(), "IHDR", ihdr(129, 128));
    const raw = zlib.inflateSync(readChunk(png(), "IDAT").data); raw[0] = 5;
    const wrongFilter = replaceChunk(png(), "IDAT", zlib.deflateSync(raw, { level: 0 }));
    for (const screenshot of [flippedCrc, invalidIdat, wrongLength, wrongFilter]) {
      await assert.rejects(store.record({ ...input, screenshot }), /unavailable/i);
    }
    const refs = await store.record(input);
    const hash = refs.artifact_ref.split("/").at(-1);
    fs.writeFileSync(path.join(dataDir, "objects", "sha256", hash), Buffer.from("tampered"));
    await assert.rejects(store.record(input), /collision/i);
    const source = fs.readFileSync(path.join(__dirname, "peatix-evidence-store.js"), "utf8");
    assert.match(source, /linkSync\(temporary, file\)/); assert.doesNotMatch(source, /renameSync\(temporary, file\)/);
    await assert.rejects(store.record({ ...input, eventRef: "peatix-event://event/0" }), /unavailable/i);
    await assert.rejects(store.record({ ...input, screenshot: Buffer.concat([PNG, Buffer.alloc(5_000)]) }), /unavailable/i);
    await assert.rejects(store.record({ ...input, screenshot: png().subarray(0, -12) }), /unavailable/i);
    const zeroWidth = png(); zeroWidth.writeUInt32BE(0, 16);
    await assert.rejects(store.record({ ...input, screenshot: zeroWidth }), /unavailable/i);
  } finally { fs.rmSync(dataDir, { recursive: true, force: true }); }
});
