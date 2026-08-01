# Wake Loop Isolation (daily organ #1c) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the wake call its own 60-second tick with its own short per-user deadline, so a slow care/diet/mental/late organ can never delay or abandon a wake call.

**Architecture:** `wakeUserOnce` splits into two halves. `wakeCallOnce` fetches the user's upcoming events, publishes them to an in-process cache, and runs only the dial block. `organsUserOnce` runs late/mental/care/diet/precepts/relations and READS that cache instead of fetching, so Composio call volume is unchanged. `wakeUserOnce` remains as the composition of both (the Inngest per-user path and the existing 1a/1b tests keep calling it unchanged). A new `startWakeLoop()` drives `wakeCallOnce` every 60s with a 20s per-user deadline; the existing `startScheduler()` keeps its dynamic interval and 90s deadline but now drives `organsUserOnce`. Every organ call is wrapped in a timing helper that logs elapsed ms, which is the evidence the spec's done receipt requires.

**Tech Stack:** Node.js CommonJS, `node --test`, Supabase PostgREST, Composio calendar transport.

**Spec:** `docs/superpowers/specs/2026-08-01-lm-daily-organ-design.md` §3 row 1c and §3.1 (method A).

**Working directory:** `/Users/operator/anicca/.worktrees/spec-two-loops/apps/life-manager`

---

## Environment note — read before Task 1

`node_modules` is deleted at random by `~/scripts/disk-sentinel.sh` whenever free disk drops under 10 GB (it treats `node_modules` as rebuildable). If any test run dies with `Cannot find module 'canonicalize'`, that is the cause — it is NOT a code defect. Always run tests as one chained command:

```bash
cd /Users/operator/anicca/.worktrees/spec-two-loops/apps/life-manager \
  && npm ci --ignore-scripts --no-audit --no-fund >/dev/null 2>&1 \
  && node --test <files>
```

Every "Run:" step below assumes that chain. Do not `npm install` in a separate step and then run tests in another — the install can be wiped in between.

---

## File Structure

| File | Responsibility |
|---|---|
| `lib/event-cache.js` (create) | In-process per-uid calendar cache. Wake tick writes, organ tick reads. No I/O. |
| `lib/event-cache.test.js` (create) | Unit tests for the cache. |
| `lib/organ-run.js` (create) | `runOrgan()` — times one organ, logs elapsed ms, swallows its throw. |
| `lib/organ-run.test.js` (create) | Unit tests for the timing wrapper. |
| `scheduler.js` (modify) | Split `wakeUserOnce` into `wakeCallOnce` + `organsUserOnce`; add `wakeTick`/`startWakeLoop`; route organs through `runOrgan`. |
| `lib/maybe-start-loops.js` (modify) | Start the new wake loop alongside the existing five. |
| `lib/maybe-start-loops.test.js` (modify) | Assert the wake loop is started. |
| `test/wake-loop-isolation.test.js` (create) | The done receipt: a slow organ cannot delay the dial; Composio fetches are not doubled. |

---

### Task 1: Event cache

**Files:**
- Create: `lib/event-cache.js`
- Test: `lib/event-cache.test.js`

- [ ] **Step 1: Write the failing test**

Create `lib/event-cache.test.js`:

```js
"use strict";
// spec 2026-08-01-lm-daily-organ-design.md §3.1 (method A).
//
// Splitting the wake call onto its own tick would double Composio usage if both loops fetched the
// calendar: lib/calendar-cache.js keys on a MINUTE bucket derived from now, so two loops running at
// different phases never share an entry. Instead the wake tick OWNS the fetch and publishes here;
// the organ tick reads. This cache is deliberately in-process and tiny — it is a hand-off between
// two timers in one process, not a durable store.
//
// Run: node --test lib/event-cache.test.js
const { test } = require("node:test");
const assert = require("node:assert");

const { putEvents, getEvents, clearEvents, EVENT_CACHE_TTL_MS } = require("./event-cache.js");

test("what the wake tick publishes is what the organ tick reads", () => {
  clearEvents();
  const events = [{ id: "e1" }];
  putEvents("u1", events, 1000);
  assert.deepEqual(getEvents("u1", 1000), events);
});

test("a stale entry is not served — a caller must fetch rather than act on old calendar data", () => {
  clearEvents();
  putEvents("u1", [{ id: "e1" }], 1000);
  assert.equal(getEvents("u1", 1000 + EVENT_CACHE_TTL_MS + 1), null);
});

test("one user's events are never served to another", () => {
  clearEvents();
  putEvents("u1", [{ id: "e1" }], 1000);
  assert.equal(getEvents("u2", 1000), null);
});

test("a miss is null, never an empty array — 'no events' and 'never fetched' must not look alike", () => {
  clearEvents();
  assert.equal(getEvents("nobody", 1000), null);
  putEvents("u1", [], 1000);
  assert.deepEqual(getEvents("u1", 1000), []);
});

test("publishing again replaces the entry and restarts its freshness", () => {
  clearEvents();
  putEvents("u1", [{ id: "old" }], 1000);
  putEvents("u1", [{ id: "new" }], 1000 + EVENT_CACHE_TTL_MS);
  assert.deepEqual(getEvents("u1", 1000 + EVENT_CACHE_TTL_MS), [{ id: "new" }]);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd /Users/operator/anicca/.worktrees/spec-two-loops/apps/life-manager \
  && npm ci --ignore-scripts --no-audit --no-fund >/dev/null 2>&1 \
  && node --test lib/event-cache.test.js
```
Expected: FAIL — `Cannot find module './event-cache.js'`.

