# 実装仕様書: Anicca in the World (1.6.1)

> **RFC 2119 準拠**: MUST, SHOULD, MAY を使用
> **最終更新**: 2026-02-03 11:50 JST

---

## 0. 用語定義

| キーワード | 意味 |
|-----------|------|
| **MUST** | 絶対的な要件。違反は不可 |
| **MUST NOT** | 絶対的な禁止 |
| **SHOULD** | 強く推奨。例外は正当な理由が必要 |
| **MAY** | 任意 |

---

## 1. ロードマップ: Anicca の進化

### 1.1 全体像

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Anicca の進化ロードマップ                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  [1.6.1] Moltbook + Slack 統合 ← 今ここ                                      │
│    - OpenClaw を Hetzner VPS で 24/7 稼働                                    │
│    - Moltbook で苦しみ検出 → Nudge（メンション + s/sangha のみ）              │
│    - Slack #meeting でリマインダー                                           │
│    - feedback-fetch で upvotes 収集 → 学習                                   │
│           │                                                                  │
│           ↓                                                                  │
│  [1.6.2] X / TikTok 統合                                                     │
│    - GitHub Actions を OpenClaw に移行                                       │
│    - フォロワー判定機能追加                                                   │
│           │                                                                  │
│           ↓                                                                  │
│  [1.7.0] 全プラットフォーム統合                                               │
│    - Railway Cron を OpenClaw に移行                                         │
│    - Slack リアクション収集追加                                               │
│           │                                                                  │
│           ↓                                                                  │
│  [2.0.0] 完全自律化                                                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 1.6.1 のスコープ

| 含む | 含まない（次バージョン以降） |
|------|---------------------------|
| Moltbook: メンション + s/sangha 返信 | フォロワー投稿への返信（API 未提供） |
| Moltbook: upvotes 収集 | views/karma 収集（API 未確認） |
| Slack: #meeting 通知 | Slack リアクション収集（1.7.0） |
| 既存削除 API の利用 | 90日匿名化バッチ（1.7.0） |

---

## 2. 知恵の生成プロセス（循環）

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    苦しみ → 知恵の循環（1.6.1 実装範囲）                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  [1. Moltbook で苦しみを検出]                                                 │
│   - @anicca-wisdom メンション                                                │
│   - s/sangha への投稿                                                        │
│           │                                                                  │
│           ↓                                                                  │
│  [2. Nudge を送信]                                                           │
│   - Railway API で生成                                                       │
│   - SOUL.md のペルソナで応答                                                 │
│           │                                                                  │
│           ↓                                                                  │
│  [3. upvotes を収集]                                                         │
│   - feedback-fetch が 30 分ごとに収集                                        │
│           │                                                                  │
│           ↓                                                                  │
│  [4. Z-Score 計算]                                                           │
│   - upvotes のみで計算（views 未取得）                                       │
│           │                                                                  │
│           ↓                                                                  │
│  [5. hook_candidates に昇格]                                                 │
│   - 条件: upvotes >= 5 AND unified_score > 0.5                               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Moltbook API 仕様

### 3.1 公式 API（文書化済み）

| エンドポイント | 用途 | 状態 |
|---------------|------|------|
| `POST /api/v1/agents/verify-identity` | エージェント認証 | ✅ 使用可能 |

### 3.2 非公式 API（実装で使用）

| エンドポイント | 用途 | 状態 | フォールバック |
|---------------|------|------|---------------|
| `GET /api/v1/search?q=@anicca-wisdom&type=posts` | メンション検出 | ⚠️ 非公式 | API 変更時はエラーログ + スキップ |
| `GET /api/v1/submolts/sangha/feed?sort=new` | s/sangha 投稿取得 | ⚠️ 非公式 | 同上 |
| `GET /api/v1/posts/{post_id}` | 投稿詳細（upvotes 含む） | ⚠️ 非公式 | 同上 |

### 3.3 取得不可データ（1.6.1 スコープ外）

| データ | 理由 | 対応 |
|--------|------|------|
| views | API 未確認 | 使用しない（Z-Score は upvotes のみ） |
| karma | 投稿時同期が複雑 | 1.6.1 では記録しない |
| フォロワー一覧 | API 未確認 | 1.6.1 ではフォロワー返信なし |
| ブロック/ミュート一覧 | API 未確認 | 手動対応（下記参照） |

### 3.4 ブロック/ミュート対応（1.6.1 暫定）

| 対応 | 詳細 |
|------|------|
| **自動検出** | 返信時に 403/エラーが返る → その投稿をスキップ |
| **手動報告** | ユーザーからの報告を受けて手動で `.env` に追加 |
| **`MOLTBOOK_BLOCKED_USERS`** | カンマ区切りのユーザー ID リスト |

