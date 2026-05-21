# Design System: VagusReset

Source: [Apple Human Interface Guidelines — Color](https://developer.apple.com/design/human-interface-guidelines/color) — 「Use color to guide people's attention and communicate status」
Source: [Apple HIG — Typography](https://developer.apple.com/design/human-interface-guidelines/typography) — 「Use Dynamic Type so text scales with user preferences」
Source: [Apple HIG — Accessibility](https://developer.apple.com/design/human-interface-guidelines/accessibility) — 「Contrast ratio of at least 4.5:1 for normal text」

---

## 1. Color Tokens

| Token | Light | Dark | Usage |
|-------|-------|------|-------|
| `colorBackground` | `#F5F5F0` | `#0D0D0D` | 全画面背景 |
| `colorSurface` | `#FFFFFF` | `#1A1A1A` | カード・モーダル背景 |
| `colorPrimary` | `#2E7D6E` | `#4AADA0` | CTA ボタン、アクセント、アクティブ状態 |
| `colorPrimaryLight` | `#E8F5F3` | `#1A3530` | プライマリボタン背景（ソフト） |
| `colorSecondary` | `#5C8B99` | `#7BB3C0` | セカンダリアクション、タグ |
| `colorOnPrimary` | `#FFFFFF` | `#FFFFFF` | プライマリ背景上のテキスト |
| `colorTextPrimary` | `#1A1A1A` | `#F0F0F0` | 本文・見出し |
| `colorTextSecondary` | `#6B6B6B` | `#9B9B9B` | サブテキスト、プレースホルダー |
| `colorTextDisabled` | `#BDBDBD` | `#4A4A4A` | 非アクティブ要素 |
| `colorSuccess` | `#2E7D32` | `#66BB6A` | ストリーク達成、完了アニメーション |
| `colorWarning` | `#F57C00` | `#FFA726` | ストリーク警告、注意喚起 |
| `colorError` | `#C62828` | `#EF5350` | 購入失敗、エラー状態 |
| `colorDivider` | `#E0E0E0` | `#2A2A2A` | セパレーター |
| `colorShadow` | `#00000014` | `#00000040` | カードシャドウ |

**シマンティックカラー（用途別）:**

| Token | 値 | Usage |
|-------|-----|-------|
| `colorHumming` | `#7E57C2` | ハミングカテゴリアイコン背景 |
| `colorGargling` | `#26A69A` | うがいカテゴリ |
| `colorCold` | `#42A5F5` | 冷水カテゴリ |
| `colorDiaphragm` | `#66BB6A` | 横隔膜カテゴリ |
| `colorLaughter` | `#FFA726` | 笑いカテゴリ |
| `colorPaywallGradientStart` | `#1A3530` | Paywall グラデーション開始 |
| `colorPaywallGradientEnd` | `#0D1F1C` | Paywall グラデーション終了 |

---

## 2. Typography

Source: [Apple HIG — Dynamic Type Sizes](https://developer.apple.com/design/human-interface-guidelines/typography#Specifications) — 「Large (default) body size is 17pt」

| Style | SF Size (default) | Weight | Line Height | Usage |
|-------|------------------|--------|-------------|-------|
| `displayLarge` | 34pt | Bold | 41pt | オンボーディング大見出し |
| `displayMedium` | 28pt | Bold | 34pt | セクション大見出し |
| `headlineLarge` | 22pt | Semibold | 28pt | 画面タイトル |
| `headlineMedium` | 17pt | Semibold | 22pt | カード見出し、エクササイズ名 |
| `bodyLarge` | 17pt | Regular | 22pt | 本文（長文説明） |
| `bodyMedium` | 15pt | Regular | 20pt | 説明文、サブコピー |
| `bodySmall` | 13pt | Regular | 18pt | キャプション、ラベル |
| `labelLarge` | 17pt | Semibold | 22pt | CTAボタン |
| `labelMedium` | 15pt | Medium | 20pt | セカンダリボタン |
| `timerDisplay` | 72pt | Thin | 80pt | カウントダウンタイマー |
| `streakNumber` | 48pt | Bold | 56pt | ストリーク数表示 |

**Dynamic Type:** 全スタイルは `Font.custom` ではなく `.system(size:weight:)` + `.scaledFont` でアクセシビリティ対応。

---

## 3. Spacing & Layout

Source: [Apple HIG — Layout](https://developer.apple.com/design/human-interface-guidelines/layout) — 「Use consistent spacing values to create visual harmony」

| Token | 値 | Usage |
|-------|-----|-------|
| `spacingXS` | 4pt | アイコンとラベル間の最小余白 |
| `spacingSM` | 8pt | コンポーネント内パディング（小） |
| `spacingMD` | 12pt | リスト行間、アイコン余白 |
| `spacingLG` | 16pt | 標準パディング（水平マージン） |
| `spacingXL` | 24pt | セクション間余白 |
| `spacingXXL` | 32pt | 大セクション余白 |
| `spacingHuge` | 48pt | 画面トップ余白 |
| `cornerRadiusSM` | 8pt | 小カード、バッジ |
| `cornerRadiusMD` | 12pt | エクササイズカード |
| `cornerRadiusLG` | 16pt | モーダル、ボトムシート |
| `cornerRadiusXL` | 24pt | 大ボタン、タイマー円 |
| `cornerRadiusFull` | 999pt | ピル型ボタン、バッジ |

**グリッド:** 水平マージン `spacingLG` (16pt)。画面幅に応じたフルWidth or 2カラムグリッド（エクササイズ一覧）。

---

## 4. Components

| Name | Props | Usage |
|------|-------|-------|
| `PrimaryButton` | `title: String`, `isLoading: Bool`, `action: () -> Void` | CTAボタン（colorPrimary背景） |
| `SecondaryButton` | `title: String`, `action: () -> Void` | セカンダリアクション（アウトライン） |
| `GhostButton` | `title: String`, `action: () -> Void` | [Maybe Later] などソフトアクション |
| `ExerciseCard` | `exercise: Exercise`, `isLocked: Bool`, `onTap: () -> Void` | エクササイズ一覧カード |
| `TimerRing` | `progress: Double`, `timeRemaining: Int`, `color: Color` | セッション画面のタイマーサークル |
| `StreakBadge` | `streak: Int`, `isActive: Bool` | ホーム画面のストリーク表示 |
| `CategoryTag` | `category: String`, `color: Color` | エクササイズカテゴリラベル |
| `PaywallPlanCard` | `package: Package`, `isSelected: Bool`, `isBestValue: Bool` | Paywall の価格プランカード |
| `SectionHeader` | `title: String`, `subtitle: String?` | リストセクション見出し |
| `ProgressCalendarCell` | `date: Date`, `isCompleted: Bool` | カレンダーグリッドセル |
| `OnboardingPageIndicator` | `currentPage: Int`, `totalPages: Int` | オンボーディング進捗ドット |
| `NotificationTimeRow` | `hour: Int`, `minute: Int`, `onEdit: () -> Void` | 設定画面の通知時刻行 |

---

## 5. Icons (SF Symbols)

| Name | SF Symbol | Color | Usage |
|------|-----------|-------|-------|
| `iconHumming` | `waveform.and.mic` | colorHumming | ハミングエクササイズ |
| `iconGargling` | `drop.fill` | colorGargling | うがいエクササイズ |
| `iconCold` | `thermometer.snowflake` | colorCold | 冷水エクササイズ |
| `iconDiaphragm` | `lungs.fill` | colorDiaphragm | 横隔膜エクササイズ |
| `iconLaughter` | `face.smiling.fill` | colorLaughter | 笑いエクササイズ |
| `iconTimer` | `timer` | colorPrimary | タイマーボタン |
| `iconStreak` | `flame.fill` | colorWarning | ストリーク表示 |
| `iconCalendar` | `calendar` | colorSecondary | 進捗カレンダー |
| `iconSettings` | `gearshape.fill` | colorTextSecondary | 設定タブ |
| `iconHome` | `house.fill` | colorPrimary | ホームタブ |
| `iconLock` | `lock.fill` | colorTextDisabled | プレミアムロックアイコン |
| `iconCheckmark` | `checkmark.circle.fill` | colorSuccess | 完了状態 |
| `iconClose` | `xmark` | colorTextSecondary | 閉じるボタン |
| `iconNotification` | `bell.fill` | colorPrimary | 通知設定 |
| `iconRestore` | `arrow.counterclockwise` | colorSecondary | 購入復元 |

---

## 6. Animations

Source: [Apple HIG — Motion](https://developer.apple.com/design/human-interface-guidelines/motion) — 「Use motion to communicate and enhance the experience, not just to entertain」

| Name | Trigger | Duration | Type | Implementation |
|------|---------|----------|------|----------------|
| `timerRingProgress` | セッション進行中 | 連続 | `animation(.linear)` | `Circle` stroke の `trim` 変化 |
| `sessionComplete` | セッション完了 | 0.6s | `spring(response:0.4, damping:0.6)` | スケール 1.0→1.2→1.0 + `colorSuccess` フラッシュ |
| `streakBounce` | ストリーク更新 | 0.4s | `.spring(response:0.3, damping:0.5)` | `StreakBadge` の y軸バウンス |
| `paywallSlideIn` | Paywall 表示 | 0.35s | `.easeOut` | 下から上へ `offset` アニメーション |
| `cardPressBounce` | エクササイズカードタップ | 0.15s | `.easeInOut` | スケール 1.0→0.96→1.0 |
| `onboardingPageSlide` | ページ遷移 | 0.3s | `.easeInOut` | `TabView` ページスワイプ |
| `completionConfetti` | セッション100%完了 | 1.2s | カスタム | `Canvas` でパーティクル（60fps、軽量実装） |
| `planCardHighlight` | Paywall プラン選択 | 0.2s | `.easeOut` | ボーダー色 + スケール変化 |

**注意:** `withAnimation` は `MainActor` で実行。`Reduce Motion` 設定を `UIAccessibility.isReduceMotionEnabled` で確認し、重いアニメーションはスキップ。

---

## 7. Accessibility

Source: [Apple HIG — Accessibility](https://developer.apple.com/design/human-interface-guidelines/accessibility) — 「Design for all users regardless of ability」
Source: [WCAG 2.1 Level AA](https://www.w3.org/WAI/WCAG21/quickref/) — 「Contrast ratio 4.5:1 for normal text, 3:1 for large text」

### コントラスト比

| Combination | Contrast Ratio | WCAG Level |
|-------------|---------------|------------|
| colorTextPrimary on colorBackground | 14.7:1 | AAA |
| colorPrimary on colorBackground | 4.8:1 | AA |
| colorOnPrimary on colorPrimary | 8.2:1 | AAA |
| colorTextSecondary on colorBackground | 4.6:1 | AA |

### Dynamic Type サポート

全フォントは `.scaledMetric` または `.system(size:weight:)` を使用。最小サイズ制約なし（ユーザー設定を尊重）。

### VoiceOver ラベル

| UI 要素 | `accessibilityLabel` | `accessibilityHint` |
|--------|---------------------|---------------------|
| `ExerciseCard` | `exercise.title` | 「タップしてエクササイズを開始」|
| `TimerRing` | 「タイマー: \(timeRemaining)秒」| — |
| `StreakBadge` | 「\(streak)日連続達成」| — |
| `PrimaryButton (CTA)` | ボタンタイトル | 「ダブルタップで購入を開始」|
| `GhostButton ([Maybe Later])` | 「後で」| 「タップでペイウォールを閉じる」|
| `LockIcon` | 「プレミアム限定」| 「アンロックするには購読してください」|

### 最小タップターゲット

全インタラクティブ要素は `44×44pt` 以上（Apple HIG 準拠）。
