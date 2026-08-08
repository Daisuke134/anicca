"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const {
  fixture,
  assertGeneratedEnglish,
  assertNoClientAuthority,
  assertOpaque,
} = require("./mobile-contract-support.js");

test("structured mobile errors expose a stable code, retry decision, and request id", () => {
  const result = fixture("error.json");
  assert.deepEqual(Object.keys(result), ["error"]);
  assert.deepEqual(Object.keys(result.error).sort(), ["code", "message", "requestId", "retryable"].sort());
  assert.match(result.error.code, /^[a-z][a-z0-9_]{2,63}$/u);
  assert.equal(typeof result.error.message, "string");
  assert.equal(typeof result.error.retryable, "boolean");
  assertOpaque(result.error.requestId, "error request id");
  assertGeneratedEnglish(result, "structured error");
  assertNoClientAuthority(result, "structured error");
});
