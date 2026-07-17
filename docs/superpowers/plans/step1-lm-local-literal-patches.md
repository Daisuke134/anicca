# STEP 1 — Life Manager LOCAL — LITERAL diff patches v3 (schedule-based, Dais 2026-06-17)

Supersedes v1/v2 (loop.js polling). CORRECTED per Dais: ALL events get calls; offsets **15/14/13/10/5**;
**schedule-based `--at` one-shots, NOT polling**. Verified interfaces:
- `openclaw cron add --at <ISO> --delete-after-run --agent <id> --session isolated --wake now --tools exec --timeout-seconds <n> --name <name> --message <text>` (from `openclaw cron add --help`).
- `travel.js`: `listEvents()` sync, event `{summary, start:{dateTime:ISO}, location}`, `[Travel] `+title blocks, exports at :238 (PATCH 1 adds `listEvents`).
- `call.js`: `placeCall({to?})` sync → `life-call-telnyx.mjs` (the runner that rang Dais; Telnyx not Twilio).
Maps to spec §15 bullet 4 (LM-E4). Verifies: phone rings at −15/−14/−13/−10/−5 of every event's leave time.

═══════════════════════════════════════════════════════════════════════════
## PATCH 1 — export `listEvents` from travel.js
FILE: /Users/anicca/anicca/skills/life/travel/travel.js  (module.exports, verified :238-244)
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

═══════════════════════════════════════════════════════════════════════════
## PATCH 2 — NEW FILE: the schedule-based call planner
FILE: /Users/anicca/anicca/skills/life/planner.js  (create, full content)
```js
#!/usr/bin/env node
// skills/life/planner.js — schedule-based call planner (replaces polling). A thin cron runs this
// every 10 min (07–23 JST); it does NOT call. It reads today + horizon gcal events (so an early
// next-morning wake-up is registered by tonight's last run), and, for EVERY timed event,
// for each offset [15,14,13,10,5] whose fire time is still in the FUTURE, registers a one-shot
// `openclaw cron add --at <fireISO> --delete-after-run` job that places the Charon call at that exact
// minute. Idempotent by deterministic job name → re-runs never double-register. LEAVE time = the
// event's [Travel] block start (travel included) if present, else the event start.
// Reuses travel.js (listEvents/isTravelBlock) + call.js (via the registered job). No polling, no calls here.
"use strict";
const { execFileSync } = require("child_process");
const { listEvents, isTravelBlock, TRAVEL_PREFIX } = require("../travel/travel");

const OFFSETS = (process.env.LIFE_SCHEDULE_OFFSETS || "15,14,13,10,5")
  .split(",").map((s) => Number(s.trim())).filter((n) => Number.isFinite(n));
const OPENCLAW = process.env.OPENCLAW_BIN || "openclaw";
const AGENT = process.env.LIFE_AGENT_ID || "anicca";
const CALL_CMD = `Use exec to run: node ${process.env.HOME}/anicca/skills/life/call/call.js`;

function existingJobNames() {
  try {
    const raw = execFileSync(OPENCLAW, ["cron", "list", "--json"], { timeout: 30000 }).toString();
    const d = JSON.parse(raw);
    const jobs = Array.isArray(d) ? d : (d.jobs || []);
    return new Set(jobs.map((j) => j && j.name).filter(Boolean));
  } catch { return new Set(); }
}

// leave time (ms) = the event's [Travel] block start, else the event start
function leaveTimeMs(ev, all) {
  const title = (ev.summary || "").trim();
  const block = all.find((e) => isTravelBlock(e.summary || "") &&
    (e.summary || "").slice(TRAVEL_PREFIX.length).trim() === title);
  const iso = (block && block.start && block.start.dateTime) || (ev.start && ev.start.dateTime);
  return iso ? Date.parse(iso) : null;
}
function safeName(s) { return (s || "").replace(/[^A-Za-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 40); }

function registerAt(name, fireIso, dryRun) {
  const args = ["cron", "add", "--name", name, "--at", fireIso, "--delete-after-run",
    "--agent", AGENT, "--session", "isolated", "--wake", "now", "--tools", "exec",
    "--timeout-seconds", "120", "--message", CALL_CMD];
  if (dryRun) { console.log("[plan] would add", name, "@", fireIso); return; }
  execFileSync(OPENCLAW, args, { timeout: 30000 });
}

function plan({ nowMs = Date.now(), dryRun = false } = {}) {
  const events = listEvents();             // today + TRAVEL_HORIZON_DAYS (covers early next-morning events)
  const existing = existingJobNames();
  let added = 0;
  for (const ev of events) {
    try {
      const summary = (ev.summary || "").trim();
      if (isTravelBlock(summary)) continue;            // skip the [Travel] blocks themselves
      if (!ev.start || !ev.start.dateTime) continue;   // skip all-day events
      const leaveMs = leaveTimeMs(ev, events);
      if (leaveMs == null) continue;
      // FIX1: name keyed on the leave INSTANT (YYYYMMDDHHMM), not just the ASCII slug — so two
      // same-slug JP events on one day (e.g. [NAIST]…#5 ×2) no longer collapse to one name.
      const stamp = new Date(leaveMs).toISOString().slice(0, 16).replace(/[-:T]/g, "");
      for (const off of OFFSETS) {
        const fireMs = leaveMs - off * 60_000;
        if (fireMs <= nowMs) continue;                 // offset already passed → no past --at
        const name = `life-call-${stamp}-${safeName(summary)}-${off}`;
        if (existing.has(name)) continue;              // idempotent: already scheduled
        registerAt(name, new Date(fireMs).toISOString(), dryRun);
        added++;
      }
    } catch (e) { console.error("[plan] skip", (ev.summary || "").slice(0, 40), e.message); } // one bad event must not starve the rest
  }
  console.log(`[plan] ${events.length} events scanned, ${added} call job(s) registered`);
  return added;
}

if (require.main === module) {
  try { plan({ dryRun: process.argv.includes("--dry-run") }); }
  catch (e) { console.error("[plan] error:", e.message); process.exit(1); } // surface gog/openclaw failure
}
module.exports = { plan, leaveTimeMs, safeName };
```

