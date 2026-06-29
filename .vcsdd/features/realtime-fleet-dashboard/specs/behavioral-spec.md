# Behavioral Spec — realtime-fleet-dashboard (lean, typescript) — ITERATION 3 (grounded; fixes F1–F16 + N1–N9; spec gate PASS)

## Goal (provable)
Make `/dashboard` a LIVE fleet board sourced from the EXISTING signed-telemetry → Supabase pipeline, showing every
Anicca instance's **assets (net worth) + revenue + real activity log**, with **harness/env/brain/model** as the primary
axis and **funding origin (human/self)** + the **economic self-funded flag** as labeled attributes. Kill the page's
hardcoded-fallback + dead static `dashboard.json` read. Add the 3 missing identity fields and wire the page to live data.

## GROUNDING — the REAL existing pipeline (per-artifact repo + path; fixes F1)
Two repos. `~/anicca` (THIS repo, where .vcsdd lives) holds the instance side; `~/anicca-project` holds the receiver + page + Supabase.
| Artifact | Repo / path | What it already does |
|---|---|---|
| poster (heartbeat) | `~/anicca/runtime/dashboard/telemetry-poster.mjs` | every **120s** builds `msg`, **signs with wallet** (`acct.signMessage`), POSTs `{message,signature}` to `aniccaai.com/.netlify/functions/telemetry`. Carries net_worth, revenue, `log: recentLog(20)` |
| identity | `~/anicca/runtime/identity.mjs` | id = **wallet address** (collision-impossible); host = `anicca-<6hex>`; first POST auto-registers |
| receiver | `~/anicca-project/apps/landing/netlify/functions/telemetry.js` | id must be `0x[40hex]`, then `verifyTelemetry` |
| **id-binding (the akash fix)** | `_lib/telemetry-verify.js:28` | `verifyMessage(message,signature)` recovers signer; **`signer.toLowerCase() !== id ⇒ 401 `signer_mismatch`** — a post can only write the row of the wallet that signed it. (NOT a "host-guard"; there is no host check beyond nonempty-string.) Plus freshness: `ts>now+5⇒future`, `now-ts>60⇒stale`, `ts<=lastTs⇒replay` |
| schema | `_lib/telemetry-schema.js` | validates 11 fields; `status ∈ {alive, critical, dead}`; unknown extra keys pass through untouched |
| store | `_lib/telemetry-store.js` | `upsertInstance(p)` POSTs the WHOLE payload `p` to `instances?on_conflict=id` (PostgREST merge-duplicates). PK = id = wallet addr. **Only keys that are COLUMNS persist** → new fields need a DDL migration |
| aggregate | `_lib/telemetry-aggregate.js` | `aggregate(rows)`→`{total_net_worth_usd, earned_mo_usd, alive, self_funded_pct, frontier_pct, leaderboard[], updated_at}`; self-funded = `status!=='dead' && revenue_mo_usd/30 >= burn_day_usd`; `leaderboard` = the FULL rows (`select=*`) sorted by net_worth |
| sync (read API) | `apps/landing/netlify/functions/dashboard-sync.js` | reads `instances?select=*` → `aggregate()` JSON (15s cache); `leaderboard[]` = full rows (carry every column incl `log` IF it is a column) |
| page | `~/anicca-project/apps/landing/app/dashboard/page.tsx` | ★BROKEN: reads STATIC `public/dashboard.json`; empty `lineage` ⇒ 3 HARDCODED rows; never calls dashboard-sync★ |

## Decision: REUSE, do not fork (fixes F2/F8/F10)
The registry IS the existing signed-telemetry→Supabase pipeline. We do **NOT** add an anon Supabase upsert or a new id.
Identity stays **wallet-address id + signature (`signer_mismatch` binds writer→row) + replay guard** (collision/spoof already
prevented). The 3 new fields ride the SAME signed `msg`. `telemetry-poster.mjs` is EXTENDED (not replaced);
`skills/report/anicca-report.sh` (the old `host:'akash'` poster) is NOT reintroduced.

## Scope
IN: (1) add 3 fields `funding('human'|'self')`, `env('local'|'cloud')`, `brain('claude-p'|'proxy')` to the signed `msg`
(poster) + accept/store them (schema + store) + pass through aggregate/leaderboard; (2) a PURE `dashboard-core` (TS) =
status/self-funded/totals/card-model/log-normalize; (3) rewrite `page.tsx` to render LIVE from `dashboard-sync`
(leaderboard[] + totals) with harness/env/brain/model badges + funding label + economic flag + assets(net_worth) +
revenue + per-instance recent log + fleet totals + auto-refresh; (4) ensure THIS human-funded instance posts with
`funding='human',env='local',brain='claude-p'`.
OUT (separate features): resurrection (#17; only the stale DERIVATION is here), day/night (#15), bot2bot semantics (#16),
changing the 120s cadence, basescan cross-check (net worth already computed on-chain by the poster).

## Requirements (EARS) — each objectively checkable
- **REQ-1 (extend signed msg):** WHEN the poster builds `msg`, it SHALL include `funding∈{human,self}`, `env∈{local,cloud}`,
  `brain∈{claude-p,proxy}`, read from env (`ANICCA_FUNDING`/`ANICCA_ENV`/`ANICCA_BRAIN`) with defaults
  `human/local/claude-p`; these fields SHALL be inside the SIGNED message (not added post-signature). NOTE: the poster
  signs the verbatim full `msg` JSON (which already carries extra fields like log/breakdown), so the signature covers the
  3 new fields automatically; `canonicalMessage()` in telemetry-verify is a DORMANT client-side helper NOT on the verify
  path (the verifier recovers the signer from the verbatim bytes), so it needs no change for verification to succeed.
- **REQ-2 (receiver accepts):** the schema/store SHALL accept + persist the 3 new fields; an OLD poster that omits them
  SHALL still upsert (fields default server-side) — backward compatible.
- **REQ-3 (no new auth surface):** writes SHALL remain signature-verified — `verifyTelemetry` recovers the signer and
  requires `signer===id` (`signer_mismatch` else); NO anon/​unauthenticated write path is added; the 3 new fields are
  INSIDE the signed message (so the signature covers them). (closes F2/F8/F10; fixes N1)
- **REQ-4 (deriveStatus, PURE):** GIVEN a row + `nowSec`, derived display status SHALL be: `'dead'` if `status==='dead'`;
  else `'stale'` if `row.ts` is missing/null/NaN OR `nowSec - row.ts > 300` (300s > the real 120s heartbeat); else
  `'critical'` if `status==='critical'` (preserved, not swallowed); else `'alive'`. (fixes F7 null/NaN; F12 cadence; N3 critical)
- **REQ-5 (economic self-funded, PURE):** `isSelfFundedEconomic(row, nowSec)` SHALL be `deriveStatus(row,nowSec)!=='dead'
  && (revenue_mo_usd/30) >= burn_day_usd`. Division is by the constant 30 only (no division by burn_day). Signature is
  `(row, nowSec)` in BOTH spec docs. (fixes F5; N9)
- **REQ-6 (counts PURE; $ totals REUSED):** to avoid forking `aggregate()`, the $ totals (`total_net_worth_usd`,
  `earned_mo_usd`, `self_funded_pct`, `frontier_pct`) SHALL be REUSED from the server-side `aggregate()` output (extended:
  `self_funded_pct` already uses the economic test REQ-5; `aggregate` is NOT reimplemented in TS). The ONLY new aggregation
  is `countByStatus(rows, nowSec) -> {alive, stale, dead, critical}` (TS pure, display-staleness over `row.ts`, which
  `aggregate` does not compute). ON empty fleet `countByStatus([])` = all-zero. `self_funded_pct` source = the economic
  flag (REQ-5), not the declared `funding`. (fixes F6, F11; resolves N2 — no $ duplication)
- **REQ-7 (render live, no fake):** WHEN `/dashboard` loads, it SHALL fetch `dashboard-sync` (live) and render its
  `leaderboard[]` + totals. IF the fetch fails, it SHALL show an explicit "registry unavailable" state — NEVER the
  hardcoded fallback rows (which SHALL be deleted) and NEVER the stale static `dashboard.json`. (fixes F9 fate-of-sync: KEEP dashboard-sync as the source)
- **REQ-8 (badges + assets + revenue + log, view-model PURE):** `toCardModel(row, nowSec)` SHALL return the FULL fixed
  shape (no open-ended fields): `{ id, host, statusDisplay, funding, env, brain, model, modelTier, walletUrl, assetsUsd(=net_worth_usd),
  revenueMoUsd, burnDayUsd, netUsd, selfFundedEconomic:boolean, logs: Array<{ts,kind,note}> (newest-first, ≤20 from the
  row's `log[]`) }`. Each card SHALL visibly show env/brain/model/funding + assets + revenue + the recent log. (fixes F3 assets=net_worth incl positions+HL; F13/F14 logs in model + full shape)
- **REQ-9 (primary axis vs funding, per THESIS):** the PRIMARY visual grouping/axis SHALL be harness/env/brain/model
  (THESIS: human/self-funded "behave identically"; the meaningful axis is the harness/env). `funding` SHALL be shown as a
  labeled ORIGIN attribute (Dais: keep the distinction visible) and the ECONOMIC self-funded flag (REQ-5) shown as the REAL
  independence metric — documented so a `funding='human' & economic=true` row reads "kickstarted by a human, now economically
  self-sustaining". (resolves F4)
- **REQ-10 (real-time refresh):** WHILE `/dashboard` is open it SHALL refresh from `dashboard-sync` at an interval ≤ the
  heartbeat (≤120s; default 30s client poll is acceptable and SHALL be labelled in code as the mechanism). Activity
  granularity is bounded by the 120s poster; finer (event-driven) posting is OUT of scope. (fixes F16 SLA realism)
- **REQ-11 (this instance):** the human-funded body (wallet `0x810f…29c5`, host `anicca-810f…`) SHALL post with
  `funding='human',env='local',brain='claude-p'` and appear as a LIVE row (derived status alive), assets = its on-chain
  net worth. NOTE: `model_live` is DERIVED by the poster (`lastModel()` from the ledger), not declared; with `brain='claude-p'`
  it will read `claude-sonnet-4-6`. (fixes N8)
- **REQ-13 (DDL migration — do NOT assume columns):** persisting the new fields + per-instance logs requires the Supabase
  `instances` table to HAVE those columns. The feature SHALL ship an explicit migration `ALTER TABLE instances ADD COLUMN
  IF NOT EXISTS funding text, ADD COLUMN IF NOT EXISTS env text, ADD COLUMN IF NOT EXISTS brain text;` and SHALL verify
  (round-trip integration test) that `log` is a persisted column (jsonb) — adding it if absent. Without the migration,
  `upsertInstance` silently drops the keys and REQ-8 logs + the F16 sentinel cannot render. (fixes N7)
- **REQ-14 (defaults for legacy rows):** the migration columns default NULL; a row from an OLD poster (no fields) renders
  funding/env/brain as `'unknown'` (NOT assumed human/local). A CURRENT poster always sends them (REQ-1 env defaults). (fixes N4)
- **REQ-12 (key safety, testable):** the signed `msg` payload key-set SHALL be a FIXED allowlist (the documented fields);
  a test SHALL assert (a) the wallet private key string and `SUPABASE_SERVICE_ROLE_KEY` value NEVER appear as a substring
  of any posted `message`, and (b) no key outside the allowlist is present. The private-key heuristic SHALL NOT scan the
  `log[]` notes for 64-hex (no `tx_hash` field exists in this payload). (fixes F15)

## Acceptance / E2E (objective; fixes F16)
- Unit (pure `dashboard-core`, no network): REQ-4 (incl. missing/NaN ts, exactly-300s boundary, dead), REQ-5, REQ-6
  (incl. empty fleet → pct 0, negative net), REQ-8 toCardModel full-shape + log ordering/cap, normalizeLogKind. RED first.
- Integration: a signed post incl. the 3 new fields → receiver 202 → row upserted with the fields; an old post (no fields)
  → still 202 + defaults; an UNSIGNED/anon write attempt → rejected (proves REQ-3).
- E2E (MY browser, AFTER adversary PASS): write a UNIQUE random sentinel string into THIS instance's `ledger.jsonl`; run one
  poster cycle; open `/dashboard`; assert that exact sentinel appears in the rendered DOM within one poll+heartbeat window
  (≤150s) on this instance's card, AND the 3 badges (human/local/claude-p) render. The unique sentinel proves it is the LIVE
  registry, not a cached/hardcoded board. Screenshot + DOM check.
