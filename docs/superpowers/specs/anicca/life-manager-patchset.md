# Life Manager — VCSDD Patchset (line-by-line, reviewed BEFORE implementation)

Dais 2026-06-18: "write the complete line by line +- patches… then get reviewed… too worried to go when things aren't cleared."

Rule: **one workstream at a time, COMPLETE real diffs grounded in current code, code-reviewer → ok:true, THEN next.** No mega-fake dump. Dependency order: WS1 (adapter) defines the file boundaries every later patch builds on.

### STATUS
- **WS1 + WS1b — ✅ IMPLEMENTED & VERIFIED (2026-06-18)**. Reviewed ok:true ×2. anicca commit `52f0851`.
  - 34/34 unit tests green (planner 4, ask 6, notify-logic 20, motion-gate 4; travel pytest 9).
  - **OpenClaw gateway E2E** (live runtime, no-mock): `gog planner real gcal → {"action":"plan","events":28}`; composio selector throws "not wired yet (#49)" in BOTH JS and Python (no silent fake). Log: `~/.openclaw/state/ws1-adapter-e2e.log`.
- WS2..WS8 — pending (next: WS2 agentic location/ask).

Source of truth for current code: `~/anicca/skills/life/` (read in full for each diff).

---

## WS1 — Transport adapter (the ONLY local↔cloud difference)  ✅ REVIEW PASSED (code-reviewer ok:true, 2026-06-18, after argv-equivalent doc fix + gog 0.17.0 empirical proof)

**Goal**: every consumer (planner / ask / notify / travel) talks to `calendar.*` / `mail.*`, never `gog` directly. `LIFE_TRANSPORT=gog` (local, user keys) | `composio` (cloud, we manage keys). Same core code both sides. **Invariant = argv-EQUIVALENT** (not literally byte-identical): the adapter appends `--account` last uniformly; gog flags are order-independent (verified gog 0.17.0, see adapter comment).

**Caveat (Finding 9)**: WS1-v1 migrates only `planner.js` + `ask-local.js`. `notify.js` + `travel_fill.py` keep their own gog calls until WS1-v2 → so `LIFE_TRANSPORT=composio` is NOT end-to-end selectable until WS1-v2 lands (a half-cloud state is reachable but unused). Local `gog` path is fully consistent throughout.

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
  // every gog call ends with --account <account>. NOTE: this is argv-EQUIVALENT, not byte-identical:
  // the adapter appends --account last uniformly, whereas current call sites place it mid-argv on
  // `calendar list` and `gmail send`. gog flags are order-independent — VERIFIED on gog 0.17.0:
  //   `gog calendar events list -j --from today --all-pages --max 1 --account <acct>` → exit 0 + valid JSON.
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

## WS1b — Python adapter (travel_fill.py) + notify.js migration  ✅ REVIEW PASSED (code-reviewer ok:true, 2026-06-18; 2 NON-BLOCKING clarity items folded in: CAL placement split into Hunk A/B, execFileSync removal made definitive)

Completes the adapter migration so ALL four consumers go through the transport boundary. Same invariant: argv-EQUIVALENT (gog order-independent, verified gog 0.17.0). Grounded in full reads of `travel/travel_fill.py` (gog at :111 list, :225 create) and `notify/notify.js` (gog at :269 list, :287 send, :298 search, :309 getBody).

