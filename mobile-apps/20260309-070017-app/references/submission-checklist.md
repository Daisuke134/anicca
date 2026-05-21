# App Store 提出前チェックリスト

mobileapp-builder PHASE 11 で実行する全項目。1件でも FAIL → STOP。

---

## A: コード品質

| # | チェック項目 | コマンド |
|---|------------|---------|
| A1 | Greenlight CRITICAL = 0 | `greenlight preflight <app_dir>` |
| A2 | PrivacyInfo.xcprivacy 存在確認 | Greenlight が検出 |
| A3 | Privacy Policy リンク（Settings画面） | Greenlight が検出 |

---

## B: ビルド

Source: Apple Developer News (https://developer.apple.com/news/?id=ey6d8onl)
> "Starting in April 2026, all submissions must use the iOS 26 SDK or later."

| # | チェック項目 | コマンド |
|---|------------|---------|
| B1 | ビルドが VALID（processingState = VALID） | `asc builds list --app <APP_ID> --sort -uploadedDate --limit 1` |
| B2 | バージョンが存在 | `asc versions list --app <APP_ID>` |
| B3 | **iOS 26 SDK 以降でビルド（2026年4月以降必須）** | `xcodebuild -version \| grep "Xcode 26"` または `xcodebuild -showBuildSettings \| grep SDKROOT` で SDK = iphonesimulator26.0 以上を確認 |

---

## C: RevenueCat

| # | チェック項目 | 確認方法 |
|---|------------|---------|
| C1 | Weekly product が RevenueCat に登録済み | RC Dashboard |
| C2 | Monthly product が RevenueCat に登録済み | RC Dashboard |
| C3 | Annual product が RevenueCat に登録済み | RC Dashboard |
| C4 | Offering に Weekly + Monthly + Annual の3パッケージ（Rule 41） | RC Dashboard |

---

## D: IAP（最重要 — Guideline 2.1 拒否防止）

| # | チェック項目 | コマンド |
|---|------------|---------|
| D1 | `asc validate subscriptions` blocking = 0 | `asc validate subscriptions --app <APP_ID>` |
| D2 | Weekly: state = READY_TO_SUBMIT | `asc subscriptions get --id <WEEKLY_ID>` |
| D3 | Monthly: state = READY_TO_SUBMIT | `asc subscriptions get --id <MONTHLY_ID>` |
| D4 | Annual: state = READY_TO_SUBMIT | `asc subscriptions get --id <ANNUAL_ID>` |
| D5 | Weekly: 175 territories 価格設定済み | `asc subscriptions prices list --id <WEEKLY_ID> --paginate \| python3 -c "import sys,json;d=json.load(sys.stdin);print(len(d['data']))"` |
| D6 | Monthly: 175 territories 価格設定済み | `asc subscriptions prices list --id <MONTHLY_ID> --paginate \| python3 -c "import sys,json;d=json.load(sys.stdin);print(len(d['data']))"` |
| D7 | Annual: 175 territories 価格設定済み | `asc subscriptions prices list --id <ANNUAL_ID> --paginate \| python3 -c "import sys,json;d=json.load(sys.stdin);print(len(d['data']))"` |
| D8 | Weekly: App Review Screenshot 添付済み | `asc subscriptions review-screenshots create --subscription-id <WEEKLY_ID> --file ./paywall-review.png` → "already exists" |
| D9 | Monthly: App Review Screenshot 添付済み | `asc subscriptions review-screenshots create --subscription-id <MONTHLY_ID> --file ./paywall-review.png` → "already exists" |
| D10 | Annual: App Review Screenshot 添付済み | `asc subscriptions review-screenshots create --subscription-id <ANNUAL_ID> --file ./paywall-review.png` → "already exists" |
| D11 | Weekly: en-US ローカライゼーション設定済み | `asc subscriptions localizations list --subscription-id <WEEKLY_ID>` |
| D12 | Monthly: en-US ローカライゼーション設定済み | `asc subscriptions localizations list --subscription-id <MONTHLY_ID>` |
| D13 | Annual: en-US ローカライゼーション設定済み | `asc subscriptions localizations list --subscription-id <ANNUAL_ID>` |

---

## E: アプリメタデータ

| # | チェック項目 | コマンド |
|---|------------|---------|
| E1 | en-US タイトル・サブタイトル・説明文設定済み | `asc localizations list --version <VERSION_ID>` |
| E2 | ja タイトル・サブタイトル・説明文設定済み | 同上 |
| E3 | キーワード設定済み（en-US + ja） | 同上 |
| E4a | iPhone 6.7" スクリーンショット 3枚（1290×2796）EN + JA | `asc screenshots list --app <APP_ID> --locale en-US` |
| E4b | **iPad 13" スクリーンショット 3枚（2048×2732）EN + JA（Submit 必須 — 2026-02-28 確認）** | version localization の appScreenshotSets で APP_IPAD_PRO_3GEN_129 を確認 |
| E5 | アイコン（1024×1024）設定済み | Xcode プロジェクト内確認 |
| E6 | Privacy Policy URL 設定済み | `asc app-infos list --app <APP_ID>` |
| E7 | **copyright（著作権）設定済み（Submit 必須 — 2026-02-28 確認）** | `asc versions get --version-id <VERSION_ID> --output json \| python3 -c "import sys,json;d=json.load(sys.stdin);print(d['data']['attributes'].get('copyright','NOT SET'))"` |
| E8 | **contentRightsDeclaration 設定済み（Submit 必須 — 2026-02-28 確認）** | `curl -H "Authorization: Bearer $TOKEN" https://api.appstoreconnect.apple.com/v1/appStoreVersions/<VERSION_ID> \| python3 -c "import sys,json;d=json.load(sys.stdin);print(d['data']['attributes'].get('contentRightsDeclaration','NOT SET'))"` |
| E9 | **app pricing 設定済み（Submit 必須 — 2026-02-28 確認）** | `asc apps prices list --app <APP_ID>` → 1件以上 |
| E10 | **App Privacy（asc web privacy apply + publish で自動設定済み）** | ASC Web → App Privacy が「編集済み」状態であること |
| E11 | **usesIdfa 設定済み（INVALID_BINARY 防止 — 2026-02-28 確認）** | `curl -H "Authorization: Bearer $TOKEN" https://api.appstoreconnect.apple.com/v1/appStoreVersions/<VERSION_ID> \| python3 -c "import sys,json;d=json.load(sys.stdin);print(d['data']['attributes'].get('usesIdfa','NOT SET'))"` → `False` であること |
| E12 | **primaryCategory 設定済み（INVALID_BINARY 防止 — 2026-02-28 確認）** | `curl -H "Authorization: Bearer $TOKEN" https://api.appstoreconnect.apple.com/v1/appInfos/<APP_INFO_ID>/primaryCategory` → id が返ること |

---

## S: 署名ヘルスチェック（PHASE 2.5 で実施済みであることを確認）

| # | チェック項目 | コマンド |
|---|------------|---------|
| S1 | 有効な Distribution cert が1件以上ある | `asc certificates list --type IOS_DISTRIBUTION --output json \| python3 -c "import sys,json;d=json.load(sys.stdin);valid=[c for c in d['data'] if c['attributes'].get('certificateState')!='REVOKED'];print('PASS' if valid else 'FAIL: no valid cert')"` |
| S2 | Keychain に REVOKED Distribution 証明書がない | `security find-identity -v -p codesigning \| grep -c REVOKED \|\| true` → 0 であること |
| S3 | アプリの Provisioning Profile がインストール済み | `ls ~/Library/MobileDevice/Provisioning\ Profiles/ \| grep <PROFILE_UUID>` → 存在すること |
| S4 | Fastfile が `signingStyle: "manual"` を使用している | Fastfile の `export_options` ブロックを目視確認 |

**⚠️ S1〜S4 が1件でも FAIL の場合は PHASE 2.5 SIGNING PREFLIGHT を実行してから PHASE 10 に進む。INVALID_BINARY の主原因。**

---

## F: 提出前の最終確認

| # | チェック項目 | 方法 |
|---|------------|------|
| F1 | 全 D チェック（D1-D9）が PASS した後に提出する | フェーズ順序を守る |
| F2 | キャンセル→再提出ではなく初回提出 | MISSING_METADATA のまま提出していない |
| F3 | GATE 1〜11 全て PASS（PHASE 11 参照） | copyright + content rights + pricing + iPad スクショ + usesIdfa + primaryCategory + iOS 26 SDK 全確認 |
| F4 | S1〜S4 全て PASS（署名ヘルスチェック） | INVALID_BINARY / ITMS-90035 を事前に防ぐ |

---

## よくあるリジェクト理由と防ぎ方

| リジェクト理由 | 防ぐチェック | 対処 |
|--------------|------------|------|
| Guideline 2.1（IAP products not submitted for review） | D1-D13 全部 PASS | `asc subscriptions prices import` + screenshot + localization |
| **INVALID_BINARY（iOS 26 SDK未使用、2026年4月以降）** | B3 | Xcode 26 でビルドし直す |
| Guideline 5.1.1（Privacy Policy） | A3, E6 | Settings 画面に Privacy Policy リンク追加 |
| Guideline 2.3.3（Metadata misrepresentation） | E1-E4 | スクショと実機能が一致しているか確認 |
| PrivacyInfo.xcprivacy 不足 | A2 | Greenlight が検出するので CRITICAL=0 を確認 |
| App is not eligible for submission（iPad スクショ未設定） | E4b | PHASE 9 Step 3b で APP_IPAD_PRO_3GEN_129 をアップロード |
| App is not eligible for submission（copyright 未設定） | E7 | `asc versions update --copyright "2025 <Name>"` |
| App is not eligible for submission（content rights 未設定） | E8 | curl PATCH で `contentRightsDeclaration: DOES_NOT_USE_THIRD_PARTY_CONTENT` |
| App is not eligible for submission（pricing 未設定） | E9 | `appPriceSchedules` POST で無料または有料を設定 |
| **INVALID_BINARY（usesIdfa 未設定）** | E11 | `curl PATCH /v1/appStoreVersions/<ID>` で `{"attributes":{"usesIdfa":false}}` を設定（PHASE 9 Step 6）|
| **INVALID_BINARY（primaryCategory 未設定）** | E12 | `curl PATCH /v1/appInfos/<ID>` で `relationships.primaryCategory.data.id = "UTILITIES"` を設定（PHASE 4）|
