# UX Specification: Zone2Daily

Source: [Apple HIG — Onboarding](https://developer.apple.com/design/human-interface-guidelines/onboarding) — 「Make a great first impression by guiding people quickly to the experience they're looking for.」
Source: [Appagent — Paywall Optimization](https://appagent.com/blog/mobile-app-onboarding-5-paywall-optimization-strategies/) — 「Paywall immediately after onboarding achieves up to +234% conversion.」
Source: [NN Group — Information Architecture](https://www.nngroup.com/articles/ia-vs-navigation/) — 「IA defines the structure of content; navigation defines how users move through it.」

---

## 1. User Personas

### Persona A: "Scientific Trainer" Marcus (プライマリ)

| 属性 | 内容 |
|------|------|
| 年齢 | 38歳 |
| 職業 | エンジニア / マーケター |
| デバイス | iPhone 15 Pro |
| トレーニング頻度 | 週4回ランニング |
| ゴール | Peter Attia の推奨する Zone 2 を週150分達成したい |
| フラストレーション | Apple Fitness+ / Strava は全ゾーン混在でわかりにくい。Zone 2 だけに特化したシンプルな tracker が欲しい |
| Willingness to Pay | $4.99/月なら即決。科学的根拠があれば価値を感じる |

### Persona B: "Health Conscious" Yuki (セカンダリ)

| 属性 | 内容 |
|------|------|
| 年齢 | 45歳 |
| 職業 | 会社員 |
| デバイス | iPhone 14 |
| トレーニング頻度 | 週3回（ランニング + 自転車） |
| ゴール | 脂肪燃焼を効率化。長寿プロトコルに興味あり |
| フラストレーション | 「ゆっくり走れ」と言われるが、どのくらいゆっくりかわからない |
| Willingness to Pay | $29.99/年なら検討（月割 $2.50 のバリュー感） |

---

## 2. Information Architecture

```
Zone2Daily
├── Onboarding（初回のみ）
│   ├── Age Input（年齢入力）
│   ├── Zone 2 Explainer（科学的説明）
│   ├── Notification Permission（通知許可）
│   └── PaywallView（ソフトペイウォール — Maybe Later 可）
│
├── Tab: Dashboard（🏠）
│   ├── Weekly Progress Ring（今週の Zone 2 分数 / 150分）
│   ├── Zone 2 HR 表示（Maffetone 計算値）
│   ├── Streak Badge（連続日数）
│   └── Recent Workouts（直近3件 — Free tier 制限）
│
├── Tab: Workout（⏱）
│   ├── WorkoutTimerView（タイマー + Zone 2 ガイド）
│   └── WorkoutLogView（終了後: Zone 2 滞在時間入力）
│
└── Tab: Settings（⚙️）
    ├── Age 変更
    ├── 週間目標変更（150分 → カスタム）
    ├── 通知時刻設定
    ├── Upgrade（→ PaywallView）
    ├── Restore Purchases
    ├── Privacy Policy リンク
    └── Terms of Service リンク
```

---

## 3. Navigation Structure

| 構造 | 実装 | 備考 |
|------|------|------|
| Tab Bar | `TabView` (3 tabs) | Dashboard / Workout / Settings |
| Onboarding | `NavigationStack` over Tab | 完了後に TabView へ切替 |
| Paywall | `.sheet` presentation | Settings の Upgrade tap で表示 |
| WorkoutLog | `NavigationStack` push | タイマー終了後に push |

### Tab Bar 定義

| Tab | Icon | accessibilityIdentifier | Badge |
|-----|------|------------------------|-------|
| Dashboard | `chart.bar.fill` | `tab_dashboard` | なし |
| Workout | `stopwatch.fill` | `tab_workout` | なし |
| Settings | `gearshape.fill` | `tab_settings` | なし |

---

## 4. Screen Inventory

| Screen ID | Name | Tab / Flow | File | Description |
|-----------|------|-----------|------|-------------|
| SCR-001 | AgeInputView | Onboarding | `Onboarding/AgeInputView.swift` | 年齢スライダー + Zone 2 HR プレビュー |
| SCR-002 | Zone2ExplainerView | Onboarding | `Onboarding/Zone2ExplainerView.swift` | Maffetone 式説明 + 科学的根拠 |
| SCR-003 | NotificationPermissionView | Onboarding | `Onboarding/NotificationPermissionView.swift` | 通知許可リクエスト |
| SCR-004 | PaywallView | Onboarding / Settings | `Onboarding/PaywallView.swift` | ソフトペイウォール（Maybe Later 付き）Rule 20 |
| SCR-005 | DashboardView | Dashboard Tab | `Dashboard/DashboardView.swift` | 週間進捗 + HR + ストリーク |
| SCR-006 | WeeklyProgressView | Dashboard (embed) | `Dashboard/WeeklyProgressView.swift` | 詳細週間グラフ |
| SCR-007 | WorkoutTimerView | Workout Tab | `Workout/WorkoutTimerView.swift` | タイマー + Zone 2 HR ガイド |
| SCR-008 | WorkoutLogView | Workout flow | `Workout/WorkoutLogView.swift` | ワークアウト記録入力 |
| SCR-009 | SettingsView | Settings Tab | `Settings/SettingsView.swift` | 設定画面 |

---

## 5. Wireframes

### SCR-001: AgeInputView（オンボーディング Step 1）

```
┌─────────────────────────────────────┐
│         ●  ○  ○  ○               │  ← OnboardingStepView (step: 1, total: 4)
│                                     │
│    Zone 2 Heart Rate Coach          │  ← title.large / text.primary
│                                     │
│    How old are you?                 │  ← headline / text.secondary
│                                     │
│         ┌──────────────┐            │
│         │     35       │            │  ← metric.large / brand.primary
│         │    years     │            │  ← subheadline / text.secondary
│         └──────────────┘            │
│                                     │
│    ←────────●──────────────→        │  ← AgeSlider (10-80)
│    10                      80       │
│                                     │
│    ┌─────────────────────────────┐  │
│    │  Your Zone 2 HR: 125-145   │  │  ← MetricCard / brand.success
│    │  (Maffetone: 180 - 35 = 145) │ │
│    └─────────────────────────────┘  │
│                                     │
│    ┌─────────────────────────────┐  │
│    │      Continue →             │  │  ← PrimaryButton / accessibilityIdentifier: "btn_continue_age"
│    └─────────────────────────────┘  │
└─────────────────────────────────────┘
```

### SCR-004: PaywallView（ソフトペイウォール — Rule 20 必須）

```
┌─────────────────────────────────────┐
│  ×  Maybe Later                     │  ← SecondaryButton / accessibilityIdentifier: "btn_maybe_later"
│                                     │
│    🔥 Unlock Your Zone 2 Potential  │  ← title.medium / text.primary
│                                     │
│    ★★★★★  4.9 · 200+ ratings      │  ← caption / text.secondary（社会的証明）
│                                     │
│  ✓ Unlimited workout history        │  ← PaywallBenefitRow
│  ✓ Full weekly analytics dashboard  │
│  ✓ Custom weekly goal setting       │
│  ✓ Daily streak tracking            │
│  ✓ Morning reminders customization  │
│                                     │
│  ┌─────────────┐  ┌──────────────┐  │
│  │  Monthly    │  │  Annual  🏆  │  │  ← pricing grid
│  │  $4.99/mo   │  │  $29.99/yr  │  │
│  │             │  │ Save 50% 🔥 │  │  ← "Best Value" highlighted
│  └─────────────┘  └──────────────┘  │
│                                     │
│  ┌─────────────────────────────────┐│
│  │     Start Training →            ││  ← PrimaryButton / accessibilityIdentifier: "btn_subscribe"
│  └─────────────────────────────────┘│
│                                     │
│  Restore Purchases                  │  ← text.link / accessibilityIdentifier: "btn_restore"
│                                     │
│  By subscribing you agree to our    │  ← footnote / text.tertiary
│  Terms of Service & Privacy Policy  │
└─────────────────────────────────────┘
```

### SCR-005: DashboardView（メイン画面）

```
┌─────────────────────────────────────┐
│  Zone2Daily            🔔           │  ← NavigationBar / notification icon
│                                     │
│  ┌─────────────────────────────────┐│
│  │    This Week                    ││  ← MetricCard
│  │         ◎                       ││  ← ProgressRing (週間進捗)
│  │      87/150 min                 ││  ← metric.medium / brand.primary
│  │    ████████░░░░ 58%             ││  ← progress bar
│  └─────────────────────────────────┘│
│                                     │
│  ┌──────────────┐ ┌────────────────┐│
│  │ Your Zone 2  │ │   🔥 Streak   ││  ← 2-column grid
│  │   HR Target  │ │   5 days      ││
│  │  125-145 bpm │ │               ││
│  └──────────────┘ └────────────────┘│
│                                     │
│  Recent Workouts                    │  ← headline / text.primary
│  ┌─────────────────────────────────┐│
│  │ Mon · 45 min · Zone 2: 38 min  ││  ← WorkoutHistoryRow
│  │ Fri · 30 min · Zone 2: 25 min  ││
│  │ Wed · 60 min · Zone 2: 50 min  ││
│  └─────────────────────────────────┘│
│                                     │
│  🔒 Unlock full history →           │  ← Free tier upsell（有料機能）
│                                     │
└─────────────────────────────────────┘
```

### SCR-007: WorkoutTimerView（ワークアウト画面）

```
┌─────────────────────────────────────┐
│  Today's Workout                    │  ← NavigationBar
│                                     │
│  ┌─────────────────────────────────┐│
│  │  Stay in Zone 2:               ││  ← MetricCard / bg.secondary
│  │  125 - 145 bpm                 ││  ← metric.large / brand.success
│  │                                 ││
│  │  HRZoneIndicator               ││  ← zone bar visualization
│  └─────────────────────────────────┘│
│                                     │
│         00 : 24 : 37               │  ← metric.large タイマー表示
│                                     │
│    Zone 2 time: 00:18:42           │  ← zone2 経過時間（入力後に表示）
│                                     │
│  ┌──────────────────────────────┐   │
│  │       ■ Stop Workout         │   │  ← PrimaryButton(danger) / accessibilityIdentifier: "btn_stop_workout"
│  └──────────────────────────────┘   │
│                                     │
│  Keep your heart rate between       │  ← callout / text.secondary
│  125-145 bpm for fat burning        │
└─────────────────────────────────────┘
```

---

## 6. Onboarding Flow

**🔴 Rule 20: 最終画面 = ソフトペイウォール必須。[Maybe Later] で閉じれる。**

```
Start
  │
  ▼
SCR-001: AgeInputView
  - 年齢スライダー（10-80、デフォルト 35）
  - Zone 2 HR リアルタイムプレビュー（180 - age = 上限, -10 = 下限）
  - [Continue →] → SCR-002
  │
  ▼
SCR-002: Zone2ExplainerView
  - 見出し: "Why Zone 2 Works"
  - Peter Attia / Andrew Huberman の推薦テキスト
  - Maffetone 式の図解
  - 週150分目標の科学的根拠
  - [Got it! →] → SCR-003
  │
  ▼
SCR-003: NotificationPermissionView
  - 見出し: "Stay Consistent"
  - モーニングリマインダーの説明
  - [Enable Reminders] → UNUserNotificationCenter.requestAuthorization()
  - [Not Now] → SCR-004（スキップ可）
  │
  ▼
SCR-004: PaywallView（Rule 20: 必須ソフトペイウォール）
  - [× Maybe Later] で閉じて Dashboard へ（Free tier で継続）
  - [Start Training →] で購入フロー（Purchases.shared.purchase(package:)）
  - 購入完了 / Maybe Later → DashboardView（Tab切替）
```

### オンボーディング完了条件

| 条件 | 保存先 |
|------|--------|
| `hasCompletedOnboarding = true` | UserDefaults |
| `UserProfile(age:)` 保存 | SwiftData |

---

## 7. Accessibility

全 `accessibilityIdentifier` テーブル。Maestro E2E テストで使用するため全て必須。

| ID | Screen | Element | Type |
|----|--------|---------|------|
| `tab_dashboard` | TabView | Dashboard タブ | Tab |
| `tab_workout` | TabView | Workout タブ | Tab |
| `tab_settings` | TabView | Settings タブ | Tab |
| `slider_age` | SCR-001 | 年齢スライダー | Slider |
| `label_zone2_hr` | SCR-001 | Zone 2 HR プレビューラベル | Label |
| `btn_continue_age` | SCR-001 | Continue ボタン | Button |
| `btn_continue_explainer` | SCR-002 | Got it! ボタン | Button |
| `btn_enable_notifications` | SCR-003 | Enable Reminders ボタン | Button |
| `btn_skip_notifications` | SCR-003 | Not Now リンク | Button |
| `btn_maybe_later` | SCR-004 | Maybe Later ボタン | Button |
| `btn_subscribe` | SCR-004 | Start Training ボタン | Button |
| `btn_restore` | SCR-004 | Restore Purchases リンク | Button |
| `selector_plan_monthly` | SCR-004 | Monthly プラン選択 | Button |
| `selector_plan_annual` | SCR-004 | Annual プラン選択 | Button |
| `label_weekly_progress` | SCR-005 | 週間分数ラベル | Label |
| `ring_weekly_progress` | SCR-005 | 進捗リング | View |
| `label_zone2_target` | SCR-005 | Zone 2 HR ターゲット | Label |
| `label_streak` | SCR-005 | ストリーク数 | Label |
| `btn_start_workout` | SCR-007 | ワークアウト開始ボタン | Button |
| `btn_stop_workout` | SCR-007 | ワークアウト停止ボタン | Button |
| `label_timer` | SCR-007 | タイマー表示 | Label |
| `label_zone2_time` | SCR-007 | Zone 2 経過時間 | Label |
| `input_zone2_minutes` | SCR-008 | Zone 2 分数入力 | TextField |
| `btn_save_workout` | SCR-008 | Save Workout ボタン | Button |
| `input_age_settings` | SCR-009 | 年齢設定入力 | TextField |
| `btn_upgrade` | SCR-009 | Upgrade ボタン（Paywall 表示） | Button |
| `toggle_notifications` | SCR-009 | 通知 ON/OFF トグル | Toggle |

---

## 8. Interaction Patterns

| パターン | トリガー | 挙動 |
|---------|---------|------|
| スワイプで次のオンボーディングステップ | 右→左スワイプ | `NavigationStack` push（0.35s slide） |
| Paywall の月額/年額切替 | タップ | ボーダー色変更 + チェックマーク（0.2s） |
| ワークアウト開始 | `btn_start_workout` タップ | タイマー開始 + ボタン→Stop に変化 |
| ワークアウト停止 | `btn_stop_workout` タップ | 確認 ActionSheet → WorkoutLogView push |
| ストリーク更新 | ワークアウト保存後 | `StreakBadge` バウンスアニメーション（0.4s） |
| Free tier 上限到達 | 4件目ワークアウト閲覧 | PaywallView `.sheet` 表示 |
| 長押し履歴行 | WorkoutHistoryRow 長押し | Delete 確認 Alert |
| プルツーリフレッシュ | Dashboard 下引き | RevenueCat customerInfo 更新 |

---

## 9. Localization Notes

| 言語 | ロケール | 文字列長 | 考慮点 |
|------|---------|---------|-------|
| English | en-US | 基準 | — |
| Japanese | ja | +20〜40% 長 | CTA ボタン幅を動的サイズに。固定幅禁止 |

### 特に注意が必要な文字列

| 画面 | en-US | ja | 対策 |
|------|-------|-----|------|
| Paywall CTA | "Start Training" | 「トレーニングを始める」 | `PrimaryButton` で `.dynamicTypeSize` 対応 |
| Tab: Dashboard | "Dashboard" | 「ダッシュボード」 | Tab label を短縮しない |
| Settings: Notifications | "Enable Reminders" | 「リマインダーを有効にする」 | ボタン幅 flexible |

### Localizable.xcstrings 管理

| キー | en-US | ja |
|-----|-------|-----|
| `onboarding.age.title` | "How old are you?" | "何歳ですか？" |
| `onboarding.age.zone2preview` | "Your Zone 2 HR: %d–%d bpm" | "あなたのゾーン2 HR: %d〜%d bpm" |
| `onboarding.explainer.title` | "Why Zone 2 Works" | "ゾーン2が効果的な理由" |
| `onboarding.notification.title` | "Stay Consistent" | "習慣を継続しよう" |
| `paywall.headline` | "Unlock Your Zone 2 Potential" | "ゾーン2の可能性を解放" |
| `paywall.cta` | "Start Training" | "トレーニングを始める" |
| `paywall.maybeLater` | "Maybe Later" | "あとで" |
| `dashboard.weeklyGoal` | "This Week: %d/%d min" | "今週: %d/%d分" |
| `dashboard.streak` | "%d day streak" | "%d日連続" |
| `workout.zone2target` | "Zone 2: %d–%d bpm" | "ゾーン2: %d〜%d bpm" |
