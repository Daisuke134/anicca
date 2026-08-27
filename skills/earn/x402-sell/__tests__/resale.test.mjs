// resale.test.mjs — PROD-2 (/web-search resale). No network, no real fs, no real payment: every
// I/O dependency of resaleHandler is injected via makeResaleHandler(deps), and the pure guard
// decisions in lib/resale-guards.mjs are tested directly.
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  floatGuardTripped, rolloverSpendState, dailyCapTripped, recordSpend,
  decodeChallengeHeader, extractChallengeMaxUsd, challengeGuardTripped,
} from "../lib/resale-guards.mjs";
import { makeResaleHandler } from "../resale.mjs";

const b64 = (o) => Buffer.from(JSON.stringify(o)).toString("base64");

// ---------------------------------------------------------------------------------------------
// pure guard logic
// ---------------------------------------------------------------------------------------------
test("floatGuardTripped: below floor trips, at/above floor does not", () => {
  assert.equal(floatGuardTripped(0.1, 0.5), true);
  assert.equal(floatGuardTripped(0.5, 0.5), false);
  assert.equal(floatGuardTripped(5, 0.5), false);
  assert.equal(floatGuardTripped(NaN, 0.5), true);
  assert.equal(floatGuardTripped(undefined, 0.5), true);
});

test("rolloverSpendState: same UTC date carries spend forward, stale date resets to 0", () => {
  assert.deepEqual(rolloverSpendState({ date: "2026-07-18", spentUsd: 0.3 }, "2026-07-18"), { date: "2026-07-18", spentUsd: 0.3 });
  assert.deepEqual(rolloverSpendState({ date: "2026-07-17", spentUsd: 0.9 }, "2026-07-18"), { date: "2026-07-18", spentUsd: 0 });
  assert.deepEqual(rolloverSpendState(null, "2026-07-18"), { date: "2026-07-18", spentUsd: 0 });
  assert.deepEqual(rolloverSpendState({ date: "2026-07-18", spentUsd: "oops" }, "2026-07-18"), { date: "2026-07-18", spentUsd: 0 });
});

test("dailyCapTripped: strictly under cap passes, at/over cap trips", () => {
  assert.equal(dailyCapTripped({ date: "d", spentUsd: 0.99 }, 1.0), false);
  assert.equal(dailyCapTripped({ date: "d", spentUsd: 1.0 }, 1.0), true);
  assert.equal(dailyCapTripped({ date: "d", spentUsd: 1.5 }, 1.0), true);
});

test("recordSpend: accumulates without mutating the input state", () => {
  const s0 = { date: "2026-07-18", spentUsd: 0.2 };
  const s1 = recordSpend(s0, 0.011);
  assert.deepEqual(s0, { date: "2026-07-18", spentUsd: 0.2 }, "input state must not be mutated");
  assert.deepEqual(s1, { date: "2026-07-18", spentUsd: 0.211 });
});

test("decodeChallengeHeader: valid base64 JSON decodes, malformed/absent returns null", () => {
  assert.deepEqual(decodeChallengeHeader(b64({ x402Version: 2, accepts: [] })), { x402Version: 2, accepts: [] });
  assert.equal(decodeChallengeHeader("!!!not-b64!!!"), null);
  assert.equal(decodeChallengeHeader(undefined), null);
  assert.equal(decodeChallengeHeader(""), null);
});

test("extractChallengeMaxUsd: v2 amount field, v1 maxAmountRequired fallback, no match, malformed atomic", () => {
  const v2 = { accepts: [{ scheme: "exact", network: "eip155:8453", amount: "11000" }] };
  assert.equal(extractChallengeMaxUsd(v2, { network: "eip155:8453" }), 0.011);

  const v1 = { accepts: [{ scheme: "exact", network: "base", maxAmountRequired: "9000" }] };
  assert.equal(extractChallengeMaxUsd(v1, { network: "eip155:8453" }), 0.009);

  const noMatch = { accepts: [{ scheme: "exact", network: "eip155:1", amount: "11000" }] };
  assert.equal(extractChallengeMaxUsd(noMatch, { network: "eip155:8453" }), null);

  const badAtomic = { accepts: [{ scheme: "exact", network: "eip155:8453", amount: "not-a-number" }] };
  assert.equal(extractChallengeMaxUsd(badAtomic, { network: "eip155:8453" }), null);

  assert.equal(extractChallengeMaxUsd(null), null);
  assert.equal(extractChallengeMaxUsd({}), null);
});

test("challengeGuardTripped: over ceiling trips, under/equal passes, unreadable (NaN) trips", () => {
  assert.equal(challengeGuardTripped(0.012, 0.011), true);
  assert.equal(challengeGuardTripped(0.011, 0.011), false);
  assert.equal(challengeGuardTripped(0.005, 0.011), false);
  assert.equal(challengeGuardTripped(null, 0.011), true);
  assert.equal(challengeGuardTripped(NaN, 0.011), true);
});