- [ ] **Step 3: Write minimal implementation**

Create `lib/event-cache.js`:

```js
"use strict";
// lib/event-cache.js — spec 2026-08-01-lm-daily-organ-design.md §3.1 (method A).
//
// A hand-off between two timers in ONE process: the wake tick fetches the calendar and publishes
// here, the organ tick reads. It exists for one reason — lib/calendar-cache.js keys on a minute
// bucket derived from `now`, so two loops on different phases would each pay a real Composio call.
// Owning the fetch in one place keeps call volume exactly where it was before the split.
//
// Deliberately NOT durable: a restart simply means the first organ tick fetches once. Anything that
// must survive a restart belongs in Supabase, not here.

// The organ tick runs at most every 5 minutes, and the wake tick republishes every 60s, so entries
// are normally under a minute old. The TTL is the honesty boundary: past it, a reader must fetch
// rather than act on a calendar that may have changed.
const EVENT_CACHE_TTL_MS = Number(process.env.LM_EVENT_CACHE_TTL_MS) || 5 * 60_000;

const cache = new Map(); // uid -> { events, atMs }

function putEvents(uid, events, nowMs) {
  if (!uid) return;
  cache.set(String(uid), { events, atMs: nowMs == null ? Date.now() : nowMs });
}

// null means "you must fetch" — never confuse it with [] ("fetched, the user has no events").
function getEvents(uid, nowMs) {
  const entry = cache.get(String(uid || ""));
  if (!entry) return null;
  const now = nowMs == null ? Date.now() : nowMs;
  if (now - entry.atMs > EVENT_CACHE_TTL_MS) return null;
  return entry.events;
}

function clearEvents() {
  cache.clear();
}

module.exports = { putEvents, getEvents, clearEvents, EVENT_CACHE_TTL_MS };
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd /Users/operator/anicca/.worktrees/spec-two-loops/apps/life-manager \
  && npm ci --ignore-scripts --no-audit --no-fund >/dev/null 2>&1 \
  && node --test lib/event-cache.test.js
```
Expected: `pass 5`, `fail 0`.

- [ ] **Step 5: Commit**

```bash
cd /Users/operator/anicca/.worktrees/spec-two-loops
git add apps/life-manager/lib/event-cache.js apps/life-manager/lib/event-cache.test.js
git commit -m "feat(daily): hand the calendar from the wake tick to the organ tick"
```

---

### Task 2: Organ timing wrapper

**Files:**
- Create: `lib/organ-run.js`
- Test: `lib/organ-run.test.js`

- [ ] **Step 1: Write the failing test**

Create `lib/organ-run.test.js`:

```js
"use strict";
// spec 2026-08-01-lm-daily-organ-design.md §3 row 1c: the done receipt is "organ 毎の経過ms がログに
// 出る". Today every organ logs only its outcome, so when `tenant timeout 90000ms` fires there is no
// way to tell which organ ate the budget. This wrapper is that measurement.
//
// Run: node --test lib/organ-run.test.js
const { test } = require("node:test");
const assert = require("node:assert");

const { runOrgan } = require("./organ-run.js");

test("runOrgan returns the organ's value and logs how long it took", async () => {
  const lines = [];
  let clock = 1000;
  const result = await runOrgan({
    label: "care", uid: "lm_abcdefghijklmnop",
    run: async () => { clock += 250; return { status: "scanned" }; },
    log: (line) => lines.push(line),
    now: () => clock,
  });
  assert.deepEqual(result, { status: "scanned" });
  assert.equal(lines.length, 1);
  assert.match(lines[0], /\[care\]/);
  assert.match(lines[0], /ms=250/);
  assert.match(lines[0], /uid=lm_abcdefgh/, "the uid is truncated like every other organ log line");
});

test("a throwing organ is logged with its error and does NOT propagate", async () => {
  const lines = [];
  const result = await runOrgan({
    label: "diet", uid: "u1",
    run: async () => { throw new Error("places api down"); },
    log: (line) => lines.push(line),
    now: () => 0,
  });
  assert.equal(result, null, "the caller continues with no value rather than dying");
  assert.match(lines[0], /err places api down/);
  assert.match(lines[0], /ms=/, "a failure is still timed — a slow failure is the interesting case");
});

test("runOrgan times the failure path too, so a slow throw is visible", async () => {
  const lines = [];
  let clock = 0;
  await runOrgan({
    label: "mental", uid: "u1",
    run: async () => { clock += 4000; throw new Error("boom"); },
    log: (line) => lines.push(line),
    now: () => clock,
  });
  assert.match(lines[0], /ms=4000/);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd /Users/operator/anicca/.worktrees/spec-two-loops/apps/life-manager \
  && npm ci --ignore-scripts --no-audit --no-fund >/dev/null 2>&1 \
  && node --test lib/organ-run.test.js
```
Expected: FAIL — `Cannot find module './organ-run.js'`.

