#!/usr/bin/env bash
set -euo pipefail

: "${GEMINI_API_KEY:?GEMINI_API_KEY is required}"
for command in docker psql curl node; do command -v "$command" >/dev/null || { printf 'FAIL missing command: %s\n' "$command" >&2; exit 1; }; done
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MIGRATION="$ROOT_DIR/migrations/2026-08-10-cfo-model-usage-evidence.sql"
RPC_MIGRATION="$ROOT_DIR/migrations/2026-08-10-cfo-model-usage-evidence-append-rpc.sql"
LIVE_MIGRATION="$ROOT_DIR/migrations/2026-08-10-cfo-model-usage-evidence-live-provenance.sql"
LIVE_RPC_MIGRATION="$ROOT_DIR/migrations/2026-08-10-cfo-model-usage-evidence-live-append-rpc.sql"
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
"${PSQL[@]}" -f "$LIVE_MIGRATION" >/dev/null 2>&1
"${PSQL[@]}" -f "$LIVE_RPC_MIGRATION" >/dev/null 2>&1
"${PSQL[@]}" >/dev/null <<'SQL'
BEGIN;
DO $$
DECLARE constraint_name text; first_receipt jsonb; retry_receipt jsonb; observed_at timestamptz := '2026-08-10T01:02:03Z';
BEGIN
  INSERT INTO public.lm_cfo_model_usage_evidence (uid, financial_unit_id, attribution_status, provider, provider_request_id, usage_sequence, occurred_at, trace_id, request_model, response_model, input_tokens, output_tokens, total_tokens, cached_input_tokens, reasoning_output_tokens, tool_input_tokens, evidence_status, local_correlation_id) VALUES ('cfo-e2e-owner', 'life_manager_saas', 'attributed', 'gcp.gemini', NULL, 0, clock_timestamp(), repeat('1', 32), 'gemini-live', NULL, 1, 1, 2, NULL, NULL, NULL, 'provider_reported', 'live-session:' || repeat('2', 32));
  BEGIN
    INSERT INTO public.lm_cfo_model_usage_evidence (uid, financial_unit_id, attribution_status, provider, provider_request_id, usage_sequence, occurred_at, trace_id, request_model, response_model, input_tokens, output_tokens, total_tokens, cached_input_tokens, reasoning_output_tokens, tool_input_tokens, evidence_status, local_correlation_id) VALUES ('cfo-e2e-owner', 'life_manager_saas', 'attributed', 'gcp.gemini', 'mixed-provider-id', 0, clock_timestamp(), repeat('3', 32), 'gemini-live', 'gemini-live', 1, 1, 2, NULL, NULL, NULL, 'provider_reported', 'live-session:' || repeat('2', 32));
    RAISE EXCEPTION 'expected_identity_path_check';
  EXCEPTION WHEN check_violation THEN
    GET STACKED DIAGNOSTICS constraint_name = CONSTRAINT_NAME;
    IF constraint_name <> 'lm_cfo_model_usage_evidence_identity_path_check' THEN RAISE; END IF;
  END;
  BEGIN
    INSERT INTO public.lm_cfo_model_usage_evidence (uid, financial_unit_id, attribution_status, provider, provider_request_id, usage_sequence, occurred_at, trace_id, request_model, response_model, input_tokens, output_tokens, total_tokens, cached_input_tokens, reasoning_output_tokens, tool_input_tokens, evidence_status, local_correlation_id) VALUES ('cfo-e2e-owner', 'life_manager_saas', 'attributed', 'gcp.gemini', NULL, 0, clock_timestamp(), repeat('4', 32), 'gemini-live', NULL, 1, 1, 2, NULL, NULL, NULL, 'provider_reported', 'live-session:' || repeat('2', 32));
    RAISE EXCEPTION 'expected_local_identity_unique';
  EXCEPTION WHEN unique_violation THEN
    GET STACKED DIAGNOSTICS constraint_name = CONSTRAINT_NAME;
    IF constraint_name <> 'lm_cfo_model_usage_evidence_local_identity_unique' THEN RAISE; END IF;
  END;
  BEGIN
    INSERT INTO public.lm_cfo_model_usage_evidence (uid, financial_unit_id, attribution_status, provider, provider_request_id, usage_sequence, occurred_at, trace_id, request_model, response_model, input_tokens, output_tokens, total_tokens, cached_input_tokens, reasoning_output_tokens, tool_input_tokens, evidence_status, local_correlation_id) VALUES ('cfo-e2e-owner', 'life_manager_saas', 'attributed', 'gcp.gemini', NULL, 1, clock_timestamp(), repeat('5', 32), 'gemini-live', NULL, 1, 1, 2, NULL, NULL, NULL, 'provider_reported', 'live-session:not-hex');
    RAISE EXCEPTION 'expected_local_correlation_format';
  EXCEPTION WHEN check_violation THEN
    GET STACKED DIAGNOSTICS constraint_name = CONSTRAINT_NAME;
    IF constraint_name <> 'lm_cfo_model_usage_evidence_local_correlation_format' THEN RAISE; END IF;
  END;
  SELECT public.lm_append_cfo_model_usage_evidence('cfo-e2e-owner', 'life_manager_saas', 'attributed', 'gcp.gemini', NULL, 7, observed_at, repeat('6', 32), 'models/gemini-2.5-flash-native-audio-preview-09-2025', NULL, 515, 38, 560, 2, 5, 1, 'provider_reported', 'live-session:' || repeat('7', 32)) INTO first_receipt;
  SELECT public.lm_append_cfo_model_usage_evidence('cfo-e2e-owner', 'life_manager_saas', 'attributed', 'gcp.gemini', NULL, 7, observed_at, repeat('6', 32), 'models/gemini-2.5-flash-native-audio-preview-09-2025', NULL, 515, 38, 560, 2, 5, 1, 'provider_reported', 'live-session:' || repeat('7', 32)) INTO retry_receipt;
  IF first_receipt IS DISTINCT FROM retry_receipt OR first_receipt->>'local_correlation_id' <> 'live-session:' || repeat('7', 32) OR first_receipt ? 'provider_request_id' OR (SELECT count(*) FROM jsonb_object_keys(first_receipt)) <> 6 THEN RAISE EXCEPTION 'live_receipt_contract_failed'; END IF;
  BEGIN PERFORM public.lm_append_cfo_model_usage_evidence('cfo-e2e-owner', 'life_manager_saas', 'attributed', 'gcp.gemini', NULL, 7, observed_at, repeat('8', 32), 'models/gemini-2.5-flash-native-audio-preview-09-2025', NULL, 515, 38, 560, 2, 5, 1, 'provider_reported', 'live-session:' || repeat('7', 32)); RAISE EXCEPTION 'expected_provider_usage_identity_conflict'; EXCEPTION WHEN unique_violation THEN IF SQLERRM <> 'provider_usage_identity_conflict' THEN RAISE; END IF; END;
