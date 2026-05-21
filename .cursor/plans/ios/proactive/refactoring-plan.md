# Proactive Agent リファクタリング計画

> 作成日: 2026-01-18
> 最終更新: 2026-01-18
> 目的: 音声対話アプリから Proactive Agent への移行に伴う、コードベースの整理

---

## エグゼクティブサマリー

### 現在の問題
1. **2つの並行システム**が存在し、AIエージェントの混乱を招いている
   - 旧: HabitType → NotificationScheduler → HabitSessionView (音声セッション)
   - 新: ProblemType → ProblemNotificationScheduler → NudgeCardView (カード)
2. **スキップされたOnboardingステップ**のコードが残っている
3. **Talkタブ関連コード**が非表示なのに残存

### 根拠: 未使用コード削除のベストプラクティス
- [Goldman Sachs](https://developer.gs.com/blog/posts/importance-of-deleting-unused-code): 67%のコードベース削減に成功
- [Meta SCARF](https://dl.acm.org/doi/10.1145/3611643.3613871): 自動的に未使用コードを検出・削除
- [Built In](https://builtin.com/software-engineering-perspectives/delete-old-dead-code-braintree): 「削除してもgit historyから復元可能」

---

## 現在のアーキテクチャ分析

### UIの状態

| 項目 | 状態 |
|------|------|
| FigmaTabBar | 2タブのみ表示 (My Path, Profile) |
| Talkタブ | **非表示** (コードは残存) |
| MainTabView | `case .talk: TalkView()` のコードが**残存** |

### Onboardingフロー

**現在のフロー（コード確認済み）:**
```
welcome → value → struggles → notifications → att → complete
```

**スキップされているステップ:**
- `account` (Sign in with Apple)
- `source` (流入元)
- `name` (名前入力)
- `gender` (性別)
- `age` (年齢)
- `ideals` (Ideal Self)
- `habitSetup` (習慣設定) ← これが最大の問題
- `alarmkit` (アラーム許可)

### 通知システムの二重構造

| システム | Scheduler | 通知タップ時 | 使用Enum |
|----------|-----------|-------------|----------|
| 旧 (習慣) | NotificationScheduler | HabitSessionView (音声) | HabitType |
| 新 (問題) | ProblemNotificationScheduler | NudgeCardView (カード) | ProblemType |

**問題**: 旧システムがまだ完全に動作している（AppDelegateでハンドリング）

---

## ファイル分類

### Category A: 完全に未使用（安全に削除可能）

| ファイル | 理由 | 依存関係 |
|----------|------|----------|
| `Views/Talk/TalkView.swift` | Talkタブ非表示 | SessionView, FeelingTopic, FeelingCard, QuoteCard |
| `Views/Talk/FeelingTopic.swift` | TalkView依存 | なし |
| `Views/Talk/FeelingCard.swift` | TalkView依存 | なし |
| `Views/Talk/QuoteCard.swift` | TalkView依存 | QuoteProvider (共有) |
| `Views/Session/SessionView.swift` | TalkViewからのみ呼び出し | VoiceSessionController, OrbView |
| `Intents/StartConversationIntent.swift` | Siri Intent、未使用 | HabitType, AppState |

### Category B: スキップされたOnboardingステップ

| ファイル | OnboardingStep | 到達可能性 |
|----------|---------------|------------|
| `Onboarding/HabitSetupStepView.swift` | `.habitSetup` | **到達不可** (struggles→notifications) |
| `Onboarding/IdealsStepView.swift` | `.ideals` | **到達不可** (value→struggles) |
| `Onboarding/AuthenticationStepView.swift` | `.account` | **到達不可** |
| `Onboarding/SourceStepView.swift` | `.source` | **到達不可** |
| `Onboarding/ProfileInfoStepView.swift` | `.name` | **到達不可** |
| `Onboarding/GenderStepView.swift` | `.gender` | **到達不可** |
| `Onboarding/AgeStepView.swift` | `.age` | **到達不可** |
| `Onboarding/AlarmKitPermissionStepView.swift` | `.alarmkit` | **到達不可** |

### Category C: 旧習慣システム（慎重に検討が必要）

**現在まだ動作している経路:**
```
通知タップ → AppDelegate.handleHabitLaunch() → prepareForImmediateSession()
→ MainTabView.fullScreenCover → HabitSessionView → VoiceSessionController
```

| ファイル | 役割 | 削除判断 |
|----------|------|----------|
| `Views/Session/HabitSessionView.swift` | 習慣音声セッション画面 | 経路を無効化してから削除 |
| `Views/Session/OrbView.swift` | 音声オーブUI | HabitSessionView依存 |
| `VoiceSessionController.swift` | 音声セッション制御 | HabitSessionView依存 |
| `AudioSessionCoordinator.swift` | オーディオ管理 | 音声セッション依存 |
| `Onboarding/HabitType.swift` | 旧習慣enum | 多数のファイルが依存 |
| `Models/PendingHabitTrigger.swift` | 習慣トリガー | AppState依存 |
| `WakePromptBuilder.swift` | 起床プロンプト生成 | 音声セッション用 |
| `Habits/HabitsTabView.swift` | 習慣タブ（未使用） | MyPathTabViewに置き換え済み |
| `Habits/HabitsSectionView.swift` | 習慣セクション | 使用状況要確認 |
| `Settings/HabitFollowUpView.swift` | フォローアップ設定 | Profile内で使用 |
| `Notifications/AlarmKitHabitCoordinator.swift` | AlarmKit連携 | 習慣通知用 |
| `Shared/HabitLaunchBridge.swift` | Intent連携 | AppDelegate依存 |

### Category D: 未使用だがUIパターンとして記録推奨

| ファイル | 記録先 | 理由 |
|----------|--------|------|
| `OrbView.swift` | `ui-patterns/voice-orb-animation.md` | 音声状態のビジュアル表現 |
| `HabitSetupStepView.swift` | `ui-patterns/time-picker-cards.md` | 時刻選択UIパターン |

---

## 実行計画

### Phase 1: ドキュメント更新（混乱防止）

#### 1.1 CLAUDE.md 更新

**技術スタック変更:**
```markdown
## 技術スタック（現在）
- **iOS**: Swift, SwiftUI
- **通知**: ProblemType-based Nudge System
- **決済**: RevenueCat, Superwall

## 非アクティブ機能（コード残存）
- 音声対話 (TalkView, VoiceSessionController)
- HabitType通知 (NotificationScheduler.habitAlarm)
```

**アーキテクチャセクション追加:**
```markdown
### 現在のコア機能
1. オンボーディング: 13個の問題（苦しみ）から選択
2. 通知: ProblemNotificationScheduler でルールベース Nudge
3. NudgeCard: 通知タップで1枚カード表示
4. My Path: 選択した問題の管理
```

### Phase 2: 安全な削除（Category A）

**削除順序:**
1. `Views/Talk/` ディレクトリ全体
2. `Views/Session/SessionView.swift`
3. `Intents/StartConversationIntent.swift`

**削除前チェック:**
```bash
# 参照確認
grep -r "TalkView" aniccaios/aniccaios --include="*.swift"
grep -r "SessionView" aniccaios/aniccaios --include="*.swift"
grep -r "StartConversationIntent" aniccaios/aniccaios --include="*.swift"
```

### Phase 3: Onboardingステップ削除（Category B）

**削除ファイル:**
- `HabitSetupStepView.swift`
- `IdealsStepView.swift`
- `AuthenticationStepView.swift`
- `SourceStepView.swift`
- `ProfileInfoStepView.swift`
- `GenderStepView.swift`
- `AgeStepView.swift`
- `AlarmKitPermissionStepView.swift`

**OnboardingFlowView.swift 更新:**
```swift
// 削除後のswitch文
switch step {
case .welcome:
    WelcomeStepView(next: advance)
case .value:
    ValueStepView(next: advance)
case .struggles:
    StrugglesStepView(next: advance)
case .notifications:
    NotificationPermissionStepView(next: advance)
case .att:
    ATTPermissionStepView(next: advance)
// 他のcaseは削除
}
```

**OnboardingStep.swift 更新:**
```swift
enum OnboardingStep: Int {
    case welcome = 0
    case value = 1
    case struggles = 2
    case notifications = 3
    case att = 4
}
```

### Phase 4: 旧習慣システム無効化（Category C）

**重要**: この Phase は慎重に実行

#### 4.1 経路の無効化

**AppDelegate.swift:**
```swift
// 旧: handleHabitLaunch → HabitSessionView
// 新: Problem Nudge のみ処理、旧習慣通知は無視

// didReceive内の習慣通知ハンドリングを削除またはログのみに変更
```

#### 4.2 MainTabView.swift 整理

```swift
// 削除:
// - case .talk: TalkView()
// - fullScreenCover(item: $activeHabitSession)
// - ActiveHabitSession struct
// - checkPendingHabitTrigger()
```

#### 4.3 AppState.swift 整理

**削除対象プロパティ:**
- `habitSchedules`
- `habitFollowupCounts`
- `pendingHabitTrigger`
- `shouldStartSessionImmediately`
- HabitType関連メソッド多数

**削除対象enum:**
```swift
// 変更:
enum RootTab: Int {
    case myPath = 0  // renamed from habits
    case profile = 1
    // talk は削除
}
```

#### 4.4 関連ファイル削除

- `VoiceSessionController.swift`
- `AudioSessionCoordinator.swift`
- `Views/Session/HabitSessionView.swift`
- `Views/Session/OrbView.swift`
- `Onboarding/HabitType.swift`
- `Models/PendingHabitTrigger.swift`
- `WakePromptBuilder.swift`
- `Habits/HabitsTabView.swift`
- `Habits/HabitsSectionView.swift`
- `Notifications/AlarmKitHabitCoordinator.swift`
- `Shared/HabitLaunchBridge.swift`

### Phase 5: NotificationScheduler 整理

**残すもの:**
- `Category.nudge`
- Problem通知のサポート

**削除:**
- `Category.habitAlarm`
- `Category.preReminder`（習慣用）
- HabitType関連のスケジューリングロジック

---

## UIパターン記録

### `.cursor/plans/ui-patterns/voice-orb-animation.md`

```markdown
# Voice Orb Animation Pattern

## 概要
音声セッション中の状態を視覚的に表現するアニメーションオーブ

## 元ファイル
`aniccaios/aniccaios/Views/Session/OrbView.swift`

## 状態
- Listening: 穏やかなパルス
- Speaking: 活発なパルス
- Connecting: スピン

## 実装ポイント
- SwiftUI Animation
- @ObservedObject VoiceSessionController.shared
- 状態に応じた色・サイズ変化
```

### `.cursor/plans/ui-patterns/time-picker-cards.md`

```markdown
# Time Picker Cards Pattern

## 概要
習慣ごとに時刻を設定するカードUI

## 元ファイル
`aniccaios/aniccaios/Onboarding/HabitSetupStepView.swift`

## 特徴
- Toggle付きカード
- Sheet式DatePicker
- 時系列ソート表示
```

---

## チェックリスト

### Phase 1: ドキュメント
- [ ] CLAUDE.md 技術スタック更新
- [ ] CLAUDE.md アーキテクチャ概要追加

### Phase 2: Talk関連削除
- [ ] UIパターン記録 (OrbView)
- [ ] `Views/Talk/` ディレクトリ削除
- [ ] `Views/Session/SessionView.swift` 削除
- [ ] `Intents/StartConversationIntent.swift` 削除
- [ ] ビルド確認

### Phase 3: Onboarding整理
- [ ] UIパターン記録 (HabitSetupStepView)
- [ ] スキップされたステップファイル削除
- [ ] OnboardingFlowView.swift 更新
- [ ] OnboardingStep.swift 更新
- [ ] ビルド確認

### Phase 4: 習慣システム無効化
- [ ] AppDelegate.swift 習慣ハンドリング削除
- [ ] MainTabView.swift Talk/HabitSession削除
- [ ] AppState.swift 習慣関連プロパティ削除
- [ ] 関連ファイル削除
- [ ] ビルド確認

### Phase 5: NotificationScheduler整理
- [ ] 習慣通知ロジック削除
- [ ] ビルド確認
- [ ] 動作確認

---

## 参考

- **リファクタリング方針**: CLAUDE.md「4. リファクタリング方針（未使用コードの扱い）」
- **Proactive Agent 仕様**: `.cursor/plans/ios/proactive/proactive-agent-spec.md`
- **ベストプラクティス根拠**:
  - [Goldman Sachs - Importance of Deleting Unused Code](https://developer.gs.com/blog/posts/importance-of-deleting-unused-code)
  - [Meta SCARF - Dead Code Removal](https://dl.acm.org/doi/10.1145/3611643.3613871)
  - [Built In - Delete Old Dead Code](https://builtin.com/software-engineering-perspectives/delete-old-dead-code-braintree)
  - [Avanderlee - Refactoring Swift Best Practices](https://www.avanderlee.com/optimization/refactoring-swift-best-practices/)
