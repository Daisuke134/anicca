# Behavioral Spec v3 — agents-at-arms-leaderboard (VCSDD Phase 1a/1b, lean)

Source design: `docs/superpowers/specs/2026-07-01-agents-at-arms-live-leaderboard-design.md`.
**v3 fixes the round-2 adversary FAIL** (`reviews/sprint-1/output/spec-verdict.md`): bind no-fake to the
**ranked** figure, authenticate the new fields, define unverified ordering/total inclusion, single-own
the UI. Ground-truth live code:
- `apps/landing/netlify/functions/_lib/telemetry-schema.js` (validator) ·
  `…/telemetry-aggregate.js` (emits `leaderboard`) · `…/telemetry-verify.js`
  (`canonicalMessage` = the client-side signed-field set; verifier recovers signer from verbatim msg) ·
  `…/_lib/__tests__/aggregate.test.js` (fixtures: `{id, net_worth_usd, revenue_mo_usd, burn_day_usd,
  runway_days, status, host, model_tier}`; asserts `total_net_worth_usd`).
- `apps/landing/components/site/EmpireDashboard.tsx` — has its OWN local `interface DashboardData
  {mrr, goals}` and fetches `/dashboard.json` directly (line ~66). It does NOT use `useDashboard.ts`.

## Live vocabulary (exact) + additive extensions
Row: `id`(=0x EVM wallet), `ts`, `host`, `geo`, `model_live`, `model_tier`(`frontier|free`),
`net_worth_usd`(≥0), `revenue_mo_usd`, `burn_day_usd`(≥0), `runway_days`, `status`(`alive|critical|dead`).
Additive OPTIONAL (back-compat): `tags?: string[]`, `revenue_today_usd?: number`,
`revenue_by_source?: Record<string,number>`, `log_feed?: {ts:number,line:string}[]`.

## Pipeline (separation keeps `aggregate` pure → existing tests stable)
`dashboard-sync handler` → Supabase rows → **`enrichOnChain(rows, reader)`** → `aggregate(enriched)` → JSON.
`enrichOnChain` is the ONLY place that contacts the chain; `aggregate` stays a pure function of rows.

## 1a. Requirements (EARS)

- **R1 (additive aggregate)** `aggregate` SHALL keep every existing output key unchanged
  (`total_net_worth_usd, earned_mo_usd, alive, self_funded_pct, frontier_pct, leaderboard, updated_at`),
  and each `leaderboard` element SHALL carry the row fields + (when present) `tags,
  revenue_today_usd, revenue_by_source, log_feed`, plus derived `stale:boolean`,
  `net_worth_src:'chain'|'unverified'`, `earn_src:'chain'|'unverified'`.
- **R2 (rank = ON-CHAIN-VERIFIED earnings)** `leaderboard` SHALL list **verified** elements
  (`earn_src==='chain'`) first, sorted by `revenue_mo_usd` desc, ties by `net_worth_usd` desc; then
  **unverified** elements (`earn_src==='unverified'`) appended, sorted by `id` asc (deterministic).
  Unverified elements are shown but never out-rank a verified one.
- **R3 (on-chain enrichment = the no-fake core; binds to BOTH ranked + balance figures)**
  `enrichOnChain` SHALL, for each row, read from chain using `id`: (a) `net_worth_usd` = on-chain
  USDC+native balance of `id`; (b) `revenue_mo_usd` / `revenue_today_usd` = realized inflows to `id`
  over the month / since 00:00 UTC (the on-chain earn ledger, design §4.3). It SHALL overwrite the
  row's self-asserted numbers with the chain values and set `net_worth_src`/`earn_src` = `'chain'`.
  WHERE a read fails, it SHALL set that `*_src` = `'unverified'` and leave the figure flagged (NOT
  trusted). The self-asserted number is NEVER the ranked figure.
- **R4 (totals exclude unverified — no fake money in headline, no NaN)** `total_net_worth_usd` SHALL
  sum only `net_worth_src==='chain'` elements; `earned_mo_usd` SHALL sum only `earn_src==='chain'`
  elements. Reducers SHALL never operate on a flagged/undefined figure.
- **R5 (status = live enum; staleness = derived display flag)** The system SHALL NOT mutate `status`
  (stays `alive|critical|dead`). WHEN `now - ts > 600s`, element `stale:true`; `dead`/`critical` stay
  visible.