// ---------------------------------------------------------------------------------------------
// resaleHandler integration (fully injected deps — no network, no fs, no real payment)
// ---------------------------------------------------------------------------------------------
function fakeReq(query) { return { query }; }
function fakeRes() {
  const res = { statusCode: 200, body: undefined };
  res.status = (c) => { res.statusCode = c; return res; };
  res.json = (b) => { res.body = b; return res; };
  return res;
}
function fakeChallengeResp(amountAtomic, { network = "eip155:8453" } = {}) {
  const header = b64({ x402Version: 2, accepts: [{ scheme: "exact", network, amount: String(amountAtomic) }] });
  return { status: 402, headers: { get: (name) => (name.toLowerCase() === "payment-required" ? header : undefined) } };
}

test("resaleHandler: float guard trips before any upstream call", async () => {
  let bareCalls = 0, payCalls = 0;
  const handler = makeResaleHandler({
    getBalanceUsd: async () => 0.1,
    readState: () => ({ date: "2026-07-18", spentUsd: 0 }),
    writeState: () => { throw new Error("must not write state when float guard trips"); },
    bareFetch: async () => { bareCalls++; return fakeChallengeResp(11000); },
    payingFetch: async () => { payCalls++; return { status: 200, headers: { get: () => undefined }, json: async () => ({ results: [] }) }; },
    now: () => new Date("2026-07-18T00:00:00Z"),
  });
  const res = fakeRes();
  await handler(fakeReq({ q: "test" }), res);
  assert.equal(res.statusCode, 503);
  assert.equal(res.body.error, "resale paused: low float");
  assert.equal(bareCalls, 0, "must not call upstream when float guard trips");
  assert.equal(payCalls, 0, "must never pay when float guard trips");
});

test("resaleHandler: daily cap trips before any upstream call", async () => {
  let bareCalls = 0;
  const handler = makeResaleHandler({
    getBalanceUsd: async () => 5,
    dailyCapUsd: 1.0,
    readState: () => ({ date: "2026-07-18", spentUsd: 1.0 }),
    writeState: () => { throw new Error("must not write state when daily cap trips"); },
    bareFetch: async () => { bareCalls++; return fakeChallengeResp(11000); },
    now: () => new Date("2026-07-18T00:00:00Z"),
  });
  const res = fakeRes();
  await handler(fakeReq({ q: "test" }), res);
  assert.equal(res.statusCode, 503);
  assert.equal(res.body.error, "resale paused: daily upstream cap reached");
  assert.equal(bareCalls, 0);
});

test("resaleHandler: daily cap uses UTC-rolled state, so yesterday's spend does not carry over", async () => {
  let paid = null;
  const handler = makeResaleHandler({
    getBalanceUsd: async () => 5,
    dailyCapUsd: 1.0,
    readState: () => ({ date: "2026-07-17", spentUsd: 1.0 }), // stale date, would trip if not rolled over
    writeState: (path, s) => { paid = s; },
    bareFetch: async () => fakeChallengeResp(11000),
    payingFetch: async () => ({ status: 200, headers: { get: () => undefined }, json: async () => ({ results: [] }) }),
    now: () => new Date("2026-07-18T00:00:00Z"),
  });
  const res = fakeRes();
  await handler(fakeReq({ q: "test" }), res);
  assert.equal(res.statusCode, 200);
  assert.deepEqual(paid, { date: "2026-07-18", spentUsd: 0.011 });
});

test("resaleHandler: challenge over guard ceiling refuses to pay", async () => {
  let payCalls = 0;
  const handler = makeResaleHandler({
    getBalanceUsd: async () => 5,
    readState: () => ({ date: "2026-07-18", spentUsd: 0 }),
    writeState: () => { throw new Error("must not write state when challenge guard trips"); },
    bareFetch: async () => fakeChallengeResp(20000), // $0.02 > $0.011 ceiling
    payingFetch: async () => { payCalls++; return { status: 200, headers: { get: () => undefined }, json: async () => ({ results: [] }) }; },
    now: () => new Date("2026-07-18T00:00:00Z"),
  });
  const res = fakeRes();
  await handler(fakeReq({ q: "test" }), res);
  assert.equal(res.statusCode, 503);
  assert.equal(res.body.error, "upstream price above guard");
  assert.equal(payCalls, 0, "must never pay once the challenge guard trips");
});

