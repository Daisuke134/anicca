# Privacy Disclosure Checklist for Factory Apps

**Source**: iOS App Store Review Guidelines 2026 (https://theapplaunchpad.com/blog/app-store-review-guidelines)

**核心の引用**:
> "Privacy and data transparency are major priorities in 2026. Apps must clearly disclose what data they collect, how it is used, and obtain consent before sharing it with third parties, especially AI services."

---

## Default SDK Data Collection (All Factory Apps)

| SDK | データ収集内容 | 用途 | Privacy Label 必須 |
|---|---|---|---|
| RevenueCat | Purchase history, device ID, user ID | サブスクリプション管理 | ✅ Yes |
| Mixpanel | Events, device info, user ID | 分析 | ✅ Yes |
| Singular | Ad interactions, attribution data | マーケティング分析 | ✅ Yes |
| HealthKit | (Optional) 健康データ | アプリ機能による | ✅ Yes (if used) |
| ScreenTime | (Optional) 使用時間 | アプリ機能による | ✅ Yes (if used) |

---

## AI Services Data Sharing

**必須**: ユーザーが AI 機能を使う前に明示的な同意モーダルを表示する。

**含めるべき情報**:
- どの AI プロバイダーを使用するか（例: OpenAI, Anthropic）
- どのようなデータを共有するか（例: "Your journal entries and behavior patterns"）
- データがどのように使用されるか（例: "To generate personalized nudges"）

**実装場所**:
- SwiftUI: `AIConsentView.swift`
- prd.json: `aiDataSharing` フィールド

---

## App Privacy Labels (App Store Connect)

### 必須カテゴリ

1. **Identifiers**
   - Device ID (RevenueCat, Mixpanel, Singular)
   - User ID (RevenueCat, Mixpanel)

2. **Usage Data**
   - Product Interaction (Mixpanel events)
   - Advertising Data (Singular attribution)

3. **Health & Fitness** (if applicable)
   - Health (HealthKit)

4. **Other Data**
   - Other Usage Data (ScreenTime, if used)

### Data Use Purpose

- **Analytics**: Mixpanel, Singular
- **App Functionality**: RevenueCat, HealthKit, ScreenTime
- **Product Personalization**: AI Services (if used)

---

## PrivacyInfo.xcprivacy (自動生成候補)

**Location**: `<AppName>/PrivacyInfo.xcprivacy`

**Template**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>NSPrivacyTracking</key>
    <true/>
    <key>NSPrivacyTrackingDomains</key>
    <array>
        <string>mixpanel.com</string>
        <string>singular.net</string>
    </array>
    <key>NSPrivacyCollectedDataTypes</key>
    <array>
        <dict>
            <key>NSPrivacyCollectedDataType</key>
            <string>NSPrivacyCollectedDataTypeDeviceID</string>
            <key>NSPrivacyCollectedDataTypeLinked</key>
            <true/>
            <key>NSPrivacyCollectedDataTypeTracking</key>
            <true/>
            <key>NSPrivacyCollectedDataTypePurposes</key>
            <array>
                <string>NSPrivacyCollectedDataTypePurposeAnalytics</string>
                <string>NSPrivacyCollectedDataTypePurposeAppFunctionality</string>
            </array>
        </dict>
    </array>
</dict>
</plist>
```

---

## Checklist for Each App

- [ ] RevenueCat SDK included → Add "Purchase History" to Privacy Labels
- [ ] Mixpanel SDK included → Add "Usage Data" to Privacy Labels
- [ ] Singular SDK included → Add "Advertising Data" to Privacy Labels
- [ ] AI features enabled → Add consent modal + "AI Data Sharing" disclosure
- [ ] HealthKit used → Add "Health & Fitness" to Privacy Labels + Info.plist usage description
- [ ] ScreenTime used → Add "Other Usage Data" to Privacy Labels + Info.plist usage description
- [ ] PrivacyInfo.xcprivacy file exists in Xcode project
- [ ] Privacy Policy URL set in App Store Connect

---

## Implementation in ralph.sh

**Suggested Addition**:
```bash
# After project creation, generate PrivacyInfo.xcprivacy
echo "Generating PrivacyInfo.xcprivacy..."
cat > "$APP_DIR/$APP_NAME/PrivacyInfo.xcprivacy" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
...
EOF

# Add to Xcode project
xcodebuild -project "$APP_DIR/$APP_NAME.xcodeproj" -target "$APP_NAME" -configuration Debug -showBuildSettings | grep -q "PrivacyInfo.xcprivacy" || {
    echo "Warning: PrivacyInfo.xcprivacy not added to Xcode project. Manual fix required."
}
```

---

**Last Updated**: 2026-03-28 by factory-bp-efficiency cron
