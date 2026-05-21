# Spec: オンボーディング v3 — ファネル修正 & Mixpanelトラッキング正確化

> **目的:** 離脱率の高いステップを削除/修正し、購入フローを修復し、全ステップのMixpanelトラッキングを正確にする
> **参照:** `ios-app-onboarding` スキル、`.cursor/plans/ios/onboarding-paywall-best-practices.md`
> **ブランチ:** `feature/onboarding-v3` (dev から作成)
> **日付:** 2026-03-21
> **Mixpanelデータ期間:** 2026-03-13 ~ 03-20 (直近7日)

---

## 1. AS-IS（現状）

### 1.1 現状フロー図

```
PHASE 1: HOOK                PHASE 2: INVEST              PHASE 3: VALUE DEMO
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│ Welcome  │→│ Struggles│→│ Struggle │→│ Goals    │→│ Personal │→│ ValueProp│
│          │  │          │  │ Depth    │  │          │  │ Insight  │  │ 7日旅程  │
│ CTA+SIWA │  │ チップ選択│  │ 1タップ  │  │ チップ   │  │ ミラー   │  │ コミット │
└──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘
     34            27            23            23            23            23

PHASE 3(続)           PHASE 4              PHASE 5: CONVERT（3ステップペイウォール）
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│ Live     │→│ Notif    │→│ Paywall  │→│ Trial    │→│ Plan     │
│ Demo     │  │ 通知許可 │  │ Primer   │  │ Timeline │  │ Selection│
│ Nudge体験│  │          │  │ 価格なし │  │ Blinkist │  │ 購入CTA  │
└──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘
     20            18            18            14           22(異常)
```

### 1.2 現状 Mixpanelファネル（直近7日、34ユーザー）

| # | ステップ | Mixpanelイベント | 件数 | ステップ離脱率 | 累計残存率 |
|---|---------|-----------------|------|-------------|----------|
| 0 | オンボ開始 | `onboarding_started` | 34 | — | 100% |
| 1 | Welcome完了 | `onboarding_welcome_completed` | 27 | 🔴 **20.6%** | 79.4% |
| 2 | 悩み選択 | `onboarding_struggles_completed` | 23 | 🟡 14.8% | 67.6% |
| 3 | 悩みの深さ | `onboarding_struggle_depth_completed` | 23 | 0% | 67.6% |
| 4 | 目標選択 | `onboarding_goals_completed` | 23 | 0% | 67.6% |
| 5 | パーソナル洞察 | `onboarding_insight_completed` | 23 | 0% | 67.6% |
| 6 | 価値提案 | `onboarding_valueprop_completed` | 23 | 0% | 67.6% |
| 7 | ライブデモ | `onboarding_live_demo_completed` | 20 | 🟠 **13.0%** | 58.8% |
| 8 | 通知許可 | `onboarding_notifications_completed` | 18 | 🟡 10.0% | 52.9% |
| 9 | オンボ完了 | `onboarding_completed` | 18 | 0% | 52.9% |
| P0 | Paywall Primer | `paywall_primer_viewed` | 18 | 0% | 52.9% |
| P1 | Trial Timeline | `paywall_timeline_viewed` | 14 | 🟠 **22.2%** | 41.2% |
| P2 | プラン選択 | `paywall_plan_selection_viewed` | 22 | ⚠️ 異常(重複) | — |
| — | 購入完了 | `onboarding_paywall_purchased` | 0 | 🔴 **100%** | 0.0% |
| — | 無料スキップ | `onboarding_paywall_dismissed_free` | 9 | — | — |
| — | ドロワー表示 | `paywall_drawer_viewed` | 12 | — | — |
| — | ドロワーCTA | `paywall_drawer_converted` | 3 | — | — |

**変換率: 0.0% (目標: >10% DL→Trial)**

### 1.3 ペイウォール分岐の正確なフロー（AS-IS）

```
Plan Selection 画面に到達
│
├─ 選択A: [購入CTA] タップ → purchase() → Apple決済シート
│   ├─ 成功 → onboarding_paywall_purchased → 完了        … 0人
│   ├─ キャンセル → 画面に留まる
│   └─ エラー → errorMessage表示
│
├─ 選択B: [Maybe Later] タップ → ドロワーがスライドアップ  … 12人が見た
│   ├─ B-1: ドロワー[Start Trial] タップ                  … 3人
│   │   → ❌ 購入しない！ドロワー閉じてplan selectionに戻るだけ
│   │   → onAppear再発火 → track重複（データ異常A1の原因）
│   └─ B-2: ドロワー[Skip] タップ                         … 9人
│       → handlePaywallDismissedAsFree() → 無料で完了
│
└─ 選択C: 何もせず離脱（アプリ閉じる等）
```

### 1.4 データ異常の根本原因

