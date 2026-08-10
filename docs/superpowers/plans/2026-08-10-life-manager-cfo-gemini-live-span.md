# CFO-2a2.4c3 Gemini Live Span Implementation Plan

**Status:** READY — Ponytail scope and fresh Sol review required before Luna implementation.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development task by task.

**Goal:** Correlate one successfully stored Gemini Live usage observation with one truthful, content-free OTel span.

**Architecture:** Extend the existing provider usage span module and tests. Reuse its tracer lifecycle/error contract,
the 4b Live normalizer, and the 4c2 Live store. Start a span, derive trace/time, normalize, store once, then finish the
span. Add no module, dependency, migration, service, or bridge wiring.

**Tech Stack:** CommonJS, OpenTelemetry API/Node SDK already pinned, Node built-in `node:test`.

## Global constraints

- Luna owns exactly `apps/life-call/lib/cfo-provider-usage-span.js` and
  `apps/life-call/lib/cfo-provider-usage-span.test.js`; Sol owns docs/review/verification/commit/push.
- Soft targets: at most 35 production additions and 35 test additions; exactly two files / at most 70 additions total.
- Preserve `captureGeminiGenerateContent`, its public behavior, span name, attributes, ordering, errors, and tests.
- No migration/database deployment, real provider call, WebSocket/server/bridge, aggregation, duration estimate,
  scheduler, launchd, Telegram, logging, retry, dependency, or exported abstraction beyond the one Live function.
- Run every command from `apps/life-call`. Do not commit or push.

## Task 1: Capture one stored Live observation

- [ ] **Step 1 — write the smallest RED tests**

Add one success test with an in-memory exporter, injected clock, injected append, and a Live content sentinel. Require:

- exact CLIENT span name `generate_content models/gemini-2.5-flash-native-audio-preview-09-2025`;
- append called once with the original message, context extended only by the injected RFC3339 `occurred_at` and the
  nonzero 32-hex recording trace ID, and unchanged store options;
- append observes zero finished spans, proving success ends only after storage;
- the returned value is the append receipt;
- one finished span has the normalized Live OTel attributes/counts, no events, and no sentinel/content/raw metadata.

Add one compact failure test covering invalid message, append failure, and one Live-specific zero-trace recording
case. Invalid input ends one fixed `invalid_response` error span and makes zero append calls. Append failure ends one
`store` error span. The zero-trace case makes zero append calls, throws fixed `tracing`, and leaves one ended CLIENT
span with the exact Live name/model/base attributes, no events/content/log/retry. Existing tests already cover the rest
of the unavailable/non-recording matrix; do not duplicate it.

- [ ] **Step 2 — run RED**

```bash
node --test lib/cfo-provider-usage-span.test.js
```

Expected: the four historical GenerateContent tests pass and only the two new Live tests fail because the export is
absent.

- [ ] **Step 3 — add the minimum span extension**

Import the Live normalizer/store and define the exact Live model/name constants. Reuse or minimally generalize the
existing option validator so the default append is path-specific. The Live function accepts an already-received
message and a closed caller context without time/trace, starts one recording CLIENT span, creates a context with the
clock time and span trace, normalizes, appends once, then sets normalized attributes and ends success. On normalize or
store failure, finish the same span once with only a fixed `error.type`, throw the existing fixed-prefix error, and do
not retry or log. Return the closed append receipt.

- [ ] **Step 4 — run GREEN and scope gates**

```bash
node --test lib/cfo-provider-usage-span.test.js
npm run test:cfo
npm test
node --check lib/cfo-provider-usage-span.js
git diff --check -- lib/cfo-provider-usage-span.js lib/cfo-provider-usage-span.test.js
git diff --numstat -- lib/cfo-provider-usage-span.js lib/cfo-provider-usage-span.test.js \
  | awk '{ added += $1; files += 1 } END { print "files=" files, "added=" added; exit !(files == 2 && added <= 70) }'
```

Expected: all commands exit `0`; exactly two files and at most 70 additions. Return exact RED/GREEN totals and line
counts to Sol. Do not commit or push.

## Plan self-review

- Truth: provider counts are span attributes; observation sequence is preserved, never summed.
- Correlation: the stored row receives the exact recording span trace ID and injected observation time.
- Ordering: success exists only after append succeeds; failures close the same span once.
- Privacy: span name/attributes/errors contain no message content or raw metadata.
- YAGNI: two existing files, one new export, no bridge or deployment.
- Placeholders: none. Function, model/name, ordering, errors, tests, commands, and size limit are fixed.
