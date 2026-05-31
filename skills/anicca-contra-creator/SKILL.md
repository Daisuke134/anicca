---
name: anicca-contra-creator
description: **CONDITIONAL** (default OFF)。 gate = profile.tax_form (W-8 BEN / W-9) + profile.coinbase_account_link。 Contra Independent signup → digital products / payment links / paid project → Coinbase USDC payout。 commission-free $200M paid out track record。 install user の tax info 借りた conditional creator path。
metadata:
  type: conditional-earner
  spec: ANICCA_TRUE_AUTONOMY_SPEC.md §5 + §11.5
  parallel_safe: true
  default: DORMANT
  expected_revenue: $50-$10k/件 (commission-free, 2% Coinbase payout fee)
  requires:
    skills: [anicca-agentmail]
    bins: [camofox, python3, jq, curl]
    profile_required: [tax_form, coinbase_account_link]
---

# anicca-contra-creator

## なぜ (conditional)
Contra は creator commission-free + Coinbase USDC payout (2% fee, 1% Pro, $0 Max) を 提供 する 数少ない creator platform。 但し Independent signup で W-8/W-9 tax form 必須 + Coinbase account 必要。 install user が 両方 提供 した 場合 のみ Anicca が運用。

## Profile.json gate
```json
{
  "tax_form": {
    "type": "W-8 BEN" | "W-9",
    "form_path": "~/.openclaw/identity/tax-form.pdf",
    "country": "JP" | "US" | etc.
  },
  "coinbase_account_link": {
    "linked_at": "...",
    "user_uuid": "..."
  }
}
```

## Flow
```
1. scripts/check-profile.sh → tax_form + coinbase_account 揃ってるか
2. scripts/signup.sh        → contra.com signup (= agentmail mail, install user 名義)
3. scripts/tax-form-upload.sh → W-8/W-9 を Contra に upload
4. scripts/coinbase-link.sh → Contra ↔ user Coinbase 連携
5. scripts/create-products.sh → digital products (= PDF / AI prompt pack / template) を Anicca 自走 で 作成 + publish
6. scripts/create-payment-links.sh → custom service の payment link 発行
7. scripts/poll-orders.sh   → 注文検出 → digital product delivery (= R2 + signed URL)
8. scripts/payout.sh        → 月末 余剰 を Coinbase USDC で user wallet 着金
```

## Verify (HARD RULE #8 + #18)
- profile gate なし → silent
- digital product 1 件 売り上げ → Coinbase USDC tx hash で proof
- user に「tax form 出して」と聞かない (= profile に既存 のみ trigger)
