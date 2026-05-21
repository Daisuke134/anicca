# Auto-Dev + Night Builder System

## 概要

2スキル構成で Anicca の開発を自動化する。
auto-dev（昼）が調査+スペック作成、night-builder（夜）が並列実装。
同じ日付フォルダに全タスクが入り、night-builder が全体をまとめる。

---

## auto-dev（昼 — cron 12時間）

### 時間・頻度
- 12時間ごと（例: 10:00 JST / 22:00 JST）
- 将来: 1時間ごとに短縮 → 24/7化

### インプット
1. **app-metrics の最新データ**（必須・最初に読む）
   - `~/.openclaw/workspace/app-metrics/metrics_YYYY-MM-DD_*.json`
   - 重要指標: MRR、ペイウォール→トライアル変換率、DL数
   - メトリクスを見て「今一番改善すべきこと」を判断してから調査開始

### フロー
1. メトリクス読み込み → 最重要ボトルネック特定
2. x-research + web_search で調査（ベストプラクティス、事例）
3. 見つけたこと全部をスペックにする（簡単なものもスペック書く。実装しない）
4. Mac ローカルに task-*.md を SSH で書く
5. Slack #metrics に投稿（メトリクス背景 + 全スペック一覧 + 各ファイルパス）

### アウトプット

**ファイル（Mac ローカル）:**
```
/Users/cbns03/Downloads/anicca-project/.cursor/plans/ios/1.6.3/YYYY-MM-DD/
├── task-001-paywall-social-proof.md
├── task-002-trial-copy-change.md
└── task-003-superwall-ab-test.md
```

**各 task-*.md フォーマット:**
```markdown
# task-XXX: タイトル

## Source
メトリクス: ペイウォール→トライアル 0.0%
調査元: https://example.com/article

## Problem
何が問題か

## Spec
1. 具体的にやること
2. 具体的にやること
3. 具体的にやること

## Files
- 変更対象ファイル一覧

## Tests
- ユニットテスト要件
- Maestro/Playwright E2E 要件
```

**Slack 投稿例:**
```
📋 auto-dev 調査完了 — YYYY-MM-DD HH:MM JST

📊 現状メトリクス:
- MRR: $XX / 目標$100
- ペイウォール→トライアル: X.X%
- DL: XX件/7日

🔍 調査結果 → N件のスペック作成:

1️⃣ task-001: タイトル
   → 概要
   📄 .cursor/plans/ios/1.6.3/YYYY-MM-DD/task-001-xxx.md

2️⃣ task-002: タイトル
   → 概要
   📄 .cursor/plans/ios/1.6.3/YYYY-MM-DD/task-002-xxx.md

🌙 night-builder が 0:00 JST に全タスク実装予定
```

### 制約
- **実装しない。** スペックだけ書く。全ての実装は night-builder に任せる。
- **全てスペックにする。** 「スキルDLするだけ」でも task-*.md を書く。
- **メトリクス起点。** 調査テーマはメトリクスから逆算する。

---

## Dais + Anicca チャット（手動）

- auto-dev のスペックを確認・修正
- 新しいスペックを追加（同じ日付フォルダに）
- auto-dev の SKILL.md 自体をイテレーション改善

---

## night-builder（夜 — cron 0:00 JST = 15:00 UTC）

### インプット
```
その日の日付フォルダ内の全 task-*.md:
/Users/cbns03/Downloads/anicca-project/.cursor/plans/ios/1.6.3/YYYY-MM-DD/
├── task-001-xxx.md   ← auto-dev が書いた
├── task-002-xxx.md   ← auto-dev が書いた
├── task-003-xxx.md   ← Dais と Anicca が書いた
└── task-004-xxx.md   ← Dais と Anicca が書いた
```

### フロー
1. SSH to Mac
2. 日付フォルダの task-*.md 全部読む
3. タスクごとに **並列で**:
   - git worktree add（dev ブランチから）
   - codex/claude --full-auto 起動（SSH → Mac、並列実行）
   - Codex/Claude Code が自律で:
     - spec 読んで実装
     - テスト書いて全パス（TDD）
     - Maestro / Playwright E2E テスト実行
     - task-*.md の Result セクションに結果追記
     - git commit + push
     - gh pr create（worktree から）
4. 全 worktree 完了後 → Anicca が最終チェック:
   - 各 worktree の結果確認
   - テスト通ってない → その Codex に修正指示
   - 足りないもの → 追加指示
   - 全部 OK になるまで繰り返す
5. 全タスク完了後:
   - implementation-summary.md 作成（Mac ローカル）
   - Mac → VPS に同期
   - Slack #metrics に投稿（1回だけ）

### アウトプット

**task-*.md に Result 追記（Codex/Claude Code が書く）:**
```markdown
---

## Result

### Status: ✅ done
### Branch: night/task-001-xxx
### PR: https://github.com/Daisuke134/anicca.ai/pull/XX
### Duration: Xm XXs

### Changes
- ファイル名: +XX -XX（変更内容）

### Build: ✅ passed
### Unit Tests: ✅ X/X passed
### E2E: ✅ test_name.yaml passed

### Notes
実装時の補足
```

**implementation-summary.md（night-builder が作る）:**
```markdown
# Implementation Summary — YYYY-MM-DD

## 実行: 0:00〜X:XX JST

## メトリクス背景
- MRR: $XX / 目標$100
- ペイウォール→トライアル: X.X%

## 結果

| # | Task | Status | PR | 時間 |
|---|------|--------|-----|------|
| 001 | タイトル | ✅ | #XX | Xm |
| 002 | タイトル | ❌ | — | Xm |

## 成功: X/Y | 失敗: Z/Y

## 失敗詳細（あれば）
### task-XXX: タイトル
- エラー内容
- → 明日のauto-devでスペック見直し

## 全PR一覧
- #XX: URL
```

**Slack 投稿（全完了後に1回だけ）:**
```
🌙 Night Builder 完了 — YYYY-MM-DD HH:MM JST

📊 背景: MRR $XX, ペイウォールCVR X.X%

✅ task-001: タイトル → PR #XX (Xm)
❌ task-002: タイトル → エラー概要

📊 成功: X/Y | 合計: XXm
📄 詳細: .cursor/plans/ios/1.6.3/YYYY-MM-DD/implementation-summary.md
```

---

## 同期（Mac → VPS）

night-builder 完了後に1コマンドで同期:
```bash
scp -r cbns03@cbns03macbook-pro:/Users/cbns03/Downloads/anicca-project/.cursor/plans/ios/1.6.3/YYYY-MM-DD/ \
  ~/.openclaw/workspace/auto-dev/YYYY-MM-DD/
```

---

## 後のフェーズで追加すること

- **codex-review ゲート**: auto-dev がスペック書いた後、Slack投稿前に codex-review でレビュー通す
- **自動マージ+デプロイ**: night-builder 成功 → 自動で dev にマージ → Vercel/App Store デプロイ
- **24/7化**: auto-dev + night-builder 統合 → 1時間ごとに調査+実装サイクル

---

## 進化パス

```
今:     auto-dev 12h → 夜 night-builder
次:     auto-dev 1h → 24/7 builder（統合）
最終:   完璧な spec マスター + 常時 Codex/CC 並列
        → 自動デプロイ
        → revenue ↑ → more compute → faster iteration → revenue ↑↑
```
