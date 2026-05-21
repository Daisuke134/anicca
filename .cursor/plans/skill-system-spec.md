# Skill System Spec — 複利で効くスキル設計

> **目的**: 2つの外部記事 + プロジェクト現状分析から、Aniccaに導入すべきスキルの設計仕様。
> コンテキストが失われても、このファイル単体で「何を・なぜ・どう作るか」が分かるように記述する。
> **最終更新**: 2026-02-09
> **ステータス**: 設計中

---

## 0. 背景（2つの外部記事の要点）

### 記事1: 「Opus 4.6を間違って使っている」（5プロンプトシステム）

**核心**: 単発プロンプトではなく、5つが循環するシステムを組むと複利で賢くなる。

| Step | 名前 | 何をするか | Aniccaの対応状況 |
|------|------|-----------|-----------------|
| 1 | **THE AUDIT** | ワークフロー分析、自動化すべきタスクを「時間コスト × エネルギー消耗 × 実現可能性」でスコアリング → 4週間計画 | **なし** |
| 2 | **THE ARCHITECT** | 実装前に2-3アプローチ比較 → 最もシンプルな設計図を選ぶ | **部分的**: `decisive-agent`（判断のみ）、`/plan`（計画） |
| 3 | **THE ANALYST** | 自分の品質基準を埋め込んだコードレビュー（47点チェック） | **あり**: `codex-review`（反復ループ付き。より高度） |
| 4 | **THE REFINERY** | 生成→自己採点→診断→改善→再採点の収束ループ | **あり**: `recursive-improver`（マーケ特化版。本日作成済み） |
| 5 | **THE COMPOUNDER** | 週次振り返り。何が動いてるか、何が壊れたか、次は何を自動化するか | **なし** |

**著者の主張する効果**:

| 指標 | Before | After | 改善 |
|------|--------|-------|------|
| コンテキスト再説明 | 13h/週 | 0.5h/週 | 96%削減 |
| バグ修正 | 8h/週 | 2h/週 | 75%削減 |
| ドキュメント作業 | 6h/週 | 0h/週 | 100%削減 |
| デバッグ | 4h/週 | 1.5h/週 | 62%削減 |
| **実コーディング時間** | **9h/週** | **36h/週** | **4倍** |

### 記事2: 「Claude Skillsで100x開発者になった方法」（5スキルシステム）

**核心**: スキルは「保存されたプロンプト」ではない。Claudeにインストールする実行可能な知識パッケージ。

| # | 著者のスキル | 何をするか | Aniccaの対応状況 |
|---|-------------|-----------|-----------------|
| 1 | **Project Context Guardian** | プロジェクト構造・DB・API・コーディング規約を自動ロード | **部分的**: CLAUDE.md + rules 16個 + Serenaメモリ 12個。ただし「スキル」としては存在しない |
| 2 | **TDD Enforcer** | テスト先行を強制 | **あり**: `tdd-workflow` |
| 3 | **Documentation Generator** | コーディング中に質問→回答をADR・README等に自動変換 | **なし** |
| 4 | **Code Review Protocol** | 47点チェックリストでセキュリティ・品質を自動チェック | **あり（より高度）**: `codex-review`（Codex CLI + 反復ループ） |
| 5 | **Systematic Debug Framework** | 再現→仮説→排除→根本原因→修正→回帰テストの6ステップ | **なし** |

### 2つの記事の共通メッセージ

| 原則 | 説明 |
|------|------|
| **システム > プロンプト集** | 47個のブックマークより、5個の循環するスキル |
| **メタワークの消滅** | 説明・記憶・確認・レビューをスキルが自動化。人間は「判断」に集中 |
| **複利効果** | スキル同士が連携すると、1+1+1=3 ではなく 1×1.5×1.5=3.4 |
| **1個から始めて磨く** | 最初のスキルは間違う前提。小さく作って使いながら改善 |

---

## 1. 現在のスキルマップ（2026-02-09）

### 既存スキル（48個）

