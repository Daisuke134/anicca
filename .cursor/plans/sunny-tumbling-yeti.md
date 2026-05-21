# ASC CLI 0.37.2 Factory Pipeline Upgrade — 即時パッチ + 全体刷新

## Context

ASC CLI 0.37.2 (2026-03-06) で高レベルコマンドが多数追加された。
FrostDip US-008a が **5回連続失敗**（axe空ツリー、座標タップ失敗、UserDefaultsキー名ミス等）。

**即時パッチ（P1-P7）:** E2E テスト実証済みの修正を `us-008-release.md` に適用。
**全体刷新:** US-005a～US-010 を新コマンドで刷新（別フェーズ）。

---

## 即時パッチ（E2E テスト 2026-03-08 実証済み）

### 対象ファイル
`references/us-008-release.md`

### P1: screenshots.json スキーマ修正（Step 1）
- `sequences` → `steps`
- `seconds` → `duration_ms`
- トップレベル: `"app": { "bundle_id": "$BUNDLE_ID" }`

### P2: locale 切替フロー修正（Step 1）
- en-US 撮影前: `defaults write NSGlobalDomain AppleLanguages -array "en"` 明示セット
- ja 切替: `uninstall → install`（defaults delete だけでは不十分）
- 撮影後: en に戻す

### P3: 通知画面ハンドリング（Step 1）
- `onboarding_skip_notifications` を使って通知ダイアログ回避
- `wait_for` が通知ダイアログでブロックされる問題を回避

### P4: device-type マッピング注記（Step 1）
- `IPHONE_69` → ASC は `APP_IPHONE_67` にマッピング（正常動作、注記追加）

### P5: Step 1h Review screenshot 全面書き換え
- axe tap/describe-ui 全削除
- `asc screenshots run --plan` + review-screenshots.json で置き換え
- CC が a11y ID を grep → plan 動的生成 → 実行

### P6: localizations upload フラグ修正（Step 2）
- `--version`（正しいフラグ名確認済み）
- `.strings` ファイルフォーマット明記

### P7: localizations list フラグ修正（Step 1）
- `--version`（正しいフラグ名確認済み — 変更不要）

### P8: Decision Table（Step 8）
- ✅ 既にコミット済み（c363f005）

### 適用状態: ✅ 全パッチ適用済み（2026-03-08 確認）
P1-P8 全て `us-008-release.md` に反映済み。grep で全キーワード確認完了。

---

## US-008a 失敗分析（FrostDip iteration-20~22）

| # | 問題 | 回数 | 新コマンドの解決策 |
|---|------|------|-------------------|
| P1 | `axe describe-ui` 空ツリー | 3/3 | `asc screenshots run` は axe 不要 |
| P2 | `axe tap --label` 動かない | 3/3 | JSON `tap` で a11y ID 指定 |
| P3 | 座標タップ毎回間違う | 3/3 | a11y ID ベース。座標不要 |
| P4 | Maestro stdin parse error | 1/3 | 不要 |
| P5 | UserDefaultsキー名ミス | 3/3 | JSON に1回正しく書けば永久に正しい |
| P6 | ja locale 作成に JWT必要 | 1/3 | `asc localizations upload` で自動作成 |
| P7 | Paywall遷移失敗 | 1/3 | JSON sequence + `wait_for` |
| P8 | validate.sh タイムアウト | 3/3 | 全自動3分 |

---

## 存在確認

| コマンド | 存在 | 確認方法 |
|---------|------|---------|
| `asc screenshots run --plan` | YES | `--help`: actions: launch, tap, type, wait, wait_for, screenshot |
| `asc workflow run` | YES | `--help`: .asc/workflow.json, hooks, dry-run, if条件, private |
| `asc release run` | YES | `--help`: dry-run, checkpoint, strict-validate, timeout |
| `asc publish testflight` | YES | `--help`: --app, --ipa, --group, --wait, --notify, --test-notes |
| `asc publish appstore` | YES | `--help`: --ipa, --version, --submit, --confirm, --wait |
| `asc submit create` | YES | `--help`: --app, --version, --build, --confirm |
| `asc metadata push/pull` | YES | `--help`: --app, --version, --dir |
| `asc localizations upload/download` | YES | `--help`: --version, --path (.strings) |
| `asc validate testflight/iap/subscriptions` | YES | 個別バリデーション |
| `asc screenshots frame` | YES | `--help`: --input, --device, --output-dir |
| `asc screenshots review-generate/open/approve` | YES | HTML サイドバイサイド |
| `asc status` | YES | リリースダッシュボード |
| `asc notify slack` | YES | --webhook, --message |
| `asc auth doctor --fix` | YES | 認証問題自動診断+修復 |
| `asc app-setup info/categories/availability/pricing` | YES | ポスト作成セットアップ |
| `asc diff localizations` | YES | metadata差分確認 |
| `asc insights weekly/daily` | YES | 週次/日次分析 |
| `asc release-notes generate` | YES | git履歴→What's New |
| `asc migrate import/export` | YES | fastlane互換 |
| `asc nominations create` | YES | featuring申請 |
| `asc reviews/ratings/summarizations` | YES | レビュー監視 |
| ~~`asc release orchestrate`~~ | **NO** | 存在しない |
| ~~`asc localizations batch-update`~~ | **NO** | 存在しない |

