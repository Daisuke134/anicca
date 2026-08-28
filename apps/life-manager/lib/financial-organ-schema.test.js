"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { validateFinancialRecord } = require("./financial-organ-schema.js");

test("accepts the four minimal financial records and rejects missing fields", () => {
  const common = { id: "r1", source_ref: "provider:r1", observed_at: "2026-01-01T00:00:00Z" };
  const rows = {
    account: { ...common, source: "moneytree", name: "bank", kind: "cash", balance_jpy: 1 },
    transaction: { ...common, account_id: "a1", amount_jpy: 1, occurred_at: "2026-01-01T00:00:00Z" },
    position: { ...common, account_id: "a1", name: "asset", value_jpy: 1 },
    liability: { ...common, name: "card", balance_jpy: 1 },
  };

  for (const [type, row] of Object.entries(rows)) {
    assert.equal(validateFinancialRecord(type, row), row);
  }
  assert.throws(() => validateFinancialRecord("account", { ...rows.account, balance_jpy: null }), /account\.balance_jpy is required/);
});
