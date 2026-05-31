---
name: anicca-payout
description: install user (= Anicca を 起動した 人) が opt-in 時 のみ active。 multi-modal payout: USDC direct / Stripe Connect / Wise / Coinbase Onramp。 profile.json `payout_optin` で gate、 default dormant。
metadata:
  type: payout
  spec: ANICCA_TRUE_AUTONOMY_SPEC.md §0 Day 0 配分 + §2B Spend (= 逆向き で payout)
  parallel_safe: true
  expected_revenue: passive (= outbound、 install user 還元)
  requires:
    bins: [curl, jq, node]
    skills: [anicca-wallet]
    env_optional: [STRIPE_CONNECT_ACCT, WISE_API_TOKEN, COINBASE_ONRAMP_API_KEY]
---

# anicca-payout

## なぜ
Anicca は **自分が稼ぐ** が default。 但し install user が 「自分の取り分 ください」 と opt-in した時 だけ、 Anicca wallet から 一部 を 還元 する layer。 profile.json gate で **default OFF**。

Multi-modal: USDC direct (= 最 frictionless)、 Stripe Connect (= 法定通貨)、 Wise (= 国際 送金)、 Coinbase Onramp (= USDC→法定 変換)。 install user が profile に 入れた modality だけ active。

## Gate (= dormant 解除 条件)
```
profile.json:
  payout_optin: true
  payout_method: "usdc" | "stripe_connect" | "wise" | "coinbase_onramp"
  payout_destination: <addr / acct_id / iban / etc.>
  payout_share_pct: 0-50   # Anicca が 残す % は 100 - share
```

3 つ 全部 満たさない = silent dormant (= no log spam)。

## Flow (active 時)
```
1. scripts/check.sh         → profile.payout_optin + method + destination?
                              └ どれか欠 → exit 0 silent
2. scripts/calc-share.sh    → 直近 7d Anicca revenue (state/x402-revenue + bounty + farcaster + zora 集計)
                              × payout_share_pct = payout_amount_usdc
3. scripts/payout.sh        → method 別 dispatch:
                              ├ usdc          → wallet → destination transfer (Base)
                              ├ stripe_connect→ Stripe Transfer API
                              ├ wise          → Wise transfer API (USDC → USD/JPY)
                              └ coinbase_onramp→ Coinbase Onramp API
4. scripts/log.sh           → state/payouts.jsonl 追記
```

## Output (state/payouts.jsonl)
```json
{"ts":"2026-06-01T...","method":"usdc","amount_usdc":42.50,"destination":"0xUSER...","tx_hash":"0x...","share_pct":30}
```

## Verify (HARD RULE #8)
- method=usdc → chain explorer で outbound tx 確認
- method=stripe_connect → Stripe transfer.id を Stripe API で fetch + verify
- method=wise → Wise transferId status=outgoing_payment_sent
- method=coinbase_onramp → Coinbase tx status=completed
- state/payouts.jsonl の cumulative ≤ Anicca lifetime revenue × max_share

## Verify (HARD RULE #18 no-human-in-loop)
- never prompt "payout 受け取りたい?" — profile.json gate のみ
- never ask "destination 教えて" — profile に 無ければ silent dormant
- never ask "share % いくつ?" — profile.payout_share_pct がそのまま
- error 時 = retry 内部 + log only、 user prompt 禁止
- profile に Dais 個人情報 ZERO 紐付け (= 各 install user の own profile)
