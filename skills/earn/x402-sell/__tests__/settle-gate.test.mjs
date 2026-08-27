import { test } from "node:test";
import assert from "node:assert";
import { decodeTransaction, isSettled } from "../lib/settle-gate.mjs";
const enc = (o) => Buffer.from(JSON.stringify(o)).toString("base64");
test("success:true → settled", () => assert.equal(isSettled(enc({ success: true, payer: "0xabc" })), true));
test("success:false → not settled", () => assert.equal(isSettled(enc({ success: false, errorReason: "x" })), false));
test("undefined header → not settled", () => assert.equal(isSettled(undefined), false));
test("garbage base64 → not settled", () => assert.equal(isSettled("!!!notb64!!!"), false));
test("settle response exposes the on-chain transaction hash", () => {
  assert.equal(decodeTransaction(enc({ success: true, transaction: "0xabc" })), "0xabc");
});
test("missing or malformed transaction decodes to null", () => {
  assert.equal(decodeTransaction(enc({ success: true })), null);
  assert.equal(decodeTransaction("!!!notb64!!!"), null);
});
