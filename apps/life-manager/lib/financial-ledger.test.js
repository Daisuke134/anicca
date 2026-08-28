"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { summarizeTransactions } = require("./financial-ledger.js");

test("excludes both sides of an internal transfer", () => {
  assert.deepEqual(summarizeTransactions([
    { id: "t1", amount_jpy: -1000, transfer_id: "move-1" },
    { id: "t2", amount_jpy: 1000, transfer_id: "move-1" },
    { id: "income", amount_jpy: 500 },
    { id: "spend", amount_jpy: -200 },
  ]), { income_jpy: 500, spending_jpy: 200, net_jpy: 300, excluded_transfer_rows: 2 });
});
