"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { collectLocalAgentUsageBatch } = require("./cfo-local-agent-usage-collector.js");
const { scanLocalAgentUsageAppend } = require("./cfo-local-agent-usage-cursor.js");

const SOURCE = "life_manager_agent_usage";
const base = { version: 1, timestamp: "2026-08-10T01:02:03Z", loop: "gig", task_label: "gig-daily", provider: "codex", provider_name: "openai", model: "gpt-5.6", upstream_model: null, attempt: 1, status: "success", measurement: "provider_reported", tokens: { input: 1, cached_input: 0, cache_creation_input: 0, output: 2, reasoning_output: 0, total: 3 } };
const row = (event_id, changes = {}) => ({ ...base, event_id, ...changes });
const missing = row("b".repeat(24), { timestamp: "2026-08-10T01:03:03Z", loop: "connector", task_label: "connector-send", status: "failed", measurement: "unavailable", tokens: Object.fromEntries(Object.keys(base.tokens).map((key) => [key, null])) });
const bytes = Buffer.from(`${JSON.stringify(row("a".repeat(24)))}\n${JSON.stringify(missing)}\n`);
const scan = (value, state = null) => scanLocalAgentUsageAppend(SOURCE, Buffer.from(value), state);

test("composes an exact frozen receipt without mutating source bytes", () => {
  const before = Buffer.from(bytes); const receipt = collectLocalAgentUsageBatch(SOURCE, bytes, null);
  assert.deepEqual(bytes, before); assert.deepEqual(Object.keys(receipt), ["events", "source_state", "mapping_id", "counts", "coverage_exceptions"]);
  assert.equal(receipt.mapping_id, "local_agent_usage_v1");
  assert.deepEqual(Object.keys(receipt.counts), ["discovered_rows", "accepted_rows", "duplicate_rows", "conflicting_rows", "missing_usage_rows", "runner_collision_groups", "attributed_rows", "unattributed_rows"]);
  assert.deepEqual(receipt.counts, { discovered_rows: 2, accepted_rows: 2, duplicate_rows: 0, conflicting_rows: 0, missing_usage_rows: 1, runner_collision_groups: 0, attributed_rows: 1, unattributed_rows: 1 });
  assert.equal(receipt.counts.accepted_rows, receipt.counts.attributed_rows + receipt.counts.unattributed_rows); assert.deepEqual(receipt.coverage_exceptions, ["missing_usage", "unattributed_usage"]);
  const sorted = [...receipt.events].sort((a, b) => a.source_event_id < b.source_event_id ? -1 : a.source_event_id > b.source_event_id ? 1 : 0);
  assert.deepEqual(receipt.source_state, scan(bytes).state); assert.deepEqual(receipt.events, sorted);
  assert.ok(Object.isFrozen(receipt) && Object.isFrozen(receipt.events) && Object.isFrozen(receipt.events[0].tokens) && Object.isFrozen(receipt.events[0].run) && Object.isFrozen(receipt.source_state) && Object.isFrozen(receipt.counts) && Object.isFrozen(receipt.coverage_exceptions));
});

test("keeps cursor defects transactional and redacted", () => {
  const first = collectLocalAgentUsageBatch(SOURCE, bytes, null); const prior = first.source_state;
  const unchanged = collectLocalAgentUsageBatch(SOURCE, bytes, prior); assert.deepEqual(unchanged.events, []); assert.deepEqual(unchanged.source_state, prior);
  const truncated = collectLocalAgentUsageBatch(SOURCE, bytes.subarray(0, bytes.length - 1), prior); assert.deepEqual(truncated.events, []); assert.deepEqual(truncated.source_state, prior); assert.deepEqual(truncated.coverage_exceptions, ["source_truncated"]);
  const rewritten = Buffer.from(bytes); rewritten[0] = 91; assert.deepEqual(collectLocalAgentUsageBatch(SOURCE, rewritten, prior).coverage_exceptions, ["source_rewritten"]);
  const partialBytes = Buffer.concat([bytes, Buffer.from("{\"version\":" )]); const partial = collectLocalAgentUsageBatch(SOURCE, partialBytes, null);
  assert.equal(partial.events.length, 2); assert.equal(partial.source_state.byte_offset, bytes.length); assert.equal(partial.source_state.observed_file_size, partialBytes.length); assert.deepEqual(partial.coverage_exceptions, ["missing_usage", "partial_tail", "unattributed_usage"]);
  const invalidBytes = Buffer.concat([bytes, Buffer.from('{"version":2,"event_id":"HOSTILE_EVENT_SENTINEL"}\n')]); const invalid = collectLocalAgentUsageBatch(SOURCE, invalidBytes, prior);
  assert.deepEqual(invalid.events, []); assert.deepEqual(invalid.source_state, prior); assert.deepEqual(invalid.coverage_exceptions, ["invalid_source_row"]); assert.doesNotMatch(JSON.stringify(invalid), /HOSTILE_EVENT_SENTINEL|password|token_secret/);
  assert.throws(() => collectLocalAgentUsageBatch("HOSTILE_SOURCE", Buffer.alloc(0), null), (error) => /^cfo_local_agent_usage_cursor_invalid:invalid_source$/.test(error.message) && !/HOSTILE_SOURCE|HOSTILE_EVENT_SENTINEL/.test(JSON.stringify(error)));
});
