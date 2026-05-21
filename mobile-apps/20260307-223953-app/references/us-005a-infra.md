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

## Step 4.9: iris セッション事前確認 (CRITICAL — 5回以上の繰り返しブロックを防ぐ)

Source: Internal feedback — iris session expiry blocks apps across 5+ factory runs without early detection
> "irisセッション失効 + 2FA必要" appeared in progress.txt of 20260302, 20260303, 20260304 apps (3+ occurrences each)

```bash
source ~/.config/mobileapp-builder/.env
SESSION_STATUS=$(asc web auth status 2>&1)
if echo "$SESSION_STATUS" | grep -q '"authenticated":false\|authenticated.*false\|not authenticated\|session.*expired'; then
  echo "⚠️ iris session EXPIRED — requesting 2FA immediately"
  # Slack通知: 即 WAITING_FOR_HUMAN にして無駄な retry を防ぐ
  curl -s -X POST "$SLACK_WEBHOOK_AGENTS" \
    -H "Content-Type: application/json" \
    -d '{"text":"WAITING_FOR_HUMAN: iris session expired\niPhoneに届く6桁コードを送ってください。\n`asc web auth login --apple-id '"$APPLE_ID"' --password '"$APPLE_ID_PASSWORD"' --two-factor-code <CODE>`"}'
  exit 0  # WAITING_FOR_HUMAN — 次 iteration でコード受信後に再実行
else
  echo "✅ iris session active"
fi
```

**⛔ セッション失効を検出したら即 WAITING_FOR_HUMAN。retry 禁止。**

## Step 5: ASC App Creation（~/bin/asc apps create — Apple ID 認証 + 2FA）

### 5.0: Bundle ID 存在確認（前提チェック）
```bash
# Bundle ID が Step 4.5 で登録済みか確認（未登録だと apps create が 500 エラーで死ぬ）
asc bundle-ids list --output json 2>&1 | jq -e --arg bid "<bundle_id>" '.data[] | select(.attributes.identifier == $bid) | .id' > /dev/null 2>&1 || {
  echo "❌ Bundle ID <bundle_id> not registered. Run Step 4.5 first."
  exit 1
}
echo "✅ Bundle ID confirmed"
```

### 5.1: 2FA コード取得（WAITING_FOR_HUMAN）

⛔ **2FA コードを受け取るまで apps create を実行しない。**
CC は Slack で以下を送信:
```
WAITING_FOR_HUMAN: ASC App Creation
📱 App Store Connect アプリ作成に 2FA コードが必要です（30秒）:
1. 以下のコマンドを実行すると iPhone に 6桁コードが届きます
2. 届いた 6桁コードをこのチャットに貼り付けてください

それだけでOKです。残りは全て自動で行います。
```

### 5.2: アプリ作成（2FA コード受信後）
```bash
source ~/.config/mobileapp-builder/.env
APP_RESULT=$(~/bin/asc apps create \
  --name "<app_name>" \
  --bundle-id "<bundle_id>" \
  --sku "<slug>" \
  --platform IOS \
  --primary-locale "en-US" \
  --apple-id "$APPLE_ID" \
  --password "$APPLE_ID_PASSWORD" \
  --two-factor-code <CODE_FROM_SLACK> \
  --output json 2>&1)

if echo "$APP_RESULT" | jq -e '.data.id' > /dev/null 2>&1; then
  APP_ID=$(echo "$APP_RESULT" | jq -r '.data.id')
  echo "APP_ID=$APP_ID" >> ~/.config/mobileapp-builder/projects/<slug>/.env
  echo "✅ ASC App created: $APP_ID"
else
  echo "❌ App creation failed:"
  echo "$APP_RESULT"
  exit 1
fi
```

### アプリ名の重複
`--auto-rename` はデフォルト true。名前が既に使われている場合、
`<app_name> - <sku>` に自動リネームされる。
作成後に ASC ダッシュボードまたは `asc app-info` で正しい名前に更新可能。

## 次のステップ
US-005a 完了後、`references/us-005b-monetization.md` に進む。
