"use strict";

const CACHE_MS = 60 * 60 * 1000;
const WARN_MS = 60 * 60 * 1000;
let cache = { key: "", available: false, expiresAt: -1 };
let lastWarnAt = -Infinity;

function warnUnavailable(nowMs, warn, reason) {
  if (nowMs - lastWarnAt < WARN_MS) return;
  lastWarnAt = nowMs;
  warn(`[mail] Gmail unavailable; feature is honestly OFF (${reason})`);
}

async function mailAvailable(user, opts = {}) {
  const accountId = user && user.gmail_account_id;
  const token = opts.token || process.env.UNIPILE_TOKEN || "";
  const dsn = opts.dsn || process.env.UNIPILE_DSN || "";
  const nowMs = opts.nowMs == null ? Date.now() : opts.nowMs;
  const warn = opts.warn || console.warn;
  if (!accountId || !token || !dsn) {
    warnUnavailable(nowMs, warn, "missing account or provider credentials");
    return false;
  }
  const key = `${dsn}\n${token}`;
  if (cache.key === key && nowMs < cache.expiresAt) {
    if (!cache.available) warnUnavailable(nowMs, warn, "provider probe failed");
    return cache.available;
  }
  let available = false;
  try {
    const fetchImpl = opts.fetchImpl || globalThis.fetch;
    const response = await fetchImpl(`https://${dsn}/api/v1/accounts?limit=1`, {
      headers: { "X-API-KEY": token, accept: "application/json" },
    });
    available = Boolean(response && response.ok);
  } catch { available = false; }
  cache = { key, available, expiresAt: nowMs + CACHE_MS };
  if (!available) warnUnavailable(nowMs, warn, "provider probe failed");
  return available;
}

function resetMailAvailabilityCache() {
  cache = { key: "", available: false, expiresAt: -1 };
  lastWarnAt = -Infinity;
}

module.exports = { CACHE_MS, WARN_MS, mailAvailable, resetMailAvailabilityCache };
