"use strict";

const { createHash, randomUUID } = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const TENANT = /^[a-z0-9][a-z0-9._-]{0,127}$/i;
const EVENT_REF = /^connpass-event:\/\/event\/[1-9][0-9]*$/;
const RECEIPT_REF = /^provider-receipt:\/\/connpass\/([0-9a-f]{64})$/;
const OBJECT_REF = /^object:\/\/sha256\/([0-9a-f]{64})$/;
const PNG = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);

function invalid(message = "Connpass evidence unavailable") { throw new Error(message); }
function tenant(value) {
  const text = String(value || "").trim();
  if (!TENANT.test(text)) invalid();
  return text;
}
function instant(value) {
  const text = String(value || "");
  if (!Number.isFinite(Date.parse(text)) || new Date(Date.parse(text)).toISOString() !== text) invalid();
  return text;
}
function atomicWrite(file, bytes) {
  fs.mkdirSync(path.dirname(file), { recursive: true, mode: 0o700 });
  if (fs.existsSync(file)) {
    if (!fs.readFileSync(file).equals(bytes)) invalid("Connpass evidence collision");
    return;
  }
  const temporary = `${file}.tmp-${process.pid}-${randomUUID()}`;
  try {
    fs.writeFileSync(temporary, bytes, { mode: 0o600, flag: "wx" });
    fs.renameSync(temporary, file);
  } finally {
    try { fs.unlinkSync(temporary); } catch (error) { if (error.code !== "ENOENT") throw error; }
  }
}

function createConnpassEvidenceStore(options = {}) {
  const dataDir = path.resolve(String(options.dataDir || ""));
  if (!path.isAbsolute(dataDir) || dataDir === path.parse(dataDir).root) invalid();
  const root = (tenantId) => path.join(dataDir, "tenants", tenant(tenantId), "outbound", "connpass");
  return Object.freeze({
    async record(input = {}) {
      const tenantId = tenant(input.tenantId);
      const eventRef = String(input.eventRef || "");
      const observedAt = instant(input.observedAt);
      const screenshot = input.screenshot;
      if (
        !EVENT_REF.test(eventRef) || !Buffer.isBuffer(screenshot) || screenshot.length < 5_000
        || !screenshot.subarray(0, PNG.length).equals(PNG)
      ) invalid();
      const artifactHash = createHash("sha256").update(screenshot).digest("hex");
      const providerId = createHash("sha256")
        .update(`${tenantId}\n${eventRef}\n${observedAt}\n${artifactHash}`, "utf8").digest("hex");
      atomicWrite(path.join(dataDir, "objects", "sha256", artifactHash), screenshot);
      atomicWrite(path.join(root(tenantId), "provider-receipts", `${providerId}.json`), Buffer.from(`${JSON.stringify({
        kind: "provider_response", provider_id: providerId, observed_at: observedAt,
        event_ref: eventRef, artifact_sha256: artifactHash,
      })}\n`));
      atomicWrite(path.join(root(tenantId), "artifacts", `${artifactHash}.json`), Buffer.from(`${JSON.stringify({
        sha256: artifactHash, event_ref: eventRef,
      })}\n`));
      return Object.freeze({
        external_receipt_ref: `provider-receipt://connpass/${providerId}`,
        artifact_ref: `object://sha256/${artifactHash}`,
      });
    },
    async readExternalReceipt(tenantId, ref) {
      const match = RECEIPT_REF.exec(String(ref || ""));
      if (!match) invalid();
      let value;
      try { value = JSON.parse(fs.readFileSync(path.join(root(tenantId), "provider-receipts", `${match[1]}.json`))); }
      catch { invalid(); }
      if (
        value.kind !== "provider_response" || value.provider_id !== match[1]
        || !EVENT_REF.test(value.event_ref) || !/^[0-9a-f]{64}$/.test(value.artifact_sha256)
      ) invalid();
      return Object.freeze({ kind: value.kind, provider_id: value.provider_id, observed_at: instant(value.observed_at) });
    },
    async readArtifact(tenantId, ref) {
      const match = OBJECT_REF.exec(String(ref || ""));
      if (!match) invalid();
      try {
        const marker = JSON.parse(fs.readFileSync(path.join(root(tenantId), "artifacts", `${match[1]}.json`)));
        const bytes = fs.readFileSync(path.join(dataDir, "objects", "sha256", match[1]));
        if (marker.sha256 !== match[1] || !EVENT_REF.test(marker.event_ref)
          || createHash("sha256").update(bytes).digest("hex") !== match[1]) invalid();
        return bytes;
      } catch { invalid(); }
    },
  });
}

module.exports = { createConnpassEvidenceStore };