```
.claude/skills/
├── 開発系(13): tdd-workflow, codex-review, codex, decisive-agent, ralph-autonomous-dev,
│               maestro-ui-testing, webapp-testing, mcp-builder, skill-creator,
│               software-architecture, supabase-postgres-best-practices,
│               prompt-engineering, changelog-generator
├── マーケ系(7): recursive-improver, aso-growth, competitive-ads-extractor, tiktok-ads,
│               tiktok-ads-optimization, lead-research-assistant, domain-name-brainstormer
├── コンテンツ系(4): content-creator, content-research-writer, build-in-public, auto-article-poster
├── UI/UX系(4): ui-skills, canvas-design, theme-factory, image-enhancer
├── ドキュメント系(4): xlsx, pdf, pptx, docx
├── 自動化系(8): mixpanel-automation, slack-automation, github-automation, sentry-automation,
│               tiktok-automation, twitter-automation, google-drive-automation, google-calendar-automation
├── 分析系(2): meeting-insights-analyzer, developer-growth-analysis
├── 整理系(2): file-organizer, invoice-organizer
├── SNS最適化(1): twitter-algorithm-optimizer
├── メモリ(1): agent-memory
├── 動画(2): remotion, video-downloader
```

### 既存のルール・メモリ（スキル相当の機能を持つもの）

| 仕組み | 数 | 役割 |
|--------|-----|------|
| `.claude/rules/` | 16個 | 毎セッション自動読み込み。コーディングスタイル、デプロイ、テスト等 |
| `.serena/memories/` | 12個 | プロジェクト知識の永続化。アーキテクチャ、ワークフロー等 |
| CLAUDE.md | 1個 | プロジェクト概要（150行以下） |
| `.cursor/plans/reference/` | 5個 | 低頻度参照情報（secrets, infrastructure等） |

### ギャップ分析

| ニーズ | 対応状況 | ギャップ |
|--------|---------|---------|
| コンテキスト自動ロード | rules + Serenaメモリで大部分カバー | Project Context「スキル」としては存在しない（ただし機能的には十分） |
| TDD強制 | `tdd-workflow` | OK |
| コードレビュー | `codex-review` | OK（記事2より高度） |
| 再帰的品質改善 | `recursive-improver` | OK（マーケ特化。コード版は未作成） |
| **体系的デバッグ** | **なし** | **ギャップ: 最優先** |
| **OpenClaw運用ガイド** | reference/に散在 | **ギャップ: Phase 2-3の実装時に必須** |
| **リリース自動化** | deployment.mdに手順あり | **ギャップ: スキルとしては未体系化** |
| **メトリクス分析** | なし | **ギャップ: 毎回MCPを個別に叩いている** |
| **週次振り返り** | なし | **ギャップ: 複利効果の核** |
| **ドキュメント自動生成** | なし | **ギャップ: ADR手動作成** |

---

## 2. 作成するスキル（6個）

### 優先順位

| # | スキル名 | 理由 | 記事対応 | 既存資産との関係 |
|---|---------|------|---------|----------------|
| 1 | **systematic-debugger** | Phase 3実装中に確実に必要。VPS+API+Slack+Cron連携のデバッグ | 記事2の#5 | なし（新規） |
| 2 | **openclaw-ops** | Phase 2-3の作業効率化。VPS操作手順の集約 | - | reference/に散在 → 1箇所に集約 |
| 3 | **metrics-analyst** | 毎回同じMCPツール呼び出しパターンの自動化 | - | mcp-openclaw.md のMixpanel/RC情報 |
| 4 | **release-conductor** | 1.6.2完了後のApp Storeリリース。手順をスキル化 | - | deployment.md → スキル昇格 |
| 5 | **weekly-compounder** | 週次振り返りで複利効果を生む。スキル改善の核 | 記事1のStep 5 | なし（新規） |
| 6 | **adr-generator** | 設計判断の自動記録。1.6.2でADR-004〜007が既にある | 記事2の#3（部分的） | closed-loop-ops ADRパターン |

---

## 3. 各スキル詳細設計

### 3.1 systematic-debugger

**概要**: デバッグを「ランダムな試行」から「体系的な6ステップ調査」に変える。

```
.claude/skills/systematic-debugger/
├── SKILL.md
└── references/
    └── debug-patterns.md    ← よくあるバグパターンと解法
```

**SKILL.md**:

