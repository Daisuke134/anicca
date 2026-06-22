# SPEC — #5 dashboard: every AI shows ALL its venues + HL, computed by the SYSTEM (VCSDD, 2026-06-22)

Dais: "nothing hardcoded — hundreds of AIs, each a different mix of revenue streams, different net worth /
monthly / daily / per-source revenue, updated in REAL TIME by the SYSTEM (not the agent)."

## Problem (two readers, each incomplete → the dashboard lies by omission)
- `runtime/monitor/portfolio-realtime.mjs`: reads liquid + aave + **HL** only → MISSES morpho/moonwell/
  beefy/fluid/bluechip (≈$7 of real positions invisible).
- `runtime/dashboard/telemetry-poster.mjs` netWorth(): reads all 7 Base venues → MISSES **HL** ($8.84
  invisible; the user asked "why is HL not in the dashboard").
- Result: net worth + revenue_by_source are wrong/inconsistent between the two.

## Contract (invariants)
1. NET WORTH = liquid + every yield venue with an on-chain position + HL account value. No venue omitted.
2. REVENUE_BY_SOURCE includes HL = its unrealised PnL (Hyperliquid `clearinghouseState` gives it directly,
   no cost-basis needed); shown red when negative; hidden when the stream is unused (value≈0 & cost≈0).
3. NOTHING hardcoded per-agent: every number derives from THAT instance's own wallet via live on-chain
   reads. Per-instance config (wallet, reserve) via env; the value/PnL numbers are read, never seeded.
4. Both readers use ONE shared source of position values so they can NEVER drift again (DRY).
5. Real-time: the loop/cron runs these on a cadence; the dashboard reflects the live chain.

## Plan
- `runtime/lib/hl-state.mjs` (shared): `hlState(wallet)` → `{ accountValue, unrealizedPnl }` from
  `clearinghouseState` (sum assetPositions[].position.unrealizedPnl; accountValue from marginSummary). Pure
  aggregation of the API JSON is unit-tested with a fixture; the fetch is the only effectful edge.
- `skills/earn/lib/revenue.mjs`: add `hl` to the stream handling so revenueBySource surfaces HL unrealised
  PnL as a cell (extend YIELD_VENUES or accept an `unrealised` map). Tests: HL loss shows red, HL hidden
  when flat.
- `telemetry-poster.mjs` netWorth(): add `hl: hlState().accountValue`; pass HL upnl into revenueBySource.
- `portfolio-realtime.mjs`: read the 5 missing Base venues (reuse telemetry's addresses/decimals) so its
  total matches telemetry's net worth.

## RED → GREEN → adversary gate → no-mock E2E
- Unit: hlState aggregation (fixture), revenueBySource with HL (loss/flat/profit).
- E2E: run telemetry-poster once → net_worth includes HL; run portfolio-realtime → total ≈ telemetry net
  worth (both complete); verify against a live `clearinghouseState` + balanceOf consensus.
