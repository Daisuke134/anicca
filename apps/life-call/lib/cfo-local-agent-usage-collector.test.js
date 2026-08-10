"use strict";

const crypto = require("node:crypto");
const test = require("node:test");
const assert = require("node:assert/strict");
const { collectLocalAgentUsageBatch } = require("./cfo-local-agent-usage-collector.js");
const { scanLocalAgentUsageSource } = require("./cfo-local-agent-usage-source.js");
const { normalizeLocalAgentUsageEvent } = require("./ledger.js");

const SOURCE_ID = "life_manager_agent_usage";
const BASE = { version: 1, timestamp: "2026-08-10T01:02:03Z", loop: "gig", task_label: "gig-daily", provider: "codex", provider_name: "openai", model: "gpt-5.6", upstream_model: null, attempt: 1, status: "success", measurement: "provider_reported", tokens: { input: 1, cached_input: 0, cache_creation_input: 0, output: 2, reasoning_output: 0, total: 3 } };
const attributed = { ...BASE, event_id: "a".repeat(24) };
const unavailable = { ...BASE, event_id: "b".repeat(24), timestamp: "2026-08-10T01:03:03Z", loop: "connector", task_label: "connector-send", status: "failed", measurement: "unavailable", tokens: Object.fromEntries(Object.keys(BASE.tokens).map((key) => [key, null])) };
const data = Buffer.from(`${JSON.stringify(attributed)}\n${JSON.stringify(unavailable)}\n`);
const options = (prior_state = null) => ({ source_id: SOURCE_ID, prior_state });
const hash = (value) => crypto.createHash("sha256").update(value).digest("hex");
const sourceRef = (offset) => hash(Buffer.from(`cfo-local-agent-row-v1\0${SOURCE_ID}\0${offset}`));

test("composes mapped and unmapped rows into one exact frozen receipt", () => {
  const before = Buffer.from(data); const expectedState = scanLocalAgentUsageSource(data, options()).state; const receipt = collectLocalAgentUsageBatch(data, options());
  assert.deepEqual(data, before); assert.deepEqual(Object.keys(receipt), ["events", "source_state", "mapping_id", "counts", "coverage_exceptions"]);
  assert.deepEqual(receipt.source_state, { source_id: SOURCE_ID, byte_offset: data.length, prefix_sha256: hash(data), discovered_rows: 2 });
  assert.deepEqual(receipt.source_state, expectedState); assert.equal(receipt.mapping_id, "local_agent_usage_v1");
  const expectedEvents = [normalizeLocalAgentUsageEvent(attributed, { source_row_ref: sourceRef(0), financial_unit_id: "gig_work" }), normalizeLocalAgentUsageEvent(unavailable, { source_row_ref: sourceRef(JSON.stringify(attributed).length + 1), financial_unit_id: null })].sort((a, b) => a.source_event_id < b.source_event_id ? -1 : 1);
  assert.deepEqual(receipt.events, expectedEvents);
  assert.deepEqual(receipt.counts, { discovered_rows: 2, accepted_rows: 2, duplicate_rows: 0, conflicting_rows: 0, missing_usage_rows: 1, runner_collision_groups: 0, attributed_rows: 1, unattributed_rows: 1 }); assert.deepEqual(receipt.coverage_exceptions, ["missing_usage", "unattributed_usage"]);
  assert.ok(Object.isFrozen(receipt) && Object.isFrozen(receipt.events) && Object.isFrozen(receipt.source_state) && Object.isFrozen(receipt.counts) && Object.isFrozen(receipt.coverage_exceptions));
});

test("passes scanner defects and hides schema failures before exposing state", () => {
  const prior = scanLocalAgentUsageSource(data, options()).state;
  const truncated = collectLocalAgentUsageBatch(data.subarray(0, prior.byte_offset - 1), options(prior)); assert.deepEqual(truncated.events, []); assert.deepEqual(truncated.source_state, prior); assert.deepEqual(truncated.coverage_exceptions, ["source_truncated"]);
  const rewritten = Buffer.from(data); rewritten[0] = 91; assert.deepEqual(collectLocalAgentUsageBatch(rewritten, options(prior)).coverage_exceptions, ["source_rewritten"]);
  const partial = collectLocalAgentUsageBatch(Buffer.concat([data, Buffer.from("{\"version\":")]), options()); assert.equal(partial.events.length, 2); assert.deepEqual(partial.source_state, prior); assert.deepEqual(partial.coverage_exceptions, ["incomplete_tail", "missing_usage", "unattributed_usage"]);
  assert.throws(() => collectLocalAgentUsageBatch(Buffer.from(`${JSON.stringify({ version: 1 })}\n`), options()), /^Error: cfo_local_agent_collector_invalid:invalid_batch$/);
});