---

## 全体フロー: Before → After

### Before（20-25 iterations, 4,103行スペック, 50+手動コマンド）

```
US-001～004-R: 5 iter ✅安定
US-005a: 1-2 iter ⚠️ 2FA×2, iris切れ, keychain
US-005b: 2-3 iter ⚠️ 111 API calls, 175カ国price
US-006 a-d: 4 iter ✅安定
US-006-R: 1 iter ✅
US-007: 1 iter ✅
US-008a: 5+ iter ❌ BLOCKED（axe/座標/キー名/locale）
US-008b~e: 3-4 iter（未到達）
US-009: 1-2 iter（未到達）
US-010: 1 iter
```

### After（14-17 iterations, ~2,000行スペック, 15手動コマンド）

```
US-001～004-R: 5 iter（変更なし）
US-005a: 1 iter（asc auth doctor + app-setup で簡素化）
US-005b: 2 iter（変更なし — 低レベルAPI依存）
US-006 a-d: 4 iter（変更なし）
US-006-R: 1 iter
US-007: 1 iter
US-008a: 1 iter ← screenshots run --plan で1発
US-008b: 1 iter ← metadata push + localizations upload
US-008c+d+e: 1 iter ← publish appstore --wait + validate 3種 + publish testflight
US-009: 1 iter ← submit create OR release run
US-010: 1 iter
```

---

## 変更計画（US別）

### US-005a: Infrastructure（`references/us-005a-infra.md` 171行）

| 現状 | 新 | 効果 |
|------|-----|------|
| PREFLIGHT で認証チェック手動 | `asc auth doctor --fix --confirm` | 認証問題自動診断+修復 |
| app作成後のカテゴリ/availability 散在 | `asc app-setup categories set` + `availability set` | セットアップ一括 |
| — | `asc app-setup info set --app $APP_ID --primary-locale en-US` | app info 初期化 |

**追加するコード:**
```bash
# Step 0: 認証診断（PREFLIGHT代替）
asc auth doctor --output json
# 問題あれば: asc auth doctor --fix --confirm

# Step 6: ポスト作成セットアップ（app create 直後）
asc app-setup categories set --app "$APP_ID" --primary HEALTH_AND_FITNESS
asc app-setup availability set --app "$APP_ID" --territory "USA,JPN,GBR" --available true
```

### US-008a: Screenshots（`references/us-008-release.md` Step 1 — 現状 ~500行）

**全面書き換え。** 現状の手動30+ステップを以下に置き換え:

```bash
# Step 1a: screenshots.json 生成（CC がアプリ固有のa11y IDから自動生成）
# テンプレート:
cat > .asc/screenshots.json << 'JSON'
{
  "bundle_id": "$BUNDLE_ID",
  "output_dir": "./screenshots/raw",
  "sequences": [
    {"action": "launch"},
    {"action": "wait", "seconds": 3},
    {"action": "screenshot", "name": "screen1_welcome"},
    {"action": "tap", "id": "onboarding_get_started"},
    {"action": "wait", "seconds": 2},
    {"action": "screenshot", "name": "screen2_features"},
    ...
  ]
}
JSON
# CC は UX_SPEC の accessibilityIdentifier + prd.json の features から
# 実際のシーケンスを生成する。上記はテンプレートのみ。

# Step 1b: 撮影（4コマンドで16枚）
# en-US 6.1"
xcrun simctl spawn $UDID_61 defaults write NSGlobalDomain AppleLanguages -array "en"
asc screenshots run --plan .asc/screenshots.json --udid $UDID_61 --output-dir ./screenshots/raw/en-US
# en-US 6.5"
asc screenshots run --plan .asc/screenshots.json --udid $UDID_65 --output-dir ./screenshots/raw-65/en-US
# ja 6.1"
xcrun simctl spawn $UDID_61 defaults write NSGlobalDomain AppleLanguages -array "ja"
asc screenshots run --plan .asc/screenshots.json --udid $UDID_61 --output-dir ./screenshots/raw/ja
# ja 6.5"
asc screenshots run --plan .asc/screenshots.json --udid $UDID_65 --output-dir ./screenshots/raw-65/ja

# Step 1c: アップロード
asc screenshots upload --version-localization "$EN_LOC_ID" --path ./screenshots/raw/en-US --device-type IPHONE_61
asc screenshots upload --version-localization "$EN_LOC_ID" --path ./screenshots/raw-65/en-US --device-type IPHONE_65
asc screenshots upload --version-localization "$JA_LOC_ID" --path ./screenshots/raw/ja --device-type IPHONE_61
asc screenshots upload --version-localization "$JA_LOC_ID" --path ./screenshots/raw-65/ja --device-type IPHONE_65
```

**sim準備、ビルド、インストール、MD5検証、review screenshot は既存手順を維持。**
変更するのは「画面遷移 + キャプチャ」部分のみ（最大の失敗ポイント）。

### US-008b: Metadata（`references/us-008-release.md` Step 2 — 現状 ~20行）

