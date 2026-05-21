# 🔴 工場（mobileapp-builder）ギャップ分析: あるべき姿 vs 現状

**対象アプリ:** AffirmFlow / Affirm Well (App ID: 6759867998, Bundle ID: com.anicca.affirmflow)
**分析日:** 2026-03-01
**SKILL.md バージョン:** mobileapp-builder v1.5.0（14 PHASES, 43 CRITICAL RULES）
**通過率:** 8/47 = **17%**

---

## 📊 サマリー

```
┌────────────────────────────────┬──────┬──────┬──────┐
│ カテゴリ                        │  ✅   │  ❌   │ 🔴   │
├────────────────────────────────┼──────┼──────┼──────┤
│ PHASE 4: ASC App Setup        │   0  │   3  │   0  │
│ PHASE 4.5: RC Offerings       │   0  │   3  │   0  │
│ PHASE 5: IAP Pricing          │   0  │   2  │   0  │
│ PHASE 6: IAP Localization     │   0  │   4  │   0  │
│ PHASE 7: IAP Review Screenshot│   0  │   2  │   0  │
│ PHASE 8: IAP Validate         │   0  │   3  │   0  │
│ PHASE 9: App Assets           │   0  │   6  │   0  │
│ PHASE 11: Preflight Gate      │   8  │   8  │   3  │
│ PHASE 11.5: App Privacy       │   0  │   1  │   0  │
│ コード品質                      │   0  │   2  │   2  │
├────────────────────────────────┼──────┼──────┼──────┤
│ 合計                           │   8  │  34  │   5  │
└────────────────────────────────┴──────┴──────┴──────┘
```

---

## 🔴 CRITICAL（これがないと100%リジェクト）

| # | 問題 | 影響する Guideline | 詳細 |
|---|------|-------------------|------|
| 1 | **サブスクリプションが存在しない** — Group も Monthly も Annual も未作成 | Guideline 2.1 | PRD に Freemium Subscription と明記されているがASCにサブスクが0個 |
| 2 | **RevenueCat 未統合** — Mock のまま。課金が動かない | Guideline 2.1 | `SubscriptionService.swift` が `MockPackage`, `MockOffering` を使用。SPM で RC 未導入 |
| 3 | **PrivacyInfo.xcprivacy が存在しない** — ITMS-91061 で自動リジェクト | ITMS-91061 | `find AffirmFlowios -name "PrivacyInfo*"` → 0件 |
| 4 | **App Privacy 未設定** — Web UI から手動設定が必要 | 提出ブロック | ASC Web → App Privacy が未設定。API では設定不可 |
| 5 | **usesIdfa 未設定** — INVALID_BINARY | INVALID_BINARY | API 確認で `usesIdfa: None`（未設定） |

---

## 根本原因

**工場（SKILL.md）の PHASE 4〜8 が完全にスキップされた。** ビルド（PHASE 10）に直行し、IAP/RC/サブスクリプション関連の全工程が未実行。PRD に「Freemium Subscription」「RevenueCat integration」と明記されているにも関わらず、実装は Mock のまま出荷しようとした。

```
PHASE 0-3:  ✅ 実行された（トレンド調査、スペック、スキャフォールド、ビルド）
PHASE 3.5:  ✅ Privacy Policy & Landing Page デプロイ済み
PHASE 4:    ❌ ASC App Setup — サブスクグループ未作成
PHASE 4.5:  ❌ RC Offerings Setup — 完全スキップ
PHASE 5:    ❌ IAP Pricing — 完全スキップ
PHASE 6:    ❌ IAP Localization — 完全スキップ
PHASE 7:    ❌ IAP Review Screenshot — 完全スキップ
PHASE 8:    ❌ IAP Validate STOP GATE — 完全スキップ
PHASE 9:    ⚠️ 部分実行（en-US のみ、ja 未設定、スクショ中身未確認）
PHASE 10:   ✅ Build & Upload 完了（ビルド VALID）
PHASE 11:   ❌ Preflight Gate — 未実行（Greenlight 未実行、PrivacyInfo なし）
PHASE 11.5: ❌ App Privacy — 未設定
PHASE 12:   ❌ Submit — ブロック中（上記の問題で提出不可）
```

