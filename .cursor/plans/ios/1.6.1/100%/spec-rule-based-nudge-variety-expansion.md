# Rule-based Nudge Variety 拡張仕様書

## 概要

ルールベースNudgeのバリアント数を拡張し、2週間の新鮮なメッセージ体験を提供する。
LLM生成が不安定な場合のフォールバックとしても機能する。

---

## 問題（As-Is）

### 現象

| ProblemType | バリアント数 | スロット/日 | 一周するまで |
|-------------|-------------|------------|-------------|
| staying_up_late | 10 | 5 | **2日** |
| porn_addiction | 8 | 3 | **2.67日** |
| その他11種類 | 8 | 3 | **2.67日** |

**結果**: Day 3から「あれ、このメッセージ前にも見た」→ 飽き → 通知オフ → 解約

### Day-Cycling計算式

```javascript
variantIndex = (dayIndex * slotsPerDay + slotIndexInProblem) % totalVariants
```

**porn_addiction（8バリアント）の例**:

| Day | 20:30 | 22:30 | 23:45 |
|-----|-------|-------|-------|
| Day 1 | V1 | V2 | V3 |
| Day 2 | V4 | V5 | V6 |
| Day 3 | V7 | V8 | **V1（繰り返し開始）** |

---

## 解決策（To-Be）

### 目標

| ProblemType | バリアント数 | スロット/日 | 一周するまで |
|-------------|-------------|------------|-------------|
| staying_up_late | **21** | 5 | **4.2日** |
| その他12種類 | **14** | 3 | **4.67日** |

**結果**: トライアル1週間で同じメッセージは1-2回のみ → 新鮮さ維持 → 継続 → 課金

### porn_addiction（14バリアント）の例

| Day | 20:30 | 22:30 | 23:45 |
|-----|-------|-------|-------|
| Day 1 | V1 | V2 | V3 |
| Day 2 | V4 | V5 | V6 |
| Day 3 | V7 | V8 | V9 |
| Day 4 | V10 | V11 | V12 |
| Day 5 | V13 | V14 | **V1（繰り返し開始）** |

---

## 実装変更

### 1. ProblemType.swift 更新

**ファイル**: `aniccaios/aniccaios/Models/ProblemType.swift`

```swift
// Before
var notificationVariantCount: Int {
    switch self {
    case .stayingUpLate: return 10
    default: return 8
    }
}

// After
var notificationVariantCount: Int {
    switch self {
    case .stayingUpLate: return 21  // 5回/日 × 4.2日
    default: return 14              // 3回/日 × 4.67日
    }
}
```

### 2. Localizable.strings 更新（1.6.1では日本語+英語のみ）

**対象ファイル（1.6.1）**:
- `aniccaios/aniccaios/Resources/ja.lproj/Localizable.strings`
- `aniccaios/aniccaios/Resources/en.lproj/Localizable.strings`

**1.6.2で追加予定**:
- `aniccaios/aniccaios/Resources/es.lproj/Localizable.strings`
- `aniccaios/aniccaios/Resources/fr.lproj/Localizable.strings`
- `aniccaios/aniccaios/Resources/de.lproj/Localizable.strings`
- `aniccaios/aniccaios/Resources/pt-BR.lproj/Localizable.strings`

**追加するキー（各問題で notification_9 〜 notification_14、detail_9 〜 detail_14）**:

```
// porn_addiction の例（日本語）
"nudge_porn_addiction_notification_9" = "今日も勝てる。昨日も勝った。";
"nudge_porn_addiction_notification_10" = "30秒だけ待て。それで変わる。";
...
"nudge_porn_addiction_detail_9" = "毎日の小さな勝利が積み重なる。今日も勝てば、明日はもっと楽。";
...
```

**staying_up_late は notification_11 〜 notification_21 を追加（別紙 `nudge-content-variants-ja.md` にて作成済み）**。

### 3. 通知タイトル変更（porn_addiction）

**変更理由**: 「衝動に勝て」は曖昧。より直接的な表現に変更。

| 言語 | Before | After | 対応バージョン |
|------|--------|-------|---------------|
| 日本語 | 衝動に勝て | **性欲に勝て** | 1.6.1 |
| English | Beat the Urge | **Beat Your Lust** | 1.6.1 |
| Español | Beat the Urge | **Vence Tu Lujuria** | 1.6.2 |
| Français | Beat the Urge | **Maîtrise Ton Désir** | 1.6.2 |
| Deutsch | Beat the Urge | **Besiege Deine Lust** | 1.6.2 |
| Português | Beat the Urge | **Vença Sua Luxúria** | 1.6.2 |

**対象キー**: `problem_porn_addiction_notification_title`
**注意**: 1.6.1では日本語と英語のみ変更。他言語は1.6.2で対応。

---

## 新規コンテンツ

### コンテンツ設計原則

**Tone配分（6バリアント追加の場合）**: 各ProblemTypeの新規6バリアントは以下のバランスで作成:
- strict: 2個（命令口調）
- gentle: 1個（優しく寄り添う）
- empathetic: 1個（共感的）
- analytical: 1個（論理的・データ的）
- playful: 1個（軽やかで親しみやすい）

