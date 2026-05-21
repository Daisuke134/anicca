# US-008: Release Preparation

Source: rshankras WORKFLOW.md Phase 6 + rudrankriyam asc-* skills

## Source Skills (参考のみ — 読み込み不要。コマンドは下記各 Step にインライン)
元ネタ:
- US-008a (Screenshots): axe-ios-simulator, asc-shots-pipeline
- US-008b (Metadata): asc-metadata-sync
- US-008c (Build+Upload): asc-xcode-build
- US-008d (Compliance): asc-release-flow
- US-008e (Preflight+TF): release-review, asc-submission-health

## Quality Gate (MANDATORY — US-007 検証)
```bash
xcodebuild test -scheme <AppName> -destination "platform=iOS Simulator,id=$UDID_69" || { echo "GATE FAIL: tests broken"; exit 1; }
# StoreKit Configuration は不要（uiPreviewMode で代替。us-005b 参照）
test $(ls maestro/*.yaml 2>/dev/null | wc -l) -ge 6 || { echo "GATE FAIL: need 6+ Maestro flows"; exit 1; }
```


## Step 0: Greenlight ASC Scan (MANDATORY)

Source: Greenlight README
> "greenlight scan --app-id $APP_ID  # App Store Connect API checks"

**ASC メタデータが完全か確認:**

```bash
# Greenlight ASC scan を実行
GL_SCAN=$(greenlight scan --app-id $APP_ID --tier 1 --format json 2>&1)
GL_PASSED=$(echo "$GL_SCAN" | jq '.summary.passed // false')

if [ "$GL_PASSED" != "true" ]; then
  echo "❌ Greenlight ASC scan failed"
  echo "$GL_SCAN" | jq '.findings[] | select(.severity >= 2)'
  # 問題を修正して再実行
fi

echo "✅ Greenlight ASC scan passed"
```

### PROHIBITED
- ⛔ ASC scan が失敗したまま passes:true にするな

## Step 0b: Localization File Check (MANDATORY — before screenshots)

Source: Apple Developer Documentation
https://developer.apple.com/documentation/xcode/localizing-and-varying-text-with-a-string-catalog
> 「Use a string catalog to translate text, handle plurals, and vary the text your app displays on specific devices.」

Source: fline.dev — The Missing String Catalogs FAQ
https://www.fline.dev/the-missing-string-catalogs-faq-for-xcode-15/
> 「Xcode automatically extracts any added localizations from your source code, the source of truth for your localizations is reversed here and lies in your code.」

**ja スクショが英語になる原因は `.xcstrings` が存在しないこと。**
`String(localized:)` を使っていても翻訳ファイルがなければフォールバック（= 英語）のまま。

```bash
# .xcstrings の存在チェック
XCODE_DIR=$(find . -name "*.xcodeproj" -maxdepth 2 | head -1 | xargs dirname)
XCSTRINGS=$(find "$XCODE_DIR" -name "*.xcstrings" -not -path "*/build/*" -not -path "*/.build/*" -not -path "*/SourcePackages/*" | head -1)

if [ -z "$XCSTRINGS" ]; then
  echo "⚠️ .xcstrings not found — ja screenshots will show English"
  echo "Creating Localizable.xcstrings with Japanese translations..."

  # 1. 全 String(localized:) キーを収集
  KEYS=$(grep -rh 'String(localized: "' "$XCODE_DIR" --include="*.swift" 2>/dev/null \
    | sed 's/.*String(localized: "\([^"]*\)".*/\1/' | sort -u)

  # 2. Localizable.xcstrings を生成（sourceLanguage: en, ja 翻訳付き）
  # CCが各キーの日本語翻訳を作成し、JSON形式で書き出す
  # 3. Xcode プロジェクトに追加（XcodeGen なら project.yml に追加 → xcodegen generate）
  # 4. 再ビルド + 再インストール
  echo "✅ Localizable.xcstrings created — rebuild required"
fi

# .xcstrings 内容検証（MANDATORY — Fix #2: %% タイポ防止）
# Source: Apple Developer Documentation
# https://developer.apple.com/documentation/xcode/localizing-and-varying-text-with-a-string-catalog
# 核心の引用: 「Use a string catalog to translate text」
# → .xcstrings は JSON 形式で % をそのまま書く。String(localized:) は %% エスケープ不要。
XCSTRINGS=$(find . -name "*.xcstrings" -not -path "*/build/*" | head -1)
if [ -n "$XCSTRINGS" ]; then
  DOUBLE_PCT=$(grep -c '%%' "$XCSTRINGS" 2>/dev/null || echo "0")
  if [ "$DOUBLE_PCT" -gt 0 ]; then
    echo "❌ FAIL: $DOUBLE_PCT occurrences of %% found in $XCSTRINGS"
    echo "String(localized:) does not require %% escaping. Auto-fixing..."
    sed -i '' 's/%%/%/g' "$XCSTRINGS"
    echo "✅ AUTO-FIXED: %% → %"
  fi
fi
```

### PROHIBITED
- ⛔ `.xcstrings` なしで ja スクショを撮って passes:true にするな
- ⛔ `.lproj/Localizable.strings` は使わない（Xcode 15+ は `.xcstrings` が標準）

## Step 1: Screenshots（ロケール別キャプチャ + ASC アップロード）

Source: asc-shots-pipeline SKILL.md Section 3-6
Verified: 2026-03-06 DeskStretch 実機テスト済み — en-US 4枚 + ja 4枚 = 8枚 COMPLETE

### スクショ保存先（明示）
```bash
# $APP_DIR = ralph.sh の作業ディレクトリ（例: mobile-apps/desk-stretch）
# スクショは $APP_DIR/screenshots/raw/{en-US,ja}/ に保存する（worktree内ではない）
SCREENSHOTS_DIR="$APP_DIR/screenshots/raw"
mkdir -p "$SCREENSHOTS_DIR/en-US" "$SCREENSHOTS_DIR/ja"
```

### 使用デバイス（固定）

Source: Apple ASC Help — Screenshot specifications
https://developer.apple.com/help/app-store-connect/reference/screenshot-specifications
> 6.5" Display: "Required if app runs on iPhone and screenshots for 6.9" display aren't provided"
> 13"/12.9" Display: "Required if app runs on iPad"

| デバイス | 解像度 | ASC device-type | 必須条件 |
|---------|--------|----------------|---------|
| iPhone 16 Pro Max | 1320x2868 | IPHONE_69 | 常に必須（6.9" 提出で全サイズ自動スケール） |

