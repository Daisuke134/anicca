# P-lm-separate — Life Manager web = a SEPARATE cloud product `/lm`

> Spec: `docs/superpowers/specs/anicca/28-product-redesign-merge-2026-06-16.md` §0 (three product lines), §2 (Life Manager separate `/lm`), §3 (malice-guard), §5 (UX skills), §6 (P-lm-separate row).
> Branch off `main`. Patches are REAL git-applicable diffs against the live tree at `4f03a6e1`.
> UX taste reference (cited in code headers, per §5): **taste-skill** (design-taste-frontend) + **github.com/nextlevelbuilder/ui-ux-pro-max-skill** — premium, locale-routed (this product surface is EN-only, NOT mixed EN/JA), no AI-slop, no fake "coming soon".

---

## 1. Reality found (cited file:line)

| Fact | Evidence |
|---|---|
| `/life-manager` "Install Anicca" CTA routes to **`/install`** — the SAME place as cloud Anicca. There are **3** `href="/install"` occurrences on that page. | `apps/landing/app/life-manager/page.tsx:83` (hero `CTA`), `:253` (getting-started `<li>`), `:303` (bottom "get started" card). (Verified: `grep -c 'href="/install"' page.tsx` → 3, at lines 83/253/303.) |
| The page itself says LM is "a set of skills inside your local Anicca daemon … no cloud subscription required" — i.e. it currently sells the LOCAL skill, not a separate **cloud** product. | `apps/landing/app/life-manager/page.tsx:115-117` |
| The page marks B-call/B-ask/B-notify as **`status: 'coming'`** — but B-call is in fact LIVE (real Twilio call SID recorded). The "coming/fake" copy violates §2 "24/7 LIVE, no 'coming', no fake". | `apps/landing/app/life-manager/page.tsx:43,51,59` vs `apps/landing/app/life-call/page.tsx:22-27` (`Call SID CA2c025395…`, `completed / 45s`, recording SID). |
| `/lm` route does **not** exist yet → free to add (`ls apps/landing/app/lm` → not found). | filesystem check |
| **Composio is the live connector.** A real Netlify Function already provisions a per-user **Google Calendar** connection via Composio managed OAuth and returns a `redirect_url` for one-click consent. Pattern: `POST {COMPOSIO_API}/connected_accounts` with `{ auth_config:{id}, connection:{user_id} }`, idempotent on existing `ACTIVE` connection found via `?user_ids=…&toolkit_slugs=googlecalendar`. | `apps/landing/netlify/functions/calendar-connect.js:6-8,30-58` |
| Only the **`googlecalendar`** Composio toolkit is wired today. **Gmail (`gmail` toolkit) is NOT yet wired** anywhere — `grep -rn "toolkit_slugs" apps/landing/netlify` returns ONLY the `googlecalendar` line. So Gmail-connect is a NEW connector (scoped truthfully below, mirroring the proven gcal function). | `grep -rn "toolkit_slugs" apps/landing/netlify/functions` → 1 hit (calendar-connect.js:32) |
| Auth/identity infra that already exists: **Supabase** (`SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY`) is used server-side in functions; subscriber rows keyed by a stable id (`phone`, `owntracks_token`). Composio `user_id` is the subscriber's **phone** (stable id). | `apps/landing/netlify/functions/calendar-connect.js:9-10,25,47` |
| Front-end is a **Next.js static export** (`output: 'export'`), server = **Netlify Functions (CJS)** (`{"type":"commonjs"}`). Per-user data is fetched **at runtime in the browser** via a client island (`MeClient.tsx` fetches `/.netlify/functions/dashboard-sync`). New onboarding must follow the same client-island pattern. | `apps/landing/next.config.mjs:2` (`'export'`); `apps/landing/netlify/functions/package.json` (`commonjs`); `apps/landing/app/me/MeClient.tsx:1-11` |
| **Real backend skills behind the LM marketing copy (honest mapping — do NOT promise UI for anything without a backend):** | |
| auto-register travel time for every event | python cron **`anicca-travel-fill`** (`expr 0 5 * * *`) → `~/.openclaw/skills/anicca-travel-fill/scripts/run.sh`; web mirror = Netlify scheduled fn **`life-travel`** (`netlify.toml: [functions."life-travel"] schedule "0 21 * * *"`), logic `netlify/functions/_lib/travel-logic.js` |
| email-ask when location unknown → reply → auto-register | python cron **`anicca-life-ask`** (`expr 0 21 * * *`); web fn **`life-ask`** (`netlify.toml [functions."life-ask"]`), logic `_lib/ask-logic.js`; AgentMail reply webhook writes location back to GCal |
| call 15 min before each event with route guidance | LIVE bridge: `apps/landing/app/life-call/page.tsx:22-27` (real Twilio Call SID + recording); logic `_lib/call-logic.js` |
| notify stakeholders when late (after approving target + draft) | python crons **`anicca-life-notify-scan`** (`*/10 8-22 * * *`) + **`anicca-life-notify-poll`** (`*/5 8-22 * * *`); web fn **`life-notify`** (scan+approval), logic `_lib/notify-logic.js` |

**Honest gap:** Google **login/signup** as a first-class auth step and a real **`/lm` dashboard** reading per-user LM state are NOT built today (the existing `/me` reads colony telemetry by wallet, not LM state). This patch ships: (a) the CTA re-route to `/lm`, (b) a real, working `/lm` onboarding flow whose gcal/Gmail steps call REAL Composio connectors (gcal = existing function, extended with a `uid` branch in Diff A2 so it reaches `connected` for /lm users; Gmail = new function mirroring it), (c) phone capture persisted to a dedicated Supabase `lm_users` table (isolated from the alarm `subscriber_profiles` table), (d) a dashboard that renders the connected-state + the four LM skills with LIVE status. Per-user *live event telemetry* on the dashboard is explicitly marked as the next milestone (no fake numbers) — consistent with §2 "no fake".

---

## 2. The diffs

### Diff A — re-route `/life-manager` CTAs to `/lm`, drop "coming/fake", point at the separate cloud product

Replaces the 3 `/install` links (lines 83, 253, 303) with `/lm`, flips the three "coming" features to "live" (B-call is proven live; B-ask/B-notify run on live crons), updates copy so the page sells the **separate $20/mo cloud product** (not the local skill), and adds a price line. EN-only (locale-routed surface). This block is generated canonically (real tree edit → `git diff` → restore) so it applies with **plain `git apply`** — no `--recount`.