| # | 異常 | 根本原因 | コード箇所 |
|---|------|---------|-----------|
| A1 | `plan_selection_viewed`=22 > `timeline_viewed`=14 | `PlanSelectionStepView.swift:128` の `onAppear` がドロワー開閉時に再発火。14初回 + ドロワー操作の重複 = 22 | `PlanSelectionStepView.swift:128-129` |
| A2 | `drawer_converted`=3 だが `purchased`=0 | ドロワーCTAは購入を実行しない。`showDrawer = false` するだけ。ユーザーは再度CTAを押す必要がある（2段階） | `OnboardingFlowView.swift:50-54` |
| A3 | `onboarding_paywall_viewed`=0 | Enum定義あるがtrack()呼出しなし。cronがこのイベントを参照 → 常に0 | `AnalyticsManager.swift:164` |
| A4 | `rc_trial_started_event`=0 | iOSアプリ側にtrack()実装なし。cronが参照してるが発火コードなし | `mixpanel_client.py:25` |

### 1.5 レガシーEnum（削除対象）

| Enum | 状態 |
|------|------|
| `onboardingAccountCompleted` | ❌ 画面削除済み |
| `onboardingValueCompleted` | ❌ 画面削除済み |
| `onboardingSourceCompleted` | ❌ 画面削除済み |
| `onboardingNameCompleted` | ❌ 画面削除済み |
| `onboardingGenderCompleted` | ❌ 画面削除済み |
| `onboardingAgeCompleted` | ❌ 画面削除済み |
| `onboardingIdealsCompleted` | ❌ 画面削除済み |
| `onboardingHabitsetupCompleted` | ❌ 画面削除済み |
| `onboardingAlarmkitCompleted` | ❌ 画面削除済み |
| `onboardingStepCompleted` | ❌ 互換性用だが未使用 |
| `onboardingPaywallViewed` | ❌ 未実装。`paywallPrimerViewed`と重複 |
| `onboardingPaywallDismissed` | ❌ 未実装。`onboardingPaywallDismissedFree`と重複 |
| `paywallViewed` | ⚠️ メソッド内使用だがメソッド自体が未呼出 |
| `paywallDismissed` | ⚠️ メソッド内使用だがメソッド自体が未呼出 |
| `upgradePaywallPurchased` | ⚠️ 未実装 |

### 1.6 AS-IS ペイウォール全画面 ASCII（コードから正確に再現）

#### P0: PaywallPrimerStepView（現状）

```
┌──────────────────────────────────────────────┐
│                                              │
│                   (Spacer)                   │
│                                              │
│          "We want you to try                 │  font: 32pt bold, center
│           Anicca for free"                   │  色: AppTheme.Colors.label
│                                              │
│    "Your personalized plan is ready.         │  font: 16pt, center
│     Experience the full journey risk-free."  │  色: secondary
│                                              │
│      ✅  Full access to all features         │  checkmark.circle.fill
│                                              │  font: 20pt icon + 16pt medium text
│      🔔  Personalized nudges                │  bell.badge.fill
│                                              │
│      ❌  Cancel anytime                     │  xmark.circle
│                                              │
│                   (Spacer)                   │
│                                              │
│    [============= Continue ==============]   │  font: 18pt semibold, 白文字
│                                              │  accent色背景, h:56, r:28
│                                              │
│              (padding-bottom: 64)            │
│                                              │
│    ×ボタン: なし                             │
│    価格: なし                                │
│    背景: AppBackground()                     │
└──────────────────────────────────────────────┘
```

#### P1: TrialTimelineStepView（現状）

```
┌──────────────────────────────────────────────┐
│                                              │
│                   (Spacer)                   │
│                                              │
│        "Your free trial timeline"            │  font: 32pt bold, center
│                                              │  色: AppTheme.Colors.label
│                                              │
│      ▶  Today — Start exploring Anicca      │  play.circle.fill (24pt)
│      │                                       │  accent色アイコン, w:32 h:32
│      │  (縦線: w:2, h:40, accent 30%)       │
│      │                                       │
│      🔔 Day 5 — We'll send you a reminder  │  bell.fill (24pt)
│      │                                       │
│      │  (縦線: w:2, h:40, accent 30%)       │
│      │                                       │
│      ✅ Day 7 — Your trial ends.            │  checkmark.seal.fill (24pt)
│              You decide.                     │
│                                              │  テキスト: 16pt medium, label色
│                                              │  padding-top: 4 on each text
│    "We'll remind you before you're           │
│     charged. No surprises."                  │  font: 14pt, secondary, center
│                                              │
│                   (Spacer)                   │
│                                              │
│    [============= Continue ==============]   │  font: 18pt semibold, 白文字
│                                              │  accent色背景, h:56, r:28
│              (padding-bottom: 64)            │
│                                              │
│    ×ボタン: なし                             │
│    背景: AppBackground()                     │
└──────────────────────────────────────────────┘
```

#### P2: PlanSelectionStepView（現状）

