# Release Specification: VagusReset

Source: [App Store Review Guidelines](https://developer.apple.com/app-store/review/guidelines/) — 「Submit accurate, complete information」
Source: [Apple App Store Connect Help — App Information](https://developer.apple.com/help/app-store-connect/create-an-app-record/add-app-information/) — 「Fill in all required metadata before submission」
Source: [Greenlight Preflight Tool](https://github.com/anicca-products/greenlight) — 「CRITICAL=0 before any submission」

---

## 1. Pre-Submission Checklist

| # | Gate | Command | Pass Criteria |
|---|------|---------|---------------|
| 1 | Greenlight CRITICAL=0 | `greenlight preflight VagusResetios/` | `CRITICAL: 0` |
| 2 | Unit + Integration テスト | `cd VagusResetios && fastlane test` | 0 failures |
| 3 | E2E テスト | `maestro test maestro/` | all PASS |
| 4 | ビルド成功 | `cd VagusResetios && fastlane build` | 0 errors |
| 5 | アーカイブ成功 | `cd VagusResetios && fastlane archive` | .ipa 生成 |
| 6 | ASC Validate | `asc validate --bundle-id com.aniccafactory.vagusreset` | Errors=0 |
| 7 | RevenueCat 設定確認 | `asc subscriptions list --group $GROUP_ID` | monthly + annual 両方 READY_TO_SUBMIT |
| 8 | スクリーンショット | `find screenshots/framed -name '*.png' \| wc -l` | ≥ 8（en-US 4+ ja 4+） |
| 9 | App Privacy 設定 | ASC Web で手動設定（センサーなし・収集なし） | `.app-privacy-done` ファイル存在 |

---

## 2. App Store Metadata

### en-US

| 項目 | 内容 | 文字数制限 |
|------|------|-----------|
| Name | Vagus Nerve Reset - VagusReset | 30文字以内 |
| Subtitle | Calm Your Nervous System Daily | 30文字以内 |
| Keywords | vagus nerve,nervous system reset,vagal tone,stress relief,anxiety relief,parasympathetic,autonomic nervous,daily routine | 100文字以内 |
| Promotional Text | Science-backed vagus nerve exercises. No sensors needed — just 2 minutes a day. | 170文字以内 |
| Description | Reset your nervous system in 2 minutes. VagusReset guides you through scientifically-backed vagus nerve exercises — humming, gargling, cold water, and more — to calm anxiety and reduce stress. No sensors required. Start free with 5 exercises, or unlock 20+ with Premium. Build your daily streak and feel the difference in a week. | 4000文字以内 |

### ja（日本語）

| 項目 | 内容 | 文字数制限 |
|------|------|-----------|
| Name | Vagus Nerve Reset - VagusReset | 30文字以内 |
| Subtitle | 迷走神経デイリーリセット | 30文字以内 |
| Keywords | 迷走神経,自律神経,ストレス解消,リラックス,不安解消,副交感神経,毎日ルーティン,セルフケア | 100文字以内 |
| Promotional Text | 科学的根拠のある迷走神経エクササイズ。センサー不要、毎日2分で自律神経を整える。 | 170文字以内 |
| Description | 迷走神経をリセットして、毎日2分でストレスを手放そう。VagusResetは科学的に実証された迷走神経活性化エクササイズ（哼り・うがい・冷水など）をガイドし、不安を和らげ自律神経バランスを整えます。センサー不要。まず5種のエクササイズを無料で体験、Premiumで20種以上にアクセス。デイリーストリークで習慣化をサポートします。 | 4000文字以内 |

---

## 3. Screenshots

| デバイス | サイズ | 必要枚数 | 備考 |
|---------|--------|---------|------|
| iPhone 6.9" (IPHONE_69) | 1320×2868px | en-US: 4+、ja: 4+ | Rule 24: 6.9"のみ。Apple が自動スケール |

**スクリーンショット内容（推奨順）:**

| # | 画面 | コピー（en-US） | コピー（ja） |
|---|------|--------------|------------|
| 1 | OnboardingStep1 | "Reset in 2 Minutes Daily" | 「毎日2分でリセット」 |
| 2 | HomeView（ストリーク表示） | "Build Your Streak" | 「ストリークを積み上げる」 |
| 3 | SessionView（タイマー） | "Guided Timer. No Sensors." | 「ガイド付きタイマー。センサー不要。」 |
| 4 | PaywallView | "Unlock All 20+ Exercises" | 「20種以上を全解放」 |

**キャプチャコマンド（asc-shots-pipeline 準拠）:**

```bash
# 環境変数
UDID=$(xcrun simctl list devices | grep "iPhone 16 Pro" | grep Booted | awk -F'[()]' '{print $2}')
BUNDLE_ID="com.aniccafactory.vagusreset"

# キャプチャ
asc screenshots capture \
  --bundle-id "$BUNDLE_ID" \
  --udid "$UDID" \
  --output-dir screenshots/raw \
  --output json

# フレーミング（Koubou）
asc screenshots frame --input screenshots/raw --output screenshots/framed

# アップロード（en-US）
LOC_ID_EN=$(asc app-store-version-localizations list --version-id "$VERSION_ID" | jq -r '.[] | select(.locale=="en-US") | .id')
asc screenshots upload --version-localization "$LOC_ID_EN" --path screenshots/framed/en-US --device-type IPHONE_69

# アップロード（ja）
LOC_ID_JA=$(asc app-store-version-localizations list --version-id "$VERSION_ID" | jq -r '.[] | select(.locale=="ja") | .id')
asc screenshots upload --version-localization "$LOC_ID_JA" --path screenshots/framed/ja --device-type IPHONE_69
```

---

## 4. Privacy

| 項目 | 設定 |
|------|------|
| `PrivacyInfo.xcprivacy` | NSPrivacyAccessedAPICategoryUserDefaults: CA92.1 のみ |
| NSPrivacyTracking | false |
| NSPrivacyCollectedDataTypes | [] （収集なし） |
| ATT | 不使用（Rule 20b） |
| App Privacy（ASC） | 「データを収集しない」 |

**App Privacy 回答（ASC Web — 手動設定）:**

| 質問 | 回答 |
|------|------|
| Does your app collect data? | No |
| Does your app use crash data? | No |
| Does your app use performance data? | No |
| Does your app use third-party advertising? | No |

---

## 5. Build & Archive

```bash
# Secrets ロード
source ~/.config/mobileapp-builder/.env
[ -f ./.env ] && source ./.env
security unlock-keychain -p "$KEYCHAIN_PASSWORD" ~/Library/Keychains/login.keychain-db

# テスト
cd VagusResetios && fastlane test

# ビルド（Debug 確認用）
fastlane build

# アーカイブ + IPA 生成
fastlane archive

# ASC アップロード
fastlane upload_to_asc
```

**バージョン管理:**

| 項目 | 値 |
|------|-----|
| CFBundleShortVersionString | 1.0.0 |
| CFBundleVersion | 1（ビルドごとにインクリメント） |
| Minimum Deployment Target | iOS 17.0 |

---

## 6. TestFlight

```bash
# ビルドをベータグループに追加
GROUP_ID=$(asc testflight groups list --app "$APP_ID" | jq -r '.[] | select(.name=="External Testers") | .id')
BUILD_ID=$(asc builds list --app "$APP_ID" --sort -uploadedDate --limit 1 | jq -r '.[0].id')
asc builds add-groups --build "$BUILD_ID" --group "$GROUP_ID"

# テスター招待
asc testflight beta-testers invite --app "$APP_ID" --email "daisuke@example.com"

# TestFlight リンク取得
TESTFLIGHT_URL=$(asc testflight builds get-link --app "$APP_ID" --build "$BUILD_ID" 2>/dev/null || echo "N/A")

# Slack 通知
curl -s -X POST "$SLACK_WEBHOOK_AGENTS" \
  -H 'Content-Type: application/json' \
  -d "{\"text\":\"🧪 TestFlight準備完了\nリンク: $TESTFLIGHT_URL\n↑タップしてテスト可能\"}"
```

---

## 7. Submission

**ASC Review Details:**

| 項目 | 値 |
|------|-----|
| First Name | Daisuke |
| Last Name | (Apple Developer Account) |
| Phone | (Apple Developer Account) |
| Email | (Apple Developer Account) |
| Demo Account Required | false |
| Notes | This app guides users through vagus nerve exercises (humming, gargling, cold water splash). No sensors, camera, microphone, or HealthKit used. Exercises are static content (JSON). RevenueCat handles subscription management. |

**コンプライアンス回答:**

| 質問 | 回答 |
|------|------|
| Encryption | ITSAppUsesNonExemptEncryption = NO（Info.plist） |
| Content Rights | Does not use third-party content |
| Advertising Identifier | No |

**審査提出コマンド:**

```bash
SUBMISSION_ID=$(asc review submissions-create --app "$APP_ID" | jq -r '.id')
asc review submissions-items-add --submission "$SUBMISSION_ID" --version "$VERSION_ID"
asc review submissions-submit --id "$SUBMISSION_ID"
```

---

## 8. Review Notes

```
This app provides guided vagus nerve stimulation exercises to help users manage
stress and anxiety. All content is pre-curated and stored locally as JSON —
no AI APIs, no external servers, no user data collected.

Key points for reviewers:
- Subscription: Monthly ($4.99) and Annual ($29.99) via RevenueCat/StoreKit
- Free tier: 5 exercises available without subscription
- No camera, microphone, HealthKit, or location permissions requested
- Exercises: humming (vocalizing "mmm"), gargling, cold water splash on face
- These are established vagus nerve stimulation techniques from published research
- Privacy: Only UserDefaults for streak tracking. No third-party SDKs.
```

---

## 9. Age Rating

Source: [App Store Connect — Age Rating](https://developer.apple.com/help/app-store-connect/reference/app-information/age-rating/) — 「Set age rating based on content」

| Category | Level |
|----------|-------|
| Alcohol, Tobacco, or Drug Use or References | None |
| Contests | None |
| Gambling and Contests | None |
| Horror/Fear Themes | None |
| Mature/Suggestive Themes | None |
| Medical/Treatment Information | None |
| Profanity or Crude Humor | None |
| Sexual Content or Nudity | None |
| Simulated Gambling | None |
| Violence | None |
| All other categories | None |

**Resulting Rating:** 4+

---

## 10. Hotfix Protocol

| Step | Action | Command |
|------|--------|---------|
| 1 | バグ確認 + 優先度判定 | Xcode Organizer でクラッシュレポート確認 |
| 2 | release ブランチで修正 | `git checkout release/1.0.0` → fix → `git commit` |
| 3 | dev に cherry-pick | `git checkout dev && git cherry-pick <hash>` |
| 4 | CFBundleVersion インクリメント | `1.0.0 (1)` → `1.0.0 (2)` |
| 5 | テスト実行 | `fastlane test` → 0 failures |
| 6 | アーカイブ + アップロード | `fastlane archive && fastlane upload_to_asc` |
| 7 | TestFlight 配布 | `asc builds add-groups ...` |
| 8 | App Store 再提出 | Submission API or ASC Web |

---

## 11. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-03 | 初回リリース: 20+エクササイズ、タイマー、ストリーク、PaywallView |
