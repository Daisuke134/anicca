# Patch: life-ask (B-ask) — email round-trip to fill unknown gcal location/duration

Spec: `docs/superpowers/specs/anicca/27-launch-workflow-and-ubi.md` §2 WF-B **B-ask** (line 28)
+ `docs/superpowers/specs/anicca/07-life-manager.md`.

Spec verbatim (27 line 28):
> **B-ask**: 所要/場所が不明なら `skills/life/ask.js` が Dais の Gmail に質問メールを送り、返信内容で gcal の where を補完(AgentMail inbound webhook 駆動)。…検証 agent = 質問メール着信→返信→gcal 補完を確認。

Audited files (RAW evidence):
- `~/anicca/skills/life/ask.js` — thin shim → `require("./ask/ask")`.
- `~/anicca/skills/life/ask/ask.js` — CLI wrapper that POSTs `https://aniccaai.com/.netlify/functions/life-ask?action=<action>`. No business logic, no mail. **Must be rewritten to do the local `gog` send.**
- `apps/landing/netlify/functions/life-ask.js` — current canonical impl. `question` (scan GCal → send via AgentMail) + `reply` (parse inbound webhook → patch GCal).
- `apps/landing/netlify/functions/_lib/ask-logic.js` — pure logic.
- `apps/landing/netlify/functions/_lib/gcal-token.js` — `getAccessToken()`.
- `~/.openclaw/cron/jobs.json` — job `anicca-life-ask` (id `891b90bb…`), cron `0 21 * * *` (06:00 JST), runs `node $HOME/anicca/skills/life/ask/ask.js --action question`.
- Proven `gog gmail send` pattern: `~/anicca/skills/anicca-life-manager/scripts/renraku.py:58-65` — `["/opt/homebrew/bin/gog","gmail","send","--account",gog_account(),"--to",..,"--subject",..,"--body",..]` with `env={**os.environ,"GOG_KEYRING_PASSWORD":env("GOG_KEYRING_PASSWORD")}`.
- `~/.openclaw/.env` has `GOG_ACCOUNT`, `GOG_KEYRING_PASSWORD`, `GOOGLE_LOGIN_EMAIL` PRESENT (grep, names only).

---

## Architecture decision (settled — resolves runtime gap)

`gog` is a **Mac-mini-only binary** (`/opt/homebrew/bin/gog`) and CANNOT run inside a Netlify lambda. Therefore:

| Concern | Runtime | Why |
|---|---|---|
| GCal read (list today) + patch (location/end) | **Netlify** `life-ask.js` | OAuth via `gcal-token.js`; already there. |
| Mail **send** (question email) | **Local** `ask/ask.js` (Mac-mini) | `gog` lives here; no AgentMail quota. |
| Inbound reply intake | AgentMail webhook → Netlify `?action=reply` (GCal patch only) | parse + patch is GCal-only, fine on Netlify. |

So `?action=question` on Netlify becomes **GCal-read-only**: it returns the list of events that need asking (+ the pre-built subject/body/pending-patch), and the **local `ask/ask.js`** sends each email via `gog` and then calls Netlify `?action=mark-asked` to set the pending flag. This keeps the only mutation that needs `gog` on the Mac-mini.

---

## Gaps