```
┌──────────────────────────────────────────────┐
│                                              │
│    "Choose your plan"                        │  font: 28pt bold
│                                              │  色: label, padding-top: 32
│  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─  │
│  (packages空 → ProgressView + Spacer)       │
│  (packages有 → 以下表示:)                    │
│                                              │
│  ScrollView ↓                                │
│  ┌────────────────────────────────────────┐  │  ← yearly planCard
│  │                                        │  │  背景: accent 10% (選択時)
│  │  "Anicca Premium"   [BEST VALUE]       │  │  title: 16pt semibold, label色
│  │                      10pt bold白文字   │  │  badge: accent背景 Capsule
│  │                      accent色背景      │  │
│  │                                        │  │
│  │  "$49.99/yr"         "Save 58%"        │  │  price: 14pt secondary
│  │                       12pt semibold    │  │  save: accent色
│  │                                        │  │
│  │                   [✓ checkmark.fill]   │  │  24pt accent色
│  │                                        │  │
│  │  枠線: accent色 2px (選択時)           │  │  角丸: 16pt
│  └────────────────────────────────────────┘  │
│                                              │
│  ┌────────────────────────────────────────┐  │  ← monthly planCard
│  │                                        │  │  背景: buttonUnselected
│  │  "Anicca Premium"                      │  │  badge: なし
│  │                                        │  │  save: なし
│  │  "$9.99/mo"                            │  │
│  │                                        │  │
│  │                        [○ circle]      │  │  24pt secondary色
│  │                                        │  │
│  │  枠線: なし (未選択)                   │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  "⭐ 4.9 · Trusted by 10,000+ users"       │  font: 14pt medium
│                                              │  色: secondary
│                                              │
│  (errorMessage時: 赤caption)                 │
│                                              │
│  [======= Start Free Trial =======]         │  font: 18pt semibold, 白文字
│  or "Subscribe" (trial無し時)                │  accent背景(選択時) / 50%(未選択)
│                                              │  h:56, r:28
│                                              │  disabled: package未選択 or 購入中
│                                              │
│  "No commitment. Cancel anytime."            │  font: 13pt, secondary
│                                              │
│  "Maybe later"          "Restore Purchases"  │  font: 14pt medium, secondary
│                                              │  HStack spacing: 24
│                                              │
│                          (padding-bottom: 32)│
│                                              │
│  ×ボタン: ❌ なし                            │
│  Terms/Privacy: ❌ なし                      │
│  パーソナライズ見出し: ❌ なし                │
│  背景: AppBackground()                       │
└──────────────────────────────────────────────┘
```

#### ドロワー: DrawerOfferView（現状 — "Maybe later"タップ時）

```
┌──────────────────────────────────────────────┐
│  (黒40%オーバーレイ — タップでドロワー閉じる) │
│                                              │
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │          ━━━━━━━━━━━                   │  │  ドラッグインジケーター
│  │          (w:36, h:5, gray 40%, r:2.5)  │  │  padding-top: 8
│  │                                        │  │
│  │    "Not ready for a year?"             │  │  font: 24pt bold, label色
│  │                                        │  │  center
│  │    "That's just $0.96/week             │  │  font: 16pt, secondary
│  │     — less than a cup of coffee"       │  │  center, padding-h: 16
│  │                                        │  │
│  │    [==== Start Free Trial ====]        │  │  font: 18pt semibold
│  │                                        │  │  accent背景, 白文字
│  │                                        │  │  h:56, r:28
│  │                                        │  │  padding-h: 24
│  │                                        │  │
│  │             "Maybe later"              │  │  font: 14pt medium
│  │                                        │  │  secondary色
│  │                                        │  │  padding-bottom: 16
│  │                                        │  │
│  │  背景: cardBackground, r:24            │  │
│  │  影: 黒15%, radius:20, y:-5            │  │
│  └────────────────────────────────────────┘  │
└──────────────────────────────────────────────┘

ドロワーCTA "Start Free Trial" の動作:
  → track(.paywallDrawerConverted)
  → onStartTrial()
  → showDrawer = false (ドロワー閉じる)
  → Plan Selection画面に戻る
  → ❌ 購入は実行されない！
  → onAppear再発火 → track重複

ドロワー "Maybe later" の動作:
  → onSkip()
  → handlePaywallDismissedAsFree()
  → track(.onboardingPaywallDismissedFree)
  → 無料ユーザーとして完了、メイン画面へ
```

---

## 2. TO-BE（改善後）

### 2.1 改善後フロー図

```
PHASE 1: HOOK (3ステップ)
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ [1] Welcome  │→│ [2] Struggles│→│ [3] Struggle │
│ CTA=accent色 │  │ チップ選択   │  │    Depth     │
│ SIWA=小さく  │  │              │  │ 1タップ      │
└──────────────┘  └──────────────┘  └──────────────┘

PHASE 2: INVEST (2ステップ)
┌──────────────┐  ┌──────────────┐
│ [4] Goals    │→│ [5] Personal │
│ チップ選択   │  │    Insight   │
│              │  │ ミラーリング │
└──────────────┘  └──────────────┘

PHASE 3: VALUE DEMO (1ステップ) ← ライブデモ削除
┌──────────────┐
│ [6] ValueProp│
│ 7日旅程      │
└──────────────┘

PHASE 4: PERMISSION (1ステップ)
┌──────────────┐
│ [7] Notif    │
│ 通知許可     │
└──────────────┘

PHASE 5: CONVERT (2ステップペイウォール) ← Timeline削除
┌──────────────┐  ┌──────────────┐
│ [P0] Primer  │→│ [P1] Plan    │
│ "Try free"   │  │ Selection    │
│ 価格なし     │  │              │
│ ×なし        │  │ [X]→メイン   │
│              │  │ 個人化見出し │
│              │  │ Terms追加    │
│              │  │ ドロワー削除 │
└──────────────┘  └──────┬───────┘
                                           │
                              ┌────────────┼────────────┐
                              ▼            ▼            ▼
                        [購入CTA]    [Maybe Later]    [X]
                              │            │            │
                              ▼            ▼            ▼
                        purchase()   無料で完了     無料で完了
                        RevenueCat   → メイン画面   → メイン画面
                              │
                         ┌────┴────┐
                         ▼         ▼
                      成功      キャンセル
                      purchased  (留まる)
                      +trial_started (introductoryDiscount有の場合のみ)
                      → メイン画面
```

