"use strict";
// FIN-c — the production leg: the earn loop's revenue reaching the ledger, and the month coming back
// out of it as the message the user actually reads.
//
// The failure this guards against is a report that looks complete while resting on something nobody
// measured. So: an invalid row must never reach the database, a retry must not book twice, and a
// balance we could not read must abort the report rather than be filled in with a plausible number.

const assert = require("node:assert/strict");
const test = require("node:test");

const { recordEarnLoopRevenue, readMonthRows, generateMonthlyReport } = require("./earnings-runtime.js");

const WALLET = "0x477EeE969ccfdc0e959F38cE8B83e372FC0262ad";
const SUPA = { supaUrl: "https://db.example", supaKey: "service-key" };

function fetchStub(handler) {
  const calls = [];
  const impl = async (url, init) => {
    calls.push({ url: String(url), init: init || {} });
    return handler(String(url), init || {}, calls.length);
  };
  impl.calls = calls;
  return impl;
}

function ok(body, headers = {}) {
  return {
    ok: true,
    status: 200,
    headers: { get: (key) => headers[String(key).toLowerCase()] || null },
    json: async () => body,
  };
}

test("a valid revenue row is posted to the earnings table with the wallet attached", async () => {
  const fetchImpl = fetchStub(() => ok(null));
  const result = await recordEarnLoopRevenue({
    entry_key: "earn-loop:2026-07-25:001",
    wallet_address: WALLET,
    kind: "financial_external_income",
    amount_minor: 12430,
    currency: "USD",
    occurred_at: "2026-07-25T04:00:00.000Z",
    tx_hash: `0x${"c".repeat(64)}`,
  }, { ...SUPA, fetchImpl });

  assert.equal(result.ok, true);
  assert.equal(result.duplicate, false);
  assert.equal(fetchImpl.calls.length, 1);
  assert.match(fetchImpl.calls[0].url, /\/rest\/v1\/lm_agent_earnings$/);
  const body = JSON.parse(fetchImpl.calls[0].init.body);
  assert.equal(body.wallet_address, WALLET);
  assert.equal(body.amount_minor, 12430);
  assert.equal(body.kind, "financial_external_income");
});

test("an invalid row never reaches the database — it is refused before the request", async () => {
  const fetchImpl = fetchStub(() => ok(null));
  await assert.rejects(() => recordEarnLoopRevenue({
    entry_key: "bad",
    wallet_address: WALLET,
    kind: "financial_external_income",
    amount_minor: 124.305,
    currency: "USD",
    occurred_at: "2026-07-25T04:00:00.000Z",
  }, { ...SUPA, fetchImpl }), /amount/i);
  assert.equal(fetchImpl.calls.length, 0, "a bad number must not be written and then explained away");
});

test("a private key attached to a revenue row aborts the write instead of being persisted", async () => {
  const fetchImpl = fetchStub(() => ok(null));
  await assert.rejects(() => recordEarnLoopRevenue({
    entry_key: "leak",
    wallet_address: WALLET,
    kind: "financial_external_income",
    amount_minor: 100,
    currency: "USD",
    occurred_at: "2026-07-25T04:00:00.000Z",
    privateKey: "ab".repeat(32),
  }, { ...SUPA, fetchImpl }), /secret/i);
  assert.equal(fetchImpl.calls.length, 0);
});

test("a retry of the same entry key is reported as already recorded, not as new revenue", async () => {
  const fetchImpl = fetchStub(() => ({
    ok: false,
    status: 409,
    headers: { get: () => null },
    json: async () => ({ code: "23505" }),
  }));
  const result = await recordEarnLoopRevenue({
    entry_key: "earn-loop:2026-07-25:001",
    wallet_address: WALLET,
    kind: "financial_external_income",
    amount_minor: 12430,
    currency: "USD",
    occurred_at: "2026-07-25T04:00:00.000Z",
  }, { ...SUPA, fetchImpl });

  assert.equal(result.ok, true);
  assert.equal(result.duplicate, true);
});

test("a database refusal is surfaced, never swallowed into a false success", async () => {
  const fetchImpl = fetchStub(() => ({ ok: false, status: 500, headers: { get: () => null }, json: async () => ({}) }));
  await assert.rejects(() => recordEarnLoopRevenue({
    entry_key: "boom",
    wallet_address: WALLET,
    kind: "financial_external_income",
    amount_minor: 100,
    currency: "USD",
    occurred_at: "2026-07-25T04:00:00.000Z",
  }, { ...SUPA, fetchImpl }), /500/);
});

test("the month query asks the database for exactly the month, half-open, for this wallet only", async () => {
  const fetchImpl = fetchStub(() => ok([]));
  await readMonthRows({ year: 2026, month: 7, timezone: "Asia/Tokyo", walletAddress: WALLET }, { ...SUPA, fetchImpl });

  const url = fetchImpl.calls[0].url;
  assert.match(url, /wallet_address=eq\./);
  assert.ok(url.includes(encodeURIComponent("2026-06-30T15:00:00.000Z")), "month starts at the Tokyo boundary");
  assert.ok(url.includes(encodeURIComponent("2026-07-31T15:00:00.000Z")), "and ends half-open at the next one");
  assert.match(url, /occurred_at=gte\./);
  assert.match(url, /occurred_at=lt\./);
});

