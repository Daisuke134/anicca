# API Key & Secret 管理

## 設定先パス（絶対パスで示す）

| 場所 | パス |
|------|------|
| **ローカル（プロジェクト .env）** | **`/Users/cbns03/Downloads/anicca-project/.env`**（プロジェクトルート。ここに実値を書く） |
| **VPS（OpenClaw が読む .env）** | **`/home/anicca/.openclaw/.env`**（同期先。ローカルで値を入れてからここに反映する） |

相対パスで言うとローカルは **`.env`**（リポジトリルート）。

---

## admin 系で詰まる「実値必須」3項目

**ローカル .env で値が `None` や未設定だと、同期しても VPS 側も空のまま。admin 系（heartbeat / app-nudge-sender / autonomy-check 等）がブロックされる。**

以下3つは **必ずローカル .env に実値を入れること。** 入れるファイルは上記「設定先パス」のローカル .env。

| 変数名 | 用途 | 取得元・例 |
|--------|------|------------|
| `API_BASE_URL` | Anicca API のベースURL。admin job や ops/heartbeat が叩く先。 | Railway Production: `https://anicca-proxy-production.up.railway.app` |
| `INTERNAL_API_TOKEN` | admin 系 API の Bearer 認証。 | Railway の Variables の `INTERNAL_API_TOKEN` と同じ値。GHA の `API_AUTH_TOKEN` と同一。 |
| `NUDGE_ALPHA_USER_ID` | app-nudge-sender の alpha ルーティング先。未設定だと `NUDGE_ALPHA_USER_ID is required` でブロック。 | iOS 端末の Device ID（E2E 通知デバッグ画面などで確認できる UUID）。 |

---

## 原則: 全シークレットは `.env` で一元管理

| ルール | 詳細 |
|--------|------|
| **シークレット保管場所** | プロジェクトルート `.env`（gitignored）。パスは上記「設定先パス」参照。 |
| **VPS** | `/home/anicca/.openclaw/.env`（OpenClaw）。`/home/anicca/.env` は systemd 用。 |
| **Railway** | Railway Dashboard で設定済み |
| **GitHub Actions** | `gh secret set` で CLI 登録 |
| **このファイルに実値を書くな** | 変数名と用途のみ記載。値は `.env` を見ろ |

## GitHub Actions Secrets（Daisuke134/anicca.ai）

| Secret Name | 用途 |
|-------------|------|
| `OPENAI_API_KEY` | LLM（Nudge生成、TikTokエージェント、Vision） |
| `BLOTATO_API_KEY` | TikTok投稿（Blotato API） |
| `FAL_API_KEY` | 画像生成（Fal.ai） |
| `EXA_API_KEY` | トレンド検索（Exa） |
| `APIFY_API_TOKEN` | TikTokメトリクス取得（Apify） |
| `API_AUTH_TOKEN` | Railway API 認証（= Railway の INTERNAL_API_TOKEN） |
| `API_BASE_URL` | Railway Production URL |
| `APPLE_APP_SPECIFIC_PASSWORD` | App Store提出 |
| `APPLE_ID` | App Store提出 |
| `APPLE_TEAM_ID` | App Store提出 |
| `ASC_KEY_ID` | ASC API Key ID |
| `ASC_ISSUER_ID` | ASC API Issuer ID |
| `ASC_PRIVATE_KEY` | ASC API .p8 秘密鍵 |
| `ASC_VENDOR_NUMBER` | ASC Sales Reports 用ベンダー番号 |
| `REVENUECAT_V2_SECRET_KEY` | RevenueCat API v2 シークレットキー |
| `SLACK_METRICS_WEBHOOK_URL` | Slack Webhook URL |

## GitHub Actions Variables

| Variable Name | 用途 |
|---------------|------|
| `BLOTATO_ACCOUNT_ID_EN` | TikTok EN カード投稿 |
| `BLOTATO_ACCOUNT_ID_JA` | TikTok JA カード投稿 |

## Railway 環境変数（主要）

| 変数名 | 用途 |
|--------|------|
| `DATABASE_URL` | PostgreSQL接続 |
| `OPENAI_API_KEY` | Nudge生成 |
| `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` | 補助サービス |
| `REVENUECAT_*` | 決済連携 |
| `APNS_*` | プッシュ通知 |
| `INTERNAL_API_TOKEN` | API認証（= GHA の `API_AUTH_TOKEN`） |
| `ANICCA_AGENT_TOKEN` | Agent認証 |

