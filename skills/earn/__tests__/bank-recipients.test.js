import { test } from "node:test";
import assert from "node:assert/strict";
import { parseBankRecipient, bankRecipientsFromRows } from "../lib/bank-recipients.mjs";

// EXACT notes string the landing _jp-bank.buildBankNotes produces (round-trip contract).
const NOTES = "method=bank;country=jp;bankCode=0005;branchCode=001;accountType=1;accountNumber=1234567;beneficiaryName=ﾀﾅｶ ﾀﾛｳ";

test("parseBankRecipient: round-trips the income-signup JP bank notes into a watcher recipient", () => {
  const r = parseBankRecipient({ id: "u1", notes: NOTES });
  assert.deepEqual(r, {
    id: "u1", provider: "gmo", currency: "JPY",
    bank: { bankCode: "0005", branchCode: "001", accountType: "1", accountNumber: "1234567", beneficiaryName: "ﾀﾅｶ ﾀﾛｳ" },
  });
});

test("parseBankRecipient: returns null for non-bank or incomplete rows", () => {
  assert.equal(parseBankRecipient({ id: "x", notes: "method=email;wallet=" }), null);
  assert.equal(parseBankRecipient({ id: "x", notes: "method=wallet;wallet=0xabc" }), null);
  assert.equal(parseBankRecipient({ id: "x", notes: "method=bank;country=jp;bankCode=0005" }), null); // missing fields
  assert.equal(parseBankRecipient({ id: "x", notes: "method=bank;country=us" }), null); // non-JP future rail
});

test("bankRecipientsFromRows: keeps only valid JP bank rows", () => {
  const rows = [
    { id: "a", notes: NOTES },
    { id: "b", notes: "method=email;wallet=" },
    { id: "c", notes: NOTES.replace("u1", "c") },
  ];
  const out = bankRecipientsFromRows(rows);
  assert.equal(out.length, 2);
  assert.deepEqual(out.map((r) => r.id), ["a", "c"]);
});
