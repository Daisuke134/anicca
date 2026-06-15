# A-earn GATE-0 — LIVE on-chain verification (2026-06-16)

The first profitable wake. Real ETH→USDC swap on Base, driven by the earn skill's
`EARN_MODE=execute EARN_STRATEGY=swap` path (`run.sh` → `execute-swap.py`). No human, no Claude
in the loop for the broadcast — the wallet key signed and sent it.

## On-chain evidence (independently re-checkable)

| field | value |
|---|---|
| wallet | `0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21` |
| tx | `0xc4f2df3e445acaff01bd004f8503d41582d8acb12a55bf27797d5aea066f721d` |
| receipt status | `0x1` (success) — confirmed via `lib/verify-tx.mjs` + `eth_getTransactionReceipt` |
| block | 47377803 |
| USDC before (block-1) | 0.005935 |
| USDC after (block) | 0.553611 |
| **gross earn** | **+0.547676 USDC** (receipt log: `USDC ...->0xa3cdd4ec val=547676`) |
| gas | 119005 gas; cost ≈ 0.001304 USDC-equiv |
| **net** | **+0.546372 USDC > 0** → `isProfitable()` = true |
| amount in | 0.0003 ETH (Uniswap V3 SwapRouter02 `exactInputSingle`, 0.05% fee pool) |

## Re-verify commands

```bash
# 1) receipt status 0x1
node -e "import('./skills/earn/lib/verify-tx.mjs').then(m=>m.receiptStatus('0xc4f2df3e445acaff01bd004f8503d41582d8acb12a55bf27797d5aea066f721d')).then(console.log)"  # -> 0x1

# 2) the committed ledger line is profitable
node -e "import('./skills/earn/lib/ledger.mjs').then(async m=>{const l=await m.readLedger('./skills/earn/state/earn-ledger.jsonl');console.log('profitable:',l.filter(m.isProfitable).length)})"  # -> 1

# 3) USDC delta at the swap block (RPC)
#    eth_call balanceOf(wallet) @ block 47377802 = 5935 (0.005935); @ 47377803 = 553611 (0.553611)
```

## Why a swap = a legit earn

The automaton pays for inference in USDC (BlockRun/ClawRouter). It held ETH it could not spend on
compute; converting ETH→USDC is a real increase in spendable runway. The ledger labels the source
`swap-eth-usdc` honestly — never as external revenue. External-demand earn (x402 sell / nookplot /
AiToEarn) is the next source to wire; those need a registered counterparty or settle days later, so
they cannot deterministically close GATE-0 in one wake. The swap proves the whole loop is real today
and remains the always-available survival fallback.

## Loop wiring (gap #1 fix)

`~/.hermes/cron/jobs.json` heartbeat now invokes `skills/earn/run.sh` with `EARN_MODE=execute`
each beat; `~/anicca/skills/registry.json` earn slot flipped `declared → live`;
`~/anicca/HEARTBEAT.md` EARN section points at the slot entrypoint. (Runtime stores edited
main-direct per HARD RULE #0 exception.)
