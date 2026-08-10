"use strict";

const crypto = require("node:crypto");
const { types: { isProxy } } = require("node:util");
const { createCfoSupabaseRpc } = require("./cfo-supabase-rpc.js");
const { fail, plain, exact, freeze } = createCfoSupabaseRpc("cfo_local_agent_source_invalid:");
const decodeUtf8 = new TextDecoder("utf-8", { fatal: true });
const SOURCE_IDS = new Set(["life_manager_agent_usage", "anicca_agent_usage"]);
const OPTION_KEYS = new Set(["source_id", "prior_state"]);
const STATE_KEYS = new Set(["source_id", "byte_offset", "prefix_sha256", "discovered_rows"]);
const hash = (bytes) => crypto.createHash("sha256").update(bytes).digest("hex");
const rowRef = (sourceId, offset) => hash(Buffer.from(`cfo-local-agent-row-v1\0${sourceId}\0${offset}`, "utf8"));
const rowCount = (bytes) => { let count = 0; let start = 0; for (let i = 0; i < bytes.length; i++) if (bytes[i] === 10) { if (i > start) count++; start = i + 1; } return count; };
const cloneState = (state) => state === null ? null : { source_id: state.source_id, byte_offset: state.byte_offset, prefix_sha256: state.prefix_sha256, discovered_rows: state.discovered_rows };
const receipt = (pairs, state, exceptions) => freeze({ pairs, state: cloneState(state), coverage_exceptions: [...new Set(exceptions)].sort() });
function scanLocalAgentUsageSource(data, options) {
  if (isProxy(data) || !Buffer.isBuffer(data)) fail("invalid_source_data");
  exact(options, OPTION_KEYS, "invalid_options");
  const sourceId = options.source_id;
  if (!SOURCE_IDS.has(sourceId)) fail("invalid_source_id");
  const prior = options.prior_state;
  if (prior !== null) {
    exact(prior, STATE_KEYS, "invalid_prior_state");
    const { source_id: priorSource, byte_offset: offset, prefix_sha256: prefixHash, discovered_rows: discovered } = prior;
    if (priorSource !== sourceId || !Number.isSafeInteger(offset) || offset < 0 || typeof prefixHash !== "string" || !/^[0-9a-f]{64}$/.test(prefixHash) || !Number.isSafeInteger(discovered) || discovered < 0) fail("invalid_prior_state");
    if (data.length < offset) return receipt([], prior, ["source_truncated"]);
    const prefix = Buffer.prototype.subarray.call(data, 0, offset);
    if (hash(prefix) !== prefixHash) return receipt([], prior, ["source_rewritten"]);
    if (offset > 0 && data[offset - 1] !== 10) fail("invalid_prior_state");
    if (rowCount(prefix) !== discovered) fail("invalid_prior_state");
  }
  const start = prior === null ? 0 : prior.byte_offset;
  let cursor = start; let discovered = prior === null ? 0 : prior.discovered_rows; const pairs = [];
  while (cursor < data.length) {
    const newline = Buffer.prototype.indexOf.call(data, 10, cursor);
    if (newline < 0) break;
    if (newline === cursor) { cursor++; continue; }
    let input;
    try { input = JSON.parse(decodeUtf8.decode(Buffer.prototype.subarray.call(data, cursor, newline))); } catch { return receipt([], prior, ["invalid_source_row"]); }
    if (!plain(input)) return receipt([], prior, ["invalid_source_row"]);
    pairs.push({ input, context: { source_row_ref: rowRef(sourceId, cursor) } });
    discovered++; cursor = newline + 1;
  }
  const state = { source_id: sourceId, byte_offset: cursor, prefix_sha256: hash(Buffer.prototype.subarray.call(data, 0, cursor)), discovered_rows: discovered };
  return receipt(pairs, state, cursor < data.length ? ["incomplete_tail"] : []);
}

module.exports = { scanLocalAgentUsageSource };
