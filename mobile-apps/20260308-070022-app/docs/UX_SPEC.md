# UX Specification: LymphaFlow

Source: [Apple HIG App Architecture](https://developer.apple.com/design/human-interface-guidelines/app-architecture) — 「Navigation should reflect the structure and purpose of your app.」
Source: [Apple HIG Onboarding](https://developer.apple.com/design/human-interface-guidelines/onboarding) — 「Help people get started quickly. Focus on the most important task.」
Source: [Adapty iOS Paywall Guide](https://adapty.io/blog/how-to-design-ios-paywall/) — 「Paywall immediately after onboarding achieves highest visibility.」

---

## 1. User Personas

### Persona A — "むくみ悩み美容女子" (Primary)

| 属性 | 値 |
|------|-----|
| 名前 | Yuki（30歳、東京在住）|
| 職業 | リモートワーク会社員 |
| デバイス | iPhone 15 (iOS 17) |
| 問題 | 夕方になると足・顔がむくむ。TikTokで#lymphaticdrainage を見て試したいが、正確な手順を覚えられない |
| ゴール | 毎朝10分のリンパマッサージを習慣化する |
| フラストレーション | 動画を再生しながら実践しにくい。どこを何秒マッサージすればいいか不明 |
| 支払い意欲 | $29.99/年（年間でコーヒー数杯分の価値を感じる）|

### Persona B — "術後リカバリー中" (Secondary)

| 属性 | 値 |
|------|-----|
| 名前 | Sarah（38歳、California）|
| 職業 | 在宅フリーランサー |
| デバイス | iPhone 14 Pro (iOS 17) |
| 問題 | 乳がん術後のリンパ浮腫ケア。医師からセルフドレナージュを勧められたが方法が分からない |
| ゴール | 医師の指示に沿ったセルフケアを毎日継続する |
| フラストレーション | 専門書は難しい。デバイス型ツール（Kylee）は高価で一般向けではない |
| 支払い意欲 | $4.99/月（月額医療費に比べ安い）|

---

## 2. Information Architecture

```
LymphaFlow
│
├── [初回起動] OnboardingFlow
│   ├── OnboardingPage1 (アプリ紹介)
│   ├── OnboardingPage2 (機能紹介)
│   ├── OnboardingPage3 (ルーティン選択プレビュー)
│   ├── NotificationPermissionView
│   └── PaywallView ← [ソフトペイウォール — Rule 20]
│       └── [Maybe Later] → HomeView
│
└── [メインApp] TabView
    ├── Tab 1: HomeView (ホーム)
    │   ├── RoutineCard × N (Free: 3 / Pro: 12)
    │   └── [タップ] → SessionView
    │       ├── StepView × N (ステップバイステップ)
    │       └── SessionCompleteView (完了画面)
    │
    ├── Tab 2: ProgressDashboardView (進捗)
    │   ├── StreakBadge
    │   ├── Calendar (月間達成カレンダー)
    │   └── SessionHistoryList
    │
    └── Tab 3: SettingsView (設定)
        ├── SubscriptionStatus
        ├── [Upgrade] → PaywallView
        ├── NotificationSettings
        ├── ReminderTimePicker (朝/夜)
        ├── RestorePurchases
        └── Links (Privacy Policy / Terms)
```

---

## 3. Navigation Structure

Source: [Apple HIG Tab Bars](https://developer.apple.com/design/human-interface-guidelines/tab-bars) — 「Tab bars let people navigate between sections of an app.」

### Tab Bar Configuration

| Tab | Screen | SF Symbol | Accessibility Label |
|-----|--------|-----------|---------------------|
| 0 | HomeView | `house.fill` | "Home" |
| 1 | ProgressDashboardView | `chart.bar.fill` | "Progress" |
| 2 | SettingsView | `gearshape.fill` | "Settings" |

### Navigation Modality

| Navigation Type | 用途 |
|----------------|------|
| `NavigationStack` | HomeView → SessionView → SessionCompleteView |
| `.sheet` | PaywallView (onboarding後 & Settings Upgrade) |
| `.fullScreenCover` | OnboardingFlow (初回起動のみ) |

---

## 4. Screen Inventory

| Screen ID | Name | Tab | Description |
|-----------|------|-----|-------------|
| SCR-001 | OnboardingPage1 | — | "Feel Lighter Every Day" ヒーロー画面 |
| SCR-002 | OnboardingPage2 | — | "Step-by-Step + Timer" 機能紹介 |
| SCR-003 | OnboardingPage3 | — | "Build Your Daily Habit" ストリーク紹介 |
| SCR-004 | NotificationPermissionView | — | "Set Your Daily Reminder" 通知許可 |
| SCR-005 | PaywallView | — | ソフトペイウォール（Rule 20）|
| SCR-006 | HomeView | 0 | ルーティン一覧（Free 3 / Pro 12）|
| SCR-007 | SessionView | 0 | ステップバイステップガイド + タイマー |
| SCR-008 | SessionCompleteView | 0 | セッション完了 + ストリーク更新 |
| SCR-009 | ProgressDashboardView | 1 | ストリーク + カレンダー + 履歴 |
| SCR-010 | SettingsView | 2 | サブスク管理 + 通知設定 |

---

## 5. Wireframes

### SCR-006: HomeView

```
┌─────────────────────────────────┐
│ [LymphaFlow]         [🔥 7日]   │ ← DSTextPrimary, streak badge
│                                 │
│ ┌─────────────────────────────┐ │
│ │ ☀️  Morning Routine         │ │ ← DSRoutineCard (Pro locked if Free)
│ │     5 min · 4 steps         │ │
│ │     [PRO] 🔒                │ │
│ └─────────────────────────────┘ │
│                                 │
│ ┌─────────────────────────────┐ │
│ │ 😊  Face Drainage           │ │ ← Free ルーティン
│ │     5 min · 6 steps         │ │
│ └─────────────────────────────┘ │
│                                 │
│ ┌─────────────────────────────┐ │
│ │ 💆  Neck & Collarbone       │ │ ← Free ルーティン
│ │     5 min · 5 steps         │ │
│ └─────────────────────────────┘ │
│                                 │
│ [🏠 Home] [📊 Progress] [⚙️ Settings] │
└─────────────────────────────────┘
```

### SCR-007: SessionView (ステップ表示)

```
┌─────────────────────────────────┐
│ [< Back]   Step 2 of 6    [Skip]│
│─────────────────────────────────│
│                                 │
│    ┌─────────────────────────┐  │
│    │   [イラスト placeholder] │  │ ← DSSpacing.lg パディング
│    │     SF Symbol or image   │  │
│    └─────────────────────────┘  │
│                                 │
│      Neck Sweep                 │ ← DSFont.title2
│  Gently sweep from behind       │ ← DSFont.body
│  your ear down to collarbone.   │
│  Repeat 5 times each side.      │
│                                 │
│         ┌─────────┐             │
│         │  0:45   │             │ ← DSFont.timerDisplay
│         │ ●●●●○○  │             │ ← DSTimerRing
│         └─────────┘             │
│                                 │
│  [=========>          ] 33%     │ ← DSProgressBar (DSColor.primary)
│                                 │
│    [    ✓ Done / Next    ]      │ ← DSPrimaryButton
└─────────────────────────────────┘
```

### SCR-005: PaywallView (ソフトペイウォール)

```
┌─────────────────────────────────┐
│                         [✕ Later]│ ← DSGhostButton (Maybe Later — Rule 20)
│                                 │
│  ★★★★★  4.8 · 2,400 ratings    │ ← Social proof
│                                 │
│  Unlock Your Full Body          │ ← DSFont.largeTitle, DSColor.textPrimary
│  Lymph Journey 💧               │
│                                 │
│  ✅ All 12 body areas           │
│  ✅ Morning & Evening programs  │
│  ✅ Goal-based routines         │ ← Benefits list (5項目)
│  ✅ Full progress dashboard     │
│  ✅ Priority support            │
│                                 │
│ ┌─────────┐   ┌───────────────┐ │
│ │ Monthly │   │  Annual 🏆    │ │ ← DSColor.primary border
│ │  $4.99  │   │  $29.99/yr   │ │
│ │   /mo   │   │ $2.49/mo     │ │
│ │         │   │  Save 50%    │ │
│ └─────────┘   └───────────────┘ │
│                                 │
│  [ Start 7-Day Free Trial ]     │ ← DSPrimaryButton (Annual選択時)
│  [ Subscribe Monthly      ]     │ ← DSSecondaryButton (Monthly選択時)
│                                 │
│  Cancel anytime · FAQ ▼         │ ← DSFont.footnote
│  Privacy Policy · Terms         │
└─────────────────────────────────┘
```

### SCR-009: ProgressDashboardView

```
┌─────────────────────────────────┐
│ Progress                        │
│─────────────────────────────────│
│                                 │
│    🔥 12                        │ ← DSStreakBadge (streak count)
│    Day Streak                   │ ← DSFont.streakNumber
│                                 │
│  March 2026                     │
│  Mo Tu We Th Fr Sa Su           │
│  ●  ●  ●  ●  ●  ○  ●           │ ← 達成: DSColor.success, 未: DSColor.streakInactive
│  ...                            │
│                                 │
│  Recent Sessions                │
│  ────────────────               │
│  Face Drainage    Mar 8  5min   │
│  Neck Collarbone  Mar 7  5min   │
│  ...                            │
└─────────────────────────────────┘
```

---

## 6. Onboarding Flow

Source: [Appagent Paywall Optimization](https://appagent.com/blog/mobile-app-onboarding-5-paywall-optimization-strategies/) — 「Paywall immediately after onboarding: up to +234% conversion.」

```
App Launch (初回)
     ↓
SCR-001: OnboardingPage1
"Feel Lighter Every Day"
[Continue →]
     ↓
SCR-002: OnboardingPage2
"Step-by-Step + Timer"
[Continue →]
     ↓
SCR-003: OnboardingPage3
"Build Your Streak"
[Continue →]
     ↓
SCR-004: NotificationPermissionView
"Set Your Daily Reminder"
[Allow Notifications] / [Skip]
     ↓
SCR-005: PaywallView ← MUST (Rule 20)
[Start 7-Day Free Trial] → MainApp (isPro=true)
[Subscribe Monthly]     → MainApp (isPro=true)
[✕ Maybe Later]         → MainApp (isPro=false) ← MUST (Rule 20: soft paywall)
     ↓
SCR-006: HomeView (メインアプリ)
```

### Onboarding Design Rules

| Rule | 詳細 |
|------|------|
| 最大4ページ（コンテンツ3 + 通知1）| HIG「Don't require people to sign in before doing anything useful」|
| 各ページに1つの明確なメッセージ | 認知負荷最小化 |
| [Maybe Later] ボタンは必ず表示 | Rule 20: ソフトペイウォール。強制購入禁止 |
| ATT ダイアログなし | Rule 20b |
| Sign in with Apple なし | Out of Scope（Maestro E2E自動化不可）|

---

## 7. Accessibility

Source: [Apple HIG Accessibility Identifiers](https://developer.apple.com/documentation/swiftui/view/accessibilityidentifier(_:)) — 「Use accessibilityIdentifier to identify elements in automated tests.」

### accessibilityIdentifier Table（Maestro E2E用）

| ID | Screen | Element | Type |
|----|--------|---------|------|
| `onboarding_page_1` | SCR-001 | OnboardingPageView コンテナ | View |
| `onboarding_continue_btn` | SCR-001〜003 | Continue ボタン | Button |
| `notification_allow_btn` | SCR-004 | Allow Notifications ボタン | Button |
| `notification_skip_btn` | SCR-004 | Skip ボタン | Button |
| `paywall_view` | SCR-005 | PaywallView コンテナ | View |
| `paywall_annual_option` | SCR-005 | Annual プラン選択 | Button |
| `paywall_monthly_option` | SCR-005 | Monthly プラン選択 | Button |
| `paywall_cta_button` | SCR-005 | CTA ボタン（Trial / Subscribe）| Button |
| `paywall_maybe_later_button` | SCR-005 | Maybe Later / ✕ ボタン | Button |
| `home_view` | SCR-006 | HomeView コンテナ | View |
| `routine_card_{id}` | SCR-006 | ルーティンカード（例: `routine_card_face`）| Button |
| `pro_lock_badge` | SCR-006 | Pro ロックバッジ | View |
| `session_view` | SCR-007 | SessionView コンテナ | View |
| `step_card_{index}` | SCR-007 | ステップカード（例: `step_card_0`）| View |
| `timer_ring` | SCR-007 | タイマーリング | View |
| `step_done_btn` | SCR-007 | Done / Next ボタン | Button |
| `session_complete_view` | SCR-008 | 完了画面コンテナ | View |
| `session_home_btn` | SCR-008 | Back to Home ボタン | Button |
| `progress_view` | SCR-009 | ProgressDashboardView コンテナ | View |
| `streak_badge` | SCR-009 | ストリークバッジ | View |
| `settings_view` | SCR-010 | SettingsView コンテナ | View |
| `settings_upgrade_btn` | SCR-010 | Upgrade ボタン | Button |
| `settings_restore_btn` | SCR-010 | Restore Purchases ボタン | Button |
| `settings_morning_time` | SCR-010 | 朝リマインダー時刻 Picker | Picker |
| `settings_evening_time` | SCR-010 | 夜リマインダー時刻 Picker | Picker |

---

## 8. Interaction Patterns

| Pattern | 操作 | 画面 | 動作 |
|---------|------|------|------|
| Tap | タップ | HomeView RoutineCard | SessionView へ遷移 |
| Tap | タップ | SessionView Done/Next | 次ステップへ進む（最終ステップで完了）|
| Tap | タップ | PaywallView [Maybe Later] | PaywallView を閉じて HomeView へ |
| Swipe | 水平スワイプ | OnboardingPageView | 次/前ページへ遷移（PageTabViewStyle）|
| Long Press | 長押し | ProgressDashboardView カレンダー日付 | その日のセッション詳細表示（.popover）|
| Tap | タップ | Pro Locked RoutineCard | PaywallView を表示 |
| Tap | タップ | Settings Upgrade | PaywallView を `.sheet` 表示 |

### エラー状態のインタラクション

| エラー | UI 対応 |
|--------|---------|
| RevenueCat 購入失敗 | `.alert("Purchase failed. Please try again.")` |
| RevenueCat 復元失敗 | `.alert("Could not restore purchases.")` |
| オフライン時 | トースト非表示（RC がキャッシュ利用のため透過的に動作）|
| 通知許可拒否 | SettingsView に「通知を有効にするには設定アプリへ」バナー |

---

## 9. Localization Notes

Source: [Apple HIG Localization](https://developer.apple.com/design/human-interface-guidelines/inclusion) — 「Adapt content for different languages and regions.」

### 文字列長差異

| 言語 | 特性 | UI 対応 |
|------|------|---------|
| en-US | 基準長（100%）| 標準レイアウト |
| ja | 漢字で短縮（70-80%）| maxWidth制約なし。折り返し許容 |

### 日本語特有の考慮事項

| 項目 | 対応 |
|------|------|
| フォント | San Francisco + ヒラギノ角ゴシック（システムデフォルト）|
| 数字 | アラビア数字（"12" not "十二"）|
| 価格 | "$4.99/月" — ¥換算ではなくドル表記（App Store が換算表示する）|
| 「Maybe Later」翻訳 | "後で" — ダークパターン回避のため否定的な表現を使わない |
| PaywallView CTA | "7日間無料で試す" — 直訳より自然な日本語 |

### Localizable.xcstrings キー命名規則

```
// 命名: <screen>.<element>.<property>
"home.morning_routine.title" = "Morning Routine"
"session.step_done_btn.label" = "Done"
"paywall.maybe_later_btn.label" = "Maybe Later"
"paywall.headline" = "Unlock Your Full Body Lymph Journey"
```

### 対応言語ファイル

| ファイル | 内容 |
|---------|------|
| `Localizable.xcstrings` | UI 全文字列（en-US + ja）|
| `routines.json` | ルーティンデータ（`titleKey` / `descriptionKey` で Localizable 参照）|