| # | Required (spec) | Exists today | Gap | Evidence |
|---|---|---|---|---|
| G1 | Send via `gog gmail send` (AGENTMAIL daily-limited) | `handleQuestion` sends via AgentMail INSIDE Netlify | gog can't run on Netlify → send must move to local `ask/ask.js`. | life-ask.js:93-108; renraku.py:58-65 |
| G2 | Inbound reply → gcal `where` update | `handleReply` parses webhook, patches `location` | Exists + wired (webhook `ep_3FBcXGwrcP575GjLm46jCMj2TYr`); only `location`, never duration. | life-ask.js:158-219 |
| G3 | Detect/parse **unknown duration** ("所要") | none | `needsLocationAsk` only checks empty `location`; no duration. | ask-logic.js:31-41 |
| G4 | GCal env present **in the Netlify lambda** (every action calls `getAccessToken()` first → absent = 500 `auth_error`) | **CONFIRMED SET** via `netlify env:list --json` (linked site `d67537f0-21bd-477e-ac1a-323f7ec6d5cd`): `GCAL_ID=primary`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN` ALL present. | NO GAP — satisfied prereq, not a blocker. (Local `~/.openclaw/.env` does NOT need these; the Netlify lambda reads its own env. The local sender needs only `GOG_*`, which are present.) | `netlify env:list --json` (run in apps/landing); gcal-token.js:27-37; life-ask.js:240-245 |
| G5 | DURATION_RE cross-module reference | — | If guard uses `DURATION_RE` in `handleReply` but it's only `const` in `ask-logic.js`, that's a ReferenceError. Must export it (or inline). | (review point 3) |
| G6 | Netlify schedule removed (no dead lambda) | `netlify.toml` lines 26-27 declare `[functions."life-ask"]  schedule = "0 21 * * *"` + stale comment (17-25) describing AgentMail-send-from-Netlify | **STALE**: after the architecture change `question` is GCal-read-only and sends NO mail. A scheduled Netlify invoke = a daily lambda emailing nothing. The local cron `anicca-life-ask` (jobs.json:5710/5722) is the SOLE driver. Remove the stanza + fix the comment. | netlify.toml:17-27; jobs.json:5710,5722 |

---

## Diff

Four parts: **(P1)** duration logic in `ask-logic.js` (exports DURATION_RE — fixes G5); **(P2)** Netlify `life-ask.js` → GCal-read-only `question` + new `mark-asked` action + duration in `reply`; **(P3)** real rewrite of local `ask/ask.js` to do the `gog` send; **(P4)** remove the orphaned Netlify schedule + stale comment in `netlify.toml` (fixes G6).

### P1 — `apps/landing/netlify/functions/_lib/ask-logic.js`

```diff
@@ const ASK_PREFIX = "[Ask] ";
 const AGENTMAIL_PENDING_PROP = "anicca_ask_pending";
 const AGENTMAIL_QUESTION_ID_PROP = "anicca_ask_question_id";
+// Exported so handleReply (life-ask.js) can guard against writing a
+// duration-only reply as a bogus location. (Review point 3 — no ReferenceError.)
+const DURATION_RE = /(?:所要|duration|時間)[：:\s]*([0-9０-９]{1,3})\s*(?:分|min)/i;
```

```diff
@@ function needsLocationAsk(event) { ... unchanged ... }
+
+/** Duration unknown: no end.dateTime OR end<=start. start.dateTime required. */
+function needsDurationAsk(event) {
+  if (!event || !event.start || !event.start.dateTime) return false;
+  const summary = (event.summary || "").trim();
+  if (summary.startsWith("[Travel]") || summary.startsWith(ASK_PREFIX)) return false;
+  if (event.extendedProperties?.private?.[AGENTMAIL_PENDING_PROP] === "true") return false;
+  const endDt = event.end?.dateTime;
+  if (!endDt) return true;
+  return new Date(endDt).getTime() <= new Date(event.start.dateTime).getTime();
+}
+
+function detectAskKind(event) {
+  return { location: needsLocationAsk(event), duration: needsDurationAsk(event) };
+}
```

```diff
@@ function detectMissingLocations(events) { ... unchanged ... }
+
+/** Events needing EITHER location OR duration. Items: { event, kind }. */
+function detectMissingInfo(events) {
+  if (!Array.isArray(events)) return [];
+  return events
+    .map((event) => ({ event, kind: detectAskKind(event) }))
+    .filter(({ kind }) => kind.location || kind.duration);
+}
```

```diff
@@ function buildQuestionBody(event) {
   const title = (event.summary || "").trim() || "(no title)";
   const when = event.start?.dateTime
     ? new Date(event.start.dateTime).toLocaleString("ja-JP", { timeZone: "Asia/Tokyo" })
     : "日時不明";
-  return ( ... location-only text ... );
+  const kind = detectAskKind(event);
+  const wants = [];
+  if (kind.location) wants.push(`・場所(住所・目的地)`);
+  if (kind.duration) wants.push(`・所要時間(例: 所要 60分)`);
+  const ask = wants.length ? wants.join("\n") : `・場所(住所・目的地)`;
+  return (
+    `Anicca より確認です。\n\n` +
+    `予定「${title}」(${when})の以下が未設定です。\n${ask}\n` +
+    `そのまま返信してください。Anicca が自動でカレンダーに反映します。\n\n` +
+    `---\nEvent ID: ${event.id || "unknown"}`
+  );
 }
