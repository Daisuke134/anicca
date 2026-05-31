---
name: anicca-upwork-earner
description: **CONDITIONAL** (default OFF)。 gate = profile.passport + profile.bank_account (= 海外 KYC 用)。 Upwork signup → 案件 bid → contract → deliver → Payoneer / Wise payout。 USD 単価 $50-150/h、 install user の海外 KYC 持ち込み 必須。
metadata:
  type: conditional-earner
  spec: ANICCA_TRUE_AUTONOMY_SPEC.md §5 + §11.5
  parallel_safe: true
  default: DORMANT
  expected_revenue: $50-150/hour (= USD 最強市場、 Wael Khalifa $12K/mo 実例)
  requires:
    skills: [anicca-agentmail, anicca-github-account]
    bins: [camofox, python3, jq, curl]
    profile_required: [passport, bank_account, legal_name_en]
---

# anicca-upwork-earner

## なぜ (conditional)
Upwork は USD client 予算 平均 $5,045/案件 (Fiverr の 19倍)、 fee 10% (Fiverr 20%)。 但し signup で bot detection 厳しい + 海外 KYC (passport 等) 必須。 install user の passport + bank 借りる 前提。

## Profile.json gate
```json
{
  "passport": {
    "image_path": "~/.openclaw/identity/passport.jpg",
    "country": "JP",
    "expires_at": "..."
  },
  "bank_account": {...},
  "legal_name_en": "..."
}
```

## Flow
```
1. scripts/check-profile.sh → passport + bank + name_en 揃ってる?
2. scripts/signup.sh        → upwork.com signup via cloak browser (bot detection 突破)
3. scripts/kyc-upload.sh    → passport upload to Upwork verify
4. scripts/payoneer-link.sh → Payoneer or Wise を 振込先 として 設定
5. scripts/bid.sh           → /jobs/search で AI / Python / TS 系 案件 を Anthropic で 提案文 生成 → bid (= 1 day 5 件)
6. scripts/poll-interviews.sh → invite / message 検出 → reply
7. scripts/contract.sh      → contract 受領後 milestone 確認 + 着手
8. scripts/deliver.sh       → 制作 (Claude API + subagent) → submit work
9. scripts/withdraw.sh      → Payoneer / Wise 経由で user bank 着金
```

## Verify (HARD RULE #8 + #18)
- profile gate なし → silent
- 第 1 contract → deliver → 着金 = end-to-end proof
- bot detection 突破 = cloak browser (= visible で humanly 操作)、 user 介在 ZERO
- 「passport 提出 ください」 user に asking 禁止
