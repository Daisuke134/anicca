# mobileapp-builder スキル仕様書

**作成日:** 2026-02-23
**ステータス:** 設計中
**目的:** spec.md を渡すだけで、SwiftUI アプリを自律的にビルド・ASC 設定・提出まで完了させる Claude Code スキル。

---

## 概要（What & Why）

### What
`spec.md` を INPUT として受け取り、Swift/SwiftUI アプリを以下まで自律実行する：
- Xcode プロジェクト生成
- アプリ実装（ralph-autonomous-dev）
- ASC サブスクリプション設定（175カ国価格・ローカライズ・スクショ）
- アイコン・スクショ・メタデータ生成
- 提出前ゲート（Greenlight + 追加チェック）
- `fastlane full_release` + `asc submit create`

### Why
Daily Dhamma の提出で3回リジェクトを経験。全ての失敗パターンをこのスキルに封じ込め、次からは **1発承認** を目指す。

---

## 受け入れ条件

| # | 条件 | 確認方法 |
|---|------|---------|
| AC1 | `asc review submissions-list` で state=WAITING_FOR_REVIEW | CLI |
| AC2 | `asc validate subscriptions` で blocking=0 | CLI |
| AC3 | Annual + Monthly 両方が READY_TO_SUBMIT | `asc subscriptions get --id` |
| AC4 | Annual + Monthly それぞれに 175 territories の価格設定 | `asc subscriptions prices list --id --paginate` |
| AC5 | Annual + Monthly それぞれに App Review Screenshot 添付済み | create コマンドが "already exists" を返す |
| AC6 | Annual + Monthly それぞれに en-US ローカライゼーション設定済み | `asc subscriptions localizations list` |
| AC7 | Greenlight CRITICAL = 0 | `greenlight preflight <app_dir>` |
| AC8 | ビルドが VALID で App Store Connect に存在する | `asc builds list` |

---

## トリガーと INPUT

### トリガー方式

```
Anicca (Mac Mini)
    └─ [app-factory cron: 毎晩 23:00 JST]
          └─ spec.md 生成
                └─ exec: claude --print "mobileapp-builder: spec=<PATH>"
                              └─ Claude Code がこのスキルを実行
```

### INPUT 仕様（spec.md の必須フィールド）

```markdown
# <App Name>

## 基本情報
- app_name: Thankful         # Xcode プロジェクト名
- bundle_id: com.daisuke134.<name>
- version: 1.0
- price_monthly_usd: 4.99
- price_annual_usd: 19.99
- output_dir: /Users/cbns03/Downloads/anicca-project/mobile-apps/<name>

## コンセプト
<1-3行。何をするアプリか。誰の苦しみを減らすか>

## 画面構成
- オンボーディング: <ステップ数・内容>
- メイン画面: <コア機能>
- 通知: <通知の種類・目的>
- 設定画面: <必須項目>

## Paywall
- monthly_price: $4.99/month
- annual_price: $19.99/year
- trial: 7日間無料
- cta_text: <ボタン文言>

## メタデータ（ASC）
- title_en: <30文字以内>
- subtitle_en: <30文字以内>
- title_ja: <30文字以内>
- subtitle_ja: <30文字以内>
- keywords_en: <100文字以内>
- keywords_ja: <100文字以内>
- privacy_policy_url: https://aniccaai.com/privacy
```

---

## To-Be: 12フェーズ実行フロー

