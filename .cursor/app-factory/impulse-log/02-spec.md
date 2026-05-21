# ImpulseLog — App Spec

**生成日:** 2026-02-26
**フェーズ:** PHASE 0.5 SPEC 生成

---

## 基本情報

| フィールド | 値 |
|-----------|-----|
| `app_name` | ImpulseLog |
| `bundle_id` | com.anicca.impulselog |
| `version` | 1.0.0 |
| `output_dir` | ~/Downloads/impulse-log-app |
| `slug` | impulse-log |
| `price_monthly_usd` | 9.99 |
| `price_annual_usd` | 49.99 |

---

## コンセプト

**concept:** ADHD・HSP向けの感情爆発ログアプリ。衝動・怒り・感情の嵐を30秒で記録し、週次レポートでトリガーパターンを可視化する。

---

## Paywall

| フィールド | 値 |
|-----------|-----|
| `paywall.cta_text_en` | Unlock Full Access |
| `paywall.cta_text_ja` | フルアクセスを解除する |

**Free プラン制限:**
- ログ記録: 1日5件まで
- レポート: 直近7日分のみ
- 感情タグ: 基本5種類のみ

**Pro プラン:**
- ログ記録: 無制限
- レポート: 無制限（週次・月次パターン分析）
- 感情タグ: 全20種類（カスタムタグ追加可能）
- トリガー分析: AIによるパターン検出
- エクスポート: PDF/CSV

---

## App Store メタデータ

| フィールド | EN | JA |
|-----------|----|----|
| `title` | ImpulseLog: Anger & ADHD Diary | ImpulseLog: 怒り・衝動ログ |
| `subtitle` | Track Emotions, Find Patterns | 感情を記録してパターンを発見 |

### Description (EN)
```
ImpulseLog helps you break the cycle of emotional explosions and regret.

Designed specifically for people with ADHD, HSP, and those who struggle with emotional regulation — record your impulses and anger episodes in just 30 seconds, then uncover the hidden triggers behind them.

🔥 HOW IT WORKS
• Tap the log button the moment you feel an emotional surge
• Choose your emotion type and intensity (1-10)
• Tag the trigger: Work, Family, Traffic, etc.
• Add a quick note (optional)

📊 SEE YOUR PATTERNS
• Weekly reports reveal your top triggers
• Time-of-day analysis shows when you're most vulnerable
• Progress tracking shows improvement over time

💡 KEY FEATURES
• 30-second quick log — designed for impulsive moments
• Emotion intensity scale
• Trigger tagging system
• Weekly pattern reports
• Private & secure — data stays on your device

Whether you're newly diagnosed, awaiting diagnosis, or simply struggling with emotional dysregulation, ImpulseLog gives you the self-awareness tool you need to break the cycle.

Terms of Use: https://www.apple.com/legal/internet-services/itunes/dev/stdeula/
```

### Description (JA)
```
ImpulseLogは、感情の爆発と後悔のループを断ち切るためのアプリです。

ADHD・HSP・感情調整が難しい方向けに設計されています。衝動や怒りが起きた瞬間を30秒でログ記録し、背後に潜むトリガーを明らかにします。

🔥 使い方
• 感情が高ぶった瞬間にログボタンをタップ
• 感情の種類と強度（1〜10）を選択
• トリガーをタグ付け: 仕事、家族、交通など
• 短いメモを追加（任意）

📊 パターンを発見
• 週次レポートであなたの主要トリガーを表示
• 時間帯分析でいつ最も脆弱かを把握
• 進捗追跡で改善を確認

💡 主な機能
• 30秒クイックログ — 衝動的な瞬間向けのUI設計
• 感情強度スケール
• トリガータグシステム
• 週次パターンレポート
• プライベート＆安全 — データはデバイスに保存

診断済みの方、診断待ちの方、あるいは単に感情の波に悩んでいる方に。
ImpulseLogが感情の嵐を理解する第一歩になります。

利用規約: https://www.apple.com/legal/internet-services/itunes/dev/stdeula/
```

### Keywords

| 言語 | キーワード |
|------|-----------|
| EN | ADHD,anger,emotion,impulse,diary,HSP,feelings,log,tracker,mental health |
| JA | ADHD,感情日記,怒り,衝動,HSP,メンタルヘルス,感情記録,感情管理,アンガー,ログ |

---

## URLs

| フィールド | 値 |
|-----------|-----|
| `urls.privacy_en` | https://anicca.app/impulse-log/privacy/en |
| `urls.privacy_ja` | https://anicca.app/impulse-log/privacy/ja |
| `urls.terms` | https://www.apple.com/legal/internet-services/itunes/dev/stdeula/ |
| `urls.landing` | https://anicca.app/impulse-log |

---

## ローカライズ

| フィールド | 値 |
|-----------|-----|
| `localization` | os_language |
| `supported_locales` | ["en", "ja"] |

---

## 画面構成

### オンボーディング（4ステップ）

| ステップ | 画面 | 内容 |
|---------|------|------|
| 1 | Welcome | アプリ名・コンセプト説明（「感情の嵐に、名前をつけよう」） |
| 2 | Pain Selection | 「あなたの悩みは？」→ 怒り / 衝動 / 感情爆発 / HSP / ADHD から選択 |
| 3 | Live Demo | 実際のログ画面をデモ体験（感情強度スライダーを動かす） |
| 4 | Notification + Paywall | 通知許可 → Paywall 表示 |

### メイン画面（TabView）

| タブ | 内容 |
|------|------|
| 📝 Log（ホーム） | 今すぐログボタン（大きい）+ 本日のログ一覧 |
| 📊 Reports | 週次レポート（感情ヒートマップ + トップトリガー） |
| ⚙️ Settings | Pro機能・Privacy Policy・Terms of Use |

### クイックログシート（30秒 UI）

| 項目 | 内容 |
|------|------|
| 感情タイプ | 怒り / 不安 / パニック / 悲しみ / 衝動 |
| 強度スライダー | 1〜10 |
| トリガータグ | 仕事 / 家族 / 交通 / SNS / 自分自身 / その他 |
| メモ | テキスト入力（任意・Pro） |
| 保存 | タップ → ホームに戻る |

### Paywall

| 要素 | 内容 |
|------|------|
| ヘッドライン（EN） | Break the Cycle. Understand Your Triggers. |
| ヘッドライン（JA） | ループを断ち切る。トリガーを理解する。 |
| Free制限表示 | 「5 logs/day · 7-day history · Basic tags」 |
| Pro機能リスト | 「Unlimited logs · Full reports · AI pattern analysis · Custom tags」 |
| Monthly | $9.99/month |
| Annual | $49.99/year（Save 58%） |
| CTA（EN） | Unlock Full Access |
| CTA（JA） | フルアクセスを解除する |
| Skip | テキストリンク「Maybe Later」 |
| Restore | テキストリンク「Restore Purchase」 |

---

## 技術スタック

| 項目 | 値 |
|------|-----|
| プラットフォーム | iOS 15+ |
| UI | SwiftUI |
| データ | SwiftData（ローカル保存） |
| 課金 | RevenueCat SDK |
| 分析 | Mixpanel |
| 通知 | UserNotifications (APNs) |

---

## 開発環境

| 項目 | 値 |
|------|-----|
| **ワークツリーパス** | `~/Downloads/anicca-impulse-log` |
| **ブランチ** | `app-factory/impulse-log` |
| **ベースブランチ** | `main` |
| **作業状態** | 実装中 |
