"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const {
  encodeWakeClientState, encodeTestCallClientState, decodeCallClientState, decodeWakeClientState,
} = require("./telnyx-webhook.js");

test("a wake client_state decodes as kind=wake", () => {
  const encoded = encodeWakeClientState({ wakeUid: "lm_abc", wakeEventKey: "lm_abc|2026-08-02T09:00:00+09:00|10" });
  assert.deepEqual(decodeCallClientState(encoded), {
    kind: "wake", wakeUid: "lm_abc", wakeEventKey: "lm_abc|2026-08-02T09:00:00+09:00|10",
  });
});

test("a test-call client_state decodes as kind=test", () => {
  const encoded = encodeTestCallClientState({ testUid: "lm_abc" });
  assert.deepEqual(decodeCallClientState(encoded), { kind: "test", testUid: "lm_abc" });
});

test("a test-call client_state is NOT mistaken for a wake row", () => {
  // Mistaking one for the other would send an amd_result PATCH at an lm_wake_log row that does not
  // exist, and every test call would report matched=0 — the same log line that means a real wake row
  // went missing. The two must stay distinguishable or the matched=0 alarm stops meaning anything.
  assert.equal(decodeWakeClientState(encodeTestCallClientState({ testUid: "lm_abc" })), null);
});

test("empty and unreadable client_state stay null", () => {
  assert.equal(decodeCallClientState(""), null);
  assert.equal(decodeCallClientState("not-base64-json"), null);
  assert.equal(decodeCallClientState(Buffer.from(JSON.stringify({ other: 1 }), "utf8").toString("base64")), null);
});

test("encodeTestCallClientState requires a uid", () => {
  // An empty string is what dial.js checks for before it puts client_state on the dial body. Encoding
  // `{}` into a decodable-but-anonymous blob would hand the webhook a test call it cannot name.
  assert.equal(encodeTestCallClientState({}), "");
  assert.equal(encodeTestCallClientState(), "");
});
