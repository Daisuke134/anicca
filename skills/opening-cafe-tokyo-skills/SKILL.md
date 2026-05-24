---
name: opening-cafe-tokyo-skills
description: End-to-end lifecycle skill for opening a ghost-kitchen cafe in Tokyo. Manages every phase from kitchen discovery → contract → 開業届け → 営業許可 → Uber Eats merchant signup → menu publish → daily sales sync → SNS cross-post. Configurable per entity (any operator, any product, any Tokyo area). Use when triggered by `opening-cafe-status-weekly` Mon 10:00 JST, manually as `bash scripts/phase{0..10}-*.sh`, or via event-driven phase transitions.
metadata:
  tags: cafe, ghost-kitchen, tokyo, uber-eats, license, {{profile.lateness.stakeholders.channel}}-harness, end-to-end
  requires:
    bins: [bash, jq, curl, {{profile.lateness.stakeholders.channel}}-harness, gog]
    env: [DAIS_EMAIL, DAIS_PRIMARY_PW, DAIS_PHONE, GOG_ACCOUNT, GOG_KEYRING_PASSWORD, SLACK_CHANNEL]
---

# opening-cafe-tokyo-skills

End-to-end ghost-kitchen lifecycle in Tokyo. **Generic** — driven by `data/config.json`, so any entity (Anicca cafe / another AI entity / human) can run it for their own product, address, schedule.

## Why ghost-kitchen first

- 客席不要 → 物件コスト最小
- Uber Eats 経由の純デリバリー収益
- 1 人運営可、週末のみ稼働でも回る
- 営業許可取得済シェアキッチンを借りれば 自前申請不要

## Phase 0-10 (whole lifecycle)

| Phase | What | Auto/Manual |
|---|---|---|
| 0 | Kitchen discover + 内見申込 | auto + Dais 物理訪問 |
| 1 | 個人事業主 開業届け (yamitzky/freee-cli) | auto + Dais e-Tax 提出 |
| 2 | 食品衛生責任者 講習 (シェア許可借用なら不要) | conditional |
| 3 | 営業許可確保 (Route A: 借用 / Route B: 自前申請) | auto + Dais 立会必要時 |
| 4 | Uber Eats merchant signup | auto + Dais 契約面談 |
| 5 | メニュー登録 (UberEats Manager) | auto + Dais 商品撮影 |
| 6 | landing /cafe → Uber Eats store URL リダイレクト | auto |
| 7 | 物理ローンチ準備 (Vitamix / 容器 / 仕入れ) | Dais |
| 8 | ローンチ初日 | Dais 仕込み + skill 監視 |
| 9 | 日次運営 sync (cron 23 JST) | auto |
| 10 | SNS cross-post (cron 16 JST) | auto |

## Generic config (`data/config.example.json`)

```json
{
  "entity_name": "Anicca",
  "operator": {
    "name": "<your-name>",
    "name_kana": "<your-name>",
    "{{profile.lateness.stakeholders.channel}}": "${DAIS_EMAIL}",
    "phone": "${DAIS_PHONE}",
    "address": "東京都<your-address>",
    "home_station": "信濃町"
  },
  "preferences": {
    "areas": ["新宿区", "文京区", "千代田区", "渋谷区"],
    "max_hourly_jpy": 1500,
    "max_monthly_jpy": 50000,
    "weekly_hours": 10,
    "weekend_only": true,
    "license_required": ["飲食店営業許可"]
  },
  "product": {
    "name": "Anicca Mango Reset",
    "category": "ジュース・飲料",
    "price_jpy": 1500,
    "cost_jpy": 350,
    "description": "完熟マンゴー + ライム + 氷の 350ml ボトル",
    "allergens": ["マンゴー", "ライム"]
  },
  "delivery_platforms": ["uber_eats_jp"],
  "landing_redirect_path": "/cafe",
  "social_cross_post_to": ["x", "tiktok", "instagram"]
}
```

別 entity が `data/config.json` 差替えるだけで Tokyo 内 任意エリア・任意 product で稼働。

## Platform modules (`scripts/lib/`)

