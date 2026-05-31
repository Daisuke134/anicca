---
name: anicca-lancers-earner
description: **conditional** (default OFF)。 gate: profile.bank_account + profile.government_id_image 両方 揃った install user のみ。 Lancers signup → 案件 apply → 制作 → 納品 → eKYC auto-upload → 出金。 spec §10 で DEAD だが install user 持ち込み 資産 ある時 のみ revive。
metadata:
  type: conditional
  spec: ANICCA_TRUE_AUTONOMY_SPEC.md §5 + §10 (conditional revive only)
  parallel_safe: true
  expected_revenue: ¥3k-50k / 案件 (active 時)
  requires:
    bins: [camofox, curl, jq, node]
    skills: [anicca-wallet, anicca-payout]
    env_optional: [LANCERS_EMAIL, LANCERS_PASSWORD]
---

# anicca-lancers-earner

## なぜ
spec §5: Lancers は eKYC + マイナンバー 必須 = Anicca 自前 では NG。 但し install user が **「自分の bank + 政府ID を Anicca に 預ける」 と opt-in した時 のみ** revive 可能 (= user 持ち込み 資産 で 出金 path 確保)。 default OFF。

profile.json で 両方 揃わない 限り silent dormant。 揃った時 = user 名義 で signup + 案件 apply + 納品 + 出金 を Anicca が 全部 自動化、 出金先 = profile.bank_account。

## Gate
```
profile.json:
  bank_account: { name, branch, number, holder }
  government_id_image: <path or URL to user's ID image>
  jp_resident: true
  lancers_optin: true

全部 揃わない → silent dormant、 log なし、 cron fire しない
```

## Flow (active 時)
```
1. scripts/check.sh           → 4 gate keys 全部 satisfy?
                                └ 1 つでも欠 → exit 0 silent
2. scripts/signup.sh          → camofox で lancers.jp/register
                                ├ email: profile.email
                                ├ password: 自動生成 → secrets vault
                                └ SMS verify: profile.phone (or LNVPN eSIM)
3. scripts/scan-jobs.sh       → /work API or scrape で skill match top N pick
4. scripts/apply.sh <job_id>  → 提案文 LLM 生成 + send
5. scripts/deliver.sh <job_id>→ 採用 → 制作 → 納品 (= 該当 deliver skill fire)
6. scripts/ekyc.sh            → 出金前 必須: profile.government_id_image を upload
                                + 顔写真 selfie (要 user one-time、 ★ HARD RULE #18 例外)
7. scripts/withdraw.sh        → 報酬 → bank_account に 振込 trigger
                                → state/lancers-earnings.jsonl 追記
```

## Output (state/lancers-earnings.jsonl)
```json
{"ts":"2026-06-01T...","job_id":"...","amount_jpy":15000,"status":"delivered|accepted|paid","withdraw_tx":"..."}
```

## Verify (HARD RULE #8)
- Lancers dashboard URL を camofox 再訪 → job status visible
- bank_account に 着金 (= Anicca が user の 銀行 web を scrape 確認、 NOT MUFG固定)
- state/lancers-earnings.jsonl 累計 > 0

## Verify (HARD RULE #18 no-human-in-loop)
- never ask install user "bank info 教えて" — profile.json 経由 のみ
- never ask "ID 写真 ください" — profile.government_id_image path 経由
- gate 不足 = silent (= user に "足り ません" 通知 禁止、 log only)
- 案件 apply / 納品 / 出金 全部 confirm 求めない、 only profile.json 参照
- selfie 撮影 = HARD RULE #18 物理例外 (= ekyc.sh が one-time 要求、 以後 永続)