test("resaleHandler: malformed challenge fails closed (never pays an unreadable price)", async () => {
  let payCalls = 0;
  const handler = makeResaleHandler({
    getBalanceUsd: async () => 5,
    readState: () => ({ date: "2026-07-18", spentUsd: 0 }),
    writeState: () => { throw new Error("must not write state when challenge is unreadable"); },
    bareFetch: async () => ({ status: 402, headers: { get: () => undefined } }), // no PAYMENT-REQUIRED header at all
    payingFetch: async () => { payCalls++; return { status: 200, headers: { get: () => undefined }, json: async () => ({ results: [] }) }; },
    now: () => new Date("2026-07-18T00:00:00Z"),
  });
  const res = fakeRes();
  await handler(fakeReq({ q: "test" }), res);
  assert.equal(res.statusCode, 503);
  assert.equal(payCalls, 0);
});

test("resaleHandler: upstream non-200 after payment -> 502, no spend recorded", async () => {
  let wrote = false;
  const handler = makeResaleHandler({
    getBalanceUsd: async () => 5,
    readState: () => ({ date: "2026-07-18", spentUsd: 0 }),
    writeState: () => { wrote = true; },
    bareFetch: async () => fakeChallengeResp(11000),
    payingFetch: async () => ({ status: 500, headers: { get: () => undefined }, json: async () => ({}) }),
    now: () => new Date("2026-07-18T00:00:00Z"),
  });
  const res = fakeRes();
  await handler(fakeReq({ q: "test" }), res);
  assert.equal(res.statusCode, 502);
  assert.equal(res.body.error, "upstream failed");
  assert.equal(wrote, false, "a failed upstream call must never be recorded as spend");
});

test("resaleHandler: upstream fetch throws -> 502, no spend recorded", async () => {
  let wrote = false;
  const handler = makeResaleHandler({
    getBalanceUsd: async () => 5,
    readState: () => ({ date: "2026-07-18", spentUsd: 0 }),
    writeState: () => { wrote = true; },
    bareFetch: async () => fakeChallengeResp(11000),
    payingFetch: async () => { throw new Error("network down"); },
    now: () => new Date("2026-07-18T00:00:00Z"),
  });
  const res = fakeRes();
  await handler(fakeReq({ q: "test" }), res);
  assert.equal(res.statusCode, 502);
  assert.equal(wrote, false);
});

test("resaleHandler: success records the real settled amount and returns the trimmed shape", async () => {
  let paid = null;
  const settleHeader = b64({ success: true, payer: "0xabc", transaction: "0xdead", amount: "9500" });
  const handler = makeResaleHandler({
    getBalanceUsd: async () => 5,
    readState: () => ({ date: "2026-07-18", spentUsd: 0.2 }),
    writeState: (path, s) => { paid = s; },
    bareFetch: async () => fakeChallengeResp(11000),
    payingFetch: async () => ({
      status: 200,
      headers: { get: (name) => (name.toLowerCase() === "payment-response" ? settleHeader : undefined) },
      json: async () => ({
        results: [
          { title: "x402 update", url: "https://example.com/a", publishedDate: "2026-07-18", author: "a", text: "x".repeat(3000), extraAccountField: "must-not-leak" },
        ],
      }),
    }),
    now: () => new Date("2026-07-18T00:00:00Z"),
  });
  const res = fakeRes();
  await handler(fakeReq({ q: "x402 news", numResults: 1 }), res);
  assert.equal(res.statusCode, 200);
  assert.equal(res.body.query, "x402 news");
  assert.equal(res.body.source, "exa");
  assert.equal(res.body.results.length, 1);
  assert.equal(res.body.results[0].title, "x402 update");
  assert.equal(res.body.results[0].text.length, 2000, "text must be trimmed");
  assert.equal(res.body.results[0].extraAccountField, undefined, "must not pass through unlisted upstream fields");
  // real settled amount ($0.0095) wins over the conservative guard-ceiling estimate ($0.011).
  assert.deepEqual(paid, { date: "2026-07-18", spentUsd: 0.2095 });
});

test("resaleHandler: success without a PAYMENT-RESPONSE header falls back to the conservative guard-ceiling estimate", async () => {
  let paid = null;
  const handler = makeResaleHandler({
    getBalanceUsd: async () => 5,
    readState: () => ({ date: "2026-07-18", spentUsd: 0 }),
    writeState: (path, s) => { paid = s; },
    bareFetch: async () => fakeChallengeResp(11000),
    payingFetch: async () => ({ status: 200, headers: { get: () => undefined }, json: async () => ({ results: [] }) }),
    now: () => new Date("2026-07-18T00:00:00Z"),
  });
  const res = fakeRes();
  await handler(fakeReq({ q: "test" }), res);
  assert.equal(res.statusCode, 200);
  assert.deepEqual(paid, { date: "2026-07-18", spentUsd: 0.011 });
});

test("resaleHandler: missing query rejects before touching any guard", async () => {
  let calls = 0;
  const handler = makeResaleHandler({ getBalanceUsd: async () => { calls++; return 5; } });
  const res = fakeRes();
  await handler(fakeReq({}), res);
  assert.equal(res.statusCode, 400);
  assert.equal(calls, 0);
});
