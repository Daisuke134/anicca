# Behavioral Spec v5 — agents-at-arms-leaderboard (VCSDD Phase 1a/1b, lean)

Source design: `docs/superpowers/specs/2026-07-01-agents-at-arms-live-leaderboard-design.md`.
**v5 fixes round-4 FAIL**: (1) per-row `excludeSet(row)` (a static set cannot hold an arbitrary
entrant's own id) + HONEST no-fake scope (self/seed excluded = un-pumpable; donations/airdrops counted
as real received money, earn-ledger settlement cross-check = follow-up); (2) dimensioned `net_worth_usd`
(decimal scaling + ETH/USD price); (3) producer invariant R12 — EVERY emitter of `leaderboard`
(incl. the live netlify `dashboard-sync.js`) MUST `enrichOnChain` first; raw self-reported rankings are
never served.

Ground-truth live code: `telemetry-schema.js`, `telemetry-aggregate.js` (emits `leaderboard`),
`telemetry-verify.js` (verbatim-message signer recovery — signed `tags` authenticated, adversary-confirmed),
`_lib/__tests__/{aggregate.test.js,handler-telemetry.test.js}`,
`apps/landing/netlify/functions/dashboard-sync.js` (line 14 returns `aggregate(rows)` of RAW rows —
reconciled by R12), `components/site/EmpireDashboard.tsx` (own `DashboardData{mrr,goals}`, fetches
`/dashboard.json`), `apps/landing/public/dashboard.json` (STATIC, Dais-render-owned, no leaderboard).

