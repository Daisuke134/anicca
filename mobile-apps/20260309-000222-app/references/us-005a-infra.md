# US-005a: Infrastructure (Privacy + ASC App Creation)

Source: rudrankriyam asc-* skills

## Source Skills (参考のみ — 読み込み不要。コマンドは下記に全てインライン)
元ネタ: asc-signing-setup, asc-app-create-ui (証明書・ASCアプリ作成)
※ asc-subscription-localization, asc-ppp-pricing は US-005b で使用

## Quality Gate (MANDATORY — US-004 の成果物検証)
```bash
# 前 US の acceptance criteria を再検証。gate fails → この US を実行しない。
test -f docs/PRD.md || { echo "GATE FAIL: docs/PRD.md missing"; exit 1; }
test -f docs/ARCHITECTURE.md || { echo "GATE FAIL"; exit 1; }
test -f docs/IMPLEMENTATION_GUIDE.md || { echo "GATE FAIL"; exit 1; }
grep -qi "bundle.id\|bundle_id" docs/PRD.md || { echo "GATE FAIL: no bundle_id in PRD"; exit 1; }
```

## Step 1: Privacy Policy + Terms（既存 URL を使用）

カスタム Privacy Policy の生成・ホスティングは不要。ASC 提出時にこれらの URL を設定する。

| ドキュメント | URL |
|-------------|-----|
| **Privacy Policy** | `https://aniccaai.com/privacy` |
| **Terms / EULA** | `https://www.apple.com/legal/internet-services/itunes/dev/stdeula/` |

## Step 2: PrivacyInfo.xcprivacy (PATCH 7)

> ⚠️ **US-006 で実行。** iOS プロジェクト作成後に PrivacyInfo.xcprivacy を追加する。US-005a ではスキップ。