```

```diff
@@ function buildQuestionSubject(event) {
   const title = (event.summary || "").trim() || "(no title)";
-  return `${ASK_PREFIX}場所を教えて — ${title}`;
+  const k = detectAskKind(event);
+  const what = k.location && k.duration ? "場所と所要時間" : k.duration ? "所要時間" : "場所";
+  return `${ASK_PREFIX}${what}を教えて — ${title}`;
 }
```

```diff
@@ function parseLocationFromReply(body) { ... unchanged ... }
+
+/** Parse minutes from "所要 60分" / "duration: 90 min" / a bare "N分" line. */
+function parseDurationFromReply(body) {
+  if (!body || typeof body !== "string") return null;
+  const norm = body.replace(/[０-９]/g, (d) => "0123456789"["０１２３４５６７８９".indexOf(d)]);
+  const m =
+    norm.match(/(?:所要|duration|時間)[：:\s]*([0-9]{1,3})\s*(?:分|min)/i) ||
+    norm.match(/(?:^|\n)\s*([0-9]{1,3})\s*(?:分|min|m)\s*(?:$|\n)/i);
+  if (!m) return null;
+  const mins = parseInt(m[1], 10);
+  return Number.isFinite(mins) && mins > 0 && mins <= 1440 ? mins : null;
+}
```

```diff
@@ function buildLocationPatch(location, existingEvent) {
   ... build newPrivate ...
-  return { location, extendedProperties: { private: newPrivate } };
+  return { ...(location ? { location } : {}), extendedProperties: { private: newPrivate } };
 }
+
+/** Set end.dateTime = start + N min, optionally location, clear pending. */
+function buildResolvePatch({ location, durationMinutes }, existingEvent) {
+  const patch = buildLocationPatch(location || "", existingEvent);
+  if (durationMinutes && existingEvent?.start?.dateTime) {
+    const startMs = new Date(existingEvent.start.dateTime).getTime();
+    patch.end = {
+      dateTime: new Date(startMs + durationMinutes * 60000).toISOString(),
+      ...(existingEvent.start.timeZone ? { timeZone: existingEvent.start.timeZone } : {}),
+    };
+  }
+  return patch;
+}
```

```diff
@@ module.exports = {
   needsLocationAsk,
+  needsDurationAsk,
+  detectAskKind,
   detectMissingLocations,
+  detectMissingInfo,
   buildQuestionBody,
   buildQuestionSubject,
   parseLocationFromReply,
+  parseDurationFromReply,
   buildLocationPatch,
+  buildResolvePatch,
   buildAskPendingPatch,
   ASK_PREFIX,
+  DURATION_RE,                 // ← exported (review point 3)
   AGENTMAIL_PENDING_PROP,
   AGENTMAIL_QUESTION_ID_PROP,
 };
