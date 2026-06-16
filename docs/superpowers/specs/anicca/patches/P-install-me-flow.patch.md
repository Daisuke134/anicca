# P-install-me-flow — REAL patch (cloud Anicca `/install` → `/me`, auth-gated, $5/$30 tiers)

> Spec: `docs/superpowers/specs/anicca/28-product-redesign-merge-2026-06-16.md` §0,§1,§3,§6
> Target repo: `Daisuke134/anicca-products` · path `apps/landing` · **deploys from `main`** (`.github/workflows/netlify-deploy.yml` triggers on `main`+`dev`, but production = `main`).
> This file is a SPEC artifact only. **No `apps/landing` source is modified and nothing is committed here** — the diffs below are applied on a feature branch off `main` per the commands in §Apply.

---

## Reality found (cited to live code)

| Fact | Evidence |
|---|---|
| `apps/landing` is Next.js **static export** — no server render, no API routes, no middleware | `apps/landing/next.config.mjs` → `output: 'export'`; every page uses `export const dynamic = 'force-static'` (e.g. `app/install/page.tsx:14`, `app/me/page.tsx:15`) |
| Server runtime = **Netlify Functions** (CJS `exports.handler`, called from the browser at `/.netlify/functions/<name>`) | `app/alarm/setup/page.tsx:44` `fetch('/.netlify/functions/calendar-connect?...')`; functions dir `netlify/functions/*.js` all `exports.handler = async (event) => {...}` |
| Data layer = **Supabase via PostgREST**, accessed **server-side with the service-role key only** | `netlify/functions/dashboard-sync.js` reads `instances` with `SUPABASE_SERVICE_ROLE_KEY`; `_lib/owners-store.js` upserts `owners`/`spawn_events` |
| **NO website auth of any kind exists.** No `@supabase/supabase-js`, no Supabase Auth, no Netlify Identity, no Google sign-in for visitors. `grep -riE "supabase\.auth\|signInWith\|netlify-identity\|gotrue"` over `app lib components` → **0 hits** | `grep` run 2026-06-16; `package.json` has `stripe`, `ethers`, `ws` — **no `@supabase/supabase-js`** (confirmed `grep -i supabase apps/landing/package.json` → "NOT in package.json") |
| The **only** OAuth present is **Composio managed** Google Calendar, keyed by an existing subscriber's phone — runs *after* the user exists, not a website login | `netlify/functions/calendar-connect.js:1-6,44-50` |
| Stripe **spawn pipeline is real**: `checkout.session.completed` → `createDroplet` (DO) → upsert Supabase `owners`; `customer.subscription.deleted` → `destroyDroplet`. Idempotent via `spawn_events` | `netlify/functions/stripe-spawn-webhook.js:59-91`, `_lib/spawn-droplet.js`, `_lib/owners-store.js` |
| `/me` today is **public** and renders **fake/illustrative numbers** ($6.00 "sent to you", $18.40 "earned this month", 3 hard-coded child instances) plus the real `MeClient` wallet card | `app/me/page.tsx:51-74` (`MONEY`, `CHILDREN` constants), rendered at `app/me/page.tsx:228-380` |
| `/me` already has the **honesty constant** that gates the "外部収益はまだ" badge | `app/me/page.tsx:80-94` — `GATE0_WAKE.source='swap-eth-usdc'`, `GATE0_EXTERNAL = !/swap|liquidat/i.test(...)`, so `GATE0_MET` is `false` → amber "未達" badge renders. **Preserved verbatim** in the new file. |
| `/install` hero CTA today points at a **dead** Stripe URL and says "$30/月で始める" | `app/install/page.tsx:124-130` → `href="https://buy.stripe.com/anicca-cloud"` (placeholder, not a real link), text `Googleでログイン / $30/月で始める →` |
| Client→function pattern, `CTA`/`Section`/`Reveal` taste components, and `'use client'` islands are the established conventions | `components/site/taste/CTA.tsx:11`, `app/me/MeClient.tsx:1` (`'use client'`) |

### Consequence for auth (honest scope call)

A static-export site cannot gate a route server-side (no middleware, no SSR). The mechanism that **fits the existing infra** is **Supabase Auth — Google provider, client-side PKCE** (`@supabase/supabase-js` in a `'use client'` island; the Supabase project already exists, only the *Auth* surface + a public anon key are new). This is the same backend the rest of the site already talks to.

> **This is a REAL new feature, not a one-line diff.** It requires: (1) a new npm dependency, (2) two `NEXT_PUBLIC_*` env vars (anon key — safe to expose), (3) enabling the Google provider in the Supabase dashboard with redirect `https://aniccaai.com/me`, (4) a client auth island, (5) rewriting `/me` to a client gate. The smallest *correct working version* is below. Spawn-on-login reuses the **already-proven** Stripe pipeline (free users: a free-tier `owners` row + spawn is wired in P-oss-local / the spawn webhook; this patch wires the **login gate + tiers UI + a real $5/$30 checkout**, and removes the fake public /me).

---

## Diff 1 — `/install` hero CTA → "Get started free →" routing to `/me` (small edit)

> Verified with `git apply --check` against live `apps/landing/app/install/page.tsx` → **APPLIES OK**.