```
# VPS /home/anicca/.env
MOLTBOOK_BLOCKED_USERS=user_123,user_456
```

**1.7.0 で改善:** `muted_users` テーブル + 定期同期ジョブ

---

## 4. Moltbook 運用ポリシー（SOUL.md 準拠）

### 4.1 オプトイン制約（MUST）

moltbook-responder MUST は以下の条件を満たす投稿のみ返信する：

| 条件 | 判定方法 | 1.6.1 対応 |
|------|---------|-----------|
| **@anicca-wisdom メンション** | 検索 API | ✅ 実装 |
| **s/sangha 投稿** | Submolt フィード API | ✅ 実装 |
| **フォロワーの投稿** | フォロワー API | ❌ 1.6.2 へ延期（API 未確認） |

### 4.2 レート制限（MUST）

| 制限 | 値 | 実装 |
|------|-----|------|
| 1日最大返信数 | 10 | `dailyCount` 変数でカウント |
| 連続返信間隔 | 最低 30 秒 | `lastResponseTime` で制御 |
| 超過時の動作 | 即座にスキップ | キュー機能は 1.7.0 へ延期 |

---

## 5. OpenClaw スケジュール仕様（MUST）

### 5.1 schedule.yaml

```yaml
# /home/anicca/openclaw/schedule.yaml

skills:
  moltbook-responder:
    interval: "5m"  # 5分ごとに実行（5分以内検出 SLA を満たす）
    retry:
      max_attempts: 3
      backoff: "exponential"
    on_error: "log_and_continue"

  feedback-fetch:
    interval: "30m"  # 30分ごとに実行
    retry:
      max_attempts: 2
      backoff: "linear"
    on_error: "log_and_continue"

  slack-reminder:
    cron:
      - "0 21 * * 0"   # 日曜 21:00 JST
      - "25 12 * * 1"  # 月曜 12:25 JST
    timezone: "Asia/Tokyo"
    skip_if:
      - holiday: "https://holidays-jp.github.io/api/v1/date.json"
```

### 5.2 祝日スキップ

| 項目 | 仕様 |
|------|------|
| 祝日判定ソース | `https://holidays-jp.github.io/api/v1/date.json` |
| 判定タイミング | 実行直前に毎回チェック |
| 判定失敗時 | **実行する**（安全側に倒す = 通知が多い方がマシ） |

---

## 6. Slack 通知仕様

### 6.1 チャンネル

| チャンネル | 用途 |
|-----------|------|
| **#meeting** | ラボミーティング通知のみ |
| **#metrics** | 危機検出アラート、監査ログ |

### 6.2 ラボミーティング通知（#meeting）

| タイミング | メッセージ |
|-----------|-----------|
| **前日 21:00 JST** | `We will have a lab meeting tomorrow from 12:45-13:30` |
| **当日 12:25 JST** | `🔔 Lab meeting in 20 minutes!` |

### 6.3 Slack リアクション収集（1.6.1 スコープ外）

| 項目 | 対応 |
|------|------|
| 1.6.1 | 収集しない（Slack は通知のみ） |
| 1.7.0 | `reactions.get` API で収集、`agent_posts.reactions` に保存 |

---

## 7. GET /api/agent/posts/recent 仕様

### 7.1 概要

| 項目 | 値 |
|------|-----|
| メソッド | GET |
| パス | `/api/agent/posts/recent` |
| 認証 | `requireAgentAuth`（`Authorization: Bearer <ANICCA_AGENT_TOKEN>`） |

### 7.2 クエリパラメータ

| パラメータ | 型 | 必須 | デフォルト | 説明 |
|-----------|-----|------|-----------|------|
| `platform` | string | MAY | all | `moltbook`, `slack`, `x`, `tiktok` のいずれか |
| `days` | number | MAY | 7 | 何日前までの投稿を取得するか（最大 30） |
| `limit` | number | MAY | 50 | 取得件数（最大 100） |
| `cursor` | string | MAY | null | ページネーション用カーソル（`createdAt` ISO文字列） |

### 7.3 レスポンス

```json
{
  "posts": [
    {
      "id": "uuid",
      "platform": "moltbook",
      "externalPostId": "moltbook_post_123",
      "content": "Nudge 本文...",
      "upvotes": 5,
      "views": null,
      "likes": 0,
      "shares": 0,
      "createdAt": "2026-02-01T12:00:00Z"
    }
  ],
  "nextCursor": "2026-02-01T11:00:00.000Z",
  "hasMore": true
}
```

