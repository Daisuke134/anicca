"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { composeMoneytreeRead, deriveMoneytreeState } = require("./cfo-moneytree-state.js");
const { recoverMoneytreeRead } = require("./cfo-moneytree-recovery.js");

const INPUT = Object.freeze({ reportingDate: "2026-08-09", observedAt: "2026-08-09T08:00:00+09:00" });
const NEXT_RETRY_AT = "2026-08-09T08:30:00+09:00";
const FAILURE_KINDS = ["timeout", "network", "rate_limited", "provider_5xx"];
const RECONSENT_KINDS = ["unauthorized", "forbidden", "expired", "revoked"];

function validRead(observedAt = INPUT.observedAt, amount = 1234) {
  const source = {
    schemaVersion: 1, sourceId: "moneytree_mufg", consent: "valid", freshness: "fresh", asOf: observedAt,
    accounts: [{ accountRef: "source_account:mt_test", label: "MUFG 普通預金", kind: "deposit", currency: "JPY", balanceMinor: amount, verificationStatus: "provider_reported" }],
    liabilities: [], evidenceRef: "evidence:mt_test", partial: true, actionRequired: null,
  };
  const state = deriveMoneytreeState({ signal: "authorized", observedAt, aggregationAsOf: null, aggregationFreshnessCutoff: null, liabilitiesExposed: false, liabilityCount: null });
  return composeMoneytreeRead({ source, state });
}

function effects(overrides = {}) {
  return { read: overrides.read || (async () => ({ ok: true, moneytreeRead: validRead() })), repair: overrides.repair || (async () => true), wait: overrides.wait || (async () => undefined) };
}

