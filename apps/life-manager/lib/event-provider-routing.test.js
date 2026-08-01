"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { runEventProviderRouting } = require("./event-provider-routing.js");

const candidates = [
  { event_ref: "luma-event://event/a", canonical_url: "https://luma.com/a" },
  { event_ref: "luma-event://event/b", canonical_url: "https://luma.com/b" },
];

test("Lumaでbookedならconnpassを呼ばない", async () => {
  let connpassCalls = 0;
  const result = await runEventProviderRouting({
    date: "2026-08-10", lumaCandidates: candidates,
    attemptLuma: async () => ({ status: "verified_registered", receipt_ref: "provider-receipt://luma/a" }),
    runConnpass: async () => { connpassCalls += 1; },
  });
  assert.equal(result.status, "booked");
  assert.equal(result.provider, "luma");
  assert.equal(connpassCalls, 0);
});

test("Luma recoveryやunknown effectでは別providerへ進まない", async () => {
  for (const outcome of [{ status: "login_required" }, { status: "unknown_effect" }]) {
    let connpassCalls = 0;
    const result = await runEventProviderRouting({
      date: "2026-08-10", lumaCandidates: candidates,
      attemptLuma: async () => outcome,
      runConnpass: async () => { connpassCalls += 1; },
    });
    assert.equal(connpassCalls, 0);
    assert.equal(["recovery_required", "reconciliation_required"].includes(result.status), true);
  }
});

test("全Luma候補を既知理由で尽くした時だけconnpassを一度呼ぶ", async () => {
  let lumaCalls = 0;
  let connpassCalls = 0;
  const result = await runEventProviderRouting({
    date: "2026-08-10", lumaCandidates: candidates,
    attemptLuma: async () => { lumaCalls += 1; return { status: "full" }; },
    runConnpass: async ({ date }) => {
      connpassCalls += 1;
      assert.equal(date, "2026-08-10");
      return { status: "booked", receipt_ref: "provider-receipt://connpass/event-1" };
    },
  });
  assert.equal(lumaCalls, 2);
  assert.equal(connpassCalls, 1);
  assert.equal(result.status, "booked");
  assert.equal(result.provider, "connpass");
});

test("connpass key未発行はその日をcoverage_openのまま残す", async () => {
  const result = await runEventProviderRouting({
    date: "2026-08-10", lumaCandidates: candidates,
    attemptLuma: async () => ({ status: "not_eligible" }),
    runConnpass: async () => ({ status: "disabled", reason: "api_key_unavailable" }),
  });
  assert.deepEqual(result, {
    status: "coverage_open", date: "2026-08-10", reason: "api_key_unavailable",
    luma_candidates_exhausted: true, connpass_attempted: true,
  });
});

test("connpass unknown effectはreconciliationで止め、invalid resultを成功扱いしない", async () => {
  const base = { date: "2026-08-10", lumaCandidates: candidates, attemptLuma: async () => ({ status: "full" }) };
  const unknown = await runEventProviderRouting({ ...base, runConnpass: async () => ({ status: "unknown_effect" }) });
  assert.equal(unknown.status, "reconciliation_required");
  await assert.rejects(runEventProviderRouting({ ...base, runConnpass: async () => ({ status: "booked" }) }), /receipt/i);
});
