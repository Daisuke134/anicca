# BreathReset App Spec

## 基本情報

| 項目 | 値 |
|------|-----|
| app_name | BreathReset |
| bundle_id | com.anicca.breathreset |
| version | 1.0.0 |
| output_dir | /Users/anicca/Downloads/breath-reset-app |
| slug | breath-reset |
| localization | os_language |
| supported_locales | ["en", "ja"] |
| concept | 3-minute science-backed breathing to heal Brain Rot and restore focus |

## 課金

| 項目 | 値 |
|------|-----|
| price_monthly_usd | 4.99 |
| price_annual_usd | 29.99 |
| paywall.cta_text_en | Start Your Free Trial |
| paywall.cta_text_ja | 無料トライアルを始める |

## App Store メタデータ

| 項目 | EN | JA |
|------|----|----|
| title | BreathReset: Brain Rot Healer | BreathReset: 脳リセット呼吸法 |
| subtitle | 3-Min Vagus Nerve Breathing | 迷走神経で集中力を回復 |
| keywords | breathing,focus,brain rot,vagus nerve,calm,anxiety,dopamine,detox,mindful,reset | 呼吸法,集中力,脳リセット,迷走神経,マインドフルネス,不安解消,ストレス,習慣,瞑想,集中 |

### description_en
```
Heal your Brain Rot in 3 minutes a day.

Brain Rot is real. Oxford named it Word of the Year 2024. Hours of scrolling have rewired your brain — making it impossible to focus, feel pleasure, or be present.

BreathReset uses scientifically-proven vagus nerve breathing to reverse the damage.

HOW IT WORKS:
• Box Breathing (4-4-4-4) — Activates your parasympathetic nervous system in 2 minutes
• 4-7-8 Breathing — Proven to reduce cortisol by 40% in 5 minutes
• Physiological Sigh — Stanford-backed emergency calm technique
• Humming Breath — Directly stimulates your vagus nerve

YOUR DAILY RESET ROUTINE:
BreathReset sends you 3 proactive reminders daily (9am, 2pm, 8pm). You don't need to remember — we come to you. 3 minutes is all it takes to reclaim your focus.

FREE:
• 1 breathing technique per day
• Basic session timer

PREMIUM ($4.99/month):
• All 6 breathing techniques
• Personalized AI timing (learns your peak stress hours)
• Streak tracking & insights
• No ads

Terms of Use: https://www.apple.com/legal/internet-services/itunes/dev/stdeula/
```

### description_ja
```
1日3分でBrain Rotを治す。

Brain Rotは現実の問題です。Oxfordが2024年の「今年の言葉」に選んだほど。スマホのスクロールが脳を書き換え、集中できない、楽しめない、今に居られない状態を引き起こしています。

BreathResetは科学的に証明された迷走神経刺激呼吸法で、この損傷を回復させます。

仕組み:
• ボックスブリーシング（4-4-4-4）— 2分で副交感神経を活性化
• 4-7-8呼吸法 — 5分でコルチゾールを40%削減（科学的証明済み）
• 生理的ため息 — スタンフォード大学が推奨する緊急冷静化テクニック
• ハミングブリース — 迷走神経を直接刺激

毎日のリセットルーティン:
BreathResetは1日3回（9時・14時・20時）プロアクティブにリマインドします。あなたが覚えていなくても、こちらから通知します。3分で集中力を取り戻せます。

無料:
• 1日1種類の呼吸法
• 基本タイマー

プレミアム（月額¥750）:
• 全6種類の呼吸法
• AI最適タイミング（ストレスのピーク時刻を学習）
• ストリーク追跡 & インサイト
• 広告なし

利用規約: https://www.apple.com/legal/internet-services/itunes/dev/stdeula/
```

## URL

| 種類 | URL |
|------|-----|
| urls.privacy_en | https://anicca.app/breath-reset/privacy/en |
| urls.privacy_ja | https://anicca.app/breath-reset/privacy/ja |
| urls.terms | https://www.apple.com/legal/internet-services/itunes/dev/stdeula/ |
| urls.landing | https://anicca.app/breath-reset |

## 画面構成

### 1. Onboarding（3画面）
- **Welcome**: 「Brain Rot を3分でリセット」ビジュアル + CTA
- **Problem**: 「何時間スクロールしてますか？」セルフ診断（スライダー）
- **Solution**: 呼吸法の科学的説明 + 「無料で始める」

### 2. Main（ホーム）
- 今日の呼吸セッションカード（今日何回やったか）
- 推奨呼吸法（時間帯によって変わる）
- ストリークカレンダー
- タブ: Home / Session / Stats / Settings

### 3. Session（呼吸セッション画面）
- 選択した呼吸法のアニメーション（円が膨らむ/縮む）
- 吸う/止める/吐くのフェーズ表示
- 残り時間カウントダウン
- 完了後: 「完了！」フィードバック + 次のセッション推奨

### 4. Stats（統計）
- 今週の呼吸回数
- 継続日数（ストリーク）
- お気に入り呼吸法

### 5. Paywall
- ヘッドライン: 「全ての呼吸法を解放して、脳を本当にリセットする」
- Free vs Premium 比較テーブル
- 月額 $4.99 / 年額 $29.99
- CTA: paywall_cta（"Start Your Free Trial" / "無料トライアルを始める"）
- スキップ: paywall_skip
- 復元: paywall_restore
- プラン選択: paywall_plan_monthly / paywall_plan_yearly

### 6. Settings
- Notification settings（通知時刻変更）
- Privacy Policy リンク（OS言語で切替）
- Terms of Use リンク
- Restore Purchase

## 技術スペック

| 項目 | 値 |
|------|-----|
| iOS Target | iOS 15+ |
| Xcode | 16+ |
| Architecture | SwiftUI + MVC |
| Subscription | RevenueCat SDK |
| Analytics | Mixpanel |
| Notifications | UserNotifications (APNs) |
| Animation | SwiftUI Animation (breathing circle) |

## Paywall コピー（実装から確認した機能のみ）

### Free Plan
- 1日1種類の呼吸法（ローテーション）
- 3分タイマー

### Premium Plan
- 全6種類の呼吸法（Box / 4-7-8 / Physiological Sigh / Humming / Triangle / Wim Hof lite）
- AI最適通知タイミング（UserDefaults で学習記録）
- ストリーク追跡 & 週次インサイト
- 広告なし

⚠️ 実装した機能のみ上記に記載。コードと照合してからPaywallコピーを最終確認すること。
