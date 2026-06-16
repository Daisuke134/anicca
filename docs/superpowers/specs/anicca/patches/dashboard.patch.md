# Patch — A-dashboard (`/dashboard`) renders REAL numbers for ALL clients

Subsystem: **dashboard** (spec 26 §A8b / spec 27 §2 A-dashboard / spec 20 §3 `/dashboard`).
Author: dashboard patch-author. Date: 2026-06-16. Branch base: `dev`.
Files in scope: `apps/landing/app/dashboard/page.tsx` (+ build-time prerender helper, append-only).

---

## ★ Premise correction (RAW evidence) — read first

The task brief states the dashboard *"currently serves bare Loading… with no real numbers (verified)."*
That is **true only for non-JS clients (curl / social crawlers / link-preview bots)**. It is **FALSE for a real browser user**.

RAW evidence gathered live on 2026-06-16:

| Probe | Command | Result |
|---|---|---|
| Static SSR HTML (no JS) | `curl -sL https://aniccaai.com/dashboard/` | `<p style="opacity:0.6;font-size:14px">Loading…</p>` + 3 skeleton bars. **No numbers.** |
| Data function (server) | `curl -s https://aniccaai.com/.netlify/functions/dashboard-sync` | `HTTP 200 application/json` → `{"total_net_worth_usd":5.0145,"earned_mo_usd":0,"alive":4,"self_funded_pct":100,"frontier_pct":0,"leaderboard":[…4 rows…],"updated_at":"2026-06-16T01:45:22.455Z"}` |
| Page chunk | `curl -o/dev/null -w%{http_code} …/app/dashboard/page-073b28f7a758b7ef.js` | `200` |
| **Real browser (JS executed)** | `agent-browser open …/dashboard/` → `agent-browser eval "document.body.innerText"` | `Live · 2026/6/16 10:46:18 … TOTAL NET WORTH $5.01 … BODIES ALIVE 4 … SELF-FUNDED % 100% … LEADERBOARD (4 BODIES) #1 0X70997970… test · US … $5.00 …` — **renders REAL numbers.** |
| **Real browser screenshot** | `agent-browser screenshot /tmp/dashboard-live.png` | Shows GROUP P&L: `$5.01` / `$0.00` / `4` / `100%` / `0%`, leaderboard heading "LEADERBOARD (4 BODIES)". Visual confirmed (read PNG). |

Conclusion: the client-side `useEffect` fetch (`page.tsx` L37–53) **works**. The only failure surface is the **static-export SSR snapshot**, which is the pre-hydration `loading=true` state (`page.tsx` L69: `{loading ? "Loading…" : …}`). Every `curl`-based verifier, every Slack/X/Discord/Google link-preview, and every JS-disabled reader sees only "Loading…".

This patch makes the dashboard show REAL numbers to **every** client (JS and no-JS alike) by pre-rendering a data snapshot into the static HTML at build time, while keeping the live client refresh.

---

## Gaps

| # | Spec requires | RAW live evidence | Severity |
|---|---|---|---|
| G1 | spec 20 §3 `/dashboard`: "Total Anicca net worth ★HUGE" visible; spec 26 §A8b verify = "curl 200 ✅ + page を camofox 目視"; **task acceptance = "curl the served HTML and confirm" real numbers** | `curl …/dashboard/` returns only `Loading…` + skeletons, **zero numbers** in the served HTML. Numbers exist only after client JS runs. | **HIGH** — curl/crawler/no-JS verification fails; OGP/Slack/X previews show empty "Loading…". |
| G2 | spec 27 §2 A-dashboard: "全個体の profile+収支が realtime 公開" — must be readable, no human/internal jargon (HARD 0.19 "no jargon", task constraint "no internal jargon") | Browser render shows raw model strings `x (free)` and `auto (free)`, and the **raw 0x wallet hex as the primary line** (`0X70997970C51812DC3A010C7D01B50E0D17DC79C8`). `x` and `auto` are not human model names. | **MEDIUM** — jargon/garbage strings surfaced to public users. |
| G3 | spec 20 §3 ASCII: leaderboard centerpiece + clean lineage; data should be production telemetry | One leaderboard row is a **test fixture**: `{"host":"test","model_live":"x","net_worth_usd":5,…}` — it accounts for **$5.00 of the $5.01** total. Real genesis bodies are `akash`/`do` at `$0.01`/`$0.00`. | **LOW** (data-pipeline, not page) — flagged for visibility; page must not crash on or glamorize the test row. Out of page scope to delete; in scope to label model `x`→"unknown" gracefully. |

