# 1.6.3 X Article（長文 1 本 25k 文字）スペック

作成: 2026-02-11  
スコープ: X の「1本最大 25,000 文字」の Long-form Post（Article）を mission-worker 経由で自動投稿する。

---

## 1. 目的

| 項目 | 内容 |
|------|------|
| 成果物 | X 上に「記事」として長文（281〜25,000 文字）を 1 本で投稿する。 |
| 用途 | Nudge の一形態として長文コンテンツを配信する（1.6.3 の X 縦活用）。 |
| 前提 | 投稿に使う X アカウントは X Premium（旧 Twitter Blue）であること。Premium でない場合は 280 文字で切り捨てられる。 |

---

## 2. 外部仕様（X API v2）

| 項目 | 値 |
|------|-----|
| エンドポイント | `POST https://api.twitter.com/2/tweets` |
| リクエストボディ | `{ "text": "<本文>" }`。Premium アカウントで 25,000 文字まで。 |
| 認証 | OAuth 2.0 User Context（そのアカウントの access token）が必須。ユーザー代わりに投稿するため。 |
| レート制限 | 同一ユーザあたり 200 リクエスト / 15 分（一般の Create Post と同様と仮定）。 |
| 参照 | X Developer Changelog（2024-08: Long Form Posts 対応）、Publer ドキュメント（25k 文字・Premium 必須）。 |

---

## 3. 認証方針

| 優先 | 方法 | 内容 |
|------|------|------|
| 1 | Blotato に確認 | Blotato API で long-form（1本 25k 文字）がサポートされているか問い合わせる。サポートされていれば既存 Blotato 経由で実装する。 |
| 2 | X API 直叩き | Blotato が未対応の場合、Backend から X API v2 を直接呼ぶ。OAuth 2.0 で取得した Anicca 用 X アカウントの access token を env で保持する。 |

本スペックは **方針 2（X API 直叩き）** を前提に記載する。方針 1 が使える場合は executor の実装先が Blotato に変わるだけで、step 名・入出力・DB は同じとする。

---

## 4. Step 定義

| 項目 | 値 |
|------|-----|
| step_kind | `post_x_article` |
| 役割 | 長文（281〜25,000 文字）を X に 1 本の Article として投稿し、DB に記録する。 |
| 入力（input） | `content`（string, 必須）, `hookId`（string, 任意）, `slot`（string, 任意）, `verificationScore`（number, 任意） |
| 出力（output） | `postId`（string）, `xPostId`（string, X の tweet id）, `platform: "x"` |
| イベント | `x_article_posted`（tags: `["article", "posted"]`, payload: postId, xPostId, hookId, contentPreview） |

入力検証:

| ルール | 内容 |
|--------|------|
| content 必須 | `input.content` が無い場合はエラー（`post_x_article requires input.content`）。 |
| 文字数 | 281 以上 25,000 以下。280 以下は既存 `post_x` に任せる。25,001 以上は 25,000 で truncate するかエラーにする（実装でどちらかを固定する）。 |

---

## 5. Executor

| 項目 | 内容 |
|------|------|
| ファイル | `apps/api/src/services/ops/stepExecutors/executePostXArticle.js` |
| 登録 | `registry.js` に `post_x_article` → `executePostXArticle` を追加する。 |
| 処理概要 | 1) 入力検証 2) X API v2 `POST /2/tweets` に `{ "text": content }` を送る 3) `Authorization: Bearer <X_ARTICLE_ACCESS_TOKEN>` を使用 4) 応答の `data.id` を x_post_id として DB に保存 5) output と events を返す。 |
| 失敗時 | 4xx/5xx の場合はエラーを投げ、step は failed として記録する。リトライは既存の post_x と同様のポリシー（429/5xx のみなど）に合わせる。 |

---

## 6. 認証（X API 直叩きの場合）

| 項目 | 内容 |
|------|------|
| 取得手順 | X Developer Portal でアプリ作成 → OAuth 2.0 有効化 → scopes に `tweet.read`, `tweet.write`, `users.read` を含める。Anicca 用 X アカウントで 1 回 OAuth 認証し、access token（および必要なら refresh token）を取得する。 |
| 環境変数 | `X_ARTICLE_ACCESS_TOKEN`（必須）。必要に応じて `X_ARTICLE_REFRESH_TOKEN`, `X_API_CLIENT_ID`, `X_API_CLIENT_SECRET` を用意し、token 更新処理を実装する。 |
| 保管 | トークンは env またはシークレットに格納し、リポジトリにコミットしない。 |

---

## 7. DB

| 項目 | 内容 |
|------|------|
| テーブル | 既存の `x_posts` を流用する。 |
| 追加カラム | `is_long_form`（boolean, デフォルト false）。`post_x_article` で作成したレコードは `true` にする。 |
| 保存内容 | `text` に長文全文を保存する。`blotato_post_id` は null。`x_post_id` に X API の返却 id を保存する。`hook_candidate_id`, `slot`, `posted_at`, `agent_reasoning` は既存と同様。 |

Migration: `is_long_form` を追加する Prisma migration を 1 本用意する。

---

## 8. スキル・提案との接続

| 項目 | 内容 |
|------|------|
| スキル名 | `x-article-poster`（x-poster とは別）。 |
| 役割 | 「Article 用の長文を draft し、verify のあと `post_x_article` を実行する」までをスキル指示に書く。 |
| Proposal / Mission | 既存の proposal → mission → steps の流れに、step_kind `post_x_article` を追加できるようにする。draft_article（または draft_content の article モード）→ verify_content → post_x_article の 3 ステップを想定。 |
| レート制限対策 | Article 投稿は 1 日あたりの上限を設ける（例: 1 日 1 本）。cap gate または proposal 側で制限する。 |

---

## 9. 既存 post_x との役割分担

| step_kind | 文字数 | 経路 | 用途 |
|-----------|--------|------|------|
| post_x | 1〜280 | Blotato API | 通常ツイート。既存の x-poster のまま。 |
| post_x_article | 281〜25,000 | X API v2 直 | 1 本の長文 Article。x-article-poster で使用。 |

同一の `x_posts` テーブルで `is_long_form` により区別する。

---

## 10. 実装チェックリスト

| # | タスク | 必須 |
|---|--------|------|
| 1 | Blotato に long-form 対応の有無を問い合わせる | MUST |
| 2 | 未対応の場合: X Developer でアプリ作成・OAuth 2.0 で Anicca アカウントの token 取得 | MUST |
| 3 | env に `X_ARTICLE_ACCESS_TOKEN` を設定（直叩きの場合） | MUST |
| 4 | `x_posts.is_long_form` の migration 追加 | MUST |
| 5 | `executePostXArticle.js` 実装（入力検証・X API 呼び出し・DB 保存・output/events） | MUST |
| 6 | `registry.js` に `post_x_article` を登録 | MUST |
| 7 | proposal / step で `post_x_article` を扱えるようにする（既存 step 種別追加） | MUST |
| 8 | OpenClaw スキル `x-article-poster` の SKILL.md を作成し、VPS に配置 | MUST |
| 9 | Article 用のレート制限または 1 日上限を設ける | MUST |

---

## 11. 参照

| ソース | 内容 |
|--------|------|
| X API Changelog | Long Form Posts（2024-08） |
| Publer: Twitter/X Long-Form Posts | 25,000 文字・Premium 必須・`long_post` 形式 |
| Blotato: Publish Post | 現状は thread（additionalPosts）まで。long-form は要確認。 |
| 既存 post_x | `apps/api/src/services/ops/stepExecutors/executePostX.js` |

---

最終更新: 2026-02-11
