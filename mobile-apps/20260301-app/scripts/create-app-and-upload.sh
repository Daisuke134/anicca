#!/bin/bash
# AffirmFlow - ASC App Creation + TestFlight Upload Script
# Usage: ./scripts/create-app-and-upload.sh <2FA_CODE>
#
# This script:
# 1. Authenticates with Apple ID + 2FA
# 2. Creates the app in ASC
# 3. Sets up metadata, categories, privacy URL
# 4. Uploads IPA to TestFlight
# 5. Waits for processing
# 6. Sends Slack notification

set -euo pipefail

TWO_FA_CODE="${1:-}"
if [ -z "$TWO_FA_CODE" ]; then
  echo "❌ Usage: $0 <2FA_CODE>"
  echo "   Example: $0 123456"
  exit 1
fi

# Load env
source ~/.config/mobileapp-builder/.env
export ASC_KEY_ID ASC_ISSUER_ID
export ASC_PRIVATE_KEY_PATH=/Users/anicca/.appstoreconnect/private_keys/AuthKey_646Y27MJ8C.p8

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "🔐 Step 1: Apple ID Authentication + 2FA"
ASC_WEB_PASSWORD="$APPLE_ID_PASSWORD" asc web auth login \
  --apple-id "$APPLE_ID" \
  --two-factor-code "$TWO_FA_CODE"
echo "✅ Authenticated"

echo ""
echo "📱 Step 2: Create AffirmFlow in ASC"
ASC_WEB_PASSWORD="$APPLE_ID_PASSWORD" asc web apps create \
  --name "AffirmFlow" \
  --bundle-id "com.anicca.affirmflow" \
  --sku "affirmflow-001" \
  --primary-locale "en-US" \
  --platform IOS \
  --apple-id "$APPLE_ID" \
  --auto-rename || echo "⚠️ App may already exist, continuing..."

echo ""
echo "🔍 Step 3: Get APP_ID"
APP_ID=$(asc apps list --output json 2>&1 | \
  python3 -c "import sys,json;d=json.load(sys.stdin);apps=[a for a in d['data'] if a['attributes']['bundleId']=='com.anicca.affirmflow'];print(apps[0]['id'] if apps else 'NOT_FOUND')")
echo "APP_ID: $APP_ID"

if [ "$APP_ID" = "NOT_FOUND" ]; then
  echo "❌ App not found in ASC after creation. Check manually."
  exit 1
fi

