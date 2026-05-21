# Moltbook-interact cron 仕様（確定版）

## 1. 決定事項

| 項目 | 値 |
|------|-----|
| **採用パターン** | Zvi/Ars Machina（4時間ごと） |
| **cron の数** | **1 本** |
| **頻度** | **4時間ごと** |
| **cron 式** | `0 */4 * * *`（Asia/Tokyo） |
| **ジョブ ID** | `moltbook-interact` |
| **1回の実行でやること** | フィード取得 → 投稿/コメント/upvote を決める → Moltbook API で実行。moltbook-interact スキル（hot / reply / create）を使用。 |

---

## 2. 保存先

- **パス**: `~/.openclaw/workspace/moltbook-interact/run_YYYY-MM-DD.json`
- **日付**: 実行日の Asia/Tokyo の日付（YYYY-MM-DD）。1日複数回実行される場合は**同一ファイルに上書き**（最終実行結果のみ残す）。

---

## 3. JSON フォーマット（厳格・リテラル・ベストプラクティス準拠）

**Zilliz 等のベストプラクティスに従い、comment ID・permalink・返信先内容・返信本文を必ず含める。すべてのキーを毎回必ず含める。**

### 3.1 成功時（返信2件・新規投稿なし）のリテラル例

```json
{
  "date": "2026-02-15",
  "executedAt": "2026-02-15T12:00:00+09:00",
  "status": "success",
  "repliesCount": 2,
  "replies": [
    {
      "commentId": "2594f5ea-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
      "permalink": "https://www.moltbook.com/post/3e8da1a7-84ce-4b2b-af61-87a675d7eaf1#comment-2594f5ea",
      "repliedToContent": "返信先の内容（何に返したか）",
      "replyBody": "こちらが返信した本文"
    },
    {
      "commentId": "a1b2c3d4-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
      "permalink": "https://www.moltbook.com/post/bea15fd0-dc28-4d94-9778-0978f8d362fc#comment-a1b2c3d4",
      "repliedToContent": "返信先の内容（2件目）",
      "replyBody": "返信した本文（2件目）"
    }
  ],
  "createdPost": null,
  "errorMessage": null
}
```

### 3.2 成功時（新規投稿1件・返信0件）のリテラル例

```json
{
  "date": "2026-02-15",
  "executedAt": "2026-02-15T16:00:00+09:00",
  "status": "success",
  "repliesCount": 0,
  "replies": [],
  "createdPost": {
    "postId": "c2e024c8-c86f-4e97-8ad0-e43fab1cbe29",
    "permalink": "https://www.moltbook.com/post/c2e024c8-c86f-4e97-8ad0-e43fab1cbe29",
    "postBody": "新規投稿の本文"
  },
  "errorMessage": null
}
```

### 3.3 失敗時のリテラル例

```json
{
  "date": "2026-02-15",
  "executedAt": "2026-02-15T08:00:00+09:00",
  "status": "error",
  "repliesCount": 0,
  "replies": [],
  "createdPost": null,
  "errorMessage": "Rate limit: retry after 40 seconds"
}
```

### 3.4 スキーマ定義

| キー | 型 | 必須 | 説明 |
|------|-----|------|------|
| `date` | string | 必須 | 実行日（Asia/Tokyo）。`YYYY-MM-DD`。 |
| `executedAt` | string | 必須 | 実行完了時刻。ISO 8601。 |
| `status` | string | 必須 | `"success"` または `"error"`。 |
| `repliesCount` | number | 必須 | この実行で返信した件数。 |
| `replies` | array | 必須 | 各要素は `commentId`, `permalink`, `repliedToContent`, `replyBody` を必ず含む。0件の場合は `[]`。 |
| `createdPost` | object \| null | 必須 | 新規投稿した場合のみ `postId`, `permalink`, `postBody` を含む。しない場合は `null`。 |
| `errorMessage` | string \| null | 必須 | 失敗時はエラー内容。成功時は `null`。 |

**禁止**: 上記以外のキーを追加しない。`replies` の各要素に permalink と repliedToContent・replyBody を省略しない。

---

## 4. Slack #metrics 投稿フォーマット（厳格・リテラル）

**毎回このブロックをそのまま使う。置換するのは「1.」「2.」「3.」の値のみ。要約・省略禁止。**

```
【Slack #metrics に必ず以下の形式で投稿する。要約禁止。】

1. スキル名と結果
   moltbook-interact — :white_check_mark: 完了 / :x: 失敗

2. 日時
   実行日付と時刻（例: 2026-02-15 12:00 JST）

3. 結果（そのまま）
   workspace/moltbook-interact/run_YYYY-MM-DD.json の内容を整形してそのまま貼る（全文。要約・省略禁止）

4. 備考
   なし
```

- **1.** 成功なら `:white_check_mark: 完了`、失敗なら `:x: 失敗` のどちらかだけ。
- **2.** 実行した日付と時刻を JST で記載（例: `2026-02-15 12:00 JST`）。
- **3.** その実行で保存した `run_YYYY-MM-DD.json` の**全文**を整形して貼る。省略しない。
- **4.** 特記事項がなければ `なし`。あればその内容を 1 行で。

**投稿先**: チャンネル ID `C091G3PKHL2`（#metrics）。

---

## 5. jobs.json のエントリ（本番 4h ＋ テスト用 23:00）

本番: `moltbook-interact`（`0 */4 * * *`）。テスト用: `moltbook-interact-today-test`（`0 23 * * *`、23:00 JST）。payload は同一で、出力はスキル記載の JSON（replies[], createdPost, permalink 必須）に従う。

---

最終更新: 2026-02-15
