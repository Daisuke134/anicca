# Patch: life-ask (B-ask) — email round-trip to fill unknown gcal location/duration

Spec: `docs/superpowers/specs/anicca/27-launch-workflow-and-ubi.md` §2 WF-B **B-ask** (line 28)
+ `docs/superpowers/specs/anicca/07-life-manager.md`.

Spec verbatim (27 line 28):
> **B-ask**: 所要/場所が不明なら `skills/life/ask.js` が Dais の Gmail に質問メールを送り、返信内容で gcal の where を補完(AgentMail inbound webhook 駆動)。…検証 agent = 質問メール着信→返信→gcal 補完を確認。

Audited files (RAW evidence):
- `~/anicca/skills/life/ask.js` — thin shim → `require("./ask/ask")`.
- `~/anicca/skills/life/ask/ask.js` — CLI wrapper that POSTs `https://aniccaai.com/.netlify/functions/life-ask?action=<action>`. No business logic.
- `apps/landing/netlify/functions/life-ask.js` — **canonical implementation**. Two actions: `question` (scan GCal → send email) and `reply` (parse inbound webhook → patch GCal).
- `apps/landing/netlify/functions/_lib/ask-logic.js` — pure logic: `needsLocationAsk`, `detectMissingLocations`, `buildQuestionBody/Subject`, `parseLocationFromReply`, `buildLocationPatch`, `buildAskPendingPatch`.
- `apps/landing/netlify/functions/_lib/gcal-token.js` — `getAccessToken()` (token / refresh-token strategy).
- `~/.openclaw/cron/jobs.json` — job `anicca-life-ask` (id `891b90bb…`), cron `0 21 * * *` (06:00 JST), runs `node $HOME/anicca/skills/life/ask/ask.js --action question`.

---

## Gaps

| # | Required (spec) | Exists today | Gap | Evidence |
|---|---|---|---|---|
| G1 | Send path (question email reaches Dais Gmail) | `handleQuestion` → `sendEmail` via **AgentMail** `POST /v0/inboxes/{inboxId}/messages/send` | Prompt mandates `gog gmail send` because **AGENTMAIL is daily-limited** (the function comment itself notes genesis inbox "hits 429 daily limit"). AgentMail path is brittle. | life-ask.js:93-108, 254-265 |
| G2 | Inbound reply → gcal where update | `handleReply` parses `{message:{body,subject}}`, extracts `Event ID:`, `parseLocationFromReply`, PATCHes `location`. | Path **exists and is wired** (webhook `ep_3FBcXGwrcP575GjLm46jCMj2TYr`). But it only updates `location`, never **duration** — spec says "所要/場所". | life-ask.js:158-219; ask-logic.js:115-141 |
| G3 | Detect **unknown duration** ("所要") | `needsLocationAsk` only checks empty `location`. No duration detection. | Events with no `end.dateTime` (or end==start) never trigger an ask. Spec's "所要…不明" half is unimplemented. | ask-logic.js:31-41 |
| G4 | Required env keys present | `~/.openclaw/.env` has only `AGENTMAIL_API_KEY`, `AGENTMAIL_INBOX_ID`, `GOOGLE_LOGIN_EMAIL`. | **MISSING**: `LIFE_ASK_INBOX_ID`, `DAIS_EMAIL`, `GCAL_ID`, and all GCal-token keys (`GOOGLE_REFRESH_TOKEN`/`GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET`/`GOOGLE_CALENDAR_TOKEN`). Netlify function returns `auth_error` / `missing AGENTMAIL_API_KEY or LIFE_ASK_INBOX_ID`. (Netlify env may differ; local `.env` cannot run it.) | grep `~/.openclaw/.env`; gcal-token.js:27-37; life-ask.js:258-265 |
| G5 | `gog` available for local mail send | `/opt/homebrew/bin/gog` present, `gog gmail send` supports `--account --to --subject --body/--body-file --json`. | No gap — confirmed available. Use `--account keiodaisuke@gmail.com` (= `GOOGLE_LOGIN_EMAIL`). | `which gog`; `gog gmail send --help` |

**Net**: location round-trip is wired against AgentMail; the gaps are (a) switch send to `gog gmail send` (G1, no quota), (b) add duration detection + parse (G3, G2-extension), (c) env keys (G4).

---

## Diff

Two parts: **(P1)** add duration logic to the pure module `ask-logic.js`; **(P2)** add a `gog gmail send` mail adapter + duration wiring to the Netlify handler `life-ask.js`. Both are additive/backward-compatible.

### P1 — `apps/landing/netlify/functions/_lib/ask-logic.js`

