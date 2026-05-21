# Maestro CI 修正 — 完全仕様書

**作成日**: 2026-02-07
**ステータス**: 未着手
**優先度**: 高（CIが壊れている — E2Eジョブが毎回失敗）
**TDDスキル**: `/tdd-workflow` 適用

---

## 開発環境

| 項目 | 値 |
|------|-----|
| **作業ブランチ** | `dev`（直接コミット — Maestro YAML は設定ファイルであり、worktree.md の「ドキュメント変更などコード以外の変更はdev直接コミット可」に該当） |
| **作業状態** | 未着手 |

---

## 概要（What & Why）

### What

GitHub Actions の `ios-ci.yml` → `E2E Tests (Maestro)` ジョブが毎回失敗する。原因は Maestro がサブディレクトリ内のフローファイルを認識できていないこと。

### Why

`maestro test aniccaios/maestro/` はデフォルトでトップレベルの `.yaml` ファイルしか探さない。現在、全フローファイルがサブディレクトリ（`onboarding/`, `nudge/`, `nudge/phase6/`）に配置されているため、「フローが見つからない」で即座に exit code 1 で終了する。

### CIエラーログ

```
Top-level directories do not contain any Flows: /Users/runner/work/anicca.ai/anicca.ai/aniccaios/maestro
To configure Maestro to run Flows in subdirectories, check out the following resources:
  * https://maestro.mobile.dev/cli/test-suites-and-reports#inclusion-patterns
Error: Process completed with exit code 1.
```

---

## 受け入れ条件

| # | 条件 | テスト可能な形式 |
|---|------|-----------------|
| AC-1 | `maestro test aniccaios/maestro/` がサブディレクトリのフローを認識する | config.yaml 作成後、`maestro test aniccaios/maestro/ --include-tags smokeTest` でフローが列挙される |
| AC-2 | `--include-tags smokeTest,phase6` で該当フローのみ実行される | smokeTest: 1件 (01-onboarding)、phase6: 4件 → 合計5件が実行対象 |
| AC-3 | `runFlow` の相対パス参照が正しく解決される | `nudge/05-*.yaml` から `../onboarding/01-onboarding.yaml` が呼べる |
| AC-4 | 存在しないファイルへの `runFlow` 参照がない | `01-onboarding-fixed.yaml` への参照が0件 |
| AC-5 | 全フローにタグが設定されている | `tags:` セクションがない `.yaml` が0件 |
| AC-6 | GitHub Actions の `E2E Tests (Maestro)` ジョブが成功する | `gh run view --log-failed` でエラーなし |

---

## As-Is / To-Be

### As-Is: 現在のディレクトリ構造

```
aniccaios/maestro/
├── (config.yaml なし)          ← 問題の核心
├── onboarding/
│   ├── 01-onboarding.yaml      (tags: smokeTest, onboarding)
│   ├── 02-live-demo.yaml       (tags: onboarding, liveDemo)
│   └── 03-soft-paywall.yaml    (tags: onboarding, paywall)
└── nudge/
    ├── 05-phase5-thompson-sampling.yaml     (tags: なし ← 問題)
    ├── 06-phase5-unresponsive-simulation.yaml (tags: なし ← 問題)
    ├── 15-nudge-card-loading-speed.yaml     (tags: performance, nudge)
    └── phase6/
        ├── 01-llm-nudge-display.yaml        (tags: phase6, llm, nudge)
        ├── 02-feedback-flow.yaml            (tags: phase6, feedback, nudge)
        ├── 03-feedback-thumbs-down.yaml     (tags: phase6, feedback, nudge)
        └── 04-nudge-single-primary-button.yaml (tags: phase6, nudge)
```

### As-Is: 問題一覧

| # | ファイル | 問題 | 影響 |
|---|---------|------|------|
| P-1 | （存在しない） | `config.yaml` がない | Maestro がフローを1つも認識しない → CI即死 |
| P-2 | `nudge/05-phase5-thompson-sampling.yaml:8` | `runFlow: 01-onboarding.yaml` → 呼び出し元からの相対パスで `nudge/01-onboarding.yaml` を探す → 存在しない | フロー実行時にエラー |
| P-3 | `nudge/15-nudge-card-loading-speed.yaml:17` | `file: 01-onboarding-fixed.yaml` → 削除済みファイルを参照 | フロー実行時にエラー |
| P-4 | `nudge/05-phase5-thompson-sampling.yaml` | `tags:` セクションがない | `--include-tags` で永遠にスキップ |
| P-5 | `nudge/06-phase5-unresponsive-simulation.yaml` | `tags:` セクションがない | `--include-tags` で永遠にスキップ |

### To-Be: 修正後のディレクトリ構造