**Tone配分（staying_up_late: 11バリアント追加の場合）**: 以下のバランスで作成:
- strict: 4個（命令口調）
- gentle: 2個（優しく寄り添う）
- empathetic: 2個（共感的）
- analytical: 2個（論理的・データ的）
- playful: 1個（軽やかで親しみやすい）

**Detail要件**: 各Detailは**必ず1つ以上の具体的アクション**を含む:
- 数えろ、書け、立て、歩け、置け、言え、送れ、等

### コンテンツファイル

**別紙**: `nudge-content-variants-ja.md`
- 日本語 + 英語の全バリアント（9-14、staying_up_lateは11-21）
- Toneラベル付き

**注意**: 1.6.1では日本語と英語のみ実装。他言語（es, fr, de, pt-BR）は1.6.2で英語をベースに翻訳予定。

---

## テスト計画

### ユニットテスト（iOS）

| テスト | 期待結果 |
|-------|---------|
| `ProblemType.stayingUpLate.notificationVariantCount` | 21 |
| `ProblemType.pornAddiction.notificationVariantCount` | 14 |
| `ProblemType.anxiety.notificationVariantCount` | 14（default確認） |
| `NudgeContent.notificationMessages(for: .stayingUpLate).count` | 21 |
| `NudgeContent.notificationMessages(for: .pornAddiction).count` | 14 |
| `NudgeContent.detailMessages(for: .stayingUpLate).count` | 21 |
| `NudgeContent.detailMessages(for: .pornAddiction).count` | 14 |

### ローカライズテスト（iOS）- 1.6.1はJA/ENのみ

| テスト | 期待結果 |
|-------|---------|
| JA/ENで `nudge_*_notification_1` 〜 `_14` が存在 | Pass |
| JA/ENで `nudge_*_detail_1` 〜 `_14` が存在 | Pass |
| JA/ENでstaying_up_late は `_1` 〜 `_21` が存在 | Pass |
| JA/ENで `problem_porn_addiction_notification_title` が「性欲に勝て」「Beat Your Lust」に変更済み | Pass |

**注意**: 他言語（es/fr/de/pt-BR）のテストは1.6.2で実施。

### Backendテスト

| テスト | 期待結果 |
|-------|---------|
| dayCycling: staying_up_late 35バリアントで7日間ユニーク | Pass（修正済み） |

### E2Eテスト（Maestro）

| テスト | 期待結果 |
|-------|---------|
| porn_addictionを選択 → 通知タイトルが「性欲に勝て」 | Pass |
| 7日間シミュレーション → 同じメッセージが連続しない | Pass |

---

## dayCycling.test.js 修正（完了）

**問題**: `staying_up_late` のスロット数が 6 → 5 に変更されたが、テストが旧値のまま。

**修正済み**:

```javascript
// Before
it('staying_up_late with 42 variants covers 7 days', () => {
  const variants = Array.from({ length: 42 }, ...);
  expect(result.totalSlots).toBe(42); // 6 slots * 7 days

// After ✅
it('staying_up_late with 35 variants covers 7 days', () => {
  const variants = Array.from({ length: 35 }, ...);
  expect(result.totalSlots).toBe(35); // 5 slots * 7 days (v1.6.0 schedule)
```

---

## 影響範囲（1.6.1）

| ファイル | 変更内容 | 状態 |
|---------|---------|------|
| `aniccaios/Models/ProblemType.swift` | notificationVariantCount 更新 | 未着手 |
| `aniccaios/Resources/ja.lproj/Localizable.strings` | 新バリアント追加 + タイトル変更 | 未着手 |
| `aniccaios/Resources/en.lproj/Localizable.strings` | 新バリアント追加 + タイトル変更 | 未着手 |
| `apps/api/src/agents/__tests__/dayCycling.test.js` | 期待値修正（42→35） | ✅ 完了 |

## 影響範囲（1.6.2 - 他言語対応）

| ファイル | 変更内容 | 状態 |
|---------|---------|------|
| `aniccaios/Resources/es.lproj/Localizable.strings` | 新バリアント追加 + タイトル変更 | 1.6.2で対応 |
| `aniccaios/Resources/fr.lproj/Localizable.strings` | 新バリアント追加 + タイトル変更 | 1.6.2で対応 |
| `aniccaios/Resources/de.lproj/Localizable.strings` | 新バリアント追加 + タイトル変更 | 1.6.2で対応 |
| `aniccaios/Resources/pt-BR.lproj/Localizable.strings` | 新バリアント追加 + タイトル変更 | 1.6.2で対応 |

---

## デプロイ

1. iOS変更あり（Localizable.strings + ProblemType.swift）
2. Backend変更なし（dayCycling.jsはそのまま動作）
3. App Store提出が必要（コンテンツ変更）

---

## 今後の拡張

| Phase | 内容 |
|-------|------|
| 1.6.1 | 14バリアント拡張 - 日本語 + 英語のみ（本Spec） |
| 1.6.2 | 他言語のバリアント翻訳（es, fr, de, pt-BR）- 英語ベースで翻訳 |
| 1.7.x | LLM生成が安定したらルールベースをフォールバック専用に |

**注意**: 1.6.1では日本語と英語のみ実装。他言語（es, fr, de, pt-BR）は既存の1-8バリアントのまま。1.6.2で追加翻訳を実施。

---

*Last updated: 2026-02-02*
