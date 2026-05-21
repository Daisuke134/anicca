# App Store Submission Checklist — Universal Gate

**目的:** 全アプリ共通。このチェックリストを通過しない限り `fastlane full_release` を実行できない。
**運用:** `app-ship` スキルが呼ばれるたびに自動実行。CI/CD ゲートとして機能する。
**対象:** Anicca、Thankful Gratitude App、今後の全アプリ。

---

## ゲート構成（順番必須）

```
GATE 1: Greenlight（自動）
    ↓ CRITICAL = 0 でなければ STOP
GATE 2: 追加チェック（自動 + 半自動）
    ↓ 全項目 PASS でなければ STOP
GATE 3: fastlane full_release
```

**原則:** GATE 1 か GATE 2 でひとつでも失敗 → Fastlane を実行しない。

---

## GATE 1: Greenlight（完全自動）

Greenlight が検出するもの（以下を個別にチェックする必要はない）:

| カテゴリ | Greenlight でカバー |
|---------|-------------------|
| PrivacyInfo.xcprivacy の存在 | ✅ |
| NSPrivacyAccessedAPITypes の申告 | ✅ |
| 必須の Info.plist キー | ✅ |
| リジェクト既知パターン（ITMS エラー） | ✅ |

**実行コマンド:**
```bash
/tmp/greenlight/build/greenlight preflight <app_dir>
# CRITICAL が 1件でもあれば → 修正してから再実行
# CRITICAL = 0 → GATE 2 へ進む
```

**Greenlight が未インストールの場合:**
```bash
cd /tmp && git clone https://github.com/RevylAI/greenlight.git && cd greenlight && make build
```

---

## GATE 2: 追加チェック（Greenlight が検出しない項目）

以下は Greenlight では検出されない。手動 or スクリプトで確認する。

### A. ビルド・署名

| # | チェック項目 | 確認方法 | 自動化可否 |
|---|------------|---------|-----------|
| A1 | `DEVELOPMENT_TEAM` が空でない | `grep DEVELOPMENT_TEAM project.pbxproj` | ✅ 自動 |
| A2 | `MARKETING_VERSION` が前回より大きい | `asc builds list` で比較 | ✅ 自動 |
| A3 | `CURRENT_PROJECT_VERSION` が前回より大きい | 同上 | ✅ 自動 |
| A4 | デプロイターゲットが 17.0 以下 | `grep IPHONEOS_DEPLOYMENT_TARGET project.pbxproj` | ✅ 自動 |
| A5 | デバッグコード・テストアカウントが残っていない | `grep -r "TODO\|FIXME\|HARDCODED\|testuser" Sources/` | ✅ 自動 |

### B. App Store メタデータ

| # | チェック項目 | 確認方法 | 自動化可否 |
|---|------------|---------|-----------|
| B1 | タイトル・サブタイトル（EN）が設定済み | `asc metadata list` | ✅ 自動 |
| B2 | タイトル・サブタイトル（JA）が設定済み | 同上 | ✅ 自動 |
| B3 | 説明文（EN）が設定済みかつ 空でない | 同上 | ✅ 自動 |
| B4 | 説明文（JA）が設定済みかつ 空でない | 同上 | ✅ 自動 |
| B5 | キーワード（EN + JA）が設定済み | 同上 | ✅ 自動 |
| B6 | プライバシーポリシー URL が設定済み | `asc apps info` で確認 | ✅ 自動 |
| B7 | 年齢レーティングが設定済み | 同上 | ✅ 自動 |

### C. スクリーンショット（Greenlight が検出しない最大のリジェクト要因）

| # | チェック項目 | 確認方法 | 自動化可否 |
|---|------------|---------|-----------|
| C1 | 6.7インチ スクリーンショット（EN）が 3枚以上 | `asc screenshots list --locale en-US` | ✅ 自動 |
| C2 | 6.7インチ スクリーンショット（JA）が 3枚以上 | `asc screenshots list --locale ja-JP` | ✅ 自動 |
| C3 | スクリーンショットにプレースホルダーがない | 目視（自動困難） | ⚠️ 半自動 |
| C4 | スクリーンショット 1枚目がアプリのコア機能を見せている | 目視 | ⚠️ 半自動 |