Source: Apple ASC Help — Screenshot specifications (2026)
https://developer.apple.com/help/app-store-connect/reference/screenshot-specifications
核心の引用: 「6.5" Display — Required if screenshots for 6.9" display aren't provided」
核心の引用: 「If screenshots with the accepted sizes aren't provided, scaled screenshots for 6.9" displays are used」
→ 6.9" を提出すれば 6.5"/6.3"/6.1" は Apple が自動スケーリング。1台で全カバー。
Verified: `asc screenshots upload --device-type IPHONE_69` が 1320x2868 を受付（2026-03-08 テスト済み）

- ❌ IPHONE_61 / IPHONE_65 は不要（6.9" が全てカバー）
- ❌ iPad スクショは不要（TARGETED_DEVICE_FAMILY: "1" = iPhone only の場合）

### 1a: シミュレータ準備 + アプリインストール

```bash
export ASC_BYPASS_KEYCHAIN=true

# 6.9" シミュレータのみ使用（Apple が 6.5"/6.3"/6.1" を自動スケール）
UDID_69=$(xcrun simctl list devices available | grep "iPhone16ProMax-69\|iPhone 16 Pro Max\|iPhone 17 Pro Max" | head -1 | grep -oE '[A-F0-9-]{36}')
if [ -z "$UDID_69" ]; then
  RUNTIME=$(xcrun simctl list runtimes | grep "iOS" | tail -1 | grep -oE 'com.apple[^ ]+')
  UDID_69=$(xcrun simctl create "iPhone16ProMax-69" "com.apple.CoreSimulator.SimDeviceType.iPhone-16-Pro-Max" "$RUNTIME")
fi
xcrun simctl boot $UDID_69 2>/dev/null || true

# CRITICAL: Accessibility を有効にする（asc screenshots run --plan + axe の前提条件）
# OFF だと axe が UI ツリーを見れない → children: [] → 全 tap 失敗
# Verified: 2026-03-08 — ON で asc screenshots run --plan 14/14 ALL OK
xcrun simctl spawn $UDID_69 defaults write com.apple.Accessibility AccessibilityEnabled -bool true
xcrun simctl spawn $UDID_69 defaults write com.apple.Accessibility ApplicationAccessibilityEnabled -bool true

# Maestro パス（$HOME が空になる場合があるため絶対パス指定）
MAESTRO="/Users/anicca/.maestro/bin/maestro"
[ -x "$MAESTRO" ] || MAESTRO=$(which maestro 2>/dev/null || echo "maestro")

# アプリビルド + インストール
XCODE_DIR=$(find . -name "*.xcodeproj" -maxdepth 2 | head -1 | xargs dirname)
xcodebuild build -project "$XCODE_DIR"/*.xcodeproj -scheme * \
  -destination "platform=iOS Simulator,id=$UDID_69" -derivedDataPath build/
APP_PATH=$(find . -path "*/Debug-iphonesimulator/*.app" -not -path "*/DerivedData/SourcePackages/*" | head -1)
[ -n "$APP_PATH" ] || { echo "FAIL: .app not found after build"; exit 1; }
xcrun simctl install $UDID_69 "$APP_PATH"
```

### 1b: screenshots.json 生成 + en-US キャプチャ

Verified: `asc screenshots run --plan` E2E テスト済み（2026-03-08 FrostDip: 19/19 steps OK, 5枚 COMPLETE upload）

**axe tap --label は使わない。** `asc screenshots run --plan` で a11y ID ベースの決定論的キャプチャを行う。

```bash
mkdir -p screenshots/raw-69/en-US screenshots/raw-69/ja

# ⚠️ MANDATORY: a11y ID はアプリの Swift コードから grep する（ハードコード厳禁）
# CC が US-006 で書いたコード → CC が grep → CC が plan 生成 → CC が実行
# これにより全アプリで動作する（ボタンラベルに依存しない）
A11Y_IDS=$(grep -rh "accessibilityIdentifier" --include="*.swift" . 2>/dev/null \
  | grep -oE '"[^"]*"' | tr -d '"' | sort -u)
echo "Found a11y IDs: $A11Y_IDS"

# CC は上の a11y ID リストと UX_SPEC のオンボーディングフローから
# screenshots.json を生成する。以下はテンプレート — CC がアプリ固有の値に書き換えること。
cat > .asc/screenshots.json << 'JSON'
{
  "app": {"bundle_id": "$BUNDLE_ID"},
  "output_dir": "./screenshots/raw-69/en-US",
  "steps": [
    {"action": "launch"},
    {"action": "wait", "duration_ms": 3000},
    {"action": "screenshot", "name": "screen1_welcome"},
    {"action": "tap", "id": "<onboarding_button_1_a11y_id>"},
    {"action": "wait", "duration_ms": 2000},
    {"action": "screenshot", "name": "screen2_features"},
    {"action": "tap", "id": "<onboarding_button_2_a11y_id>"},
    {"action": "wait", "duration_ms": 1000},
    {"action": "tap", "id": "<onboarding_continue_a11y_id>"},
    {"action": "wait", "duration_ms": 2000},
    {"action": "screenshot", "name": "screen3_notifications"},
    {"action": "tap", "id": "<onboarding_skip_a11y_id>"},
    {"action": "wait", "duration_ms": 3000},
    {"action": "screenshot", "name": "screen4_paywall"},
    {"action": "tap", "id": "<paywall_maybe_later_a11y_id>"},
    {"action": "wait", "duration_ms": 2000},
    {"action": "screenshot", "name": "screen5_main"}
  ]
}
JSON
# ⚠️ CC は上のテンプレートを実際の a11y ID に書き換えること
# ⚠️ JSON keys: "steps"（not "sequences"）、"duration_ms"（not "seconds"）、"app.bundle_id"

# en-US ロケール明示セット + 完全リセット（uninstall 必須 — defaults delete だけでは不十分）
# Verified: 2026-03-08 FrostDip E2E — uninstall+install でオンボーディング完全リセット確認済み
xcrun simctl terminate $UDID_69 $BUNDLE_ID 2>/dev/null
xcrun simctl spawn $UDID_69 defaults write NSGlobalDomain AppleLanguages -array "en"
xcrun simctl spawn $UDID_69 defaults write NSGlobalDomain AppleLocale "en_US"
xcrun simctl uninstall $UDID_69 $BUNDLE_ID 2>/dev/null || true
xcrun simctl install $UDID_69 "$APP_PATH"

# en-US キャプチャ（1コマンドで全画面）
asc screenshots run \
  --plan .asc/screenshots.json \
  --udid "$UDID_69" \
  --output-dir "./screenshots/raw-69/en-US" \
  --output json

# Fix #1: Paywallスクショはプロダクトページに含めない（DL率低下のため）
# Source: RevenueCat SOSA 2025 — https://www.revenuecat.com/blog/growth/sosa-2025-launch-sub-club/
# → Paywallはアプリ内体験であってスクショに見せるものじゃない
# ※ Paywall（review screenshot用）は Step 1h で別途撮影
# CC は screenshots.json で Paywall 画面を撮っても ASC アップロード時に除外すること
```

