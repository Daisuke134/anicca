---
name: anicca-earn-skill-marketplace
description: GitHub anicca-ai org に skill repos 公開、 free clone + x402-gated premium branch ($9-29)。 Claw Mart の OSS 代替、 backend Stripe 不要 = KYC ZERO、 全 USDC settle。
metadata:
  type: earn
  spec: ANICCA_TRUE_AUTONOMY_SPEC.md §2A x402 endpoint inbound (skill products)
  parallel_safe: true
  expected_revenue: $9-29 / sale, $30-500/mo
  requires:
    bins: [git, gh, jq, node]
    skills: [anicca-wallet, anicca-earn-x402, anicca-github-account]
    env_optional: [GITHUB_TOKEN]
---

# anicca-earn-skill-marketplace

## なぜ
Claw Mart (shopclawmart.com) = Stripe backend で Anicca に 不可 (= KYC)。 同 demand を OSS + x402 で 置換: GitHub repo に SKILL.md + free scripts/、 `premium/` branch を x402 gate ($9-29) で 売る。 anicca-earn-x402 の /pdf-pattern を skill bundle に 流用。

free side = 認知 acquisition (clone + star)、 premium side = revenue。 Felix model の "agent-run product" の skill-shaped 版。

## Flow
```
1. scripts/check.sh                → state/products.json 既存 list?
2. scripts/scaffold.sh <skill_name> → gh repo create anicca-ai/<skill_name>
                                     ├ free: SKILL.md + scripts/basic-*
                                     └ premium/: scripts/advanced-* + bundle.zip
3. scripts/publish.sh <skill_name> <price>
                                   → README に "★ Premium: $X via x402"
                                   → anicca-earn-x402 の routes に /skill/<name> 登録
                                     payload = bundle.zip URL (R2 host)
4. scripts/promote.sh <skill_name> → Farcaster + X に link cast
                                   → README badge: "Buy premium $X USDC"
5. scripts/poll-sales.sh           → x402-revenue.jsonl から /skill/* 集計
                                   → GitHub repo star count も track (= demand 指標)
```

## Skill product categories (Anicca own taste で pick)
| category | example | tier |
|---|---|---|
| earn | "x402 endpoint scaffold" | $9 |
| identity | "ENS + agentmail bootstrap" | $19 |
| ops | "Akash auto-redeploy" | $29 |
| meta | "Anicca runtime mini-clone" | $29 |

## Output (state/products.json)
```json
{
  "products": [
    {
      "id": "x402-scaffold",
      "repo": "anicca-ai/x402-scaffold",
      "price_usdc": 9,
      "x402_route": "/skill/x402-scaffold",
      "stars": 0,
      "sales": 0,
      "revenue_usdc": 0
    }
  ]
}
```

## Verify (HARD RULE #8)
- gh repo view anicca-ai/<name> で repo public + README rendered
- `curl https://anicca.workers.dev/skill/<name>` → 402 returns
- x402 paid call で bundle.zip download 可
- state/products.json sales > 0 後 chain explorer inbound 確認

## Verify (HARD RULE #18 no-human-in-loop)
- never ask "どの skill を 商品化 する?" — Anicca own backlog から pick
- never ask "free / premium 線引き OK?" — heuristics: heavy logic = premium
- README / marketing copy も recursive-improver で 自前採点
- pricing も auto tier (上 table)、 user 確認 求めない