```

### P2 — `apps/landing/netlify/functions/life-ask.js` (GCal-only; NO gog here)

Remove the AgentMail `sendEmail` from `question`. `question` now RETURNS the events to ask (read-only). Add `mark-asked` to set the pending flag after the local sender sends. `reply` gains duration + the duration-only guard.

```diff
@@
 const {
-  detectMissingLocations,
+  detectMissingInfo,
   buildQuestionBody,
   buildQuestionSubject,
   buildAskPendingPatch,
-  buildLocationPatch,
+  buildResolvePatch,
   parseLocationFromReply,
+  parseDurationFromReply,
+  DURATION_RE,
 } = require("./_lib/ask-logic");
```

```diff
-// ── action=question handler ──────────────────────────────────────
-async function handleQuestion(token, calendarId, agentMailCfg) {
-  const events = await listTodayEvents(calendarId, token);
-  const missing = detectMissingLocations(events);
-  ... AgentMail send + patch ...
-}
+// ── action=question (GCAL-READ-ONLY) ─────────────────────────────
+// gog can't run on Netlify, so this only DETECTS and returns the
+// events to ask. The local ask/ask.js sends the mail via gog, then
+// calls action=mark-asked to set the pending flag.
+async function handleQuestion(token, calendarId) {
+  const events = await listTodayEvents(calendarId, token);
+  const missing = detectMissingInfo(events); // [{ event, kind }]
+  const toAsk = missing.map(({ event: ev }) => ({
+    eventId: ev.id,
+    eventTitle: ev.summary || "",
+    subject: buildQuestionSubject(ev),
+    body: buildQuestionBody(ev),
+  }));
+  return { statusCode: 200, body: JSON.stringify({ ok: true, checked: events.length, toAsk }) };
+}
+
+// ── action=mark-asked ─────────────────────────────────────────────
+// Called by local sender after a question email is sent.
+// Body: { eventId, messageId }
+async function handleMarkAsked(rawBody, token, calendarId) {
+  let p; try { p = typeof rawBody === "string" ? JSON.parse(rawBody) : rawBody; }
+  catch { return { statusCode: 400, body: "invalid_json" }; }
+  const { eventId, messageId } = p || {};
+  if (!eventId) return { statusCode: 400, body: "missing_event_id" };
+  let ev;
+  try { ev = await getEvent(calendarId, eventId, token); }
+  catch (err) { return { statusCode: 502, body: `gcal_get_error: ${err.message}` }; }
+  try { await patchEvent(calendarId, eventId, buildAskPendingPatch(messageId || "", ev), token); }
+  catch (err) { return { statusCode: 502, body: `gcal_patch_error: ${err.message}` }; }
+  return { statusCode: 200, body: JSON.stringify({ ok: true, eventId }) };
+}
```

```diff
@@ async function handleReply(body, token, calendarId) {
   ... extract eventId ...
-  const location = parseLocationFromReply(replyBody);
-  if (!location) return { statusCode: 422, body: "no_location_found_in_reply" };
+  // Parse location AND/OR duration.
+  let location = parseLocationFromReply(replyBody);
+  const durationMinutes = parseDurationFromReply(replyBody);
+  // Duration-only guard (review point 4): if the candidate "location" is really
+  // a duration string, don't write it as a bogus location. Catches both the
+  // prefixed form ("所要 90分", via DURATION_RE) AND a bare line ("60分" / "60 min").
+  const BARE_DURATION_RE = /^\s*\d{1,3}\s*(?:分|min)\s*$/i;
+  if (location && (DURATION_RE.test(location) || BARE_DURATION_RE.test(location))) location = null;
+  if (!location && !durationMinutes) {
+    return { statusCode: 422, body: "no_location_or_duration_in_reply" };
+  }
   ... getEvent ...
-  const patch = buildLocationPatch(location, existingEvent);
+  const patch = buildResolvePatch({ location, durationMinutes }, existingEvent);
   ... patchEvent ...
-  return { statusCode: 200, body: JSON.stringify({ ok: true, eventId, location }) };
+  return { statusCode: 200, body: JSON.stringify({ ok: true, eventId, location, durationMinutes }) };
 }
