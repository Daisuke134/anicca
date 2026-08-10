"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { scanLocalAgentUsageSource } = require("./cfo-local-agent-usage-source.js");

const SOURCE_ID = "life_manager_agent_usage";
const ROW_1 = '{"version":1,"event_id":"111111111111111111111111","timestamp":"2026-08-10T01:02:03Z","loop":"朝日","task_label":"brief","provider":"codex","provider_name":"openai","model":"gpt-5.6","upstream_model":null,"attempt":1,"status":"success","measurement":"provider_reported","tokens":{"input":1,"cached_input":0,"cache_creation_input":0,"output":2,"reasoning_output":0,"total":3}}';
const ROW_2 = '{"version":1,"event_id":"222222222222222222222222","timestamp":"2026-08-10T01:03:03Z","loop":"night","task_label":"reflect","provider":"claude","provider_name":"anthropic","model":"claude-sonnet","upstream_model":null,"attempt":1,"status":"success","measurement":"provider_reported","tokens":{"input":4,"cached_input":1,"cache_creation_input":2,"output":5,"reasoning_output":0,"total":12}}';
const ROW_3 = ROW_2.replace(/222222222222222222222222/g, "333333333333333333333333").replace("01:03:03", "01:04:03");
const data = (tail = "") => Buffer.from(`${ROW_1}\n${ROW_2}\n${tail}`);
const options = (prior_state = null) => ({ source_id: SOURCE_ID, prior_state });
const ref = (value) => value;

test("initial scan emits exact byte state, pairs, and source refs", () => {
  const receipt = scanLocalAgentUsageSource(data(), options());
  assert.deepEqual(Object.keys(receipt), ["pairs", "state", "coverage_exceptions"]);
  assert.deepEqual(receipt.state, { source_id: SOURCE_ID, byte_offset: 768, prefix_sha256: "3637c189308c5c507d297535ba793502c2fa5bf6be9e3649a28d9f0a7566f841", discovered_rows: 2 });
  assert.deepEqual(receipt.pairs.map((pair) => ({ keys: Object.keys(pair), context: pair.context, event_id: pair.input.event_id })), [{ keys: ["input", "context"], context: { source_row_ref: ref("99de2df67db2d8d7e94d8c95f12ffb9aa7481c290fa7bfe3e79619580bfc8170") }, event_id: "111111111111111111111111" }, { keys: ["input", "context"], context: { source_row_ref: ref("dfc6543f8e4bfbfb3ee7742fa93114f97e9565067e4ac73c31e22cf9518c60f3") }, event_id: "222222222222222222222222" }]);
  assert.deepEqual(receipt.coverage_exceptions, []);
});

test("rescan, append, truncation, rewrite, partial tail, and malformed rows are covered", () => {
  const first = scanLocalAgentUsageSource(data(), options());
  assert.deepEqual(scanLocalAgentUsageSource(data(), options(first.state)).pairs, []);
  const appended = scanLocalAgentUsageSource(Buffer.concat([data(), Buffer.from(`${ROW_3}\n`)]), options(first.state));
  assert.deepEqual(appended.pairs.map(({ input }) => input.event_id), ["333333333333333333333333"]);
  assert.equal(appended.state.byte_offset, 1158);
  const terminalRewrite = Buffer.from(data()); terminalRewrite[first.state.byte_offset - 1] = 32;
  for (const [input, exception] of [[data().subarray(0, 10), "source_truncated"], [Buffer.from("X" + data().subarray(1).toString()), "source_rewritten"], [terminalRewrite, "source_rewritten"]]) {
    const result = scanLocalAgentUsageSource(input, options(first.state));
    assert.deepEqual(result.pairs, []); assert.deepEqual(result.state, first.state); assert.deepEqual(result.coverage_exceptions, [exception]);
  }
  const partial = scanLocalAgentUsageSource(Buffer.from(`${ROW_1}\n{"version":1`), options());
  assert.equal(partial.pairs.length, 1); assert.deepEqual(partial.coverage_exceptions, ["incomplete_tail"]);
  const malformed = scanLocalAgentUsageSource(Buffer.from(`${ROW_1}\nbad-json\n`), options());
  assert.deepEqual(malformed.pairs, []); assert.equal(malformed.state, null); assert.deepEqual(malformed.coverage_exceptions, ["invalid_source_row"]);
});

test("scanner clones and freezes receipts and redacts invalid boundaries", () => {
  const prior = scanLocalAgentUsageSource(data(), options()).state;
  const receipt = scanLocalAgentUsageSource(data(), options(prior));
  assert.ok(Object.isFrozen(receipt) && Object.isFrozen(receipt.state) && Object.isFrozen(receipt.pairs) && Object.isFrozen(receipt.coverage_exceptions));
  for (const [input, opts] of [["not-buffer", options()], [Buffer.alloc(0), { source_id: "bad-source", prior_state: null }], [Buffer.from("x"), { source_id: SOURCE_ID, prior_state: { ...prior, byte_offset: 1, prefix_sha256: "2d711642b726b04401627ca9fbac32f5c8530fb1903cc4db02258717921a4881" } }], [data(), { source_id: SOURCE_ID, prior_state: { ...prior, discovered_rows: 1 } }]]) {
    assert.throws(() => scanLocalAgentUsageSource(input, opts), (error) => /^cfo_local_agent_source_invalid:[a-z_]+$/.test(error.message) && !/bad-source|3637c189|not-buffer/.test(error.message));
  }
});
