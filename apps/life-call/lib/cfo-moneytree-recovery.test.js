"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { validateFinancialSourceResult } = require("./cfo-financial-source.js");
const { composeMoneytreeRead, deriveMoneytreeState } = require("./cfo-moneytree-state.js");
const { recoverMoneytreeRead } = require("./cfo-moneytree-recovery.js");

const INPUT = Object.freeze({ reportingDate: "2026-08-09", observedAt: "2026-08-09T08:00:00+09:00" });
const NEXT_RETRY_AT = "2026-08-09T08:30:00+09:00";
const TRANSIENT = ["timeout", "network", "rate_limited", "provider_5xx"];
const RECONSENT = ["unauthorized", "forbidden", "expired", "revoked"];

function validRead(observedAt = INPUT.observedAt, amount = 1234) {
  const source = validateFinancialSourceResult({
    schemaVersion: 1, sourceId: "moneytree_mufg", consent: "valid", freshness: "fresh", asOf: observedAt,
    accounts: [{ accountRef: "source_account:mt_test", label: "MUFG 普通預金", kind: "deposit", currency: "JPY", balanceMinor: amount, verificationStatus: "provider_reported" }],
    liabilities: [], evidenceRef: "evidence:mt_test", partial: true, actionRequired: null,
  });
  const state = deriveMoneytreeState({ signal: "authorized", observedAt, aggregationAsOf: null, aggregationFreshnessCutoff: null, liabilitiesExposed: false, liabilityCount: null });
  return composeMoneytreeRead({ source, state });
}

function effects(overrides = {}) {
  return {
    read: async () => ({ ok: true, moneytreeRead: validRead() }),
    repair: async () => true,
    wait: async () => undefined,
    ...overrides,
  };
}