END;
$$;
ROLLBACK;
SQL

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
const assert = require("node:assert/strict"), crypto = require("node:crypto"), fs = require("node:fs"), path = require("node:path"), inspect = require("node:util").inspect, WebSocket = require("ws");
const nativeFetch = globalThis.fetch, base = new URL(process.env.CFO_E2E_URL), providerResponses = [], providerLiveMessages = [], postTurnLiveMessages = [], exportedSpans = [];
let exporterOutput = ""; const writeExport = (...args) => { for (const value of args) if (value && Object.getPrototypeOf(value) === Object.prototype && /^(?!0{32})[0-9a-f]{32}$/.test(value.traceId || "")) exportedSpans.push(value); exporterOutput += args.map((value) => typeof value === "string" ? value : inspect(value, { depth: null, colors: false })).join(" ") + "\n"; };
const oldLog = console.log, oldDir = console.dir; console.log = writeExport; console.dir = writeExport;
const localPostgrestFetch = async (input, init) => { const url = new URL(typeof input === "string" ? input : input.url); if (url.origin === base.origin) url.pathname = url.pathname.replace(/^\/rest\/v1(?=\/|$)/, ""); return nativeFetch(url.origin === base.origin ? url : input, init); };
globalThis.fetch = async (...args) => { const response = await nativeFetch(...args), input = args[0], url = new URL(typeof input === "string" ? input : input.url || String(input)); if (url.origin === "https://generativelanguage.googleapis.com") providerResponses.push(await response.clone().json()); return response; };
const projectGeminiUsage = (value) => { const u = value.usageMetadata; return { uid: "cfo-e2e-owner", financial_unit_id: "life_manager_saas", attribution_status: "attributed", provider: "gcp.gemini", provider_request_id: value.responseId, usage_sequence: 0, request_model: "gemini-2.5-flash", response_model: value.modelVersion, input_tokens: u.promptTokenCount, output_tokens: u.candidatesTokenCount, total_tokens: u.totalTokenCount, cached_input_tokens: u.cachedContentTokenCount ?? null, reasoning_output_tokens: u.thoughtsTokenCount ?? null, tool_input_tokens: u.toolUsePromptTokenCount ?? null, evidence_status: "provider_reported", local_correlation_id: null }; };
const projectRow = (row) => ({ uid: row.uid, financial_unit_id: row.financial_unit_id, attribution_status: row.attribution_status, provider: row.provider, provider_request_id: row.provider_request_id, usage_sequence: row.usage_sequence, request_model: row.request_model, response_model: row.response_model, input_tokens: row.input_tokens, output_tokens: row.output_tokens, total_tokens: row.total_tokens, cached_input_tokens: row.cached_input_tokens, reasoning_output_tokens: row.reasoning_output_tokens, tool_input_tokens: row.tool_input_tokens, evidence_status: row.evidence_status, local_correlation_id: row.local_correlation_id });
const sorted = (values) => [...values].sort((a, b) => { const left = `${a.provider_request_id}\0${a.usage_sequence}`, right = `${b.provider_request_id}\0${b.usage_sequence}`; return left < right ? -1 : left > right ? 1 : 0; });
const collectStrings = (value, out = []) => { if (typeof value === "string" && value) out.push(value); else if (Array.isArray(value)) value.forEach((item) => collectStrings(item, out)); else if (value && typeof value === "object") Object.values(value).forEach((item) => collectStrings(item, out)); return out; };
;(async () => {
try {
  const { agentSearchCandidate } = require(path.join(process.env.CFO_ROOT, "lib", "ask.js"));
  await agentSearchCandidate({ summary: "Tokyo International Forum venue", description: process.env.CFO_E2E_SENTINEL }, { geminiKey: process.env.GEMINI_API_KEY, providerUsage: { owner_id: "cfo-e2e-owner", financial_unit_id: "life_manager_saas", request_model: "gemini-2.5-flash", storeOptions: { supaUrl: process.env.CFO_E2E_URL, supaKey: process.env.CFO_E2E_JWT, fetchImpl: localPostgrestFetch } }, mailAvailable: async () => false, mail: { ready: () => false, searchInbox: async () => [] } });
  const { LIVE_MODEL, geminiLiveWsUrl, buildGeminiSetup, buildGeminiTurn } = require(path.join(process.env.CFO_ROOT, "lib", "call-logic.js")); const { captureGeminiLiveUsageObservation } = require(path.join(process.env.CFO_ROOT, "lib", "cfo-provider-usage-span.js"));
  const setup = buildGeminiSetup({ model: LIVE_MODEL, voiceName: "Charon", systemInstruction: "" }); let liveSessionId; do liveSessionId = crypto.randomBytes(16).toString("hex"); while (/^0+$/.test(liveSessionId));
  const liveMessage = await new Promise((resolve, reject) => {
    let socket, timer, turnSent = false, settled = false;
    const settle = (error, value) => { if (settled) return; settled = true; clearTimeout(timer); if (socket) { socket.removeListener("message", onMessage); socket.removeListener("error", onError); socket.removeListener("close", onClose); socket.removeListener("open", onOpen); if (socket.readyState === WebSocket.CONNECTING) { socket.once("error", () => {}); try { socket.terminate(); } catch { try { socket.close(); } catch {} } } else { try { socket.close(); } catch {} } } error ? reject(error) : resolve(value); };
    const onMessage = (data) => { let message; try { message = JSON.parse(data.toString()); } catch { return; } if (!turnSent) { if (!message.setupComplete) return; turnSent = true; try { socket.send(JSON.stringify(buildGeminiTurn(process.env.CFO_E2E_SENTINEL))); } catch { settle(new Error("live_error")); } return; } postTurnLiveMessages.push(message); if (message.usageMetadata) { providerLiveMessages.push(message); settle(null, message); } };
    const onError = () => settle(new Error("live_error")); const onClose = () => settle(new Error("live_early_close")); const onOpen = () => { try { socket.send(JSON.stringify(setup)); } catch { settle(new Error("live_error")); } }; timer = setTimeout(() => settle(new Error("live_timeout")), 30000);
    try { socket = new WebSocket(geminiLiveWsUrl(process.env.GEMINI_API_KEY)); socket.on("message", onMessage); socket.on("error", onError); socket.on("close", onClose); socket.on("open", onOpen); } catch { settle(new Error("live_error")); }
  });
  await captureGeminiLiveUsageObservation(liveMessage, { owner_id: "cfo-e2e-owner", financial_unit_id: "life_manager_saas", request_model: setup.setup.model, live_session_id: liveSessionId, usage_sequence: 0 }, { storeOptions: { supaUrl: process.env.CFO_E2E_URL, supaKey: process.env.CFO_E2E_JWT, fetchImpl: localPostgrestFetch } });
  const readResponse = await localPostgrestFetch(`${process.env.CFO_E2E_URL}/rest/v1/lm_cfo_model_usage_evidence?select=uid,financial_unit_id,attribution_status,provider,provider_request_id,usage_sequence,trace_id,request_model,response_model,input_tokens,output_tokens,total_tokens,cached_input_tokens,reasoning_output_tokens,tool_input_tokens,evidence_status,local_correlation_id`, { headers: { apikey: process.env.CFO_E2E_JWT, Authorization: `Bearer ${process.env.CFO_E2E_JWT}`, Accept: "application/json" } });
  assert.equal(readResponse.ok, true); const rows = await readResponse.json(), providerRows = rows.filter((row) => row.provider_request_id !== null); assert.equal(providerResponses.length, 2); assert.equal(providerRows.length, 2); assert.deepEqual(sorted(providerRows).map(projectRow), sorted(providerResponses.map(projectGeminiUsage))); assert.ok(providerRows.every((row) => row.provider_request_id && row.response_model && row.local_correlation_id === null));
  assert.equal(providerLiveMessages.length, 1); assert.equal(rows.filter((row) => row.local_correlation_id === `live-session:${liveSessionId}`).length, 1); const liveUsage = providerLiveMessages[0].usageMetadata, liveRow = rows.find((row) => row.local_correlation_id === `live-session:${liveSessionId}`); assert.deepEqual(projectRow(liveRow), { uid: "cfo-e2e-owner", financial_unit_id: "life_manager_saas", attribution_status: "attributed", provider: "gcp.gemini", provider_request_id: null, usage_sequence: 0, request_model: setup.setup.model, response_model: null, input_tokens: liveUsage.promptTokenCount, output_tokens: liveUsage.responseTokenCount, total_tokens: liveUsage.totalTokenCount, cached_input_tokens: liveUsage.cachedContentTokenCount ?? null, reasoning_output_tokens: liveUsage.thoughtsTokenCount ?? null, tool_input_tokens: liveUsage.toolUsePromptTokenCount ?? null, evidence_status: "provider_reported", local_correlation_id: `live-session:${liveSessionId}` }); assert.equal(rows.length, 3); assert.equal(exportedSpans.length, 3);
  assert.ok(rows.every((row) => /^(?!0{32})[0-9a-f]{32}$/.test(row.trace_id))); assert.equal(new Set(rows.map((row) => row.trace_id)).size, 3); assert.deepEqual(exportedSpans.map((span) => span.traceId).sort(), rows.map((row) => row.trace_id).sort()); assert.ok(!JSON.stringify(rows).includes(process.env.CFO_E2E_SENTINEL));
  const traceIds = rows.map((row) => row.trace_id); fs.writeFileSync(process.env.CFO_E2E_TRACE_FILE, `${traceIds.join("\n")}\n`); const providerStrings = [], providerTexts = [];
  for (const response of providerResponses) for (const part of (response.candidates || []).flatMap((candidate) => candidate.content?.parts || [])) { if (typeof part.text === "string" && part.text) providerTexts.push(part.text); const call = part.functionCall; if (call) { if (typeof call.name === "string" && call.name) providerStrings.push(call.name); providerStrings.push(...collectStrings(call.args)); } }
  assert.ok(providerTexts.length > 0); for (const value of [...providerTexts, ...providerStrings, ...collectStrings(postTurnLiveMessages)].filter((value) => value.length >= 12)) assert.ok(!exporterOutput.includes(value)); assert.ok(!exporterOutput.includes(process.env.CFO_E2E_SENTINEL)); assert.ok(!exporterOutput.includes(process.env.GEMINI_API_KEY)); assert.ok(!exporterOutput.includes("gen_ai.input.messages")); assert.ok(!exporterOutput.includes("gen_ai.output.messages"));
  for (const traceId of traceIds) assert.equal(exporterOutput.split(traceId).length - 1, 1); console.log = oldLog; console.dir = oldDir; process.stdout.write("cfo-provider-usage-real-e2e: PASS rows=3 spans=3 live=1\n");
} catch (error) { console.log = oldLog; console.dir = oldDir; const message = String(error?.message || "unknown").replaceAll(process.env.GEMINI_API_KEY, "[redacted]").replaceAll(process.env.CFO_E2E_SENTINEL, "[redacted]"); process.stderr.write(`cfo-provider-usage-real-e2e: FAIL ${message}\n`); process.exitCode = 1; }
})();
NODE
