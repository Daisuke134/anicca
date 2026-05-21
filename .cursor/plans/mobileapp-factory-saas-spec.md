# Spec: mobileapp-factory SaaS 製品化

## Context

| 項目 | 値 |
|------|-----|
| 製品名 | **Anicca Factory**（仮） |
| URL | aniccaai.com/factory |
| OSS | github.com/Daisuke134/mobileapp-factory |
| 既存実績 | FrostDip: 78.7M tokens → 58M（パッチ後）、App Store 提出まで全自動 |
| Source | Polsia ($49/月 + 20% rev share, 3,138社, $450k+ ARR) |
| Source | TinyClaw (MIT OSS, BYOKey, 3k stars, 収益ゼロ) |
| Source | ClawHost (OpenClaw PaaS, Polar.sh サブスク) |

---

## 1. ビジネスモデル

### OSS + SaaS ハイブリッド（Sentry/GitLab モデル）

| レイヤー | 公開範囲 | 収益 |
|---------|---------|------|
| **ralph.sh + レシピ（references/）** | MIT OSS | 無料 |
| **実行環境（認証管理、キュー、ダッシュボード）** | SaaS クローズド | 有料 |
| **テンプレート（prd.json 生成 + US-001 トレンドDB）** | SaaS クローズド | 有料 |