- [ ] **Step 3: Write minimal implementation**

Create `lib/organ-run.js`:

```js
"use strict";
// lib/organ-run.js — spec 2026-08-01-lm-daily-organ-design.md §3 row 1c.
//
// Every organ in the tick was already try/catch-wrapped, so a THROW could not kill its siblings.
// Nothing measured how LONG one took, which is the failure that actually happened: organs share one
// per-user budget, and `tenant timeout 90000ms` named the user but never the organ that ate it.
// runOrgan is that missing measurement, and it keeps the existing swallow-and-continue contract.

async function runOrgan({ label, uid, run, log, now }) {
  const clock = now || Date.now;
  const started = clock();
  const who = `uid=${String(uid || "?").slice(0, 12)}`;
  try {
    const value = await run();
    log(`[${label}] ${who} ms=${clock() - started}`);
    return value;
  } catch (e) {
    log(`[${label}] ${who} ms=${clock() - started} err ${e && e.message}`);
    return null;
  }
}

module.exports = { runOrgan };
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd /Users/operator/anicca/.worktrees/spec-two-loops/apps/life-manager \
  && npm ci --ignore-scripts --no-audit --no-fund >/dev/null 2>&1 \
  && node --test lib/organ-run.test.js
```
Expected: `pass 3`, `fail 0`.

- [ ] **Step 5: Commit**

```bash
cd /Users/operator/anicca/.worktrees/spec-two-loops
git add apps/life-manager/lib/organ-run.js apps/life-manager/lib/organ-run.test.js
git commit -m "feat(daily): measure how long each organ takes, not just whether it threw"
```

---

### Task 3: Split `wakeUserOnce` into `wakeCallOnce` + `organsUserOnce`

`wakeUserOnce` currently runs, in order: `recordDailyComposioPoll` → `fetchUpcomingEvents` → late → mental → the wake-call block → care → diet-nudge → diet → precepts-mirror → precepts → relations.

After this task:
- `wakeCallOnce(u, nowMs, deps)` = poll + fetch + **publish to the event cache** + the wake-call block.
- `organsUserOnce(u, nowMs, deps)` = late + mental + care + diet-nudge + diet + precepts-mirror + precepts + relations, reading events from the cache and fetching only on a miss.
- `wakeUserOnce(u, nowMs, deps)` = `await wakeCallOnce(...)` then `await organsUserOnce(...)`.

Keeping `wakeUserOnce` as the composition is what preserves the Inngest per-user path (`inngest/functions.js:157-164` passes it to `makeWakeUserHandler`) and every existing test (`test/wake-catchup.test.js`, `test/wake-miss-record.test.js`, `test/daily-journey-contract.test.js`).

**Files:**
- Modify: `scheduler.js`
- Test: `test/wake-loop-isolation.test.js` (created in Task 5; this task is covered by the existing suites)

- [ ] **Step 1: Read the current function before changing it**

Run:
```bash
cd /Users/operator/anicca/.worktrees/spec-two-loops/apps/life-manager && sed -n '343,590p' scheduler.js
```
Expected: the whole of `wakeUserOnce`, ending just before `forEachUserSafe`.

- [ ] **Step 2: Capture the green baseline you must not break**

Run:
```bash
cd /Users/operator/anicca/.worktrees/spec-two-loops/apps/life-manager \
  && npm ci --ignore-scripts --no-audit --no-fund >/dev/null 2>&1 \
  && node --test test/wake-catchup.test.js test/wake-miss-record.test.js lib/wake-miss.test.js lib/slash-command.test.js
```
Expected: `pass 55`, `fail 0`. Write the number down; it must not drop.

- [ ] **Step 3: Add the imports**

In `scheduler.js`, next to the other `lib/` requires (near `require("./lib/wake-miss.js")`), add:

