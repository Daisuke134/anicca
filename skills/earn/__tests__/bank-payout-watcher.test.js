import { test } from "node:test";
import assert from "node:assert/strict";
import { makeGmoAdapter, buildSubmittedPatch, buildClaimPatch, buildReleasePatch, claimedFromRows, idempotencyKey, pollCompletions, todayYmd } from "../bank-payout-watcher.mjs";

test("makeGmoAdapter: builds GMO request, stamps idempotency key, calls submit with token", async () => {
  let captured = null;
  const submit = async (req, token) => { captured = { req, token }; return { apptransferNo: "G1" }; };
  const adapter = makeGmoAdapter({ accountId: "A1", remitterName: "ﾃｽﾄ", transferDesignatedDate: "20260620", token: "TKN", submit });
  const res = await adapter([{ to: "u1", amount: 20000, currency: "JPY", bank: { bankCode: "0005", branchCode: "001", accountNumber: "1234567", beneficiaryName: "ﾀﾅｶ ﾀﾛｳ" } }]);
  assert.equal(res.apptransferNo, "G1");
  assert.equal(captured.token, "TKN");
  assert.equal(captured.req.totalAmount, "20000");
  assert.ok(captured.req.idempotencyKey && captured.req.idempotencyKey.startsWith("anicca-ubi-")); // FIND-B
});

test("buildSubmittedPatch: status=submitted (accepted≠完了) + persists ref (FIND-005)", () => {
  assert.deepEqual(buildSubmittedPatch({ provider: "gmo", amount: 20000, currency: "JPY", res: { apptransferNo: "G1" } }), {
    status: "submitted", notes: "submitted;provider=gmo;amount=20000;currency=JPY;ref=G1",
  });
});

test("claim/release patches", () => {
  assert.deepEqual(buildClaimPatch(), { status: "processing" });
  assert.deepEqual(buildReleasePatch(), { status: "queued" });
});

test("FIND-A claimedFromRows: 1 returned row = we won the CAS; 0 or >1 = not ours", () => {
  assert.equal(claimedFromRows([{ id: "a" }]), true);
  assert.equal(claimedFromRows([]), false);           // another pass already flipped it
  assert.equal(claimedFromRows(null), false);
  assert.equal(claimedFromRows([{}, {}]), false);
});

test("FIND-B idempotencyKey: deterministic + order-independent (same batch -> same key)", () => {
  const a = [{ to: "u1", amount: 100 }, { to: "u2", amount: 200 }];
  const b = [{ to: "u2", amount: 200 }, { to: "u1", amount: 100 }]; // reordered
  assert.equal(idempotencyKey(a), idempotencyKey(b));
  assert.notEqual(idempotencyKey(a), idempotencyKey([{ to: "u1", amount: 101 }, { to: "u2", amount: 200 }]));
});

test("FIND-D pollCompletions: completed->paid, failed->requeue, else pending", async () => {
  const paid = [], requeued = [];
  const out = await pollCompletions({
    readSubmitted: async () => [{ id: "a", ref: "R1" }, { id: "b", ref: "R2" }, { id: "c", ref: "R3" }],
    queryStatus: async (ref) => ({ R1: "completed", R2: "failed", R3: "processing" }[ref]),
    markPaid: async (id) => paid.push(id),
    requeue: async (id) => requeued.push(id),
  });
  assert.deepEqual(out.done, ["a"]);
  assert.deepEqual(out.failed, ["b"]);
  assert.deepEqual(out.pending, ["c"]);
  assert.deepEqual(paid, ["a"]);
  assert.deepEqual(requeued, ["b"]);
});

test("todayYmd: YYYYMMDD zero-padded", () => {
  assert.equal(todayYmd(new Date(2026, 0, 5)), "20260105");
});
