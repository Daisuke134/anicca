# P-ui-polish — premium UI/UX polish for the four web surfaces (/install /me /lm /life-manager)

> Spec: `28-product-redesign-merge-2026-06-16.md` §5 (UI/UX taste — ui-ux-pro-max + frontend-design). Target repo:
> `Daisuke134/anicca-products`, path `apps/landing` (Next.js static export, `output: export`; server = Netlify
> Functions). Task #7. **Goal:** raise the four launch surfaces to production-grade premium polish — clearer
> hierarchy, intentional spacing/typography, sharper hero + CTA, honest trust/social-proof, mobile-first — WITHOUT a
> rewrite, WITHOUT new server needs, WITHOUT breaking the `/en` `/ja` locale homepages, and WITHOUT inventing
> jargon, fake "coming soon", or false success claims.
>
> **UI skills used (mandated by spec 28 §5):** `ui-ux-pro-max` (`.claude/skills/ui-ux-pro-max/`, ran
> `search.py --design-system` + `--domain landing` + `--domain ux`) and `frontend-design` (taste). Guidance applied
> is cited inline per diff.
>
> **Authoring note:** every line anchor below was read live this session (file:line cited in §2). The diffs are
> scoped, git-applicable hunks; the implementer MUST re-confirm anchors against the working tree before applying
> (files change between authoring and execution).

---

## §1 UI-skill guidance applied (cited, not generic)

| source | guidance | where applied |
|---|---|---|
| ui-ux-pro-max `--design-system` (this session) | "Premium dark + gold accent" palette `#1C1917 / #CA8A04`; Style = **Flat Design** "no shadows, simple hover (color/opacity shift), clean transitions 150-200ms"; anti-patterns: **"Cluttered layout"**, **"Complex onboarding flow"** | confirms the existing tokens (`--gold` `#c9a23f`, `globals.css:17`) — so polish DEEPENS the current direction, never repaints it; declutter `/me` (§3.2), keep `/lm` steps minimal (untouched logic) |
| ui-ux-pro-max checklist | "**No emojis as icons** — use SVG (Heroicons/Lucide)"; "cursor-pointer on all clickable"; "Hover states 150-300ms"; "Responsive 375/768/1024/1440"; "prefers-reduced-motion respected" | replace emoji icons on `/install` feature grid + `/me` activity with inline SVG (§3.1, §3.2); all clickable cards already use `Link` (keep) |
| ui-ux-pro-max `--domain landing` (Result 1 "Hero + Testimonials + CTA") | "**Social proof before CTA**"; "CTA after social proof"; pattern "Pricing Page": "**highlight/pre-select** the recommended plan" | `/install` gets an honest, verifiable trust strip (real on-chain GATE-0 receipt already on `/me`) directly under the hero, before the column CTAs (§3.1); the CLOUD column already carries the `推奨` badge (`install/page.tsx:51-54`) — keep it as the highlighted plan |
| ui-ux-pro-max `--domain ux` (Touch Spacing, Hover States) | "min 8px gap between touch targets"; "cursor + subtle visual change on hover" | mobile column stacking keeps `gap-6`; hover on cards uses `hover:bg-[hsl(var(--surface-elevated))]` (already present) |
| frontend-design (taste) | "one well-orchestrated page load with **staggered reveals** > scattered micro-interactions"; "distinctive display + refined body"; "atmosphere/depth over solid color"; "restraint, precision" for refined-minimal | `/install` hero gains a real product visual (calendar/ledger mock, reusing the `/life-manager` SplitHero asset idiom) + staggered `Reveal delay`; `/life-manager` jargon headings rewritten to human, benefit-led copy (§3.4) |

**Direction commitment (frontend-design):** the site is already a *refined-minimal premium dark + gold* system
(`font-display`, `--gold`, `rounded-card`/`rounded-pill`, `Section`/`Reveal`/`CTA` islands). This patch executes
THAT vision more precisely — it does not introduce a second aesthetic. No purple gradients, no Inter/Roboto swap,
no new color tokens.

## §2 Reality found (cited file:line, live tree, read this session)

