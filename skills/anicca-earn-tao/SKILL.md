---
name: anicca-earn-tao
description: Bittensor TAO mining (subnet validator/miner)、 KYC ZERO。 **conditional**: wallet > $1000 USDC で trigger、 それ未満 dormant。 subnet inference + registration、 $30-200/mo/subnet。
metadata:
  type: conditional
  spec: ANICCA_TRUE_AUTONOMY_SPEC.md §2A Bittensor TAO mining
  parallel_safe: true
  expected_revenue: $30-200/mo/subnet (when active)
  requires:
    bins: [btcli, python3, jq]
    skills: [anicca-wallet]
    env_optional: [TAO_HOTKEY_PASS]
---

# anicca-earn-tao

## なぜ
Bittensor = decentralized AI inference market、 TAO で reward。 Anicca が **subnet miner** または **validator** として inference 提供 → TAO 受領 (USDC で swap 可)。 KYC ZERO、 wallet sign で identity 完結。

但し registration cost が 高い (= recycle TAO, 通常 $500-2000相当)。 wallet < $1000 USDC で 着手 = 即赤字。 **gate logic で dormant** (= heartbeat fire しない) が default。

## Gate (= dormant 解除 条件)
```
state/wallet.json balance_usdc >= 1000  →  active
                          <  1000        →  dormant (silent, no log spam)
```

## Flow (active 時 のみ)
```
1. scripts/check.sh             → wallet balance + state/tao.json status
                                  └ balance < $1000 → exit 0 silent
2. scripts/install-btcli.sh     → 初回 のみ pip install bittensor
3. scripts/keygen.sh            → coldkey + hotkey 生成 (encrypted with TAO_HOTKEY_PASS)
4. scripts/pick-subnet.sh       → 公式 subnet list から ROI top 3 pick
                                  ├ heuristic: emission rate / registration cost
                                  └ output: state/target-subnets.json
5. scripts/register.sh <netuid> → btcli subnet register --netuid <n>
                                  └ TAO burn (= entry cost)
6. scripts/serve.sh <netuid>    → subnet inference daemon launch (axon serve)
                                  ├ model: Claude API / Venice / local
                                  └ runs on Akash via anicca-self-spawn
7. scripts/poll-rewards.sh      → btcli wallet balance を 日次 集計
                                  → state/tao-rewards.jsonl 追記
8. scripts/swap-to-usdc.sh      → TAO → USDC swap via DEX (= Anicca wallet 戻し)
```

## Output (state/tao.json)
```json
{
  "active": false,
  "gate_balance_usdc": 1000,
  "current_balance_usdc": 250,
  "registered_subnets": [],
  "lifetime_tao_earned": 0,
  "lifetime_usdc_swapped": 0
}
```

## Verify (HARD RULE #8)
- wallet < $1000 → state/tao.json `active: false` + no btcli call (= cost zero verify)
- wallet >= $1000 で active → `btcli subnet list` + register tx hash 記録
- subnet axon が answer 返す (= curl test)
- TAO inbound tx を chain (Subtensor) explorer で 確認

## Verify (HARD RULE #18 no-human-in-loop)
- never ask user "TAO mining 始めて いい?" — gate 自動判定
- never ask "どの subnet?" — ROI heuristic で auto
- dormant 中も silent (= "wallet 足り ません" 通知 禁止、 log only)
- registration cost burn も 自動、 confirm 求めない
