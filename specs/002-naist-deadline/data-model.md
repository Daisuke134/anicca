# Data Model: naist-deadline

**Branch**: `002-naist-deadline`
**Date**: 2026-02-23

## Storage Location

```
/Users/anicca/.openclaw/skills/naist-deadline/data/deadlines.json
```

## Deadline エンティティ

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `id` | string (UUID) | YES | 一意識別子 |
| `title` | string | YES | 課題名（例: "機械学習レポート"） |
| `due` | string (ISO8601) | YES | 締切日時（JST、例: "2026-03-10T23:59:00+09:00"） |
| `done` | boolean | YES | 完了フラグ（デフォルト: false） |
| `createdAt` | string (ISO8601) | YES | 登録日時 |
| `remindedAt` | string[] | YES | 通知済みタイムスタンプ一覧（重複防止） |

## deadlines.json スキーマ

```json
{
  "schemaVersion": 1,
  "updatedAt": "2026-02-23T10:30:00+09:00",
  "deadlines": [
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "title": "機械学習レポート",
      "due": "2026-03-10T23:59:00+09:00",
      "done": false,
      "createdAt": "2026-02-23T10:30:00+09:00",
      "remindedAt": []
    }
  ]
}
```

## 状態遷移

```
active（done: false）
    │
    │ 「完了にして」
    ▼
done（done: true）
    │
    │ ※ 一覧表示から除外されるが削除はしない
    │ （履歴として保持）
```

## リマインド判定ロジック

```
現在時刻から締切までの残り分数を計算:
  残り <= 60分  → "⏰ あと1時間: {title}"
  残り <= 1440分 → "📅 明日が締切: {title}"
  毎朝8:00      → 当日締切の全件ダイジェスト

重複防止:
  remindedAt に「前日通知済み」「当日通知済み」「1時間前通知済み」の
  タイムスタンプが存在する場合はスキップ
```

## バリデーションルール

| ルール | 内容 |
|--------|------|
| title | 空文字禁止、255文字以内 |
| due | ISO8601形式、パース可能な日付文字列 |
| 過去日付 | 警告を出すが登録は許可（今日以前の締切も記録可能） |

## 書き込みパターン（原子性確保）

```
1. deadlines.json を読み込む
2. 変更を加えたオブジェクトを作成
3. deadlines.json.tmp に書き込む
4. fs.renameSync(tmp, deadlines.json) で原子的に置き換える
```
