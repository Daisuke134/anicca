# CFO-2a2.4c2 Gemini Live Node Store Implementation Plan

**Status:** READY — Ponytail scope and fresh Sol review required before Luna implementation.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development task by task.

**Goal:** Append one normalized Gemini Live usage observation through the existing Node RPC store without changing the
verified GenerateContent path.

**Architecture:** Extend the existing store with one Live entry point and make its receipt validator select one of two
closed identity shapes. Reuse the existing normalizers, RPC helper, endpoint, error prefix, and tests. Add no module,
dependency, migration, service, or runtime wiring.

**Tech Stack:** CommonJS, Node built-in `node:test`, existing Supabase/PostgREST RPC helper.

## Global constraints

- Luna owns exactly `apps/life-call/lib/cfo-provider-usage-store.js` and
  `apps/life-call/lib/cfo-provider-usage-store.test.js`; Sol owns docs/review/verification/commit/push.
- Soft targets: at most 30 production additions and 35 test additions; exactly two files / at most 65 additions total.
- Preserve the existing `appendGeminiUsageEvidence` export, request body, receipt shape, error contract, and tests.
- No migration/database deployment, real provider call, span/OTel lifecycle, WebSocket/bridge, aggregation, duration
  estimate, scheduler, launchd, Telegram, logging, retry, dependency, or exported abstraction.
- Run every command from `apps/life-call`. Do not commit or push.

## Task 1: Append one Live usage observation

- [ ] **Step 1 — write the smallest RED tests**

Add one complete success test using a Live message that contains both `usageMetadata` and a content sentinel. Require:

- one call to `lm_append_cfo_model_usage_evidence` with the existing auth headers;
- this exact 18-key body: `p_uid`, `p_financial_unit_id`, `p_attribution_status`, `p_provider`,
  `p_provider_request_id`, `p_usage_sequence`, `p_occurred_at`, `p_trace_id`, `p_request_model`, `p_response_model`,
  `p_input_tokens`, `p_output_tokens`, `p_total_tokens`, `p_cached_input_tokens`, `p_reasoning_output_tokens`,
  `p_tool_input_tokens`, `p_evidence_status`, `p_local_correlation_id`; the two provider-only values are null and the
  local value is `live-session:<id>`;
- a returned exact six-key local receipt that is cloned/frozen and contains no provider identity or sentinel;
- the original message/context remain unchanged.

Add one compact failure test: one representative invalid Live input makes zero calls; wrong local identity, wrong
`trace_id`, mixed provider/local identity, or one extra receipt key each fails with the existing fixed redacted prefix,
makes one call, never retries, and never logs. Do not duplicate the normalizer's count/context edge-case matrix.

- [ ] **Step 2 — run RED**

```bash
node --test lib/cfo-provider-usage-store.test.js
```

Expected: the historical provider tests pass and only the new Live tests fail because the export is absent.

- [ ] **Step 3 — add the minimum store extension**

Import `normalizeGeminiLiveUsageEvidence`. Keep one internal RPC-body builder for already-normalized evidence. Make the
receipt validator choose the exact provider or local six-key set from the normalized evidence, compare only the
shared `provider`, `usage_sequence`, and `trace_id` plus that path's expected identity, and return a cloned/frozen
six-key projection. Export `appendGeminiLiveUsageEvidence` beside the existing function. Never pass the original
message or content to the RPC helper. The existing provider path must keep its exact 17-key body and must not send
`p_local_correlation_id`.

- [ ] **Step 4 — run GREEN and scope gates**

```bash
node --test lib/cfo-provider-usage-store.test.js
npm run test:cfo
npm test
node --check lib/cfo-provider-usage-store.js
git diff --check -- lib/cfo-provider-usage-store.js lib/cfo-provider-usage-store.test.js
git diff --numstat -- lib/cfo-provider-usage-store.js lib/cfo-provider-usage-store.test.js \
  | awk '{ added += $1; files += 1 } END { print "files=" files, "added=" added; exit !(files == 2 && added <= 65) }'
```

Expected: all commands exit `0`; exactly two files and at most 65 additions. Return exact RED/GREEN totals and line
counts to Sol. Do not commit or push.

## Plan self-review

- Truth: local identity remains local; provider ID/model stay null.
- Compatibility: the provider export/body/receipt are unchanged and remain covered by historical tests.
- Privacy: only normalized typed evidence enters the RPC body; no content/raw payload is stored or returned.
- YAGNI: two existing files, one new export, no deployment or runtime wiring.
- Placeholders: none. Function, body, receipt shapes, errors, commands, and size limit are fixed.
