---
name: x-poster
description: "workspace/hooks の slot(9am/9pm) を読んで X に投稿する（返信はしない）"
metadata: {"openclaw":{"emoji":"𝕏","os":["darwin","linux"]}}
---

# x-poster

## 目的
X 投稿の Proposal を作成。steps: `draft_content -> verify_content -> post_x`。X は**投稿のみ**（返信禁止）。朝は **slot 9am**、夜は **slot 9pm** の 1 本だけを使う。

## 保存先（Anicca 内・読むだけ）

| データ | フルパス |
|--------|----------|
| 投稿文（読む） | **morning:** `~/.openclaw/workspace/hooks/9am/YYYY-MM-DD.json` の `entries` のうち `platform: "x"` の `postText`。**evening:** `~/.openclaw/workspace/hooks/9pm/YYYY-MM-DD.json` の同様。 |

YYYY-MM-DD は今日の日付（Asia/Tokyo）。trend-hunter が slot 別に書いた 1 本をそのまま X に投稿する。

## 必須 env
| キー | 説明 |
|------|------|
| `POSTIZ_API_KEY` | Postiz API キー |
| `POSTIZ_X_INTEGRATION_ID` | Postiz X integration ID (@aniccaxxx: cmm6d7m5703rwpr0yr5vtme3w) |

## Postiz API（S1準拠）

**Base URL: `https://api.postiz.com/public/v1`**
**Rate Limit: 30 requests/hour**

```
POST https://api.postiz.com/public/v1/posts
Header: Authorization: <POSTIZ_API_KEY>
Header: Content-Type: application/json
Body:
{
  "type": "now",
  "shortLink": false,
  "tags": [],
  "posts": [{
    "integration": { "id": "<POSTIZ_X_INTEGRATION_ID>" },
    "value": [{ "content": "<投稿テキスト>" }],
    "settings": { "__type": "x", "who_can_reply_post": "everyone" }
  }]
}
```

レスポンスの posts[0].releaseURL で公開URLを即取得（ポーリング不要）。
posts[0].id をメトリクス取得用に保存する。

## 必須 tools
- `web_fetch`（Postiz API呼び出し用）

## 入力
- cron slot 起動時: trigger で proposal 作成。
- `skillName: "x-poster"`, `steps: [draft_content, verify_content, post_x]`。

## 実行手順
1. 今日の日付（Asia/Tokyo）を取得する
2. slot に対応するJSONファイルを読む（`~/.openclaw/workspace/hooks/<slot>/YYYY-MM-DD.json`）
3. `platform: "x"` の `postText` を取得する
4. Postiz API（`https://api.postiz.com/public/v1/posts`）で投稿する
5. レスポンスから `releaseURL` を取得する
6. Slack #metrics に結果を投稿する

## Slack 報告
**【絶対】** 実行結果を Slack #metrics（チャンネル ID: `{{profile.channels.reportChannel}}`）に投稿する。

```
x-poster ({slot}) — ✅ 投稿成功 / ❌ 失敗

日時: YYYY-MM-DD HH:MM JST
投稿テキスト: <全文そのまま>
X リンク: <releaseURL>
備考: <エラー・スキップ理由等>
```

## 出力 / 監査ログ
- `post_x` 完了時: `tweet_posted` イベント、postId を output に含める。
- 失敗時: DLQ + ops event。

## 失敗時処理
- 429: 60/300/1800s でリトライ。
- 5xx: 同様リトライ（最大3回）。
- その他（DNS不可・接続失敗等）: DLQ + ops event + Slack通知。

## 禁止事項
- **X 返信は絶対禁止**。投稿のみ。
- 文字数 260 超禁止。

## Cron
- `x-poster-morning`: `0 9 * * *`（停止予定）
- `x-poster-evening`: `0 21 * * *`（停止予定）
