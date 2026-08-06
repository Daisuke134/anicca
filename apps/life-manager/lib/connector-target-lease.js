"use strict";

const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

function unavailable(message) {
  throw new Error(message || "Connector target lease unavailable");
}

function exactInstant(value) {
  const text = value instanceof Date ? value.toISOString() : String(value || "");
  if (!Number.isFinite(Date.parse(text)) || new Date(Date.parse(text)).toISOString() !== text) {
    unavailable("Connector target lease timestamp invalid");
  }
  return text;
}

function targetId(value) {
  const text = String(value || "");
  if (!/^[A-Za-z0-9_-]{1,128}$/.test(text)) unavailable("Connector target ID invalid");
  return text;
}

function pageWebsocket(value, expectedTargetId) {
  const text = String(value || "");
  let parsed;
  try { parsed = new URL(text); } catch { unavailable("Connector page websocket invalid"); }
  if (
    parsed.protocol !== "ws:"
    || parsed.hostname !== "127.0.0.1"
    || parsed.port !== "9222"
    || parsed.pathname !== `/devtools/page/${expectedTargetId}`
    || parsed.username || parsed.password || parsed.search || parsed.hash
  ) unavailable("Connector page websocket invalid");
  return text;
}

function canonicalUrl(value) {
  let parsed;
  try { parsed = new URL(String(value || "")); } catch { unavailable("Connector canonical URL invalid"); }
  if (
    parsed.protocol !== "https:"
    || !["luma.com", "lu.ma"].includes(parsed.hostname)
    || parsed.username || parsed.password || parsed.hash
  ) unavailable("Connector canonical URL invalid");
  parsed.hash = "";
  return parsed.toString();
}

function ownerToken(value) {
  const text = String(value || "");
  if (!/^[A-Za-z0-9._-]{16,200}$/.test(text)) unavailable("Connector owner token invalid");
  return text;
}

function privateParent(filePath) {
  const parent = path.dirname(filePath);
  fs.mkdirSync(parent, { recursive: true, mode: 0o700 });
  fs.chmodSync(parent, 0o700);
}

function readLedger(filePath) {
  try {
    const stat = fs.statSync(filePath);
    if (stat.size > 1_000_000) unavailable("Connector target lease ledger invalid");
    const value = JSON.parse(fs.readFileSync(filePath, "utf8"));
    if (!value || value.schema_version !== 1 || !value.targets || typeof value.targets !== "object") {
      unavailable("Connector target lease ledger invalid");
    }
    return value;
  } catch (error) {
    if (error && error.code === "ENOENT") return { schema_version: 1, targets: {} };
    throw error;
  }
}

function writeLedger(filePath, value) {
  const temporary = `${filePath}.${process.pid}.${crypto.randomUUID()}.tmp`;
  try {
    fs.writeFileSync(temporary, `${JSON.stringify(value, null, 2)}\n`, { flag: "wx", mode: 0o600 });
    fs.renameSync(temporary, filePath);
    fs.chmodSync(filePath, 0o600);
  } finally {
    if (fs.existsSync(temporary)) fs.unlinkSync(temporary);
  }
}

async function withLedgerLock(filePath, task) {
  privateParent(filePath);
  const lockPath = `${filePath}.lock`;
  let handle;
  try {
    handle = fs.openSync(lockPath, "wx", 0o600);
  } catch (error) {
    if (error && error.code === "EEXIST") unavailable("Connector target lease ledger busy");
    throw error;
  }
  try {
    return await task(readLedger(filePath));
  } finally {
    fs.closeSync(handle);
    fs.unlinkSync(lockPath);
  }
}

function assertFence(record, fence) {
  if (
    !record
    || record.target_id !== targetId(fence && fence.target_id)
    || record.owner_token !== ownerToken(fence && fence.owner_token)
    || record.generation !== (fence && fence.generation)
  ) unavailable("Connector target lease fence mismatch");
  return record;
}

function createConnectorTargetLease(options = {}) {
  const ledgerPath = path.resolve(String(options.ledgerPath || ""));
  const now = options.now || (() => new Date());
  const makeOwnerToken = options.ownerToken || (() => crypto.randomUUID());
  const probeTarget = options.probeTarget;
  const closeTarget = options.closeTarget;
  if (!path.isAbsolute(ledgerPath) || ledgerPath === path.parse(ledgerPath).root) unavailable();
  if (typeof probeTarget !== "function" || typeof closeTarget !== "function") unavailable();

  return Object.freeze({
    async claim(input = {}) {
      const id = targetId(input.targetId);
      const websocket = pageWebsocket(input.pageWebsocket, id);
      const url = canonicalUrl(input.canonicalUrl);
      return withLedgerLock(ledgerPath, async (ledger) => {
        if (ledger.targets[id]) unavailable("Connector target already claimed");
        const observedAt = exactInstant(now());
        const record = Object.freeze({
          schema_version: 1,
          owner_token: ownerToken(makeOwnerToken()),
          generation: 1,
          target_id: id,
          page_websocket: websocket,
          canonical_url: url,
          claimed_at: observedAt,
          heartbeat_at: observedAt,
        });
        ledger.targets[id] = record;
        writeLedger(ledgerPath, ledger);
        return record;
      });
    },

    async heartbeat(fence) {
      return withLedgerLock(ledgerPath, async (ledger) => {
        const record = assertFence(ledger.targets[fence && fence.target_id], fence);
        const next = { ...record, heartbeat_at: exactInstant(now()) };
        ledger.targets[record.target_id] = next;
        writeLedger(ledgerPath, ledger);
        return Object.freeze(next);
      });
    },

    async probe(fence) {
      return withLedgerLock(ledgerPath, async (ledger) => {
        const record = assertFence(ledger.targets[fence && fence.target_id], fence);
        return (await probeTarget(record.page_websocket)) === true;
      });
    },

    async release(fence) {
      return withLedgerLock(ledgerPath, async (ledger) => {
        const record = assertFence(ledger.targets[fence && fence.target_id], fence);
        if ((await closeTarget(record.target_id)) !== true) unavailable("Connector target close failed");
        delete ledger.targets[record.target_id];
        writeLedger(ledgerPath, ledger);
        return true;
      });
    },

    async reapStale(input = {}) {
      const maxIdleMs = input.maxIdleMs;
      if (!Number.isInteger(maxIdleMs) || maxIdleMs < 1_000 || maxIdleMs > 86_400_000) {
        unavailable("Connector target lease stale threshold invalid");
      }
      return withLedgerLock(ledgerPath, async (ledger) => {
        const observedMs = Date.parse(exactInstant(now()));
        const reaped = [];
        const retained = [];
        for (const id of Object.keys(ledger.targets).sort()) {
          const record = ledger.targets[id];
          const heartbeatMs = Date.parse(exactInstant(record && record.heartbeat_at));
          if (observedMs - heartbeatMs <= maxIdleMs) {
            retained.push(id);
            continue;
          }
          if ((await closeTarget(id)) !== true) unavailable("Connector stale target close failed");
          delete ledger.targets[id];
          reaped.push(id);
        }
        writeLedger(ledgerPath, ledger);
        return Object.freeze({
          reaped_target_ids: Object.freeze(reaped),
          retained_target_ids: Object.freeze(retained),
        });
      });
    },
  });
}

module.exports = { createConnectorTargetLease };
