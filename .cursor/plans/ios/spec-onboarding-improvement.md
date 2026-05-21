# Spec: Anicca オンボーディング改善

> **目的:** ベストプラクティスに100%準拠したオンボーディング+ペイウォールへの改修
> **参照:** `.cursor/plans/ios/onboarding-paywall-best-practices.md`
> **ブランチ:** `feature/onboarding-v2`（dev から作成）
> **最終更新:** 2026-03-10

---

## 1. 現状 vs 改善後

### 現状フロー（4ステップ）

```
Welcome → Struggles → LiveDemo → Notifications → [Paywall: single fullScreenCover]
```

**問題点:**

| # | 問題 | 影響 |
|---|------|------|
| 1 | ステップ数が4しかない | サンクコスト・コミットメント不足 → ペイウォール到達時の課金意欲が低い |
| 2 | パーソナライゼーションがない | 悩みを選んでも結果が表示されない → 「理解された」感がゼロ |
| 3 | ペイウォールが単一画面 | RevenueCatデフォルト → 信頼構築なし → トライアル開始率が低い |
| 4 | プログレスバーなし | 完了予測不能 → 離脱率上昇 |
| 5 | ゴール設定がない | コミットメント・一貫性の心理原則を活用していない |
| 6 | ソーシャルプルーフが弱い | Welcome に「Join thousands」のみ。具体的数字・パーソナライズなし |
| 7 | 通知許可の動機付けが弱い | なぜ通知が必要かの価値説明が不十分 |
| 8 | Drawer Offer なし | ペイウォール離脱ユーザーの回収手段がない |

### 改善後フロー（12ステップ + 3ステップペイウォール）

```
┌─ PHASE 1: HOOK ──────────────────────────────────────────────────────┐
│                                                                       │
│  [1] Welcome          Dream Outcome + ソーシャルプルーフ               │
│  [2] Struggles         「何に苦しんでる？」チップ選択（既存改善）       │
│  [3] Struggle Depth    選んだ悩みの深掘り（1問：頻度/深刻度）          │
│                                                                       │
├─ PHASE 2: INVEST ────────────────────────────────────────────────────┤
│                                                                       │
│  [4] Goals             「どうなりたい？」チップ選択                    │
│  [5] Personalized      「あなたの分析結果」 + パーソナライズ統計       │
│      Insight                                                          │
│                                                                       │
├─ PHASE 3: VALUE DEMO ────────────────────────────────────────────────┤
│                                                                       │
│  [6] Value Prop        プログラムプレビュー（7日間の旅程）             │
│  [7] Live Demo         Nudge体験（既存改善）                          │
│                                                                       │
├─ PHASE 4: PERMISSION ────────────────────────────────────────────────┤
│                                                                       │
│  [8] Notifications     通知許可（価値を理解した上で）                  │
│                                                                       │
├─ PHASE 5: CONVERT (3-Step Paywall) ──────────────────────────────────┤
│                                                                       │
│  [9] Risk-Free Primer  「まず無料で試してください」                    │
│  [10] Trial Timeline   Blinkistタイムライン（Day1→Day5通知→Day7課金） │
│  [11] Plan Selection   プラン選択 + CTA                               │
│  [12] [Drawer Offer]     ×押下時のみ: 別オファー                        │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
```

---

## 2. ファイル変更マップ

### 新規作成

| ファイル | 役割 |
|---------|------|
| `Onboarding/OnboardingProgressBar.swift` | プログレスバーコンポーネント |
| `Onboarding/StruggleDepthStepView.swift` | 悩み深掘りステップ |
| `Onboarding/GoalsStepView.swift` | ゴール設定ステップ |
| `Onboarding/PersonalizedInsightStepView.swift` | パーソナライズ分析結果 |
| `Onboarding/ValuePropStepView.swift` | 7日間プログラムプレビュー |
| `Onboarding/PaywallPrimerStepView.swift` | Risk-Free Primer画面 |
| `Onboarding/TrialTimelineStepView.swift` | Blinkistタイムライン画面 |
| `Onboarding/PlanSelectionStepView.swift` | プラン選択画面（RevenueCat統合） |
| `Onboarding/DrawerOfferView.swift` | Drawer Offer モーダル |