```js
const { putEvents, getEvents } = require("./lib/event-cache.js");
const { runOrgan } = require("./lib/organ-run.js");
```

- [ ] **Step 4: Rename `wakeUserOnce` to `wakeCallOnce` and cut it down to the dial**

Change the signature line from `async function wakeUserOnce(u, nowMs, deps = {}) {` to:

```js
// wakeCallOnce — the DEADLINE-CRITICAL half. It owns the calendar fetch (and publishes it for the
// organ tick), then does nothing but decide and place the call. Everything that can be late lives in
// organsUserOnce, on its own timer, so no organ can spend this user's budget before the dial
// (spec §3.1: late+mental sat in front of the dial inside one shared 90s budget).
async function wakeCallOnce(u, nowMs, deps = {}) {
```

Immediately after `const futureEvents = (events || []).filter((e) => Number(e.startMs) >= now);`, publish the fetch:

```js
  // The organ tick reads this instead of fetching. Publishing the RAW events (not futureEvents) is
  // deliberate: the MENTAL organ needs the lookback slice that futureEvents throws away.
  (deps.putEvents || putEvents)(u.uid, events, now);
```

Then DELETE from `wakeCallOnce` every block below the wake-call loop and the late/mental blocks above it — specifically: the `late` try/catch, the `mental` try/catch, and the `care`, `diet-nudge`, `diet`, `precepts-mirror`, `precepts`, `relations` try/catch blocks. Move them verbatim into `organsUserOnce` in Step 5. `wakeCallOnce` ends after the `if (u.call_enabled !== false) { ... }` wake-call block closes.

- [ ] **Step 5: Add `organsUserOnce` directly below `wakeCallOnce`**

```js
// organsUserOnce — everything that is NOT the wake call. Runs on its own timer with the original 90s
// per-user budget, so a slow care/diet/mental/late organ delays only its siblings. Each organ is
// wrapped in runOrgan, which both preserves the old swallow-and-continue contract and records the
// elapsed ms that used to be missing when `tenant timeout` fired (spec §3 row 1c done receipt).
async function organsUserOnce(u, nowMs, deps = {}) {
  if (u && u.daily_automation_enabled === false) return;
  const now = nowMs !== undefined ? nowMs : Date.now();
  const log = deps.log || console.log;

  // Read what the wake tick already fetched. A miss (first tick after a restart, or a wake tick that
  // failed) falls back to a real fetch: the organs still run, and the cost is bounded to that case.
  let events = (deps.getEvents || getEvents)(u.uid, now);
  if (events == null) {
    try {
      events = await (deps.fetchUpcomingEvents || fetchUpcomingEvents)(u.uid, {
        nowMs: now, horizonH: 6, lookbackMs: MENTAL_LOOKBACK_MS,
        apiKey: deps.apiKey || process.env.COMPOSIO_API_KEY,
        calendar: deps.calendar, gmailAccountId: u.gmail_account_id,
      });
      (deps.putEvents || putEvents)(u.uid, events, now);
    } catch {
      return;
    }
  }
  const futureEvents = (events || []).filter((e) => Number(e.startMs) >= now);

  if (u.notifications_enabled !== false) {
    const late = await runOrgan({
      label: "late", uid: u.uid, log,
      run: () => (deps.lateNotice || lateNoticeUserOnce)(u, now, { events: futureEvents }),
    });
    if (late && late.telegramMessageId !== undefined) {
      log(`[late] uid=${String(u.uid).slice(0, 12)} decision=${late.decision} sent=${!!late.sent} tg_message_id=${late.telegramMessageId}`);
    }
  }

  const mental = await runOrgan({
    label: "mental", uid: u.uid, log,
    run: () => (deps.mental || mentalUserOnce)(u, now, mentalDeps(u, events, deps)),
  });
  if (mental && mental.delivered) {
    log(`[mental] uid=${String(u.uid).slice(0, 12)} trigger=${mental.trigger} tg_message_id=${mental.telegramMessageId}`);
  }

  // Paste the care / diet-nudge / diet / precepts-mirror / precepts / relations blocks here, each
  // converted from `try { const x = await (deps.foo || foo)(...); ...log... } catch (e) { console.error(...) }`
  // into:
  //   const x = await runOrgan({ label: "<organ>", uid: u.uid, log, run: () => (deps.foo || foo)(...) });
  //   ...the same log line the block already had...
  // runOrgan already catches and logs the throw, so the old catch block is deleted, not kept.
}

// wakeUserOnce — kept as the composition of both halves. The Inngest per-user path
// (inngest/functions.js makeWakeUserHandler) and the 1a/1b test suites call this name, and a
// per-user Inngest run has no sibling users to protect, so running both halves there is correct.
async function wakeUserOnce(u, nowMs, deps = {}) {
  await wakeCallOnce(u, nowMs, deps);
  await organsUserOnce(u, nowMs, deps);
}
```