test("the whole month becomes the 9.11 message, from real rows and a real balance", async () => {
  const rows = [
    { entry_key: "a", wallet_address: WALLET, kind: "financial_external_income", amount_minor: 12430, currency: "USD", occurred_at: "2026-07-10T04:00:00.000Z" },
    { entry_key: "b", wallet_address: WALLET, kind: "financial_fee", amount_minor: 820, currency: "USD", occurred_at: "2026-07-11T04:00:00.000Z" },
    { entry_key: "c", wallet_address: WALLET, kind: "financial_user_transfer", amount_minor: 10000, currency: "USD", occurred_at: "2026-07-12T04:00:00.000Z" },
  ];
  const fetchImpl = fetchStub(() => ok(rows));

  const report = await generateMonthlyReport({
    year: 2026, month: 7, timezone: "Asia/Tokyo", walletAddress: WALLET,
    readBalanceMinor: async () => 20350,
  }, { ...SUPA, fetchImpl });

  assert.equal(report.summary.net_minor, 11610);
  assert.equal(report.text, [
    "💰 今月の収支報告です。",
    "・私のwalletでの収益: +$124.30",
    "・あなたへの送金: $100.00（送金済み）",
    "・手数料・実費: $8.20",
    "・私の残高: $203.50",
    "取引はすべてこちらで確認できます: basescan.org/address/0x477E…62ad",
  ].join("\n"));
});

test("the monthly runtime preserves a measured six-decimal pUSD balance", async () => {
  const fetchImpl = fetchStub(() => ok([]));
  const report = await generateMonthlyReport({
    year: 2026, month: 7, timezone: "Asia/Tokyo", walletAddress: WALLET,
    readBalanceAtomic: async () => "4422182",
    balanceDecimals: 6,
    explorerBaseUrl: "polygonscan.com",
  }, { ...SUPA, fetchImpl });

  assert.equal(report.summary.balance_minor, null);
  assert.equal(report.summary.balance_atomic, "4422182");
  assert.equal(report.summary.balance_decimals, 6);
  assert.match(report.text, /・私の残高: \$4\.422182/);
  assert.match(report.text, /polygonscan\.com\/address\/0x477E…62ad/);
});

test("the monthly runtime refuses ambiguous balance readers", async () => {
  const fetchImpl = fetchStub(() => ok([]));
  await assert.rejects(() => generateMonthlyReport({
    year: 2026, month: 7, timezone: "Asia/Tokyo", walletAddress: WALLET,
    readBalanceMinor: async () => 442,
    readBalanceAtomic: async () => "4422182",
    balanceDecimals: 6,
  }, { ...SUPA, fetchImpl }), /balance/i);

  await assert.rejects(() => generateMonthlyReport({
    year: 2026, month: 7, timezone: "Asia/Tokyo", walletAddress: WALLET,
    readBalanceAtomic: async () => "4422182",
  }, { ...SUPA, fetchImpl }), /decimals/i);
});

test("a losing month still produces a report, with the loss copy", async () => {
  const rows = [
    { entry_key: "a", wallet_address: WALLET, kind: "financial_external_income", amount_minor: 800, currency: "USD", occurred_at: "2026-07-10T04:00:00.000Z" },
    { entry_key: "b", wallet_address: WALLET, kind: "financial_realized_loss", amount_minor: 2040, currency: "USD", occurred_at: "2026-07-11T04:00:00.000Z" },
  ];
  const fetchImpl = fetchStub(() => ok(rows));

  const report = await generateMonthlyReport({
    year: 2026, month: 7, timezone: "Asia/Tokyo", walletAddress: WALLET,
    readBalanceMinor: async () => 19110,
    cause: "試行の当たりが薄かったこと", plan: "単価の高い依頼だけに絞ること",
  }, { ...SUPA, fetchImpl });

  assert.equal(report.summary.is_loss, true);
  assert.match(report.text, /・収益: -\$12\.40（マイナスでした）/);
  assert.match(report.text, /・送金: なし（利益が出た月のみ送金します）/);
});

test("a balance we could not measure aborts the report rather than filling in a plausible number", async () => {
  const fetchImpl = fetchStub(() => ok([]));
  await assert.rejects(() => generateMonthlyReport({
    year: 2026, month: 7, timezone: "Asia/Tokyo", walletAddress: WALLET,
    readBalanceMinor: async () => { throw new Error("rpc down"); },
  }, { ...SUPA, fetchImpl }), /balance/i);

  await assert.rejects(() => generateMonthlyReport({
    year: 2026, month: 7, timezone: "Asia/Tokyo", walletAddress: WALLET,
    readBalanceMinor: async () => null,
  }, { ...SUPA, fetchImpl }), /balance/i);
});

test("an unreadable ledger aborts the report — an empty month and an unread month are not the same", async () => {
  const fetchImpl = fetchStub(() => ({ ok: false, status: 503, headers: { get: () => null }, json: async () => ({}) }));
  await assert.rejects(() => generateMonthlyReport({
    year: 2026, month: 7, timezone: "Asia/Tokyo", walletAddress: WALLET,
    readBalanceMinor: async () => 0,
  }, { ...SUPA, fetchImpl }), /503/);
});

test("a month with no rows at all is reported honestly as zero", async () => {
  const fetchImpl = fetchStub(() => ok([]));
  const report = await generateMonthlyReport({
    year: 2026, month: 7, timezone: "Asia/Tokyo", walletAddress: WALLET,
    readBalanceMinor: async () => 0,
  }, { ...SUPA, fetchImpl });

  assert.equal(report.summary.gross_income_minor, 0);
  assert.equal(report.summary.counted_rows, 0);
  assert.match(report.text, /・私のwalletでの収益: \+\$0\.00/);
  assert.match(report.text, /・私の残高: \$0\.00/);
});