### 既存変更

| ファイル | 変更内容 |
|---------|---------|
| `Onboarding/OnboardingStep.swift` | enum を12ステップに拡張 |
| `Onboarding/OnboardingFlowView.swift` | フロー制御を12ステップ対応に。ペイウォールを3ステップシーケンスに変更 |
| `Onboarding/WelcomeStepView.swift` | コピー改善 + ソーシャルプルーフ強化 |
| `Onboarding/StrugglesStepView.swift` | スキップボタン削除 + コピー改善 |
| `Onboarding/DemoNudgeStepView.swift` | コピー改善 + 自動遷移改善 |
| `Onboarding/NotificationPermissionStepView.swift` | コピー改善 + 価値説明追加 |
| `Resources/en.lproj/Localizable.strings` | 新キー追加 + 既存キー改善 |
| `Resources/ja.lproj/Localizable.strings` | 同上（日本語） |
| `Models/UserProfile.swift`（想定） | goals プロパティ追加 |

### 削除

| ファイル | 理由 |
|---------|------|
| `Onboarding/ValueStepView.swift` | ValuePropStepView で置き換え（現在未使用、enum から除外済み） |
| `Onboarding/ATTPermissionStepView.swift` | 既に enum から除外済み。ファイル削除 |

---

## 3. 各ステップの詳細スペック

### Step 1: Welcome（既存改善）

**ファイル:** `WelcomeStepView.swift`

| 要素 | 現在 | 改善後 |
|------|------|--------|
| ソーシャルプルーフ | 「Join thousands finding peace」 | 「⭐ 4.9 · 10,000+ people finding inner peace」 |
| タイトル | 「Welcome to Anicca」 | 「Break free from the patterns that hold you back」 |
| サブタイトルL1 | 「Anicca reaches out to you」 | 「Anicca reaches out at the moments you struggle most」 |
| サブタイトルL2 | 「at the moments you struggle most.」 | 削除（L1に統合） |
| CTA | 「Get Started」 | 「Get Started」（維持） |
| Sign In with Apple | 表示 | 維持（既存ユーザー復元用） |
| **追加** | - | プログレスバー（上部、20%開始） |

**EN:**
```
"onboarding_welcome_social_proof" = "⭐ 4.9 · 10,000+ people finding inner peace";
"onboarding_welcome_title" = "Break free from\nthe patterns that\nhold you back";
"onboarding_welcome_subtitle_line1" = "Anicca reaches out at the moments you struggle most.";
```

**JA:**
```
"onboarding_welcome_social_proof" = "⭐ 4.9 · 10,000人以上が内なる安らぎを実感";
"onboarding_welcome_title" = "あなたを縛る\nパターンから\n自由になろう";
"onboarding_welcome_subtitle_line1" = "一番つらい瞬間に、アニッチャが寄り添います。";
```

### Step 2: Struggles（既存改善）

**ファイル:** `StrugglesStepView.swift`

| 要素 | 現在 | 改善後 |
|------|------|--------|
| タイトル | 「What are you struggling with now?」 | 「What's holding you back?」 |
| サブタイトル | 「Select all that apply.」 | 「Select all that apply — we'll personalize your experience」 |
| スキップボタン | あり | **削除**（選択必須化） |
| 次へボタン | 「Next」（disabled when empty） | 「Continue」（disabled when empty） |
| プログレスバー | なし | 表示 |

**EN:**
```
"onboarding_struggles_title" = "What's holding you back?";
"onboarding_struggles_subtitle" = "Select all that apply — we'll personalize your experience.";
```

**JA:**
```
"onboarding_struggles_title" = "何があなたを止めていますか？";
"onboarding_struggles_subtitle" = "当てはまるものを全て選んでください — あなた専用に調整します。";
```

