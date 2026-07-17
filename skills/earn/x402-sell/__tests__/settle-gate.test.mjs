import { test } from "node:test";
import assert from "node:assert";
import { isSettled } from "../lib/settle-gate.mjs";
const enc = (o) => Buffer.from(JSON.stringify(o)).toString("base64");
test("success:true → settled", () => assert.equal(isSettled(enc({ success: true, payer: "0xabc" })), true));
test("success:false → not settled", () => assert.equal(isSettled(enc({ success: false, errorReason: "x" })), false));
test("undefined header → not settled", () => assert.equal(isSettled(undefined), false));
test("garbage base64 → not settled", () => assert.equal(isSettled("!!!notb64!!!"), false));
