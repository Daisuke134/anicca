# BreathCalm — spec.md

Generated: 2026-02-24 (Phase 0.5 output)

---

## 基本情報

| フィールド | 値 |
|-----------|-----|
| **app_name** | BreathCalm |
| **bundle_id** | `com.aniccaai.breathcalm` |
| **version** | 1.0.0 |
| **output_dir** | `/Users/cbns03/Downloads/anicca-project/daily-apps/breath-calm` |
| **sku** | `breathcalm-001` |
| **price_monthly_usd** | 9.99 |
| **price_annual_usd** | 49.99 |
| **localization** | os_language |
| **supported_locales** | `["en", "ja"]` |

---

## コンセプト

**concept**: 9Dバイノーラルビーツ付きガイド呼吸法で、6分間で不安をリセットするiOSアプリ。

---

## Paywall

| フィールド | 値 |
|-----------|-----|
| **cta_text_en** | Start Your Free Trial |
| **cta_text_ja** | 無料トライアルを始める |

### Paywall コピー（EN）

**Headline**: Reset Anxiety in 6 Minutes
**Subheadline**: 9D Binaural Breathwork That Actually Works
**Features**:
- ✓ 9D Binaural Beat sessions (4-7-8, Box, Coherent Breathing)
- ✓ Emergency SOS mode for instant relief
- ✓ Mood score tracking (before & after)
- ✓ Streak tracker to build daily habit
- ✓ Japanese Walking breathing guide

### Paywall コピー（JA）

**Headline**: 6分で不安をリセット
**Subheadline**: 全身に効く9Dバイノーラル呼吸法
**Features**:
- ✓ 9Dバイノーラルビーツ付き呼吸セッション
- ✓ 緊急SOSモード（今すぐ不安を止める）
- ✓ セッション前後の気分スコア記録
- ✓ 連続記録でモチベ維持
- ✓ 日本式ウォーキング呼吸ガイド

---

## App Store メタデータ

### 英語 (en-US)

| フィールド | 値 |
|-----------|-----|
| **title_en** | BreathCalm: 9D Breathwork |
| **subtitle_en** | Reset Anxiety in 6 Minutes |
| **description_en** | Feeling anxious? BreathCalm uses 9D binaural beats combined with guided breathing techniques to help you reset in just 6 minutes. No medication. No complicated routines. Just breathe.\n\nFEATURES:\n• 9D Binaural Breathwork: 4-7-8, Box Breathing, Coherent Breathing with immersive binaural audio\n• SOS Emergency Mode: One tap for instant anxiety relief\n• Mood Tracking: See exactly how much better you feel after each session\n• Daily Streaks: Build your breathwork habit without guilt\n• Japanese Walking Guide: Breathe while you walk\n\nJoin thousands who've discovered that 6 minutes of intentional breathing changes everything. |
| **keywords_en** | breathwork,anxiety relief,binaural beats,9D breathing,calm,stress relief,panic attack,meditation alternative |

### 日本語 (ja)

| フィールド | 値 |
|-----------|-----|
| **title_ja** | BreathCalm: 9D呼吸法 |
| **subtitle_ja** | 6分で不安をリセット |
| **description_ja** | 不安を感じていますか？BreathCalmは9Dバイノーラルビーツとガイド付き呼吸法を組み合わせ、たった6分で心を落ち着かせます。薬不要。複雑なルーティン不要。ただ、呼吸するだけ。\n\n機能:\n• 9Dバイノーラル呼吸法：4-7-8、ボックスブリーシング、コヒーレント呼吸\n• 緊急SOSモード：ワンタップで即座に不安を解消\n• 気分スコア記録：セッション前後の効果を可視化\n• 連続記録：罪悪感なく続けられる習慣設計\n• 日本式ウォーキングガイド：歩きながら呼吸\n\n6分の呼吸が全てを変えることに気づいた人たちに加わりましょう。 |
| **keywords_ja** | 呼吸法,不安解消,バイノーラルビーツ,瞑想,ストレス解消,パニック,リラックス,9D |

---

## URLs

| URL | 値 |
|-----|-----|
| **privacy_en** | `https://aniccaai.com/breath-calm/privacy/en` |
| **privacy_ja** | `https://aniccaai.com/breath-calm/privacy/ja` |
| **terms** | `https://www.apple.com/legal/internet-services/itunes/dev/stdeula/` |
| **landing** | `https://aniccaai.com/breath-calm` |

---

## 画面構成

### Onboarding (3画面)

| 画面 | accessibilityIdentifier | 内容 |
|------|------------------------|------|
| Welcome | `onboarding-welcome-cta` | 「6分で不安をリセット」+ 始めるボタン |
| Anxiety Check | `onboarding-anxiety-level` | 今の不安レベルを選択 (高/中/低) |
| Notification Permission | `onboarding-notifications-allow` | 「毎日の呼吸リマインダー」許可 |

### Main画面 (TabBar: Home / History / Settings)

**Home Tab**:
- 今日のセッション推奨 (4-7-8 / ボックス / コヒーレント)
- SOSボタン (大きく目立つ)
- 本日のストリーク

**Session画面** (Homeからタップ):
- 開始前: 気分スコア入力 (0-10)
- セッション中: 呼吸ガイドアニメーション + 残り時間
- 終了後: 気分スコア入力 → 前後比較表示

**History Tab**:
- セッション履歴 (日付 / 種類 / 前後スコア)
- ストリークカレンダー

**Settings Tab**:
- 通知設定
- Privacy Policy (`urls.privacy_en` / `urls.privacy_ja` — OS言語で切替)
- Terms of Use (`urls.terms`)
- Restore Purchases
- サブスクリプション管理

### Paywall画面

- `paywall_plan_monthly` / `paywall_plan_yearly`
- `paywall_cta`
- `paywall_skip`
- `paywall_restore`

---

## Free / Pro 差分

| 機能 | Free | Pro |
|------|------|-----|
| 呼吸セッション | 1日1回 / 4-7-8のみ | 無制限 / 全5種類 |
| SOSモード | ❌ | ✅ |
| 気分スコア記録 | ❌ | ✅ |
| バイノーラルビーツ | ❌ (基本サウンド) | ✅ 9D audio |
| 日本式ウォーキング | ❌ | ✅ |
| 履歴 | ❌ | ✅ |

---

## RevenueCat 設定

| 項目 | 値 |
|------|-----|
| Monthly Product ID | `com.aniccaai.breathcalm.premium.monthly` |
| Annual Product ID | `com.aniccaai.breathcalm.premium.yearly` |
| RC Offering identifier | `default` |
