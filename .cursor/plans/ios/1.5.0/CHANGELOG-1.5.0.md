# Anicca 1.5.0 — Cross-User Learning

Release Date: 2026-01-29

---

## 新機能 (New Features)

### Cross-User Learning（ユーザー横断学習）
- ユーザーが選択した問題タイプに基づき、4つのユーザータイプ（T1完璧主義 / T2比較傾向 / T3衝動型 / T4不安型）に自動分類
- 同じタイプのユーザー間でフック効果データを共有し、Thompson Sampling で最適なフックを選択
- `UserTypeSegment` テーブルと `WisdomEntry` テーブルをバックエンドに追加（Track A）

### Learning Loop（学習ループ）
- Thompson Sampling（80% exploit / 20% explore）による Wisdom ベースのフック選択を実装
- Nudge の反応データを集約し、ユーザータイプ別にフック効果を継続的に学習（Track C）

### TikTok AI Agent
- AI エージェントによる TikTok コンテンツ自動生成・投稿機能を全実装（Track B）
- エージェント推論ログを DB に保存し、意思決定の透明性を確保
- スケジュール投稿機能 -- エージェントが最適な投稿時間（WHEN）を決定
- Blotato API 連携による自動投稿

### Daily Metrics Automation（日次メトリクス自動化）
- GitHub Actions による TikTok メトリクス自動収集ワークフローを追加
- App Store Connect 売上データ + RevenueCat サブスクリプションデータの自動取得

### Nudge 強化
- 1日あたり5回のNudge頻度に引き上げ + LLM グラウンディング改善
- 交互ロジックの削除によるシンプル化
- 未読 Nudge を示す青ドット UI を追加

### Time Sensitive 通知
- iOS の Time Sensitive（即時配信）通知を有効化
- ScreenTime Extension を完全削除（不要機能のクリーンアップ）

---

## 改善 (Improvements)

| 項目 | 内容 |
|------|------|
| TikTok Agent ロバスト化 | リトライ・エラーハンドリング強化、Blotato API 認証/ペイロード修正 |
| 画像生成モデル | デフォルトモデルを `nano_banana` に変更（高品質化） |
| 投稿時間制御 | `posting_time` を HH:MM 形式に統一、日付はコード側で固定 |
| トーン名修正 | `warm` → `gentle` に統一（DB 制約との整合性） |
| Nudge 間隔制御 | 60分間隔違反をログ警告のみに変更（reject → warn） |
| オンボーディング | テキストを現在のプロダクトに合わせて更新 |

---

## バグ修正 (Bug Fixes)

| 項目 | 内容 |
|------|------|
| P2003 Foreign Key エラー | `TiktokPost` 作成時の FK 制約違反を防止するバリデーション追加 |
| PROXY_BASE_URL | 未設定時に throw せず warn で継続するフォールバック実装 |
| Prisma Client import | パスを `generated` ディレクトリに修正 |
| Trust Proxy | Railway リバースプロキシ用の `trust proxy` 設定を追加 |
| メトリクス収集 | ASC gzip レポートの展開処理追加、RevenueCat API フィールド名修正 |
| コードレビュー指摘 | CRITICAL 3件 + HIGH 6件 + MEDIUM 3件を一括修正 |

---

## インフラ (Infrastructure)

| 項目 | 内容 |
|------|------|
| Prisma Migration | `startスクリプト` に `prisma migrate deploy` を追加（本番DB自動マイグレーション） |
| `TiktokPost` スキーマ | `scheduled_at` カラムを追加 |
| GitHub Actions | Daily Metrics ワークフロー追加（`ASC_VENDOR_NUMBER` 環境変数対応） |
| Production DB | Prisma migration baseline を適用し、本番DBとの整合性を確保 |

---

## 技術的な変更の概要

```
Track A: Cross-User Learning バックエンド
  └─ UserTypeSegment, WisdomEntry テーブル追加
  └─ ユーザータイプ自動分類ロジック

Track B: TikTok AI Agent
  └─ コンテンツ生成 → 画像生成 → Blotato 投稿
  └─ スケジュール投稿、推論ログ保存

Track C: Learning Loop
  └─ Thompson Sampling (80/20) によるフック選択
  └─ Wisdom データの集約・活用

Track D: Production Stability
  └─ P2003 FK 修正、PROXY_BASE_URL 耐障害性
  └─ Prisma migration baseline

Track E: Daily Metrics Automation
  └─ GitHub Actions cron ワークフロー
  └─ ASC + RevenueCat データ自動収集
```
