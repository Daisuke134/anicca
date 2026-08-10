"use strict";

const fs = require("node:fs");
const os = require("node:os");
const { types } = require("node:util");
const path = require("node:path");
const { SpanKind, SpanStatusCode } = require("@opentelemetry/api");
const { NodeTracerProvider, SimpleSpanProcessor, InMemorySpanExporter } = require("@opentelemetry/sdk-trace-node");

const NAME = "cfo.local_agent_usage.collect";
const IDS = ["life_manager_agent_usage", "anicca_agent_usage"];
const CAPTURE_EXCEPTIONS = new Set(["ambiguous_completion", "capture_not_started", "conflicting_attempt", "duplicate_attempt", "missing_completion", "unmatched_completion", "usage_chain_incomplete", "attempt_source_invalid", "attempt_source_unreadable", "local_state_failure"]);
const FAIL = (kind) => new Error(`cfo_local_agent_usage_span_failed:${kind}`);
function plain(v) { try { return v !== null && typeof v === "object" && !types.isProxy(v) && Object.getPrototypeOf(v) === Object.prototype; } catch { return false; } }
function keys(v, expected) { return plain(v) && Reflect.ownKeys(v).length === expected.length && Object.keys(v).sort().join("\0") === expected.slice().sort().join("\0") && expected.every(k => Object.getOwnPropertyDescriptor(v, k)?.enumerable &&  Object.prototype.hasOwnProperty.call(Object.getOwnPropertyDescriptor(v, k), "value")); }
function array(v) { try { if (!Array.isArray(v) || types.isProxy(v) || Object.getPrototypeOf(v) !== Array.prototype || Reflect.ownKeys(v).length !== v.length + 1) return false; const l = Object.getOwnPropertyDescriptor(v, "length"); return l && !l.enumerable && !l.get && !l.set && l.value === v.length && [...Array(v.length).keys()].every(i => { const d = Object.getOwnPropertyDescriptor(v, String(i)); return d && d.enumerable && !d.get && !d.set && Object.prototype.hasOwnProperty.call(d, "value"); }); } catch { return false; } }
function inputOk(collect, input) { try { if (typeof collect !== "function" || types.isProxy(collect) || !keys(input, ["env"]) || !plain(input.env) || !Reflect.ownKeys(input.env).every(k => k === "LIFE_MANAGER_STATE_HOME") || Reflect.ownKeys(input.env).length > 1) return false; const d = Object.getOwnPropertyDescriptor(input.env, "LIFE_MANAGER_STATE_HOME"); if (d && (!d.enumerable || !Object.prototype.hasOwnProperty.call(d, "value"))) return false; const value = d?.value; if (value !== undefined && value !== "") return typeof value === "string" && value.length > 0 && value.trim() === value && !value.includes("\0") && path.isAbsolute(value) && path.resolve(value) === value && value !== path.parse(value).root; return true; } catch { return false; } }
function receiptOk(r) {
  try { if (!keys(r, ["status", "collected_at", "sources", "coverage_exceptions"]) || typeof r.collected_at !== "string" || !["complete", "partial"].includes(r.status) || !array(r.sources) || r.sources.length !== 2 || !array(r.coverage_exceptions) || r.coverage_exceptions.some((v, i, a) => typeof v !== "string" || i > 0 && a[i - 1] >= v) || !/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$/.test(r.collected_at) || Number.isNaN(Date.parse(r.collected_at)) || new Date(r.collected_at).toISOString() !== r.collected_at) return false;
  const seen = new Set(); let exceptions = [];
  for (const s of r.sources) { if (!keys(s, ["source_id", "status", "record_id", "byte_offset", "event_count", "mapping_id", "coverage_exceptions"]) || !IDS.includes(s.source_id) || seen.has(s.source_id) || !array(s.coverage_exceptions)) return false; seen.add(s.source_id); const pub = s.status === "published", unavailable = ["failed", "unavailable"].includes(s.status); if (!pub && !unavailable) return false; if (pub && (typeof s.record_id !== "string" || !/^[0-9a-f]{64}$/.test(s.record_id) || !Number.isSafeInteger(s.byte_offset) || s.byte_offset < 0 || !Number.isSafeInteger(s.event_count) || s.event_count < 0 || s.mapping_id !== "local_agent_usage_v1" || s.coverage_exceptions.length)) return false; if (s.status === "failed" && (s.record_id !== null || s.byte_offset !== null || s.event_count !== null || s.mapping_id !== null || s.coverage_exceptions.length !== 1 || s.coverage_exceptions[0] !== "local_state_failure")) return false; if (s.status === "unavailable" && (s.record_id !== null || s.byte_offset !== null || s.event_count !== null || s.mapping_id !== null || s.coverage_exceptions.length !== 1 || s.coverage_exceptions[0] !== "source_unreadable")) return false; exceptions.push(...s.coverage_exceptions); }
  const union = [...new Set(exceptions)].sort(); return seen.size === 2 && union.every(v => r.coverage_exceptions.includes(v)) && r.coverage_exceptions.every(v => union.includes(v) || CAPTURE_EXCEPTIONS.has(v)) && (r.status === (r.coverage_exceptions.length ? "partial" : "complete")); } catch { return false; }
}
function attrs(r, error) { const a = { "cfo.operation.name": "local_agent_usage.collect", "cfo.usage.collection.status": r.status, "cfo.usage.collection.collected_at": r.collected_at, "cfo.usage.collection.source_count": 2, "cfo.usage.collection.coverage_exception_count": r.coverage_exceptions.length }; if (r.coverage_exceptions.length) a["cfo.usage.collection.coverage_exceptions"] = [...r.coverage_exceptions]; for (const s of r.sources) { const p = `cfo.usage.source.${s.source_id}.`; a[p + "status"] = s.status; if (s.status === "published") { a[p + "record_id"] = s.record_id; a[p + "byte_offset"] = s.byte_offset; a[p + "event_count"] = s.event_count; a[p + "mapping_id"] = s.mapping_id; } } if (error) a["error.type"] = error; return a; }
async function captureLocalAgentUsageCollection(collect, input) {
  if (!inputOk(collect, input)) throw FAIL("invalid_input");
  const root = input.env.LIFE_MANAGER_STATE_HOME || path.join(os.homedir(), ".local", "state", "life-manager"), file = path.join(root, "telemetry", "cfo-local-agent-usage-otel-spans.jsonl");
  let provider, span, receipt, failure = null, terminalError = null; const exporter = new InMemorySpanExporter();
  try {
    provider = new NodeTracerProvider({ spanProcessors: [new SimpleSpanProcessor(exporter)] }); span = provider.getTracer("cfo-local-agent-usage").startSpan(NAME, { kind: SpanKind.INTERNAL });
    try { receipt = await collect(input); } catch { failure = "collection_failed"; span.setStatus({ code: SpanStatusCode.ERROR }); }
    const valid = failure === null && receiptOk(receipt);
    if (!valid && !failure) { failure = "invalid_receipt"; span.setStatus({ code: SpanStatusCode.ERROR }); }
    if (failure) span.setAttribute("error.type", failure); if (valid) { if (receipt.status === "partial") { failure = "collection_partial"; span.setStatus({ code: SpanStatusCode.ERROR }); } for (const [k, v] of Object.entries(attrs(receipt, failure))) span.setAttribute(k, v); }
    span.end(); await provider.forceFlush(); const finished = exporter.getFinishedSpans(); if (finished.length !== 1) throw FAIL("export"); const s = finished[0], record = { schema_version: 1, trace_id: s.spanContext().traceId, span_id: s.spanContext().spanId, name: s.name, kind: s.kind, status_code: s.status.code, attributes: s.attributes }; fs.mkdirSync(path.dirname(file), { recursive: true, mode: 0o700 }); if (!fs.existsSync(file)) fs.writeFileSync(file, "", { mode: 0o600 }); fs.appendFileSync(file, JSON.stringify(record) + "\n", { mode: 0o600 }); if (failure === "invalid_receipt") terminalError = FAIL("invalid_receipt"); else if (failure === "collection_failed") terminalError = FAIL("collection");
  } catch { terminalError = FAIL("export"); } finally { try { if (provider) await provider.shutdown(); } catch { terminalError = FAIL("export"); } }
  if (terminalError) throw terminalError; return receipt;
}
module.exports = { captureLocalAgentUsageCollection };