```diff
diff --git a/apps/landing/app/life-manager/page.tsx b/apps/landing/app/life-manager/page.tsx
index 0922570a..c7a6cd82 100644
--- a/apps/landing/app/life-manager/page.tsx
+++ b/apps/landing/app/life-manager/page.tsx
@@ -2,10 +2,11 @@ import LaunchNav from '@/components/site/LaunchNav';
 import Footer from '@/components/site/Footer';
 import { SplitHero, Section, Reveal, CTA } from '@/components/site/taste';
 
-// B-travel (spec27 WF-B) — Life Manager landing page.
-// Replaces Foundation placeholder. Collision rule: ONLY replaces body; LaunchNav +
-// Footer are imported as-is, not modified. Skill lives at ~/anicca/skills/life/travel.js.
-// Logic module: netlify/functions/_lib/travel-logic.js (TDD-verified, 12 tests pass).
+// spec28 P-lm-separate: this is the MARKETING page for the SEPARATE cloud product `/lm`
+// ($20/mo, no trial). Its "Get started" CTA routes to /lm (NOT /install — for cloud they
+// are DIFFERENT products). UX taste: design-taste-frontend + nextlevelbuilder/ui-ux-pro-max-skill.
+// Collision rule: ONLY the body changes; LaunchNav + Footer imported as-is. Skill logic:
+// netlify/functions/_lib/{travel,ask,call,notify}-logic.js + python crons anicca-{travel-fill,life-ask,life-notify-*}.
 
 export const dynamic = 'force-static';
 
@@ -17,7 +18,7 @@ export const metadata = {
 
 // ── Feature table data ────────────────────────────────────────────────────────
 
-type FeatureStatus = 'live' | 'coming';
+type FeatureStatus = 'live';
 
 const FEATURES: {
   id: string;
@@ -40,7 +41,7 @@ const FEATURES: {
     headline: '15-min phone call before every event',
     body:
       'Gemini Live (voice: Charon, male) bridges over your carrier’s media stream. Anicca dials your number 15 minutes before each event, says "Next is Dentist at 10:00 — leave now, walk time 18 min, via Omotesando Exit A3." Two-way voice: you can ask follow-ups. The bridge is provider-agnostic — it routes over Twilio by default and over Telnyx for Japan (+81) numbers, since the same μ-law↔PCM transcode and Charon socket serve both carriers.',
-    status: 'coming',
+    status: 'live',
   },
   {
     id: 'ask',
@@ -48,7 +49,7 @@ const FEATURES: {
     headline: 'Missing location? Ask you by email',
     body:
       "When a calendar event has no location, Anicca emails you: \"Where is the Team Sync? Reply with the address and I'll update the event.\" Your reply triggers an AgentMail webhook that writes the location back to GCal.",
-    status: 'coming',
+    status: 'live',
   },
   {
     id: 'notify',
@@ -56,19 +57,16 @@ const FEATURES: {
     headline: 'Late-risk → draft → you approve → notify attendees',
     body:
       "If Anicca detects you're running late (travel block starts after current time), she drafts \"I'll be 10 min late\" to the event attendees and emails you for approval. One-word reply \"OK\" fires the message. No app, pure email.",
-    status: 'coming',
+    status: 'live',
   },
 ];
 
 const STATUS_BADGE: Record<FeatureStatus, string> = {
   live: 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20',
-  coming:
-    'bg-[hsl(var(--surface-elevated))] text-[hsl(var(--text-secondary))] border border-[hsl(var(--border))]',
 };
 
 const STATUS_LABEL: Record<FeatureStatus, string> = {
   live: 'live',
-  coming: 'coming',
 };
 
 export default function Page() {
@@ -78,10 +76,10 @@ export default function Page() {
 
       <SplitHero
         headline="Life Manager"
-        subtext="Anicca reads your calendar, inserts travel time, calls you before every event, and handles late-notice — all by phone and email. No app to open."
+        subtext="A dedicated cloud product: Anicca reads your calendar, inserts travel time, calls you before every event, and handles late-notice — all by phone and email. $20/mo, no app to open."
         primary={
-          <CTA href="/install" variant="primary">
-            Install Anicca
+          <CTA href="/lm" variant="primary">
+            Get started — $20/mo
           </CTA>
         }
         secondary={
@@ -112,8 +110,8 @@ export default function Page() {
             Four skills, one goal — never be late
           </h2>
           <p className="mt-2 text-sm text-[hsl(var(--text-secondary))]">
-            Life Manager is a set of skills inside your local Anicca daemon. Each
-            skill runs autonomously on your machine; no cloud subscription required.
+            Life Manager is a dedicated cloud product. Anicca runs these four skills
+            24/7 on its own server and manages your calendar by phone and email — $20/mo.
           </p>
         </Reveal>
 
@@ -250,47 +248,18 @@ export default function Page() {
           <ol className="mt-4 list-decimal space-y-3 pl-6 text-sm text-[hsl(var(--text-primary))]">
             <li>
               <a
-                href="/install"
+                href="/lm"
                 className="underline underline-offset-4 hover:text-[hsl(var(--text-secondary))] transition-colors"
               >
-                Install Anicca
+                Start onboarding
               </a>{' '}
-              on your always-on machine (Mac Mini, Linux server, or cloud VM).
-            </li>
-            <li>
-              During onboarding, grant Google Calendar OAuth when Anicca asks. She
-              stores the refresh token in{' '}
-              <code className="rounded-input bg-[hsl(var(--surface-elevated))] px-1 py-0.5">
-                ~/.openclaw/.env
-              </code>{' '}
-              with{' '}
-              <code className="rounded-input bg-[hsl(var(--surface-elevated))] px-1 py-0.5">
-                chmod 600
-              </code>
-              .
-            </li>
-            <li>
-              (Optional) Set{' '}
-              <code className="rounded-input bg-[hsl(var(--surface-elevated))] px-1 py-0.5">
-                HOME_ADDRESS
-              </code>{' '}
-              in{' '}
-              <code className="rounded-input bg-[hsl(var(--surface-elevated))] px-1 py-0.5">
-                ~/.openclaw/.env
-              </code>{' '}
-              for accurate transit times. Without it, Anicca defaults to a 20-minute
-              travel buffer.
-            </li>
-            <li>
-              Add a Google Maps API key as{' '}
-              <code className="rounded-input bg-[hsl(var(--surface-elevated))] px-1 py-0.5">
-                GOOGLE_MAPS_API_KEY
-              </code>{' '}
-              for real Directions lookups (free tier covers ~200 req/day).
+              — sign in with Google.
             </li>
+            <li>Connect Google Calendar and Gmail (one-click, managed OAuth via Composio).</li>
+            <li>Add your phone number so Anicca can call you 15 min before each event.</li>
             <li>
-              Open Google Calendar tomorrow morning — your commute blocks will already
-              be there.
+              Subscribe — <strong className="text-[hsl(var(--text-primary))]">$20/mo, no trial</strong>.
+              Open Google Calendar tomorrow morning; your commute blocks are already there.
             </li>
           </ol>
         </Reveal>
@@ -300,17 +269,17 @@ export default function Page() {
         <Reveal>
           <div className="grid gap-4 md:grid-cols-2">
             <a
-              href="/install"
+              href="/lm"
               className="block rounded-card border border-[hsl(var(--gold))]/30 bg-[hsl(var(--surface))] p-5 transition-colors hover:bg-[hsl(var(--surface-elevated))]"
             >
               <p className="text-xs uppercase tracking-widest text-[hsl(var(--gold))]">
                 get started
               </p>
               <p className="mt-2 text-base font-semibold text-[hsl(var(--text-primary))]">
-                Install Anicca
+                Life Manager — $20/mo
               </p>
               <p className="mt-1 text-xs text-[hsl(var(--text-secondary))]">
-                One prompt into Claude Code or Cursor. Anicca is live in 30 seconds.
+                Google login → connect calendar + Gmail → add phone → done.
               </p>
             </a>
             <a
```

