---
name: anicca-earn-zora
description: DALL-E (or open SD) で 生成 した art を Zora protocol で mint + sell on Base。 $10-500 / mint、 wallet sign のみ、 KYC ZERO。 Anicca own collection (anicca.zora.co) を 育てる。
metadata:
  type: earn
  spec: ANICCA_TRUE_AUTONOMY_SPEC.md §2A Zora NFT mint+sell
  parallel_safe: true
  expected_revenue: $10-500 / mint, $30-1000/mo
  requires:
    bins: [node, curl, jq, ffmpeg]
    skills: [anicca-wallet]
    env_optional: [OPENAI_API_KEY, ZORA_API_KEY]
---

# anicca-earn-zora

## なぜ
Zora = Base 上 の NFT protocol、 mint + sell 全部 wallet sign で 完結 (KYC ZERO)。 Anicca が own art (DALL-E 3 / SDXL で 生成) を 日次 1-3 mint = 「visual diary」 として 育てる。 Felix model の "agent-run product" の Anicca 版 (=純 on-chain version)。

## Flow
```
1. scripts/check.sh              → state/zora-collection.json 既存?
2. scripts/init-collection.sh    → 初回: Zora SDK で create collection
                                   └ output: collection address (= anicca.zora.eth)
3. scripts/draft-art.sh <theme>  → Claude で concept → DALL-E 3 で image
                                   ├ output: art/<id>.png + metadata.json
                                   └ theme は heartbeat が pick (Anicca's day / dharma / x402 culture)
4. scripts/mint.sh <id> <price>  → Zora SDK で mint
                                   ├ price USDC (Base): $10-500
                                   ├ supply: open edition (default) or limited 1/1
                                   └ wallet sign で 完結
5. scripts/promote.sh <id>       → Farcaster + X に link post
                                   → anicca-earn-farcaster 連携
6. scripts/poll-sales.sh         → Zora API で sales 集計
                                   → state/zora-sales.jsonl 追記
```

## Pricing heuristics
| art type | price | edition |
|---|---|---|
| diary daily | $5-10 | open edition |
| concept piece | $30-100 | 100 supply |
| 1/1 milestone | $200-500 | unique |

## Output (state/zora-collection.json)
```json
{
  "collection_address": "0xZORA...",
  "collection_name": "Anicca Diary",
  "chain": "base",
  "created_at": "2026-06-01T...",
  "mints": 0,
  "total_revenue_usdc": 0
}
```

## Verify (HARD RULE #8)
- Zora UI (zora.co/<collection>) で mint visible
- chain explorer で Anicca wallet inbound USDC tx (= sale 後)
- state/zora-sales.jsonl 累計 > 0
- art/<id>.png が 512+ resolution + metadata.json valid OpenSea schema

## Verify (HARD RULE #18 no-human-in-loop)
- never ask "どの絵 を mint しよう?" — Anicca own taste で pick
- never ask "値段 OK?" — heuristics table 自動適用
- never request "preview して" — ship + post 即時
- Dais 紐付き ZERO — collection name に Dais 名前 入れない
