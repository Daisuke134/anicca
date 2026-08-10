"use strict";
const test = require("node:test"), assert = require("node:assert/strict"), { trace, SpanKind } = require("@opentelemetry/api");
const { NodeTracerProvider, SimpleSpanProcessor, InMemorySpanExporter } = require("@opentelemetry/sdk-trace-node");
const { normalizeLocalAgentUsageEvent } = require("./ledger.js");
const { runLocalAgentUsageCollection } = require("./cfo-local-agent-usage-runner.js");
const LM = "life_manager_agent_usage", AN = "anicca_agent_usage", at = "2026-08-11T01:02:03.000Z";
const prior = { schema_version: 1, source_id: LM, byte_offset: 4, prefix_sha256: "a".repeat(64), observed_file_size: 4 };
const chain = (id, state = null) => ({ status: state ? "ready" : "empty", source_state: state, record_count: 0, events: [], counts: { discovered_rows: 0, accepted_rows: 0, duplicate_rows: 0, conflicting_rows: 0, missing_usage_rows: 0, runner_collision_groups: 0, attributed_rows: 0, unattributed_rows: 0 }, coverage_exceptions: [] });
const receipt = (id, bytes, offset = bytes.length, event_count = 0) => ({ record_id: "b".repeat(64), source_id: id, byte_offset: offset, event_count, mapping_id: "local_agent_usage_v1" });
const attempt = id => ({ version: 1, event_id: id, timestamp: "2026-08-11T01:00:00.000Z", loop: "loop", task_label: "task", attempt: 1, provider: "codex", model: "gpt-5.6" });
const event = id => normalizeLocalAgentUsageEvent({ version: 1, event_id: id, timestamp: "2026-08-11T01:00:00.000Z", loop: "loop", task_label: "task", provider: "codex", provider_name: "openai", model: "gpt-5.6", upstream_model: null, attempt: 1, status: "success", measurement: "provider_reported", tokens: { input: 1, cached_input: 0, cache_creation_input: 0, output: 2, reasoning_output: 0, total: 3 } }, { source_row_ref: id + "a".repeat(40), financial_unit_id: null });
const captureChain = (id, item) => item ? { status: "ready", source_state: { schema_version: 1, source_id: id, byte_offset: 5, prefix_sha256: "a".repeat(64), observed_file_size: 5 }, record_count: 1, events: [item], counts: { discovered_rows: 1, accepted_rows: 1, duplicate_rows: 0, conflicting_rows: 0, missing_usage_rows: 0, runner_collision_groups: 0, attributed_rows: 0, unattributed_rows: 1 }, coverage_exceptions: ["unattributed_usage"] } : chain(id);
function owned(t, register = true) { const exporter = new InMemorySpanExporter(), provider = new NodeTracerProvider({ spanProcessors: [new SimpleSpanProcessor(exporter)] }); if (register) provider.register(); t.after(() => { if (register) trace.disable(); return provider.shutdown(); }); return { exporter, tracer: provider.getTracer("cfo-test") }; }
function options(overrides = {}) {
  const calls = [], clocks = { count: 0 }, chainReads = { count: 0 }, base = {
    home: "/tmp/cfo-home", env: { LIFE_MANAGER_STATE_HOME: "/tmp/cfo-state" }, now: () => { clocks.count += 1; return new Date(at); },
    readChain: (root, id) => { calls.push(["chain", root, id]); chainReads.count += 1; return chainReads.count > 2 ? chain(id) : chain(id, id === LM ? prior : null); },
    readFile: file => { calls.push(["read", file]); return file.endsWith("agent-usage-attempts.jsonl") ? Buffer.alloc(0) : Buffer.from("12345"); },
    writeBatch: (root, collectedAt, id, bytes, state) => { calls.push(["write", root, collectedAt, id, bytes, state]); return receipt(id, bytes); },
  };
  return { calls, clocks, options: { ...base, ...overrides } };
}
test("publishes exact capture receipts after both usage writes", t => {
  const { exporter, tracer } = owned(t, false), f = options(); let chains = 0;
  f.options.tracer = tracer; f.options.readChain = (root, id) => { f.calls.push(["chain", root, id]); chains += 1; return chains <= 2 ? chain(id, id === LM ? prior : null) : captureChain(id, event(id === LM ? "a".repeat(24) : "b".repeat(24))); };
  f.options.readFile = file => { f.calls.push(["read", file]); if (file.endsWith("agent-usage-attempts.jsonl")) return Buffer.from(`${JSON.stringify(attempt(file.startsWith("/tmp/cfo-state/") ? "a".repeat(24) : "b".repeat(24)))}\n`); return Buffer.from("12345"); };
  const got = runLocalAgentUsageCollection(f.options), [span] = exporter.getFinishedSpans();
  assert.equal(got.status, "complete"); assert.deepEqual(got.coverage_exceptions, []); assert.deepEqual(got.capture_sources, [
    { source_id: LM, status: "reconciled", receipt: { schema_version: 1, source_id: LM, status: "complete", cutover_at: "2026-08-11T01:00:00.000Z", attempted_rows: 1, success_rows: 1, failed_rows: 0, missing_completion_rows: 0, unmatched_completion_rows: 0, duplicate_attempt_rows: 0, conflicting_attempt_rows: 0, ambiguous_completion_rows: 0, coverage_exceptions: [] }, coverage_exceptions: [] },
    { source_id: AN, status: "reconciled", receipt: { schema_version: 1, source_id: AN, status: "complete", cutover_at: "2026-08-11T01:00:00.000Z", attempted_rows: 1, success_rows: 1, failed_rows: 0, missing_completion_rows: 0, unmatched_completion_rows: 0, duplicate_attempt_rows: 0, conflicting_attempt_rows: 0, ambiguous_completion_rows: 0, coverage_exceptions: [] }, coverage_exceptions: [] },
  ]); assert.ok(Object.isFrozen(got) && Object.isFrozen(got.capture_sources) && got.capture_sources.every(source => Object.isFrozen(source) && Object.isFrozen(source.receipt)));
  assert.deepEqual(span.attributes, { "cfo.local_agent_usage.status": "complete", "cfo.local_agent_usage.source.count": 2, "cfo.local_agent_usage.published_source.count": 2, "cfo.local_agent_usage.coverage_exception.count": 0, "cfo.local_agent_usage.capture.status": "complete", "cfo.local_agent_usage.capture.source.count": 2, "cfo.local_agent_usage.capture.reconciled_source.count": 2, "cfo.local_agent_usage.capture.attempted.count": 2, "cfo.local_agent_usage.capture.success.count": 2, "cfo.local_agent_usage.capture.failed.count": 0, "cfo.local_agent_usage.capture.missing_completion.count": 0, "cfo.local_agent_usage.capture.unmatched_completion.count": 0, "cfo.local_agent_usage.capture.duplicate_attempt.count": 0, "cfo.local_agent_usage.capture.conflicting_attempt.count": 0, "cfo.local_agent_usage.capture.ambiguous_completion.count": 0, "cfo.local_agent_usage.capture.coverage_exception.count": 0, "cfo.local_agent_usage.life_manager.status": "published", "cfo.local_agent_usage.life_manager.record_id": "b".repeat(64), "cfo.local_agent_usage.life_manager.byte_offset": 5, "cfo.local_agent_usage.life_manager.event_count": 0, "cfo.local_agent_usage.life_manager.mapping_id": "local_agent_usage_v1", "cfo.local_agent_usage.anicca.status": "published", "cfo.local_agent_usage.anicca.record_id": "b".repeat(64), "cfo.local_agent_usage.anicca.byte_offset": 5, "cfo.local_agent_usage.anicca.event_count": 0, "cfo.local_agent_usage.anicca.mapping_id": "local_agent_usage_v1", "cfo.local_agent_usage.event.count": 0 }); assert.ok(!Object.keys(span.attributes).some(key => /token|cost/i.test(key)));
});
test("keeps a durable attempt visible when usage persistence fails", t => {
  const { exporter, tracer } = owned(t, false), f = options(); let chains = 0;
  f.options.tracer = tracer; f.options.readChain = (root, id) => { f.calls.push(["chain", root, id]); chains += 1; return chains <= 2 ? chain(id, id === LM ? prior : null) : chain(id); };
  f.options.readFile = file => { f.calls.push(["read", file]); if (file.endsWith("agent-usage-attempts.jsonl")) return file.startsWith("/tmp/cfo-state/") ? Buffer.from(`${JSON.stringify(attempt("a".repeat(24)))}\n`) : Buffer.alloc(0); return Buffer.from("12345"); };
  f.options.writeBatch = (root, collectedAt, id, bytes, state) => { f.calls.push(["write", root, collectedAt, id, bytes, state]); if (id === LM) throw new Error("HOSTILE_WRITE"); return receipt(id, bytes); };
  const got = runLocalAgentUsageCollection(f.options), [span] = exporter.getFinishedSpans(), capture = got.capture_sources[0];
  assert.equal(got.status, "partial"); assert.equal(capture.status, "reconciled"); assert.equal(capture.receipt.missing_completion_rows, 1); assert.deepEqual(capture.coverage_exceptions, ["missing_completion"]); assert.equal(span.attributes["cfo.local_agent_usage.capture.missing_completion.count"], 1); assert.ok(!Object.keys(span.attributes).some(key => /token|cost/i.test(key))); assert.doesNotMatch(JSON.stringify(got), /HOSTILE_WRITE/);
});
test("maps attempt source boundaries to fixed redacted envelopes", () => {
  for (const [kind, expected, status] of [["enoent", "capture_not_started", "reconciled"], ["malformed", "attempt_source_invalid", "unavailable"], ["partial", "attempt_source_invalid", "unavailable"], ["unreadable", "attempt_source_unreadable", "unavailable"]]) {
    const f = options(); f.options.readFile = file => { if (!file.endsWith("agent-usage-attempts.jsonl")) return Buffer.from("12345"); if (!file.startsWith("/tmp/cfo-state/")) return Buffer.alloc(0); if (kind === "enoent") { const error = new Error("HOSTILE_ENOENT"); error.code = "ENOENT"; throw error; } if (kind === "unreadable") throw new Error("HOSTILE_UNREADABLE"); return Buffer.from(kind === "malformed" ? "{bad}\n" : "{}"); };
    const got = runLocalAgentUsageCollection(f.options), source = got.capture_sources[0]; assert.equal(source.status, status); assert.deepEqual(source.coverage_exceptions, [expected]); if (status === "unavailable") assert.equal(source.receipt, null); assert.doesNotMatch(JSON.stringify(got), /HOSTILE_/);
  }
});
test("publishes both fixed ledgers once with one clock, prior cursors, and a frozen content-free receipt", t => {
  const { exporter } = owned(t), f = options(), got = runLocalAgentUsageCollection(f.options), [span] = exporter.getFinishedSpans();
  assert.equal(f.clocks.count, 1);
  assert.deepEqual(f.calls.slice(0, 6).map(call => [call[0], call[0] === "chain" ? call[2] : call[0] === "read" ? call[1] : call[3]]), [["chain", LM], ["read", "/tmp/cfo-state/telemetry/agent-usage.jsonl"], ["write", LM], ["chain", AN], ["read", "/tmp/cfo-home/.local/state/anicca/telemetry/agent-usage.jsonl"], ["write", AN]]);
  assert.deepEqual(f.calls.filter(call => call[0] === "write").map(call => call[5]), [prior, null]);
  assert.deepEqual(got.sources, [
    { source_id: LM, status: "published", record_id: "b".repeat(64), byte_offset: 5, event_count: 0, mapping_id: "local_agent_usage_v1", coverage_exceptions: [] },
    { source_id: AN, status: "published", record_id: "b".repeat(64), byte_offset: 5, event_count: 0, mapping_id: "local_agent_usage_v1", coverage_exceptions: [] },
  ]); assert.equal(got.collected_at, at);
  assert.ok(Object.isFrozen(got) && Object.isFrozen(got.sources) && got.sources.every(source => Object.isFrozen(source) && Object.isFrozen(source.coverage_exceptions)));
  assert.doesNotMatch(JSON.stringify({ receipt: got, span: span && { attributes: span.attributes, events: span.events } }), /12345|HOSTILE|payload|prompt|secret/i);
  assert.equal(exporter.getFinishedSpans().length, 1); assert.equal(span.name, "collect local_agent_usage"); assert.equal(span.kind, SpanKind.INTERNAL); assert.equal(span.ended, true); assert.equal(span.attributes["cfo.local_agent_usage.source.count"], 2); assert.equal(span.attributes["cfo.local_agent_usage.published_source.count"], 2); assert.equal(span.attributes["cfo.local_agent_usage.event.count"], 0); assert.equal(span.attributes["cfo.local_agent_usage.life_manager.status"], "published"); assert.equal(span.attributes["cfo.local_agent_usage.anicca.status"], "published"); assert.equal(span.events.length, 0); assert.equal(span.status.code, 0); assert.equal(span.instrumentationScope.name, "anicca-life-call-cfo");
});
test("isolates an unreadable source and lets the other source publish without leaking the thrown sentinel", t => {
  const { exporter, tracer } = owned(t, false), f = options({ readFile: file => { f.calls.push(["read", file]); if (file.endsWith("agent-usage-attempts.jsonl")) return Buffer.alloc(0); if (file.startsWith("/tmp/cfo-state/")) throw new Error("HOSTILE_PATH_RAW"); return Buffer.from("safe"); }, writeBatch: (root, collectedAt, id, bytes, state) => { f.calls.push(["write", root, collectedAt, id, bytes, state]); return receipt(id, bytes, undefined, 2); }, tracer });
  const got = runLocalAgentUsageCollection(f.options), failed = got.sources[0], published = got.sources[1];
  assert.equal(got.status, "partial"); assert.ok(got.coverage_exceptions.includes("source_unreadable"));
  assert.deepEqual(failed, { source_id: LM, status: "unavailable", record_id: null, byte_offset: null, event_count: null, mapping_id: null, coverage_exceptions: ["source_unreadable"] });
  assert.equal(published.status, "published"); assert.equal(f.calls.filter(call => call[0] === "write").length, 1); assert.equal(f.calls.filter(call => call[0] === "write")[0][3], AN);
  assert.doesNotMatch(JSON.stringify(got), /HOSTILE_PATH_RAW|safe|agent-usage\.jsonl/i); const [span] = exporter.getFinishedSpans(); assert.equal(span.kind, SpanKind.INTERNAL); assert.equal(span.attributes["cfo.local_agent_usage.event.count"], 2); assert.equal(span.attributes["cfo.local_agent_usage.published_source.count"], 1); assert.ok(span.attributes["cfo.local_agent_usage.coverage_exception.count"] >= 1); assert.equal(span.attributes["cfo.local_agent_usage.life_manager.status"], "unavailable"); assert.equal(span.attributes["cfo.local_agent_usage.anicca.status"], "published"); for (const key of ["record_id", "byte_offset", "event_count", "mapping_id"]) assert.equal(span.attributes[`cfo.local_agent_usage.life_manager.${key}`], undefined); assert.equal(span.attributes["cfo.local_agent_usage.anicca.event_count"], 2); assert.equal(span.events.length, 0);
});
test("turns malformed dependencies into local-state failures, preserves null-only empty writes, accepts truncation, and rejects bad arguments before effects", () => {
  for (const kind of ["chain", "writer"]) {
    const f = options(kind === "chain" ? { readChain: (root, id) => id === LM ? { ...chain(LM, prior), hostile: "HOSTILE_CHAIN" } : chain(AN, null) } : { readChain: (root, id) => chain(id, null), writeBatch: (root, atValue, id, bytes, state) => id === AN ? { ...receipt(id, bytes), source_id: "HOSTILE_SOURCE", extra: "HOSTILE_WRITER" } : receipt(id, bytes) });
    const got = runLocalAgentUsageCollection(f.options), failed = got.sources[kind === "chain" ? 0 : 1], other = got.sources[kind === "chain" ? 1 : 0];
    assert.equal(failed.status, "failed"); assert.deepEqual(failed.coverage_exceptions, ["local_state_failure"]); assert.equal(other.status, "published");
    if (kind === "chain") assert.equal(f.calls.filter(call => call[0] === "read" && call[1].includes("life-manager")).length, 0);
    assert.doesNotMatch(JSON.stringify(got), /HOSTILE_CHAIN|HOSTILE_SOURCE|HOSTILE_WRITER/);
  }
  const trunc = options({ readFile: file => file.endsWith("agent-usage-attempts.jsonl") ? Buffer.alloc(0) : Buffer.from("12"), writeBatch: (root, atValue, id, bytes, state) => receipt(id, bytes, state ? state.byte_offset : bytes.length) }), truncated = runLocalAgentUsageCollection(trunc.options);
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
