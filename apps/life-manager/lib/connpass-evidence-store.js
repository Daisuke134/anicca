"use strict";

const { createHash, randomUUID } = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const TENANT = /^[a-z0-9][a-z0-9._-]{0,127}$/i;
const EVENT_REF = /^connpass-event:\/\/event\/[1-9][0-9]*$/;
const RECEIPT_REF = /^provider-receipt:\/\/connpass\/([0-9a-f]{64})$/;
const OBJECT_REF = /^object:\/\/sha256\/([0-9a-f]{64})$/;
const PNG = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
const RECEIPT_KEYS = "artifact_sha256,event_ref,kind,observed_at,provider_id";
const ARTIFACT_KEYS = "sha256";

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
function providerId(tenantId, eventRef, observedAt, artifactHash) {
  return createHash("sha256").update(`${tenantId}\n${eventRef}\n${observedAt}\n${artifactHash}`, "utf8").digest("hex");
}
function atomicWrite(file, bytes, collisionMessage = "Connpass evidence collision") {
  fs.mkdirSync(path.dirname(file), { recursive: true, mode: 0o700 });
  if (fs.existsSync(file)) {
    if (!fs.readFileSync(file).equals(bytes)) invalid(collisionMessage);
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

function createBrowserProviderEvidenceStore(options = {}) {
  const dataDir = path.resolve(String(options.dataDir || ""));
  if (!path.isAbsolute(dataDir) || dataDir === path.parse(dataDir).root) invalid();
  const provider = String(options.provider || "connpass");
  const eventPattern = options.eventRef || EVENT_REF;
  const receiptPattern = options.receiptRef || RECEIPT_REF;
  const collisionMessage = options.collisionMessage || "Connpass evidence collision";
  const root = (tenantId) => path.join(dataDir, "tenants", tenant(tenantId), "outbound", provider);
  return Object.freeze({
    async record(input = {}) {
      const tenantIdValue = tenant(input.tenantId);
      const eventRef = String(input.eventRef || "");
      const observedAt = instant(input.observedAt);
      const screenshot = input.screenshot;
      if (
        !eventPattern.test(eventRef) || !Buffer.isBuffer(screenshot) || screenshot.length < 5_000
        || !screenshot.subarray(0, PNG.length).equals(PNG)
      ) invalid();
      const artifactHash = createHash("sha256").update(screenshot).digest("hex");
      const receiptId = providerId(tenantIdValue, eventRef, observedAt, artifactHash);
      atomicWrite(path.join(dataDir, "objects", "sha256", artifactHash), screenshot, collisionMessage);
      atomicWrite(path.join(root(tenantIdValue), "provider-receipts", `${receiptId}.json`), Buffer.from(`${JSON.stringify({
        kind: "provider_response", provider_id: receiptId, observed_at: observedAt,
        event_ref: eventRef, artifact_sha256: artifactHash,
      })}\n`), collisionMessage);
      atomicWrite(path.join(root(tenantIdValue), "artifacts", `${artifactHash}.json`), Buffer.from(`${JSON.stringify({ sha256: artifactHash })}\n`), collisionMessage);
      return Object.freeze({
        external_receipt_ref: `provider-receipt://${provider}/${receiptId}`,
        artifact_ref: `object://sha256/${artifactHash}`,
      });
    },
    async readExternalReceipt(tenantId, ref) {
      const tenantIdValue = tenant(tenantId);
      const match = receiptPattern.exec(String(ref || ""));
      if (!match) invalid();
      let value;
      try { value = JSON.parse(fs.readFileSync(path.join(root(tenantIdValue), "provider-receipts", `${match[1]}.json`))); }
      catch { invalid(); }
      if (
        !value || typeof value !== "object" || Array.isArray(value)
        || Object.keys(value).sort().join(",") !== RECEIPT_KEYS
        || value.kind !== "provider_response" || typeof value.provider_id !== "string" || value.provider_id !== match[1]
        || typeof value.event_ref !== "string" || !eventPattern.test(value.event_ref)
        || typeof value.artifact_sha256 !== "string" || !/^[0-9a-f]{64}$/.test(value.artifact_sha256)
      ) invalid();
      if (typeof value.observed_at !== "string") invalid();
      const observedAt = instant(value.observed_at);
      if (value.provider_id !== providerId(tenantIdValue, value.event_ref, observedAt, value.artifact_sha256)) invalid();
      return Object.freeze({ kind: value.kind, provider_id: value.provider_id, observed_at: observedAt, event_ref: value.event_ref, artifact_sha256: value.artifact_sha256 });
    },
    async readArtifact(tenantId, ref) {
      const tenantIdValue = tenant(tenantId);
      const match = OBJECT_REF.exec(String(ref || ""));
      if (!match) invalid();
      try {
        const marker = JSON.parse(fs.readFileSync(path.join(root(tenantIdValue), "artifacts", `${match[1]}.json`)));
        const bytes = fs.readFileSync(path.join(dataDir, "objects", "sha256", match[1]));
        if (!marker || typeof marker !== "object" || Array.isArray(marker)
          || Object.keys(marker).sort().join(",") !== ARTIFACT_KEYS || marker.sha256 !== match[1]
          || createHash("sha256").update(bytes).digest("hex") !== match[1]) invalid();
        return bytes;
      } catch { invalid(); }
    },
  });
}

function createConnpassEvidenceStore(options = {}) {
  return createBrowserProviderEvidenceStore({
    ...options, provider: "connpass", eventRef: EVENT_REF, receiptRef: RECEIPT_REF,
    collisionMessage: "Connpass evidence collision",
  });
}

function createMeetupEvidenceStore(options = {}) {
  return createBrowserProviderEvidenceStore({
    ...options, provider: "meetup",
    eventRef: /^meetup-event:\/\/event\/[1-9][0-9]*$/,
    receiptRef: /^provider-receipt:\/\/meetup\/([0-9a-f]{64})$/,
    collisionMessage: "Meetup evidence collision",
  });
}

function createDoorkeeperEvidenceStore(options = {}) {
  return createBrowserProviderEvidenceStore({
    ...options, provider: "doorkeeper",
    eventRef: /^doorkeeper-event:\/\/event\/[1-9][0-9]*$/,
    receiptRef: /^provider-receipt:\/\/doorkeeper\/([0-9a-f]{64})$/,
    collisionMessage: "Doorkeeper evidence collision",
  });
}

function createEventbriteEvidenceStore(options = {}) {
  return createBrowserProviderEvidenceStore({
    ...options, provider: "eventbrite",
    eventRef: /^eventbrite-event:\/\/event\/[1-9][0-9]*$/,
    receiptRef: /^provider-receipt:\/\/eventbrite\/([0-9a-f]{64})$/,
    collisionMessage: "Eventbrite evidence collision",
  });
}

function createTechPlayEvidenceStore(options = {}) {
  return createBrowserProviderEvidenceStore({
    ...options, provider: "techplay",
    eventRef: /^techplay-event:\/\/event\/[1-9][0-9]*$/,
    receiptRef: /^provider-receipt:\/\/techplay\/([0-9a-f]{64})$/,
    collisionMessage: "Tech Play evidence collision",
  });
}

function createKokuchProEvidenceStore(options = {}) {
  return createBrowserProviderEvidenceStore({
    ...options, provider: "kokuchpro",
    eventRef: /^kokuchpro-event:\/\/event\/[0-9a-f]{32}(?:\/[1-9][0-9]*)?$/,
    receiptRef: /^provider-receipt:\/\/kokuchpro\/([0-9a-f]{64})$/,
    collisionMessage: "KokuchPro evidence collision",
  });
}

module.exports = { createConnpassEvidenceStore, createMeetupEvidenceStore, createDoorkeeperEvidenceStore, createEventbriteEvidenceStore, createTechPlayEvidenceStore, createKokuchProEvidenceStore };
