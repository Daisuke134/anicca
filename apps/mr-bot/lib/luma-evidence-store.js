"use strict";

const { createHash, randomUUID } = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const TENANT = /^[a-z0-9][a-z0-9._-]{0,127}$/i;
const EVENT_REF = /^luma-event:\/\/event\/[A-Za-z0-9_-]+$/;
const RECEIPT_REF = /^provider-receipt:\/\/luma\/([0-9a-f]{64})$/;
const OBJECT_REF = /^object:\/\/sha256\/([0-9a-f]{64})$/;
const PNG_SIGNATURE = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);

function tenantId(value) {
  const text = String(value == null ? "" : value).trim();
  if (!TENANT.test(text)) throw new Error("Luma evidence tenant invalid");
  return text;
}

function exactInstant(value) {
  const text = String(value || "");
  const date = new Date(text);
  if (!Number.isFinite(date.getTime()) || date.toISOString() !== text) {
    throw new Error("Luma evidence observed time invalid");
  }
  return text;
}

function rootDir(value) {
  const root = path.resolve(String(value || ""));
  if (!path.isAbsolute(root) || root === path.parse(root).root) {
    throw new Error("Luma evidence data directory invalid");
  }
  return root;
}

function atomicWrite(file, bytes) {
  fs.mkdirSync(path.dirname(file), { recursive: true, mode: 0o700 });
  if (fs.existsSync(file)) {
    if (!fs.readFileSync(file).equals(bytes)) {
      throw new Error("Luma evidence immutable object collision");
    }
    return;
  }
  const temporary = `${file}.tmp-${process.pid}-${randomUUID()}`;
  fs.writeFileSync(temporary, bytes, { mode: 0o600, flag: "wx" });
  try {
    fs.renameSync(temporary, file);
  } catch (error) {
    if (error.code !== "EEXIST") throw error;
    fs.unlinkSync(temporary);
  }
}

function createLumaEvidenceStore(options = {}) {
  const dataDir = rootDir(options.dataDir);
  const tenantRoot = (tenant) => path.join(
    dataDir,
    "tenants",
    tenantId(tenant),
    "outbound",
    "luma",
  );

  return Object.freeze({
    async record(input = {}) {
      const tenant = tenantId(input.tenantId);
      const eventRef = String(input.eventRef || "");
      const observedAt = exactInstant(input.observedAt);
      const screenshot = input.screenshot;
      if (!EVENT_REF.test(eventRef)) throw new Error("Luma evidence event reference invalid");
      if (
        !Buffer.isBuffer(screenshot)
        || screenshot.length < 5000
        || !screenshot.subarray(0, PNG_SIGNATURE.length).equals(PNG_SIGNATURE)
      ) {
        throw new Error("Luma evidence PNG invalid");
      }
      const artifactHash = createHash("sha256").update(screenshot).digest("hex");
      const providerId = createHash("sha256")
        .update(`${tenant}\n${eventRef}\n${observedAt}\n${artifactHash}`, "utf8")
        .digest("hex");
      const objectFile = path.join(dataDir, "objects", "sha256", artifactHash);
      atomicWrite(objectFile, screenshot);

      const receipt = {
        kind: "provider_response",
        provider_id: providerId,
        observed_at: observedAt,
        event_ref: eventRef,
        artifact_sha256: artifactHash,
      };
      const receiptBytes = Buffer.from(`${JSON.stringify(receipt)}\n`, "utf8");
      const root = tenantRoot(tenant);
      atomicWrite(path.join(root, "provider-receipts", `${providerId}.json`), receiptBytes);
      atomicWrite(
        path.join(root, "artifacts", `${artifactHash}.json`),
        Buffer.from(`${JSON.stringify({ sha256: artifactHash, event_ref: eventRef })}\n`, "utf8"),
      );
      return Object.freeze({
        external_receipt_ref: `provider-receipt://luma/${providerId}`,
        artifact_ref: `object://sha256/${artifactHash}`,
      });
    },

    async readExternalReceipt(requestTenantId, ref) {
      const tenant = tenantId(requestTenantId);
      const match = RECEIPT_REF.exec(String(ref || ""));
      if (!match) throw new Error("Luma provider receipt unavailable");
      const file = path.join(tenantRoot(tenant), "provider-receipts", `${match[1]}.json`);
      let value;
      try {
        value = JSON.parse(fs.readFileSync(file, "utf8"));
      } catch {
        throw new Error("Luma provider receipt unavailable");
      }
      if (
        value.kind !== "provider_response"
        || value.provider_id !== match[1]
        || !EVENT_REF.test(String(value.event_ref || ""))
        || !/^[0-9a-f]{64}$/.test(String(value.artifact_sha256 || ""))
      ) {
        throw new Error("Luma provider receipt unavailable");
      }
      return Object.freeze({
        kind: value.kind,
        provider_id: value.provider_id,
        observed_at: exactInstant(value.observed_at),
      });
    },

    async readArtifact(requestTenantId, ref) {
      const tenant = tenantId(requestTenantId);
      const match = OBJECT_REF.exec(String(ref || ""));
      if (!match) throw new Error("Luma artifact unavailable");
      const marker = path.join(tenantRoot(tenant), "artifacts", `${match[1]}.json`);
      try {
        const ownership = JSON.parse(fs.readFileSync(marker, "utf8"));
        if (ownership.sha256 !== match[1] || !EVENT_REF.test(ownership.event_ref)) {
          throw new Error("invalid marker");
        }
        const bytes = fs.readFileSync(path.join(dataDir, "objects", "sha256", match[1]));
        const digest = createHash("sha256").update(bytes).digest("hex");
        if (digest !== match[1]) throw new Error("integrity mismatch");
        return bytes;
      } catch {
        throw new Error("Luma artifact unavailable");
      }
    },
  });
}

module.exports = {
  createLumaEvidenceStore,
};
