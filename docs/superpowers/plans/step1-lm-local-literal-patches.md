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
At module.exports (verified lines 238-244), add `listEvents,` and `insertEvent,`:
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
// Cron runs this every minute (07–23 JST). For each of today's real events it fires the
// 15/14/13/5-min-before Charon phone call at the LEAVE time (= the event's [Travel] block start,
// else the event start), de-duped via ~/.openclaw/state/life-called-today.jsonl so an event is
// never called twice for the same offset. Reuses travel.js/locate.js/call.js (no new carrier code).
"use strict";
const fs = require("fs");
const path = require("path");
const os = require("os");
const { listEvents, isTravelBlock, TRAVEL_PREFIX } = require("../travel/travel");
const { scheduleDueCalls } = require("../locate/locate");
const { placeCall } = require("../call/call");

const OFFSETS = (process.env.LIFE_SCHEDULE_OFFSETS || "15,14,13,5")
  .split(",").map((s) => Number(s.trim())).filter((n) => Number.isFinite(n));
const TICK_MS = Number(process.env.LIFE_LOOP_TICK_MS || 60_000); // must cover the cron interval
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
// leave time (ms) = the event's [Travel] block start, else the event start
function leaveTimeMs(ev, allEvents) {
  const title = (ev.summary || "").trim();
  const block = allEvents.find((e) => isTravelBlock(e.summary || "") &&
    (e.summary || "").slice(TRAVEL_PREFIX.length).trim() === title);
  const iso = (block && block.start && block.start.dateTime) || (ev.start && ev.start.dateTime);
  return iso ? Date.parse(iso) : null;
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
    .catch((e) => { console.error("[life-loop] error:", e.message); process.exit(0); }); // fail-soft
}
module.exports = { runLoop, leaveTimeMs, eventKey };
```

═══════════════════════════════════════════════════════════════════════════
## PATCH 3 — cron entry (wire loop.js every minute, 07–23 JST)
FILE: /Users/anicca/.openclaw/cron/jobs.json
Add to the jobs array (same shape as the verified existing `anicca-life-notify-poll` entry):
```diff
+    {
+      "id": "anicca-life-call",
+      "name": "anicca-life-call",
+      "enabled": true,
+      "schedule": { "kind": "cron", "expr": "* 7-23 * * *", "tz": "Asia/Tokyo" },
+      "payload": {
+        "kind": "agentTurn",
+        "message": "Use exec to run: node /Users/anicca/anicca/skills/life/loop.js",
+        "timeoutSeconds": 120
+      }
+    },
```
Gateway hot-reloads jobs.json (no restart). De-dup state auto-creates at ~/.openclaw/state/life-called-today.jsonl.

═══════════════════════════════════════════════════════════════════════════
## DESIGN DECISIONS (resolve before coding)
1. **Call timing** = 15/14/13/5 min before **LEAVE time** (event start − travel), NOT event start. (chosen: leave time, so travel is included — matches the product promise. Confirm.)
2. **Cron cadence** = every 1 min + `tickMs=60_000` → each offset fires once, precisely. (Alt: every 5 min + tickMs=300_000 = fewer gog calls but lumps the 15/14/13 reminders. Chosen: 1-min for precise reminders. Confirm.)
3. **Multiple reminders**: Dais gets ~3 calls (−15, then −14/−13 lumped if a tick lands between, then −5). If ONE call is wanted, set `LIFE_SCHEDULE_OFFSETS=15` (single). (Confirm desired # of reminders.)
4. **profile.json**: skills today read ENV + hardcoded defaults, NOT `~/.anicca/.../profile.json`. For Dais's dogfood this already works (phone/home/keys all set). Wiring profile.json as SSOT = deferred to the product onboarding (LM web / `anicca life setup`), out of STEP-1 scope.

## E2E (no-mock, the final check)
1. Insert a real GCal event 16 min out with a real `location` (so travel.js adds a [Travel] block).
2. Run `node skills/life/travel/travel.js` (or wait for travel-fill cron) → confirm [Travel] block inserted.
3. Run `node skills/life/loop.js` at T−15 → **Dais's real phone rings**, Gemini-Charon guides.
4. Verify: Telnyx call-id returned + audio stream present + de-dup record written + no 2nd call same offset.