---

## PHASE 別 詳細ギャップ

### PHASE 4: ASC APP SETUP

| # | SKILL.md のあるべき姿 | 現状 | 状態 |
|---|---------------------|------|------|
| P4-1 | **Subscription Group 作成** — `asc subscriptions groups create --app 6759867998 --name "AffirmFlow Premium"` | ASC に Subscription Group = **0 個**。`curl .../subscriptionGroups` で確認済み | ❌ 未作成 |
| P4-2 | **Monthly サブスク作成** — `asc subscriptions create --group <GROUP_ID> --product-id "com.anicca.affirmflow.monthly" --name "Monthly" --period ONE_MONTH` | 存在しない | ❌ 未作成 |
| P4-3 | **Annual サブスク作成** — `asc subscriptions create --group <GROUP_ID> --product-id "com.anicca.affirmflow.annual" --name "Annual" --period ONE_YEAR` | 存在しない | ❌ 未作成 |

---

### PHASE 4.5: RC OFFERINGS SETUP

| # | SKILL.md のあるべき姿 | 現状 | 状態 |
|---|---------------------|------|------|
| P4.5-1 | **RevenueCat に Products 登録** — RC Dashboard or MCP で Monthly + Annual を登録 | RC に何も登録されていない | ❌ 未実行 |
| P4.5-2 | **RevenueCat に Offering + Packages 作成** — `mcp__revenuecat__mcp_RC_create_offering` + `mcp_RC_create_package` + `mcp_RC_attach_products_to_package` | RC に何も作成されていない | ❌ 未実行 |
| P4.5-3 | **コードに本物の RevenueCat SDK を統合** — SPM で `RevenueCat` + `RevenueCatUI` を追加。`PaywallView` を使用 | **Mock クラスのまま** — `SubscriptionService.swift` が `MockPackage`, `MockOffering`, `MockOfferings` を定義。SPM で RC 未導入。課金は一切動作しない | ❌ Mock のまま |

**`SubscriptionService.swift` の冒頭:**
```swift
// MARK: - Mock Types (Replace with RevenueCat when SPM is configured)
struct MockPackage: Identifiable, Equatable {
    let id: String
    let identifier: String
    // ...
}
```

---

### PHASE 5: IAP PRICING（★最重要 — Guideline 2.1 拒否の最大原因）

| # | SKILL.md のあるべき姿 | 現状 | 状態 |
|---|---------------------|------|------|
| P5-1 | **Monthly: 175カ国の価格設定** — `python3 scripts/add_prices.py --monthly-sub <ID> --monthly-pp <PP_ID>` で `ok:174, skip:0, fail:0` | サブスク自体が存在しないため価格設定不可 | ❌ |
| P5-2 | **Annual: 175カ国の価格設定** — `python3 scripts/add_prices.py --annual-sub <ID> --annual-pp <PP_ID>` で `ok:174, skip:0, fail:0` | サブスク自体が存在しないため価格設定不可 | ❌ |

---

### PHASE 6: IAP LOCALIZATION

| # | SKILL.md のあるべき姿 | 現状 | 状態 |
|---|---------------------|------|------|
| P6-1 | **Monthly: en-US ローカライゼーション** — `asc subscriptions localizations create --subscription-id <ID> --locale en-US --name "Monthly" --description "..."` | 存在しない | ❌ |
| P6-2 | **Annual: en-US ローカライゼーション** — 同上 | 存在しない | ❌ |
| P6-3 | **Monthly: ja ローカライゼーション** — `--locale ja --name "月額プラン"` | 存在しない | ❌ |
| P6-4 | **Annual: ja ローカライゼーション** — `--locale ja --name "年間プラン"` | 存在しない | ❌ |

---

### PHASE 7: IAP REVIEW SCREENSHOT

