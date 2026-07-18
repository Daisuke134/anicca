"use strict";

const crypto = require("node:crypto");

const ED25519_SPKI_PREFIX = Buffer.from("302a300506032b6570032100", "hex");
const MAX_WEBHOOK_AGE_SECONDS = 5 * 60;

function encodeWakeClientState({ wakeUid, wakeEventKey } = {}) {
  if (!wakeUid || !wakeEventKey) return "";
  return Buffer.from(JSON.stringify({ wakeUid, wakeEventKey }), "utf8").toString("base64");
}

function decodeWakeClientState(value) {
  if (!value) return null;
  try {
    const parsed = JSON.parse(Buffer.from(String(value), "base64").toString("utf8"));
    if (!parsed || typeof parsed.wakeUid !== "string" || typeof parsed.wakeEventKey !== "string") return null;
    if (!parsed.wakeUid || !parsed.wakeEventKey) return null;
    return {
      wakeUid: parsed.wakeUid.slice(0, 100),
      wakeEventKey: parsed.wakeEventKey.slice(0, 300),
    };
  } catch {
    return null;
  }
}

function createTelnyxPublicKey(value) {
  const text = String(value || "").trim().replace(/\\n/g, "\n");
  if (!text) return null;
  if (text.includes("BEGIN PUBLIC KEY")) return crypto.createPublicKey(text);
  const raw = Buffer.from(text, "base64");
  if (raw.length !== 32) return null;
  return crypto.createPublicKey({
    key: Buffer.concat([ED25519_SPKI_PREFIX, raw]),
    format: "der",
    type: "spki",
  });
}

function verifyTelnyxSignature({ rawBody, signature, timestamp, publicKey, nowMs = Date.now() } = {}) {
  try {
    if (!Buffer.isBuffer(rawBody) || !signature || !timestamp || !publicKey) return false;
    const signedAt = Number(timestamp);
    if (!Number.isFinite(signedAt) || Math.abs(Math.floor(nowMs / 1000) - signedAt) > MAX_WEBHOOK_AGE_SECONDS) return false;
    const key = createTelnyxPublicKey(publicKey);
    if (!key) return false;
    const signedPayload = Buffer.concat([Buffer.from(`${timestamp}|`, "utf8"), rawBody]);
    return crypto.verify(null, signedPayload, key, Buffer.from(String(signature), "base64"));
  } catch {
    return false;
  }
}

module.exports = {
  encodeWakeClientState,
  decodeWakeClientState,
  verifyTelnyxSignature,
};
