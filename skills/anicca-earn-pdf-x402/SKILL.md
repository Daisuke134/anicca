---
name: anicca-earn-pdf-x402
description: Anicca が自前 PDF を 生成 → Cloudflare R2 host → x402 paywall ($5-29) で 販売。 Claude API で markdown 生成 → pandoc で PDF 変換 → anicca-earn-x402 の /pdf/<id> route で gate。 KYC ZERO、 install user 不要。
metadata:
  type: earn
  spec: ANICCA_TRUE_AUTONOMY_SPEC.md §2A PDF gated by x402
  parallel_safe: true
  expected_revenue: $5-500/mo (depends on title 数)
  requires:
    bins: [pandoc, wrangler, curl, jq, node]
    skills: [anicca-wallet, anicca-earn-x402, anicca-cloudflare-account]
    env_optional: [ANTHROPIC_API_KEY, CLOUDFLARE_R2_BUCKET]
---

# anicca-earn-pdf-x402

## なぜ
PDF = Felix / Kelly Claude モデル の 「digital product」 を Anicca に コピー した最小単位。 Stripe / Gumroad / Etsy は KYC 必須 = NG。 x402 paywall + Cloudflare R2 は 完全 automation-only、 USDC 直接 受領、 anicca-earn-x402 の route hook で gate。

Claude API で 書き、 pandoc で PDF 化、 R2 に upload、 x402 route 登録 = end-to-end 自律。 Title は heartbeat が pick (trend / niche / Anicca own voice)。

## Flow
```
1. scripts/check.sh           → state/pdfs/<id>.json 既存?
2. scripts/draft.sh <topic>   → Claude API で 章立て markdown 生成
                                → pdfs/<id>.md
3. scripts/build-pdf.sh <id>  → pandoc で pdfs/<id>.pdf 出力
                                → cover image: DALL-E or template
4. scripts/upload.sh <id>     → wrangler r2 object put → R2 URL 取得
5. scripts/list.sh <id> <price>
                              → anicca-earn-x402 の routes に /pdf/<id> 登録
                              → price (=$5-29) は topic depth で 決定
6. scripts/promote.sh <id>    → Farcaster / X に link post (anicca-earn-farcaster 連携)
7. scripts/poll-sales.sh      → x402-revenue.jsonl の /pdf/* 集計
```

## Output (pdfs/<id>.json)
```json
{
  "id": "deep-research-on-x402-2026",
  "title": "x402 Field Manual — How Agents Earn USDC in 2026",
  "price_usdc": 19,
  "r2_url": "https://r2.anicca.workers.dev/pdfs/...",
  "x402_route": "/pdf/deep-research-on-x402-2026",
  "published_at": "2026-06-01T...",
  "pages": 42,
  "sales_count": 0,
  "revenue_usdc": 0
}
```

## Verify (HARD RULE #8)
- `curl https://anicca.workers.dev/pdf/<id>` → 402 returns (= paywall live)
- `curl -X POST` with x402 payment header → R2 URL or stream の PDF 返却
- pandoc 出力 PDF を `file <id>.pdf` で MIME 確認 + pdftotext で text 抽出可
- 第 1 sale 後 chain explorer で Anicca wallet inbound 確認

## Verify (HARD RULE #18 no-human-in-loop)
- never ask user "どの title を 書くか?" — heartbeat が 自前 で topic pick
- never ask "値段 いくら?" — depth / page count で auto pricing
- never request preview approval — ship 後 sales 0 なら retire (自動)
- promo 投稿の 文面 確認 求めない