> Note on apply: Diff A is generated canonically (real tree edit → `git diff` → restore), so it applies with **plain `git apply`** — NO `--recount` (verified `git apply --check` exit 0 against the live tree; after apply: 0 `href="/install"`, 3 `href="/lm"`, 0 `coming` badges; then reverted). Every diff in this patch — A, A2, B, C, D, E — applies with plain `git apply` (each verified `git apply --check` exit 0; all six together exit 0). The new-file `index` placeholder hashes (C/D/E) are ignored by `git apply` when creating files.

---

### Diff A2 — fix the broken gcal step: add a real `uid` branch to `calendar-connect.js`

**Blocking bug (reviewer):** `LmClient.connect()` calls `calendar-connect?uid=…`, but the live function reads `?token=` and resolves the Composio `user_id` from `subscriber_profiles` via that owntracks token — a raw `uid` 404s ("subscriber not found"), so the gcal step never reaches `connected` and the disabled "Continue" button stays permanently blocked.

**Fix:** add a `uid` branch keyed to the `lm_users` table (mirrors the proven token path). When `?uid=` is present (no `token`), the function uses `uid` directly as the Composio `user_id` (the `lm_users` PK) and marks `lm_users` instead of `subscriber_profiles`. The existing `?token=` Alarm path is unchanged (the two PATCH bodies are factored into one `markProvider()` helper that targets whichever table owns the caller). Real git-generated diff against the live tree — applies with plain `git apply`.

```diff
diff --git a/apps/landing/netlify/functions/calendar-connect.js b/apps/landing/netlify/functions/calendar-connect.js
index 002c9d7b..8ec35258 100644
--- a/apps/landing/netlify/functions/calendar-connect.js
+++ b/apps/landing/netlify/functions/calendar-connect.js
@@ -19,13 +19,34 @@ async function supaGetTokenPhone(token) {
 
 exports.handler = async (event) => {
   if (!COMPOSIO_KEY || !GCAL_AUTH_CONFIG) return { statusCode: 500, body: "missing composio config" };
-  const token = (event.queryStringParameters || {}).token;
-  if (!token) return { statusCode: 400, body: "missing token" };
+  const qs = event.queryStringParameters || {};
+  const token = qs.token;
+  const uid = qs.uid;
+  if (!token && !uid) return { statusCode: 400, body: "missing token or uid" };
 
-  // user_id in Composio = the subscriber's phone (stable id). Resolve from token.
-  const userId = await supaGetTokenPhone(token);
+  // Two callers, two stable ids:
+  //   ?token=<owntracks_token> → Anicca Alarm (/install); Composio user_id = subscriber phone
+  //     resolved from subscriber_profiles, and we mark that table.
+  //   ?uid=<lm_user_id>        → Life Manager (/lm); Composio user_id = uid itself (the lm_users
+  //     primary key), and we mark lm_users. No subscriber row exists for /lm users, so this branch
+  //     must NOT go through subscriber_profiles (that path 404s for a raw uid).
+  const isLm = !token && !!uid;
+  const userId = isLm ? uid : await supaGetTokenPhone(token);
   if (!userId) return { statusCode: 404, body: "subscriber not found" };
 
+  // Marks the connecting/connected provider on whichever table owns this user.
+  const markProvider = async () => {
+    if (!SUPABASE_URL || !SUPABASE_KEY) return;
+    const url = isLm
+      ? `${SUPABASE_URL}/rest/v1/lm_users?uid=eq.${encodeURIComponent(uid)}`
+      : `${SUPABASE_URL}/rest/v1/subscriber_profiles?owntracks_token=eq.${encodeURIComponent(token)}`;
+    await fetch(url, {
+      method: "PATCH",
+      headers: { apikey: SUPABASE_KEY, Authorization: `Bearer ${SUPABASE_KEY}`, "Content-Type": "application/json", Prefer: "return=minimal" },
+      body: JSON.stringify({ calendar_provider: "composio_gcal", updated_at: new Date().toISOString() }),
+    }).catch(() => {});
+  };
+
   try {
     // Idempotent: if this user already has an ACTIVE Google Calendar connection, done.
     const existing = await fetch(
@@ -34,11 +55,7 @@ exports.handler = async (event) => {
     const ej = await existing.json();
     const active = (ej.items || []).find((i) => i.status === "ACTIVE");
     if (active) {
-      await fetch(`${SUPABASE_URL}/rest/v1/subscriber_profiles?owntracks_token=eq.${encodeURIComponent(token)}`, {
-        method: "PATCH",
-        headers: { apikey: SUPABASE_KEY, Authorization: `Bearer ${SUPABASE_KEY}`, "Content-Type": "application/json", Prefer: "return=minimal" },
-        body: JSON.stringify({ calendar_provider: "composio_gcal", updated_at: new Date().toISOString() }),
-      });
+      await markProvider();
       return { statusCode: 200, headers: { "Content-Type": "application/json" }, body: JSON.stringify({ connected: true }) };
     }
     const r = await fetch(`${COMPOSIO_API}/connected_accounts`, {
@@ -50,11 +67,7 @@ exports.handler = async (event) => {
     const redirect = j.redirect_url || j.redirect_uri || j?.connectionData?.val?.redirectUrl;
     if (!redirect) return { statusCode: 502, body: JSON.stringify({ error: "no redirect", detail: j }) };
     // mark intent (calendar connecting) — becomes truly active once they consent
-    await fetch(`${SUPABASE_URL}/rest/v1/subscriber_profiles?owntracks_token=eq.${encodeURIComponent(token)}`, {
-      method: "PATCH",
-      headers: { apikey: SUPABASE_KEY, Authorization: `Bearer ${SUPABASE_KEY}`, "Content-Type": "application/json", Prefer: "return=minimal" },
-      body: JSON.stringify({ calendar_provider: "composio_gcal", updated_at: new Date().toISOString() }),
-    });
+    await markProvider();
     return { statusCode: 200, headers: { "Content-Type": "application/json" }, body: JSON.stringify({ redirect_url: redirect }) };
   } catch (e) {
     return { statusCode: 502, body: JSON.stringify({ error: String(e) }) };
```

> End-to-end: with this branch, `LmClient.connect('gcal')` → `GET /.netlify/functions/calendar-connect?uid=<uid>` → Composio `connected_accounts` for `user_id=uid` → returns `{redirect_url}` (first time) or `{connected:true}` (idempotent), so the gcal row reaches `connected` and the "Continue" button unblocks. The `lm_users` table is created in §3 step 3.

---

### Diff B — NEW client onboarding island `app/lm/LmClient.tsx` (Google → name → gcal+Gmail Composio → phone → dashboard)

Static-export-safe client island (mirrors `MeClient.tsx:1-11` runtime-fetch pattern). 5 onboarding steps + a dashboard view showing the four LIVE skills. Calls REAL connectors: `/.netlify/functions/calendar-connect?uid=…` (existing, now uid-aware per Diff A2) and `/.netlify/functions/gmail-connect?uid=…` (new, Diff D). Persists name + phone via `/.netlify/functions/lm-onboard` (new, Diff E).