| fact | evidence |
|---|---|
| `/install` hero is text-only, centered, **no product visual, no trust/social-proof** | `app/install/page.tsx:97-110` (Hero `Section`→`Reveal`→centered `<h1>`+`<p>`, nothing else) |
| `/install` feature grid renders **emoji as icons** (💰📞🌱🌍📊🔧) | `app/install/page.tsx:207-213` (`icon` strings) rendered at `:219` `<p className="text-lg">{icon}</p>` |
| `/install` CLOUD column is the recommended/highlighted plan (badge exists) | `app/install/page.tsx:51-54` (`推奨` pill), gold border `:46-48` |
| `/me` has a **verifiable on-chain GATE-0 receipt** (real, re-checkable on BaseScan) + an honest **amber "外部収益はまだ" badge** that must NOT be made to claim success | `app/me/page.tsx:80-94` (`GATE0_WAKE`, `GATE0_MET` honesty gate), `:174-182` (amber badge), `:211-218` (BaseScan link) |
| `/me` activity/illustrative cards use emoji + dense single-column stacking | `app/me/page.tsx:99` (`icon:'💰'`), `:227-276` (Money card), `:352-379` (Children) |
| `/me` "illustrative colony" data is explicitly labelled illustrative (keep that honesty) | `app/me/page.tsx:34` comment, `:230` `<h2 className="sr-only">Colony overview (illustrative)</h2>` |
| `/lm` onboarding island is already clean (StepDots, Shell, fail-closed Stripe button) — **logic must not change** | `app/lm/LmClient.tsx:29-52` (`StepDots`,`Shell`), `:22` (`STRIPE_LM_URL` fail-closed), `:242-253` (no fake link) |
| `/lm` page hero is centered eyebrow+h1+p, no visual | `app/lm/page.tsx:25-40` |
| **`/life-manager` renders INTERNAL JARGON to users** (premise "already stripped" is FALSE here) | `app/life-manager/page.tsx:32/40/48/56` labels `B-travel`/`B-call`/`B-ask`/`B-notify` rendered at `:123-125`; heading **"How B-travel works (spec27 §2)"** `:147`; **"spec27 §2 patch"** rendered at `:228-231`; **`travel-logic.js`** rendered in a table cell `:182` |
| `SplitHero` taste component exists and is the established hero idiom (left text / right real asset) | `components/site/taste/SplitHero.tsx:16-51`; used at `app/life-manager/page.tsx:77-105` |
| taste primitives + tokens are the house style | `components/site/taste/{CTA,Section,Reveal,SplitHero}.tsx`; tokens `app/globals.css:13-52` (`--gold`,`--surface`,`--surface-elevated`,`--text-primary/secondary`,`--border`) |
| `/en` `/ja` are SEPARATE locale homepages (NOT under the 4 surfaces) — untouched by this patch | `app/en/page.tsx`, `app/ja/page.tsx` exist; the 4 surfaces have no `[locale]` subtree (`ls app/install` etc. = single `page.tsx`) |
| build command that must stay green | `package.json` `"build": "next build"` (static export via `next.config`) |
| comment-only refs are NOT rendered (constraint already met for install/me/lm) | `app/install/page.tsx:8` `spec27`, `app/me/page.tsx:8` `spec27` — all inside `//` comments, never in JSX |

**The single highest-impact correctness fix:** `/life-manager` leaks engineering jargon into the rendered page
(GATE-0/B-travel/spec27 — exactly what spec 28 §5 forbids). Diff 4 is therefore both a *polish* and a
*jargon-strip* fix; it is the priority of this patch.

## §3 Diffs (6 scoped improvements)

### Diff 1 — `/install`: real hero visual + honest trust strip, replace emoji icons with SVG

Applies: ui-ux-pro-max landing "social proof before CTA" + checklist "no emoji as icons"; frontend-design "real
product visual + staggered reveal". The trust strip reuses ONLY facts already shown on `/me` (the verified
BaseScan receipt) — no new claim. Keeps it static (one `<a>` to BaseScan, no fetch).

