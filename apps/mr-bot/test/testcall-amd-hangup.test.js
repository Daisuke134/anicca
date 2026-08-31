"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { applyTestCallDetection } = require("../lib/late-notice.js");

// The whole point of the test-call branch is what it does NOT do: it never touches Supabase, because
// there is no lm_wake_log row for a call the scheduler did not place. So the spy watches the ONLY
// transport this path is allowed to use, and every test asserts its exact call count — a Supabase
// write sneaking back in would have to go through a fetch, and no fetch but hangup is permitted here.
function hangupSpy() {
  const calls = [];
  const fetchImpl = async (url, init) => {
    calls.push({ url, method: init && init.method });
    return { ok: true, status: 200, json: async () => ({}) };
  };
  return { calls, fetchImpl };
}

test("a machine on a test call is hung up on", async () => {
  const spy = hangupSpy();
  const out = await applyTestCallDetection({
    result: "machine", callControlId: "v2:abc", fetchImpl: spy.fetchImpl, telnyxApiKey: "k",
  });
  assert.equal(out.result, "machine");
  assert.equal(out.hangup.ok, true);
  assert.equal(spy.calls.length, 1);
  // Encoded: a call_control_id is opaque base64url-ish text that can carry `/`, which unencoded would
  // walk straight out of the actions path and POST somewhere else entirely.
  assert.match(spy.calls[0].url, /\/calls\/v2%3Aabc\/actions\/hangup$/);
  assert.equal(spy.calls[0].method, "POST");
});

test("not_sure is hung up on too", async () => {
  // Same verdict as the wake path (§5.2.1): Telnyx's docs suggest treating not_sure as human, the
  // measured ratio (17 machines / 3 humans) says otherwise, and being wrong here costs one missed
  // nudge while being wrong the other way costs two minutes of paid speech into a recording.
  const spy = hangupSpy();
  const out = await applyTestCallDetection({
    result: "not_sure", callControlId: "v2:abc", fetchImpl: spy.fetchImpl, telnyxApiKey: "k",
  });
  assert.equal(out.hangup.ok, true);
  assert.equal(spy.calls.length, 1);
});

test("a human is never hung up on", async () => {
  // The user pressed "Call me now" and picked up. Hanging up on them is the one outcome that makes
  // the feature worse than not having it.
  const spy = hangupSpy();
  const out = await applyTestCallDetection({
    result: "human", callControlId: "v2:abc", fetchImpl: spy.fetchImpl, telnyxApiKey: "k",
  });
  assert.equal(out.hangup, null);
  assert.equal(spy.calls.length, 0);
});

test("an unreadable result hangs up on nobody", async () => {
  // An empty result is not an AMD verdict, it is a payload we failed to read. Cutting on it would let
  // one Telnyx schema change become "every test call dies on answer" — the silent-total-failure class.
  const spy = hangupSpy();
  const out = await applyTestCallDetection({
    result: "", callControlId: "v2:abc", fetchImpl: spy.fetchImpl, telnyxApiKey: "k",
  });
  assert.equal(out.hangup, null);
  assert.equal(spy.calls.length, 0);
});

test("a failed hangup is reported, never thrown", async () => {
  // The webhook has to answer Telnyx 200 either way; a throw here would surface as a 500 and make
  // Telnyx retry a detection we already acted on.
  const fetchImpl = async () => ({ ok: false, status: 422, json: async () => ({ error: "gone" }) });
  const out = await applyTestCallDetection({
    result: "machine", callControlId: "v2:abc", fetchImpl, telnyxApiKey: "k",
  });
  assert.equal(out.hangup.ok, false);
  assert.match(out.hangup.error, /422/);
});
