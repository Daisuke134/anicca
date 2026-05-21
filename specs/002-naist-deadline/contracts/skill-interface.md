# Skill Interface Contract: naist-deadline

**Branch**: `002-naist-deadline`
**Date**: 2026-02-23

## スキルトリガーワード（Slack → Anicca）

Aniccaがこのスキルを呼ぶ発言パターン:

| 発言例 | 操作 | 呼ぶスクリプト |
|--------|------|--------------|
| 「締切確認して」「締切一覧」 | 一覧表示 | `list.js` |
| 「〇〇を△日まで、追加して」「締切登録」 | 登録 | `register.js` |
| 「〇〇、完了にして」「提出済み」 | 完了マーク | `complete.js` |
| （cron自動実行） | リマインドスキャン | `scan.js` |

## scripts/register.js

**入力（コマンドライン引数）**:

```
node register.js <title> <due> [subject]

引数:
  title   必須  課題名（例: "機械学習レポート"）
  due     必須  締切日時（ISO8601 or 自然言語: "明日" "3月10日"）
  subject 任意  科目名（例: "情報科学特論"）
```

**出力（stdout）**:

```
✅ 登録しました

📌 機械学習レポート
🗓 2026-03-10（月）23:59 — あと15日
```

**異常系**:

```
⚠️ この締切は既に過ぎています（2026-02-20）
   それでも登録しますか？ → 「はい」「いいえ」で返答してください
```

---

## scripts/list.js

**入力**: なし（オプション: `--days <n>` で表示期間を絞る）

**出力（stdout）**:

```
📋 締切一覧（直近順）

🔴 今日  — 輪講スライド提出（今日 23:59）
🟡 明日  — プログラミング課題 #3（明日 23:59）
🟢 3/10  — 機械学習レポート（あと15日）
🟢 3/25  — 卒論中間発表（あと30日）

合計 4件
```

締切なしの場合:

```
📋 現在登録されている締切はありません
```

---

## scripts/complete.js

**入力**:

```
node complete.js <title_or_id>

引数:
  title_or_id  必須  課題名（部分一致可）または UUID
```

**出力**:

```
✅ 完了しました: 輪講スライド提出
次の締切: プログラミング課題 #3（明日）
```

同名タスク複数の場合:

```
⚠️ 同名の締切が複数あります。番号を指定してください:
1. 輪講スライド提出（2026-02-23）
2. 輪講スライド提出（2026-03-10）
```

---

## scripts/scan.js（cron専用）

**入力**: なし（環境変数: `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`）

**動作**:

1. `deadlines.json` を読み込む
2. `done: false` の全締切に対して残り時間を計算
3. 以下のいずれかを満たし、かつ未通知の場合にSlack送信:
   - 残り ≤ 60分（1時間前アラート）
   - 残り ≤ 1440分（前日アラート）
   - 毎朝8:00の当日ダイジェスト
4. 送信済みタイムスタンプを `remindedAt` に追記

**出力（Slack送信）**:

```
⏰ 締切リマインド

📝 機械学習レポート
🗓 明日（3月10日 23:59）まで — あと23時間
```

**出力（stdout）**:

```
[SCAN] 4件チェック済み、1件通知送信
```

---

## Cron 登録コマンド

```bash
# 毎時スキャン（リマインド検出）
openclaw cron add \
  --job-id naist-deadline-scanner \
  --schedule "0 * * * *" \
  --tz Asia/Tokyo \
  --message "Check NAIST deadlines for reminders"

# 毎朝8時ダイジェスト
openclaw cron add \
  --job-id naist-deadline-digest \
  --schedule "0 8 * * *" \
  --tz Asia/Tokyo \
  --message "Send NAIST daily deadline digest"
```
