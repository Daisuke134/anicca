import { test } from "node:test";
import assert from "node:assert/strict";
import { buildBulkTransferRequest } from "../gmo-furikomi.mjs";

const tx = (amount, name = "ﾀﾅｶ ﾀﾛｳ") => ({ to: name, amount, bank: { bankCode: "0005", branchCode: "001", accountNumber: "1234567", beneficiaryName: name } });

test("buildBulkTransferRequest: maps fan-out transfers to GMO BulkTransfer payload (verified field names)", () => {
  const req = buildBulkTransferRequest({ accountId: "A1", remitterName: "ｱﾆﾂﾁﬔ", transferDesignatedDate: "20260620", transfers: [tx(20000), tx(30000, "ｻﾄｳ ﾊﾅｺ")] });
  assert.equal(req.accountId, "A1");
  assert.equal(req.totalCount, "2");
  assert.equal(req.totalAmount, "50000");
  assert.equal(req.bulkTransfers.length, 2);
  const d = req.bulkTransfers[0];
  assert.equal(d.itemId, "1");
  assert.equal(d.beneficiaryBankCode, "0005");
  assert.equal(d.beneficiaryBranchCode, "001");
  assert.equal(d.accountTypeCode, "1");        // default 普通
  assert.equal(d.accountNumber, "1234567");
  assert.equal(d.beneficiaryName, "ﾀﾅｶ ﾀﾛｳ");
  assert.equal(d.transferAmount, "20000");     // string per GMO
});

test("buildBulkTransferRequest: respects explicit accountTypeCode (当座=2)", () => {
  const t = tx(10000); t.bank.accountTypeCode = "2";
  const req = buildBulkTransferRequest({ accountId: "A1", remitterName: "X", transferDesignatedDate: "20260620", transfers: [t] });
  assert.equal(req.bulkTransfers[0].accountTypeCode, "2");
});

test("FIND-001 regression: accountType from parseBankRecipient flows to GMO accountTypeCode (not silently 普通)", () => {
  // parseBankRecipient emits bank.accountType (NOT accountTypeCode). Must not default to "1".
  const t = tx(10000); t.bank.accountType = "2"; // 当座, as a parsed recipient carries it
  delete t.bank.accountTypeCode;
  const req = buildBulkTransferRequest({ accountId: "A1", remitterName: "X", transferDesignatedDate: "20260620", transfers: [t] });
  assert.equal(req.bulkTransfers[0].accountTypeCode, "2"); // was "1" before the fix
});

test("buildBulkTransferRequest: throws on missing header fields", () => {
  assert.throws(() => buildBulkTransferRequest({ remitterName: "X", transferDesignatedDate: "20260620", transfers: [tx(1000)] }), /accountId/);
  assert.throws(() => buildBulkTransferRequest({ accountId: "A1", remitterName: "X", transferDesignatedDate: "20260620", transfers: [] }), /transfers required/);
});

test("buildBulkTransferRequest: throws on incomplete bank / bad amount", () => {
  assert.throws(() => buildBulkTransferRequest({ accountId: "A1", remitterName: "X", transferDesignatedDate: "20260620", transfers: [{ to: "u", amount: 1000, bank: { bankCode: "0005" } }] }), /missing bank fields/);
  assert.throws(() => buildBulkTransferRequest({ accountId: "A1", remitterName: "X", transferDesignatedDate: "20260620", transfers: [{ to: "u", amount: 0, bank: { bankCode: "0005", branchCode: "1", accountNumber: "1", beneficiaryName: "n" } }] }), /invalid amount/);
});
