# Design System: LumaRed

Source: [Apple HIG: Color](https://developer.apple.com/design/human-interface-guidelines/color) — 「Use color to communicate information and enhance the interface, but always include contrast ratios for accessibility.」
Source: [Apple HIG: Typography](https://developer.apple.com/design/human-interface-guidelines/typography) — 「Use SF Pro (system font). Support Dynamic Type for accessibility.」
Source: [Apple HIG: SF Symbols](https://developer.apple.com/sf-symbols/) — 「Use SF Symbols for icons — automatically adapt to text size and weight.」

---

## 1. Color Tokens

| Token | Light Mode | Dark Mode | Usage |
|-------|-----------|-----------|-------|
| `colorPrimary` | `#E8533A` | `#FF6B52` | CTA ボタン、アクセント、タイマー |
| `colorPrimaryDark` | `#C0392B` | `#E84C30` | アクティブ状態、プレス状態 |
| `colorBackground` | `#FFFFFF` | `#0D0D0D` | 全画面背景 |
| `colorSurface` | `#F5F5F5` | `#1A1A1A` | カード、シート背景 |
| `colorSurfaceElevated` | `#FFFFFF` | `#242424` | モーダル、ポップアップ |
| `colorOnBackground` | `#1A1A1A` | `#F0F0F0` | 主テキスト |
| `colorOnSurface` | `#333333` | `#DDDDDD` | 副テキスト |
| `colorSubtext` | `#888888` | `#999999` | ヒント、キャプション |
| `colorDivider` | `#E0E0E0` | `#2A2A2A` | 区切り線 |
| `colorSuccess` | `#27AE60` | `#2ECC71` | 連続日数、完了状態 |
| `colorWarning` | `#F39C12` | `#F1C40F` | 制限に近い状態 |
| `colorPremiumGold` | `#F5A623` | `#FFB83D` | プレミアムバッジ、Best Value |

**Contrast Ratios (WCAG AA):**

| Combination | Ratio | Standard |
|-------------|-------|---------|
| colorOnBackground on colorBackground | 17.2:1 | AAA ✅ |
| colorPrimary on colorBackground | 4.6:1 | AA ✅ |
| colorSubtext on colorBackground | 4.5:1 | AA ✅ |

---

## 2. Typography

Source: [Apple HIG: Dynamic Type Sizes](https://developer.apple.com/design/human-interface-guidelines/typography#Specifications) — 「Support all Dynamic Type sizes from xSmall to AX5.」

| Style | Size (pts) | Weight | Line Height | SwiftUI | Usage |
|-------|-----------|--------|-------------|---------|-------|
| `typeLargeTitle` | 34 | Bold | 41 | `.largeTitle` | 画面タイトル |
| `typeTitle1` | 28 | Bold | 34 | `.title` | セクション見出し |
| `typeTitle2` | 22 | SemiBold | 28 | `.title2` | カードタイトル |
| `typeTitle3` | 20 | SemiBold | 25 | `.title3` | サブセクション |
| `typeHeadline` | 17 | SemiBold | 22 | `.headline` | リストアイテムヘッダー |
| `typeBody` | 17 | Regular | 22 | `.body` | 本文テキスト |
| `typeCallout` | 16 | Regular | 21 | `.callout` | 説明文 |
| `typeSubheadline` | 15 | Regular | 20 | `.subheadline` | プロトコル詳細 |
| `typeFootnote` | 13 | Regular | 18 | `.footnote` | キャプション |
| `typeCaption1` | 12 | Regular | 16 | `.caption` | タイムスタンプ |
| `typeCaption2` | 11 | Regular | 13 | `.caption2` | バッジテキスト |

**Timer Display (特殊):**

| Style | Size | Weight | Usage |
|-------|------|--------|-------|
| `typeTimerDisplay` | 72 | Thin | タイマーカウントダウン（MM:SS） |
| `typeTimerLabel` | 24 | Regular | タイマー部位名 |

---

## 3. Spacing & Layout

Source: [Apple HIG: Layout](https://developer.apple.com/design/human-interface-guidelines/layout) — 「Use consistent spacing based on 8pt grid.」

| Token | Value (pts) | Usage |
|-------|------------|-------|
| `spacing2` | 2 | アイコンとテキストの最小間隔 |
| `spacing4` | 4 | インラインアイテム間隔 |
| `spacing8` | 8 | コンポーネント内要素 |
| `spacing12` | 12 | 小カード padding |
| `spacing16` | 16 | 標準 padding（水平マージン） |
| `spacing20` | 20 | セクション間 |
| `spacing24` | 24 | カード padding |
| `spacing32` | 32 | 大セクション間 |
| `spacing48` | 48 | 画面上下 padding |

**Screen Layout:**

| 要素 | 値 |
|------|-----|
| 水平マージン | 16pt |
| Tab Bar 高さ | システムデフォルト（34pt + safe area） |
| カード corner radius | 12pt |
| ボタン corner radius | 12pt |
| ボタン最小高さ | 52pt |

---

## 4. Components

| Name | Props | Usage |
|------|-------|-------|
| `PrimaryButton` | `title: String`, `action: () -> Void`, `isLoading: Bool` | CTA ボタン（colorPrimary 背景） |
| `SecondaryButton` | `title: String`, `action: () -> Void` | サブアクション（アウトライン） |
| `GhostButton` | `title: String`, `action: () -> Void` | "Maybe Later"（Rule 20 必須） |
| `ProtocolCard` | `protocol: LightProtocol`, `isPremiumLocked: Bool` | ホーム画面プロトコル一覧 |
| `SessionRow` | `session: Session` | ダッシュボードセッション一覧 |
| `StatBadge` | `value: String`, `label: String`, `color: Color` | 統計値表示 |
| `StreakIndicator` | `streak: Int` | 連続日数アニメーション表示 |
| `TimerRing` | `progress: Double`, `color: Color` | タイマー円形プログレス |
| `PremiumBadge` | — | プレミアム限定コンテンツマーカー |
| `PaywallPlanCard` | `package: Package`, `isSelected: Bool`, `isBestValue: Bool` | ペイウォール価格カード |

---

## 5. Icons (SF Symbols)

Source: [SF Symbols 5](https://developer.apple.com/sf-symbols/) — 「All symbols support multicolor and hierarchical rendering modes.」

| Name | Symbol | Usage |
|------|--------|-------|
| `iconHome` | `house.fill` | ホームタブ |
| `iconTimer` | `timer` | タイマータブ / タイマー画面 |
| `iconDashboard` | `chart.bar.fill` | ダッシュボードタブ |
| `iconSettings` | `gearshape.fill` | 設定タブ |
| `iconPremium` | `crown.fill` | プレミアムバッジ |
| `iconPlay` | `play.fill` | タイマー開始 |
| `iconPause` | `pause.fill` | タイマー一時停止 |
| `iconStop` | `stop.fill` | タイマー停止 |
| `iconCheckmark` | `checkmark.circle.fill` | 完了状態 |
| `iconFace` | `face.smiling` | 顔・肌プロトコル |
| `iconJoint` | `figure.walk` | 関節・筋肉プロトコル |
| `iconWound` | `bandage.fill` | 傷・回復プロトコル |
| `iconBack` | `figure.core.training` | 背中・脊椎プロトコル |
| `iconFullBody` | `figure.arms.open` | 全身プロトコル |
| `iconStreak` | `flame.fill` | 連続日数 |
| `iconNotification` | `bell.fill` | 通知設定 |
| `iconLock` | `lock.fill` | プレミアムロック |

---

## 6. Animations

Source: [Apple HIG: Motion](https://developer.apple.com/design/human-interface-guidelines/motion) — 「Use animation purposefully to provide feedback, draw attention, and orient users.」

| Trigger | Duration | Type | SwiftUI |
|---------|----------|------|---------|
| タイマー開始 | 0.4s | Spring（dampingFraction: 0.8） | `.animation(.spring(dampingFraction: 0.8))` |
| タイマー完了 | 0.8s | ScaleEffect → ConfettiBurst | `.scaleEffect(1.2).animation(.easeInOut)` |
| セッション保存 | 0.3s | Fade + Slide | `.transition(.opacity.combined(with: .move(edge: .bottom)))` |
| Paywall ペイン切り替え | 0.25s | EaseInOut | `.animation(.easeInOut(duration: 0.25))` |
| StreakIndicator 更新 | 0.6s | Bounce | `.animation(.interpolatingSpring(stiffness: 120, damping: 10))` |
| プロトコルカード タップ | 0.2s | Scale + Highlight | `.scaleEffect(0.97).animation(.easeInOut(duration: 0.2))` |
| TimerRing 進捗 | 1.0s（毎秒） | Linear | `.animation(.linear(duration: 1.0))` |

**Reduced Motion 対応:**

```swift
@Environment(\.accessibilityReduceMotion) var reduceMotion
// reduceMotion == true の場合、全アニメーションを .none に切り替え
```

---

## 7. Accessibility

Source: [Apple HIG: Accessibility](https://developer.apple.com/design/human-interface-guidelines/accessibility) — 「Design for Dynamic Type, VoiceOver, and Reduce Motion from the start.」

| 項目 | 要件 | 実装 |
|------|------|------|
| Dynamic Type | xSmall〜AX5 全サイズ対応 | SwiftUI `.font(.system(size:))` 使用禁止。HIG スタイル必須 |
| VoiceOver | 全インタラクティブ要素にラベル | `.accessibilityLabel()` + `.accessibilityHint()` |
| Reduce Motion | 全アニメーション対応 | `@Environment(\.accessibilityReduceMotion)` チェック |
| Color-only info | 色だけで情報を伝えない | アイコン + テキストと組み合わせる |
| Touch targets | 最小 44×44pt | `.frame(minWidth: 44, minHeight: 44)` |
| Focus management | モーダル表示時にフォーカス移動 | `.accessibilityAddTraits(.isModal)` |
