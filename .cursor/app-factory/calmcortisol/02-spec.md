# CalmCortisol — App Spec

## 基本情報

| フィールド | 値 |
|-----------|-----|
| app_name | CalmCortisol |
| bundle_id | com.anicca.calmcortisol |
| version | 1.0.0 |
| output_dir | /Users/anicca/anicca-project/apps/calmcortisol |
| price_monthly_usd | 9.99 |
| price_annual_usd | 49.99 |
| localization | os_language |
| supported_locales | en, ja |
| concept | AI-driven cortisol stress relief via 60-second breathing sessions with proactive push notifications |

---

## 課金

| フィールド | 値 |
|-----------|-----|
| paywall.cta_text_en | Start 7-Day Free Trial |
| paywall.cta_text_ja | 7日間無料トライアルを始める |
| paywall.monthly_product_id | com.anicca.calmcortisol.premium.monthly |
| paywall.annual_product_id | com.anicca.calmcortisol.premium.yearly |
| free_limit | 3 sessions/day, rule-based breathing only |
| pro_features | Unlimited sessions, AI-recommended breathing type, sleep pre-session, cortisol trend history |

---

## App Store メタデータ

### 英語 (en-US)

| フィールド | 値 |
|-----------|-----|
| title_en | CalmCortisol: Stress Relief |
| subtitle_en | 60-sec Breathing & Cortisol Reset |
| description_en | Stressed? Anxious? Can't sleep? CalmCortisol uses AI to detect when your cortisol is spiking — and steps in before you spiral.\n\nScience-backed breathing exercises reset your nervous system in 60 seconds. No meditation experience needed.\n\n✓ AI proactive push — the app checks on YOU, not the other way around\n✓ Box breathing, 4-7-8, physiological sigh — guided with calming animations\n✓ Cortisol trend tracking — see patterns in your stress over time (Pro)\n✓ Sleep pre-session — wind down with a 5-min session before bed (Pro)\n✓ No streaks, no guilt — failure is expected and designed for\n\nPro Plan: Unlimited sessions + AI breathing recommendation + sleep pre-session + full history\n\nTerms of Use: https://www.apple.com/legal/internet-services/itunes/dev/stdeula/ |
| keywords_en | stress relief,cortisol,breathing exercise,anxiety,calm,nervous system,box breathing,4-7-8,sleep,mindfulness |

### 日本語 (ja)

| フィールド | 値 |
|-----------|-----|
| title_ja | CalmCortisol: ストレス解消 |
| subtitle_ja | 60秒呼吸法でコルチゾールリセット |
| description_ja | ストレス、不安、眠れない夜。CalmCortisolはAIがコルチゾールが高まる瞬間を検知し、あなたが消耗する前に先手で介入します。\n\n科学的根拠のある呼吸法で、神経系を60秒でリセット。瞑想の経験は不要です。\n\n✓ AIプロアクティブ通知 — アプリがあなたの状態を見て先にアプローチ\n✓ ボックス呼吸・4-7-8・生理的ため息 — 落ち着くアニメーションでガイド\n✓ コルチゾール傾向グラフ — ストレスのパターンを把握（Pro）\n✓ 就寝前セッション — 5分で緊張をほぐして眠りに入る（Pro）\n✓ ストリークなし、自責なし — 失敗を前提にした設計\n\nProプラン: 無制限セッション + AI呼吸法推薦 + 就寝前セッション + 全履歴\n\n利用規約: https://www.apple.com/legal/internet-services/itunes/dev/stdeula/ |
| keywords_ja | ストレス解消,コルチゾール,呼吸法,不安,リラックス,神経系,ボックス呼吸,睡眠,マインドフルネス,瞑想 |

---

## URLs

| フィールド | 値 |
|-----------|-----|
| urls.privacy_en | https://aniccaai.com/calmcortisol/privacy/en |
| urls.privacy_ja | https://aniccaai.com/calmcortisol/privacy/ja |
| urls.terms | https://www.apple.com/legal/internet-services/itunes/dev/stdeula/ |
| urls.landing | https://aniccaai.com/calmcortisol |

---

## 画面構成 (screens)

### 1. Onboarding

| 画面 | 説明 | accessibilityIdentifier |
|------|------|------------------------|
| Welcome | タイトル + 一言キャッチ + 「始める」ボタン | onboarding-welcome-cta |
| Pain Selection | 「今一番の悩みは？」選択肢: 仕事のストレス/眠れない/不安・パニック/怒り・イライラ | pain-option-work, pain-option-sleep, pain-option-anxiety, pain-option-anger |
| Demo Session | 呼吸アニメーション体験（30秒） + 「気持ちよかった？」フィードバック | demo-session-start, demo-feedback-yes, demo-feedback-no |
| Notification Permission | 「AIがあなたを見守ります」通知許可 | onboarding-notifications-allow |
| Paywall | 7日トライアル提案（通知許可後に表示） | paywall_plan_monthly, paywall_plan_yearly, paywall_cta, paywall_skip, paywall_restore |

### 2. Main (Dashboard)

| 要素 | 説明 | accessibilityIdentifier |
|------|------|------------------------|
| コルチゾール推定バー | 時刻・過去パターンから推定（Free: 今日のみ / Pro: 7日グラフ） | cortisol-bar |
| 今日のミッション | 「今日3回セッションしよう」 | daily-mission-card |
| クイックスタートボタン | 「60秒セッションを始める」 | quick-start-cta |
| 履歴カード | 今日のセッション回数 | session-history-card |

### 3. セッション画面

| 要素 | 説明 |
|------|------|
| 呼吸タイプ選択 | Box Breathing / 4-7-8 / Physiological Sigh（Pro: AI推薦あり） |
| 呼吸アニメーション | 円が膨らむ/縮むアニメーション + 音声ガイド（テキスト） |
| タイマー | 60秒 / 3分 / 5分 |
| 完了後フィードバック | 「どう感じた？」👍/👎 |

### 4. Paywall

| 要素 | 値 |
|------|-----|
| 見出し(en) | Unlimited Calm, Zero Guilt |
| 見出し(ja) | 無制限の安らぎ、自責ゼロ |
| Free tier 説明 | 3 sessions/day, rule-based breathing |
| Pro tier 説明 | Unlimited + AI recommendation + sleep pre-session |
| 月額 | $9.99/month |
| 年額 | $49.99/year (save 58%) |
| CTA | 7-day free trial |

### 5. Settings

| 要素 | 説明 |
|------|------|
| Privacy Policy | OS言語に応じて privacy_en / privacy_ja を開く |
| Terms of Use | Apple EULA URL |
| Restore Purchase | RevenueCat restorePurchases() |
| バージョン情報 | アプリバージョン表示 |

---

## 技術スタック

| 項目 | 値 |
|------|-----|
| iOS Target | iOS 15.0+ |
| UI Framework | SwiftUI |
| Architecture | MVC (シンプル) |
| 課金 | RevenueCat SDK |
| 分析 | Mixpanel SDK |
| 通知 | UserNotifications (APNs) |
| ビルド | Fastlane |

---

## RevenueCat 設定

| 項目 | 値 |
|------|-----|
| Offering identifier | default |
| Monthly package | $rc_monthly → com.anicca.calmcortisol.premium.monthly |
| Annual package | $rc_annual → com.anicca.calmcortisol.premium.yearly |

---

## Mixpanel イベント（必須）

| イベント | プロパティ |
|---------|-----------|
| paywall_viewed | offering_id |
| session_started | breathing_type, duration_sec |
| session_completed | breathing_type, duration_sec, felt_better |
| onboarding_completed | pain_type |
| subscription_started | product_id, offering_id |