- [ ] **Step 6: Export the new functions**

In `module.exports`, next to `wakeUserOnce, travelUserOnce, askUserOnce,` add:

```js
  // the two halves of the old wakeUserOnce — separate timers drive them (spec §3.1 method A)
  wakeCallOnce, organsUserOnce,
```

- [ ] **Step 7: Run the baseline suite — it must still be green**

Run:
```bash
cd /Users/operator/anicca/.worktrees/spec-two-loops/apps/life-manager \
  && npm ci --ignore-scripts --no-audit --no-fund >/dev/null 2>&1 \
  && node --test test/wake-catchup.test.js test/wake-miss-record.test.js lib/wake-miss.test.js lib/slash-command.test.js
```
Expected: `pass 55`, `fail 0` — the same number as Step 2.

If a test fails because an organ's stub is no longer called, that is a real regression in the split: `wakeUserOnce` must still run both halves. Fix the composition, not the test.

- [ ] **Step 8: Commit**

```bash
cd /Users/operator/anicca/.worktrees/spec-two-loops
git add apps/life-manager/scheduler.js
git commit -m "refactor(daily): separate the dial from the organs that can be late"
```

---

### Task 4: Dedicated wake tick with its own deadline

**Files:**
- Modify: `scheduler.js`

- [ ] **Step 1: Add the wake tick above `startScheduler`**

In `scheduler.js`, directly above `function startScheduler() {`:

```js
// The wake call gets its own timer and its own budget. 20 seconds is sized to what wakeCallOnce
// actually does — one calendar fetch, one departure resolve, one dial — where 90s was sized for the
// care organ's browser work. A user who blows 20s here still cannot delay the next user's dial.
const WAKE_USER_TIMEOUT_MS = Number(process.env.LIFE_WAKE_USER_TIMEOUT_MS) || 20000;

async function wakeTick(deps = {}) {
  const listUsers = deps.listUsers || supaUsers;
  const wake = deps.wake || wakeCallOnce;
  const users = await listUsers();
  const now = deps.now !== undefined ? deps.now : Date.now();
  await forEachUserSafe(
    users.filter(u => u.daily_automation_enabled !== false && u.call_enabled !== false),
    "wake", (u) => wake(u, now), WAKE_USER_TIMEOUT_MS,
  );
}

// Fixed 60s, deliberately NOT schedulerPollInterval(): the Composio budget degradation that slows the
// organ tick to 5 minutes must not slow the dial (that defect is spec row #1d, tracked separately).
// The wake tick owns the calendar fetch, so this loop's call volume equals the old combined tick's.
function startWakeLoop() {
  console.log(`[wake] started — dedicated tick every ${TICK_MS / 1000}s, ${WAKE_USER_TIMEOUT_MS / 1000}s per user, wakes at T-${WAKE_LEVELS.map((l) => l.min).join("/")}min`);
  let timer;
  const run = async () => {
    try { await wakeTick(); } catch (e) { console.error("[wake] tick err", e.message); }
    timer = setTimeout(run, TICK_MS);
  };
  run();
  return { close: () => clearTimeout(timer) };
}
```

- [ ] **Step 2: Point the existing tick at the organs**

In `tick()`, change:

```js
  const wake = deps.wake || wakeUserOnce;
```

to:

```js
  // The organ half only. The dial moved to wakeTick above, on its own timer and its own deadline.
  const organs = deps.organs || organsUserOnce;
```

and change the `forEachUserSafe` call's function from `(u) => wake(u, now)` to `(u) => organs(u, now)`.

Update `startScheduler`'s log line from `[scheduler] started — tick every ...` to:

```js
  console.log(`[scheduler] started — organ tick every ${TICK_MS / 1000}s (wake runs on its own loop)`);
```

- [ ] **Step 3: Export the new entry points**

In `module.exports`, change the first line from:

```js
  startScheduler, startTravelLoop, startAskLoop, startOnboardLoop, startDiscoveryLoop,
  tick, travelTick, askTickAll, onboardTick, discoveryTick,
```

to:

```js
  startScheduler, startWakeLoop, startTravelLoop, startAskLoop, startOnboardLoop, startDiscoveryLoop,
  tick, wakeTick, travelTick, askTickAll, onboardTick, discoveryTick,
  // the wake loop's own per-user budget — exported so a revert to the shared 90s is test-caught
  WAKE_USER_TIMEOUT_MS,
```

- [ ] **Step 4: Verify the module still loads and both loops are exported**

