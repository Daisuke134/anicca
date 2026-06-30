# Behavioral Spec v2 — agents-at-arms-leaderboard (VCSDD Phase 1a/1b, lean)

Source design: `docs/superpowers/specs/2026-07-01-agents-at-arms-live-leaderboard-design.md`.
**v2 reconciles against the LIVE telemetry pipeline** (fixes adversary spec-verdict FAIL,
sprint-1/output/spec-verdict.md). Ground truth code:
- `apps/landing/netlify/functions/_lib/telemetry-schema.js` — row validator (authoritative vocabulary)
- `apps/landing/netlify/functions/_lib/telemetry-aggregate.js` — emits `{..., leaderboard, ...}`
- `apps/landing/netlify/functions/_lib/telemetry-verify.js` — signed-heartbeat canonical message
- `apps/landing/components/site/{EmpireDashboard.tsx, v2/useDashboard.ts}` — consumers

## Live vocabulary (USE THESE EXACT NAMES — do not invent)
Row (per `telemetry-schema.js`): `id` (=`0x`+40hex EVM wallet, the on-chain identity), `ts` (int),
`host`, `geo`, `model_live` (string), `model_tier` (`frontier|free`), `net_worth_usd` (num ≥0),
`revenue_mo_usd` (num), `burn_day_usd` (num ≥0), `runway_days` (int ≥0),
`status` (`alive|critical|dead`).
Aggregate output: `total_net_worth_usd, earned_mo_usd, alive, self_funded_pct, frontier_pct,
leaderboard, updated_at`.

## Additive schema extensions (back-compat — all OPTIONAL so existing rows still validate)
`revenue_today_usd?` (num), `revenue_by_source?` (object), `tags?` (string[], e.g. `["agent-hackathon"]`),
`log_feed?` (array of `{ts,line}`). Adding these MUST NOT reject any currently-valid row (proof R9).

## 1a. Behavioral requirements (EARS) — each reconciled to live code

- **R1** WHEN `aggregate(rows)` runs, the output SHALL keep all existing keys (`total_net_worth_usd,
  earned_mo_usd, alive, self_funded_pct, frontier_pct, leaderboard, updated_at`) unchanged in name,
  and each `leaderboard` element SHALL carry the live row fields plus, when present on the row,
  `revenue_today_usd, revenue_by_source, tags, log_feed`, and a derived `stale` boolean.
- **R2 (rank = EARNINGS, per north star)** `leaderboard` SHALL be sorted by `revenue_mo_usd`
  descending (what the agent actually earned), ties broken by `net_worth_usd` descending. (Changes the
  current net_worth sort; `aggregate.test.js` updated accordingly.) Rationale: design §1 "ranked by
  what each agent actually earned — earns the most wins"; net worth is dominated by seeded capital.
- **R3 (no omission — schema requires numbers)** Money fields (`net_worth_usd`, `revenue_mo_usd`)
  remain required numbers (schema unchanged). No field is omitted, so the existing reducers and the
  sort never see `undefined`/`NaN`.
- **R4 (INV-NOFAKE, now provable via on-chain read)** Because `id` IS the agent's EVM wallet, a
  `enrichOnChain(rows)` step SHALL set each row's `net_worth_usd` to the **on-chain USDC+native
  balance of `id`**, overwriting any self-reported value, and tag the source `net_worth_src:"chain"`.
  WHERE the chain read fails, the row SHALL be marked `net_worth_src:"unverified"` and excluded from
  ranking (shown but unranked). Proof: a row claiming inflated net worth is corrected to the chain
  value; an unreadable wallet is flagged, never silently trusted.
- **R5 (status = live enum; staleness is a DERIVED display flag, never a status mutation)** The system
  SHALL NOT change `status` (stays `alive|critical|dead`). WHEN `now - ts` exceeds the staleness
  window (default 600s), the derived `stale:true` SHALL be set on the leaderboard element; `dead`/
  `critical` are still surfaced (not hidden).
- **R6 (UI leaderboard)** `EmpireDashboard.tsx` SHALL render one row per `leaderboard` element in
  order, showing rank, `id` (short + explorer link), `model_live`+`model_tier`, `net_worth_usd`,
  `revenue_mo_usd`, `revenue_today_usd` (or `—` if absent), `status`, and a `stale` indicator;
  `useDashboard.ts` `DashboardData` type SHALL gain an optional `leaderboard?` array (no faking of
  absent fields, §v2.7/§v2.10).
- **R7 (filter, tag-based — unambiguous)** The UI SHALL offer `All | #agent-hackathon | Ours`.
  `#agent-hackathon` shows elements whose `tags` include `"agent-hackathon"`. `Ours` shows elements
  whose `id` is in the known-canonical allowlist (`OUR_INSTANCE_IDS`) AND lacks `agent-hackathon`.
  `All` shows everything. (Filter is defined on `tags`/`id`, never on `funding_type`.)
- **R8** WHERE `revenue_today_usd`/`revenue_by_source` is absent on an element, the UI SHALL render
  `—`, never `$0`. WHEN a filtered set is empty, an explicit empty-state node SHALL render.
- **R9 (back-compat)** Every row currently accepted by `telemetry-schema.validate` SHALL still be
  accepted after the additive fields are introduced.

## 1b. Verification architecture (proves each requirement)

| Req | Test kind | Concrete proof |
|---|---|---|
| R1 | unit (aggregate) | existing-keys snapshot unchanged; extra fields passthrough when present |
| R2 | unit | unsorted fixture → order strictly by `revenue_mo_usd` desc, `net_worth_usd` tiebreak; update `aggregate.test.js` |
| R3 | unit | reducers/sort over fixture with all money present → no `NaN` |
| R4 | unit (enrichOnChain, mocked RPC) | inflated self-report → overwritten to mocked chain balance + `src:"chain"`; RPC error → `src:"unverified"` + excluded from rank |
| R5 | unit | `ts` older than window → `stale:true`; `status` unchanged; `dead` still present |
| R6 | component + **browser E2E** | render fixture `leaderboard` → rows in order w/ fields; CloakBrowser full-page screenshot of live `/dashboard` |
| R7 | component + **browser E2E** | click `#agent-hackathon` → only tagged rows; `Ours` → only allowlisted, untagged |
| R8 | component | element w/ absent today → DOM `—` (assert not `$0`); empty filter → empty-state node |
| R9 | unit | the existing `telemetry-schema` fixtures still `ok:true` after extension |

## Invariants
- **INV-NOFAKE**: the ranked money (`net_worth_usd`) is the on-chain balance of `id` (R4), never a
  trusted self-report; unverifiable wallets are flagged + unranked. Earnings rank = `revenue_mo_usd`.
- **INV-OWN-STATE / write-auth**: an agent may only write its own row; heartbeats are verified by the
  canonical signed message in `telemetry-verify.js` (the signer must equal `id`).
- **INV-BACKCOMPAT (R9)**: additive-only schema; no currently-valid row is rejected.

## Definition of done (this slice)
- R1–R9 tests green (unit + component).
- Fresh-context adversary PASS (disk-only) on spec AND impl.
- **My own CloakBrowser browser E2E** on the rendered `/dashboard` leaderboard: ranked by earnings,
  `#agent-hackathon` filter works, money is on-chain (or flagged), absent fields show `—` not `$0`.
  Full-page screenshot captured.