async function rejected(call, pattern = /^cfo_moneytree_recovery_failed:[a-z0-9_]+$/) {
  await assert.rejects(call, (error) => {
    assert.match(error.message, pattern);
    assert.doesNotMatch(error.message, /secret|token|account|amount|https?:\/\//i);
    return true;
  });
}

test("first fresh read returns fresh with one read and no repair or wait", async () => {
  const calls = { read: 0, repair: 0, wait: 0 };
  const result = await recoverMoneytreeRead(INPUT, effects({
    read: async () => { calls.read += 1; return { ok: true, moneytreeRead: validRead() }; },
    repair: async () => { calls.repair += 1; return true; }, wait: async () => { calls.wait += 1; },
  }));
  assert.equal(result.status, "fresh"); assert.equal(result.attempts, 1); assert.equal(calls.read, 1);
  assert.equal(calls.repair, 0); assert.equal(calls.wait, 0); assert.equal(result.failureKind, null);
  assert.deepEqual(Object.keys(result).sort(), ["action", "attempts", "failureKind", "moneytreeRead", "observedAt", "repair", "reportingDate", "status"]);
  assert.equal(Object.isFrozen(result), true); assert.equal(Object.isFrozen(result.moneytreeRead), true);
});
for (const kind of FAILURE_KINDS) test(`${kind} repairs, waits, rereads, composes, and reconciles before recovered`, async () => {
  const calls = { reads: 0, repairs: [], waits: [] };
  const result = await recoverMoneytreeRead(INPUT, effects({
    read: async () => { calls.reads += 1; return calls.reads === 1 ? { ok: false, kind } : { ok: true, moneytreeRead: validRead() }; },
    repair: async (input) => { calls.repairs.push(input); return true; }, wait: async (milliseconds) => { calls.waits.push(milliseconds); },
  }));
  assert.equal(result.status, "recovered"); assert.equal(result.attempts, 2); assert.equal(result.failureKind, null);
  assert.equal(calls.reads, 2); assert.deepEqual(calls.repairs, [{ kind, attempt: 1 }]); assert.deepEqual(calls.waits, [1000]);
  assert.deepEqual(result.repair, { sourceLabel: "Moneytree", freshReread: true, reconciled: true });
});

test("exhausted recovery is bounded and preserves the original failure kind", async () => {
  const calls = { reads: 0, repairs: [], waits: [] };
  const result = await recoverMoneytreeRead(INPUT, effects({
    read: async () => { calls.reads += 1; return { ok: false, kind: "timeout" }; },
    repair: async (input) => { calls.repairs.push(input); return true; }, wait: async (milliseconds) => { calls.waits.push(milliseconds); },
  }));
  assert.equal(result.status, "action_required"); assert.equal(result.attempts, 3); assert.equal(result.failureKind, "timeout");
  assert.equal(result.action.kind, "provider_outage"); assert.equal(result.action.nextRetryAt, NEXT_RETRY_AT);
  assert.equal(result.moneytreeRead, null); assert.equal(result.repair, null);
  assert.equal(calls.reads, 3); assert.deepEqual(calls.repairs, [{ kind: "timeout", attempt: 1 }, { kind: "timeout", attempt: 2 }]); assert.deepEqual(calls.waits, [1000, 5000]);
});

for (const kind of RECONSENT_KINDS) test(`${kind} requires reconsent without repair or wait`, async () => {
  let reads = 0; let repairs = 0; let waits = 0;
  const result = await recoverMoneytreeRead(INPUT, effects({
    read: async () => { reads += 1; return { ok: false, kind }; }, repair: async () => { repairs += 1; return true; }, wait: async () => { waits += 1; },
  }));
  assert.equal(result.status, "action_required"); assert.equal(result.failureKind, kind); assert.equal(result.action.kind, "reconsent");
  assert.equal(result.action.nextRetryAt, NEXT_RETRY_AT); assert.equal(reads, 1); assert.equal(repairs, 0); assert.equal(waits, 0);
});

test("schema failure becomes provider outage and does not claim repair", async () => {
  const result = await recoverMoneytreeRead(INPUT, effects({ read: async () => ({ ok: true, moneytreeRead: { schemaVersion: 1 } }) }));
  assert.equal(result.status, "action_required"); assert.equal(result.failureKind, "provider_outage");
  assert.equal(result.action.kind, "provider_outage"); assert.equal(result.repair, null); assert.equal(result.moneytreeRead, null);
});

test("input and option shapes fail before callback effects", async () => {
  let calls = 0; const options = effects({ read: async () => { calls += 1; return { ok: true, moneytreeRead: validRead() }; } });
  const inputs = [
    { ...INPUT, reportingDate: "2026-02-29" }, { ...INPUT, reportingDate: "2026-08-09", observedAt: "2026-08-09T08:00:00" },
    Object.assign(Object.create(null), INPUT), { ...INPUT, extra: true }, { ...INPUT, [Symbol("secret")]: true },
  ];
  for (const input of inputs) await rejected(() => recoverMoneytreeRead(input, options));
  const accessor = {}; Object.defineProperty(accessor, "reportingDate", { enumerable: true, get: () => "2026-08-09" }); Object.defineProperty(accessor, "observedAt", { enumerable: true, value: INPUT.observedAt });
  await rejected(() => recoverMoneytreeRead(accessor, options));
  const custom = Object.assign(Object.create({ inherited: true }), INPUT); await rejected(() => recoverMoneytreeRead(custom, options));
  const proxied = new Proxy({ ...INPUT }, {}); await rejected(() => recoverMoneytreeRead(proxied, options));
  await rejected(() => recoverMoneytreeRead(INPUT, { ...options, extra: true })); assert.equal(calls, 0);
});

test("hostile callback values and errors are fixed and redacted", async () => {
  const hostile = "secret-token account=123 amount=999 https://private.example";
  await rejected(() => recoverMoneytreeRead(INPUT, effects({ read: async () => { throw new Error(hostile); } })));
  await rejected(() => recoverMoneytreeRead(INPUT, effects({ read: async () => ({ ok: "yes", kind: hostile }) })));
  await rejected(() => recoverMoneytreeRead(INPUT, effects({ read: async () => ({ ok: false, kind: hostile }) })));
  await rejected(() => recoverMoneytreeRead(INPUT, effects({ read: async () => ({ ok: false, kind: "timeout" }), repair: async () => hostile })));
  await rejected(() => recoverMoneytreeRead(INPUT, effects({ read: async () => ({ ok: false, kind: "timeout" }), wait: async () => hostile })));
});