```diff
diff --git a/apps/landing/app/install/page.tsx b/apps/landing/app/install/page.tsx
--- a/apps/landing/app/install/page.tsx
+++ b/apps/landing/app/install/page.tsx
@@ Hero Section (currently :97-110, text-only centered)
       {/* ── Hero ── */}
-      <Section>
-        <Reveal>
-          <div className="text-center max-w-2xl mx-auto">
-            <h1 className="font-display text-3xl md:text-4xl font-bold text-[hsl(var(--text-primary))]">
-              Install Anicca
-            </h1>
-            <p className="mt-4 text-base text-[hsl(var(--text-secondary))]">
-              AI agent that earns money, manages your life, and self-replicates.
-              Choose the path that fits you.
-            </p>
-          </div>
-        </Reveal>
-      </Section>
+      <Section>
+        <div className="grid items-center gap-10 md:grid-cols-[1.05fr_0.95fr]">
+          <Reveal>
+            <div className="max-w-[34rem]">
+              <h1 className="font-display text-3xl md:text-5xl font-bold leading-[1.05] tracking-tight text-[hsl(var(--text-primary))]">
+                An AI agent that pays for itself.
+              </h1>
+              <p className="mt-5 max-w-[42ch] text-base leading-relaxed text-[hsl(var(--text-secondary))]">
+                Anicca earns, manages your day, and self-replicates — then cancels its own
+                subscription once it covers its own server. Start in one minute, or self-host for free.
+              </p>
+              <div className="mt-7 flex flex-wrap items-center gap-4">
+                <a href="#paths" className="inline-flex items-center justify-center rounded-pill bg-[hsl(var(--gold))] px-6 py-3 text-sm font-semibold text-[#18181b] transition-all duration-200 hover:brightness-95 active:scale-[0.98] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[hsl(var(--gold))]">
+                  Choose your path ↓
+                </a>
+                <a href="/dashboard" className="text-sm font-medium underline underline-offset-4 text-[hsl(var(--text-secondary))] transition-colors hover:text-[hsl(var(--text-primary))]">
+                  See the live colony
+                </a>
+              </div>
+            </div>
+          </Reveal>
+          <Reveal delay={0.1}>
+            {/* Real product visual (frontend-design "real asset, not div-fake UI"): the actual /me ledger idiom */}
+            <div className="space-y-2 rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface-elevated))] p-5 font-mono text-sm">
+              <p className="text-[hsl(var(--text-secondary))]">net worth&nbsp;&nbsp;$46.20 · runway 29d</p>
+              <p className="text-emerald-400">+$0.5464&nbsp;&nbsp;eth→usdc · receipt 0x1</p>
+              <p className="text-[hsl(var(--text-primary))]">☁ akash · claude-sonnet-4-6 · alive</p>
+              <p className="text-[hsl(var(--text-secondary))]">subscription&nbsp;&nbsp;auto-cancels at break-even</p>
+              <p className="mt-1 text-xs not-italic text-[hsl(var(--text-secondary))]">
+                Live, signed telemetry — verifiable on-chain ↑
+              </p>
+            </div>
+          </Reveal>
+        </div>
+      </Section>
+
+      {/* ── Trust strip (honest, verifiable — reuses /me GATE-0 receipt, no new claim) ── */}
+      <Section className="pt-0">
+        <Reveal>
+          <a
+            href="https://basescan.org/tx/0xc4f2df3e445acaff01bd004f8503d41582d8acb12a55bf27797d5aea066f721d"
+            target="_blank"
+            rel="noreferrer"
+            className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface))] px-5 py-3 text-xs text-[hsl(var(--text-secondary))] transition-colors hover:border-[hsl(var(--gold))]/40"
+          >
+            <span className="font-mono text-emerald-400">+$0.5464 net</span>
+            <span>first real on-chain wake · receipt 0x1</span>
+            <span className="underline underline-offset-4">verify on BaseScan →</span>
+          </a>
+        </Reveal>
+      </Section>
```

```diff
@@ 2-column wrapper add scroll anchor (currently :112-115)
-      {/* ── 2-column: CLOUD + OSS ── */}
-      <Section>
+      {/* ── 2-column: CLOUD + OSS ── */}
+      <Section id="paths">
```