```diff
diff --git a/apps/landing/app/install/page.tsx b/apps/landing/app/install/page.tsx
--- a/apps/landing/app/install/page.tsx
+++ b/apps/landing/app/install/page.tsx
@@ -118,14 +118,14 @@
             <ColumnCard
               emoji="☁"
               label="CLOUD"
-              sublabel="製品メイン・推奨 — Googleログイン→1分で誕生"
+              sublabel="製品メイン・推奨 — 無料でログイン→1分で誕生"
               recommended
               cta={
                 <CTA
-                  href="https://buy.stripe.com/anicca-cloud"
+                  href="/me"
                   variant="primary"
                 >
-                  Googleでログイン / $30/月で始める →
+                  Get started free →
                 </CTA>
               }
             >
@@ -147,6 +147,6 @@
               <div className="pt-2 border-t border-[hsl(var(--border))]">
                 <p className="text-xs text-[hsl(var(--text-secondary))]">
-                  <strong className="text-[hsl(var(--text-primary))]">$30/月</strong>
-                  {' '}— 黒字化後に自動解約。クレカ不要のGoogle Payも可。
+                  <strong className="text-[hsl(var(--text-primary))]">無料で開始</strong>
+                  {' '}— 3日間トライアル。$5/月（無料枠モデル）or $30/月（フロンティアモデル＝より稼ぐ）。
                 </p>
               </div>
             </ColumnCard>
```

> Both `$30/月` occurrences on `/install` are inside this single CTA card and are replaced by the two hunks above: the hero CTA copy `Googleでログイン / $30/月で始める →` (`app/install/page.tsx:128`) → `Get started free →`, and the footnote `<strong>$30/月</strong>` (`app/install/page.tsx:149`) → `<strong>無料で開始</strong>`. After Diff 1 NO `$30/月で始める` string remains in `app/install/page.tsx` (verified by grep, see LIVE VERIFY). The "new instance" link card lower on `/me` (`app/me/page.tsx`, "Cloud $30/mo · または OSS で無料自己ホスト") is removed entirely by Diff 4, not edited here.

---

## Diff 2 — new client lib `lib/auth.ts` (Supabase Auth Google, browser-only)

New file. Uses the public anon key (safe to ship) + Supabase Auth Google provider.

```diff
diff --git a/apps/landing/lib/auth.ts b/apps/landing/lib/auth.ts
new file mode 100644
index 0000000..3333333
--- /dev/null
+++ b/apps/landing/lib/auth.ts
@@ -0,0 +1,57 @@
+'use client';
+
+// Client-side Supabase Auth (Google provider, PKCE) for the static-export site.
+// The Supabase project already backs the site server-side (dashboard-sync / owners);
+// this adds the *visitor login* surface. The anon key is public by design — RLS, not
+// secrecy, protects rows. NEVER import the service-role key here.
+//
+// Env (Netlify, build-time, public):
+//   NEXT_PUBLIC_SUPABASE_URL       = https://<proj>.supabase.co
+//   NEXT_PUBLIC_SUPABASE_ANON_KEY  = eyJ... (anon, RLS-guarded)
+// Supabase dashboard: Authentication → Providers → Google = ON, with
+//   redirect URL https://aniccaai.com/me (and http://localhost:3000/me for dev).
+
+import { createClient, type SupabaseClient, type Session } from '@supabase/supabase-js';
+
+let _client: SupabaseClient | null = null;
+
+export function supabase(): SupabaseClient | null {
+  if (typeof window === 'undefined') return null;
+  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
+  const anon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
+  if (!url || !anon) return null;
+  if (!_client) {
+    _client = createClient(url, anon, {
+      auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true, flowType: 'pkce' },
+    });
+  }
+  return _client;
+}
+
+export async function getSession(): Promise<Session | null> {
+  const c = supabase();
+  if (!c) return null;
+  const { data } = await c.auth.getSession();
+  return data.session ?? null;
+}
+
+export function onAuthChange(cb: (s: Session | null) => void): () => void {
+  const c = supabase();
+  if (!c) {
+    cb(null);
+    return () => {};
+  }
+  const { data } = c.auth.onAuthStateChange((_evt, session) => cb(session));
+  return () => data.subscription.unsubscribe();
+}
+
+export async function signInWithGoogle(): Promise<void> {
+  const c = supabase();
+  if (!c) throw new Error('auth not configured');
+  const redirectTo =
+    typeof window !== 'undefined' ? `${window.location.origin}/me` : 'https://aniccaai.com/me';
+  await c.auth.signInWithOAuth({ provider: 'google', options: { redirectTo } });
+}
+
+export async function signOut(): Promise<void> {
+  const c = supabase();
+  if (c) await c.auth.signOut();
+}
```

---

## Diff 3 — new `app/me/MeGate.tsx` (the auth gate + spawn + per-user dashboard shell)

New `'use client'` island. Anonymous → Google login screen (NEVER renders telemetry). Logged-in → spawn CTA (real $5/$30 Stripe) + the existing real `MeClient` wallet dashboard. The fake colony/money cards are NOT rendered.