### D. サブスクリプション（RevenueCat アプリ必須）

| # | チェック項目 | 確認方法 | 自動化可否 |
|---|------------|---------|-----------|
| D1 | ASC にサブスクリプショングループが存在する | `asc subscriptions groups list` | ✅ 自動 |
| D2 | サブスクリプショングループにスクリーンショットが添付済み | ASC GUI 確認（API なし） | ⚠️ 手動必須 |
| D3 | Paywall スクリーンショット（EN + JA）がグループに添付済み | 同上 | ⚠️ 手動必須 |
| D4 | RC Offering のパッケージが ASC の IAP と一致している | RC MCP `list_packages` vs `asc iaps list` | ✅ 自動 |
| D5 | Sandbox で購入フローが動作する | 実機テスト | ⚠️ 手動必須 |

### E. プライバシー・コンプライアンス

| # | チェック項目 | 確認方法 | 自動化可否 |
|---|------------|---------|-----------|
| E1 | アプリ内に Privacy Policy へのリンクがある | Maestro or 目視 | ⚠️ 半自動 |
| E2 | アカウント作成があれば削除機能がある | コード検索 `delete.*account` | ✅ 自動 |
| E3 | HealthKit データを広告に使っていない | 該当なければスキップ | ✅ 自動 |
| E4 | プッシュ通知を課金コンテンツとして販売していない | Paywall コピー目視 | ⚠️ 手動 |

### F. 機能テスト

| # | チェック項目 | 確認方法 | 自動化可否 |
|---|------------|---------|-----------|
| F1 | ユニットテスト全件 PASS | `fastlane test` | ✅ 自動 |
| F2 | シミュレータでクラッシュなし | `fastlane build_for_simulator` | ✅ 自動 |
| F3 | 実機で起動・コア機能が動作する | `fastlane build_for_device` → 目視 | ⚠️ 手動 |
| F4 | オフライン時にアプリがクラッシュしない | 機内モードで確認 | ⚠️ 手動 |
| F5 | 全外部リンク（Privacy Policy 等）が生きている | `curl -I <url>` | ✅ 自動 |
| F6 | アプリ内に "Lorem ipsum" がない | `grep -r "lorem\|Lorem\|placeholder" Sources/` | ✅ 自動 |

---

## CI/CD パイプライン実装（Fastfile ゲート）

**コンセプト:** `fastlane full_release` を直接呼ばせない。必ず `fastlane preflight` を先に通す。

### Fastfile に追加する lane

