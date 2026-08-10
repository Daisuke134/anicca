"use strict";
const assert = require("node:assert/strict");
const { test } = require("node:test");
const crypto = require("node:crypto");
const { scanLocalAgentUsageAppend } = require("./cfo-local-agent-usage-cursor.js");

const source = "life_manager_agent_usage", otherSource = "anicca_agent_usage", ref = (s, n) => crypto.createHash("sha256").update(`cfo-local-agent-row-v1\0${s}\0${n}`).digest("hex");
const row = (o = {}) => ({ version: 1, event_id: "0123456789abcdef01234567", timestamp: "2026-08-10T01:02:03Z", loop: "morning-loop", task_label: "daily-brief", provider: "codex", provider_name: "openai", model: "gpt-5.6", upstream_model: null, attempt: 1, status: "success", measurement: "provider_reported", tokens: { input: 1, cached_input: 0, cache_creation_input: 0, output: 2, reasoning_output: 0, total: 3 }, ...o });
const line = (o) => JSON.stringify(row(o));
const scan = (b, s = null, sourceId = source) => scanLocalAgentUsageAppend(sourceId, Buffer.from(b), s);

test("initial scan uses raw byte offsets and freezes private pairs/state", () => {
  const bytes = Buffer.from(`${line({ loop: "é-loop" })}\n${line({ task_label: "二" })}\n`), out = scan(bytes);
  assert.equal(out.pairs.length, 2); assert.equal(out.pairs[0].context.source_row_ref, ref(source, 0)); assert.equal(out.pairs[1].context.source_row_ref, ref(source, bytes.indexOf(10) + 1));
  assert.deepEqual(out.state, { schema_version: 1, source_id: source, byte_offset: bytes.length, prefix_sha256: crypto.createHash("sha256").update(bytes).digest("hex"), observed_file_size: bytes.length }); assert.deepEqual(out.coverage_exceptions, []);
  const callerState = { ...out.state }, callerBefore = { ...callerState }; scan(bytes, callerState); assert.deepEqual(callerState, callerBefore); assert.ok(!Object.isFrozen(callerState));
  assert.ok(Object.isFrozen(out) && Object.isFrozen(out.pairs) && Object.isFrozen(out.pairs[0]) && Object.isFrozen(out.pairs[0].input) && Object.isFrozen(out.pairs[0].input.tokens) && Object.isFrozen(out.pairs[0].context) && Object.isFrozen(out.state) && Object.isFrozen(out.coverage_exceptions));
  assert.deepEqual(Object.keys(out).sort(), ["coverage_exceptions", "pairs", "state"]); assert.equal(scan(`${line()}\n`, null, otherSource).pairs[0].context.source_row_ref, ref(otherSource, 0)); assert.doesNotMatch(JSON.stringify(out), /HOSTILE|password|token_secret/);
});

test("unchanged, append, and partial tail are transactional", () => {
  const first = Buffer.from(`${line()}\n`), initial = scan(first), unchanged = scan(first, initial.state); assert.deepEqual(unchanged.pairs, []); assert.deepEqual(unchanged.state, initial.state);
  const appended = Buffer.concat([first, Buffer.from(`${line({ event_id: "fedcba9876543210fedcba98" })}\npartial`)]), next = scan(appended, initial.state); assert.equal(next.pairs.length, 1); assert.deepEqual(next.coverage_exceptions, ["partial_tail"]); assert.equal(next.state.byte_offset, appended.length - 7); assert.equal(next.state.observed_file_size, appended.length);
});

test("truncate and rewrite preserve the committed state", () => {
  const bytes = Buffer.from(`${line()}\n${line({ event_id: "fedcba9876543210fedcba98" })}\n`), prior = scan(bytes), mutable = { ...prior.state }, truncated = scan(bytes.subarray(0, bytes.length - 1), mutable), rewritten = scan(Buffer.from("x".repeat(bytes.length)), prior.state);
  assert.deepEqual(truncated.pairs, []); assert.deepEqual(truncated.coverage_exceptions, ["source_truncated"]); assert.deepEqual(truncated.state, prior.state); assert.ok(!Object.isFrozen(mutable) && truncated.state !== mutable); assert.deepEqual(rewritten.coverage_exceptions, ["source_rewritten"]); assert.deepEqual(rewritten.state, prior.state);
});

test("malformed and schema-invalid complete rows roll back, before partial tail", () => {
  const prefix = Buffer.from(`${line()}\n`), prior = scan(prefix).state;
  for (const bad of [`${line({ event_id: "fedcba9876543210fedcba98" })}\n{"bad"}\npartial`, `${line({ event_id: "fedcba9876543210fedcba98" })}\n${JSON.stringify(row({ version: 2 }))}\npartial`]) { const out = scan(Buffer.concat([prefix, Buffer.from(bad)]), prior); assert.deepEqual(out.pairs, []); assert.deepEqual(out.state, prior); assert.deepEqual(out.coverage_exceptions, ["invalid_source_row"]); assert.doesNotMatch(JSON.stringify(out), /bad|HOSTILE|gpt-5\.6/); }
});

test("arguments are closed, source-bound, and redacted", () => {
  const valid = scan(Buffer.alloc(0)).state, bad = (fn) => assert.throws(fn, (error) => /^cfo_local_agent_usage_cursor_invalid:[a-z_]+$/.test(error.message));
  for (const args of [["bad", Buffer.alloc(0), null], [source, "bytes", null], [source, Buffer.alloc(0), { ...valid, byte_offset: -1 }], [source, Buffer.alloc(0), { ...valid, byte_offset: Number.MAX_SAFE_INTEGER + 1 }], [source, Buffer.alloc(0), { ...valid, observed_file_size: Number.MAX_SAFE_INTEGER + 1 }], [source, Buffer.alloc(0), Object.fromEntries(Object.entries(valid).slice(1))], [source, Buffer.alloc(0), { ...valid, byte_offset: 1 }], [source, Buffer.alloc(0), { ...valid, prefix_sha256: valid.prefix_sha256.toUpperCase() }], [source, Buffer.alloc(0), { ...valid, extra: 1 }], [source, Buffer.alloc(0), Object.assign([], valid)], [otherSource, Buffer.alloc(0), valid]]) bad(() => scanLocalAgentUsageAppend(...args));
  bad(() => scanLocalAgentUsageAppend(source, new Proxy(Buffer.alloc(0), { get() { throw new Error("HOSTILE"); } }), null)); let trapped = false; const hostile = new Proxy(valid, { get() { trapped = true; throw new Error("HOSTILE"); }, ownKeys() { trapped = true; throw new Error("HOSTILE"); }, getPrototypeOf() { trapped = true; throw new Error("HOSTILE"); } }); bad(() => scanLocalAgentUsageAppend(source, Buffer.alloc(0), hostile)); assert.equal(trapped, false);
});