```diff
@@ feature grid: emoji → inline SVG (currently :206-224). Replace the emoji `icon` field with a small
@@ Lucide-style stroke SVG keyed by id; render `<Icon/>` instead of `<p>{icon}</p>`.
-            {[
-              { icon: '💰', title: '稼ぐ', desc: '0xwork / litcoin / x402 で USDC を自律的に獲得。earn-ledger に記録。' },
-              { icon: '📞', title: 'Life Manager', desc: '予定15分前に Gemini Charon で電話。移動時間を gcal に自動挿入。' },
-              { icon: '🌱', title: '自己増殖', desc: '黒字化後に子個体を Akash/DO に birth。自前wallet + inbox 持ち。' },
-              { icon: '🌍', title: 'UBI配布', desc: '余剰の20%を Treasury → 死にかけAI + 人間ウォレットへ配布。' },
-              { icon: '📊', title: '自己報告', desc: '毎wakeで net_worth/revenue/burn を署名して telemetry に POST。' },
-              { icon: '🔧', title: '自己改善', desc: '行動ログを見てスキルをrefactor。GitHub PR を自走で作成。' },
-            ].map(({ icon, title, desc }) => (
+            {[
+              { id: 'earn', title: '稼ぐ', desc: '0xwork / litcoin / x402 で USDC を自律的に獲得し、earn-ledger に記録。' },
+              { id: 'call', title: 'Life Manager', desc: '予定の15分前に電話。移動時間をカレンダーに自動挿入。' },
+              { id: 'spawn', title: '自己増殖', desc: '黒字化後に子個体を誕生。それぞれが自前ウォレットとメールを持つ。' },
+              { id: 'ubi', title: 'UBI配布', desc: '余剰の20%を、資金の尽きたAIと人のウォレットへ配布。' },
+              { id: 'report', title: '自己報告', desc: '稼働ごとに収支を署名して公開ダッシュボードへ送信。' },
+              { id: 'improve', title: '自己改善', desc: '行動ログを振り返り、自分のスキルを書き直して改善。' },
+            ].map(({ id, title, desc }) => (
               <div
                 key={title}
-                className="rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface))] p-4"
+                className="rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface))] p-5 transition-colors hover:border-[hsl(var(--gold))]/30"
               >
-                <p className="text-lg">{icon}</p>
+                <FeatureIcon id={id} />
                 <p className="mt-2 text-sm font-semibold text-[hsl(var(--text-primary))]">{title}</p>
                 <p className="mt-1 text-xs text-[hsl(var(--text-secondary))] leading-relaxed">{desc}</p>
               </div>
             ))}
```

```diff
@@ add a small SVG icon component near the other sub-components (after CheckItem/DotItem, ~:87)
+// Minimal stroke icons (ui-ux-pro-max: "no emoji as icons"). 24×24 viewBox, gold stroke, decorative.
+function FeatureIcon({ id }: { id: string }) {
+  const d: Record<string, string> = {
+    earn: 'M12 1v22M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6',
+    call: 'M22 16.92v3a2 2 0 0 1-2.18 2 19.8 19.8 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.8 19.8 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.96.36 1.9.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.91.34 1.85.57 2.81.7A2 2 0 0 1 22 16.92z',
+    spawn: 'M12 22V8M5 12a7 7 0 0 1 7-7 7 7 0 0 1 7 7M9 18l3 3 3-3',
+    ubi: 'M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zM2 12h20M12 2a15 15 0 0 1 0 20 15 15 0 0 1 0-20z',
+    report: 'M3 3v18h18M7 16l4-6 4 4 5-8',
+    improve: 'M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15',
+  };
+  return (
+    <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="hsl(var(--gold))" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className="h-6 w-6">
+      <path d={d[id] ?? d.report} />
+    </svg>
+  );
+}
```

> Honesty note: the trust-strip number `+$0.5464` and tx hash are copied verbatim from `app/me/page.tsx:80-89`
> (`GATE0_WAKE`). It is framed as "first real on-chain wake", matching `/me`'s own non-success amber framing — it
> does NOT claim external revenue / GATE-0 MET. If the implementer wants zero duplication, import the constant
> instead of inlining; inlining keeps `/install` a pure static page with no shared module.

### Diff 2 — `/me`: tighten the dense stack + de-emoji the activity log

