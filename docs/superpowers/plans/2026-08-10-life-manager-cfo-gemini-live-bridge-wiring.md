# CFO-2a2.4d1 Gemini Live Bridge Wiring Implementation Plan

**Status:** READY — reviewed repair plan returned `ship`; ready for Luna implementation.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development task by task.

**Goal:** Feed each provider-reported Live usage message once, in order, into the verified capture path while retaining
the duration estimate only as an honest fallback.

**Architecture:** Add one injected per-socket recorder closure to `call-bridge.cjs`, test its observation and close
lifecycle there, and wire it into the existing `server.js` Gemini socket. Reuse the 4c3 capture function, current
per-socket close path, Node crypto, Supabase env, and duration ledger. Add no module, dependency, migration, service,
scheduler, or reporting path.

**Tech Stack:** CommonJS, existing `ws`, Node crypto/promises/test.

## Global constraints

- Luna owns exactly `apps/life-call/lib/call-bridge.cjs`, `apps/life-call/lib/call-bridge.test.js`, and
  `apps/life-call/server.js`; Sol owns docs/review/verification/commit/push.
- Soft targets: bridge helper 25 additions, tests 40, server wiring 25; exactly 3 files / at most 90 additions total.
- Preserve audio routing, reconnect, barge-in, transcripts, call recording, Telnyx cost, and all existing tests.
- No real provider call, migration/database deployment, aggregation/rollup, scheduler, launchd, Telegram, retry, raw
  provider logging, dependency, or new file.
- Run every command from `apps/life-call`. Do not commit or push.

## Task 1: Queue provider usage and wire the socket

- [ ] **Step 1 — write the smallest revised RED tests**

Export the production seam `attachGeminiUsageTracking` from `call-bridge.cjs`. Add three behavioral tests and one
compact server source-contract test:

1. non-usage input is ignored; two usage messages are captured once in arrival order with `usage_sequence` 0 and 1,
   the exact fixed base context/options, and `settle()` returns the exact frozen
   `{ seen: 2, stored: 2, failed: 0, complete: true }`;
2. a first capture rejection is swallowed and counted, the second observation still stores, no retry/log occurs, and
   settle returns `{ seen: 2, stored: 1, failed: 1, complete: false }`; zero observed also settles incomplete;
3. drive `attachGeminiUsageTracking` with fake Gemini sockets and deliberately deferred capture. The same production seam
   must parse socket messages into observation, invoke `onEnd` synchronously on close, and decide fallback only after
   settlement. Prove `0/0/0 -> fallback`, `2/2/0 -> no fallback`, and `2/1/1 -> fallback`, exact CFO/store context, and
   that a reconnect socket with a distinct session starts again at sequence zero without sharing settlement state.
   Start the reconnect socket while the old socket's first capture remains pending. Prove the new capture starts at
   sequence zero without waiting, a post-close old message is ignored, and an async rejecting `onFallback` creates no
   `unhandledRejection`. Trap `console.log`, `console.error`, and `console.warn` around content sentinels.

Prove actual serialization before resolving the first capture:

```js
emitUsage(socket, first); emitUsage(socket, second);
await Promise.resolve();
assert.equal(pending.length, 1);
pending[0].resolve();
while (pending.length < 2) await Promise.resolve();
assert.equal(pending[1].context.usage_sequence, 1);
```

Use two simultaneous production seams for reconnect isolation:

```js
oldSocket.emit("close");
emitUsage(oldSocket, usageMessage(99));
emitUsage(newSocket, usageMessage(1));
await Promise.resolve();
assert.equal(oldPending.length, 1);
assert.equal(newPending.length, 1);
assert.equal(newPending[0].context.usage_sequence, 0);
```

Read `server.js` in the same test file and pin both server-only fixes so direct seam tests cannot hide them:

```js
const fs = require("node:fs"), path = require("node:path");
const serverSource = fs.readFileSync(path.join(__dirname, "../server.js"), "utf8");
assert.match(serverSource, /buildStreamUrl\(\{\s*\.\.\.ev,\s*wakeUid:\s*body\.uid\s*\},\s*urgency,\s*lang,\s*u\.name\)/);
assert.match(serverSource, /onEnd:\s*\(\)\s*=>\s*\{[\s\S]*?geminiDurationSeconds\s*=\s*Math\.max\([\s\S]*?onGeminiEnd\("closed"\);?\s*\}/);
assert.match(serverSource, /onFallback:\s*\(\)\s*=>\s*\{[^}]*const quantity\s*=\s*geminiDurationSeconds\s*===\s*null\s*\?\s*0\s*:\s*geminiDurationSeconds/s);
const fallbackSource = serverSource.slice(serverSource.indexOf("onFallback:", serverSource.indexOf("attachGeminiUsageTracking")), serverSource.indexOf("});", serverSource.indexOf("onFallback:", serverSource.indexOf("attachGeminiUsageTracking"))));
assert.doesNotMatch(fallbackSource, /Date\.now\(/);
```