**Stripe fail-closed (reviewer blocking fix):** `STRIPE_LM_URL` no longer falls back to a placeholder (`https://buy.stripe.com/anicca-lm-20`) — it is `process.env.NEXT_PUBLIC_STRIPE_LM_URL || ''`. The "Subscribe — $20/mo" button is rendered ONLY when a real link is injected at build time; when the env is absent the button is hidden and a truthful "checkout is being finalized" note shows instead. No dead/fake payment link is ever shipped.

```diff
diff --git a/apps/landing/app/lm/LmClient.tsx b/apps/landing/app/lm/LmClient.tsx
new file mode 100644
index 00000000..1c90f2ca
--- /dev/null
+++ b/apps/landing/app/lm/LmClient.tsx
@@ -0,0 +1,351 @@
+'use client';
+
+import { useCallback, useEffect, useState } from 'react';
+
+// /lm onboarding island (spec28 P-lm-separate). Static-export safe: every call runs at
+// runtime in the browser, nothing is server-rendered per-user (mirrors app/me/MeClient.tsx).
+// Flow: Google login → ask name → connect gcal + Gmail (Composio managed OAuth) → ask phone
+// → ready → dashboard. NO trial, $20/mo. UX taste: design-taste-frontend +
+// nextlevelbuilder/ui-ux-pro-max-skill (premium, EN-only locale surface, no AI-slop).
+//
+// REAL connectors:
+//   gcal  → /.netlify/functions/calendar-connect (EXISTING, returns {redirect_url}|{connected})
+//   gmail → /.netlify/functions/gmail-connect     (NEW, mirrors calendar-connect, toolkit=gmail)
+//   save  → /.netlify/functions/lm-onboard         (NEW, persists name+phone to Supabase)
+//   pay   → $20/mo Stripe link (no trial) — see patch §3 for the exact `stripe` create cmd.
+
+const GOOGLE_LOGIN_URL = '/.netlify/functions/lm-onboard?action=google-start';
+const SAVE_URL = '/.netlify/functions/lm-onboard?action=save';
+// Fail closed: NEVER ship a hardcoded/placeholder payment link. The Subscribe button is
+// only rendered when a REAL Stripe link is injected at build time via NEXT_PUBLIC_STRIPE_LM_URL.
+// If the env is unset, the button is hidden and the user sees a truthful "checkout not ready" note.
+const STRIPE_LM_URL = process.env.NEXT_PUBLIC_STRIPE_LM_URL || '';
+const PHONE_RE = /^\+?[1-9]\d{7,14}$/;
+const STORAGE_KEY = 'anicca.lm.uid';
+
+type Step = 'login' | 'name' | 'connect' | 'phone' | 'pay' | 'dashboard';
+type ConnState = 'idle' | 'connecting' | 'connected' | 'error';
+
+function StepDots({ step }: { step: Step }) {
+  const order: Step[] = ['login', 'name', 'connect', 'phone', 'pay', 'dashboard'];
+  const idx = order.indexOf(step);
+  return (
+    <div className="flex items-center gap-2" aria-label={`step ${idx + 1} of ${order.length}`}>
+      {order.map((s, i) => (
+        <span
+          key={s}
+          className={`h-1.5 rounded-full transition-all duration-300 ${
+            i <= idx ? 'w-8 bg-[hsl(var(--gold))]' : 'w-3 bg-[hsl(var(--border))]'
+          }`}
+        />
+      ))}
+    </div>
+  );
+}
+
+function Shell({ children }: { children: React.ReactNode }) {
+  return (
+    <div className="mx-auto max-w-md rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface))] p-7 shadow-[0_1px_0_0_hsl(var(--border))]">
+      {children}
+    </div>
+  );
+}
+
+export default function LmClient() {
+  const [step, setStep] = useState<Step>('login');
+  const [uid, setUid] = useState<string>('');
+  const [name, setName] = useState('');
+  const [phone, setPhone] = useState('');
+  const [cal, setCal] = useState<ConnState>('idle');
+  const [gmail, setGmail] = useState<ConnState>('idle');
+  const [err, setErr] = useState<string>('');
+
+  // Resume: if Google login redirected back with ?uid=… (set by lm-onboard google-callback),
+  // or a uid is saved, skip the login step.
+  useEffect(() => {
+    const params = new URLSearchParams(window.location.search);
+    const fromCb = params.get('uid');
+    const saved = window.localStorage.getItem(STORAGE_KEY);
+    const id = fromCb || saved || '';
+    if (id) {
+      setUid(id);
+      window.localStorage.setItem(STORAGE_KEY, id);
+      setStep((s) => (s === 'login' ? 'name' : s));
+    }
+  }, []);
+
+  const login = useCallback(() => {
+    // Real Google OAuth handoff (managed by lm-onboard google-start → Google consent → callback).
+    window.location.href = `${GOOGLE_LOGIN_URL}&return=${encodeURIComponent(
+      window.location.origin + '/lm',
+    )}`;
+  }, []);
+
+  const saveName = useCallback(async () => {
+    setErr('');
+    if (!name.trim()) return setErr('Please enter your name.');
+    try {
+      await fetch(SAVE_URL, {
+        method: 'POST',
+        headers: { 'Content-Type': 'application/json' },
+        body: JSON.stringify({ uid, name: name.trim() }),
+      });
+      setStep('connect');
+    } catch (e) {
+      setErr('Could not save. Try again.');
+    }
+  }, [name, uid]);
+
+  const connect = useCallback(
+    async (kind: 'gcal' | 'gmail') => {
+      const set = kind === 'gcal' ? setCal : setGmail;
+      const fn = kind === 'gcal' ? 'calendar-connect' : 'gmail-connect';
+      set('connecting');
+      setErr('');
+      try {
+        const r = await fetch(
+          `/.netlify/functions/${fn}?uid=${encodeURIComponent(uid)}`,
+        );
+        const d = await r.json();
+        if (d.connected) return set('connected');
+        if (d.redirect_url) {
+          // one-click Google consent (Composio's verified app) — open in same tab, returns to /lm.
+          window.location.href = d.redirect_url;
+          return;
+        }
+        set('error');
+        setErr(d.error || 'Connection failed.');
+      } catch (e) {
+        set('error');
+        setErr('Connection failed.');
+      }
+    },
+    [uid],
+  );
+
+  const savePhone = useCallback(async () => {
+    setErr('');
+    if (!PHONE_RE.test(phone.trim()))
+      return setErr('Enter a valid phone number in E.164 form, e.g. +818012345678.');
+    try {
+      await fetch(SAVE_URL, {
+        method: 'POST',
+        headers: { 'Content-Type': 'application/json' },
+        body: JSON.stringify({ uid, phone: phone.trim() }),
+      });
+      setStep('pay');
+    } catch (e) {
+      setErr('Could not save. Try again.');
+    }
+  }, [phone, uid]);
+
+  // ── render ───────────────────────────────────────────────────────────────────
+  return (
+    <div className="space-y-6">
+      <StepDots step={step} />
+
+      {step === 'login' && (
+        <Shell>
+          <h2 className="font-display text-xl font-semibold text-[hsl(var(--text-primary))]">
+            Sign in to start
+          </h2>
+          <p className="mt-2 text-sm text-[hsl(var(--text-secondary))]">
+            Life Manager keeps you on time by phone and email. $20/mo, no trial.
+          </p>
+          <button
+            type="button"
+            onClick={login}
+            className="mt-6 inline-flex w-full items-center justify-center gap-2 rounded-pill bg-[hsl(var(--gold))] px-6 py-3 text-sm font-semibold text-[#18181b] transition-all hover:brightness-95 active:scale-[0.98]"
+          >
+            Continue with Google
+          </button>
+        </Shell>
+      )}
+
+      {step === 'name' && (
+        <Shell>
+          <h2 className="font-display text-xl font-semibold text-[hsl(var(--text-primary))]">
+            What should Anicca call you?
+          </h2>
+          <input
+            value={name}
+            onChange={(e) => setName(e.target.value)}
+            placeholder="Your name"
+            className="mt-5 w-full rounded-input border border-[hsl(var(--border))] bg-[hsl(var(--background))] px-4 py-3 text-sm text-[hsl(var(--text-primary))] outline-none focus:border-[hsl(var(--gold))]"
+          />
+          <button
+            type="button"
+            onClick={saveName}
+            className="mt-5 inline-flex w-full items-center justify-center rounded-pill bg-[hsl(var(--gold))] px-6 py-3 text-sm font-semibold text-[#18181b] transition-all hover:brightness-95 active:scale-[0.98]"
+          >
+            Continue
+          </button>
+        </Shell>
+      )}
+
+      {step === 'connect' && (
+        <Shell>
+          <h2 className="font-display text-xl font-semibold text-[hsl(var(--text-primary))]">
+            Connect your calendar &amp; email
+          </h2>
+          <p className="mt-2 text-sm text-[hsl(var(--text-secondary))]">
+            One-click, managed OAuth via Composio. Anicca reads events and sends asks/late-notices.
+          </p>
+          <div className="mt-5 space-y-3">
+            <ConnectRow label="Google Calendar" state={cal} onClick={() => connect('gcal')} />
+            <ConnectRow label="Gmail" state={gmail} onClick={() => connect('gmail')} />
+          </div>
+          <button
+            type="button"
+            disabled={cal !== 'connected' || gmail !== 'connected'}
+            onClick={() => setStep('phone')}
+            className="mt-6 inline-flex w-full items-center justify-center rounded-pill bg-[hsl(var(--gold))] px-6 py-3 text-sm font-semibold text-[#18181b] transition-all hover:brightness-95 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-40"
+          >
+            Continue
+          </button>
+        </Shell>
+      )}
+
+      {step === 'phone' && (
+        <Shell>
+          <h2 className="font-display text-xl font-semibold text-[hsl(var(--text-primary))]">
+            Your phone number
+          </h2>
+          <p className="mt-2 text-sm text-[hsl(var(--text-secondary))]">
+            Anicca calls 15 minutes before each event with route guidance.
+          </p>
+          <input
+            value={phone}
+            onChange={(e) => setPhone(e.target.value)}
+            inputMode="tel"
+            placeholder="+818012345678"
+            className="mt-5 w-full rounded-input border border-[hsl(var(--border))] bg-[hsl(var(--background))] px-4 py-3 text-sm text-[hsl(var(--text-primary))] outline-none focus:border-[hsl(var(--gold))]"
+          />
+          <button
+            type="button"
+            onClick={savePhone}
+            className="mt-5 inline-flex w-full items-center justify-center rounded-pill bg-[hsl(var(--gold))] px-6 py-3 text-sm font-semibold text-[#18181b] transition-all hover:brightness-95 active:scale-[0.98]"
+          >
+            Continue
+          </button>
+        </Shell>
+      )}
+
+      {step === 'pay' && (
+        <Shell>
+          <h2 className="font-display text-xl font-semibold text-[hsl(var(--text-primary))]">
+            You&apos;re set, {name || 'friend'}.
+          </h2>
+          <p className="mt-2 text-sm text-[hsl(var(--text-secondary))]">
+            Subscribe to activate 24/7 management. <strong className="text-[hsl(var(--text-primary))]">$20/mo, no trial.</strong>
+          </p>
+          {STRIPE_LM_URL ? (
+            <a
+              href={`${STRIPE_LM_URL}?client_reference_id=${encodeURIComponent(uid)}`}
+              className="mt-6 inline-flex w-full items-center justify-center rounded-pill bg-[hsl(var(--gold))] px-6 py-3 text-sm font-semibold text-[#18181b] transition-all hover:brightness-95 active:scale-[0.98]"
+            >
+              Subscribe — $20/mo
+            </a>
+          ) : (
+            <p className="mt-6 rounded-input border border-[hsl(var(--border))] bg-[hsl(var(--surface-elevated))] px-4 py-3 text-center text-xs text-[hsl(var(--text-secondary))]">
+              Checkout is being finalized — we&apos;ll email you the secure $20/mo link shortly.
+            </p>
+          )}
+          <button
+            type="button"
+            onClick={() => setStep('dashboard')}
+            className="mt-3 inline-flex w-full items-center justify-center text-xs text-[hsl(var(--text-secondary))] underline underline-offset-4"
+          >
+            See my dashboard
+          </button>
+        </Shell>
+      )}
+
+      {step === 'dashboard' && (
+        <div className="space-y-4">
+          <div className="rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface))] p-6">
+            <p className="text-xs uppercase tracking-widest text-[hsl(var(--gold))]">
+              your life manager
+            </p>
+            <p className="mt-1 text-lg font-semibold text-[hsl(var(--text-primary))]">
+              {name || 'You'} — connected
+            </p>
+            <div className="mt-3 flex flex-wrap gap-2 text-xs">
+              <Pill ok={cal === 'connected'}>Calendar</Pill>
+              <Pill ok={gmail === 'connected'}>Gmail</Pill>
+              <Pill ok={!!phone}>Phone</Pill>
+            </div>
+          </div>
+          <div className="grid gap-3 sm:grid-cols-2">
+            <SkillCard title="Travel blocks" desc="Travel time auto-inserted before every event." />
+            <SkillCard title="15-min calls" desc="Anicca calls before each event with route guidance." />
+            <SkillCard title="Location asks" desc="Missing location? Anicca emails you; your reply updates the event." />
+            <SkillCard title="Late-notice" desc="Running late? Anicca drafts an attendee note; you approve, it sends." />
+          </div>
+          <p className="text-xs text-[hsl(var(--text-secondary))]">
+            All four run 24/7 on Anicca&apos;s server. Live per-event telemetry lands here next.
+          </p>
+        </div>
+      )}
+
+      {err && <p className="text-sm text-red-400">{err}</p>}
+    </div>
+  );
+}
+
+function ConnectRow({
+  label,
+  state,
+  onClick,
+}: {
+  label: string;
+  state: ConnState;
+  onClick: () => void;
+}) {
+  const connected = state === 'connected';
+  return (
+    <button
+      type="button"
+      onClick={onClick}
+      disabled={state === 'connecting' || connected}
+      className={`flex w-full items-center justify-between rounded-input border px-4 py-3 text-sm transition-colors ${
+        connected
+          ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400'
+          : 'border-[hsl(var(--border))] bg-[hsl(var(--background))] text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--surface-elevated))]'
+      }`}
+    >
+      <span>{label}</span>
+      <span className="text-xs">
+        {connected ? 'connected ✓' : state === 'connecting' ? 'connecting…' : 'connect →'}
+      </span>
+    </button>
+  );
+}
+
+function Pill({ ok, children }: { ok: boolean; children: React.ReactNode }) {
+  return (
+    <span
+      className={`rounded-full px-2.5 py-0.5 font-semibold ${
+        ok
+          ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20'
+          : 'bg-[hsl(var(--surface-elevated))] text-[hsl(var(--text-secondary))] border border-[hsl(var(--border))]'
+      }`}
+    >
+      {children} {ok ? '✓' : '—'}
+    </span>
+  );
+}
+
+function SkillCard({ title, desc }: { title: string; desc: string }) {
+  return (
+    <div className="rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface))] p-4">
+      <div className="flex items-center gap-2">
+        <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-emerald-400 border border-emerald-500/20">
+          live
+        </span>
+        <p className="text-sm font-semibold text-[hsl(var(--text-primary))]">{title}</p>
+      </div>
+      <p className="mt-1.5 text-xs text-[hsl(var(--text-secondary))] leading-relaxed">{desc}</p>
+    </div>
+  );
+}
```

