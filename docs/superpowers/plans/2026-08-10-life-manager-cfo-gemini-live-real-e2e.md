# CFO-2a2.4d2 Real Gemini Live Usage E2E Implementation Plan

**Status:** READY — CFO-2a2.4d1 is verified; this is the first unfinished CFO item.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development task by task.

**Goal:** Prove one genuine Gemini Live `usageMetadata` message becomes the matching private PostgreSQL row and
content-free OpenTelemetry span through the already-built CFO path.

**Architecture:** Extend the existing disposable provider E2E only. Reuse its real API key boundary, temporary
PostgreSQL/PostgREST, console span capture, redaction, cleanup, and current two `generateContent` calls. Open one real
Gemini Live WebSocket with existing `ws` and `call-logic.js` builders, capture the first post-turn usage message, and
pass that exact object once to `captureGeminiLiveUsageObservation`.

**Tech Stack:** Bash, Node CommonJS heredoc, existing `ws`, existing Gemini Live builders, disposable Docker PostgreSQL
18/PostgREST, OpenTelemetry exporter already owned by the capture path.

## Global constraints

- Luna owns exactly `apps/life-call/test/postgres/cfo-provider-usage-real-e2e.sh`; Sol owns docs, review, final E2E,
  commit, and push.
- Soft target 55 additions; hard gate exactly one file and at most 75 additions.
- No production code/test module, dependency, migration, database deployment, service, scheduler, launchd, Telegram,
  retry, raw payload/audio/text logging, or new E2E file.
- Use the real key only from `/Users/anicca/.openclaw/.env`; never print it. Do not commit or push.

## Task 1: Add the genuine Live proof

- [ ] **Step 1 — write the smallest RED contract**

Add an empty `providerLiveMessages` collection and final assertions requiring one Live message, one matching Live row,
one matching span, and the exact success line `rows=3 spans=3 live=1`. Keep the existing real provider and disposable
database assertions unchanged.

- [ ] **Step 2 — run RED against the real disposable boundary**

Run the script with `GEMINI_API_KEY` injected from `/Users/anicca/.openclaw/.env` via `env -i`. Expected: Docker,
PostgREST, and the existing two genuine `generateContent` calls succeed; the new assertion fails only because Live
observations are zero. Secrets and private content must not appear.

- [ ] **Step 3 — add the minimum real WebSocket path**

Inside the existing Node heredoc:

1. require existing `ws`, `crypto`, `geminiLiveWsUrl`, `buildGeminiSetup`, `buildGeminiTurn`, `LIVE_MODEL`, and
   `captureGeminiLiveUsageObservation`;
2. open one WebSocket, send one minimal AUDIO/Charon setup, wait for `setupComplete`, then send one text turn containing
   the existing private sentinel;
3. resolve on the first later parsed message with top-level `usageMetadata`; use fixed timeout/error/early-close reasons,
   one 30-second timer, no retry, and no raw logging; close the socket after capture;
4. create one random nonzero 32-hex session and call the capture once with the unchanged message, exact CFO context,
   sequence zero, and existing local PostgREST store options;
5. project the Live message into the expected row and prove exact provider counts, null provider/response IDs,
   `live-session:<id>`, distinct trace ID, one span, and content privacy. Keep provider payloads in memory only.

- [ ] **Step 4 — run GREEN and scope gates**

Run the real script again with the same secret-safe `env -i` injection, then `bash -n`, `git diff --check`, and the exact
one-file/75-addition gate. Expected success line: `cfo-provider-usage-real-e2e: PASS rows=3 spans=3 live=1`.

## Plan self-review

- Truth: the provider message, stored row, and span are compared in one real execution; no mock token count exists.
- Privacy: raw Live messages remain in memory and every failure reason is fixed before output.
- Reliability: one bounded WebSocket attempt cannot hang and cleanup remains under the existing trap.
- YAGNI: one existing E2E file, no production change, no abstraction, no deployment.
- Placeholders: none; provider boundary, timeout, row/span assertions, output, and scope gate are fixed.
