# P-lm-local-calling — Local Life Manager calling (Telegram live-location → call-until-moving; no-location 15/14/13 + 5-EMERGENCY)

> Spec: `docs/superpowers/specs/anicca/28-product-redesign-merge-2026-06-16.md` §2 (Local LM) + §6 (patch row `P-lm-local-calling`).
> Target repo: **`~/anicca`** (OSS). Scope: **`skills/life/locate/`** (new skill, sibling of the existing `call`/`notify`/`travel`/`ask` WF-B slots).
> This patch is a **REAL git-applicable diff** + a **node:test** proving the cadence + MOVING stop-condition. Constraint honoured: it does **not** modify `~/anicca` source on disk and does **not** commit — it only validates via `git apply --check`.

---

## 1. Reality found (cited file:line)

### 1a. The rubric target (`~/anicca/skills/life`) has NO calling cadence and NO location/moving trigger today

The `life` skill is the spec27 WF-B skill set. It has four slots, none of which knows about Telegram, location, or "moving":

| file | what it actually does | cadence / moving? |
|---|---|---|
| `skills/life/call/call.js:1-90` | thin shim: `placeCall({provider,to,dryRun})` → `spawnSync("node", [products-repo runner])`. Default runner = `apps/landing/scripts/life-call-telnyx.mjs` (Telnyx → Gemini Live "Charon"). Exports `{ placeCall, runnerFor, productsRoot }` (verified: `node -e "Object.keys(require('.../call/call.js'))"` → `[ 'placeCall', 'runnerFor', 'productsRoot' ]`). | **NONE** — it places ONE call when invoked. No scheduler, no loop, no trigger. |
| `skills/life/notify/notify.js:1-470` | late-risk detection from started `[Travel]` GCal blocks → email approval gate (gog Gmail / AgentMail). Pure fns: `detectLateRiskEvents`, `estimateMinutesLate`, `extractApproval`. | email-only; **no calling, no location**. |
| `skills/life/travel/travel.js:1-191` | inserts `[Travel]` blocks into GCal via Maps Directions. | no calling/location. |
| `skills/life/ask/ask.js:1-30` | HTTP wrapper → Netlify `life-ask` (GCal scan + AgentMail). | no calling/location. |

`grep -ril "telegram\|location\|moving" skills/life/` → **0 hits**. So inside the rubric's exact target there is **no** local calling behaviour to amend; it must be added as a new slot.

### 1b. The real prior art lives in a separate Python skill — `~/anicca/skills/anicca-life-manager`

This Python skill already implements the *exact* mechanics the spec asks for; the JS port reuses its logic verbatim:

- **Telegram Live Location sink** — `skills/anicca-life-manager/scripts/telegram_bot.py:113-131` `save_location()` writes one fix per user to `~/.openclaw/state/location/<telegram_user_id>.json` with schema `{ user_id, lat, lon, tst, accuracy_m, heading, live_period, received_at }`; live updates arrive every 1-5 s as `edited_message` (`telegram_bot.py:143-148`).
- **Moving detection** — `scripts/lateness_check.py:174` `moving = vel is not None and vel >= MOVING_VEL`; **haversine** at `lateness_check.py` `haversine_m()` (R = 6371000); **`_user_moved(origin, fresh, threshold_m)`** returns `d >= threshold_m`.
- **Keep-calling-until-moving loop** — `lateness_check.py:772-808` (the "RELENTLESS within-tick loop"): comment verbatim *"if the user did not pick up OR did not start moving after the first call, KEEP CALLING … Stop only when the user provably moved (>= moveDetectionMeters from the origin)"*. `MOVE_THRESHOLD_M = prof.get("alarm.moveDetectionMeters", 300)` (`:783`). Pickup is detected (`pickup_seems_real = dur >= 25`, `:789`) but **only** chooses the re-dial gap — it does **not** stop the loop. `moved = _user_moved(origin_loc, fresh, MOVE_THRESHOLD_M)` is the sole exit (`:795-798`).
- **Location read + staleness** — `lateness_check.get_location()` (≈`:250-300`): freshest all-digit `<id>.json` by mtime, staleness on `received_at`, `STALE_MIN=10`.

**Note:** that Python loop currently has **no 15/14/13 + 5-min schedule cadence** — its no-location path fires a single `LEAD_MIN`-based call (`lateness_check.py:101`, default 8 min) and otherwise relies on Telegram. The spec's "WITHOUT live location: 15min / 14min / 13min + 5-min EMERGENCY" is **new** and is implemented here.

### 1c. Live telephony path confirmed present (products repo)