```bash
# 現状: locale個別に asc localizations update × 4回
# 新: 一括 push
asc metadata push --app "$APP_ID" --version "$VERSION" --dir "./metadata"

# 差分確認（push前）
asc diff localizations --app "$APP_ID" --path "./metadata" --version-id "$VER_ID"

# ja locale が存在しない場合:
asc localizations upload --version "$VERSION_ID" --path "./localizations"
```

### US-008c: Build + Upload（`references/us-008-release.md` Step 3 — 現状 ~40行）

```bash
# 現状: xcodebuild archive → export → xcrun altool upload → asc versions attach-build
# 新: archive + export は変更なし。upload以降を1コマンド化:
asc publish appstore \
  --app "$APP_ID" \
  --ipa "$IPA_PATH" \
  --version "$VERSION" \
  --wait \
  --output json
# upload + processing wait + version find/create + build attach が全部入り
```

### US-008e: Preflight + TestFlight（`references/us-008-release.md` Step 8-9 — 現状 ~60行）

```bash
# バリデーション強化（3種追加）
asc validate --app "$APP_ID" --version "$VERSION" --strict
asc validate testflight --app "$APP_ID" --build "$BUILD_ID"
asc validate iap --app "$APP_ID"
asc validate subscriptions --app "$APP_ID"

# ステータス確認
asc status --app "$APP_ID" --output table

# TestFlight 全自動（現状5コマンド → 1コマンド）
asc publish testflight \
  --app "$APP_ID" \
  --ipa "$IPA_PATH" \
  --group "$GROUP_ID" \
  --wait \
  --notify \
  --test-notes "Initial beta test" \
  --locale "en-US" \
  --output json
```

### US-009: Submit（`references/us-009-submit.md` 132行）

```bash
# 方法A: シンプル提出（現状3コマンド → 1コマンド）
asc submit create \
  --app "$APP_ID" \
  --version "$VERSION" \
  --build "$BUILD_ID" \
  --confirm \
  --output json

# 方法B: フルリリースパイプライン（metadata含む全自動）
asc release run \
  --app "$APP_ID" \
  --version "$VERSION" \
  --build "$BUILD_ID" \
  --metadata-dir "./metadata" \
  --dry-run          # まず確認
# 問題なければ:
asc release run \
  --app "$APP_ID" \
  --version "$VERSION" \
  --build "$BUILD_ID" \
  --metadata-dir "./metadata" \
  --confirm \
  --checkpoint-file ./release-checkpoint.json
```

### US-010: Build Report（`references/us-010-report.md` 171行）

```bash
# 追加: リリースノート自動生成
asc release-notes generate --since-tag "v1.0.0" --max-chars 4000
```

### CLAUDE.md: コマンド表更新（PREFLIGHT + 全US共通）

```bash
# ralph.sh PREFLIGHT に追加（CLAUDE.md の指示経由）
asc auth doctor --output json  # 認証診断
```

**テーブル追加（15コマンド）:**

| タスク | 正しいコマンド |
|--------|---------------|
| 認証診断 | `asc auth doctor --output json` |
| ポスト作成セットアップ | `asc app-setup categories/availability/pricing set` |
| スクショ自動撮影 | `asc screenshots run --plan .asc/screenshots.json` |
| スクショフレーム | `asc screenshots frame --input raw.png --device iphone-air` |
| Metadata 一括push | `asc metadata push --app $APP_ID --dir ./metadata` |
| Localization 一括 | `asc localizations upload --version $VER_ID --path ./localizations` |
| Metadata差分 | `asc diff localizations --app $APP_ID --path ./metadata` |
| IPA upload+attach | `asc publish appstore --app $APP_ID --ipa $IPA --wait` |
| TestFlight 全自動 | `asc publish testflight --app $APP_ID --ipa $IPA --group $GID --wait --notify` |
| バリデーション(TF/IAP/Subs) | `asc validate testflight/iap/subscriptions --app $APP_ID` |
| ステータス | `asc status --app $APP_ID --output table` |
| App Store 提出 | `asc submit create --app $APP_ID --confirm` |
| フルリリース | `asc release run --app $APP_ID --metadata-dir ./metadata --confirm` |
| Release Notes | `asc release-notes generate --since-tag $TAG` |
| ワークフロー実行 | `asc workflow run <name> KEY:VALUE` |

---

## asc workflow — ファクトリー全体の JSON 統合

### `.asc/workflow.json` テンプレート（us-008-release.md に追加）

CC は US-005a 完了後、このテンプレートをアプリディレクトリに生成する。
env の値は `.env` から注入。各 US iteration で `asc workflow run <name>` を呼ぶ。

