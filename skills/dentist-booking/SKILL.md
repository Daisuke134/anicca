---
name: dentist-booking
description: 任意ユーザーの周辺で「レビュー高」 + 「online 予約 or 連絡可能」な歯科を発見 → 予約 → gcal → Slack 報告。3 ヶ月毎の install 型 cron。entity-agnostic。
version: 0.1.0
---

# dentist-booking — universal recipe

任意の住所 + Gmail account を渡すと、Google Maps で「評価 4.3★+ + サンプル 30件+」の歯科を見つけて、定期メンテナンス受診を予約 + gcal + Slack。3 ヶ月毎 install 型 cron。

## Install — auto-add cron

```bash
bash ~/.openclaw/skills/dentist-booking/scripts/install.sh \
  --account "{{profile.contact.personalEmail}}" \
  --address "東京都{{profile.identity.homeAddress}}" \
  --name "<your-name>" \
  --gender "male" \
  --phone "08046270314" \
  --preferred-clinic "team428.com"  # 既に通ってるクリニックがあれば
```

cron 自動登録: `0 9 1 2,5,8,11 *` JST (Feb/May/Aug/Nov 1 日 9 JST)。

## Recipe — exact way

### Step 1: discover (preferred-clinic があれば skip)

camofox で Maps 検索:
```
https://www.google.com/maps/search/歯科+near+<URL-encoded address>
```

filter:
- rating >= 4.3
- review_count >= 30 (歯科は皆気合入った review 書く)
- 営業日に土曜午前を含む (平日 9-17 work block の制約)

### Step 2: 予約 method 判定

1. 自社サイト form (e.g. team428.com の mailformpro) — broken な場合多い
2. EPARK 歯科予約 (haisha-yoyaku.jp) — オンライン予約最大手
3. {{profile.lateness.stakeholders.channel}} backup (firecrawl で web から info@ や contact@ を取得)

### 🔴 KNOWN GOTCHA (2026-05-11)

team428.com (デンタルアソシエイツ歯科四谷) の form は **send.cgi の Perl @INC エラー** で壊れてる:
> Can't locate functions.cgi in @INC ... at send.cgi line 5

→ webmaster `brs-support@xbit.jp` 経由 {{profile.lateness.stakeholders.channel}} backup ルート使用。

### Step 3: 土曜午前 10 時 4 候補

土曜午前は平日 9-17 と被らない。4-8 週後の土曜 4 連続。

### Step 4: {{profile.lateness.stakeholders.channel}} or form submit

```bash
gog -a "$ACCOUNT" gmail send \
  --to "$CLINIC_CONTACT" \
  --subject "$CLINIC_NAME 予約申込み (土曜午前) — $NAME" \
  --body-file "$BODY_FILE"
```

本文 template (instance config から組み立て):

```
$CLINIC_NAME ご担当者様

お世話になっております。$ADDRESS 在住の患者の $NAME ($FURIGANA) と申します。
$VISIT_REASON のメンテナンス受診の予約をお願いしたくご連絡差し上げました。

【予約内容】
- 受診目的: メンテナンス (歯石除去 / クリーニング)
- 患者氏名: $NAME
- メール: $EMAIL
- 電話: $PHONE
- 性別: $GENDER

【ご予約希望日 (土曜午前 10:00)】
第一希望: $D1 (土) 10:00
第二希望: $D2 (土) 10:00
第三希望: $D3 (土) 10:00
第四希望: $D4 (土) 10:00

平日は本業の都合 9:00-17:00 が NG のため、土曜午前帯で調整いただけますと幸いです。
ご都合の良い日程をご教示いただけましたら、確定の旨ご返信させていただきます。

何卒よろしくお願い申し上げます。

$NAME
$EMAIL
$PHONE
```

### Step 5: gcal [PENDING] event 追加

返信受信後 mail-auto-reply 経由 or 手動で [CONFIRMED] に格上げ。

### Step 6: Slack 報告

## Frequency presets

| frequency | cron expr (JST) |
|----------|---|
| monthly | `0 9 1 * *` |
| **quarterly** (default) | `0 9 1 2,5,8,11 *` |
| biannual | `0 9 1 2,8 *` |
| yearly | `0 9 1 6 *` |

## Reference instance — Dais

- preferred-clinic: team428.com (デンタルアソシエイツ歯科四谷)
- Cron: `0 9 1 2,5,8,11 *` JST
- 既存 wrapper: `anicca-dentist-quarterly`

## Files

| Path | Purpose |
|------|---------|
| `scripts/install.sh` | config + cron add + restart |
| `scripts/discover.sh` | Maps 検索 + score |
| `scripts/book.sh` | form / {{profile.lateness.stakeholders.channel}} / EPARK 予約完走 |
| `scripts/run.sh` | discover → book → gcal → slack |
| `data/instances/<id>.json` | per-user config |

## ガード

- 平日 9-17 NG (HARD RULE #4)
- 既に直近 90 日で受診済みなら skip
- gcal で被ってる土曜は別の土曜に
