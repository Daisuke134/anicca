# UX Specification: LumaRed

Source: [Apple HIG: App Architecture](https://developer.apple.com/design/human-interface-guidelines/app-architecture) — 「Choose navigation patterns that match the structure of your app's content.」
Source: [NNGroup: Mobile Onboarding](https://www.nngroup.com/articles/mobile-onboarding/) — 「Onboarding should demonstrate value before asking for commitment. Progressive disclosure reduces cognitive load.」
Source: [Baymard: Paywall UX](https://baymard.com/) — 「Always provide an exit path from paywalls. Forced paywalls reduce conversion.」

---

## 1. User Personas

Source: [PRD.md §2 Target User]()

### Primary: Biohacker Kenji (US) / Health-Conscious Haruki (JP)

| 属性 | 詳細 |
|------|------|
| Age | 28–40歳 |
| Goals | 赤色光デバイスを正しく使って最大の効果を得たい |
| Frustrations | プロトコルが複雑でどこに何分当てればいいかわからない。デバイスを買ったが使わなくなった |
| Usage Context | 自宅で朝のルーティン中。スマホを脇に置いてタイマー計測したい |
| Tech Savvy | 中〜高（健康アプリを複数使用） |
| Paid Apps | 健康カテゴリで月$10–30投資 |

### Secondary: Recovery Sarah (US) / Rehabilitation User (JP)

| 属性 | 詳細 |
|------|------|
| Age | 35–55歳 |
| Goals | 関節痛・傷の回復に特定プロトコルを使いたい |
| Frustrations | 「顔用」「関節用」の使い分けがわからない |
| Usage Context | 夜のケアルーティン中 |

---

## 2. Information Architecture

```
LumaRed App
├── Onboarding (初回のみ)
│   ├── Welcome Screen (SC-00)
│   ├── Feature Highlight (SC-01)
│   ├── Notification Permission (SC-02)
│   └── Paywall (SC-03) ← ソフトペイウォール [Maybe Later]
│
└── Main App (Tab Bar)
    ├── [house.fill] Home (SC-10)
    │   ├── Protocol List
    │   │   ├── Face & Skin Card (SC-11) [Free]
    │   │   ├── Joints & Muscles Card (SC-11) [Free]
    │   │   ├── Wound Healing Card (SC-11) [Free]
    │   │   ├── Back & Spine Card (SC-11) [Premium 🔒]
    │   │   └── Full Body Card (SC-11) [Premium 🔒]
    │   └── Protocol Detail → Timer (SC-20)
    │
    ├── [timer] Timer (SC-20)
    │   ├── Active Timer
    │   └── Session Complete (SC-21)
    │
    ├── [chart.bar.fill] Dashboard (SC-30)
    │   ├── Streak Counter
    │   ├── Cumulative Time
    │   └── Session History List
    │
    └── [gearshape.fill] Settings (SC-40)
        ├── Notification Toggle
        ├── Reminder Time Picker
        ├── Upgrade to Premium → Paywall (SC-03)
        └── Restore Purchases
```

---

## 3. Navigation Structure

Source: [Apple HIG: Tab Bars](https://developer.apple.com/design/human-interface-guidelines/tab-bars) — 「Use tab bars for flat information hierarchies with equal importance.」

| タイプ | 実装 | 理由 |
|--------|------|------|
| Tab Bar (Bottom) | `TabView` with 4 tabs | Home / Timer / Dashboard / Settings は並列関係 |
| Modal Sheet | Onboarding, Paywall | フルスクリーン体験。ユーザーが [Maybe Later] でいつでも閉じられる |
| NavigationStack | Home → Protocol Detail → Timer | 深い階層の線形フロー |

**Tab Bar 定義:**

| Index | Tab | Icon | Screen |
|-------|-----|------|--------|
| 0 | Home | `house.fill` | SC-10 |
| 1 | Timer | `timer` | SC-20 |
| 2 | Dashboard | `chart.bar.fill` | SC-30 |
| 3 | Settings | `gearshape.fill` | SC-40 |

---

## 4. Screen Inventory

| Screen ID | Name | Tab/Context | Description |
|-----------|------|-------------|-------------|
| SC-00 | Welcome | Onboarding | アプリ初期表示。ロゴ + ヒーローコピー + [Get Started] |
| SC-01 | Feature Highlight | Onboarding | 3スライド: プロトコル / タイマー / トラッキング |
| SC-02 | Notification Permission | Onboarding | 通知許可リクエスト。拒否時もスキップ可 |
| SC-03 | Paywall | Onboarding / Settings | ソフトペイウォール。[Maybe Later] 必須（Rule 20） |
| SC-10 | Home / Protocol List | Home Tab | 全5プロトコルカード。Premium 未購入は Back/FullBody が 🔒 |
| SC-11 | Protocol Detail | Home Tab | 波長・距離・時間・頻度のエビデンス詳細 + [Start Timer] |
| SC-20 | Timer | Timer Tab | カウントダウン表示。背景動作継続 |
| SC-21 | Session Complete | Timer Tab | 完了アニメーション。セッション保存確認 |
| SC-30 | Dashboard | Dashboard Tab | 連続日数 / 累計時間 / セッション履歴 |
| SC-40 | Settings | Settings Tab | 通知設定 / Upgrade / Restore |

---

## 5. Wireframes

### SC-00: Welcome Screen

```
┌─────────────────────────────┐
│                             │
│          [Logo]             │
│         LumaRed             │
│                             │
│   ┌─────────────────────┐   │
│   │  🔴  (Hero Image)    │   │
│   │  Red Light Device   │   │
│   └─────────────────────┘   │
│                             │
│  Your Red Light Therapy     │
│  Companion                  │
│                             │
│  Science-backed protocols   │
│  + session tracking         │
│                             │
│  ┌─────────────────────┐    │
│  │    Get Started      │    │  ← colorPrimary
│  └─────────────────────┘    │
│                             │
│  Privacy Policy · Terms     │
└─────────────────────────────┘
```

accessibilityIdentifier: `"welcome_get_started_button"`

### SC-03: Paywall (ソフトペイウォール — Rule 20 必須)

```
┌─────────────────────────────┐
│  [X] ← Maybe Later         │  ← GhostButton "Maybe Later"
│                             │
│  Start Your Glow Journey 🔴 │  ← typeTitle1
│                             │
│  ✓ All 5 body protocols     │
│  ✓ Unlimited session log    │
│  ✓ Progress dashboard       │
│  ✓ Background timer         │
│                             │
│  ┌──────────┐ ┌───────────┐ │
│  │ Monthly  │ │  Annual   │ │
│  │ $4.99/mo │ │ $29.99/yr │ │ ← PaywallPlanCard
│  │          │ │BEST VALUE │ │
│  │          │ │ Save 50%  │ │
│  └──────────┘ └───────────┘ │
│                             │
│  ┌─────────────────────┐    │
│  │  Start Free Trial   │    │  ← PrimaryButton
│  │  7 days free (Annual)│   │
│  └─────────────────────┘    │
│                             │
│  ⭐⭐⭐⭐⭐ 4.8 · 1,200 users │
│                             │
│  Cancel anytime · Billed    │
│  by Apple                   │
│                             │
│  FAQ: [Does it really work?]│
│       [How to cancel?]      │
│                             │
│  Privacy Policy · Terms     │
└─────────────────────────────┘
```

accessibilityIdentifier: `"paywall_maybe_later_button"`, `"paywall_monthly_card"`, `"paywall_annual_card"`, `"paywall_subscribe_button"`

### SC-10: Home / Protocol List

```
┌─────────────────────────────┐
│  LumaRed              🔴    │
│  ─────────────────────────  │
│                             │
│  ┌─────────────────────┐    │
│  │ 😊 Face & Skin       │   │  ← ProtocolCard (Free)
│  │ 630–660nm · 10 min  │    │
│  │ Daily               │    │
│  └─────────────────────┘    │
│                             │
│  ┌─────────────────────┐    │
│  │ 🚶 Joints & Muscles  │   │  ← ProtocolCard (Free)
│  │ 630–850nm · 15 min  │    │
│  └─────────────────────┘    │
│                             │
│  ┌─────────────────────┐    │
│  │ 🩹 Wound Healing     │   │  ← ProtocolCard (Free)
│  │ 630nm · 5–10 min    │    │
│  └─────────────────────┘    │
│                             │
│  ┌─────────────────────┐    │
│  │ 🔒 Back & Spine      │   │  ← ProtocolCard (Premium)
│  │ PREMIUM             │    │
│  └─────────────────────┘    │
│                             │
│  ┌─────────────────────┐    │
│  │ 🔒 Full Body         │   │  ← ProtocolCard (Premium)
│  │ PREMIUM             │    │
│  └─────────────────────┘    │
│                             │
│ [Home] [Timer] [📊] [⚙️]   │
└─────────────────────────────┘
```

accessibilityIdentifier: `"home_protocol_list"`, `"protocol_card_face"`, `"protocol_card_joint"`, `"protocol_card_wound"`, `"protocol_card_back_locked"`, `"protocol_card_fullbody_locked"`

### SC-20: Timer Screen

```
┌─────────────────────────────┐
│  ← Face & Skin              │
│                             │
│                             │
│      ┌───────────┐          │
│      │   TimerRing          │  ← 円形プログレス
│      │            │         │
│      │  09:47     │         │  ← typeTimerDisplay 72pt
│      │            │         │
│      └───────────┘          │
│                             │
│      Face & Skin Session    │  ← typeTimerLabel
│      630–660nm · 6–12 inch  │
│                             │
│  ┌──────┐       ┌────────┐  │
│  │Pause │       │  Stop  │  │
│  └──────┘       └────────┘  │
│                             │
│  💡 Keep device 6–12 inches │
│     from skin surface       │
│                             │
│ [Home] [Timer] [📊] [⚙️]   │
└─────────────────────────────┘
```

accessibilityIdentifier: `"timer_countdown_label"`, `"timer_pause_button"`, `"timer_stop_button"`, `"timer_progress_ring"`

### SC-30: Dashboard Screen

```
┌─────────────────────────────┐
│  Progress                   │
│                             │
│  ┌──────────┐ ┌──────────┐  │
│  │🔥 Streak │ │⏱️ Total  │  │  ← StatBadge
│  │  7 days  │ │ 2h 15min │  │
│  └──────────┘ └──────────┘  │
│                             │
│  Weekly Sessions            │  ← SwiftUI Charts (BarChart)
│  ┌─────────────────────┐    │
│  │ M T W T F S S       │    │
│  │ █ █   █ █ █ █       │    │
│  └─────────────────────┘    │
│                             │
│  Recent Sessions            │
│  ─────────────────────────  │
│  Today · Face & Skin · 10m  │  ← SessionRow
│  Yesterday · Joints · 15m   │
│  Mar 7 · Wound · 8m         │
│  [Free: 7 days / Upgrade]   │  ← Free limit banner
│                             │
│ [Home] [Timer] [📊] [⚙️]   │
└─────────────────────────────┘
```

accessibilityIdentifier: `"dashboard_streak_value"`, `"dashboard_total_time_value"`, `"dashboard_session_list"`, `"dashboard_upgrade_banner"`

---

## 6. Onboarding Flow

Source: [NNGroup: Mobile Onboarding UX](https://www.nngroup.com/articles/mobile-app-onboarding/) — 「Show value first, then ask for permissions. Never gate content before demonstrating value.」

```
App Launch (初回)
      │
      ▼
[SC-00] Welcome Screen
  - ロゴ + ヒーローコピー
  - [Get Started] タップ
      │
      ▼
[SC-01] Feature Highlight (3スライド)
  - Slide 1: "Science-Backed Protocols" (F-001)
  - Slide 2: "Background Timer" (F-002)
  - Slide 3: "Track Your Progress" (F-003, F-006)
  - [Next] / [Skip]
      │
      ▼
[SC-02] Notification Permission
  - メリット説明: "Get session reminders"
  - [Allow Notifications] → iOS permission dialog
  - [Skip for now] → スキップ可能
      │
      ▼
[SC-03] Paywall (ソフトペイウォール — Rule 20 MUST)
  - Annual plan デフォルト選択
  - [Start Free Trial] → RevenueCat purchase
  - [Maybe Later] → Main App へ (GhostButton 必須)
      │
      ▼
Main App (Tab Bar)
  - lr_onboarding_complete = true 保存
```

**オンボーディングルール（Rule 20 準拠）:**

| Rule | 実装 |
|------|------|
| ソフトペイウォール必須 | [Maybe Later] ボタン常時表示 |
| ATT 禁止 | SC-02 は通知許可のみ。ATT ダイアログなし |
| 自前 PaywallView 必須（RC-UI-library 不使用） | 自前 SwiftUI PaywallView を実装 |
| `Purchases.shared.purchase(package:)` | 購入ボタンタップ時に呼び出す |

---

## 7. Accessibility

Source: [Apple HIG: Accessibility](https://developer.apple.com/design/human-interface-guidelines/accessibility) — 「accessibilityIdentifier must be unique and stable across builds for UI test automation.」

| accessibilityIdentifier | Screen | Element | Maestro E2E 用途 |
|------------------------|--------|---------|-----------------|
| `welcome_get_started_button` | SC-00 | [Get Started] ボタン | onboarding.yaml |
| `onboarding_next_button` | SC-01 | [Next] ボタン | onboarding.yaml |
| `onboarding_skip_button` | SC-01 | [Skip] ボタン | onboarding.yaml |
| `notification_allow_button` | SC-02 | [Allow Notifications] | onboarding.yaml |
| `notification_skip_button` | SC-02 | [Skip for now] | onboarding.yaml |
| `paywall_maybe_later_button` | SC-03 | [Maybe Later] | payment-failure.yaml |
| `paywall_monthly_card` | SC-03 | Monthly プランカード | payment-monthly.yaml |
| `paywall_annual_card` | SC-03 | Annual プランカード | payment-annual.yaml |
| `paywall_subscribe_button` | SC-03 | [Start Free Trial] | payment-monthly.yaml |
| `home_protocol_list` | SC-10 | プロトコル一覧 ScrollView | home.yaml |
| `protocol_card_face` | SC-10 | Face & Skin カード | home.yaml |
| `protocol_card_joint` | SC-10 | Joints & Muscles カード | home.yaml |
| `protocol_card_wound` | SC-10 | Wound Healing カード | home.yaml |
| `protocol_card_back_locked` | SC-10 | Back & Spine (locked) | home.yaml |
| `protocol_card_fullbody_locked` | SC-10 | Full Body (locked) | home.yaml |
| `protocol_detail_start_button` | SC-11 | [Start Timer] ボタン | timer.yaml |
| `timer_countdown_label` | SC-20 | カウントダウン表示 | timer.yaml |
| `timer_pause_button` | SC-20 | [Pause] ボタン | timer.yaml |
| `timer_stop_button` | SC-20 | [Stop] ボタン | timer.yaml |
| `timer_progress_ring` | SC-20 | 円形プログレス | timer.yaml |
| `session_complete_save_button` | SC-21 | [Save Session] ボタン | timer.yaml |
| `dashboard_streak_value` | SC-30 | 連続日数テキスト | settings.yaml |
| `dashboard_total_time_value` | SC-30 | 累計時間テキスト | settings.yaml |
| `dashboard_session_list` | SC-30 | セッション履歴リスト | settings.yaml |
| `dashboard_upgrade_banner` | SC-30 | Upgrade バナー（Free時） | settings.yaml |
| `settings_notification_toggle` | SC-40 | 通知トグル | settings.yaml |
| `settings_upgrade_button` | SC-40 | [Upgrade to Premium] | settings.yaml |
| `settings_restore_button` | SC-40 | [Restore Purchases] | settings.yaml |

---

## 8. Interaction Patterns

| パターン | トリガー | 動作 |
|---------|---------|------|
| タップ | ProtocolCard | Protocol Detail (SC-11) へ NavigationPush |
| タップ | Locked ProtocolCard | Paywall Sheet 表示 |
| タップ | [Start Timer] | TimerView (SC-20) へ。TimerViewModel 開始 |
| タップ | [Pause] | タイマー一時停止。[Resume] 表示 |
| タップ | [Stop] | 確認アラート → Session 保存 → SC-21 |
| タップ | [Maybe Later] | Paywall dismiss。Main App 表示 |
| タップ | [Upgrade to Premium] | Paywall Sheet 表示 |
| タップ | [Restore Purchases] | RevenueCat restorePurchases() |
| タップ | Locked item in Dashboard | Free ユーザーへの Upgrade バナー表示 |
| スワイプ | Onboarding スライド | 次スライドへ |

---

## 9. Localization Notes

Source: [Apple HIG: Localization](https://developer.apple.com/design/human-interface-guidelines/localization) — 「Design for text expansion. Japanese text is typically 10–30% shorter but requires larger line height.」

| 言語 | コード | 文字特性 | レイアウト考慮 |
|------|-------|---------|-------------|
| English (US) | en-US | 単語区切り。長い単語は改行 | ボタン幅 = コンテンツ依存 |
| Japanese | ja | 文字詰め不要。漢字で短くなる場合多い | 行高 = 1.4〜1.6 em 推奨 |

**翻訳対象:**

| Key | en-US | ja |
|-----|-------|-----|
| `btn.get_started` | Get Started | はじめる |
| `btn.maybe_later` | Maybe Later | あとで |
| `btn.start_trial` | Start Free Trial | 無料トライアルを開始 |
| `btn.start_timer` | Start Timer | タイマー開始 |
| `btn.pause` | Pause | 一時停止 |
| `btn.stop` | Stop | 停止 |
| `btn.upgrade` | Upgrade to Premium | プレミアムにアップグレード |
| `btn.restore` | Restore Purchases | 購入を復元 |
| `label.streak` | day streak | 日連続 |
| `label.total_time` | Total Time | 累計時間 |
| `paywall.headline` | Start Your Glow Journey | グロージャーニーを始めよう |
| `paywall.best_value` | Best Value | ベストバリュー |
| `paywall.save` | Save 50% | 50%お得 |
| `notification.complete` | Session complete! Great work. | セッション完了！よくできました。 |
| `notification.reminder` | Time for your red light session. | 赤色光セッションの時間です。 |
