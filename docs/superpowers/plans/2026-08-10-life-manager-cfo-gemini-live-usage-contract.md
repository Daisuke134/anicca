# CFO-2a2.4a Gemini Live Usage Contract Implementation Plan

**Status:** READY — only active task.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Normalize one Gemini Live provider `usageMetadata` message into the existing content-free CFO evidence
shape without inventing a provider response ID or response model.

**Architecture:** Add one pure export beside `normalizeGeminiUsageEvidence`. Reuse the existing validation helpers
and output shape, but map Live's `responseTokenCount` and omit both provider-response OTel attributes. No I/O or
runtime wiring changes.

**Tech Stack:** CommonJS, Node built-in `node:test` / strict assert, existing ledger validators.

## Global Constraints

- Luna owns production/test code and implementation commands. Sol owns review, final verification, closure, commit, and push.
- Modify only `apps/life-call/lib/ledger.js` and `apps/life-call/lib/ledger.test.js`.
- Soft target: at most 30 production additions and 55 test additions; two files and 85 additions total.
- Add no dependency, helper file, migration, store/span/WebSocket/server/scheduler/launchd/Telegram behavior.
- Provider token fields are facts; local session identity and request-model fallback stay explicitly distinguishable.
- Never emit prompt, audio, transcript, function arguments, credentials, or local session ID as provider-response OTel attributes.

---

### Task 1: Normalize one Live usage message

**Files:**
- Modify: `apps/life-call/lib/ledger.js`
- Modify: `apps/life-call/lib/ledger.test.js`

**Interfaces:**
- Consumes: `normalizeGeminiLiveUsageEvidence(message, context)` with the exact section 13.2 contract.
- Produces: the existing evidence shape, `provider_request_id: "local-live-session:<32hex>"`,
  `response_model: "request-model:<exact requested model>"`, caller-supplied `usage_sequence`, and content-free
  OTel attributes without `gen_ai.response.id/model`.

- [ ] **Step 1: Write the two focused tests first**

The normal case uses literal Live provider data and content sentinels:

```js
const message = { usageMetadata: {
  promptTokenCount: 515, responseTokenCount: 38, totalTokenCount: 560,
  cachedContentTokenCount: 2, thoughtsTokenCount: 5, toolUsePromptTokenCount: 1,
}, serverContent: { outputTranscription: { text: "LIVE_OUTPUT_SENTINEL" } } };
const context = {
  owner_id: "u1", financial_unit_id: "life_manager_saas",
  occurred_at: "2026-08-10T01:02:03.000Z", trace_id: "1".repeat(32),
  request_model: "gemini-2.5-flash-native-audio-preview-09-2025",
  live_session_id: "2".repeat(32), usage_sequence: 7,
};
```

Assert a hand-written complete result: identity/model fallbacks have the exact `local-live-session:` and
`request-model:` prefixes; output tokens are `38`; OTel output tokens are `43`; stream is `true`; output type is
`speech`; optional fields map exactly; response ID/model OTel keys and all sentinels are absent; inputs are unchanged;
a repeat call is deep-equal.

The second test proves zero/missing-optionals and a literal invalid matrix: missing/negative/string/fractional/unsafe
counts, overflow of response+thoughts, invalid/missing session ID, negative/fractional sequence, wrong Live model,
and invalid owner/unit/time/trace. Shared plain-object guards already have dedicated coverage and are not duplicated.
Every failure matches only
`/^cfo_provider_usage_invalid:[a-z_]+$/` and contains no hostile value.

- [ ] **Step 2: Run RED**

```bash
node --test lib/ledger.test.js
```

Expected: only the two new cases fail because `normalizeGeminiLiveUsageEvidence` is not exported.

- [ ] **Step 3: Add the minimum pure implementation**

Use the existing `plainUsageInput`, `usageString`, `providerCount`, `validUsageTimestamp`, and `usageFail`. Validate
exact current model, session ID, sequence, owner/unit/time/trace. Build the literal evidence object directly; do not
manufacture a `GenerateContentResponse` and do not add an abstraction layer. Map:

```js
tokens.output = usageMetadata.responseTokenCount;
provider_request_id = `local-live-session:${context.live_session_id}`;
response_model = `request-model:${context.request_model}`;
```

OTel attributes include exact `gen_ai.operation.name: "generate_content"`, `gen_ai.provider.name`,
`gen_ai.request.model`, `gen_ai.request.stream: true`, `gen_ai.output.type: "speech"`, provider input/output counts,
optional cache/reasoning counts, `server.address`, and `server.port`. They contain no `gen_ai.response.*`.
Export the function beside `normalizeGeminiUsageEvidence`.

- [ ] **Step 4: Run GREEN and scope gates**

```bash
node --test lib/ledger.test.js
npm run test:cfo
npm test
node --check lib/ledger.js
git diff --check
git diff --stat
```

Expected: all commands exit `0`; only the two planned files change and additions remain at or below 85. Return exact
RED/GREEN totals, line counts, and concerns to Sol. Do not commit or push.

## Plan self-review

- Coverage: provider count mapping, explicit local provenance, invalid input, privacy, immutability, and suite gates.
- Scope: two existing pure files; no runtime/storage/span behavior.
- Placeholders: none. Exact model, field names, identity format, errors, commands, and limits are fixed.
