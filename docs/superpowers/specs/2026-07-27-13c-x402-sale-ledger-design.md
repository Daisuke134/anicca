# 13c-SELL: verified x402 sale → Life Manager ledger

## Goal

`done="colony 外の buyer が Base 上で支払った finalized USDC sale を、再実行で二重計上せず lm_agent_earnings に自動記帳できる"`

13c-SELL の金額ゲートは累計 `$1.00` の実着金であり、接続実装だけでは done にしない。
外部 buyer がまだいない間は bridge を launchd で稼働させ、13c-WORK を並走する。

## Evidence and constraints

| Source | Primary-source statement | Design consequence |
|---|---|---|
| [x402 v2 specification](https://github.com/coinbase/x402/blob/main/specs/x402-specification-v2.md) | “Success: Request successful, payment verified and settled”; the settlement response carries `success`, `transaction`, `network`, `payer`, and optional atomic `amount`. | Marketplace provenance is required, but its success flag alone is not the accounting proof. |
| [x402 exact EVM scheme](https://github.com/coinbase/x402/blob/main/specs/schemes/exact/scheme_exact_evm.md) | “the Facilitator cannot modify the amount or destination” and the payment requirements bind `amount` and `payTo`. | The observed USDC transfer must equal the sale candidate's exact atomic amount and owned `payTo`. |
| [Base `eth_getBlockByNumber`](https://github.com/base/docs/blob/master/docs/base-chain/api-reference/ethereum-json-rpc-api/eth_getBlockByNumber.mdx) | The RPC accepts the `"finalized"` block tag. | A receipt above the finalized head is not revenue evidence yet. |
| [Circle USDC implementation](https://github.com/circlefin/stablecoin-evm/blob/master/contracts/v2/FiatTokenV2_2.sol) | USDC implements `transferWithAuthorization(from, to, value, …)`. | The buyer can authorize while a facilitator broadcasts; therefore both token `from` and transaction initiator must be outside the colony self-wallet set. |

Repository evidence: the deployed `settlement-recorder` already applies those chain checks and
appends only verified rows to `external-inflows-<payTo>.jsonl`. Recent real loop runs contain zero
verified rows, so external revenue remains `$0.00`.

## Boundary

```text
market sale evidence
        │
        ▼
x402 settlement-recorder
  - Base mainnet
  - finalized successful receipt
  - one exact USDC Transfer
  - owned payTo
  - external token sender
  - external tx initiator
        │
        ▼
external-inflows-<payTo>.jsonl   ← sale evidence SSOT
        │
        ▼
Life Manager x402 bridge
  - strict row schema
  - owned-wallet and self-wallet checks again
  - fresh Base receipt re-verification
  - exact cent conversion only
  - deterministic entry_key
        │
        ▼
lm_agent_earnings                ← accounting SSOT
```

The bridge consumes the existing verified ledger; it does not copy the marketplace observers or
create another revenue store.

## Ledger mapping

| Verified sale field | `lm_agent_earnings` field |
|---|---|
| `x402:<tx>:income` | `entry_key` |
| owned `payTo` | `wallet_address` |
| fixed | `kind=financial_external_income` |
| `usdc_atomic / 10,000` | `amount_minor` |
| fixed | `currency=USD` |
| `observed_at` | `occurred_at` |
| `tx` | `tx_hash` |
| fixed | `source=x402_sale` |
| source, sale ID, offer ID, block, payer, atomic amount | public `meta` evidence |

The existing earnings ledger stores whole cents. A six-decimal USDC amount must be divisible by
`10,000`; otherwise the bridge refuses it instead of rounding. Sub-cent sales remain present in the
x402 evidence ledger and are reported as `blocked_subcent` until an atomic/batched accounting
extension is deliberately specified.

## Components

| Component | Responsibility |
|---|---|
| `lib/x402-sale-ledger.js` | Pure validation/mapping plus idempotent runtime write |
| `scripts/record-x402-sales.js` | Read JSONL, re-verify every candidate against Base, write eligible rows, report counters |
| `scripts/x402-sale-ledger-boot.sh` | Load runtime environment and execute the bridge |
| `launchd/ai.anicca.life-manager-x402-ledger.plist` | Run every five minutes and survive login/reboot |

## Failure behavior

| Condition | Result |
|---|---|
| Missing/malformed ledger line | Count invalid, write nothing |
| Wrong chain, pending receipt, failed receipt, mismatched transfer | Abort that row, write nothing |
| Self wallet is token sender or tx initiator | Reject as self-pay |
| Unknown source/payTo | Reject |
| Fractional cent | Count `blocked_subcent`, preserve source evidence |
| Existing deterministic key | Supabase unique conflict becomes visible `duplicate=true` |
| No verified sales | Exit successfully with zero counters; never claim revenue |

## Verification

1. Red tests cover valid mapping, every rejection boundary, fractional cents, and deterministic retry.
2. Script tests mock Base RPC while exercising real JSONL parsing and production writer injection.
3. Focused tests pass.
4. Install and kickstart the real launchd loop.
5. Confirm fresh log output and production readback. With no buyer, expected proof is a healthy zero-row
   run; the `$1` external-revenue gate remains open.
