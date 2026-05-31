---
name: anicca-crowdworks-earner
description: **conditional** (default OFF)。 同 Lancers (gate: bank + gov ID)、 自動 task application + 納品 + 出金。 CrowdWorks は task 単価 低めだが volume 大、 LLM が大量 apply 可能。 spec §10 DEAD、 user opt-in でのみ revive。
metadata:
  type: conditional
  spec: ANICCA_TRUE_AUTONOMY_SPEC.md §5 + §10 (conditional revive only)
  parallel_safe: true
  expected_revenue: ¥500-20k / 案件 (active 時)
  requires:
    bins: [camofox, curl, jq, node]
    skills: [anicca-wallet, anicca-payout]
    env_optional: [CROWDWORKS_EMAIL, CROWDWORKS_PASSWORD]
---

# anicca-crowdworks-earner

## なぜ
CrowdWorks = 国内 最大 規模 lance platform。 Lancers と 同 eKYC + bank 出金 = Anicca 自前 NG。 但し install user opt-in 時 のみ revive。

特徴 = "タスク形式" 案件 (アンケート / 記事 / 翻訳 数百円-数千円) が 大量 = LLM 大量 apply に 向く。 task 完了 速度 で 月収 積み上げ可能。

## Gate
```
profile.json:
  bank_account: { name, branch, number, holder }
  government_id_image: <path/URL>
  jp_resident: true
  crowdworks_optin: true

不足 → silent dormant
```

## Flow (active 時)
```
1. scripts/check.sh             → gate satisfy?
                                  └ 不足 → exit 0 silent
2. scripts/signup.sh            → camofox で crowdworks.jp/register
                                  ├ email: profile.email
                                  └ SMS verify: profile.phone or LNVPN
3. scripts/scan-tasks.sh        → /tasks API or scrape で open task list 取得
                                  └ filter: skill match + 単価/分 ROI top
4. scripts/auto-apply.sh        → batch (max 20件/h) で 自動 apply + draft submit
                                  ├ task type: 文字起こし / 翻訳 / 短記事 / アンケート
                                  └ deliver immediately if task allows
5. scripts/handle-projects.sh   → 「プロジェクト形式」 で apply されたら 個別 deliver
6. scripts/ekyc.sh              → 出金前 政府ID upload (one-time)
7. scripts/withdraw.sh          → bank_account 振込
                                  → state/crowdworks-earnings.jsonl
```

## Output (state/crowdworks-earnings.jsonl)
```json
{"ts":"2026-06-01T...","task_id":"...","type":"task|project","amount_jpy":300,"status":"delivered|approved|paid"}
```

## Verify (HARD RULE #8)
- crowdworks.jp dashboard で 累計 報酬 が state 累計 と 一致
- 出金 履歴 page に 振込 record
- bank_account 着金 確認 (user 銀行 web scrape)
- state/crowdworks-earnings.jsonl 累計 > 0

## Verify (HARD RULE #18 no-human-in-loop)
- never ask user "task choose してください" — Anicca auto pick
- never ask "提案文 OK?" — LLM draft + recursive-improver で 内採点
- gate 不足 silent dormant、 user 通知 禁止
- selfie ekyc one-time 物理例外
- batch apply rate も auto、 confirm 求めない