### 2.2 変更サマリ

| 変更 | AS-IS | TO-BE | 理由 |
|------|-------|-------|------|
| ライブデモ | ✅ Step 7 | 🗑️ **削除** | 13%離脱。ユーザーが理解不能（従兄弟テスト失敗） |
| ドロワー | ✅ スライドアップ | 🗑️ **完全削除** | 無意味。CTA押しても購入しない。複雑さの元凶 |
| [X]ボタン | ❌ なし | ✅ **Plan Selection右上** | Apple準拠。タップ→**直接メイン画面へ**（無料完了） |
| "Maybe Later" | ドロワー表示 | **直接メイン画面へ**（無料完了） | ドロワー不要。シンプルに |
| ソーシャルプルーフ | "⭐ 4.9 · 10,000+ users" | 🗑️ **削除** | 嘘。10,000ユーザーいない。レーティングは5.0 |
| Welcome CTA | label色（地味）| **accent色（目立つ）** | 20.6%離脱削減 |
| SIWA | 大きい h:44 | **小さい h:36 + 薄く** | 新規ユーザーの注意をCTAに集中 |
| ペイウォールタイトル | "Choose your plan"固定 / personalizedTitle(悩み名含む動的) | **"Your path to change starts here" (固定、アウトカム訴求)** | "Sell the outcome, not the product" +50% CVR (Superwall)。F4で実装 |
| Terms/Privacy | ❌ なし | ✅ **追加** | Apple必須。リジェクトリスク |
| Trial Timeline | ✅ PaywallStep P1 | 🗑️ **削除** | 22.2%離脱。Primer→Plan直行で十分 |
| onAppear重複 | 毎回発火 | **1回だけ** | データ異常A1修正 |
| trial_started | 未実装 | **購入成功時、introductoryDiscount有の場合のみ発火** | トライアル追跡 |
| 朝メトリクスcron | 9イベント(2つ壊れ) | **全ステップ対応** | 毎日のファネル追跡 |
| レガシーEnum | 15個残存 | **全削除** | コード衛生 |
| ステップ数 | 11 (8オンボ+3ペイウォール) | **9 (7オンボ+2ペイウォール)** | ライブデモ+Timeline削除 |

### 2.3 TO-BE ペイウォール全画面 ASCII

#### P0: PaywallPrimerStepView（変更なし）

```
┌──────────────────────────────────────────────┐
│                                              │
│                   (Spacer)                   │
│                                              │
│          "We want you to try                 │  font: 32pt bold, center
│           Anicca for free"                   │  色: label
│                                              │
│    "Your personalized plan is ready.         │  font: 16pt, center
│     Experience the full journey risk-free."  │  色: secondary
│                                              │
│      ✅  Full access to all features         │  checkmark.circle.fill
│      🔔  Personalized nudges                │  bell.badge.fill
│      ❌  Cancel anytime                     │  xmark.circle
│                                              │
│                   (Spacer)                   │
│                                              │
│    [============= Continue ==============]   │  18pt semibold, accent背景
│                                              │
│              (padding-bottom: 64)            │
│                                              │
│    ×ボタン: なし ✅ (BP: Step1は逃げ道なし)  │
│    価格: なし ✅                             │
└──────────────────────────────────────────────┘
変更: なし
```

#### P1: TrialTimelineStepView → 🗑️ **完全削除**

```
TrialTimelineStepView.swift → 削除
PaywallStep enum から .timeline を削除
Primer [Continue] → 直接 Plan Selection へ遷移
```

#### P2→P1: PlanSelectionStepView（大幅変更）

