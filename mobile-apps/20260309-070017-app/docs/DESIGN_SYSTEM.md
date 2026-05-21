# Design System: Zone2Daily

Source: [Apple HIG — Color](https://developer.apple.com/design/human-interface-guidelines/color) — 「Use color to convey information, evoke emotions, and bring visual richness to your app's interface.」
Source: [Apple HIG — Typography](https://developer.apple.com/design/human-interface-guidelines/typography) — 「Use SF Pro for legibility and Dynamic Type for accessibility.」
Source: [Apple HIG — Spacing](https://developer.apple.com/design/human-interface-guidelines/layout) — 「Use a consistent spacing system based on a 4pt grid.」

---

## 1. Color Tokens

Zone2Daily の配色は「科学的 × アクティブ」のコンセプトで設計。Zone 2 = 脂肪燃焼ゾーンのイメージからオレンジ/アンバー系をプライマリとし、心拍数モニタリングの視認性を最優先。

### Brand Colors

| Token | Light | Dark | Usage |
|-------|-------|------|-------|
| `brand.primary` | `#F97316` (Orange-500) | `#FB923C` (Orange-400) | CTA ボタン、アクティブ状態、ハイライト |
| `brand.primaryDark` | `#EA580C` (Orange-600) | `#F97316` (Orange-500) | ボタン押下状態、アクセント |
| `brand.secondary` | `#0EA5E9` (Sky-500) | `#38BDF8` (Sky-400) | セカンダリアクション、リンク |
| `brand.success` | `#22C55E` (Green-500) | `#4ADE80` (Green-400) | 目標達成、Zone 2 内 HR |
| `brand.warning` | `#EAB308` (Yellow-500) | `#FACC15` (Yellow-400) | Zone 2 境界、注意 |
| `brand.danger` | `#EF4444` (Red-500) | `#F87171` (Red-400) | Zone 2 超過、エラー |

### Background & Surface

| Token | Light | Dark | Usage |
|-------|-------|------|-------|
| `bg.primary` | `#FFFFFF` | `#0A0A0A` | メイン背景 |
| `bg.secondary` | `#F5F5F5` | `#171717` | カード背景、セクション背景 |
| `bg.tertiary` | `#E5E5E5` | `#262626` | インプット背景、区切り |
| `surface.card` | `#FFFFFF` | `#1C1C1C` | ワークアウトカード、統計カード |
| `surface.elevated` | `#FAFAFA` | `#222222` | モーダル、シート |

### Text Colors

| Token | Light | Dark | Usage |
|-------|-------|------|-------|
| `text.primary` | `#0A0A0A` | `#FAFAFA` | 見出し、ボディ |
| `text.secondary` | `#525252` | `#A3A3A3` | サブラベル、キャプション |
| `text.tertiary` | `#A3A3A3` | `#525252` | プレースホルダー |
| `text.onPrimary` | `#FFFFFF` | `#FFFFFF` | ブランドカラー背景上のテキスト |
| `text.link` | `#0EA5E9` | `#38BDF8` | リンク、タップ可能テキスト |

### HR Zone Colors（ワークアウト画面専用）

| Zone | Token | Color | Hex | Description |
|------|-------|-------|-----|-------------|
| Zone 1 | `zone.1` | Gray | `#A3A3A3` | 軽強度（ウォームアップ） |
| Zone 2 | `zone.2` | Green | `#22C55E` | 脂肪燃焼（ターゲット） |
| Zone 3 | `zone.3` | Yellow | `#EAB308` | 有酸素閾値（注意） |
| Zone 4 | `zone.4` | Orange | `#F97316` | 乳酸閾値（警告） |
| Zone 5 | `zone.5` | Red | `#EF4444` | 最大強度（超過） |

Source: [Phil Maffetone — Training Zones](https://philmaffetone.com/zone-training/) — 「Zone 2 is where fat oxidation is maximized.」

---

## 2. Typography

SF Pro Rounded を見出し系に使用してフレンドリーな印象を与え、SF Pro をボディに使用して可読性を確保。

| Style | Size | Weight | Line Height | Usage |
|-------|------|--------|-------------|-------|
| `title.large` | 34pt | Bold | 41pt | オンボーディング見出し |
| `title.medium` | 28pt | Bold | 34pt | 画面タイトル（Dashboard, Workout） |
| `title.small` | 22pt | SemiBold | 28pt | セクション見出し |
| `headline` | 17pt | SemiBold | 22pt | カードヘッダー、ラベル |
| `body` | 17pt | Regular | 22pt | 説明文、ボディテキスト |
| `callout` | 16pt | Regular | 21pt | 補足説明 |
| `subheadline` | 15pt | Regular | 20pt | メタデータ、日付 |
| `footnote` | 13pt | Regular | 18pt | キャプション、法的テキスト |
| `caption` | 12pt | Regular | 16pt | タグ、バッジラベル |
| `metric.large` | 64pt | Bold | 72pt | HR 数値の大型表示 |
| `metric.medium` | 48pt | Bold | 56pt | Zone 2 分数表示 |
| `metric.small` | 34pt | SemiBold | 41pt | 週間進捗パーセンテージ |

**Dynamic Type:** 全フォントで Dynamic Type 対応必須（`.scaledFont()` 使用）。

Source: [Apple HIG — Dynamic Type](https://developer.apple.com/design/human-interface-guidelines/typography#Dynamic-type-sizes) — 「Support Dynamic Type sizes to improve legibility for users with different visual needs.」

---

## 3. Spacing & Layout

4pt グリッドに基づく統一スペーシングシステム。

| Token | Value | Usage |
|-------|-------|-------|
| `spacing.xxs` | 4pt | アイコンとラベルの間隔 |
| `spacing.xs` | 8pt | コンパクトなリスト行間 |
| `spacing.sm` | 12pt | カード内パディング（コンパクト） |
| `spacing.md` | 16pt | 標準パディング、カード間隔 |
| `spacing.lg` | 24pt | セクション間隔 |
| `spacing.xl` | 32pt | 大セクション間隔、ページパディング |
| `spacing.xxl` | 48pt | 画面トップマージン |
| `spacing.xxxl` | 64pt | 大型コンポーネント間隔 |

### Layout Constants

| 定数 | 値 | 用途 |
|------|-----|------|
| `layout.screenPadding` | 20pt | 水平パディング（全画面） |
| `layout.cardRadius` | 16pt | カード角丸 |
| `layout.buttonRadius` | 14pt | ボタン角丸 |
| `layout.inputRadius` | 12pt | 入力フィールド角丸 |
| `layout.tabBarHeight` | 83pt | Tab Bar 高さ（Home Indicator 込） |
| `layout.buttonHeight` | 56pt | CTA ボタン高さ |
| `layout.cardPadding` | 20pt | カード内パディング |

---

## 4. Components

再利用コンポーネントテーブル。全コンポーネントは `DesignSystem/` 配下に実装。

| Name | File | Props | Usage |
|------|------|-------|-------|
| `PrimaryButton` | `Buttons.swift` | `title: String`, `action: () -> Void`, `isLoading: Bool` | CTA ボタン（オンボーディング, Paywall） |
| `SecondaryButton` | `Buttons.swift` | `title: String`, `action: () -> Void` | セカンダリアクション（Maybe Later） |
| `MetricCard` | `Cards.swift` | `title: String`, `value: String`, `unit: String`, `color: Color` | HR 表示、週間統計カード |
| `ProgressRing` | `Progress.swift` | `progress: Double`, `goal: Double`, `color: Color` | 週間目標進捗リング |
| `WorkoutHistoryRow` | `Lists.swift` | `session: WorkoutSession` | ワークアウト履歴リスト行 |
| `HRZoneIndicator` | `HRZone.swift` | `currentHR: Int`, `targetHR: Int` | HR ゾーン視覚化バー |
| `OnboardingStepView` | `Onboarding.swift` | `step: Int`, `total: Int` | オンボーディング進捗 dot |
| `AgeSlider` | `Inputs.swift` | `age: Binding<Int>` | 年齢入力スライダー（10-80） |
| `StreakBadge` | `Badges.swift` | `streak: Int` | ストリーク表示バッジ |
| `PaywallBenefitRow` | `Paywall.swift` | `icon: String`, `title: String`, `description: String` | Paywall 特典リスト行 |

---

## 5. Icons

SF Symbols を使用。カスタムアイコン不要。

| Name | SF Symbol | Usage |
|------|-----------|-------|
| `tab.dashboard` | `chart.bar.fill` | Dashboard タブ |
| `tab.workout` | `stopwatch.fill` | Workout タブ |
| `tab.settings` | `gearshape.fill` | Settings タブ |
| `icon.heart` | `heart.fill` | HR 表示 |
| `icon.zone2` | `flame.fill` | Zone 2 達成 |
| `icon.timer` | `timer` | タイマー |
| `icon.trophy` | `trophy.fill` | ストリーク |
| `icon.checkmark` | `checkmark.circle.fill` | 完了状態 |
| `icon.lock` | `lock.fill` | 有料機能ロック |
| `icon.notification` | `bell.fill` | 通知設定 |
| `icon.calendar` | `calendar` | 週間ダッシュボード |
| `icon.chevron` | `chevron.right` | ナビゲーション |
| `icon.star` | `star.fill` | 評価（Paywall 社会的証明） |

Source: [Apple SF Symbols 6](https://developer.apple.com/sf-symbols/) — 「SF Symbols provide over 6,000 configurable symbols that integrate seamlessly with San Francisco.」

---

## 6. Animations

| Animation | Trigger | Duration | Type | Usage |
|-----------|---------|----------|------|-------|
| `progressRingFill` | Dashboard 表示時 | 0.8s | `easeOut` | 進捗リングのフィルアニメーション |
| `cardSlideIn` | 画面遷移時 | 0.3s | `spring(damping: 0.8)` | カードスライドイン |
| `heartbeat` | Zone 2 内 HR 時 | 0.6s repeat | `easeInOut` | HR 数値のパルスアニメーション |
| `buttonTap` | CTA タップ時 | 0.1s | `easeIn` | ボタンスケールダウン (0.97) |
| `streakBounce` | ストリーク更新時 | 0.4s | `spring(response: 0.3)` | バッジバウンス |
| `onboardingTransition` | ステップ遷移 | 0.35s | `easeInOut` | 右→左スライド |
| `paywallReveal` | Paywall 表示時 | 0.5s | `spring(damping: 0.85)` | 下からスライドアップ |

Source: [Apple HIG — Motion](https://developer.apple.com/design/human-interface-guidelines/motion) — 「Use animation purposefully; use it to communicate, not just to decorate.」

---

## 7. Accessibility

| 要件 | 実装方法 | 基準 |
|------|---------|------|
| カラーコントラスト比 | `brand.primary` (#F97316) on `bg.primary` (#FFF) = 3.0:1 (Large text WCAG AA) | WCAG 2.1 AA |
| Dynamic Type | `.scaledFont()` 全テキストに適用。最小テキストサイズ 11pt | Apple HIG |
| VoiceOver | 全インタラクティブ要素に `accessibilityLabel` 付与 | Apple Accessibility |
| 最小タップ領域 | 44×44pt（Apple HIG 準拠） | Apple HIG |
| ダークモード | 全 Color Token に Dark variant 設定 | Apple HIG |
| 点滅回避 | アニメーション周期 > 3Hz を避ける | WCAG 2.3.3 |

Source: [WCAG 2.1 — Contrast Minimum](https://www.w3.org/TR/WCAG21/#contrast-minimum) — 「Color contrast ratio must be at least 3:1 for large text and 4.5:1 for normal text.」
Source: [Apple Accessibility — VoiceOver](https://developer.apple.com/accessibility/) — 「All interactive elements must have meaningful accessibility labels.」