═══════════════════════════════════════════════════════════════════════════
## PATCH 3 — planner cron (every 10 min, 07–23 JST) — full verified shape
FILE: /Users/anicca/.openclaw/cron/jobs.json  (add to jobs[]; mirrors anicca-life-notify-poll)
```diff
+    {
+      "id": "anicca-life-plan",
+      "agentId": "anicca",
+      "name": "anicca-life-plan",
+      "enabled": true,
+      "schedule": { "kind": "cron", "expr": "*/10 7-23 * * *", "tz": "Asia/Tokyo" },
+      "sessionTarget": "isolated",
+      "wakeMode": "now",
+      "payload": {
+        "kind": "agentTurn",
+        "message": "Use exec to run: node /Users/anicca/anicca/skills/life/planner.js",
+        "toolsAllow": ["exec"],
+        "timeoutSeconds": 120
+      }
+    },
```
Planner runs every 10 min (cheap: lists gcal + registers --at jobs, NEVER calls). The actual calls fire
exactly at −15/−14/−13/−10/−5 via the one-shot `--at` jobs, which auto-delete after firing.

═══════════════════════════════════════════════════════════════════════════
## OPEN review points (for S6 code-review)
1. `openclaw cron list --json` job object — is the field `.name`? (idempotency depends on it). VERIFY.
2. Does a `--at ... --tools exec` one-shot actually run with exec permitted when it fires? VERIFY (dry test).
3. `--at` accepts a UTC `Z` ISO (we pass `toISOString()`)? Or must it carry an offset + `--tz`? VERIFY.
4. Planner every 10 min vs smallest lead: an event added <15 min before leave gets only the offsets still
   in the future — acceptable (some reminders), confirm with Dais.
5. call.js `placeCall({})` uses default Dais number — correct for dogfood; param when multi-user (STEP 2).

## E2E (LM-E4, no-mock — the verifying test for spec §15 bullet 4)
1. Insert a real gcal event ~16 min out with a location → travel.js adds its [Travel] block (leave time).
2. Run `node skills/life/planner.js` → assert 5 `--at` jobs registered (`openclaw cron list` shows them).
3. Wait → **Dais's real phone rings at −15/−14/−13/−10/−5** (Telnyx call-id + Gemini-Charon audio each).
4. Assert each one-shot job auto-deleted after firing; re-running planner does NOT double-register.