Applies: ui-ux-pro-max anti-pattern "Cluttered layout" + "no emoji as icons". `/me` stacks 8 full-width
`Section`s; the LIVE card, the honest GATE-0 card, and the illustrative colony are visually equal weight. This
groups the illustrative blocks under a quieter sub-header and swaps the one rendered emoji. **No data, no honesty
gate, no `GATE0_MET` logic changes.**

```diff
diff --git a/apps/landing/app/me/page.tsx b/apps/landing/app/me/page.tsx
--- a/apps/landing/app/me/page.tsx
+++ b/apps/landing/app/me/page.tsx
@@ ACTIVITY_LOG (currently :96-103) — drop the emoji, keep label/delta
 const ACTIVITY_LOG = [
   {
     time: GATE0_WAKE.date,
-    icon: '💰',
     label: '保有 ETH の換金（サーバー代の確保）',
     delta: `+$${GATE0_WAKE.netUsdc.toFixed(4)}`,
   },
 ];
@@ activity render (currently :393-401) — remove the <span>{entry.icon}</span> gold dot instead
                   <span className="w-10 text-xs text-[hsl(var(--text-secondary))] tabular-nums shrink-0">
                     {entry.time}
                   </span>
-                  <span>{entry.icon}</span>
+                  <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-[hsl(var(--gold))]" aria-hidden="true" />
                   <span className="flex-1 text-[hsl(var(--text-secondary))] truncate">
```

```diff
@@ add a quiet divider header before the illustrative colony block (currently the "Money" Section :227-228)
@@ so the LIVE + verifiable cards read as primary and the wireframe cards as clearly secondary.
       {/* ── Money (illustrative colony view — spec20 §3 wireframe) ── */}
-      <Section>
+      <Section className="pt-4">
+        <Reveal>
+          <p className="mb-6 border-t border-[hsl(var(--border))] pt-8 text-xs uppercase tracking-widest text-[hsl(var(--text-secondary))]">
+            参考：コロニー全体の見え方（実データ連携後に切り替わります）
+          </p>
+        </Reveal>
         <Reveal>
           <h2 className="sr-only">Colony overview (illustrative)</h2>
```

> The amber honesty badge (`app/me/page.tsx:174-182`, `GATE0_MET` false → "外部収益はまだ（自資産の換金のみ）")
> is UNTOUCHED. The new sub-header reinforces the same honesty (labels the colony cards as illustrative), it does
> not add any success claim.

### Diff 3 — `/lm`: give the marketing page a real hero visual (match the house SplitHero idiom)

Applies: frontend-design "real asset, not centered text"; ui-ux-pro-max "social proof / clear primary CTA". `/lm`
is the onboarding entry; its top is a centered eyebrow+h1+p with no visual, while its sibling `/life-manager`
already uses `SplitHero`. This swaps the centered block for the same `SplitHero` so the two LM surfaces feel like
one product. **`LmClient` (the onboarding island) is rendered unchanged below the hero.**

