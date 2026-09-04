"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  buildAlpacaPublicProjection,
  fetchAlpacaPublicProjection,
  publishAlpacaPublicProjection,
  resolveAlpacaPublicProjection,
} = require("./alpaca-public.js");

const SUPA = {
  supaUrl: "https://db.example",
  supaKey: "service-role-key",
};
const UPDATED_AT = "2026-09-04T12:34:56.000Z";

const INPUT = {
  observation: {
    clock: { observed_at: "2026-09-04T12:30:00.000Z" },
    account: {
      account_id: "acct-must-not-leave-local-state",
      api_key: "broker-secret",
      cash: 98_500.25,
      equity: 100_250.5,
      last_equity: 100_000,
      raw_prompt: "private model prompt",
    },
    open_and_closed_orders_count: 2,
    raw_error: "private provider error",
  },
  campaign: {
    observed_at: "2026-09-04T12:30:00.000Z",
    realized_pnl_usd: 125,
    unrealized_pnl_usd: 125.5,
    positions: [{
      symbol: "AAPL",
      side: "long",
      qty: 2,
      average_entry_price: 200,
      current_price: 210.25,
      market_value: 420.5,
      unrealized_pl: 20.5,
      broker_order_id: "broker-order-secret",
    }],
    fills: [{
      id: "fill-secret",
      symbol: "AAPL",
      side: "buy",
      qty: 2,
      price: 200,
      transaction_time: "2026-09-04T12:31:00.000Z",
    }],
    raw_error: "private campaign error",
  },
  decision: {
    candidate_ref: "candidate-aapl",
    gate: "approved",
    approved: true,
    probability_profit: 0.7,
    expected_gain_usd: 12.345,
    reason: "bounded paper decision",
    observed_at: "2026-09-04T12:30:00.000Z",
    raw_prompt: "private decision prompt",
  },
  telegram: { status: "delivered", bot_token: "telegram-secret" },
  receipts: [{
    receipt_type: "outcome",
    status: "filled",
    effect_id: "effect-secret",
    recorded_at: "2026-09-04T12:32:00.000Z",
  }],
};

function jsonResponse(body, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  };
}

test("publisher upserts only the existing redacted projection", async () => {
  const calls = [];
  const fetchImpl = async (url, init) => {
    calls.push({ url, init });
    return jsonResponse([{ id: "alpaca-hackathon", projection: buildAlpacaPublicProjection(INPUT) }], 201);
  };
  const expected = buildAlpacaPublicProjection(INPUT);

  const result = await publishAlpacaPublicProjection({
    ...INPUT,
    ...SUPA,
    fetchImpl,
    now: UPDATED_AT,
  });

  assert.deepEqual(result, expected);
  assert.equal(calls.length, 1);
  assert.equal(
    calls[0].url,
    "https://db.example/rest/v1/lm_alpaca_public_snapshot?on_conflict=id",
  );
  assert.equal(calls[0].init.method, "POST");
  assert.equal(calls[0].init.headers.apikey, SUPA.supaKey);
  assert.equal(calls[0].init.headers.Authorization, `Bearer ${SUPA.supaKey}`);
  assert.match(calls[0].init.headers.Prefer, /resolution=merge-duplicates/);

  const body = JSON.parse(calls[0].init.body);
  assert.deepEqual(Object.keys(body).sort(), ["id", "observed_at", "projection", "updated_at"]);
  assert.equal(body.id, "alpaca-hackathon");
  assert.equal(body.observed_at, expected.observed_at);
  assert.equal(body.updated_at, UPDATED_AT);
  assert.deepEqual(body.projection, expected);
  assert.doesNotMatch(calls[0].init.body, /acct-must-not-leave-local-state|broker-secret|private model prompt|private provider error|telegram-secret|broker-order-secret/);
});

test("reader returns the redacted projection from the single durable row", async () => {
  const expected = buildAlpacaPublicProjection(INPUT);
  const calls = [];
  const fetchImpl = async (url, init) => {
    calls.push({ url, init });
    return jsonResponse([{
      id: "alpaca-hackathon",
      projection: expected,
      observed_at: expected.observed_at,
      updated_at: UPDATED_AT,
    }]);
  };

  const result = await fetchAlpacaPublicProjection({ ...SUPA, fetchImpl });

  assert.deepEqual(result, expected);
  assert.equal(calls.length, 1);
  assert.equal(
    calls[0].url,
    "https://db.example/rest/v1/lm_alpaca_public_snapshot?id=eq.alpaca-hackathon&select=projection&limit=1",
  );
  assert.equal(calls[0].init.headers.apikey, SUPA.supaKey);
  assert.equal(calls[0].init.headers.Authorization, `Bearer ${SUPA.supaKey}`);
});

test("resolver prefers observed local state and otherwise reads the durable row", async () => {
  const local = { paper: true, observed_at: UPDATED_AT };
  let calls = 0;
  assert.equal(await resolveAlpacaPublicProjection({
    buildLocal: () => local,
    ...SUPA,
    fetchImpl: async () => { calls += 1; return jsonResponse([]); },
  }), local);
  assert.equal(calls, 0);

  const remote = buildAlpacaPublicProjection(INPUT);
  const result = await resolveAlpacaPublicProjection({
    buildLocal: () => ({ paper: true, observed_at: null }),
    ...SUPA,
    fetchImpl: async () => { calls += 1; return jsonResponse([{ projection: remote }]); },
  });
  assert.deepEqual(result, remote);
  assert.equal(calls, 1);
});