```

```diff
@@ exports.handler = async (event) => {
   ... method + action + token + calendarId ...
   if (action === "reply") return handleReply(event.body, token, calendarId);
+  if (action === "mark-asked") return handleMarkAsked(event.body, token, calendarId);
-  // Default: action=question
-  const apiKey = process.env.AGENTMAIL_API_KEY;
-  const inboxId = process.env.LIFE_ASK_INBOX_ID || process.env.AGENTMAIL_INBOX_ID;
-  const daisEmail = process.env.DAIS_EMAIL || "keiodaisuke@gmail.com";
-  if (!apiKey || !inboxId) return { statusCode: 500, body: "missing AGENTMAIL_API_KEY or LIFE_ASK_INBOX_ID" };
-  try { return await handleQuestion(token, calendarId, { apiKey, inboxId, daisEmail }); }
-  catch (err) { return { statusCode: 502, body: `ask_error: ${err.message}` }; }
+  // Default: action=question (GCal read-only; no mail here)
+  try { return await handleQuestion(token, calendarId); }
+  catch (err) { return { statusCode: 502, body: `ask_error: ${err.message}` }; }
 };
```

### P3 — `~/anicca/skills/life/ask/ask.js` (REAL rewrite: local gog sender)

Replace the pure HTTP shim with: (1) POST Netlify `?action=question` to GET the events to ask; (2) for each, `gog gmail send` from the Mac-mini; (3) POST Netlify `?action=mark-asked`. Mirrors `renraku.py:58-65` (execFile gog + `GOG_KEYRING_PASSWORD` env).

```diff
@@ "use strict";
 const path = require("path");
 const fs = require("fs");
+const { execFileSync } = require("node:child_process");

 // ... loadEnv() unchanged (parses ~/.openclaw/.env) ...
 const ENV = loadEnv();
 const SITE_URL = process.env.NETLIFY_SITE_URL || ENV.NETLIFY_SITE_URL || "https://aniccaai.com";