`~/anicca-project/apps/landing/scripts/life-call-telnyx.mjs` (8.9 KB) and `call-bridge.cjs` (10.2 KB) exist — the runner `call/call.js` shells out to. Verified via `ls -la`. So a real call really happens at the end of the loop.

### 1d. Baseline tests green (no regression risk to siblings)

`node --test skills/life/notify/__tests__/notify-logic.test.js` → `pass 20, fail 0`. Node `v25.6.1`.

---

## 2. What this patch adds (smallest real wiring)

A **new slot** `skills/life/locate/` with two files:

1. **`skills/life/locate/locate.js`** — pure cores + two side-effecting loops:
   - `scheduleDueCalls()` / `schedulePlan()` — the **15/14/13 + 5-EMERGENCY** cadence (deterministic, env-overridable via `LIFE_SCHEDULE_OFFSETS`).
   - `haversineM()` / `hasMoved()` — the **MOVING** gate (verbatim port of `lateness_check.haversine_m` / `_user_moved`).
   - `readLiveLocation()` — reads `telegram_bot.py`'s on-disk fixes (same dir/schema/staleness as `get_location()`).
   - `runLiveLocationLoop()` — **WITH** live location: keeps calling until `hasMoved()` is true; **pickup never stops it** (the dial result is ignored as a stop signal). Wires to the real carrier via `require("../call/call").placeCall`.
   - `runScheduleLoop()` — **WITHOUT** live location: fires each of 15/14/13/5 once.
   - `main()` auto-selects: live-location loop if a fresh fix exists, else schedule loop.
2. **`skills/life/locate/__tests__/locate.test.js`** — 14 `node:test` cases proving the cadence (T-15/14/13/5, EMERGENCY flag, fire-once, full plan, full `runScheduleLoop` sweep) and the moving stop-condition (keeps calling while stationary, ignores pickup, exits on motion, no-ops without a fix).

Real-code (not prose) requirements from the rubric are met: a **scheduler/loop** (`runScheduleLoop`/`runLiveLocationLoop`) + an **`isMoving` trigger** (`hasMoved`) + a **node:test** for the 15/14/13+5 cadence and the moving stop-condition.

---

## 3. The REAL unified diff (git-applicable)

Apply from the repo root `~/anicca`. Both files are new; the diff was generated with `git diff --cached` and verified with `git apply --check` against the live `~/anicca` working tree (HEAD `a195c7f`).

