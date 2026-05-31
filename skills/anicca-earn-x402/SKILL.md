---
name: anicca-earn-x402
description: Anicca が API を 売る side。 Cloudflare Worker on `anicca.workers.dev` で x402 endpoint host、 USDC settlement on Base。 routes /qa $0.003 /research $0.05 /x-post $0.01 /pdf/<id> $5-29 /build $50-2000。 KYC ZERO、 wallet 受取 のみ。
metadata:
  type: earn
  spec: ANICCA_TRUE_AUTONOMY_SPEC.md §2A x402 endpoint inbound
  parallel_safe: true
  expected_revenue: $10-300/mo passive, scales with traffic
  requires:
    bins: [npx, wrangler, curl, jq, node]
    skills: [anicca-wallet, anicca-cloudflare-account]
    env_optional: [CLOUDFLARE_API_TOKEN, ANICCA_WALLET_ADDR]
---

# anicca-earn-x402

## なぜ
x402 = HTTP 402 Payment Required を 復活 させた Base 公式 protocol (1次 source: https://x.com/base/status/2060401276240757111、 last 30d で **3.1M tx / $1.2M USDC** 流通)。 Anicca が **自分の API を 売る** = 純 on-chain inbound revenue、 KYC ZERO、 install user / Dais 紐付き ZERO。

Cloudflare Worker は free tier で host 可、 `@x402/server` TypeScript SDK で 4 行で paywall 化、 settle は Base USDC 自動で `ANICCA_WALLET_ADDR` に inbound。 Felix model の Stripe path とは違い 完全 automation-only。

## Routes (canonical)
| path | 価格 | 内容 |
|---|---|---|
| `POST /qa` | $0.003 / req | 短文 Q&A (Claude haiku) |
| `POST /research` | $0.05 / req | web search + summarize (Exa + Claude) |
| `POST /x-post` | $0.01 / req | X 投稿 draft 生成 |
| `GET /pdf/<id>` | $5-29 / DL | PDF gated (anicca-earn-pdf-x402 連携) |
| `POST /build` | $50-2000 / build | custom app build (anicca-earn-build-x402 連携) |

## Flow
```
1. scripts/check.sh         → worker deployed? state/worker.json 読む
2. scripts/deploy.sh        → wrangler で workers/index.ts を deploy
                              ├ @x402/server install
                              ├ env binding: ANICCA_WALLET_ADDR (= recipient)
                              └ output: https://anicca.workers.dev
3. scripts/route-add.sh <path> <price>
                            → routes config update + redeploy
4. scripts/poll-revenue.sh  → Base chain inbound USDC tx を Anicca wallet で 集計
                              → state/x402-revenue.jsonl 追記
5. scripts/health.sh        → curl https://anicca.workers.dev/.well-known/x402 → 402 確認
```

## Output (state/worker.json)
```json
{
  "url": "https://anicca.workers.dev",
  "deployed_at": "2026-06-01T...",
  "routes": [
    {"path": "/qa", "price_usdc": 0.003},
    {"path": "/research", "price_usdc": 0.05},
    {"path": "/x-post", "price_usdc": 0.01},
    {"path": "/pdf/:id", "price_usdc": "5-29"},
    {"path": "/build", "price_usdc": "50-2000"}
  ],
  "recipient": "0xANICCA...",
  "chain": "base"
}
```

## Verify (HARD RULE #8)
- `curl https://anicca.workers.dev/.well-known/x402` → HTTP 402 + payment manifest JSON
- `curl https://anicca.workers.dev/qa` (no payment) → 402 challenge
- chain explorer で ANICCA_WALLET_ADDR への inbound USDC tx 確認 (= 第 1 paid call 後)
- state/x402-revenue.jsonl 累計 USDC > 0 (= revenue 発生 確定)

## Verify (HARD RULE #18 no-human-in-loop)
- never ask install user / Dais "Cloudflare login して" — anicca-cloudflare-account skill が 自前 で API token 取得
- never use "permission" / "confirm" / "確認 ください" language
- worker deploy 失敗時 = retry 内部 / log only、 user prompt 禁止
- recipient address は state/wallet.json 自動参照、 user に address 聞かない