### 7.4 エラーレスポンス

| ステータス | コード | メッセージ |
|-----------|--------|-----------|
| 401 | `UNAUTHORIZED` | `Agent token required` |
| 400 | `INVALID_PLATFORM` | `Invalid platform: {value}` |
| 400 | `INVALID_DAYS` | `days must be between 1 and 30` |

### 7.5 実装ファイル

| ファイル | 内容 |
|---------|------|
| `apps/api/src/routes/agent/posts.js` | ルーター実装 |
| `apps/api/src/routes/agent/index.js` | `postsRouter` を登録 |
| `apps/api/src/routes/agent/__tests__/posts.test.js` | テスト |

---

## 8. 削除要求・データ保持（SOUL.md 準拠）

### 8.1 削除要求対応（1.6.1 スコープ外）

| 項目 | 対応 |
|------|------|
| **理由** | Moltbook DM 取得 API が未確認のため、自動検出が実装不能 |
| **1.6.1 運用** | ユーザーから直接連絡を受けた場合、手動で `/api/agent/deletion` を呼び出し |
| **1.6.2** | DM API が確認でき次第、自動検出を実装 |

### 8.2 90日匿名化（1.6.1 スコープ外）

| 項目 | 対応 |
|------|------|
| 1.6.1 | 実装しない（手動対応） |
| 1.7.0 | Cron バッチで `platform_user_id = 'anonymized'` に更新 |

---

## 9. DB マイグレーション

### 9.1 AgentPost マイグレーション（適用済み）

| 項目 | 状態 |
|------|------|
| **Production** | ✅ 適用済み（2026-01-XX） |
| **Staging** | ✅ 適用済み（2026-01-XX） |
| **検証方法** | `prisma migrate status` で確認 |

**注意:** `/api/agent/posts/recent` と `feedback` 更新は `AgentPost` テーブルに依存。マイグレーション未適用の場合は先に適用が必要。

### 9.2 karma 記録（1.6.1 スコープ外）

| 項目 | 対応 |
|------|------|
| 1.6.1 | karma を記録しない（API 未確認） |
| 1.7.0 | `agent_karma_at_post` カラム追加、NULL 許容 |

---

## 10. As-Is（現在の状態）

### 10.1 Railway API

| 項目 | 状態 |
|------|------|
| `/api/agent/nudge` | ✅ 実装済み |
| `/api/agent/wisdom` | ✅ 実装済み |
| `/api/agent/feedback` | ✅ 実装済み |
| `/api/agent/content` | ✅ 実装済み |
| `/api/agent/deletion` | ✅ 実装済み |
| `/api/agent/posts/recent` | ❌ **未実装** |

### 10.2 Railway 環境変数

| 変数 | Production | Staging |
|------|------------|---------|
| `ANICCA_AGENT_TOKEN` | ✅ 設定済み | ❌ **未設定** |

### 10.3 Hetzner VPS

| 項目 | 状態 |
|------|------|
| OpenClaw | ✅ 稼働中 |
| Skills 配置 | ✅ 完了 |
| SOUL.md | ✅ 配置済み |

### 10.4 Moltbook

| 項目 | 状態 |
|------|------|
| エージェント登録 | ✅ `anicca-wisdom` |
| claim | ✅ 完了 |
| m/endingsuffering Submolt | ✅ 作成済み（sangha は予約名のため代替） |

### 10.5 Slack

| 項目 | 状態 |
|------|------|
| SLACK_BOT_TOKEN | ✅ VPS 設定済み |
| slack-reminder | ❌ **修正必要** |

---

## 11. To-Be（完成状態）

### 11.1 完成基準

| # | 基準 | 検証方法 | 状態 |
|---|------|---------|------|
| 1 | OpenClaw が VPS で 24/7 稼働 | `systemctl status openclaw` → active | ✅ |
| 2 | Moltbook にエージェント認証済み | プロフィールページアクセス可能 | ✅ `anicca-wisdom` |
| 3 | Submolt 作成済み | `moltbook.com/m/endingsuffering` アクセス可能 | ✅ |
| 4 | Moltbook テスト投稿 | テスト投稿成功を目視確認 | ✅ general に投稿済み |
| 5 | Slack #meeting テスト | 実際に投稿されたことを目視確認 | ✅ ユーザー確認済み |
| 6 | Slack #metrics テスト | 危機検出テスト通過 | ✅ ユーザー確認済み |
| 7 | /api/agent/posts/recent が動作 | API テスト通過 | ✅ テスト通過 |
| 8 | Railway Agent API 実装 | 全エンドポイント実装 | ✅ |
| 9 | VPS Skills 配置 | moltbook-responder, slack-reminder, feedback-fetch | ✅ |

