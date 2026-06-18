# Life Manager — VCSDD Patchset (line-by-line, reviewed BEFORE implementation)

Dais 2026-06-18: "write the complete line by line +- patches… then get reviewed… too worried to go when things aren't cleared."

Rule: **one workstream at a time, COMPLETE real diffs grounded in current code, code-reviewer → ok:true, THEN next.** No mega-fake dump. Dependency order: WS1 (adapter) defines the file boundaries every later patch builds on.

Source of truth for current code: `~/anicca/skills/life/` (read in full for each diff).

---

## WS1 — Transport adapter (the ONLY local↔cloud difference)

**Goal**: every consumer (planner / ask / notify / travel) talks to `calendar.*` / `mail.*`, never `gog` directly. `LIFE_TRANSPORT=gog` (local, user keys) | `composio` (cloud, we manage keys). Same core code both sides.

**Files in WS1**: NEW `adapters/transport.js`; edit `planner.js`, `ask/ask-local.js`, `notify/notify.js` (JS). Python sibling `travel/travel_fill.py` = WS1b (separate diff, same interface in Python).

This document v1 contains the fully-grounded diffs for the NEW adapter + `planner.js` + `ask/ask-local.js` (both read line-by-line). `notify.js` + `travel_fill.py` follow in v2 of this same WS1 once their full bodies are read — same mechanical pattern.

### WS1.1 — NEW FILE `~/anicca/skills/life/adapters/transport.js`

```js
"use strict";
// Life Manager transport adapter — the ONE place local & cloud differ.
//   LIFE_TRANSPORT=gog       (local)  → user's own gog CLI + keychain
//   LIFE_TRANSPORT=composio  (cloud)  → Composio OAuth, keys we manage (wired in #49)
// Consumers call calendar.*/mail.* ONLY. They never spawn gog themselves.
const { execFileSync } = require("node:child_process");

// LOCAL implementation: wraps the verified `gog` CLI shapes (gog 0.17.0).
function gogTransport({ bin = "/opt/homebrew/bin/gog", account, keyring = "", calId = "primary" } = {}) {
  const env = () => ({ ...process.env, GOG_KEYRING_PASSWORD: keyring, GOG_ACCOUNT: account });
  // every gog call ends with --account <account> (matches current call sites verbatim)
  const run = (args, timeout = 60000) =>
    execFileSync(bin, [...args, "--account", account], { env: env(), encoding: "utf8", timeout });
  return {
    calendar: {
      // from default "today"; to = "YYYY-MM-DD" (optional). Returns raw gog event items[].
      list({ from = "today", to, max = 250 } = {}) {
        const args = ["calendar", "events", "list", "-j", "--from", from, "--all-pages", "--max", String(max)];
        if (to) args.push("--to", to);
        const d = JSON.parse(run(args));
        return Array.isArray(d) ? d : (d.events || d.items || []);
      },
      // gog calendar update needs <calendarId> <eventId> (two positionals) — verified.
      updateLocation(eventId, location) {
        run(["calendar", "update", calId, eventId, "--location", location, "-j"], 30000);
        return true;
      },
    },
    mail: {
      send({ to, subject, body }) {
        const out = run(["gmail", "send", "--to", to, "--subject", subject, "--body", body, "--json"], 30000);
        try { const j = JSON.parse(out); return j.id || j.messageId || ""; } catch { return ""; }
      },
      search(query) {
        const d = JSON.parse(run(["gmail", "search", query, "-j"], 30000));
        return (d.threads || d.messages || d || []).map((t) => ({ id: t.id, subject: t.subject || "" }));
      },
      getBody(id) {
        const d = JSON.parse(run(["gmail", "get", id, "-j"], 30000));
        const subject = (d.headers && (d.headers.subject || d.headers.Subject)) || d.subject || "";
        return { subject, body: d.body || "" };
      },
    },
  };
}

// CLOUD implementation: same interface, OAuth per user. Wired in the web-app workstream (#49).
function composioTransport() {
  const nyi = () => { throw new Error("composio transport not wired yet (#49 web app)"); };
  return { calendar: { list: nyi, updateLocation: nyi }, mail: { send: nyi, search: nyi, getBody: nyi } };
}

function makeTransport(cfg = {}) {
  const kind = (process.env.LIFE_TRANSPORT || cfg.kind || "gog").toLowerCase();
  return kind === "composio" ? composioTransport(cfg) : gogTransport(cfg);
}

module.exports = { makeTransport, gogTransport, composioTransport };
```