```json
{
  "env": {
    "APP_ID": "",
    "VERSION": "1.0.0",
    "GROUP_ID": "",
    "BUNDLE_ID": "",
    "EN_LOC_ID": "",
    "JA_LOC_ID": ""
  },
  "before_all": "asc auth doctor --output json",
  "error": "curl -s -X POST $SLACK_WEBHOOK_AGENTS -H 'Content-Type: application/json' -d '{\"text\":\"workflow failed\"}'",
  "workflows": {
    "screenshots": {
      "description": "Capture + upload screenshots for en-US and ja (US-008a)",
      "steps": [
        {"name": "capture_en_61", "run": "asc screenshots run --plan .asc/screenshots.json --udid $UDID_61 --output-dir ./screenshots/raw/en-US"},
        {"name": "capture_en_65", "run": "asc screenshots run --plan .asc/screenshots.json --udid $UDID_65 --output-dir ./screenshots/raw-65/en-US"},
        {"name": "locale_ja", "run": "xcrun simctl spawn $UDID_61 defaults write NSGlobalDomain AppleLanguages -array ja"},
        {"name": "capture_ja_61", "run": "asc screenshots run --plan .asc/screenshots.json --udid $UDID_61 --output-dir ./screenshots/raw/ja"},
        {"name": "capture_ja_65", "run": "asc screenshots run --plan .asc/screenshots.json --udid $UDID_65 --output-dir ./screenshots/raw-65/ja"},
        {"name": "upload_en_61", "run": "asc screenshots upload --version-localization $EN_LOC_ID --path ./screenshots/raw/en-US --device-type IPHONE_61"},
        {"name": "upload_en_65", "run": "asc screenshots upload --version-localization $EN_LOC_ID --path ./screenshots/raw-65/en-US --device-type IPHONE_65"},
        {"name": "upload_ja_61", "run": "asc screenshots upload --version-localization $JA_LOC_ID --path ./screenshots/raw/ja --device-type IPHONE_61"},
        {"name": "upload_ja_65", "run": "asc screenshots upload --version-localization $JA_LOC_ID --path ./screenshots/raw-65/ja --device-type IPHONE_65"}
      ]
    },
    "metadata": {
      "description": "Push metadata for en-US and ja (US-008b)",
      "steps": [
        {"name": "diff", "run": "asc diff localizations --app $APP_ID --path ./metadata --version-id $VER_ID"},
        {"name": "push", "run": "asc metadata push --app $APP_ID --version $VERSION --dir ./metadata"}
      ]
    },
    "build": {
      "description": "Upload IPA + attach to version (US-008c)",
      "steps": [
        {"name": "publish", "run": "asc publish appstore --app $APP_ID --ipa $IPA_PATH --version $VERSION --wait --output json"}
      ]
    },
    "preflight": {
      "private": true,
      "description": "Pre-submission validation suite",
      "steps": [
        {"name": "v_version", "run": "asc validate --app $APP_ID --version $VERSION --strict"},
        {"name": "v_iap", "run": "asc validate iap --app $APP_ID"},
        {"name": "v_subs", "run": "asc validate subscriptions --app $APP_ID"},
        {"name": "status", "run": "asc status --app $APP_ID --output table"}
      ]
    },
    "beta": {
      "description": "TestFlight distribution (US-008e)",
      "steps": [
        {"name": "validate_tf", "run": "asc validate testflight --app $APP_ID --build $BUILD_ID"},
        {"name": "distribute", "run": "asc publish testflight --app $APP_ID --ipa $IPA_PATH --group $GROUP_ID --wait --notify --output json"}
      ]
    },
    "release": {
      "description": "Full App Store submission (US-009)",
      "steps": [
        {"workflow": "preflight"},
        {"name": "submit", "run": "asc submit create --app $APP_ID --version $VERSION --build $BUILD_ID --confirm --output json"}
      ]
    },
    "release_full": {
      "description": "Alternative: metadata + attach + validate + submit in one shot",
      "steps": [
        {"name": "run", "run": "asc release run --app $APP_ID --version $VERSION --build $BUILD_ID --metadata-dir ./metadata --confirm --output json"}
      ]
    }
  }
}
```

**実行例:**
```bash
asc workflow validate                                # 構文チェック
asc workflow list                                    # ワークフロー一覧
asc workflow run --dry-run screenshots               # ドライラン
asc workflow run screenshots UDID_61:xxx UDID_65:yyy # 実行
asc workflow run beta BUILD_ID:xxx                   # TestFlight
asc workflow run release VERSION:1.0.0 BUILD_ID:xxx  # 提出
asc workflow run release_full VERSION:1.0.0 BUILD_ID:xxx  # 全自動
```

---

## 追加機能（リリース後 / P4）

| 機能 | コマンド | 用途 |
|------|---------|------|
| Slack 組み込み通知 | `asc notify slack --webhook $URL --message "..."` | curl 置き換え |
| レビュー監視 | `asc reviews --app $APP_ID --stars 1` | 1つ星自動取得 |
| レビュー要約 | `asc reviews summarizations --app $APP_ID --platform IOS` | AI要約 |
| 週次分析 | `asc insights weekly --app $APP_ID --source analytics` | KPI追跡 |
| Featuring申請 | `asc nominations create --app $APP_ID --type APP_LAUNCH` | US-009後 |
| Sandbox管理 | `asc sandbox clear-history --id $ID --confirm` | IAP テスト |
| fastlane互換 | `asc migrate import --fastlane-dir ./fastlane` | 既存プロジェクト移行 |

---

## 数値比較

