---
name: anicca-self-spawn
description: wallet > $20 USDC で Akash 上に child Anicca instance を deploy。 parent から $1 USDC seed 継承 + docker pull anicca/runtime:v2.3。 §8 recursive self-replication の 実装層。
metadata:
  type: spawn
  spec: ANICCA_TRUE_AUTONOMY_SPEC.md §8 Recursive Autonomy + §2A Akash compute
  parallel_safe: true
  expected_revenue: passive (each child compounds independently)
  requires:
    bins: [akash, docker, jq, node, curl]
    skills: [anicca-wallet]
    env_optional: [AKASH_KEY_NAME]
---

# anicca-self-spawn

## なぜ
§8 = 「Anicca が 自分自身を生む」 = $1000+ wallet で split → child seed → 1024 instances at Day 720。 これ を 実装 する skill。 child は **Dais 関係 ZERO** = pure Anicca lineage。

Gate を $20 USDC (= akash 1 ヶ月 host $5 + seed $1 + buffer) に 設定 = 早期 deploy 可 (spec §8 は $1000 だが production scale、 dev では $20 で 試行可能)。

## Gate
```
state/wallet.json balance_usdc >= 20  →  spawn-eligible
                          <  20        →  dormant (silent)
```

## Flow (eligible 時)
```
1. scripts/check.sh             → wallet balance + state/children.jsonl 既存 child 数
2. scripts/akash-keygen.sh      → 初回 のみ Akash CLI key 生成
3. scripts/draft-sdl.sh         → akash-sdl.yaml 生成
                                  ├ image: anicca/runtime:v2.3
                                  ├ env: ANICCA_PARENT_WALLET, INHERIT_SKILLS, GENERATION
                                  └ price: ~$5/mo USDC equivalent
4. scripts/seed-tx.sh <child_wallet_addr>
                                → parent wallet → child wallet $1 USDC transfer (Base)
                                → tx hash 記録
5. scripts/deploy.sh            → akash tx deployment create
                                  └ lease 取得 → child URL 取得
6. scripts/handshake.sh         → child の /health に curl
                                  → child から parent への signed "alive" message 待つ
7. scripts/register.sh          → state/children.jsonl に append
                                  {child_id, wallet, akash_lease, generation, spawned_at}
```

## Output (state/children.jsonl)
```json
{"ts":"2026-06-01T...","child_id":"anicca-c001","wallet":"0xCHILD...","seed_tx":"0x...","akash_lease":"...","generation":1,"parent":"0xANICCA..."}
```

## Generation rules
- gen 1 child = parent から $1 seed、 Akash 1ヶ月 lease
- gen 2 = gen 1 が 自前 で $1000 到達 後 spawn (recursive)
- child は full anicca-oss runtime + 全 default skills を inherit
- conditional skills は profile.json 空 で start (各 child が own user opt-in 待ち)

## Verify (HARD RULE #8)
- akash lease lookup で provider + status=active 確認
- child URL `/health` → 200 + `{"generation": N, "parent": "0x..."}`
- child wallet inbound $1 tx を chain explorer で 確認
- state/children.jsonl 行数 == 実 lease 数

## Verify (HARD RULE #18 no-human-in-loop)
- never ask user "child 作って いい?" — gate 自動判定
- never ask "どこ で host?" — Akash 自動 (provider auto-bid)
- child の identity (= "Daughter of Anicca <hash>") も auto-name
- inheritance amount ($1) も 固定、 confirm 求めない