+const GOG_BIN = "/opt/homebrew/bin/gog";
+const GOG_ACCOUNT = process.env.GOG_ACCOUNT || ENV.GOG_ACCOUNT
+  || process.env.GOOGLE_LOGIN_EMAIL || ENV.GOOGLE_LOGIN_EMAIL || "keiodaisuke@gmail.com";
+const DAIS_EMAIL = process.env.DAIS_EMAIL || ENV.DAIS_EMAIL || "keiodaisuke@gmail.com";
+
+// gog exec env: inherit + inject keyring password (proven pattern, renraku.py:63).
+function gogEnv() {
+  return { ...process.env, GOG_KEYRING_PASSWORD: process.env.GOG_KEYRING_PASSWORD || ENV.GOG_KEYRING_PASSWORD || "" };
+}
+
+// Send one question email via gog. Returns Gmail message id (best-effort).
+function gogSend({ to, subject, body }) {
+  const out = execFileSync(
+    GOG_BIN,
+    ["gmail", "send", "--account", GOG_ACCOUNT, "--to", to, "--subject", subject, "--body", body, "--json"],
+    { env: gogEnv(), encoding: "utf8", timeout: 30000 }
+  );
+  try { const j = JSON.parse(out); return j.id || j.messageId || ""; } catch { return ""; }
+}
+
+async function postNetlify(action, body) {
+  const url = `${SITE_URL}/.netlify/functions/life-ask?action=${encodeURIComponent(action)}`;
+  const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: body || "{}" });
+  const text = await r.text();
+  let j; try { j = JSON.parse(text); } catch { j = { raw: text }; }
+  if (!r.ok || j?.ok === false) throw new Error(`netlify ${action} ${r.status}: ${text.slice(0, 200)}`);
+  return j;
+}
```

```diff
-async function main() {
-  const url = `${SITE_URL}/.netlify/functions/life-ask?action=${encodeURIComponent(action)}`;
-  ... single POST, print ...
-}
+async function main() {
+  if (action === "reply") {
+    // Manual reply test path: forward body straight to Netlify reply handler.
+    const res = await postNetlify("reply", bodyOverride || "{}");
+    console.log(JSON.stringify(res, null, 2));
+    return;
+  }
+  // action=question: GCal-read on Netlify, send locally via gog, then mark-asked.
+  const { toAsk = [], checked = 0 } = await postNetlify("question", "{}");
+  const asked = [];
+  for (const a of toAsk) {
+    let messageId = "";
+    try { messageId = gogSend({ to: DAIS_EMAIL, subject: a.subject, body: a.body }); }
+    catch (err) { asked.push({ eventId: a.eventId, error: `gog_send: ${err.message}` }); continue; }
+    try { await postNetlify("mark-asked", JSON.stringify({ eventId: a.eventId, messageId })); }
+    catch (err) { asked.push({ eventId: a.eventId, messageId, markError: err.message }); continue; }
+    asked.push({ eventId: a.eventId, eventTitle: a.eventTitle, messageId });
+  }
+  console.log(JSON.stringify({ ok: true, checked, asked }, null, 2));
+  if (asked.some((x) => x.error)) process.exit(1);
+}
```

(Keep the flat shim `~/anicca/skills/life/ask.js` as-is — it still `require("./ask/ask")`.)

### P4 — `apps/landing/netlify.toml` (remove orphaned schedule + stale comment, G6)

The local cron `anicca-life-ask` (jobs.json id `891b90bb…`, `0 21 * * *`) is now the SOLE driver: it runs `ask/ask.js`, which POSTs Netlify for GCal read and sends mail via `gog` locally. A Netlify-side schedule would invoke the lambda with the default `question` action, which is GCal-read-only and sends NOTHING → a dead daily lambda. Delete the stanza and rewrite the comment.

```diff
@@ apps/landing/netlify.toml  (lines 17-27)
-# B-ask scheduled trigger — runs daily at 06:00 JST (21:00 UTC).
-# Scans today's GCal events for missing location, emails Dais via the DEDICATED
-# B-ask inbox (LIFE_ASK_INBOX_ID = anicca-life-ask@agentmail.to) to avoid the
-# daily 429 quota contention with high-frequency "Anicca wake" report emails.
-# The action=reply path is driven by AgentMail webhook ep_3FBcXGwrcP575GjLm46jCMj2TYr
-# (client_id b-ask-reply-webhook) which POSTs to this function when Dais replies.
-# Required env: GOOGLE_REFRESH_TOKEN, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
-#               AGENTMAIL_API_KEY, LIFE_ASK_INBOX_ID (= anicca-life-ask@agentmail.to)
-# Optional env: DAIS_EMAIL (default: keiodaisuke@gmail.com), GCAL_ID
-[functions."life-ask"]
-  schedule = "0 21 * * *"
+# B-ask (life-ask) is NOT scheduled by Netlify. The local cron `anicca-life-ask`
+# (~/.openclaw/cron/jobs.json, 0 21 * * *) drives it: it runs ask/ask.js which
+# POSTs this function for GCal read (action=question) + flag set (action=mark-asked),
+# and sends the question email locally via `gog gmail send` (no Netlify-side mail).
+# This function therefore exposes ONLY on-demand actions (question / mark-asked / reply);
+# action=reply is invoked by the AgentMail inbound webhook ep_3FBcXGwrcP575GjLm46jCMj2TYr.
+# Required Netlify env (read + patch GCal): GOOGLE_REFRESH_TOKEN, GOOGLE_CLIENT_ID,
+#   GOOGLE_CLIENT_SECRET (or GOOGLE_CALENDAR_TOKEN), GCAL_ID — all CONFIRMED set.
```

### Env status (G4) — CONFIRMED, no change required

```
# Netlify lambda (read + patch GCal) — CONFIRMED set via `netlify env:list --json`:
GCAL_ID=primary               ✓
GOOGLE_CLIENT_ID=...           ✓
GOOGLE_CLIENT_SECRET=...       ✓
GOOGLE_REFRESH_TOKEN=...       ✓
# Local sender (~/.openclaw/.env) — CONFIRMED present:
GOG_ACCOUNT, GOG_KEYRING_PASSWORD, GOOGLE_LOGIN_EMAIL  ✓
# AgentMail NOT needed for SEND anymore. LIFE_ASK_INBOX_ID only if the reply
# webhook intake path is kept (see open question 2).
```

---

## Commands (safe test — throwaway event, no real data disturbed)

Run on the Mac-mini. Disposable event; cleaned up at the end.

```bash
set -a; . ~/.openclaw/.env; set +a
ACC="${GOG_ACCOUNT:-${GOOGLE_LOGIN_EMAIL:-keiodaisuke@gmail.com}}"