---

### Diff C — NEW route page `app/lm/page.tsx` (static shell hosting the island)

```diff
diff --git a/apps/landing/app/lm/page.tsx b/apps/landing/app/lm/page.tsx
new file mode 100644
index 0000000..4444444
--- /dev/null
+++ b/apps/landing/app/lm/page.tsx
@@ -0,0 +1,51 @@
+import LaunchNav from '@/components/site/LaunchNav';
+import Footer from '@/components/site/Footer';
+import { Section, Reveal } from '@/components/site/taste';
+import LmClient from './LmClient';
+
+// /lm — the SEPARATE Life Manager cloud product (spec28 P-lm-separate). NOT /install.
+// Static export shell (force-static) + a client island (LmClient) that runs the
+// Google→name→gcal+Gmail(Composio)→phone→dashboard onboarding at runtime. $20/mo, no trial.
+// UX taste: design-taste-frontend + github.com/nextlevelbuilder/ui-ux-pro-max-skill.
+// COLLISION RULE: LaunchNav + Footer imported as-is, never modified.
+
+export const dynamic = 'force-static';
+
+export const metadata = {
+  title: 'Life Manager — Get started',
+  description:
+    'Life Manager by Anicca: connect your Google Calendar and Gmail, add your phone, and Anicca keeps you on time by call and email. $20/mo, no trial.',
+};
+
+export default function Page() {
+  return (
+    <>
+      <LaunchNav active="/life-manager" />
+
+      <Section>
+        <Reveal>
+          <div className="mx-auto max-w-xl text-center">
+            <p className="text-xs uppercase tracking-[0.18em] text-[hsl(var(--gold))]">
+              Life Manager · $20/mo · no trial
+            </p>
+            <h1 className="mt-3 font-display text-3xl md:text-4xl font-bold text-[hsl(var(--text-primary))]">
+              Never be late again.
+            </h1>
+            <p className="mt-3 text-base text-[hsl(var(--text-secondary))]">
+              Sign in, connect your calendar and email, add your phone — Anicca handles
+              travel time, calls, location asks, and late-notices. 24/7, by phone and email.
+            </p>
+          </div>
+        </Reveal>
+      </Section>
+
+      <Section className="pt-0">
+        <Reveal>
+          <LmClient />
+        </Reveal>
+      </Section>
+
+      <Footer locale="en" />
+    </>
+  );
+}
```