Run:
```bash
cd /Users/operator/anicca/.worktrees/spec-two-loops/apps/life-manager \
  && npm ci --ignore-scripts --no-audit --no-fund >/dev/null 2>&1 \
  && node -e 'const s=require("./scheduler.js"); console.log(typeof s.startWakeLoop, typeof s.wakeTick, typeof s.wakeCallOnce, typeof s.organsUserOnce, s.WAKE_USER_TIMEOUT_MS)'
```
Expected: `function function function function 20000`.

- [ ] **Step 5: Commit**

```bash
cd /Users/operator/anicca/.worktrees/spec-two-loops
git add apps/life-manager/scheduler.js
git commit -m "feat(daily): give the wake call its own tick and its own deadline"
```

---

### Task 5: Prove the isolation

**Files:**
- Create: `test/wake-loop-isolation.test.js`

- [ ] **Step 1: Write the failing test**

Create `test/wake-loop-isolation.test.js`:

```js
"use strict";
// spec 2026-08-01-lm-daily-organ-design.md §3 row 1c — the done receipt.
//
// The measured failure (§3.1): late and mental ran BEFORE the dial inside one 90s per-user budget, so
// two slow organs abandoned the user before a call was ever attempted. These tests pin the property
// that fixes it — the dial does not run the organs at all — and pin the constraint that made method A
// worth choosing: the split must not double Composio calls.
//
// Run: node --test test/wake-loop-isolation.test.js
const { test } = require("node:test");
const assert = require("node:assert");

process.env.LM_CALL_SECRET = "unit_secret";
process.env.PUBLIC_WSS = "wss://life-call.invalid";

const {
  wakeCallOnce, organsUserOnce, wakeTick, WAKE_USER_TIMEOUT_MS, forEachUserSafe,
} = require("../scheduler.js");
const { clearEvents, getEvents } = require("../lib/event-cache.js");

const MINUTE = 60_000;
const EVENT_START_ISO = "2026-08-05T14:00:00+09:00";
const EVENT_START_MS = Date.parse(EVENT_START_ISO);
const TRAVEL_MIN = 35; // + resolveDeparture's 5-min buffer → departure = start − 40 min
const DEPARTURE_MS = EVENT_START_MS - 40 * MINUTE;

const USER = {
  uid: "iso-user",
  name: "Iso User",
  phone: "+810000000000",
  home_address: "東京都渋谷区",
  call_language: "ja",
  daily_automation_enabled: true,
  call_enabled: true,
  notifications_enabled: false,
};

const EVENT = {
  id: "iso-event",
  summary: "新宿で打ち合わせ",
  location: "新宿",
  startMs: EVENT_START_MS,
  startIso: EVENT_START_ISO,
  endMs: EVENT_START_MS + 60 * MINUTE,
};

function deps({ slowOrganMs = 0, fetches } = {}) {
  const dialed = [];
  const held = new Set();
  const stall = async () => { if (slowOrganMs) await new Promise((r) => setTimeout(r, slowOrganMs)); return null; };
  return {
    dialed,
    deps: {
      recordDailyPoll: async () => true,
      fetchUpcomingEvents: async () => { if (fetches) fetches.push(1); return [{ ...EVENT }]; },
      directionsMinutes: async () => TRAVEL_MIN,
      mapsKey: "iso-maps-key",
      claimWake: async (_uid, key) => { if (held.has(key)) return false; held.add(key); return true; },
      placeCall: async () => { dialed.push(Date.now()); return { ok: true, ccid: "iso-1" }; },
      releaseWake: async () => {},
      alertLowBalance: async () => {},
      recordWakeMiss: async () => ({ ok: true }),
      wakeWasClaimed: async (_uid, key) => held.has(key),
      // every organ stalls
      lateNotice: stall, mental: stall, care: stall, diet: stall, dietNudge: stall,
      preceptsMirror: stall, precepts: stall, relations: stall,
      log: () => {},
    },
  };
}

test("the dial half does not run a single organ — a stalled organ cannot reach it", async () => {
  clearEvents();
  const h = deps({ slowOrganMs: 5000 });
  const started = Date.now();
  await wakeCallOnce(USER, DEPARTURE_MS - 5 * MINUTE, h.deps);
  const elapsed = Date.now() - started;
  assert.equal(h.dialed.length, 1, "the call is placed");
  assert.ok(elapsed < 1000, `the dial path must not wait on organs (took ${elapsed}ms)`);
});

test("the wake loop's per-user budget is its own, and far below the organ budget", () => {
  assert.equal(WAKE_USER_TIMEOUT_MS, 20000);
  assert.ok(WAKE_USER_TIMEOUT_MS < 90000, "the shared 90s budget was sized for the care organ, not the dial");
});

test("the dial publishes the calendar so the organ tick does not fetch it again", async () => {
  clearEvents();
  const fetches = [];
  const h = deps({ fetches });
  const now = DEPARTURE_MS - 5 * MINUTE;
  await wakeCallOnce(USER, now, h.deps);
  assert.equal(fetches.length, 1, "the wake half fetches once");
  assert.ok(getEvents(USER.uid, now), "and publishes what it fetched");

  await organsUserOnce(USER, now, h.deps);
  assert.equal(fetches.length, 1, "the organ half reuses it — the split must not double Composio calls");
});

test("the organ half still fetches when nothing was published (first tick after a restart)", async () => {
  clearEvents();
  const fetches = [];
  const h = deps({ fetches });
  await organsUserOnce(USER, DEPARTURE_MS - 5 * MINUTE, h.deps);
  assert.equal(fetches.length, 1, "a cache miss falls back to a real fetch rather than skipping the organs");
});

test("one user blowing the wake budget does not stop the next user's dial", async () => {
  const order = [];
  await forEachUserSafe(
    [{ uid: "slow" }, { uid: "fast" }],
    "wake",
    async (u) => {
      if (u.uid === "slow") await new Promise((r) => setTimeout(r, 200));
      order.push(u.uid);
    },
    50, // a 50ms budget stands in for the real 20s one
  );
  assert.deepEqual(order, ["fast"], "the slow user is abandoned; the fast user is still served");
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd /Users/operator/anicca/.worktrees/spec-two-loops/apps/life-manager \
  && npm ci --ignore-scripts --no-audit --no-fund >/dev/null 2>&1 \
  && node --test test/wake-loop-isolation.test.js
```
Expected before Tasks 3-4 land: FAIL — `wakeCallOnce is not a function`. After Tasks 3-4: this run is the verification.