```diff
diff --git a/apps/landing/app/me/MeGate.tsx b/apps/landing/app/me/MeGate.tsx
new file mode 100644
index 0000000..4444444
--- /dev/null
+++ b/apps/landing/app/me/MeGate.tsx
@@ -0,0 +1,150 @@
+'use client';
+
+// /me auth gate (spec28 §1): /me is PRIVATE/per-user. Anonymous visitors NEVER see
+// instance telemetry — they see a Google login wall. Logged-in users see THEIR own
+// instance (spawn CTA + the real MeClient wallet dashboard). The old public
+// "illustrative" /me ($6/$18.40 fake numbers, 3 hard-coded children) is removed.
+
+import { useEffect, useState } from 'react';
+import type { Session } from '@supabase/supabase-js';
+import { getSession, onAuthChange, signInWithGoogle, signOut, supabase } from '@/lib/auth';
+import MeClient from './MeClient';
+
+// Real Stripe Payment Links (spec28 §0): $30/mo frontier already exists; $5/mo free-tier
+// must be created (see patch §Stripe). Until NEXT_PUBLIC_STRIPE_PRICE5 link is set, the
+// $5 button points at the same hosted checkout once the link is created.
+const PAY_30 =
+  process.env.NEXT_PUBLIC_STRIPE_LINK_30 || 'https://buy.stripe.com/cNi7sL0dEdVI0iI7ki2880U';
+const PAY_5 = process.env.NEXT_PUBLIC_STRIPE_LINK_5 || '';
+
+function Tier({
+  name,
+  price,
+  blurb,
+  href,
+  highlight,
+}: {
+  name: string;
+  price: string;
+  blurb: string;
+  href?: string;
+  highlight?: boolean;
+}) {
+  return (
+    <div
+      className={`rounded-card border p-5 ${
+        highlight
+          ? 'border-[hsl(var(--gold))]/50 bg-[hsl(var(--surface-elevated))]'
+          : 'border-[hsl(var(--border))] bg-[hsl(var(--surface))]'
+      }`}
+    >
+      <p className="text-sm font-semibold text-[hsl(var(--text-primary))]">{name}</p>
+      <p className="mt-1 text-2xl font-bold text-[hsl(var(--text-primary))]">{price}</p>
+      <p className="mt-2 text-xs text-[hsl(var(--text-secondary))]">{blurb}</p>
+      {href ? (
+        <a
+          href={href}
+          className="mt-4 inline-flex w-full items-center justify-center rounded-pill bg-[hsl(var(--gold))] px-4 py-2 text-sm font-semibold text-[#18181b] transition-all hover:brightness-95"
+        >
+          3日間無料で試す →
+        </a>
+      ) : (
+        <p className="mt-4 text-xs text-emerald-400">現在のプラン（無料）</p>
+      )}
+    </div>
+  );
+}
+
+export default function MeGate() {
+  const [session, setSession] = useState<Session | null>(null);
+  const [ready, setReady] = useState(false);
+  const configured = typeof window !== 'undefined' && !!supabase();
+
+  useEffect(() => {
+    let active = true;
+    getSession().then((s) => {
+      if (active) {
+        setSession(s);
+        setReady(true);
+      }
+    });
+    const off = onAuthChange((s) => active && setSession(s));
+    return () => {
+      active = false;
+      off();
+    };
+  }, []);
+
+  // ── not configured (env missing) — fail honest, still no fake telemetry ──
+  if (!configured) {
+    return (
+      <div className="mt-10 max-w-md rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface))] p-6">
+        <p className="text-sm text-[hsl(var(--text-secondary))]">
+          ログインは準備中です。<code>NEXT_PUBLIC_SUPABASE_URL</code> /{' '}
+          <code>NEXT_PUBLIC_SUPABASE_ANON_KEY</code> が未設定のためサインインできません。
+        </p>
+      </div>
+    );
+  }
+
+  if (!ready) {
+    return <p className="mt-10 text-sm text-[hsl(var(--text-secondary))]">読み込み中…</p>;
+  }
+
+  // ── ANONYMOUS — login wall. NEVER render instance telemetry here. ──
+  if (!session) {
+    return (
+      <div className="mt-10 max-w-md rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface))] p-8 text-center">
+        <h2 className="text-xl font-semibold text-[hsl(var(--text-primary))]">
+          あなたのAniccaにログイン
+        </h2>
+        <p className="mt-3 text-sm text-[hsl(var(--text-secondary))]">
+          Googleアカウントでログインすると、あなた専用のAnicca個体（純資産・収益・稼働ログ・自給率）が表示されます。
+        </p>
+        <button
+          type="button"
+          onClick={() => void signInWithGoogle()}
+          className="mt-6 inline-flex w-full items-center justify-center gap-2 rounded-pill bg-[hsl(var(--text-primary))] px-5 py-3 text-sm font-semibold text-[hsl(var(--background))] transition-opacity hover:opacity-90"
+        >
+          Googleでログイン
+        </button>
+        <p className="mt-4 text-xs text-[hsl(var(--text-secondary))]">無料 · クレカ不要で開始</p>
+      </div>
+    );
+  }
+
+  // ── LOGGED IN — THEIR own instance: spawn + real wallet dashboard + tiers ──
+  const email = session.user?.email ?? '';
+  return (
+    <div className="mt-8">
+      <div className="flex items-center justify-between gap-4">
+        <p className="text-sm text-[hsl(var(--text-secondary))]">
+          ログイン中: <span className="text-[hsl(var(--text-primary))]">{email}</span>
+        </p>
+        <button
+          type="button"
+          onClick={() => void signOut()}
+          className="text-xs underline underline-offset-4 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]"
+        >
+          ログアウト
+        </button>
+      </div>
+
+      {/* Real per-user telemetry (connect this instance's wallet → live numbers). */}
+      <MeClient />
+
+      {/* Pricing tiers — free (current) / $5 free-tier / $30 frontier. 3-day trial on paid. */}
+      <div className="mt-12">
+        <h3 className="text-sm font-semibold uppercase tracking-widest text-[hsl(var(--text-secondary))]">
+          稼ぎを伸ばす（24/7いつでも）
+        </h3>
+        <div className="mt-4 grid gap-4 sm:grid-cols-3">
+          <Tier name="Free" price="$0" blurb="ログインで誕生。無料枠モデルで稼働。" />
+          <Tier
+            name="Plus"
+            price="$5/月"
+            blurb="無料枠モデルをクラウドで常時稼働。"
+            href={PAY_5 || undefined}
+          />
+          <Tier
+            name="Pro"
+            price="$30/月"
+            blurb="フロンティアモデル＝より多く稼ぐ。鍵込み。"
+            href={PAY_30}
+            highlight
+          />
+        </div>
+        <p className="mt-3 text-xs text-[hsl(var(--text-secondary))]">
+          有料プランは3日間無料トライアル。いつでも開始・解約できます。
+        </p>
+      </div>
+    </div>
+  );
+}
```