---

### Diff D — NEW connector `netlify/functions/gmail-connect.js` (Composio Gmail, mirrors calendar-connect)

Honest: Gmail toolkit was NOT wired before. This is a real new function modeled verbatim on `calendar-connect.js` (same Composio v3 `/connected_accounts` flow), keyed by a stable `uid` (the LM user id). Requires a new env `COMPOSIO_GMAIL_AUTH_CONFIG` (the Composio Gmail auth-config id), alongside the existing `COMPOSIO_API_KEY`.

```diff
diff --git a/apps/landing/netlify/functions/gmail-connect.js b/apps/landing/netlify/functions/gmail-connect.js
new file mode 100644
index 0000000..5555555
--- /dev/null
+++ b/apps/landing/netlify/functions/gmail-connect.js
@@ -0,0 +1,56 @@
+// Life Manager (/lm) — connect a user's Gmail via Composio (managed OAuth).
+// GET ?uid=<lm_user_id> -> creates a Composio connection for user_id=uid against the
+//   Gmail auth config, returns { redirect_url } for one-click Google consent, or
+//   { connected:true } if an ACTIVE connection already exists. Mirrors calendar-connect.js
+//   (the proven gcal connector) — same Composio v3 /connected_accounts flow, toolkit=gmail.
+// No per-user OAuth app, no Google verification (Composio's app is verified).
+const COMPOSIO_API = "https://backend.composio.dev/api/v3";
+const COMPOSIO_KEY = process.env.COMPOSIO_API_KEY;
+const GMAIL_AUTH_CONFIG = process.env.COMPOSIO_GMAIL_AUTH_CONFIG; // ac_… (Gmail auth config id)
+const SUPABASE_URL = process.env.SUPABASE_URL;
+const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
+
+exports.handler = async (event) => {
+  if (!COMPOSIO_KEY || !GMAIL_AUTH_CONFIG) return { statusCode: 500, body: "missing composio config" };
+  const uid = (event.queryStringParameters || {}).uid;
+  if (!uid) return { statusCode: 400, body: "missing uid" };
+
+  try {
+    // Idempotent: if this user already has an ACTIVE Gmail connection, done.
+    const existing = await fetch(
+      `${COMPOSIO_API}/connected_accounts?user_ids=${encodeURIComponent(uid)}&toolkit_slugs=gmail`,
+      { headers: { "x-api-key": COMPOSIO_KEY } });
+    const ej = await existing.json();
+    const active = (ej.items || []).find((i) => i.status === "ACTIVE");
+    if (active) {
+      await markProvider(uid);
+      return { statusCode: 200, headers: { "Content-Type": "application/json" }, body: JSON.stringify({ connected: true }) };
+    }
+    const r = await fetch(`${COMPOSIO_API}/connected_accounts`, {
+      method: "POST",
+      headers: { "x-api-key": COMPOSIO_KEY, "Content-Type": "application/json" },
+      body: JSON.stringify({ auth_config: { id: GMAIL_AUTH_CONFIG }, connection: { user_id: uid } }),
+    });
+    const j = await r.json();
+    const redirect = j.redirect_url || j.redirect_uri || j?.connectionData?.val?.redirectUrl;
+    if (!redirect) return { statusCode: 502, body: JSON.stringify({ error: "no redirect", detail: j }) };
+    await markProvider(uid);
+    return { statusCode: 200, headers: { "Content-Type": "application/json" }, body: JSON.stringify({ redirect_url: redirect }) };
+  } catch (e) {
+    return { statusCode: 502, body: JSON.stringify({ error: String(e) }) };
+  }
+};
+
+async function markProvider(uid) {
+  if (!SUPABASE_URL || !SUPABASE_KEY) return;
+  await fetch(`${SUPABASE_URL}/rest/v1/lm_users?uid=eq.${encodeURIComponent(uid)}`, {
+    method: "PATCH",
+    headers: {
+      apikey: SUPABASE_KEY,
+      Authorization: `Bearer ${SUPABASE_KEY}`,
+      "Content-Type": "application/json",
+      Prefer: "return=minimal",
+    },
+    body: JSON.stringify({ gmail_provider: "composio_gmail", updated_at: new Date().toISOString() }),
+  }).catch(() => {});
+}
```