```diff
@@ const ASK_PREFIX = "[Ask] ";
 const AGENTMAIL_PENDING_PROP = "anicca_ask_pending";
 const AGENTMAIL_QUESTION_ID_PROP = "anicca_ask_question_id";
+// Reply-parse markers
+const DURATION_RE = /(?:所要|duration|時間)[：:\s]*([0-9０-９]{1,3})\s*(?:分|min)/i;

@@ function needsLocationAsk(event) {
   if (!event || !event.start || !event.start.dateTime) return false;
   const summary = (event.summary || "").trim();
   if (summary.startsWith("[Travel]") || summary.startsWith(ASK_PREFIX)) return false;
   if (event.location && event.location.trim() !== "") return false;
   const pending = event.extendedProperties?.private?.[AGENTMAIL_PENDING_PROP];
   if (pending === "true") return false;
   return true;
 }
+
+/**
+ * Returns true if the event's duration is unknown:
+ *   - no end.dateTime, OR
+ *   - end.dateTime === start.dateTime (zero-length / placeholder).
+ * (start.dateTime is required — all-day events are out of scope.)
+ */
+function needsDurationAsk(event) {
+  if (!event || !event.start || !event.start.dateTime) return false;
+  const summary = (event.summary || "").trim();
+  if (summary.startsWith("[Travel]") || summary.startsWith(ASK_PREFIX)) return false;
+  const pending = event.extendedProperties?.private?.[AGENTMAIL_PENDING_PROP];
+  if (pending === "true") return false;
+  const endDt = event.end?.dateTime;
+  if (!endDt) return true;
+  return new Date(endDt).getTime() <= new Date(event.start.dateTime).getTime();
+}
+
+/**
+ * What does THIS event need asked? Returns a set: {location?, duration?}.
+ */
+function detectAskKind(event) {
+  return {
+    location: needsLocationAsk(event),
+    duration: needsDurationAsk(event),
+  };
+}
```

```diff
@@ function detectMissingLocations(events) {
   if (!Array.isArray(events)) return [];
   return events.filter(needsLocationAsk);
 }
+
+/**
+ * Filter to events that need EITHER a location OR a duration question.
+ * Each returned item is { event, kind:{location,duration} }.
+ */
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
-  return (
-    `Anicca より確認です。\n\n` +
-    `予定「${title}」(${when})の場所が未設定です。\n` +
-    `場所・住所・目的地を返信してください。\n` +
-    `Anicca が自動でカレンダーに反映します。\n\n` +
-    `---\nEvent ID: ${event.id || "unknown"}`
-  );
+  const kind = detectAskKind(event);
+  const wants = [];
+  if (kind.location) wants.push(`・場所(住所・目的地)`);
+  if (kind.duration) wants.push(`・所要時間(例: 所要 60分)`);
+  const ask = wants.length ? wants.join("\n") : `・場所(住所・目的地)`;
+  return (
+    `Anicca より確認です。\n\n` +
+    `予定「${title}」(${when})の以下が未設定です。\n` +
+    `${ask}\n` +
+    `そのまま返信してください。Anicca が自動でカレンダーに反映します。\n\n` +
+    `---\nEvent ID: ${event.id || "unknown"}`
+  );
 }
```

```diff
@@ function buildQuestionSubject(event) {
   const title = (event.summary || "").trim() || "(no title)";
-  return `${ASK_PREFIX}場所を教えて — ${title}`;
+  const kind = detectAskKind(event);
+  const what = kind.location && kind.duration ? "場所と所要時間"
+    : kind.duration ? "所要時間" : "場所";
+  return `${ASK_PREFIX}${what}を教えて — ${title}`;
 }
```

```diff
@@ function parseLocationFromReply(body) {
   ... (unchanged) ...
 }
+
+/**
+ * Parse a duration in minutes from a reply body, or null.
+ * Matches "所要 60分", "duration: 90 min", "時間 45分", or a bare "Nm"/"N分" line.
+ */
+function parseDurationFromReply(body) {
+  if (!body || typeof body !== "string") return null;
+  const norm = body.replace(/[０-９]/g, (d) => "0123456789"["０１２３４５６７８９".indexOf(d)]);
+  const m = norm.match(/(?:所要|duration|時間)[：:\s]*([0-9]{1,3})\s*(?:分|min)/i)
+    || norm.match(/(?:^|\n)\s*([0-9]{1,3})\s*(?:分|min|m)\s*(?:$|\n)/i);
+  if (!m) return null;
+  const mins = parseInt(m[1], 10);
+  return Number.isFinite(mins) && mins > 0 && mins <= 1440 ? mins : null;
+}
```

