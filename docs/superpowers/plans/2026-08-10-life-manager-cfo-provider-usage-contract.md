# Life Manager CFO-2a2.1 Provider Usage Contract Implementation Plan

**Status:** READY — one Luna task; no later CFO-2a2 slice is included.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Implement the single
> task with strict RED → minimal GREEN → focused review.

**Goal:** Convert one real-shaped Gemini `generateContent` response into content-free provider-reported usage
evidence and the pinned OpenTelemetry GenAI attribute projection.

**Architecture:** Extend the existing pure boundary area in `apps/life-call/lib/ledger.js` and reuse
`ledger.test.js`. The function receives parsed JSON and explicit context; it performs no I/O. Storage, OpenTelemetry
SDK/export, pricing, call-site wiring, and Gemini Live remain later slices.

**Tech Stack:** Node.js CommonJS, built-in `node:test`, built-in `node:assert/strict`; no dependency change.

## Global constraints

- Modify exactly `apps/life-call/lib/ledger.js` and `apps/life-call/lib/ledger.test.js`.
- Add at most 45 production LOC and 55 test LOC; total additions at most 100.
- Sol owns spec/plan/final verification/push. Luna owns production code, tests, implementation commands, and the
  implementation commit.
- Add no file, dependency, SDK, collector, exporter, migration, table, RPC, network call, environment variable,
  scheduler, logger, price card, or call-site change.
- Use Gemini response fields only. Never count prompt text, candidates, duration, characters, or local tokens.
- Emit no prompt, candidate, system instruction, tool argument/result, raw response, or unknown key.
- The exact OpenTelemetry provider value is `gcp.gemini`, pinned to semantic-conventions-genai commit
  `46d43c8949afb53765a202e89f4534eeb75ca3fa`.
- Tests call the real export with literal objects. No mocks, generated expected objects, source-text assertions, or
  broad hostile-object matrix.

---

### Task 1: Normalize Gemini provider usage

**Files**

- Modify: `apps/life-call/lib/ledger.test.js`
- Modify: `apps/life-call/lib/ledger.js`

**Estimated change:** 45–55 test LOC, then 35–45 production LOC.

- [ ] **Step 1 — Write two behavioral tests first**

Add one exact happy-path test and one compact zero/missing/invalid test:

1. A literal response with `responseId`, `modelVersion`, all six usage counts, and secret-shaped candidate
   content maps to the exact record from the child spec. Assert:
   - `tokens.output` is the provider candidate count;
   - `gen_ai.usage.output_tokens` is candidate + reasoning;
   - no content or unknown key survives;
   - both inputs remain unchanged;
   - a repeated call is deep-equal.
2. A valid response with zero required counts and absent optional counts preserves required zero, returns optional
   `null`, and omits optional OTel keys. In the same test, a compact cases table rejects:
   - missing/blank response ID or model;
   - missing, negative, fractional, `NaN`, infinite, or unsafe counts;
   - unsafe candidate + reasoning addition;
   - invalid timestamp, trace ID, owner, requested model, or non-`life_manager_saas` unit.
   Every error must match only `/^cfo_provider_usage_invalid:[a-z_]+$/` and exclude a sentinel value.

- [ ] **Step 2 — Run RED**

From `apps/life-call`:

```bash
node --test lib/ledger.test.js
```

Expected: the existing ten tests pass and the two new tests fail only because
`ledger().normalizeGeminiUsageEvidence is not a function`.

- [ ] **Step 3 — Implement the smallest pure adapter**

Reuse `createCfoSupabaseRpc` with a separate `cfo_provider_usage_invalid:` error provenance to obtain
`fail`, `plain`, and `timestamp`. Add only:

- one helper for trimmed non-empty strings;
- one helper for required/optional non-negative safe-integer counts;
- `normalizeGeminiUsageEvidence(response, context)`.

The output must match child spec §5 exactly. Required mappings:

| Output | Provider/context source |
|---|---|
| `provider_request_id` | `response.responseId` |
| `response_model` | `response.modelVersion` |
| `tokens.input` | `usageMetadata.promptTokenCount` |
| `tokens.output` | `usageMetadata.candidatesTokenCount` |
| `tokens.cached_input` | optional `cachedContentTokenCount`, otherwise `null` |
| `tokens.reasoning_output` | optional `thoughtsTokenCount`, otherwise `null` |
| `tokens.tool_input` | optional `toolUsePromptTokenCount`, otherwise `null` |
| `tokens.total` | `usageMetadata.totalTokenCount` |
| OTel `input_tokens` | provider prompt count |
| OTel `output_tokens` | provider candidates + provider thoughts; safe-integer checked |

Optional OTel cache/reasoning keys are present when and only when the provider field exists, including explicit
zero. Do not recompute or validate the provider's `totalTokenCount` against component sums.

Export `normalizeGeminiUsageEvidence` beside `normalizeApiCostEvent`.

- [ ] **Step 4 — Run GREEN and regressions**

```bash
node --test lib/ledger.test.js
npm run test:cfo
npm test
node --check lib/ledger.js
```

Expected: focused ledger 12/12; CFO suite 254/254; full suite exits 0; syntax check exits 0.

- [ ] **Step 5 — Enforce Ponytail scope**

```bash
git diff --check
git diff --numstat -- apps/life-call/lib/ledger.js apps/life-call/lib/ledger.test.js
git status --short
```

Expected: only the two planned files; production additions ≤45, tests ≤55, total ≤100.

- [ ] **Step 6 — Commit for review, do not push**

```bash
git add apps/life-call/lib/ledger.js apps/life-call/lib/ledger.test.js
git commit -m "feat(cfo): normalize provider-reported Gemini usage"
```

Write the RED/GREEN/count/scope evidence to the ignored Superpowers task report. Sol then generates an exact diff
package, obtains a fresh focused review, reruns final verification, closes spec checkboxes, fetches, and pushes.