```yaml
---
name: systematic-debugger
description: >
  Transforms debugging from random trial-and-error into a methodical 6-step investigation
  framework (reproduce, hypothesize, eliminate, root-cause, fix, prevent).
  Use when encountering bugs, errors, crashes, unexpected behavior, or when something
  doesn't work. Keywords: debug, bug, error, crash, 動かない, バグ, エラー, なぜ動かない.
---
```

**ワークフロー（6ステップ）**:

| Step | 名前 | 何をするか | 出力形式 |
|------|------|-----------|---------|
| 1 | **REPRODUCE** | 失敗するテスト or 再現手順を確立 | 再現条件テーブル |
| 2 | **HYPOTHESIZE** | 3-5個の想定原因を列挙。各仮説に確率と検証方法 | 仮説テーブル |
| 3 | **ELIMINATE** | 確率高い順に検証。検証結果を記録 | 検証結果テーブル |
| 4 | **ROOT CAUSE** | 5 Whys で根本原因特定。修正は原因特定まで禁止 | 5 Whys チェーン |
| 5 | **FIX** | 根本原因のみを最小差分で修正 | diff |
| 6 | **PREVENT** | Step 1のテストがGREEN確認 + 同種バグ防止策 | 回帰テスト |

**禁止事項**:

| 禁止 | 理由 |
|------|------|
| ランダムな修正の試行 | 症状を隠すだけで根本原因が残る |
| console.log爆撃 | 仮説なしの情報収集は非効率 |
| Step 4より前の修正 | 原因不明のまま修正すると別のバグを生む |
| 「動いたからOK」 | 回帰テスト（Step 6）なしで完了とは認めない |

**Anicca固有のデバッグパターン（references/debug-patterns.md）**:

| パターン | 症状 | よくある原因 | 確認方法 |
|---------|------|------------|---------|
| OpenClaw Cron不発火 | Slack投稿が来ない | delivery.mode設定ミス / Gateway未再起動 | `openclaw cron list` + systemd status |
| Slack二重投稿 | 同じメッセージが2回 | announce + exec 同時使用 / bindings未設定 | openclaw.json の delivery.mode確認 |
| Railway API 404 | iOS側でエラー | デプロイ未完了 / エンドポイントパス不一致 | Railway ログ + `curl` でエンドポイント確認 |
| Prisma P2003 | FK制約違反 | upsert前のFK先レコード不存在 | `findUnique` で存在チェック |
| VPS SSH接続切れ | ssh: Connection refused | systemd restart中 / ポート変更 | `ping` → `ssh -v` で詳細確認 |
| Mixpanel データなし | セグメンテーション結果0件 | イベント名スペルミス / プロジェクトID違い | `project_id: 3970220`、イベント名を再確認 |
| RevenueCat 不整合 | iOS側で課金情報が古い | Webhook遅延 / sandbox環境 | RC Dashboard で subscriber status確認 |
| Maestro テスト失敗 | element not found | accessibilityIdentifier未設定 / テキスト変更 | `inspect_view_hierarchy` で実際のテキスト確認 |

---

### 3.2 openclaw-ops

**概要**: VPS上のOpenClaw運用操作を1箇所に集約。SSH→設定変更→再起動→動作確認のワンストップガイド。

```
.claude/skills/openclaw-ops/
├── SKILL.md
└── references/
    └── cron-templates.md    ← Cronジョブテンプレート集
```

**SKILL.md**:

```yaml
---
name: openclaw-ops
description: >
  OpenClaw VPS (46.225.70.241) の運用操作ガイド。SSH接続、設定変更、Gateway再起動、
  Cronジョブ追加/修正、スキル配置、ログ確認を1箇所に集約。
  Use when OpenClaw, VPS, Cron, Gateway, openclaw.json, anicca agent, スキル配置,
  ログ確認, エージェント設定.
---
```

**クイックリファレンス**:

| 操作 | コマンド |
|------|---------|
| SSH接続 | `ssh anicca@46.225.70.241` |
| Gateway再起動 | `export XDG_RUNTIME_DIR=/run/user/$(id -u) && systemctl --user restart openclaw-gateway` |
| Gateway状態確認 | `systemctl --user status openclaw-gateway` |
| Cronジョブ一覧 | `openclaw cron list` |
| スキル一覧 | `openclaw skills list` |
| ログ確認 | `ls -lt ~/.openclaw/logs/ \| head -5` |
| 環境変数確認 | `cat ~/.env` |
| 設定確認 | `cat ~/.openclaw/openclaw.json` |