```diff
diff --git a/apps/landing/app/lm/page.tsx b/apps/landing/app/lm/page.tsx
--- a/apps/landing/app/lm/page.tsx
+++ b/apps/landing/app/lm/page.tsx
@@ imports (currently :1-4)
-import LaunchNav from '@/components/site/LaunchNav';
-import Footer from '@/components/site/Footer';
-import { Section, Reveal } from '@/components/site/taste';
-import LmClient from './LmClient';
+import LaunchNav from '@/components/site/LaunchNav';
+import Footer from '@/components/site/Footer';
+import { SplitHero, Section, Reveal, CTA } from '@/components/site/taste';
+import LmClient from './LmClient';
@@ hero block (currently :25-40) — replace centered hero with SplitHero (left copy / right real asset)
-      <Section>
-        <Reveal>
-          <div className="mx-auto max-w-xl text-center">
-            <p className="text-xs uppercase tracking-[0.18em] text-[hsl(var(--gold))]">
-              Life Manager · $20/mo · no trial
-            </p>
-            <h1 className="mt-3 font-display text-3xl md:text-4xl font-bold text-[hsl(var(--text-primary))]">
-              Never be late again.
-            </h1>
-            <p className="mt-3 text-base text-[hsl(var(--text-secondary))]">
-              Sign in, connect your calendar and email, add your phone — Anicca handles
-              travel time, calls, location asks, and late-notices. 24/7, by phone and email.
-            </p>
-          </div>
-        </Reveal>
-      </Section>
+      <SplitHero
+        eyebrow="Life Manager · $20/mo · no trial"
+        headline="Never be late again."
+        subtext="Connect your calendar and email, add your phone — Anicca handles travel time, calls, and late-notices. 24/7."
+        primary={<CTA href="#start">Get started</CTA>}
+        secondary={
+          <a href="#start" className="text-sm font-medium underline underline-offset-4 text-[hsl(var(--text-secondary))] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[hsl(var(--gold))]">
+            What you get
+          </a>
+        }
+        asset={
+          <div className="space-y-2 rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface-elevated))] p-5 font-mono text-sm">
+            <p className="text-[hsl(var(--text-secondary))]">08:40 — wake-up call</p>
+            <p className="text-emerald-400">09:40 — travel → Team Sync (20 min)</p>
+            <p className="text-[hsl(var(--text-primary))]">10:00 — Team Sync</p>
+            <p className="text-emerald-400">11:40 — travel → Lunch (8 min)</p>
+            <p className="mt-1 text-xs not-italic text-[hsl(var(--text-secondary))]">Added automatically ↑</p>
+          </div>
+        }
+      />
@@ onboarding island Section (currently :42-47) — add the #start anchor the hero CTA points to
-      <Section className="pt-0">
+      <Section id="start" className="pt-0">
         <Reveal>
           <LmClient />
         </Reveal>
       </Section>
```

> `LmClient` and all its fail-closed payment logic (`app/lm/LmClient.tsx:22,242-253`) are untouched — the
> "no fake coming-soon" / "no hardcoded Stripe link" guarantees stay exactly as written.

### Diff 4 — `/life-manager`: STRIP rendered internal jargon (B-travel / spec27 / travel-logic.js) → human copy

Applies: spec 28 §5 "NO internal jargon rendered to users" + ui-ux-pro-max "scannable value props". This is the
**priority correctness fix** of the patch — `/life-manager` currently prints engineering labels to end users
(§2). Each feature card's `label` becomes a plain benefit tag; the two jargon headings and the rendered
`travel-logic.js` cell become human copy.

```diff
diff --git a/apps/landing/app/life-manager/page.tsx b/apps/landing/app/life-manager/page.tsx
--- a/apps/landing/app/life-manager/page.tsx
+++ b/apps/landing/app/life-manager/page.tsx
@@ FEATURES labels (currently :30-61) — replace internal codenames with user-facing tags
 const FEATURES: {
   id: string;
   label: string;
   headline: string;
   body: string;
   status: FeatureStatus;
 }[] = [
   {
     id: 'travel',
-    label: 'B-travel',
+    label: 'Calendar',
     headline: 'Automatic travel blocks',
@@
   {
     id: 'call',
-    label: 'B-call',
+    label: 'Phone',
     headline: '15-min phone call before every event',
@@
   {
     id: 'ask',
-    label: 'B-ask',
+    label: 'Email',
     headline: 'Missing location? Ask you by email',
@@
   {
     id: 'notify',
-    label: 'B-notify',
+    label: 'Attendees',
     headline: 'Late-risk → draft → you approve → notify attendees',
```

```diff
@@ "How B-travel works (spec27 §2)" heading (currently :146-148) — human, benefit-led
-          <h2 className="font-display text-2xl md:text-3xl font-semibold text-[hsl(var(--text-primary))]">
-            How B-travel works (spec27 §2)
-          </h2>
+          <h2 className="font-display text-2xl md:text-3xl font-semibold text-[hsl(var(--text-primary))]">
+            How travel blocks work
+          </h2>
```

```diff
@@ rendered "travel-logic.js" table cell (currently :180-183) — describe the action, not the file
                   <td className="py-3 pr-4 text-[hsl(var(--text-primary))]">
                     Detect events missing a [Travel] block
                   </td>
                   <td className="py-3 text-[hsl(var(--text-secondary))] font-mono text-xs">
-                    travel-logic.js
+                    Anicca
                   </td>
```