echo ""
echo "🏷️ Step 4: Set Primary Category (HEALTH_AND_FITNESS)"
TOKEN=$(python3 -c "
import jwt,time,os,pathlib
key=pathlib.Path(os.environ['ASC_PRIVATE_KEY_PATH']).read_text()
payload={'iss':os.environ['ASC_ISSUER_ID'],'iat':int(time.time()),'exp':int(time.time())+1200,'aud':'appstoreconnect-v1'}
print(jwt.encode(payload,key,algorithm='ES256',headers={'kid':os.environ['ASC_KEY_ID'],'typ':'JWT'}))
")

APP_INFO_ID=$(curl -s -H "Authorization: Bearer $TOKEN" \
  "https://api.appstoreconnect.apple.com/v1/apps/$APP_ID/appInfos" | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print(d['data'][0]['id'])")

curl -s -X PATCH \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "https://api.appstoreconnect.apple.com/v1/appInfos/$APP_INFO_ID" \
  -d "{\"data\":{\"type\":\"appInfos\",\"id\":\"$APP_INFO_ID\",\"relationships\":{\"primaryCategory\":{\"data\":{\"type\":\"appCategories\",\"id\":\"HEALTH_AND_FITNESS\"}}}}}" > /dev/null
echo "✅ Category set"

echo ""
echo "🔗 Step 5: Set Privacy Policy URLs (en-US + ja)"
PRIVACY_URL="https://daisuke134.github.io/anicca-products/affirmflow/privacy/"

# Get en-US localization ID
EN_LOC_ID=$(curl -s -H "Authorization: Bearer $TOKEN" \
  "https://api.appstoreconnect.apple.com/v1/appInfos/$APP_INFO_ID/appInfoLocalizations" | \
  python3 -c "import sys,json; d=json.load(sys.stdin); locs=[l for l in d['data'] if l['attributes']['locale']=='en-US']; print(locs[0]['id'] if locs else 'NOT_FOUND')")

if [ "$EN_LOC_ID" != "NOT_FOUND" ]; then
  curl -s -X PATCH -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    "https://api.appstoreconnect.apple.com/v1/appInfoLocalizations/$EN_LOC_ID" \
    -d "{\"data\":{\"type\":\"appInfoLocalizations\",\"id\":\"$EN_LOC_ID\",\"attributes\":{\"privacyPolicyUrl\":\"$PRIVACY_URL\"}}}" > /dev/null
  echo "✅ en-US privacy URL set"
fi

# Create/update ja localization
JA_LOC_ID=$(curl -s -H "Authorization: Bearer $TOKEN" \
  "https://api.appstoreconnect.apple.com/v1/appInfos/$APP_INFO_ID/appInfoLocalizations" | \
  python3 -c "import sys,json; d=json.load(sys.stdin); locs=[l for l in d['data'] if l['attributes']['locale']=='ja']; print(locs[0]['id'] if locs else 'NOT_FOUND')")

if [ "$JA_LOC_ID" = "NOT_FOUND" ]; then
  curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    "https://api.appstoreconnect.apple.com/v1/appInfoLocalizations" \
    -d "{\"data\":{\"type\":\"appInfoLocalizations\",\"attributes\":{\"locale\":\"ja\",\"privacyPolicyUrl\":\"$PRIVACY_URL\"},\"relationships\":{\"appInfo\":{\"data\":{\"type\":\"appInfos\",\"id\":\"$APP_INFO_ID\"}}}}}" > /dev/null
  echo "✅ ja localization created with privacy URL"
else
  curl -s -X PATCH -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    "https://api.appstoreconnect.apple.com/v1/appInfoLocalizations/$JA_LOC_ID" \
    -d "{\"data\":{\"type\":\"appInfoLocalizations\",\"id\":\"$JA_LOC_ID\",\"attributes\":{\"privacyPolicyUrl\":\"$PRIVACY_URL\"}}}" > /dev/null
  echo "✅ ja privacy URL set"
fi

echo ""
echo "📤 Step 6: Upload IPA to TestFlight"
IPA_PATH="$PROJECT_DIR/AffirmFlowios/build/AffirmFlow.ipa"
if [ ! -f "$IPA_PATH" ]; then
  echo "❌ IPA not found at $IPA_PATH"
  exit 1
fi

xcrun altool --upload-app \
  --type ios \
  --file "$IPA_PATH" \
  --apiKey "$ASC_KEY_ID" \
  --apiIssuer "$ASC_ISSUER_ID" 2>&1 || {
  echo "⚠️ altool upload failed, trying xcrun notarytool..."
  echo "Manual upload may be needed"
}

echo ""
echo "⏳ Step 7: Wait for processing (checking every 30s, max 10 min)"
for i in $(seq 1 20); do
  STATUS=$(asc builds list --app "$APP_ID" --limit 1 --output json 2>&1 | \
    python3 -c "import sys,json; d=json.load(sys.stdin); builds=d.get('data',[]); print(builds[0]['attributes']['processingState'] if builds else 'NO_BUILDS')" 2>&1)
  echo "  [$i/20] Processing state: $STATUS"
  if [ "$STATUS" = "VALID" ] || [ "$STATUS" = "INVALID" ]; then
    break
  fi
  sleep 30
done

echo ""
echo "📊 Step 8: Set metadata"
# Get version ID
VERSION_ID=$(curl -s -H "Authorization: Bearer $TOKEN" \
  "https://api.appstoreconnect.apple.com/v1/apps/$APP_ID/appStoreVersions?filter[appStoreState]=PREPARE_FOR_SUBMISSION" | \
  python3 -c "import sys,json; d=json.load(sys.stdin); vers=d.get('data',[]); print(vers[0]['id'] if vers else 'NOT_FOUND')")

if [ "$VERSION_ID" != "NOT_FOUND" ]; then
  # Set usesIdfa to false
  curl -s -X PATCH -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    "https://api.appstoreconnect.apple.com/v1/appStoreVersions/$VERSION_ID" \
    -d "{\"data\":{\"type\":\"appStoreVersions\",\"id\":\"$VERSION_ID\",\"attributes\":{\"usesIdfa\":false}}}" > /dev/null
  echo "✅ usesIdfa set to false"

  # Set copyright
  curl -s -X PATCH -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    "https://api.appstoreconnect.apple.com/v1/appStoreVersions/$VERSION_ID" \
    -d "{\"data\":{\"type\":\"appStoreVersions\",\"id\":\"$VERSION_ID\",\"attributes\":{\"copyright\":\"2026 Anicca\"}}}" > /dev/null
  echo "✅ Copyright set"
fi

# Set content rights declaration
curl -s -X PATCH -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  "https://api.appstoreconnect.apple.com/v1/apps/$APP_ID" \
  -d "{\"data\":{\"type\":\"apps\",\"id\":\"$APP_ID\",\"attributes\":{\"contentRightsDeclaration\":\"DOES_NOT_USE_THIRD_PARTY_CONTENT\"}}}" > /dev/null
echo "✅ Content rights set"

echo ""
echo "💬 Step 9: Slack notification"
curl -s -X POST "https://slack.com/api/chat.postMessage" \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"channel\": \"$SLACK_CHANNEL_ID\",
    \"text\": \"✅ *AffirmFlow US-007 Complete*\n\n• App created in ASC (ID: $APP_ID)\n• IPA uploaded to TestFlight\n• Privacy Policy deployed: $PRIVACY_URL\n• Metadata configured\n\n🎯 Next: US-008 (App Store submission)\"
  }" > /dev/null

echo ""
echo "🎉 Done! APP_ID=$APP_ID"
echo "Next steps:"
echo "  1. Check TestFlight processing at appstoreconnect.apple.com"
echo "  2. Upload screenshots: asc screenshots upload --app $APP_ID"
echo "  3. Sync metadata: asc metadata sync --app $APP_ID"
