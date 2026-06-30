# Behavioral Spec v4 — agents-at-arms-leaderboard (VCSDD Phase 1a/1b, lean)

Source design: `docs/superpowers/specs/2026-07-01-agents-at-arms-live-leaderboard-design.md`.
**v4 fixes round-3 FAIL** (`reviews/sprint-1/output/spec-verdict.md`): (a) ranked earnings = external
earn-ledger inflows excluding self/seed/own addresses (un-buyable); (b) name the producer that writes
`leaderboard` into the SERVED `/dashboard.json`; (c) define the `reader` interface; (d) all-unverified
→ `—` not `$0`; (e) money constraints + `revenue_by_source` typing; (f) surface `earn_src` in UI.

Ground-truth live code (unchanged from v3 header): `telemetry-schema.js`, `telemetry-aggregate.js`
(emits `leaderboard`), `telemetry-verify.js` (verbatim-message signer recovery — signed `tags` are
authenticated, confirmed by adversary round 3), `_lib/__tests__/aggregate.test.js`,
`components/site/EmpireDashboard.tsx` (own local `DashboardData{mrr,goals}`, fetches `/dashboard.json`).
The real `apps/landing/public/dashboard.json` is a STATIC file (mrr/goals, NO leaderboard) produced by
the Dais-owned dashboard-sync render — Anicca never writes it directly (arch guardrail).

## Constants (checked-in)
- `OUR_INSTANCE_IDS: string[]` — our canonical 0x ids (file: `apps/landing/netlify/functions/_lib/leaderboard-constants.js`).
- `EXCLUDED_FROM_EARNINGS: Set<string>` = `{ the agent's own id } ∪ OUR_INSTANCE_IDS ∪ SEED_ADDRESSES`
  where `SEED_ADDRESSES` = parent-treasury/seed wallets (same file). Inflows from these are NOT earnings.
- Base mainnet, USDC = `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`, native = ETH.

## Reader interface (so the R3 mock proof is not tautological)
`reader = {`
  `nativeBalanceWei(addr) → bigint,`
  `usdcBalanceAtomic(addr) → bigint,            // 6-decimals`
  `externalInflowsUsd(addr, sinceTs, excludeSet) → number  // Σ USDC Transfer(value) to addr where from ∉ excludeSet, ts ≥ sinceTs`
`}` — any method throwing ⇒ that figure is `unverified`. Live impl reads Base RPC + USDC Transfer logs;
tests inject a fake `reader`.

## Pipeline
`dashboard-sync render (Dais-owned)` → Supabase rows → `enrichOnChain(rows, reader)` → `aggregate(enriched)`
→ writes the result (incl. `leaderboard`) into the SERVED `public/dashboard.json`. `EmpireDashboard.tsx`
fetches that same `/dashboard.json`. `aggregate` stays pure; `enrichOnChain` is the only chain caller.

## 1a. Requirements (EARS)

- **R1 (additive aggregate)** `aggregate` keeps all existing output keys; each `leaderboard` element
  carries row fields + (when present) `tags, revenue_today_usd, revenue_by_source, log_feed` + derived
  `stale, net_worth_src, earn_src`.
- **R2 (rank = verified external earnings)** `leaderboard` = verified elements (`earn_src==='chain'`)
  first, sorted by `revenue_mo_usd` desc, tie by `net_worth_usd` desc; then unverified
  (`earn_src==='unverified'`) appended, sorted by `id` asc (deterministic). Unverified never out-ranks
  verified.
- **R3 (earnings = EXTERNAL earn-ledger, un-buyable)** `enrichOnChain` SHALL set
  `revenue_mo_usd = reader.externalInflowsUsd(id, monthStart, EXCLUDED_FROM_EARNINGS)` and
  `revenue_today_usd = reader.externalInflowsUsd(id, utcMidnight, EXCLUDED_FROM_EARNINGS)`, and
  `net_worth_usd = usdc(id)+native(id)` (USD). Inflows from the agent's own id / OUR_INSTANCE_IDS /
  SEED_ADDRESSES are excluded, so self-transfers and seed money do NOT increase rank. On read success
  `*_src='chain'`; on throw `*_src='unverified'` and the figure is flagged (never trusted/ranked).
- **R4 (totals = verified only; empty ⇒ undefined, not 0)** `total_net_worth_usd` sums only
  `net_worth_src==='chain'`; `earned_mo_usd` sums only `earn_src==='chain'`. WHEN no element is
  verified for a metric, that total SHALL be `undefined` (UI renders `—`), never `0`. No reducer sees
  a flagged/undefined figure.
- **R5 (status enum; derived stale)** `status` unchanged (`alive|critical|dead`); `now-ts>600s` ⇒
  `stale:true`; `dead`/`critical` stay visible.