**⚠️ screenshots.json ルール（E2E テスト実証済み）:**

| キー | 正しい値 | 間違い（使うな） |
|------|---------|----------------|
| アクション配列 | `"steps"` | ~~`"sequences"`~~ |
| 待機時間 | `"duration_ms": 3000` | ~~`"seconds": 3`~~ |
| アプリ指定 | `"app": {"bundle_id": "..."}` | ~~`"bundle_id": "..."`~~（トップレベル不可） |
| タップ | `"id": "<a11y_id>"` | ~~`"label": "Next"`~~（ハードコード厳禁） |
| 要素待ち | `"wait_for"` + `"timeout"` | ~~通知ダイアログ出る画面では使うな~~（タイムアウトする） |

**⚠️ 通知許可画面の注意:**
- `onboarding_enable_notifications` をタップすると iOS の通知ダイアログが出る
- ダイアログが `wait_for` をブロックしてタイムアウトする
- → `onboarding_skip_notifications` を使ってダイアログを回避すること
- Verified: 2026-03-08 FrostDip E2E — skip で Paywall に正常到達

### 1b2: タブ画面キャプチャ（defaults write + relaunch）

SwiftUI の TabView のタブボタンは axe に見えない（children: [] — SwiftUI の既知の制限）。
代わりに `defaults write` でタブ state を直接書き換えて relaunch → simctl screenshot する。

```bash
# CC は grep で実際のキー名を動的に取得すること（アプリごとに異なる）
TAB_KEY=$(grep -roh '@AppStorage("\([^"]*\)")' --include="*.swift" "$XCODE_DIR" 2>/dev/null \
  | grep -i "tab\|selected" | head -1 | sed 's/@AppStorage("//;s/")//')
ONBOARDING_KEY=$(grep -roh '@AppStorage("\([^"]*\)")' --include="*.swift" "$XCODE_DIR" 2>/dev/null \
  | grep -i "onboard\|completed" | head -1 | sed 's/@AppStorage("//;s/")//')

# タブ 0 は asc screenshots run --plan で撮影済み。残りのタブ:
for TAB_INDEX in 1 2 3; do
  xcrun simctl terminate "$UDID_69" "$BUNDLE_ID" 2>/dev/null
  xcrun simctl uninstall "$UDID_69" "$BUNDLE_ID" 2>/dev/null || true
  xcrun simctl install "$UDID_69" "$APP_PATH"
  xcrun simctl spawn "$UDID_69" defaults write "$BUNDLE_ID" "$ONBOARDING_KEY" -bool true
  xcrun simctl spawn "$UDID_69" defaults write "$BUNDLE_ID" "$TAB_KEY" -int "$TAB_INDEX"
  xcrun simctl launch "$UDID_69" "$BUNDLE_ID"
  sleep 3
  xcrun simctl io "$UDID_69" screenshot "./screenshots/raw-69/${LOCALE}/screen$((TAB_INDEX + 2))_tab${TAB_INDEX}.png"
done
```

Verified: 2026-03-08 FrostDip — Timer(0)/History(1)/Progress(2) 全て異なる MD5 で撮影成功。

### 1c: ja キャプチャ（同じ screenshots.json で OK — a11y ID は言語非依存）

Verified: 2026-03-08 FrostDip E2E — ja locale で 19/19 steps OK

```bash
# ja ロケール切替（uninstall → install 必須 — defaults delete だけではリセット不十分）
# Verified: 2026-03-08 — defaults delete のみだとオンボーディング完了状態が残り a11y ID が見えない
xcrun simctl terminate $UDID_69 $BUNDLE_ID 2>/dev/null
xcrun simctl spawn $UDID_69 defaults write NSGlobalDomain AppleLanguages -array "ja"
xcrun simctl spawn $UDID_69 defaults write NSGlobalDomain AppleLocale "ja_JP"
xcrun simctl uninstall $UDID_69 $BUNDLE_ID 2>/dev/null || true
xcrun simctl install $UDID_69 "$APP_PATH"

# ja キャプチャ（同じ plan で OK — a11y ID はロケール非依存）
asc screenshots run \
  --plan .asc/screenshots.json \
  --udid "$UDID_69" \
  --output-dir "./screenshots/raw-69/ja" \
  --output json
```

### 1d: en-US に戻す（後続ステップのため）

```bash
xcrun simctl spawn $UDID_69 defaults write NSGlobalDomain AppleLanguages -array "en"
xcrun simctl spawn $UDID_69 defaults write NSGlobalDomain AppleLocale "en_US"
```

### 1e: MD5 検証（MUST — 2段階チェック）

```bash
# チェック1: en-US vs ja が異なること（ロケール適用確認）
EN_MD5=$(/usr/bin/openssl dgst -md5 screenshots/raw-69/en-US/screen1_welcome.png | awk '{print $2}')
JA_MD5=$(/usr/bin/openssl dgst -md5 screenshots/raw-69/ja/screen1_welcome.png | awk '{print $2}')
[ "$EN_MD5" != "$JA_MD5" ] || { echo "FAIL: en/ja screenshots identical — locale not applied"; exit 1; }

# チェック2: 同一ロケール内の重複がないこと（画面遷移確認）
# ⚠️ これが前回欠けていた。3/4枚が同じ画面だったのに検出できなかった
EN_DUPES=$(/usr/bin/openssl dgst -md5 screenshots/raw-69/en-US/*.png | awk '{print $2}' | sort | uniq -d | wc -l | tr -d ' ')
JA_DUPES=$(/usr/bin/openssl dgst -md5 screenshots/raw-69/ja/*.png | awk '{print $2}' | sort | uniq -d | wc -l | tr -d ' ')
[ "$EN_DUPES" -eq 0 ] || { echo "FAIL: $EN_DUPES duplicate screenshots in en-US — screen navigation failed"; exit 1; }
[ "$JA_DUPES" -eq 0 ] || { echo "FAIL: $JA_DUPES duplicate screenshots in ja — screen navigation failed"; exit 1; }

echo "✅ MD5 checks passed: en≠ja, no same-locale duplicates"
```

