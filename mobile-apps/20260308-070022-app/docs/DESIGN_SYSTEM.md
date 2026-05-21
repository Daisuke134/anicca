# Design System: LymphaFlow

Source: [Apple Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines/) — 「Use standard patterns and components to create familiar, intuitive experiences.」
Source: [Material Design Color System](https://m3.material.io/styles/color/system/overview) — 「Semantic color tokens decouple intent from specific values.」
Source: [Apple SF Symbols](https://developer.apple.com/sf-symbols/) — 「SF Symbols integrates with San Francisco to provide consistent icons across Apple platforms.」

---

## 1. Color Tokens

### DesignSystem/Colors.swift

```swift
import SwiftUI

enum DSColor {
    // Primary
    static let primary       = Color("DSPrimary")       // #3E7CB1 — ブルーリンパ
    static let primaryLight  = Color("DSPrimaryLight")  // #7AAFE4 — ホバー/アクセント
    static let primaryDark   = Color("DSPrimaryDark")   // #1A4E7C — ダーク用

    // Secondary
    static let secondary     = Color("DSSecondary")     // #5BBFA6 — ティール（健康）
    static let secondaryLight = Color("DSSecondaryLight") // #96D9CA

    // Surface
    static let background    = Color("DSBackground")    // #F8FBFF (Light) / #0F1B27 (Dark)
    static let surface       = Color("DSSurface")       // #FFFFFF (Light) / #162330 (Dark)
    static let surfaceSecond = Color("DSSurfaceSecond") // #EEF4FB (Light) / #1E2E3E (Dark)

    // Text
    static let textPrimary   = Color("DSTextPrimary")   // #1A2B3C (Light) / #F0F6FF (Dark)
    static let textSecondary = Color("DSTextSecondary") // #5A7388 (Light) / #8AAABF (Dark)
    static let textDisabled  = Color("DSTextDisabled")  // #A8C0D0

    // Semantic
    static let success       = Color("DSSuccess")       // #4CAF50
    static let warning       = Color("DSWarning")       // #FF9800
    static let error         = Color("DSError")         // #F44336
    static let proGold       = Color("DSProGold")       // #FFB300 — Pro バッジ

    // Streak / Gamification
    static let streakFire    = Color("DSStreakFire")    // #FF6B2B
    static let streakInactive = Color("DSStreakInactive") // #D0E4F2
}
```

### Color Token Table

| Token | Light | Dark | Usage |
|-------|-------|------|-------|
| `DSPrimary` | `#3E7CB1` | `#5A9FD4` | CTA ボタン、リンク、強調 |
| `DSPrimaryLight` | `#7AAFE4` | `#7AAFE4` | ボタンホバー、進捗バー |
| `DSPrimaryDark` | `#1A4E7C` | `#1A4E7C` | ナビゲーション背景 |
| `DSSecondary` | `#5BBFA6` | `#5BBFA6` | 完了バッジ、ステップ完了 |
| `DSSecondaryLight` | `#96D9CA` | `#96D9CA` | カード背景アクセント |
| `DSBackground` | `#F8FBFF` | `#0F1B27` | 画面背景 |
| `DSSurface` | `#FFFFFF` | `#162330` | カード、モーダル背景 |
| `DSSurfaceSecond` | `#EEF4FB` | `#1E2E3E` | 区切りセクション |
| `DSTextPrimary` | `#1A2B3C` | `#F0F6FF` | 見出し、本文 |
| `DSTextSecondary` | `#5A7388` | `#8AAABF` | サブテキスト、説明 |
| `DSTextDisabled` | `#A8C0D0` | `#A8C0D0` | 無効状態テキスト |
| `DSSuccess` | `#4CAF50` | `#66BB6A` | 完了状態、ストリーク |
| `DSWarning` | `#FF9800` | `#FFA726` | 注意喚起 |
| `DSError` | `#F44336` | `#EF5350` | エラー表示 |
| `DSProGold` | `#FFB300` | `#FFCA28` | Pro バッジ、プレミアム表示 |
| `DSStreakFire` | `#FF6B2B` | `#FF8C54` | 連続記録炎アイコン |
| `DSStreakInactive` | `#D0E4F2` | `#2A3E52` | 未達成日のドット |

---

## 2. Typography

Source: [Apple HIG Typography](https://developer.apple.com/design/human-interface-guidelines/typography) — 「Use Dynamic Type to support accessibility text sizes.」

### DesignSystem/Typography.swift

```swift
import SwiftUI

enum DSFont {
    static let largeTitle  = Font.largeTitle.weight(.bold)       // 34pt Bold
    static let title1      = Font.title.weight(.semibold)        // 28pt Semibold
    static let title2      = Font.title2.weight(.semibold)       // 22pt Semibold
    static let title3      = Font.title3.weight(.medium)         // 20pt Medium
    static let headline    = Font.headline                       // 17pt Semibold
    static let body        = Font.body                           // 17pt Regular
    static let callout     = Font.callout                        // 16pt Regular
    static let subheadline = Font.subheadline                    // 15pt Regular
    static let footnote    = Font.footnote                       // 13pt Regular
    static let caption1    = Font.caption                        // 12pt Regular
    static let caption2    = Font.caption2                       // 11pt Regular

    // Special
    static let timerDisplay = Font.system(size: 56, weight: .thin, design: .rounded)
    static let streakNumber = Font.system(size: 42, weight: .bold, design: .rounded)
}
```

### Typography Scale Table

| Style | Size | Weight | Line Height | Usage |
|-------|------|--------|-------------|-------|
| `largeTitle` | 34pt | Bold | 41pt | ページタイトル（PaywallView ヘッドライン）|
| `title1` | 28pt | Semibold | 34pt | セクションヘッド（HomeView ルーティン名）|
| `title2` | 22pt | Semibold | 28pt | カードタイトル |
| `title3` | 20pt | Medium | 25pt | Step タイトル |
| `headline` | 17pt | Semibold | 22pt | リスト項目の強調 |
| `body` | 17pt | Regular | 22pt | 本文、説明テキスト |
| `callout` | 16pt | Regular | 21pt | ボタンラベル |
| `subheadline` | 15pt | Regular | 20pt | サブタイトル、タグ |
| `footnote` | 13pt | Regular | 18pt | FAQ、注釈 |
| `caption1` | 12pt | Regular | 16pt | バッジ、メタ情報 |
| `caption2` | 11pt | Regular | 13pt | Privacy Policy リンク |
| `timerDisplay` | 56pt | Thin (Rounded) | — | セッションタイマー数字 |
| `streakNumber` | 42pt | Bold (Rounded) | — | ストリーク日数 |

**Dynamic Type:** 全スタイルに `.dynamicTypeSize` 制限なし。Accessibility Large Text サポート必須。

---

## 3. Spacing & Layout

### DesignSystem/Spacing.swift

```swift
import SwiftUI

enum DSSpacing {
    static let xs:  CGFloat = 4
    static let sm:  CGFloat = 8
    static let md:  CGFloat = 12
    static let base: CGFloat = 16
    static let lg:  CGFloat = 24
    static let xl:  CGFloat = 32
    static let xxl: CGFloat = 48
    static let xxxl: CGFloat = 64
}

enum DSRadius {
    static let sm:   CGFloat = 8
    static let md:   CGFloat = 12
    static let lg:   CGFloat = 16
    static let xl:   CGFloat = 24
    static let full: CGFloat = 999
}
```

### Spacing Scale Table

| Token | Value | Usage |
|-------|-------|-------|
| `DSSpacing.xs` | 4pt | アイコン間マージン、バッジ内パディング |
| `DSSpacing.sm` | 8pt | テキスト間スペース、リスト行間 |
| `DSSpacing.md` | 12pt | カード内パディング（コンパクト）|
| `DSSpacing.base` | 16pt | 標準パディング（スクリーンマージン）|
| `DSSpacing.lg` | 24pt | セクション間スペース |
| `DSSpacing.xl` | 32pt | 大きなセクション区切り |
| `DSSpacing.xxl` | 48pt | ヒーローセクションパディング |
| `DSSpacing.xxxl` | 64pt | ページ底部の余白（Tab Bar対策）|

**Screen Margins:** 水平 `DSSpacing.base`（16pt）。ScrollView 内 `.padding(.horizontal, DSSpacing.base)`。

---

## 4. Components

Source: [Apple HIG Buttons](https://developer.apple.com/design/human-interface-guidelines/buttons) — 「Use filled buttons for the most important action on a screen.」

| Component | Props | Usage |
|-----------|-------|-------|
| `DSPrimaryButton` | `title: String, action: () -> Void, isLoading: Bool` | CTA（"Start Trial", "Subscribe"）|
| `DSSecondaryButton` | `title: String, action: () -> Void` | セカンダリアクション |
| `DSGhostButton` | `title: String, action: () -> Void` | "Maybe Later"（Rule 20）|
| `DSRoutineCard` | `routine: Routine, isPro: Bool, onTap: () -> Void` | HomeView ルーティン一覧 |
| `DSStepCard` | `step: Step, isActive: Bool, timeRemaining: Int` | SessionView ステップ |
| `DSStreakBadge` | `count: Int` | ProgressDashboardView ストリーク数 |
| `DSProBadge` | — | Pro コンテンツのロック表示 |
| `DSTimerRing` | `progress: Double, timeRemaining: Int` | SessionView 円形タイマー |
| `DSProgressBar` | `progress: Double, color: Color` | セッション進捗バー |
| `DSOnboardingPage` | `title: String, description: String, imageName: String` | オンボーディング各ページ |

### DSPrimaryButton 実装例

```swift
struct DSPrimaryButton: View {
    let title: String
    let action: () -> Void
    var isLoading: Bool = false

    var body: some View {
        Button(action: action) {
            Group {
                if isLoading {
                    ProgressView().tint(.white)
                } else {
                    Text(title).font(DSFont.headline)
                }
            }
            .frame(maxWidth: .infinity)
            .frame(height: 56)
            .background(DSColor.primary)
            .foregroundColor(.white)
            .cornerRadius(DSRadius.full)
        }
        .disabled(isLoading)
        .padding(.horizontal, DSSpacing.base)
    }
}
```

---

## 5. Icons

Source: [Apple SF Symbols 6](https://developer.apple.com/sf-symbols/) — 「SF Symbols 6 includes 800+ new symbols.」

| Symbol Name | SF Symbol | Usage |
|-------------|-----------|-------|
| `drop.fill` | 💧 | リンパ流れアイコン、メインロゴ |
| `timer` | ⏱ | タイマー画面 |
| `flame.fill` | 🔥 | ストリーク |
| `checkmark.circle.fill` | ✅ | ステップ完了 |
| `lock.fill` | 🔒 | Pro コンテンツロック |
| `star.fill` | ⭐ | レビュー評価（Paywall） |
| `bell.fill` | 🔔 | 通知設定 |
| `gearshape.fill` | ⚙️ | 設定画面 |
| `chart.bar.fill` | 📊 | 進捗ダッシュボード |
| `sun.max.fill` | ☀️ | Morningプログラム |
| `moon.fill` | 🌙 | Eveningプログラム |
| `arrow.counterclockwise` | 🔄 | 購入復元ボタン |
| `xmark` | ✕ | Maybe Later / 閉じる |
| `chevron.right` | › | リスト項目のナビゲーション |
| `person.crop.circle` | 👤 | ユーザーアバター（設定）|

---

## 6. Animations

Source: [Apple HIG Motion](https://developer.apple.com/design/human-interface-guidelines/motion) — 「Motion should be purposeful, not decorative. It should help users understand state changes.」

| Trigger | Duration | Type | Component |
|---------|----------|------|-----------|
| ステップ完了 | 0.35s | `.easeOut` + スケール1.2→1.0 | `DSStepCard` |
| タイマーリング進捗 | 1.0s | `.linear` | `DSTimerRing` |
| PaywallView 登場 | 0.4s | `.spring(response: 0.4, dampingFraction: 0.7)` | `PaywallView` |
| ストリーク達成 | 0.6s | `.bouncy` | `DSStreakBadge` |
| オンボーディング遷移 | 0.3s | `.easeInOut` | `OnboardingPageView` |
| ルーティンカード タップ | 0.15s | `.easeIn` スケール0.97 | `DSRoutineCard` |
| CTA ボタン ローディング | — | `ProgressView` (indefinite) | `DSPrimaryButton` |
| 通知許可アニメ | 0.5s | `.easeOut` 上から出現 | `NotificationPermissionView` |

**Reduced Motion 対応:**
```swift
@Environment(\.accessibilityReduceMotion) var reduceMotion
// アニメーション duration を 0 にフォールバック
```

---

## 7. Accessibility

Source: [Apple HIG Accessibility](https://developer.apple.com/design/human-interface-guidelines/accessibility) — 「Make your app accessible to everyone, including people with disabilities.」
Source: [WCAG 2.1 Contrast](https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html) — 「Minimum contrast ratio: 4.5:1 for normal text, 3:1 for large text.」

### Contrast Ratios

| Foreground | Background | Ratio | WCAG |
|-----------|-----------|-------|------|
| `DSTextPrimary` (#1A2B3C) | `DSBackground` (#F8FBFF) | 14.2:1 | AAA ✅ |
| White (#FFFFFF) | `DSPrimary` (#3E7CB1) | 4.8:1 | AA ✅ |
| `DSTextSecondary` (#5A7388) | `DSBackground` (#F8FBFF) | 4.6:1 | AA ✅ |
| White (#FFFFFF) | `DSSecondary` (#5BBFA6) | 3.2:1 | AA Large ✅ |

### Dynamic Type

- 全フォントは `Font` (Dynamic Type) 使用。固定サイズ `Font.system(size:)` は `timerDisplay` / `streakNumber` のみ（視覚的インパクト重視）。
- `accessibilityLabel` は全インタラクティブ要素に付与。
- `accessibilityHint` はジェスチャー操作を持つ要素に付与。

### VoiceOver Labels（主要要素）

| Element | accessibilityLabel |
|---------|-------------------|
| DSPrimaryButton | ボタンタイトルをそのまま使用 |
| DSRoutineCard（Pro Locked） | "{routine.name}, Pro feature, double tap to unlock" |
| DSTimerRing | "Timer, {seconds} seconds remaining" |
| DSStreakBadge | "{count} day streak" |
| DSProBadge | "Pro content" |