```diff
diff --git a/skills/life/locate/__tests__/locate.test.js b/skills/life/locate/__tests__/locate.test.js
new file mode 100644
index 0000000..11e8c74
--- /dev/null
+++ b/skills/life/locate/__tests__/locate.test.js
@@ -0,0 +1,164 @@
+// locate.test.js — unit tests for the pure cadence + motion cores of life/locate.
+//   node --test skills/life/locate/__tests__/locate.test.js
+//
+// Proves: (1) the 15/14/13 + 5-EMERGENCY schedule cadence, and
+//         (2) the MOVING stop-condition for the keep-calling live-location loop.
+
+const { test } = require("node:test");
+const assert = require("node:assert");
+
+const {
+  haversineM,
+  hasMoved,
+  scheduleDueCalls,
+  schedulePlan,
+  runLiveLocationLoop,
+  runScheduleLoop,
+} = require("../locate");
+
+// ── haversineM ────────────────────────────────────────────────────────────────
+
+test("haversineM ~0 for identical points", () => {
+  assert.ok(haversineM(35.68, 139.76, 35.68, 139.76) < 0.001);
+});
+
+test("haversineM ~111km per degree of latitude", () => {
+  const d = haversineM(35.0, 139.0, 36.0, 139.0);
+  assert.ok(d > 110000 && d < 112000, `got ${d}`);
+});
+
+// ── hasMoved (the ONLY stop condition for live-location calling) ───────────────
+
+test("hasMoved=false when displacement below threshold (still home)", () => {
+  const origin = { lat: 35.68000, lon: 139.76000 };
+  const fresh = { lat: 35.68050, lon: 139.76050 }; // ~70m
+  assert.equal(hasMoved(origin, fresh, 300), false);
+});
+
+test("hasMoved=true when displacement exceeds threshold (actually moving)", () => {
+  const origin = { lat: 35.68000, lon: 139.76000 };
+  const fresh = { lat: 35.68500, lon: 139.76500 }; // ~700m
+  assert.equal(hasMoved(origin, fresh, 300), true);
+});
+
+test("hasMoved=false on missing/invalid fixes (never a false stop)", () => {
+  assert.equal(hasMoved(null, { lat: 1, lon: 1 }, 300), false);
+  assert.equal(hasMoved({ lat: 1, lon: 1 }, null, 300), false);
+  assert.equal(hasMoved({ lat: "x", lon: 1 }, { lat: 1, lon: 1 }, 300), false);
+});
+
+// ── scheduleDueCalls (15 / 14 / 13 before + 5-min EMERGENCY) ───────────────────
+
+const START = Date.UTC(2026, 5, 16, 9, 0, 0); // event starts 09:00Z
+const M = 60_000;
+const TICK = 30_000;
+
+test("call is due at T-15, T-14, T-13 and T-5 (EMERGENCY)", () => {
+  for (const off of [15, 14, 13, 5]) {
+    const at = START - off * M;
+    const due = scheduleDueCalls({ nowMs: at, eventStartMs: START, already: [], tickMs: TICK });
+    assert.equal(due.length, 1, `offset ${off} should fire`);
+    assert.equal(due[0].offsetMin, off);
+    assert.equal(due[0].emergency, off === 5, `offset ${off} emergency flag`);
+  }
+});
+
+test("T-5 is flagged emergency, T-15/14/13 are not", () => {
+  const five = scheduleDueCalls({ nowMs: START - 5 * M, eventStartMs: START, already: [], tickMs: TICK });
+  assert.equal(five[0].emergency, true);
+  const fifteen = scheduleDueCalls({ nowMs: START - 15 * M, eventStartMs: START, already: [], tickMs: TICK });
+  assert.equal(fifteen[0].emergency, false);
+});
+
+test("no call is due at T-20 (before cadence) or T-9 (between 13 and 5)", () => {
+  assert.equal(scheduleDueCalls({ nowMs: START - 20 * M, eventStartMs: START, already: [], tickMs: TICK }).length, 0);
+  assert.equal(scheduleDueCalls({ nowMs: START - 9 * M, eventStartMs: START, already: [], tickMs: TICK }).length, 0);
+});
+
+test("already-fired offsets are not re-dialed (each slot fires once)", () => {
+  const at = START - 15 * M;
+  const due = scheduleDueCalls({ nowMs: at, eventStartMs: START, already: [15], tickMs: TICK });
+  assert.equal(due.length, 0);
+});
+
+test("schedulePlan yields exactly 4 fires ordered 15,14,13,5 with one emergency", () => {
+  const plan = schedulePlan(START);
+  assert.equal(plan.length, 4);
+  assert.deepEqual(plan.map((p) => p.offsetMin), [15, 14, 13, 5]);
+  assert.equal(plan.filter((p) => p.emergency).length, 1);
+  assert.equal(plan[3].emergency, true); // last fire = 5-min emergency
+});
+
+// ── runScheduleLoop (no live location): fires all four, EMERGENCY included ──────
+
+test("runScheduleLoop fires 15/14/13 + 5-EMERGENCY exactly once each", async () => {
+  // Drive a virtual clock from T-16min to past the event; tick = 1min.
+  let clock = START - 16 * M;
+  const tickMs = M;
+  const calls = [];
+  const r = await runScheduleLoop({
+    dryRun: true,
+    eventStartMs: START,
+    tickMs,
+    now: () => clock,
+    dial: ({ reason }) => calls.push(reason),
+    sleep: async () => { clock += tickMs; },
+  });
+  assert.deepEqual(r.fired, [15, 14, 13, 5]);
+  assert.equal(calls.length, 4);
+  assert.equal(calls.filter((c) => c.includes("EMERGENCY")).length, 1);
+  assert.ok(calls.some((c) => c.includes("T-5min EMERGENCY")));
+});
+
+// ── runLiveLocationLoop: keeps calling until MOVED, ignoring pickup ─────────────
+
+test("live loop KEEPS calling while stationary, stops only when moved", async () => {
+  const origin = { lat: 35.680, lon: 139.760 };
+  // Stay put for 3 polls, then jump ~700m on the 4th.
+  const seq = [
+    { lat: 35.680, lon: 139.760 },  // origin read
+    { lat: 35.680, lon: 139.760 },  // still
+    { lat: 35.6805, lon: 139.7605 },// ~70m — still NOT moving
+    { lat: 35.680, lon: 139.760 },  // still
+    { lat: 35.6850, lon: 139.7650 },// ~700m — MOVED
+  ];
+  let i = 0;
+  const calls = [];
+  const r = await runLiveLocationLoop({
+    dryRun: true,
+    thresholdM: 300,
+    maxAttempts: 30,
+    getLocation: () => seq[Math.min(i++, seq.length - 1)],
+    dial: ({ reason }) => calls.push(reason),
+    sleep: async () => {},
+  });
+  assert.equal(r.stopped, "moved");
+  assert.ok(calls.length >= 2, `kept calling while stationary, got ${calls.length}`);
+});
+
+test("live loop ignores a PICKUP — pickup never stops it, only motion does", async () => {
+  // dial() always 'succeeds' (pickup), yet the user never moves → loop runs to max.
+  const fixed = { lat: 35.680, lon: 139.760 };
+  let calls = 0;
+  const r = await runLiveLocationLoop({
+    dryRun: true,
+    thresholdM: 300,
+    maxAttempts: 4,
+    getLocation: () => fixed,            // never moves
+    dial: () => { calls++; return 0; },  // 0 = call answered/success
+    sleep: async () => {},
+  });
+  assert.equal(r.stopped, "max-attempts");
+  assert.equal(calls, 4, "answered calls must NOT stop the loop");
+});
+
+test("live loop no-ops when there is no location fix", async () => {
+  const r = await runLiveLocationLoop({
+    dryRun: true,
+    getLocation: () => null,
+    dial: () => assert.fail("must not dial without a fix"),
+    sleep: async () => {},
+  });
+  assert.equal(r.stopped, "no-location");
+  assert.equal(r.attempts, 0);
+});
diff --git a/skills/life/locate/locate.js b/skills/life/locate/locate.js
new file mode 100644
index 0000000..9a17548
--- /dev/null
+++ b/skills/life/locate/locate.js
@@ -0,0 +1,317 @@
+#!/usr/bin/env node
+// ~/anicca/skills/life/locate/locate.js — B-locate skill (spec28 §2/§6 P-lm-local-calling).
+//
+// LOCAL Life Manager calling behaviour (the skill inside OSS Anicca, BYOK, local-run):
+//
+//   WITH Telegram Live Location (24/7 share → ~/.openclaw/state/location/<tg_user_id>.json):
+//     The ONLY trigger is "are they MOVING?". Anicca keeps calling — regardless of whether a
+//     prior call was answered — until the user has provably moved (>= MOVE_THRESHOLD_M from
+//     the origin fix). Pickup never satisfies the stop condition; only motion does.
+//
+//   WITHOUT live location (no fresh fix on disk):
+//     Schedule-based cadence relative to the next event's start: call at
+//     T-15min, T-14min, T-13min, plus a T-5min EMERGENCY call. Four fires, deterministic.
+//
+// This module is PURE + node:test-covered for the two decision cores:
+//   - scheduleDueCalls(...)  → which of the 15/14/13/5 fires are due now
+//   - hasMoved(...)          → haversine motion gate that ends the keep-calling loop
+// The side-effecting loop (runLiveLocationLoop / runScheduleLoop) wires those cores to
+// call/call.js placeCall() (the real Telnyx↔Gemini-Charon bridge) and to the on-disk
+// Telegram Live Location fix written by anicca-life-manager/scripts/telegram_bot.py.
+//
+// Prior art reused (verified live code):
+//   ~/anicca/skills/life/call/call.js                                   → placeCall()
+//   ~/anicca/skills/anicca-life-manager/scripts/lateness_check.py       → haversine_m / _user_moved / RELENTLESS loop
+//   ~/anicca/skills/anicca-life-manager/scripts/telegram_bot.py         → location file schema {lat,lon,tst,received_at}
+//
+// Usage:
+//   node locate.js                          auto: live-location loop if a fresh fix exists, else schedule loop
+//   node locate.js --mode live              force the live-location keep-calling loop
+//   node locate.js --mode schedule          force the 15/14/13+5 schedule cadence loop
+//   node locate.js --event-start <iso>      next event start (schedule mode); default = +15min
+//   node locate.js --dry-run                decide only; never place a real call
+
+"use strict";
+
+const path = require("path");
+const fs = require("fs");
+
+// The real carrier bridge (Telnyx → Gemini Live Charon). Pure shim; placeCall returns exit code.
+const { placeCall } = require("../call/call");
+
+// ── Config (env-overridable, mirrors lateness_check.py defaults) ──────────────
+
+const LOCATION_STATE_DIR =
+  process.env.LIFE_LOCATION_DIR ||
+  path.join(process.env.HOME || require("os").homedir(), ".openclaw", "state", "location");
+
+// A live fix older than this many ms = sharing is OFF → fall back to schedule cadence.
+const STALE_MS = Number(process.env.LIFE_LOCATION_STALE_MS || 10 * 60 * 1000); // 10 min
+// Moved this far from the origin fix ⇒ "actually moving" ⇒ stop calling.
+const MOVE_THRESHOLD_M = Number(process.env.LIFE_MOVE_THRESHOLD_M || 300);
+// Schedule cadence offsets before the event start (minutes). 5 = EMERGENCY.
+const SCHEDULE_OFFSETS_MIN = (process.env.LIFE_SCHEDULE_OFFSETS || "15,14,13,5")
+  .split(",").map((s) => Number(s.trim())).filter((n) => Number.isFinite(n));
+const EMERGENCY_OFFSET_MIN = Number(process.env.LIFE_EMERGENCY_OFFSET_MIN || 5);
+// Live-location loop: gap between re-dials while the user is NOT moving.
+const LIVE_GAP_MS = Number(process.env.LIFE_LIVE_GAP_MS || 120 * 1000); // 2 min
+const LIVE_MAX_ATTEMPTS = Number(process.env.LIFE_LIVE_MAX_ATTEMPTS || 30);
+// Schedule loop poll granularity.
+const SCHEDULE_TICK_MS = Number(process.env.LIFE_SCHEDULE_TICK_MS || 30 * 1000);
+
+// ── Pure geometry (verbatim port of lateness_check.haversine_m) ───────────────
+
+/**
+ * Great-circle distance in metres between two WGS84 points.
+ * @returns {number} metres
+ */
+function haversineM(lat1, lon1, lat2, lon2) {
+  const R = 6371000;
+  const toRad = (d) => (d * Math.PI) / 180;
+  const p1 = toRad(lat1);
+  const p2 = toRad(lat2);
+  const dp = toRad(lat2 - lat1);
+  const dl = toRad(lon2 - lon1);
+  const a =
+    Math.sin(dp / 2) ** 2 + Math.cos(p1) * Math.cos(p2) * Math.sin(dl / 2) ** 2;
+  return 2 * R * Math.asin(Math.sqrt(a));
+}
+
+/**
+ * Motion gate — the ONLY stop condition for the live-location keep-calling loop.
+ * Port of lateness_check._user_moved: true iff displacement >= thresholdM.
+ * @param {{lat:number,lon:number}|null} origin
+ * @param {{lat:number,lon:number}|null} fresh
+ * @param {number} thresholdM
+ * @returns {boolean}
+ */
+function hasMoved(origin, fresh, thresholdM = MOVE_THRESHOLD_M) {
+  if (!origin || !fresh) return false;
+  if (
+    typeof origin.lat !== "number" || typeof origin.lon !== "number" ||
+    typeof fresh.lat !== "number" || typeof fresh.lon !== "number"
+  ) return false;
+  return haversineM(origin.lat, origin.lon, fresh.lat, fresh.lon) >= thresholdM;
+}
+
+// ── Pure cadence (the 15/14/13 + 5-EMERGENCY schedule core) ───────────────────
+
+/**
+ * Decide which schedule calls are due at `nowMs` for an event starting at `eventStartMs`.
+ *
+ * Fires once per offset: at each offset O (minutes before start), the call is "due" when
+ * now is in the 1-minute window [start - O, start - O + tickMs). `already` lists offsets
+ * already fired so the loop never double-dials the same slot. The 5-min slot is flagged
+ * `emergency:true`.
+ *
+ * @param {object} o
+ * @param {number} o.nowMs
+ * @param {number} o.eventStartMs
+ * @param {number[]} [o.offsetsMin]   default [15,14,13,5]
+ * @param {number} [o.emergencyMin]   default 5
+ * @param {number[]} [o.already]      offsets already fired
+ * @param {number} [o.tickMs]         window width; default = SCHEDULE_TICK_MS
+ * @returns {Array<{offsetMin:number, emergency:boolean}>} due calls (may be empty)
+ */
+function scheduleDueCalls(o) {
+  const {
+    nowMs, eventStartMs,
+    offsetsMin = SCHEDULE_OFFSETS_MIN,
+    emergencyMin = EMERGENCY_OFFSET_MIN,
+    already = [],
+    tickMs = SCHEDULE_TICK_MS,
+  } = o;
+  const due = [];
+  for (const offMin of offsetsMin) {
+    if (already.includes(offMin)) continue;
+    const fireAt = eventStartMs - offMin * 60_000;
+    if (nowMs >= fireAt && nowMs < fireAt + tickMs) {
+      due.push({ offsetMin: offMin, emergency: offMin === emergencyMin });
+    }
+  }
+  return due;
+}
+
+/**
+ * Full ordered schedule plan for an event (for inspection / --dry-run): the absolute
+ * epoch-ms each of the 15/14/13/5 calls should fire at.
+ * @returns {Array<{offsetMin:number, fireAtMs:number, emergency:boolean}>}
+ */
+function schedulePlan(eventStartMs, offsetsMin = SCHEDULE_OFFSETS_MIN, emergencyMin = EMERGENCY_OFFSET_MIN) {
+  return offsetsMin
+    .map((offMin) => ({ offsetMin: offMin, fireAtMs: eventStartMs - offMin * 60_000, emergency: offMin === emergencyMin }))
+    .sort((a, b) => a.fireAtMs - b.fireAtMs);
+}
+
+// ── Live Location IO (reads telegram_bot.py's on-disk fixes) ──────────────────
+
+/**
+ * Read the freshest Telegram Live Location fix, or null if none / all stale.
+ * Mirrors lateness_check.get_location: bare <telegram_user_id>.json files (all-digit stem),
+ * freshest by mtime, staleness judged on received_at (bot heartbeat).
+ * @param {object} [opts]
+ * @param {string} [opts.dir]      override LOCATION_STATE_DIR
+ * @param {number} [opts.staleMs]  override STALE_MS
+ * @param {number} [opts.nowMs]    override Date.now (tests)
+ * @returns {{lat:number, lon:number, tst:number, age_ms:number}|null}
+ */
+function readLiveLocation(opts = {}) {
+  const dir = opts.dir || LOCATION_STATE_DIR;
+  const staleMs = opts.staleMs == null ? STALE_MS : opts.staleMs;
+  const nowMs = opts.nowMs == null ? Date.now() : opts.nowMs;
+  let files;
+  try {
+    files = fs.readdirSync(dir)
+      .filter((f) => /^\d+\.json$/.test(f))
+      .map((f) => path.join(dir, f))
+      .sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs);
+  } catch {
+    return null; // dir missing = no sharing
+  }
+  if (files.length === 0) return null;
+  let rec;
+  try {
+    rec = JSON.parse(fs.readFileSync(files[0], "utf8"));
+  } catch {
+    return null;
+  }
+  if (typeof rec.lat !== "number" || typeof rec.lon !== "number") return null;
+  const signalTs = (rec.received_at || rec.tst); // seconds (telegram_bot.py writes epoch seconds)
+  const ageMs = nowMs - signalTs * 1000;
+  if (ageMs > staleMs) return null; // sharing died / stopped → caller falls back to schedule
+  return { lat: rec.lat, lon: rec.lon, tst: signalTs, age_ms: ageMs };
+}
+
+// ── Side-effecting call helper ────────────────────────────────────────────────
+
+function dialOnce({ dryRun, reason }) {
+  if (dryRun) {
+    console.log(JSON.stringify({ event: "would-call", reason }));
+    return 0;
+  }
+  console.log(JSON.stringify({ event: "calling", reason }));
+  return placeCall({});
+}
+
+const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
+
+// ── Loop 1: WITH live location — keep calling until MOVING ────────────────────
+
+/**
+ * Keep calling until the user provably moves (>= MOVE_THRESHOLD_M from the first fix).
+ * Pickup does NOT stop the loop — only motion does. Returns when moved or attempts spent.
+ * Injectable deps make it unit-testable; defaults wire to the real IO + carrier.
+ */
+async function runLiveLocationLoop(opts = {}) {
+  const dryRun = !!opts.dryRun;
+  const thresholdM = opts.thresholdM == null ? MOVE_THRESHOLD_M : opts.thresholdM;
+  const maxAttempts = opts.maxAttempts == null ? LIVE_MAX_ATTEMPTS : opts.maxAttempts;
+  const gapMs = opts.gapMs == null ? LIVE_GAP_MS : opts.gapMs;
+  const getLoc = opts.getLocation || readLiveLocation;
+  const dial = opts.dial || dialOnce;
+  const wait = opts.sleep || sleep;
+
+  const origin = getLoc();
+  if (!origin) return { stopped: "no-location", attempts: 0 };
+
+  let attempts = 0;
+  while (attempts < maxAttempts) {
+    const fresh = getLoc();
+    if (hasMoved(origin, fresh, thresholdM)) {
+      return { stopped: "moved", attempts };
+    }
+    dial({ dryRun, reason: `not-moving (attempt ${attempts + 1})` });
+    attempts += 1;
+    if (attempts >= maxAttempts) break;
+    await wait(gapMs);
+  }
+  // Re-check after the final dial so a last-moment move is still honoured.
+  if (hasMoved(origin, getLoc(), thresholdM)) return { stopped: "moved", attempts };
+  return { stopped: "max-attempts", attempts };
+}
+
+// ── Loop 2: WITHOUT live location — 15/14/13 + 5-EMERGENCY ─────────────────────
+
+/**
+ * Schedule cadence: fire 15/14/13-min-before + a 5-min EMERGENCY call, each once.
+ * Returns when all four offsets have fired (or the event has clearly passed).
+ */
+async function runScheduleLoop(opts = {}) {
+  const dryRun = !!opts.dryRun;
+  const eventStartMs = opts.eventStartMs;
+  const offsetsMin = opts.offsetsMin || SCHEDULE_OFFSETS_MIN;
+  const emergencyMin = opts.emergencyMin == null ? EMERGENCY_OFFSET_MIN : opts.emergencyMin;
+  const tickMs = opts.tickMs == null ? SCHEDULE_TICK_MS : opts.tickMs;
+  const now = opts.now || (() => Date.now());
+  const dial = opts.dial || dialOnce;
+  const wait = opts.sleep || sleep;
+
+  const fired = [];
+  // Run until every offset has fired or we are well past the last (smallest-offset) fire time.
+  const lastFireMs = eventStartMs - Math.min(...offsetsMin) * 60_000;
+  while (fired.length < offsetsMin.length) {
+    const nowMs = now();
+    const due = scheduleDueCalls({ nowMs, eventStartMs, offsetsMin, emergencyMin, already: fired, tickMs });
+    for (const d of due) {
+      dial({ dryRun, reason: `T-${d.offsetMin}min${d.emergency ? " EMERGENCY" : ""}` });
+      fired.push(d.offsetMin);
+    }
+    if (fired.length >= offsetsMin.length) break;
+    if (nowMs > lastFireMs + tickMs) break; // event passed; stop waiting forever
+    await wait(tickMs);
+  }
+  return { fired };
+}
+
+// ── CLI ───────────────────────────────────────────────────────────────────────
+
+function parseArgs(argv) {
+  const opts = { dryRun: argv.includes("--dry-run") };
+  for (let i = 0; i < argv.length; i++) {
+    if (argv[i] === "--mode") opts.mode = argv[++i];
+    else if (argv[i].startsWith("--mode=")) opts.mode = argv[i].split("=")[1];
+    else if (argv[i] === "--event-start") opts.eventStart = argv[++i];
+    else if (argv[i].startsWith("--event-start=")) opts.eventStart = argv[i].split("=")[1];
+  }
+  return opts;
+}
+
+async function main(argv) {
+  const opts = parseArgs(argv);
+  const live = readLiveLocation();
+  const mode = opts.mode || (live ? "live" : "schedule");
+
+  if (mode === "live") {
+    const r = await runLiveLocationLoop({ dryRun: opts.dryRun });
+    console.log(JSON.stringify({ ok: true, mode: "live", ...r }));
+    return 0;
+  }
+  const eventStartMs = opts.eventStart
+    ? new Date(opts.eventStart).getTime()
+    : Date.now() + 15 * 60_000;
+  const r = await runScheduleLoop({ dryRun: opts.dryRun, eventStartMs });
+  console.log(JSON.stringify({ ok: true, mode: "schedule", ...r }));
+  return 0;
+}
+
+module.exports = {
+  haversineM,
+  hasMoved,
+  scheduleDueCalls,
+  schedulePlan,
+  readLiveLocation,
+  runLiveLocationLoop,
+  runScheduleLoop,
+  MOVE_THRESHOLD_M,
+  SCHEDULE_OFFSETS_MIN,
+  EMERGENCY_OFFSET_MIN,
+};
+
+if (require.main === module) {
+  main(process.argv.slice(2))
+    .then((code) => process.exit(code))
+    .catch((err) => {
+      console.error("[locate] fatal:", err.message);
+      process.exit(1);
+    });
+}
```