**設定変更フロー**:

```
1. SSH接続
2. 設定ファイル編集（nano/vi）
3. 変更内容をテーブルで報告（Before/After）
4. Gateway再起動
5. 動作確認（cron list / skills list / ログ）
6. 結果をテーブルで報告
```

**重要ルール（MEMORY.mdから抽出）**:

| ルール | 理由 |
|--------|------|
| delivery.mode は `"announce"` or `"none"` のみ | `"silent"` は無効（undefined behavior） |
| announce + exec in prompt = 禁止 | 二重投稿になる |
| Cron は `agentTurn` + message | `systemEvent` は main session のみに行く |
| Profile: `full` | `coding` だとSlack送信できない |
| Gateway再起動は設定変更後のみ | クラッシュ時はsystemd自動復帰 |
| MCP ツール (`mcp__*`) はVPSで使えない | Claude Code専用 |

**Cronジョブ追加テンプレート（references/cron-templates.md）**:

```json
{
  "id": "<ジョブ名>",
  "schedule": "0 <hour_utc> * * *",
  "kind": "agentTurn",
  "message": "<エージェントへの指示>",
  "delivery": {
    "mode": "none"
  }
}
```

---

### 3.3 metrics-analyst

**概要**: ASC + RevenueCat + Mixpanel を横断分析。KPIダッシュボードを自動生成。

```
.claude/skills/metrics-analyst/
├── SKILL.md
└── references/
    └── kpi-definitions.md    ← KPI定義と計算式
```

**SKILL.md**:

```yaml
---
name: metrics-analyst
description: >
  App Store Connect、RevenueCat、Mixpanelを横断してAniccaのKPIを自動分析する。
  ダウンロード数、MRR、トライアル開始、ファネル転換率、前週比トレンドをテーブルで出力。
  Use when メトリクス, KPI, ダウンロード数, MRR, revenue, 分析, ファネル,
  コンバージョン, トライアル, metrics, analytics.
---
```

**データソースと取得方法**:

| データ | ソース | MCPツール | パラメータ |
|--------|--------|----------|-----------|
| ダウンロード数 | App Store Connect | `mcp__app-store-connect__*` | アプリID自動取得 |
| MRR / Active Subs / Trials | RevenueCat | `mcp__revenuecat__mcp_RC_get_overview_metrics` | `project_id: "projbb7b9d1b"` |
| onboarding_started | Mixpanel | Segmentation query | `project_id: 3970220` |
| onboarding_paywall_viewed | Mixpanel | Segmentation query | `project_id: 3970220` |
| rc_trial_started_event | Mixpanel | Segmentation query | `project_id: 3970220` |

**出力テーブル形式**:

```
## Anicca KPI Report（{期間}）

### コアメトリクス
| 指標 | 今週 | 先週 | 変化 |
|------|------|------|------|
| ダウンロード数 | XX | XX | +XX% |
| MRR | $XX | $XX | +XX% |
| Active Subs | X | X | +X |
| Active Trials | X | X | +X |

### ファネル分析
| ステップ | 数 | 転換率 |
|---------|-----|--------|
| onboarding_started | XXX | - |
| onboarding_paywall_viewed | XX | XX.X% |
| rc_trial_started_event | X | X.X% |

### インサイト
| 発見 | 影響 | 推奨アクション |
|------|------|--------------|
| ... | ... | ... |
```

**注意事項**:

| 注意 | 理由 |
|------|------|
| `onboarding_paywall_purchased` は使わない | DEBUG/サンドボックス含むため不正確 |
| トライアル開始は `rc_trial_started_event` のみ | RevenueCat→Mixpanel経由が正確 |
| Mixpanel `project_id` は integer `3970220` | 文字列ではない |
| RevenueCat `project_id` は string `"projbb7b9d1b"` | integerではない |

---

### 3.4 release-conductor

**概要**: dev→main→release/x.x.x→App Store→devマージの全自動リリースフロー。

```
.claude/skills/release-conductor/
├── SKILL.md
└── references/
    └── troubleshooting.md    ← リリースエラーと対処法
```