This patch fully closes **G1** (the blocking gap) and **G2** (jargon). **G3** is a telemetry/`instances`-table data issue (delete the `host:"test"` row in Supabase); noted as an open question, not fixed in `page.tsx`.

---

## Diff — `apps/landing/app/dashboard/page.tsx`

### Approach (justified)

The site is `output: 'export'` (verified in `apps/landing/next.config.mjs`: `output: 'export'`). A Server Component cannot run a per-request fetch on a static host. Two ways to get numbers into the served HTML:

- **(a) build-time prerender** — fetch the live JSON during `next build`, embed it as the component's initial state. The static HTML ships with real numbers; the client `useEffect` then refreshes to live. Works for **every** client (curl, crawlers, no-JS, JS). Numbers are "fresh as of last deploy" for no-JS, "live" for JS.
- **(b) client-only** — what exists today. Numbers only for JS clients; curl/crawlers see "Loading…".

**Chosen: (a) build-time prerender + keep client live refresh.** It is the only approach that satisfies the task's own acceptance ("curl the served HTML and confirm real numbers") AND spec 26 §A8b ("curl 200 + 目視") on a static export, with no placeholder/mock numbers. The build fetches the *real* function; if the build-time fetch fails, it falls back to `null` (today's behavior) so the build never breaks and the client still hydrates live.

`page.tsx` stays `"use client"` (it needs `useState`/`useEffect`). The build-time snapshot is produced by a tiny async Server Component wrapper around it via the `dashboard/page.tsx`→ data passed as a prop is NOT possible while the leaf is a client component fetching at build. Instead we generate a static JSON snapshot file at build and import it synchronously as the seed. This keeps `page.tsx` a client component, requires no server runtime, and embeds real numbers in the export.

### Diff 1 — new build-time snapshot generator (append-only new file)

`apps/landing/scripts/gen-dashboard-snapshot.mjs` (NEW):

```js
// Build-time: fetch the live dashboard data and write it into the app so the
// static export ships REAL numbers (not a permanent "Loading…").
// Runs in `prebuild`. Never throws — on failure writes an empty snapshot so the
// build still succeeds and the client useEffect refreshes live at runtime.
import { writeFile, mkdir } from "node:fs/promises";
import { dirname } from "node:path";

const OUT = new URL("../app/dashboard/_snapshot.json", import.meta.url);
// Prefer the deployed function; allow override for preview builds.
const SRC =
  process.env.DASHBOARD_SNAPSHOT_URL ||
  "https://aniccaai.com/.netlify/functions/dashboard-sync";

async function main() {
  let snapshot = null;
  try {
    const res = await fetch(SRC, { signal: AbortSignal.timeout(10_000) });
    if (res.ok) {
      const json = await res.json();
      if (json && typeof json.total_net_worth_usd === "number") snapshot = json;
    }
  } catch (e) {
    console.warn(`[gen-dashboard-snapshot] live fetch failed, shipping empty seed: ${e.message}`);
  }
  await mkdir(dirname(OUT.pathname), { recursive: true });
  await writeFile(OUT, JSON.stringify(snapshot));
  console.log(`[gen-dashboard-snapshot] wrote seed (${snapshot ? "live" : "empty"}) → app/dashboard/_snapshot.json`);
}
main();
```

### Diff 2 — `apps/landing/package.json` (add prebuild hook)

