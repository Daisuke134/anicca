# UX Specification: VagusReset

Source: [Apple Human Interface Guidelines — App Architecture](https://developer.apple.com/design/human-interface-guidelines/app-architecture) — 「Provide clear, predictable navigation so users always know where they are」
Source: [Nielsen Norman Group — Onboarding UX](https://www.nngroup.com/articles/mobile-app-onboarding/) — 「Reduce friction during first use to improve retention」
Source: [Appagent Paywall Optimization](https://appagent.com/blog/mobile-app-onboarding-5-paywall-optimization-strategies/) — 「Paywall immediately after onboarding achieves 100% visibility rate」

---

## 1. User Personas

### Persona A: ストレス過多のデスクワーカー（Primary）

| 属性 | 詳細 |
|------|------|
| 名前 | Sarah（さくら） |
| 年齢 | 32歳 |
| 職業 | IT企業勤務（在宅ワーク） |
| 主な悩み | 会議が多く、終業後も頭が切れない。睡眠の質が低下している |
| 目標 | センサーなし、5分以内で自律神経を整えたい |
| 挫折パターン | 「続かなかったら意味がない」→ ストリーク機能で習慣化 |
| 課金耐性 | Headspace 経験あり。月$5–10 は許容範囲 |

### Persona B: 子育て中の親（Secondary）

| 属性 | 詳細 |
|------|------|
| 名前 | Mark（まさき） |
| 年齢 | 38歳 |
| 職業 | 営業職（2児の父） |
| 主な悩み | 子育てと仕事のストレスで常に交感神経優位 |
| 目標 | 隙間時間（2分）でリセットできる手法が欲しい |
| 挫折パターン | 道具が必要なものは続かない → センサー不要を強調 |
| 課金耐性 | 家計意識高め → 年間プランの割引価値を重視 |

---

## 2. Information Architecture

```
VagusReset
├── [Onboarding — 初回のみ]
│   ├── Step1: 問題提示（共感フック）
│   ├── Step2: 解決策 + 通知権限リクエスト
│   └── Step3: ソフトペイウォール（PaywallView）
│
└── [メインアプリ — TabView 2タブ]
    ├── Tab1: ホーム (HomeView)
    │   ├── 今日のルーティン表示
    │   ├── デイリーストリーク
    │   └── エクササイズカード一覧
    │       └── ExerciseCard タップ → SessionView
    │           └── セッション完了 → 完了アニメーション
    └── Tab2: 設定 (SettingsView)
        ├── サブスク状態
        ├── Upgrade → PaywallView（有料未登録時）
        ├── 通知時間設定
        └── 購入の復元
```

---

## 3. Navigation Structure

| Screen | 遷移方法 | 戻り方 |
|--------|---------|--------|
| OnboardingView | アプリ初回起動時に fullScreenCover | 不要（完了後に消える） |
| HomeView | Tab1（ルート） | — |
| SessionView | NavigationLink from ExerciseCard | NavigationStack「戻る」or 完了で自動 |
| PaywallView（オンボーディング） | オンボーディング Step3 として表示 | [Maybe Later] タップで閉じる |
| PaywallView（設定から） | sheet from SettingsView | スワイプ down or × |
| SettingsView | Tab2（ルート） | — |
| ProgressCalendarView | NavigationLink from SettingsView | NavigationStack「戻る」|

**NavigationStack:** iOS 16+ の `NavigationStack` + `NavigationPath` を使用。`NavigationLink(value:)` で型安全遷移。

---

## 4. Screen Inventory

| Screen ID | Name | Tab | Description |
|-----------|------|-----|-------------|
| S-001 | OnboardingStep1View | — | 問題提示: 「自律神経が乱れていませんか?」共感フック |
| S-002 | OnboardingStep2View | — | 解決策提示 + 通知権限リクエスト |
| S-003 | PaywallView | — | ソフトペイウォール (Rule 20): Monthly/Annual + [Maybe Later] |
| S-004 | HomeView | Tab1 | 今日のルーティン + デイリーストリーク + エクササイズカード一覧 |
| S-005 | SessionView | — | タイマー付きエクササイズガイド画面 |
| S-006 | SessionCompleteView | — | 完了アニメーション + 次のエクササイズへ |
| S-007 | SettingsView | Tab2 | サブスク管理・通知設定・Upgrade |
| S-008 | ProgressCalendarView | — | 月次完了カレンダー（有料機能） |

---

## 5. Wireframes

### S-001: OnboardingStep1View（問題提示）

```
┌─────────────────────────────┐
│  [ページインジケーター: ●○○]   │
│                              │
│   🌊 [大きなイラスト/アイコン] │
│                              │
│   「毎日なんとなく疲れていませ │
│    んか?」                   │
│   (displayLarge, Center)    │
│                              │
│   ストレス・不安・睡眠の質低下。│
│   その原因は自律神経かもしれない│
│   (bodyMedium, Center)      │
│                              │
│   世界3億人超が不安障害に悩む  │
│   (bodySmall, colorTextSec) │
│                              │
│  ┌─────────────────────────┐ │
│  │  次へ (PrimaryButton)   │ │
│  └─────────────────────────┘ │
└─────────────────────────────┘
accessibilityIdentifier: "onboarding_step1_next_button"
```

### S-002: OnboardingStep2View（解決策 + 通知）

```
┌─────────────────────────────┐
│  [ページインジケーター: ○●○]   │
│                              │
│   ✨ [ハミング/うがいイラスト]  │
│                              │
│   「迷走神経リセットで         │
│    2分で整える」              │
│   (displayMedium, Center)   │
│                              │
│   センサー不要。哼り・うがい・   │
│   冷水だけで自律神経を整える    │
│   (bodyMedium)              │
│                              │
│  ┌─────────────────────────┐ │
│  │  通知をオンにする          │ │
│  │  (PrimaryButton)        │ │
│  └─────────────────────────┘ │
│   後でスキップ (GhostButton)  │
└─────────────────────────────┘
accessibilityIdentifier: "onboarding_step2_notification_button"
accessibilityIdentifier: "onboarding_step2_skip_button"
```

### S-003: PaywallView（ソフトペイウォール）

```
┌─────────────────────────────┐
│  [グラデーション背景           │
│   colorPaywallGradientStart] │
│                              │
│   「VagusReset Premium」      │
│   (headlineLarge, white)    │
│                              │
│   ✓ 20+エクササイズ無制限      │
│   ✓ ストリーク無制限           │
│   ✓ 進捗カレンダー            │
│   ✓ 詳細ガイド付き            │
│                              │
│  ┌───────────┬─────────────┐ │
│  │  月額プラン  │  年間プラン  │ │
│  │  $4.99/mo  │  $29.99/yr │ │
│  │           │ ★Best Value│ │
│  │           │  Save 50%  │ │
│  └───────────┴─────────────┘ │
│                              │
│  ┌─────────────────────────┐ │
│  │  Start My Reset         │ │
│  │  (PrimaryButton, white) │ │
│  └─────────────────────────┘ │
│   Maybe Later (GhostButton) │
│   Privacy Policy | Terms    │
└─────────────────────────────┘
accessibilityIdentifier: "paywall_monthly_plan_card"
accessibilityIdentifier: "paywall_annual_plan_card"
accessibilityIdentifier: "paywall_cta_button"
accessibilityIdentifier: "paywall_maybe_later_button"
```

### S-004: HomeView（ホーム）

```
┌─────────────────────────────┐
│  VagusReset        🔔        │
│                              │
│  ┌──────────────────────── ┐ │
│  │  🔥 7日連続！             │ │
│  │  StreakBadge            │ │
│  └─────────────────────────┘ │
│                              │
│  「今日のリセット」            │
│  (headlineMedium)           │
│                              │
│  ┌─────────────────────────┐ │
│  │ 🎵 ハミング呼吸   60s [>]│ │
│  └─────────────────────────┘ │
│  ┌─────────────────────────┐ │
│  │ 💧 うがいリセット  45s [>]│ │
│  └─────────────────────────┘ │
│  ┌─────────────────────────┐ │
│  │ 🔒 冷水スプラッシュ [🔒] │ │
│  └─────────────────────────┘ │
│  [Tab: 🏠 ホーム | ⚙ 設定]   │
└─────────────────────────────┘
accessibilityIdentifier: "home_streak_badge"
accessibilityIdentifier: "home_exercise_card_\(exercise.id)"
accessibilityIdentifier: "home_tab_bar"
```

### S-005: SessionView（タイマー）

```
┌─────────────────────────────┐
│  ← 戻る          ⏸         │
│                              │
│   「ハミング呼吸」             │
│   (headlineLarge, Center)   │
│                              │
│      ┌──────────────┐        │
│      │  ◯ タイマー   │        │
│      │    0:45      │        │
│      │  (timerDisplay)│       │
│      └──────────────┘        │
│                              │
│   ガイド: 口を閉じ、鼻から息を   │
│   吸い、「んー」と哼る。        │
│   (bodyMedium)              │
│                              │
│  ┌─────────────────────────┐ │
│  │  スタート (PrimaryButton)│ │
│  └─────────────────────────┘ │
└─────────────────────────────┘
accessibilityIdentifier: "session_timer_ring"
accessibilityIdentifier: "session_start_button"
accessibilityIdentifier: "session_pause_button"
accessibilityIdentifier: "session_back_button"
```

---

## 6. Onboarding Flow

Source: [Appagent Paywall Optimization](https://appagent.com/blog/mobile-app-onboarding-5-paywall-optimization-strategies/) — 「Show paywall immediately after onboarding for 100% visibility rate」
Source: Rule 20 — 「オンボーディング最終画面はソフトペイウォール必須。[Maybe Later] で閉じれる」

```
アプリ起動
    │
    ▼ (onboarding.complete == false)
OnboardingView (TabView, 3ページ)
    │
    ├─ Page 1: OnboardingStep1View
    │   問題提示「毎日なんとなく疲れていませんか?」
    │   → [次へ] タップ
    │
    ├─ Page 2: OnboardingStep2View
    │   解決策「迷走神経リセットで2分で整える」
    │   → [通知をオンにする]: UNUserNotificationCenter.requestAuthorization()
    │   → [後でスキップ]: 通知なしで次へ
    │
    └─ Page 3: PaywallView (Rule 20 必須)
        ソフトペイウォール
        → [Start My Reset]: Purchases.shared.purchase(package:)
        → [Maybe Later]: onboarding.complete = true → HomeView へ
```

**オンボーディングルール（Rule 20 準拠）:**

| ルール | 実装 |
|--------|------|
| 最終画面 = ソフトペイウォール | PaywallView が Step3 として表示 |
| [Maybe Later] で閉じれる | `GhostButton` → `isOnboardingComplete = true` |
| ATT ダイアログ禁止（Rule 20b） | `AppTrackingTransparency` を一切使用しない |
| RC-UI-package 禁止（Rule 20） | 自前 SwiftUI `PaywallView` のみ |

---

## 7. Accessibility

Source: [Apple — Accessibility for iOS](https://developer.apple.com/accessibility/ios/) — 「Every interactive element should be accessible to all users」

### accessibilityIdentifier 一覧（Maestro E2E で使用）

| ID | Screen | Element | 用途 |
|----|--------|---------|------|
| `onboarding_step1_next_button` | S-001 | 「次へ」ボタン | Maestro: オンボーディング進行 |
| `onboarding_step2_notification_button` | S-002 | 通知許可ボタン | Maestro: 通知フロー |
| `onboarding_step2_skip_button` | S-002 | スキップボタン | Maestro: 通知スキップ |
| `paywall_monthly_plan_card` | S-003 | 月額プランカード | Maestro: 月額購入 |
| `paywall_annual_plan_card` | S-003 | 年額プランカード | Maestro: 年額購入 |
| `paywall_cta_button` | S-003 | 「Start My Reset」 | Maestro: 購入フロー |
| `paywall_maybe_later_button` | S-003 | 「Maybe Later」 | Maestro: Paywall スキップ |
| `home_streak_badge` | S-004 | ストリークバッジ | Maestro: ストリーク確認 |
| `home_exercise_card_{id}` | S-004 | エクササイズカード | Maestro: カード選択（id: humming-01 等） |
| `home_tab_bar` | S-004 | タブバー | Maestro: タブ切り替え |
| `session_timer_ring` | S-005 | タイマーリング | Maestro: タイマー確認 |
| `session_start_button` | S-005 | スタートボタン | Maestro: セッション開始 |
| `session_pause_button` | S-005 | 一時停止ボタン | Maestro: セッション一時停止 |
| `session_back_button` | S-005 | 戻るボタン | Maestro: セッション中断 |
| `session_complete_view` | S-006 | 完了画面コンテナ | Maestro: セッション完了確認 |
| `session_complete_next_button` | S-006 | 「次へ」ボタン | Maestro: 完了後の画面遷移 |
| `settings_upgrade_button` | S-007 | Upgrade ボタン | Maestro: Paywall 遷移 |
| `settings_restore_button` | S-007 | 購入の復元 | Maestro: 復元フロー |
| `settings_notification_time_row` | S-007 | 通知時間行 | Maestro: 通知設定 |

---

## 8. Interaction Patterns

| 操作 | 対象 | 結果 |
|------|------|------|
| タップ | ExerciseCard（無料） | SessionView へ遷移 |
| タップ | ExerciseCard（有料・未登録） | PaywallView を sheet 表示 |
| タップ | [Maybe Later] | `isOnboardingComplete = true`、オンボーディング終了 |
| タップ | PrimaryButton (Paywall) | `Purchases.shared.purchase(package:)` 実行 |
| タップ | 設定 > Upgrade | PaywallView を sheet 表示 |
| タップ | 設定 > 購入の復元 | `Purchases.shared.restorePurchases()` 実行 |
| スワイプ上 | Paywall Sheet | Sheet を閉じる |
| 長押し | なし | 未定義（MVP対象外） |
| バックグラウンド移行 | SessionView タイマー中 | 残り秒数を UserDefaults に保存し、フォアグラウンド復帰時に補正 |
| スワイプ左 | OnboardingView ページ | 次ページへ（TabView pagingStyle） |

---

## 9. Localization Notes

Source: [Apple HIG — Language and Locale](https://developer.apple.com/design/human-interface-guidelines/translation-and-localization) — 「Account for text expansion of up to 40% in translations」

| 考慮点 | en-US | ja | 対策 |
|--------|-------|-----|------|
| テキスト長差異 | 基準 | en より 20% 短め（漢字圧縮） | `minimumScaleFactor(0.8)` |
| フォント | SF Pro | SF Pro（日本語は自動ヒラギノ） | `.system(size:)` で自動 |
| 日付表示 | "Mar 9, 2026" | 「2026年3月9日」 | `DateFormatter.localizedString` |
| 通貨表示 | "$4.99/mo" | 「¥800/月」（App Store 換算） | RevenueCat の `localizedPriceString` |
| エクササイズ名 | "Humming Breath" | 「ハミング呼吸」 | `Exercise.titleJa` フィールド |
| CTA コピー | "Start My Reset" | 「リセットを始める」 | `Localizable.xcstrings` |
| エラーメッセージ | "Purchase failed. Please try again." | 「購入に失敗しました。もう一度お試しください。」| `Localizable.xcstrings` |

**RTL 対応:** 不要（en-US + ja は LTR）。

**xcstrings ファイル:** `Resources/Localizable.xcstrings`（Xcode 15+ 対応の単一ファイル形式）。