- [ ] **Step 3: Make it pass**

Tasks 3 and 4 are the implementation. If a test here fails, fix `scheduler.js`, not the test. The most likely real failure is the first one: if `wakeCallOnce` still awaits an organ, the elapsed assertion catches it — that is the bug this whole task exists to prevent.

- [ ] **Step 4: Run the full affected suite**

Run:
```bash
cd /Users/operator/anicca/.worktrees/spec-two-loops/apps/life-manager \
  && npm ci --ignore-scripts --no-audit --no-fund >/dev/null 2>&1 \
  && node --test test/wake-loop-isolation.test.js test/wake-catchup.test.js test/wake-miss-record.test.js \
       lib/wake-miss.test.js lib/event-cache.test.js lib/organ-run.test.js lib/slash-command.test.js
```
Expected: `fail 0`, with at least 68 passing (55 baseline + 5 cache + 3 timing + 5 isolation).

- [ ] **Step 5: Commit**

```bash
cd /Users/operator/anicca/.worktrees/spec-two-loops
git add apps/life-manager/test/wake-loop-isolation.test.js
git commit -m "test(daily): pin that a stalled organ cannot reach the dial"
```

---

### Task 6: Start the wake loop in production

**Files:**
- Modify: `lib/maybe-start-loops.js`
- Test: `lib/maybe-start-loops.test.js`

- [ ] **Step 1: Read the existing test so the new assertion matches its style**

Run:
```bash
cd /Users/operator/anicca/.worktrees/spec-two-loops/apps/life-manager && cat lib/maybe-start-loops.test.js
```

- [ ] **Step 2: Add a failing assertion**

In `lib/maybe-start-loops.test.js`, in the test that asserts the loops start (the one calling `maybeStartLoops` with an env that permits loops), add `startWakeLoop` to the stub `starters` object and assert it was called. Follow the file's existing stub style. If the file tracks calls in an array, push `"wake"`; if it uses counters, add one. The assertion to add:

```js
assert.equal(started.wake, 1, "the dedicated wake loop must start in production, not only in tests");
```