```diff
@@ function buildLocationPatch(location, existingEvent) {
   const priorPrivate = existingEvent?.extendedProperties?.private || {};
   const newPrivate = Object.fromEntries(
     Object.entries(priorPrivate).filter(
       ([k]) => k !== AGENTMAIL_PENDING_PROP && k !== AGENTMAIL_QUESTION_ID_PROP
     )
   );
-
-  return {
-    location,
-    extendedProperties: {
-      private: newPrivate,
-    },
-  };
+  return {
+    ...(location ? { location } : {}),
+    extendedProperties: { private: newPrivate },
+  };
 }
+
+/**
+ * Build a GCal patch that sets end.dateTime = start + durationMinutes,
+ * AND optionally location, AND clears the pending flag.
+ * existingEvent MUST carry start.dateTime + start.timeZone.
+ */
+function buildResolvePatch({ location, durationMinutes }, existingEvent) {
+  const patch = buildLocationPatch(location || "", existingEvent);
+  if (durationMinutes && existingEvent?.start?.dateTime) {
+    const startMs = new Date(existingEvent.start.dateTime).getTime();
+    const endIso = new Date(startMs + durationMinutes * 60000).toISOString();
+    patch.end = {
+      dateTime: endIso,
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
   AGENTMAIL_PENDING_PROP,
   AGENTMAIL_QUESTION_ID_PROP,
 };
```

### P2 — `apps/landing/netlify/functions/life-ask.js`

Add a `gog gmail send` adapter (Netlify runs Node with the host PATH; on the Mac-mini runtime `gog` is on PATH). Keep AgentMail as a fallback. Switch `detectMissingLocations` → `detectMissingInfo`, and `buildLocationPatch` → `buildResolvePatch`.

```diff
@@
 const { getAccessToken } = require("./_lib/gcal-token");
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
 } = require("./_lib/ask-logic");
+const { execFile } = require("node:child_process");
```

```diff
@@ async function sendEmail({ apiKey, inboxId, to, subject, text }) {
   ... (AgentMail path unchanged — kept as fallback) ...
 }
+
+// ── gog gmail send adapter (primary; AGENTMAIL is daily-limited) ─────────────────
+// Uses the host `gog` CLI authenticated as GOOGLE_LOGIN_EMAIL (keiodaisuke@gmail.com).
+function gogSend({ account, to, subject, text }) {
+  return new Promise((resolve, reject) => {
+    const args = [
+      "gmail", "send",
+      "--account", account,
+      "--to", to,
+      "--subject", subject,
+      "--body-file", "-",   // body via stdin to avoid shell-escaping issues
+      "--json",
+    ];
+    const child = execFile("gog", args, { timeout: 30000 }, (err, stdout, stderr) => {
+      if (err) return reject(new Error(`gog send failed: ${stderr || err.message}`));
+      let id = "";
+      try { id = (JSON.parse(stdout)?.id) || (JSON.parse(stdout)?.messageId) || ""; } catch {}
+      resolve({ id });
+    });
+    child.stdin.write(text);
+    child.stdin.end();
+  });
+}
+
+// Choose send transport: gog (default, no quota) → AgentMail (fallback).
+async function dispatchEmail(cfg, { to, subject, text }) {
+  const useGog = (process.env.LIFE_ASK_MAIL_TRANSPORT || "gog") !== "agentmail";
+  if (useGog) {
+    try {
+      const account = process.env.GOOGLE_LOGIN_EMAIL || "keiodaisuke@gmail.com";
+      return await gogSend({ account, to, subject, text });
+    } catch (e) {
+      if (!cfg.apiKey || !cfg.inboxId) throw e; // no fallback configured
+    }
+  }
+  return sendEmail({ apiKey: cfg.apiKey, inboxId: cfg.inboxId, to, subject, text });
+}
```

```diff
@@ async function handleQuestion(token, calendarId, agentMailCfg) {
   const events = await listTodayEvents(calendarId, token);
-  const missing = detectMissingLocations(events);
+  const missing = detectMissingInfo(events); // [{ event, kind }]
   const asked = [];

-  for (const ev of missing) {
+  for (const { event: ev } of missing) {
     const subject = buildQuestionSubject(ev);
     const text = buildQuestionBody(ev);

     let messageId = "";
     try {
-      const sent = await sendEmail({
-        apiKey: agentMailCfg.apiKey,
-        inboxId: agentMailCfg.inboxId,
-        to: agentMailCfg.daisEmail,
-        subject,
-        text,
-      });
+      const sent = await dispatchEmail(agentMailCfg, {
+        to: agentMailCfg.daisEmail, subject, text,
+      });
       messageId = sent?.id || sent?.messageId || "";
     } catch (err) {
       asked.push({ eventId: ev.id, eventTitle: ev.summary, error: err.message });
       continue;
     }
     ... (pending patch unchanged) ...
   }
   ...
 }
```