```
┌──────────────────────────────────────────────┐
│                                         [X]  │  ← NEW: xmarkボタン
│                                              │  タップ → 無料で完了 → メイン画面
│    "夜更かしを克服する —                      │  ← NEW: パーソナライズ見出し
│     あなた専用のプラン"                       │  ユーザーのstrugglesから動的生成
│                                              │  font: 28pt bold, label色
│  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─  │
│                                              │
│  ScrollView ↓                                │
│  ┌────────────────────────────────────────┐  │  yearly planCard（変更なし）
│  │                                        │  │
│  │  "Anicca Premium"   [BEST VALUE]       │  │  16pt semibold + badge
│  │                      accent Capsule    │  │
│  │                                        │  │
│  │  "$49.99/yr"         "Save 58%"        │  │  14pt secondary + accent
│  │                                        │  │
│  │                   [✓ checkmark.fill]   │  │  24pt accent
│  │                                        │  │
│  │  accent10%背景 + accent2px枠           │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  ┌────────────────────────────────────────┐  │  monthly planCard（変更なし）
│  │                                        │  │
│  │  "Anicca Premium"                      │  │
│  │  "$9.99/mo"            [○ circle]      │  │
│  │                                        │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  （ソーシャルプルーフ削除）                    │  ← REMOVED: 嘘の数字
│                                              │
│  [======= Start Free Trial =======]         │  18pt semibold, accent背景
│  or "Subscribe" (trial無し時)                │  h:56, r:28
│                                              │
│  "No commitment. Cancel anytime."            │  13pt, secondary
│                                              │
│  "Maybe later"          "Restore Purchases"  │  14pt medium, secondary
│                                              │
│  Terms · Privacy                             │  ← NEW: 法的リンク
│                                              │  12pt, secondary
│                          (padding-bottom: 32)│  タップでSafari
│                                              │
└──────────────────────────────────────────────┘

[X]ボタン タップ時:
  → track(.onboardingPaywallDismissedFree)
  → handlePaywallDismissedAsFree()
  → メイン画面へ（無料ユーザー）

"Maybe later" タップ時:
  → track(.onboardingPaywallDismissedFree)
  → handlePaywallDismissedAsFree()
  → メイン画面へ（無料ユーザー）
  （ドロワーは出ない。直接メインへ。）

[Start Free Trial] タップ時:
  → purchase() → Apple決済シート
  → 成功: track(.onboardingPaywallPurchased) + track(.trialStarted)
  → メイン画面へ
```

#### ドロワー: 🗑️ 完全削除

```
DrawerOfferView.swift → 削除
OnboardingFlowView.swift の showDrawer 関連コード → 全削除
AnalyticsEvent の paywallDrawerViewed, paywallDrawerConverted → 削除
```

---

## 3. 修正パッチ一覧

### P1: ライブデモ削除 🗑️

| 項目 | 値 |
|------|-----|
| 影響ファイル | `OnboardingStep.swift`, `OnboardingFlowView.swift`, `DemoNudgeStepView.swift` |
| 内容 | `.liveDemo` enum削除。`advance()`で `.valueProp`→`.notifications` 直接遷移。`DemoNudgeStepView.swift` 削除 |
| Mixpanel | `onboarding_live_demo_completed` 削除 |
| 期待効果 | 13%離脱回復 |

### P2: ドロワー完全削除 + [X]/"Maybe Later" → メイン画面 🗑️

| 項目 | 値 |
|------|-----|
| 影響ファイル | `DrawerOfferView.swift`(削除), `OnboardingFlowView.swift`, `PlanSelectionStepView.swift` |
| 削除するもの | `DrawerOfferView.swift` ファイル削除。`OnboardingFlowView` から `showDrawer`, `weeklyPriceString`, ドロワーoverlay全体, `onShowDrawer`コールバック削除 |
| [X]ボタン | `PlanSelectionStepView` 右上に `xmark` ボタン追加。タップ → `onDismiss()` → `handlePaywallDismissedAsFree()` → メイン画面 |
| "Maybe Later" | `onShowDrawer()` → `onDismiss()` に変更。タップ → 直接メイン画面 |
| Mixpanel | `paywallDrawerViewed`, `paywallDrawerConverted` enum削除 |

### P3: onAppear重複発火修正 🔧

| 項目 | 値 |
|------|-----|
| 影響ファイル | `PlanSelectionStepView.swift`, `PaywallPrimerStepView.swift` |
| 内容 | 各画面に `@State private var hasTracked = false` 追加。`onAppear`で1回だけtrack |

### P4: Welcome画面CTA改善 🔧

| 項目 | 値 |
|------|-----|
| 影響ファイル | `WelcomeStepView.swift` |
| AS-IS | CTA=`label`色 + SIWA=`h:44`で目立つ |
| TO-BE | CTA=`accent`色 + SIWA=`h:36` + 説明=`caption`+`opacity(0.6)` |

### P5: ソーシャルプルーフ削除 🗑️

| 項目 | 値 |
|------|-----|
| 影響ファイル | `PlanSelectionStepView.swift`, Localizable.strings (en/ja) |
| 内容 | `paywall_plan_social_proof` 表示を削除。Localizable.stringsからも削除 |
| 理由 | "10,000+ users" は嘘。レーティングは5.0で4.9も嘘 |

### P6: ~~パーソナライズ見出し追加~~ → **F4に統合済み。このパッチは無効**

| 項目 | 値 |
|------|-----|
| ~~影響ファイル~~ | ~~`PlanSelectionStepView.swift`, Localizable.strings~~ |
| 状態 | **F4で上書き。personalizedTitleは削除し、固定テキスト "Your path to change starts here" を使用** |
| 理由 | 悩み名を見出しに入れるのはBP違反。"Sell the outcome, not the product" (+50% CVR) |