## Railway URL

| 環境 | URL |
|------|-----|
| Staging | `anicca-proxy-staging.up.railway.app` |
| Production | `anicca-proxy-production.up.railway.app` |

**注意**: `anicca-api-production` ではない。`anicca-proxy-production` が正しいURL。

## Railway DB Proxy URL

ローカルからRailway DBに接続する場合（Prismaマイグレーション等）:
**詳細**: `apps/api/.env.proxy` に保存済み（gitignored）

## Railway トラブルシューティング

| 問題 | 原因 | 解決 |
|------|------|------|
| **P3005: database schema not empty** | 既存DBにPrismaベースラインがない | `DATABASE_URL="..." npx prisma migrate resolve --applied <migration>` |
| **pushしたのにRailwayが古いまま** | キャッシュまたはデプロイ未トリガー | `git commit --allow-empty -m "trigger redeploy" && git push` |
| **502 Bad Gateway** | デプロイ中 or サーバークラッシュ | Railway Dashboard でログ確認 |
| **railway run が internal hostに接続** | 内部URLはRailway内からのみアクセス可 | Proxy URLを使う |

## 本番デプロイ前チェックリスト

| # | 項目 | コマンド |
|---|------|---------|
| 1 | GHA secrets確認 | `gh secret list -R Daisuke134/anicca.ai` |
| 2 | API_BASE_URL確認 | `anicca-proxy-production` になっているか |
| 3 | Prismaマイグレーション | 既存DBなら `migrate resolve --applied` |

## VPS (Hetzner) — OpenClaw 稼働環境

| 項目 | 値 |
|------|-----|
| **サーバー名** | `ubuntu-4gb-nbg1-7` |
| **IPv4** | `46.225.70.241` |
| **SSH コマンド** | `ssh anicca@46.225.70.241`（または `root@`） |
| **OpenClaw バージョン** | 2026.2.3-1 |
| **OpenClaw 状態** | 稼働中（systemd user service + lingering） |
| **Profile** | `full`（全ツール有効） |

### VPS 環境変数（/home/anicca/.env）

| 変数名 | 用途 |
|--------|------|
| `OPENAI_API_KEY` | OpenClaw GPT-4o |
| `REVENUECAT_V2_SECRET_KEY` | メトリクス取得 |
| `MIXPANEL_API_SECRET` | メトリクス取得 |
| `MIXPANEL_PROJECT_ID` | Mixpanel |
| `SLACK_BOT_TOKEN` | Slack 接続 |
| `SLACK_APP_TOKEN` | Slack Socket Mode |
| `ASC_KEY_ID` | App Store Connect |
| `ASC_ISSUER_ID` | App Store Connect |
| `EXA_API_KEY` | Web検索（Exa） |
| `BRAVE_API_KEY` | Brave Search |
| `X_CLIENT_ID` | X API |
| `X_CLIENT_SECRET` | X API |
| `X_BEARER_TOKEN` | X API |
| `X_ACCOUNT_ID` | X API |

### VPS 確認コマンド

```bash
# SSH 接続
ssh anicca@46.225.70.241

# Gateway 状態確認（anicca ユーザーで実行）
export XDG_RUNTIME_DIR=/run/user/$(id -u)
systemctl --user status openclaw-gateway

# Gateway 再起動（設定変更後のみ）
systemctl --user restart openclaw-gateway

# ログ確認
journalctl --user -u openclaw-gateway -n 50
```

---

## OpenClaw / Slack 設定

| 項目 | 値 |
|------|-----|
| **Gateway Port** | 18789 |
| **Config** | `~/.openclaw/openclaw.json` |
| **Cron Jobs** | `~/.openclaw/cron/jobs.json` |
| **Logs** | `~/.openclaw/logs/` |
| **groupPolicy** | `open`（全チャンネル許可） |

### Slack チャンネル ID

| チャンネル | ID |
|-----------|-----|
| #metrics | C091G3PKHL2 |
| #ai | C08RZ98SBUL |
| #meeting | C03HRM5V5PD |

---

## Blotato アカウント

| プラットフォーム | アカウント | Blotato Account ID | 用途 |
|-----------------|-----------|-------------------|------|
| TikTok EN（動画） | @anicca.self | 28152 | AI動画投稿 |
| TikTok EN（カード） | @anicca122 | 29171 | NudgeCard投稿 |
| TikTok JA（カード） | @anicca.jp2 | 29172 | NudgeCard投稿 |

