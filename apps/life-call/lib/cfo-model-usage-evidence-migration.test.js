"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { test } = require("node:test");
const migrationPath = path.join(__dirname, "..", "migrations", "2026-08-10-cfo-model-usage-evidence.sql");
const appendMigrationPath = path.join(__dirname, "..", "migrations", "2026-08-10-cfo-model-usage-evidence-append-rpc.sql");
const liveProvenanceMigrationPath = path.join(__dirname, "..", "migrations", "2026-08-10-cfo-model-usage-evidence-live-provenance.sql");
const liveAppendMigrationPath = path.join(__dirname, "..", "migrations", "2026-08-10-cfo-model-usage-evidence-live-append-rpc.sql");
const patterns = [
  /CREATE TABLE IF NOT EXISTS public\.lm_cfo_model_usage_evidence/i, /id\s+bigint\s+GENERATED ALWAYS AS IDENTITY\s+PRIMARY KEY/i, /public_ref\s+uuid\s+NOT NULL\s+DEFAULT\s+gen_random_uuid\(\)\s+UNIQUE.*public_ref\s*<>\s*'00000000-0000-0000-0000-000000000000'::uuid/is, /uid\s+text\s+NOT NULL\s+REFERENCES\s+public\.lm_users\(uid\).*btrim\(uid\)\s*<>\s*''/is,
  /financial_unit_id\s+text.*financial_unit_id\s+~\s*'\^\[a-z\]\[a-z0-9_\]\*\$'/is, /attribution_status\s+text.*attribution_status\s*=\s*'attributed'.*financial_unit_id\s+IS NOT NULL.*attribution_status\s*=\s*'unattributed'.*financial_unit_id\s+IS NULL/is, /provider\s+text\s+NOT NULL\s+CHECK\s*\(\s*provider\s*~\s*'\^\[a-z0-9\]\+\(\?:\\\.\[a-z0-9-\]\+\)\+\$'.*provider_request_id\s+text\s+NOT NULL.*btrim\(provider_request_id\)\s*<>\s*''.*provider_request_id\s*=\s*btrim\(provider_request_id\)/is, /usage_sequence\s+bigint\s+NOT NULL.*CHECK\s*\(\s*usage_sequence\s*>=\s*0\s*\)/is, /occurred_at\s+timestamptz\s+NOT NULL.*trace_id\s+text\s+NOT NULL.*\^\[0-9a-f\]\{32\}.*repeat\('0',\s*32\)/is,
  /request_model\s+text\s+NOT NULL\s+CHECK\s*\(\s*btrim\(request_model\)\s*<>\s*''.*request_model\s*=\s*btrim\(request_model\).*response_model\s+text\s+NOT NULL\s+CHECK\s*\(\s*btrim\(response_model\)\s*<>\s*''.*response_model\s*=\s*btrim\(response_model\)/is, /input_tokens\s+bigint\s+NOT NULL.*CHECK\s*\(\s*input_tokens\s*>=\s*0\s*\).*output_tokens\s+bigint\s+NOT NULL.*CHECK\s*\(\s*output_tokens\s*>=\s*0\s*\).*total_tokens\s+bigint\s+NOT NULL.*CHECK\s*\(\s*total_tokens\s*>=\s*0\s*\)/is, /cached_input_tokens\s+bigint\s+CHECK\s*\(\s*cached_input_tokens\s+IS NULL\s+OR\s+cached_input_tokens\s*>=\s*0\s*\).*reasoning_output_tokens\s+bigint\s+CHECK\s*\(\s*reasoning_output_tokens\s+IS NULL\s+OR\s+reasoning_output_tokens\s*>=\s*0\s*\).*tool_input_tokens\s+bigint\s+CHECK\s*\(\s*tool_input_tokens\s+IS NULL\s+OR\s+tool_input_tokens\s*>=\s*0\s*\)/is, /evidence_status\s+text\s+NOT NULL\s+CHECK\s*\(\s*evidence_status\s+IN\s*\(\s*'provider_reported',\s*'locally_estimated'\s*\)\).*created_at\s+timestamptz\s+NOT NULL\s+DEFAULT\s+clock_timestamp\(\)/is,
  /CONSTRAINT\s+lm_cfo_model_usage_evidence_identity_unique\s+UNIQUE\s*\(provider,\s*provider_request_id,\s*usage_sequence\)/i, /ENABLE ROW LEVEL SECURITY/i, /CREATE POLICY\s+\S+\s+ON public\.lm_cfo_model_usage_evidence\s+FOR SELECT\s+TO service_role\s+USING\s*\(true\)/i, /CREATE POLICY\s+\S+\s+ON public\.lm_cfo_model_usage_evidence\s+FOR INSERT\s+TO service_role\s+WITH CHECK\s*\(true\)/i, /REVOKE ALL ON TABLE public\.lm_cfo_model_usage_evidence FROM PUBLIC, anon, authenticated, service_role/i,
  /GRANT SELECT, INSERT ON TABLE public\.lm_cfo_model_usage_evidence TO service_role/i, /REVOKE UPDATE, DELETE ON TABLE public\.lm_cfo_model_usage_evidence FROM service_role/i, /REVOKE ALL ON SEQUENCE public\.lm_cfo_model_usage_evidence_id_seq FROM PUBLIC, anon, authenticated, service_role/i, /GRANT USAGE, SELECT ON SEQUENCE public\.lm_cfo_model_usage_evidence_id_seq TO service_role/i, /BEFORE UPDATE OR DELETE ON public\.lm_cfo_model_usage_evidence/i, /RETURNS trigger.*SECURITY INVOKER.*SET search_path\s*=\s*public,\s*pg_temp/is, /RAISE EXCEPTION 'lm_cfo_model_usage_evidence is append-only'/i,
];
test("CFO model usage evidence migration is structured, private, and append-only", () => {
  const sql = fs.readFileSync(migrationPath, "utf8");
  patterns.forEach((pattern) => assert.match(sql, pattern));
  assert.doesNotMatch(sql, /\bjsonb?\b|raw_response|otel_attributes|gen_ai_|prompt|candidate|tool_arguments?|output_content|input_content|(?:request|response)_metadata|lm_append_cfo_model_usage_evidence/i);
  assert.doesNotMatch(sql, /^\s*(?:content|metadata)\s+\w+\b/im);
  assert.doesNotMatch(sql, /(?:input_tokens|output_tokens|cached_input_tokens|reasoning_output_tokens|tool_input_tokens)\s*\+\s*(?:input_tokens|output_tokens|cached_input_tokens|reasoning_output_tokens|tool_input_tokens)\s*=\s*total_tokens|total_tokens\s*=\s*(?:input_tokens|output_tokens|cached_input_tokens|reasoning_output_tokens|tool_input_tokens)\s*\+\s*(?:input_tokens|output_tokens|cached_input_tokens|reasoning_output_tokens|tool_input_tokens)/i);
});

test("CFO usage append RPC is typed, idempotent, invoker-private, and receipt-closed", () => {
  const sql = fs.readFileSync(appendMigrationPath, "utf8");
  assert.equal((sql.match(/CREATE OR REPLACE FUNCTION public\.lm_append_cfo_model_usage_evidence/gi) || []).length, 1);
  const start = sql.indexOf("CREATE OR REPLACE FUNCTION public.lm_append_cfo_model_usage_evidence");
  const end = sql.indexOf("\nREVOKE ALL ON FUNCTION", start);
  assert.ok(start >= 0 && end > start);
  const fn = sql.slice(start, end);
  [
    /public\.lm_append_cfo_model_usage_evidence\(\s*p_uid text,\s*p_financial_unit_id text,\s*p_attribution_status text,\s*p_provider text,\s*p_provider_request_id text,\s*p_usage_sequence bigint,\s*p_occurred_at timestamptz,\s*p_trace_id text,\s*p_request_model text,\s*p_response_model text,\s*p_input_tokens bigint,\s*p_output_tokens bigint,\s*p_total_tokens bigint,\s*p_cached_input_tokens bigint,\s*p_reasoning_output_tokens bigint,\s*p_tool_input_tokens bigint,\s*p_evidence_status text\s*\)\s*RETURNS jsonb/is,
    /SECURITY INVOKER\s+SET search_path\s*=\s*public,\s*pg_temp/i, /INSERT INTO public\.lm_cfo_model_usage_evidence\s*\(\s*uid,\s*financial_unit_id,\s*attribution_status,\s*provider,\s*provider_request_id,\s*usage_sequence,\s*occurred_at,\s*trace_id,\s*request_model,\s*response_model,\s*input_tokens,\s*output_tokens,\s*total_tokens,\s*cached_input_tokens,\s*reasoning_output_tokens,\s*tool_input_tokens,\s*evidence_status\s*\)\s*VALUES\s*\(\s*p_uid,\s*p_financial_unit_id,\s*p_attribution_status,\s*p_provider,\s*p_provider_request_id,\s*p_usage_sequence,\s*p_occurred_at,\s*p_trace_id,\s*p_request_model,\s*p_response_model,\s*p_input_tokens,\s*p_output_tokens,\s*p_total_tokens,\s*p_cached_input_tokens,\s*p_reasoning_output_tokens,\s*p_tool_input_tokens,\s*p_evidence_status\s*\)\s*ON CONFLICT ON CONSTRAINT lm_cfo_model_usage_evidence_identity_unique DO NOTHING\s*RETURNING \*/is,
    /SELECT \* INTO stored FROM public\.lm_cfo_model_usage_evidence\s+WHERE provider\s*=\s*p_provider\s+AND provider_request_id\s*=\s*p_provider_request_id\s+AND usage_sequence\s*=\s*p_usage_sequence/is, /RAISE EXCEPTION 'provider_usage_identity_conflict'\s+USING ERRCODE\s*=\s*'23505'/i, /jsonb_build_object\s*\(/i,
  ].forEach((pattern) => assert.match(fn, pattern));
  ["uid", "financial_unit_id", "attribution_status", "provider", "provider_request_id", "usage_sequence", "occurred_at", "trace_id", "request_model", "response_model", "input_tokens", "output_tokens", "total_tokens", "cached_input_tokens", "reasoning_output_tokens", "tool_input_tokens", "evidence_status"].forEach((field) => assert.match(fn, new RegExp(`stored\\.${field}\\s+IS DISTINCT FROM\\s+p_${field}`, "i")));
  assert.ok(fn.indexOf("SELECT * INTO stored") > fn.indexOf("INSERT INTO public.lm_cfo_model_usage_evidence"));
  const receipt = fn.slice(fn.indexOf("jsonb_build_object"), fn.indexOf(");", fn.indexOf("jsonb_build_object")));
  assert.deepEqual([...receipt.matchAll(/'([a-z_]+)'\s*,/g)].map((match) => match[1]), ["public_ref", "provider", "provider_request_id", "usage_sequence", "trace_id", "created_at"]);
  assert.doesNotMatch(fn, /\b(?:UPDATE|DELETE|EXECUTE\s+(?:format|immediate))\b/i);
  assert.doesNotMatch(sql, /\bp_\w+\s+jsonb?\b|\b(?:content|metadata|prompt|candidate|token_price|billing|otel_)\w*/i);
  assert.match(sql, /REVOKE ALL ON FUNCTION public\.lm_append_cfo_model_usage_evidence\([^;]+\) FROM PUBLIC, anon, authenticated, service_role/i);
  assert.match(sql, /GRANT EXECUTE ON FUNCTION public\.lm_append_cfo_model_usage_evidence\([^;]+\) TO service_role/i);
  assert.doesNotMatch(sql, /GRANT EXECUTE ON FUNCTION public\.lm_append_cfo_model_usage_evidence\([^;]+\) TO (?:PUBLIC|anon|authenticated)/i);
});

test("CFO Live provenance migration keeps provider and local identities exclusive", () => {
  const sql = fs.readFileSync(liveProvenanceMigrationPath, "utf8");
  [
    /ADD COLUMN\s+local_correlation_id\s+text\s+CONSTRAINT\s+lm_cfo_model_usage_evidence_local_correlation_format\s+CHECK\s*\(\s*local_correlation_id\s+IS NULL\s+OR\s+local_correlation_id\s*~\s*'\^live-session:\[0-9a-f\]\{32\}\$'\s*\)/is,
    /ALTER COLUMN\s+provider_request_id\s+DROP NOT NULL/i,
    /ALTER COLUMN\s+response_model\s+DROP NOT NULL/i,
    /CONSTRAINT\s+lm_cfo_model_usage_evidence_identity_path_check\s+CHECK\s*\(\s*\(\s*provider_request_id\s+IS NOT NULL\s+AND\s+response_model\s+IS NOT NULL\s+AND\s+local_correlation_id\s+IS NULL\s*\)\s*OR\s*\(\s*provider_request_id\s+IS NULL\s+AND\s+response_model\s+IS NULL\s+AND\s+local_correlation_id\s+IS NOT NULL\s*\)\s*\)/is,
    /CREATE UNIQUE INDEX\s+lm_cfo_model_usage_evidence_local_identity_unique\s+ON\s+public\.lm_cfo_model_usage_evidence\s*\(\s*provider\s*,\s*local_correlation_id\s*,\s*usage_sequence\s*\)\s*WHERE\s+local_correlation_id\s+IS NOT NULL/i,
  ].forEach((pattern) => assert.match(sql, pattern));
  assert.doesNotMatch(sql, /\b(?:UPDATE|DELETE|backfill)\b|\b(?:content|raw[_-]?response|metadata)\b|\bjsonb?\b|\b(?:CREATE|DROP|ALTER)\s+(?:OR\s+REPLACE\s+)?(?:FUNCTION|PROCEDURE)\b|\b(?:CREATE|DROP)\s+TABLE\b|\b(?:RPC|POLICY|GRANT|REVOKE)\b/i);
});

test("CFO Live append RPC supports one truthful local identity without changing provider receipts", () => {
  const sql = fs.readFileSync(liveAppendMigrationPath, "utf8");
  assert.match(sql, /DROP FUNCTION public\.lm_append_cfo_model_usage_evidence\(text, text, text, text, text, bigint, timestamptz, text, text, text, bigint, bigint, bigint, bigint, bigint, bigint, text\)/i); assert.match(sql, /p_evidence_status text,\s*p_local_correlation_id text DEFAULT NULL\s*\)/is); assert.match(sql, /local_correlation_id\s*\).*p_local_correlation_id.*ON CONFLICT DO NOTHING\s*RETURNING \*/is); assert.doesNotMatch(sql, /ON CONFLICT\s+(?:ON CONSTRAINT|\()/i); assert.match(sql, /provider_request_id IS NOT DISTINCT FROM p_provider_request_id.*local_correlation_id IS NOT DISTINCT FROM p_local_correlation_id/is);
  ["uid", "financial_unit_id", "attribution_status", "provider", "provider_request_id", "usage_sequence", "occurred_at", "trace_id", "request_model", "response_model", "input_tokens", "output_tokens", "total_tokens", "cached_input_tokens", "reasoning_output_tokens", "tool_input_tokens", "evidence_status", "local_correlation_id"].forEach((field) => assert.match(sql, new RegExp(`stored\\.${field}\\s+IS DISTINCT FROM\\s+p_${field}`, "i"))); assert.match(sql, /RAISE EXCEPTION 'provider_usage_identity_conflict' USING ERRCODE = '23505'/i);
  const receipt = sql.slice(sql.indexOf("jsonb_strip_nulls"), sql.indexOf(");", sql.indexOf("jsonb_strip_nulls"))); assert.deepEqual([...receipt.matchAll(/'([a-z_]+)'\s*,/g)].map((match) => match[1]), ["public_ref", "provider", "provider_request_id", "local_correlation_id", "usage_sequence", "trace_id", "created_at"]); assert.match(sql, /REVOKE ALL ON FUNCTION public\.lm_append_cfo_model_usage_evidence\([^;]+, text\) FROM PUBLIC, anon, authenticated, service_role/i); assert.match(sql, /GRANT EXECUTE ON FUNCTION public\.lm_append_cfo_model_usage_evidence\([^;]+, text\) TO service_role/i); assert.doesNotMatch(sql, /\b(?:UPDATE|DELETE|EXECUTE\s+(?:format|immediate))\b|\b(?:content|raw_response|metadata|otel_|token_price|billing|secret)\w*/i);
});