| メトリクス | 現状 | 新 | 改善 |
|-----------|------|-----|------|
| reference 総行数 | 4,103行 | ~2,000行 | **-51%** |
| US-008 スペック行数 | 948行 | ~300行 | **-68%** |
| US-008a~009 iteration数 | 10-15 | 3-4 | **-70%** |
| 手動 shell コマンド数 | 50+ | 15 | **-70%** |
| 失敗ポイント（脆弱箇所） | 20+ | 5 | **-75%** |
| Total iterations（全体） | 20-25 | 14-17 | **-30%** |
| Token消費（推定） | ~100M | ~60M | **-40%** |
| Cost per app ($200 plan) | ~$9 | ~$5 | **-44%** |

---

## ファイル変更一覧

| # | ファイル | 操作 |
|---|---------|------|
| 1 | `references/us-005a-infra.md` | `asc auth doctor` + `app-setup` コマンド追加 |
| 2 | `references/us-008-release.md` | **大幅書き換え**: Step 1 → `screenshots run --plan`、Step 2 → `metadata push`、Step 3 → `publish appstore`、Step 8 → validate 3種、Step 9 → `publish testflight`。workflow.json テンプレート追加 |
| 3 | `references/us-009-submit.md` | 3段提出 → `submit create`。`release run` オプション追加 |
| 4 | `CLAUDE.md` ASC CLI テーブル | 15コマンド追加 + PREFLIGHT に `auth doctor` 指示 |

**注意:** `ralph.sh` は DO NOT MODIFY ルール対象。変更しない。

---

## 実装順序

1. **CLAUDE.md** — CC が新コマンドを認識できるようにする（全USに影響）
2. **us-008-release.md** — 最大の改善。948行 → ~300行
3. **us-009-submit.md** — 提出フロー簡素化
4. **us-005a-infra.md** — auth doctor + app-setup 追加

---

## コミット 68de72a6 レビュー結果（factory-patch-v2）

| Item | 変更内容 | 状態 | 備考 |
|------|---------|------|------|
| B | Device table → IPHONE_69 only | ✅ OK | auto-scale コメント付き |
| C | Single UDID_69 sim | ✅ OK | auto-create + boot 含む |
| D | UserDefaults key grep | ✅ OK | Swift コードから `ONBOARDING_KEY` 変数を grep |
| E | Maestro absolute path | ✅ OK | `/Users/anicca/.maestro/bin/maestro` + fallback |
| F | defaults delete comment | ✅ OK | "Domain not found" を無視する `|| true` |
| G | find path fix | ✅ OK | `*/Debug-iphonesimulator/*.app` + not-path filter |
| H | Upload IPHONE_69 only | ✅ OK | 6.5"/6.1"/iPad upload 全削除 |
| I | iPad + 6.5" sections deleted | ✅ OK | Sections 1b2/1c2/1b3/1c3 全削除 |
| J | `localizations upload` | ✅ OK | `.strings` ファイル生成 + 2コマンドで全ロケール完了 |
| K | `asc release run` | ✅ OK | dry-run → confirm フロー。Prerequisites リスト明確 |
| M | CLAUDE.md ASC skills refs | ✅ OK | 4行追加 |

### 残存リスク — ✅ 全解決済み（2026-03-08）

| # | 問題 | 解決状態 | コミット/証拠 |
|---|------|---------|-------------|
| 1 | Review screenshot の axe 依存 | ✅ P5 で解決 | `review-screenshots.json` + `asc screenshots run --plan` に移行済み |
| 2 | `axe describe-ui` 空ツリー | ✅ P5 で解決 | axe 禁止ルール追加済み |
| 3 | `asc release run` Prerequisites | ✅ P8 で解決 | Decision Table で 19 error.id → 自動修正マッピング |

---

## E2E テスト結果（2026-03-08 FrostDip 実証）

| コマンド | 結果 |
|---------|------|
| `asc screenshots run --plan` (en-US) | ✅ 19/19 steps |
| `asc screenshots run --plan` (ja) | ✅ 19/19 steps（uninstall 必須） |
| `asc screenshots upload` (en-US) | ✅ 5/5 COMPLETE |
| `asc screenshots upload` (ja) | ✅ 5/5 COMPLETE |
| `asc localizations upload --dry-run` | ✅ 2 locales |
| `asc metadata pull/push --dry-run` | ✅ |
| `asc release run --dry-run` (Desk Stretch) | ✅ 4/5 steps（validate で正しくブロック） |

---

## 全フェーズブレイクダウン（修正版 2026-03-08）

### 鉄則

| # | ルール |
|---|--------|
| 1 | **1フェーズ = 1スキル**（複数スキル呼び出し禁止） |
| 2 | **全ASC CLIコマンド `--help` 検証済み** ✅ |
| 3 | **品質レビュー = code-quality-reviewer サブエージェント**（codex-review ではない） |
| 4 | **スキルがない → 新規作成** |
| 5 | **スキル大きすぎ → フェーズ分割** |
| 6 | **スキル = レシピ（how）、reference md = オーケストレーター（what/when）** |

### コマンド存在検証（全件 `--help` 確認済み）

