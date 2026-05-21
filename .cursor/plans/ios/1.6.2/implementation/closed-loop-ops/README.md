# Closed-Loop Ops Layer — サブフォルダ構成

> **元ファイル**: `../closed-loop-ops.md`（3670行）を論理グループに分割
> **最終更新**: 2026-02-08

---

## ファイル一覧

| # | ファイル | 元Section | 内容 | 行数(目安) |
|---|---------|-----------|------|-----------|
| 1 | `01-overview-adr.md` | §0-1 | Executive Summary + ADR-004〜007 | ~70 |
| 2 | `02-data-layer.md` | §2-5 | DB Schema (Prisma) + Migration SQL + Seed Data | ~370 |
| 3 | `03-api-services.md` | §6 | コアサービス群 (Proposal, CapGate, Policy, EventEmitter, Trigger, Reaction, StaleRecovery, Heartbeat) | ~660 |
| 4 | `04-api-routes-security.md` | §7, 9, 10 | API Routes + Kill Switch + Auth Middleware | ~390 |
| 5 | `05-step-executors.md` | §15-16 | 12 Step Executors + SAFE-T + Step-to-Step Data Passing | ~1150 |
| 6 | `06-slack-approval.md` | §17 | Slack Interactive 承認フロー (Block Kit + Handler) | ~260 |
| 7 | `07-vps-worker-migration.md` | §8, 18 | VPS Worker + Cron統合 + 既存Skill移行パス | ~340 |
| 8 | `08-event-trigger-system.md` | §19-20 | delay_min修正 + emitEvent→Reaction Matrix接続 | ~100 |
| 9 | `09-infrastructure.md` | §22-24 | 監視・アラート + insightPromoter + Staging→Production移行 | ~300 |
| 10 | `10-test-matrix-checklist.md` | §11-14, 21, 25-27 | テストマトリックス(T1-T67) + テスト基盤 + チェックリスト + 境界 + ファイル構成 | ~520 |
| 11 | `11-agent-evaluation.md` | **NEW** | エージェント性能評価テーブル（質問→期待→実際→PASS/FAIL→理由） | ~new |
| 12 | `12-e2e-integration-tests.md` | **NEW** | E2E統合テスト マトリックス（スキル間ループ検証） | ~new |
| 13 | `13-gui-prerequisites.md` | **NEW** | GUI必須タスク（**BLOCKING** — 実装前にユーザーが完了必須） | ~new |

---

## 読む順序

### パターン A: 全体概要

| 順番 | ファイル | 読む範囲 | 所要時間 |
|------|---------|---------|---------|
| 1 | `01-overview-adr.md` | 全体 | 2分 |
| 2 | `10-test-matrix-checklist.md` | チェックリスト部分 | 3分 |
| 3 | `13-gui-prerequisites.md` | P0タスク | 2分 |

### パターン B: 特定コンポーネント実装

| やりたいこと | 読むファイル |
|-------------|------------|
| DB セットアップ | `02-data-layer.md` |
| Proposal Service 実装 | `03-api-services.md` |
| Step Executor 追加 | `05-step-executors.md` |
| Slack承認フロー | `06-slack-approval.md` |
| VPS Worker 設定 | `07-vps-worker-migration.md` |
| テスト作成 | `10-test-matrix-checklist.md` → テスト基盤セクション |

### パターン C: TDDで実装

| ステップ | 参照先 |
|---------|-------|
| 1. テストマトリックス確認 | `10-test-matrix-checklist.md` (T1〜T67) |
| 2. テスト基盤セットアップ | `10-test-matrix-checklist.md` (Vitest + Prisma Mock) |
| 3. RED: テスト作成 | テスト名とカバー対象がマトリックスに記載済み |
| 4. GREEN: 実装 | 各コンポーネントファイル参照 |
| 5. GUI前提タスク確認 | `13-gui-prerequisites.md` (P0は実装ブロッカー) |

---

## 関係図

```
13-gui-prerequisites ──(BLOCKING)──→ 実装開始
                                        │
                                        ▼
01-overview-adr ──→ 02-data-layer ──→ 03-api-services
                                        │
                    ┌───────────────────┼───────────────────┐
                    ▼                   ▼                   ▼
          04-api-routes-security  05-step-executors  06-slack-approval
                    │                   │
                    ▼                   ▼
          07-vps-worker-migration  08-event-trigger-system
                    │
                    ▼
          09-infrastructure
                    │
                    ▼
          10-test-matrix-checklist ←── 11-agent-evaluation
                                  ←── 12-e2e-integration-tests
```

---

## 元ファイルとの関係

`../closed-loop-ops.md` は分割元のマスターファイルとして残す（アーカイブ）。
実装時はこのサブフォルダ内のファイルを参照する。

## 関連サブフォルダ

| フォルダ | 関係 |
|---------|------|
| `../trend-hunter/` | trend-hunterの出力が `ops_events` に emit → 本フォルダのトリガー/リアクション/ステップ実行に繋がる |