### P7: Terms/Privacy リンク追加 🔧

| 項目 | 値 |
|------|-----|
| 影響ファイル | `PlanSelectionStepView.swift` |
| 内容 | Restore Purchases下に `Terms · Privacy` リンク追加 |
| Apple準拠 | CRITICAL |

### P8: Trial Timeline削除 🗑️

| 項目 | 値 |
|------|-----|
| 影響ファイル | `TrialTimelineStepView.swift`(削除), `OnboardingStep.swift`, `OnboardingFlowView.swift`, `Localizable.strings (en/ja)` |
| 内容 | `TrialTimelineStepView.swift` 削除。`PaywallStep` enum から `.timeline` 削除。`OnboardingFlowView` の遷移ロジックで Primer → Plan Selection 直行 |
| Localizable削除キー | `paywall_timeline_title`, `paywall_timeline_today`, `paywall_timeline_day5`, `paywall_timeline_day7`, `paywall_timeline_subtitle`（5キー×2言語）。`common_continue` は他画面共通のため削除しない |
| Mixpanel | `paywall_timeline_viewed` 削除 |
| 期待効果 | 22.2%離脱回復 |

### P9: trial_started イベント実装 🔧

| 項目 | 値 |
|------|-----|
| 影響ファイル | `PlanSelectionStepView.swift` |
| 内容 | `purchase()`成功時、`introductoryDiscount != nil` → `track(.trialStarted)` |

### P10: 朝メトリクスcron修正 🔧

| 項目 | 値 |
|------|-----|
| 影響ファイル | `scripts/daily-metrics/mixpanel_client.py`, `models.py` |
| 内容 | `_EVENTS`を全ステップに拡張。壊れたイベント名修正。ドロワー関連削除 |

### P11: レガシーEnum + 未使用メソッド削除 🗑️

| 項目 | 値 |
|------|-----|
| 影響ファイル | `AnalyticsManager.swift` |
| 内容 | 15個のレガシーenumケース + `trackPaywallViewed()` + `trackPaywallDismissed()` 削除 |

---

## 4. 実装順序

| # | パッチ | 理由 |
|---|--------|------|
| 1 | **P2** ドロワー削除 + [X]/MaybeLater→メイン | 最大の構造変更。他のパッチの前提 |
| 2 | **P8** Trial Timeline削除 | 構造変更。P2と同時にやるべき |
| 3 | **P1** ライブデモ削除 | 13%離脱回復 |
| 4 | **P3** onAppear重複修正 | データ正確化 |
| 5 | **P5** ソーシャルプルーフ削除 | 嘘を消す |
| 6 | **P7** Terms/Privacy追加 | Apple準拠 |
| 7 | **P9** trial_started実装 | メトリクス |
| 8 | **P4** Welcome CTA改善 | 20.6%離脱削減 |
| 9 | **P6** パーソナライズ見出し | CVR改善 |
| 10 | **P10** 朝メトリクスcron | ファネル追跡 |
| 11 | **P11** レガシーEnum削除 | コード衛生 |

---

## 5. 改善後の目標メトリクス

| メトリクス | AS-IS | TO-BE目標 | ベンチマーク |
|-----------|-------|----------|------------|
| オンボ完了率 | 52.9% | >70% | スキル基準 |
| ペイウォール到達率 | 52.9% | >80% | Superwall |
| DL→Trial | 0.0% | >10% | RC H&F P75 |
| Trial→Paid | N/A | >60% | RC Best |
| ペイウォールCVR | 0.0% | >5% | スキル基準 |

---

## 6. TO-BE 完全体験フロー（ユーザー視点 + 全Mixpanelイベント）

