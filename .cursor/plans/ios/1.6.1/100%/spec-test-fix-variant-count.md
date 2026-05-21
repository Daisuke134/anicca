# テスト修正仕様書: バリアント数変更に伴うコード・テスト更新

## 概要

ProblemType.notificationVariantCount の変更（8→14、10→21）に伴い、
NudgeContent.swift と既存のテストが古いバリアント数に依存しているため失敗している。

---

## 問題（As-Is）

### 根本原因

1. **NudgeContent.swift**: `notificationMessages(for:)` と `detailMessages(for:)` がハードコードで8/10個のメッセージを返している
2. **テスト**: 古いバリアント数（8/10）を期待している

### 失敗テスト一覧

| テストファイル | テスト名 | 失敗理由 |
|---------------|---------|---------|
| NotificationHotfixTests | test_variantCount_allProblems | 古い期待値（8/10） |
| NotificationHotfixTests | test_selectVariant_allUsed_returnsFirst | 古い期待値 |
| NotificationHotfixTests | test_selectVariant_respectsUsedVariants | 古い期待値 |
| NudgeLocalizationTests | test_notificationMessages_countMatchesVariantCount | NudgeContent.swift が8/10個しか返さない |
| NudgeLocalizationTests | test_detailMessages_countMatchesVariantCount | 同上 |
| NudgeContentSelectorTests | test_selectVariant_returns_valid_variant_for_other_problems | 範囲チェック失敗 |
| NudgeContentSelectorTests | test_selectVariant_returns_valid_variant_for_stayingUpLate | 範囲チェック失敗 |
| NudgeContentSelectorTests | test_selectVariant_stayingUpLate_allVariantsAreGeneric | バリアント数不一致 |

---

## 解決策（To-Be）

### 1. NudgeContent.swift 修正（根本修正）

**変更内容:**
- `notificationMessages(for:)` を動的生成に変更
- `detailMessages(for:)` を動的生成に変更
- `ProblemType.notificationVariantCount` を使用して動的にメッセージ配列を生成

```swift
// Before: ハードコード
case .stayingUpLate:
    return [
        NSLocalizedString("nudge_staying_up_late_notification_1", comment: ""),
        // ... 10個
    ]

// After: 動的生成
static func notificationMessages(for problem: ProblemType) -> [String] {
    let prefix = problem.rawValue
    return (1...problem.notificationVariantCount).map { i in
        NSLocalizedString("nudge_\(prefix)_notification_\(i)", comment: "")
    }
}
```

### 2. NotificationHotfixTests.swift 修正

**変更内容:**
- `test_variantCount_allProblems`: 期待値を14（default）と21（stayingUpLate）に更新
- `test_selectVariant_allUsed_returnsFirst`: usedVariants配列のサイズを14に更新
- `test_selectVariant_respectsUsedVariants`: usedVariants配列のサイズを更新

### 3. NudgeContentSelectorTests.swift 修正

**変更内容:**
- `test_selectVariant_returns_valid_variant_for_other_problems`: 範囲を0-13に更新
- `test_selectVariant_returns_valid_variant_for_stayingUpLate`: 範囲を0-20に更新
- `test_selectVariant_stayingUpLate_allVariantsAreGeneric`: バリアント数を21に更新

---

## 影響範囲

| ファイル | 変更内容 |
|---------|---------|
| `aniccaios/Models/NudgeContent.swift` | 動的メッセージ生成に変更 |
| `aniccaiosTests/NotificationHotfixTests.swift` | バリアント数の期待値更新 |
| `aniccaiosTests/NudgeContentSelectorTests.swift` | 範囲チェックの期待値更新 |

---

## テスト計画

修正後、以下のコマンドでテストを実行:

```bash
cd aniccaios && fastlane test
```

**期待結果:** 全テスト Pass

---

*Last updated: 2026-02-03*
