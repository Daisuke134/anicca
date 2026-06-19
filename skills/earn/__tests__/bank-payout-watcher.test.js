import { test } from "node:test";
import assert from "node:assert/strict";
import { makeGmoAdapter, buildPaidPatch, todayYmd } from "../bank-payout-watcher.mjs";

test("makeGmoAdapter: builds the GMO BulkTransfer request from fan-out transfers + calls submit with the token", async () => {
  let captured = null;
  const submit = async (req, token) => { captured = { req, token }; return { apptransferNo: "G1" }; };
  const adapter = makeGmoAdapter({ accountId: "A1", remitterName: "ﾃｽﾄ", transferDesignatedDate: "20260620", token: "TKN", submit });
  const res = await adapter([
    { to: "u1", amount: 20000, currency: "JPY", bank: { bankCode: "0005", branchCode: "001", accountNumber: "1234567", beneficiaryName: "ﾀﾅｶ ﾀﾛｳ" } },
  ]);
  assert.equal(res.apptransferNo, "G1");
  assert.equal(captured.token, "TKN");
  assert.equal(captured.req.accountId, "A1");
  assert.equal(captured.req.totalAmount, "20000");
  assert.equal(captured.req.bulkTransfers[0].beneficiaryBankCode, "0005");
  assert.equal(captured.req.bulkTransfers[0].transferAmount, "20000");
});

test("buildPaidPatch: marks status=paid with provider/amount/currency in notes", () => {
  assert.deepEqual(buildPaidPatch({ provider: "gmo", amount: 20000, currency: "JPY" }), {
    status: "paid", notes: "paid;provider=gmo;amount=20000;currency=JPY",
  });
});

test("todayYmd: formats YYYYMMDD (zero-padded)", () => {
  assert.equal(todayYmd(new Date(2026, 0, 5)), "20260105");
  assert.equal(todayYmd(new Date(2026, 11, 31)), "20261231");
});
