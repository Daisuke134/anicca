// Integration test: the WHOLE ③ JP bank chain composed (VCSDD — verify the system, not just units).
// recipients rows (income-signup notes format) → bankRecipientsFromRows(parseBankRecipient)
//   → bankWatcherPass(plan + dispatch) → makeGmoAdapter(buildBulkTransferRequest + submit)
//   → markPaid. Proves the pieces wire together end-to-end with mocked I/O (no live token/DB).
import { test } from "node:test";
import assert from "node:assert/strict";
import { bankWatcherPass } from "../bank-watcher.mjs";
import { bankRecipientsFromRows } from "../lib/bank-recipients.mjs";
import { makeGmoAdapter } from "../bank-payout-watcher.mjs";

const NOTES = (bc, acc, name) => `method=bank;country=jp;bankCode=${bc};branchCode=001;accountType=1;accountNumber=${acc};beneficiaryName=${name}`;

test("FULL CHAIN: queued JP bank rows → GMO bulk transfer + only valid recipients marked paid", async () => {
  // What income-signup wrote to Supabase recipients (mixed: 2 valid JP bank, 1 email, 1 incomplete).
  const rows = [
    { id: "r1", notes: NOTES("0005", "1234567", "ﾀﾅｶ ﾀﾛｳ") },
    { id: "r2", notes: "method=email;wallet=" },                     // ignored (not bank)
    { id: "r3", notes: NOTES("9900", "7654321", "ｻﾄｳ ﾊﾅｺ") },
    { id: "r4", notes: "method=bank;country=jp;bankCode=0005" },     // ignored (incomplete)
  ];

  let submitted = null;
  const submit = async (req, token) => { submitted = { req, token }; return { apptransferNo: "OK1" }; };
  const gmo = makeGmoAdapter({ accountId: "ACCT", remitterName: "ｱﾆﾂﾁﬔ", transferDesignatedDate: "20260620", token: "SANDBOX_TKN", submit });

  const marked = [];
  const out = await bankWatcherPass({
    readBankRecipients: async () => bankRecipientsFromRows(rows),
    getPool: async () => 40000,
    markPaid: async (id, info) => marked.push({ id, info }),
    adapters: { gmo },
    opts: { feePerTransfer: 130 },
  });

  // plan: 40000 pool, 2 recipients, fee 130 each → afterFees 39740 → per 19870
  assert.equal(out.outcome, "sent");
  assert.equal(submitted.token, "SANDBOX_TKN");
  assert.equal(submitted.req.accountId, "ACCT");
  assert.equal(submitted.req.totalCount, "2");
  assert.equal(submitted.req.bulkTransfers.length, 2);
  assert.equal(submitted.req.bulkTransfers[0].beneficiaryBankCode, "0005");
  assert.equal(submitted.req.bulkTransfers[0].transferAmount, "19870");
  assert.equal(submitted.req.bulkTransfers[1].beneficiaryBankCode, "9900");
  // only the 2 valid JP bank recipients marked paid (email + incomplete excluded)
  assert.deepEqual(marked.map((m) => m.id).sort(), ["r1", "r3"]);
  assert.equal(marked[0].info.amount, 19870);
});

test("FULL CHAIN: no valid bank rows → idle, GMO never called, nobody marked", async () => {
  let called = false;
  const gmo = makeGmoAdapter({ accountId: "A", remitterName: "X", transferDesignatedDate: "20260620", token: "T", submit: async () => { called = true; } });
  const out = await bankWatcherPass({
    readBankRecipients: async () => bankRecipientsFromRows([{ id: "e", notes: "method=email;wallet=" }]),
    getPool: async () => 40000,
    markPaid: async () => {},
    adapters: { gmo },
  });
  assert.equal(out.outcome, "idle");
  assert.equal(called, false);
});