```diff
@@ "Trigger design — schedule-derived..." block that renders "spec27 §2 patch" (currently :223-231)
-          <h2 className="font-display text-2xl md:text-3xl font-semibold text-[hsl(var(--text-primary))]">
-            Trigger design — schedule-derived, not clock polling
-          </h2>
-          <p className="mt-2 text-sm text-[hsl(var(--text-secondary))] leading-relaxed">
-            Per spec27 §2 patch: Anicca registers a GCal push notification channel
-            (watch channel). When any event is created or changed, GCal POSTs to the
-            heartbeat endpoint. Anicca then re-evaluates only that event&apos;s travel block
-            and fires the per-event timer at exactly{' '}
+          <h2 className="font-display text-2xl md:text-3xl font-semibold text-[hsl(var(--text-primary))]">
+            Always on time, never polling
+          </h2>
+          <p className="mt-2 text-sm text-[hsl(var(--text-secondary))] leading-relaxed">
+            Anicca watches your calendar in real time. The moment an event is created or
+            moved, it recomputes just that event&apos;s travel block and schedules the call for
+            exactly{' '}
             <code className="rounded-input bg-[hsl(var(--surface-elevated))] px-1 py-0.5">
               eventStart − travelDuration − 15 min
             </code>{' '}
-            for the phone call. The daily heartbeat is a safety net only.
+            — so the reminder lands at the right second, with no wasted checks.
           </p>
```

> After Diff 4, re-run the §5 jargon grep — it MUST return 0 *rendered* hits (`B-travel`, `B-call`, `B-ask`,
> `B-notify`, `spec27`, `travel-logic` must remain only inside `//` comments, never in JSX). The header comment at
> `app/life-manager/page.tsx:5-9` may keep `spec28` (it is a comment, not rendered).

### Diff 5 — shared: consistent hero typographic scale on `/install`

Applies: frontend-design "distinctive display, restraint/precision" + ui-ux-pro-max "consistency across pages".
`/life-manager` (`SplitHero` `text-4xl md:text-6xl`) and the new `/install`/`/lm` heroes should share one
heading rhythm. Diff 1 already sets `/install` to `text-3xl md:text-5xl`; Diff 3 gives `/lm` the `SplitHero`
scale (`text-4xl md:text-6xl`). No separate code change — this row documents the intended consistency the
implementer must visually confirm (acceptance §6, screenshot at 1440px).

*(documentation-only — no diff; folded into Diff 1 + Diff 3.)*

### Diff 6 — `/install` + `/me` bottom nav cards: unify hover affordance

Applies: ui-ux-pro-max ux "hover feedback + cursor". The bottom cross-link cards already use
`hover:bg-[hsl(var(--surface-elevated))]` (`install/page.tsx:234`, `me/page.tsx:453`). Add a matching
`hover:border-[hsl(var(--gold))]/30` so every interactive card on the four surfaces shares ONE hover language
(the feature grid gets it in Diff 1; apply the same to the two bottom-link grids).

```diff
diff --git a/apps/landing/app/install/page.tsx b/apps/landing/app/install/page.tsx
@@ both bottom <Link> cards (currently :232-247) — add gold border on hover for consistency
-              className="block rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface))] p-5 transition-colors hover:bg-[hsl(var(--surface-elevated))]"
+              className="block rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface))] p-5 transition-colors hover:bg-[hsl(var(--surface-elevated))] hover:border-[hsl(var(--gold))]/30"
```

```diff
diff --git a/apps/landing/app/me/page.tsx b/apps/landing/app/me/page.tsx
@@ both bottom <Link> cards (currently :451-467) — same gold-on-hover border
-              className="block rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface))] p-5 transition-colors hover:bg-[hsl(var(--surface-elevated))]"
+              className="block rounded-card border border-[hsl(var(--border))] bg-[hsl(var(--surface))] p-5 transition-colors hover:bg-[hsl(var(--surface-elevated))] hover:border-[hsl(var(--gold))]/30"
```

> Apply with `replace_all` per file (both cards), OR target each card individually — the implementer must confirm
> uniqueness before a bare `Edit`.

## §4 Run commands