### Step 3: Struggle Depth（新規）

**ファイル:** `StruggleDepthStepView.swift`

| 要素 | 内容 |
|------|------|
| タイトル | 「How often does this affect you?」 |
| 表示条件 | 最初に選んだ悩み1つについてのみ質問 |
| 選択肢 | 「Every day」「Several times a week」「Once a week」「Occasionally」 |
| UIパターン | 縦並びボタン（1タップで自動遷移） |
| プログレスバー | 表示 |

**EN:**
```
"onboarding_depth_title" = "How often does this affect you?";
"onboarding_depth_daily" = "Every day";
"onboarding_depth_several" = "Several times a week";
"onboarding_depth_weekly" = "Once a week";
"onboarding_depth_occasionally" = "Occasionally";
```

**JA:**
```
"onboarding_depth_title" = "どのくらいの頻度で影響を受けていますか？";
"onboarding_depth_daily" = "毎日";
"onboarding_depth_several" = "週に数回";
"onboarding_depth_weekly" = "週に1回";
"onboarding_depth_occasionally" = "たまに";
```

### Step 4: Goals（新規）

**ファイル:** `GoalsStepView.swift`

| 要素 | 内容 |
|------|------|
| タイトル | 「What does your best self look like?」 |
| サブタイトル | 「Choose what matters most to you」 |
| UIパターン | チップ選択（StrugglesStepViewと同じUI） |
| 選択肢 | `better_sleep`, `emotional_calm`, `less_screen_time`, `more_discipline`, `self_acceptance`, `deeper_focus`, `healthier_habits`, `inner_peace` |
| プログレスバー | 表示 |

**EN:**
```
"onboarding_goals_title" = "What does your best self look like?";
"onboarding_goals_subtitle" = "Choose what matters most to you.";
"goal_better_sleep" = "Better Sleep";
"goal_emotional_calm" = "Emotional Calm";
"goal_less_screen_time" = "Less Screen Time";
"goal_more_discipline" = "More Discipline";
"goal_self_acceptance" = "Self-Acceptance";
"goal_deeper_focus" = "Deeper Focus";
"goal_healthier_habits" = "Healthier Habits";
"goal_inner_peace" = "Inner Peace";
```

**JA:**
```
"onboarding_goals_title" = "最高の自分は、どんな姿ですか？";
"onboarding_goals_subtitle" = "大切なものを選んでください。";
"goal_better_sleep" = "良い睡眠";
"goal_emotional_calm" = "心の穏やかさ";
"goal_less_screen_time" = "スクリーン時間の削減";
"goal_more_discipline" = "自律心";
"goal_self_acceptance" = "自己受容";
"goal_deeper_focus" = "深い集中力";
"goal_healthier_habits" = "健康的な習慣";
"goal_inner_peace" = "内なる平和";
```

### Step 5: Personalized Insight（新規）

**ファイル:** `PersonalizedInsightStepView.swift`

| 要素 | 内容 |
|------|------|
| タイトル | 「Based on your answers」 |
| 内容 | 選んだ悩みとゴールに基づくパーソナライズメッセージ |
| 統計表示 | 「81% of people with similar struggles improved within 30 days」 |
| UIパターン | カード形式。悩み→ゴールの矢印図 + 統計 |
| CTA | 「See Your Plan」 |
| プログレスバー | 表示 |

**EN:**
```
"onboarding_insight_title" = "Based on your answers";
"onboarding_insight_stat" = "81% of people with similar struggles improved within 30 days";
"onboarding_insight_message" = "Anicca will create a personalized path from %@ to %@.";
"onboarding_insight_cta" = "See Your Plan";
```

**JA:**
```
"onboarding_insight_title" = "あなたの回答に基づいて";
"onboarding_insight_stat" = "同じ悩みを持つ81%の人が30日以内に改善しました";
"onboarding_insight_message" = "アニッチャが%@から%@への道を作ります。";
"onboarding_insight_cta" = "あなたのプランを見る";
```

