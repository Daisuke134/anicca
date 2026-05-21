# Release Specification: LumaRed

Source: [Apple App Store Review Guidelines](https://developer.apple.com/app-store/review/guidelines/) — 「Apps must include a privacy policy link and comply with guidelines before submission.」
Source: [App Store Connect Help: Distribute](https://developer.apple.com/help/app-store-connect/manage-builds/upload-builds) — 「Upload builds using Xcode or Transporter. Attach to a version before submission.」
Source: [RevenueCat: App Store Submission](https://www.revenuecat.com/docs/getting-started/entitlements) — 「Set up entitlements and offerings before submitting.」

---

## 1. Pre-Submission Checklist

| # | Gate | Command / Check | Pass Criteria |
|---|------|----------------|---------------|
| 1 | Build compiles | `fastlane build` | Exit code 0 |
| 2 | Unit tests pass | `fastlane test` | 0 failures |
| 3 | Rule 17: No tracking-SDK | `greenlight preflight ./LumaRedios` | CRITICAL: 0 (tracking-SDK 検出なし) |
| 4 | Rule 20: No RC-UI-library | `greenlight preflight ./LumaRedios` | CRITICAL: 0 (RC-UI-library 検出なし) |
| 5 | Rule 20b: No ATT | `greenlight preflight ./LumaRedios` | CRITICAL: 0 (ATT 系 API 検出なし) |
| 6 | Rule 21: No AI SDK | `greenlight preflight ./LumaRedios` | CRITICAL: 0 (third-party-AI-API 検出なし) |
| 7 | Greenlight CRITICAL=0 | `greenlight preflight ./LumaRedios` | CRITICAL: 0 |
| 8 | E2E smoke pass | `maestro test --tags smokeTest maestro/` | All PASS |
| 9 | ASC validate | `asc builds validate --build BUILD_ID` | Errors=0 |

---

## 2. App Store Metadata

Source: [PRD.md §14 App Store Metadata]() — この RELEASE_SPEC は PRD の値と完全一致必須。

### en-US

| フィールド | 値 |
|-----------|-----|
| App Name | LumaRed |
| Subtitle | Red Light Therapy Timer |
| Keywords | red light therapy,photobiomodulation,RLT timer,biohacking,infrared therapy,wellness tracker,light therapy session,red light protocol |
| Description | **LumaRed — Your Red Light Therapy Companion**\n\nOwn a red light therapy device but not sure how to use it? LumaRed gives you science-backed protocols for every body part, a background-compatible timer, and session tracking to build a lasting habit.\n\n**Science-Backed Protocols**\nEvidence-based guidelines for Face & Skin, Joints & Muscles, Wound Healing, Back & Spine, and Full Body — with optimal wavelength, distance, duration, and frequency for each.\n\n**Background Timer**\nStart a session and put your phone down. LumaRed's timer keeps running in the background, completing your session without interruption.\n\n**Session Tracking & Streaks**\nLog every session automatically. Track your streak, cumulative time, and progress over time.\n\n**Free to Start**\n3 protocols and 7-day log history — no credit card required. Upgrade to Premium for all protocols and unlimited history.\n\nNo AI. No backend. No data collection. Everything runs on your device. |
| Promotional Text | Master your red light therapy routine. |
| Privacy Policy URL | https://daisuke134.github.io/anicca-products/apps/lumared/privacy |

### ja

| フィールド | 値 |
|-----------|-----|
| App Name | LumaRed |
| Subtitle | 赤色光療法タイマー |
| Keywords | 赤色光療法,フォトバイオモジュレーション,RLTタイマー,バイオハッキング,赤外線療法,ウェルネス,光療法,赤色光プロトコル |
| Description | **LumaRed — 赤色光療法コンパニオン**\n\n赤色光デバイスを持っているけど、使い方がわからない？LumaRedはエビデンスに基づく部位別プロトコル、バックグラウンド対応タイマー、セッション記録で習慣化をサポートします。\n\n**科学的根拠のあるプロトコル**\n顔・肌、関節・筋肉、傷の回復、背中・脊椎、全身の5部位について、最適な波長・距離・時間・頻度を提供。\n\n**バックグラウンドタイマー**\nセッション開始後はスマホを置いていても大丈夫。バックグラウンドでタイマーが動き続けます。\n\n**セッション記録 & 連続日数**\nすべてのセッションを自動記録。連続日数・累計時間で進捗を可視化。\n\n**まずは無料で試せる**\n3プロトコル・7日分のログは無料。プレミアムにアップグレードすると全プロトコル・無制限ログが使えます。\n\nAI不使用。バックエンド不要。個人情報収集なし。すべてデバイス内で完結。 |
| Promotional Text | 赤色光療法を習慣に。 |
| Privacy Policy URL | https://daisuke134.github.io/anicca-products/apps/lumared/privacy |

### Subscription Pricing (PRD §8 と一致)

| Plan | Price | Trial | Product ID |
|------|-------|-------|-----------|
| Monthly | $4.99/月 | なし | `lumaRed_monthly_499` |
| Annual | $29.99/年 | 7日間 | `lumaRed_annual_2999` |

---

## 3. Screenshots

Source: [CLAUDE.md Rule 24]() — 「IPHONE_69 のみ。1320x2868。Apple が 6.9" から自動スケール。」

| Device | Size | Required | Notes |
|--------|------|---------|-------|
| IPHONE_69 | 1320×2868 | ✅ REQUIRED | 6.9" Pro Max |

**Screenshot List (en-US + ja, 各 4+):**

| # | Screen | Content | accessibilityIdentifier |
|---|--------|---------|------------------------|
| 1 | SC-10 Home | 全5プロトコルカード表示 | `home_protocol_list` |
| 2 | SC-20 Timer | カウントダウン + 円形プログレス | `timer_countdown_label` |
| 3 | SC-30 Dashboard | 連続日数 + 週次チャート | `dashboard_streak_value` |
| 4 | SC-03 Paywall | 価格プラン + CTA | `paywall_subscribe_button` |

**Capture Command:**

```bash
export ASC_BYPASS_KEYCHAIN=true
asc screenshots capture \
  --bundle-id com.aniccafactory.lumared \
  --udid $SIMULATOR_UDID \
  --output-dir screenshots/raw \
  --output json
```

**Upload Command:**

```bash
asc screenshots upload \
  --version-localization $LOC_ID_EN \
  --path screenshots/framed/en-US \
  --device-type IPHONE_69
```

---

## 4. Privacy

Source: [Apple Developer: PrivacyInfo.xcprivacy](https://developer.apple.com/documentation/bundleresources/privacy_manifest_files) — 「Required for apps using UserDefaults accessed API category.」

| 項目 | 値 |
|------|-----|
| PrivacyInfo.xcprivacy | 必須（`NSPrivacyAccessedAPICategoryUserDefaults: CA92.1`） |
| ATT | **不使用（Rule 20b）** |
| データ収集 | なし |
| サーバー送信 | なし |

**App Store Connect App Privacy 回答:**

| 質問 | 回答 |
|------|------|
| データの収集 | いいえ — ユーザーに関するデータを収集しない |
| サードパーティ共有 | なし |
| トラッキング | なし |

---

## 5. Build & Archive

Source: [CLAUDE.md — Fastlane必須]() — 「xcodebuild 直接実行禁止。`cd aniccaios && fastlane <lane>`」

```bash
# Secrets 読み込み
source ~/.config/mobileapp-builder/.env
security unlock-keychain -p "$KEYCHAIN_PASSWORD" ~/Library/Keychains/login.keychain-db

# Build & Archive
fastlane build

# Upload to ASC
fastlane upload
```

**Fastlane lanes:**

| Lane | 用途 |
|------|------|
| `fastlane test` | Unit + Integration テスト実行 |
| `fastlane build` | Archive + IPA 生成 |
| `fastlane upload` | ASC へアップロード |
| `fastlane screenshots` | スクリーンショット取得 |

---

## 6. TestFlight

| 項目 | 詳細 |
|------|------|
| ベータグループ | "Internal Testers"（開発者のみ） |
| テスト期間 | 提出前 3〜7 日 |
| 確認ポイント | オンボーディング完走、購入フロー、バックグラウンドタイマー |

**コマンド:**

```bash
# ビルドをTestFlightグループに追加
asc builds add-groups --build $BUILD_ID --group $BETA_GROUP_ID

# テスター追加
asc testflight beta-testers add --app $APP_ID --email daisuke@example.com --group $BETA_GROUP_ID
```

---

## 7. Submission

Source: [asc-submission-health skill]() — `asc review submissions-create → items-add → submissions-submit`

**Review Details:**

| 項目 | 値 |
|------|-----|
| Demo Account Required | No |
| Contact Information | daisuke@aniccafactory.com |
| Review Notes | This app does not use AI, backend services, or user data collection. All content is static and runs entirely on-device. Red light therapy protocols are based on published photobiomodulation research. Subscriptions managed via RevenueCat + StoreKit 2. |

**Compliance:**

| 質問 | 回答 |
|------|------|
| 暗号化使用 | No（ITSAppUsesNonExemptEncryption = NO） |
| コンテンツ権利 | Does not use third-party content |
| 広告識別子 | No |

---

## 8. Review Notes (審査官向け)

```
LumaRed is a red light therapy companion app that:
- Uses NO AI or machine learning
- Uses NO backend servers
- Collects NO user data
- Stores session logs ONLY in local UserDefaults (on-device)
- Subscriptions: Monthly ($4.99) and Annual ($29.99 with 7-day free trial)
  managed via RevenueCat + StoreKit 2
- All protocols are static educational content based on photobiomodulation research
- Background timer uses BGProcessingTaskRequest for session tracking
- Privacy manifest (PrivacyInfo.xcprivacy) included with CA92.1 for UserDefaults access
```

---

## 9. Age Rating

Source: [Apple Developer: Age Ratings](https://developer.apple.com/app-store/age-ratings/) — 「Set all 22 items. NONE unless content matches category.」

| Category | Rating |
|----------|--------|
| Cartoon or Fantasy Violence | NONE |
| Realistic Violence | NONE |
| Prolonged Graphic or Sadistic Realistic Violence | NONE |
| Profanity or Crude Humor | NONE |
| Mature/Suggestive Themes | NONE |
| Horror/Fear Themes | NONE |
| Medical/Treatment Information | NONE |
| Alcohol, Tobacco, or Drug Use or References | NONE |
| Simulated Gambling | NONE |
| Sexual Content or Nudity | NONE |
| Graphic Sexual Content and Nudity | NONE |
| Unrestricted Web Access | NONE |
| Gambling and Contests | NONE |
| **最終 Age Rating** | **4+** |

---

## 10. Hotfix Protocol

| Step | Command |
|------|---------|
| 1. バージョンバンプ | Xcode → MARKETING_VERSION を 1.0.1 に変更 |
| 2. ビルド番号更新 | Xcode → CURRENT_PROJECT_VERSION を +1 |
| 3. テスト実行 | `fastlane test` |
| 4. アーカイブ | `fastlane build` |
| 5. アップロード | `fastlane upload` |
| 6. TestFlight 確認 | `asc builds list --app $APP_ID --sort -uploadedDate --limit 1` |
| 7. 提出 | `asc review submissions-create --app $APP_ID` |

---

## 11. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-03-xx | 初回リリース。5部位プロトコル、バックグラウンドタイマー、セッションログ、ダッシュボード、RevenueCatサブスク |