### WS1.2 — `~/anicca/skills/life/planner.js` (rewire listEvents → adapter)

```diff
@@ planner.js: after ENV/const block (lines 23-28) @@
 const ENV = loadEnv();
 const GOG_BIN = "/opt/homebrew/bin/gog";
 const GOG_ACCOUNT = process.env.GOG_ACCOUNT || ENV.GOG_ACCOUNT || "keiodaisuke@gmail.com";
+const { makeTransport } = require("./adapters/transport");
+const CAL = makeTransport({
+  bin: GOG_BIN,
+  account: GOG_ACCOUNT,
+  keyring: process.env.GOG_KEYRING_PASSWORD || ENV.GOG_KEYRING_PASSWORD || "",
+}).calendar;
 const OPENCLAW = process.env.OPENCLAW_BIN || "openclaw";
```

```diff
@@ planner.js lines 46-56: replace gogEnv()+listEvents() internals @@
-function gogEnv() { return { ...process.env, GOG_KEYRING_PASSWORD: process.env.GOG_KEYRING_PASSWORD || ENV.GOG_KEYRING_PASSWORD || "", GOG_ACCOUNT }; }
 function listEvents() {
   const to = new Date(Date.now() + HORIZON_DAYS * 864e5).toISOString().slice(0, 10);
-  let out = "";
-  try {
-    out = execFileSync(GOG_BIN, ["calendar", "events", "list", "-j", "--account", GOG_ACCOUNT, "--from", "today", "--to", to, "--all-pages", "--max", "250"], { env: gogEnv(), encoding: "utf8", timeout: 60000 });
-  } catch (e) { console.error("[plan] gog list failed:", e.message); return []; }
-  let d; try { d = JSON.parse(out); } catch { return []; }
-  const items = Array.isArray(d) ? d : (d.events || d.items || []);
+  let items;
+  try { items = CAL.list({ from: "today", to, max: 250 }); }
+  catch (e) { console.error("[plan] gog list failed:", e.message); return []; }
   return items.map((e) => ({ id: e.id, summary: e.summary || "", location: e.location || "", start: e.start || {}, end: e.end || {} }));
 }
```

Note: `execFileSync` is still imported+used by `existingJobNames()`/`registerAt()` (openclaw cron). `GOG_BIN`/`GOG_ACCOUNT` now feed the adapter. No other call site changes.

### WS1.3 — `~/anicca/skills/life/ask/ask-local.js` (rewire 4 gog fns → adapter)

```diff
@@ ask-local.js lines 26-33: replace GOG consts + gogEnv with adapter @@
 const ENV = loadEnv();
-const GOG_BIN = "/opt/homebrew/bin/gog";
 const GOG_ACCOUNT = process.env.GOG_ACCOUNT || ENV.GOG_ACCOUNT || "keiodaisuke@gmail.com";
 const DAIS_EMAIL = process.env.DAIS_EMAIL || ENV.DAIS_EMAIL || "keiodaisuke@gmail.com";
 const QUEUE = process.env.LIFE_ASK_QUEUE || path.join(HOME, ".openclaw", "state", "life-ask-queue.jsonl");
 const TRAVEL_STATE = path.join(HOME, ".openclaw", "skills", "anicca-travel-fill", "state", "travel_filled.json");
-function gogEnv() {
-  return { ...process.env, GOG_KEYRING_PASSWORD: process.env.GOG_KEYRING_PASSWORD || ENV.GOG_KEYRING_PASSWORD || "", GOG_ACCOUNT };
-}
+const CAL_ID = process.env.LIFE_CAL_ID || ENV.GCAL_ID || "primary";
+const { makeTransport } = require("../adapters/transport");
+const T = makeTransport({
+  account: GOG_ACCOUNT,
+  keyring: process.env.GOG_KEYRING_PASSWORD || ENV.GOG_KEYRING_PASSWORD || "",
+  calId: CAL_ID,
+});
```

