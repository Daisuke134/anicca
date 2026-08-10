# CFO-2a2.4c1 Gemini Live Append RPC Implementation Plan

**Status:** READY — first review fixes applied; fresh re-review required before Luna implementation.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development task by task.

**Goal:** Make the existing typed append RPC idempotently accept truthful Gemini Live evidence while keeping the
verified provider caller and receipt unchanged.

**Architecture:** Replace one PostgreSQL function signature in a forward migration. Reuse the existing evidence table,
provider unique constraint, local partial unique index, RPC name, real provider E2E, and error contract. Add no table,
service, dependency, or runtime wiring.

**Tech Stack:** PostgreSQL 18, PL/pgSQL, Node built-in `node:test`, disposable Docker PostgreSQL/PostgREST, real Gemini
GenerateContent regression.

## Global constraints

- Luna owns implementation commands and exactly these three files:
  1. new `apps/life-call/migrations/2026-08-10-cfo-model-usage-evidence-live-append-rpc.sql`;
  2. existing `apps/life-call/lib/cfo-model-usage-evidence-migration.test.js`;
  3. existing `apps/life-call/test/postgres/cfo-provider-usage-real-e2e.sh`.
- Sol owns spec/plan, review, independent verification, spec closure, commit, and push.
- At most three files and 90 additions total. No Node production/store/span, WebSocket/server, aggregation, duration
  estimate, scheduler, launchd, Telegram, dependency, or production database change.
- Preserve all existing provider behavior. Do not loosen table constraints, privileges, append-only guards, or receipt
  disclosure.
- Run implementation commands from `apps/life-call` inside the CFO worktree. Do not commit or push.

## Task 1: Replace the append RPC with a dual-identity contract

- [ ] **Step 1 — write the focused static test first**

Add this path beside the existing migration paths:

```js
const liveAppendMigrationPath = path.join(
  __dirname, "..", "migrations", "2026-08-10-cfo-model-usage-evidence-live-append-rpc.sql",
);
```

Add this complete focused test:

```js
test("CFO Live append RPC supports one truthful local identity without changing provider receipts", () => {
  const sql = fs.readFileSync(liveAppendMigrationPath, "utf8");
  assert.match(sql, /DROP FUNCTION public\.lm_append_cfo_model_usage_evidence\(text, text, text, text, text, bigint, timestamptz, text, text, text, bigint, bigint, bigint, bigint, bigint, bigint, text\)/i);
  assert.match(sql, /p_evidence_status text,\s*p_local_correlation_id text DEFAULT NULL\s*\)/is);
  assert.match(sql, /local_correlation_id\s*\).*p_local_correlation_id.*ON CONFLICT DO NOTHING\s*RETURNING \*/is);
  assert.doesNotMatch(sql, /ON CONFLICT\s+(?:ON CONSTRAINT|\()/i);
  assert.match(sql, /provider_request_id IS NOT DISTINCT FROM p_provider_request_id.*local_correlation_id IS NOT DISTINCT FROM p_local_correlation_id/is);
  ["uid", "financial_unit_id", "attribution_status", "provider", "provider_request_id", "usage_sequence",
    "occurred_at", "trace_id", "request_model", "response_model", "input_tokens", "output_tokens",
    "total_tokens", "cached_input_tokens", "reasoning_output_tokens", "tool_input_tokens", "evidence_status",
    "local_correlation_id"].forEach((field) =>
    assert.match(sql, new RegExp(`stored\\.${field}\\s+IS DISTINCT FROM\\s+p_${field}`, "i")));
  assert.match(sql, /RAISE EXCEPTION 'provider_usage_identity_conflict' USING ERRCODE = '23505'/i);
  const receipt = sql.slice(sql.indexOf("jsonb_strip_nulls"), sql.indexOf(");", sql.indexOf("jsonb_strip_nulls")));
  assert.deepEqual([...receipt.matchAll(/'([a-z_]+)'\s*,/g)].map((match) => match[1]),
    ["public_ref", "provider", "provider_request_id", "local_correlation_id", "usage_sequence", "trace_id", "created_at"]);
  assert.match(sql, /REVOKE ALL ON FUNCTION public\.lm_append_cfo_model_usage_evidence\([^;]+, text\) FROM PUBLIC, anon, authenticated, service_role/i);
  assert.match(sql, /GRANT EXECUTE ON FUNCTION public\.lm_append_cfo_model_usage_evidence\([^;]+, text\) TO service_role/i);
  assert.doesNotMatch(sql, /\b(?:UPDATE|DELETE|EXECUTE\s+(?:format|immediate))\b|\b(?:content|raw_response|metadata|otel_|token_price|billing|secret)\w*/i);
});
```

- [ ] **Step 2 — run the focused static RED**

```bash
node --test lib/cfo-model-usage-evidence-migration.test.js
```