async function rejected(call) {
  await assert.rejects(call, (error) => {
    assert.match(error.message, /^cfo_moneytree_recovery_failed:[a-z0-9_]+$/);
    assert.doesNotMatch(error.message, /secret|token|account|amount|https?:\/\//i);
    return true;
  });
}

function assertFrozen(value, seen = new WeakSet()) {
  if (value === null || typeof value !== "object" || seen.has(value)) return;
  seen.add(value);
  assert.equal(Object.isFrozen(value), true);
  Reflect.ownKeys(value).forEach((key) => assertFrozen(value[key], seen));
}

test("recovers a valid first read with the exact frozen result contract", async () => {
  const calls = { read: 0, repair: 0, wait: 0 };
  const result = await recoverMoneytreeRead(
    { reportingDate: "2026-08-09", observedAt: "2026-08-09T08:00:00+09:00" },
    effects({
      read: async () => { calls.read += 1; return { ok: true, moneytreeRead: validRead() }; },
      repair: async () => { calls.repair += 1; return true; },
      wait: async () => { calls.wait += 1; },
    }),
  );
  assert.equal(result.status, "fresh");
  assert.equal(calls.read, 1);
  assert.equal(calls.repair, 0);
  assert.equal(calls.wait, 0);
  assert.equal(result.failureKind, null);
  assert.deepEqual(Object.keys(result).sort(), ["action", "attempts", "failureKind", "moneytreeRead", "observedAt", "repair", "reportingDate", "status"]);
  assert.deepEqual(result.attempts, { reads: 1, repairs: 0, waits: [] });
  assert.equal(result.reportingDate, INPUT.reportingDate);
  assert.equal(result.observedAt, INPUT.observedAt);
  assert.equal(result.repair, null);
  assert.equal(result.action, null);
  assert.deepEqual(result.moneytreeRead, validRead());
  assertFrozen(result);
});

for (const kind of TRANSIENT) test(`${kind} repairs, waits, rereads, composes, and reconciles before recovered`, async () => {
  const calls = { reads: 0, repairs: [], waits: [] };
  const result = await recoverMoneytreeRead(INPUT, effects({
    read: async () => { calls.reads += 1; return calls.reads === 1 ? { ok: false, kind } : { ok: true, moneytreeRead: validRead() }; },
    repair: async (value) => { calls.repairs.push(value); return true; },
    wait: async (milliseconds) => { calls.waits.push(milliseconds); },
  }));
  assert.equal(result.status, "recovered");
  assert.equal(result.attempts.reads, 2);
  assert.equal(result.failureKind, null);
  assert.deepEqual(calls.repairs, [{ kind, attempt: 1 }]);
  assert.deepEqual(calls.waits, [1000]);
  assert.deepEqual(result.repair, { sourceLabel: "Moneytree", freshReread: true, reconciled: true });
  assertFrozen(result);
});

test("exhausted recovery is bounded and preserves the original failure kind", async () => {
  const calls = { reads: 0, repairs: [], waits: [] };
  const result = await recoverMoneytreeRead(INPUT, effects({
    read: async () => { calls.reads += 1; return { ok: false, kind: "timeout" }; },
    repair: async (value) => { calls.repairs.push(value); return true; },
    wait: async (milliseconds) => { calls.waits.push(milliseconds); },
  }));
  assert.equal(result.status, "action_required");
  assert.equal(result.attempts.reads, 3);
  assert.equal(result.failureKind, "timeout");
  assert.equal(result.action.kind, "provider_outage");
  assert.equal(result.action.nextRetryAt, NEXT_RETRY_AT);
  assert.equal(result.moneytreeRead, null);
  assert.equal(result.repair, null);
  assert.deepEqual(calls.repairs, [{ kind: "timeout", attempt: 1 }, { kind: "timeout", attempt: 2 }]);
  assert.deepEqual(calls.waits, [1000, 5000]);
  assertFrozen(result);
});

for (const kind of RECONSENT) test(`${kind} requires reconsent without repair or wait`, async () => {
  let reads = 0; let repairs = 0; let waits = 0;
  const result = await recoverMoneytreeRead(INPUT, effects({
    read: async () => { reads += 1; return { ok: false, kind }; },
    repair: async () => { repairs += 1; return true; },
    wait: async () => { waits += 1; },
  }));
  assert.equal(result.status, "action_required");
  assert.equal(result.failureKind, kind);
  assert.equal(result.action.kind, "reconsent");
  assert.equal(result.action.nextRetryAt, NEXT_RETRY_AT);
  assert.equal(reads, 1); assert.equal(repairs, 0); assert.equal(waits, 0);
});

test("schema and composition failures become provider outage", async () => {
  let repairs = 0; let waits = 0;
  const result = await recoverMoneytreeRead(INPUT, effects({
    read: async () => ({ ok: true, moneytreeRead: { schemaVersion: 1 } }),
    repair: async () => { repairs += 1; return true; },
    wait: async () => { waits += 1; },
  }));
  assert.equal(result.status, "action_required");
  assert.equal(result.failureKind, "provider_outage");
  assert.equal(result.action.kind, "provider_outage");
  assert.equal(result.action.nextRetryAt, NEXT_RETRY_AT);
  assert.equal(result.moneytreeRead, null); assert.equal(result.repair, null);
  assert.equal(repairs, 0); assert.equal(waits, 0);
});

test("a repaired read is not recovered unless the fresh reread composes and reconciles", async () => {
  let reads = 0;
  const result = await recoverMoneytreeRead(INPUT, effects({
    read: async () => {
      reads += 1;
      return reads === 1 ? { ok: false, kind: "timeout" } : { ok: true, moneytreeRead: { schemaVersion: 1 } };
    },
  }));
  assert.equal(result.status, "action_required");
  assert.equal(result.failureKind, "timeout");
  assert.equal(result.action.kind, "provider_outage");
  assert.equal(result.attempts.reads, 2);
  assert.equal(result.repair, null);
});

test("preserves the initial transient failure kind when a reread requires reconsent", async () => {
  let reads = 0;
  const result = await recoverMoneytreeRead(INPUT, effects({
    read: async () => {
      reads += 1;
      return reads === 1 ? { ok: false, kind: "timeout" } : { ok: false, kind: "forbidden" };
    },
  }));
  assert.equal(result.status, "action_required");
  assert.equal(result.failureKind, "timeout");
  assert.equal(result.action.kind, "reconsent");
  assert.equal(result.attempts.reads, 2);
});

test("preserves the original failure kind and computes retry time from the RFC3339 instant", async () => {
  const input = { reportingDate: "2024-02-29", observedAt: "2024-02-29T23:45:00.123Z" };
  const kinds = ["timeout", "network", "provider_5xx"];
  const result = await recoverMoneytreeRead(input, effects({
    read: async () => ({ ok: false, kind: kinds.shift() }),
  }));
  assert.equal(result.status, "action_required");
  assert.equal(result.failureKind, "timeout");
  assert.equal(result.action.nextRetryAt, "2024-03-01T00:15:00.123Z");
  assert.deepEqual(result.attempts, { reads: 3, repairs: 2, waits: [1000, 5000] });
});

test("valid calendar dates and RFC3339 times are accepted", async () => {
  const result = await recoverMoneytreeRead(
    { reportingDate: "2024-02-29", observedAt: "2024-02-29T23:59:59.123Z" },
    effects(),
  );
  assert.equal(result.status, "fresh");
});

test("input and option shapes are closed before callback effects", async () => {
  let calls = 0;
  const options = effects({ read: async () => { calls += 1; return { ok: true, moneytreeRead: validRead() }; } });
  const accessor = {}; Object.defineProperty(accessor, "reportingDate", { enumerable: true, get: () => INPUT.reportingDate }); Object.defineProperty(accessor, "observedAt", { enumerable: true, value: INPUT.observedAt });
  const hidden = { ...INPUT }; Object.defineProperty(hidden, "secret", { value: true });
  const custom = Object.assign(Object.create({ inherited: true }), INPUT);
  const inputs = [null, [], { ...INPUT, extra: true }, { ...INPUT, [Symbol("secret")]: true }, accessor, hidden, Object.create(null), custom, new Proxy({ ...INPUT }, {})];
  for (const input of inputs) await rejected(() => recoverMoneytreeRead(input, options));
  const optionAccessor = { ...options }; Object.defineProperty(optionAccessor, "wait", { enumerable: true, get: () => options.wait });
  const optionHidden = { ...options }; Object.defineProperty(optionHidden, "hidden", { value: true });
  const optionCustom = Object.assign(Object.create({ inherited: true }), options);
  for (const value of [null, [], Object.create(null), { ...options, [Symbol("secret")]: true }, { ...options, extra: true }, { read: options.read, repair: options.repair }, optionAccessor, optionHidden, optionCustom, new Proxy(options, {})]) {
    await rejected(() => recoverMoneytreeRead(INPUT, value));
  }
  assert.equal(calls, 0);
});

test("hostile callback values and errors are fixed and redacted", async () => {
  const hostile = "secret-token account=123 amount=999 https://private.example";
  const hostileError = new Proxy({}, { get: () => { throw new Error("message getter accessed"); } });
  await rejected(() => recoverMoneytreeRead(INPUT, effects({ read: async () => { throw new Error(hostile); } })));
  await rejected(() => recoverMoneytreeRead(INPUT, effects({ read: async () => { throw hostileError; } })));
  await rejected(() => recoverMoneytreeRead(INPUT, effects({ read: async () => ({ ok: "yes", kind: hostile }) })));
  await rejected(() => recoverMoneytreeRead(INPUT, effects({ read: async () => ({ ok: false, kind: hostile }) })));
  await rejected(() => recoverMoneytreeRead(INPUT, effects({ read: async () => new Proxy({ ok: false, kind: "timeout" }, {}) })));
  await rejected(() => recoverMoneytreeRead(INPUT, effects({ read: async () => ({ ok: true, moneytreeRead: { ...validRead(), extra: true } }) })));
  await rejected(() => recoverMoneytreeRead(INPUT, effects({ read: async () => ({ ok: false, kind: "timeout" }), repair: async () => hostile })));
  await rejected(() => recoverMoneytreeRead(INPUT, effects({ read: async () => ({ ok: false, kind: "timeout" }), repair: async () => { throw hostileError; } })));
  await rejected(() => recoverMoneytreeRead(INPUT, effects({ read: async () => ({ ok: false, kind: "timeout" }), wait: async () => hostile })));
  await rejected(() => recoverMoneytreeRead(INPUT, effects({ read: async () => ({ ok: false, kind: "timeout" }), wait: async () => { throw hostileError; } })));
});

test("rejects nested custom prototypes and non-enumerable callback read properties", async () => {
  const customPrototype = structuredClone(validRead());
  Object.setPrototypeOf(customPrototype.source, { inherited: true });
  await rejected(() => recoverMoneytreeRead(INPUT, effects({ read: async () => ({ ok: true, moneytreeRead: customPrototype }) })));

  const nonEnumerable = structuredClone(validRead());
  Object.defineProperty(nonEnumerable.source, "hidden", { value: true });
  await rejected(() => recoverMoneytreeRead(INPUT, effects({ read: async () => ({ ok: true, moneytreeRead: nonEnumerable }) })));
});