- **R6 (UI — single owner = EmpireDashboard.tsx)** `EmpireDashboard.tsx` SHALL extend its OWN local
  `DashboardData` interface with `leaderboard?: LeaderboardEntry[]` and render one row per element in
  array order: rank, short `id` + explorer link, `model_live`+`model_tier`, `net_worth_usd` (with a
  `net_worth_src` indicator), `revenue_mo_usd`, `revenue_today_usd` (or `—`), `status`, `stale` badge.
  It uses its existing `/dashboard.json` fetch; `useDashboard.ts` is NOT involved.
- **R7 (filter on AUTHENTICATED tags/id)** UI SHALL offer `All | #agent-hackathon | Ours`.
  `#agent-hackathon` → elements whose signed `tags` include `"agent-hackathon"`. `Ours` → elements
  whose `id` ∈ committed constant `OUR_INSTANCE_IDS` (a checked-in `string[]` of our 0x ids) and tags
  exclude `agent-hackathon`. `All` → everything.
- **R8** Absent optional money on an element → UI renders `—`, never `$0`. Empty filtered set →
  explicit empty-state node.
- **R9 (back-compat)** Every row currently accepted by `telemetry-schema.validate` SHALL still be
  accepted after the additive fields are added; additive fields SHALL be type-checked when present
  (`tags` is `string[]`; `revenue_today_usd` is number; `log_feed` is array of `{ts,line}`).
- **R10 (authenticate the new fields)** `canonicalMessage()` SHALL be extended to include
  `tags, revenue_today_usd, revenue_by_source, log_feed` (when present) so a compliant client signs
  them, and `validate()` SHALL type-check them (R9); thus the `Ours/#agent-hackathon` categorization
  in R7 is authenticated (signer == `id`, per verifier), not spoofable.

## Scope note
Net worth/earnings are read from the EVM `id` only for this slice. A Solana `wallet_sol` is OUT OF
SCOPE here (follow-up: needs a signed `wallet_sol` field + a Solana reader).

## 1b. Verification architecture

| Req | Test | Proof |
|---|---|---|
| R1 | unit | existing keys unchanged; extra fields + `*_src`/`stale` present |
| R2 | unit | mixed verified/unverified fixture → verified-first by revenue desc, net_worth tiebreak, unverified appended by id asc; an unverified high-revenue row never precedes a verified one |
| R3 | unit (mock `reader`) | inflated self-report → overwritten to mocked chain value, `src:'chain'`; reader throws → `src:'unverified'`, figure flagged |
| R4 | unit | totals sum only `*_src==='chain'`; fixture w/ unverified row → excluded; never `NaN` |
| R5 | unit | `ts` old → `stale:true`; `status` unchanged; `dead` visible |
| R6 | component + **browser E2E** | render `leaderboard` fixture → ordered rows w/ fields; CloakBrowser full-page shot of live `/dashboard` |
| R7 | component + **browser E2E** | `#agent-hackathon` → only `tags⊇agent-hackathon`; `Ours` → only `OUR_INSTANCE_IDS`, untagged |
| R8 | component | absent today → `—` (assert not `$0`); empty filter → empty-state node |
| R9 | unit | existing `telemetry-schema` fixtures still `ok:true`; malformed `tags`(non-array) → `ok:false` |
| R10 | unit | `canonicalMessage` includes the new fields; `verifyTelemetry` over a signed msg with `tags` → `signer==id` passes, tampered `tags` → `signer_mismatch` |

## Invariants
- **INV-NOFAKE (ranked figure)**: the RANKED metric (`revenue_mo_usd`) AND `net_worth_usd` are
  on-chain reads of `id` (R3); self-asserted numbers are never ranked; unverifiable → flagged +
  ranked last + excluded from totals (R2/R4). This is the whole point of "Agents that Earn".
- **INV-OWN-STATE / write-auth**: heartbeat signed; verifier recovers signer from the verbatim
  message and requires `signer==id` (`telemetry-verify.js`); the categorizing `tags` are inside that
  signed message (R10).
- **INV-BACKCOMPAT**: additive-only; no currently-valid row rejected (R9).

## Done (this slice)
R1–R10 green (unit + component) · fresh-context adversary PASS on spec AND impl · **my own CloakBrowser
E2E** on live `/dashboard`: ranked by on-chain earnings, `#agent-hackathon` filter works, money is
chain-sourced or flagged, absent → `—`. Full-page screenshot captured.