**Intentional argv ADDITIONS when notify migrates (pre-flagged by reviewer Finding 10, safe):**
- `mail.send` adds `--json` (notify's old send omitted it). notify ignores the return → harmless.
- `calendar.list` adds `--max 250` (notify's old list omitted --max). A single-day window never exceeds 250 → safe cap.

### WS1b.1 — NEW FILE `~/anicca/skills/life/adapters/transport.py`

```python
"""Life Manager transport adapter — Python sibling of adapters/transport.js.
LIFE_TRANSPORT=gog (local, user keys) | composio (cloud, wired in #49).
Consumers call calendar.list/create — never subprocess gog directly. argv-EQUIVALENT
to current call sites (gog flags order-independent, verified gog 0.17.0)."""
import json
import os
import subprocess

GOG_BIN = "/opt/homebrew/bin/gog"


class _GogCalendar:
    def __init__(self, account, keyring):
        self.account = account
        self._env = {**os.environ, "GOG_KEYRING_PASSWORD": keyring or "", "GOG_ACCOUNT": account}

    def _run(self, args, timeout=60):
        return subprocess.run([GOG_BIN, *args, "--account", self.account],
                              capture_output=True, text=True, env=self._env, timeout=timeout)

    def list(self, frm="today", to=None, max=250):
        args = ["calendar", "events", "list", "-j", "--from", frm, "--all-pages", "--max", str(max)]
        if to:
            args += ["--to", to]
        out = self._run(args)
        if out.returncode != 0:
            raise RuntimeError(f"gog list failed: {out.stderr[:200]}")
        d = json.loads(out.stdout)
        return d if isinstance(d, list) else d.get("events", d.get("items", []))

    def create(self, summary, frm, to, location, description, calendar="primary"):
        out = self._run(["calendar", "create", calendar, "-j",
                         "--summary", summary, "--from", frm, "--to", to,
                         "--location", location, "--description", description], timeout=30)
        if out.returncode != 0:
            raise RuntimeError(f"gog create failed: {out.stderr[:200]}")
        try:
            return json.loads(out.stdout)["event"]["id"]
        except Exception:
            return None


class _NyiCalendar:
    def list(self, *a, **k):
        raise RuntimeError("composio transport not wired yet (#49 web app)")

    def create(self, *a, **k):
        raise RuntimeError("composio transport not wired yet (#49 web app)")


def make_transport(account, keyring="", kind=None):
    kind = (kind or os.environ.get("LIFE_TRANSPORT", "gog")).lower()
    cal = _NyiCalendar() if kind == "composio" else _GogCalendar(account, keyring)
    return type("Transport", (), {"calendar": cal})()
```

### WS1b.2 — `travel/travel_fill.py` (rewire fetch_events + insert_travel_event)

Hunk A — top of file: add the adapter import ONLY (no construction here — `env`/`prof` aren't defined at module top yet).
```diff
@@ travel_fill.py lines 21-22: after the prof import @@
 sys.path.insert(0, str(Path.home() / ".openclaw" / "skills" / "_shared"))
 import anicca_profile as prof  # noqa: E402
+sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "adapters"))
+import transport as _t  # noqa: E402
```

Hunk B — immediately ABOVE `def fetch_events` (line 108): build CAL HERE, where `env()` and `prof` already exist (this is the correct placement; do NOT put it at module top → NameError).
```diff
@@ travel_fill.py line 108: directly above `def fetch_events` @@
+CAL = _t.make_transport(
+    account=env("GOG_ACCOUNT") or prof.google_account(),
+    keyring=env("GOG_KEYRING_PASSWORD"),
+).calendar
+
 def fetch_events(days):
-    acct = env("GOG_ACCOUNT") or prof.google_account()
     to = (datetime.now(JST) + timedelta(days=days)).strftime("%Y-%m-%d")
-    out = subprocess.run(
-        ["/opt/homebrew/bin/gog", "calendar", "events", "list", "-j",
-         "--account", acct, "--from", "today", "--to", to,
-         "--all-pages", "--max", "250"],
-        capture_output=True, text=True,
-        env={**os.environ, "GOG_KEYRING_PASSWORD": env("GOG_KEYRING_PASSWORD"),
-             "GOG_ACCOUNT": acct},
-        timeout=60,
-    )
-    if out.returncode != 0:
-        print(f"[fill] gog failed: {out.stderr[:200]}", file=sys.stderr)
-        return []
-    d = json.loads(out.stdout)
-    items = d if isinstance(d, list) else d.get("events", d.get("items", []))
+    try:
+        items = CAL.list(frm="today", to=to, max=250)
+    except Exception as e:
+        print(f"[fill] gog failed: {e}", file=sys.stderr)
+        return []
     rows = []
     for e in items:
```

```diff
@@ travel_fill.py lines 221-244: insert_travel_event uses CAL.create @@
 def insert_travel_event(start_dt, end_dt, src, dst, dst_addr):
     summary = f"🚆 移動 {short_name(src)}→{short_name(dst)}"
     desc = "Auto-inserted by anicca-travel-fill. Adjust if route is wrong."
-    acct = env("GOG_ACCOUNT") or prof.google_account()
-    out = subprocess.run(
-        ["/opt/homebrew/bin/gog", "calendar", "create", "primary", "-j",
-         "--account", acct,
-         "--summary", summary,
-         "--from", start_dt.isoformat(),
-         "--to", end_dt.isoformat(),
-         "--location", dst_addr,
-         "--description", desc],
-        capture_output=True, text=True,
-        env={**os.environ, "GOG_KEYRING_PASSWORD": env("GOG_KEYRING_PASSWORD"),
-             "GOG_ACCOUNT": acct},
-        timeout=30,
-    )
-    if out.returncode != 0:
-        print(f"[fill] insert failed: {out.stderr[:200]}", file=sys.stderr)
-        return None
-    try:
-        return json.loads(out.stdout)["event"]["id"]
-    except Exception:
-        return None
+    try:
+        return CAL.create(summary=summary, frm=start_dt.isoformat(), to=end_dt.isoformat(),
+                          location=dst_addr, description=desc)
+    except Exception as e:
+        print(f"[fill] insert failed: {e}", file=sys.stderr)
+        return None
```
After this, `import subprocess` (line 14) is unused in travel_fill.py → remove it (the adapter owns subprocess). Verify no other subprocess use remains (grep: only :111 and :225 today → both gone).

### WS1b.3 — `notify/notify.js` (rewire to the WS1 JS adapter)

```diff
@@ notify.js: after the GOG consts (lines 61-63), build the adapter @@
 const GOG_KEYRING_PASSWORD = process.env.GOG_KEYRING_PASSWORD || ENV.GOG_KEYRING_PASSWORD || "";
+const { makeTransport } = require("../adapters/transport");
+const T = makeTransport({ bin: GOG_BIN, account: GOG_ACCOUNT, keyring: GOG_KEYRING_PASSWORD });
```

```diff
@@ notify.js lines 261-317: replace gogEnv + 4 gog fns with adapter-backed wrappers @@
-function gogEnv() {
-  return { ...process.env, GOG_KEYRING_PASSWORD, GOG_ACCOUNT };
-}
-function listTodayEvents() {
-  const today = new Date().toISOString().slice(0, 10);
-  const raw = execFileSync(GOG_BIN, [
-    "calendar", "events", "list",
-    "-j",
-    "--account", GOG_ACCOUNT,
-    "--from", today,
-    "--to", today,
-    "--all-pages",
-  ], { env: gogEnv(), timeout: 60000 }).toString();
-
-  const d = JSON.parse(raw);
-  return Array.isArray(d) ? d : (d.events || d.items || []);
-}
+function listTodayEvents() {
+  const today = new Date().toISOString().slice(0, 10);
+  return T.calendar.list({ from: today, to: today, max: 250 });   // +--max 250 (safe; 1-day window)
+}
-function gogGmailSend({ to, subject, body }) {
-  execFileSync(GOG_BIN, [
-    "gmail", "send",
-    "--account", GOG_ACCOUNT,
-    "--to", to,
-    "--subject", subject,
-    "--body", body,
-  ], { env: gogEnv(), timeout: 60000 });
-}
+function gogGmailSend({ to, subject, body }) { T.mail.send({ to, subject, body }); }  // +--json (return ignored)
-function gogGmailSearch(query) {
-  const raw = execFileSync(GOG_BIN, [
-    "gmail", "search", query,
-    "-j",
-    "--account", GOG_ACCOUNT,
-  ], { env: gogEnv(), timeout: 60000 }).toString();
-  const d = JSON.parse(raw);
-  return Array.isArray(d.threads) ? d.threads : [];
-}
+function gogGmailSearch(query) { return T.mail.search(query); }   // [{id,subject}]; callers use .id only
-function gogGmailBody(threadId) {
-  const raw = execFileSync(GOG_BIN, [
-    "gmail", "get", threadId,
-    "-j",
-    "--account", GOG_ACCOUNT,
-  ], { env: gogEnv(), timeout: 60000 }).toString();
-  const d = JSON.parse(raw);
-  return typeof d.body === "string" ? d.body : "";
-}
+function gogGmailBody(threadId) { return T.mail.getBody(threadId).body; }  // unwrap to STRING (prior contract)
```
Caller-contract checks (must hold): `listTodayEvents()` returns event items[] (unchanged); `gogGmailSearch` callers use `t.id` only (adapter returns `{id,subject}` — OK); `gogGmailBody` callers expect a STRING (wrapper returns `.body` — OK); `gogGmailSend` return ignored (OK). **`execFileSync` removal (DEFINITIVE)**: grep confirms notify.js used `execFileSync` ONLY in the 4 replaced fns (`:271/:288/:299/:310`) — after this rewire it is unused, so REMOVE the import `const { execFileSync } = require("child_process");` at notify.js:37. (Reviewer-verified: no other use.)

### WS1b verification (no-mock, BY OpenClaw)
- `python3 -m pytest`/`node --test` on travel + notify test files → unchanged green (pure fns untouched).
- `LIFE_TRANSPORT=gog python3 travel/travel_fill.py` via `openclaw cron run` → real gcal list through adapter, prints summary JSON.
- `LIFE_TRANSPORT=composio python3 travel/travel_fill.py` → raises NYI (selector proven, no silent fake).
- `LIFE_TRANSPORT=gog node notify/notify.js --poll` → real Gmail search/get/send through adapter.

---

## WS3 — SELF-CONTAINED single repo (zero ~/.openclaw / anicca_profile dependency)

Dais 2026-06-18: "everything of Life Manager in ONE repo. OpenClaw is just an executor, nothing else. no dependency. confined in one clean repo. so people can manage their life anywhere — local OR cloud (cloud = paid sub)."

**Grounded dependency inventory (grep of the staged tree ~/life-manager):**
| dep | files:line |
|---|---|
| `~/.openclaw/.env` | planner.js:19, ask-local.js:15, notify.js:47, call/call.js:44, travel_fill.py:26, travel.js:35 |
| `~/.openclaw/state/*` | ask-local.js:27 (ask-queue), notify.js:87 (notify-pending), call/call.js:78 (call.log), locate.js:46 (location), travel_fill.py:250 (ask-queue) |
| `~/.openclaw/skills/anicca-travel-fill/state` | ask-local.js:28 (travel_filled) — also INCONSISTENT with travel_fill.py state path (pre-existing bug; fixed by unifying on DATA_DIR) |
| `anicca_profile` (prof.*) | travel_fill.py:21,95,110 — the only hard external import |
| `/opt/homebrew/bin/gog` | transport.js:9, transport.py:9, planner.js:24, notify.js:43, travel.js:32 |
| `openclaw` / `cloudflared` bin | planner.js:32, runner-telnyx.mjs:133 |

**Keystone = repo-local `config.{js,py}`** (same idea as the adapter): ONE place resolves env, data dir, profile, bins. Nothing reaches into `~/.openclaw`. Defaults are repo-portable; everything overridable by env (so cloud injects its own).
- env: `LIFE_ENV_FILE` → else repo-local `./.env` → else process.env.
- data dir: `LIFE_DATA_DIR` → else `~/.life-manager/` (NOT ~/.openclaw). All state files live here.
- profile: `LIFE_HOME_ADDRESS` / `LIFE_GOOGLE_ACCOUNT` / `LIFE_OWNER_EMAIL` / `LIFE_PHONE` (replaces anicca_profile).
- bins: `GOG_BIN` (default `gog` on PATH), `LIFE_SCHEDULER_BIN` (default `openclaw` — the executor), `CLOUDFLARED_BIN`.

### WS3.1 — NEW FILE `config.js` (repo root)
```js
"use strict";
// Self-contained config for Life Manager. ONE place resolves env, data dir, profile, bins.
// No dependency on ~/.openclaw or any host layout — runs anywhere (local OR cloud).
const fs = require("node:fs");
const path = require("node:path");
const os = require("node:os");

function loadEnv() {
  const out = {};
  const file = process.env.LIFE_ENV_FILE || path.join(__dirname, ".env");
  let raw = ""; try { raw = fs.readFileSync(file, "utf8"); } catch { return out; }
  for (const line of raw.split("\n")) {
    const m = line.match(/^(?:export\s+)?([A-Z_][A-Z0-9_]*)=(.*)$/);
    if (m) out[m[1]] = m[2].replace(/^["']|["']$/g, "");
  }
  return out;
}
const ENV = loadEnv();
function env(k, d = "") { return process.env[k] || ENV[k] || d; }

const DATA_DIR = process.env.LIFE_DATA_DIR || path.join(os.homedir(), ".life-manager");
function dataPath(...p) {
  const f = path.join(DATA_DIR, ...p);
  fs.mkdirSync(path.dirname(f), { recursive: true });
  return f;
}
const profile = {
  account: () => env("GOG_ACCOUNT") || env("LIFE_GOOGLE_ACCOUNT"),
  ownerEmail: () => env("LIFE_OWNER_EMAIL") || env("GOG_ACCOUNT") || env("LIFE_GOOGLE_ACCOUNT"),
  homeAddress: () => env("LIFE_HOME_ADDRESS"),
  phone: () => env("LIFE_PHONE"),
  calId: () => env("LIFE_CAL_ID") || env("GCAL_ID", "primary"),
};
const bins = {
  gog: () => env("GOG_BIN", "gog"),
  scheduler: () => env("LIFE_SCHEDULER_BIN", "openclaw"),
  cloudflared: () => env("CLOUDFLARED_BIN", "cloudflared"),
};
module.exports = { ENV, env, DATA_DIR, dataPath, profile, bins };
```

### WS3.2 — NEW FILE `config.py` (repo root)
```python
"""Self-contained config for Life Manager (Python sibling of config.js).
No dependency on ~/.openclaw or anicca_profile — runs anywhere (local OR cloud)."""
import os
from pathlib import Path

_ROOT = Path(__file__).resolve().parent


def _load_env():
    out = {}
    f = Path(os.environ.get("LIFE_ENV_FILE", _ROOT / ".env"))
    try:
        raw = f.read_text()
    except OSError:
        return out
    import re
    for line in raw.splitlines():
        m = re.match(r"^(?:export\s+)?([A-Z_][A-Z0-9_]*)=(.*)$", line)
        if m:
            out[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return out


ENV = _load_env()


def env(k, d=""):
    return os.environ.get(k) or ENV.get(k, d)


DATA_DIR = Path(os.environ.get("LIFE_DATA_DIR", Path.home() / ".life-manager"))


def data_path(*p):
    f = DATA_DIR.joinpath(*p)
    f.parent.mkdir(parents=True, exist_ok=True)
    return f


def home_address():
    return env("LIFE_HOME_ADDRESS")


def google_account():
    return env("GOG_ACCOUNT") or env("LIFE_GOOGLE_ACCOUNT")
```

### WS3.3 — per-file rewires (replace inline host deps with config)
| file | current | → becomes |
|---|---|---|
| planner.js:17-23 | inline `loadEnv()` reading `~/.openclaw/.env` | `const C = require("./config"); const ENV = C.ENV;` (drop inline loader) |
| planner.js:24 | `GOG_BIN="/opt/homebrew/bin/gog"` | `const GOG_BIN = C.bins.gog();` |
| planner.js:32 | `OPENCLAW=...|| "openclaw"` | `const OPENCLAW = C.bins.scheduler();` |
| ask-local.js:14-24 | inline loadEnv `~/.openclaw/.env` | `const C = require("./config")` (ask/ is a subdir → `require("../config")`) |
| ask-local.js:27 | QUEUE `~/.openclaw/state/life-ask-queue.jsonl` | `C.dataPath("life-ask-queue.jsonl")` |
| ask-local.js:28 | TRAVEL_STATE `~/.openclaw/skills/anicca-travel-fill/state/travel_filled.json` | `C.dataPath("travel_filled.json")` (now unified with travel_fill) |
| notify.js:45-57 | inline loadEnv | `const C = require("../config")` |
| notify.js:87 | pending `~/.openclaw/state/life-notify-pending.jsonl` | `C.dataPath("life-notify-pending.jsonl")` |
| notify.js:43 | GOG_BIN homebrew | `C.bins.gog()` |
| notify.js OWNER_EMAIL | `~/.openclaw` account | `C.profile.ownerEmail()` |
| locate.js:46 | location `~/.openclaw/state/location` | `C.dataPath("location")` (require `../config`) |
| call/call.js:42-50 | loadOpenclawEnv | `const C = require("../config")` (keeps merging into process.env for the runner) |
| call/call.js:78 | log `~/.openclaw/state/life-call.log` | `C.dataPath("life-call.log")` |
| travel/travel_fill.py:20-21 | `sys.path … _shared` + `import anicca_profile as prof` | `import config as C` (add `sys.path.insert(0, parent)`) — DELETE anicca_profile |
| travel/travel_fill.py:26 | `ENV = (~/.openclaw/.env).read_text()` + `env()` regex | use `C.env(...)` |
| travel/travel_fill.py:95 | `prof.home_address()` | `C.home_address()` |
| travel/travel_fill.py:110 | `prof.google_account()` | `C.google_account()` |
| travel/travel_fill.py:250 | ASK_QUEUE `~/.openclaw/state/...` | `C.data_path("life-ask-queue.jsonl")` |
| travel/travel_fill.py STATE_FILE | skill-local `../state/travel_filled.json` | `C.data_path("travel_filled.json")` (unify) |
| adapters/transport.js:9 | `bin="/opt/homebrew/bin/gog"` | `bin = process.env.GOG_BIN || "gog"` |
| adapters/transport.py:9 | `GOG_BIN="/opt/homebrew/bin/gog"` | `GOG_BIN = os.environ.get("GOG_BIN","gog")` |
| call/lib/runner-telnyx.mjs:133 | cloudflared homebrew | already `process.env.CLOUDFLARED_BIN || ...` — change fallback to `"cloudflared"` |

### WS3.4 — dead-code removal (coding-style: delete unused)
- `travel/travel.js` — superseded by `travel_fill.py` (the wired one); its own gog/env path. Confirm not referenced by any cron, then DELETE (don't ship two travel impls).

### WS3.5 — repo hygiene + portability
- Add `SKILL.md` (OpenClaw manifest), `README.md` (EN+JA: install into OpenClaw, env vars, local vs cloud), `.env.example` (all LIFE_* + provider keys), `.gitignore` (`.env`, `node_modules`, `__pycache__`, `state/`).
- `call/lib` needs `ws`; document `cd call/lib && npm i` in README/install.

### WS3.6 — extraction + rewire (executor only) — AFTER code is self-contained + reviewed
1. `gh repo create Daisuke134/life-manager --public` (or private until de-personalized; flip after).
2. push the self-contained tree.
3. Rewire the live OpenClaw crons (executor) — change exec path `$HOME/anicca/skills/life/X` → `$HOME/life-manager/X`, inject config via env (`LIFE_DATA_DIR`, `LIFE_ENV_FILE=$HOME/.openclaw/.env` for Dais's local so keys/profile resolve). Static crons: `anicca-life-plan`, `anicca-life-ask`, `anicca-life-notify-scan`, `anicca-life-notify-poll`. The `life-call-*` crons are regenerated by planner (new `__dirname`) → delete stale + re-run plan.
4. `git rm -r skills/life` from anicca repo; commit + push.

### WS3.7 — verification (vcsdd E2E, proves ZERO ~/.openclaw dependency)
- Run from the clean repo with a TEMP data dir and NO ~/.openclaw access path:
  `LIFE_DATA_DIR=/tmp/lm-test LIFE_ENV_FILE=/tmp/lm-test/.env GOG_BIN=$(command -v gog) node ~/life-manager/planner.js --dry-run` → lists real gcal, writes state ONLY under /tmp/lm-test (assert nothing written to ~/.openclaw).
- `grep -rn "\.openclaw\|anicca_profile" ~/life-manager` (excl node_modules) → **0 hits** = self-contained proven.
- composio throws (JS+Py). 34/34 unit tests green from new location.
- OpenClaw executor E2E: fire `anicca-life-plan` (rewired) → real gcal → regenerates life-call crons at new path.

## WS2 / WS4..WS8 — written + reviewed in order AFTER WS3 ok:true
WS1b travel_fill.py adapter · WS2 agentic location/ask (#47) · WS3 repo extraction (#48) · WS4 /life-manager→GitHub link (#52) · WS5 natural call VAD+affective (#43) · WS6 web app flow + cloud wake (#49) · WS7 demo-reel cron→@anicca.comedy (#50) · WS8 launch PH+X (#51). Each gets its own complete diff section here, each reviewed, none started before its predecessor passes.
