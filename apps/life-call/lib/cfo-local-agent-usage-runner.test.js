"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const { runLocalAgentUsageCollection } = require("./cfo-local-agent-usage-runner.js");

const home = "/Users/tester", root = `${home}/.local/state/life-manager`, at = "2026-08-11T00:00:00Z";
const ids = ["life_manager_agent_usage", "anicca_agent_usage"], paths = [`${root}/telemetry/agent-usage.jsonl`, `${home}/.local/state/anicca/telemetry/agent-usage.jsonl`];
const state = id => ({ schema_version: 1, source_id: id, byte_offset: 4, prefix_sha256: "a".repeat(64), observed_file_size: 4 });
const receipt = id => ({ record_id: `${id}-record`, source_id: id, byte_offset: 4, event_count: 1, mapping_id: "local_agent_usage_v1" });
const frozen = value => { if (!value || typeof value !== "object") return; assert.ok(Object.isFrozen(value)); Object.values(value).forEach(frozen); };

test("reads both fixed sources once, resumes chains, and returns a frozen redacted receipt", () => {
  let clocks = 0; const files = [], chains = [], writes = [], bytes = Buffer.from("HOSTILE_RAW_LEDGER");
  const result = runLocalAgentUsageCollection({ home, env: { LIFE_MANAGER_STATE_HOME: root }, now: () => { clocks += 1; return at; }, readFile: file => { files.push(file); return bytes; }, readChain: (stateRoot, source) => { chains.push([stateRoot, source]); return { status: "ready", source_state: state(source) }; }, writeBatch: (...args) => { writes.push(args); return receipt(args[2]); } });
  assert.deepEqual(result, { status: "complete", collected_at: at, sources: ids.map(id => ({ source_id: id, status: "published", ...receipt(id), coverage_exceptions: [] })), coverage_exceptions: [] });
  assert.equal(clocks, 1); assert.deepEqual(files, paths); assert.deepEqual(chains, ids.map(id => [root, id])); assert.equal(writes.length, 2);
  writes.forEach((args, index) => { assert.equal(args[0], root); assert.equal(args[1], at); assert.equal(args[2], ids[index]); assert.equal(args[3], bytes); assert.deepEqual(args[4], state(ids[index])); });
  frozen(result); assert.doesNotMatch(JSON.stringify(result), /HOSTILE_RAW_LEDGER|agent-usage\.jsonl|Users\/tester/);
});

test("continues after one unreadable ledger without writing it", () => {
  const writes = [], result = runLocalAgentUsageCollection({ home, env: { LIFE_MANAGER_STATE_HOME: root }, now: () => at, readFile: file => { if (file === paths[0]) throw new Error("HOSTILE_READ_SENTINEL"); return Buffer.from("other"); }, readChain: (_stateRoot, source) => ({ status: "ready", source_state: state(source) }), writeBatch: (...args) => { writes.push(args[2]); return receipt(args[2]); } });
  assert.equal(result.status, "partial"); assert.deepEqual(writes, [ids[1]]); assert.deepEqual(result.sources[0], { source_id: ids[0], status: "unavailable", record_id: null, byte_offset: null, event_count: null, mapping_id: null, coverage_exceptions: ["source_unreadable"] }); assert.deepEqual(result.coverage_exceptions, ["source_unreadable"]); assert.doesNotMatch(JSON.stringify(result), /HOSTILE_READ_SENTINEL|agent-usage\.jsonl/);
});

test("does not restart from null when a chain fails", () => {
  const writes = [], result = runLocalAgentUsageCollection({ home, env: { LIFE_MANAGER_STATE_HOME: root }, now: () => at, readFile: () => Buffer.from("other"), readChain: (_stateRoot, source) => { if (source === ids[0]) throw new Error("HOSTILE_CHAIN_SENTINEL"); return { status: "empty", source_state: null }; }, writeBatch: (...args) => { writes.push(args); return receipt(args[2]); } });
  assert.equal(result.status, "partial"); assert.deepEqual(writes.map(args => args[2]), [ids[1]]); assert.equal(writes[0][4], null); assert.deepEqual(result.sources[0], { source_id: ids[0], status: "failed", record_id: null, byte_offset: null, event_count: null, mapping_id: null, coverage_exceptions: ["local_state_failure"] }); assert.deepEqual(result.coverage_exceptions, ["local_state_failure"]); assert.doesNotMatch(JSON.stringify(result), /HOSTILE_CHAIN_SENTINEL/);
});

test("does not trust prefix-spoofed external errors", () => {
  const invoke = fn => { try { fn(); return ""; } catch (error) { return error.message; } }, prefix = "cfo_local_agent_usage_runner_invalid:";
  const env = {}; Object.defineProperty(env, "LIFE_MANAGER_STATE_HOME", { enumerable: true, get: () => { throw new Error(`${prefix}LEAK_ENV_SECRET`); } });
  assert.deepEqual([invoke(() => runLocalAgentUsageCollection({ env })), invoke(() => runLocalAgentUsageCollection({ now: () => { throw new Error(`${prefix}LEAK_CLOCK_SECRET`); } }))], [`${prefix}invalid_options`, `${prefix}invalid_clock`]);
});
