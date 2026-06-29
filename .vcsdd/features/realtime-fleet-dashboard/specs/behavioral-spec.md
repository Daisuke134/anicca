# Behavioral Spec — realtime-fleet-dashboard (lean, typescript) — ITERATION 2 (grounded; fixes F1–F16)

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
| receiver | `~/anicca-project/apps/landing/netlify/functions/telemetry.js` | verifies signature (`telemetry-verify.js`, round-3 bytes), id must be `0x[40hex]`, **replay guard** (monotonic `getLastTs`), then `upsertInstance` |
| host-guard | telemetry-verify | rejects post whose host ≠ `anicca-<wallet hex>` (400 host_wallet_mismatch) — the **akash-stole-the-row fix** |
| store | `~/anicca-project/apps/landing/netlify/functions/_lib/telemetry-store.js` | upsert into Supabase `instances` (PK = id = wallet addr) |
| aggregate | `_lib/telemetry-aggregate.js` | `aggregate(rows)`→`{total_net_worth_usd, earned_mo_usd, alive, self_funded_pct, frontier_pct, leaderboard[], updated_at}`; self-funded = `status!=='dead' && revenue_mo_usd/30 >= burn_day_usd` |
| sync (read API) | `_lib/dashboard-sync.js` (netlify fn) | returns `aggregate()` JSON (15s cache); `leaderboard[]` keyed by `host` |
| page | `~/anicca-project/apps/landing/app/dashboard/page.tsx` | ★BROKEN: reads STATIC `public/dashboard.json`; empty `lineage` ⇒ 3 HARDCODED rows; never calls dashboard-sync★ |

## Decision: REUSE, do not fork (fixes F2/F8/F10)
The registry IS the existing signed-telemetry→Supabase pipeline. We do **NOT** add an anon Supabase upsert or a new id.
Identity stays **wallet-address + signature + host-guard + replay guard** (collision/spoof already prevented). The 3 new
fields ride the SAME signed `msg`. `telemetry-poster.mjs` is EXTENDED (not replaced); `skills/report/anicca-report.sh`
(the old `host:'akash'` poster) is NOT reintroduced.

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
  `human/local/claude-p`; these fields SHALL be inside the SIGNED message (not added post-signature).
- **REQ-2 (receiver accepts):** the schema/store SHALL accept + persist the 3 new fields; an OLD poster that omits them
  SHALL still upsert (fields default server-side) — backward compatible.
- **REQ-3 (no new auth surface):** writes SHALL remain signature-verified with the host-guard; NO anon/​unauthenticated
  write path is added. (closes F2/F8/F10)
- **REQ-4 (deriveStatus, PURE):** GIVEN a row + `nowSec`, derived display status SHALL be: `'dead'` if `status==='dead'`;
  else `'stale'` if `last ts` is missing/NaN OR `nowSec - ts > 300` (300s = 2.5× the real 120s heartbeat); else `'alive'`.
  (fixes F7 null/NaN; F12 cadence — threshold ABOVE the 120s heartbeat).
- **REQ-5 (economic self-funded, PURE):** `isSelfFundedEconomic(row)` SHALL be `deriveStatus!=='dead' && (revenue_mo_usd/30) >= burn_day_usd`.
  Division is by the constant 30 only (no division by burn_day) → no burn_day=0 hazard. (fixes F5)
- **REQ-6 (totals, PURE):** `computeTotals(rows, nowSec)` SHALL return `{assets:Σ net_worth_usd, revenue30d:Σ revenue_mo_usd,
  net:Σrevenue_mo − Σ(burn_day·30), counts:{alive,stale,dead}, self_funded_pct, frontier_pct}`. ON empty fleet (len 0)
  BOTH pcts SHALL be `0` (guard 0-denominator). `self_funded_pct` SHALL be computed from `isSelfFundedEconomic` (REQ-5),
  NOT from the declared `funding` field. (fixes F6, F11)
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
  `funding='human',env='local',brain='claude-p',model='claude-sonnet-4-6'` and appear as a LIVE row (status alive),
  assets = its on-chain net worth.
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