# 1. Throwaway timed event, NO location, end==start (duration unknown).
#    gog 0.17.0: `gog calendar create <calendarId>` (calId is a POSITIONAL arg).
START=$(date -u -v+2H +%Y-%m-%dT%H:%M:%S 2>/dev/null || date -u -d '+2 hours' +%Y-%m-%dT%H:%M:%S)
EV_ID=$(GOG_KEYRING_PASSWORD="$GOG_KEYRING_PASSWORD" /opt/homebrew/bin/gog calendar create primary \
  --account "$ACC" \
  --summary "[TEST-ASK] throwaway $(date +%s)" \
  --start "${START}Z" --end "${START}Z" --json \
  | python3 -c 'import json,sys;print(json.load(sys.stdin).get("id",""))')
echo "throwaway = $EV_ID"

# 2. Pure-logic unit check (no network): duration + location + parse + guard.
node -e '
const L=require("/Users/anicca/anicca-project/apps/landing/netlify/functions/_lib/ask-logic");
const ev={id:"x",summary:"t",start:{dateTime:"2026-06-16T10:00:00Z",timeZone:"Asia/Tokyo"},end:{dateTime:"2026-06-16T10:00:00Z"}};
console.log("needsDuration", L.needsDurationAsk(ev));           // true
console.log("needsLocation", L.needsLocationAsk(ev));           // true
console.log("parseDur", L.parseDurationFromReply("所要 90分"));  // 90
console.log("durRE on 所要90分", L.DURATION_RE.test("所要 90分")); // true (guard works)
const p=L.buildResolvePatch({location:"渋谷",durationMinutes:90},ev);
console.log("patch.end", p.end.dateTime, "loc", p.location);     // start+90m, 渋谷
'

# 3. Send the question locally via gog (this is the REAL send path).
node $HOME/anicca/skills/life/ask/ask.js --action question   # POSTs Netlify question, gog-sends, mark-asked

# 4. Confirm email left (gog), in Dais Gmail.
GOG_KEYRING_PASSWORD="$GOG_KEYRING_PASSWORD" /opt/homebrew/bin/gog gmail search \
  --account "$ACC" "subject:[Ask] newer_than:1h" --json | python3 -c 'import json,sys;print(len(json.load(sys.stdin).get("threads",[])),"thread(s)")'

# 5. SIMULATE inbound reply (no webhook needed) — feed reply body to Netlify reply handler.
node $HOME/anicca/skills/life/ask/ask.js --action reply --body \
  "$(python3 -c 'import json;print(json.dumps({"message":{"subject":"Re: [Ask] 場所と所要時間を教えて","body":"渋谷ヒカリエ 8F\n所要 90分\n---\nEvent ID: '"$EV_ID"'"}}))')"

# 6. VERIFY gcal where + end populated.
#    gog 0.17.0: `gog calendar event <calendarId> <eventId>` (get; calId+eventId positional).
GOG_KEYRING_PASSWORD="$GOG_KEYRING_PASSWORD" /opt/homebrew/bin/gog calendar event primary "$EV_ID" \
  --account "$ACC" --json \
  | python3 -c 'import json,sys;e=json.load(sys.stdin);print("location=",e.get("location"));print("end=",e.get("end"))'

