"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { amdDialOptions } = require("./dial.js");
const { encodeTestCallClientState, decodeCallClientState } = require("./telnyx-webhook.js");

const WAKE_URL = "wss://life-call-production.up.railway.app/ws?summary=x&wakeUid=lm_abc&wakeEventKey=k1";
const TEST_URL = "wss://life-call-production.up.railway.app/ws?summary=x&wakeUid=&wakeEventKey=";

test("a wake stream url still derives its client_state from the url", () => {
  // The wake path is the one that already works in production; the test-call fix must not move it.
  const opts = amdDialOptions(WAKE_URL, { LM_AMD: "on" });
  assert.deepEqual(decodeCallClientState(opts.client_state), { kind: "wake", wakeUid: "lm_abc", wakeEventKey: "k1" });
});

test("an explicit client_state wins over the url", () => {
  const clientState = encodeTestCallClientState({ testUid: "lm_abc" });
  const opts = amdDialOptions(TEST_URL, { LM_AMD: "on" }, { clientState });
  assert.equal(opts.answering_machine_detection, "detect");
  assert.deepEqual(decodeCallClientState(opts.client_state), { kind: "test", testUid: "lm_abc" });
});

test("without either, AMD still runs but no client_state is sent", () => {
  // A dial body carrying client_state:"" would make Telnyx echo an empty state back and the webhook
  // would have to tell "the caller chose not to say" apart from "the caller said nothing decodable".
  const opts = amdDialOptions(TEST_URL, { LM_AMD: "on" });
  assert.equal(opts.answering_machine_detection, "detect");
  assert.equal("client_state" in opts, false);
});

test("LM_AMD=off disables AMD even with an explicit client_state", () => {
  // The kill switch stays absolute: no AMD means no detection webhook, so a client_state on the dial
  // body would only be a promise of a callback that is never coming.
  const opts = amdDialOptions(TEST_URL, { LM_AMD: "off" }, { clientState: encodeTestCallClientState({ testUid: "lm_abc" }) });
  assert.deepEqual(opts, {});
});
