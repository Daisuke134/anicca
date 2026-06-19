import { test } from "node:test";
import assert from "node:assert/strict";
import { parseBankRecipient, bankRecipientsFromRows } from "../lib/bank-recipients.mjs";

// EXACT notes string the landing _jp-bank.buildBankNotes produces (round-trip contract).
const NOTES = "method=bank;country=jp;bankCode=0005;branchCode=001;accountType=1;accountNumber=1234567;beneficiaryName=ﾀﾅｶ ﾀﾛｳ";

test("parseBankRecipient: round-trips the income-signup JP bank notes into a watcher recipient", () => {
  const r = parseBankRecipient({ id: "u1", notes: NOTES });
  assert.deepEqual(r, {
    id: "u1", provider: "gmo", currency: "JPY", raw: NOTES,
    bank: { bankCode: "0005", branchCode: "001", accountType: "1", accountNumber: "1234567", beneficiaryName: "ﾀﾅｶ ﾀﾛｳ" },
  });
});

test("parseBankRecipient: returns null for non-bank or incomplete rows", () => {
  assert.equal(parseBankRecipient({ id: "x", notes: "method=email;wallet=" }), null);
  assert.equal(parseBankRecipient({ id: "x", notes: "method=wallet;wallet=0xabc" }), null);
  assert.equal(parseBankRecipient({ id: "x", notes: "method=bank;country=jp;bankCode=0005" }), null); // missing fields
  assert.equal(parseBankRecipient({ id: "x", notes: "method=bank;country=us" }), null); // non-JP future rail
});

test("FIND-105: an already-submitted row (carries ref=) is REFUSED even with full valid bank fields (no double-pay)", () => {
  const submitted = NOTES + ";submitted;provider=gmo;amount=19870;currency=JPY;ref=G1";
  assert.equal(parseBankRecipient({ id: "x", notes: submitted }), null); // ref= present => never auto-redispatched
  // sanity: WITHOUT the ref it would parse (so the guard is the ref, not the extra tokens)
  assert.ok(parseBankRecipient({ id: "x", notes: NOTES }));
});

test("FIND-107: a submitted-but-unrecorded row (claimed_at, NO ref=) is REFUSED — closes the FIND-007 requeue double-pay", () => {
  // The dangerous case: adapter sent the money but markPaid failed, so notes carry claimed_at but no ref.
  const claimedNoRef = NOTES + ";claimed_at=2026-06-20T00:00:00.000Z";
  assert.equal(parseBankRecipient({ id: "x", notes: claimedNoRef }), null); // never auto-redispatched on operator requeue
  assert.ok(parseBankRecipient({ id: "x", notes: NOTES })); // a fresh, never-claimed signup row still dispatches once
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
