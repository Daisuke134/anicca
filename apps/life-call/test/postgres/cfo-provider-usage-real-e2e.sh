#!/usr/bin/env bash
set -euo pipefail

: "${GEMINI_API_KEY:?GEMINI_API_KEY is required}"
for command in docker psql curl node; do command -v "$command" >/dev/null || { printf 'FAIL missing command: %s\n' "$command" >&2; exit 1; }; done
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MIGRATION="$ROOT_DIR/migrations/2026-08-10-cfo-model-usage-evidence.sql"
RPC_MIGRATION="$ROOT_DIR/migrations/2026-08-10-cfo-model-usage-evidence-append-rpc.sql"
TMP_ROOT="${TMPDIR:-/tmp}"
TEST_TMP="$(mktemp -d "$TMP_ROOT/cfo-provider-usage-real-e2e-$$.XXXXXX")"
NETWORK="cfo-provider-usage-net-$$"
PG_NAME="cfo-provider-usage-pg-$$"
REST_NAME="cfo-provider-usage-rest-$$"
TRACE_FILE="$TEST_TMP/traces-$$.txt"
JWT_SECRET="cfo-provider-e2e-jwt-secret-32-bytes"
[[ ${#JWT_SECRET} -ge 32 ]]
CFO_E2E_SENTINEL="CFO_E2E_PRIVATE_EVENT_$$"
case "$TEST_TMP" in "$TMP_ROOT/cfo-provider-usage-real-e2e-$$."*) ;; *) printf 'FAIL invalid temporary directory\n' >&2; exit 1 ;; esac
cleanup() {
  docker stop "$REST_NAME" >/dev/null 2>&1 || true
  docker stop "$PG_NAME" >/dev/null 2>&1 || true
  docker network rm "$NETWORK" >/dev/null 2>&1 || true
  case "$TEST_TMP" in "$TMP_ROOT/cfo-provider-usage-real-e2e-$$."*) rm -rf -- "$TEST_TMP" ;; esac
}
trap cleanup EXIT INT TERM

docker network create "$NETWORK" >/dev/null
docker run --rm -d --name "$PG_NAME" --network "$NETWORK" \
  -e POSTGRES_PASSWORD=cfo-e2e-only -e POSTGRES_DB=cfo_provider_e2e \
  -p 127.0.0.1::5432 postgres:18-alpine >/dev/null 2>&1
PG_PORT=""
for _ in {1..120}; do PG_PORT="$(docker port "$PG_NAME" 5432/tcp 2>/dev/null | sed -n 's/.*://p' | tail -n 1)"; [[ "$PG_PORT" =~ ^[0-9]+$ ]] && break; sleep 0.1; done
[[ "$PG_PORT" =~ ^[0-9]+$ ]]
export PGPASSWORD=cfo-e2e-only
PSQL=(psql -X -v ON_ERROR_STOP=1 -h 127.0.0.1 -p "$PG_PORT" -U postgres -d cfo_provider_e2e)
PG_START=""; PG_STABLE=0
for _ in {1..120}; do CURRENT_START="$("${PSQL[@]}" -Atqc 'SELECT pg_postmaster_start_time()' 2>/dev/null || true)"; if [[ -n "$CURRENT_START" && "$CURRENT_START" == "$PG_START" ]]; then PG_STABLE=$((PG_STABLE + 1)); else PG_START="$CURRENT_START"; PG_STABLE=1; fi; (( PG_STABLE >= 3 )) && break; sleep 0.2; done
(( PG_STABLE >= 3 ))
"${PSQL[@]}" >/dev/null <<'SQL'
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE ROLE anon NOLOGIN;
CREATE ROLE authenticated NOLOGIN;
CREATE ROLE service_role NOLOGIN NOINHERIT;
CREATE ROLE authenticator LOGIN NOINHERIT PASSWORD 'cfo-e2e-only';
GRANT service_role TO authenticator;
CREATE TABLE public.lm_users(uid text PRIMARY KEY);
INSERT INTO public.lm_users(uid) VALUES ('cfo-e2e-owner');
SQL
"${PSQL[@]}" -f "$MIGRATION" >/dev/null 2>&1
"${PSQL[@]}" -f "$RPC_MIGRATION" >/dev/null 2>&1