Expected: all historical tests pass and only the new test fails because the migration file is absent.

- [ ] **Step 3 — add the smallest real PostgreSQL regression before implementation**

Add this variable:

```bash
LIVE_RPC_MIGRATION="$ROOT_DIR/migrations/2026-08-10-cfo-model-usage-evidence-live-append-rpc.sql"
```

Apply it after the base RPC and Live provenance migrations:

```bash
"${PSQL[@]}" -f "$LIVE_RPC_MIGRATION" >/dev/null 2>&1
```

Extend the existing `DO` block's `DECLARE` list with:

```sql
first_receipt jsonb;
retry_receipt jsonb;
observed_at timestamptz := '2026-08-10T01:02:03Z';
```

Place this fixture inside that block after the existing schema checks:

```sql
SELECT public.lm_append_cfo_model_usage_evidence(
  'cfo-e2e-owner', 'life_manager_saas', 'attributed', 'gcp.gemini', NULL, 7,
  observed_at, repeat('6', 32), 'models/gemini-2.5-flash-native-audio-preview-09-2025', NULL,
  515, 38, 560, 2, 5, 1, 'provider_reported', 'live-session:' || repeat('7', 32)
) INTO first_receipt;
SELECT public.lm_append_cfo_model_usage_evidence(
  'cfo-e2e-owner', 'life_manager_saas', 'attributed', 'gcp.gemini', NULL, 7,
  observed_at, repeat('6', 32), 'models/gemini-2.5-flash-native-audio-preview-09-2025', NULL,
  515, 38, 560, 2, 5, 1, 'provider_reported', 'live-session:' || repeat('7', 32)
) INTO retry_receipt;
IF first_receipt IS DISTINCT FROM retry_receipt
   OR first_receipt->>'local_correlation_id' <> 'live-session:' || repeat('7', 32)
   OR first_receipt ? 'provider_request_id'
   OR jsonb_object_length(first_receipt) <> 6 THEN
  RAISE EXCEPTION 'live_receipt_contract_failed';
END IF;
BEGIN
  PERFORM public.lm_append_cfo_model_usage_evidence(
    'cfo-e2e-owner', 'life_manager_saas', 'attributed', 'gcp.gemini', NULL, 7,
    observed_at, repeat('8', 32), 'models/gemini-2.5-flash-native-audio-preview-09-2025', NULL,
    515, 38, 560, 2, 5, 1, 'provider_reported', 'live-session:' || repeat('7', 32)
  );
  RAISE EXCEPTION 'expected_provider_usage_identity_conflict';
EXCEPTION WHEN unique_violation THEN
  IF SQLERRM <> 'provider_usage_identity_conflict' THEN RAISE; END IF;
END;
```

Keep the final real Gemini provider path unchanged: its PostgREST client omits the defaulted local argument, stores
two real provider responses, receives the old six-key provider receipt, and prints exactly
`cfo-provider-usage-real-e2e: PASS rows=2 spans=2`. The transaction rollback keeps the final row count at two.

- [ ] **Step 4 — run the real PostgreSQL RED before any provider call**

```bash
GEMINI_API_KEY=red-only bash test/postgres/cfo-provider-usage-real-e2e.sh
```

Expected: non-zero exit while applying the absent migration, before PostgREST starts or Gemini is called.

- [ ] **Step 5 — add the minimum forward migration**

Create exactly this migration; line wrapping may change but semantics may not:

