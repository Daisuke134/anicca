"use strict";

const crypto = require("node:crypto");

class MobileError extends Error {
  constructor(code, message, status = 400, retryable = false, details = undefined) {
    super(message || code);
    this.name = "MobileError";
    this.code = code;
    this.status = status;
    this.retryable = retryable;
    if (details !== undefined) this.details = details;
  }
}

function nowMs(deps = {}) {
  const value = typeof deps.now === "function" ? deps.now() : Date.now();
  return Number.isFinite(value) ? value : Date.now();
}

function nowIso(deps = {}) {
  return new Date(nowMs(deps)).toISOString();
}

function randomOpaque(prefix, deps = {}, bytes = 18) {
  const source = typeof deps.randomBytes === "function" ? deps.randomBytes(bytes) : crypto.randomBytes(bytes);
  const raw = Buffer.isBuffer(source) ? source : Buffer.from(String(source));
  return `${prefix}${raw.toString("base64url")}`;
}

function sha256(value) {
  return crypto.createHash("sha256").update(String(value)).digest("hex");
}

function hashOpaque(value) {
  return sha256(value);
}

function timingEqual(left, right) {
  const a = Buffer.from(String(left || ""));
  const b = Buffer.from(String(right || ""));
  return a.length > 0 && a.length === b.length && crypto.timingSafeEqual(a, b);
}

function parseBearer(req) {
  const value = req && req.headers && (req.headers.authorization || req.headers.Authorization);
  const match = /^Bearer[ \t]+([^ \t]+)$/u.exec(String(value || ""));
  return match ? match[1] : null;
}

function normalizeLocale(value, fallback = "en") {
  const locale = String(value || fallback).toLowerCase();
  if (locale !== "en" && locale !== "ja") throw new MobileError("invalid_locale", "Supported product language is required.");
  return locale;
}

function maskPhone(value) {
  if (!value) return null;
  const phone = String(value);
  if (phone.length <= 4) return "••••";
  return `${phone.slice(0, 3)}${"•".repeat(Math.max(4, phone.length - 5))}${phone.slice(-2)}`;
}

function canonicalJson(value) {
  if (value === null || typeof value !== "object") return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`;
  return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(",")}}`;
}

function safeTimeZone(value, fallback = "UTC") {
  const candidate = String(value || fallback);
  try {
    new Intl.DateTimeFormat("en-US", { timeZone: candidate }).format();
    return candidate;
  } catch {
    throw new MobileError("invalid_timezone", "A valid IANA timezone is required.");
  }
}

function requestId(req) {
  const incoming = String(req && req.headers && (req.headers["x-request-id"] || req.headers["X-Request-Id"]) || "").trim();
  return incoming && incoming.length <= 128 ? incoming : randomOpaque("request:v1:");
}

module.exports = {
  MobileError,
  nowMs,
  nowIso,
  randomOpaque,
  sha256,
  hashOpaque,
  timingEqual,
  parseBearer,
  normalizeLocale,
  maskPhone,
  canonicalJson,
  safeTimeZone,
  requestId,
};