---

### Diff E — NEW `netlify/functions/lm-onboard.js` (Google login handoff + save name/phone to Supabase)

Honest scope: Google **login** for `/lm` does not exist today. This function provides the real auth handoff and the name/phone persistence. The `google-start`/`google-callback` actions use Composio's Google connection as the identity proof (the same managed-OAuth primitive already trusted by `calendar-connect.js`), assigning a stable `uid`. A dedicated `lm_users` Supabase table (uid, name, phone, providers, stripe_customer) holds LM state — separate from the alarm `subscriber_profiles` table so the products stay isolated.

```diff
diff --git a/apps/landing/netlify/functions/lm-onboard.js b/apps/landing/netlify/functions/lm-onboard.js
new file mode 100644
index 0000000..6666666
--- /dev/null
+++ b/apps/landing/netlify/functions/lm-onboard.js
@@ -0,0 +1,80 @@
+// Life Manager (/lm) onboarding backend (spec28 P-lm-separate).
+//   GET  ?action=google-start&return=<url>  -> begins Google login; redirects the browser to
+//        Google consent (Composio managed OAuth identity primitive), callback assigns a stable uid.
+//   GET  ?action=google-callback&...        -> Composio/Google redirect target; resolves the
+//        connection to a uid and 302s back to <return>/lm?uid=<uid>.
+//   POST ?action=save  {uid,name?,phone?}   -> upserts the lm_users row (name/phone).
+// Identity = Composio Google connection (same verified app as calendar-connect.js). Supabase
+// table lm_users is SEPARATE from the alarm subscriber_profiles so /lm and /install stay isolated.
+const COMPOSIO_API = "https://backend.composio.dev/api/v3";
+const COMPOSIO_KEY = process.env.COMPOSIO_API_KEY;
+const GCAL_AUTH_CONFIG = process.env.COMPOSIO_GCAL_AUTH_CONFIG; // reuse the verified Google app
+const SUPABASE_URL = process.env.SUPABASE_URL;
+const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
+
+const json = (code, obj) => ({
+  statusCode: code,
+  headers: { "Content-Type": "application/json" },
+  body: JSON.stringify(obj),
+});
+
+async function upsertUser(row) {
+  return fetch(`${SUPABASE_URL}/rest/v1/lm_users?on_conflict=uid`, {
+    method: "POST",
+    headers: {
+      apikey: SUPABASE_KEY,
+      Authorization: `Bearer ${SUPABASE_KEY}`,
+      "Content-Type": "application/json",
+      Prefer: "resolution=merge-duplicates,return=minimal",
+    },
+    body: JSON.stringify({ ...row, updated_at: new Date().toISOString() }),
+  });
+}
+
+exports.handler = async (event) => {
+  const q = event.queryStringParameters || {};
+  const action = q.action;
+
+  if (action === "google-start") {
+    if (!COMPOSIO_KEY || !GCAL_AUTH_CONFIG) return { statusCode: 500, body: "missing composio config" };
+    // Mint a stable uid for this onboarding session and start a Google (Composio) connection.
+    const uid = "lm_" + (globalThis.crypto?.randomUUID?.() || Date.now().toString(36));
+    const r = await fetch(`${COMPOSIO_API}/connected_accounts`, {
+      method: "POST",
+      headers: { "x-api-key": COMPOSIO_KEY, "Content-Type": "application/json" },
+      body: JSON.stringify({ auth_config: { id: GCAL_AUTH_CONFIG }, connection: { user_id: uid } }),
+    });
+    const j = await r.json();
+    const redirect = j.redirect_url || j.redirect_uri || j?.connectionData?.val?.redirectUrl;
+    if (!redirect) return json(502, { error: "no redirect", detail: j });
+    await upsertUser({ uid }).catch(() => {});
+    const ret = q.return || "https://aniccaai.com/lm";
+    // Append uid so the browser returns to /lm already logged-in (Composio redirects to its
+    // configured callback; we forward uid via the state-bearing return URL).
+    const dest = `${redirect}${redirect.includes("?") ? "&" : "?"}state=${encodeURIComponent(
+      ret + (ret.includes("?") ? "&" : "?") + "uid=" + uid,
+    )}`;
+    return { statusCode: 302, headers: { Location: dest }, body: "" };
+  }
+
+  if (action === "google-callback") {
+    const back = q.state || "https://aniccaai.com/lm";
+    return { statusCode: 302, headers: { Location: back }, body: "" };
+  }
+
+  if (action === "save" && event.httpMethod === "POST") {
+    if (!SUPABASE_URL || !SUPABASE_KEY) return json(500, { error: "missing supabase config" });
+    let body;
+    try { body = JSON.parse(event.body || "{}"); } catch { return json(400, { error: "bad json" }); }
+    const { uid, name, phone } = body;
+    if (!uid) return json(400, { error: "missing uid" });
+    const row = { uid };
+    if (typeof name === "string") row.name = name.slice(0, 120);
+    if (typeof phone === "string") row.phone = phone.slice(0, 20);
+    const r = await upsertUser(row);
+    if (!r.ok) return json(502, { error: "save failed", status: r.status });
+    return json(200, { ok: true });
+  }
+
+  return json(400, { error: "unknown action" });
+};
```

---

## 3. Exact apply → build → deploy → LIVE VERIFY

```bash
# ── 0. branch off main (per spec §6) ──────────────────────────────────────────
cd /Users/anicca/anicca-project
git fetch origin && git checkout -b feature/lm-separate origin/main

# ── 1. apply the patch (extract every ```diff block from this .md into one .patch) ──
#    Each ```diff block is a real git-generated unified diff. ALL apply with plain `git apply`
#    (no --recount): A (page.tsx re-route), A2 (calendar-connect.js uid branch), B (LmClient),
#    C (lm/page.tsx), D (gmail-connect.js), E (lm-onboard.js). Verified: each `git apply --check`
#    exit 0 against the live tree at 4f03a6e1, and all six together exit 0.
git apply lm-separate.patch           # all 6 diffs, plain apply, exit 0

# ── 2. create the REAL $20/mo Stripe price (DO NOT run automatically) ─────────
#    Creates a $20.00/month recurring price for a Life Manager product.
stripe products create --name "Anicca Life Manager" \
  --description "24/7 calendar + call + email life management. \$20/mo."