```sql
DROP FUNCTION public.lm_append_cfo_model_usage_evidence(text, text, text, text, text, bigint, timestamptz, text, text, text, bigint, bigint, bigint, bigint, bigint, bigint, text);

CREATE FUNCTION public.lm_append_cfo_model_usage_evidence(
  p_uid text, p_financial_unit_id text, p_attribution_status text,
  p_provider text, p_provider_request_id text, p_usage_sequence bigint,
  p_occurred_at timestamptz, p_trace_id text, p_request_model text, p_response_model text,
  p_input_tokens bigint, p_output_tokens bigint, p_total_tokens bigint,
  p_cached_input_tokens bigint, p_reasoning_output_tokens bigint, p_tool_input_tokens bigint,
  p_evidence_status text, p_local_correlation_id text DEFAULT NULL
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public, pg_temp
AS $$
DECLARE
  stored public.lm_cfo_model_usage_evidence%ROWTYPE;
BEGIN
  INSERT INTO public.lm_cfo_model_usage_evidence
    (uid, financial_unit_id, attribution_status, provider, provider_request_id, usage_sequence,
     occurred_at, trace_id, request_model, response_model, input_tokens, output_tokens, total_tokens,
     cached_input_tokens, reasoning_output_tokens, tool_input_tokens, evidence_status, local_correlation_id)
  VALUES
    (p_uid, p_financial_unit_id, p_attribution_status, p_provider, p_provider_request_id, p_usage_sequence,
     p_occurred_at, p_trace_id, p_request_model, p_response_model, p_input_tokens, p_output_tokens, p_total_tokens,
     p_cached_input_tokens, p_reasoning_output_tokens, p_tool_input_tokens, p_evidence_status, p_local_correlation_id)
  ON CONFLICT DO NOTHING
  RETURNING * INTO stored;
  IF NOT FOUND THEN
    SELECT * INTO stored
    FROM public.lm_cfo_model_usage_evidence
    WHERE provider = p_provider
      AND usage_sequence = p_usage_sequence
      AND provider_request_id IS NOT DISTINCT FROM p_provider_request_id
      AND local_correlation_id IS NOT DISTINCT FROM p_local_correlation_id;
    IF NOT FOUND
      OR stored.uid IS DISTINCT FROM p_uid
      OR stored.financial_unit_id IS DISTINCT FROM p_financial_unit_id
      OR stored.attribution_status IS DISTINCT FROM p_attribution_status
      OR stored.provider IS DISTINCT FROM p_provider
      OR stored.provider_request_id IS DISTINCT FROM p_provider_request_id
      OR stored.usage_sequence IS DISTINCT FROM p_usage_sequence
      OR stored.occurred_at IS DISTINCT FROM p_occurred_at
      OR stored.trace_id IS DISTINCT FROM p_trace_id
      OR stored.request_model IS DISTINCT FROM p_request_model
      OR stored.response_model IS DISTINCT FROM p_response_model
      OR stored.input_tokens IS DISTINCT FROM p_input_tokens
      OR stored.output_tokens IS DISTINCT FROM p_output_tokens
      OR stored.total_tokens IS DISTINCT FROM p_total_tokens
      OR stored.cached_input_tokens IS DISTINCT FROM p_cached_input_tokens
      OR stored.reasoning_output_tokens IS DISTINCT FROM p_reasoning_output_tokens
      OR stored.tool_input_tokens IS DISTINCT FROM p_tool_input_tokens
      OR stored.evidence_status IS DISTINCT FROM p_evidence_status
      OR stored.local_correlation_id IS DISTINCT FROM p_local_correlation_id THEN
      RAISE EXCEPTION 'provider_usage_identity_conflict' USING ERRCODE = '23505';
    END IF;
  END IF;
  RETURN jsonb_strip_nulls(jsonb_build_object(
    'public_ref', stored.public_ref, 'provider', stored.provider,
    'provider_request_id', stored.provider_request_id, 'local_correlation_id', stored.local_correlation_id,
    'usage_sequence', stored.usage_sequence, 'trace_id', stored.trace_id, 'created_at', stored.created_at
  ));
END;
$$;

REVOKE ALL ON FUNCTION public.lm_append_cfo_model_usage_evidence(text, text, text, text, text, bigint, timestamptz, text, text, text, bigint, bigint, bigint, bigint, bigint, bigint, text, text) FROM PUBLIC, anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.lm_append_cfo_model_usage_evidence(text, text, text, text, text, bigint, timestamptz, text, text, text, bigint, bigint, bigint, bigint, bigint, bigint, text, text) TO service_role;
```

- [ ] **Step 6 — run GREEN and scope gates**

```bash
node --test lib/cfo-model-usage-evidence-migration.test.js
GEMINI_API_KEY="$GEMINI_API_KEY" bash test/postgres/cfo-provider-usage-real-e2e.sh
npm run test:cfo
npm test
bash -n test/postgres/cfo-provider-usage-real-e2e.sh
git diff --check -- migrations/2026-08-10-cfo-model-usage-evidence-live-append-rpc.sql lib/cfo-model-usage-evidence-migration.test.js test/postgres/cfo-provider-usage-real-e2e.sh
git diff --numstat -- migrations/2026-08-10-cfo-model-usage-evidence-live-append-rpc.sql lib/cfo-model-usage-evidence-migration.test.js test/postgres/cfo-provider-usage-real-e2e.sh \
  | awk '{ added += $1; files += 1 } END { print "files=" files, "added=" added; exit !(files == 3 && added <= 90) }'
```

Expected: every command exits `0`, the real E2E prints the exact PASS line, and scope is three files / at most 90
additions. Return exact RED/GREEN totals and counts to Sol. Do not commit or push.

## Plan self-review

- Truth: provider and local identities remain separate; no invented provider ID/model.
- Idempotency: both unique paths reach one exact compare-before-return contract.
- Compatibility: the defaulted final parameter and stripped null receipt preserve the old provider client.
- Privacy: the RPC accepts typed counts/identity only; no content or raw payload exists.
- TDD: static and disposable-real gates fail before the migration exists; the real Gemini call occurs only after GREEN.
- YAGNI: one migration plus two existing tests; Node persistence/span/bridge stay deferred.
- Placeholders: none. Signature, identities, receipt, error, commands, output, and size limit are fixed.
