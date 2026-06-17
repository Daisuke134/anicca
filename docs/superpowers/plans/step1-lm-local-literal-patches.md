# STEP 1 — Life Manager LOCAL — LITERAL diff patches (file / line / +-)

Grounded against real code (Explore audit 2026-06-17). System is ~95% built + cron-wired.
ONLY GAP = the 15-min-before call loop is not wired. These 3 patches close it. No web-app, no UI.

Reuses (verified, unchanged): `travel.js listEvents/isTravelBlock` · `locate.js scheduleDueCalls` (pure
`[{offsetMin,emergency}]`) · `call.js placeCall({to?})` → `life-call-telnyx.mjs` → Telnyx↔Gemini-Charon.
Event shape (verified travel.js:145-152): `{summary:string, start:{dateTime:ISO}, location:string}`.
[Travel] block (verified travel.js:127-149): `summary === "[Travel] " + eventSummary`.

═══════════════════════════════════════════════════════════════════════════
## PATCH 1 — export `listEvents` from travel.js (so loop.js can reuse it)
FILE: /Users/anicca/anicca/skills/life/travel/travel.js
At module.exports (verified lines 238-244), add `listEvents,` (loop.js needs only this):
```diff
 module.exports = {
+  listEvents,
   isTravelBlock,
   detectMissingTravelBlocks,
   getTravelDurationSec,
   TRAVEL_PREFIX,
   DEFAULT_TRAVEL_SEC,
 };
```
(`listEvents` is defined at travel.js:64 but currently not exported.)

═══════════════════════════════════════════════════════════════════════════
## PATCH 2 — NEW FILE: the call dispatcher loop
FILE: /Users/anicca/anicca/skills/life/loop.js  (create, full content)
```js
#!/usr/bin/env node
// skills/life/loop.js — the missing glue: the life-call dispatcher.
// Cron runs this every 5 min (07–23 JST). For each of today's events that REQUIRE TRAVEL (has a
// [Travel] block), it fires the Charon phone call ~15 min before the LEAVE time, de-duped via
// ~/.openclaw/state/life-called-today.jsonl so an event is never called twice for the same offset.
// Reuses travel.js/locate.js/call.js (no new carrier code). Note: locate.js's `emergency` flag is
// computed in `due` but not consumed here (call.js takes no urgency arg) — fine for STEP 1.
"use strict";
const fs = require("fs");
const path = require("path");
const os = require("os");
const { listEvents, isTravelBlock, TRAVEL_PREFIX } = require("../travel/travel");
const { scheduleDueCalls } = require("../locate/locate");
const { placeCall } = require("../call/call");

const OFFSETS = (process.env.LIFE_SCHEDULE_OFFSETS || "15")  // single reminder by default (no spam)
  .split(",").map((s) => Number(s.trim())).filter((n) => Number.isFinite(n));
const TICK_MS = Number(process.env.LIFE_LOOP_TICK_MS || 300_000); // must cover the cron interval (*/5 = 300s)
const STATE_FILE = process.env.LIFE_CALLED_STATE
  || path.join(os.homedir(), ".openclaw", "state", "life-called-today.jsonl");

function today() { return new Date().toISOString().slice(0, 10); }
function eventKey(summary, leaveMs) { return `${(summary || "").trim()}@${leaveMs}`; }

// already-fired offsets per event key, today only → { key: [offsetMin,...] }
function readCalled() {
  const out = {}; let raw = "";
  try { raw = fs.readFileSync(STATE_FILE, "utf8"); } catch { return out; }
  for (const line of raw.split("\n")) {
    const t = line.trim(); if (!t) continue;
    let rec; try { rec = JSON.parse(t); } catch { continue; }
    if (rec.day !== today()) continue;
    (out[rec.key] ||= []).push(rec.offsetMin);
  }
  return out;
}
function recordCalled(key, offsetMin) {
  const rec = { key, offsetMin, day: today(), ts: Date.now() };
  fs.mkdirSync(path.dirname(STATE_FILE), { recursive: true });
  fs.appendFileSync(STATE_FILE, JSON.stringify(rec) + "\n");
}
// leave time (ms) = the event's [Travel] block start. ELIGIBILITY FILTER: only events that have a
// [Travel] block (= real external location, travel needed) get a call. Events with no location/no
// block (meditation, sleep, home routines) return null → skipped. This is what prevents carpet-bombing.
function leaveTimeMs(ev, allEvents) {
  const title = (ev.summary || "").trim();
  const block = allEvents.find((e) => isTravelBlock(e.summary || "") &&
    (e.summary || "").slice(TRAVEL_PREFIX.length).trim() === title);
  if (!block || !block.start || !block.start.dateTime) return null; // no travel needed → no call
  return Date.parse(block.start.dateTime);
}

async function runLoop({ nowMs = Date.now(), dryRun = false } = {}) {
  const events = listEvents();          // sync (execFileSync gog), today..+horizon
  const called = readCalled();
  let calls = 0;
  for (const ev of events) {
    const summary = (ev.summary || "").trim();
    if (isTravelBlock(summary)) continue;            // skip the [Travel] blocks
    if (!ev.start || !ev.start.dateTime) continue;   // skip all-day
    const leaveMs = leaveTimeMs(ev, events);
    if (leaveMs == null) continue;
    const key = eventKey(summary, leaveMs);
    const due = scheduleDueCalls({ nowMs, eventStartMs: leaveMs, offsetsMin: OFFSETS, already: called[key] || [], tickMs: TICK_MS });
    if (!due.length) continue;
    console.log(`[life-loop] "${summary}" leave=${new Date(leaveMs).toISOString()} due=${due.map((d) => d.offsetMin).join(",")}`);
    if (!dryRun) placeCall({});                       // real Telnyx↔Charon call to Dais
    for (const d of due) recordCalled(key, d.offsetMin);
    calls++;
  }
  console.log(`[life-loop] ${events.length} events, ${calls} call(s) fired`);
  return calls;
}

if (require.main === module) {
  runLoop({ dryRun: process.argv.includes("--dry-run") })
    .catch((e) => { console.error("[life-loop] error:", e.message); process.exit(1); }); // exit 1 so broken gog-auth surfaces (HARD 0.24), not a silent "phone never rang"
}
module.exports = { runLoop, leaveTimeMs, eventKey };
```

