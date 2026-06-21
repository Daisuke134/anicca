import { test } from "node:test";
import assert from "node:assert/strict";
import { buildCreatePoolCall, buildUpdateMemberUnitsCall, buildDistributeFlowCall, sendGdaCall, GDA_FORWARDER } from "../gda-pool.mjs";

const A = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"; // a valid checksummed address (Base USDC)
const B = "0x6DA13Bde224A05a288748d857b9e7DDEffd1dE08";

test("buildCreatePoolCall: returns 0x calldata for valid addrs", () => {
  const d = buildCreatePoolCall({ token: A, admin: B });
  assert.ok(typeof d === "string" && d.startsWith("0x") && d.length > 10);
});
test("buildCreatePoolCall: rejects invalid address", () => {
  assert.throws(() => buildCreatePoolCall({ token: "0xbad", admin: B }), /valid address/);
});
test("buildUpdateMemberUnitsCall: integer units ok; negative/fractional rejected", () => {
  assert.ok(buildUpdateMemberUnitsCall({ pool: A, member: B, units: 1 }).startsWith("0x"));
  assert.ok(buildUpdateMemberUnitsCall({ pool: A, member: B, units: 0 }).startsWith("0x")); // 0 = remove
  assert.throws(() => buildUpdateMemberUnitsCall({ pool: A, member: B, units: -1 }), /non-negative integer/);
  assert.throws(() => buildUpdateMemberUnitsCall({ pool: A, member: B, units: 1.5 }), /non-negative integer/);
});
test("buildDistributeFlowCall: bigint flowRate ok; negative/non-bigint rejected", () => {
  assert.ok(buildDistributeFlowCall({ token: A, from: B, pool: A, flowRatePerSec: 1000n }).startsWith("0x"));
  assert.ok(buildDistributeFlowCall({ token: A, from: B, pool: A, flowRatePerSec: 0n }).startsWith("0x")); // 0 = stop
  assert.throws(() => buildDistributeFlowCall({ token: A, from: B, pool: A, flowRatePerSec: -1n }), /non-negative bigint/);
  assert.throws(() => buildDistributeFlowCall({ token: A, from: B, pool: A, flowRatePerSec: 1000 }), /non-negative bigint/);
  assert.throws(() => buildDistributeFlowCall({ token: A, from: B, pool: A, flowRatePerSec: 2n ** 96n }), /int96 max/); // FIND-B02 overflow guard
});
test("sendGdaCall: sends to the forwarder; requires sendTx + calldata", async () => {
  let cap = null;
  const hash = await sendGdaCall("0xabcdef", { sendTx: async (tx) => { cap = tx; return "0xhash"; } });
  assert.equal(hash, "0xhash");
  assert.equal(cap.to, GDA_FORWARDER);
  assert.equal(cap.data, "0xabcdef");
  await assert.rejects(sendGdaCall("0xabc", {}), /sendTx .* required/);
  await assert.rejects(sendGdaCall("notcalldata", { sendTx: async () => "h" }), /calldata required/);
});