| コマンド | 存在 | 主要フラグ |
|---------|------|-----------|
| `asc auth doctor` | ✅ | `--fix --confirm --output json` |
| `asc app-setup categories set` | ✅ | `--app --primary --secondary` |
| `asc app-setup availability set` | ✅ | `--app --territory --available` |
| `asc screenshots run` | ✅ | `--plan --bundle-id --output-dir` |
| `asc screenshots upload` | ✅ | `--version-localization --path --device-type` |
| `asc screenshots frame` | ✅ | `--input --config`（Koubou v0.14.0） |
| `asc metadata push` | ✅ | `--app --version --dir --dry-run` |
| `asc metadata pull` | ✅ | `--app --version --dir` |
| `asc localizations upload` | ✅ | `--version --path --locale` |
| `asc diff localizations` | ✅ | `--app --path --version` |
| `asc publish appstore` | ✅ | `--app --ipa --version --wait --submit` |
| `asc publish testflight` | ✅ | `--app --ipa --group --wait --notify` |
| `asc validate` | ✅ | `--app --version --strict` |
| `asc validate testflight` | ✅ | `--app --build` |
| `asc validate iap` | ✅ | `--app --strict` |
| `asc validate subscriptions` | ✅ | `--app` |
| `asc submit create` | ✅ | `--app --version --build --confirm` |
| `asc release run` | ✅ | `--app --version --build --metadata-dir --dry-run --confirm` |
| `asc release-notes generate` | ✅ | `--since-tag --since-ref` |
| `asc status` | ✅ | `--app --output table/json` |
| `asc workflow run` | ✅ | `<name> KEY:VALUE` |
| `asc notify slack` | ✅ | `--webhook --message` |

---

### フェーズ一覧

```
US-001 ─→ US-002 ─→ US-003 ─→ US-004a ─→ US-004b ─→ US-004-R
  │          │          │          │           │           │
  prd     architect   ux-spec  impl-spec   tdd-work    c-q-r
                                             flow      (gate)
                                                         │
US-005a ─→ US-005b ─→ US-005c ─→ US-006 ─→ US-006-R ─→ US-007
  │          │          │          │          │           │
signing    pricing   rc-sync   app-build  greenlight  maestro
                                             (gate)
                                                │
US-008a ─→ US-008b ─→ US-008c ─→ US-008d ─→ US-008e ─→ US-009 ─→ US-010
  │          │          │          │          │          │          │
shots     metadata   xc-build  sub-health  testflight release  changelog
pipeline    sync      +upload              orch.       flow
```

---

### Phase 1: US-001 — トレンド発見

| 項目 | 値 |
|------|-----|
| スキル | `prd-generator` |
| やること | App Store/市場トレンド調査 → PRD生成 |
| 主要ツール | CC生成（コード不要） |
| 閉ループ | code-quality-reviewer サブエージェント → blocking=0 まで |
| 変更不要 | ✅ 既存スキルそのまま |

### Phase 2: US-002 — アーキテクチャ

| 項目 | 値 |
|------|-----|
| スキル | `architecture-spec` |
| やること | PRD → ARCHITECTURE.md 生成 |
| 主要ツール | CC生成 |
| 閉ループ | code-quality-reviewer サブエージェント → blocking=0 まで |
| 変更不要 | ✅ 既存スキルそのまま |

### Phase 3: US-003 — UX 設計

| 項目 | 値 |
|------|-----|
| スキル | `ux-spec` |
| やること | ARCHITECTURE.md → UX_SPEC 生成（a11y ID含む） |
| 主要ツール | CC生成 |
| 閉ループ | code-quality-reviewer サブエージェント → blocking=0 まで |
| 変更不要 | ✅ 既存スキルそのまま |

### Phase 4a: US-004a — スペック群生成

| 項目 | 値 |
|------|-----|
| スキル | `implementation-spec` |
| やること | DESIGN_SYSTEM, UX_SPEC, TEST_SPEC, RELEASE_SPEC 生成 |
| 主要ツール | CC生成 |
| 閉ループ | code-quality-reviewer サブエージェント → blocking=0 まで |
| 変更不要 | ✅ 既存スキルそのまま |

### Phase 4b: US-004b — TDD 実装

| 項目 | 値 |
|------|-----|
| スキル | `tdd-workflow` |
| やること | RED → GREEN → REFACTOR サイクル |
| 主要ツール | `fastlane test` |
| 閉ループ | テスト全pass + coverage 80%+ まで |
| 変更不要 | ✅ 既存スキルそのまま |

### Gate: US-004-R — スペックレビュー

| 項目 | 値 |
|------|-----|
| 実行方法 | **code-quality-reviewer サブエージェント**（スキルではない） |
| やること | US-001〜004 の全成果物レビュー |
| 閉ループ | blocking=0 になるまで最大5回反復 |
| 注意 | ~~codex-review~~ ではない |

### Phase 5a: US-005a — インフラ（認証 + App作成 + 署名）

| 項目 | 値 |
|------|-----|
| スキル | `asc-signing-setup` |
| やること | 認証診断 → Bundle ID登録 → App作成 → カテゴリ/地域設定 |
| 主要コマンド | `asc auth doctor --fix --confirm` → `asc app-setup categories set` → `asc app-setup availability set` |
| 閉ループ | `asc auth doctor --output json` → issues=0 まで retry |
| **要更新** | ⚠️ `auth doctor` + `app-setup` コマンドをスキルに追加 |