Source: Apple WWDC23 (https://developer.apple.com/videos/play/wwdc2023/10060/)
> 「Third-party SDK developers can include a privacy manifest by creating PrivacyInfo.xcprivacy」

```bash
cat > <AppName>ios/<AppName>/PrivacyInfo.xcprivacy << 'PRIVEOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>NSPrivacyTracking</key><false/>
  <key>NSPrivacyTrackingDomains</key><array/>
  <key>NSPrivacyCollectedDataTypes</key><array/>
  <key>NSPrivacyAccessedAPITypes</key><array/>
</dict>
</plist>
PRIVEOF
```

## Step 3: ITSAppUsesNonExemptEncryption (PATCH 8)

> ⚠️ **US-006 で実行。** Info.plist は iOS プロジェクト作成後に編集する。US-005a ではスキップ。

Source: Apple Developer (https://developer.apple.com/documentation/bundleresources/information-property-list/itsappusesnonexemptencryption)
> 「A Boolean value indicating whether the app uses encryption」

```bash
/usr/libexec/PlistBuddy -c "Add :ITSAppUsesNonExemptEncryption bool false" <AppName>ios/<AppName>/Info.plist
```

## Step 3.5: プロジェクト .env ディレクトリ作成

```bash
# プロジェクト固有の変数はグローバル .env を汚さない
mkdir -p ~/.config/mobileapp-builder/projects/<slug>
```

| ファイル | パス | 内容 |
|---------|------|------|
| **グローバル** | `~/.config/mobileapp-builder/.env` | APPLE_ID, KEYCHAIN_PASSWORD, SLACK_WEBHOOK_AGENTS |
| **プロジェクト** | `~/.config/mobileapp-builder/projects/<slug>/.env` | APP_ID, GROUP_ID, MONTHLY_ID, RC_IOS_PUBLIC_KEY |

## Step 4: Keychain Unlock (PATCH 3)
Source: 12-Factor App (https://12factor.net/config)
> 「stores config in environment variables」

```bash
source ~/.config/mobileapp-builder/.env
security unlock-keychain -p "$KEYCHAIN_PASSWORD" ~/Library/Keychains/login.keychain-db
```


## Step 4.5: Bundle ID 登録（API Key認証 — 完全自動）

```bash
~/bin/asc bundle-ids create \
  --identifier "<bundle_id>" \
  --name "<app_name>" \
  --platform IOS --output json
```

**人間介入不要。** API Key認証で常に自動実行される。

## Step 4.9: iris セッション確認（keychain auto モード — ralph.sh PREFLIGHT で検証済み）

```bash
source ~/.config/mobileapp-builder/.env
# ASC_WEB_SESSION_CACHE_BACKEND は設定しない（auto = keychain 優先）
# ralph.sh PREFLIGHT Check 6 で keychain unlock + session 確認済み

SESSION_STATUS=$(asc web auth status --apple-id "$APPLE_ID" 2>&1)
if echo "$SESSION_STATUS" | grep -q '"authenticated":true'; then
  echo "✅ iris session active"
else
  echo "❌ iris session expired — ralph.sh PREFLIGHT が検知してるはず"
  exit 1
fi
```

## Step 5: ASC App Creation（セッション有効 → 2FA 不要）

### 5.0: Bundle ID 存在確認（前提チェック）
```bash
# Bundle ID が Step 4.5 で登録済みか確認（未登録だと apps create が 500 エラーで死ぬ）
asc bundle-ids list --output json 2>&1 | jq -e --arg bid "<bundle_id>" '.data[] | select(.attributes.identifier == $bid) | .id' > /dev/null 2>&1 || {
  echo "❌ Bundle ID <bundle_id> not registered. Run Step 4.5 first."
  exit 1
}
echo "✅ Bundle ID confirmed"
```

### 5.1: アプリ作成（keychain セッション有効 → 2FA 不要）
```bash
source ~/.config/mobileapp-builder/.env
# ASC_WEB_SESSION_CACHE_BACKEND は設定しない（auto = keychain 優先）

APP_RESULT=$(ASC_WEB_PASSWORD="$APPLE_ID_PASSWORD" asc apps create \
  --name "<app_name>" \
  --bundle-id "<bundle_id>" \
  --sku "<slug>" \
  --platform IOS \
  --primary-locale "en-US" \
  --apple-id "$APPLE_ID" \
  --output json 2>&1)

if echo "$APP_RESULT" | jq -e '.data.id' > /dev/null 2>&1; then
  APP_ID=$(echo "$APP_RESULT" | jq -r '.data.id')
  echo "APP_ID=$APP_ID" >> ~/.config/mobileapp-builder/projects/<slug>/.env
  echo "✅ ASC App created: $APP_ID"
else
  echo "❌ App creation failed: $APP_RESULT"
  exit 1
fi
```

### アプリ名の重複
`--auto-rename` はデフォルト true。名前が既に使われている場合、
`<app_name> - <sku>` に自動リネームされる。
作成後に ASC ダッシュボードまたは `asc app-info` で正しい名前に更新可能。

## Step 5.3: App Privacy（DATA_NOT_COLLECTED — US-009 から移動）

```bash
source ~/.config/mobileapp-builder/.env
source ~/.config/mobileapp-builder/projects/<slug>/.env
# ASC_WEB_SESSION_CACHE_BACKEND は設定しない（auto = keychain 優先）

echo '{"schemaVersion":1,"dataUsages":[{"dataProtections":["DATA_NOT_COLLECTED"]}]}' > /tmp/privacy.json

ASC_WEB_PASSWORD="$APPLE_ID_PASSWORD" asc web privacy apply \
  --app "$APP_ID" --file /tmp/privacy.json --apple-id "$APPLE_ID"
ASC_WEB_PASSWORD="$APPLE_ID_PASSWORD" asc web privacy publish \
  --app "$APP_ID" --confirm --apple-id "$APPLE_ID"

# 検証
PRIVACY_CHECK=$(ASC_WEB_PASSWORD="$APPLE_ID_PASSWORD" asc web privacy pull --app "$APP_ID" --apple-id "$APPLE_ID" 2>&1)
echo "$PRIVACY_CHECK" | grep -q '"published":true' && echo "✅ App Privacy published" || { echo "❌ App Privacy failed"; exit 1; }
```

## 次のステップ
US-005a 完了後、`references/us-005b-monetization.md` に進む。