## 新しい Secret の登録方法（エージェント向け）

```bash
# GitHub Actions
echo "VALUE" | gh secret set SECRET_NAME --repo Daisuke134/anicca.ai

# 確認
gh secret list --repo Daisuke134/anicca.ai
```

## 1.6.2 Credentials

### X (Twitter) API — OAuth 2.0 PKCE

| 項目 | 保管場所 |
|------|---------|
| `X_CLIENT_ID` | `.env` / VPS `.env` |
| `X_CLIENT_SECRET` | `.env` / VPS `.env` |
| `X_BEARER_TOKEN` | `.env` / VPS `.env` |
| `X_ACCOUNT_ID` | `.env` / VPS `.env` |
| X Handle | @aniccaen |
| Callback URL | `https://anicca-proxy-staging.up.railway.app/auth/x/callback` |

### Trend Hunter データソース

| 項目 | 保管場所 |
|------|---------|
| `TWITTERAPI_KEY` | `.env` / VPS `.env` |
| `REDDIT_SESSION` | `.env` / VPS `~/.openclaw/.env`（Cookie 認証、reddit-cli 用） |

### 保存先まとめ

| 変数 | ローカル `.env` | VPS `~/.env` | Railway Staging | Railway Production |
|------|:---:|:---:|:---:|:---:|
| `OPENAI_API_KEY` | ✅ | ✅ | ✅ | ✅ |
| `BLOTATO_API_KEY` | ✅ | ✅ | — | — |
| `SLACK_BOT_TOKEN` | ✅ | ✅ | — | — |
| `SLACK_APP_TOKEN` | ✅ | ✅ | — | — |
| `SLACK_WEBHOOK_AGENTS` | ✅ | ✅ | — | — |
| `X_CLIENT_ID` | ✅ | ✅ | — | — |
| `X_CLIENT_SECRET` | ✅ | ✅ | — | — |
| `X_BEARER_TOKEN` | ✅ | ✅ | — | — |
| `X_ACCOUNT_ID` | ✅ | ✅ | — | — |
| `TWITTERAPI_KEY` | ✅ | ✅ | — | — |
| `REDDIT_SESSION` | ✅ | ✅ | — | — |
| `ANICCA_AGENT_TOKEN` | ✅ | ✅ | ✅ | ✅（本番移行時） |
| `BRAVE_API_KEY` | ✅ | ✅ | — | — |
| `EXA_API_KEY` | ✅ | ✅ | — | — |

## PostHog

| 項目 | 値 | 用途 |
|------|-----|------|
| `POSTHOG_PERSONAL_API_KEY` | `.claude.json` MCP 設定に保存（`phx_...`） | API 経由のデータ取得・feature flag 操作・Experiment 結果取得 |
| `POSTHOG_PROJECT_ID` | `327882` | 全 API エンドポイントで使用 |
| `POSTHOG_SDK_KEY` (public) | `phc_Mw4K3aByYDRuAlfe55u5OYJrTwTcwhPextZjOw8z2nw` | iOS SDK 初期化（AppDelegate.swift L32）、イベント送信。Public key なのでコードに埋め込み OK |
| API Host | `https://us.posthog.com` (管理API) / `https://us.i.posthog.com` (SDK) | US リージョン |
| MCP Server | `.claude.json` → `mcpServers.posthog` | Claude Code から PostHog API を MCP 経由で操作 |
| Feature Flag ID | `628062` | `paywall-ab-test` の ID |
| Experiment ID | `364239` | "Paywall A/B Test v1" の ID |

### PostHog 保存先まとめ

| 変数 | `.claude.json` MCP | Mac Mini `.env` | OpenClaw jobs |
|------|:---:|:---:|:---:|
| `POSTHOG_PERSONAL_API_KEY` | ✅ | ⬜（Cron 設定時に追加） | ⬜（Cron 設定時に追加） |
| `POSTHOG_PROJECT_ID` | ✅ | — | — |
| `POSTHOG_SDK_KEY` | — (iOS コード内) | — | — |

---

**ルール:**
- シークレットの実値は `.env` ファイルのみ
- このファイルには変数名と保管場所だけ記載
- `gh secret set` で GitHub Actions に登録
- VPS は `/home/anicca/.env` にコピー
