"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { cycleLedgerEntries } = require("./polymarket-cycle.js");

const CONDITION = "0x5ecd0d050ea3e753b787ad8ef3b023448b78d232ebe28b24b3d18bf878fb8b5d";
const WALLET = "0x904B50d2e214Da947d83D6a2D32c4E3Ffc17Eb74";
const TRADE_TX = "0xe6bbfb7d610a774f4548af9393930e99039f0a33f6aaeae34d7fe1f240321659";
const REDEEM_TX = "0xdfaf37b33da21da10ba0398ccbe4e853d8111e2867606a4c81b85acc454086ef";

function cycle(overrides = {}) {
  return {
    cycle_id: `polymarket:${CONDITION}`,
    wallet_address: WALLET,
    condition_id: CONDITION,
    deployed_microusd: "3150000",
    recovered_microusd: "0",
    fee_microusd: "0",
    realized_pnl_microusd: "-3150000",
    occurred_at: "2026-07-27T04:05:43.000Z",
    trade_tx_hash: TRADE_TX,
    redeem_tx_hash: REDEEM_TX,
    receipt_status: "0x1",
    evidence: {
      clob_status: "CONFIRMED",
      trader_side: "MAKER",
      fee_rate_bps: "0",
      receipt_block: "0x56bbccc",
    },
    ...overrides,
  };
}

test("the real losing cycle becomes one loss row with all four exact components", () => {
  const rows = cycleLedgerEntries(cycle());

  assert.equal(rows.length, 1);
  assert.equal(rows[0].entry_key, `polymarket:${CONDITION}:loss`);
  assert.equal(rows[0].kind, "financial_realized_loss");
  assert.equal(rows[0].amount_minor, 315);
  assert.equal(rows[0].tx_hash, REDEEM_TX);
  assert.deepEqual({
    deployed: rows[0].meta.deployed_microusd,
    recovered: rows[0].meta.recovered_microusd,
    fee: rows[0].meta.fee_microusd,
    realized: rows[0].meta.realized_pnl_microusd,
  }, {
    deployed: "3150000",
    recovered: "0",
    fee: "0",
    realized: "-3150000",
  });
  assert.equal(rows[0].meta.trade_tx_hash, TRADE_TX);
  assert.equal(rows[0].meta.redeem_tx_hash, REDEEM_TX);
  assert.ok(Object.isFrozen(rows[0]));
});

test("only the gain above returned principal is income, and fees stay separate", () => {
  const rows = cycleLedgerEntries(cycle({
    deployed_microusd: "5000000",
    recovered_microusd: "6000000",
    fee_microusd: "10000",
    realized_pnl_microusd: "990000",
  }));

  assert.deepEqual(rows.map((row) => ({
    key: row.entry_key,
    kind: row.kind,
    amount: row.amount_minor,
  })), [
    {
      key: `polymarket:${CONDITION}:income`,
      kind: "financial_external_income",
      amount: 100,
    },
    {
      key: `polymarket:${CONDITION}:fee`,
      kind: "financial_fee",
      amount: 1,
    },
  ]);
  assert.notEqual(rows[0].amount_minor, 600, "the recovered $6 principal must not be called revenue");
});

test("a flat cycle with a fee emits only the fee", () => {
  const rows = cycleLedgerEntries(cycle({
    deployed_microusd: "5000000",
    recovered_microusd: "5000000",
    fee_microusd: "20000",
    realized_pnl_microusd: "-20000",
  }));

  assert.deepEqual(rows.map((row) => [row.kind, row.amount_minor]), [
    ["financial_fee", 2],
  ]);
});

test("cycle money must be exact decimal strings and satisfy the accounting identity", () => {
  assert.throws(() => cycleLedgerEntries(cycle({ deployed_microusd: 3150000 })), /string|money/i);
  assert.throws(() => cycleLedgerEntries(cycle({ recovered_microusd: "1.5" })), /integer|micro/i);
  assert.throws(() => cycleLedgerEntries(cycle({ fee_microusd: "-1" })), /fee|negative/i);
  assert.throws(() => cycleLedgerEntries(cycle({ realized_pnl_microusd: "-3140000" })), /formula|realized/i);
});

test("fractional-cent economic rows are refused instead of rounded", () => {
  assert.throws(() => cycleLedgerEntries(cycle({
    deployed_microusd: "5000000",
    recovered_microusd: "5000001",
    fee_microusd: "0",
    realized_pnl_microusd: "1",
  })), /exact.*cent|cent/i);
  assert.throws(() => cycleLedgerEntries(cycle({
    deployed_microusd: "5000000",
    recovered_microusd: "5000000",
    fee_microusd: "1",
    realized_pnl_microusd: "-1",
  })), /exact.*cent|cent/i);
});

test("invalid public evidence and nested secrets fail before a ledger row exists", () => {
  assert.throws(() => cycleLedgerEntries(cycle({ wallet_address: WALLET.toLowerCase() })), /checksum/i);
  assert.throws(() => cycleLedgerEntries(cycle({ condition_id: "0x1234" })), /condition/i);
  assert.throws(() => cycleLedgerEntries(cycle({ cycle_id: "polymarket:wrong" })), /cycle_id/i);
  assert.throws(() => cycleLedgerEntries(cycle({ trade_tx_hash: "0x1234" })), /transaction|hash/i);
  assert.throws(() => cycleLedgerEntries(cycle({ redeem_tx_hash: "0x1234" })), /transaction|hash/i);
  assert.throws(() => cycleLedgerEntries(cycle({ receipt_status: "0x0" })), /receipt/i);
  assert.throws(() => cycleLedgerEntries(cycle({
    evidence: { nested: { private_key: "do-not-store" } },
  })), /secret/i);
});
