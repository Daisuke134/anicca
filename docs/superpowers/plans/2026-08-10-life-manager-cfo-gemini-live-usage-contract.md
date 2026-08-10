# CFO-2a2.4b Gemini Live Usage Contract Implementation Plan

**Status:** COMPLETE — verified and ready for CFO-2a2.4c.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development task by task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert one Gemini Live provider `usageMetadata` message into truthful, content-free CFO evidence without
inventing a provider response ID or response model.

**Architecture:** Add one pure export beside `normalizeGeminiUsageEvidence`. Reuse existing validation helpers and
the evidence shape; add no I/O or abstraction. The verified schema receives a separate local correlation identity.

**Tech Stack:** CommonJS, Node built-in `node:test`, existing ledger validators.

## Global constraints

- Luna owns implementation commands and exactly `apps/life-call/lib/ledger.js` plus `ledger.test.js`.
- Sol owns review, final verification, spec closure, commit, and push.
- At most 30 production additions and 40 test additions; two files and 70 additions total.
- No dependency, migration, RPC/store, span lifecycle, WebSocket/server, duration estimate, scheduler, launchd, or
  Telegram change.
- Provider counts are facts. Provider response ID/model stay `null`; local identity stays in `local_correlation_id`.
- `usage_sequence` is local observation order only. It is not a delta; this slice never appends or sums observations.
- Run every command from `apps/life-call` inside the CFO worktree.

## Task 1: Normalize one Live usage message

**Interface:** `normalizeGeminiLiveUsageEvidence(message, context)` returns the exact Section 13.3 contract.

- [x] **Step 1 — write two focused tests first**

Normal fixture:

```js
const message = { usageMetadata: {
  promptTokenCount: 515, responseTokenCount: 38, totalTokenCount: 560,
  cachedContentTokenCount: 2, thoughtsTokenCount: 5, toolUsePromptTokenCount: 1,
}, serverContent: { outputTranscription: { text: "LIVE_OUTPUT_SENTINEL" } } };
const context = {
  owner_id: "u1", financial_unit_id: "life_manager_saas",
  occurred_at: "2026-08-10T01:02:03.000Z", trace_id: "1".repeat(32),
  request_model: "models/gemini-2.5-flash-native-audio-preview-09-2025",
  live_session_id: "2".repeat(32), usage_sequence: 7,
};
```

Assert one hand-written complete result: provider ID/model are null; local correlation is exact; output is `38`;
OTel output is `43`; stream is `true`; output type is `speech`; optional fields map exactly; no `gen_ai.response.*`
or sentinel appears; inputs are unchanged; repeated calls are deep-equal.

The second test proves zero/missing optionals plus one compact invalid matrix: missing response count, one hostile
non-integer count, one negative count, one unsafe count, output+thought overflow, zero session ID, invalid sequence,
wrong Live model, and one representative invalid shared-context case (`trace_id`). Existing GenerateContent tests already
cover the shared validator edge-case classes; do not duplicate them. Every failure matches
`/^cfo_provider_usage_invalid:[a-z_]+$/` and omits hostile values.

- [x] **Step 2 — run RED**

```bash
node --test lib/ledger.test.js
```

Expected: existing cases pass; exactly the two new cases fail because the export is absent.

- [x] **Step 3 — add the minimum pure implementation**

Reuse `plainUsageInput`, `usageString`, `providerCount`, `validUsageTimestamp`, and `usageFail`. Validate the exact
current wire model including `models/`, local ID, observation sequence, owner/unit/time/trace. Build the result directly:

```js
provider_request_id = null;
local_correlation_id = `live-session:${context.live_session_id}`;
response_model = null;
tokens.output = message.usageMetadata.responseTokenCount;
```

OTel includes operation `generate_content`, provider `gcp.gemini`, exact request model, `gen_ai.request.stream: true`,
`gen_ai.output.type: "speech"`, provider input/output/cache/reasoning counts, address, and `443`. OTel output equals
response plus reasoning with safe-integer validation. Emit no `gen_ai.response.*`. Export beside the existing Gemini
normalizer.

- [x] **Step 4 — run GREEN and scope gates**

```bash
node --test lib/ledger.test.js
npm run test:cfo
npm test
node --check lib/ledger.js
git diff --check -- lib/ledger.js lib/ledger.test.js
git diff --numstat -- lib/ledger.js lib/ledger.test.js \
  | awk '{ added += $1; files += 1 } END { print "files=" files, "added=" added; exit !(files == 2 && added <= 70) }'
```

Expected: every command exits `0`; exactly two files and at most 70 additions. Return exact RED/GREEN totals and
line counts to Sol. Do not commit or push.

## Plan self-review

- Coverage: exact provider mapping, truthful null identity/model, privacy, optional absence, overflow, immutability.
- Scope: two existing pure files; no runtime or persistence.
- Rollup: intentionally absent; sequence is observation order and repeated observations are not declared additive.
- Placeholders: none. Model, fields, attributes, errors, commands, and limits are fixed.

## Completion evidence

- RED: 12/14 passed; only the two calls to the missing export failed.
- GREEN: focused 14/14, CFO 264/264, full 906/906 from Luna; Sol independently reran focused/CFO and full exit `0`.
- Review: one Important optional-zero regression was fixed by the same Luna; re-review returned `ship`.
- Scope: exactly two implementation files and 54 additions; syntax and diff gates passed.
- No I/O, persistence, runtime, or Telegram mutation occurred.
