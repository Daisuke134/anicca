# Phase 3 実装仕様書

**作成日**: 2026-01-18
**更新日**: 2026-01-18
**対象**: Proactive Agent Phase 3 実装
**参照**: proactive-agent-spec.md

---

## 目次

1. [概要](#1-概要)
2. [AS-IS（現状）](#2-as-is現状)
3. [TO-BE（あるべき姿）](#3-to-beあるべき姿)
4. [修正パッチ一覧](#4-修正パッチ一覧)
5. [詳細仕様](#5-詳細仕様)
6. [ローカライゼーション](#6-ローカライゼーション)
7. [Phase 4以降の予定](#7-phase-4以降の予定)

---

## 1. 概要

### 目的
- Phase 1-3で決めた仕様を完全に実装する
- ローカライゼーション（日本語/英語）を完全にする
- My PathタブのUI/UXを仕様通りにする

### スコープ
- Profile画面のセクション非表示
- NudgeContent多言語化
- ProblemType多言語化（ボタン、タイトル）
- DeepDiveQuestions多言語化（選択肢UI含む）
- MyPathTabViewのUI改善
- 「Aniccaに伝える」機能
- カスタム課題対応
- 既存ユーザーマイグレーション
- デバッグ機能

### Phase 1-2で実装済み（参考）

| 項目 | ファイル | 状態 |
|------|---------|------|
| NudgeCardView（1枚画面カード） | `Views/NudgeCardView.swift` | ✅ 存在 |
| ProblemNotificationScheduler | `Notifications/ProblemNotificationScheduler.swift` | ✅ 存在 |
| ProblemType enum | `Models/ProblemType.swift` | ✅ 存在（13問題） |
| NudgeContent | `Models/NudgeContent.swift` | ✅ 存在（日本語のみ） |
| Talkタブ非表示 | `Components/FigmaTabBar.swift` | ✅ 完了 |

---

## 2. AS-IS（現状）

### 2.1 NudgeCardView.swift（Phase 2で実装済み）

**現状**: 完全に実装済み
- 1択ボタン / 2択ボタン対応
- フィードバックボタン（👍👎）
- `content.problemType.positiveButtonText` 等を使用

**問題点**: `positiveButtonText` 等が日本語ハードコードのため、英語対応が必要

### 2.2 ProblemType.swift

**現状のボタン文言（日本語ハードコード）**:

```swift
// positiveButtonText (L79-109)
case .stayingUpLate:
    return "明日を守る 💪"
case .cantWakeUp:
    return "今日を始める ☀️"
// ...

// negativeButtonText (L112-138)
case .stayingUpLate:
    return "傷つける"
case .cantWakeUp:
    return "逃げる"
// ...

// notificationTitle (L193-222)
case .stayingUpLate:
    return "就寝"
case .selfLoathing:
    return "Self-Compassion"
// ...
```

**問題**: 英語版がない

### 2.3 Profile画面のstrugglesリスト

**ProfileView.swift:234-235**
```swift
options: ["procrastination", "anxiety", "poor_sleep", "stress", "focus", "motivation", "self_doubt", "time_management", "burnout", "relationships", "energy", "work_life_balance"]
```

**問題**: 古い12問題リスト（Phase 3では非表示にするため更新不要）

### 2.4 NudgeContent.swift

**現状**: 通知文言・詳細文言がすべて日本語ハードコード

```swift
case .stayingUpLate:
    return [
        "スクロールより、呼吸。",
        "その「あと5分だけ」で、何年失ってきた？",
        ...
    ]
```

**問題**: 英語版がない

### 2.5 MyPathTabView.swift

**現状**:
- 日本語ハードコード（L13, L58, L63, L103, L133）
- 「深掘りする」ボタンが独立している（カード全体タップではない）
- 深掘りシートは質問リストのみ（選択肢なし、保存ボタンなし）
- 「＋ 課題を追加」ボタンなし
- 「Aniccaに伝える」セクションなし

### 2.6 DeepDiveQuestions

**現状**: 質問のみ、選択肢なし、日本語のみ

### 2.7 デバッグ機能

**現状**: ProfileViewに撮影用ボタンはあるが、Nudge/通知テストボタンなし

### 2.8 Memory.swift

**現状**: ❌ 存在しない（作成必要）

### 2.9 既存ユーザーの struggles データ

**現状**: 古いキー（`poor_sleep`, `stress`, `focus`, `motivation`, `self_doubt`）が保存されている可能性あり

**問題**: 新しい13問題タイプへのマイグレーションが必要

---

## 3. TO-BE（あるべき姿）

### 3.1 My PathタブのUI

```
┌─────────────────────────────────────┐
│  My Path                            │
│                                     │
│  [説明文]                           │
│  Aniccaはあなたの苦しみを理解し、   │
│  適切なタイミングで寄り添います。    │
│                                     │
│  ── 今向き合っている課題 ──         │
│                                     │
│  ┌─────────────────────────────┐    │
│  │ 🌙 夜更かし              →  │    │  ← カード全体タップで深掘りシート
│  └─────────────────────────────┘    │
│  ┌─────────────────────────────┐    │
│  │ 💭 反芻                  →  │    │
│  └─────────────────────────────┘    │
│                                     │
│  ＋ 課題を追加                       │
│                                     │
│  ── Aniccaに伝える ──               │
│                                     │
│  ┌─────────────────────────────┐    │
│  │ ✏️ 今辛いのは...             │    │
│  └─────────────────────────────┘    │
│  ┌─────────────────────────────┐    │
│  │ 🎯 取り組んでいる目標は...    │    │
│  └─────────────────────────────┘    │
│  ┌─────────────────────────────┐    │
│  │ 💭 覚えておいてほしいのは... │    │
│  └─────────────────────────────┘    │
│                                     │
└─────────────────────────────────────┘
```

### 3.2 空状態

```
┌─────────────────────────────────────┐
│  My Path                            │
│                                     │
│  [説明文]                           │
│                                     │
│  ── 今向き合っている課題 ──         │
│                                     │
│         🍃                          │
│                                     │
│    向き合いたい課題を               │
│    追加してみましょう               │
│                                     │
│    [＋ 課題を追加]                   │  ← 1つの明確なアクション
│                                     │
│  ── Aniccaに伝える ──               │
│  ...                                │
└─────────────────────────────────────┘
```

### 3.3 「＋ 課題を追加」シート

```
┌─────────────────────────────────────┐
│  ╳              課題を追加          │
│                                     │
│  [夜更かし ✓] [起きれない] [自己嫌悪]│
│  [反芻 ✓] [先延ばし] [不安]         │
│  [嘘をつく] [悪口] [ポルノ依存]      │
│  [お酒依存] [怒り] [強迫的思考]      │
│  [孤独]                             │
│                                     │
│  ──────────────────────────────     │
│  ✏️ その他（自由入力）              │
│  ┌─────────────────────────────┐    │
│  │                             │    │
│  └─────────────────────────────┘    │
│                                     │
│         [追加]                       │
│                                     │
└─────────────────────────────────────┘
```

**設計決定**:
- 設定済み課題は `✓` マーク + グレーアウト（選択不可）
- 非表示にしない（発見性確保、達成感）
- チップ形式（横並び）でスクロール最小化
- 下に自由入力欄

### 3.4 深掘りシート

```
┌─────────────────────────────────────┐
│  ╳                    夜更かし      │
│                                     │
│  🌙                                 │
│                                     │
│  ──────────────────────────────     │
│                                     │
│  どのくらい前からこの問題がある？    │  ← 共通質問
│                                     │
│  [最近] [数ヶ月] [1年以上] [ずっと]  │
│                                     │
│  ──────────────────────────────     │
│                                     │
│  夜更かしして何をしてることが多い？  │
│                                     │
│  [SNS] [YouTube] [ゲーム] [仕事]    │
│  [その他]                           │
│                                     │
│  ──────────────────────────────     │
│                                     │
│  なぜ夜更かししてしまう？            │
│                                     │
│  [今日やるべきことができなかった]    │
│  [ストレス解消] [習慣になってる]     │
│  [寝たくない]                       │
│                                     │
│  ──────────────────────────────     │
│                                     │
│         [保存]                       │
│                                     │
│  ────────────────────────────────   │
│  この課題を削除                      │  ← 削除はシート内
│                                     │
└─────────────────────────────────────┘
```

### 3.5 「Aniccaに伝える」タップ時

```
┌─────────────────────────────────────┐
│  ╳                                  │
│                                     │
│  今辛いのは                          │
│  ┌─────────────────────────────┐    │
│  │ ｜                           │    │  ← カーソル位置、キーボード自動
│  └─────────────────────────────┘    │
│                                     │
│  [キーボード]                        │
│                                     │
└─────────────────────────────────────┘
```

**送信後**:
```
┌─────────────────────────────────────┐
│                                     │
│         ✓                           │
│     覚えました                       │
│                                     │
│  [0.8秒後に自動で閉じる]             │
│                                     │
└─────────────────────────────────────┘
```

---

## 4. 修正パッチ一覧

### 4.1 ProblemType.swift（🔴 新規追加パッチ）

| # | 箇所 | AS-IS | TO-BE |
|---|------|-------|-------|
| 1 | positiveButtonText (L79-109) | 日本語ハードコード | `String(localized:)` |
| 2 | negativeButtonText (L112-138) | 日本語ハードコード | `String(localized:)` |
| 3 | notificationTitle (L193-222) | 日本語ハードコード | `String(localized:)` |

**具体的な変更**:

```swift
// BEFORE
var positiveButtonText: String {
    switch self {
    case .stayingUpLate:
        return "明日を守る 💪"
    // ...
    }
}

// AFTER
var positiveButtonText: String {
    switch self {
    case .stayingUpLate:
        return String(localized: "problem_button_positive_staying_up_late")
    // ...
    }
}
```

### 4.2 Profile画面（ProfileView.swift）

| # | 箇所 | AS-IS | TO-BE |
|---|------|-------|-------|
| ~~1~~ | ~~strugglesSection options~~ | ~~更新~~ | ~~削除（非表示にするため不要）~~ |
| 2 | traitsCard | 表示 | 非表示（コメントアウト） |
| 3 | idealsSection | 表示 | 非表示（コメントアウト） |
| 4 | strugglesSection | 表示 | 非表示（コメントアウト）※My Pathで管理 |
| 5 | stickyModeSection | 表示 | 非表示（コメントアウト） |
| 6 | recordingSection (DEBUG) | 撮影用のみ | Nudge/通知テストボタン追加 |

**注**: strugglesSection の options 更新は不要。セクション自体を非表示にするため。

### 4.3 MyPathTabView.swift

| # | 箇所 | AS-IS | TO-BE |
|---|------|-------|-------|
| 1 | L13 | `"あなたが向き合いたい問題"` | `String(localized: "mypath_header_description")` |
| 2 | L58 | `"問題が選択されていません"` | `String(localized: "mypath_empty_title")` |
| 3 | L63 | `"プロフィール設定から..."` | 削除（空状態はシンプルに） |
| 4 | L103 | `"深掘りする"` ボタン | カード全体タップ、ボタン削除 |
| 5 | L133 | `"自分を深く理解するための質問"` | 削除または `String(localized:)` |
| 6 | 新規 | なし | 「＋ 課題を追加」ボタン |
| 7 | 新規 | なし | 「Aniccaに伝える」セクション |
| 8 | 新規 | なし | 説明文セクション |

### 4.4 DeepDiveSheetView（MyPathTabView.swift内）

| # | 箇所 | AS-IS | TO-BE |
|---|------|-------|-------|
| 1 | 質問表示 | テキストリストのみ | 質問 + 選択肢チップ |
| 2 | 選択肢 | なし | spec.mdの選択肢をチップで表示 |
| 3 | 保存ボタン | なし | 追加 |
| 4 | 削除ボタン | なし | 「この課題を削除」+ AlertDialog |
| 5 | 共通質問 | なし | 「どのくらい前からこの問題がある？」追加 |

### 4.5 NudgeContent.swift

| # | 箇所 | AS-IS | TO-BE |
|---|------|-------|-------|
| 1 | notificationMessages | 日本語ハードコード | `String(localized:)` |
| 2 | detailMessages | 日本語ハードコード | `String(localized:)` |

### 4.6 ProblemNotificationScheduler.swift（🔴 新規追加パッチ）

| # | 箇所 | AS-IS | TO-BE |
|---|------|-------|-------|
| 1 | scheduleNotifications | ProblemTypeのみ対応 | カスタム課題も対応 |

**具体的な変更**:

```swift
// 追加メソッド
func scheduleCustomProblemNotifications(for customProblems: [CustomProblem]) async {
    for problem in customProblems {
        // 9:00 AM
        await scheduleCustomNotification(
            for: problem,
            hour: 9,
            minute: 0
        )
        // 8:00 PM
        await scheduleCustomNotification(
            for: problem,
            hour: 20,
            minute: 0
        )
    }
}

private func scheduleCustomNotification(for problem: CustomProblem, hour: Int, minute: Int) async {
    let content = UNMutableNotificationContent()
    content.title = problem.name
    content.body = String(localized: "nudge_custom_notification_body")
    // ...
}
```

### 4.7 AppState.swift / UserProfile マイグレーション（🔴 新規追加パッチ）

| # | 箇所 | AS-IS | TO-BE |
|---|------|-------|-------|
| 1 | 起動時 | マイグレーションなし | 古いstruggleキーを新しいキーに変換 |

**マイグレーションマッピング**:

```swift
static let migrationMapping: [String: String] = [
    "poor_sleep": "staying_up_late",
    "stress": "", // 削除（広すぎる）
    "self_doubt": "self_loathing",
    "motivation": "procrastination",
    "focus": "procrastination",
    "time_management": "", // 削除
    "burnout": "", // 削除
    "relationships": "loneliness",
    "energy": "", // 削除
    "work_life_balance": "" // 削除
]

func migrateStruggles() {
    var newStruggles: [String] = []
    for struggle in userProfile.struggles {
        if let newKey = Self.migrationMapping[struggle] {
            if !newKey.isEmpty && !newStruggles.contains(newKey) {
                newStruggles.append(newKey)
            }
        } else if ProblemType(rawValue: struggle) != nil {
            // 既に新しいキーの場合はそのまま
            if !newStruggles.contains(struggle) {
                newStruggles.append(struggle)
            }
        }
        // マッピングにない場合は削除
    }
    userProfile.struggles = newStruggles
}
```

### 4.8 新規ファイル

| ファイル | 内容 |
|---------|------|
| DeepDiveQuestionsData.swift | 各問題の質問・選択肢データ（ローカライズキー） |
| AddProblemSheetView.swift | 「＋ 課題を追加」シート |
| TellAniccaView.swift | 「Aniccaに伝える」入力シート |
| Memory.swift | メモリ（記憶）モデル |
| CustomProblem.swift | カスタム課題モデル |

### 4.9 UserProfile拡張

```swift
// 追加するプロパティ
var problemDetails: [String: [String]]  // 深掘り回答（問題ID: 選択した選択肢）
var memories: [Memory]                   // 「Aniccaに伝える」の保存先
var customProblems: [CustomProblem]      // カスタム課題
```

### 4.10 Localizable.strings（ja/en）

**追加するキーのカテゴリ**:

| カテゴリ | キー数 | 例 |
|---------|-------|-----|
| My Pathタブ | 15+ | `mypath_*` |
| Aniccaに伝える | 5 | `mypath_tell_*` |
| 課題追加シート | 5 | `mypath_add_problem_*` |
| 共通質問 | 5 | `deepdive_common_*` |
| 13問題の深掘り質問・選択肢 | 100+ | `deepdive_{problem}_q{n}_*` |
| NudgeContent | 50+ | `nudge_{problem}_notification_{n}` |
| ProblemTypeボタン | 26+ | `problem_button_*` |
| ProblemType通知タイトル | 13 | `problem_notification_title_*` |
| カスタム課題 | 10+ | `nudge_custom_*`, `deepdive_custom_*` |

---

## 5. 詳細仕様

### 5.1 CustomProblem モデル（🔴 新規定義）

```swift
struct CustomProblem: Codable, Identifiable, Equatable {
    let id: UUID
    let name: String
    let createdAt: Date
    var problemDetails: [String: [String]]?  // 深掘り回答

    init(id: UUID = UUID(), name: String, createdAt: Date = Date()) {
        self.id = id
        self.name = name
        self.createdAt = createdAt
    }
}
```

### 5.2 Memory モデル

```swift
struct Memory: Codable, Identifiable, Equatable {
    let id: UUID
    let timestamp: Date
    let type: MemoryType
    let content: String

    init(id: UUID = UUID(), timestamp: Date = Date(), type: MemoryType, content: String) {
        self.id = id
        self.timestamp = timestamp
        self.type = type
        self.content = content
    }
}

enum MemoryType: String, Codable {
    case struggle = "struggle"  // 今辛いのは...
    case goal = "goal"          // 取り組んでいる目標は...
    case note = "note"          // 覚えておいてほしいのは...
}
```

**保存先**: `UserProfile.memories: [Memory]`

### 5.3 課題削除の方法

**決定**: 深掘りシート内の「この課題を削除」ボタン

**理由**:
- スワイプ削除は誤操作リスクが高い
- シート内なら「わざわざ開いて削除」という意図的アクション
- 削除は頻繁にする操作ではないので、奥にあっても問題ない

**実装**:
- 定義済み13問題 → `userProfile.struggles`から削除（問題定義自体は残る）
- カスタム課題 → `userProfile.customProblems`から完全削除
- AlertDialogで確認後に削除

### 5.4 カスタム課題の通知時刻

**決定**: ルールベースで固定

- **朝 9:00**: 1日の始まり、意識付け
- **夜 20:00**: 振り返りのタイミング

**理由**:
- ユーザーに入力の手間を取らせない
- エージェントとして「察して動く」べき
- Phase 4でAIが最適なタイミングを決定する

### 5.5 カスタム課題の深掘り質問

**汎用的な質問を用意**:

| 質問 | 選択肢 |
|------|--------|
| どのくらい前からこの問題がある？ | 最近 / 数ヶ月 / 1年以上 / ずっと |
| この問題で一番辛いことは？ | 自分を責める / 時間を無駄にする / 人間関係に影響 / 健康に影響 / その他 |
| 何がきっかけで起きる？ | ストレス / 暇な時 / 疲れてる時 / 人と会った後 / その他 |

### 5.6 デバッグ機能（DEBUG only）

Profile画面のrecordingSectionに追加:

```swift
// Nudge/通知テスト
Button("🔔 Nudge通知テスト（夜更かし）") {
    Task {
        await ProblemNotificationScheduler.shared.testNotification(for: .stayingUpLate)
    }
}

Button("📱 1枚画面テスト（夜更かし）") {
    appState.showNudgeCard(for: .stayingUpLate)
}

// 全問題のテスト
ForEach(ProblemType.allCases, id: \.self) { problem in
    Button("📱 \(problem.displayName)") {
        appState.showNudgeCard(for: problem)
    }
}
```

---

## 6. ローカライゼーション

### 6.1 ProblemType ボタン文言（🔴 新規追加）

**日本語 (ja.lproj/Localizable.strings)**:

```
// ポジティブボタン
"problem_button_positive_staying_up_late" = "明日を守る 💪";
"problem_button_positive_cant_wake_up" = "今日を始める ☀️";
"problem_button_positive_self_loathing" = "自分を許す 🤍";
"problem_button_positive_rumination" = "今に戻る 🧘";
"problem_button_positive_procrastination" = "5分やる ⚡";
"problem_button_positive_anxiety" = "深呼吸する 🌬️";
"problem_button_positive_lying" = "誠実でいる 🤝";
"problem_button_positive_bad_mouthing" = "善い言葉を使う 💬";
"problem_button_positive_porn_addiction" = "誘惑に勝つ 💪";
"problem_button_positive_alcohol_dependency" = "今夜は飲まない 🍵";
"problem_button_positive_anger" = "手放す 🕊️";
"problem_button_positive_obsessive" = "手放す 🌿";
"problem_button_positive_loneliness" = "誰かに連絡する 📱";

// ネガティブボタン
"problem_button_negative_staying_up_late" = "傷つける";
"problem_button_negative_cant_wake_up" = "逃げる";
"problem_button_negative_rumination" = "考え続ける";
"problem_button_negative_procrastination" = "後回し";
"problem_button_negative_lying" = "嘘をつく";
"problem_button_negative_bad_mouthing" = "悪口を言う";
"problem_button_negative_porn_addiction" = "負ける";
"problem_button_negative_alcohol_dependency" = "飲む";
"problem_button_negative_anger" = "怒り続ける";
"problem_button_negative_obsessive" = "考え続ける";

// 通知タイトル
"problem_notification_title_staying_up_late" = "就寝";
"problem_notification_title_cant_wake_up" = "起床";
"problem_notification_title_self_loathing" = "Self-Compassion";
"problem_notification_title_rumination" = "今この瞬間";
"problem_notification_title_procrastination" = "先延ばし";
"problem_notification_title_anxiety" = "不安";
"problem_notification_title_lying" = "誠実";
"problem_notification_title_bad_mouthing" = "言葉";
"problem_notification_title_porn_addiction" = "自制";
"problem_notification_title_alcohol_dependency" = "禁酒";
"problem_notification_title_anger" = "冷静";
"problem_notification_title_obsessive" = "手放す";
"problem_notification_title_loneliness" = "つながり";
```

**英語 (en.lproj/Localizable.strings)**:

```
// Positive buttons
"problem_button_positive_staying_up_late" = "Protect tomorrow 💪";
"problem_button_positive_cant_wake_up" = "Start the day ☀️";
"problem_button_positive_self_loathing" = "Forgive myself 🤍";
"problem_button_positive_rumination" = "Return to now 🧘";
"problem_button_positive_procrastination" = "Do 5 min ⚡";
"problem_button_positive_anxiety" = "Deep breath 🌬️";
"problem_button_positive_lying" = "Be honest 🤝";
"problem_button_positive_bad_mouthing" = "Kind words 💬";
"problem_button_positive_porn_addiction" = "Overcome 💪";
"problem_button_positive_alcohol_dependency" = "Stay sober tonight 🍵";
"problem_button_positive_anger" = "Let go 🕊️";
"problem_button_positive_obsessive" = "Let go 🌿";
"problem_button_positive_loneliness" = "Reach out 📱";

// Negative buttons
"problem_button_negative_staying_up_late" = "Hurt myself";
"problem_button_negative_cant_wake_up" = "Stay in bed";
"problem_button_negative_rumination" = "Keep thinking";
"problem_button_negative_procrastination" = "Later";
"problem_button_negative_lying" = "Lie";
"problem_button_negative_bad_mouthing" = "Bad-mouth";
"problem_button_negative_porn_addiction" = "Give in";
"problem_button_negative_alcohol_dependency" = "Drink";
"problem_button_negative_anger" = "Stay angry";
"problem_button_negative_obsessive" = "Keep thinking";

// Notification titles
"problem_notification_title_staying_up_late" = "Bedtime";
"problem_notification_title_cant_wake_up" = "Wake Up";
"problem_notification_title_self_loathing" = "Self-Compassion";
"problem_notification_title_rumination" = "Present Moment";
"problem_notification_title_procrastination" = "Procrastination";
"problem_notification_title_anxiety" = "Anxiety";
"problem_notification_title_lying" = "Honesty";
"problem_notification_title_bad_mouthing" = "Words";
"problem_notification_title_porn_addiction" = "Self-Control";
"problem_notification_title_alcohol_dependency" = "Sobriety";
"problem_notification_title_anger" = "Calm";
"problem_notification_title_obsessive" = "Let Go";
"problem_notification_title_loneliness" = "Connection";
```

### 6.2 My Pathタブ

**日本語**:

```
// My Path タブ
"mypath_header_description" = "Aniccaはあなたの苦しみを理解し、適切なタイミングで寄り添います。";
"mypath_section_current_struggles" = "今向き合っている課題";
"mypath_section_tell_anicca" = "Aniccaに伝える";
"mypath_empty_title" = "向き合いたい課題を追加してみましょう";
"mypath_empty_action" = "課題を追加";
"mypath_add_problem" = "課題を追加";
"mypath_deepdive_save" = "保存";
"mypath_deepdive_delete" = "この課題を削除";
"mypath_deepdive_delete_confirm_title" = "この課題を削除しますか？";
"mypath_deepdive_delete_confirm_message" = "関連する通知も停止されます。";

// Aniccaに伝える
"mypath_tell_struggling_with" = "今辛いのは...";
"mypath_tell_my_goal_is" = "取り組んでいる目標は...";
"mypath_tell_remember_that" = "覚えておいてほしいのは...";
"mypath_tell_saved" = "覚えました";

// 課題追加シート
"mypath_add_problem_title" = "課題を追加";
"mypath_add_problem_custom" = "その他（自由入力）";
"mypath_add_problem_action" = "追加";
"mypath_add_problem_already_added" = "追加済み";
```

**英語**:

```
// My Path tab
"mypath_header_description" = "Anicca understands your struggles and supports you at the right moments.";
"mypath_section_current_struggles" = "Current Struggles";
"mypath_section_tell_anicca" = "Tell Anicca";
"mypath_empty_title" = "Add a struggle to work on";
"mypath_empty_action" = "Add Struggle";
"mypath_add_problem" = "Add Struggle";
"mypath_deepdive_save" = "Save";
"mypath_deepdive_delete" = "Delete this struggle";
"mypath_deepdive_delete_confirm_title" = "Delete this struggle?";
"mypath_deepdive_delete_confirm_message" = "Related notifications will also be stopped.";

// Tell Anicca
"mypath_tell_struggling_with" = "I'm struggling with...";
"mypath_tell_my_goal_is" = "My goal is...";
"mypath_tell_remember_that" = "Remember that...";
"mypath_tell_saved" = "Remembered";

// Add problem sheet
"mypath_add_problem_title" = "Add Struggle";
"mypath_add_problem_custom" = "Other (custom)";
"mypath_add_problem_action" = "Add";
"mypath_add_problem_already_added" = "Already added";
```

### 6.3 共通質問

**日本語**:

```
"deepdive_common_duration_question" = "どのくらい前からこの問題がある？";
"deepdive_common_duration_recent" = "最近";
"deepdive_common_duration_months" = "数ヶ月";
"deepdive_common_duration_year" = "1年以上";
"deepdive_common_duration_always" = "ずっと";
```

**英語**:

```
"deepdive_common_duration_question" = "How long have you had this problem?";
"deepdive_common_duration_recent" = "Recently";
"deepdive_common_duration_months" = "A few months";
"deepdive_common_duration_year" = "Over a year";
"deepdive_common_duration_always" = "Always";
```

### 6.4 全13問題の深掘り質問・選択肢

**日本語 (proactive-agent-spec.md Section 5 より)**:

```
// ===== staying_up_late（夜更かし）=====
"deepdive_staying_up_late_q1" = "夜更かしして何をしてることが多い？";
"deepdive_staying_up_late_q1_opt1" = "SNS";
"deepdive_staying_up_late_q1_opt2" = "YouTube";
"deepdive_staying_up_late_q1_opt3" = "ゲーム";
"deepdive_staying_up_late_q1_opt4" = "仕事";
"deepdive_staying_up_late_q1_opt5" = "その他";

"deepdive_staying_up_late_q2" = "なぜ夜更かししてしまう？";
"deepdive_staying_up_late_q2_opt1" = "今日やるべきことができなかった";
"deepdive_staying_up_late_q2_opt2" = "ストレス解消";
"deepdive_staying_up_late_q2_opt3" = "習慣になってる";
"deepdive_staying_up_late_q2_opt4" = "寝たくない";

// ===== cant_wake_up（起きれない）=====
"deepdive_cant_wake_up_q1" = "起きれない時、どんな気持ちになる？";
"deepdive_cant_wake_up_q1_opt1" = "自己嫌悪";
"deepdive_cant_wake_up_q1_opt2" = "焦り";
"deepdive_cant_wake_up_q1_opt3" = "諦め";
"deepdive_cant_wake_up_q1_opt4" = "何も感じない";

"deepdive_cant_wake_up_q2" = "なぜ起きれないと思う？";
"deepdive_cant_wake_up_q2_opt1" = "睡眠不足";
"deepdive_cant_wake_up_q2_opt2" = "やる気がない";
"deepdive_cant_wake_up_q2_opt3" = "起きる理由がない";
"deepdive_cant_wake_up_q2_opt4" = "体調";

// ===== self_loathing（自己嫌悪）=====
"deepdive_self_loathing_q1" = "どんな時に自己嫌悪になる？";
"deepdive_self_loathing_q1_opt1" = "失敗した時";
"deepdive_self_loathing_q1_opt2" = "比較した時";
"deepdive_self_loathing_q1_opt3" = "何もしなかった時";
"deepdive_self_loathing_q1_opt4" = "常に";

"deepdive_self_loathing_q2" = "何について自分を責める？";
"deepdive_self_loathing_q2_opt1" = "能力";
"deepdive_self_loathing_q2_opt2" = "外見";
"deepdive_self_loathing_q2_opt3" = "性格";
"deepdive_self_loathing_q2_opt4" = "過去の行動";

// ===== rumination（反芻）=====
"deepdive_rumination_q1" = "何について考え続けてしまう？";
"deepdive_rumination_q1_opt1" = "過去の失敗";
"deepdive_rumination_q1_opt2" = "人間関係";
"deepdive_rumination_q1_opt3" = "将来の不安";
"deepdive_rumination_q1_opt4" = "自分の欠点";

"deepdive_rumination_q2" = "いつ反芻しやすい？";
"deepdive_rumination_q2_opt1" = "夜寝る前";
"deepdive_rumination_q2_opt2" = "朝起きた時";
"deepdive_rumination_q2_opt3" = "一人の時";
"deepdive_rumination_q2_opt4" = "常に";

// ===== procrastination（先延ばし）=====
"deepdive_procrastination_q1" = "何を先延ばしにしがち？";
"deepdive_procrastination_q1_opt1" = "仕事のタスク";
"deepdive_procrastination_q1_opt2" = "家事";
"deepdive_procrastination_q1_opt3" = "予約・手続き";
"deepdive_procrastination_q1_opt4" = "人に連絡";

"deepdive_procrastination_q2" = "なぜ先延ばしにしてしまう？";
"deepdive_procrastination_q2_opt1" = "面倒";
"deepdive_procrastination_q2_opt2" = "完璧にやりたい";
"deepdive_procrastination_q2_opt3" = "失敗が怖い";
"deepdive_procrastination_q2_opt4" = "やり方がわからない";

// ===== anxiety（不安）=====
"deepdive_anxiety_q1" = "何について不安を感じる？";
"deepdive_anxiety_q1_opt1" = "将来";
"deepdive_anxiety_q1_opt2" = "人間関係";
"deepdive_anxiety_q1_opt3" = "仕事";
"deepdive_anxiety_q1_opt4" = "健康";

"deepdive_anxiety_q2" = "いつ不安を感じやすい？";
"deepdive_anxiety_q2_opt1" = "朝";
"deepdive_anxiety_q2_opt2" = "夜";
"deepdive_anxiety_q2_opt3" = "人と会う前";
"deepdive_anxiety_q2_opt4" = "常に";

// ===== lying（嘘をつく）=====
"deepdive_lying_q1" = "どんな嘘をつくことが多い？";
"deepdive_lying_q1_opt1" = "小さな嘘";
"deepdive_lying_q1_opt2" = "言い訳";
"deepdive_lying_q1_opt3" = "自分を良く見せる嘘";
"deepdive_lying_q1_opt4" = "相手を傷つけないための嘘";

"deepdive_lying_q2" = "誰に嘘をつくことが多い？";
"deepdive_lying_q2_opt1" = "家族";
"deepdive_lying_q2_opt2" = "友人";
"deepdive_lying_q2_opt3" = "職場の人";
"deepdive_lying_q2_opt4" = "自分";

"deepdive_lying_q3" = "なぜ嘘をついてしまう？";
"deepdive_lying_q3_opt1" = "怒られたくない";
"deepdive_lying_q3_opt2" = "嫌われたくない";
"deepdive_lying_q3_opt3" = "習慣";
"deepdive_lying_q3_opt4" = "面倒を避けたい";

// ===== bad_mouthing（悪口）=====
"deepdive_bad_mouthing_q1" = "どんな悪口を言ってしまう？";
"deepdive_bad_mouthing_q1_opt1" = "陰口";
"deepdive_bad_mouthing_q1_opt2" = "皮肉";
"deepdive_bad_mouthing_q1_opt3" = "バカにする";
"deepdive_bad_mouthing_q1_opt4" = "批判";

"deepdive_bad_mouthing_q2" = "誰に対して言ってしまう？";
"deepdive_bad_mouthing_q2_opt1" = "家族";
"deepdive_bad_mouthing_q2_opt2" = "友人";
"deepdive_bad_mouthing_q2_opt3" = "職場の人";
"deepdive_bad_mouthing_q2_opt4" = "SNSで";

"deepdive_bad_mouthing_q3" = "なぜ悪口を言ってしまう？";
"deepdive_bad_mouthing_q3_opt1" = "ストレス発散";
"deepdive_bad_mouthing_q3_opt2" = "相手にイライラ";
"deepdive_bad_mouthing_q3_opt3" = "習慣";
"deepdive_bad_mouthing_q3_opt4" = "認めてほしい";

// ===== porn_addiction（ポルノ依存）=====
"deepdive_porn_addiction_q1" = "どんな時に見てしまう？";
"deepdive_porn_addiction_q1_opt1" = "夜更かし中";
"deepdive_porn_addiction_q1_opt2" = "帰宅後";
"deepdive_porn_addiction_q1_opt3" = "ストレスを感じた時";
"deepdive_porn_addiction_q1_opt4" = "暇な時";

"deepdive_porn_addiction_q2" = "なぜ見てしまうと思う？";
"deepdive_porn_addiction_q2_opt1" = "ストレス解消";
"deepdive_porn_addiction_q2_opt2" = "習慣";
"deepdive_porn_addiction_q2_opt3" = "逃避";
"deepdive_porn_addiction_q2_opt4" = "寂しさ";

// ===== alcohol_dependency（お酒依存）=====
"deepdive_alcohol_dependency_q1" = "どんな時に飲みたくなる？";
"deepdive_alcohol_dependency_q1_opt1" = "仕事終わり";
"deepdive_alcohol_dependency_q1_opt2" = "ストレスを感じた時";
"deepdive_alcohol_dependency_q1_opt3" = "人と会う時";
"deepdive_alcohol_dependency_q1_opt4" = "毎日";

"deepdive_alcohol_dependency_q2" = "なぜ飲んでしまう？";
"deepdive_alcohol_dependency_q2_opt1" = "リラックスしたい";
"deepdive_alcohol_dependency_q2_opt2" = "習慣";
"deepdive_alcohol_dependency_q2_opt3" = "付き合い";
"deepdive_alcohol_dependency_q2_opt4" = "寝たい";

// ===== anger（怒り）=====
"deepdive_anger_q1" = "どんな時に怒りを感じる？";
"deepdive_anger_q1_opt1" = "思い通りにならない時";
"deepdive_anger_q1_opt2" = "理不尽な時";
"deepdive_anger_q1_opt3" = "無視された時";
"deepdive_anger_q1_opt4" = "疲れてる時";

"deepdive_anger_q2" = "怒りをどう表現する？";
"deepdive_anger_q2_opt1" = "爆発する";
"deepdive_anger_q2_opt2" = "黙り込む";
"deepdive_anger_q2_opt3" = "物に当たる";
"deepdive_anger_q2_opt4" = "言葉で攻撃";

// ===== obsessive（強迫的思考）=====
"deepdive_obsessive_q1" = "どんなことを考え続けてしまう？";
"deepdive_obsessive_q1_opt1" = "細かいミス";
"deepdive_obsessive_q1_opt2" = "完璧にできたか";
"deepdive_obsessive_q1_opt3" = "人にどう思われたか";
"deepdive_obsessive_q1_opt4" = "同じ心配事";

"deepdive_obsessive_q2" = "いつ考え続けてしまう？";
"deepdive_obsessive_q2_opt1" = "常に";
"deepdive_obsessive_q2_opt2" = "夜";
"deepdive_obsessive_q2_opt3" = "仕事中";
"deepdive_obsessive_q2_opt4" = "何かした後";

// ===== loneliness（孤独）=====
"deepdive_loneliness_q1" = "どんな時に孤独を感じる？";
"deepdive_loneliness_q1_opt1" = "一人でいる時";
"deepdive_loneliness_q1_opt2" = "人といても";
"deepdive_loneliness_q1_opt3" = "夜";
"deepdive_loneliness_q1_opt4" = "SNSを見てる時";

"deepdive_loneliness_q2" = "なぜ孤独を感じる？";
"deepdive_loneliness_q2_opt1" = "友人が少ない";
"deepdive_loneliness_q2_opt2" = "理解されてない";
"deepdive_loneliness_q2_opt3" = "遠くに住んでる";
"deepdive_loneliness_q2_opt4" = "わからない";

// ===== カスタム課題の深掘り質問 =====
"deepdive_custom_q1" = "この問題で一番辛いことは？";
"deepdive_custom_q1_opt1" = "自分を責める";
"deepdive_custom_q1_opt2" = "時間を無駄にする";
"deepdive_custom_q1_opt3" = "人間関係に影響";
"deepdive_custom_q1_opt4" = "健康に影響";
"deepdive_custom_q1_opt5" = "その他";

"deepdive_custom_q2" = "何がきっかけで起きる？";
"deepdive_custom_q2_opt1" = "ストレス";
"deepdive_custom_q2_opt2" = "暇な時";
"deepdive_custom_q2_opt3" = "疲れてる時";
"deepdive_custom_q2_opt4" = "人と会った後";
"deepdive_custom_q2_opt5" = "その他";
```

**英語 (en.lproj/Localizable.strings)**:

```
// ===== Common =====
"deepdive_common_duration_question" = "How long have you had this problem?";
"deepdive_common_duration_recent" = "Recently";
"deepdive_common_duration_months" = "A few months";
"deepdive_common_duration_year" = "Over a year";
"deepdive_common_duration_always" = "Always";

// ===== staying_up_late =====
"deepdive_staying_up_late_q1" = "What do you usually do when staying up late?";
"deepdive_staying_up_late_q1_opt1" = "Social media";
"deepdive_staying_up_late_q1_opt2" = "YouTube";
"deepdive_staying_up_late_q1_opt3" = "Games";
"deepdive_staying_up_late_q1_opt4" = "Work";
"deepdive_staying_up_late_q1_opt5" = "Other";
"deepdive_staying_up_late_q2" = "Why do you stay up late?";
"deepdive_staying_up_late_q2_opt1" = "Couldn't finish what I needed to do today";
"deepdive_staying_up_late_q2_opt2" = "Stress relief";
"deepdive_staying_up_late_q2_opt3" = "It's become a habit";
"deepdive_staying_up_late_q2_opt4" = "Don't want to sleep";

// ===== cant_wake_up =====
"deepdive_cant_wake_up_q1" = "How do you feel when you can't wake up?";
"deepdive_cant_wake_up_q1_opt1" = "Self-loathing";
"deepdive_cant_wake_up_q1_opt2" = "Panic";
"deepdive_cant_wake_up_q1_opt3" = "Giving up";
"deepdive_cant_wake_up_q1_opt4" = "Nothing";
"deepdive_cant_wake_up_q2" = "Why can't you wake up?";
"deepdive_cant_wake_up_q2_opt1" = "Lack of sleep";
"deepdive_cant_wake_up_q2_opt2" = "No motivation";
"deepdive_cant_wake_up_q2_opt3" = "No reason to wake up";
"deepdive_cant_wake_up_q2_opt4" = "Health issues";

// ===== self_loathing =====
"deepdive_self_loathing_q1" = "When do you feel self-loathing?";
"deepdive_self_loathing_q1_opt1" = "After failing";
"deepdive_self_loathing_q1_opt2" = "When comparing myself";
"deepdive_self_loathing_q1_opt3" = "When I did nothing";
"deepdive_self_loathing_q1_opt4" = "Always";
"deepdive_self_loathing_q2" = "What do you blame yourself for?";
"deepdive_self_loathing_q2_opt1" = "My abilities";
"deepdive_self_loathing_q2_opt2" = "My appearance";
"deepdive_self_loathing_q2_opt3" = "My personality";
"deepdive_self_loathing_q2_opt4" = "Past actions";

// ===== rumination =====
"deepdive_rumination_q1" = "What do you keep thinking about?";
"deepdive_rumination_q1_opt1" = "Past failures";
"deepdive_rumination_q1_opt2" = "Relationships";
"deepdive_rumination_q1_opt3" = "Future worries";
"deepdive_rumination_q1_opt4" = "My flaws";
"deepdive_rumination_q2" = "When do you tend to ruminate?";
"deepdive_rumination_q2_opt1" = "Before sleep";
"deepdive_rumination_q2_opt2" = "When waking up";
"deepdive_rumination_q2_opt3" = "When alone";
"deepdive_rumination_q2_opt4" = "Always";

// ===== procrastination =====
"deepdive_procrastination_q1" = "What do you tend to procrastinate on?";
"deepdive_procrastination_q1_opt1" = "Work tasks";
"deepdive_procrastination_q1_opt2" = "Housework";
"deepdive_procrastination_q1_opt3" = "Appointments & paperwork";
"deepdive_procrastination_q1_opt4" = "Contacting people";
"deepdive_procrastination_q2" = "Why do you procrastinate?";
"deepdive_procrastination_q2_opt1" = "Too troublesome";
"deepdive_procrastination_q2_opt2" = "Want to do it perfectly";
"deepdive_procrastination_q2_opt3" = "Fear of failure";
"deepdive_procrastination_q2_opt4" = "Don't know how";

// ===== anxiety =====
"deepdive_anxiety_q1" = "What makes you anxious?";
"deepdive_anxiety_q1_opt1" = "The future";
"deepdive_anxiety_q1_opt2" = "Relationships";
"deepdive_anxiety_q1_opt3" = "Work";
"deepdive_anxiety_q1_opt4" = "Health";
"deepdive_anxiety_q2" = "When do you feel anxious?";
"deepdive_anxiety_q2_opt1" = "Morning";
"deepdive_anxiety_q2_opt2" = "Night";
"deepdive_anxiety_q2_opt3" = "Before meeting people";
"deepdive_anxiety_q2_opt4" = "Always";

// ===== lying =====
"deepdive_lying_q1" = "What kind of lies do you tell?";
"deepdive_lying_q1_opt1" = "Small lies";
"deepdive_lying_q1_opt2" = "Excuses";
"deepdive_lying_q1_opt3" = "To look better";
"deepdive_lying_q1_opt4" = "To not hurt others";
"deepdive_lying_q2" = "Who do you lie to?";
"deepdive_lying_q2_opt1" = "Family";
"deepdive_lying_q2_opt2" = "Friends";
"deepdive_lying_q2_opt3" = "Coworkers";
"deepdive_lying_q2_opt4" = "Myself";
"deepdive_lying_q3" = "Why do you lie?";
"deepdive_lying_q3_opt1" = "Don't want to be scolded";
"deepdive_lying_q3_opt2" = "Don't want to be disliked";
"deepdive_lying_q3_opt3" = "Habit";
"deepdive_lying_q3_opt4" = "Avoiding trouble";

// ===== bad_mouthing =====
"deepdive_bad_mouthing_q1" = "What kind of bad things do you say?";
"deepdive_bad_mouthing_q1_opt1" = "Gossip";
"deepdive_bad_mouthing_q1_opt2" = "Sarcasm";
"deepdive_bad_mouthing_q1_opt3" = "Making fun";
"deepdive_bad_mouthing_q1_opt4" = "Criticism";
"deepdive_bad_mouthing_q2" = "Who do you say bad things about?";
"deepdive_bad_mouthing_q2_opt1" = "Family";
"deepdive_bad_mouthing_q2_opt2" = "Friends";
"deepdive_bad_mouthing_q2_opt3" = "Coworkers";
"deepdive_bad_mouthing_q2_opt4" = "On social media";
"deepdive_bad_mouthing_q3" = "Why do you badmouth?";
"deepdive_bad_mouthing_q3_opt1" = "Stress relief";
"deepdive_bad_mouthing_q3_opt2" = "Annoyed at them";
"deepdive_bad_mouthing_q3_opt3" = "Habit";
"deepdive_bad_mouthing_q3_opt4" = "Want recognition";

// ===== porn_addiction =====
"deepdive_porn_addiction_q1" = "When do you watch porn?";
"deepdive_porn_addiction_q1_opt1" = "Late at night";
"deepdive_porn_addiction_q1_opt2" = "After coming home";
"deepdive_porn_addiction_q1_opt3" = "When stressed";
"deepdive_porn_addiction_q1_opt4" = "When bored";
"deepdive_porn_addiction_q2" = "Why do you watch porn?";
"deepdive_porn_addiction_q2_opt1" = "Stress relief";
"deepdive_porn_addiction_q2_opt2" = "Habit";
"deepdive_porn_addiction_q2_opt3" = "Escape";
"deepdive_porn_addiction_q2_opt4" = "Loneliness";

// ===== alcohol_dependency =====
"deepdive_alcohol_dependency_q1" = "When do you want to drink?";
"deepdive_alcohol_dependency_q1_opt1" = "After work";
"deepdive_alcohol_dependency_q1_opt2" = "When stressed";
"deepdive_alcohol_dependency_q1_opt3" = "When with others";
"deepdive_alcohol_dependency_q1_opt4" = "Every day";
"deepdive_alcohol_dependency_q2" = "Why do you drink?";
"deepdive_alcohol_dependency_q2_opt1" = "To relax";
"deepdive_alcohol_dependency_q2_opt2" = "Habit";
"deepdive_alcohol_dependency_q2_opt3" = "Social pressure";
"deepdive_alcohol_dependency_q2_opt4" = "To sleep";

// ===== anger =====
"deepdive_anger_q1" = "When do you feel angry?";
"deepdive_anger_q1_opt1" = "When things don't go my way";
"deepdive_anger_q1_opt2" = "When treated unfairly";
"deepdive_anger_q1_opt3" = "When ignored";
"deepdive_anger_q1_opt4" = "When tired";
"deepdive_anger_q2" = "How do you express anger?";
"deepdive_anger_q2_opt1" = "Explode";
"deepdive_anger_q2_opt2" = "Go silent";
"deepdive_anger_q2_opt3" = "Take it out on things";
"deepdive_anger_q2_opt4" = "Verbal attacks";

// ===== obsessive =====
"deepdive_obsessive_q1" = "What do you obsess over?";
"deepdive_obsessive_q1_opt1" = "Small mistakes";
"deepdive_obsessive_q1_opt2" = "Did I do it perfectly?";
"deepdive_obsessive_q1_opt3" = "What people think of me";
"deepdive_obsessive_q1_opt4" = "Same worries";
"deepdive_obsessive_q2" = "When do you obsess?";
"deepdive_obsessive_q2_opt1" = "Always";
"deepdive_obsessive_q2_opt2" = "At night";
"deepdive_obsessive_q2_opt3" = "At work";
"deepdive_obsessive_q2_opt4" = "After doing something";

// ===== loneliness =====
"deepdive_loneliness_q1" = "When do you feel lonely?";
"deepdive_loneliness_q1_opt1" = "When alone";
"deepdive_loneliness_q1_opt2" = "Even with people";
"deepdive_loneliness_q1_opt3" = "At night";
"deepdive_loneliness_q1_opt4" = "On social media";
"deepdive_loneliness_q2" = "Why do you feel lonely?";
"deepdive_loneliness_q2_opt1" = "Few friends";
"deepdive_loneliness_q2_opt2" = "Not understood";
"deepdive_loneliness_q2_opt3" = "Live far away";
"deepdive_loneliness_q2_opt4" = "Don't know";

// ===== Custom =====
"deepdive_custom_q1" = "What's the hardest part about this problem?";
"deepdive_custom_q1_opt1" = "Blaming myself";
"deepdive_custom_q1_opt2" = "Wasting time";
"deepdive_custom_q1_opt3" = "Affects relationships";
"deepdive_custom_q1_opt4" = "Affects health";
"deepdive_custom_q1_opt5" = "Other";
"deepdive_custom_q2" = "What triggers it?";
"deepdive_custom_q2_opt1" = "Stress";
"deepdive_custom_q2_opt2" = "When bored";
"deepdive_custom_q2_opt3" = "When tired";
"deepdive_custom_q2_opt4" = "After seeing people";
"deepdive_custom_q2_opt5" = "Other";
```

### 6.5 NudgeContent通知文言（🔴 新規追加）

**日本語 (ja.lproj/Localizable.strings)**:

```
// ===== staying_up_late =====
"nudge_staying_up_late_notification_1" = "スクロールより、呼吸。";
"nudge_staying_up_late_notification_2" = "その「あと5分だけ」で、何年失ってきた？";
"nudge_staying_up_late_notification_3" = "明日の自分、泣くよ。";
"nudge_staying_up_late_detail_1" = "夜更かしは明日の自分を傷つける行為。今夜は画面を閉じよう。";
"nudge_staying_up_late_detail_2" = "睡眠不足の脳は酔っ払いと同じ判断力。明日の自分を守るために、今夜は休もう。";
"nudge_staying_up_late_detail_3" = "今スクロールしてる内容、明日覚えてる？でも睡眠不足は確実に残る。";

// ===== cant_wake_up =====
"nudge_cant_wake_up_notification_1" = "起きないと、今日が始まらん。";
"nudge_cant_wake_up_notification_2" = "あと5分の君、信用ゼロ。";
"nudge_cant_wake_up_notification_3" = "Stay Mediocre";
"nudge_cant_wake_up_detail_1" = "布団の中で何も変わらない。まず足を床につけよう。";
"nudge_cant_wake_up_detail_2" = "「あと5分」を何回言った？今起きれば、今日の自分を好きになれる。";
"nudge_cant_wake_up_detail_3" = "平凡なままでいい？今起きれば、今日は違う1日になる。";

// ===== self_loathing =====
"nudge_self_loathing_notification_1" = "今日も生きてる。それだけで十分。";
"nudge_self_loathing_notification_2" = "自分を責めるのは、もうやめていい。";
"nudge_self_loathing_notification_3" = "あなたは思ってるより、ずっといい人だよ。";
"nudge_self_loathing_detail_1" = "自己嫌悪は、自分を良くしようとしている証拠。でもその方法は逆効果。今日できた小さなことを1つ思い出してみて。";
"nudge_self_loathing_detail_2" = "完璧じゃなくていい。今のあなたで十分。";
"nudge_self_loathing_detail_3" = "自分に厳しすぎる。他の人にするように、自分にも優しくしていい。";

// ===== rumination =====
"nudge_rumination_notification_1" = "今、何を感じてる？";
"nudge_rumination_notification_2" = "Are you present right now?";
"nudge_rumination_notification_3" = "朝の5分、瞑想してみない？";
"nudge_rumination_detail_1" = "頭の中のループに気づいた？気づいたなら、もう半分解決してる。今この瞬間に戻ろう。";
"nudge_rumination_detail_2" = "過去でも未来でもなく、今ここにいる？深呼吸して、今の身体の感覚に意識を向けてみて。";
"nudge_rumination_detail_3" = "反芻を止める最も効果的な方法は瞑想。今朝5分だけ、呼吸に集中してみよう。";

// ===== procrastination =====
"nudge_procrastination_notification_1" = "5分だけ。それだけでいい。";
"nudge_procrastination_notification_2" = "また自分との約束、破る？";
"nudge_procrastination_notification_3" = "やらない理由、全部言い訳。";
"nudge_procrastination_detail_1" = "完璧にやる必要はない。5分だけ始めれば、続けられる。";
"nudge_procrastination_detail_2" = "先延ばしは未来の自分を苦しめる。今やれば、未来の自分が感謝する。";
"nudge_procrastination_detail_3" = "本当にできない？それとも、やりたくないだけ？正直になろう。";

// ===== anxiety =====
"nudge_anxiety_notification_1" = "今この瞬間、あなたは安全。";
"nudge_anxiety_notification_2" = "今、何を感じてる？";
"nudge_anxiety_notification_3" = "深呼吸。4秒吸って、4秒止めて、4秒吐く。";
"nudge_anxiety_detail_1" = "不安は未来への恐れ。でも今この瞬間は、何も起きていない。深呼吸して、今に戻ろう。";
"nudge_anxiety_detail_2" = "不安に気づいた？気づいたなら、それを観察してみて。不安は来て、去っていく。";
"nudge_anxiety_detail_3" = "身体を落ち着かせれば、心も落ち着く。今すぐやってみて。";

// ===== lying =====
"nudge_lying_notification_1" = "今日は正直に生きる日。";
"nudge_lying_detail_1" = "嘘は一時的に楽でも、長期的には自分を苦しめる。今日は誠実でいよう。";

// ===== bad_mouthing =====
"nudge_bad_mouthing_notification_1" = "今日は誰かを傷つける言葉を使わない。";
"nudge_bad_mouthing_notification_2" = "その言葉、自分に言われたらどう感じる？";
"nudge_bad_mouthing_detail_1" = "悪口は言った瞬間気持ちいいかもしれない。でも後から自己嫌悪が来る。今日は善い言葉だけ。";
"nudge_bad_mouthing_detail_2" = "言う前に一呼吸。相手の立場に立ってみよう。";

// ===== porn_addiction =====
"nudge_porn_addiction_notification_1" = "誘惑に勝てば、明日の自分が変わる。";
"nudge_porn_addiction_notification_2" = "本当にそれが欲しい？それとも逃げたいだけ？";
"nudge_porn_addiction_detail_1" = "今の衝動は一時的。5分待てば、衝動は去る。その5分を乗り越えよう。";
"nudge_porn_addiction_detail_2" = "ポルノは一時的な逃避。根本の問題は解決しない。今何から逃げようとしてる？";

// ===== alcohol_dependency =====
"nudge_alcohol_dependency_notification_1" = "今夜は飲まない。それだけで勝ち。";
"nudge_alcohol_dependency_notification_2" = "飲まなくても、リラックスできる。";
"nudge_alcohol_dependency_detail_1" = "1日だけ。今夜だけ我慢しよう。明日の朝、自分を誇れる。";
"nudge_alcohol_dependency_detail_2" = "お酒なしでストレス解消する方法を試してみて。散歩、深呼吸、音楽。";

// ===== anger =====
"nudge_anger_notification_1" = "怒りは自分を傷つける。深呼吸。";
"nudge_anger_notification_2" = "3秒待ってから、話そう。";
"nudge_anger_detail_1" = "怒りを持ち続けるのは、自分が毒を飲んで相手が死ぬのを待つようなもの。手放そう。";
"nudge_anger_detail_2" = "怒りに任せて話すと後悔する。3秒だけ待とう。";

// ===== obsessive =====
"nudge_obsessive_notification_1" = "完璧じゃなくていい。手放していい。";
"nudge_obsessive_notification_2" = "その考え、何回目？";
"nudge_obsessive_notification_3" = "考えすぎてない？";
"nudge_obsessive_detail_1" = "その考え、本当に重要？今手放しても、何も悪いことは起きない。";
"nudge_obsessive_detail_2" = "同じことを考え続けても、答えは変わらない。今は手放して、後で考えよう。";
"nudge_obsessive_detail_3" = "考えることと、実際に行動することは違う。今は考えるのをやめて、動いてみよう。";

// ===== loneliness =====
"nudge_loneliness_notification_1" = "一人じゃない。誰かがあなたを想ってる。";
"nudge_loneliness_notification_2" = "大切な人に、一言送ってみない？";
"nudge_loneliness_detail_1" = "孤独を感じても、それは真実じゃない。今日、誰かに連絡してみない？";
"nudge_loneliness_detail_2" = "つながりは待っていても来ない。自分から動こう。";

// ===== カスタム課題 =====
"nudge_custom_notification_body" = "この問題に向き合う時間です。";
"nudge_custom_detail_body" = "小さな一歩でも、前に進んでいます。";
```

**英語 (en.lproj/Localizable.strings)**:

```
// ===== staying_up_late =====
"nudge_staying_up_late_notification_1" = "Breathe, don't scroll.";
"nudge_staying_up_late_notification_2" = "How many years have you lost to 'just 5 more minutes'?";
"nudge_staying_up_late_notification_3" = "Tomorrow's you will regret this.";
"nudge_staying_up_late_detail_1" = "Staying up late hurts tomorrow's you. Close that screen tonight.";
"nudge_staying_up_late_detail_2" = "A sleep-deprived brain has the judgment of a drunk. Rest tonight to protect tomorrow's you.";
"nudge_staying_up_late_detail_3" = "Will you remember what you're scrolling? But the sleep deprivation will definitely stay.";

// ===== cant_wake_up =====
"nudge_cant_wake_up_notification_1" = "Your day won't start until you get up.";
"nudge_cant_wake_up_notification_2" = "The 'just 5 more minutes' you has zero credibility.";
"nudge_cant_wake_up_notification_3" = "Stay Mediocre";
"nudge_cant_wake_up_detail_1" = "Nothing changes under the blanket. Put your feet on the floor first.";
"nudge_cant_wake_up_detail_2" = "How many times have you said '5 more minutes'? Get up now, and you'll like today's you.";
"nudge_cant_wake_up_detail_3" = "Want to stay average? Get up now, and today will be different.";

// ===== self_loathing =====
"nudge_self_loathing_notification_1" = "You're alive today. That's enough.";
"nudge_self_loathing_notification_2" = "It's okay to stop blaming yourself.";
"nudge_self_loathing_notification_3" = "You're a much better person than you think.";
"nudge_self_loathing_detail_1" = "Self-loathing shows you want to improve. But it's counterproductive. Remember one small thing you did well today.";
"nudge_self_loathing_detail_2" = "You don't have to be perfect. You're enough as you are.";
"nudge_self_loathing_detail_3" = "You're too hard on yourself. Be kind to yourself like you would to others.";

// ===== rumination =====
"nudge_rumination_notification_1" = "What are you feeling right now?";
"nudge_rumination_notification_2" = "Are you present right now?";
"nudge_rumination_notification_3" = "Why not meditate for 5 minutes this morning?";
"nudge_rumination_detail_1" = "Noticed the loop in your head? Noticing it means you're halfway there. Come back to this moment.";
"nudge_rumination_detail_2" = "Are you here now, not in the past or future? Take a deep breath and notice how your body feels.";
"nudge_rumination_detail_3" = "Meditation is the most effective way to stop rumination. Focus on your breath for just 5 minutes.";

// ===== procrastination =====
"nudge_procrastination_notification_1" = "Just 5 minutes. That's all you need.";
"nudge_procrastination_notification_2" = "Breaking another promise to yourself?";
"nudge_procrastination_notification_3" = "Every reason not to do it is an excuse.";
"nudge_procrastination_detail_1" = "You don't have to do it perfectly. Start for 5 minutes and you can keep going.";
"nudge_procrastination_detail_2" = "Procrastination hurts future you. Do it now and future you will thank you.";
"nudge_procrastination_detail_3" = "Can't you really do it? Or do you just not want to? Be honest.";

// ===== anxiety =====
"nudge_anxiety_notification_1" = "In this moment, you are safe.";
"nudge_anxiety_notification_2" = "What are you feeling right now?";
"nudge_anxiety_notification_3" = "Deep breath. Inhale 4 seconds, hold 4, exhale 4.";
"nudge_anxiety_detail_1" = "Anxiety is fear of the future. But nothing is happening right now. Breathe and come back to now.";
"nudge_anxiety_detail_2" = "Noticed your anxiety? Watch it. Anxiety comes and goes.";
"nudge_anxiety_detail_3" = "Calm your body, calm your mind. Try it now.";

// ===== lying =====
"nudge_lying_notification_1" = "Today is a day to live honestly.";
"nudge_lying_detail_1" = "Lies may be easy short-term, but they hurt you long-term. Be truthful today.";

// ===== bad_mouthing =====
"nudge_bad_mouthing_notification_1" = "No hurtful words today.";
"nudge_bad_mouthing_notification_2" = "How would you feel if someone said that to you?";
"nudge_bad_mouthing_detail_1" = "Gossip feels good in the moment. But self-loathing follows. Only kind words today.";
"nudge_bad_mouthing_detail_2" = "Take a breath before speaking. Put yourself in their shoes.";

// ===== porn_addiction =====
"nudge_porn_addiction_notification_1" = "Beat the temptation and tomorrow's you will change.";
"nudge_porn_addiction_notification_2" = "Do you really want it? Or are you just escaping?";
"nudge_porn_addiction_detail_1" = "This urge is temporary. Wait 5 minutes and it'll pass. Get through those 5 minutes.";
"nudge_porn_addiction_detail_2" = "Porn is temporary escape. It doesn't solve the root problem. What are you running from?";

// ===== alcohol_dependency =====
"nudge_alcohol_dependency_notification_1" = "Don't drink tonight. That alone is a win.";
"nudge_alcohol_dependency_notification_2" = "You can relax without drinking.";
"nudge_alcohol_dependency_detail_1" = "Just today. Just tonight. You'll be proud tomorrow morning.";
"nudge_alcohol_dependency_detail_2" = "Try stress relief without alcohol. A walk, deep breaths, music.";

// ===== anger =====
"nudge_anger_notification_1" = "Anger hurts you. Take a deep breath.";
"nudge_anger_notification_2" = "Wait 3 seconds before speaking.";
"nudge_anger_detail_1" = "Holding onto anger is like drinking poison expecting the other person to die. Let it go.";
"nudge_anger_detail_2" = "Speaking in anger leads to regret. Wait just 3 seconds.";

// ===== obsessive =====
"nudge_obsessive_notification_1" = "It doesn't have to be perfect. You can let go.";
"nudge_obsessive_notification_2" = "How many times have you thought that?";
"nudge_obsessive_notification_3" = "Aren't you overthinking?";
"nudge_obsessive_detail_1" = "Is that thought really important? Nothing bad happens if you let it go now.";
"nudge_obsessive_detail_2" = "Thinking the same thing won't change the answer. Let go now, think later.";
"nudge_obsessive_detail_3" = "Thinking and acting are different. Stop thinking, start moving.";

// ===== loneliness =====
"nudge_loneliness_notification_1" = "You're not alone. Someone is thinking of you.";
"nudge_loneliness_notification_2" = "Why not send a message to someone you care about?";
"nudge_loneliness_detail_1" = "Feeling lonely doesn't make it true. Why not reach out to someone today?";
"nudge_loneliness_detail_2" = "Connection won't come to you. Make the first move.";

// ===== Custom =====
"nudge_custom_notification_body" = "Time to face this problem.";
"nudge_custom_detail_body" = "Even a small step is progress.";
```

---

## 7. Phase 4以降の予定

### 7.1 フィードバック履歴画面

```
┌─────────────────────────────────────┐
│  ←              フィードバック履歴   │
│                                     │
│  1/18 10:30                         │
│  今辛いのは 仕事のプレッシャー       │  ← スワイプで削除可能
│                                     │
│  1/17 22:15                         │
│  覚えておいてほしいのは              │
│  明日のプレゼンが不安                │
│                                     │
└─────────────────────────────────────┘
```

### 7.2 AI活用（Nudgeパーソナライズ）

memoriesをNudge生成に反映

### 7.3 カスタム課題の通知時刻AI決定

Phase 4でAIが適切なタイミングを決定

### 7.4 深掘り回答のNudge反映

problemDetailsをNudge生成に活用

---

## 付録: ui-skills適用チェックリスト

| ルール | 適用箇所 |
|--------|---------|
| MUST give empty states one clear next action | 空状態に「課題を追加」ボタン1つ |
| MUST use AlertDialog for destructive actions | 課題削除時に確認ダイアログ |
| NEVER add animation unless explicitly requested | 「覚えました」フェードインのみ（200ms以下） |
| MUST show errors next to where action happens | 入力エラーはフィールド直下 |
| MUST use project's existing component primitives | CardView, ProfileFlowChips, AppTheme等 |
| SHOULD limit accent color to one per view | buttonSelectedのみ |

---

## 付録: 実装順序

1. **Localizable.strings更新**（ja/en）- ProblemTypeボタン、通知タイトル、My Path、深掘り質問
2. **ProblemType.swift修正**（ローカライズ）
3. **NudgeContent.swift修正**（ローカライズ）
4. **Memory.swift作成**
5. **CustomProblem.swift作成**
6. **UserProfile拡張**（problemDetails, memories, customProblems）
7. **AppState.swift マイグレーション追加**
8. **DeepDiveQuestionsData.swift作成**（質問・選択肢データ）
9. **ProfileView.swift修正**（セクション非表示、デバッグ機能）
10. **MyPathTabView.swift大幅改修**
    - カード全体タップ
    - DeepDiveSheetView改修（選択肢UI、保存、削除）
    - 「＋ 課題を追加」ボタン
    - 「Aniccaに伝える」セクション
11. **AddProblemSheetView.swift作成**
12. **TellAniccaView.swift作成**
13. **ProblemNotificationScheduler.swift修正**（カスタム課題対応）

---

## 付録: パッチサマリー

| # | ファイル | パッチ内容 | 優先度 |
|---|---------|-----------|--------|
| 1 | ProblemType.swift | positiveButtonText, negativeButtonText, notificationTitle ローカライズ | 高 |
| 2 | NudgeContent.swift | notificationMessages, detailMessages ローカライズ | 高 |
| 3 | ProfileView.swift | traitsCard, idealsSection, strugglesSection, stickyModeSection 非表示 | 高 |
| 4 | ProfileView.swift | recordingSection にNudge/通知テストボタン追加 | 中 |
| 5 | MyPathTabView.swift | 日本語ハードコード → ローカライズ | 高 |
| 6 | MyPathTabView.swift | カード全体タップ、ボタン削除 | 高 |
| 7 | DeepDiveSheetView | 選択肢UI、保存ボタン、削除ボタン追加 | 高 |
| 8 | MyPathTabView.swift | 「＋ 課題を追加」ボタン追加 | 高 |
| 9 | MyPathTabView.swift | 「Aniccaに伝える」セクション追加 | 高 |
| 10 | ProblemNotificationScheduler.swift | カスタム課題対応 | 中 |
| 11 | AppState.swift | マイグレーション処理追加 | 高 |
| 12 | Localizable.strings (ja/en) | 全キー追加 | 高 |
| 13 | Memory.swift | 新規作成 | 高 |
| 14 | CustomProblem.swift | 新規作成 | 高 |
| 15 | UserProfile.swift | problemDetails, memories, customProblems 追加 | 高 |
| 16 | DeepDiveQuestionsData.swift | 新規作成 | 高 |
| 17 | AddProblemSheetView.swift | 新規作成 | 高 |
| 18 | TellAniccaView.swift | 新規作成 | 高 |

---

**作成者**: Claude
**レビュー待ち**: 他のエージェントによるレビュー
