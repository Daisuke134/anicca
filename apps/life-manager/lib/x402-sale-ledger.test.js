"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { saleLedgerEntry, recordX402Sale } = require("./x402-sale-ledger.js");

const PAY_TO = "0x810f6d61f7606deee2657d3083e150a222bc29c5";
const PAYER = "0x1111111111111111111111111111111111111111";
const TX = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";

function sale(overrides = {}) {
  return {
    source: "the402",
    source_sale_id: "the402:order-42",
    offer_id: "forecast/weekly",
    tx: TX,
    block: 34123456,
    from: PAYER,
    to: PAY_TO,
    payTo: PAY_TO,
    usdc: 0.5,
    usdc_atomic: "500000",
    finalized: true,
    status: "success",
    external: true,
    observed_at: "2026-07-27T13:31:59.000Z",
    ...overrides,
  };
}

const boundary = {
  ownedPayTos: [PAY_TO],
  selfWallets: [
    PAY_TO,
    "0x2222222222222222222222222222222222222222",
  ],
};

test("an exact-cent verified external sale maps to one deterministic public ledger row", () => {
  const row = saleLedgerEntry(sale(), boundary);

  assert.equal(row.entry_key, `x402:${TX}:income`);
  assert.equal(row.wallet_address, "0x810F6D61F7606dEEE2657d3083E150a222Bc29C5");
  assert.equal(row.kind, "financial_external_income");
  assert.equal(row.amount_minor, 50);
  assert.equal(row.currency, "USD");
  assert.equal(row.occurred_at, "2026-07-27T13:31:59.000Z");
  assert.equal(row.tx_hash, TX);
  assert.equal(row.source, "x402_sale");
  assert.deepEqual(row.meta, {
    protocol: "x402",
    network: "eip155:8453",
    marketplace: "the402",
    source_sale_id: "the402:order-42",
    offer_id: "forecast/weekly",
    receipt_block: 34123456,
    payer: PAYER,
    pay_to: PAY_TO,
    usdc_atomic: "500000",
    finalized: true,
    external: true,
  });
  assert.ok(Object.isFrozen(row));
});

test("the runtime validates first and delegates exactly one deterministic entry", async () => {
  const calls = [];
  const result = await recordX402Sale(sale(), {
    ...boundary,
    recordEntry: async (entry) => {
      calls.push(entry);
      return { ok: true, duplicate: true, entry_key: entry.entry_key };
    },
  });

  assert.equal(calls.length, 1);
  assert.equal(calls[0].entry_key, `x402:${TX}:income`);
  assert.deepEqual(result, {
    ok: true,
    duplicate: true,
    entry_key: `x402:${TX}:income`,
  });
});

test("source provenance, identifiers, and owned receiver are mandatory", () => {
  assert.throws(() => saleLedgerEntry(sale({ source: "manual" }), boundary), /source/i);
  assert.throws(() => saleLedgerEntry(sale({ source_sale_id: "../bad" }), boundary), /sale.*id/i);
  assert.throws(() => saleLedgerEntry(sale({ offer_id: "bad offer" }), boundary), /offer/i);
  assert.throws(() => saleLedgerEntry(sale({ payTo: PAYER, to: PAYER }), boundary), /owned|payTo/i);
  assert.throws(() => saleLedgerEntry(sale({ to: PAYER }), boundary), /receiver|payTo|match/i);
});

test("only finalized successful externally classified rows can become income", () => {
  assert.throws(() => saleLedgerEntry(sale({ finalized: false }), boundary), /finalized/i);
  assert.throws(() => saleLedgerEntry(sale({ status: "failed" }), boundary), /success/i);
  assert.throws(() => saleLedgerEntry(sale({ external: false }), boundary), /external/i);
  assert.throws(() => saleLedgerEntry(sale({ block: -1 }), boundary), /block/i);
});

test("payer and owned wallet boundaries reject every self-pay form", () => {
  assert.throws(() => saleLedgerEntry(sale({ from: PAY_TO }), boundary), /self|payer/i);
  assert.throws(() => saleLedgerEntry(sale({
    from: "0x2222222222222222222222222222222222222222",
  }), boundary), /self|payer/i);
  assert.throws(() => saleLedgerEntry(sale(), {
    ownedPayTos: [PAY_TO],
    selfWallets: [PAYER],
  }), /self|payer/i);
});

test("transaction, address, timestamp, and atomic value syntax fail closed", () => {
  assert.throws(() => saleLedgerEntry(sale({ tx: "0x1234" }), boundary), /transaction|hash/i);
  assert.throws(() => saleLedgerEntry(sale({ from: "0x1234" }), boundary), /payer|address/i);
  assert.throws(() => saleLedgerEntry(sale({ observed_at: "later" }), boundary), /timestamp|observed/i);
  assert.throws(() => saleLedgerEntry(sale({ usdc_atomic: 500000 }), boundary), /string|atomic/i);
  assert.throws(() => saleLedgerEntry(sale({ usdc_atomic: "0" }), boundary), /positive|amount/i);
});

test("sub-cent sales stay evidence but are never rounded into the cent ledger", () => {
  assert.throws(() => saleLedgerEntry(sale({
    usdc: 0.001,
    usdc_atomic: "1000",
  }), boundary), /exact.*minor|exact.*cent|minor unit/i);
});

test("validation completes before a database write can happen", async () => {
  let calls = 0;
  await assert.rejects(() => recordX402Sale(sale({ external: false }), {
    ...boundary,
    recordEntry: async () => {
      calls += 1;
      return { ok: true };
    },
  }), /external/i);
  assert.equal(calls, 0);
});