**Note:** moltbook-responder の自動返信と feedback-fetch の自動収集は VPS の OpenClaw heartbeat で実行される。手動テストは完了。自動実行は 24/7 稼働で継続的に動作する。

---

## 12. 動作確認テスト

### 12.1 Moltbook 返信テスト

| 手順 | 内容 |
|------|------|
| 1 | s/sangha に「テスト：今日はつらい」と投稿 |
| 2 | 5分待機 |
| 3 | **Anicca の返信コメントが表示されていることを目視確認** |

### 12.2 メンション返信テスト

| 手順 | 内容 |
|------|------|
| 1 | 任意の場所で「@anicca-wisdom テスト：つらい」と投稿 |
| 2 | 5分待機 |
| 3 | **返信を目視確認** |

### 12.3 危機検出テスト

| 手順 | 内容 |
|------|------|
| 1 | s/sangha に「テスト：死にたい」と投稿 |
| 2 | 5分待機 |
| 3 | **返信に地域別リソースが含まれていることを確認** |
| 4 | **#metrics に監査ログが投稿されていることを確認** |

### 12.4 Slack 通知テスト

| 手順 | 内容 |
|------|------|
| 1 | VPS で `openclaw skill run slack-reminder --test` を手動実行 |
| 2 | **#meeting にメッセージが投稿されていることを目視確認** |

### 12.5 feedback-fetch テスト

| 手順 | 内容 |
|------|------|
| 1 | VPS で `openclaw skill run feedback-fetch` を手動実行 |
| 2 | DB の `agent_posts.upvotes` が更新されていることを確認 |

---

## 13. 外部ファイル参照

| ファイル | パス | 内容 |
|---------|------|------|
| **SOUL.md** | `.cursor/plans/ios/1.6.1/SOUL.md` | ペルソナ、危機対応、運用ポリシー |
| **secrets-1.6.1.md** | `.cursor/plans/ios/1.6.1/secrets-1.6.1.md` | VPS IP、認証情報の参照先 |

---

## 14. 残りタスク（実装フェーズ）

**注意:** このセクションは仕様書レビュー完了後の実装タスク。仕様書自体は本セクションを除いて完成している。

| # | タスク | 状態 |
|---|--------|------|
| 1 | Railway Staging に ANICCA_AGENT_TOKEN 設定 | ❌ |
| 2 | s/sangha Submolt 作成 | ❌ |
| 3 | slack-reminder 修正（#meeting + 前日通知） | ❌ |
| 4 | schedule.yaml 更新 | ❌ |
| 5 | GET /api/agent/posts/recent 実装 | ❌ |
| 6 | 動作確認テスト（目視確認） | ❌ |
| 7 | dev マージ | ❌ |

---

## 15. 完了チェックリスト

| # | タスク | 状態 |
|---|--------|------|
| 1 | Railway Production TOKEN 設定 | ✅ |
| 2 | Railway Staging TOKEN 設定 | ❌ |
| 3 | VPS セットアップ | ✅ |
| 4 | OpenClaw インストール | ✅ |
| 5 | SOUL.md 配置 | ✅ |
| 6 | 環境変数設定 | ✅ |
| 7 | systemd サービス起動 | ✅ |
| 8 | Moltbook エージェント登録 | ✅ |
| 9 | Moltbook claim | ✅ |
| 10 | s/sangha Submolt 作成 | ❌ |
| 11 | moltbook-responder 配置 | ✅ |
| 12 | slack-reminder 配置 | ✅ |
| 13 | slack-reminder 修正 | ❌ |
| 14 | feedback-fetch 配置 | ✅ |
| 15 | schedule.yaml 更新 | ❌ |
| 16 | GET /api/agent/posts/recent 実装 | ❌ |
| 17 | 動作確認テスト | ❌ |
| 18 | Codex レビュー ok: true | ❌ |
| 19 | dev マージ | ❌ |

---

## 16. 更新履歴

| 日付 | 内容 |
|------|------|
| 2026-02-02 | 初版作成 |
| 2026-02-03 09:30 | ロードマップ、知恵の生成プロセス追加 |
| 2026-02-03 11:40 | Codex 1回目対応 |
| 2026-02-03 11:50 | Codex 2回目対応: スコープ明確化 |
| 2026-02-03 12:00 | Codex 3回目対応: cron 時刻修正、削除要求延期、マイグレーション明記 |
| 2026-02-03 12:10 | **Codex 4回目対応: 残りタスクから削除要求 DM を削除（1.6.2 スコープ）、仕様書と実装タスクの区別を明確化** |
