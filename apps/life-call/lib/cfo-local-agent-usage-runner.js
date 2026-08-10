"use strict";
const fs = require("node:fs"), os = require("node:os"), path = require("node:path"), { types: { isProxy } } = require("node:util");
const { readLocalAgentUsageChain } = require("./cfo-local-agent-usage-chain.js"); const { collectAndWriteLocalAgentUsageBatch } = require("./cfo-local-agent-usage-batch-store.js");
const { reconcileLocalAgentCapture } = require("./cfo-local-agent-capture-reconciliation.js");
const ERROR = "cfo_local_agent_usage_runner_invalid:", LM = "life_manager_agent_usage", AN = "anicca_agent_usage", OPTION_KEYS = ["home", "env", "now", "readFile", "readChain", "writeBatch"], CHAIN_KEYS = ["status", "source_state", "record_count", "events", "counts", "coverage_exceptions"], CURSOR_KEYS = ["schema_version", "source_id", "byte_offset", "prefix_sha256", "observed_file_size"], WRITER_KEYS = ["record_id", "source_id", "byte_offset", "event_count", "mapping_id"], HEX = /^[0-9a-f]{64}$/;
const SOURCES = [{ id: LM, file: (home, root) => path.join(root, "telemetry", "agent-usage.jsonl") }, { id: AN, file: home => path.join(home, ".local", "state", "anicca", "telemetry", "agent-usage.jsonl") }];
const attemptFile = (source, home, root) => path.join(path.dirname(source.file(home, root)), "agent-usage-attempts.jsonl");
const fail = reason => { throw new Error(`${ERROR}${reason}`); }, has = (value, key) => Object.prototype.hasOwnProperty.call(value, key);
function plain(value) { if (value === null || typeof value !== "object" || Array.isArray(value) || isProxy(value)) return false; try { return Object.getPrototypeOf(value) === Object.prototype; } catch { return false; } }
function exact(value, keys) { if (!plain(value)) return false; let own; try { own = Reflect.ownKeys(value); } catch { return false; } return own.length === keys.length && own.every(key => typeof key === "string" && keys.includes(key) && (() => { const descriptor = Object.getOwnPropertyDescriptor(value, key); return descriptor && descriptor.enumerable && has(descriptor, "value"); })()); }
function canonicalPath(value, reason) { if (typeof value !== "string" || value.length === 0 || value.trim() !== value || value.includes("\0") || !path.isAbsolute(value) || path.parse(value).root === value) fail(reason); try { if (path.resolve(value) !== value) fail(reason); } catch { fail(reason); } return value; }
function validateOptions(options) {
  if (!plain(options)) fail("invalid_options"); let own; try { own = Reflect.ownKeys(options); } catch { fail("invalid_options"); }
  if (own.some(key => typeof key !== "string" || !OPTION_KEYS.includes(key))) fail("invalid_options");
  for (const key of own) { const descriptor = Object.getOwnPropertyDescriptor(options, key); if (!descriptor || !descriptor.enumerable || !has(descriptor, "value")) fail("invalid_options"); }
  if (has(options, "env") && (options.env === null || typeof options.env !== "object" || Array.isArray(options.env) || isProxy(options.env))) fail("invalid_options");
  for (const key of ["readFile", "readChain", "writeBatch"]) if (has(options, key) && (typeof options[key] !== "function" || isProxy(options[key]))) fail("invalid_options");
  if (has(options, "now") && (typeof options.now !== "function" || isProxy(options.now))) fail("invalid_clock");
  return { home: has(options, "home") ? options.home : os.homedir(), env: has(options, "env") ? options.env : process.env, now: has(options, "now") ? options.now : () => new Date(), readFile: has(options, "readFile") ? options.readFile : fs.readFileSync, readChain: has(options, "readChain") ? options.readChain : readLocalAgentUsageChain, writeBatch: has(options, "writeBatch") ? options.writeBatch : collectAndWriteLocalAgentUsageBatch };
}
function stateRoot(env, home) { const descriptor = Object.getOwnPropertyDescriptor(env, "LIFE_MANAGER_STATE_HOME"); if (descriptor && (!descriptor.enumerable || !has(descriptor, "value"))) fail("invalid_options"); const configured = descriptor ? descriptor.value : undefined; return canonicalPath(configured === undefined || configured === "" ? path.join(home, ".local", "state", "life-manager") : configured, "invalid_state_root"); }
function capture(now) { try { const date = now(), time = Date.prototype.getTime.call(date); if (!Number.isFinite(time)) fail("invalid_clock"); return Date.prototype.toISOString.call(date); } catch { fail("invalid_clock"); } }
function validCursor(value, sourceId) { return exact(value, CURSOR_KEYS) && value.schema_version === 1 && value.source_id === sourceId && Number.isSafeInteger(value.byte_offset) && value.byte_offset >= 0 && Number.isSafeInteger(value.observed_file_size) && value.observed_file_size >= value.byte_offset && typeof value.prefix_sha256 === "string" && HEX.test(value.prefix_sha256); }
function validateChain(value, sourceId) { if (!exact(value, CHAIN_KEYS)) throw Error(); if (value.status === "empty" && value.source_state === null) return null; if (value.status !== "ready" || !validCursor(value.source_state, sourceId)) throw Error(); return value.source_state; }
function validateWriter(value, sourceId, prior, length) { if (!exact(value, WRITER_KEYS) || typeof value.record_id !== "string" || !HEX.test(value.record_id) || value.source_id !== sourceId || !Number.isSafeInteger(value.byte_offset) || value.byte_offset < 0 || !Number.isSafeInteger(value.event_count) || value.event_count < 0 || value.mapping_id !== "local_agent_usage_v1") throw Error(); const priorOffset = prior === null ? 0 : prior.byte_offset; if (value.byte_offset < priorOffset || value.byte_offset > Math.max(priorOffset, length)) throw Error(); return value; }
function parseAttempts(bytes) { if (!Buffer.isBuffer(bytes)) throw Error(); if (!bytes.length) return []; if (bytes[bytes.length - 1] !== 10) throw Error(); const lines = bytes.toString("utf8").split("\n"); lines.pop(); if (lines.some(line => !line)) throw Error(); try { return lines.map(line => JSON.parse(line)); } catch { throw Error(); } }
function captureSource(source, home, root, configured) {
  let bytes, readError = null, readFailed = false; try { bytes = configured.readFile(attemptFile(source, home, root)); } catch (error) { readFailed = true; readError = error; }
  let enoent = false; try { enoent = Boolean(readError && readError.code === "ENOENT"); } catch { enoent = false; }
  let rows = null, parseError = readFailed && !enoent ? "attempt_source_unreadable" : null;
  if (!readFailed) try { rows = parseAttempts(bytes); } catch { parseError = "attempt_source_invalid"; }
  if (readFailed && enoent) rows = [];
  let chain; try { chain = configured.readChain(root, source.id); } catch { return ["local_state_failure"]; }
  if (parseError) return [parseError];
  try { return reconcileLocalAgentCapture(source.id, rows, chain).coverage_exceptions; } catch { return ["local_state_failure"]; }
}
const failed = (sourceId, status, exception) => ({ source_id: sourceId, status, record_id: null, byte_offset: null, event_count: null, mapping_id: null, coverage_exceptions: [exception] });
function freeze(value, seen = new WeakSet()) { if (value === null || typeof value !== "object" || seen.has(value)) return value; seen.add(value); Object.values(value).forEach(child => freeze(child, seen)); return Object.freeze(value); }
function runLocalAgentUsageCollection(options = {}) {
  const configured = validateOptions(options), home = canonicalPath(configured.home, "invalid_home"), root = stateRoot(configured.env, home), collected_at = capture(configured.now), sources = [];
  for (const source of SOURCES) {
    let prior; try { prior = validateChain(configured.readChain(root, source.id), source.id); } catch { sources.push(failed(source.id, "failed", "local_state_failure")); continue; }
    let bytes; try { bytes = configured.readFile(source.file(home, root)); if (!Buffer.isBuffer(bytes)) throw Error(); } catch { sources.push(failed(source.id, "unavailable", "source_unreadable")); continue; }
    try { const result = validateWriter(configured.writeBatch(root, collected_at, source.id, bytes, prior), source.id, prior, bytes.length); sources.push({ source_id: source.id, status: "published", record_id: result.record_id, byte_offset: result.byte_offset, event_count: result.event_count, mapping_id: result.mapping_id, coverage_exceptions: [] }); } catch { sources.push(failed(source.id, "failed", "local_state_failure")); }
  }
  const captureExceptions = SOURCES.flatMap(source => captureSource(source, home, root, configured));
  const coverage_exceptions = [...new Set([...sources.flatMap(source => source.coverage_exceptions), ...captureExceptions])].sort(); return freeze({ status: sources.every(source => source.status === "published") && !coverage_exceptions.length ? "complete" : "partial", collected_at, sources, coverage_exceptions });
}
module.exports = { runLocalAgentUsageCollection };
