---
name: x-poster
description: "workspace/hooks の slot(9am/9pm) を読んで X に投稿する（返信はしない）"
metadata: {"openclaw":{"emoji":"𝕏","os":["linux"]}}
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
| `POSTIZ_API_KEY` | Postiz API キー（X 投稿に必須） |
| `POSTIZ_X_INTEGRATION_ID` | Postiz X integration ID（@aniccaxxx: `cmm6d7m5703rwpr0yr5vtme3w`） |

> 2026-05-07: Blotato → Postiz 移行（Daisuke direction）。`BLOTATO_*` env は廃止。
> Integration ID 一覧の正本: `~/.openclaw/state/postiz-integrations.json`。

## 必須 tools
- `web_fetch`（Postiz API 呼び出し）
- X 投稿は **Postiz API のみ**（`POST https://api.postiz.com/public/v1/posts`）。Twitter API 直接は使わない。

## Postiz API リクエスト

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

レスポンスの `posts[0].releaseURL` で公開 URL を即取得（ポーリング不要）。`posts[0].id` をメトリクス取得用に保存する。

## 入力
- cron slot 起動時: trigger で proposal 作成。
- `skillName: "x-poster"`, `steps: [draft_content, verify_content, post_x]`。

## 実行手順
1. ops-heartbeat の trigger または cron で proposal 作成。
2. mission-worker が draft_content -> verify_content -> post_x を順実行。
3. 文字数上限 260、429/5xx のみリトライ（最大3回）、DLQ に非リトライを退避。

## Slack 報告
**【絶対】** 実行結果を Slack #metrics（チャンネル ID: `C091G3PKHL2`）に投稿する。要約禁止。**以下をそのままこの形式で投稿する。**

```
【Slack #metrics に必ず以下の形式で投稿する。要約禁止。】

1. スキル名と結果
   x-poster ({slot}) — :white_check_mark: 投稿成功 / :x: 失敗

2. 日時
   日付と投稿実行時刻（例: 2026-02-15 15:10 JST）

3. 内容（省略禁止）
   投稿したツイート全文をそのまま貼る。1文字も省略しない。

4. X の投稿リンク
   Postiz の **`releaseURL`**（投稿レスポンスから即取得・ポーリング不要）。他 URL は貼らない。（例: https://x.com/username/status/1234567890）

5. 備考（あれば）
   スキップ理由・エラー・手動トリガー等
```

## 出力 / 監査ログ
- `post_x` 完了時: `tweet_posted` イベント、postId を output に含める。
- 失敗時: DLQ + ops event。

## 失敗時処理
- 429: 60/300/1800s でリトライ。
- 5xx: 同様リトライ。
- その他: DLQ + ops event。

## 禁止事項
- **X 返信は絶対禁止**。投稿のみ。
- 文字数 260 超禁止。

## Cron
- `x-poster-morning`: `0 9 * * *`
- `x-poster-evening`: `0 21 * * *`