### Step 6: Value Prop — 7日間プログラムプレビュー（新規）

**ファイル:** `ValuePropStepView.swift`

| 要素 | 内容 |
|------|------|
| タイトル | 「Your 7-Day Journey」 |
| UIパターン | 縦タイムライン（Day 1〜Day 7） |
| Day 1 | 「Awareness — Notice your patterns」 |
| Day 2 | 「Understanding — Learn your triggers」 |
| Day 3 | 「First Shift — Replace one habit」 |
| Day 4 | 「Deepening — Mindful moments」 |
| Day 5 | 「Strength — Handle urges differently」 |
| Day 6 | 「Integration — New daily rhythm」 |
| Day 7 | 「Reflection — See how far you've come」 |
| CTA | 「Start My Journey」 |
| プログレスバー | 表示 |

**EN/JA:** 全7日分のローカライズキーを作成（省略）

### Step 7: Live Demo（既存改善）

**ファイル:** `DemoNudgeStepView.swift`

| 要素 | 現在 | 改善後 |
|------|------|--------|
| タイトル | 「Experience Your First Nudge」 | 維持 |
| サブタイトル | 「See how Anicca gently nudges...」 | 「This is what it feels like when Anicca reaches out to you」 |
| ボタン | 「Receive a Nudge」 | 「Try It Now」 |
| **追加** | - | カード dismiss 後に「That's what Anicca does — at the moment you need it most.」テキスト表示 |
| プログレスバー | なし | 表示 |

### Step 8: Notifications（既存改善）

**ファイル:** `NotificationPermissionStepView.swift`

| 要素 | 現在 | 改善後 |
|------|------|--------|
| タイトル | 「Notifications」 | 「Stay on track」 |
| 説明 | 長文 | 「Anicca sends gentle reminders exactly when you need them. Without notifications, Anicca can't reach you.」 |
| **追加** | - | 3つのミニカード: 🌅 Morning nudge / 💭 Midday check-in / 🌙 Evening reflection |
| CTA | 「Allow notifications」 | 「Allow Notifications」 |
| プログレスバー | なし | 表示 |

### Step 9: Risk-Free Primer（新規 — ペイウォールStep 1）

**ファイル:** `PaywallPrimerStepView.swift`

| 要素 | 内容 |
|------|------|
| タイトル | 「We want you to try Anicca for free」 |
| サブタイトル | 「Your personalized plan is ready. Experience the full journey risk-free.」 |
| ビジュアル | チェックマーク3つ: ✅ Full access to all features / ✅ Personalized nudges / ✅ Cancel anytime |
| CTA | 「Continue」 |
| ×ボタン | **なし**（この画面からは戻れない） |
| プログレスバー | **非表示** |

### Step 10: Trial Timeline（新規 — ペイウォールStep 2）

**ファイル:** `TrialTimelineStepView.swift`

| 要素 | 内容 |
|------|------|
| タイトル | 「Your free trial timeline」 |
| UIパターン | Blinkist式タイムライン |
| Day 1 | 🟢 「Today — Start exploring Anicca」 |
| Day 5 | 🔔 「Day 5 — We'll send you a reminder」 |
| Day 7 | 💳 「Day 7 — Your trial ends. You decide.」 |
| サブテキスト | 「We'll remind you before you're charged. No surprises.」 |
| CTA | 「Continue」 |
| プログレスバー | **非表示** |

### Step 11: Plan Selection（新規 — ペイウォールStep 3）

**ファイル:** `PlanSelectionStepView.swift`

| 要素 | 内容 |
|------|------|
| タイトル | 「Choose your plan」 |
| **年額カード** | 「Annual — $49.99/year」+ 「$0.96/week」+ 「Most Popular」バッジ + 「Save 58%」 |
| **月額カード** | 「Monthly — $9.99/month」 |
| 年額がデフォルト選択 | はい |
| ソーシャルプルーフ | 「⭐ 4.9 · Trusted by 10,000+ users」（CTA直上） |
| CTA | 「Start Free Trial」（年額選択時）/ 「Subscribe」（月額選択時） |
| トラストテキスト | 「No commitment. Cancel anytime.」（CTA直下） |
| ×ボタン | あり（右上） |
| プログレスバー | **非表示** |