| # | SKILL.md のあるべき姿 | 現状 | 状態 |
|---|---------------------|------|------|
| P7-1 | **Monthly: App Review Screenshot** — `asc subscriptions review-screenshots create --subscription-id <MONTHLY_ID> --file ./paywall-review.png` | 存在しない（サブスクが未作成のため添付不可） | ❌ |
| P7-2 | **Annual: App Review Screenshot** — 同上 for Annual | 存在しない | ❌ |

**注意:** `asc subscriptions images create` は**プロモーショナル画像用**であり IAP Review Screenshot ではない。正しいコマンドは `asc subscriptions review-screenshots create`。

---

### PHASE 8: IAP VALIDATE（★STOP GATE — ここを通過するまで先に進んではいけない）

| # | SKILL.md のあるべき姿 | 現状 | 状態 |
|---|---------------------|------|------|
| P8-1 | **`asc validate subscriptions --app 6759867998` blocking = 0** | 検証不可（サブスクが0個） | ❌ |
| P8-2 | **Monthly state = READY_TO_SUBMIT** — `asc subscriptions get --id <ID>` で state 確認 | 存在しない | ❌ |
| P8-3 | **Annual state = READY_TO_SUBMIT** — 同上 | 存在しない | ❌ |

**READY_TO_SUBMIT への遷移条件（3つ全て必要）:**
1. 少なくとも1つのテリトリーに価格設定（175カ国推奨）
2. en-US ローカライゼーション（name フィールド必須）
3. App Store Review Screenshot（1枚）

---

### PHASE 9: APP ASSETS

| # | SKILL.md のあるべき姿 | 現状 | 状態 |
|---|---------------------|------|------|
| P9-1 | **iPhone 6.7" スクショ 3枚 EN** — `screenshot-creator` スキルで生成 → `asc screenshots upload` | ASC に `APP_IPHONE_65` セットは存在するが**中身（実画像）が入っているか未確認** | ⚠️ 要確認 |
| P9-2 | **iPhone 6.7" スクショ 3枚 JA** — ja ローカライゼーション作成後にアップロード | **ja ローカライゼーション自体が存在しない** | ❌ 未作成 |
| P9-3 | **iPad 13" スクショ 3枚 EN** — `APP_IPAD_PRO_3GEN_129` (2048x2732) | ASC にセットは存在するが**中身が入っているか未確認** | ⚠️ 要確認 |
| P9-4 | **iPad 13" スクショ 3枚 JA** — ja ローカライゼーション作成後にアップロード | **ja ローカライゼーション自体が存在しない** | ❌ 未作成 |
| P9-5 | **ja ローカライゼーション（タイトル・説明・キーワード）** — `asc localizations create --version <VERSION_ID> --locale ja --description "..." --keywords "..." --whats-new "..."` | **en-US のみ**。ja 未作成。ASC API 確認済み: ローカライゼーションは en-US の1件のみ | ❌ 未作成 |
| P9-6 | **whatsNew（en-US）** — 初回リリースでも設定必須 | API 確認で **MISSING** | ❌ 未設定 |
| P9-7 | **whatsNew（ja）** — ja ローカライゼーションに含める | ja 自体が存在しない | ❌ 未設定 |
| P9-8 | **usesIdfa = false を明示設定** — PHASE 9 Step 6 で `curl PATCH /v1/appStoreVersions/<ID>` で `{"attributes":{"usesIdfa":false}}` | API 確認で **None（未設定）** | ❌ 未設定 |

---

### PHASE 10: BUILD & UPLOAD

| # | SKILL.md のあるべき姿 | 現状 | 状態 |
|---|---------------------|------|------|
| P10-1 | **`ITSAppUsesNonExemptEncryption = NO` を Info.plist に追加** — PHASE 10 Step 0 で毎回聞かれないようにする | Info.plist に**記載なし**。API で事後的に `usesNonExemptEncryption = false` を設定したが、次回ビルドでも毎回手動設定が必要になる | ⚠️ 毎回手動設定が必要 |
| P10-2 | **ビルドが VALID** | ✅ Build ID `3d57348d` が VALID | ✅ |
| P10-3 | **ビルドがバージョンに紐付け** | ✅ Version `bf509ce6` に紐付け済み | ✅ |