═══════════════════════════════════════════════════════════════════════════
## PATCH 3 — cron entry (wire loop.js every 5 min, 07–23 JST) — FULL verified shape
FILE: /Users/anicca/.openclaw/cron/jobs.json
Mirror the EXACT field set of the live `anicca-life-notify-poll` entry. Review found the v1 draft
dropped 4 required fields → without them the phone would NOT ring (no `toolsAllow:["exec"]`) and the
job would NOT wake (no `sessionTarget`/`wakeMode`). Corrected:
```diff
+    {
+      "id": "anicca-life-call",
+      "agentId": "anicca",
+      "name": "anicca-life-call",
+      "enabled": true,
+      "schedule": { "kind": "cron", "expr": "*/5 7-23 * * *", "tz": "Asia/Tokyo" },
+      "sessionTarget": "isolated",
+      "wakeMode": "now",
+      "payload": {
+        "kind": "agentTurn",
+        "message": "Use exec to run: node /Users/anicca/anicca/skills/life/loop.js",
+        "toolsAllow": ["exec"],
+        "timeoutSeconds": 120
+      }
+    },
```
`*/5` = verified granularity (0/221 jobs use minute-cron; finest existing = `*/5`). With single offset
`15` + `tickMs=300000`, the call fires once at the first */5 tick inside [leave−15min, leave−10min).
Gateway hot-reloads jobs.json (no restart). De-dup state auto-creates at ~/.openclaw/state/life-called-today.jsonl.

═══════════════════════════════════════════════════════════════════════════
## DESIGN DECISIONS — resolved per review (round 2), confirm:
1. **Call timing** = ~15 min before **LEAVE time** (= the [Travel] block start, travel included). ✅ chosen.
2. **Eligibility filter (review CRITICAL #3 — anti-carpet-bomb)**: call ONLY for events that HAVE a [Travel] block (real external location, travel needed). Events with no location (meditation/sleep/home) are skipped. `leaveTimeMs` returns null for them. ✅ chosen — cuts the 21 events/day down to genuine trips.
3. **Reminders** = **1 call per event** (default `LIFE_SCHEDULE_OFFSETS=15`). Not 3-4. Add more offsets only if Dais wants. ✅ chosen.
4. **Cron cadence** = `*/5` (verified granularity; minute-cron is 0/221 untested) + `tickMs=300000`. ✅ chosen.
5. **Cron entry shape** = full verified field set (`agentId/sessionTarget/wakeMode/toolsAllow`). ✅ fixed (review CRITICAL #1/#2 — without these the phone never rings / never wakes).
6. **fail = exit 1** (broken gog-auth surfaces, not a silent no-ring). ✅ fixed.
7. **profile.json** = STEP 1 stays env-driven (Dais already configured). SSOT-wiring deferred to LM web (STEP 2).
OPEN for Dais: is "every event that needs travel, one call ~15min before leave" the right scope, or restrict further (e.g. only trips > N min, or only work/external — via a calendar-color or location≠home filter)?

## E2E (no-mock, the final check)
1. Insert a real GCal event 16 min out with a real `location` (so travel.js adds a [Travel] block).
2. Run `node skills/life/travel/travel.js` (or wait for travel-fill cron) → confirm [Travel] block inserted.
3. Run `node skills/life/loop.js` at T−15 → **Dais's real phone rings**, Gemini-Charon guides.
4. Verify: Telnyx call-id returned + audio stream present + de-dup record written + no 2nd call same offset.