- [ ] **Step 2 — run revised RED**

```bash
node --test lib/call-bridge.test.js
```

Expected: at least one revised contract fails against the current implementation for the observed owner/timing/async
containment/post-close/reconnect defect. Record the exact failure before production edits.

- [ ] **Step 3 — add the minimum queue and wiring**

`attachGeminiUsageTracking({ socket, capture, context, options, onEnd, onFallback })` creates one private recorder for
that socket, keeps `seen/stored/failed/nextSequence/tail`, and attaches only `message` and `close`. A parsed message
without `usageMetadata` is ignored; otherwise it reserves the next sequence immediately, appends one capture task to
`tail`, and catches that task into `failed`. Close invokes `onEnd` synchronously, then settles the queue asynchronously
and invokes `onFallback` unless the exact frozen result has `complete === true`; it contains a settlement rejection and
still invokes fallback. It never retries or logs, and may return the recorder's settlement promise only for tests.

The message handler starts with `if (closed) return`. Contain both synchronous throws and rejected fallback thenables:

```js
const fallback = result => {
  if (!onFallback) return;
  try { Promise.resolve(onFallback(result)).catch(() => {}); } catch {}
};
```

In `server.js`, import `LIVE_MODEL`, `captureGeminiLiveUsageObservation`, and the seam. Inside each `openGeminiLive`
invocation, attach it once using a random session ID and the existing owner/unit/model/Supabase context. Keep the existing
audio message handler unchanged. The seam's close callback runs existing `onGeminiEnd("closed")` synchronously, while
the old exact duration `recordCost` runs later only as `onFallback`. Remove the replaced close listener. A recorder or
settlement failure must never delay or stop reconnect/carrier teardown.

Preserve the authenticated owner in `/test-call`:

```js
const streamUrl = buildStreamUrl({ ...ev, wakeUid: body.uid }, urgency, lang, u.name);
```

Snapshot duration synchronously at close and never include database settlement latency:

```js
let geminiDurationSeconds = null;
onEnd: () => {
  if (geminiDurationSeconds === null) {
    geminiDurationSeconds = Math.max(0, (Date.now() - geminiStartedAtMs) / 1000);
  }
  onGeminiEnd("closed");
},
onFallback: () => {
  if (geminiCostRecorded) return;
  geminiCostRecorded = true;
  const quantity = geminiDurationSeconds === null ? 0 : geminiDurationSeconds;
  recordCost({ uid: wakeUid || null, kind: "gemini_live", quantity, unit: "seconds",
    estUsd: quantity / 60 * 0.023, meta: { reconnect: geminiReconnects } });
},
```

- [ ] **Step 4 — run GREEN and scope gates**

```bash
node --test lib/call-bridge.test.js
npm run test:cfo
npm test
node --check lib/call-bridge.cjs
node --check server.js
git diff 7ee07646b --check -- lib/call-bridge.cjs lib/call-bridge.test.js server.js
git diff 7ee07646b --numstat -- lib/call-bridge.cjs lib/call-bridge.test.js server.js \
  | awk '{ added += $1; files += 1 } END { print "files=" files, "added=" added; exit !(files == 3 && added <= 90) }'
```

Expected: all commands exit `0`; exactly three files and at most 90 additions. Return exact RED/GREEN totals and line
counts to Sol. Do not commit or push.

## Plan self-review

- Truth: all-success observations suppress the duration proxy; partial failure visibly leaves the stored subset plus
  fallback, with aggregation policy explicitly deferred rather than falsely claimed complete.
- Ordering: sequence is reserved at arrival and work is serialized; one failure cannot poison later tasks.
- Reliability: capture failure cannot block audio/reconnect/close; teardown is synchronous and fallback is asynchronous.
- Privacy: the helper neither logs nor projects provider payloads.
- YAGNI: three existing files, one private queue, no deployment or new service.
- Placeholders: none. API, state, fallback rule, wiring, tests, commands, and size limit are fixed.