---

### PHASE 11: PREFLIGHT GATE（Submission Checklist 全項目）

#### A: コード品質

| # | チェック項目 | コマンド | 現状 | 状態 |
|---|------------|---------|------|------|
| A1 | Greenlight CRITICAL = 0 | `greenlight preflight <app_dir>` | **未実行** | ❌ |
| A2 | PrivacyInfo.xcprivacy 存在確認 | `find AffirmFlowios -name "PrivacyInfo*"` | **ファイルが存在しない** | 🔴 |
| A3 | Privacy Policy リンク（Settings画面） | Greenlight が検出 | 未確認（Greenlight 未実行） | ⚠️ |

#### B: ビルド

| # | チェック項目 | 現状 | 状態 |
|---|------------|------|------|
| B1 | ビルドが VALID（processingState = VALID） | ✅ Build `3d57348d` VALID | ✅ |
| B2 | バージョンが存在 | ✅ Version 1.0 存在 | ✅ |

#### C: RevenueCat

| # | チェック項目 | 現状 | 状態 |
|---|------------|------|------|
| C1 | Monthly product が RevenueCat に登録済み | **RC に何も登録されていない** | ❌ |
| C2 | Annual product が RevenueCat に登録済み | **RC に何も登録されていない** | ❌ |
| C3 | Offering に Monthly + Annual の両パッケージ | **RC に何も作成されていない** | ❌ |

#### D: IAP（★最重要 — Guideline 2.1 拒否防止）

| # | チェック項目 | 現状 | 状態 |
|---|------------|------|------|
| D0 | `asc subscriptions submit` は使わない。READY_TO_SUBMIT 確認のみ | N/A（サブスクなし） | ❌ |
| D1 | `asc validate subscriptions` blocking = 0 | 検証不可（サブスク 0 個） | ❌ |
| D2 | Monthly: state = READY_TO_SUBMIT | 存在しない | ❌ |
| D3 | Annual: state = READY_TO_SUBMIT | 存在しない | ❌ |
| D4 | Monthly: 175 territories 価格設定済み | 存在しない | ❌ |
| D5 | Annual: 175 territories 価格設定済み | 存在しない | ❌ |
| D6 | Monthly: App Review Screenshot 添付済み | 存在しない | ❌ |
| D7 | Annual: App Review Screenshot 添付済み | 存在しない | ❌ |
| D8 | Monthly: en-US ローカライゼーション設定済み | 存在しない | ❌ |
| D9 | Annual: en-US ローカライゼーション設定済み | 存在しない | ❌ |

#### E: アプリメタデータ

| # | チェック項目 | 現状 | 状態 |
|---|------------|------|------|
| E1 | en-US タイトル・サブタイトル・説明文 | ✅ SET | ✅ |
| E2 | **ja タイトル・サブタイトル・説明文** | **未作成** — ja ローカライゼーション自体がない | ❌ |
| E3 | **ja キーワード** | **未作成** | ❌ |
| E4a | iPhone 6.7" スクショ 3枚 EN + JA | セットあり（中身未確認）。JA は未作成 | ⚠️ |
| E4b | iPad 13" スクショ 3枚 EN + JA | セットあり（中身未確認）。JA は未作成 | ⚠️ |
| E5 | アイコン 1024x1024 | ✅ IPA に Assets.car 含まれている | ✅ |
| E6 | Privacy Policy URL | ✅ SET（GitHub Pages にデプロイ済み） | ✅ |
| E7 | copyright | ✅ `2026 Anicca` | ✅ |
| E8 | contentRightsDeclaration | ✅ `DOES_NOT_USE_THIRD_PARTY_CONTENT`（API で設定済み） | ✅ |
| E9 | app pricing | ✅ FREE 設定済み（price point `10000` = $0.0） | ✅ |
| E10 | **App Privacy（データの使用方法）** | **未設定** — ASC Web から手動設定が必要。API では設定不可 | ❌ |
| E11 | **usesIdfa** | **None（未設定）** — `curl` で確認済み | ❌ |
| E12 | primaryCategory | ✅ `HEALTH_AND_FITNESS` | ✅ |