## Constants / helpers (NEW file, created in GREEN: `apps/landing/netlify/functions/_lib/leaderboard-constants.js`)
- `OUR_INSTANCE_IDS: string[]` — our canonical 0x ids.
- `SEED_ADDRESSES: string[]` — parent-treasury / seed wallets.
- `excludeSet(row) → Set<string>` = `{ row.id } ∪ OUR_INSTANCE_IDS ∪ SEED_ADDRESSES` (PER ROW — must
  contain the row's own id so self-transfers never count).
- Base mainnet · USDC `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` (6dp) · native ETH (18dp).

## Reader interface (mock-injectable; live = Base RPC + USDC Transfer logs + a price feed)
`reader = {`
  `nativeBalanceWei(addr) → bigint,`
  `usdcBalanceAtomic(addr) → bigint,                       // 6 decimals`
  `ethUsdPrice() → number,                                 // USD per 1 ETH`
  `externalInflowsUsd(addr, sinceTs, excludeSet) → number  // Σ USDC Transfer(value)/1e6 to addr where from ∉ excludeSet, ts ≥ sinceTs`
`}` — any method throwing ⇒ that figure is `unverified`.

## Pipeline (single rule: enrich BEFORE aggregate, everywhere)
`producer` → Supabase rows → `enrichOnChain(rows, reader)` → `aggregate(enriched)` → emit. Two producers
exist and BOTH obey this (R12): the live netlify `dashboard-sync.js` endpoint AND the Dais-owned render
that writes the served `public/dashboard.json`. `aggregate` stays pure; `enrichOnChain` is the only
chain caller.

## 1a. Requirements (EARS)

- **R1 (additive aggregate)** `aggregate` keeps all existing output keys; each `leaderboard` element
  carries row fields + (when present) `tags, revenue_today_usd, revenue_by_source, log_feed` + derived
  `stale, net_worth_src, earn_src`.
- **R2 (rank = verified external earnings)** verified (`earn_src==='chain'`) first by `revenue_mo_usd`
  desc; ties broken by `net_worth_usd` desc WHEN both tied rows are `net_worth_src==='chain'`, else by
  `id` asc (a non-chain net worth is never used to rank); then unverified (`earn_src==='unverified'`)
  appended by `id` asc. Unverified never out-ranks verified.
- **R3 (enrichment — dimensioned + per-row exclude)** `enrichOnChain` SHALL set, per row:
  - `net_worth_usd = usdcBalanceAtomic(id)/1e6 + (nativeBalanceWei(id)/1e18) * ethUsdPrice()` (USD).
  - `revenue_mo_usd = externalInflowsUsd(id, monthStart, excludeSet(row))`,
    `revenue_today_usd = externalInflowsUsd(id, utcMidnight, excludeSet(row))`.
  On success `*_src='chain'` (overwriting any self-asserted value); on any read throw `*_src='unverified'`
  and the figure is flagged (never trusted/ranked).
- **R4 (totals = verified only; empty ⇒ undefined)** `total_net_worth_usd` sums only
  `net_worth_src==='chain'`; `earned_mo_usd` sums only `earn_src==='chain'`; when none verified → that
  total is `undefined` (UI `—`), never `0`; reducers never see a flagged/undefined figure.
- **R5 (status enum; derived stale)** `status` unchanged; `now-ts>600s` ⇒ `stale:true`;
  `dead`/`critical` stay visible.
- **R6 (UI — EmpireDashboard, served json)** `EmpireDashboard.tsx` extends its own `DashboardData` with
  `leaderboard?: LeaderboardEntry[]`; renders rank, short `id`+explorer, `model_live`+`model_tier`,
  `net_worth_usd`+`net_worth_src`, `revenue_mo_usd`, `revenue_today_usd`(or `—`)+`earn_src`, `status`,
  `stale`; from its existing `/dashboard.json` fetch.
- **R7 (filter, authenticated)** `All | #agent-hackathon | Ours`. `#agent-hackathon` → signed `tags`
  include `agent-hackathon`. `Ours` → `id ∈ OUR_INSTANCE_IDS` & not tagged. `All` → everything.
- **R8** absent optional money → `—` not `$0`; all-unverified total → `—`; empty filter → empty-state.
- **R9 (back-compat + typed extensions)** existing rows still validate; additive fields typed when
  present: `tags:string[]`; `revenue_today_usd:number ≥0 and ≤revenue_mo_usd`;
  `revenue_by_source:Record<string,number>` (values ≥0); `log_feed:{ts:number,line:string}[]`.
- **R10 (authenticate new fields)** `canonicalMessage()` includes the additive fields when present;
  verbatim-message verifier ⇒ they are signed by `id`; `validate()` type-checks them (R9). Tag-based
  categorization is not cross-agent-spoofable.
- **R11 (served-json producer)** The Dais-owned dashboard-sync render writes the enriched aggregate
  (incl. `leaderboard`) into the SERVED `apps/landing/public/dashboard.json`. Anicca instances SHALL NOT
  write that file (guardrail); they only write their own Supabase row.
- **R12 (NO raw rankings anywhere)** EVERY producer that emits a `leaderboard` — INCLUDING the live
  netlify `apps/landing/netlify/functions/dashboard-sync.js` — SHALL apply `enrichOnChain` before
  `aggregate`. A `leaderboard` of raw self-reported figures SHALL NOT be served from ANY endpoint.
  (Reconciles `dashboard-sync.js:14`.)

## INV-NOFAKE — HONEST SCOPE (no overclaim)
The ranked `revenue_*` is **on-chain external USDC inflow** to `id` (R3), never a self-asserted number;
`net_worth_usd` is the on-chain balance (R3). `excludeSet(row)` removes the agent's OWN id + SEED +
OUR addresses, so **you cannot pump your rank by moving your own / seed / treasury money in**
(anti-buy proof, 1b). KNOWN v1 LIMITATION (stated, not hidden): a genuine third-party donation/airdrop
to the wallet counts as inflow — it is real money received, but it is not "earned via service". A
follow-up will cross-check each inflow against the agent's earn-ledger settlement tx (design §4.3) to
separate earned-vs-gifted. v5 claims ONLY: self/seed/treasury self-funding cannot buy rank, and the
ranked figure is on-chain, not self-asserted.

## Other invariants
- **INV-OWN-STATE / write-auth**: heartbeat signed; verifier requires `signer==id`; categorizing `tags`
  are inside the signed message (R10). Anicca never writes the served json (R11).
- **INV-ENRICH-EVERYWHERE (R12)**: no endpoint serves a non-enriched leaderboard.
- **INV-BACKCOMPAT (R9)**: additive-only; no currently-valid row rejected.

## Scope: EVM `id` only; Solana `wallet_sol` OUT OF SCOPE (follow-up).

## 1b. Verification architecture

| Req | Test | Proof |
|---|---|---|
| R1 | unit | existing keys unchanged; extra fields + `*_src`/`stale` present |
| R2 | unit | mixed fixture → verified-first by revenue desc (net_worth tie), unverified by id asc |
| R3 | unit (mock reader) | net_worth = usdc/1e6 + eth/1e18*price (dimensioned, exact); **a row whose only inflows are from its OWN id / a SEED address → revenue 0 → NOT rank #1** (per-row excludeSet anti-buy proof); reader throw → `unverified` flagged |
| R4 | unit | totals sum only `*_src==='chain'`; all-unverified → `undefined` (not 0); never NaN |
| R5 | unit | old `ts` → `stale:true`; status unchanged; `dead` visible |
| R6 | component + **browser E2E on served /dashboard.json** | ordered rows w/ all fields incl `earn_src`; CloakBrowser full-page shot of live `/dashboard` |
| R7 | component + **browser E2E** | `#agent-hackathon` → only tagged; `Ours` → only `OUR_INSTANCE_IDS` untagged |
| R8 | component | absent today → `—`; all-unverified headline → `—`; empty filter → empty-state |
| R9 | unit | existing fixtures `ok:true`; non-array `tags`→`ok:false`; `revenue_today>revenue_mo`→`ok:false`; negative `revenue_by_source` value→`ok:false` |
| R10 | unit | `canonicalMessage` includes new fields; signed msg w/ `tags` → `signer==id`; tampered `tags` → `signer_mismatch` |
| R11 | integration | sync render produces `public/dashboard.json` containing `leaderboard`; the R6 E2E reads THAT served file |
| R12 | unit/integration | calling the netlify `dashboard-sync` handler with raw rows + a mock reader → its `leaderboard` reflects ENRICHED figures (self-transfer excluded), i.e. it cannot serve raw self-reported rankings |

## Done (this slice)
R1–R12 green · fresh-context adversary PASS on spec AND impl · **my own CloakBrowser E2E** on live
`/dashboard` (served json): ranked by on-chain external earnings, self/seed money can't buy rank,
`#agent-hackathon` filter works, money chain-sourced or `—`. Full-page screenshot captured.