**RevenueCat統合:**
- `SubscriptionManager.shared` から offering を取得
- `Purchases.shared.purchase(package:)` で購入実行
- 既存の `handlePaywallSuccess` / `handlePaywallDismissedAsFree` を再利用

### Step 12: Drawer Offer（×ボタン押下時のみ）

**ファイル:** `DrawerOfferView.swift`

> **注意:** Drawer Offer（モーダル）は Apple Guideline 5.6 でリジェクト事例あり（RevenueCat 2026/03）。
> 代わりに Drawer戦略（自然なスライドアップ）を採用。

| 要素 | 内容 |
|------|------|
| 表示条件 | PlanSelection の×ボタン押下時 |
| UIパターン | 画面下部からスライドアップ（`.sheet` ではなくカスタムDrawer） |
| タイトル | 「Not ready for a year?」 |
| サブタイトル | 年額を週額に換算: 「That's just $0.96/week — less than a cup of coffee」 |
| CTA | 「Start Free Trial」 |
| Skip | 「Maybe later」（フリープランで完了） |
| **禁止** | 大幅値引き表示（ブランド価値低下防止。値引きはイベント限定） |

---

## 4. OnboardingStep enum 変更

**ファイル:** `OnboardingStep.swift`

```swift
enum OnboardingStep: Int, CaseIterable {
    case welcome           // 0
    case struggles         // 1
    case struggleDepth     // 2
    case goals             // 3
    case personalizedInsight // 4
    case valueProp         // 5
    case liveDemo          // 6
    case notifications     // 7
    // ペイウォールステップはenum外で管理（PaywallStep enum）
}

enum PaywallStep: Int {
    case primer            // 0
    case timeline          // 1
    case planSelection     // 2
}
```

---

## 5. OnboardingFlowView 変更

**ファイル:** `OnboardingFlowView.swift`

主要変更:
1. `switch step` を12ケース対応に
2. `OnboardingProgressBar` を全ステップ（ペイウォール除く）で表示
3. ペイウォール部分を `fullScreenCover` から画面内遷移に変更（3ステップシーケンス）
4. Drawer Offer を `sheet` で表示
5. `advance()` メソッドを12ステップ対応に

---

## 6. プログレスバー仕様

**ファイル:** `OnboardingProgressBar.swift`

| 属性 | 値 |
|------|-----|
| 位置 | SafeArea top、8px padding |
| 高さ | 4px |
| 角丸 | 2px |
| 色 | `AppTheme.Colors.accent` |
| 背景色 | `AppTheme.Colors.label.opacity(0.1)` |
| 初期値 | 20%（エンダウド・プログレス効果） |
| ステップ計算 | `(0.2 + 0.8 * (currentStep / totalSteps))` |
| アニメーション | `.easeInOut(duration: 0.4)` |
| 表示条件 | Step 1-8（ペイウォールでは非表示） |

---

## 7. アナリティクスイベント

| イベント | タイミング |
|---------|-----------|
| `onboarding_started` | Step 1 表示 |
| `onboarding_welcome_completed` | Step 1 → 2 |
| `onboarding_struggles_completed` | Step 2 → 3 |
| `onboarding_struggle_depth_completed` | Step 3 → 4 |
| `onboarding_goals_completed` | Step 4 → 5 |
| `onboarding_insight_viewed` | Step 5 表示 |
| `onboarding_value_prop_viewed` | Step 6 表示 |
| `onboarding_live_demo_completed` | Step 7 → 8 |
| `onboarding_notifications_completed` | Step 8 → ペイウォール |
| `onboarding_paywall_primer_viewed` | Paywall Step 1 表示 |
| `onboarding_paywall_timeline_viewed` | Paywall Step 2 表示 |
| `onboarding_paywall_plan_viewed` | Paywall Step 3 表示 |
| `onboarding_paywall_purchased` | 購入完了 |
| `onboarding_paywall_dismissed_free` | ×ボタン → フリー |
| `onboarding_drawer_offer_shown` | Drawer Offer 表示 |
| `onboarding_drawer_offer_accepted` | Drawer Offer 受諾 |
| `onboarding_drawer_offer_declined` | Drawer Offer 拒否 |
| `onboarding_completed` | 全フロー完了 |