#### F: 提出前の最終確認

| # | チェック項目 | 現状 | 状態 |
|---|------------|------|------|
| F1 | 全 D チェック（D1-D9）が PASS した後に提出する | **D1-D9 全て FAIL** | ❌ |
| F2 | キャンセル→再提出ではなく初回提出 | 初回提出（まだ提出していない） | ✅ |
| F3 | GATE 1〜11 全て PASS | **多数 FAIL** | ❌ |

---

### PHASE 11.5: APP PRIVACY 手動設定

| # | SKILL.md のあるべき姿 | 現状 | 状態 |
|---|---------------------|------|------|
| P11.5-1 | **ASC Web で App Privacy を設定** — App Privacy → Get Started → カテゴリ選択 → Publish。AffirmFlow はデータ収集なしなので「Data Not Collected」 | **未設定** — ASC Web UI でのみ設定可能。HUMAN STOP ポイント | ❌ |

**設定手順:**
1. https://appstoreconnect.apple.com/apps/6759867998/distribution/privacy にアクセス
2. 「Get Started」をクリック
3. すべてのカテゴリで「No」を選択（データ収集なし）
4. 「Publish」をクリック

---

### コード品質の問題

| # | あるべき姿（SKILL.md / PRD の仕様） | 現状 | 状態 |
|---|-----------------------------------|------|------|
| C-1 | **RevenueCat SDK を SPM で導入** — SKILL.md PHASE 4.5 で `RevenueCat` + `RevenueCatUI` を Package.swift に追加 | **Mock クラスのみ** — `SubscriptionService.swift` が `MockPackage`, `MockOffering`, `MockOfferings` を定義。Purchases フレームワーク未統合。課金は一切動作しない | 🔴 CRITICAL |
| C-2 | **Paywall は RevenueCatUI の PaywallView を使用** — SKILL.md CRITICAL RULE で RevenueCatUI 強制 | **自作 Mock Paywall** — RevenueCatUI の PaywallView を使っていない | ❌ |
| C-3 | **`PrivacyInfo.xcprivacy` をプロジェクトに追加** — SKILL.md PHASE 10 / Submission Checklist A2 で必須 | **ファイル自体が存在しない** — `find AffirmFlowios -name "PrivacyInfo*"` → 0 件。2024年5月以降 ITMS-91061 で自動リジェクト | 🔴 CRITICAL |
| C-4 | **`ITSAppUsesNonExemptEncryption = NO` を Info.plist に追加** — SKILL.md PHASE 10 Step 0 | **Info.plist に未記載** — API で事後設定したが、次回ビルド時にも毎回手動設定が必要 | ❌ |

---

## ✅ 正常に完了している項目

| # | 項目 | 確認方法 | 状態 |
|---|------|---------|------|
| 1 | ASC アプリレコード作成 | App ID: 6759867998, Name: Affirm Well | ✅ |
| 2 | Bundle ID 登録 | com.anicca.affirmflow | ✅ |
| 3 | Primary Category 設定 | HEALTH_AND_FITNESS | ✅ |
| 4 | App Version 作成 | Version 1.0 (bf509ce6) | ✅ |
| 5 | en-US メタデータ | description, keywords, subtitle 設定済み | ✅ |
| 6 | Privacy Policy URL | https://daisuke134.github.io/anicca-products/affirmflow/privacy/ (HTTP 200) | ✅ |
| 7 | App Icon | Assets.xcassets に 1024x1024 含む | ✅ |
| 8 | IPA ビルド & アップロード | Build 202603010840 VALID | ✅ |
| 9 | ビルド紐付け | Version bf509ce6 に紐付け済み | ✅ |
| 10 | copyright | `2026 Anicca` | ✅ |
| 11 | contentRightsDeclaration | `DOES_NOT_USE_THIRD_PARTY_CONTENT` | ✅ |
| 12 | App Pricing | FREE ($0.0) | ✅ |
| 13 | App Availability | 175 territories 有効 | ✅ |
| 14 | Age Rating | 全22項目設定済み | ✅ |
| 15 | Review Details | 連絡先設定済み（demoAccountRequired = false） | ✅ |
| 16 | usesNonExemptEncryption | false（API で設定済み） | ✅ |
| 17 | Signing Chain | Distribution cert + profiles 再構築済み | ✅ |
| 18 | Fastfile | Manual signing 対応済み | ✅ |