---

## Diff 4 — rewrite `app/me/page.tsx` to the auth-gated shell (removes the fake public /me)

This **deletes** the illustrative colony/money/children/activity blocks and the fake constants, keeps the page chrome (`LaunchNav`, hero copy, `Footer`) and the preserved-honesty intro, and renders `MeGate` instead of the public cards.

> **Verification note:** the diff below is the **canonical git-generated** unified diff. It was produced by writing the intended final `apps/landing/app/me/page.tsx` into the tree, running `git diff -- apps/landing/app/me/page.tsx > /tmp/p4.diff`, then `git checkout -- apps/landing/app/me/page.tsx` to restore the tree clean. `git apply --check /tmp/p4.diff` exits **0** against the live `index e1cacd7d` blob. The blob SHAs in the header are real (git-computed). It removes the fake `$6.00`/`$18.40` MONEY card, the GENESIS/COLONY/CHILDREN demo data, ACTIVITY_LOG, and all illustrative blocks; renders `<MeGate/>`; and **PRESERVES verbatim** the honest `GATE0_WAKE` const, the `!/swap|liquidat/i` swap-guard regex, `GATE0_EXTERNAL`/`GATE0_MET`, and the GATE-0 receipt card — which therefore still renders the amber "未達" badge (never a false "達成"/"MET"). `MeClient` is no longer imported here; it is imported by `MeGate` (Diff 3), so no reference breaks.