```bash
# Phase 5a フロー
asc auth doctor --output json                    # 1. 認証診断
asc auth doctor --fix --confirm                  # 2. 問題あれば修復
# ... 既存の signing + app create ...
asc app-setup categories set --app "$APP_ID" --primary HEALTH_AND_FITNESS
asc app-setup availability set --app "$APP_ID" --territory "USA,JPN" --available true
```

### Phase 5b: US-005b — 価格設定

| 項目 | 値 |
|------|-----|
| スキル | `asc-ppp-pricing` |
| やること | 175カ国の価格ティア設定 |
| 主要コマンド | ASC API 直接（低レベル） |
| 閉ループ | pricing verify → 不一致あれば retry |
| 変更不要 | ✅ 既存スキルそのまま |

### Phase 5c: US-005c — RevenueCat カタログ同期

| 項目 | 値 |
|------|-----|
| スキル | `asc-revenuecat-catalog-sync` |
| やること | ASC subscriptions ↔ RC products/entitlements/offerings 同期 |
| 主要コマンド | RC MCP ツール |
| 閉ループ | audit diff → 差分0 まで retry |
| 変更不要 | ✅ 既存スキルそのまま |
| 注意 | US-005b から分離（1フェーズ1スキル原則） |

### Phase 6: US-006 — 実装 + ビルド

| 項目 | 値 |
|------|-----|
| スキル | `app-builder` |
| やること | Xcode プロジェクト作成 → Swift実装 → TDD → ビルド成功 |
| 主要ツール | `fastlane build`, TDD |
| 閉ループ | ビルド成功 + テスト全pass まで |
| 変更不要 | ✅ 既存スキルそのまま |

### Gate: US-006-R — ビルドレビュー

| 項目 | 値 |
|------|-----|
| スキル | `greenlight` |
| やること | `greenlight preflight <app_dir>` → CRITICAL=0 確認 |
| 閉ループ | CRITICAL=0 まで修正 → 再実行ループ |
| 変更不要 | ✅ 既存スキルそのまま |

### Phase 7: US-007 — E2Eテスト

| 項目 | 値 |
|------|-----|
| スキル | `maestro-e2e` |
| やること | Maestro フロー 6+ 作成 → 全pass |
| 主要ツール | Maestro MCP |
| 閉ループ | 6+ flows 全pass まで |
| 変更不要 | ✅ 既存スキルそのまま |

### Phase 8a: US-008a — スクリーンショット

| 項目 | 値 |
|------|-----|
| スキル | `asc-shots-pipeline` |
| やること | screenshots.json 生成 → 撮影 → アップロード |
| 主要コマンド | `asc screenshots run --plan` → `asc screenshots upload` |
| 閉ループ | upload 結果 5/5 COMPLETE まで retry |
| **要更新** | ⚠️ axe 依存全削除 → `screenshots run --plan` に移行 |

```bash
# Phase 8a フロー（E2E実証済み）
# 1. CC が a11y ID から screenshots.json を動的生成
# 2. en-US 撮影
defaults write NSGlobalDomain AppleLanguages -array "en"
asc screenshots run --plan .asc/screenshots.json --udid $UDID_69 --output-dir ./screenshots/raw/en-US
# 3. ja 撮影（uninstall → install で状態リセット）
xcrun simctl uninstall $UDID_69 $BUNDLE_ID
defaults write NSGlobalDomain AppleLanguages -array "ja"
xcrun simctl install $UDID_69 "$APP_PATH"
asc screenshots run --plan .asc/screenshots.json --udid $UDID_69 --output-dir ./screenshots/raw/ja
# 4. アップロード
asc screenshots upload --version-localization "$EN_LOC_ID" --path ./screenshots/raw/en-US --device-type IPHONE_69
asc screenshots upload --version-localization "$JA_LOC_ID" --path ./screenshots/raw/ja --device-type IPHONE_69
```

### Phase 8b: US-008b — メタデータ

| 項目 | 値 |
|------|-----|
| スキル | `asc-metadata-sync` |
| やること | metadata ファイル生成 → diff確認 → push → localizations upload |
| 主要コマンド | `asc diff localizations` → `asc metadata push` → `asc localizations upload` |
| 閉ループ | push 後に `asc metadata pull` で検証 → 差分0 まで |
| **要更新** | ⚠️ `metadata push` + `localizations upload` コマンド追加 |

```bash
# Phase 8b フロー
asc diff localizations --app "$APP_ID" --path ./metadata --version "$VER_ID"  # 差分確認
asc metadata push --app "$APP_ID" --version "$VERSION" --dir ./metadata       # push
asc localizations upload --version "$VERSION_ID" --path ./localizations       # .strings upload
```

### Phase 8c: US-008c — ビルド + アップロード

| 項目 | 値 |
|------|-----|
| スキル | `asc-xcode-build` |
| やること | archive → export → IPA upload → version attach |
| 主要コマンド | `fastlane build` → `asc publish appstore --wait` |
| 閉ループ | build processing complete まで `--wait` が自動待機 |
| **要更新** | ⚠️ `asc publish appstore` コマンド追加（upload + attach 一体化） |