---

## 8. データモデル変更

### UserProfile に追加

```swift
// 既存
var problems: [String]  // struggles

// 追加
var goals: [String]           // ゴール選択
var struggleFrequency: String? // 頻度（"daily", "several", "weekly", "occasionally"）
```

### API同期

- `goals` と `struggleFrequency` を `updateUserProfile` 時にAPIへ送信
- バックエンド: `user_profiles` テーブルに `goals TEXT[]`, `struggle_frequency TEXT` カラム追加

---

## 9. マイグレーション戦略

| ユーザー種別 | 対応 |
|-------------|------|
| **新規ユーザー** | 新フロー（12ステップ）を通る |
| **既存ユーザー（オンボーディング完了済み）** | 何も変わらない |
| **既存ユーザー（オンボーディング途中）** | `migratedFromLegacyRawValue` で最寄りのステップにマッピング |

マイグレーションマッピング:
```swift
// 旧 rawValue → 新 rawValue
// 0 (welcome) → 0 (welcome)
// 1 (struggles) → 1 (struggles)
// 2 (liveDemo) → 6 (liveDemo)
// 3 (notifications) → 7 (notifications)
```

---

## 10. テスト計画

### ユニットテスト

| テスト | 内容 |
|--------|------|
| `OnboardingStepTests` | enum 遷移ロジック、マイグレーションマッピング |
| `PersonalizedInsightTests` | 悩み+ゴール → メッセージ生成ロジック |
| `PaywallStepTests` | 3ステップシーケンスの遷移 |
| `ExitOfferTests` | 表示条件、アクション |

### E2E（Maestro）

| フロー | 内容 |
|--------|------|
| `onboarding_full_flow.yaml` | 12ステップ完走 → 購入 |
| `onboarding_free_user.yaml` | 12ステップ → ペイウォール×→ Drawer Offer → Maybe later |
| `onboarding_existing_user.yaml` | Sign In with Apple → スキップ |
| `onboarding_drawer_offer.yaml` | ペイウォール× → Drawer Offer → 3日トライアル |

---

## 11. 実装順序

| Phase | 内容 | 依存 |
|-------|------|------|
| **Phase A** | `OnboardingStep` enum 拡張 + `OnboardingProgressBar` + `OnboardingFlowView` スケルトン | なし |
| **Phase B** | 新規ステップView 5つ（StruggleDepth, Goals, PersonalizedInsight, ValueProp）| Phase A |
| **Phase C** | 3ステップペイウォール（Primer, Timeline, PlanSelection）+ Drawer Offer | Phase A |
| **Phase D** | 既存ステップ改善（Welcome, Struggles, Demo, Notifications コピー変更）| Phase A |
| **Phase E** | ローカライズ（EN/JA全キー） | Phase B, C, D |
| **Phase F** | アナリティクス全イベント追加 | Phase B, C, D |
| **Phase G** | マイグレーション + ユニットテスト | Phase A |
| **Phase H** | E2Eテスト（Maestro） | Phase B, C, D, E |
| **Phase I** | バックエンド（goals, struggleFrequency カラム追加 + API更新）| Phase B |

---

## 12. 見送り事項（v2以降）

| 項目 | 理由 |
|------|------|
| 名前収集ステップ | 最小限の追加でまず効果検証 |
| Demand Score ベースのパーソナライズペイウォール | Superwall SDK統合が必要 |
| Web Purchase Button | Apple 30%回避は別施策 |
| A/Bテスト基盤 | まずv1の結果を見てから |
