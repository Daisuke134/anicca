"use strict";
const { types: { isProxy } } = require("node:util");
const { canonicalJson } = require("./cfo-registry.js");
const { createCfoSupabaseRpc } = require("./cfo-supabase-rpc.js");
const { fail, internal, exact, timestamp, freeze } = createCfoSupabaseRpc("cfo_local_agent_capture_invalid:");
const SOURCES = new Set(["life_manager_agent_usage", "anicca_agent_usage"]), HEX = /^[0-9a-f]{24}$/, SHA = /^[0-9a-f]{64}$/, UTC = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)$/;
const ATTEMPT = ["version", "event_id", "timestamp", "loop", "task_label", "attempt", "provider", "model"], RECEIPT = ["status", "source_state", "record_count", "events", "counts", "coverage_exceptions"], STATE = ["schema_version", "source_id", "byte_offset", "prefix_sha256", "observed_file_size"], COUNTS = ["discovered_rows", "accepted_rows", "duplicate_rows", "conflicting_rows", "missing_usage_rows", "runner_collision_groups", "attributed_rows", "unattributed_rows"];
const EVENT = ["schema_version", "source_ledger", "source_event_id", "runner_event_id", "occurred_at", "provider", "provider_name", "request_model", "upstream_model", "run", "financial_unit_id", "attribution_status", "measurement", "token_value_basis", "tokens", "coverage_status"], RUN = ["attempt", "loop", "status", "task_label"], TOKENS = ["cache_creation_input", "cached_input", "input", "output", "reasoning_output", "total"], CHAIN_EXCEPTIONS = new Set(["partial_tail", "invalid_source_row", "source_rewritten", "source_truncated", "conflicting_usage", "missing_usage", "runner_identity_collision", "unattributed_usage"]);
function arrayShape(value) {
  if (isProxy(value) || !Array.isArray(value) || Object.getPrototypeOf(value) !== Array.prototype) fail("invalid_input");
  let own; try { own = Reflect.ownKeys(value); } catch { fail("invalid_input"); }
  const length = value.length, descriptor = Object.getOwnPropertyDescriptor(value, "length");
  if (own.length !== length + 1 || !descriptor || !Object.hasOwn(descriptor, "value") || descriptor.value !== length || descriptor.enumerable) fail("invalid_input");
  for (let index = 0; index < length; index++) { const item = Object.getOwnPropertyDescriptor(value, String(index)); if (!item || !Object.hasOwn(item, "value") || !item.enumerable) fail("invalid_input"); }
  for (const key of own) if (key !== "length" && (typeof key !== "string" || !/^(0|[1-9]\d*)$/.test(key) || Number(key) >= length)) fail("invalid_input");
}
function shape(value, keys) { exact(value, new Set(keys)); }
function text(value) { return typeof value === "string" && value.length > 0 && value.trim() === value; }
function safe(value) { return Number.isSafeInteger(value) && value >= 0; }
function validUtc(value) { return typeof value === "string" && UTC.test(value) && timestamp(value); }
function validCounts(counts, events, exceptions) {
  const runners = new Map(), missing = events.filter(event => event.coverage_status === "missing_usage").length, attributed = events.filter(event => event.attribution_status === "attributed").length;
  for (const event of events) { const ids = runners.get(event.runner_event_id) || new Set(); ids.add(event.source_event_id); runners.set(event.runner_event_id, ids); }
  const collision = [...runners.values()].filter(ids => ids.size > 1).length, derived = new Set(); if (missing) derived.add("missing_usage"); if (collision) derived.add("runner_identity_collision"); if (events.length - attributed) derived.add("unattributed_usage"); if (counts.conflicting_rows) derived.add("conflicting_usage");
  return counts.accepted_rows === events.length && counts.discovered_rows === counts.accepted_rows + counts.duplicate_rows + counts.conflicting_rows && counts.missing_usage_rows === missing && counts.attributed_rows === attributed && counts.unattributed_rows === events.length - attributed && counts.runner_collision_groups === collision && ["missing_usage", "runner_identity_collision", "unattributed_usage", "conflicting_usage"].every(key => exceptions.includes(key) === derived.has(key));
}
function validate(sourceId, rows, chain) {
  if (!SOURCES.has(sourceId)) fail("invalid_input");
  arrayShape(rows); for (const row of rows) shape(row, ATTEMPT);
  shape(chain, RECEIPT); arrayShape(chain.events); arrayShape(chain.coverage_exceptions); shape(chain.counts, COUNTS);
  if (!["ready", "empty"].includes(chain.status) || !safe(chain.record_count) || chain.status === "ready" && chain.record_count < 1) fail("invalid_input");
  for (const count of Object.values(chain.counts)) if (!safe(count)) fail("invalid_input");
  if (chain.status === "ready") { shape(chain.source_state, STATE); if (chain.source_state.schema_version !== 1 || chain.source_state.source_id !== sourceId || !safe(chain.source_state.byte_offset) || !safe(chain.source_state.observed_file_size) || chain.source_state.observed_file_size < chain.source_state.byte_offset || typeof chain.source_state.prefix_sha256 !== "string" || !SHA.test(chain.source_state.prefix_sha256)) fail("invalid_input"); }
  else if (chain.source_state !== null || chain.record_count !== 0 || chain.events.length !== 0 || chain.coverage_exceptions.length || Object.values(chain.counts).some(Boolean)) fail("invalid_input");
  for (const event of chain.events) shape(event, EVENT);
  for (const event of chain.events) { shape(event.run, RUN); shape(event.tokens, TOKENS); }
  for (const row of rows) if (row.version !== 1 || typeof row.event_id !== "string" || !HEX.test(row.event_id) || !validUtc(row.timestamp) || !safe(row.attempt) || row.attempt < 1 || ![row.loop, row.task_label, row.provider, row.model].every(text)) fail("invalid_input");
  let previous = ""; for (const value of chain.coverage_exceptions) if (typeof value !== "string" || !CHAIN_EXCEPTIONS.has(value) || value <= previous) fail("invalid_input"); else previous = value;
  for (const event of chain.events) {
    if (event.schema_version !== 1 || event.source_ledger !== "local_agent_usage" || typeof event.source_event_id !== "string" || !event.source_event_id.startsWith("local_agent_usage:") || typeof event.runner_event_id !== "string" || !HEX.test(event.runner_event_id) || !timestamp(event.occurred_at) || event.occurred_at !== new Date(event.occurred_at).toISOString() || !["success", "failed"].includes(event.run.status) || !safe(event.run.attempt) || event.run.attempt < 1 || ![event.run.loop, event.run.task_label].every(text) || !["covered", "missing_usage"].includes(event.coverage_status) || !["attributed", "unattributed"].includes(event.attribution_status)) fail("invalid_input");
    for (const value of Object.values(event.tokens)) if (value !== null && !safe(value)) fail("invalid_input");
  }
  if (!validCounts(chain.counts, chain.events, chain.coverage_exceptions)) fail("invalid_input");
}
function reconcileLocalAgentCapture(sourceId, attemptRows, usageChain) {
  try {
    validate(sourceId, attemptRows, usageChain);
    if (!attemptRows.length) return freeze({ schema_version: 1, source_id: sourceId, status: "empty", cutover_at: null, attempted_rows: 0, success_rows: 0, failed_rows: 0, missing_completion_rows: 0, unmatched_completion_rows: 0, duplicate_attempt_rows: 0, conflicting_attempt_rows: 0, ambiguous_completion_rows: 0, coverage_exceptions: ["capture_not_started"] });
    let cutoverAt = attemptRows[0].timestamp, cutoverMs = Date.parse(cutoverAt);
    for (const row of attemptRows) { const instant = Date.parse(row.timestamp); if (instant < cutoverMs || instant === cutoverMs && row.timestamp < cutoverAt) { cutoverAt = row.timestamp; cutoverMs = instant; } }
    const groups = new Map();
    for (const row of attemptRows) { const variants = groups.get(row.event_id) || new Map(), signature = canonicalJson(row), prior = variants.get(signature); if (prior) prior.count++; else variants.set(signature, { count: 1, row }); groups.set(row.event_id, variants); }
    const usable = new Map(); let duplicate = 0, conflict = 0;
    for (const [id, variants] of groups) { if (variants.size > 1) { conflict += [...variants.values()].reduce((sum, item) => sum + item.count, 0); continue; } const item = variants.values().next().value; duplicate += item.count - 1; usable.set(id, item.row); }
    const completions = usageChain.events.filter(event => Date.parse(event.occurred_at) >= cutoverMs); let success = 0, failed = 0, missing = 0, ambiguous = 0;
    for (const [id, row] of usable) { const matches = completions.filter(event => event.runner_event_id === id && Date.parse(event.occurred_at) >= Date.parse(row.timestamp)); if (matches.length === 1) (matches[0].run.status === "success" ? success++ : failed++); else { missing++; ambiguous += matches.length > 1 ? matches.length : 0; } }
    let unmatched = 0; for (const event of completions) { const row = usable.get(event.runner_event_id); if (!row || Date.parse(event.occurred_at) < Date.parse(row.timestamp)) unmatched++; }
    const exceptions = []; if (ambiguous) exceptions.push("ambiguous_completion"); if (conflict) exceptions.push("conflicting_attempt"); if (duplicate) exceptions.push("duplicate_attempt"); if (missing) exceptions.push("missing_completion"); if (unmatched) exceptions.push("unmatched_completion"); if (usageChain.coverage_exceptions.length) exceptions.push("usage_chain_incomplete");
    return freeze({ schema_version: 1, source_id: sourceId, status: exceptions.length ? "partial" : "complete", cutover_at: cutoverAt, attempted_rows: usable.size, success_rows: success, failed_rows: failed, missing_completion_rows: missing, unmatched_completion_rows: unmatched, duplicate_attempt_rows: duplicate, conflicting_attempt_rows: conflict, ambiguous_completion_rows: ambiguous, coverage_exceptions: exceptions });
  } catch (error) { if (internal(error)) throw error; fail("invalid_input"); }
}
module.exports = { reconcileLocalAgentCapture };