CFO_E2E_JWT="$(JWT_SECRET="$JWT_SECRET" node -e 'const c=require("node:crypto"),b=v=>Buffer.from(JSON.stringify(v)).toString("base64url"),h=`${b({alg:"HS256",typ:"JWT"})}.${b({role:"service_role"})}`;process.stdout.write(`${h}.${c.createHmac("sha256",process.env.JWT_SECRET).update(h).digest("base64url")}`)')"

docker run --rm -d --name "$REST_NAME" --network "$NETWORK" \
  -e PGRST_DB_URI=postgres://authenticator:cfo-e2e-only@"$PG_NAME":5432/cfo_provider_e2e \
  -e PGRST_DB_ANON_ROLE=anon -e PGRST_JWT_SECRET="$JWT_SECRET" \
  -p 127.0.0.1::3000 postgrest/postgrest:v16.0 >/dev/null 2>&1
REST_PORT=""
for _ in {1..120}; do REST_PORT="$(docker port "$REST_NAME" 3000/tcp 2>/dev/null | sed -n 's/.*://p' | tail -n 1)"; [[ "$REST_PORT" =~ ^[0-9]+$ ]] && break; sleep 0.1; done
[[ "$REST_PORT" =~ ^[0-9]+$ ]]
CFO_E2E_URL="http://127.0.0.1:$REST_PORT"
for _ in {1..120}; do curl -fsS --max-time 2 "$CFO_E2E_URL/" -H "Authorization: Bearer $CFO_E2E_JWT" >/dev/null 2>&1 && break; sleep 0.1; done
curl -fsS --max-time 2 "$CFO_E2E_URL/" -H "Authorization: Bearer $CFO_E2E_JWT" >/dev/null 2>&1