```ruby
# すべての提出の前に必ず実行する
lane :preflight do |options|
  app_dir = options[:app_dir] || "."

  UI.message "=== GATE 1: Greenlight ==="
  greenlight_result = sh("/tmp/greenlight/build/greenlight preflight #{app_dir} --json 2>&1", error_callback: proc { |result|
    UI.user_error!("Greenlight が見つかりません。インストールしてください: cd /tmp && git clone https://github.com/RevylAI/greenlight.git && cd greenlight && make build")
  })

  # CRITICAL が 0 件か確認
  if greenlight_result.include?('"critical":') && !greenlight_result.include?('"critical":0')
    UI.user_error!("GATE 1 FAILED: Greenlight CRITICAL issues detected. Fix before submitting.")
  end
  UI.success("GATE 1 PASSED: Greenlight CRITICAL = 0")

  UI.message "=== GATE 2A: Build Settings ==="
  # 開発チームID チェック
  pbxproj = File.read("#{app_dir}/**/*.xcodeproj/project.pbxproj")
  if pbxproj.include?('DEVELOPMENT_TEAM = ""') || pbxproj.include?("DEVELOPMENT_TEAM = ''")
    UI.user_error!("GATE 2 FAILED: DEVELOPMENT_TEAM is empty. Set your Apple Team ID.")
  end

  # デプロイターゲット確認（17.0 以下）
  if pbxproj.match?(/IPHONEOS_DEPLOYMENT_TARGET = 1[89]\./)
    UI.user_error!("GATE 2 FAILED: Deployment target is iOS 18+. Lower to 17.0.")
  end
  UI.success("GATE 2A PASSED: Build settings OK")

  UI.message "=== GATE 2B: No debug artifacts ==="
  sources = Dir.glob("#{app_dir}/**/*.swift").map { |f| File.read(f) }.join("\n")
  if sources.match?(/TODO|FIXME|fatalError\("PLACEHOLDER/)
    UI.user_error!("GATE 2 FAILED: Debug artifacts found in source code.")
  end
  UI.success("GATE 2B PASSED: No debug artifacts")

  UI.message "=== GATE 2C: Unit Tests ==="
  run_tests(
    scheme: options[:scheme],
    device: "iPhone 16 Pro",
    clean: false
  )
  UI.success("GATE 2C PASSED: All unit tests green")

  UI.success("===================================")
  UI.success("ALL GATES PASSED. Ready to release.")
  UI.success("===================================")
end

# 提出はこの lane 経由でのみ可能
lane :safe_release do |options|
  preflight(options)
  full_release
end
```

### 使い方

```bash
# ❌ これを直接呼ばない
fastlane full_release

# ✅ これだけ呼ぶ（preflight が自動実行される）
fastlane safe_release scheme:"ThankfulGratitudeApp"
```

---

## このチェックリストと Greenlight のカバレッジ比較

| カテゴリ | Greenlight | このリスト |
|---------|-----------|-----------|
| PrivacyInfo.xcprivacy | ✅ | ✅（Greenlight に任せる） |
| コード署名 | ⚠️ 一部 | ✅ DEVELOPMENT_TEAM 空チェック |
| スクリーンショット数 | ❌ | ✅ asc で確認 |
| サブスクリプショングループ | ❌ | ✅ 手動必須として明記 |
| メタデータ（EN + JA） | ❌ | ✅ asc で確認 |
| Sandbox テスト | ❌ | ✅ 手動必須として明記 |
| 外部リンク生死確認 | ❌ | ✅ curl で自動確認 |
| Lorem ipsum 残留 | ❌ | ✅ grep で自動確認 |
| デプロイターゲット | ⚠️ 一部 | ✅ 自動チェック |
| アカウント削除機能 | ❌ | ✅ コード検索 |

---

## App Factory での使い方（`app-ship` スキル組み込み）

`app-ship` スキルの提出フローに以下を追加する:

```
STEP 6（現在）: greenlight preflight → CRITICAL=0
↓
STEP 6.5（追加）: fastlane preflight → GATE 2 全項目 PASS
↓
STEP 7（現在）: fastlane full_release → fastlane safe_release に変更
```

**目標:** 10アプリ/日の提出で、リジェクト率を 0% に近づける。

---

## リジェクトパターン別の担当ゲート

Daily Dhamma でのリジェクト実績と、このパイプラインでの対応:

| リジェクト理由 | 実績 | 担当ゲート | 防止策 |
|---------------|------|-----------|--------|
| ITMS-91061（PrivacyInfo なし） | ✅ 発生した | GATE 1 Greenlight | Fix 4 |
| サブスクリプショングループ スクショなし | ✅ 発生した | GATE 2 D2-D3（手動） | Phase 1 ステップ 3-4 |
| Guideline 3.1.2（Paywall 不明瞭） | 潜在リスク | GATE 2 D5（手動） | Paywall 目視確認 |
| Guideline 5.1.1(i)（Privacy Policy なし） | 潜在リスク | GATE 2 E1 | Settings 画面確認 |
| Guideline 2.1（クラッシュ） | 今回の問題 | GATE 2 F1-F3 | テスト + 実機確認 |