---

## 工場改善に向けた教訓

### 1. PHASE 順序の強制が機能していない

**問題:** PHASE 4-8（IAP/RC関連）を飛ばして PHASE 10（ビルド）に直行した。
**原因:** SKILL.md に STOP GATE（PHASE 8）が書いてあるが、エージェントが無視した。
**改善案:** 各 PHASE の冒頭に「前の PHASE の成果物を確認するコマンド」を追加し、確認できなければ進めない仕組みにする。

### 2. Mock → 本番の移行が設計されていない

**問題:** `SubscriptionService.swift` が Mock のまま出荷されようとした。
**原因:** PHASE 3（BUILD）で Mock を使って先にビルドを通すが、PHASE 4.5 で本番に差し替える工程が実行されなかった。
**改善案:** PHASE 10（BUILD & UPLOAD）の冒頭で「Mock が残っていないか grep チェック」を必須にする。

### 3. PrivacyInfo.xcprivacy の自動生成がない

**問題:** ファイル自体が存在しない。
**原因:** PHASE 2（SCAFFOLD）でテンプレートに含まれていない。
**改善案:** PHASE 2 のスキャフォールドテンプレートに PrivacyInfo.xcprivacy を含める。

### 4. `ITSAppUsesNonExemptEncryption` の Info.plist 自動追加がない

**問題:** Info.plist に記載がなく、毎回 API で事後設定が必要。
**原因:** PHASE 2 または PHASE 10 で Info.plist に自動追加する工程がない。
**改善案:** PHASE 2 のスキャフォールドで Info.plist に `ITSAppUsesNonExemptEncryption = NO` を含める。

### 5. ja ローカライゼーションの自動化がない

**問題:** en-US のみ設定され、ja が完全に欠落。
**原因:** PHASE 9 Step 4 で ja ローカライゼーション作成のコマンドはあるが、実行されなかった。
**改善案:** PHASE 9 のチェックリストに「ja ローカライゼーション存在確認」を STOP GATE として追加。

### 6. Submission Checklist（PHASE 11）が実行されていない

**問題:** `references/submission-checklist.md` に50+のチェック項目があるが、一つも実行されなかった。
**原因:** PHASE 4-8 をスキップしたことで PHASE 11 に到達する前に問題が積み上がった。
**改善案:** PHASE 11 を独立した STOP GATE にし、`asc validate` コマンドの結果が全て PASS でないと PHASE 12 に進めないようにする。

---

## 今後のアクション（この分析を元に SKILL.md を改善する）

| # | 改善項目 | 対象 PHASE | 優先度 |
|---|---------|-----------|-------|
| 1 | PHASE 間の依存チェックコマンドを追加 | 全 PHASE | MUST |
| 2 | Mock 残存チェック（`grep -r "Mock" --include="*.swift"`）を PHASE 10 に追加 | PHASE 10 | MUST |
| 3 | PrivacyInfo.xcprivacy をスキャフォールドテンプレートに追加 | PHASE 2 | MUST |
| 4 | ITSAppUsesNonExemptEncryption を Info.plist テンプレートに追加 | PHASE 2 | MUST |
| 5 | ja ローカライゼーション STOP GATE を PHASE 9 に追加 | PHASE 9 | MUST |
| 6 | `asc validate` 全項目 PASS を PHASE 12 の前提条件にする | PHASE 11/12 | MUST |
| 7 | usesIdfa 自動設定を PHASE 9 Step 6 に強制 | PHASE 9 | MUST |
| 8 | whatsNew 設定を PHASE 9 Step 4 に追加 | PHASE 9 | MUST |
