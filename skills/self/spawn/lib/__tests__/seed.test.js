// RED-first tests for lib/seed.js (spawn-auto-seed REQ-3 / REQ-5). node:test, no I/O.
const test = require("node:test");
const assert = require("node:assert/strict");
const { buildSeedPlan, finalizeSeedRow } = require("../seed");

const PARENT = "0x810f6d61f7606deee2657d3083e150a222bc29c5";
const CHILD = "0xAbCd000000000000000000000000000000000001";

test("buildSeedPlan: happy path returns integer 6-decimal units", () => {
  const plan = buildSeedPlan({ seedUsdc: 1, parentWallet: PARENT, childWallet: CHILD, parentBalanceUsdc: 1.79 });
  assert.equal(plan.amountUnits, 1000000);
  assert.ok(Number.isInteger(plan.amountUnits));
});

test("buildSeedPlan: fractional seed converts exactly", () => {
  const plan = buildSeedPlan({ seedUsdc: 0.25, parentWallet: PARENT, childWallet: CHILD, parentBalanceUsdc: 1 });
  assert.equal(plan.amountUnits, 250000);
});

test("buildSeedPlan: throws on non-finite / zero / negative seed", () => {
  for (const bad of [0, -1, NaN, Infinity, "1", null, undefined]) {
    assert.throws(() => buildSeedPlan({ seedUsdc: bad, parentWallet: PARENT, childWallet: CHILD, parentBalanceUsdc: 10 }));
  }
});

test("buildSeedPlan: throws when child == parent (case-insensitive)", () => {
  assert.throws(() => buildSeedPlan({ seedUsdc: 1, parentWallet: PARENT, childWallet: PARENT.toUpperCase(), parentBalanceUsdc: 10 }));
});

test("buildSeedPlan: throws when balance < seed", () => {
  assert.throws(() => buildSeedPlan({ seedUsdc: 2, parentWallet: PARENT, childWallet: CHILD, parentBalanceUsdc: 1.79 }));
});

test("finalizeSeedRow: returns NEW row with seed fields, no mutation", () => {
  const row = { child_id: "anicca-c1", status: "active" };
  const out = finalizeSeedRow(row, { txHash: "0xdeadbeef" });
  assert.equal(out.seed_tx, "0xdeadbeef");
  assert.equal(out.seed_status, "sent");
  assert.equal(out.child_id, "anicca-c1");
  assert.equal(row.seed_tx, undefined); // immutability
  assert.notEqual(out, row);
});

test("finalizeSeedRow: throws on missing/invalid txHash", () => {
  for (const bad of ["", null, undefined, "nothex"]) {
    assert.throws(() => finalizeSeedRow({ a: 1 }, { txHash: bad }));
  }
});