```bash
# Phase 8c フロー
cd aniccaios && fastlane build                                    # archive + export
asc publish appstore --app "$APP_ID" --ipa "$IPA_PATH" --version "$VERSION" --wait --output json
```

### Phase 8d: US-008d — プリフライト検証

| 項目 | 値 |
|------|-----|
| スキル | `asc-submission-health` |
| やること | version + IAP + subscriptions + TestFlight バリデーション |
| 主要コマンド | `asc validate --strict` + `asc validate iap` + `asc validate subscriptions` |
| 閉ループ | 全 validate pass まで → エラーは Decision Table で自動修正 |
| **要更新** | ⚠️ 3種バリデーション追加 |

```bash
# Phase 8d フロー
asc validate --app "$APP_ID" --version "$VERSION" --strict
asc validate iap --app "$APP_ID" --strict
asc validate subscriptions --app "$APP_ID"
asc status --app "$APP_ID" --output table
```

### Phase 8e: US-008e — TestFlight 配布

| 項目 | 値 |
|------|-----|
| スキル | `asc-testflight-orchestration` |
| やること | TF validate → distribute → 通知 |
| 主要コマンド | `asc validate testflight` → `asc publish testflight --wait --notify` |
| 閉ループ | distribute 成功 まで |
| **要更新** | ⚠️ `publish testflight` 1コマンド化 |

```bash
# Phase 8e フロー
asc validate testflight --app "$APP_ID" --build "$BUILD_ID"
asc publish testflight --app "$APP_ID" --ipa "$IPA_PATH" --group "$GROUP_ID" --wait --notify --output json
```

### Phase 9: US-009 — App Store 提出

| 項目 | 値 |
|------|-----|
| スキル | `asc-release-flow` |
| やること | dry-run → confirm で全自動提出 |
| 主要コマンド | `asc release run --dry-run` → `asc release run --confirm` |
| 閉ループ | Decision Table 19件（error.id → action マッピング）で自動修正 → retry |
| **要更新** | ⚠️ `asc release run` 統合（ensure_version + metadata + build + validate + submit） |

```bash
# Phase 9 フロー
asc release run --app "$APP_ID" --version "$VERSION" --build "$BUILD_ID" \
  --metadata-dir ./metadata --dry-run --output json          # 1. ドライラン
# CC が JSON を解析 → Decision Table で問題修正
asc release run --app "$APP_ID" --version "$VERSION" --build "$BUILD_ID" \
  --metadata-dir ./metadata --confirm --output json          # 2. 本番提出
```

### Phase 10: US-010 — ビルドレポート

| 項目 | 値 |
|------|-----|
| スキル | `changelog-generator` |
| やること | git履歴 → What's New 生成 → Slack通知 |
| 主要コマンド | `asc release-notes generate --since-tag $TAG` |
| 閉ループ | — (レポート生成のみ) |
| 変更不要 | ✅ 既存スキルそのまま |

---

### スキル更新一覧

| # | スキル | 操作 | 追加するコマンド |
|---|--------|------|----------------|
| 1 | `asc-signing-setup` | 更新 | `asc auth doctor`, `asc app-setup categories/availability set` |
| 2 | `asc-shots-pipeline` | 更新 | `asc screenshots run --plan`, axe 全削除 |
| 3 | `asc-metadata-sync` | 更新 | `asc metadata push`, `asc localizations upload` |
| 4 | `asc-xcode-build` | 更新 | `asc publish appstore --wait` |
| 5 | `asc-submission-health` | 更新 | `asc validate iap/subscriptions` |
| 6 | `asc-testflight-orchestration` | 更新 | `asc publish testflight --wait --notify` |
| 7 | `asc-release-flow` | 更新 | `asc release run --dry-run/--confirm` + Decision Table |

### reference md 更新一覧

| # | ファイル | 操作 |
|---|---------|------|
| 1 | `us-005a-infra.md` | `auth doctor` + `app-setup` ステップ追加 |
| 2 | `us-008-release.md` | Step 1→`screenshots run`, Step 2→`metadata push`, Step 3→`publish appstore`, Step 8→validate 3種, Step 9→`publish testflight` |
| 3 | `us-009-submit.md` | `asc release run` に統合 |
| 4 | `CLAUDE.md` | ASC CLI コマンドテーブル 22件追加 |

### 実装順序

1. **CLAUDE.md** — CC が新コマンドを認識（全USに影響）
2. **7スキル更新** — レシピにコマンド追加
3. **us-008-release.md** — 最大改善（948行 → ~300行）
4. **us-005a-infra.md** — auth doctor + app-setup
5. **us-009-submit.md** — release run 統合

### 検証方法

```bash
# 各スキル更新後、FrostDip で E2E 検証
asc auth doctor --output json                    # Phase 5a
asc screenshots run --plan .asc/screenshots.json # Phase 8a
asc metadata push --app $APP_ID --dir ./metadata --dry-run  # Phase 8b
asc validate --app $APP_ID --version $VER --strict          # Phase 8d
asc release run --app $APP_ID --version $VER --dry-run      # Phase 9
```