### 1f: デバイスフレーム — DISABLED (2026-03-07). Skip to 1f2.

生スクショをそのままアップロード。Koubou / `kou generate` は使わない。

### 1f2: ASC アップロード（フレーム付きスクショ）

```bash
# version-localization ID 取得
EN_LOC_ID=$(asc localizations list --version "$VERSION_ID" --output json \
  | jq -r '.data[] | select(.attributes.locale=="en-US") | .id')
JA_LOC_ID=$(asc localizations list --version "$VERSION_ID" --output json \
  | jq -r '.data[] | select(.attributes.locale=="ja") | .id')
# ⚠️ ja が存在しない場合は REST API で作成:
# POST /v1/appStoreVersionLocalizations { locale: "ja", appStoreVersion: { id: VERSION_ID } }

# 6.9" のみアップロード（Apple が 6.5"/6.3"/6.1" を自動スケール）
# Verified: asc screenshots upload --device-type IPHONE_69 accepts 1320x2868 (2026-03-08)
# ⚠️ IPHONE_69 → ASC は APP_IPHONE_67 にマッピング（Apple仕様、正常動作）
# Verified: 2026-03-08 FrostDip — en-US 5枚 + ja 5枚 全て COMPLETE、displayType=APP_IPHONE_67
asc screenshots upload \
  --version-localization "$EN_LOC_ID" \
  --path "./screenshots/raw-69/en-US" \
  --device-type "IPHONE_69"

asc screenshots upload \
  --version-localization "$JA_LOC_ID" \
  --path "./screenshots/raw-69/ja" \
  --device-type "IPHONE_69"
```

**⚠️ 正しいフラグ（2026-03-08 実証済み）:**

| フラグ | 値 | 説明 |
|--------|-----|------|
| `--version-localization` | LOC_ID | ロケール別の version-localization ID |
| `--path` | ディレクトリパス | ファイルではなくディレクトリを指定 |
| `--device-type` | `IPHONE_69` | iPhone 16 Pro Max 1320×2868（ASC は `APP_IPHONE_67` にマッピング — 正常動作） |

Verified: 2026-03-08 FrostDip E2E — `IPHONE_69` で upload → `displayType: APP_IPHONE_67` で COMPLETE（Apple が 6.9" を 6.7" カテゴリで処理する仕様）

**❌ 存在しないフラグ（使うな）:** `--locale`, `--file`, `--app`, `--display-type`

### 1g: アップロード検証（MUST — Evidence Over Assertion）

```bash
EN_COUNT=$(asc screenshots list --version-localization "$EN_LOC_ID" --output json | jq '.data | length')
JA_COUNT=$(asc screenshots list --version-localization "$JA_LOC_ID" --output json | jq '.data | length')
[ "$EN_COUNT" -ge 4 ] || { echo "FAIL: en-US has $EN_COUNT screenshots (need ≥4)"; exit 1; }
[ "$JA_COUNT" -ge 4 ] || { echo "FAIL: ja has $JA_COUNT screenshots (need ≥4)"; exit 1; }
echo "✅ Screenshots: en-US=$EN_COUNT, ja=$JA_COUNT"
```

### 1h: Subscription Review Screenshot（Paywall スクショ → IAP 審査用）

依存: US-005b で `$MONTHLY_ID`, `$ANNUAL_ID` が .env に記録済み
依存: US-006 で `hasCompletedOnboarding` キーが実装済み

⚠️ US-005b Step 6.6 から移動。アプリ実装後（US-006 完了後）でないと Paywall 画面が存在しない。

```bash
# === Review Screenshot（Paywall 画面 — asc screenshots run で決定論的にキャプチャ） ===
# Verified: 2026-03-08 FrostDip E2E — axe 不使用、a11y ID ベースで Paywall + Annual 選択状態キャプチャ成功
# ⚠️ axe tap --label / axe describe-ui は使わない（5回連続失敗の主犯 — P1/P2/P3）

# 1. 完全リセット（uninstall 必須）
xcrun simctl terminate "$UDID_69" "$BUNDLE_ID" 2>/dev/null
xcrun simctl uninstall "$UDID_69" "$BUNDLE_ID" 2>/dev/null || true
xcrun simctl install "$UDID_69" "$APP_PATH"

# 2. review-screenshots.json 生成（CC が a11y ID を grep して書く）
# ⚠️ a11y ID はアプリごとに異なる — CC が Swift コードから取得すること:
#   grep -rh "accessibilityIdentifier" --include="*.swift" Views/Onboarding/ Views/Paywall/
cat > .asc/review-screenshots.json << 'JSON'
{
  "app": {"bundle_id": "$BUNDLE_ID"},
  "output_dir": "/tmp/review-screenshots",
  "steps": [
    {"action": "launch"},
    {"action": "wait", "duration_ms": 3000},
    {"action": "tap", "id": "<onboarding_start_a11y_id>"},
    {"action": "wait", "duration_ms": 2000},
    {"action": "tap", "id": "<experience_select_a11y_id>"},
    {"action": "wait", "duration_ms": 1000},
    {"action": "tap", "id": "<onboarding_continue_a11y_id>"},
    {"action": "wait", "duration_ms": 2000},
    {"action": "tap", "id": "<onboarding_skip_notifications_a11y_id>"},
    {"action": "wait", "duration_ms": 3000},
    {"action": "tap", "id": "<paywall_plan_annual_a11y_id>"},
    {"action": "wait", "duration_ms": 1000},
    {"action": "screenshot", "name": "paywall_review"}
  ]
}
JSON
# ⚠️ CC は上のテンプレートを実際の a11y ID に書き換えること
# ⚠️ 通知画面では skip を使う（enable だと iOS ダイアログが出て後続 step がブロックされる）

# 3. 撮影
mkdir -p /tmp/review-screenshots
asc screenshots run \
  --plan .asc/review-screenshots.json \
  --udid "$UDID_69" \
  --output-dir /tmp/review-screenshots \
  --output json

# 4. 検証: 100KB 未満 = 空画面の可能性
PW_SIZE=$(stat -f%z /tmp/review-screenshots/paywall_review.png)
[ "$PW_SIZE" -gt 100000 ] || { echo "FAIL: paywall screenshot too small ($PW_SIZE bytes)"; exit 1; }

# 5. Monthly + Annual 両方にアップロード
source ~/.config/mobileapp-builder/.env
asc subscriptions review-screenshots create \
  --subscription-id "$MONTHLY_ID" \
  --file /tmp/review-screenshots/paywall_review.png

asc subscriptions review-screenshots create \
  --subscription-id "$ANNUAL_ID" \
  --file /tmp/review-screenshots/paywall_review.png

echo "✅ Review screenshots uploaded for MONTHLY=$MONTHLY_ID and ANNUAL=$ANNUAL_ID"
```