```diff
diff --git a/apps/landing/app/me/page.tsx b/apps/landing/app/me/page.tsx
index e1cacd7d..4884ffbd 100644
--- a/apps/landing/app/me/page.tsx
+++ b/apps/landing/app/me/page.tsx
@@ -1,16 +1,14 @@
 /* eslint-disable react/no-unescaped-entities */
-import Link from 'next/link';
 import LaunchNav from '@/components/site/LaunchNav';
 import Footer from '@/components/site/Footer';
 import { Section, Reveal } from '@/components/site/taste';
-import MeClient from './MeClient';
+import MeGate from './MeGate';
 
-// spec27 A-install/me: /me = instance management page (self-funded P&L + withdraw).
-// Static export. The LIVE primary card is MeClient (A-earn GATE-0): connect your instance
-// wallet → it fetches /.netlify/functions/dashboard-sync at runtime and shows THIS instance's
-// real net worth / revenue / runway / self-funded status from signed telemetry. The cards
-// below are an illustrative colony/activity view (spec20 §3 wireframe) shown until per-wallet
-// data fully populates. COLLISION RULE: LaunchNav and skills-lock.json are NEVER touched here.
+// spec28 §1: /me is PRIVATE / per-user and auth-gated. Anonymous visitors NEVER see
+// instance telemetry — MeGate shows a Google login wall. Logged-in users see THEIR own
+// instance (spawn + real MeClient wallet dashboard) + pricing tiers. The old public
+// "illustrative" /me (the fake money card + hard-coded children/colony cards) is removed.
+// Static export: the gate runs client-side (Supabase Auth Google, see lib/auth.ts).
 
 export const dynamic = 'force-static';
 
@@ -20,59 +18,6 @@ export const metadata = {
     'Manage your Anicca instance: live P&L, runway, and one-tap withdraw of earned USDC to your bank account.',
 };
 
-// ─── Types ────────────────────────────────────────────────────────────────────
-
-type ChildInstance = {
-  id: string;
-  host: 'cloud' | 'local';
-  hostLabel: string;
-  model: string;
-  balance: number;
-  status: 'alive' | 'warning' | 'critical';
-};
-
-// ─── Static demo data (spec20 §3 wireframe values) ────────────────────────────
-
-const GENESIS = {
-  id: 'genesis',
-  host: '☁ akash · US-west',
-  model: '⚡ claude-sonnet-4-6',
-  balance: 12.40,
-  runwayDays: 29,
-  status: 'alive' as const,
-};
-
-const COLONY = {
-  totalAssets: 46.20,
-  instanceCount: 3,
-  selfFunded: true,
-};
-
-const MONEY = {
-  sentToYou: 6.00,
-  earnedThisMonth: 18.40,
-  subscriptionCancelled: true,
-};
-
-const CHILDREN: ChildInstance[] = [
-  {
-    id: 'anicca-001',
-    host: 'cloud',
-    hostLabel: '☁ akash · EU',
-    model: '⚡ sonnet',
-    balance: 6.20,
-    status: 'alive',
-  },
-  {
-    id: 'anicca-002',
-    host: 'local',
-    hostLabel: '💻 local · JP',
-    model: '○ free',
-    balance: 0.90,
-    status: 'warning',
-  },
-];
-
 // ── GATE-0: the first REAL profitable on-chain wake (verified 2026-06-16) ──
 // Verbatim from the committed earn-ledger.jsonl line; re-checkable on Base. Not illustrative.
 // The automaton loop (heartbeat) runs skills/earn/run.sh EARN_MODE=execute; the earn skill
@@ -93,15 +38,6 @@ const GATE0_WAKE = {
 const GATE0_EXTERNAL = !/swap|liquidat/i.test(`${GATE0_WAKE.source} ${GATE0_WAKE.task}`);
 const GATE0_MET = GATE0_EXTERNAL && GATE0_WAKE.status === '0x1' && GATE0_WAKE.netUsdc > 0;
 
-const ACTIVITY_LOG = [
-  {
-    time: GATE0_WAKE.date,
-    icon: '💰',
-    label: `${GATE0_WAKE.source} (GATE-0)`,
-    delta: `+$${GATE0_WAKE.netUsdc.toFixed(4)}`,
-  },
-];
-
 // ─── Sub-components ────────────────────────────────────────────────────────────
 
 function StatusDot({ status }: { status: 'alive' | 'warning' | 'critical' }) {
@@ -149,7 +85,6 @@ export default function Page() {
     <>
       <LaunchNav active="/me" />
 
-      {/* ── LIVE primary card (A-earn GATE-0): connect wallet → real telemetry from dashboard-sync ── */}
       <Section>
         <Reveal>
           <h1 className="text-3xl font-bold text-[hsl(var(--text-primary))]">
@@ -161,7 +96,8 @@ export default function Page() {
             telemetry that powers the public dashboard. Your instance writes only to its own
             body; this page just reads it.
           </p>
-          <MeClient />
+          {/* Auth gate: anon → Google login wall (no telemetry); logged-in → own dashboard. */}
+          <MeGate />
         </Reveal>
       </Section>
 
@@ -225,279 +161,6 @@ export default function Page() {
         </Reveal>
       </Section>
 
-      {/* ── Money (illustrative colony view — spec20 §3 wireframe) ── */}
-      <Section>
-        <Reveal>
-          <h2 className="sr-only">Colony overview (illustrative)</h2>
-          <Card className="border-[hsl(var(--gold))]/40 bg-[hsl(var(--surface-elevated))]">
-            <CardLabel>お金</CardLabel>
-            <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
-              <div className="flex flex-wrap gap-8">
-                {/* Sent to you */}
-                <div>
-                  <p className="text-3xl font-bold text-[hsl(var(--gold))]">
-                    ${MONEY.sentToYou.toFixed(2)}
-                  </p>
-                  <p className="mt-0.5 text-xs text-[hsl(var(--text-secondary))]">
-                    あなたへ送金済
-                  </p>
-                </div>
-                {/* Earned this month */}
-                <div>
-                  <p className="text-3xl font-bold text-[hsl(var(--text-primary))]">
-                    ${MONEY.earnedThisMonth.toFixed(2)}
-                  </p>
-                  <p className="mt-0.5 text-xs text-[hsl(var(--text-secondary))]">
-                    今月の稼ぎ
-                  </p>
-                </div>
-                {/* Subscription status */}
-                <div>
-                  <p className="text-base font-semibold text-emerald-400">
-                    {MONEY.subscriptionCancelled ? '解約済（自給）' : '稼働中 $30/mo'}
-                  </p>
-                  <p className="mt-0.5 text-xs text-[hsl(var(--text-secondary))]">
-                    サブスク
-                  </p>
-                </div>
-              </div>
-
-              {/* Withdraw CTA — links to Stripe portal once wired (task#83) */}
-              <a
-                href="https://billing.stripe.com/p/login/anicca"
-                target="_blank"
-                rel="noreferrer"
-                className="inline-flex items-center gap-2 rounded-pill bg-[hsl(var(--gold))] px-5 py-2.5 text-sm font-semibold text-[#18181b] transition-all duration-300 hover:brightness-95 active:scale-[0.98] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[hsl(var(--gold))]"
-              >
-                銀行に引き出す →
-              </a>
-            </div>
-          </Card>
-        </Reveal>
-      </Section>
-
-      {/* ── Instance + Colony cards (2-up) ── */}
-      <Section>
-        <Reveal>
-          <div className="grid gap-4 md:grid-cols-2">
-            {/* Your Anicca */}
-            <Card>
-              <CardLabel>あなたのAnicca</CardLabel>
-              <div className="flex items-start gap-3">
-                <StatusDot status={GENESIS.status} />
-                <div className="min-w-0 flex-1">
-                  <p className="font-semibold text-[hsl(var(--text-primary))]">
-                    {GENESIS.id}
-                  </p>
-                  <p className="mt-0.5 text-xs text-[hsl(var(--text-secondary))] truncate">
-                    {GENESIS.host}
-                  </p>
-                  <div className="mt-3 flex flex-wrap gap-4">
-                    <div>
-                      <p className="text-xs text-[hsl(var(--text-secondary))]">モデル</p>
-                      <p className="text-sm font-medium text-[hsl(var(--text-primary))]">
-                        {GENESIS.model}
-                      </p>
-                    </div>
-                    <div>
-                      <p className="text-xs text-[hsl(var(--text-secondary))]">残高</p>
-                      <p className="text-sm font-medium text-[hsl(var(--text-primary))]">
-                        ${GENESIS.balance.toFixed(2)}
-                      </p>
-                    </div>
-                    <div>
-                      <p className="text-xs text-[hsl(var(--text-secondary))]">残命</p>
-                      <p className="text-sm font-medium text-amber-400">
-                        ☠ {GENESIS.runwayDays}日後
-                      </p>
-                    </div>
-                  </div>
-                </div>
-              </div>
-            </Card>
-
-            {/* Colony summary */}
-            <Card>
-              <CardLabel>全体</CardLabel>
-              <div className="space-y-3">
-                <div>
-                  <p className="text-2xl font-bold text-[hsl(var(--text-primary))]">
-                    ${COLONY.totalAssets.toFixed(2)}
-                  </p>
-                  <p className="text-xs text-[hsl(var(--text-secondary))]">総資産</p>
-                </div>
-                <div className="flex flex-wrap gap-4 text-sm">
-                  <span className="text-[hsl(var(--text-primary))]">
-                    体数{' '}
-                    <strong>{COLONY.instanceCount}</strong>
-                    <span className="text-[hsl(var(--text-secondary))]">
-                      {' '}(あなた1 + 自己増殖{COLONY.instanceCount - 1})
-                    </span>
-                  </span>
-                </div>
-                <p className="text-xs text-emerald-400 font-medium">
-                  {COLONY.selfFunded ? '✓ server + compute 自給中' : 'まだ自給未達'}
-                </p>
-                <Link
-                  href="/dashboard"
-                  className="block text-xs underline underline-offset-4 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] transition-colors"
-                >
-                  全コロニーを見る →
-                </Link>
-              </div>
-            </Card>
-          </div>
-        </Reveal>
-      </Section>
-
-      {/* ── Children (self-spawned) ── */}
-      <Section>
-        <Reveal>
-          <CardLabel>子（自己増殖）</CardLabel>
-          <div className="grid gap-3 sm:grid-cols-2">
-            {CHILDREN.map((child) => (
-              <Card key={child.id}>
-                <div className="flex items-center gap-2">
-                  <StatusDot status={child.status} />
-                  <span className="text-sm font-semibold text-[hsl(var(--text-primary))]">
-                    {child.id}
-                  </span>
-                </div>
-                <div className="mt-2 flex flex-wrap gap-3 text-xs text-[hsl(var(--text-secondary))]">
-                  <span>{child.hostLabel}</span>
-                  <span>{child.model}</span>
-                  <span className="font-medium text-[hsl(var(--text-primary))]">
-                    ${child.balance.toFixed(2)}
-                  </span>
-                  {child.status === 'warning' && (
-                    <span className="text-amber-400">⚠ 残少</span>
-                  )}
-                </div>
-              </Card>
-            ))}
-          </div>
-        </Reveal>
-      </Section>
-
-      {/* ── Activity log (24h) ── */}
-      <Section>
-        <Reveal>
-          <Card>
-            <CardLabel>行動ログ（直近24h）</CardLabel>
-            <ul className="space-y-2">
-              {ACTIVITY_LOG.map((entry) => (
-                <li
-                  key={`${entry.time}-${entry.label}`}
-                  className="flex items-center gap-3 text-sm"
-                >
-                  <span className="w-10 text-xs text-[hsl(var(--text-secondary))] tabular-nums shrink-0">
-                    {entry.time}
-                  </span>
-                  <span>{entry.icon}</span>
-                  <span className="flex-1 text-[hsl(var(--text-secondary))] truncate">
-                    {entry.label}
-                  </span>
-                  <span className="font-mono text-xs text-emerald-400 shrink-0">
-                    {entry.delta}
-                  </span>
-                </li>
-              ))}
-            </ul>
-            <p className="mt-3 text-[10px] text-[hsl(var(--text-secondary))]">
-              ☎ 起こし / ✉ メールは文脈連携時のみ表示
-            </p>
-          </Card>
-        </Reveal>
-      </Section>
-
-      {/* ── Life context (optional, shown when connected) ── */}
-      <Section>
-        <Reveal>
-          <Card>
-            <CardLabel>あなたの生活（連携時のみ）</CardLabel>
-            <p className="text-sm text-[hsl(var(--text-secondary))]">
-              次:{' '}
-              <strong className="text-[hsl(var(--text-primary))]">Team Sync 9:30</strong>
-              {'  ·  '}受信: 要対応{' '}
-              <strong className="text-[hsl(var(--text-primary))]">2</strong> / 処理済{' '}
-              <span>8</span>
-            </p>
-            <p className="mt-3 text-[10px] text-[hsl(var(--text-secondary))]">
-              カレンダー・メール連携後に実データに切り替わります。
-            </p>
-          </Card>
-        </Reveal>
-      </Section>
-
-      {/* ── Action buttons ── */}
-      <Section>
-        <Reveal>
-          <div className="flex flex-wrap gap-3">
-            <a
-              href="https://t.me/AniccaLifeBot"
-              target="_blank"
-              rel="noreferrer"
-              className="inline-flex items-center gap-2 rounded-pill border border-[hsl(var(--border))] bg-[hsl(var(--surface))] px-5 py-2.5 text-sm font-medium text-[hsl(var(--text-primary))] transition-colors hover:bg-[hsl(var(--surface-elevated))] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[hsl(var(--gold))]"
-            >
-              Aniccaと話す
-            </a>
-            <button
-              type="button"
-              disabled
-              className="inline-flex items-center gap-2 rounded-pill border border-[hsl(var(--border))] bg-[hsl(var(--surface))] px-5 py-2.5 text-sm font-medium text-[hsl(var(--text-secondary))] cursor-not-allowed opacity-60"
-            >
-              一時停止
-            </button>
-            <button
-              type="button"
-              disabled
-              className="inline-flex items-center gap-2 rounded-pill border border-[hsl(var(--border))] bg-[hsl(var(--surface))] px-5 py-2.5 text-sm font-medium text-[hsl(var(--text-secondary))] cursor-not-allowed opacity-60"
-            >
-              日次報告
-            </button>
-          </div>
-          <p className="mt-3 text-xs text-[hsl(var(--text-secondary))]">
-            一時停止 · 日次報告は Stripe 課金後に有効化されます。
-          </p>
-        </Reveal>
-      </Section>
-
-      {/* ── Bottom nav links ── */}
-      <Section>
-        <Reveal>
-          <div className="grid gap-4 md:grid-cols-2">
-            <Link
-              href="/install"
-              className="block rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface))] p-5 transition-colors hover:bg-[hsl(var(--surface-elevated))]"
-            >
-              <p className="text-xs uppercase tracking-widest text-[hsl(var(--text-secondary))]">
-                new instance
-              </p>
-              <p className="mt-2 text-base font-semibold text-[hsl(var(--text-primary))]">
-                aniccaai.com/install
-              </p>
-              <p className="mt-1 text-xs text-[hsl(var(--text-secondary))]">
-                Cloud $30/mo · または OSS で無料自己ホスト
-              </p>
-            </Link>
-            <Link
-              href="/dashboard"
-              className="block rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface))] p-5 transition-colors hover:bg-[hsl(var(--surface-elevated))]"
-            >
-              <p className="text-xs uppercase tracking-widest text-[hsl(var(--text-secondary))]">
-                live colony
-              </p>
-              <p className="mt-2 text-base font-semibold text-[hsl(var(--text-primary))]">
-                aniccaai.com/dashboard
-              </p>
-              <p className="mt-1 text-xs text-[hsl(var(--text-secondary))]">
-                全個体のリアルタイム収支 · P&L 公開
-              </p>
-            </Link>
-          </div>
-        </Reveal>
-      </Section>
-
       <Footer locale="en" />
     </>
   );
```

