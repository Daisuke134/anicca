const { test } = require("node:test");
const assert = require("node:assert");
const { nextChildId, buildChildSpec } = require("../child-spec");

test("nextChildId starts at 001 on empty colony", () => {
  assert.strictEqual(nextChildId([], "anicca-c"), "anicca-c001");
});

test("nextChildId increments past the highest existing id (gap-safe)", () => {
  const children = [{ child_id: "anicca-c001" }, { child_id: "anicca-c003" }];
  // max is 3 → next is 004, NOT 002 (never reuse a retired id)
  assert.strictEqual(nextChildId(children, "anicca-c"), "anicca-c004");
});

test("nextChildId ignores rows with a different prefix", () => {
  const children = [{ child_id: "other-x009" }, { child_id: "anicca-c002" }];
  assert.strictEqual(nextChildId(children, "anicca-c"), "anicca-c003");
});

test("nextChildId zero-pads to width 3", () => {
  const children = Array.from({ length: 9 }, (_, i) => ({ child_id: `anicca-c00${i + 1}` }));
  assert.strictEqual(nextChildId(children, "anicca-c"), "anicca-c010");
});

test("buildChildSpec assembles a complete, distinct-wallet spec", () => {
  const spec = buildChildSpec({
    childId: "anicca-c001",
    parentWallet: "0xPARENT0000000000000000000000000000000A",
    childWallet: "0xCHILD00000000000000000000000000000000B",
    childInbox: "anicca-c001@agentmail.to",
    generation: 1,
    seedUsdc: 1,
    constitutionHash: "deadbeef",
  });
  assert.strictEqual(spec.child_id, "anicca-c001");
  assert.strictEqual(spec.wallet, "0xCHILD00000000000000000000000000000000B");
  assert.strictEqual(spec.parent_wallet, "0xPARENT0000000000000000000000000000000A");
  assert.strictEqual(spec.inbox, "anicca-c001@agentmail.to");
  assert.strictEqual(spec.generation, 1);
  assert.strictEqual(spec.seed_usdc, 1);
  assert.strictEqual(spec.constitution_hash, "deadbeef");
  assert.strictEqual(spec.status, "provisioning");
  assert.match(spec.identity, /Daughter of Anicca deadbeef/);
});

test("buildChildSpec refuses when child wallet equals parent wallet (lineage must be distinct)", () => {
  assert.throws(
    () =>
      buildChildSpec({
        childId: "anicca-c001",
        parentWallet: "0xSAME",
        childWallet: "0xsame",
        childInbox: "x@agentmail.to",
        generation: 1,
        seedUsdc: 1,
        constitutionHash: "h",
      }),
    /distinct/i
  );
});

test("buildChildSpec requires every field", () => {
  assert.throws(
    () => buildChildSpec({ childId: "anicca-c001" }),
    /missing/i
  );
});