**検証済みコマンド（2026-03-04 Chi Daily + 2026-03-08 FrostDip で実証）:**

| コマンド | 用途 |
|---------|------|
| `asc subscriptions review-screenshots create --subscription-id $ID --file PATH` | review screenshot アップロード |
| `asc subscriptions review-screenshots get --id $SHOT_ID` | アップロード確認 |
| `asc subscriptions review-screenshots delete --id $SHOT_ID --confirm` | 既存削除（更新時のみ） |

**PROHIBITED:**
- ⛔ axe tap --label 禁止（5回連続失敗の主犯 — ラベルがアプリごとに異なりハードコード不可能）
- ⛔ axe describe-ui 禁止（空ツリー問題 P1 — 信頼性なし）
- ⛔ 座標タップ禁止（デバイスごとに異なる）
- ⛔ screenshot-creator スキル禁止
- ⛔ Pencil MCP 禁止
- ⛔ Python/Pillow/ImageMagick 禁止
- ⛔ `--locale` フラグ禁止（存在しない。`--version-localization LOC_ID` を使う）
- ⛔ `--file` フラグ禁止（screenshots upload では存在しない。`--path DIR` を使う）
- ⛔ Koubou / `kou generate` 禁止（DISABLED 2026-03-07）。生スクショをそのままアップロードすること
- ⛔ Home 画面を Review Screenshot にアップロードするな（Paywall 画面を撮れ）
- ⛔ Paywall 画面をプロダクトページスクショに含めるな（Fix #1: レビュースクショ用の Step 1h でのみ使う）

## Step 2: Metadata Sync（asc localizations upload で一括）

Verified: `asc localizations upload --dry-run` テスト済み（2026-03-08）

```bash
# .strings ファイル生成（CC が PRD から内容を生成）
mkdir -p metadata/app-info metadata/version

# app-info (name, subtitle, privacyPolicyUrl) — 全ロケール
cat > metadata/app-info/en-US.strings << 'STREOF'
"name" = "<APP_NAME>";
"subtitle" = "<SUBTITLE>";
"privacyPolicyUrl" = "https://aniccafactory.com/privacy";
STREOF

cat > metadata/app-info/ja.strings << 'STREOF'
"name" = "<APP_NAME_JA>";
"subtitle" = "<SUBTITLE_JA>";
"privacyPolicyUrl" = "https://aniccafactory.com/privacy";
STREOF

# version (description, keywords, supportUrl, whatsNew) — 全ロケール
cat > metadata/version/en-US.strings << 'STREOF'
"description" = "<DESCRIPTION>";
"keywords" = "<KEYWORDS>";
"supportUrl" = "https://aniccafactory.com/support";
"whatsNew" = "Initial release";
STREOF

cat > metadata/version/ja.strings << 'STREOF'
"description" = "<DESCRIPTION_JA>";
"keywords" = "<KEYWORDS_JA>";
"supportUrl" = "https://aniccafactory.com/support";
"whatsNew" = "初回リリース";
STREOF

# 一括アップロード（2コマンドで全ロケール完了）
asc localizations upload --app "$APP_ID" --type app-info --path metadata/app-info/
asc localizations upload --version "$VERSION_ID" --path metadata/version/
```
CRITICAL: Privacy Policy URL は en-US AND ja 両方必須（Rule 7）

## Step 3: Build + Upload (Fix #6: xcodebuild + ASC API Key auth)

Source: Apple Developer Documentation — xcodebuild
https://developer.apple.com/documentation/xcode/distributing-your-app-for-testing-and-release
核心の引用: 「xcodebuild supports authentication via App Store Connect API keys using -authenticationKeyPath, -authenticationKeyID, and -authenticationKeyIssuerID」

```bash
source ~/.config/mobileapp-builder/.env

# Archive（xcodebuild + ASC API Key auth — headless CI 向け正規手順）
xcodebuild archive \
  -project *.xcodeproj -scheme "$SCHEME" \
  -archivePath build/app.xcarchive \
  -destination "generic/platform=iOS" \
  -allowProvisioningUpdates \
  -authenticationKeyPath "$ASC_KEY_PATH" \
  -authenticationKeyID "$ASC_KEY_ID" \
  -authenticationKeyIssuerID "$ASC_ISSUER_ID" \
  CODE_SIGN_STYLE=Automatic \
  DEVELOPMENT_TEAM="$TEAM_ID"

# Export
cat > build/exportOptions.plist << 'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>method</key><string>app-store</string>
  <key>signingStyle</key><string>automatic</string>
  <key>uploadSymbols</key><true/>
  <key>compileBitcode</key><false/>
</dict></plist>
PLIST

xcodebuild -exportArchive \
  -archivePath build/app.xcarchive \
  -exportPath build/export \
  -exportOptionsPlist build/exportOptions.plist \
  -allowProvisioningUpdates \
  -authenticationKeyPath "$ASC_KEY_PATH" \
  -authenticationKeyID "$ASC_KEY_ID" \
  -authenticationKeyIssuerID "$ASC_ISSUER_ID"

# Upload
IPA_PATH=$(find build/export -name "*.ipa" | head -1)
xcrun altool --upload-app -f "$IPA_PATH" -t ios \
  --apiKey "$ASC_KEY_ID" --apiIssuer "$ASC_ISSUER_ID"
```