# 7. Duration-only reply guard check (must NOT set location to "所要 60分").
#    Re-create a throwaway, simulate a reply whose ONLY content is a duration,
#    then verify location stays EMPTY and end is set.
node $HOME/anicca/skills/life/ask/ask.js --action reply --body \
  "$(python3 -c 'import json;print(json.dumps({"message":{"subject":"Re: [Ask] 所要時間を教えて","body":"所要 60分\n---\nEvent ID: '"$EV_ID"'"}}))')"
# Expect: handler returns location:null, durationMinutes:60 → step-6 re-check shows location empty.

# 8. CLEANUP.
#    gog 0.17.0: `gog calendar delete <calendarId> <eventId>`.
GOG_KEYRING_PASSWORD="$GOG_KEYRING_PASSWORD" /opt/homebrew/bin/gog calendar delete primary "$EV_ID" \
  --account "$ACC"
```

Real round-trip (optional, exercises the live AgentMail webhook):
```bash
# After step 3, reply in keiodaisuke@gmail.com to the [Ask] mail with:
#   渋谷ヒカリエ 8F
#   所要 60分
# AgentMail webhook → POST .../life-ask?action=reply → gcal patched. Then run step 6.
```

---

## Acceptance

| # | Criterion | How verified |
|---|---|---|
| A1 | Question email **arrives at Dais Gmail** for an event missing location and/or duration. | Step 3 output `{ok:true, asked:[{messageId}]}`; step 4 finds the `[Ask]` thread via `gog gmail search`. |
| A2 | Send uses `gog gmail send` **on the Mac-mini** (no AgentMail quota; not inside Netlify). | Step 3 calls `gogSend` in `ask/ask.js`; Netlify `question` returns `toAsk` only (no mail). |
| A3 | **Reply received** + routed to `action=reply`. | Real: AgentMail webhook `ep_3FBcXGwrcP575GjLm46jCMj2TYr` → handler `{ok:true,...}`. Simulated: step 5 same. |
| A4 | gcal `where` (location) **auto-populated** from reply; pending cleared. | Step 6: `location=渋谷ヒカリエ 8F`. |
| A5 | gcal **duration** (`end.dateTime`) auto-populated from 所要. | Step 6: `end` = start + 90 min. |
| A6 | Duration-only reply NOT written as a bogus location. | Step 7: `location` stays empty, `end` set. (Guard uses exported `DURATION_RE`.) |
| A7 | No real data disturbed. | Only `[TEST-ASK]` throwaway touched; deleted step 8. |

**Resolved (verified this pass)**
- `gog` 0.17.0 verbs CONFIRMED via `gog calendar --help`: `calendar create <calId>`, `calendar event <calId> <eventId>` (get), `calendar delete <calId> <eventId>`, `calendar update <calId> <eventId>` — calId/eventId are POSITIONAL (NOT `calendar events create/get/delete`, NOT `--calendar`). Commands steps 1/6/8 fixed.
- Netlify GCal env CONFIRMED set (`netlify env:list --json`): `GCAL_ID`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`. `getAccessToken()` will authenticate → no 500. (G4 satisfied.)

**Open questions**
1. Confirm the AgentMail inbound webhook (`ep_3FBcXGwrcP575GjLm46jCMj2TYr`) is still live and registered against the genesis inbox, OR move reply intake to a local `gog gmail search` poll on the Mac-mini (drops AgentMail from B-ask entirely — no quota anywhere, single runtime). Recommended: the poll, for symmetry with the local-send architecture.
2. `gog gmail send --json` exact id field: code reads `j.id || j.messageId` (best-effort); the messageId is only used as a label in `mark-asked` and is non-load-bearing, so an empty string is tolerated.
