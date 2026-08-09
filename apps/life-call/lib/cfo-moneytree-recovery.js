"use strict";

const { isProxy } = require("node:util").types;
const { composeMoneytreeRead } = require("./cfo-moneytree-state.js");
const { buildCfoDailyReport } = require("./cfo-daily-snapshot.js");

const ERROR_PREFIX = "cfo_moneytree_recovery_failed:";
const INPUT_KEYS = new Set(["reportingDate", "observedAt"]);
const OPTION_KEYS = new Set(["read", "repair", "wait"]);
const MONEYTREE_READ_KEYS = new Set(["schemaVersion", "source", "state"]);
const TRANSIENT = new Set(["timeout", "network", "rate_limited", "provider_5xx"]);
const RECONSENT = new Set(["unauthorized", "forbidden", "expired", "revoked"]);
const WAITS = Object.freeze([1000, 5000]);
const RETRY_LABELS = Object.freeze({ reconsent: "Moneytreeを再接続してください", provider_outage: "30分後に自動再試行します" });
const RFC3339 = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(\.\d+)?(Z|[+-]\d{2}:\d{2})$/;

function fail(code) { throw new Error(`${ERROR_PREFIX}${code}`); }

function exactObject(value, allowed) {
  if (value === null || typeof value !== "object" || Array.isArray(value) || isProxy(value)) fail("invalid_input");
  try {
    if (Object.getPrototypeOf(value) !== Object.prototype) fail("invalid_input");
    const keys = Reflect.ownKeys(value);
    if (keys.length !== allowed.size || keys.some((key) => typeof key !== "string" || !allowed.has(key))) fail("invalid_input");
    for (const key of keys) {
      const descriptor = Object.getOwnPropertyDescriptor(value, key);
      if (!descriptor || !Object.prototype.hasOwnProperty.call(descriptor, "value") || !descriptor.enumerable) fail("invalid_input");
    }
  } catch (error) {
    if (error.message === `${ERROR_PREFIX}invalid_input`) throw error;
    fail("invalid_input");
  }
}

function timestamp(value) {
  if (typeof value !== "string") fail("invalid_input");
  const match = RFC3339.exec(value);
  if (!match) fail("invalid_input");
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const hour = Number(match[4]);
  const minute = Number(match[5]);
  const second = Number(match[6]);
  const zone = match[8];
  const zoneHour = zone === "Z" ? 0 : Number(zone.slice(1, 3));
  const zoneMinute = zone === "Z" ? 0 : Number(zone.slice(4));
  const end = new Date(0);
  end.setUTCFullYear(year, month, 0);
  if (month < 1 || month > 12 || day < 1 || day > end.getUTCDate() || hour > 23 || minute > 59 || second > 59 || zoneHour > 23 || zoneMinute > 59) fail("invalid_input");
  const parsed = Date.parse(value);
  if (!Number.isFinite(parsed)) fail("invalid_input");
  return parsed;
}

function validateInput(input, options) {
  exactObject(input, INPUT_KEYS);
  if (typeof input.reportingDate !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(input.reportingDate)) fail("invalid_input");
  const date = new Date(`${input.reportingDate}T00:00:00Z`);
  if (date.toISOString().slice(0, 10) !== input.reportingDate) fail("invalid_input");
  timestamp(input.observedAt);
  exactObject(options, OPTION_KEYS);
  if (typeof options.read !== "function" || typeof options.repair !== "function" || typeof options.wait !== "function") fail("invalid_input");
}

function validateClosedTree(value, seen = new WeakSet()) {
  if (value === null || typeof value !== "object") {
    if (typeof value === "function" || typeof value === "symbol") fail("invalid_read_result");
    return;
  }
  if (isProxy(value) || seen.has(value)) fail("invalid_read_result");
  seen.add(value);
  let keys;
  try {
    const array = Array.isArray(value);
    if (Object.getPrototypeOf(value) !== (array ? Array.prototype : Object.prototype)) fail("invalid_read_result");
    keys = Reflect.ownKeys(value);
    for (const key of keys) {
      if (array && key === "length") continue;
      const descriptor = Object.getOwnPropertyDescriptor(value, key);
      if (typeof key !== "string" || !descriptor || !Object.prototype.hasOwnProperty.call(descriptor, "value") || !descriptor.enumerable) fail("invalid_read_result");
    }
    for (const key of keys) if (!(array && key === "length")) validateClosedTree(value[key], seen);
  } catch (error) {
    if (error.message === `${ERROR_PREFIX}invalid_read_result`) throw error;
    fail("invalid_read_result");
  }
}