```
aniccaios/maestro/
├── config.yaml                 ← 【新規作成】
├── onboarding/
│   ├── 01-onboarding.yaml      (tags: smokeTest, onboarding) — 変更なし
│   ├── 02-live-demo.yaml       (tags: onboarding, liveDemo) — 変更なし
│   └── 03-soft-paywall.yaml    (tags: onboarding, paywall) — 変更なし
└── nudge/
    ├── 05-phase5-thompson-sampling.yaml     (tags: phase5, nudge) ← タグ追加 + runFlow パス修正
    ├── 06-phase5-unresponsive-simulation.yaml (tags: phase5, nudge) ← タグ追加
    ├── 15-nudge-card-loading-speed.yaml     (tags: performance, nudge) ← runFlow パス修正
    └── phase6/
        ├── 01-llm-nudge-display.yaml        — 変更なし
        ├── 02-feedback-flow.yaml            — 変更なし
        ├── 03-feedback-thumbs-down.yaml     — 変更なし
        └── 04-nudge-single-primary-button.yaml — 変更なし
```

### To-Be: 各ファイルの変更内容

#### T-1: `aniccaios/maestro/config.yaml`（新規作成）

```yaml
# Maestro Test Suite Configuration
# サブディレクトリのフローを認識させるための設定
# 注意: 新しいサブディレクトリを追加した場合、flows: にパターンを追記すること

executionOrder:
  continueOnFailure: false

flows:
  - "onboarding/*"
  - "nudge/*"
  - "nudge/phase6/*"
```