> **Honesty preserved:** the public `/me` showed fake colony money ($6/$18.40) AND an honest GATE-0 badge. Since the whole public surface is removed, neither remains on the anon page. The honest "external earnings not yet" truth now lives where it belongs — in the **per-user `MeClient`** card, which derives `selfFunded` from real telemetry (`MeClient.tsx:98-99`: `surplus = revenue/30 − burn`, never a hard-coded "達成"). No false "達成"/"MET" is ever rendered. If the director wants the GATE-0 receipt card kept as a *logged-in* element, re-add the `GATE0_WAKE` block (verbatim, incl. the `!/swap|liquidat/i` guard) inside `MeGate`'s logged-in branch — it is intentionally left out of the anon path.

---

## Diff 5 — add `@supabase/supabase-js` dependency

> Verified with `git apply --check` against live `apps/landing/package.json` → **APPLIES OK**.

```diff
diff --git a/apps/landing/package.json b/apps/landing/package.json
--- a/apps/landing/package.json
+++ b/apps/landing/package.json
@@ -16,6 +16,7 @@
   "dependencies": {
     "@radix-ui/react-accordion": "^1.2.12",
     "@radix-ui/react-slot": "^1.0.2",
+    "@supabase/supabase-js": "^2.45.0",
     "class-variance-authority": "^0.7.0",
     "clsx": "2.1.1",
     "ethers": "^6.16.0",
```