**SKILL.md**:

```yaml
---
name: release-conductor
description: >
  Aniccaの App Store リリースを全自動化する。dev→main マージ、バージョンバンプ、
  Fastlane による Archive→Upload→審査提出、release ブランチ作成、dev への逆マージまで。
  Use when リリース, App Store, 提出, バージョンアップ, release, submit, 審査.
disable-model-invocation: true
---
```

**リリースフロー（7ステップ）**:

| Step | 操作 | コマンド | 失敗時 |
|------|------|---------|--------|
| 1 | mainを最新に | `git checkout main && git pull origin main` | - |
| 2 | releaseブランチ作成 | `git checkout -b release/X.Y.Z` | - |
| 3 | バージョン更新 | `cd aniccaios && fastlane set_version version:X.Y.Z` | バージョン番号確認 |
| 4 | コミット&プッシュ | `git add -A && git commit && git push -u origin release/X.Y.Z` | - |
| 5 | 全自動リリース | `cd aniccaios && FASTLANE_SKIP_UPDATE_CHECK=1 fastlane full_release` | `troubleshooting.md` 参照 |
| 6 | 結果報告 | ビルド番号、バージョン、審査ステータス | - |
| 7 | dev逆マージ | `git checkout dev && git merge release/X.Y.Z && git push origin dev` | コンフリクト手動解決 |

**実行前チェックリスト（BLOCKING）**:

| # | チェック | 確認方法 |
|---|---------|---------|
| 1 | 全テストPASS | `cd aniccaios && fastlane test` |
| 2 | devが最新 | `git pull origin dev` |
| 3 | Backend先にデプロイ済み | Railway Production のデプロイ状態確認 |
| 4 | ユーザーOK | 「X.Y.Z をリリースしますか？」で承認待ち |

**references/troubleshooting.md**:

| エラー | 原因 | 対処 |
|--------|------|------|
| `Invalid Pre-Release Train` | バージョンが古い/閉じている | `fastlane set_version version:正しいバージョン` |
| `CFBundleShortVersionString must be higher` | バージョンが前回以下 | バージョン番号を上げて再実行 |
| build失敗 | コンパイルエラー | Fastlane出力を読んで修正 → 再実行 |
| upload失敗 | ネットワーク/認証 | `fastlane upload` を個別再実行 |
| processingタイムアウト | Apple側の遅延 | ASCで確認 → `fastlane submit_review` |
| submit失敗 | コンプライアンス問題 | ASC確認 → `submission_information` 修正 |

---

### 3.5 weekly-compounder

**概要**: 毎週の振り返りで「何が動いてるか、何が壊れたか、次は何か」を体系化。スキル改善の核。

```
.claude/skills/weekly-compounder/
└── SKILL.md
```

**SKILL.md**:

```yaml
---
name: weekly-compounder
description: >
  毎週の開発振り返りを体系化し、スキル・自動化の複利効果を最大化する。
  動いているもの、壊れたもの、次にやるべきことをテーブルで整理し、
  パターン認識から次週の改善を提案する。
  Use when 振り返り, weekly review, 週次レビュー, 今週のまとめ, 週報, compounder.
disable-model-invocation: true
---
```

**5ステップ振り返りフロー**:

| Step | 名前 | 何をするか |
|------|------|-----------|
| 1 | **PROGRESS** | 今週の成果をSerenaメモリ + git log + Slackから収集 → テーブル化 |
| 2 | **FRICTION** | 「何に時間を取られたか」「何がイライラしたか」をヒアリング |
| 3 | **NEXT TARGET** | Friction + 未着手タスクから次週の自動化ターゲットを提案 |
| 4 | **PATTERN** | 過去の振り返り履歴から「うまくいくパターン」「失敗するパターン」を検出 |
| 5 | **SYSTEM MAP** | アクティブな自動化一覧 + 週あたり節約時間 + 次の3ターゲット |

**出力テーブル形式**:

```
## Week of YYYY-MM-DD

### 1. 成果
| 項目 | 状態 | 時間節約 |
|------|------|---------|
| ... | ... | ... |

### 2. フリクション
| 何が起きた | 時間コスト | エネルギー消耗 | 自動化可能？ |
|-----------|-----------|--------------|------------|
| ... | ... | ... | ... |

### 3. 次週ターゲット
| ターゲット | 理由 | 見積もり |
|-----------|------|---------|
| ... | ... | ... |

### 4. パターン認識
| パターン | 種類 | 対策 |
|---------|------|------|
| ... | 成功/失敗 | ... |

### 5. システムマップ
| 自動化 | ツール | 週あたり節約 | 状態 |
|--------|--------|------------|------|
| ... | ... | ... | 稼働中/改善要/廃止候補 |

**累計節約時間: Xh/週**
```

**蓄積場所**: `.cursor/logs/weekly/YYYY-WNN.md`（git管理で履歴が残る）

---

### 3.6 adr-generator

**概要**: アーキテクチャ判断をリアルタイムでADR（Architecture Decision Record）として記録。

```
.claude/skills/adr-generator/
└── SKILL.md
```

**SKILL.md**:

```yaml
---
name: adr-generator
description: >
  アーキテクチャ判断が発生した時に、ADR（Architecture Decision Record）を自動生成する。
  「なぜこの技術を選んだか」「他に何を検討したか」を構造化して記録。
  Use when ADR, architecture decision, 設計判断, なぜこれを選んだ, 技術選定記録.
disable-model-invocation: true
---
```

**ADRテンプレート**:

```markdown
# ADR-NNN: [タイトル]

| 項目 | 内容 |
|------|------|
| 日付 | YYYY-MM-DD |
| 状態 | 提案 / 採用 / 廃止 |
| 影響範囲 | [ファイル/モジュール] |

## コンテキスト
[何が問題で、なぜ判断が必要だったか]

## 検討した選択肢

| 選択肢 | メリット | デメリット | 判定 |
|--------|---------|-----------|------|
| A（採用） | ... | ... | ✅ |
| B | ... | ... | ❌ |
| C | ... | ... | ❌ |

## 決定
[何を選んだか、なぜか]

## 影響
[この判断で何が変わるか]
```

**保存場所**: `.cursor/plans/adr/ADR-NNN-<title>.md`

**採番ルール**: 既存の最大ADR番号 + 1（1.6.2で ADR-004〜007 が存在 → 次は ADR-008）

---

## 4. スキル間の循環構造

```
                    ┌─────────────────────┐
                    │  weekly-compounder   │
                    │  (週次振り返り)       │
                    └──────────┬──────────┘
                               │ フリクション検出
                               ▼
                    ┌─────────────────────┐
                    │  systematic-debugger │◄── バグ発生時
                    │  (体系的デバッグ)     │
                    └──────────┬──────────┘
                               │ 修正完了
                               ▼
              ┌────────────────────────────────────┐
              │                                    │
    ┌─────────▼─────────┐            ┌─────────────▼──────────┐
    │  codex-review      │            │  adr-generator          │
    │  (品質ゲート)       │            │  (設計判断記録)          │
    └─────────┬─────────┘            └──────────────────────────┘
              │ レビューPASS
              ▼
    ┌─────────────────────┐
    │  release-conductor   │◄── リリース時
    │  (App Storeリリース)  │
    └─────────┬─────────┘
              │ リリース完了
              ▼
    ┌─────────────────────┐
    │  metrics-analyst     │◄── 毎週/毎日
    │  (KPI分析)           │
    └─────────┬─────────┘
              │ データ
              ▼
    ┌─────────────────────┐
    │  weekly-compounder   │← ループ完了
    │  (翌週の振り返り)     │
    └─────────────────────┘

独立稼働:
    ┌─────────────────────┐
    │  openclaw-ops        │◄── VPS操作時（いつでも）
    │  (VPS運用ガイド)      │
    └─────────────────────┘
```

**複利の仕組み**:

| 循環 | 効果 |
|------|------|
| debugger → codex-review | デバッグで見つけた問題パターンがレビューチェックリストに追加される |
| metrics → compounder | KPIの変化が「次に何を改善するか」のインプットになる |
| compounder → debugger | 週次フリクションから「よくあるバグパターン」が蓄積される |
| adr-generator → 全スキル | 設計判断の記録が、将来の判断の参考になる |

---

## 5. 既存スキルとの関係（重複回避）