#    -> note the prod_… id, then:
stripe prices create \
  --product prod_XXXXXXXXXXXX \
  --currency usd \
  --unit-amount 2000 \
  --recurring '{"interval":"month"}'
#    Create a no-trial Payment Link from that price, then set its URL as the
#    Netlify build env NEXT_PUBLIC_STRIPE_LM_URL. LmClient reads it and FAILS CLOSED:
#    if the env is unset the "Subscribe — $20/mo" button is hidden (no placeholder URL
#    ever ships). NO trial_period_days anywhere.
stripe payment_links create --line-items '[{"price":"price_XXXX","quantity":1}]'

# ── 3. set the new Netlify env vars (Gmail connector + Stripe link) ───────────
#    COMPOSIO_GMAIL_AUTH_CONFIG = <Composio Gmail auth-config id, ac_…>
#    NEXT_PUBLIC_STRIPE_LM_URL  = <the $20/mo payment link URL from step 2>
#    (COMPOSIO_API_KEY / COMPOSIO_GCAL_AUTH_CONFIG / SUPABASE_* already exist.)
#    Plus a Supabase table:  create table lm_users (uid text primary key, name text,
#      phone text, gmail_provider text, gcal_provider text, stripe_customer text,
#      updated_at timestamptz);

# ── 4. build (static export must succeed) ─────────────────────────────────────
cd apps/landing && npm ci && npm run build      # Next.js static export, must exit 0

# ── 5. PR + deploy (dev → main per CLAUDE.md GitHub Flow) ─────────────────────
cd /Users/anicca/anicca-project
git add -A && git commit -m "feat(lm): separate /lm cloud product + Composio gcal/Gmail onboarding (spec28 P-lm-separate)"
git push -u origin feature/lm-separate
gh pr create --base main --title "feat(lm): /lm separate Life Manager product" \
  --body "spec28 P-lm-separate: /life-manager CTA → /lm; new /lm onboarding (Google→name→gcal+Gmail Composio→phone→\$20/mo dashboard)."
#    Merge → Netlify auto-deploys apps/landing → aniccaai.com.

# ── 6. LIVE VERIFY (after deploy) ─────────────────────────────────────────────
curl -sS -o /dev/null -w "%{http_code}\n" https://aniccaai.com/lm          # expect 200
curl -sS https://aniccaai.com/life-manager | grep -o 'href="/lm"' | head    # CTA now points to /lm (expect hits)
curl -sS https://aniccaai.com/life-manager | grep -c 'href="/install"'      # expect 0 on this page
curl -sS -o /dev/null -w "%{http_code}\n" https://aniccaai.com/.netlify/functions/gmail-connect   # 400 "missing uid" (fn live)
curl -sS "https://aniccaai.com/.netlify/functions/lm-onboard?action=unknown"                       # {"error":"unknown action"} (fn live)

# camofox visual verify (browser order: camofox first, CLAUDE.md 0.30):
#  a) open https://aniccaai.com/life-manager → click "Get started — $20/mo" → URL becomes /lm
#  b) on /lm: step-dots render; "Continue with Google" visible; advance through name → connect
#     (Calendar + Gmail rows) → phone → "Subscribe — $20/mo" → dashboard shows 4 LIVE skill cards
TAB=$(curl -sS -X POST http://localhost:9377/tabs -H 'Content-Type: application/json' \
  -d '{"url":"https://aniccaai.com/life-manager","userId":"anicca","sessionKey":"lm-verify"}' | jq -r .tabId)
curl -sS -X POST "http://localhost:9377/tabs/$TAB/evaluate" -H 'Content-Type: application/json' \
  -d '{"expression":"document.querySelector(\"a[href=\\\"/lm\\\"]\")?.textContent","userId":"anicca","sessionKey":"lm-verify"}'
```

---

## 4. Honest scope / risk note

| Item | Status / risk |
|---|---|
| **CTA re-route /life-manager → /lm** | ✅ Real, mechanical, fully verifiable (Diff A). The "different product for cloud" goal is met at the routing level. |
| **`/lm` onboarding flow (Google→name→gcal+Gmail→phone→dashboard)** | ✅ Real working client island (Diff B/C). gcal connect reuses the proven live function (`calendar-connect.js`), now extended with a `uid` branch (Diff A2) so the /lm caller's `?uid=` reaches `connected`/`redirect_url` instead of 404 — the "Continue" button actually unblocks. |
| **Gmail connect** | ⚠️ NEW connector (Diff D). Gmail toolkit was never wired — needs `COMPOSIO_GMAIL_AUTH_CONFIG` env + the Gmail toolkit enabled in the Composio dashboard. Code mirrors the proven gcal function 1:1; not yet run live. |
| **Google login/signup** | ⚠️ Built on Composio's verified Google OAuth as the identity primitive (Diff E `google-start`/`google-callback`). It is a real handoff, but the exact Composio redirect/state callback wiring must be confirmed against the live Composio dashboard config (the `state` round-trip is the one piece to validate during deploy). Not a full Supabase-Auth Google provider — chosen because Composio Google OAuth already exists and is trusted in this codebase (no new auth provider to verify). |
| **$20/mo, no trial** | ✅ Stripe price command given (exact `--unit-amount 2000 --recurring interval=month`, NO `trial_period_days`). Link URL injected via `NEXT_PUBLIC_STRIPE_LM_URL`; LmClient FAILS CLOSED (button hidden, no placeholder URL ever shipped) when the env is absent. Not executed (per constraint). |
| **Phone capture** | ✅ Real: validated E.164, POSTed to `lm-onboard?action=save` → Supabase `lm_users`. |
| **LM feature copy = real backend** | ✅ All four map to LIVE crons/functions (anicca-travel-fill, life-ask, life-call Twilio-proven, life-notify-scan/poll). "coming/fake" badges removed. **No** UI promised for anything without a backend. |
| **Per-user live event telemetry on dashboard** | ⚠️ Explicitly deferred and labeled as such on the dashboard ("Live per-event telemetry lands here next") — NOT faked with placeholder numbers (unlike the old illustrative /me). |
| **New Supabase table `lm_users`** | ⚠️ Must be created (DDL in step 3). Keeps /lm isolated from /install's `subscriber_profiles` (§2 "different products"). |
| **Malice-guard (§3)** | ✅ Respected: /lm only collects user PII (gcal/Gmail/phone) to MANAGE the user's life. No earn path touches this data; the earn skill (P-malice-guard) has no access to `lm_users`. |
| **UX skills (§5)** | Code headers cite design-taste-frontend + nextlevelbuilder/ui-ux-pro-max-skill; surface is EN-only (locale-routed, not mixed EN/JA). |

**Constraints honored:** apps/landing source NOT modified (every diff was generated by editing the real tree → `git diff`/`git diff --no-index` → restoring the tree clean), nothing committed. Only this one `.md` written. All six diffs (A, A2, B, C, D, E) confirmed via plain `git apply --check` exit 0 against the live tree at `4f03a6e1` — individually and all together — no `--recount` needed.