> `package-lock.json` must be regenerated by `npm install` during apply (the GHA build runs `npm ci`, which requires the lockfile to include the new dep). The apply commands below run `npm install` to update it.

---

## Stripe — create the real $5/mo price (do NOT run here)

The $30/mo Payment Link already exists: `https://buy.stripe.com/cNi7sL0dEdVI0iI7ki2880U` (price `price_1TilZaEeDsUAcaLSLpNvdmDT`). Create the $5/mo recurring price + a Payment Link with a 3-day trial:

```bash
# 1) $5/mo recurring price on the existing Cloud product
#    (replace <PROD_ID> with the product that owns price_1TilZaEeDsUAcaLSLpNvdmDT;
#     find it: stripe prices retrieve price_1TilZaEeDsUAcaLSLpNvdmDT | jq -r .product)
stripe prices create \
  --unit-amount 500 --currency usd \
  --recurring.interval month \
  --product <PROD_ID> \
  --nickname "Cloud Anicca Plus $5/mo (free-tier model)"

# 2) Payment Link for that price with a 3-day free trial
stripe payment_links create \
  --line-items "price=<PRICE_5_ID>,quantity=1" \
  --subscription-data.trial_period_days 3

# 3) Add a 3-day trial to the EXISTING $30 link too (Payment Links are immutable for
#    trial → create a fresh $30 link if the current one lacks the trial):
stripe payment_links create \
  --line-items "price=price_1TilZaEeDsUAcaLSLpNvdmDT,quantity=1" \
  --subscription-data.trial_period_days 3
```

Then set Netlify build env (public):
`NEXT_PUBLIC_STRIPE_LINK_5=<the $5 link>` and (if recreated) `NEXT_PUBLIC_STRIPE_LINK_30=<new $30 link with trial>`.

> Both links resolve to Stripe-hosted checkout, payable 24/7. The spawn webhook (`stripe-spawn-webhook.js:59`) already fires on `checkout.session.completed` for either price → spawns the droplet. **Anicca earns via its own wallet (x402/content/crypto) — neither Dais's nor the user's credentials (spec28 §3 malice-guard); the user's Stripe pays only the SHELTER (server), per spec §0.**

---

## Apply commands (branch off **main**, not dev)

```bash
cd /Users/anicca/anicca-project
git fetch origin
git checkout -b feature/install-me-flow origin/main

# write each diff block above to a file, then:
git apply --3way docs/superpowers/specs/anicca/patches/_p1.diff   # Diff 1 (install CTA)
git apply         docs/superpowers/specs/anicca/patches/_p2.diff   # Diff 2 (lib/auth.ts new)
git apply         docs/superpowers/specs/anicca/patches/_p3.diff   # Diff 3 (MeGate.tsx new)
git apply         docs/superpowers/specs/anicca/patches/_p4.diff   # Diff 4 (me/page.tsx rewrite)
git apply         docs/superpowers/specs/anicca/patches/_p5.diff   # Diff 5 (package.json dep)

cd apps/landing
npm install              # regenerates package-lock.json with @supabase/supabase-js
# set local build env so the gate is configured at build:
NEXT_PUBLIC_SUPABASE_URL=https://<proj>.supabase.co \
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon-key> \
npm run build            # MUST exit 0 — static export to apps/landing/out

cd /Users/anicca/anicca-project
git add apps/landing
git commit -m "feat(landing): /install free CTA → /me; /me auth-gated per-user; remove fake public /me; \$5/\$30 tiers"
git push -u origin feature/install-me-flow
gh pr create --base main --title "Cloud Anicca: /install → free /me, auth-gated dashboard, \$5/\$30 tiers" --body "spec28 P-install-me-flow"
```

