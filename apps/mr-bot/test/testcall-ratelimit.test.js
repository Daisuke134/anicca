// test/test-call-ratelimit.test.js — server-side cost guard for /test-call. The dashboard button's
// one-time disable is client-side only (a reload bypasses it), so testCallAllowed() must enforce the
// cooldown + daily cap on the server. Run: node --test test/test-call-ratelimit.test.js
"use strict";

const test = require("node:test");
const assert = require("node:assert");

// Env so requiring server.js does not throw on load (it guards listen() with require.main === module).
process.env.LM_UID_SECRET = process.env.LM_UID_SECRET || "test_secret";
process.env.LM_CALL_SECRET = process.env.LM_CALL_SECRET || "test_secret";

const { testCallAllowed, TEST_CALL_COOLDOWN_MS, TEST_CALL_DAILY_MAX } = require("../server.js");

test("first test call for a uid is allowed", () => {
  const r = testCallAllowed("uid_first", 0);
  assert.strictEqual(r.ok, true);
});

test("a second call within the cooldown is rejected with retryAfter", () => {
  const uid = "uid_cooldown";
  assert.strictEqual(testCallAllowed(uid, 0).ok, true);
  const r = testCallAllowed(uid, 1000); // 1s later, well inside the cooldown
  assert.strictEqual(r.ok, false);
  assert.ok(r.retryAfter > 0 && r.retryAfter <= TEST_CALL_COOLDOWN_MS / 1000);
});

test("a call after the cooldown elapses is allowed again", () => {
  const uid = "uid_after_cooldown";
  assert.strictEqual(testCallAllowed(uid, 0).ok, true);
  assert.strictEqual(testCallAllowed(uid, TEST_CALL_COOLDOWN_MS + 1).ok, true);
});

test("the daily cap blocks further calls even when spaced past the cooldown", () => {
  const uid = "uid_dailycap";
  let t = 0;
  for (let i = 0; i < TEST_CALL_DAILY_MAX; i++) {
    assert.strictEqual(testCallAllowed(uid, t).ok, true, `call ${i + 1} should be allowed`);
    t += TEST_CALL_COOLDOWN_MS + 1; // space past the cooldown but stay inside 24h
  }
  const blocked = testCallAllowed(uid, t);
  assert.strictEqual(blocked.ok, false, "the (cap+1)th call within 24h is blocked");
});

test("calls older than 24h fall out of the window (cap resets)", () => {
  const uid = "uid_window";
  let t = 0;
  for (let i = 0; i < TEST_CALL_DAILY_MAX; i++) { testCallAllowed(uid, t); t += TEST_CALL_COOLDOWN_MS + 1; }
  // jump > 24h past the first call → old entries pruned → allowed again
  const r = testCallAllowed(uid, 25 * 3600 * 1000);
  assert.strictEqual(r.ok, true);
});
