"use strict";
const test = require("node:test"), assert = require("node:assert/strict"), { trace, SpanKind } = require("@opentelemetry/api");
const { NodeTracerProvider, SimpleSpanProcessor, InMemorySpanExporter } = require("@opentelemetry/sdk-trace-node");
const { runLocalAgentUsageCollection } = require("./cfo-local-agent-usage-runner.js");
const LM = "life_manager_agent_usage", AN = "anicca_agent_usage", at = "2026-08-11T01:02:03.000Z";
const prior = { schema_version: 1, source_id: LM, byte_offset: 4, prefix_sha256: "a".repeat(64), observed_file_size: 4 };
const chain = (id, state = null) => ({ status: state ? "ready" : "empty", source_state: state, record_count: 0, events: [], counts: {}, coverage_exceptions: [] });
const receipt = (id, bytes, offset = bytes.length, event_count = 0) => ({ record_id: "b".repeat(64), source_id: id, byte_offset: offset, event_count, mapping_id: "local_agent_usage_v1" });
function owned(t, register = true) { const exporter = new InMemorySpanExporter(), provider = new NodeTracerProvider({ spanProcessors: [new SimpleSpanProcessor(exporter)] }); if (register) provider.register(); t.after(() => { if (register) trace.disable(); return provider.shutdown(); }); return { exporter, tracer: provider.getTracer("cfo-test") }; }
function options(overrides = {}) {
  const calls = [], clocks = { count: 0 }, base = {
    home: "/tmp/cfo-home", env: { LIFE_MANAGER_STATE_HOME: "/tmp/cfo-state" }, now: () => { clocks.count += 1; return new Date(at); },
    readChain: (root, id) => { calls.push(["chain", root, id]); return chain(id, id === LM ? prior : null); },
    readFile: file => { calls.push(["read", file]); return Buffer.from("12345"); },
    writeBatch: (root, collectedAt, id, bytes, state) => { calls.push(["write", root, collectedAt, id, bytes, state]); return receipt(id, bytes); },
  };
  return { calls, clocks, options: { ...base, ...overrides } };
}
test("publishes both fixed ledgers once with one clock, prior cursors, and a frozen content-free receipt", t => {
  const { exporter } = owned(t), f = options(), got = runLocalAgentUsageCollection(f.options), [span] = exporter.getFinishedSpans();
  assert.equal(f.clocks.count, 1);
  assert.deepEqual(f.calls.map(call => [call[0], call[0] === "chain" ? call[2] : call[0] === "read" ? call[1] : call[3]]), [["chain", LM], ["read", "/tmp/cfo-state/telemetry/agent-usage.jsonl"], ["write", LM], ["chain", AN], ["read", "/tmp/cfo-home/.local/state/anicca/telemetry/agent-usage.jsonl"], ["write", AN]]);
  assert.deepEqual(f.calls.filter(call => call[0] === "write").map(call => call[5]), [prior, null]);
  assert.deepEqual(got, { status: "complete", collected_at: at, sources: [
    { source_id: LM, status: "published", record_id: "b".repeat(64), byte_offset: 5, event_count: 0, mapping_id: "local_agent_usage_v1", coverage_exceptions: [] },
    { source_id: AN, status: "published", record_id: "b".repeat(64), byte_offset: 5, event_count: 0, mapping_id: "local_agent_usage_v1", coverage_exceptions: [] },
  ], coverage_exceptions: [] });
  assert.ok(Object.isFrozen(got) && Object.isFrozen(got.sources) && got.sources.every(source => Object.isFrozen(source) && Object.isFrozen(source.coverage_exceptions)));
  assert.doesNotMatch(JSON.stringify({ receipt: got, span: span && { attributes: span.attributes, events: span.events } }), /12345|HOSTILE|payload|prompt|secret/i);
  assert.equal(exporter.getFinishedSpans().length, 1); assert.equal(span.name, "collect local_agent_usage"); assert.equal(span.kind, SpanKind.INTERNAL); assert.equal(span.ended, true); assert.deepEqual(span.attributes, { "cfo.local_agent_usage.status": "complete", "cfo.local_agent_usage.source.count": 2, "cfo.local_agent_usage.published_source.count": 2, "cfo.local_agent_usage.event.count": 0, "cfo.local_agent_usage.coverage_exception.count": 0, "cfo.local_agent_usage.life_manager.status": "published", "cfo.local_agent_usage.anicca.status": "published", "cfo.local_agent_usage.life_manager.record_id": "b".repeat(64), "cfo.local_agent_usage.life_manager.byte_offset": 5, "cfo.local_agent_usage.life_manager.event_count": 0, "cfo.local_agent_usage.life_manager.mapping_id": "local_agent_usage_v1", "cfo.local_agent_usage.anicca.record_id": "b".repeat(64), "cfo.local_agent_usage.anicca.byte_offset": 5, "cfo.local_agent_usage.anicca.event_count": 0, "cfo.local_agent_usage.anicca.mapping_id": "local_agent_usage_v1" }); assert.equal(span.events.length, 0); assert.equal(span.status.code, 0); assert.equal(span.instrumentationScope.name, "anicca-life-call-cfo");
});
test("isolates an unreadable source and lets the other source publish without leaking the thrown sentinel", t => {
  const { exporter, tracer } = owned(t, false), f = options({ readFile: file => { f.calls.push(["read", file]); if (file.startsWith("/tmp/cfo-state/")) throw new Error("HOSTILE_PATH_RAW"); return Buffer.from("safe"); }, writeBatch: (root, collectedAt, id, bytes, state) => { f.calls.push(["write", root, collectedAt, id, bytes, state]); return receipt(id, bytes, undefined, 2); }, tracer });
  const got = runLocalAgentUsageCollection(f.options), failed = got.sources[0], published = got.sources[1];
  assert.equal(got.status, "partial"); assert.deepEqual(got.coverage_exceptions, ["source_unreadable"]);
  assert.deepEqual(failed, { source_id: LM, status: "unavailable", record_id: null, byte_offset: null, event_count: null, mapping_id: null, coverage_exceptions: ["source_unreadable"] });
  assert.equal(published.status, "published"); assert.equal(f.calls.filter(call => call[0] === "write").length, 1); assert.equal(f.calls.filter(call => call[0] === "write")[0][3], AN);
  assert.doesNotMatch(JSON.stringify(got), /HOSTILE_PATH_RAW|safe|agent-usage\.jsonl/i); const [span] = exporter.getFinishedSpans(); assert.equal(span.kind, SpanKind.INTERNAL); assert.equal(span.attributes["cfo.local_agent_usage.event.count"], 2); assert.equal(span.attributes["cfo.local_agent_usage.published_source.count"], 1); assert.equal(span.attributes["cfo.local_agent_usage.coverage_exception.count"], 1); assert.equal(span.attributes["cfo.local_agent_usage.life_manager.status"], "unavailable"); assert.equal(span.attributes["cfo.local_agent_usage.anicca.status"], "published"); for (const key of ["record_id", "byte_offset", "event_count", "mapping_id"]) assert.equal(span.attributes[`cfo.local_agent_usage.life_manager.${key}`], undefined); assert.equal(span.attributes["cfo.local_agent_usage.anicca.event_count"], 2); assert.equal(span.events.length, 0);
});
test("turns malformed dependencies into local-state failures, preserves null-only empty writes, accepts truncation, and rejects bad arguments before effects", () => {
  for (const kind of ["chain", "writer"]) {
    const f = options(kind === "chain" ? { readChain: (root, id) => id === LM ? { ...chain(LM, prior), hostile: "HOSTILE_CHAIN" } : chain(AN, null) } : { readChain: (root, id) => chain(id, null), writeBatch: (root, atValue, id, bytes, state) => id === AN ? { ...receipt(id, bytes), source_id: "HOSTILE_SOURCE", extra: "HOSTILE_WRITER" } : receipt(id, bytes) });
    const got = runLocalAgentUsageCollection(f.options), failed = got.sources[kind === "chain" ? 0 : 1], other = got.sources[kind === "chain" ? 1 : 0];
    assert.equal(failed.status, "failed"); assert.deepEqual(failed.coverage_exceptions, ["local_state_failure"]); assert.equal(other.status, "published");
    if (kind === "chain") assert.equal(f.calls.filter(call => call[0] === "read" && call[1].includes("life-manager")).length, 0);
    assert.doesNotMatch(JSON.stringify(got), /HOSTILE_CHAIN|HOSTILE_SOURCE|HOSTILE_WRITER/);
  }
  const trunc = options({ readFile: () => Buffer.from("12"), writeBatch: (root, atValue, id, bytes, state) => receipt(id, bytes, state ? state.byte_offset : bytes.length) }), truncated = runLocalAgentUsageCollection(trunc.options);
  assert.equal(truncated.sources[0].status, "published"); assert.equal(truncated.sources[0].byte_offset, 4); const oversized = runLocalAgentUsageCollection(options({ writeBatch: (root, atValue, id, bytes) => receipt(id, bytes, bytes.length, bytes.length + 1) }).options); assert.equal(oversized.sources[0].status, "failed"); assert.deepEqual(oversized.sources[0].coverage_exceptions, ["local_state_failure"]);
  const effects = { calls: 0 }, seam = () => { effects.calls += 1; throw new Error("HOSTILE_EFFECT"); }, bad = [
    [{ extra: 1 }, "invalid_options"], [{ home: "/tmp/cfo-home/..", now: seam }, "invalid_home"], [{ env: { LIFE_MANAGER_STATE_HOME: "relative" }, now: seam }, "invalid_state_root"], [{ now: () => new Date("invalid") }, "invalid_clock"],
  ];
  for (const [input, reason] of bad) assert.throws(() => runLocalAgentUsageCollection({ ...input, readChain: seam, readFile: seam, writeBatch: seam }), error => error.message === `cfo_local_agent_usage_runner_invalid:${reason}`);
  assert.equal(effects.calls, 0);
});
test("rejects a coercible hostile writer record ID without leaking it", () => {
  const hostile = { toString: () => "b".repeat(64), secret: "HOSTILE_RECORD_ID" }, f = options({ readChain: (root, id) => chain(id, null), writeBatch: (root, atValue, id, bytes) => id === LM ? { ...receipt(id, bytes), record_id: hostile } : receipt(id, bytes) }), got = runLocalAgentUsageCollection(f.options);
  assert.equal(got.sources[0].status, "failed"); assert.deepEqual(got.sources[0].coverage_exceptions, ["local_state_failure"]); assert.equal(got.sources[1].status, "published"); assert.doesNotMatch(JSON.stringify(got), /HOSTILE_RECORD_ID/);
});
test("swallows a hostile synchronous tracer and keeps the durable receipt unchanged", () => {
  const expected = runLocalAgentUsageCollection(options().options), f = options({ tracer: { startSpan: () => { throw new Error("HOSTILE_TRACE"); } } }), original = [console.log, console.error, console.warn], logs = []; console.log = console.error = console.warn = (...args) => logs.push(args);
  let got; try { got = runLocalAgentUsageCollection(f.options); } finally { [console.log, console.error, console.warn] = original; }
  assert.deepEqual(got, expected); assert.equal(logs.length, 0); assert.doesNotMatch(JSON.stringify(got), /HOSTILE_TRACE/);
});
test("default no-provider telemetry is a silent no-op", () => {
  trace.disable(); const expected = runLocalAgentUsageCollection(options().options), original = [console.log, console.error, console.warn], logs = []; console.log = console.error = console.warn = (...args) => logs.push(args); let got; try { got = runLocalAgentUsageCollection(options().options); } finally { [console.log, console.error, console.warn] = original; }
  assert.deepEqual(got, expected); assert.equal(logs.length, 0);
});