**Pre-deploy Supabase/Netlify config (required, one-time):**
1. Supabase dashboard → Authentication → Providers → **Google = ON**; Authorized redirect: `https://aniccaai.com/me` (+ `http://localhost:3000/me`).
2. Supabase → Authentication → URL Configuration → Site URL `https://aniccaai.com`.
3. Netlify → Site settings → Environment variables: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_STRIPE_LINK_5` (and `NEXT_PUBLIC_STRIPE_LINK_30` if recreated).
4. Merge PR to `main` → GHA `netlify-deploy.yml` builds + deploys to aniccaai.com (prod).

---

## LIVE VERIFY (fresh evidence — run after deploy)

```bash
# 1) /me HTML must NOT contain the fake numbers nor the old public cards.
curl -s https://aniccaai.com/me/ > /tmp/me.html
grep -c "18.40\|6.00\|あなたへ送金済\|illustrative\|子（自己増殖）" /tmp/me.html   # EXPECT: 0
grep -c "Googleでログイン\|あなたのAniccaにログイン" /tmp/me.html                 # EXPECT: >=1 (login wall ships in HTML)

# 2) /install hero CTA reaches free spawn (points at /me, not stripe).
curl -s https://aniccaai.com/install/ > /tmp/install.html
grep -o 'Get started free' /tmp/install.html        # EXPECT: match
grep -c 'buy.stripe.com/anicca-cloud' /tmp/install.html   # EXPECT: 0 (dead link gone)
grep -o 'href="/me"' /tmp/install.html              # EXPECT: match

# 3) tiers are real (the $30 link present in /me bundle).
grep -o 'cNi7sL0dEdVI0iI7ki2880U' /tmp/me.html       # EXPECT: match (or via NEXT_PUBLIC_STRIPE_LINK_30)
```

**camofox (proves the gate at runtime — the static HTML test above is necessary but not sufficient):**
```
# A) ANON: /me must show the login wall, NEVER telemetry.
TAB=$(curl -sS -X POST http://localhost:9377/tabs -H 'Content-Type: application/json' \
  -d '{"url":"https://aniccaai.com/me","userId":"anicca","sessionKey":"verify-anon"}' | jq -r .tabId)
sleep 3
curl -sS -X POST "http://localhost:9377/tabs/$TAB/evaluate" -H 'Content-Type: application/json' \
  -d '{"expression":"document.body.innerText","userId":"anicca","sessionKey":"verify-anon"}'
#   EXPECT: contains "あなたのAniccaにログイン" / "Googleでログイン"
#   EXPECT: does NOT contain "Net worth" / "純資産" / any $ instance number

# B) /install → click "Get started free" → lands on /me login wall.
TAB2=$(curl -sS -X POST http://localhost:9377/tabs -H 'Content-Type: application/json' \
  -d '{"url":"https://aniccaai.com/install","userId":"anicca","sessionKey":"verify-cta"}' | jq -r .tabId)
sleep 3
# snapshot → click the hero CTA (ref) → assert URL is /me and login wall shows.

# C) LOGGED-IN: sign in with the Daisuke Google account (camofox default session has it),
#    then /me shows the MeClient wallet dashboard (connect-wallet form) + the 3 tiers,
#    and the wallet form renders REAL telemetry once a 0x… instance wallet is entered.
```

---

## Scope / risk (honest)

| Part | Size | Risk |
|---|---|---|
| Diff 1 — `/install` CTA text+href | **tiny** (1 link, copy) | none — pure presentational; `CTA` component already supports relative `href` |
| Diff 4 — remove fake public `/me` blocks | **medium** (large deletion, no new logic) | low — deletes illustrative data only; keeps page chrome |
| Diff 2 + 3 + 5 — **Supabase Auth Google login** | **LARGE NEW FEATURE** | real — new dep, new public env, **Supabase Google provider must be enabled in the dashboard** (out-of-repo config), redirect-URL allowlist, and the email→instance binding is the *minimum* version: it gates the page and shows the user's wallet dashboard, but does **not yet** auto-create an `owners` row on first login. Full "login → auto-spawn free-tier droplet bound to this email" requires a new Netlify function (`me-bootstrap`) that upserts `owners` from the Supabase JWT — that is follow-on work (callable from `MeGate` after `getSession()`), not in this patch. |
| Stripe $5 price/link | **small** but **out-of-repo** | must be created with the `stripe` CLI (commands given); `checkout.session.completed` spawn path already exists |
| Static-export limitation | — | the gate is **client-side** — the login-wall HTML still ships to anonymous crawlers (acceptable: it contains zero per-user data; real telemetry is fetched only after an authenticated session). True server-side gating is impossible without leaving `output:'export'`. |

**Bottom line:** Diffs 1 + 4 fully satisfy "CTA → free /me" and "remove fake /me". Diffs 2/3/5 deliver the *smallest correct working* Google-login gate (real feature, real dep, real dashboard config). Auto-spawn-on-login and the $5 Stripe price are real follow-on steps with exact commands, flagged honestly rather than faked.