CFO_E2E_URL="$CFO_E2E_URL" CFO_E2E_SENTINEL="$CFO_E2E_SENTINEL" CFO_E2E_TRACE_FILE="$TRACE_FILE" CFO_ROOT="$ROOT_DIR" CFO_E2E_JWT="$CFO_E2E_JWT" \
node <<'NODE'
const assert = require("node:assert/strict"), fs = require("node:fs"), path = require("node:path"), inspect = require("node:util").inspect;
const nativeFetch = globalThis.fetch, base = new URL(process.env.CFO_E2E_URL), providerResponses = [];
let exporterOutput = ""; const writeExport = (...args) => { exporterOutput += args.map((value) => typeof value === "string" ? value : inspect(value, { depth: null, colors: false })).join(" ") + "\n"; };
const oldLog = console.log, oldDir = console.dir; console.log = writeExport; console.dir = writeExport;
const localPostgrestFetch = async (input, init) => { const url = new URL(typeof input === "string" ? input : input.url); if (url.origin === base.origin) url.pathname = url.pathname.replace(/^\/rest\/v1(?=\/|$)/, ""); return nativeFetch(url.origin === base.origin ? url : input, init); };
globalThis.fetch = async (...args) => { const response = await nativeFetch(...args), input = args[0], url = new URL(typeof input === "string" ? input : input.url || String(input)); if (url.origin === "https://generativelanguage.googleapis.com") providerResponses.push(await response.clone().json()); return response; };
const projectGeminiUsage = (value) => { const u = value.usageMetadata; return { uid: "cfo-e2e-owner", financial_unit_id: "life_manager_saas", attribution_status: "attributed", provider: "gcp.gemini", provider_request_id: value.responseId, usage_sequence: 0, request_model: "gemini-2.5-flash", response_model: value.modelVersion, input_tokens: u.promptTokenCount, output_tokens: u.candidatesTokenCount, total_tokens: u.totalTokenCount, cached_input_tokens: u.cachedContentTokenCount ?? null, reasoning_output_tokens: u.thoughtsTokenCount ?? null, tool_input_tokens: u.toolUsePromptTokenCount ?? null, evidence_status: "provider_reported" }; };
const projectRow = (row) => ({ uid: row.uid, financial_unit_id: row.financial_unit_id, attribution_status: row.attribution_status, provider: row.provider, provider_request_id: row.provider_request_id, usage_sequence: row.usage_sequence, request_model: row.request_model, response_model: row.response_model, input_tokens: row.input_tokens, output_tokens: row.output_tokens, total_tokens: row.total_tokens, cached_input_tokens: row.cached_input_tokens, reasoning_output_tokens: row.reasoning_output_tokens, tool_input_tokens: row.tool_input_tokens, evidence_status: row.evidence_status });
const sorted = (values) => [...values].sort((a, b) => { const left = `${a.provider_request_id}\0${a.usage_sequence}`, right = `${b.provider_request_id}\0${b.usage_sequence}`; return left < right ? -1 : left > right ? 1 : 0; });
const collectStrings = (value, out = []) => { if (typeof value === "string" && value) out.push(value); else if (Array.isArray(value)) value.forEach((item) => collectStrings(item, out)); else if (value && typeof value === "object") Object.values(value).forEach((item) => collectStrings(item, out)); return out; };
;(async () => {
try {
  const { agentSearchCandidate } = require(path.join(process.env.CFO_ROOT, "lib", "ask.js"));
  await agentSearchCandidate({ summary: "Tokyo International Forum venue", description: process.env.CFO_E2E_SENTINEL }, { geminiKey: process.env.GEMINI_API_KEY, providerUsage: { owner_id: "cfo-e2e-owner", financial_unit_id: "life_manager_saas", request_model: "gemini-2.5-flash", storeOptions: { supaUrl: process.env.CFO_E2E_URL, supaKey: process.env.CFO_E2E_JWT, fetchImpl: localPostgrestFetch } }, mailAvailable: async () => false, mail: { ready: () => false, searchInbox: async () => [] } });
  const readResponse = await localPostgrestFetch(`${process.env.CFO_E2E_URL}/rest/v1/lm_cfo_model_usage_evidence?select=uid,financial_unit_id,attribution_status,provider,provider_request_id,usage_sequence,trace_id,request_model,response_model,input_tokens,output_tokens,total_tokens,cached_input_tokens,reasoning_output_tokens,tool_input_tokens,evidence_status`, { headers: { apikey: process.env.CFO_E2E_JWT, Authorization: `Bearer ${process.env.CFO_E2E_JWT}`, Accept: "application/json" } });
  assert.equal(readResponse.ok, true); const rows = await readResponse.json(); assert.equal(providerResponses.length, 2); assert.equal(rows.length, 2); assert.deepEqual(sorted(rows).map(projectRow), sorted(providerResponses).map(projectGeminiUsage));
  assert.ok(rows.every((row) => /^(?!0{32})[0-9a-f]{32}$/.test(row.trace_id))); assert.equal(new Set(rows.map((row) => row.trace_id)).size, 2); assert.ok(!JSON.stringify(rows).includes(process.env.CFO_E2E_SENTINEL));
  const traceIds = rows.map((row) => row.trace_id); fs.writeFileSync(process.env.CFO_E2E_TRACE_FILE, `${traceIds.join("\n")}\n`); const providerStrings = [], providerTexts = [];
  for (const response of providerResponses) for (const part of (response.candidates || []).flatMap((candidate) => candidate.content?.parts || [])) { if (typeof part.text === "string" && part.text) providerTexts.push(part.text); const call = part.functionCall; if (call) { if (typeof call.name === "string" && call.name) providerStrings.push(call.name); providerStrings.push(...collectStrings(call.args)); } }
  assert.ok(providerTexts.length > 0); for (const value of [...providerTexts, ...providerStrings].filter((value) => value.length >= 12)) assert.ok(!exporterOutput.includes(value)); assert.ok(!exporterOutput.includes(process.env.CFO_E2E_SENTINEL)); assert.ok(!exporterOutput.includes(process.env.GEMINI_API_KEY));
  for (const traceId of traceIds) assert.equal(exporterOutput.split(traceId).length - 1, 1); console.log = oldLog; console.dir = oldDir; process.stdout.write("cfo-provider-usage-real-e2e: PASS rows=2 spans=2\n");
} catch (error) { console.log = oldLog; console.dir = oldDir; const message = String(error?.message || "unknown").replaceAll(process.env.GEMINI_API_KEY, "[redacted]").replaceAll(process.env.CFO_E2E_SENTINEL, "[redacted]"); process.stderr.write(`cfo-provider-usage-real-e2e: FAIL ${message}\n`); process.exitCode = 1; }
})();
NODE