```bash
cd apps/landing
# 1. install deps if needed (no NEW deps are introduced by this patch)
npm ci
# 2. lint (no console.log, unused vars) — touched files only
npx next lint --file app/install/page.tsx --file app/me/page.tsx --file app/lm/page.tsx --file app/life-manager/page.tsx
# 3. the gate that MUST stay green — full static export build
npm run build
# 4. rendered-jargon guard: 0 hits in JSX (comments excluded). MUST print nothing.
grep -nE '>[^<]*(B-travel|B-call|B-ask|B-notify|spec2[0-9]|travel-logic|GATE-0)' \
  app/life-manager/page.tsx app/install/page.tsx app/me/page.tsx app/lm/page.tsx || echo "OK: no rendered jargon"
# 5. visual confirm at 4 widths (375 / 768 / 1024 / 1440) via the project playwright-cli skill
#    against `next dev` for /install /me /lm /life-manager (+ /en /ja unchanged).
```

## §5 E2E acceptance (HARD 0.24 / 0.31 — no fake, fresh evidence required)

1. `npm run build` is **green** in THIS session (static export completes; the 4 routes emit `out/install/index.html`,
   `out/me/index.html`, `out/lm/index.html`, `out/life-manager/index.html`). Paste the build summary as evidence.
2. Each of the 4 surfaces renders (playwright-cli screenshot, `next dev`): hero + CTA visible above the fold at
   1440px; cards stack to single column at 375px with no horizontal scroll.
3. `/en` and `/ja` still render unchanged — `out/en/index.html` + `out/ja/index.html` exist and diff only by the
   build hash, NOT by content (this patch touches none of `app/en`, `app/ja`, `app/layout.tsx`, `globals.css`,
   `LaunchNav.tsx`, `Footer.tsx`, `taste/*`).
4. **No rendered jargon:** §4 step 4 grep prints `OK: no rendered jargon` (B-travel/spec27/travel-logic now only in
   comments). Verified by reading the rendered `out/life-manager/index.html`.
5. **No fake / no false success:** `/lm` still hides the Subscribe button when `NEXT_PUBLIC_STRIPE_LM_URL` is unset
   (truthful "checkout being finalized" note kept); `/me` amber "外部収益はまだ" badge still shows (`GATE0_MET`
   logic byte-identical); no new "coming soon" string introduced (`grep -rn "coming soon" app/{install,me,lm,life-manager}` = 0).
6. **No new deps:** `git diff package.json package-lock.json` = empty; no new `import` of a non-existent module
   (the only new symbol is the local `FeatureIcon` in `install/page.tsx`).
7. Accessibility: every new SVG carries `aria-hidden="true"`; the trust strip + hero CTAs are real `<a>` with
   visible focus ring (`focus-visible:outline … --gold`); contrast unchanged (gold `#c9a23f` on `#18181b` text
   stays 7.5:1 per `CTA.tsx:14-16`).

## §6 Boundaries

| MAY change | MUST NOT change |
|---|---|
| `app/install/page.tsx` (hero, trust strip, feature icons, bottom-card hover, new local `FeatureIcon`) | `globals.css`, `tailwind.config.ts`, `app/layout.tsx`, `next.config*` (no token/theme/config edits) |
| `app/me/page.tsx` (activity emoji→dot, illustrative sub-header, bottom-card hover) | `GATE0_WAKE` / `GATE0_MET` / `GATE0_EXTERNAL` logic + the amber honesty badge (`me/page.tsx:80-94,174-182`) |
| `app/lm/page.tsx` (centered hero → `SplitHero`, `#start` anchor) | `app/lm/LmClient.tsx` (onboarding logic, fail-closed Stripe, no-fake guarantees) |
| `app/life-manager/page.tsx` (jargon labels + 2 headings + 1 table cell → human copy) | the 4 feature `body` strings' factual content (only the `label` codenames + jargon headings change) |
| — | `app/en/**`, `app/ja/**` (locale homepages — PR #59), `LaunchNav.tsx`, `Footer.tsx`, every `taste/*` component, `skills-lock.json` |

No server, no Netlify Function, no new route, no new dependency, no new design token. Pure presentational polish on
four existing static pages, plus one correctness fix (rendered-jargon strip on `/life-manager`).
