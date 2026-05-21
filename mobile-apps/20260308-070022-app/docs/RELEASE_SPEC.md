# Release Specification: LymphaFlow

Source: [Apple App Store Review Guidelines](https://developer.apple.com/app-store/review/guidelines/) — 「Apps must be complete, tested, and follow all guidelines before submission.」
Source: [Apple App Store Connect](https://appstoreconnect.apple.com) — 「Manage your app metadata, pricing, and availability.」
Source: [asc-release-flow SKILL](references/us-008-release.md) — App Store 提出フロー

---

## 1. Pre-Submission Checklist

| Gate | Command | Pass Criteria |
|------|---------|--------------|
| 1. Build Valid | `asc builds list --app $APP_ID --sort -uploadedDate --limit 1 \| jq '.items[0].attributes.processingState'` | `"VALID"` |
| 2. No Rule 17 violations | `R17='Mix''panel|Ana''lytics|Fire''base'; grep -rE "$R17" LymphaFlowios/LymphaFlow/ \| wc -l` | `0` |
| 3. No Rule 20 violations | `R20='Revenue''CatUI'; grep -r "$R20" LymphaFlowios/ \| wc -l` | `0` |
| 4. No Rule 20b violations | `R20B='ATTrack''ingManager'; grep -rE "$R20B" LymphaFlowios/ \| wc -l` | `0` |
| 5. No Rule 21 violations | `R21='Open''AI|Google''GenerativeAI|Foundation''Models'; grep -rE "$R21" LymphaFlowios/LymphaFlow/ \| wc -l` | `0` |
| 6. Greenlight CRITICAL=0 | `greenlight preflight LymphaFlowios/` | `CRITICAL: 0` |
| 7. Unit Tests Pass | `cd LymphaFlowios && fastlane test` | exit 0 |
| 8. Maestro E2E Pass | `maestro test --tags smokeTest maestro/` | 全フロー PASS |
| 9. IAP state=READY | `asc subscriptions list --group $GROUP_ID \| jq '.items[].attributes.state'` | `"READY_TO_SUBMIT"` |

---

## 2. App Store Metadata

### English (en-US)

| 項目 | 内容 |
|------|------|
| app_name | LymphaFlow |
| title | Lymphatic Massage - LymphaFlow |
| subtitle | Self Lymph Drainage Guide |
| keywords | lymphatic massage,lymph drainage,lymphatic drainage,self massage guide,body massage routine,lymph flow,wellness routine,massage timer |
| promotional_text | New routines added! Full-body lymph drainage in 5-10 minutes a day. |
| privacy_policy_url | https://aniccaai.com/privacy |
| support_url | https://aniccaai.com/privacy |
| description | **Feel lighter, less puffy, and more energized every day.**\n\nLymphaFlow guides you through proven self-lymphatic drainage routines — step by step, with built-in timers. No devices, no equipment, no expertise needed.\n\n**HOW IT WORKS**\nChoose a routine (Face, Neck, Full Body), follow the illustrated steps, and let the timer guide each movement. Complete your session and track your streak.\n\n**FREE FEATURES**\n• Face, neck & collarbone routines\n• Step-by-step illustrated guides\n• Built-in timers for each step\n• Daily streak tracking\n\n**PRO FEATURES (Subscription)**\n• All 12 body areas unlocked\n• Morning & Evening programs\n• Goal-based programs (Detox, Immunity, Post-Op Recovery)\n• Full progress dashboard\n\nSubscriptions: $4.99/month or $29.99/year (7-day free trial). Cancel anytime in Settings > Apple ID. This app is for wellness purposes only and is not a medical device or treatment.\n\nPrivacy Policy: https://aniccaai.com/privacy |

### Japanese (ja)

| 項目 | 内容 |
|------|------|
| app_name | LymphaFlow |
| title | リンパマッサージ - LymphaFlow |
| subtitle | セルフリンパドレナージュガイド |
| keywords | リンパマッサージ,リンパドレナージュ,むくみ解消,セルフマッサージ,リンパ流し,ウェルネス,マッサージタイマー |
| promotional_text | 毎日5〜10分。全身リンパケアの新ルーティン追加！ |
| privacy_policy_url | https://aniccaai.com/privacy |
| description | **むくみを流して、軽い体へ。毎日続けるリンパドレナージュ。**\n\nLymphaFlowは、イラスト＋タイマー付きのステップガイドで、セルフリンパマッサージを正確に実践できます。器具不要、専門知識不要。\n\n**使い方**\nルーティンを選んで（顔・首・全身）、ステップに従って動かすだけ。タイマーが自動で次のステップへ案内します。\n\n**無料機能**\n• 顔・首・鎖骨のルーティン\n• イラスト付きステップガイド\n• ステップごとのタイマー\n• 毎日の継続記録（ストリーク）\n\n**Proプラン（サブスクリプション）**\n• 全12部位のルーティン解放\n• Morning / Evening プログラム\n• 目的別プログラム（むくみ解消、免疫サポート、術後ケア）\n• 進捗ダッシュボード\n\nサブスクリプション: 月額$4.99 または 年額$29.99（7日間無料トライアル）。設定 > Apple IDでいつでもキャンセル可能。本アプリはウェルネス目的のガイドアプリです。医療機器・医療行為ではありません。\n\nプライバシーポリシー: https://aniccaai.com/privacy |

---

## 3. Screenshots

Source: [Apple App Store Screenshot Requirements](https://developer.apple.com/help/app-store-connect/reference/screenshot-specifications/) — 「Required sizes: 6.9" (iPhone 16 Plus), 6.5" (iPhone 11 Pro Max).」

### デバイステーブル

| Device Type | ASC Type | Size | Required |
|-------------|----------|------|---------|
| iPhone 16 Plus (6.9") | `IPHONE_69` | 1320×2868px | ✅ |
| iPhone 11 Pro Max (6.5") | `IPHONE_65` | 1242×2688px | ✅ |
| iPhone SE 3rd gen (4.7") | `IPHONE_47` | 750×1334px | オプション |

### スクリーンショットリスト（en-US + ja 各4枚）

| 番号 | 画面 | キャプチャ時状態 | キャプションテキスト (en-US) |
|------|------|--------------|----------------------------|
| 01 | HomeView | Free ルーティン3種表示 | "Your Daily Lymph Routine" |
| 02 | SessionView | ステップ2/6、タイマー動作中 | "Step-by-Step, Timer Included" |
| 03 | ProgressDashboardView | 7日ストリーク表示 | "Build Your Streak" |
| 04 | PaywallView | Annual 選択済み | "Unlock Full Access" |

### キャプチャコマンド

```bash
export PATH="/opt/homebrew/bin:/Users/anicca/Library/Python/3.9/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
export ASC_BYPASS_KEYCHAIN=true

# シミュレータ UDID 取得
UDID=$(xcrun simctl list devices available | grep "iPhone 16 Plus" | head -1 | grep -oE '[A-F0-9-]{36}')

# スクリーンショットキャプチャ（en-US）
asc screenshots capture \
  --bundle-id com.aniccafactory.lymphaflow \
  --udid "$UDID" \
  --output-dir screenshots/raw/en-US \
  --output json

# スクリーンショットキャプチャ（ja）
asc screenshots capture \
  --bundle-id com.aniccafactory.lymphaflow \
  --udid "$UDID" \
  --output-dir screenshots/raw/ja \
  --output json

# Koubou フレーミング
asc screenshots frame --input-dir screenshots/raw/en-US --output-dir screenshots/framed/en-US
asc screenshots frame --input-dir screenshots/raw/ja --output-dir screenshots/framed/ja

# en-US / ja MD5 mismatch 確認（ロケール適用確認）
md5 screenshots/framed/en-US/01_home.png
md5 screenshots/framed/ja/01_home.png
```

### アップロードコマンド

```bash
# Version + Localization ID 取得
VERSION_ID=$(asc versions list --app $APP_ID | jq -r '.items[0].id')
EN_LOC_ID=$(asc app-store-version-localizations list --version-id $VERSION_ID | jq -r '.items[] | select(.attributes.locale == "en-US") | .id')
JA_LOC_ID=$(asc app-store-version-localizations list --version-id $VERSION_ID | jq -r '.items[] | select(.attributes.locale == "ja") | .id')

# アップロード
asc screenshots upload --version-localization $EN_LOC_ID --path screenshots/framed/en-US --device-type IPHONE_69
asc screenshots upload --version-localization $JA_LOC_ID --path screenshots/framed/ja --device-type IPHONE_69
```

---

## 4. Privacy

| 設定 | 値 |
|------|-----|
| PrivacyInfo.xcprivacy | `NSPrivacyAccessedAPICategoryUserDefaults: CA92.1` |
| データ収集（サーバー送信） | なし |
| ATT | 使用しない（Rule 20b） |
| ITSAppUsesNonExemptEncryption | false（Info.plist に追加） |
| NSUserTrackingUsageDescription | 禁止（Rule 20b） |
| Privacy Policy URL | https://aniccaai.com/privacy |

### App Privacy Questionnaire 回答

| 質問 | 回答 |
|------|------|
| Data collection | We do not collect data |
| Tracking | No |
| Third-party data | No |

---

## 5. Build & Archive

Source: [asc-xcode-build SKILL] — fastlane 経由でのビルド手順

```bash
export PATH="/opt/homebrew/bin:/Users/anicca/Library/Python/3.9/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
export ASC_BYPASS_KEYCHAIN=true

# Keychain unlock
source ~/.config/mobileapp-builder/.env
security unlock-keychain -p "$KEYCHAIN_PASSWORD" ~/Library/Keychains/login.keychain-db

# Build + Archive + Export
cd LymphaFlowios && fastlane build

# Upload to ASC
cd LymphaFlowios && fastlane upload_to_asc
```

### Fastlane Lanes

| Lane | コマンド | 内容 |
|------|---------|------|
| `test` | `fastlane test` | Unit + Integration テスト |
| `build` | `fastlane build` | Archive → IPA 生成 |
| `upload_to_asc` | `fastlane upload_to_asc` | TestFlight アップロード |
| `release` | `fastlane release` | build + upload + version attach |

---

## 6. TestFlight

```bash
export PATH="/opt/homebrew/bin:/Users/anicca/Library/Python/3.9/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
export ASC_BYPASS_KEYCHAIN=true
source ~/.config/mobileapp-builder/.env

# 最新ビルド取得
BUILD_ID=$(asc builds list --app $APP_ID --sort -uploadedDate --limit 1 | jq -r '.items[0].id')

# Internal Testers グループへ追加
GROUP_ID=$(asc testflight groups list --app $APP_ID | jq -r '.items[0].id')
asc builds add-groups --build $BUILD_ID --group $GROUP_ID

# TestFlight リンク取得
asc testflight builds get-link --app $APP_ID --build $BUILD_ID

# テスター追加
asc testflight beta-testers invite --app $APP_ID --email daisuke134@gmail.com
```

### ベータテスト計画

| フェーズ | テスター数 | 期間 | フォーカス |
|---------|---------|------|---------|
| Internal | 1-3人 | 2日 | 基本動作・クラッシュ確認 |
| External | 5-10人 | 3日 | UX フィードバック・Paywall テスト |

---

## 7. Submission

```bash
export PATH="/opt/homebrew/bin:/Users/anicca/Library/Python/3.9/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
export ASC_BYPASS_KEYCHAIN=true
source ~/.config/mobileapp-builder/.env

# バージョン存在確認
asc versions list --app $APP_ID

# Submit for Review
SUBMISSION_ID=$(asc review submissions-create --app $APP_ID | jq -r '.data.id')
asc review submissions-items-add --submission $SUBMISSION_ID
asc review submissions-submit --submission $SUBMISSION_ID
```

---

## 8. Review Notes

| 項目 | 内容 |
|------|------|
| Demo Account Required | false |
| AI Usage | No AI used. Static curated content only (Rule 21). |
| Subscription Management | In-app via Settings > Apple ID. Cancel anytime. |
| Offline Operation | Fully functional offline (local UserDefaults + bundled JSON). |
| Medical Device Disclaimer | This app is for wellness purposes only and is NOT a medical device or treatment. |
| Contact Information | support@aniccaai.com |

---

## 9. Age Rating

Source: [Apple App Store Age Rating](https://developer.apple.com/help/app-store-connect/manage-app-information/set-your-apps-age-rating/) — 「All 22 items must be set.」

| カテゴリ | 回答 |
|---------|------|
| Cartoon or Fantasy Violence | NONE |
| Realistic Violence | NONE |
| Prolonged Graphic or Sadistic Realistic Violence | NONE |
| Sexual Content or Nudity | NONE |
| Graphic Sexual Content and Nudity | NONE |
| Profanity or Crude Humor | NONE |
| Horror / Fear Themes | NONE |
| Medical / Treatment Information | NONE |
| Alcohol, Tobacco, or Drug Use or References | NONE |
| Simulated Gambling | NONE |
| Contests or Sweepstakes | NONE |
| Unrestricted Web Access | NONE |
| User-Generated Content | NONE |
| Mature / Suggestive Themes | NONE |
| Explicit Sexual Content and Nudity | NONE |
| Historical or Fictional War Crimes | NONE |
| Hate Themes | NONE |
| Threatening and Bullying Behavior | NONE |
| Gross or Indecent Content | NONE |
| Weapons | NONE |
| Drugs | NONE |
| Controversial Content | NONE |

---

## 10. Hotfix Protocol

Source: [git-workflow.md Hotfix] — 「release ブランチで修正 → dev に cherry-pick」

```bash
# バグ発見時
git checkout release/1.0.0
git checkout -b hotfix/crash-fix

# 修正実施
# ...

# バージョンバンプ: 1.0.0 → 1.0.1
# Info.plist の CFBundleShortVersionString を更新

git commit -m "fix: [hotfix] crash on session complete"
git push origin hotfix/crash-fix

# dev に cherry-pick
git checkout dev
git cherry-pick <commit-hash>

# テスト → リビルド → 再提出
cd LymphaFlowios && fastlane test
cd LymphaFlowios && fastlane release
```

---

## 11. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-03-xx | Initial release — 12 routines, Paywall, Streak tracking |
