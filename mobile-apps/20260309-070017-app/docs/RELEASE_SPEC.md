# Release Specification: Zone2Daily

Source: [Apple App Store Review Guidelines](https://developer.apple.com/app-store/review/guidelines/) — 「Apps must comply with all guidelines to be approved for distribution.」
Source: [Fastlane — Match + Deliver](https://docs.fastlane.tools/) — 「Fastlane automates the build, test, and release process for iOS apps.」
Source: [ASC CLI Documentation](https://developer.apple.com/documentation/appstoreconnectapi) — 「Use asc CLI for App Store Connect automation.」

---

## 1. Pre-Submission Checklist

| Gate | コマンド | Pass 基準 |
|------|---------|----------|
| G1: Rule チェック (Rule 17/20/20b) | `greenlight preflight Zone2DailyApp/` | CRITICAL = 0 (tracking SDK / RC UI extension / tracking dialog 検出なし) |
| G2: AI API チェック (Rule 21) | `grep -r "import CoreML" Zone2Daily/ --include="*.swift"` | 0 hits (AI SDK 不使用確認) |
| G3: PrivacyInfo 存在確認 | `test -f Zone2Daily/Resources/PrivacyInfo.xcprivacy && echo PASS` | PASS |
| G4: Unit Tests | `cd Zone2Dailyios && fastlane test` | 全テスト PASS |
| G5: Greenlight | `greenlight preflight Zone2DailyApp/` | CRITICAL = 0 |
| G6: ASC Session | `security unlock-keychain && asc apps list` | 200 response |
| G7: Build | `cd Zone2Dailyios && fastlane build` | BUILD SUCCEEDED |
| G8: Typecheck | `cd Zone2Dailyios && xcodebuild -showBuildSettings` | エラーなし |
| G9: Metadata | `asc versions list --app $APP_ID` | PREPARE_FOR_SUBMISSION |

---

## 2. App Store Metadata

### en-US

| フィールド | 内容 |
|-----------|------|
| **App Name** | Zone2Daily |
| **Subtitle** | Zone 2 Heart Rate Coach |
| **Keywords** | zone 2 cardio,heart rate zone,maffetone method,aerobic training,fat burning zone,cardio tracker,peter attia zone 2,zone 2 training |
| **Promotional Text** | Train in the fat-burning zone. Maffetone formula calculates your exact Zone 2 heart rate. Track weekly minutes, build streaks. |
| **Description** | Zone2Daily is the simplest way to train smarter using Zone 2 cardio — the proven protocol recommended by Peter Attia and Andrew Huberman for fat burning, longevity, and endurance.\n\n**What is Zone 2?**\nZone 2 is the aerobic training zone where your heart rate stays between 60-70% of your maximum. The Maffetone formula (180 minus your age) gives you your exact upper limit. Most people train too hard — Zone2Daily keeps you on track.\n\n**Features:**\n• Instant Zone 2 HR calculation (just enter your age)\n• Workout timer with Zone 2 time tracking\n• Weekly dashboard: track progress toward 150 min/week goal\n• Daily streak counter\n• Morning reminder notifications\n\n**Why Zone2Daily?**\nUnlike complex multi-zone apps, Zone2Daily focuses entirely on Zone 2 — the single most important zone for metabolic health. No complicated setup, no subscriptions required to see your target HR.\n\nPremium unlocks unlimited workout history and the full weekly analytics dashboard.\n\nPrivacy: No data leaves your device. No account required. |
| **Privacy Policy URL** | https://daisuke134.github.io/anicca-products/zone2daily/privacy-policy |

### ja

| フィールド | 内容 |
|-----------|------|
| **App Name** | Zone2Daily |
| **Subtitle** | ゾーン2 心拍数コーチ |
| **Keywords** | ゾーン2,有酸素運動,心拍数ゾーン,マフェトン法,脂肪燃焼,カーディオ,トレーニング追跡,ピーターアティア |
| **Promotional Text** | 脂肪燃焼ゾーンでトレーニング。マフェトン式であなたのゾーン2目標心拍数を自動計算。週間分数を追跡してストリークを積み上げよう。 |
| **Description** | Zone2Daily は、Peter Attia と Andrew Huberman が推奨するゾーン2カーディオで賢くトレーニングするための最もシンプルなアプリです。\n\n**ゾーン2とは？**\nゾーン2は、心拍数が最大心拍数の60〜70%に保たれた有酸素トレーニングゾーンです。マフェトン式（180マイナス年齢）があなたの正確な上限値を計算します。多くの人が運動しすぎています — Zone2Daily があなたを正しいゾーンに保ちます。\n\n**機能:**\n• 瞬時のゾーン2心拍数計算（年齢を入力するだけ）\n• ゾーン2時間追跡付きワークアウトタイマー\n• 週間ダッシュボード：週150分目標への進捗を追跡\n• 毎日のストリークカウンター\n• 朝のリマインダー通知\n\nプレミアムで無制限のワークアウット履歴と週間分析ダッシュボードが解放されます。\n\nプライバシー：データはデバイスから出ません。アカウント不要。 |
| **Privacy Policy URL** | https://daisuke134.github.io/anicca-products/zone2daily/privacy-policy |

---

## 3. Screenshots

**🔴 Rule 24: 6.9" (IPHONE_69) のみ。1320×2868。Apple が自動スケール。**

| デバイス種別 | asc device type | サイズ |
|------------|----------------|--------|
| iPhone 6.9" | `IPHONE_69` | 1320×2868 |

### スクリーンショット一覧（en-US + ja 各4枚）

| # | 画面 | キャプチャコマンド | 内容 |
|---|------|-----------------|------|
| 1 | Dashboard | `asc screenshots capture --bundle-id com.aniccafactory.zone2daily ...` | 週間進捗リング + Zone 2 HR 表示 |
| 2 | PaywallView | — | プライシング + ベネフィット |
| 3 | WorkoutTimerView | — | タイマー + Zone 2 ガイド |
| 4 | OnboardingAgeInput | — | 年齢スライダー + HR プレビュー |

### キャプチャコマンド（asc-shots-pipeline 準拠）

```bash
# Capture (en-US)
asc screenshots capture \
  --bundle-id com.aniccafactory.zone2daily \
  --udid $SIMULATOR_UDID \
  --output-dir screenshots/raw/en-US \
  --output json

# Upload (en-US)
asc screenshots upload \
  --version-localization $LOC_ID_EN \
  --path screenshots/framed/en-US \
  --device-type IPHONE_69

# Capture (ja)
asc screenshots capture \
  --bundle-id com.aniccafactory.zone2daily \
  --udid $SIMULATOR_UDID \
  --output-dir screenshots/raw/ja \
  --output json

# Upload (ja)
asc screenshots upload \
  --version-localization $LOC_ID_JA \
  --path screenshots/framed/ja \
  --device-type IPHONE_69
```

---

## 4. Privacy

### PrivacyInfo.xcprivacy

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>NSPrivacyAccessedAPITypes</key>
    <array>
        <dict>
            <key>NSPrivacyAccessedAPIType</key>
            <string>NSPrivacyAccessedAPICategoryUserDefaults</string>
            <key>NSPrivacyAccessedAPITypeReasons</key>
            <array>
                <string>CA92.1</string>
            </array>
        </dict>
    </array>
    <key>NSPrivacyCollectedDataTypes</key>
    <array/>
    <key>NSPrivacyTracking</key>
    <false/>
</dict>
</plist>
```

### App Privacy 回答テーブル（ASC Web）

| 質問 | 回答 |
|------|------|
| Does your app collect data? | No |
| Does your app track users? | No（Rule 20b: ATT 不使用） |
| Data collected | None（SwiftData はデバイスローカルのみ） |

Source: [Apple Privacy Manifest](https://developer.apple.com/documentation/bundleresources/privacy_manifest_files) — 「Required for all apps using UserDefaults.」

---

## 5. Build & Archive

```bash
# Secrets のロード
source ~/.config/mobileapp-builder/.env
[ -f ./.env ] && source ./.env
security unlock-keychain -p "$KEYCHAIN_PASSWORD" ~/Library/Keychains/login.keychain-db

# Fastlane でビルド & アーカイブ & アップロード
cd Zone2Dailyios
fastlane build       # ビルド検証
fastlane archive     # .ipa 生成
fastlane upload      # ASC にアップロード

# または一括実行
fastlane release     # build + archive + upload + TestFlight 配布
```

### Fastlane 環境変数

| 変数 | 用途 |
|------|------|
| `APP_IDENTIFIER` | `com.aniccafactory.zone2daily` |
| `APPLE_ID` | Apple Developer アカウント |
| `TEAM_ID` | Team ID（Keychain から取得） |
| `ITC_TEAM_ID` | App Store Connect Team ID |
| `RC_API_KEY` | RevenueCat API Key（.env 管理） |

---

## 6. TestFlight

### ベータテスト計画

| フェーズ | テスター | 期間 | 目標 |
|---------|---------|------|------|
| Phase 1 | 内部テスター（自分） | 3日間 | クラッシュゼロ確認 |
| Phase 2 | 外部テスター（5人） | 7日間 | UX フィードバック収集 |

### セットアップコマンド

```bash
# ビルドをグループに追加
asc builds add-groups --build $BUILD_ID --group $GROUP_ID

# テスター追加
asc testflight beta-testers add \
  --app $APP_ID \
  --email $TESTER_EMAIL \
  --group $GROUP_ID

# TestFlight リンク取得
asc testflight builds get-link --app $APP_ID --build $BUILD_ID
```

---

## 7. Submission

### レビュー情報

| 項目 | 値 |
|------|-----|
| Demo Account Required | false |
| Demo Account Email | — |
| Demo Account Password | — |
| Review Notes (en) | Zone2Daily is a Zone 2 heart rate training companion app. It uses the Maffetone formula (180 minus age) to calculate Zone 2 target heart rate. Workouts are logged manually — no HealthKit required. Subscriptions managed via RevenueCat. No third-party analytics SDKs. No AI APIs. No data leaves the device. |
| Review Notes (ja) | Zone2Daily はゾーン2心拍数トレーニングのコンパニオンアプリです。マフェトン式（180マイナス年齢）でゾーン2目標心拍数を計算。ワークアウットは手動ログ。HealthKit 不使用。サブスクリプションは RevenueCat 管理。トラッキングSDK不使用。AI API不使用。データはデバイスから出ません。 |

### 提出コマンドシーケンス

```bash
# 1. コンプライアンス確認
asc versions list --app $APP_ID

# 2. 審査提出
asc review submissions-create --app $APP_ID
asc review submissions-items-add --submission $SUBMISSION_ID --version $VERSION_ID
asc review submissions-submit --submission $SUBMISSION_ID
```

---

## 8. Review Notes

| 審査官向け情報 | 詳細 |
|-------------|------|
| AI 使用 | 不使用。Zone 2 計算は純粋な数式（180−年齢）のみ |
| サブスクリプション管理 | RevenueCat SDK 経由。[Maybe Later] でいつでも閉じれる |
| HealthKit | 不使用。手動入力のみ |
| データ収集 | なし。デバイスローカル SwiftData のみ |
| サードパーティ SDK | RevenueCat（課金）のみ。tracking SDK 不使用（Rule 17） |
| アカウント | 不要 |
| オフライン動作 | 完全オフライン動作（RevenueCat は課金時のみネット接続） |

---

## 9. Age Rating

全22項目の Age Rating 設定。

| カテゴリ | 設定値 | 根拠 |
|---------|--------|------|
| Alcohol, Tobacco, or Drug Use or References | None | 該当なし |
| Contests | None | 該当なし |
| Gambling and Contests | None | 該当なし |
| Horror/Fear Themes | None | 該当なし |
| Mature/Suggestive Themes | None | 該当なし |
| Medical/Treatment Information | None | 一般的なフィットネス情報のみ |
| Profanity or Crude Humor | None | 該当なし |
| Sexual Content or Nudity | None | 該当なし |
| Simulated Gambling | None | 該当なし |
| Violence | None | 該当なし |
| 18+ only features | None | 該当なし |
| **Final Rating** | **4+** | — |

コマンド: `asc age-ratings set --app $APP_ID --all-none`

---

## 10. Hotfix Protocol

バグ修正が必要な場合のクイックリリース手順。

```bash
# 1. バージョンバンプ
# MARKETING_VERSION: 1.0.0 → 1.0.1（バグ修正）
# CURRENT_PROJECT_VERSION: +1

# 2. 修正 + テスト
fastlane test

# 3. アーカイブ + アップロード
fastlane release

# 4. TestFlight → 内部テスト（3日）
# 5. 審査提出
```

| バグ重大度 | 対応 |
|----------|------|
| クラッシュ（起動不能） | 即 hotfix（24時間以内） |
| RevenueCat 課金不全 | 即 hotfix |
| UI バグ（軽微） | 次回マイナーリリース |

---

## 11. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-03-xx | Initial release: Zone 2 HR calculator + Manual workout log + Weekly dashboard + Paywall |
