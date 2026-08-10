# CFO-2a2.4d1 Gemini Live Bridge Review-Fix Plan

**Status:** READY — revised by Ponytail; fresh Sol review required before Luna fixes.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development task by task.

**Goal:** Close four observed truth/reliability defects and one missing reconnect proof in the existing Live usage wiring,
without adding a service, module, dependency, migration, retry, or reporting path.

**Architecture:** Keep `attachGeminiUsageTracking` and the current `server.js` wiring. Add only a closed guard and safe
thenable containment to the seam; propagate the already-authenticated test-call UID; snapshot duration at socket close.
Replace the current three added tests with small named contracts rather than stacking more test code.

## Scope and size

- Luna owns exactly `apps/life-call/lib/call-bridge.cjs`, `apps/life-call/lib/call-bridge.test.js`, and
  `apps/life-call/server.js`. Sol owns docs, review, verification, commit, and push.
- Final diff versus `7ee07646b`: helper <=23 additions, tests <=57, server <=20; exactly three files and <=100 additions.
- Preserve audio, reconnect, barge-in, transcript, recording, Telnyx cost, scheduler, and provider behavior.
- No real provider call, database/deployment, aggregation, scheduler, launchd, Telegram, retry, or raw provider logging.
- Run from `apps/life-call`; do not edit docs, commit, or push.

## Task 1: Close the reviewed gaps

- [ ] **Step 1 — replace/extend tests into independent contracts**

Keep ordered once-only capture, zero/incomplete, failure continuation, synchronous end, and fallback-matrix coverage.
Use compact helpers, then add five separately named contracts:

1. `server propagates authenticated test-call owner` reads `server.js` and narrowly matches
   `buildStreamUrl({ ...ev, wakeUid: body.uid }, urgency, lang, u.name)`;
2. `server fallback uses the close-time duration snapshot` locates only the production seam's `onFallback` prefix up to
   `recordCost(`, proves it contains `geminiDurationSeconds`, and proves that slice contains no `Date.now(`;
3. `closed socket ignores later usage` closes, emits a usage message, settles, and proves `seen/stored/failed` remains
   `0/0/0` with zero capture calls;
4. `rejecting fallback thenable is consumed` returns a custom thenable that marks itself consumed and rejects; after
   close and one event-loop turn it must be consumed with no log or escaped rejection;
5. `reconnect socket is independent while old capture is pending` opens two seams, leaves old capture pending, closes
   old, emits on new, and proves new capture starts immediately at sequence zero with a distinct session.

Trap `console.log`, `console.error`, and `console.warn` around content sentinels. Prove real serialization by emitting two
usage messages, advancing one microtask, and asserting only the first capture started before resolving it.

- [ ] **Step 2 — run honest RED**

```bash
node --test lib/call-bridge.test.js
```

Run these revised tests against a temporary copy of committed `8e79637c6`, not by reverting the shared worktree.
Copy only the revised test into that temporary tree and reuse the installed `node_modules`. Expected on that baseline:
the UID contract fails because `wakeUid` is absent; duration fails because fallback reads
`Date.now`; post-close fails because the handler still accepts messages; rejecting-thenable fails because the return is
ignored. The reconnect-isolation contract passes because per-socket state is already separate. Historical behavior stays
green. Record the exact totals; do not call a different failure RED.

- [ ] **Step 3 — make the minimum production fixes**

In `attachGeminiUsageTracking`, start the message handler with `if (closed) return`. Route fallback through one local
function that calls `onFallback(result)` inside `try`, assimilates its return with `Promise.resolve(...).catch(() => {})`,
and also contains synchronous throws. Keep ordered `tail`, exact frozen settlement, once-only close, and no logging.

In `/test-call`, pass `{ ...ev, wakeUid: body.uid }` to the existing `buildStreamUrl`. In each `openGeminiLive`, add
`geminiDurationSeconds = null`; `onEnd` snapshots `Math.max(0, (Date.now() - geminiStartedAtMs) / 1000)` once before the
existing synchronous `onGeminiEnd("closed")`; `onFallback` uses only that snapshot, defaulting to zero if absent.

- [ ] **Step 4 — run GREEN and gates**

```bash
node --test lib/call-bridge.test.js
npm run test:cfo
npm test
node --check lib/call-bridge.cjs
node --check server.js
git diff 7ee07646b --check -- lib/call-bridge.cjs lib/call-bridge.test.js server.js
git diff 7ee07646b --numstat -- lib/call-bridge.cjs lib/call-bridge.test.js server.js \
  | awk '{ added += $1; files += 1 } END { print "files=" files, "added=" added; exit !(files == 3 && added <= 100) }'
```

Return RED/GREEN totals and final per-file additions. No real external call, commit, or push.

## Plan self-review

- Truth: authenticated owner and close-time duration reach the stored/fallback facts without DB-latency inflation.
- Reliability: close remains synchronous; late messages and rejected fallback thenables cannot escape.
- Concurrency: the already-correct per-socket queue receives a real simultaneous proof, not a fabricated RED.
- YAGNI: four minimal code edits, five named regressions, three existing files, <=100 additions.
