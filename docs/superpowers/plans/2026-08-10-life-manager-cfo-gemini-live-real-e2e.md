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

Add empty `providerLiveMessages` and `postTurnLiveMessages` collections and final assertions requiring one captured
Live usage message, one matching Live row, exactly three rows, and exactly three matching spans. Require the exact
success line `rows=3 spans=3 live=1`. Keep the existing real provider and disposable database assertions unchanged.
The first new assertion executed must be `providerLiveMessages.length === 1`; row/span/output assertions come after it.

- [ ] **Step 2 — run RED against the real disposable boundary**

Run from `apps/life-call` with the already-proven isolated environment:

```bash
env -i PATH="$PATH" HOME="$HOME" TMPDIR="${TMPDIR:-/tmp}" \
  GEMINI_API_KEY="$(node --env-file=/Users/anicca/.openclaw/.env -p 'process.env.GEMINI_API_KEY')" \
  test/postgres/cfo-provider-usage-real-e2e.sh
```

Expected: Docker, PostgREST, and the existing two genuine `generateContent` calls succeed; the first new assertion fails
as exact `0 !== 1` because Live observations are zero. Secrets and private content must not appear.

- [ ] **Step 3 — add the minimum real WebSocket path**

Inside the existing Node heredoc:

1. require existing `ws`, `crypto`, `geminiLiveWsUrl`, `buildGeminiSetup`, `buildGeminiTurn`, `LIVE_MODEL`, and
   `captureGeminiLiveUsageObservation`;
2. build the setup exactly once, open one WebSocket, send that minimal AUDIO/Charon setup, wait for `setupComplete`,
   then send one text turn containing the existing private sentinel;
3. maintain `turnSent` and one idempotent `settled` gate. One `settle(error, value)` clears the 30-second timer, removes
   message/error/close listeners, and resolves or rejects once. Resolve only on the first parsed message after
   `turnSent` with top-level `usageMetadata`; error, timeout, and close-before-success reject with exact fixed reasons.
   Set `settled` before intentionally closing after capture so that close is never relabeled early-close. Use no retry
   and no raw logging; retain all post-turn parsed messages in memory until settlement;
4. create one random nonzero 32-hex session and call the capture once with the unchanged message and exact context:
   owner `cfo-e2e-owner`, unit `life_manager_saas`, `request_model: setup.setup.model`, session ID, sequence zero, and
   existing local PostgREST store options;
5. project the Live message into the expected row and prove exact provider counts, null provider/response IDs,
   `live-session:<id>`, and a distinct trace ID. In `writeExport`, retain each plain exported span object carrying a
   nonzero 32-hex `traceId`; require exactly three objects and require their sorted trace-ID multiset to equal the three
   distinct sorted row trace IDs. Reuse `collectStrings` over all post-turn messages to reject every observed
   text/transcript/audio string of at least 12 characters from exporter output; also reject the sentinel, API key,
   `gen_ai.input.messages`, and `gen_ai.output.messages`. Keep provider payloads in memory only.

- [ ] **Step 4 — run GREEN and scope gates**

Run the real script again with the exact Step 2 `env -i` command, then `bash -n`, `git diff --check`, and the exact
one-file/75-addition gate. Expected success line: `cfo-provider-usage-real-e2e: PASS rows=3 spans=3 live=1`.

## Plan self-review

- Truth: the provider message, stored row, and span are compared in one real execution; no mock token count exists.
- Privacy: raw Live messages remain in memory and every failure reason is fixed before output.
- Reliability: one idempotent settlement gate owns timer/listener cleanup, so close/error/timeout races cannot hang or
  overwrite a successful capture; process cleanup remains under the existing trap.
- YAGNI: one existing E2E file, no production change, no abstraction, no deployment.
- Placeholders: none; provider boundary, timeout, row/span assertions, output, and scope gate are fixed.
