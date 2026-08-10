"use strict";
const fs = require("node:fs");
const path = require("node:path");
const { randomUUID } = require("node:crypto");
const { types: { isProxy } } = require("node:util");
const { createCfoSupabaseRpc } = require("./cfo-supabase-rpc.js");
const { fail, exact, timestamp, freeze } = createCfoSupabaseRpc("cfo_local_agent_checkpoint_invalid:");
const SOURCE_IDS = new Set(["life_manager_agent_usage", "anicca_agent_usage"]);
const BATCH_KEYS = new Set(["events", "source_state", "mapping_id", "counts", "coverage_exceptions"]);
const STATE_KEYS = new Set(["source_id", "byte_offset", "prefix_sha256", "discovered_rows"]);
const COUNT_KEYS = new Set(["discovered_rows", "accepted_rows", "duplicate_rows", "conflicting_rows", "missing_usage_rows", "runner_collision_groups", "attributed_rows", "unattributed_rows"]);
const COUNT_FIELDS = [...COUNT_KEYS];
const EXCEPTIONS = new Set(["conflicting_usage", "incomplete_tail", "invalid_source_row", "missing_usage", "runner_identity_collision", "source_rewritten", "source_truncated", "unattributed_usage"]);
const SCANNER_EXCEPTIONS = new Set(["incomplete_tail", "invalid_source_row", "source_rewritten", "source_truncated"]);
function validCount(value) { return Number.isSafeInteger(value) && value >= 0; }
const exactArray = (value) => Array.isArray(value) && !isProxy(value) && Object.getPrototypeOf(value) === Array.prototype && Object.keys(value).length === value.length && Reflect.ownKeys(value).length === value.length + 1 && Reflect.ownKeys(value).every((key) => key === "length" || Object.prototype.propertyIsEnumerable.call(value, key) && Object.prototype.hasOwnProperty.call(Object.getOwnPropertyDescriptor(value, key) || {}, "value"));
function validateOptions(options) {
  if (options === undefined) return fs.fsyncSync;
  exact(options, new Set(["fsyncImpl"]), "invalid_options");
  if (typeof options.fsyncImpl !== "function" || isProxy(options.fsyncImpl)) fail("invalid_options");
  return options.fsyncImpl;
}
function validateBatch(batch) {
  exact(batch, BATCH_KEYS, "invalid_batch");
  if (!exactArray(batch.events)) fail("invalid_batch");
  exact(batch.source_state, STATE_KEYS, "invalid_batch");
  const source = batch.source_state;
  if (!SOURCE_IDS.has(source.source_id) || !validCount(source.byte_offset) || typeof source.prefix_sha256 !== "string" || !/^[0-9a-f]{64}$/.test(source.prefix_sha256) || !validCount(source.discovered_rows)) fail("invalid_batch");
  if (batch.mapping_id !== "local_agent_usage_v1") fail("invalid_batch");
  exact(batch.counts, COUNT_KEYS, "invalid_batch");
  const counts = batch.counts;
  if (!COUNT_FIELDS.every((field) => validCount(counts[field]))) fail("invalid_batch");
  const discovered = counts.accepted_rows + counts.duplicate_rows + counts.conflicting_rows;
  if (!Number.isSafeInteger(discovered) || discovered !== counts.discovered_rows || counts.accepted_rows !== counts.attributed_rows + counts.unattributed_rows || counts.missing_usage_rows > counts.accepted_rows || counts.runner_collision_groups > Math.floor(counts.accepted_rows / 2) || source.discovered_rows < counts.discovered_rows || batch.events.length !== counts.accepted_rows) fail("invalid_batch");
  const exceptions = batch.coverage_exceptions;
  if (!exactArray(exceptions) || exceptions.some((item, index) => typeof item !== "string" || !EXCEPTIONS.has(item) || index > 0 && exceptions[index - 1] >= item) || new Set(exceptions).size !== exceptions.length) fail("invalid_batch");
  const scanner = exceptions.filter((item) => SCANNER_EXCEPTIONS.has(item));
  if (scanner.length > 1 || ["source_truncated", "source_rewritten", "invalid_source_row"].some((item) => exceptions.includes(item)) && counts.discovered_rows !== 0) fail("invalid_batch");
  for (const [field, exception] of [["conflicting_rows", "conflicting_usage"], ["missing_usage_rows", "missing_usage"], ["runner_collision_groups", "runner_identity_collision"], ["unattributed_rows", "unattributed_usage"]]) if ((counts[field] > 0) !== exceptions.includes(exception)) fail("invalid_batch");
  return source;
}
function writeLocalAgentUsageCheckpoint(stateRoot, collectedAt, batch, options) {
  if (typeof stateRoot !== "string" || stateRoot.length === 0 || stateRoot.trim() !== stateRoot || stateRoot.includes("\0") || !path.isAbsolute(stateRoot) || path.parse(stateRoot).root === stateRoot) fail("invalid_state_root");
  if (!timestamp(collectedAt)) fail("invalid_collected_at");
  const source = validateBatch(batch); const fsyncImpl = validateOptions(options);
  const directory = path.join(stateRoot, "cfo", "local-agent-usage"); const finalPath = path.join(directory, `${source.source_id}.json`); const payload = { schema_version: 1, collected_at: collectedAt, mapping_id: batch.mapping_id, source_state: { source_id: source.source_id, byte_offset: source.byte_offset, prefix_sha256: source.prefix_sha256, discovered_rows: source.discovered_rows }, counts: Object.fromEntries(COUNT_FIELDS.map((field) => [field, batch.counts[field]])), coverage_exceptions: [...batch.coverage_exceptions] };
  const body = `${JSON.stringify(payload)}\n`; const temporaryPath = path.join(directory, `.${source.source_id}.${randomUUID()}.tmp`); let fd;
  try {
    fs.mkdirSync(directory, { recursive: true, mode: 0o700 }); fs.chmodSync(directory, 0o700); fd = fs.openSync(temporaryPath, "wx", 0o600); fs.chmodSync(temporaryPath, 0o600); fs.writeFileSync(fd, body, "utf8"); fsyncImpl(fd); fs.closeSync(fd); fd = undefined; fs.renameSync(temporaryPath, finalPath);
  } catch {
    if (fd !== undefined) try { fs.closeSync(fd); } catch {}
    try { fs.unlinkSync(temporaryPath); } catch {}
    fail("write_failed");
  }
  return freeze({ source_id: source.source_id, byte_offset: source.byte_offset, discovered_rows: source.discovered_rows, mapping_id: batch.mapping_id });
}

module.exports = { writeLocalAgentUsageCheckpoint };