```
アプリ初起動
│
▼ [track: onboarding_started]
[1] Welcome — EN: "Break free from the patterns that hold you back"
              JA: "あなたを縛るパターンから自由になろう"
    CTA=accent色（大きい）、SIWA=h:36+opacity:0.6
│ [track: onboarding_welcome_completed]
▼
[2] Struggles — EN: "What's holding you back?"
                JA: "あなたの悩みは？"
    チップ選択（複数可、13種類）
│ [track: onboarding_struggles_completed]
▼
[3] Struggle Depth — EN: "How often does this affect you?"
                     JA: "どのくらい困っている？"
    1タップ完了（毎日/週数回/たまに）
│ [track: onboarding_struggle_depth_completed + {frequency}]
▼
[4] Goals — EN: "What does your best self look like?"
            JA: "最高の自分は、どんな姿ですか？"
    チップ選択（複数可）
│ [track: onboarding_goals_completed + {goals_count}]
▼
[5] Personalized Insight — EN: "Based on your answers"
                           JA: "あなたの回答に基づいて"
    ユーザーの回答をミラーリング表示
│ [track: onboarding_insight_completed]
▼
[6] Value Prop — EN: "Your 7-Day Journey"
                 JA: "あなたの7日間の旅"
    プログラムプレビュー + コミットメント
│ [track: onboarding_valueprop_completed]
▼
[7] Notification Permission — EN: "Don't miss your nudges"
                               JA: "ナッジ通知を受け取る"
    CTA背景=accent色
│ [track: onboarding_notifications_completed]
│ [track: onboarding_completed]
▼
━━━ ペイウォール開始 ━━━
▼ [track: paywall_primer_viewed]
[P0] EN: "We want you to try Anicca for free"
     JA: "まずは無料でアニッチャを試してください"
     ✅ 全機能  🔔 ナッジ  ❌ いつでもキャンセル
     [Continue] — 価格なし、×なし
▼ [track: paywall_plan_selection_viewed]
[P1] EN: "Your path to change starts here" [X]
     JA: "変わるための道は、ここから" [X]
     サブタイトル EN: "Start your 7-day free trial"
     サブタイトル JA: "7日間無料で全機能をお試し"
     ✅ Full access / 全機能  🔔 Nudges / ナッジ  ❌ Cancel / キャンセル
     [Yearly ローカライズ価格/年 ⭐BEST VALUE ✓] ← Save 動的計算
     [Monthly ローカライズ価格/月          ○]
     [Start Free Trial / 無料トライアルを始める]
     "No commitment. Cancel anytime." / "いつでもキャンセル可能"
     "Maybe later" / "あとで"  "Restore" / "購入を復元"
     Terms · Privacy / 利用規約 · プライバシー
     │
     ├─ [購入CTA] → Apple決済 → 成功
     │   [track: onboarding_paywall_purchased]
     │   [track: trial_started + {product_id}] (introductoryDiscount有の場合のみ)
     │   → メイン画面
     │
     ├─ [X] or [Maybe later / あとで]
     │   [track: onboarding_paywall_dismissed_free]
     │   → メイン画面（無料ユーザー）
     │
     └─ Apple決済キャンセル → 画面に留まる
```

---

## 7. Mixpanelトラッキング — 改善後の完全イベントマップ

| # | ステップ | イベント | 発火タイミング | 重複防止 |
|---|---------|---------|--------------|---------|
| 0 | オンボ開始 | `onboarding_started` | Welcome onAppear | ✅ |
| 1 | Welcome完了 | `onboarding_welcome_completed` | CTAタップ | ✅ |
| 2 | 悩み選択 | `onboarding_struggles_completed` | advance() | ✅ |
| 3 | 深さ選択 | `onboarding_struggle_depth_completed` | selectFrequency() | ✅ |
| 4 | 目標選択 | `onboarding_goals_completed` | saveAndAdvance() | ✅ |
| 5 | 洞察 | `onboarding_insight_completed` | CTAタップ | ✅ |
| 6 | 価値提案 | `onboarding_valueprop_completed` | CTAタップ | ✅ |
| 7 | 通知許可 | `onboarding_notifications_completed` | advance() | ✅ |
| 8 | オンボ完了 | `onboarding_completed` | completeOnboarding() | ✅ |
| P0 | Primer | `paywall_primer_viewed` | onAppear | `hasTracked`ガード |
| P1 | Plan Selection | `paywall_plan_selection_viewed` | onAppear | `hasTracked`ガード |
| — | 購入成功 | `onboarding_paywall_purchased` | RC購入成功 | ✅ |
| — | Trial開始 | `trial_started` | 購入成功時、introductoryDiscount有の場合のみ | ✅ |
| — | 無料スキップ | `onboarding_paywall_dismissed_free` | [X] or MaybeLater | ✅ |

**削除イベント:** `onboarding_live_demo_completed`, `paywall_timeline_viewed`, `paywall_drawer_viewed`, `paywall_drawer_converted`

---

## 8. 追加修正パッチ（F1〜F8）— コピー/ローカライズ/デザイン改善

> P1〜P11 は構造変更（画面削除・トラッキング修正）。F1〜F8 はコピー・ローカライズ・UIデザインの品質改善。
> BP根拠: `ios-app-onboarding` スキル（RevenueCat 2025 / Superwall 4,500 A/B tests / Clear 30）

### F1: 通知画面タイトル修正

| 項目 | 値 |
|------|-----|
| 変更キー | `onboarding_notifications_title` |
| 影響ファイル | `Localizable.strings (en/ja/fr/es/de/pt-BR)` |
| AS-IS EN | "Stay on track" |
| TO-BE EN | **"Don't miss your nudges"** |
| AS-IS JA | "軌道を外さないために" |
| TO-BE JA | **"ナッジ通知を受け取る"** |
| BP根拠 | スキル: "Value-framed notification permission"。具体的にアプリのコア機能（nudge）を名指し。損失回避バイアス |
| 他言語 | fr/es/de/pt-BR の `onboarding_notifications_title` も変更必要。ENキー変更のためフォールバックでは古い値が残る |

### F2: 悩み選択タイトル（JA のみ）

| 項目 | 値 |
|------|-----|
| 変更キー | `onboarding_struggles_title` |
| 影響ファイル | `ja.lproj/Localizable.strings` |
| AS-IS | "何があなたを止めていますか？" |
| TO-BE | **"あなたの悩みは？"** |
| BP根拠 | 直訳で不自然。日本語として自然な表現に |

### F3: 悩み深さタイトル（JA のみ）