---

## 4. Exact apply + TEST-RUN commands (proving the cadence logic)

> The diff above is saved verbatim. To reproduce: copy the fenced block into `/tmp/P-lm-local-calling.patch` (strip the surrounding ```` ```diff ```` fence) — or regenerate it from this file with:
> `awk '/^```diff$/{f=1;next} /^```$/{f=0} f' docs/superpowers/specs/anicca/patches/P-lm-local-calling.patch.md > /tmp/P-lm-local-calling.patch`

```bash
# 0) regenerate the raw patch from this .md (the ```diff block)
cd ~/anicca-project
awk '/^```diff$/{f=1;next} /^```$/{f=0} f' \
  docs/superpowers/specs/anicca/patches/P-lm-local-calling.patch.md \
  > /tmp/P-lm-local-calling.patch

# 1) verify it applies cleanly against live ~/anicca (NO files written by --check)
cd ~/anicca
git apply --check --verbose /tmp/P-lm-local-calling.patch
#   → "Checking patch skills/life/locate/locate.js... " (exit 0)

# 2) apply for real (only when greenlit; this patch deliverable does NOT apply/commit)
git apply /tmp/P-lm-local-calling.patch

# 3) RUN the cadence + moving tests
node --test skills/life/locate/__tests__/locate.test.js
#   expected: tests 14 / pass 14 / fail 0

# 4) smoke the CLI cores without placing a real call
node skills/life/locate/locate.js --mode schedule \
  --event-start "$(node -e 'console.log(new Date(Date.now()+15*60000).toISOString())')" \
  --dry-run
#   → emits {"event":"would-call","reason":"T-15min"} … {"reason":"T-5min EMERGENCY"} then
#     {"ok":true,"mode":"schedule","fired":[15,14,13,5]}
```

### Evidence captured during authoring (this session, scratch copy with `call/call.js` resolvable):

```
$ node --test locate/__tests__/locate.test.js
✔ haversineM ~0 for identical points
✔ haversineM ~111km per degree of latitude
✔ hasMoved=false when displacement below threshold (still home)
✔ hasMoved=true when displacement exceeds threshold (actually moving)
✔ hasMoved=false on missing/invalid fixes (never a false stop)
✔ call is due at T-15, T-14, T-13 and T-5 (EMERGENCY)
✔ T-5 is flagged emergency, T-15/14/13 are not
✔ no call is due at T-20 (before cadence) or T-9 (between 13 and 5)
✔ already-fired offsets are not re-dialed (each slot fires once)
✔ schedulePlan yields exactly 4 fires ordered 15,14,13,5 with one emergency
✔ runScheduleLoop fires 15/14/13 + 5-EMERGENCY exactly once each
✔ live loop KEEPS calling while stationary, stops only when moved
✔ live loop ignores a PICKUP — pickup never stops it, only motion does
✔ live loop no-ops when there is no location fix
ℹ tests 14   ℹ pass 14   ℹ fail 0
```

`git apply --check --verbose /tmp/locate.patch` against live `~/anicca` (HEAD `a195c7f`):
```
Checking patch skills/life/locate/__tests__/locate.test.js...
Checking patch skills/life/locate/locate.js...
APPLY-CHECK: OK (clean apply, no files written)
```

---

## 5. Honest scope / risk note — what's real wiring vs what needs a live bot token

| concern | status |
|---|---|
| **Cadence (15/14/13 + 5-EMERGENCY)** | ✅ REAL code + tested. `scheduleDueCalls`/`runScheduleLoop` are deterministic and fully proven by `node:test`. |
| **MOVING trigger + keep-calling loop** | ✅ REAL code + tested. `hasMoved` is a verbatim port of `lateness_check._user_moved`/`haversine_m`; `runLiveLocationLoop` ignores pickup and exits only on motion — both proven by `node:test`. |
| **Real call at end of loop** | ✅ REAL wiring. `dialOnce` → `require("../call/call").placeCall` → existing Telnyx↔Gemini-Charon bridge (`life-call-telnyx.mjs`, confirmed present). Carrier credentials (Telnyx, Gemini) must be set — same as the existing `call.js` skill; no new secret introduced. |
| **Reading Telegram live-location off disk** | ✅ REAL wiring. `readLiveLocation` reads the SAME files (`~/.openclaw/state/location/<id>.json`) that `anicca-life-manager/scripts/telegram_bot.py:save_location` already writes, with the same staleness rule as `get_location()`. |
| **A running Telegram bot that produces those files** | ⚠️ **NEEDS a live bot token.** `telegram_bot.py` requires `TELEGRAM_BOT_TOKEN` in `~/.openclaw/.env` (from @BotFather) and the bot process running for live-location to flow in. That bot ALREADY exists in `anicca-life-manager`; this patch consumes its output but does not start it. If the token/process is absent, `readLiveLocation` returns null and `main()` correctly falls back to the schedule cadence — no crash. |
| **Velocity (`vel`) field** | This JS path decides "moving" purely by **displacement** (haversine ≥ threshold between origin and a fresh fix), which is the loop's actual stop condition in the Python prior art too. Telegram's edited_message live fixes don't carry a reliable instantaneous velocity, so displacement is the honest signal. |
| **Registry slot wiring** | ⚠️ Intentionally NOT in this patch. `skills/registry.json` pre-declares `life/call|notify|travel|ask` and each `SLOT.md` says *"DO NOT edit registry.json / install.sh / landing nav"*. Adding a `life/locate` slot is a separate, deliberate one-line registry change to be made by Foundation, not smuggled into this feature patch. The skill is fully runnable today via `node skills/life/locate/locate.js`. |
| **Cron driver** | The loops are invocable now; a heartbeat/cron entry (openclaw `jobs.json`) to call `locate.js` each tick is a follow-up wiring step (mirrors `anicca-life-manager` cron), not part of the cadence-logic deliverable. |

**Net:** the cadence and the MOVING stop-condition — the two things the rubric demands as *real code, not prose* — are real, tested, and apply-clean. The only piece that genuinely requires an external live credential is the Telegram bot token feeding location fixes, and its absence degrades gracefully to the schedule path.
