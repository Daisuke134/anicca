import { test } from "node:test";
import assert from "node:assert/strict";
import { buildTransferData, TRANSFER_SELECTOR, USDC_BASE, toBaseUnits, shareBaseUnits, splitPool } from "../transfer.mjs";

test("selector is the verified ERC20 transfer selector 0xa9059cbb", () => {
  assert.equal(TRANSFER_SELECTOR, "0xa9059cbb"); // ctx7 /websites/base encodeProlink + local keccak
});
test("buildTransferData matches the ctx7 verified example (5 USDC to fe21..e51)", () => {
  // ctx7 example: data 0xa9059cbb + word(fe21034794a5a574b94fe4fdfd16e005f1c96e51) + word(0x4c4b40=5_000_000)
  const data = buildTransferData({ to: "0xfe21034794a5a574b94fe4fdfd16e005f1c96e51", amountBaseUnits: 5000000n });
  assert.equal(
    data,
    "0xa9059cbb000000000000000000000000fe21034794a5a574b94fe4fdfd16e005f1c96e5100000000000000000000000000000000000000000000000000000000004c4b40",
  );
});
test("buildTransferData rejects a bad address / negative amount", () => {
  assert.throws(() => buildTransferData({ to: "nope", amountBaseUnits: 1n }), /address/);
  assert.throws(() => buildTransferData({ to: USDC_BASE, amountBaseUnits: -1n }), /negative/);
});
test("toBaseUnits scales 6dp with no float drift; shareBaseUnits floors bps", () => {
  assert.equal(toBaseUnits(0.45), 450000n);
  assert.equal(shareBaseUnits(0.45, 1000), 45000n);   // 10% of 0.45 = 0.045 USDC
  assert.throws(() => shareBaseUnits(1, 10001), /bps/);
});
test("splitPool floors per recipient and keeps the remainder as dust", () => {
  assert.deepEqual(splitPool(100n, 3), { per: 33n, dust: 1n });
  assert.deepEqual(splitPool(90n, 3), { per: 30n, dust: 0n });
});
