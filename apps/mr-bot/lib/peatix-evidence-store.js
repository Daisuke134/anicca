"use strict";

const { createHash, randomUUID } = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const zlib = require("node:zlib");

const TENANT = /^[a-z0-9][a-z0-9._-]{0,127}$/;
const EVENT_REF = /^peatix-event:\/\/event\/[1-9][0-9]*$/;
const RECEIPT_REF = /^provider-receipt:\/\/peatix\/([0-9a-f]{64})$/;
const OBJECT_REF = /^object:\/\/sha256\/([0-9a-f]{64})$/;
const PNG = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
const CHANNELS = Object.freeze({ 0: 1, 2: 3, 3: 1, 4: 2, 6: 4 });
const DEPTHS = Object.freeze({
  0: new Set([1, 2, 4, 8, 16]), 2: new Set([8, 16]), 3: new Set([1, 2, 4, 8]),
  4: new Set([8, 16]), 6: new Set([8, 16]),
});

function invalid(message = "Peatix evidence unavailable") { throw new Error(message); }
function tenant(value) {
  const text = String(value || "");
  if (!TENANT.test(text)) invalid();
  return text;
}
function instant(value) {
  const text = String(value || "");
  if (!Number.isFinite(Date.parse(text)) || new Date(Date.parse(text)).toISOString() !== text) invalid();
  return text;
}
function crc32(bytes) {
  let crc = 0xffffffff;
  for (const byte of bytes) { crc ^= byte; for (let bit = 0; bit < 8; bit += 1) crc = (crc >>> 1) ^ ((crc & 1) ? 0xedb88320 : 0); }
  return (crc ^ 0xffffffff) >>> 0;
}
function validPng(bytes) {
  if (!Buffer.isBuffer(bytes) || bytes.length < 5_000 || bytes.length > 20_000_000
    || !bytes.subarray(0, PNG.length).equals(PNG)) return false;
  let offset = PNG.length; let count = 0; let ended = false; let header = null; const idats = [];
  while (offset < bytes.length) {
    if (++count > 1_024 || bytes.length - offset < 12) return false;
    const length = bytes.readUInt32BE(offset);
    const type = bytes.subarray(offset + 4, offset + 8).toString("ascii");
    if (length > bytes.length - offset - 12 || !/^[A-Za-z]{4}$/.test(type)) return false;
    const next = offset + 12 + length;
    const body = bytes.subarray(offset + 4, offset + 8 + length);
    if (crc32(body) !== bytes.readUInt32BE(offset + 8 + length)) return false;
    if (count === 1) {
      if (type !== "IHDR" || length !== 13) return false;
      const data = bytes.subarray(offset + 8, offset + 21);
      header = {
        width: data.readUInt32BE(0), height: data.readUInt32BE(4), bitDepth: data[8], colorType: data[9],
        compression: data[10], filter: data[11], interlace: data[12],
      };
      if (!header.width || !header.height || !CHANNELS[header.colorType] || !DEPTHS[header.colorType]
        || !DEPTHS[header.colorType].has(header.bitDepth) || header.compression !== 0
        || header.filter !== 0 || header.interlace !== 0) return false;
    } else if (type === "IHDR") return false;
    if (type === "IDAT") { if (!length) return false; idats.push(bytes.subarray(offset + 8, offset + 8 + length)); }
    if (type === "IEND") {
      if (length !== 0 || !idats.length || next !== bytes.length) return false;
      ended = true; break;
    }
    offset = next;
  }
  if (!ended || !header || !idats.length) return false;
  const rowBytes = Math.ceil(header.width * CHANNELS[header.colorType] * header.bitDepth / 8);
  const expected = (rowBytes + 1) * header.height;
  if (!Number.isSafeInteger(expected) || expected > 20_000_000) return false;
  let decoded;
  try { decoded = zlib.inflateSync(Buffer.concat(idats), { maxOutputLength: 20_000_000 }); } catch { return false; }
  if (decoded.length !== expected) return false;
  for (let row = 0; row < header.height; row += 1) if (decoded[row * (rowBytes + 1)] > 4) return false;
  return true;
}
function atomicWrite(file, bytes) {
  fs.mkdirSync(path.dirname(file), { recursive: true, mode: 0o700 });
  const temporary = `${file}.tmp-${process.pid}-${randomUUID()}`;
  try {
    fs.writeFileSync(temporary, bytes, { mode: 0o600, flag: "wx" });
    try { fs.linkSync(temporary, file); }
    catch (error) {
      if (error.code !== "EEXIST") throw error;
      if (!fs.readFileSync(file).equals(bytes)) invalid("Peatix evidence collision");
    }
  } finally {
    try { fs.unlinkSync(temporary); } catch (error) { if (error.code !== "ENOENT") throw error; }
  }
}