```diff
   "scripts": {
     "dev": "next dev",
-    "build": "next build",
+    "prebuild": "node scripts/gen-dashboard-snapshot.mjs",
+    "build": "next build",
     "start": "next start",
```

### Diff 3 — `apps/landing/app/dashboard/page.tsx` (seed initial state from snapshot; keep live refresh)

```diff
 "use client";

 import { useEffect, useState } from "react";
+import snapshot from "./_snapshot.json";

 // Metadata is exported from a separate layout or via static export approach
 // (app/dashboard/layout.tsx) — cannot use export const metadata in "use client".
@@
 export default function DashboardPage() {
-  const [data, setData] = useState<DashboardData | null>(null);
-  const [error, setError] = useState<string | null>(null);
-  const [loading, setLoading] = useState(true);
+  // Build-time snapshot seeds the static HTML so curl / crawlers / no-JS clients
+  // see REAL numbers immediately. The client useEffect then refreshes to live.
+  const seed = (snapshot as DashboardData | null) ?? null;
+  const [data, setData] = useState<DashboardData | null>(seed);
+  const [error, setError] = useState<string | null>(null);
+  const [loading, setLoading] = useState(seed === null);

   useEffect(() => {
     let cancelled = false;
     async function load() {
       try {
         const res = await fetch("/.netlify/functions/dashboard-sync");
         if (!res.ok) throw new Error(`dashboard-sync returned ${res.status}`);
         const json = await res.json();
-        if (!cancelled) setData(json);
+        if (!cancelled) { setData(json); setError(null); }
       } catch (e) {
-        if (!cancelled) setError(e instanceof Error ? e.message : "fetch error");
+        // If we already have seed data, keep showing it; only surface error when we have nothing.
+        if (!cancelled && !data) setError(e instanceof Error ? e.message : "fetch error");
       } finally {
         if (!cancelled) setLoading(false);
       }
     }
     load();
     return () => { cancelled = true; };
-  }, []);
+    // eslint-disable-next-line react-hooks/exhaustive-deps
+  }, []);
```

The status line (`page.tsx` L68–70) already reads `loading ? "Loading…" : error ? … : \`Live · …\``. With `seed !== null`, `loading` starts `false`, so the served HTML shows `Live · <date>` plus the full `DashboardBody` (real numbers) — no permanent "Loading…".

### Diff 4 — G2 jargon: humanize model + de-emphasize raw wallet hex (`page.tsx` `InstanceCard`)

```diff
+function humanModel(live?: string, tier?: string): string {
+  if (!live || live === "x" || live === "auto") return tier === "free" ? "Free model" : "Auto";
+  return live;
+}
@@ InstanceCard
-          <p style={{ fontSize: 10, letterSpacing: 3, textTransform: "uppercase", opacity: 0.5 }}>{row.id}</p>
-          <p style={{ fontSize: 18, marginTop: 4 }}>{row.host} · {row.geo ?? "?"}</p>
-          <p style={{ fontSize: 12, opacity: 0.6, marginTop: 2 }}>{row.model_live ?? "—"} ({row.model_tier ?? "?"})</p>
+          <p style={{ fontSize: 18, marginTop: 4 }}>{row.host} · {row.geo ?? "—"}</p>
+          <p style={{ fontSize: 12, opacity: 0.6, marginTop: 2 }}>{humanModel(row.model_live, row.model_tier)}</p>
+          <p style={{ fontSize: 10, letterSpacing: 2, opacity: 0.35, marginTop: 4, wordBreak: "break-all" }}>{row.id.slice(0, 6)}…{row.id.slice(-4)}</p>
```

(Raw 0x hex moves from the prominent top line to a dimmed short-form `0x7099…79c8` sub-line; the model column no longer prints `x`/`auto`.)

### Diff 5 — `apps/landing/.gitignore` add generated snapshot (NEW or append)

```
app/dashboard/_snapshot.json
```

