import { test } from "node:test";
import assert from "node:assert/strict";
import { makeGmoAdapter, buildSubmittedPatch, buildClaimPatch, buildReleasePatch, claimedFromRows, claimWith, parseRef, reconcileStuck, idempotencyKey, pollCompletions, todayYmd } from "../bank-payout-watcher.mjs";

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

test("FIND-004 claimWith CAS: only ids whose guarded PATCH returned exactly 1 row are claimed", async () => {
  // simulate the CAS: 'a' was queued (we flip it -> 1 row); 'b' already taken by a concurrent pass -> 0 rows.
  const patchQueued = async (id) => (id === "a" ? [{ id: "a", status: "processing" }] : []);
  const claimed = await claimWith(patchQueued, ["a", "b"]);
  assert.deepEqual(claimed, ["a"]); // 'b' not claimed -> never dispatched -> no double-pay
});

test("FIND-002 parseRef: extracts ref from notes; null when absent", () => {
  assert.equal(parseRef("submitted;provider=gmo;amount=20000;currency=JPY;ref=G1"), "G1");
  assert.equal(parseRef("method=email;wallet="), null);
});

test("FIND-003 reconcileStuck: flags only 'processing' rows older than threshold to needs_review", async () => {
  const flagged = [];
  const now = 1_000_000_000_000;
  const out = await reconcileStuck({
    readProcessing: async () => [
      { id: "old", ts: new Date(now - 3_600_000).toISOString() }, // 1h old -> flag
      { id: "fresh", ts: new Date(now - 60_000).toISOString() },  // 1m old -> keep (in-flight)
    ],
    flagNeedsReview: async (id) => flagged.push(id),
    olderThanMs: 1_800_000, // 30m
    now,
  });
  assert.deepEqual(out.flagged, ["old"]);
  assert.deepEqual(flagged, ["old"]);
});