| 新スキル | 既存スキルとの関係 | 棲み分け |
|---------|-------------------|---------|
| systematic-debugger | `codex-review`（レビュー） | reviewは「コミット前の品質チェック」、debuggerは「バグ発生時の調査」。フェーズが違う |
| openclaw-ops | `mcp-openclaw.md`（ルール） | rulesは「何を使うか」、opsは「どう操作するか」。前者は判断、後者は手順 |
| metrics-analyst | `mixpanel-automation`（自動化） | automationは「MCP操作方法」、analystは「KPIの意味と分析パターン」。前者はHow、後者はWhat |
| release-conductor | `deployment.md`（ルール） | rulesは「ルール」、conductorは「実行フロー」。前者はDo/Don't、後者はStep by Step |
| weekly-compounder | なし | 完全新規 |
| adr-generator | `decisive-agent`（判断） | decisiveは「判断する」、adrは「判断を記録する」。判断後にADRが生成される |

---

## 6. 実装計画

### Phase 1: 即着手（1-2日）

| # | スキル | 作成時間 | テスト方法 |
|---|--------|---------|-----------|
| 1 | systematic-debugger | 30分 | 次のバグ発生時に実際に使う |
| 2 | openclaw-ops | 30分 | VPSにSSHして全コマンド動作確認 |

### Phase 2: 1.6.2実装中（1週間以内）

| # | スキル | 作成時間 | テスト方法 |
|---|--------|---------|-----------|
| 3 | metrics-analyst | 30分 | ASC+RC+Mixpanelの実データで分析レポート生成 |
| 4 | adr-generator | 20分 | 1.6.2の次の設計判断時にADR自動生成 |

### Phase 3: 1.6.2完了後

| # | スキル | 作成時間 | テスト方法 |
|---|--------|---------|-----------|
| 5 | release-conductor | 30分 | 1.6.2のApp Storeリリースで実際に使う |
| 6 | weekly-compounder | 30分 | 翌週の金曜振り返りで実際に使う |

---

## 7. テストマトリックス

| # | スキル | テスト名 | 検証方法 | カバー |
|---|--------|---------|---------|--------|
| S-01 | systematic-debugger | SKILL.md が500行以下 | `wc -l` | サイズ制限 |
| S-02 | systematic-debugger | description にトリガーキーワード含む | 目視確認 | 自動発動 |
| S-03 | systematic-debugger | 6ステップが全てテーブル出力 | 実際のバグで使用 | ワークフロー |
| S-04 | openclaw-ops | 全コマンドがVPSで動作 | SSH接続して実行 | 正確性 |
| S-05 | openclaw-ops | MEMORY.mdのルールが全て反映 | 差分確認 | 網羅性 |
| S-06 | metrics-analyst | 3データソース全てからデータ取得 | MCPツール実行 | データ取得 |
| S-07 | metrics-analyst | 前週比テーブルが正しい | 手動計算と照合 | 正確性 |
| S-08 | release-conductor | 7ステップが全て記載 | 目視確認 | 網羅性 |
| S-09 | release-conductor | troubleshooting.mdに6エラー以上 | 目視確認 | トラブル対応 |
| S-10 | weekly-compounder | 5ステップ出力が全てテーブル形式 | 実際の振り返りで使用 | 出力形式 |
| S-11 | adr-generator | テンプレートがADR-004〜007と整合 | 既存ADRと比較 | 一貫性 |
| S-12 | 全スキル | `disable-model-invocation` が副作用スキルに設定 | frontmatter確認 | 安全性 |

---

## 8. 境界

### やること

| 対象 | 内容 |
|------|------|
| 6つのSKILL.md作成 | `.claude/skills/` 配下に配置 |
| references/ ファイル作成 | debug-patterns.md, cron-templates.md, kpi-definitions.md, troubleshooting.md |
| tool-usage.md 更新 | スキル自動適用テーブルに6スキル追加 |

### やらないこと

| 対象 | 理由 |
|------|------|
| 既存スキルの大規模リファクタ | このSpecは新規スキル作成のみ |
| 1.6.2のコード実装 | 別Spec（ultimate-spec）の範囲 |
| agent-orchestration-specの実装 | 別Spec。P0-P3は別タスク |
| VPS上の設定変更 | openclaw-opsはガイドのみ。実際の変更は別タスク |