```diff
@@ async function handleReply(body, token, calendarId) {
   ...
   const eventId = eventIdMatch[1].trim();
   if (!eventId || eventId === "unknown") {
     return { statusCode: 400, body: "invalid_event_id" };
   }

-  // Parse location from reply
-  const location = parseLocationFromReply(replyBody);
-  if (!location) {
-    return { statusCode: 422, body: "no_location_found_in_reply" };
-  }
+  // Parse location AND/OR duration from reply
+  const location = parseLocationFromReply(replyBody);
+  const durationMinutes = parseDurationFromReply(replyBody);
+  if (!location && !durationMinutes) {
+    return { statusCode: 422, body: "no_location_or_duration_in_reply" };
+  }

   let existingEvent;
   try {
     existingEvent = await getEvent(calendarId, eventId, token);
   } catch (err) { ... }

-  const patch = buildLocationPatch(location, existingEvent);
+  const patch = buildResolvePatch({ location, durationMinutes }, existingEvent);
   try {
     await patchEvent(calendarId, eventId, patch, token);
   } catch (err) {
     return { statusCode: 502, body: `gcal_patch_error: ${err.message}` };
   }

   return {
     statusCode: 200,
-    body: JSON.stringify({ ok: true, eventId, location }),
+    body: JSON.stringify({ ok: true, eventId, location, durationMinutes }),
   };
 }
```

> **Note on `parseLocationFromReply` greediness**: when the reply contains ONLY a duration ("所要 60分"), the existing first-non-quoted-line heuristic would return "所要 60分" as a bogus location. P1 leaves `parseLocationFromReply` untouched but `buildResolvePatch` is called with both; to avoid writing a bad location, add one guard in `handleReply`: `const cleanLoc = (location && !DURATION_RE.test(location)) ? location : null;` and pass `cleanLoc`. (DURATION_RE exported alongside, or inline the regex.)

### Env to add (G4) — `~/.openclaw/.env` (names only; values out of scope)

```
LIFE_ASK_INBOX_ID=        # only if AgentMail fallback used
DAIS_EMAIL=keiodaisuke@gmail.com
GCAL_ID=primary
GOOGLE_REFRESH_TOKEN=     # + GOOGLE_CLIENT_ID + GOOGLE_CLIENT_SECRET  (or GOOGLE_CALENDAR_TOKEN)
```
With `gog` transport (default), the Netlify token keys are still required for GCal read/patch, but mail needs **no** AgentMail keys.

---

## Commands (safe test — throwaway event, no real data disturbed)

All run on the Mac-mini runtime. Uses a disposable calendar event; cleans up after.

