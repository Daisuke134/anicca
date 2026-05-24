---
name: anicca-comedy-weekly-book
description: 毎週 Dais の comedy live を 1 本ブッキングする skill。Calendar の 9-17 本業ブロックを避け、平日 18:30+ or 土日午前/夕方の枠を取る。{{profile.identity.{{profile.lateness.stakeholders.senderType}}Name}}名義、<training-school>一切書かない。
version: 0.1.0
---

# anicca-comedy-weekly-book

## What

Dais の comedy schedule が空いてる週は 1 本必ずブッキングする。9-17 本業ブロック (HARD RULE #4) は触らない。

## Recipe — exact way I did 5/14 booking

このスキルは「**今やっていることを正確に書き写したレシピ**」。Playwright 等で書き直さない。
camofox / firecrawl / gog cli / openclaw 全部 Anicca も同じ tech stack を持ってる。

### Step 1: 候補日リスト作成

```bash
# 来週分の Cal を取得
[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a
FROM=$(date -v+1d '+%Y-%m-%dT%H:%M:%SZ')
TO=$(date -v+8d '+%Y-%m-%dT%H:%M:%SZ')
gog -a {{profile.contact.personalEmail}} calendar list primary --from "$FROM" --to "$TO" --plain --max 50
```

`9-17 work block` + 既存予定 を除外して空きスロットを得る。
- 平日: 17:30 退社 + 30 min 移動 = 18:00 以降の入り (中野 / 新宿) OK
- 土日: 10:00-22:00 OK

### Step 2: open mic schedule 確認

主要サイト 4 件 + note トフィー一覧:
1. U&C パワーオブフリー: http://uandcenterprise.jp/entry.php (★ メール 1 通で entry 完結)
2. たか7 小猿/肉食ライブ: https://ameblo.jp/odakarat/
3. K-PRO ゲレロンステージ: https://kpro-web.com/gereron/
4. 下北GRIP: https://shimokita-grip.stores.jp/reserve/shimokita-grip/586126 (stores.jp 経由、camofox で予約)
5. note 一覧 (参考): https://note.com/toffee101/n/n3f48144ac982

```bash
firecrawl scrape "http://uandcenterprise.jp/schedule.php?genre=newcomer" markdown | grep -B1 -A20 "$DESIRED_DATE"
```

### Step 3: U&C パワーオブフリー エントリー (基本ルート)

メール 1 通で完結する一番楽なルート。`live_entry@yahoo.co.jp` 宛て。
テンプレート:

```
希望月日・曜日◆ YYYY/MM/DD(曜)
ライブ名◆ パワーオブフリー(Ｓ) vol.千XX
ユニット名◆ {{profile.identity.{{profile.lateness.stakeholders.senderType}}Name}}
人数◆ ピン
ネタ形態◆ 漫談
代表者名◆ <your-name>
電話番号◆ 080-4627-0314
```

```bash
gog -a {{profile.contact.personalEmail}} gmail send \
  --to "live_entry@yahoo.co.jp" \
  --subject "ライブ出演希望 — パワーオブフリー(Ｓ) vol.千XX / {{profile.identity.{{profile.lateness.stakeholders.senderType}}Name}}(ピン)" \
  --body-file /tmp/uandc-entry.txt --json
```

### Step 4: 下北GRIP (代替ルート — stores.jp で完結)

camofox で stores.jp の booking ページ操作。`feedback_calendar_first_booking_rules` で
detailed flow 記録済 (RULE F)。

### Step 5: gcal 登録

```bash
gog -a {{profile.contact.personalEmail}} calendar create primary \
  --summary "🎤 [TENTATIVE] $LIVE_NAME — {{profile.identity.{{profile.lateness.stakeholders.senderType}}Name}}(ピン 漫談)" \
  --from "$ISO_START" --to "$ISO_END" \
  --location "$VENUE" \
  --description "入り $IRI / 開場 $KAIJO / 開演 $KAIEN
ネタ尺 $NETA / 料金 ¥$FEE
キャンセルポリシー: 5日前以降キャンセル料発生 / 2日前以降は理由問わず
申込 mail: $GMAIL_MSG_ID
cancellable=false from 2 days before"
```

返信確認は `anicca-mail-auto-reply` 経由 + 手動で [CONFIRMED] にアップデート。

### Step 6: Slack 報告

```bash
python3 -c "..." -> #metrics に header + fields blocks 投稿
```

## <training-school>/<your-school> 絶対書かない (HARD RULE #4 RULE C)

- アンケート / 自由欄に「<training-school>」「1年目」「芸歴」「<your-school>」全部 NG
- 芸名 {{profile.identity.{{profile.lateness.stakeholders.senderType}}Name}} のみ
- 必要なら ピン芸人 / コメディアン まで

## キャンセル不可 marker

- gcal description に必ず `cancellable=false from <date>` 記載
- 2日切ったらキャンセル料発生

## Files

| Path | Purpose |
|------|---------|
| `scripts/phase1-find-slot.sh` | Cal + open mic schedule を merge → 候補日決定 |
| `scripts/phase2-entry-uandc.sh` | U&C パワーオブフリー mail entry |
| `scripts/phase3-cal-add.sh` | gcal [TENTATIVE] event 追加 |
| `scripts/run.sh` | phase1+2+3 順次実行 + Slack 報告 |

## Cron

毎週月 8:00 JST。前週の reply 確認 + 来週の新規 entry。
