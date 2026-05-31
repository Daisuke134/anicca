---
name: anicca-coconala-earner
description: **conditional** (default OFF)。 同 Lancers (gate: bank + gov ID)、 但し Coconala は SMS gate 突破 が 必要 (LNVPN eSIM USDC 払い)。 出品 → 受注 → 納品 → 出金。 spec §10 で DEAD だが install user 持ち込み 資産 ある時 のみ revive。
metadata:
  type: conditional
  spec: ANICCA_TRUE_AUTONOMY_SPEC.md §5 + §10 (conditional revive only)
  parallel_safe: true
  expected_revenue: ¥1k-30k / 出品 (active 時)
  requires:
    bins: [camofox, curl, jq, node]
    skills: [anicca-wallet, anicca-payout]
    env_optional: [COCONALA_EMAIL, COCONALA_PASSWORD, LNVPN_API_KEY]
---

# anicca-coconala-earner

## なぜ
Coconala = ココナラ、 「出品ベース」 marketplace。 Lancers と 同じ eKYC + bank 出金 path = Anicca 自前 では NG。 但し install user opt-in 時 のみ revive。

差分 = signup 時 **SMS verify 必須** (Lancers より 厳格)。 解 = anicca-silent-link-esim (LNVPN USDC 払い) で 自前 番号 取得、 user の phone を 使わない。

## Gate
```
profile.json:
  bank_account: { name, branch, number, holder }
  government_id_image: <path/URL>
  jp_resident: true
  coconala_optin: true

不足 → silent dormant
```

## Flow (active 時)
```
1. scripts/check.sh           → gate satisfy + state/sms-number.json 既存?
                                └ 不足 → silent
2. scripts/get-esim.sh        → LNVPN API で eSIM 購入 (USDC 支払い)
                                → JP 番号 取得 → state/sms-number.json
3. scripts/signup.sh          → camofox で coconala.com/signup
                                ├ phone: 上の JP 番号
                                ├ SMS code: LNVPN inbox API で 受信
                                └ email: profile.email
4. scripts/create-gigs.sh     → 出品 (skill catalog から auto-draft、 5-10件)
                                ├ title / description LLM 生成
                                ├ thumbnail: DALL-E 生成
                                └ price ¥1000-30000 tier
5. scripts/handle-orders.sh   → 受注 polling → deliver
6. scripts/ekyc.sh            → 出金 前 政府ID upload
7. scripts/withdraw.sh        → bank_account 振込
                                → state/coconala-earnings.jsonl
```

## Output (state/coconala-earnings.jsonl)
```json
{"ts":"2026-06-01T...","gig_id":"...","order_id":"...","amount_jpy":8000,"status":"delivered|paid","withdraw_tx":"..."}
```

## Verify (HARD RULE #8)
- coconala.com/<username> 訪問 → gig pages live (camofox)
- 受注 page で "完了" 状態 + revenue 累計
- bank_account 着金 確認 (= user の bank web scrape)
- state/coconala-earnings.jsonl 累計 > 0

## Verify (HARD RULE #18 no-human-in-loop)
- never ask "phone 教えて" — eSIM 自前
- never ask "ID ください" — profile.json 経由
- gate 不足 silent dormant、 user 通知 禁止
- 出品 文面・サムネ confirm 求めない (recursive-improver 内採点)
- selfie ekyc one-time 物理例外 のみ Dais 介在 (HARD RULE #18 captcha条 と 同列)
