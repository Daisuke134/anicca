# Sleep Ritual — Spec v1.0

調査日: 2026-02-28

---

## 技術

| フィールド | 値 |
|---------|---|
| **app_name** | SleepRitual |
| **bundle_id** | com.anicca.sleepritual |
| **version** | 1.0.0 |
| **output_dir** | /Users/anicca/anicca-project/daily-apps/sleep-ritual |

---

## 課金

| フィールド | 値 |
|---------|---|
| **price_monthly_usd** | 9.99 |
| **price_annual_usd** | 49.99 |
| **paywall.cta_text_en** | Start Your Sleep Ritual — Free Trial |
| **paywall.cta_text_ja** | 睡眠を変える — 無料で試す |

---

## App Store メタデータ

| フィールド | 値 |
|---------|---|
| **metadata.title_en** | Sleep Ritual: AI Sleep Coach |
| **metadata.title_ja** | スリープリチュアル: AI睡眠コーチ |
| **metadata.subtitle_en** | End Night Scrolling. Wake Up Rested. |
| **metadata.subtitle_ja** | 夜のスマホ習慣を断ち切る |
| **metadata.keywords_en** | sleep,sleepmaxxing,insomnia,bedtime routine,sleep coach,cortisol,anxiety,relaxation,night habit |
| **metadata.keywords_ja** | 睡眠,不眠,夜更かし,就寝ルーティン,コルチゾール,睡眠改善,AIコーチ,朝活,睡眠の質 |

### Description（EN）

```
Tired of scrolling until 3am? Can't wake up on time? Sleep Ritual is your AI sleep coach —
it sends you the right nudge at the right time to build a healthy bedtime routine that sticks.

★ What Sleep Ritual does:
• Sends you a personalized nudge at 10pm with your tonight's sleep ritual (takes under 5 min)
• Tracks your sleep quality with a simple 2-tap morning check-in
• Adjusts your ritual based on what worked yesterday
• Gradually reduces late-night phone time without harsh rules

★ Built for people who have tried 10 apps and quit all of them:
• No streaks. No shame. Just small steps that compound.
• If you skip a night, Sleep Ritual starts fresh — not from zero.

★ Science-backed:
• Bedtime rituals reduce cortisol by up to 27% (Nature, 2025)
• Consistent sleep times improve wake-up energy within 7 days

Terms of Use: https://www.apple.com/legal/internet-services/itunes/dev/stdeula/
```

### Description（JA）

```
毎晩気づいたら3時…朝のスヌーズが止まらない…そんなループを断ち切るのがSleep Ritualです。
AIが毎晩22時に、あなたに合った就寝ルーティンをお届けします。

★ Sleep Ritualがやること:
• 毎晩22時にパーソナライズされたナッジを通知（所要時間5分以内）
• 翌朝2タップで睡眠の質を記録
• 昨夜の結果を元に今夜のルーティンを自動調整
• 強制なし・ルールなし・失敗しても翌日リセット

★ 「アプリ10個試して全部やめた人」のために設計:
• ストリーク（連続記録）なし。失敗を責めない。
• 小さな積み重ねだけを記録する。

★ 科学的根拠:
• 就寝前ルーティンはコルチゾールを最大27%低下（Nature 2025）
• 7日間で起床時のエネルギーが改善

利用規約: https://www.apple.com/legal/internet-services/itunes/dev/stdeula/
```

---

## URL

| フィールド | 値 |
|---------|---|
| **urls.privacy_en** | https://aniccaai.com/sleep-ritual/privacy/en |
| **urls.privacy_ja** | https://aniccaai.com/sleep-ritual/privacy/ja |
| **urls.terms** | https://www.apple.com/legal/internet-services/itunes/dev/stdeula/ |
| **urls.landing** | https://aniccaai.com/sleep-ritual |

---

## ローカライズ方針

| フィールド | 値 |
|---------|---|
| **localization** | os_language |
| **supported_locales** | ["en", "ja"] |

---

## コンセプト

AI が毎晩22時に就寝前ルーティンをパーソナライズ配信し、夜更かし・朝起きられない問題を根本解決する iOS アプリ。

---

## 画面構成

### 1. Onboarding（3画面）

| 画面 | 内容 | アクセシビリティID |
|------|-----|----------------|
| Welcome | 「夜更かしをやめたいですか？」+ Start ボタン | `onboarding-welcome-cta` |
| Problem Select | 「最大の問題」を1つ選ぶ（夜更かし / 朝起きれない / ぐっすり眠れない） | `problem-select-{type}` |
| Notification Setup | 毎晩22時の通知許可 + 「許可する」ボタン | `onboarding-notifications-allow` |

### 2. Paywall（オンボーディング後に表示）

| 要素 | 内容 | アクセシビリティID |
|------|-----|----------------|
| ヘッドライン | 「7日間で朝が変わる」 | `paywall-headline` |
| Monthly プラン | $9.99/月 | `paywall_plan_monthly` |
| Annual プラン | $49.99/年（最もお得） | `paywall_plan_yearly` |
| CTA ボタン | 仕様書の paywall.cta_text を使う | `paywall_cta` |
| スキップ | 「後で」 | `paywall_skip` |
| 復元 | 「購入を復元」 | `paywall_restore` |

### 3. Main（タブ: ホーム / 記録 / 設定）

#### ホームタブ
- 今日のルーティン表示（夜はルーティン、朝はチェックイン）
- 「今すぐ開始」ボタン（`main-start-ritual`）
- 連続記録なし。「最近の記録」として7日分をグラフ表示

#### 記録タブ（Logs）
- 過去の睡眠チェックイン一覧
- 気分スコア（5段階）の推移グラフ
- アクセシビリティID: `logs-list`

#### 設定タブ（Settings）
- 通知時刻変更（デフォルト22:00）
- Privacy Policy リンク（OS言語で切替）: `settings-privacy-link`
- Terms of Use リンク: `settings-terms-link`
- 購入を復元: `settings-restore`

### 4. 就寝ルーティン実行画面（モーダル）

1. ガイド付きブリージング（4-7-8 呼吸法 × 3セット）
2. 画面を暗くする（輝度を下げるガイド）
3. 「おやすみ」終了ボタン → チェックインリマインダー（翌朝7時）設定
- アクセシビリティID: `ritual-start`, `ritual-complete`

---

## Paywall 機能差分（コードに基づく正確な差分）

| 機能 | Free | Pro |
|------|------|-----|
| 就寝ルーティン | 基本1種類（呼吸法のみ） | パーソナライズ3種類 |
| 朝チェックイン | 1問のみ | 詳細5問 + 睡眠スコア |
| 通知時刻変更 | 固定 22:00 | 任意設定可能 |
| 過去データ | 直近3日分 | 無制限 |
| AI 調整 | なし（固定ルーティン） | 前日結果ベースで毎晩自動調整 |