| 項目 | 値 |
|------|-----|
| 変更キー | `onboarding_depth_title` |
| 影響ファイル | `ja.lproj/Localizable.strings` |
| AS-IS | "どのくらいの頻度で影響を受けていますか？" |
| TO-BE | **"どのくらい困っている？"** |
| BP根拠 | スキル: "Each step ultra-lightweight"。硬すぎる表現をカジュアルに |

### F4: ペイウォールタイトル — アウトカムを売る

| 項目 | 値 |
|------|-----|
| 影響ファイル | `PlanSelectionStepView.swift`, `Localizable.strings (en/ja)` |
| 変更内容 | `personalizedTitle` computed property を削除。固定テキスト `paywall_plan_title` を使用 |
| AS-IS EN | "Choose your plan" / "Overcome %@ — your personalized plan" |
| TO-BE EN | **"Your path to change starts here"** |
| AS-IS JA | "プランを選択" / "%@を克服する — あなた専用プラン" |
| TO-BE JA | **"変わるための道は、ここから"** |
| 削除キー | `paywall_plan_title_personalized` (en/ja) |
| BP根拠 | スキル: "Sell the outcome, not the product" (+50% CVR)。具体的な悩み名をタイトルに入れるのはBP違反。アウトカム（変化）を売る。Welcome "Break free from the patterns" とブランド一貫性 |

### F5: 価格期間のローカライズ（"/yr" "/mo" ハードコード修正）

| 項目 | 値 |
|------|-----|
| 影響ファイル | `PlanSelectionStepView.swift`, `Localizable.strings (en/ja)` |
| AS-IS | `localizedPriceString + "/yr"`, `+ "/mo"` ← 英語ハードコード |
| TO-BE | `String(format: NSLocalizedString("paywall_plan_price_yearly", ...), price)` |
| 新キー EN | `"paywall_plan_price_yearly" = "%@/yr"`, `"paywall_plan_price_monthly" = "%@/mo"` |
| 新キー JA | `"%@/年"`, `"%@/月"` |
| BP根拠 | ローカライズ必須。日本語で "$49.99/yr" は意味不明 |
| 他言語 | 新キーのため en にフォールバック。fr/es/de/pt-BR は別タスクで翻訳追加 |

### F6: 割引率の動的計算（"Save 58%" ハードコード修正）

| 項目 | 値 |
|------|-----|
| 影響ファイル | `PlanSelectionStepView.swift`, `Localizable.strings (en/ja)` |
| AS-IS | ハードコード "Save 58%" / "58%お得" |
| TO-BE | `savePct = Int((1 - yearlyPrice / (monthlyPrice * 12)) * 100)` |
| 新キー EN | `"paywall_plan_save_dynamic" = "Save %d%%"` |
| 新キー JA | `"%d%%お得"` |
| BP根拠 | 価格変更時に嘘にならない。常に正確 |
| 他言語 | 新キーのため en にフォールバック。fr/es/de/pt-BR は別タスクで翻訳追加 |
| ゼロ除算ガード | `monthlyPrice == 0` の場合は saveLabel 非表示 |

### F7: Plan Selection サブタイトル + Feature list 追加

| 項目 | 値 |
|------|-----|
| 影響ファイル | `PlanSelectionStepView.swift`, `Localizable.strings (en/ja)` |
| 追加要素 | タイトル下にサブタイトル + ✅🔔❌ 3行の feature list |
| サブタイトル EN | "Start your 7-day free trial" |
| サブタイトル JA | "7日間無料で全機能をお試し" |
| Feature list EN | ✅ Full access to all features / 🔔 Personalized nudges / ❌ Cancel anytime |
| Feature list JA | ✅ 全機能にアクセス / 🔔 パーソナライズされたナッジ / ❌ いつでもキャンセル |
| BP根拠 | スキル The Hard Close: comparison/features + social proof above CTA。ペイウォールが簡素すぎる問題を解決 |
| 他言語 | 新キーのため en にフォールバック。fr/es/de/pt-BR は別タスクで翻訳追加 |

### F8: 通知ボタン背景色をaccent色に統一

| 項目 | 値 |
|------|-----|
| 影響ファイル | `NotificationPermissionStepView.swift:75` |
| AS-IS | `AppTheme.Colors.label`（初期状態のボタン色） |
| TO-BE | `AppTheme.Colors.accent` |
| BP根拠 | 全CTAボタンのaccent色統一。スキル: "Single clear CTA button" |

### F1〜F8 実装順序

| # | パッチ | 理由 |
|---|--------|------|
| 1 | **F4** ペイウォールタイトル | personalizedTitle削除 → 構造変更 |
| 2 | **F5** 価格ローカライズ | ハードコード修正 |
| 3 | **F6** 割引率動的計算 | ハードコード修正 |
| 4 | **F7** サブタイトル+Feature list | UI改善 |
| 5 | **F1** 通知タイトル | コピー修正 |
| 6 | **F2** 悩み選択JA | コピー修正 |
| 7 | **F3** 悩み深さJA | コピー修正 |
| 8 | **F8** 通知ボタン色 | UI修正 |