Source: [Sentry Business Model](https://blog.sentry.io/we-just-gave-500-000-dollars-to-open-source-maintainers/) — OSS コア + SaaS 実行環境
Source: [GitLab Open Core](https://about.gitlab.com/company/stewardship/) — コアは MIT、EE は有料

### 価格

| プラン | 月額 | 内容 | ターゲット |
|--------|------|------|-----------|
| **Starter** | $49/月 | 月2アプリ、基本カテゴリ | 個人開発者 |
| **Pro** | $149/月 | 月10アプリ、全カテゴリ、優先キュー | インディーハッカー |
| **Enterprise** | $499/月 | 無制限、専用インフラ、SLA | エージェンシー |

Source: Polsia $49 + 20%シェア ≈ 月$49-200。レベニューシェアは追跡困難 → 固定月額 + アプリ数制限が現実的。

### 収益予測

| 月 | ユーザー数 | MRR | 根拠 |
|----|-----------|-----|------|
| M1 | 10 (Starter) | $490 | ProductHunt + X |
| M3 | 30 Starter + 5 Pro | $2,215 | 口コミ + OSS stars |
| M6 | 50 Starter + 15 Pro + 2 Ent | $5,683 | ASO + コンテンツ |
| M12 | 100 Starter + 40 Pro + 5 Ent | $13,350 | — |

---

## 2. アーキテクチャ

### システム構成図

```
┌─────────────────────────────────────────────────────┐
│                    aniccaai.com/factory              │
│               Next.js 15 + Tailwind + shadcn        │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │ ランディング │  │ ダッシュボード │  │ Stripe Customer  │   │
│  │          │  │ (進捗表示)  │  │ Portal           │   │
│  └──────────┘  └──────────┘  └──────────────────┘   │
└───────────────────────┬─────────────────────────────┘
                        │ API Routes
┌───────────────────────┴─────────────────────────────┐
│                    API Layer                         │
│            Next.js API Routes + tRPC                 │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │ Auth     │  │ Billing  │  │ Job Queue        │   │
│  │ (Clerk)  │  │ (Stripe) │  │ (BullMQ + Redis) │   │
│  └──────────┘  └──────────┘  └──────────────────┘   │
└───────────────────────┬─────────────────────────────┘
                        │
┌───────────────────────┴─────────────────────────────┐
│                 Worker Layer                         │
│          Mac Mini クラスタ（ralph.sh 実行）             │
│                                                     │
│  ┌──────────────────────────────────────────────┐    │
│  │ Worker 1: ralph.sh (tenant-A, FrostDip)      │    │
│  │ Worker 2: ralph.sh (tenant-B, BreathCalm)    │    │
│  │ Worker N: ralph.sh (tenant-N, ...)           │    │
│  └──────────────────────────────────────────────┘    │
└───────────────────────┬─────────────────────────────┘
                        │
┌───────────────────────┴─────────────────────────────┐
│                    Data Layer                        │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │ PostgreSQL│  │ Redis    │  │ S3 (logs/assets) │   │
│  │ (Railway) │  │ (Railway)│  │                  │   │
│  └──────────┘  └──────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────┘
```

### マルチテナント分離

| レイヤー | 分離方式 | 詳細 |
|---------|---------|------|
| **ファイルシステム** | ディレクトリ分離 | `~/.config/mobileapp-builder/tenants/<tenant_id>/` |
| **ASC 認証** | テナントごとの API Key | テナントが自分の Apple Developer アカウントの API Key をアップロード |
| **iris session** | テナントごとの file cache | `ASC_WEB_SESSION_CACHE_BACKEND=file` + テナント別ディレクトリ |
| **Keychain** | 不使用 | file backend で完全回避 |
| **ログ** | テナント別 | `tenants/<id>/logs/` + S3 アーカイブ |
| **prd.json** | テナント別 | `tenants/<id>/apps/<app_slug>/prd.json` |

### キューシステム

```
Stripe Webhook (subscription.created)
  → BullMQ Job: { tenantId, plan, category? }
  → Worker picks up job
  → ralph.sh --tenant <id> --app <slug>
  → Progress updates → WebSocket → ダッシュボード
  → Completion → Slack/Email notification
```

---

## 3. ユーザーフロー（非技術者向け）

### オンボーディング（5分）

| Step | 画面 | アクション |
|------|------|-----------|
| 1 | サインアップ | Email + パスワード（Clerk） |
| 2 | プラン選択 | Stripe Checkout に遷移 |
| 3 | Apple Developer 連携 | ASC API Key アップロード（ガイド付き） |
| 4 | RevenueCat 連携 | RC API Key 入力（ガイド付き） |
| 5 | 完了 | ダッシュボードに遷移 |

### アプリ作成フロー

| Step | 画面 | アクション |
|------|------|-----------|
| 1 | 「アプリを作る」 | ボタンクリック |
| 2 | カテゴリ選択 | Health / Finance / Lifestyle / Productivity / Education |
| 3 | オプション設定 | サブスク価格（デフォルト $9.99/月）、ターゲット国 |
| 4 | 確認 | 「作成開始」→ ralph.sh キック |
| 5 | 進捗表示 | WebSocket でリアルタイム US 進捗 |
| 6 | 完了 | App Store リンク + build-report |

### 人間介入が必要な瞬間

| 介入 | 頻度 | 方法 |
|------|------|------|
| iris 2FA コード | 月1回 | Slack / ダッシュボード通知 → 6桁入力 |
| RC SK鍵 | アプリごと | ダッシュボードのガイドに従って入力 |
| CC OAuth | 年1回 | 管理者（俺ら）が対応 |

---

## 4. 技術スタック

| レイヤー | 技術 | 根拠 |
|---------|------|------|
| **フロントエンド** | Next.js 15 + Tailwind + shadcn/ui | Source: [Vercel](https://nextjs.org/) — SSR + API Routes 一体 |
| **認証** | Clerk | Source: [Clerk](https://clerk.com/) — Stripe 連携ビルトイン |
| **決済** | Stripe Billing | Source: [Stripe](https://stripe.com/billing) — サブスク + メーター課金 |
| **キュー** | BullMQ + Redis | Source: [BullMQ](https://docs.bullmq.io/) — Node.js 最適、Railway Redis 対応 |
| **DB** | PostgreSQL (Prisma) | 既存 Railway インフラ流用 |
| **リアルタイム** | WebSocket (Socket.io) | 進捗表示用 |
| **ストレージ** | S3 互換 (Cloudflare R2) | ログ + スクショ保管 |
| **デプロイ** | Vercel (Web) + Mac Mini (Workers) | Web は Vercel、Worker は既存 Mac Mini |
| **モニタリング** | Sentry | エラー追跡 |

---

## 5. Stripe 統合詳細

### Webhook フロー

```
customer.subscription.created
  → テナント作成 (DB)
  → ウェルカムメール
  → ダッシュボードアクセス有効化

customer.subscription.updated
  → プラン変更反映（アプリ上限更新）

customer.subscription.deleted
  → 新規アプリ作成停止
  → 既存アプリは30日間維持

invoice.payment_failed
  → 3回リトライ後 → サブスク停止

checkout.session.completed
  → Clerk ユーザーと Stripe Customer 紐付け
```

### メーター課金（将来）

```typescript
// アプリ作成完了時に使用量記録
await stripe.subscriptionItems.createUsageRecord(
  subscriptionItemId,
  { quantity: 1, timestamp: Date.now() }
)
```

---

## 6. DB スキーマ（追加テーブル）

```prisma
model Tenant {
  id            String   @id @default(cuid())
  clerkUserId   String   @unique
  stripeCustomerId String @unique
  plan          Plan     @default(STARTER)
  appsThisMonth Int      @default(0)
  maxApps       Int      @default(2)
  createdAt     DateTime @default(now())
  apps          App[]
  ascApiKey     String?  // encrypted
  rcApiKey      String?  // encrypted
}

model App {
  id         String    @id @default(cuid())
  tenantId   String
  tenant     Tenant    @relation(fields: [tenantId], references: [id])
  slug       String
  name       String
  category   String
  status     AppStatus @default(QUEUED)
  prdJson    Json?
  appStoreId String?
  createdAt  DateTime  @default(now())
  updatedAt  DateTime  @updatedAt
  logs       Log[]
}

model Log {
  id        String   @id @default(cuid())
  appId     String
  app       App      @relation(fields: [appId], references: [id])
  usId      String   // e.g. "US-001"
  status    String   // "running", "passed", "failed", "blocked"
  tokens    BigInt?
  details   String?
  createdAt DateTime @default(now())
}

enum Plan {
  STARTER
  PRO
  ENTERPRISE
}

enum AppStatus {
  QUEUED
  RUNNING
  COMPLETED
  FAILED
  BLOCKED
}
```

---

## 7. ランディングページ構成（aniccaai.com/factory）

| セクション | 内容 |
|-----------|------|
| **Hero** | 「AIがApp Storeアプリを自動生成。トレンド分析 → 設計 → 実装 → 提出。あなたは待つだけ。」 |
| **How it works** | 3ステップ図（Connect → Choose → Ship） |
| **Live Demo** | FrostDip の build-report をインタラクティブ表示 |
| **Pricing** | 3プラン表示 |
| **FAQ** | Apple Developer アカウント必要？→ はい。コーディング必要？→ いいえ |
| **Social Proof** | FrostDip, BreathCalm の実績（App Store リンク） |
| **CTA** | 「今すぐ始める」→ Stripe Checkout |

---

## 8. OSS 戦略

### 公開するもの

| ファイル | 理由 |
|---------|------|
| `ralph.sh` | コアオーケストレーター。MIT ライセンス |
| `references/us-*.md` | レシピ（US 手順書）。コミュニティ貢献可能 |
| `validate.sh` | 品質ゲート |
| `CLAUDE.md` テンプレート | CC 指示書 |
| `prd.json` テンプレート | PRD スキーマ |

### 公開しないもの

| 要素 | 理由 |
|------|------|
| マルチテナント管理 | SaaS 差別化要因 |
| Stripe 統合 | ビジネスロジック |
| iris auto-2FA（Slack連携） | 運用ノウハウ |
| トレンドDB + アイデア生成 AI | 競争優位 |
| ダッシュボード UI | SaaS 差別化 |

### コミュニティ育成

| 施策 | 詳細 |
|------|------|
| GitHub Discussions | バグ報告、レシピ共有 |
| `references/` への PR | 新カテゴリのレシピ追加 |
| テンプレートマーケット | コミュニティ製 prd.json テンプレート |
| Discord | ユーザーコミュニティ |

---

## 9. MVP スコープ（Phase 1 — 4週間）

| 週 | タスク | 成果物 |
|----|--------|--------|
| W1 | ランディングページ + Stripe Checkout | aniccaai.com/factory live |
| W2 | Clerk 認証 + テナント DB + ダッシュボード骨組み | ログイン → ダッシュボード |
| W3 | BullMQ キュー + ralph.sh テナント対応 | アプリ作成フロー E2E |
| W4 | WebSocket 進捗 + build-report 表示 + ベータテスト | MVP 完成 |

### MVP 後（Phase 2 — 4週間）

| 週 | タスク |
|----|--------|
| W5-6 | OSS 公開（GitHub + ProductHunt） |
| W7-8 | メーター課金 + Enterprise プラン + SLA |

---

## 10. リスク

| # | リスク | 深刻度 | 対策 |
|---|--------|--------|------|
| 1 | Apple Developer アカウント共有の ToS 違反 | HIGH | テナントが自分のアカウントを使う。俺らはツールだけ提供 |
| 2 | CC OAuth トークン共有 | HIGH | テナントごとに CC セッション。Anthropic Max プランの利用規約確認必要 |
| 3 | Mac Mini のスケーラビリティ | MEDIUM | 1台で同時 2-3 アプリ。スケール時は Mac Mini クラスタ or Mac Stadium |
| 4 | Anthropic API コスト | LOW | Max プラン $200/月固定。5h枠で1アプリ完了 |
| 5 | App Store リジェクト率 | MEDIUM | greenlight + apple-appstore-reviewer で事前チェック |
| 6 | テンプレートアプリの品質 | MEDIUM | US-006-R（コードレビュー）+ US-007（E2E テスト）で担保 |

---

## 11. 成功指標

| 指標 | M1 | M3 | M6 | M12 |
|------|-----|-----|-----|------|
| ユーザー数 | 10 | 35 | 67 | 145 |
| MRR | $490 | $2,215 | $5,683 | $13,350 |
| アプリ提出数 | 15 | 60 | 200 | 600 |
| App Store 承認率 | 80% | 90% | 95% | 95%+ |
| OSS stars | 100 | 500 | 2,000 | 5,000 |
| チャーン率 | 15% | 10% | 8% | 5% |

---

## 変更対象ファイル一覧（MVP）

| # | ファイル | 内容 |
|---|---------|------|
| 1 | `apps/factory/` | Next.js 15 アプリ（新規） |
| 2 | `apps/factory/prisma/schema.prisma` | Tenant, App, Log テーブル |
| 3 | `apps/factory/app/page.tsx` | ランディングページ |
| 4 | `apps/factory/app/dashboard/` | ダッシュボード |
| 5 | `apps/factory/app/api/webhooks/stripe/` | Stripe Webhook |
| 6 | `apps/factory/app/api/jobs/` | BullMQ ジョブ管理 |
| 7 | `.claude/skills/mobileapp-builder/ralph.sh` | テナント対応（`--tenant` フラグ） |
| 8 | `github.com/Daisuke134/mobileapp-factory` | OSS リポジトリ（新規） |