## Step 4: Review Details (PATCH 4)
```bash
asc review details-create --app $APP_ID --version-id $VERSION_ID \
  --demo-account-required false
```
Source: Apple ASC API (https://developer.apple.com/documentation/appstoreconnectapi/create_an_app_store_review_detail)
> 「Add App Store review details including contact and demo account information」
CRITICAL: デフォルトが true → 明示的に false を指定しないとデモアカウント未入力で提出ブロック

## Step 5: Copyright + Age Rating + Encryption + Content Rights

Source: Apple ASC Help — Required, localizable, and editable properties
https://developer.apple.com/help/app-store-connect/reference/app-information/required-localizable-and-editable-properties
> Platform version information: Copyright is a required field

Source: Apple ASC API — AppStoreVersion.Attributes
https://developer.apple.com/documentation/appstoreconnectapi/appstoreversion/attributes
> `copyright` — string attribute on AppStoreVersion

```bash
source ~/.config/mobileapp-builder/.env

# Copyright (REQUIRED — 未設定だと提出時にエラー)
CURRENT_YEAR=$(date +%Y)
DEVELOPER_NAME="Daisuke Kobayashi"
asc versions update --version-id "$VERSION_ID" --copyright "$CURRENT_YEAR $DEVELOPER_NAME"

# Age Rating: all 22 items NONE (FOUR_PLUS)
asc age-rating set --app "$APP_ID" --version-id "$VERSION_ID" \
  --violence-cartoon NONE --violence-realistic NONE --violence-graphic NONE \
  --sexual-content NONE --nudity NONE --profanity NONE --mature-themes NONE \
  --horror NONE --gambling NONE --alcohol-tobacco NONE --medical NONE \
  --contests NONE --unrestricted-web-access false --gambling-simulated false

# Review Details
# Verified 2026-03-08: Apple AUTO-CREATES review details when version is created.
# details-create is NEVER needed. Always use details-for-version → details-update.
# Phone format: "+81 80 1234 5678" (space-separated, NOT +819000000000)

DETAIL_ID=$(asc review details-for-version --version-id "$VERSION_ID" --output json \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['id'])")

asc review details-update \
  --id "$DETAIL_ID" \
  --contact-first-name "Daisuke" \
  --contact-last-name "Kobayashi" \
  --contact-phone "+81 80 1234 5678" \
  --contact-email "keiodaisuke@gmail.com" \
  --notes "No login required. Open app and use immediately." \
  --output json
```

### Encryption (ITSAppUsesNonExemptEncryption)

⚠️ `asc encryption set` は**存在しない**。Info.plist に `ITSAppUsesNonExemptEncryption = NO` を設定する（US-005a で済み）。
ASC 側での宣言は不要（Info.plist の値が自動的に使われる）。

### Content Rights

⚠️ `asc content-rights set` は**存在しない**。REST API で設定:

```bash
curl -s -X PATCH "https://api.appstoreconnect.apple.com/v1/apps/$APP_ID" \
  -H "Authorization: Bearer $JWT" -H "Content-Type: application/json" \
  -d "{\"data\":{\"type\":\"apps\",\"id\":\"$APP_ID\",\"attributes\":{
    \"contentRightsDeclaration\":\"DOES_NOT_USE_THIRD_PARTY_CONTENT\"
  }}}"
```

Verified: 2026-03-06 desk-stretch で `PATCH /v1/apps/{id}` 成功確認済み。

## Step 6: Availability + Pricing
CRITICAL: availability BEFORE pricing（Rule 6）

⚠️ `asc availability set --territories ALL` は**存在しない**。REST API v2 を使う:

```bash
# 1. 全テリトリー取得
TERRITORIES=$(asc pricing territories list --paginate | python3 -c "
import json,sys
d=json.load(sys.stdin)
print([t['id'] for t in d['data']])
")

# 2. POST /v2/appAvailabilities with territoryAvailabilities
PAYLOAD=$(python3 -c "
import json
territories = $TERRITORIES
ta_data = []
included = []
for i, t in enumerate(territories):
    local_id = f'ta{i}'
    ta_data.append({'type': 'territoryAvailabilities', 'id': local_id})
    included.append({'type': 'territoryAvailabilities', 'id': local_id,
                     'attributes': {'available': True},
                     'relationships': {'territory': {'data': {'type': 'territories', 'id': t}}}})
print(json.dumps({
    'data': {'type': 'appAvailabilities',
             'attributes': {'availableInNewTerritories': True},
             'relationships': {'app': {'data': {'type': 'apps', 'id': '$APP_ID'}},
                              'territoryAvailabilities': {'data': ta_data}}},
    'included': included
}))
")
curl -s -X POST "https://api.appstoreconnect.apple.com/v2/appAvailabilities" \
  -H "Authorization: Bearer $JWT" -H "Content-Type: application/json" \
  -d "$PAYLOAD"

# 3. Pricing
# サブスクアプリ: アプリ本体は FREE（デフォルト）。サブスク pricing は US-005b で設定済み。
# ここでは サブスクが READY_TO_SUBMIT であることを確認するだけ。
# ⚠️ `asc pricing schedule create` は使わない（サブスクアプリには不要、エラーになる）

SUB_GROUP=$(asc subscriptions groups list --app "$APP_ID" --output json | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['data'][0]['id'])" 2>/dev/null)
echo "Subscription group: $SUB_GROUP"

asc subscriptions list --group "$SUB_GROUP" --output json | python3 -c "
import json,sys
d=json.load(sys.stdin)
all_ready=True
for s in d['data']:
    name=s['attributes']['name']
    state=s['attributes']['state']
    period=s['attributes']['subscriptionPeriod']
    ok='✅' if state in ('READY_TO_SUBMIT','WAITING_FOR_REVIEW','APPROVED') else '❌'
    if state not in ('READY_TO_SUBMIT','WAITING_FOR_REVIEW','APPROVED'): all_ready=False
    print(f'{ok} {name}: {state} ({period})')
if all_ready: print('PRICING OK: all subscriptions ready')
else: print('PRICING FAIL: some subscriptions not ready'); sys.exit(1)
"
```

Verified: 2026-03-06 desk-stretch で全コマンド成功確認済み。

## Step 7: release-review 5 Checklists
Read `.claude/skills/release-review/SKILL.md` and execute all 5 checklists.

## Step 7.5: Prerequisites Guard（asc release run の前に全項目を確認・設定）

**MANDATORY — Step 8 の前に実行。** これを飛ばすと dry-run で 7 個の BLOCK が出てリトライ回数を消費する。

```bash
# === Prerequisites（全て冪等 — 設定済みなら上書き、未設定なら新規作成） ===
CURRENT_YEAR=$(date +%Y)
DEVELOPER_NAME="Daisuke Kobayashi"

# 1. Copyright
asc versions update --version-id "$VERSION_ID" --copyright "$CURRENT_YEAR $DEVELOPER_NAME"

# 2. Age Rating（全22項目 NONE）
asc age-rating set --app "$APP_ID" --version-id "$VERSION_ID" \
  --violence-cartoon NONE --violence-realistic NONE --violence-graphic NONE \
  --sexual-content NONE --nudity NONE --profanity NONE --mature-themes NONE \
  --horror NONE --gambling NONE --alcohol-tobacco NONE --medical NONE \
  --contests NONE --unrestricted-web-access false --gambling-simulated false

# 3. Review Details — Apple はバージョン作成時に自動で review detail を作る
DETAIL_ID=$(asc review details-for-version --version-id "$VERSION_ID" --output json \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['id'])")
asc review details-update --id "$DETAIL_ID" \
  --contact-first-name "Daisuke" --contact-last-name "Kobayashi" \
  --contact-phone "+81 80 1234 5678" --contact-email "keiodaisuke@gmail.com" \
  --notes "No login required. Open app and use immediately."

# 4. Category（PRD の appStoreCategory から取得。CC が書き換えること）
asc categories set --app-info "$APP_INFO_ID" --primary HEALTH_AND_FITNESS

# 5. Availability — use REST API v2 (asc availability set doesn't exist)
# Already handled in Step 6 above. Skip if already set.

# 6. Encryption — handled by Info.plist ITSAppUsesNonExemptEncryption=NO (US-005a)
# No ASC API call needed.

# 7. Content Rights — REST API PATCH /v1/apps
curl -s -X PATCH "https://api.appstoreconnect.apple.com/v1/apps/$APP_ID" \
  -H "Authorization: Bearer $JWT" -H "Content-Type: application/json" \
  -d "{\"data\":{\"type\":\"apps\",\"id\":\"$APP_ID\",\"attributes\":{\"contentRightsDeclaration\":\"DOES_NOT_USE_THIRD_PARTY_CONTENT\"}}}"

echo "✅ All prerequisites set"
```

## Step 8: Validate + Submit（asc release run）

Verified: `asc release run --dry-run` テスト済み（2026-03-08）
Source: ASC CLI v0.37.2 PR #849 — "Release orchestration command"

```bash
# metadata-dir for asc release run (JSON format — asc metadata pull で取得)
asc metadata pull --app "$APP_ID" --version "1.0" --dir metadata/release/

# ビルド待ち
BUILD_ID=$(asc builds latest --app "$APP_ID" --output json | jq -r '.data.id')
asc builds wait --app "$APP_ID" --build "$BUILD_ID" --timeout 30m

# プレビュー（MANDATORY — 本番前に必ず dry-run）
asc release run \
  --app "$APP_ID" \
  --version "1.0" \
  --build "$BUILD_ID" \
  --metadata-dir "metadata/release/" \
  --dry-run --pretty

# dry-run 結果を JSON で取得:
DRY_RUN=$(asc release run \
  --app "$APP_ID" \
  --version "1.0" \
  --build "$BUILD_ID" \
  --metadata-dir "metadata/release/" \
  --dry-run --output json 2>&1)

# Closed-Loop: エラーがあれば Decision Table で自動修正 → 再実行
echo "$DRY_RUN" | python3 -c "
import json, sys
d = json.loads(sys.stdin.read())
if d.get('status') == 'completed':
    print('RELEASE_READY')
    sys.exit(0)
checks = []
for step in d.get('steps', []):
    for c in step.get('details', {}).get('report', {}).get('checks', []):
        checks.append(c)
# blocking issues のみ出力
for c in checks:
    if c.get('severity') == 'error':
        print(f\"BLOCK:{c['id']}:{c.get('remediation','')}\")
if not any(c.get('severity') == 'error' for c in checks):
    print('RELEASE_READY')
"
```

### Decision Table（Closed-Loop — MUST follow）

dry-run で `BLOCK:<error.id>` が出たら、以下のテーブルに従って修正 → 再度 dry-run。
**最大 3 回リトライ。** 3 回で解決しなければ `BLOCKED: <error.id>` で停止。

| error.id | CC が修正可能？ | Action |
|----------|---------------|--------|
| `version.state.editable` | ❌ | `WAITING_FOR_HUMAN: version が WAITING_FOR_REVIEW / IN_REVIEW 状態。Apple審査完了待ち` |
| `version.state.rejected` | ✅ | `asc versions create --app $APP_ID --version "1.0.1" --platform IOS` で新version作成 → 再実行 |
| `build.missing` | ✅ | `asc versions attach-build --version-id $VERSION_ID --build $BUILD_ID` → 再実行 |
| `build.processing` | ✅ | `asc builds wait --app $APP_ID --build $BUILD_ID --timeout 30m` → 再実行 |
| `build.expired` | ❌ | `WAITING_FOR_HUMAN: ビルド期限切れ。再アーカイブ+アップロードが必要` |
| `metadata.missing.*` | ✅ | `asc metadata push --app $APP_ID --version "1.0" --dir metadata/release/` → 再実行 |
| `metadata.locale.missing` | ✅ | `asc localizations upload --version $VERSION_ID --path metadata/version/` → 再実行 |
| `screenshots.missing` | ✅ | Step 1 に戻ってスクショ撮影+アップロード → 再実行 |
| `screenshots.incomplete` | ✅ | 不足デバイスのスクショをアップロード → 再実行 |
| `subscriptions.review_readiness.*` | ✅ | `asc subscriptions submit --subscription-id $SUB_ID --confirm` → 再実行 |
| `subscriptions.images.*` (warning) | ⏭️ SKIP | promotional image は optional — warning は無視して `--confirm` 実行可 |
| `subscriptions.pricing.missing` | ✅ | us-005b の pricing set を再実行 → 再実行 |
| `review_details.missing` | ✅ | `asc review details-for-version --version-id $VERSION_ID` → ID取得 → `asc review details-update --id $DETAIL_ID ...` → 再実行 |
| `age_rating.missing` | ✅ | `asc age-rating set --app $APP_ID ...` → 再実行 |
| `copyright.missing` | ✅ | `asc versions update --version-id $VERSION_ID --copyright "$(date +%Y) Daisuke Kobayashi"` → 再実行 |
| `encryption.missing` | ✅ | Info.plist に `ITSAppUsesNonExemptEncryption=NO` 確認 → 再ビルド+アップロード |
| `content_rights.missing` | ✅ | `curl PATCH /v1/apps/$APP_ID` で `contentRightsDeclaration=DOES_NOT_USE_THIRD_PARTY_CONTENT` → 再実行 |
| `privacy.missing` | ❌ | `WAITING_FOR_HUMAN: Privacy Policy 未設定。2FA + asc web privacy apply が必要` |
| unknown error | ❌ | `BLOCKED: unknown error — <full error message>` をログに出力して停止 |

### Closed-Loop 実行フロー

```bash
# MUST: 最大 3 回の自動修正ループ
for ATTEMPT in 1 2 3; do
  echo "=== Release dry-run attempt $ATTEMPT/3 ==="

  DRY_RESULT=$(asc release run \
    --app "$APP_ID" --version "1.0" --build "$BUILD_ID" \
    --metadata-dir "metadata/release/" \
    --dry-run --output json 2>&1)

  STATUS=$(echo "$DRY_RESULT" | python3 -c "import json,sys; print(json.loads(sys.stdin.read()).get('status','error'))")

  if [ "$STATUS" = "completed" ]; then
    echo "✅ dry-run passed — executing --confirm"
    asc release run \
      --app "$APP_ID" --version "1.0" --build "$BUILD_ID" \
      --metadata-dir "metadata/release/" \
      --confirm
    break
  fi

  # エラー抽出 → Decision Table に従って修正
  # CC はここで DRY_RESULT の JSON を読み、上の Decision Table に従って
  # 該当する Action を実行する。WAITING_FOR_HUMAN の場合は即停止。
  echo "$DRY_RESULT" | python3 -c "
import json, sys
d = json.loads(sys.stdin.read())
for step in d.get('steps', []):
  if step.get('status') == 'error':
    print(f\"FAILED_STEP: {step['name']}\")
    print(f\"MESSAGE: {step.get('message','')}\")
    print(f\"REMEDIATION: {step.get('remediation','')}\")
    details = step.get('details', {}).get('report', {}).get('checks', [])
    for c in details:
      if c.get('severity') == 'error':
        print(f\"  BLOCK: {c['id']} — {c['message']}\")
        print(f\"  FIX: {c.get('remediation','')}\")
"
  # CC: Decision Table を参照して修正コマンドを実行
  # WAITING_FOR_HUMAN に該当する場合は break してループ終了
done
```

⚠️ `asc release run` がカバーしないもの → **Step 7.5 で事前設定済み。**
Decision Table は Step 7.5 を飛ばした場合のフォールバック。

Source: rudrankriyam asc-submission-health SKILL.md
> Pre-submission Checklist 7 items

## Step 9: TestFlight Upload + Distribution
Source: asc-testflight-orchestration skill (https://github.com/rudrankriyam/app-store-connect-cli-skills)

```bash
# Attach build to version
# ⚠️ `asc builds attach` は存在しない。`asc versions attach-build` を使う:
# Source: asc CLI v0.36.3 `asc versions --help`
# Source: Apple ASC API — https://developer.apple.com/documentation/appstoreconnectapi/patch-v1-appstoreversions-_id_-relationships-build
# > 「Change the build that is attached to a specific App Store version.」
asc versions attach-build --version-id "$VERSION_ID" --build "$BUILD_ID"

# 9a: Beta group 作成（存在しなければ）
asc testflight beta-groups create --app $APP_ID --name "External Testers"
GROUP_ID=$(asc testflight beta-groups list --app $APP_ID --output json | jq -r '.data[0].id')

# 9b: ビルドをグループに配布
asc builds add-groups --build $BUILD_ID --group $GROUP_ID

# 9c: ベータレビュー提出（invite の前提条件）
asc testflight review submit --build $BUILD_ID --confirm
# externalBuildState が IN_BETA_TESTING になるまで待機（通常24-48時間）
# 確認: asc builds build-beta-detail get --build $BUILD_ID --output json

# 9d: テスター追加 + 招待（ベータレビュー通過後）
source ~/.config/mobileapp-builder/.env
TESTER_EMAIL="${TESTER_EMAIL:-$APPLE_ID}"
asc testflight beta-testers add --app $APP_ID --email "$TESTER_EMAIL" --group "External Testers"
asc testflight beta-testers invite --app $APP_ID --email "$TESTER_EMAIL"

# 9e: テストノート追加
asc builds test-notes create --build $BUILD_ID --locale "en-US" --whats-new "Initial beta test"

# 9f: Public link 取得
TESTFLIGHT_URL=$(asc testflight beta-groups list --app $APP_ID --output json | jq -r '.data[] | select(.attributes.publicLinkEnabled==true) | .attributes.publicLink // empty' | head -1)
if [ -z "$TESTFLIGHT_URL" ]; then
  TESTFLIGHT_URL="https://testflight.apple.com/join/PENDING"
fi
```

### CRITICAL: invite は WAITING_FOR_BETA_REVIEW 通過後でないと「no installable build」で失敗する
- ベータレビュー提出前に invite → 100% 失敗
- ベータレビュー中に invite → 100% 失敗
- ベータレビュー通過後（IN_BETA_TESTING）に invite → 成功


## Step 10: Slack TestFlight 報告

TestFlight ビルドの distribute 完了後、Slack に TestFlight リンクを報告する:

```bash
source ~/.config/mobileapp-builder/.env

# TestFlight リンク取得
TESTFLIGHT_URL=$(asc testflight builds get-link --app $APP_ID --build $BUILD_ID 2>/dev/null || echo "https://testflight.apple.com/join/<GROUP_PUBLIC_LINK>")

# Slack 報告
curl -s -X POST "$SLACK_WEBHOOK_AGENTS" -H 'Content-Type: application/json' \
  -d '{"text":"🧪 TestFlight 準備完了\nApp: <app_name>\nリンク: '"$TESTFLIGHT_URL"'\n↑タップしてテスト可能"}'
```

progress.txt にも記録:
```
TESTFLIGHT_LINK=$TESTFLIGHT_URL
```

## Acceptance Criteria
- Screenshots uploaded to ASC for en-US and ja — IPHONE_69 (6.9" only, Apple auto-scales smaller sizes)
- Subscription review screenshots uploaded for Monthly + Annual
- Metadata synced (en-US + ja)
- Copyright set (REQUIRED field)
- .ipa uploaded (processingState = VALID)
- Build attached to version
- Age Rating set, Review Details set (demoAccountRequired=false)
- Availability + Pricing set (175 territories)
- Encryption + Content Rights set
- asc validate returns Errors=0
- release-review 5 checklists all pass
- TestFlight build distributed
- Slack #metrics notified