| module | scope |
|---|---|
| `lib/kashispace.sh` | kashispace.com 任意 room の問合せ form 自動送信 |
| `lib/theghostrestaurant.sh` | theghostrestaurant.tokyo 内見申込 form 自動送信 |
| `lib/spacemarket.sh` | spacemarket.com 問合せ (login 必要、初回 Dais signup) |
| `lib/freee.sh` | yamitzky/freee-cli wrapper、開業届け 生成 |
| `lib/toshokuken.sh` | toshokuken.or.jp 食衛責 講習会 申込 |
| `lib/uber-eats-merchant.sh` | merchants.ubereats.com/jp/ja signup + UberEats Manager |
| `lib/gcal.sh` | gog calendar create wrapper |
| `lib/slack.sh` | openclaw message send wrapper |
| `lib/dais-alert.sh` | Slack + Calendar 統合 alert (期限・URL・必要 data 込み) |

各 module は **任意の room_id / 任意の operator config** で動く。Anicca 専用 hard-code ゼロ。

## Phase scripts (`scripts/`)

| script | input | output |
|---|---|---|
| `phase0-discover.sh` | config | data/cafe/candidates.json (kashispace + theghostrestaurant + spacemarket 検索 + ranking) |
| `phase0-inquire.sh <platform> <room_id>` | candidates.json | data/cafe/inquiries/<id>.json + GCal event + Slack |
| `phase0-watch-replies.sh` (cron) | — | inquiries/*.json status flip |
| `phase1-kaigyou-todoke.sh` | config | data/cafe/operator_id.json + Slack alert (Dais e-Tax 提出) |
| `phase2-shokueisha-course.sh` | config (Phase 3 Route B 時のみ) | data/cafe/food_safety.json + Slack (Dais 講習出席) |
| `phase3-license-confirm.sh` | chosen kitchen | data/cafe/license.json |
| `phase4-uber-merchant-signup.sh` | config + license PDF | data/cafe/uber_signup.json + Slack (Dais 契約面談指示) |
| `phase5-uber-menu-publish.sh` | config.product + 商品写真 path | data/cafe/menu.json |
| `phase6-cafe-redirect-deploy.sh` | uber_merchant_id | apps/landing redirect commit + push |
| `phase9-daily-ops.sh` (cron) | uber_merchant_id | data/cafe/sales/<date>.json + dashboard.json 反映 |
| `phase10-cross-post-daily.sh` (cron) | sales + photos | post URLs (anicca-x-marketing-skill 連携) |
| `status.sh` | state.json | Slack 報告 + 次アクション |

## Pattern: human-in-the-loop alert

skill が auto できない物理タスク (電話 / 訪問 / 講習出席 / 検査立会 / 現金支払い / Captcha 等) は **必ず** 以下を実行:

```
① Slack alert (#metrics):
    📞 [Phase X | DAIS 必要] <タスク名>
    日時: <iso>
    場所/方法: <详细>
    必要持ち物: <list>
    完了後: <state.json の何を更新するか>

② Google Calendar event 追加 (gog cli):
    gog calendar create primary
      --summary "[DAIS] <タスク名>" --from <iso> --to <iso>
      --description "<full instruction>"

③ state.json に manual_action_required: true + due_at 永続化
```

→ Dais がスマホ Slack でも PC Calendar でも気づける。

## Cron grid

| name | schedule | phase | what |
|---|---|---|---|
| `opening-cafe-status-weekly` | `0 10 * * 1` JST | 全 phase | 現状 + 次アクション → Slack |
| `opening-cafe-watch-replies-6h` | `0 */6 * * *` JST | 0-3 | Gmail で 担当者返信 / freee 通知 / 保健所メール 監視 |
| `opening-cafe-daily-ops` | `0 23 * * *` JST | 9 | 日次売上 sync |
| `opening-cafe-cross-post-daily` | `0 16 * * *` JST | 10 | SNS cross-post |
| event-driven | state phase 変化時 | — | 次 phase auto 起動 |

## Generality (any AI entity が clone して使える条件)

- [x] config.json で operator info を切り替え → 別人の cafe に使える
- [x] preferences.areas で東京の任意エリアを指定可能
- [x] product 全 field 設定可能 (mango juice 限定でない)
- [x] delivery_platforms 配列 (将来 Wolt / 出前館 追加可能)
- [x] platform modules が任意 room_id / 任意 event を扱える
- [x] Anicca 専用 hard-code ゼロ (pitch / CTA も無し)
- [x] human-in-the-loop pattern で 物理タスクも skill 内で escalate
