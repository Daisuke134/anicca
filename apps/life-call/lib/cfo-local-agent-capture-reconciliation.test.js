"use strict";
const test = require("node:test"), assert = require("node:assert/strict");
const { reconcileLocalAgentUsageCapture } = require("./cfo-local-agent-capture-reconciliation.js");
const { normalizeLocalAgentUsageEvent } = require("./ledger.js");
const SOURCE = "anicca_agent_usage", prefix = "0".repeat(64);
const attempt = (id, extra = {}) => ({ version: 1, event_id: id, timestamp: "2026-08-11T02:00:00Z", loop: "loop", task_label: "task", attempt: 1, provider: "codex", model: "gpt-5.6", ...extra });
const event = (id, at, status = "success", n = "a") => normalizeLocalAgentUsageEvent({ version: 1, event_id: id, timestamp: at, loop: "loop", task_label: "task", provider: "codex", provider_name: "openai", model: "gpt-5.6", upstream_model: null, attempt: 1, status, measurement: "provider_reported", tokens: { input: 1, cached_input: 0, cache_creation_input: 0, output: 2, reasoning_output: 0, total: 3 } }, { source_row_ref: id + n.repeat(40), financial_unit_id: null });
const chain = (events = []) => { const runners = new Map(); for (const item of events) runners.set(item.runner_event_id, (runners.get(item.runner_event_id) || 0) + 1); const collisions = [...runners.values()].filter(count => count > 1).length; return { status: events.length ? "ready" : "empty", source_state: events.length ? { schema_version: 1, source_id: SOURCE, byte_offset: 0, prefix_sha256: prefix, observed_file_size: 0 } : null, record_count: events.length, events, counts: { discovered_rows: events.length, accepted_rows: events.length, duplicate_rows: 0, conflicting_rows: 0, missing_usage_rows: 0, runner_collision_groups: collisions, attributed_rows: 0, unattributed_rows: events.length }, coverage_exceptions: [...(collisions ? ["runner_identity_collision"] : []), ...(events.length ? ["unattributed_usage"] : [])] }; };
const id = (c) => c.repeat(24);

test("reconciles success, failure, missing, history, and unmatched rows", () => {
  const result = reconcileLocalAgentUsageCapture(SOURCE, [attempt(id("a")), attempt(id("b"), { timestamp: "2026-08-11T03:00:00Z", status: undefined }), attempt(id("c"), { timestamp: "2026-08-11T04:00:00Z" })].map(row => { const copy = { ...row }; delete copy.status; return copy; }), chain([event(id("9"), "2026-08-11T04:00:00Z"), event(id("a"), "2026-08-11T01:00:00Z"), event(id("a"), "2026-08-11T02:00:00Z", "success", "b"), event(id("b"), "2026-08-11T03:00:00Z", "failed")]));
  assert.deepEqual(result, { schema_version: 1, source_id: SOURCE, status: "partial", cutover_at: "2026-08-11T02:00:00Z", attempted_rows: 3, success_rows: 1, failed_rows: 1, missing_completion_rows: 1, unmatched_completion_rows: 1, duplicate_attempt_rows: 0, conflicting_attempt_rows: 0, ambiguous_completion_rows: 0, coverage_exceptions: ["missing_completion", "unmatched_completion"] });
});

test("applies duplicate/conflict precedence and counts ambiguous completions", () => {
  const d = id("d"), e = id("e"), f = id("f");
  const rows = [attempt(d), attempt(d), attempt(e), attempt(e, { attempt: 2 }), attempt(e, { attempt: 2 }), attempt(f, { timestamp: "2026-08-11T05:00:00Z" })];
  const result = reconcileLocalAgentUsageCapture(SOURCE, rows, chain([event(d, "2026-08-11T02:00:00Z", "success", "b"), event(d, "2026-08-11T02:00:01Z", "failed", "c"), event(e, "2026-08-11T03:00:00Z"), event(f, "2026-08-11T05:00:00Z")]));
  assert.equal(result.attempted_rows, 2); assert.equal(result.duplicate_attempt_rows, 1); assert.equal(result.conflicting_attempt_rows, 3); assert.equal(result.ambiguous_completion_rows, 2); assert.equal(result.unmatched_completion_rows, 1); assert.equal(result.missing_completion_rows, 1); assert.deepEqual(result.coverage_exceptions, ["ambiguous_completion", "conflicting_attempt", "duplicate_attempt", "missing_completion", "unmatched_completion"]);
});

test("empty capture has null cutover and an immutable exact receipt", () => {
  const result = reconcileLocalAgentUsageCapture(SOURCE, [], chain([event(id("a"), "2026-08-10T00:00:00Z")]));
  assert.deepEqual(result, { schema_version: 1, source_id: SOURCE, status: "empty", cutover_at: null, attempted_rows: 0, success_rows: 0, failed_rows: 0, missing_completion_rows: 0, unmatched_completion_rows: 0, duplicate_attempt_rows: 0, conflicting_attempt_rows: 0, ambiguous_completion_rows: 0, coverage_exceptions: ["capture_not_started"] });
  assert.ok(Object.isFrozen(result) && Object.isFrozen(result.coverage_exceptions)); assert.deepEqual(Object.keys(result), ["schema_version", "source_id", "status", "cutover_at", "attempted_rows", "success_rows", "failed_rows", "missing_completion_rows", "unmatched_completion_rows", "duplicate_attempt_rows", "conflicting_attempt_rows", "ambiguous_completion_rows", "coverage_exceptions"]);
});

test("rejects malformed, sparse, extra-key, and proxy inputs with redacted errors", () => {
  const valid = [attempt(id("a"))], good = chain([]), accessor = []; let touched = false; Object.defineProperty(accessor, "0", { enumerable: true, get() { touched = true; throw new Error("HOSTILE"); } }); accessor.length = 1; const bad = [[null], [{ ...valid[0], secret: "HOSTILE" }], Object.assign([], { 1: valid[0], length: 2 }), new Proxy(valid, {}), accessor];
  assert.throws(() => reconcileLocalAgentUsageCapture("bad", valid, good), /^Error: cfo_local_agent_capture_invalid:/);
  for (const rows of bad) assert.throws(() => reconcileLocalAgentUsageCapture(SOURCE, rows, good), error => /^cfo_local_agent_capture_invalid:/.test(error.message) && !error.message.includes("HOSTILE"));
  assert.equal(touched, false);
});

test("rejects chain attribution, ordering, and derived-coverage drift", () => {
  const first = event(id("a"), "2026-08-11T02:00:00Z"), bad = chain([first]); bad.coverage_exceptions = ["missing_usage"]; assert.throws(() => reconcileLocalAgentUsageCapture(SOURCE, [attempt(id("a"))], bad), /^Error: cfo_local_agent_capture_invalid:invalid_chain$/);
  const wrong = chain([{ ...first, financial_unit_id: "life_manager_saas" }]); assert.throws(() => reconcileLocalAgentUsageCapture(SOURCE, [attempt(id("a"))], wrong), /^Error: cfo_local_agent_capture_invalid:invalid_chain$/);
});
