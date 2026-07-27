# 13c Polymarket Cycle Ledger Design

## Goal

Close 13c-PM with one real, completed Polymarket cycle in Life Manager's existing
`lm_agent_earnings` ledger. The record must preserve deployed capital, recovered
capital, fees, and realized P&L without calling returned principal revenue, and the
existing monthly report must render the live six-decimal pUSD balance without
rounding it to cents.

## Ground truth

The proof cycle is the completed market
`0x5ecd0d050ea3e753b787ad8ef3b023448b78d232ebe28b24b3d18bf878fb8b5d`:

| Fact | Observed value | Evidence |
|---|---:|---|
| wallet | `0x904B50d2e214Da947d83D6a2D32c4E3Ffc17Eb74` | Polymarket public Activity API |
| deployed | `3,150,000` micro-USD (`$3.15`) | BUY activity, 7 shares at `$0.45` |
| recovered | `0` micro-USD | REDEEM activity |
| fee | `0` micro-USD | authenticated CLOB account trade, `fee_rate_bps=0` |
| realized P&L | `-3,150,000` micro-USD (`-$3.15`) | `recovered - deployed - fee` |
| trade tx | `0xe6bbfb7d610a774f4548af9393930e99039f0a33f6aaeae34d7fe1f240321659` | public Activity API |
| redeem tx | `0xdfaf37b33da21da10ba0398ccbe4e853d8111e2867606a4c81b85acc454086ef` | public Activity API + Polygon receipt `status=0x1` |
| post-cycle balance | `4,422,182` pUSD atomic units (`$4.422182`) | live pUSD `balanceOf` |

Polymarket's Position schema keeps `initialValue`, `currentValue`, `cashPnl`,
and `realizedPnl` as separate fields.  
Source: [Polymarket — Get current positions for a user](https://docs.polymarket.com/api-reference/core/get-current-positions-for-a-user)  
Core quote: “`initialValue` — The initial value of the position” and
“`cashPnl` — Profit and loss in cash terms.”

The authenticated trade schema exposes both the fee rate and transaction hash.  
Source: [Polymarket — GET /trades](https://docs.polymarket.com/developers/CLOB/trades/trades)  
Core quote: “`fee_rate_bps` — the fees paid for the taker order expressed in basic
points” and “`transaction_hash` — hash of the transaction where the trade was
executed.”

The official order flow requires the fee rate to be part of the signed order and
states that official clients handle it automatically.  
Source: [Polymarket — Create Order with Fee Rate](https://docs.polymarket.com/developers/market-makers/maker-rebates-program)  
Core quote: “Always fetch feeRateBps dynamically from the fee-rate endpoint” and
“For official CLOB clients (TypeScript, Python, Rust), fee handling is automatic.”

## Approaches considered

### A. Record only the signed net

One `financial_realized_loss=$3.15` row is arithmetically enough for the monthly
total, but without the four cycle components it cannot prove that returned
principal was excluded. Rejected.

### B. Record deployed and recovered as ordinary income/expense rows

This makes the ledger easy to inspect but incorrectly raises gross revenue when
principal returns. It violates AE-AC2. Rejected.

### C. Derive report rows from one immutable cycle envelope

Recommended. Keep the exact four components in every emitted row's `meta`, derive
only the economic delta into the existing kind vocabulary, and use deterministic
entry keys:

- `recovered > deployed`: record `recovered - deployed` as
  `financial_external_income`;
- `deployed > recovered`: record `deployed - recovered` as
  `financial_realized_loss`;
- record non-zero fee independently as `financial_fee`;
- never record deployed or recovered principal by itself as revenue;
- require `realized_pnl = recovered - deployed - fee`;
- reject fractional-cent P&L instead of rounding it into the current cent ledger.

This preserves the existing append-only table and monthly arithmetic. A retry can
repair a partial multi-row write because each component has a deterministic unique
key.

## Components

### `lib/polymarket-cycle.js`

Pure validation and mapping plus one runtime function:

```js
cycleLedgerEntries(cycle) -> frozen earning entry[]
recordPolymarketCycle(cycle, opts) -> { ok, cycle_id, entries, writes }
```

All monetary inputs are unsigned decimal strings in micro-USD. JavaScript
floating-point values are refused. `realized_pnl_microusd` is a signed decimal
string and must exactly match the formula. The cycle envelope and evidence hashes
are copied into `meta`; secrets are rejected by the existing ledger normalizer.

### Exact balance rendering

`rollUpMonth` continues to accept `balanceMinor` for existing callers. It also
accepts `balanceAtomic + balanceDecimals` as an alternative. The summary retains
the atomic string and the formatter prints all six pUSD decimals. Supplying both,
neither, an invalid decimal count, or a negative/non-integer atomic balance fails
closed.

`generateMonthlyReport` gains the parallel
`readBalanceAtomic + balanceDecimals` request path. Existing Base-USDC callers and
copy remain unchanged. The rollup also carries an explicit explorer hostname:
Base callers default to `basescan.org`, while this Polygon cycle renders
`polygonscan.com`; a chain-correct balance with a wrong explorer is not a
verifiable report.

### Production command

`scripts/record-polymarket-cycle.js` reads one committed public evidence JSON,
records it through `recordPolymarketCycle`, independently reads the live Polygon
pUSD balance, then generates the existing §9.11 monthly report for the same PM
wallet. It never reads or transports a private key.

## Error handling

| Failure | Behavior |
|---|---|
| receipt not `0x1` | no database request |
| malformed wallet/hash/condition | no database request |
| formula mismatch | no database request |
| fractional-cent derived P&L | no database request; no rounding |
| Supabase failure | surface the HTTP status |
| duplicate entry key | treat as idempotent success |
| Polygon balance unavailable | row remains recorded; report generation fails visibly |
| balance has sub-cent remainder | render all six decimals |

## Verification

1. RED/GREEN unit tests for positive, negative, fee, formula mismatch, fractional
   cent refusal, idempotent runtime writes, and exact atomic balance rendering.
2. Record the proof cycle into production `lm_agent_earnings`.
3. Read the row back and verify its immutable metadata contains all four exact
   components and both transaction hashes.
4. Independently re-read the Polygon redeem receipt and pUSD balance.
5. Generate the monthly report from the production row; expected loss is
   `-$3.15` and the balance line is `$4.422182`.

## Explicit limits

- This proves one real CAPITAL cycle is accountably connected to Life Manager.
- It does not make the PM wallet a tenant's canonical Base wallet.
- It does not prove external SELL/WORK revenue; verified external revenue remains
  `$0.00`.
- It does not unlock 13d-b, because the Life Manager tenant wallet remains unfunded.
- It does not change trading strategy, risk caps, or launchd cadence.
