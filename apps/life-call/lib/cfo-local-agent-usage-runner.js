"use strict";
const fs = require("node:fs"), os = require("node:os"), path = require("node:path");
const { readLocalAgentUsageChain } = require("./cfo-local-agent-usage-chain.js");
const { collectAndWriteLocalAgentUsageBatch } = require("./cfo-local-agent-usage-batch-store.js");
const { timestamp } = require("./cfo-supabase-rpc.js").createCfoSupabaseRpc("cfo_local_agent_usage_runner_invalid:");
const PREFIX = "cfo_local_agent_usage_runner_invalid:", IDS = ["life_manager_agent_usage", "anicca_agent_usage"];
const INTERNAL = new WeakSet();

function fail(reason) { const error = new Error(`${PREFIX}${reason}`); INTERNAL.add(error); throw error; }
function internal(error) { return error !== null && (typeof error === "object" || typeof error === "function") && INTERNAL.has(error); }
function freeze(value, seen = new WeakSet()) { if (value === null || typeof value !== "object" || seen.has(value)) return value; seen.add(value); Object.values(value).forEach(child => freeze(child, seen)); return Object.freeze(value); }
function dir(value, reason) { if (typeof value !== "string" || value.length === 0 || value.trim() !== value || !path.isAbsolute(value) || path.parse(value).root === value || path.resolve(value) !== value) fail(reason); return value; }
function plain(value) { try { return value !== null && typeof value === "object" && !Array.isArray(value) && Object.getPrototypeOf(value) === Object.prototype; } catch { return false; } }
function configure(options) {
  try {
    if (!plain(options)) fail("invalid_options"); const keys = Reflect.ownKeys(options), allowed = new Set(["env", "home", "now", "readFile", "readChain", "writeBatch"]);
    if (keys.some(key => typeof key !== "string" || !allowed.has(key) || !Object.getOwnPropertyDescriptor(options, key)?.enumerable)) fail("invalid_options");
    const env = options.env === undefined ? process.env : options.env; if (env === null || typeof env !== "object" || Array.isArray(env)) fail("invalid_options");
    let home; try { home = options.home === undefined ? os.homedir() : options.home; } catch { fail("invalid_home"); } dir(home, "invalid_home");
    const configuredRoot = env.LIFE_MANAGER_STATE_HOME, stateRoot = configuredRoot === undefined ? path.join(home, ".local/state/life-manager") : dir(configuredRoot, "invalid_state_root");
    ["readFile", "readChain", "writeBatch"].forEach(key => { if (options[key] !== undefined && typeof options[key] !== "function") fail("invalid_options"); });
    return { home, stateRoot, now: options.now, readFile: options.readFile || fs.readFileSync, readChain: options.readChain || readLocalAgentUsageChain, writeBatch: options.writeBatch || collectAndWriteLocalAgentUsageBatch };
  } catch (error) { if (internal(error)) throw error; fail("invalid_options"); }
}
function capture(now) {
  if (now !== undefined && typeof now !== "function") fail("invalid_clock");
  try { let value = (now || (() => new Date().toISOString()))(); if (value instanceof Date) value = value.toISOString(); if (!timestamp(value)) fail("invalid_clock"); return value; } catch (error) { if (internal(error)) throw error; fail("invalid_clock"); }
}
function emptySource(sourceId, status, exception) { return { source_id: sourceId, status, record_id: null, byte_offset: null, event_count: null, mapping_id: null, coverage_exceptions: [exception] }; }
function source(config, sourceId, collectedAt) {
  let chain;
  try { chain = config.readChain(config.stateRoot, sourceId); if (!chain || (chain.status !== "empty" && chain.status !== "ready")) throw new Error(); } catch { return emptySource(sourceId, "failed", "local_state_failure"); }
  let bytes;
  try { bytes = config.readFile(sourceId === IDS[0] ? path.join(config.stateRoot, "telemetry/agent-usage.jsonl") : path.join(config.home, ".local/state/anicca/telemetry/agent-usage.jsonl")); if (!Buffer.isBuffer(bytes)) throw new Error(); } catch { return emptySource(sourceId, "unavailable", "source_unreadable"); }
  try {
    const result = config.writeBatch(config.stateRoot, collectedAt, sourceId, bytes, chain.status === "empty" ? null : chain.source_state);
    if (!plain(result) || typeof result.record_id !== "string" || result.record_id.length === 0 || result.source_id !== sourceId || !Number.isSafeInteger(result.byte_offset) || result.byte_offset < 0 || !Number.isSafeInteger(result.event_count) || result.event_count < 0 || typeof result.mapping_id !== "string" || result.mapping_id.length === 0) throw new Error();
    return { source_id: sourceId, status: "published", record_id: result.record_id, byte_offset: result.byte_offset, event_count: result.event_count, mapping_id: result.mapping_id, coverage_exceptions: [] };
  } catch { return emptySource(sourceId, "failed", "local_state_failure"); }
}
function runLocalAgentUsageCollection(options = {}) {
  const config = configure(options), collectedAt = capture(config.now), sources = IDS.map(sourceId => source(config, sourceId, collectedAt)), coverage_exceptions = [...new Set(sources.flatMap(item => item.coverage_exceptions))].sort();
  return freeze({ status: sources.every(item => item.status === "published") ? "complete" : "partial", collected_at: collectedAt, sources, coverage_exceptions });
}

module.exports = { runLocalAgentUsageCollection };