```
INPUT: spec.md
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│ PHASE 1: VALIDATE INPUT                                  │
│  spec.md の必須フィールド全部あるか確認                    │
│  なければ STOP + エラーレポート                           │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│ PHASE 2: SCAFFOLD                                        │
│  base-template/ をコピー → <output_dir>/<app_name>/      │
│  bundle ID / バージョン / チーム ID を書き換え             │
│  RevenueCat SDK を SPM で追加                            │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│ PHASE 3: BUILD                                           │
│  ralph-autonomous-dev で SwiftUI 実装                    │
│  spec のコア機能・画面構成・通知を実装                     │
│  Paywall: RevenueCat のみ（Superwall 使用禁止）           │
│  Paywall の全要素に accessibilityIdentifier を付与        │
│    paywall_plan_monthly / paywall_plan_yearly             │
│    paywall_cta / paywall_skip / paywall_restore           │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│ PHASE 4: ASC APP SETUP                                   │
│  asc apps create（なければ）                              │
│  asc bundle-ids create（なければ）                        │
│  サブスクリプショングループ作成                            │
│  Monthly + Annual サブスクリプション作成                   │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│ PHASE 5: IAP PRICING（最重要）                            │
│  add_prices.py を実行（Monthly + Annual）                 │
│  US 価格 → Equalization API → 全175カ国に一括追加         │
│  確認: prices list で 175件                               │
│  ※ US+JP のみでは Guideline 2.1 拒否確定                  │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│ PHASE 6: IAP LOCALIZATION                                │
│  en-US: 表示名 + 説明を設定（Monthly / Annual 両方）       │
│  ja: 表示名 + 説明を設定                                  │
│  サブスクリプショングループの en-US + ja も設定             │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│ PHASE 7: IAP REVIEW SCREENSHOT                           │
│  asc-shots-pipeline でシミュレータのペイウォール画面を撮影  │
│    simctl 起動 → AXe でPaywall画面まで操作 → RAWスクショ   │
│  Monthly + Annual それぞれに1枚ずつアップロード            │
│  確認: create コマンドが "already exists" を返すこと       │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│ PHASE 8: IAP VALIDATE（提出前最終確認）                    │
│  asc validate subscriptions --app <APP_ID>               │
│  blocking = 0 でなければ STOP                             │
│  Monthly + Annual 両方が READY_TO_SUBMIT でなければ STOP  │
│  ※ここで STOP = PHASE 5-7 に戻って修正                    │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│ PHASE 9: APP ASSETS                                      │
│  アイコン: infsh FLUX（INFSH_API_KEY）で 1024×1024 生成   │
│  スクショ3枚:                                             │
│    Step 1: asc-shots-pipeline で実画面RAWスクショ撮影      │
│      simctl 起動 → AXe で各画面に移動 → PNG保存           │
│    Step 2: PIL で marketing テキストを上に重ねる           │
│      1枚目: benefit（ペイン直撃コピー）+ 実画面            │
│      2枚目: social proof + 実画面                        │
│      3枚目: core flow（実画面のみ）                       │
│  メタデータ: EN + JA を asc でアップロード                 │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│ PHASE 10: BUILD & UPLOAD                                 │
│  fastlane build（IPA 生成）                               │
│  fastlane upload（ASC にアップロード）                     │
│  処理完了待ち（asc builds list で VALID 確認）             │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│ PHASE 11: PREFLIGHT GATE                                 │
│  Greenlight: greenlight preflight → CRITICAL = 0         │
│  追加チェック（submission-checklist.md の全項目）          │
│  1件でも FAIL → STOP + レポート出力                       │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│ PHASE 12: SUBMIT                                         │
│  asc submit create                                       │
│    --app <APP_ID>                                        │
│    --version-id <VERSION_ID>                             │
│    --build <BUILD_ID>                                    │
│    --confirm                                             │
│  確認: state = WAITING_FOR_REVIEW                        │
└─────────────────────────────────────────────────────────┘
    │
    ▼
OUTPUT: WAITING_FOR_REVIEW ✅
```

---

## As-Is / To-Be