(Adapt the left-hand side to the file's actual tracking shape — read it in Step 1.)

- [ ] **Step 3: Run test to verify it fails**

Run:
```bash
cd /Users/operator/anicca/.worktrees/spec-two-loops/apps/life-manager \
  && npm ci --ignore-scripts --no-audit --no-fund >/dev/null 2>&1 \
  && node --test lib/maybe-start-loops.test.js
```
Expected: FAIL — the wake loop is never started.

- [ ] **Step 4: Start it**

In `lib/maybe-start-loops.js`, change:

```js
  starters.startScheduler();
  starters.startTravelLoop();
```

to:

```js
  starters.startScheduler();
  // The dial runs on its own timer (spec §3.1 method A). Starting it here rather than inside
  // startScheduler keeps the two loops independently startable and independently stoppable.
  starters.startWakeLoop();
  starters.startTravelLoop();
```

- [ ] **Step 5: Wire the starter through the server**

In `server.js`, find the `maybeStartLoops(process.env, { startScheduler, startTravelLoop, startAskLoop, startOnboardLoop, startDiscoveryLoop })` call and add `startWakeLoop` to both that object and the `require("./scheduler.js")` destructuring at the top of the file.

- [ ] **Step 6: Run test to verify it passes**

Run:
```bash
cd /Users/operator/anicca/.worktrees/spec-two-loops/apps/life-manager \
  && npm ci --ignore-scripts --no-audit --no-fund >/dev/null 2>&1 \
  && node --test lib/maybe-start-loops.test.js && node -e 'require("./server.js")' 2>&1 | head -5
```
Expected: `fail 0` for the test. The `server.js` load is a syntax/wiring check — a `Cannot find` or `is not defined` error is a real failure; the server starting up and logging is fine (kill it with Ctrl-C if it blocks, or accept the head-truncated output).

- [ ] **Step 7: Commit**

```bash
cd /Users/operator/anicca/.worktrees/spec-two-loops
git add apps/life-manager/lib/maybe-start-loops.js apps/life-manager/lib/maybe-start-loops.test.js apps/life-manager/server.js
git commit -m "feat(daily): start the dedicated wake loop in production"
```

---

### Task 7: Record the receipt in the spec

**Files:**
- Modify: `docs/superpowers/specs/2026-08-01-lm-daily-organ-design.md`

- [ ] **Step 1: Run the whole affected suite once more and capture the real numbers**

Run:
```bash
cd /Users/operator/anicca/.worktrees/spec-two-loops/apps/life-manager \
  && npm ci --ignore-scripts --no-audit --no-fund >/dev/null 2>&1 \
  && node --test test/wake-loop-isolation.test.js test/wake-catchup.test.js test/wake-miss-record.test.js \
       lib/wake-miss.test.js lib/event-cache.test.js lib/organ-run.test.js lib/slash-command.test.js \
       lib/maybe-start-loops.test.js 2>&1 | grep -E "^ℹ (tests|pass|fail)"
```
Record the exact `tests` / `pass` / `fail` numbers. Do not write numbers you did not see printed.

- [ ] **Step 2: Update the 1c row**

In `docs/superpowers/specs/2026-08-01-lm-daily-organ-design.md` §3, rewrite the `| 1c |` row as done, in the same shape as the 1a and 1b rows: strike the work text, add `✅ **DONE 2026-08-01**`, and in the receipt column state the files created/changed, the split (`wakeCallOnce` / `organsUserOnce` / `wakeUserOnce` as composition), the dedicated `startWakeLoop` at 60s with `WAKE_USER_TIMEOUT_MS=20000`, the event-cache hand-off that keeps Composio volume flat, the per-organ `ms=` logging, and the exact test numbers from Step 1.

- [ ] **Step 3: Commit and push**

```bash
cd /Users/operator/anicca/.worktrees/spec-two-loops
git add docs/superpowers/specs/2026-08-01-lm-daily-organ-design.md
git commit -m "docs(daily): record 1c as done with the evidence that proves it"
git fetch origin && git push origin HEAD:docs/two-earning-loops
```

- [ ] **Step 4: Verify the push landed**

Run:
```bash
cd /Users/operator/anicca/.worktrees/spec-two-loops && git log --oneline -1 origin/docs/two-earning-loops
```
Expected: the `docs(daily): record 1c as done` commit hash.

---

## Self-Review

**Spec coverage (§3 row 1c, four done conditions):**

| Done condition | Task |
|---|---|
| ① wake 専用 tick が他 organ の所要時間に影響されない | Tasks 3-4; pinned by Task 5 test 1 and test 5 |
| ② organ 毎の経過ms がログに出る | Task 2 (`runOrgan`), applied in Task 3 Step 5 |
| ③ 遅い organ を注入した fixture で wake が定刻に鳴る | Task 5 test 1 (`slowOrganMs: 5000`, asserts <1000ms) |
| ④ Composio 呼び出し数が増えない | Task 1 (cache) + Task 5 test 3 (`fetches.length` stays 1) |

§3.1's "別プロセスにはしない" is honored — no lease key, `runtime-up.js`, railway, or Dockerfile changes appear in any task.

**Placeholder scan:** Task 3 Step 5 and Task 6 Step 2 intentionally describe a mechanical transformation over blocks that already exist in the file rather than reproducing ~120 lines verbatim; both name the exact source lines, the exact target shape, and the test that fails if it is done wrong. No other step defers work.

**Type consistency:** `wakeCallOnce`, `organsUserOnce`, `wakeUserOnce`, `wakeTick`, `startWakeLoop`, `WAKE_USER_TIMEOUT_MS`, `putEvents`, `getEvents`, `clearEvents`, `EVENT_CACHE_TTL_MS`, `runOrgan` — each is defined in the task that first uses it and spelled identically everywhere after.