```diff
@@ ask-local.js lines 71-99: delete the 4 gog* helpers + old CAL_ID line (now via T) @@
-function gogSend({ to, subject, body }) {
-  const out = execFileSync(GOG_BIN, ["gmail", "send", "--account", GOG_ACCOUNT, "--to", to, "--subject", subject, "--body", body, "--json"],
-    { env: gogEnv(), encoding: "utf8", timeout: 30000 });
-  try { const j = JSON.parse(out); return j.id || j.messageId || ""; } catch { return ""; }
-}
-function gogSearchReplyThreads() {
-  try {
-    const out = execFileSync(GOG_BIN, ["gmail", "search", `from:${DAIS_EMAIL} subject:"[ASK-" newer_than:7d`, "-j", "--account", GOG_ACCOUNT],
-      { env: gogEnv(), encoding: "utf8", timeout: 30000 });
-    const d = JSON.parse(out);
-    return (d.threads || d.messages || d || []).map((t) => ({ id: t.id, subject: t.subject || "" }));
-  } catch { return []; }
-}
-function gogGetBody(id) {
-  try {
-    const out = execFileSync(GOG_BIN, ["gmail", "get", id, "-j", "--account", GOG_ACCOUNT], { env: gogEnv(), encoding: "utf8", timeout: 30000 });
-    const d = JSON.parse(out);
-    const subject = (d.headers && (d.headers.subject || d.headers.Subject)) || d.subject || "";
-    return { subject, body: d.body || "" };
-  } catch { return { subject: "", body: "" }; }
-}
-const CAL_ID = process.env.LIFE_CAL_ID || ENV.GCAL_ID || "primary";
-function setEventLocation(eventId, location) {
-  try {  // gog calendar update needs <calendarId> <eventId> — two positionals
-    execFileSync(GOG_BIN, ["calendar", "update", CAL_ID, eventId, "--location", location, "-j", "--account", GOG_ACCOUNT],
-      { env: gogEnv(), encoding: "utf8", timeout: 30000 });
-    return true;
-  } catch (e) { console.error("[ask] setEventLocation failed:", e.message); return false; }
-}
+function gogSend({ to, subject, body }) { return T.mail.send({ to, subject, body }); }
+function gogSearchReplyThreads() {
+  try { return T.mail.search(`from:${DAIS_EMAIL} subject:"[ASK-" newer_than:7d`); } catch { return []; }
+}
+function gogGetBody(id) { try { return T.mail.getBody(id); } catch { return { subject: "", body: "" }; } }
+function setEventLocation(eventId, location) {
+  try { return T.calendar.updateLocation(eventId, location); }
+  catch (e) { console.error("[ask] setEventLocation failed:", e.message); return false; }
+}
```

Also drop the now-unused `execFileSync` import at line 12 IF no other use remains (verify: ask-local.js has no other execFileSync after this patch → remove `const { execFileSync } = require("node:child_process");`).

### WS1 verification (no-mock, run BY OpenClaw)
- `node --test skills/life/ask/__tests__/test-ask-local.js` → 6/6 still green (pure fns untouched).
- `node --test skills/life/__tests__/test-planner.js` → 4/4 green.
- `LIFE_TRANSPORT=gog node planner.js --dry-run` via `openclaw cron run` → prints `{action:plan,...}` (real gcal list through adapter).
- `LIFE_TRANSPORT=composio node planner.js --dry-run` → throws the explicit NYI (proves selector works, cloud not silently faked).

---

## WS2..WS8 — written + reviewed in order AFTER WS1 ok:true
WS1b travel_fill.py adapter · WS2 agentic location/ask (#47) · WS3 repo extraction (#48) · WS4 /life-manager→GitHub link (#52) · WS5 natural call VAD+affective (#43) · WS6 web app flow + cloud wake (#49) · WS7 demo-reel cron→@anicca.comedy (#50) · WS8 launch PH+X (#51). Each gets its own complete diff section here, each reviewed, none started before its predecessor passes.
