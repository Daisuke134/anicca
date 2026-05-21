# Backend Refactor — 残作業 & 次フェーズ計画

**日付**: 2026-01-29
**ステータス**: 計画中

---

## 現在の状態

### 完了済み（feature/backend-cleanup ブランチ、マージ待ち）

| Phase | 内容 | コミット数 | 状態 |
|-------|------|-----------|------|
| Phase 1 | Backend クリーンアップ & DB明確化 | 6 | ✅ 完了・GATE 3 PASS |
| Phase 2 | プロジェクトルート整理 | 7 | ✅ 完了・GATE 3 PASS |

**Spec**: `.cursor/plans/ios/1.5.0/backend-cleanup-and-db-clarity-spec.md`
**ワークツリー**: `/Users/cbns03/Downloads/anicca-backend-cleanup`
**テスト**: 41/41 PASS、AC 31/31 PASS

---

## Phase 3: ルート設定ファイル整理（feature/backend-cleanup で追加実施）

### 削除対象

| ファイル | 理由 | 確認済み |
|---------|------|---------|
| `package.json` | `jsonrepair` 1件のみ、どこからも参照なし。本体は `apps/api/package.json` | ✅ |
| `package-lock.json` | 上記のロックファイル | ✅ |
| `.eslintrc.json` | TypeScript ESLint設定だがどこからも参照なし | ✅ |
| `playwright-config.json` | Playwright MCP からも参照なし。MCP は独自設定で動作 | ✅ |

### 残すもの

| ファイル | 理由 |
|---------|------|
| `.railwayignore` | Railway デプロイで必須（iOS/docs/node_modules 除外） |
| `netlify.toml` | Netlify デプロイで必須（ルートに1つだけ、apps/landing/ を base 指定） |
| `.gitignore` | 当然必要 |

### .gitignore に追加すべきもの

| パターン | 理由 |
|---------|------|
| `dpo/` | 研究フォルダ（888MB、Python ML/DPO）。git 追跡しない |

### dpo/ フォルダ取り込み

devブランチに `dpo/` が追加された。ワークツリーに取り込んでマージコンフリクトを防ぐ。
ただし `.gitignore` に追加して git 追跡しない。リファクタ対象外（研究データ）。

---

## 将来の追加リファクタ候補（別 Spec で対応）

### 優先度: 高

| 項目 | 詳細 | 影響 |
|------|------|------|
| Stripe 課金コード削除 | Desktop 課金の残骸。`apps/api/src/routes/billing/` | 影響範囲大、要分析 |
| Dead Prisma モデル分析 | `RealtimeUsageDaily`, `MobileVoipToken` 等 | raw SQL 参照あり、要調査 |
| 未使用 npm パッケージ削除 | `@composio/core`, `@composio/openai`, `@vercel/mcp-adapter` | Agent系、要影響調査 |

### 優先度: 中

| 項目 | 詳細 |
|------|------|
| `docs/` 全体クリーンアップ | `docs/12/`, `docs/ScreenBreak/`, `docs/naistQmd/` — stale ファイル多数 |
| `.kombai/` 整理 | ツール固有リソース、必要性確認 |
| `.playwright-mcp/` 整理 | スクショのみ。必要なら `assets/` に移動 |

### 優先度: 低

| 項目 | 詳細 |
|------|------|
| `SensorAccessState` Prisma モデル | DORMANT だが将来使う可能性あり |
| `daily-apps/` 整理 | Daily Dhamma 関連。アクティブ度確認 |

---

## 実行手順（Phase 3）

```bash
# ワークツリーで作業（feature/backend-cleanup）
cd /Users/cbns03/Downloads/anicca-backend-cleanup

# 1. devから dpo/ を取り込み（マージコンフリクト防止）
git fetch origin dev
git merge origin/dev --no-edit

# 2. .gitignore に dpo/ 追加
echo "# Research/thesis project" >> .gitignore
echo "dpo/" >> .gitignore

# 3. 不要ルート設定ファイル削除
git rm package.json package-lock.json .eslintrc.json playwright-config.json

# 4. コミット
git add .gitignore
git commit -m "chore: remove orphaned root configs, add dpo/ to .gitignore"

# 5. テスト
cd apps/api && npm test

# 6. プッシュ
git push origin feature/backend-cleanup
```

---

## マージ前チェックリスト

| # | 確認項目 | 状態 |
|---|---------|------|
| 1 | Phase 1 全AC PASS | ✅ |
| 2 | Phase 2 全AC PASS | ✅ |
| 3 | Phase 3 設定ファイル削除 | ✅ 完了（4ファイル削除、dpo/ gitignore追加） |
| 4 | APIテスト 59/59 PASS | ✅（Phase 3 後に再確認済み） |
| 5 | サブエージェントレビュー PASS | ✅ |
| 6 | ユーザー確認「OK」 | ⬜ 待ち |
| 7 | dev にマージ | ⬜ 待ち |