Commit a placeholder `app/dashboard/_snapshot.json` containing `null` so the import resolves on a clean checkout / before `prebuild` runs; `prebuild` overwrites it. (TypeScript: ensure `resolveJsonModule` is on in `tsconfig.json` — verify; if absent, add `"resolveJsonModule": true`.)

---

## Commands

```bash
# --- apply (on dev, isolated worktree per HARD RULE #0) ---
cd /Users/anicca/anicca-project
git fetch origin && git checkout dev && git pull
git worktree add ../anicca-dashboard -b feature/dashboard-real-numbers
cd ../anicca-dashboard/apps/landing
# apply Diff 1..5 (new scripts/gen-dashboard-snapshot.mjs, package.json prebuild,
#   app/dashboard/page.tsx edits, app/dashboard/_snapshot.json placeholder=null, .gitignore)

# --- local build verify: static HTML must contain real numbers, not only "Loading…" ---
npm run build
grep -o 'TOTAL NET WORTH\|Loading…\|Group P' out/dashboard/index.html | sort -u   # expect Group P&L present
node -e "const h=require('fs').readFileSync('out/dashboard/index.html','utf8'); if(/Loading…/.test(h) && !/Net Worth|Group P/i.test(h)){console.error('FAIL: still Loading-only');process.exit(1)} console.log('OK: HTML has rendered body')"

# --- commit + PR → main (deploy) ---
cd /Users/anicca/anicca-dashboard
git add -A && git commit -m "fix(dashboard): prerender real numbers into static export (no permanent Loading…)"
git push -u origin feature/dashboard-real-numbers
gh pr create --base dev --title "dashboard: real numbers for all clients" --body "Build-time snapshot + live refresh. Closes curl/crawler Loading… gap."
# merge to dev → verify staging → PR dev→main → main push auto-deploys aniccaai.com (netlify-deploy.yml)

# --- VERIFY live (after deploy) ---
# 1) curl the served HTML — must now contain real numbers, NOT only "Loading…"
curl -sL https://aniccaai.com/dashboard/ | grep -o 'Group P&amp;L\|Total Net Worth\|Loading…'   # expect Group P&L / Total Net Worth, NOT lone Loading…
# 2) browser render (camofox preferred; agent-browser is the working fallback here — camofox needs `camoufox fetch`)
camoufox fetch   # one-time install so camofox :9377 works
# then: open https://aniccaai.com/dashboard/ via camofox, screenshot → must show $<total_net_worth> + leaderboard, no Loading…
# fallback (verified working this session):
agent-browser open "https://aniccaai.com/dashboard/"
agent-browser eval "document.body.innerText" | grep -E 'TOTAL NET WORTH|LEADERBOARD'   # must match real numbers
agent-browser screenshot /tmp/dashboard-after.png   # read PNG: real $ total + leaderboard, no "Loading…"
agent-browser close
```

---

## Acceptance (rubric — all must pass)

| # | Criterion | Pass condition |
|---|---|---|
| 1 | Real instance numbers | Dashboard shows live `total_net_worth_usd`, leaderboard (≥ real bodies), `alive`, `self_funded_pct` from `dashboard-sync` — no mock/placeholder. |
| 2 | **curl shows numbers** | `curl -sL https://aniccaai.com/dashboard/` served HTML contains "Group P&L"/"Total Net Worth" + a `$` value — **NOT** lone "Loading…". |
| 3 | Browser screenshot | camofox (or agent-browser fallback) opens live `/dashboard`; screenshot shows real `$<total>` + leaderboard rows, **no "Loading…" only** state. |
| 4 | Deployed | Change merged dev→main, `aniccaai.com/dashboard` auto-deployed (netlify-deploy.yml), live URL reflects it. |
| 5 | No jargon | No raw `x`/`auto` model strings as model name; raw 0x wallet hex not the prominent primary line (short-form only). |
| 6 | No regression | JS clients still get live (post-deploy) refresh via `useEffect`; build never breaks if snapshot fetch fails (ships seed=null → today's behavior). |
```