| 項目 | As-Is（現状） | To-Be（このスキル後） |
|------|-------------|---------------------|
| IAP 価格設定 | US+JP のみ手動 | 175カ国を add_prices.py で自動 |
| IAP 提出チェック | なし | PHASE 8 で READY_TO_SUBMIT を強制確認 |
| Paywall ライブラリ | Superwall + RC | RC のみ |
| ビルドコマンド | xcodebuild 直接 | Fastlane のみ（禁止ルール） |
| 提出前ゲート | Greenlight のみ | Greenlight + 追加チェックリスト D6-D10 |
| App Review Screenshot | 手動 | asc-shots-pipeline で自動撮影・アップロード |
| App Store スクショ | 手動 PIL のみ | asc-shots-pipeline（実画面）+ PIL（テキスト合成） |
| アイコン生成 | 手動 | infsh FLUX で自動生成 |
| 出力先 | バラバラ | `mobile-apps/<app-name>/` に統一 |

---

## Preflight チェックリスト追加項目（Daily Dhamma 失敗から）

既存の `app-store-submission-checklist.md` の D セクションに追加必須：

| # | チェック項目 | コマンド |
|---|------------|---------|
| D6 | 全サブスクに 175 territories の価格設定済み | `asc subscriptions prices list --id <ID> --paginate` で 175件確認 |
| D7 | 各サブスクに App Review Screenshot 添付済み | `asc subscriptions review-screenshots create` が "already exists" を返す |
| D8 | 各サブスクに en-US ローカライゼーション設定済み | `asc subscriptions localizations list --subscription-id <ID>` |
| D9 | 全サブスクが READY_TO_SUBMIT（MISSING_METADATA でない） | `asc subscriptions get --id <ID>` で state 確認 |
| D10 | `asc validate subscriptions` で blocking=0 | 直接実行 |

既存の誤記修正：
- `Guideline 2.1（クラッシュ）` → `Guideline 2.1（IAP products not submitted for review）`

---

## 境界（やらないこと）

| 項目 | 理由 |
|------|------|
| Superwall の使用 | RevenueCat のみ使用する |
| Expo / React Native | Swift/SwiftUI のみ |
| Android 対応 | iOS のみ |
| TestFlight 配布 | 直接 App Store 提出のみ |
| A/B テスト実行 | mobileapp-iterator スキルの担当 |
| TikTok 投稿 | larry スキルの担当 |

---

## スキルファイル構成

```
.claude/skills/mobileapp-builder/
├── SKILL.md                      ← このスペックを要約したメインフロー
├── references/
│   ├── iap-bible.md             ← IAP設定完全手順（175カ国・ローカライズ・スクショ）
│   ├── spec-template.md         ← アプリ spec.md の標準フォーマット
│   └── submission-checklist.md  ← D6-D10 追加済みチェックリスト
└── scripts/
    └── add_prices.py            ← Equalization API で175カ国一括価格設定
```

---

## 実行手順

```bash
# Claude Code から直接実行
claude --print "mobileapp-builder: spec=/path/to/spec.md"

# Anicca から exec で呼ぶ場合
exec: claude --print "mobileapp-builder: spec=/Users/anicca/.openclaw/workspace/specs/2026-02-23/thankful.md"
```

---

## E2E 判定

| 項目 | 値 |
|------|-----|
| UI 変更 | あり（新アプリ） |
| 新画面 | あり |
| 結論 | Maestro E2E: PHASE 7 でペイウォール画面撮影に使用。フルフロー E2E は提出後 |

---

## リジェクトパターン封じ込め表

| リジェクト理由 | 防ぐフェーズ | 確認方法 |
|---------------|-----------|---------|
| Guideline 2.1（IAP not submitted） | PHASE 8 | READY_TO_SUBMIT 強制確認 |
| 175カ国価格なし → MISSING_METADATA | PHASE 5 | add_prices.py + 175件確認 |
| App Review Screenshot なし | PHASE 7 | already exists 確認 |
| PrivacyInfo.xcprivacy なし | PHASE 11 | Greenlight CRITICAL=0 |
| MISSING_METADATA のまま提出 | PHASE 8 | validate blocking=0 |
| 提出時スナップショット問題 | PHASE 8→12 の順番を守る | フェーズ順序 |
