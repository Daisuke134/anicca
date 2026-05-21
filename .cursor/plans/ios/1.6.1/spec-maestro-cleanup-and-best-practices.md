# Maestro E2Eテスト改善仕様書

**作成日**: 2026-02-02  
**ステータス**: 実行中  
**優先度**: 高（CIが壊れている）

---

## 背景

### 現状の問題

| 問題 | 影響 |
|------|------|
| CIで毎回Maestroテストが失敗 | PRマージ不可、開発効率低下 |
| `visible: true` のYAML構文エラー | 「"true"というテキストを待つ」と解釈される |
| 2つのMaestroフォルダが存在 | どっちが正解か不明、混乱 |
| `optional: true` の乱用 | 失敗しても無視、実際のUI検証がない |
| `point:` セレクターの使用 | 画面サイズ・解像度で失敗 |
| エージェントがMaestroを理解していない | 毎回クソみたいなテストを生成 |

### 失敗ログ例
```
[Failed] Onboarding flow (1m 13s) (Assertion is false: "true" is visible)
```

---

## ゴール

| ゴール | 成功基準 |
|--------|----------|
| CIでMaestroテストが100%パス | `smokeTest` タグ付きテストが全て通る |
| 1つのMaestroフォルダに統一 | `aniccaios/maestro/` のみ存在（CI参照先） |
| ベストプラクティススキル導入 | エージェントが正しいテストを書ける |
| 実際のUI操作を検証 | タップ→遷移→確認の流れ |

---

## スコープ

### IN SCOPE

| タスク | 詳細 |
|--------|------|
| ルート `/maestro/` 削除 | ルートに存在する場合のみ削除 |
| `aniccaios/maestro/01-onboarding-fixed.yaml` 削除 | 古いバージョン |
| `aniccaios/maestro/01-onboarding.yaml` 修正 | `visible: true` バグ修正済み |
| Maestro UIテストスキル作成 | `.claude/skills/maestro-ui-testing/SKILL.md` 作成済み |
| タイムアウト増加 | 5000ms → 15000ms (CI安定性) |

### OUT OF SCOPE

| タスク | 理由 |
|--------|------|
| 新規テスト追加 | 今回はクリーンアップのみ |
| accessibilityIdentifier追加（Swift側） | 別タスク |
| Maestro Cloudへの移行 | 将来検討 |

---

## 実装計画

### Phase 1: クリーンアップ（今回）

| # | タスク | ステータス |
|---|--------|----------|
| 1 | ルート `/maestro/` フォルダ削除（存在する場合） | **未確認** |
| 2 | `aniccaios/maestro/01-onboarding-fixed.yaml` 削除 | **未確認** |
| 3 | `aniccaios/maestro/01-onboarding.yaml` の `visible: true` バグ修正 | **未確認** |
| 4 | タイムアウトを15000msに増加 | **完了** |
| 5 | Maestroスキル作成 | **完了** |

### Phase 2: SwiftUI側対応（将来）

| # | タスク | ステータス |
|---|--------|----------|
| 1 | 全ViewにaccessibilityIdentifier追加 | 未着手 |
| 2 | Paywall閉じるボタンにID追加（`point:`排除） | 未着手 |
| 3 | テストカバレッジ拡大 | 未着手 |

---

## ファイル変更一覧

### 削除するファイル/フォルダ

```
maestro/                               # ルートに存在する場合のみ削除対象
maestro/01-onboarding-fixed.yaml       # ルートに存在する場合のみ削除対象

aniccaios/maestro/01-onboarding-fixed.yaml  # 古いバージョン
```

### 修正済みファイル

```
aniccaios/maestro/01-onboarding.yaml   # visible: true バグ修正 + タイムアウト増加
```

### 新規作成済みファイル

```
.claude/skills/maestro-ui-testing/SKILL.md    # ベストプラクティススキル
```

---

## ベストプラクティス（スキルに記載済み）

### セレクター優先順位

| 優先度 | 種類 | 例 | 安定性 |
|--------|------|-----|--------|
| 1 | `id:` (accessibilityIdentifier) | `id: "onboarding-cta"` | 最高 |
| 2 | `text:` | `text: "Get Started"` | 中（ローカライズで変わる） |
| 3 | `point:` | `point: "28,78"` | **最悪（使用禁止）** |

### 正しいテストパターン

```yaml
# 1. タップ
- tapOn:
    id: "button-id"

# 2. 遷移を待つ
- extendedWaitUntil:
    visible:
      id: "next-screen-element"
    timeout: 15000

# 3. 確認
- assertVisible:
    id: "expected-element"
```

### optional: true の使い方

```yaml
# GOOD: システムダイアログ（出現が不確定）
- tapOn:
    text: "許可|Allow"
    optional: true

# BAD: 通常のUI操作
- tapOn:
    id: "button"
    optional: true  # ← 失敗を無視するので検証にならない
```

---

## 検証方法

### ローカル検証

```bash
# 1. シミュレータ起動
xcrun simctl boot "iPhone 16 Pro"

# 2. アプリビルド&インストール
cd aniccaios
xcodebuild build -scheme aniccaios-staging -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -derivedDataPath ./build
xcrun simctl install booted "./build/Build/Products/staging Debug-iphonesimulator/aniccaios.app"

# 3. Maestroテスト実行
maestro test ../maestro/ --include-tags smokeTest

# 4. 3回連続成功を確認（flakiness check）
for i in {1..3}; do maestro test ../maestro/ --include-tags smokeTest; done
```

### CI検証

- Push to dev → ios-ci.yml が自動実行
- E2E Tests (Maestro) ジョブが成功することを確認

---

## リスク

| リスク | 対策 |
|--------|------|
| ルート `/maestro/` 削除で何か壊れる | CIは `aniccaios/maestro/` を参照、問題なし |
| スキルが読み込まれない | `.claude/skills/` に正しく配置済み |
| accessibilityIdentifier不足でテスト失敗 | 既存テストは既にID使用、今回スコープ外 |

---

## 完了条件

- [ ] ルート `/maestro/` が存在しない（または削除済み）
- [ ] `aniccaios/maestro/01-onboarding-fixed.yaml` が存在しない
- [ ] ローカルで `maestro test aniccaios/maestro/ --include-tags smokeTest` が通る
- [ ] CIの E2E Tests (Maestro) が成功

---

## 参照

- Maestroスキル: `.claude/skills/maestro-ui-testing/SKILL.md`
- Maestro公式ドキュメント: https://docs.maestro.dev/
- CI設定: `.github/workflows/ios-ci.yml`
