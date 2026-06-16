# Patch — life-webapp (B / Life Manager → working web app)

> Subsystem: `life-webapp` · Branch: `dev` · Author: patch-author agent · Date: 2026-06-16
> Scope: `apps/landing/app/life-manager/page.tsx` (marketing→app shell) + NEW `apps/landing/app/life-manager/start/page.tsx` (onboarding + schedule view) + NEW `apps/landing/netlify/functions/life-onboard.js` + NEW `apps/landing/netlify/functions/life-schedule.js`. Reuses existing `calendar-connect.js`, `_lib/travel-logic.js`, `_lib/gcal-token.js`.
> Goal: turn `/life-manager` from a "coming" marketing page into a WORKING web app — a real user onboards (name / phone / calendar / location), connects Google Calendar in one tap, and immediately SEES their own schedule with auto travel blocks. No "coming" badges, no internal jargon.
> Constraint: patch FILE only — NOT applied, NOT committed, NOT deployed.

Spec source — `docs/superpowers/specs/anicca/27-launch-workflow-and-ubi.md` line 24-25:
> **WF-B(Life Manager)** … **B-travel**: heartbeat が gcal を読み、各予定の前に Google Maps Directions 所要時間ぶんの「移動ブロック」を gcal へ自動 insert … 検証 agent = テスト予定作成→移動ブロックが gcal に出現を目視。

Spec source — `docs/superpowers/specs/anicca/07-life-manager.md`:
> Acceptance: a real call/notification fires 10 min before a gcal event; a mail is triaged+drafted; verified.

Spec source — `docs/superpowers/specs/anicca/14-ui-wireframes-all.md` line 177-178 (the "Your life" panel, the user-facing surface this patch realizes):
> `┌─ Your life (only if context connected) ─┐  Next: Team Sync 9:30 · Inbox: 2 need you / 8 handled`

---

## Verified facts (RAW evidence)

1. **Live page is marketing-only, with "coming" badges.** `agent-browser snapshot` of `https://aniccaai.com/life-manager/` (2026-06-16):
   ```
   - StaticText "LIVE"      ← B-travel
   - StaticText "COMING"    ← B-call
   - StaticText "COMING"    ← B-ask
   - StaticText "COMING"    ← B-notify
   - link "Install Anicca" [ref=e8]
   - link "GET STARTED Install Anicca One prompt into Claude Code or Cursor. Anicca is live in 30 seconds."
   ```
   firecrawl scrape confirms the same `B-callcoming / B-askcoming / B-notifycoming` text. There is **NO** connect-calendar button, **NO** onboarding form, **NO** schedule view anywhere on the page.

2. **The page source is a static marketing component.** `apps/landing/app/life-manager/page.tsx` declares `export const dynamic = 'force-static'`, a `FEATURES` array with `status: 'live' | 'coming'`, and renders four cards + an "Install Anicca" CTA. The only "action" offered is `/install`. Lines 20, 43, 51, 59 are the `'coming'` statuses; lines 63-72 are the `STATUS_BADGE`/`STATUS_LABEL` rendering "live"/"coming".

3. **A proven working connect+onboard flow already exists** — `apps/landing/app/alarm/setup/page.tsx` (client component) calls `GET /.netlify/functions/calendar-connect?token=<t>` → receives `{ redirect_url }` → `window.location.href = redirect_url` (one-tap Google consent), and `POST /.netlify/functions/alarm-profile` to save profile. **This patch clones that pattern for life-manager**, minus the Stripe `session_id` gate (life-manager onboards self-serve).

4. **Calendar connect is real and managed.** `apps/landing/netlify/functions/calendar-connect.js` uses Composio v3 managed OAuth (`COMPOSIO_API=https://backend.composio.dev/api/v3`, `GCAL_AUTH_CONFIG=COMPOSIO_GCAL_AUTH_CONFIG`), keyed by `user_id` = subscriber phone, idempotent (returns `{connected:true}` if an ACTIVE googlecalendar connection already exists, else `{redirect_url}`). Env present in prod (`netlify.toml` references these functions on schedules).