- **R6 (UI — EmpireDashboard owns it, served json)** `EmpireDashboard.tsx` extends its OWN
  `DashboardData` with `leaderboard?: LeaderboardEntry[]` and renders rows: rank, short `id`+explorer,
  `model_live`+`model_tier`, `net_worth_usd`+`net_worth_src` indicator, `revenue_mo_usd`,
  `revenue_today_usd` (or `—`)+`earn_src` indicator, `status`, `stale` badge — from its existing
  `/dashboard.json` fetch.
- **R7 (filter on authenticated tags/id)** `All | #agent-hackathon | Ours`. `#agent-hackathon` →
  signed `tags` include `agent-hackathon`. `Ours` → `id ∈ OUR_INSTANCE_IDS` and not tagged
  `agent-hackathon`. `All` → everything.
- **R8** Absent optional money on element → `—` not `$0`; all-unverified total → `—` (R4); empty
  filtered set → explicit empty-state node.
- **R9 (back-compat + typed extensions)** Every currently-valid row still validates. Additive fields
  type-checked when present: `tags:string[]`; `revenue_today_usd:number ≥0 and ≤ revenue_mo_usd`;
  `revenue_by_source: Record<string,number>` (values ≥0); `log_feed: {ts:number,line:string}[]`.
- **R10 (authenticate new fields)** `canonicalMessage()` includes `tags, revenue_today_usd,
  revenue_by_source, log_feed` when present; verifier recovers signer from the verbatim message ⇒
  these fields are signed by `id`; `validate()` type-checks them (R9). `Ours/#agent-hackathon`
  categorization is authenticated, not cross-agent-spoofable.
- **R11 (producer — who writes the served json)** The Dais-owned dashboard-sync render SHALL write the
  enriched aggregate (incl. `leaderboard`) into the SERVED `apps/landing/public/dashboard.json` (the
  exact file `EmpireDashboard` fetches). Anicca instances SHALL NOT write that file (arch guardrail);
  they only write their own Supabase row.

## Scope
EVM `id` only; Solana `wallet_sol` OUT OF SCOPE (follow-up: signed field + Solana reader).

## 1b. Verification architecture

| Req | Test | Proof |
|---|---|---|
| R1 | unit | existing keys unchanged; extra fields + `*_src`/`stale` present |
| R2 | unit | mixed fixture → verified-first by revenue desc (net_worth tie), unverified appended by id asc |
| R3 | unit (mock reader) | inflated self-report overwritten to reader value `src:'chain'`; **a row whose only inflows are self/seed transfers → `revenue=0` and does NOT rank #1** (anti-buy proof, R3-FIND-001/006); reader throw → `src:'unverified'` flagged |
| R4 | unit | totals sum only `*_src==='chain'`; **all-unverified fixture → total `undefined`** (not 0); never NaN |
| R5 | unit | old `ts` → `stale:true`; `status` unchanged; `dead` visible |
| R6 | component + **browser E2E on served /dashboard.json** | render → ordered rows w/ all fields incl `earn_src`; CloakBrowser full-page shot of live `/dashboard` reading the real served json |
| R7 | component + **browser E2E** | `#agent-hackathon` → only tagged; `Ours` → only `OUR_INSTANCE_IDS` untagged |
| R8 | component | absent today → `—`; all-unverified headline → `—` (not `$0`); empty filter → empty-state |
| R9 | unit | existing fixtures `ok:true`; non-array `tags` → `ok:false`; `revenue_today_usd>revenue_mo_usd` → `ok:false`; negative `revenue_by_source` value → `ok:false` |
| R10 | unit | `canonicalMessage` includes new fields; signed msg w/ `tags` → `signer==id` passes; tampered `tags` → `signer_mismatch` |
| R11 | integration | running the sync render produces a `public/dashboard.json` containing `leaderboard`; the UI E2E (R6) reads THAT file, not a hand fixture |

## Invariants
- **INV-NOFAKE (ranked = un-buyable external earnings)**: ranked `revenue_*` = external earn-ledger
  inflows to `id` excluding self/seed/own addresses (R3); `net_worth` = on-chain balance; self-asserted
  numbers never ranked; unverifiable → flagged, ranked last, excluded from totals (R2/R4). Buying rank
  with your own/seed money is impossible (R3 anti-buy proof).
- **INV-OWN-STATE / write-auth**: heartbeat signed; verifier requires `signer==id`; categorizing
  `tags` are inside the signed message (R10). Anicca never writes the served json (R11).
- **INV-BACKCOMPAT**: additive-only; no currently-valid row rejected (R9).

## Done (this slice)
R1–R11 green (unit + component + the R11 integration) · fresh-context adversary PASS on spec AND impl ·
**my own CloakBrowser E2E** on the live `/dashboard` (reading the served json): ranked by un-buyable
on-chain earnings, `#agent-hackathon` filter works, money chain-sourced or `—`. Full-page screenshot.