```bash
set -a; . ~/.openclaw/.env; set +a
ACC="${GOOGLE_LOGIN_EMAIL:-keiodaisuke@gmail.com}"

# 1. Create a THROWAWAY timed event with NO location and NO end (duration unknown).
#    Place it 'today' so the daily scan picks it up.
START=$(date -u -v+2H +%Y-%m-%dT%H:%M:%S 2>/dev/null || date -u -d '+2 hours' +%Y-%m-%dT%H:%M:%S)
EV_JSON=$(gog calendar create --account "$ACC" --calendar primary \
  --summary "[TEST-ASK] throwaway $(date +%s)" \
  --start "${START}Z" --end "${START}Z" --json)   # end==start → duration unknown
EV_ID=$(echo "$EV_JSON" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("id",""))')
echo "throwaway event = $EV_ID"

# 2. Pure-logic unit check (no network): duration + location detection + parse.
node -e '
const L=require("/Users/anicca/anicca-project/apps/landing/netlify/functions/_lib/ask-logic");
const ev={id:"x",summary:"t",start:{dateTime:"2026-06-16T10:00:00Z",timeZone:"Asia/Tokyo"},end:{dateTime:"2026-06-16T10:00:00Z"}};
console.log("needsDuration", L.needsDurationAsk(ev));      // true
console.log("needsLocation", L.needsLocationAsk(ev));      // true
console.log("parseDur", L.parseDurationFromReply("所要 90分"));   // 90
console.log("parseLoc", L.parseLocationFromReply("渋谷ヒカリエ 8F")); // 渋谷ヒカリエ 8F
const p=L.buildResolvePatch({location:"渋谷",durationMinutes:90},ev);
console.log("patch.end", p.end.dateTime, "loc", p.location); // start+90m, 渋谷
'

# 3. Trigger question send (LOCAL, gog transport) — observe email actually leaves.
LIFE_ASK_MAIL_TRANSPORT=gog \
  node $HOME/anicca/skills/life/ask/ask.js --action question   # POSTs Netlify; OR run handler locally:
# Local handler invocation (bypasses Netlify deploy):
node -e '
process.env.LIFE_ASK_MAIL_TRANSPORT="gog";
const h=require("/Users/anicca/anicca-project/apps/landing/netlify/functions/life-ask").handler;
h({httpMethod:"POST",queryStringParameters:{action:"question"},body:"{}"}).then(r=>console.log(r));
'

# 4. SIMULATE the inbound reply (no AgentMail webhook needed) — feed reply body directly.
node -e '
const h=require("/Users/anicca/anicca-project/apps/landing/netlify/functions/life-ask").handler;
const body=JSON.stringify({message:{subject:"Re: [Ask] 場所と所要時間を教えて",
  body:"渋谷ヒカリエ 8F\n所要 90分\n---\nEvent ID: '"$EV_ID"'"}});
h({httpMethod:"POST",queryStringParameters:{action:"reply"},body}).then(r=>console.log(r));
'

# 5. VERIFY gcal where + end were populated.
gog calendar get --account "$ACC" --calendar primary "$EV_ID" --json \
  | python3 -c 'import json,sys;e=json.load(sys.stdin);print("location=",e.get("location"));print("end=",e.get("end"))'

# 6. CLEANUP — delete throwaway event.
gog calendar delete --account "$ACC" --calendar primary "$EV_ID"
```

E2E with a REAL reply round-trip (optional, observes the actual inbound webhook):
```bash
# After step 3, reply to the [Ask] email in keiodaisuke@gmail.com with:
#   渋谷ヒカリエ 8F
#   所要 60分
# AgentMail webhook → POST .../life-ask?action=reply → gcal patched. Then run step 5.
```

---

## Acceptance

| # | Criterion | How verified |
|---|---|---|
| A1 | Question email **arrives at Dais Gmail** (keiodaisuke@gmail.com) for an event missing location and/or duration. | Step 3 returns `{ok:true, asked:[{messageId}]}`; email visible in `gog gmail search --account keiodaisuke@gmail.com "subject:[Ask] newer_than:1h"`. |
| A2 | Send uses `gog gmail send` (no AgentMail quota consumed). | Step 3 with `LIFE_ASK_MAIL_TRANSPORT=gog`; `gog` returns a Gmail message id; AgentMail `/messages/send` NOT called. |
| A3 | **Reply received** and routed to `action=reply`. | Real path: AgentMail webhook `ep_3FBcXGwrcP575GjLm46jCMj2TYr` fires → handler returns `{ok:true,eventId,location,durationMinutes}`. Simulated: step 4 returns same. |
| A4 | gcal `where` (location) **auto-populated** from the reply. | Step 5: `location=渋谷ヒカリエ 8F`, pending flag cleared. |
| A5 | gcal **duration** (`end.dateTime`) auto-populated when reply gives 所要. | Step 5: `end` = start + 90 min. |
| A6 | No real data disturbed. | Only the `[TEST-ASK]` throwaway event touched; deleted in step 6. |

**Open questions**
1. Netlify runtime PATH: does the deployed Netlify function actually have `gog` on PATH? The cron runs `ask/ask.js` which **POSTs to Netlify** — so `gog` would need to exist in the Netlify lambda (it does NOT). RESOLUTION OPTIONS: (a) move the mail-send out of the Netlify function and into the OSS skill `ask/ask.js` (which runs on the Mac-mini where `gog` lives), keeping Netlify for GCal-only; or (b) keep send in Netlify but use AgentMail there. The patch's `gog` adapter assumes the Mac-mini host. **Recommend (a): make `ask/ask.js` do the gog send locally and only call Netlify for GCal read/patch.** Needs a small architecture decision before commit.
2. `parseLocationFromReply` returning a bogus location when only duration is supplied — guarded inline in `handleReply` (DURATION_RE), but worth a dedicated unit test.
3. Confirm whether the AgentMail inbound webhook is still live/registered (`ep_3FBcXGwrcP575GjLm46jCMj2TYr`) or whether reply intake should also move to a `gog gmail search` poll on the Mac-mini.