function createPeatixEvidenceStore(options = {}) {
  const dataDir = path.resolve(String(options.dataDir || ""));
  if (!path.isAbsolute(dataDir) || dataDir === path.parse(dataDir).root) invalid();
  const root = (tenantId) => path.join(dataDir, "tenants", tenant(tenantId), "outbound", "peatix");
  return Object.freeze({
    async record(input = {}) {
      const tenantId = tenant(input.tenantId);
      const eventRef = String(input.eventRef || "");
      const observedAt = instant(input.observedAt);
      const screenshot = input.screenshot;
      if (!EVENT_REF.test(eventRef) || !validPng(screenshot)) invalid();
      const artifactHash = createHash("sha256").update(screenshot).digest("hex");
      const providerId = createHash("sha256")
        .update(`${tenantId}\n${eventRef}\n${observedAt}\n${artifactHash}`, "utf8").digest("hex");
      atomicWrite(path.join(dataDir, "objects", "sha256", artifactHash), screenshot);
      atomicWrite(path.join(root(tenantId), "provider-receipts", `${providerId}.json`), Buffer.from(`${JSON.stringify({
        kind: "provider_response", provider_id: providerId, observed_at: observedAt,
        event_ref: eventRef, artifact_sha256: artifactHash,
      })}\n`));
      atomicWrite(path.join(root(tenantId), "artifacts", `${artifactHash}.json`), Buffer.from(`${JSON.stringify({
        sha256: artifactHash,
      })}\n`));
      return Object.freeze({
        external_receipt_ref: `provider-receipt://peatix/${providerId}`,
        artifact_ref: `object://sha256/${artifactHash}`,
      });
    },
    async readExternalReceipt(tenantId, ref) {
      const requestTenant = tenant(tenantId);
      const match = RECEIPT_REF.exec(String(ref || ""));
      if (!match) invalid();
      let value;
      try { value = JSON.parse(fs.readFileSync(path.join(root(requestTenant), "provider-receipts", `${match[1]}.json`))); }
      catch { invalid(); }
      if (!value || typeof value !== "object" || Array.isArray(value)) invalid();
      const observedAt = instant(value.observed_at);
      const expectedProviderId = createHash("sha256")
        .update(`${requestTenant}\n${value.event_ref}\n${observedAt}\n${value.artifact_sha256}`, "utf8").digest("hex");
      if (
        Object.keys(value).sort().join(",") !== "artifact_sha256,event_ref,kind,observed_at,provider_id"
        || value.kind !== "provider_response" || value.provider_id !== match[1]
        || !EVENT_REF.test(value.event_ref) || !/^[0-9a-f]{64}$/.test(value.artifact_sha256)
        || expectedProviderId !== match[1]
      ) invalid();
      return Object.freeze({ kind: value.kind, provider_id: value.provider_id, observed_at: observedAt });
    },
    async readArtifact(tenantId, ref) {
      const requestTenant = tenant(tenantId);
      const match = OBJECT_REF.exec(String(ref || ""));
      if (!match) invalid();
      try {
        const marker = JSON.parse(fs.readFileSync(path.join(root(requestTenant), "artifacts", `${match[1]}.json`)));
        const bytes = fs.readFileSync(path.join(dataDir, "objects", "sha256", match[1]));
        if (!marker || typeof marker !== "object" || Array.isArray(marker)
          || Object.keys(marker).sort().join(",") !== "sha256" || marker.sha256 !== match[1]
          || createHash("sha256").update(bytes).digest("hex") !== match[1]) invalid();
        return bytes;
      } catch { invalid(); }
    },
  });
}

module.exports = { createPeatixEvidenceStore };
