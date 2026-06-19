import { test } from "node:test";
import assert from "node:assert/strict";
import { makeGmoAdapter, buildSubmittedPatch, buildClaimPatch, buildReleasePatch, claimedFromRows, claimWith, parseRef, parseClaimedAt, reconcileStuck, idempotencyKey, pollCompletions, todayYmd } from "../bank-payout-watcher.mjs";
import { parseBankRecipient } from "../lib/bank-recipients.mjs";

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

test("FIND-109: release restores original notes (strips claimed_at) so a skipped recipient stays payable", () => {
  const raw = "method=bank;country=jp;bankCode=0005;branchCode=001;accountType=1;accountNumber=1234567;beneficiaryName=ﾀﾅｶ ﾀﾛｳ";
  const patch = buildReleasePatch(raw);
  assert.deepEqual(patch, { status: "queued", notes: raw }); // claimed_at gone -> clean
  assert.ok(parseBankRecipient({ id: "x", notes: patch.notes })); // re-dispatchable on a later pass (no guard hit)
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

test("FIND-100 pollCompletions: completed->paid, failed->needs_review (NEVER auto-requeue), else pending", async () => {
  const paid = [], review = [];
  const out = await pollCompletions({
    readSubmitted: async () => [{ id: "a", ref: "R1" }, { id: "b", ref: "R2" }, { id: "c", ref: "R3" }],
    queryStatus: async (ref) => ({ R1: "completed", R2: "failed", R3: "processing" }[ref]),
    markPaid: async (id) => paid.push(id),
    flagNeedsReview: async (id) => review.push(id),
  });
  assert.deepEqual(out.done, ["a"]);
  assert.deepEqual(out.review, ["b"]); // failed -> review, NOT re-queued (no auto-resend of irreversible money)
  assert.deepEqual(out.pending, ["c"]);
  assert.deepEqual(paid, ["a"]);
  assert.deepEqual(review, ["b"]);
});

test("FIND-101 parseClaimedAt: extracts claimed_at from notes; null when absent", () => {
  assert.equal(parseClaimedAt("method=bank;country=jp;bankCode=0005;claimed_at=2026-06-19T10:00:00.000Z"), "2026-06-19T10:00:00.000Z");
  assert.equal(parseClaimedAt("method=bank;country=jp"), null);
});

test("FIND-103: reconcileStuck flags NULL/unparseable claimed_at processing rows (anomalous, not dropped)", async () => {
  const flagged = [];
  const out = await reconcileStuck({
    readProcessing: async () => [{ id: "nots", ts: null }, { id: "bad", ts: "not-a-date" }],
    flagNeedsReview: async (id) => flagged.push(id),
    now: 1_000_000_000_000,
  });
  assert.deepEqual(out.flagged.sort(), ["bad", "nots"]); // both flagged, neither silently dropped
});

test("FIND-105 seam: a submitted row (ref=) is REFUSED by parseBankRecipient (no auto-redispatch) yet ref stays pollable", () => {
  const raw = "method=bank;country=jp;bankCode=0005;branchCode=001;accountType=2;accountNumber=1234567;beneficiaryName=ﾀﾅｶ ﾀﾛｳ;claimed_at=2026-06-20T00:00:00.000Z";
  const patch = buildSubmittedPatch({ provider: "gmo", amount: 19870, currency: "JPY", res: { apptransferNo: "G1" }, raw });
  assert.equal(patch.status, "submitted");
  assert.equal(parseRef(patch.notes), "G1");                              // completion poll still finds the ref
  assert.equal(parseBankRecipient({ id: "u1", notes: patch.notes }), null); // FIND-105: ref= => refused, never re-dispatched (no double-pay)
  assert.ok(/bankCode=0005/.test(patch.notes));                           // bank fields preserved textually for operator audit
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
