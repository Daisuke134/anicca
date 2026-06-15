// TDD for state-path.js (spec27 §2 WF-A self-spawn gap-fix #3: durable state, fail-closed on /tmp).
// children.jsonl / wallet.json MUST live on durable storage so a tmp-clean never erases the colony.
const test = require("node:test");
const assert = require("node:assert");
const { resolveStateDir, assertDurable } = require("../state-path.js");

test("explicit durable env dir is honored", () => {
  assert.strictEqual(resolveStateDir({ env: { ANICCA_STATE_DIR: "/var/lib/anicca" } }), "/var/lib/anicca");
});

test("fail-closed: an explicit /tmp state dir is rejected (would be tmp-cleaned)", () => {
  assert.throws(
    () => resolveStateDir({ env: { ANICCA_STATE_DIR: "/tmp/anicca" } }),
    /durable|tmp/i
  );
});

test("fail-closed: /private/tmp (macOS) is also rejected", () => {
  assert.throws(
    () => resolveStateDir({ env: { ANICCA_STATE_DIR: "/private/tmp/x" } }),
    /durable|tmp/i
  );
});

test("default on a host falls back to ~/.hermes/state (durable, not tmp)", () => {
  const dir = resolveStateDir({ env: { HOME: "/home/anicca" } });
  assert.strictEqual(dir, "/home/anicca/.hermes/state");
  assert.ok(!/(^|\/)tmp(\/|$)/.test(dir), "must not resolve under tmp");
});

test("assertDurable throws on tmp paths and passes on durable ones", () => {
  assert.throws(() => assertDurable("/tmp/children.jsonl"), /durable|tmp/i);
  assert.doesNotThrow(() => assertDurable("/var/lib/anicca/children.jsonl"));
});
