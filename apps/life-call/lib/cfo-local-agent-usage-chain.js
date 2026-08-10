"use strict";
const fs = require("node:fs"), path = require("node:path"), crypto = require("node:crypto");
const { canonicalJson } = require("./cfo-registry.js");
const { createCfoSupabaseRpc } = require("./cfo-supabase-rpc.js");
const { fail, freeze, internal, plain, timestamp } = createCfoSupabaseRpc("cfo_local_agent_usage_chain_invalid:");
const SOURCES = new Set(["life_manager_agent_usage", "anicca_agent_usage"]), HEX = /^[0-9a-f]{64}$/;
const COUNTS = ["discovered_rows", "accepted_rows", "duplicate_rows", "conflicting_rows", "missing_usage_rows", "runner_collision_groups", "attributed_rows", "unattributed_rows"];
const RECORD = ["schema_version", "collected_at", "mapping_id", "prior_source_state", "source_state", "events", "delta_counts", "coverage_exceptions"], STATE = ["schema_version", "source_id", "byte_offset", "prefix_sha256", "observed_file_size"], EXCEPTIONS = new Set(["partial_tail", "invalid_source_row", "source_rewritten", "source_truncated", "conflicting_usage", "missing_usage", "runner_identity_collision", "unattributed_usage"]), SOURCE_DEFECTS = new Set(["partial_tail", "invalid_source_row", "source_rewritten", "source_truncated"]);
const EVENT = ["schema_version", "source_ledger", "source_event_id", "runner_event_id", "occurred_at", "provider", "provider_name", "request_model", "upstream_model", "run", "financial_unit_id", "attribution_status", "measurement", "token_value_basis", "tokens", "coverage_status"], RUN = ["attempt", "loop", "status", "task_label"], TOKENS = ["cache_creation_input", "cached_input", "input", "output", "reasoning_output", "total"];
const hash = bytes => crypto.createHash("sha256").update(bytes).digest("hex"), same = (a, b) => canonicalJson(a) === canonicalJson(b), empty = () => freeze({ status: "empty", source_state: null, record_count: 0, events: [], counts: Object.fromEntries(COUNTS.map(key => [key, 0])), coverage_exceptions: [] });
function exact(value, keys) { return plain(value) && Reflect.ownKeys(value).length === keys.length && Reflect.ownKeys(value).every(key => typeof key === "string" && keys.includes(key)); }
function validState(value, sourceId, nullable = true) { return value === null && nullable || exact(value, STATE) && value.schema_version === 1 && value.source_id === sourceId && Number.isSafeInteger(value.byte_offset) && value.byte_offset >= 0 && Number.isSafeInteger(value.observed_file_size) && value.observed_file_size >= value.byte_offset && HEX.test(value.prefix_sha256); }
function text(value) { return typeof value === "string" && value.length > 0 && value.trim() === value; }
function validEvent(event) {
  if (!exact(event, EVENT) || event.schema_version !== 1 || event.source_ledger !== "local_agent_usage" || !/^local_agent_usage:(?!0{64}$)[0-9a-f]{64}$/.test(event.source_event_id) || !/^[0-9a-f]{24}$/.test(event.runner_event_id) || !timestamp(event.occurred_at)) return false;
  if (!["provider", "provider_name", "request_model"].every(key => text(event[key])) || event.upstream_model !== null && !text(event.upstream_model) || !exact(event.run, RUN) || !text(event.run.loop) || !text(event.run.task_label) || !["success", "failed"].includes(event.run.status) || !Number.isSafeInteger(event.run.attempt) || event.run.attempt < 1) return false;
  if (!(event.financial_unit_id === null || text(event.financial_unit_id)) || event.attribution_status !== (event.financial_unit_id === null ? "unattributed" : "attributed") || !["provider_reported", "unavailable"].includes(event.measurement) || event.token_value_basis !== (event.measurement === "provider_reported" ? "runner_normalized_provider_usage" : "unavailable") || event.coverage_status !== (event.measurement === "provider_reported" ? "covered" : "missing_usage") || !exact(event.tokens, TOKENS)) return false;
  return TOKENS.every(key => event.measurement === "unavailable" ? event.tokens[key] === null : Number.isSafeInteger(event.tokens[key]) && event.tokens[key] >= 0); }
function validRecord(record, sourceId) {
  if (!exact(record, RECORD) || record.schema_version !== 1 || record.mapping_id !== "local_agent_usage_v1" || !timestamp(record.collected_at) || !validState(record.prior_source_state, sourceId) || !validState(record.source_state, sourceId, false) || !Array.isArray(record.events) || record.events.some(event => !validEvent(event)) || !exact(record.delta_counts, COUNTS) || !COUNTS.every(key => Number.isSafeInteger(record.delta_counts[key]) && record.delta_counts[key] >= 0) || !Array.isArray(record.coverage_exceptions)) return false;
  if (record.events.length !== record.delta_counts.accepted_rows || record.delta_counts.discovered_rows !== record.delta_counts.accepted_rows + record.delta_counts.duplicate_rows + record.delta_counts.conflicting_rows || new Set(record.coverage_exceptions).size !== record.coverage_exceptions.length || record.coverage_exceptions.some((value, index, list) => !EXCEPTIONS.has(value) || index > 0 && list[index - 1] >= value)) return false;
  const missing = record.events.filter(event => event.coverage_status === "missing_usage").length, attributed = record.events.filter(event => event.attribution_status === "attributed").length, runners = new Map();
  for (const event of record.events) { const ids = runners.get(event.runner_event_id) || new Set(); ids.add(event.source_event_id); runners.set(event.runner_event_id, ids); }
  const collision = [...runners.values()].filter(ids => ids.size > 1).length, expected = new Set(record.coverage_exceptions);
  if (record.delta_counts.missing_usage_rows !== missing || record.delta_counts.attributed_rows !== attributed || record.delta_counts.unattributed_rows !== record.events.length - attributed || record.delta_counts.runner_collision_groups !== collision || (record.delta_counts.conflicting_rows > 0) !== expected.has("conflicting_usage") || (missing > 0) !== expected.has("missing_usage") || (collision > 0) !== expected.has("runner_identity_collision") || (record.events.length - attributed > 0) !== expected.has("unattributed_usage")) return false;
  return true; }