function validReadResult(value) {
  if (value === null || typeof value !== "object" || Array.isArray(value) || isProxy(value)) fail("invalid_read_result");
  if (value.ok === true) {
    exactObject(value, new Set(["ok", "moneytreeRead"]));
    if (typeof value.moneytreeRead !== "object" || value.moneytreeRead === null) fail("invalid_read_result");
    validateClosedTree(value.moneytreeRead);
    try {
      for (const key of Reflect.ownKeys(value.moneytreeRead)) {
        const descriptor = Object.getOwnPropertyDescriptor(value.moneytreeRead, key);
        if (typeof key !== "string" || !MONEYTREE_READ_KEYS.has(key) || !descriptor || !Object.prototype.hasOwnProperty.call(descriptor, "value")) fail("invalid_read_result");
      }
    } catch (error) {
      if (error.message === `${ERROR_PREFIX}invalid_read_result`) throw error;
      fail("invalid_read_result");
    }
  } else if (value.ok === false) {
    exactObject(value, new Set(["ok", "kind"]));
    if (typeof value.kind !== "string" || (!TRANSIENT.has(value.kind) && !RECONSENT.has(value.kind))) fail("invalid_read_result");
  } else {
    fail("invalid_read_result");
  }
}

function nextRetryAt(value) {
  const match = RFC3339.exec(value);
  const zone = match[8];
  const offset = zone === "Z" ? 0 : (Number(zone.slice(1, 3)) * 60 + Number(zone.slice(4))) * (zone[0] === "-" ? -1 : 1);
  const local = new Date(Date.parse(value) + 30 * 60 * 1000 + offset * 60 * 1000);
  const fraction = match[7] ? `.${String(local.getUTCMilliseconds()).padStart(3, "0")}${match[7].slice(4)}` : "";
  const part = (number, length = 2) => String(number).padStart(length, "0");
  return `${part(local.getUTCFullYear(), 4)}-${part(local.getUTCMonth() + 1)}-${part(local.getUTCDate())}T${part(local.getUTCHours())}:${part(local.getUTCMinutes())}:${part(local.getUTCSeconds())}${fraction}${zone}`;
}

function frozenResult(value) {
  const copy = structuredClone(value);
  const freeze = (item, seen = new WeakSet()) => {
    if (item === null || typeof item !== "object" || seen.has(item)) return item;
    seen.add(item);
    Reflect.ownKeys(item).forEach((key) => freeze(item[key], seen));
    return Object.freeze(item);
  };
  return freeze(copy);
}

function result(input, attempts, status, failureKind, moneytreeRead, repair, action) {
  return frozenResult({ reportingDate: input.reportingDate, observedAt: input.observedAt, status, attempts, failureKind, moneytreeRead, repair, action });
}
function action(kind, nextRetryAt) { return { kind, sourceLabel: "Moneytree", retryLabel: RETRY_LABELS[kind], nextRetryAt }; }

async function recoverMoneytreeRead(input, options) {
  try { validateInput(input, options); } catch (error) { if (error.message.startsWith(ERROR_PREFIX)) throw error; fail("invalid_input"); }
  const attempts = { reads: 0, repairs: 0, waits: [] };
  let originalFailure = null;
  for (let index = 0; index < 3; index += 1) {
    let readResult;
    try { readResult = await options.read({ attempt: index + 1 }); validReadResult(readResult); } catch (error) { fail("callback"); }
    attempts.reads += 1;
    if (readResult.ok) {
      try {
        const composed = composeMoneytreeRead({ source: readResult.moneytreeRead.source, state: readResult.moneytreeRead.state });
        buildCfoDailyReport({ reportingDate: input.reportingDate, moneytreeRead: composed });
        return result(input, attempts, originalFailure ? "recovered" : "fresh", null, composed, originalFailure ? { sourceLabel: "Moneytree", freshReread: true, reconciled: true } : null, null);
      } catch { return result(input, attempts, "action_required", originalFailure || "provider_outage", null, null, action("provider_outage", nextRetryAt(input.observedAt))); }
    }
    if (!originalFailure) originalFailure = readResult.kind;
    if (RECONSENT.has(readResult.kind)) return result(input, attempts, "action_required", readResult.kind, null, null, action("reconsent", nextRetryAt(input.observedAt)));
    if (!TRANSIENT.has(readResult.kind) || index >= 2) break;
    try { if (await options.repair({ kind: readResult.kind, attempt: index + 1 }) !== true) fail("callback"); attempts.repairs += 1; if (await options.wait(WAITS[index]) !== undefined) fail("callback"); attempts.waits.push(WAITS[index]); } catch { fail("callback"); }
  }
  return result(input, attempts, "action_required", originalFailure, null, null, action("provider_outage", nextRetryAt(input.observedAt)));
}

module.exports = { recoverMoneytreeRead };