---

## 9. 関連ドキュメント

| ドキュメント | 関係 |
|-------------|------|
| `.cursor/plans/agent-orchestration-spec.md` | 6つの外部事例からの統合戦略。本Specのスキルはその一部を実装する |
| `.cursor/plans/ios/1.6.2/implementation/README.md` | 1.6.2全体の歩き方ガイド。Phase 2-3の実装時にスキルが必要 |
| `.claude/rules/skill-authoring.md` | スキル作成ルール。description書き方、500行制限等 |
| `.claude/skills/skill-creator/SKILL.md` | スキル作成ガイドスキル |
| `.cursor/plans/reference/openclaw-anicca.md` | OpenClawの現状。openclaw-opsスキルの情報源 |

---

## 10. 外部記事の原文要点（永続参照用）

### 記事1: 「Opus 4.6を間違って使っている」

**著者**: 不明（Xスレッド）
**核心**: 単発プロンプトは複利しない。5つのプロンプトを循環させるシステムが必要。

**5つのプロンプト概要**:

| # | 名前 | 一言で | ポイント |
|---|------|-------|---------|
| 1 | AUDIT | 何を自動化すべきか特定 | TIME COST × ENERGY DRAIN × FEASIBILITY でスコアリング。エネルギー消耗（頭の中にずっとある仕事）も重要 |
| 2 | ARCHITECT | どう作るか設計 | 2-3アプローチ比較。最もシンプルなものを推奨。「複雑なものを作ろうとしたら止めてくれ」 |
| 3 | ANALYST | 品質レビュー | 自分の品質基準をプロンプトに埋め込む。47点チェック。Architecture→Quality→Reliability→Performance |
| 4 | REFINERY | 再帰的改善 | 生成→自己採点→診断→改善→再採点。全基準8/10以上で停止。改善幅0.5未満で収穫逓減停止 |
| 5 | COMPOUNDER | 週次振り返り | Progress→Friction→Next Target→Pattern Recognition→System Map。累計節約時間を追跡 |

**Opus 4.6の評価（著者）**:

| 評価 | 内容 |
|------|------|
| 良くなった | Adaptive Thinking、1Mコンテキスト窓、サブエージェント自動委任 |
| 変わらない | 単純ライティング、基本Q&A |
| 悪くなった | 自由な創作が機械的に感じる場合あり |

### 記事2: 「Claude Skillsで100x開発者になった方法」

**著者**: Ihtesham Ali (@ihtesham2005)
**日付**: 2026年2月9日
**閲覧数**: 29,300+

**核心**: スキルは「保存されたプロンプト」ではない。実行可能な知識パッケージ。

**技術的仕組み**:

| 項目 | 値 |
|------|-----|
| 配置場所 | `.claude/skills/` ディレクトリ |
| 起動時コスト | ~100トークン/スキル（全スキルスキャン） |
| 発動時コスト | ~5kトークン（SKILL.md全文ロード） |
| 発動条件 | descriptionとユーザー発言のセマンティックマッチ |

**著者の5スキル**:

| # | スキル | 行数 | 効果 |
|---|--------|------|------|
| 1 | Project Context Guardian | 2,400行 | 160分/日の説明時間削減 |
| 2 | TDD Enforcer | 不明 | 70%のバグ削減、90%テストカバレッジ |
| 3 | Documentation Generator | 不明 | ドキュメント作業0h/週 |
| 4 | Code Review Protocol | 47行 | 2分/回のレビュー（手動20分→2分） |
| 5 | Systematic Debug Framework | 不明 | デバッグ2-3h→20-30分 |

**教訓**:

| 教訓 | 詳細 |
|------|------|
| 最初のスキルは間違う | 著者のCode Reviewは200行→47行に縮小。使いながら磨く |
| 1個から始める | 5個同時に作るな。1個作って、使って、改善して、次へ |
| スキルは複利 | TDD×Documentation = テスト理由がドキュメントに。Review×TDD = レビュー指摘がテスト化 |
| cognitive offloading | 脳を文法・手順から解放して、アーキテクチャ・戦略に集中 |

---

最終更新: 2026年2月9日
作成者: Claude Code (Opus 4.6)