function signature(record) { const { collected_at, _id, ...content } = record; return canonicalJson(content); }
function zeroLoop(record) { return same(record.prior_source_state, record.source_state) && record.events.length === 0 && COUNTS.every(key => record.delta_counts[key] === 0); }
function causal(prior, next) { return prior === null || next.byte_offset >= prior.byte_offset && next.observed_file_size >= prior.observed_file_size && !same(prior, next); }
function readLocalAgentUsageChain(stateRoot, sourceId) {
  if (typeof stateRoot !== "string" || !path.isAbsolute(stateRoot) || path.resolve(stateRoot) !== stateRoot || path.parse(stateRoot).root === stateRoot) fail("invalid_state_root");
  if (!SOURCES.has(sourceId)) fail("invalid_source");
  try {
    const dir = path.join(stateRoot, "cfo/local-agent-usage", sourceId);
    if (!fs.existsSync(dir)) return empty();
    const records = [];
    for (const name of fs.readdirSync(dir)) { if (/^\..+\.tmp$/.test(name)) continue; const match = /^([0-9a-f]{64})\.json$/.exec(name); if (!match) fail("read_failed");
      const bytes = fs.readFileSync(path.join(dir, name)); let record; try { record = JSON.parse(bytes); } catch { fail("read_failed"); } if (hash(bytes) !== match[1] || !validRecord(record, sourceId)) fail("read_failed"); records.push({ ...record, _id: match[1] }); } if (!records.length) return empty();
    records.sort((a, b) => Date.parse(a.collected_at) - Date.parse(b.collected_at) || a._id.localeCompare(b._id)); const unique = [...new Map(records.map(record => [signature(record), record])).values()]; let state = null, accepted = [], latest = { coverage_exceptions: [] };
    while (true) { const candidates = unique.filter(record => same(record.prior_source_state, state)), loops = candidates.filter(zeroLoop), advances = candidates.filter(record => !loops.includes(record));
      if (!candidates.length) break; if (advances.length > 1) fail("read_failed");
      loops.sort((a, b) => Date.parse(a.collected_at) - Date.parse(b.collected_at) || a._id.localeCompare(b._id)); accepted.push(...loops); if (loops.length) latest = loops[loops.length - 1];
      if (!advances.length) break; if (!causal(state, advances[0].source_state)) fail("read_failed"); accepted.push(advances[0]); latest = advances[0]; state = advances[0].source_state;
    }
    if (accepted.length !== unique.length) fail("read_failed");
    const events = accepted.flatMap(record => record.events), seen = new Set(); for (const event of events) { if (seen.has(event.source_event_id)) fail("read_failed"); seen.add(event.source_event_id); } events.sort((a, b) => a.source_event_id.localeCompare(b.source_event_id));
    const counts = Object.fromEntries(COUNTS.map(key => [key, 0])); for (const record of accepted) for (const key of ["discovered_rows", "duplicate_rows", "conflicting_rows"]) counts[key] += record.delta_counts[key]; counts.accepted_rows = events.length; counts.missing_usage_rows = events.filter(event => event.coverage_status === "missing_usage").length; counts.attributed_rows = events.filter(event => event.attribution_status === "attributed").length; counts.unattributed_rows = events.length - counts.attributed_rows;
    const runnerGroups = new Map(); for (const event of events) { const ids = runnerGroups.get(event.runner_event_id) || new Set(); ids.add(event.source_event_id); runnerGroups.set(event.runner_event_id, ids); } counts.runner_collision_groups = [...runnerGroups.values()].filter(ids => ids.size > 1).length;
    const exceptions = new Set(); if (counts.conflicting_rows) exceptions.add("conflicting_usage"); if (counts.missing_usage_rows) exceptions.add("missing_usage"); if (counts.runner_collision_groups) exceptions.add("runner_identity_collision"); if (counts.unattributed_rows) exceptions.add("unattributed_usage"); for (const value of latest.coverage_exceptions) if (SOURCE_DEFECTS.has(value)) exceptions.add(value);
    return freeze({ status: "ready", source_state: state, record_count: accepted.length, events, counts, coverage_exceptions: [...exceptions].sort() });
  } catch (error) { if (internal(error)) throw error; fail("read_failed"); }
}
module.exports = { readLocalAgentUsageChain };