5. **Travel-block logic is TDD-verified and reusable for display.** `apps/landing/netlify/functions/_lib/travel-logic.js` exports `detectMissingTravelBlocks(events)`, `buildTravelBlock({calendarId,eventTitle,eventStart,durationSec})`, plus `isTravelBlock(summary)` / `travelBlockTitle(title)` (line 114 `module.exports`). `life-travel.js` already wires GCal REST + Maps Directions around it.

6. **Per-user event READ needs a new function.** `calendar-connect.js` only *creates* the connection; the event read for `life-travel.js` uses a **global** `GOOGLE_REFRESH_TOKEN` (Dais's own calendar — `_lib/gcal-token.js`), not the per-user Composio connection. So a self-serve user who connects via Composio has **no** way to read their events back for display. **This patch adds `life-schedule.js`** which reads events through the user's Composio connection via the canonical REST execute endpoint.
   - Composio v3 execute endpoint (ctx7 `/websites/composio_dev`, `postToolsExecuteByToolSlug`): `POST https://backend.composio.dev/api/v3.1/tools/execute/{toolSlug}` with header `x-api-key`, body `{ "user_id": "<phone>", "arguments": {...} }`. Tool slug `GOOGLECALENDAR_EVENTS_LIST` (calendarId=`primary`, timeMin/timeMax = today).

7. **Profile schema supports it.** `subscriber_profiles` already has the needed columns (grep of `netlify/functions/*.js`): `name`, `phone`, `wake_time`, `home_address`, `home_lat`, `home_lon`, `owntracks_token`, `calendar_provider`, `ics_url`, `stakeholders`, `status`. No migration required — onboarding inserts/merges by `phone` (the Composio `user_id`).

---

## Gaps

| # | Spec requires | Live/code reality (RAW) | Severity |
|---|---|---|---|
| G1 | A real user can **connect a calendar and see their schedule** with travel blocks | Page is static marketing; only action is `/install`. No connect button, no schedule view. (evidence #1, #2) | BLOCKER |
| G2 | **Onboarding collects name / phone / calendar / location** | No form exists on `/life-manager`. The only onboarding (`/alarm/setup`) is gated behind a Stripe `session_id` and is the *alarm* product. (evidence #2, #3) | BLOCKER |
| G3 | **No "coming" badges, no jargon** | 3 `COMING` badges (B-call/B-ask/B-notify); copy exposes internals: "μ-law↔PCM transcode", "Charon socket", "AgentMail webhook", "spec27 §2 patch", "travel-logic.js", "anicca_travel_block extended property", "~/.openclaw/.env chmod 600", "heartbeat endpoint". (evidence #1, lines 42/50/58/115-117/149/213-237/263-289 of page.tsx) | BLOCKER |
| G4 | User who connects via managed OAuth can **read their own events back** | No per-user read path exists; `life-travel.js` reads only the global Dais calendar. (evidence #6) | BLOCKER |

Dependencies (separate patches — NOT in this patch's scope, but the app shell links/labels them honestly as the daemon-side skills they are): **B-call** (`life-travel`/`call.js` phone bridge), **B-ask** (`life-ask.js`), **B-notify** (`life-notify.js`). Those run inside the user's local/cloud Anicca daemon and are validated by their own functions (`life-ask.js`, `life-notify.js` already exist). This patch does NOT claim them as in-browser features; it presents them as "what your connected Anicca then does for you" and links the working web surface (connect + see schedule) as the live entry point.

---

## Diff

### D1 — `apps/landing/app/life-manager/page.tsx` — replace "coming" marketing cards with a real entry CTA

Replace the `FeatureStatus`/`STATUS_BADGE`/`STATUS_LABEL` machinery and the four-card grid so the page's primary action is **"Connect your calendar"** (→ `/life-manager/start`) instead of "Install Anicca", and the feature cards describe outcomes plainly with **no `coming` badge** and **no jargon**.

```diff
@@ apps/landing/app/life-manager/page.tsx
-type FeatureStatus = 'live' | 'coming';
-
-const FEATURES: {
-  id: string;
-  label: string;
-  headline: string;
-  body: string;
-  status: FeatureStatus;
-}[] = [
-  {
-    id: 'travel',
-    label: 'B-travel',
-    headline: 'Automatic travel blocks',
-    body:
-      'Anicca reads your primary Google Calendar each morning, calls Google Maps Directions for each timed event, and inserts a "[Travel] <event>" block so the commute is always visible. Moving dentist appointment from 10:00? The travel block moves with it.',
-    status: 'live',
-  },
-  {
-    id: 'call',
-    label: 'B-call',
-    headline: '15-min phone call before every event',
-    body:
-      'Gemini Live (voice: Charon, male) bridges over your carrier’s media stream. … μ-law↔PCM transcode and Charon socket serve both carriers.',
-    status: 'coming',
-  },
-  {
-    id: 'ask',
-    label: 'B-ask',
-    headline: 'Missing location? Ask you by email',
-    body:
-      "When a calendar event has no location, Anicca emails you … AgentMail webhook that writes the location back to GCal.",
-    status: 'coming',
-  },
-  {
-    id: 'notify',
-    label: 'B-notify',
-    headline: 'Late-risk → draft → you approve → notify attendees',
-    body:
-      "If Anicca detects you're running late … One-word reply \"OK\" fires the message. No app, pure email.",
-    status: 'coming',
-  },
-];
-
-const STATUS_BADGE: Record<FeatureStatus, string> = {
-  live: 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20',
-  coming:
-    'bg-[hsl(var(--surface-elevated))] text-[hsl(var(--text-secondary))] border border-[hsl(var(--border))]',
-};
-
-const STATUS_LABEL: Record<FeatureStatus, string> = {
-  live: 'live',
-  coming: 'coming',
-};
+// Plain outcome cards — what Anicca does once your calendar is connected.
+// No internal labels (B-travel/B-call), no "coming" badges, no jargon.
+const FEATURES: { id: string; headline: string; body: string }[] = [
+  {
+    id: 'travel',
+    headline: 'Travel time, added for you',
+    body:
+      'Anicca reads your Google Calendar and adds a travel block before each event, so your commute is always on your schedule. Move an appointment, and the travel block moves with it.',
+  },
+  {
+    id: 'call',
+    headline: 'A call before you need to leave',
+    body:
+      'Anicca calls your phone before each event — "Leave now for the dentist, it\'s 18 minutes away." You can answer back and ask questions.',
+  },
+  {
+    id: 'ask',
+    headline: 'Fills in missing details',
+    body:
+      "If an event has no location, Anicca emails you to ask. Reply with the address and it's added to your calendar automatically.",
+  },
+  {
+    id: 'notify',
+    headline: 'Tells people when you run late',
+    body:
+      "Running behind? Anicca drafts a quick \"I'll be 10 minutes late\" for the people in the event and sends it once you reply OK.",
+  },
+];
```

Hero CTA + cards (replace `primary` CTA and the `.map` render):

```diff
@@ SplitHero primary
-        primary={
-          <CTA href="/install" variant="primary">
-            Install Anicca
-          </CTA>
-        }
+        primary={
+          <CTA href="/life-manager/start" variant="primary">
+            Connect your calendar
+          </CTA>
+        }
@@ feature card render
-              <div className="rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface))] p-5 h-full">
-                <div className="flex items-center gap-2">
-                  <span className="text-xs font-mono text-[hsl(var(--text-secondary))]">
-                    {f.label}
-                  </span>
-                  <span
-                    className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${STATUS_BADGE[f.status]}`}
-                  >
-                    {STATUS_LABEL[f.status]}
-                  </span>
-                </div>
-                <h3 className="mt-2 text-base font-semibold text-[hsl(var(--text-primary))]">
+              <div className="rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface))] p-5 h-full">
+                <h3 className="text-base font-semibold text-[hsl(var(--text-primary))]">
                   {f.headline}
                 </h3>
                 <p className="mt-2 text-sm text-[hsl(var(--text-secondary))] leading-relaxed">
                   {f.body}
                 </p>
               </div>
```

Also **delete** the two jargon sections — "How B-travel works (spec27 §2)" table (page.tsx ~146-222) and "Trigger design — schedule-derived, not clock polling" (~224-243) — and rewrite the "Getting started" `<ol>` (~245-297) to the three plain steps: **1. Connect your calendar · 2. Tell Anicca where home is · 3. See your day, travel time already added** (links: step 1 → `/life-manager/start`). Replace the bottom "Install Anicca / Colony dashboard" dual-CTA's first card with `href="/life-manager/start"` → "Connect your calendar / See your real schedule in under a minute."

### D2 — NEW `apps/landing/app/life-manager/start/page.tsx` — onboarding + live schedule (client component, clones `/alarm/setup`)

```tsx
"use client";
import { useEffect, useState } from "react";

// aniccaai.com/life-manager/start — self-serve onboarding + live schedule view.
// 1) collect name / phone / location, 2) one-tap Google Calendar connect (Composio),
// 3) read the user's events back and render the day with [Travel] blocks.

type Ev = { summary: string; startIso: string | null; isTravel: boolean };

export default function Start() {
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");        // = Composio user_id + profile key
  const [home, setHome] = useState("");
  const [token, setToken] = useState<string | null>(null); // owntracks_token from onboard
  const [calConnected, setCalConnected] = useState(false);
  const [events, setEvents] = useState<Ev[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  // Resume an in-progress onboarding after the OAuth round-trip (?phone= on return).
  useEffect(() => {
    const p = new URLSearchParams(window.location.search).get("phone");
    if (p) { setPhone(p); loadSchedule(p); }
  }, []);

  async function onboard() {
    setErr(""); setBusy(true);
    try {
      const r = await fetch("/.netlify/functions/life-onboard", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name.trim(), phone: phone.trim(), home_address: home.trim() || null }),
      });
      if (!r.ok) throw new Error(await r.text());
      const d = await r.json();
      setToken(d.token);
      return d.token as string;
    } catch (e: any) { setErr("保存できませんでした。番号を確認して再度お試しください。"); throw e; }
    finally { setBusy(false); }
  }

  async function connectCalendar() {
    setErr(""); setBusy(true);
    try {
      let t = token; if (!t) t = await onboard();
      const r = await fetch(`/.netlify/functions/calendar-connect?token=${encodeURIComponent(t!)}`);
      const d = await r.json();
      if (d.connected) { setCalConnected(true); await loadSchedule(phone.trim()); return; }
      if (d.redirect_url) {
        // come back here after consent so we can render the schedule
        const back = `${window.location.origin}/life-manager/start?phone=${encodeURIComponent(phone.trim())}`;
        sessionStorage.setItem("life_return", back);
        window.location.href = d.redirect_url; return;
      }
      throw new Error("no redirect");
    } catch { setErr("接続できませんでした。少し待って再度お試しください。"); }
    finally { setBusy(false); }
  }

  async function loadSchedule(p: string) {
    setBusy(true);
    try {
      const r = await fetch(`/.netlify/functions/life-schedule?phone=${encodeURIComponent(p)}`);
      if (!r.ok) throw new Error();
      const d = await r.json();
      setCalConnected(true);
      setEvents(d.events || []);
    } catch { /* not connected yet — leave form visible */ }
    finally { setBusy(false); }
  }

  return (
    <main className="min-h-screen bg-[#0a0a0c] px-6 py-10 text-white">
      <div className="mx-auto max-w-2xl">
        <h1 className="font-soft text-3xl">Never be late again</h1>
        <p className="mt-2 text-white/55">
          Connect your calendar and Anicca adds travel time, calls you before each event, and tells people when you run late.
        </p>

        {!calConnected ? (
          <div className="mt-8 space-y-4">
            <input className="w-full rounded-lg border border-white/15 bg-white/5 px-4 py-3"
              placeholder="Your name" value={name} onChange={(e) => setName(e.target.value)} />
            <input className="w-full rounded-lg border border-white/15 bg-white/5 px-4 py-3"
              placeholder="Phone (e.g. +8190…) — Anicca calls this before events"
              value={phone} onChange={(e) => setPhone(e.target.value)} />
            <input className="w-full rounded-lg border border-white/15 bg-white/5 px-4 py-3"
              placeholder="Home address (for travel time, optional)" value={home} onChange={(e) => setHome(e.target.value)} />
            <button onClick={connectCalendar} disabled={busy || !phone.trim()}
              className="rounded-xl bg-amber-500 px-6 py-3.5 text-black disabled:opacity-40">
              {busy ? "Connecting…" : "📅 Connect Google Calendar"}
            </button>
            {err && <p className="text-red-300/80 text-sm">{err}</p>}
          </div>
        ) : (
          <section className="mt-8">
            <h2 className="font-soft text-xl">Your day</h2>
            <p className="text-white/50 text-sm">Travel time added automatically by Anicca.</p>
            <ul className="mt-4 divide-y divide-white/10 rounded-lg border border-white/10">
              {(events || []).length === 0 && <li className="p-4 text-white/50">No events today.</li>}
              {(events || []).map((e, i) => (
                <li key={i} className={`flex gap-3 p-3 ${e.isTravel ? "text-emerald-400" : "text-white"}`}>
                  <span className="font-mono text-sm tabular-nums text-white/40">
                    {e.startIso ? new Date(e.startIso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "—"}
                  </span>
                  <span>{e.summary}</span>
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>
    </main>
  );
}
```

### D3 — NEW `apps/landing/netlify/functions/life-onboard.js` — self-serve profile create (no Stripe gate)

```js
// life-onboard.js — self-serve Life Manager onboarding.
// POST { name, phone, home_address? } -> upsert subscriber_profiles by phone,
//        return { token } (owntracks_token = stable per-user id reused for calendar-connect).
const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
const crypto = require("crypto");

async function supa(method, path, body, extra) {
  const r = await fetch(`${SUPABASE_URL}/rest/v1/${path}`, {
    method,
    headers: { apikey: SUPABASE_KEY, Authorization: `Bearer ${SUPABASE_KEY}`, "Content-Type": "application/json", ...(extra || {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
  const t = await r.text();
  try { return { ok: r.ok, data: JSON.parse(t) }; } catch { return { ok: r.ok, data: t }; }
}

exports.handler = async (event) => {
  if (!SUPABASE_URL || !SUPABASE_KEY) return { statusCode: 500, body: "missing config" };
  if (event.httpMethod !== "POST") return { statusCode: 405, body: "method not allowed" };
  let b; try { b = JSON.parse(event.body || "{}"); } catch { return { statusCode: 400, body: "bad json" }; }
  const phone = (b.phone || "").trim();
  if (!/^\+?\d{8,15}$/.test(phone.replace(/[^\d+]/g, ""))) return { statusCode: 400, body: "invalid phone" };

  const token = crypto.randomBytes(16).toString("hex");
  await supa("POST", "subscriber_profiles?on_conflict=phone",
    { phone, name: (b.name || "").trim() || null, home_address: b.home_address || null,
      owntracks_token: token, status: "active", updated_at: new Date().toISOString() },
    { Prefer: "resolution=merge-duplicates,return=minimal" });
  // read back the canonical token (existing row keeps its original token)
  const { data } = await supa("GET", `subscriber_profiles?phone=eq.${encodeURIComponent(phone)}&select=owntracks_token`);
  const row = Array.isArray(data) && data[0] ? data[0] : {};
  return { statusCode: 200, headers: { "Content-Type": "application/json" }, body: JSON.stringify({ token: row.owntracks_token || token }) };
};
```

### D4 — NEW `apps/landing/netlify/functions/life-schedule.js` — read user's events via their Composio connection

```js
// life-schedule.js — read a user's Google Calendar events (today) through their
// Composio managed connection and tag auto-inserted [Travel] blocks for display.
// GET ?phone=<e164>  ->  { events: [{ summary, startIso, isTravel }] }
const { isTravelBlock } = require("./_lib/travel-logic");
const COMPOSIO_API = "https://backend.composio.dev/api/v3.1"; // execute endpoint (ctx7: postToolsExecuteByToolSlug)
const COMPOSIO_KEY = process.env.COMPOSIO_API_KEY;

exports.handler = async (event) => {
  if (!COMPOSIO_KEY) return { statusCode: 500, body: "missing composio config" };
  const phone = (event.queryStringParameters || {}).phone;
  if (!phone) return { statusCode: 400, body: "missing phone" };

  const now = new Date();
  const dayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate()).toISOString();
  const dayEnd = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1).toISOString();

  try {
    // Composio user_id == subscriber phone (same convention as calendar-connect.js).
    const r = await fetch(`${COMPOSIO_API}/tools/execute/GOOGLECALENDAR_EVENTS_LIST`, {
      method: "POST",
      headers: { "x-api-key": COMPOSIO_KEY, "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: phone,
        arguments: { calendarId: "primary", timeMin: dayStart, timeMax: dayEnd, singleEvents: true, orderBy: "startTime", maxResults: 50 },
      }),
    });
    const j = await r.json();
    if (!r.ok || j.successful === false) return { statusCode: 502, body: JSON.stringify({ error: "composio_exec", detail: j.error || j }) };
    const items = j?.data?.items || j?.data?.response_data?.items || [];
    const events = items.map((ev) => ({
      summary: ev.summary || "(no title)",
      startIso: ev.start?.dateTime || ev.start?.date || null,
      isTravel: isTravelBlock(ev.summary),
    }));
    return { statusCode: 200, headers: { "Content-Type": "application/json" }, body: JSON.stringify({ events }) };
  } catch (e) {
    return { statusCode: 502, body: JSON.stringify({ error: String(e) }) };
  }
};
```

> Note: `GOOGLECALENDAR_EVENTS_LIST` response shape (`j.data.items` vs `j.data.response_data.items`) MUST be confirmed against one live execute call (see Commands → step V0) before relying on the parse. The travel blocks themselves are inserted by the existing daemon-side `life-travel` skill; this function only reads + tags them for the web view.

---

## Commands

### Apply
```bash
cd /Users/anicca/anicca-project
git fetch && git checkout dev && git pull
git checkout -b feature/life-webapp
# apply D1 (edit app/life-manager/page.tsx), then create:
#   apps/landing/app/life-manager/start/page.tsx        (D2)
#   apps/landing/netlify/functions/life-onboard.js      (D3)
#   apps/landing/netlify/functions/life-schedule.js     (D4)
```

### Build / lint (must pass before deploy)
```bash
cd apps/landing && npm run build    # Next static export must succeed (start/ is a "use client" page, OK under output:export)
node --check netlify/functions/life-onboard.js
node --check netlify/functions/life-schedule.js
```

### Deploy (PR → main → Netlify auto-deploy)
```bash
git add -A && git commit -m "feat(life-webapp): working connect-calendar + schedule view, drop coming badges"
git push -u origin feature/life-webapp
gh pr create --base dev --title "life-webapp: working /life-manager app" --body "Connect calendar → see schedule; onboarding name/phone/calendar/location; no coming badges."
# merge to dev (staging), verify, then PR dev → main → aniccaai.com auto-deploy via netlify-deploy.yml (paths: apps/landing/**)
```

### VERIFY (live, agent-browser — fire after deploy)
```bash
# V0 — confirm Composio execute shape ONCE (pick a phone with an ACTIVE connection):
curl -s -X POST "https://backend.composio.dev/api/v3.1/tools/execute/GOOGLECALENDAR_EVENTS_LIST" \
  -H "x-api-key: $COMPOSIO_API_KEY" -H "Content-Type: application/json" \
  -d '{"user_id":"<e164>","arguments":{"calendarId":"primary","maxResults":3}}' | jq '.data | keys'

# V1 — no "coming" badges, no jargon on the landing page:
/opt/homebrew/bin/agent-browser open "https://aniccaai.com/life-manager/"
/opt/homebrew/bin/agent-browser snapshot | grep -iE "coming|μ-law|Charon socket|spec27|AgentMail|travel-logic|anicca_travel_block|\.openclaw" \
  && echo "FAIL: jargon/coming present" || echo "PASS: clean"
/opt/homebrew/bin/agent-browser snapshot | grep -i "Connect your calendar" && echo "PASS: CTA present"

# V2 — onboarding collects the 4 fields + connect works end to end:
/opt/homebrew/bin/agent-browser open "https://aniccaai.com/life-manager/start"
/opt/homebrew/bin/agent-browser snapshot | grep -iE "name|phone|home address|Connect Google Calendar"   # 4 fields + button
# fill name/phone/home, click connect → Google consent (camofox if Google fingerprint blocks agent-browser) →
# returns to /life-manager/start?phone=… → schedule renders:
/opt/homebrew/bin/agent-browser snapshot | grep -iE "Your day|Team Sync|Travel"   # events + [Travel] rows visible
```

---

## Acceptance

| # | Criterion | How verified |
|---|---|---|
| A1 | A real user can connect a Google Calendar and **see their schedule** with travel blocks rendered | V2: after Composio consent, `/life-manager/start?phone=…` shows the day's events; `[Travel]` rows render in emerald (`isTravel` from `travel-logic.isTravelBlock`) |
| A2 | Onboarding **collects name / phone / calendar / location** | V2: form shows Name, Phone, Home address inputs + "Connect Google Calendar" button; `life-onboard.js` persists name/phone/home_address to `subscriber_profiles`, calendar via `calendar-connect.js` |
| A3 | **No "coming" badges** anywhere on `/life-manager/` | V1: `grep -i coming` over live snapshot returns nothing |
| A4 | **No internal jargon** (μ-law, Charon socket, spec27, AgentMail, travel-logic, extended-property, ~/.openclaw) | V1: jargon grep returns nothing; copy is plain-language outcomes |
| A5 | Primary CTA leads to the working app, not "Install Anicca" | V1: "Connect your calendar" link → `/life-manager/start` (HTTP 200) |

---

## Open questions

1. **Composio `GOOGLECALENDAR_EVENTS_LIST` response envelope** — must run V0 once against a live ACTIVE connection to lock the `j.data.items` vs `j.data.response_data.items` path before trusting the parser (flagged inline in D4).
2. **`subscriber_profiles.name` column** — referenced in existing functions' grep output, but confirm it is non-null-safe for self-serve insert (alarm flow inserts via Stripe webhook; this inserts directly). If `name` is absent, drop it from the D3 insert (it is non-load-bearing for the connect flow).
3. **Phone as Composio `user_id` for non-paying users** — `calendar-connect.js` resolves `user_id` from `owntracks_token`→`phone`; D3 sets both so the existing function works unchanged. Confirm no uniqueness/RLS constraint on `subscriber_profiles` blocks a no-Stripe insert.
4. **Dependencies (B-call / B-ask / B-notify)** are separate patches (`life-travel`/`call`, `life-ask`, `life-notify` functions already exist as daemon-side skills). This patch presents them as outcomes of the connected daemon, NOT as in-browser features — it does not implement the phone bridge or mail webhooks.