**根拠**: RevenueCat SDK の config.yaml（`aniccaios/build/SourcePackages/checkouts/purchases-ios/Examples/rc-maestro/maestro/config.yaml`）と同じパターン。Maestro 公式ドキュメントの [Test Suites and Reports](https://maestro.mobile.dev/cli/test-suites-and-reports#inclusion-patterns) に準拠。

#### T-2: `nudge/05-phase5-thompson-sampling.yaml`（修正）

| 行 | Before | After |
|----|--------|-------|
| 1-2 | `appId: ai.anicca.app.ios` | `appId: ai.anicca.app.ios`<br>`name: "Phase 5: Thompson Sampling"`<br>`tags:`<br>`  - phase5`<br>`  - nudge` |
| 8 | `- runFlow: 01-onboarding.yaml` | `- runFlow: ../onboarding/01-onboarding.yaml` |

#### T-3: `nudge/06-phase5-unresponsive-simulation.yaml`（修正）

| 行 | Before | After |
|----|--------|-------|
| 1-2 | `appId: ai.anicca.app.ios` | `appId: ai.anicca.app.ios`<br>`name: "Phase 5: Unresponsive Simulation"`<br>`tags:`<br>`  - phase5`<br>`  - nudge` |

（runFlow 参照なし — 変更不要）

#### T-4: `nudge/15-nudge-card-loading-speed.yaml`（修正）

| 行 | Before | After |
|----|--------|-------|
| 16-18 | `- runFlow:`<br>`    when:`<br>`      notVisible: "tab-mypath"`<br>`    file: 01-onboarding-fixed.yaml` | `- runFlow:`<br>`    when:`<br>`      notVisible: "tab-mypath"`<br>`    file: ../onboarding/01-onboarding.yaml` |

**理由**: `01-onboarding-fixed.yaml` は既に削除済み（前回の maestro cleanup spec で対応済み）。正しいファイルは `../onboarding/01-onboarding.yaml`。

---

## テストマトリックス

### TDD サイクル（RED → GREEN → REFACTOR）

このタスクは Maestro YAML ファイル（テスト設定ファイル自体）の修正なので、通常の Swift Unit Test ではなく、**Maestro CLI の実行結果がテスト**となる。

| # | 対応 To-Be | テスト方法 | テストコマンド | 期待結果 |
|---|-----------|-----------|---------------|----------|
| TM-1 | T-1 (config.yaml) | Maestro がフローを列挙する | `maestro test aniccaios/maestro/ --include-tags smokeTest 2>&1 \| head -20` | フロー名が表示される（"Top-level directories do not contain any Flows" エラーが出ない） |
| TM-2 | T-2 (nudge/05 パス) | フロー実行でパスエラーなし | `maestro test aniccaios/maestro/nudge/05-phase5-thompson-sampling.yaml` | パス解決エラーなし |
| TM-3 | T-4 (nudge/15 パス) | フロー実行でパスエラーなし | `maestro test aniccaios/maestro/nudge/15-nudge-card-loading-speed.yaml` | パス解決エラーなし |
| TM-4 | T-2, T-3 (タグ追加) | include-tags で発見される | `maestro test aniccaios/maestro/ --include-tags phase5 2>&1 \| grep -c "phase5"` | 2件ヒット |
| TM-5 | 全体統合 | CIと同じコマンドでパス | `maestro test aniccaios/maestro/ --include-tags smokeTest,phase6` | 5フロー実行（smokeTest: 1 + phase6: 4） |
| TM-6 | AC-6 (CI) | GitHub Actions で成功 | `git push` → `gh run watch` → `gh run view --log-failed` | E2E Tests (Maestro) ジョブが緑 |

### タグ別フロー一覧（修正後）

| タグ | 該当フロー | 件数 |
|------|-----------|------|
| `smokeTest` | `onboarding/01-onboarding.yaml` | 1 |
| `onboarding` | `onboarding/01-*.yaml`, `02-*.yaml`, `03-*.yaml` | 3 |
| `phase5` | `nudge/05-*.yaml`, `nudge/06-*.yaml` | 2 |
| `phase6` | `nudge/phase6/01-*.yaml` ~ `04-*.yaml` | 4 |
| `nudge` | `nudge/05-*`, `06-*`, `15-*`, `phase6/01-*` ~ `04-*` | 7 |
| `performance` | `nudge/15-*.yaml` | 1 |
| `feedback` | `nudge/phase6/02-*.yaml`, `03-*.yaml` | 2 |
| `liveDemo` | `onboarding/02-*.yaml` | 1 |
| `paywall` | `onboarding/03-*.yaml` | 1 |

### CIで実行されるフロー（`--include-tags smokeTest,phase6`）

| # | フロー | マッチするタグ |
|---|--------|---------------|
| 1 | `onboarding/01-onboarding.yaml` | smokeTest |
| 2 | `nudge/phase6/01-llm-nudge-display.yaml` | phase6 |
| 3 | `nudge/phase6/02-feedback-flow.yaml` | phase6 |
| 4 | `nudge/phase6/03-feedback-thumbs-down.yaml` | phase6 |
| 5 | `nudge/phase6/04-nudge-single-primary-button.yaml` | phase6 |

---

## 境界

### 触るファイル

| ファイル | 操作 |
|---------|------|
| `aniccaios/maestro/config.yaml` | 新規作成 |
| `aniccaios/maestro/nudge/05-phase5-thompson-sampling.yaml` | 修正（tags追加 + runFlowパス修正） |
| `aniccaios/maestro/nudge/06-phase5-unresponsive-simulation.yaml` | 修正（tags追加） |
| `aniccaios/maestro/nudge/15-nudge-card-loading-speed.yaml` | 修正（runFlowパス修正） |

### 触らないファイル

| ファイル | 理由 |
|---------|------|
| `aniccaios/maestro/onboarding/*.yaml` | 問題なし、変更不要 |
| `aniccaios/maestro/nudge/phase6/*.yaml` | 問題なし、変更不要 |
| `.github/workflows/ios-ci.yml` | CIコマンド自体は正しい。config.yaml で解決 |
| Swift ソースコード | 今回のスコープ外 |
| `aniccaios/build/` 内の RevenueCat maestro | SPM 依存、gitignore 済み、制御不能 |

### やらないこと

| 項目 | 理由 |
|------|------|
| 新規 Maestro フロー追加 | 今回は既存フローの CI 修正のみ |
| accessibilityIdentifier 追加 | Swift 側変更は別スコープ |
| `nudge/05-*`, `nudge/06-*` のフロー内容修正 | Phase 5 Debug UI への依存は今回触らない |
| Maestro Cloud / BrowserStack 導入 | 将来検討 |

---

## 実行手順

**CLI使用の例外**: 本タスクはMaestro CI基盤の修正であり、`--include-tags` フィルタリングの検証が本質的に必要。ローカル検証では MCP (`mcp__maestro__run_flow_files`) を優先するが、**タグフィルタの検証とCI再現テストに限り CLI 直接使用を許可**する。

### Phase 1: RED（テストが失敗することを確認）

```bash
# 現状のCIエラーを再現
maestro test aniccaios/maestro/ --include-tags smokeTest,phase6
# 期待: "Top-level directories do not contain any Flows" で exit 1
```

### Phase 2: GREEN（最小限の修正でテストを通す）

```bash
# Step 1: config.yaml 作成
# → aniccaios/maestro/config.yaml を作成

# Step 2: 動作確認（フローが認識されるか）
maestro test aniccaios/maestro/ --include-tags smokeTest 2>&1 | head -20
# 期待: フロー名が表示される

# Step 3: runFlow パス修正
# → nudge/05-*.yaml, nudge/15-*.yaml を修正

# Step 4: タグ追加
# → nudge/05-*.yaml, nudge/06-*.yaml に tags 追加

# Step 5: 統合テスト（CIと同じコマンド）
maestro test aniccaios/maestro/ --include-tags smokeTest,phase6
# 期待: 5フロー実行、全 PASS
```

### Phase 3: CI 検証

```bash
# Step 1: commit & push
git add aniccaios/maestro/config.yaml aniccaios/maestro/nudge/05-phase5-thompson-sampling.yaml aniccaios/maestro/nudge/06-phase5-unresponsive-simulation.yaml aniccaios/maestro/nudge/15-nudge-card-loading-speed.yaml
git commit -m "fix(maestro): add config.yaml for subdirectory flow discovery + fix runFlow paths"
git push

# Step 2: CI 監視
gh run list --workflow ios-ci.yml -L 1
gh run watch <run-id>

# Step 3: 失敗時のデバッグ
gh run view <run-id> --log-failed

# Step 4: 失敗 → 修正 → 再push → 再監視（通るまでループ）
```

### Phase 4: REFACTOR（テストが通った後）

```bash
# flakiness チェック（3回連続成功）
for i in {1..3}; do
  echo "=== Run $i ==="
  maestro test aniccaios/maestro/ --include-tags smokeTest,phase6
done
```

---

## E2E判定

| 項目 | 値 |
|------|-----|
| UI変更 | なし（Maestro設定ファイルの修正のみ） |
| 新画面 | なし |
| 新ボタン/操作 | なし |
| 結論 | Maestro E2Eシナリオ: **不要**（今回は E2E テスト基盤自体の修正であり、アプリ UI は変更しない） |

---

## リスク

| リスク | 確率 | 影響 | 対策 |
|--------|------|------|------|
| config.yaml の `flows:` パターンが間違っている | 低 | CI失敗継続 | RevenueCat SDK の実例に準拠。ローカルで先に検証 |
| `runFlow` の相対パス解決がMaestroバージョンで異なる | 低 | 特定フロー失敗 | Maestro公式: 呼び出し元ファイルからの相対パス。ローカル検証で確認 |
| `nudge/05-*`, `nudge/06-*` が Phase 5 Debug UI に依存（DEBUG ビルド前提） | 中 | CI の staging ビルドで Debug セクションが非表示の場合失敗 | `--include-tags smokeTest,phase6` では phase5 タグは含まれないので CI には影響なし。phase5 フローは手動実行用 |
| CIのシミュレータ起動が遅くタイムアウト | 低 | E2E失敗 | 既存フローは `extendedWaitUntil` + `timeout: 15000-30000` で対策済み |
| 将来サブディレクトリ追加時に config.yaml 更新忘れ | 中 | 新フローがCIで実行されない | config.yaml にコメントで「サブディレクトリ追加時は flows: に追記すること」と注記 |

---

## 前回 Spec との関係

| Spec | 状態 | 今回との関係 |
|------|------|-------------|
| `spec-maestro-cleanup-and-best-practices.md` (2026-02-02) | 実行済み（ルート`maestro/`削除、`01-onboarding-fixed.yaml`削除、`visible:true`修正、スキル作成） | 前回の残課題を引き継ぎ。前回は「フォルダ統一 + 構文修正」、今回は「CI でフローが認識されない根本原因の修正」 |

---

## 完了条件チェックリスト

| # | 条件 | 検証方法 | 状態 |
|---|------|---------|------|
| 1 | `aniccaios/maestro/config.yaml` が存在する | `ls aniccaios/maestro/config.yaml` | 未着手 |
| 2 | `01-onboarding-fixed.yaml` への参照が0件 | `grep -r "onboarding-fixed" aniccaios/maestro/` | 未着手 |
| 3 | 全 `.yaml` フローに `tags:` セクションがある | `grep -rL "tags:" aniccaios/maestro/ --include="*.yaml" \| grep -v config` → 0件 | 未着手 |
| 4 | ローカルで `maestro test aniccaios/maestro/ --include-tags smokeTest,phase6` が PASS | 手動実行 | 未着手 |
| 5 | GitHub Actions `E2E Tests (Maestro)` ジョブが成功 | `gh run view --log-failed` でエラーなし | 未着手 |
| 6 | 3回連続ローカル実行で flakiness なし | ループ実行 | 未着手 |

---

## 参照

| 資料 | パス / URL |
|------|-----------|
| CI ワークフロー | `.github/workflows/ios-ci.yml` |
| Maestro スキル | `.claude/skills/maestro-ui-testing/SKILL.md` |
| 前回 Spec | `.cursor/plans/ios/1.6.1/spec-maestro-cleanup-and-best-practices.md` |
| Maestro公式: Test Suites | https://maestro.mobile.dev/cli/test-suites-and-reports#inclusion-patterns |
| RevenueCat config.yaml 実例 | `aniccaios/build/SourcePackages/checkouts/purchases-ios/Examples/rc-maestro/maestro/config.yaml` |
