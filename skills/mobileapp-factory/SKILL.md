---
name: mobileapp-factory
description: Ralph Loop パターンで毎日1本 iOS アプリを自律ビルド・リリースする。Use when triggered by mobileapp-factory cron, or told to "run mobileapp-factory", "trigger daily app build", "start app factory".
---

# mobileapp-factory v3

Source: snarktank/ralph (https://github.com/snarktank/ralph/blob/main/ralph.sh)
Source: rshankras WORKFLOW.md (https://github.com/rshankras/claude-code-apple-skills/blob/main/skills/product/WORKFLOW.md)
Source: v3 spec §14 (/Users/anicca/anicca-project/.cursor/plans/ios/1.6.3/2026-02-28/mobileapp-factory-v3-spec.md)

## 役割
Anicca(僕)が実行する。2つの責任:
1. **起動**: mobile-apps/ にフレッシュ環境を作り ralph.sh を起動する
2. **橋渡し**: Dais の Slack 返信をファイルシステムに書く(CC は Slack を見れない)

---

## STEP 1: mobile-apps フォルダを作成

```bash
APP_DIR=/Users/anicca/anicca-project/mobile-apps/$(date +%Y%m%d)-$(date +%H%M%S)-app
mkdir "$APP_DIR"
```

## STEP 2: テンプレートをコピー

```bash
BUILDER=/Users/anicca/anicca-project/.claude/skills/mobileapp-builder

cp "$BUILDER/prd.json"  "$APP_DIR/prd.json"
cp "$BUILDER/CLAUDE.md" "$APP_DIR/CLAUDE.md"
cp "$BUILDER/ralph.sh"           "$APP_DIR/ralph.sh"
cp "$BUILDER/validate.sh"        "$APP_DIR/validate.sh"
chmod +x "$APP_DIR/ralph.sh" "$APP_DIR/validate.sh"
touch "$APP_DIR/progress.txt"
```

## STEP 3: .env を作成(secrets)

Source: The Twelve-Factor App (https://12factor.net/config)
> 「stores config in environment variables」

```bash
# SSOT: ~/.config/mobileapp-builder/.env
# Source: The Twelve-Factor App (https://12factor.net/config)
source ~/.config/mobileapp-builder/.env
cat > "$APP_DIR/.env" << EOF
KEYCHAIN_PASSWORD=$KEYCHAIN_PASSWORD
APPLE_ID=$APPLE_ID
ASC_KEY_ID=$ASC_KEY_ID
ASC_ISSUER_ID=$ASC_ISSUER_ID
ASC_PRIVATE_KEY_PATH=$ASC_KEY_PATH
MIXPANEL_TOKEN=
RC_PROJECT_ID=
APP_ID=
BUNDLE_ID=
EOF
```

## STEP 4: Slack に起動報告

Slack #metrics に送る:
```
🏭 Factory 起動
📁 $APP_DIR
⏰ 開始: $(date)
```

## STEP 4.5: 提出前の preflight を機械的に通す

Source: Apple Developer - App Review Guidelines (https://developer.apple.com/app-store/review/guidelines/)
核心の引用: "Test your app for crashes and bugs"
核心の引用: "Ensure that all app information and metadata is complete and accurate"
核心の引用: "Provide App Review with full access to your app"
Source: App Store Connect Help - Overview of submitting for review (https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/overview-of-submitting-for-review/)
核心の引用: "Use the App Review information section on the latest approved app version for that platform to provide additional information or context that will help App Review during the review process."
核心の引用: "App versions for each platform are submitted separately."

→ 1つでも欠けたら起動後の submit へ進まない。
→ crash, bug, metadata, contact, demo account, backend live, access instructions, and review notes を最初に揃える。
→ platform ごとに分けて扱い、App Review information を SSOT にする。

## STEP 5: tmux で ralph.sh を起動

```bash
tmux kill-session -t factory 2>/dev/null || true
```

exec で起動(coding-agent パターン):
```
exec pty:true background:true command:"tmux new-session -d -s factory -c '$APP_DIR' './ralph.sh'"
```

sessionId を記録する。以降は process action:log/poll で監視。

## STEP 6: ralph.sh が自走する(Anicca は待つ)

ralph.sh が自分で:
- 各 iteration で CC を起動
- US 完了ごとに Slack に通知(curl)
- validate.sh を実行
- WAITING_FOR_HUMAN を検出して Slack に通知

**Anicca は基本的に何もしない。Slack 通知が来るのを待つ。**

### 🚨 ビルドエラー時のルール(BP 2)

Source: Reddit r/ClaudeAI - Best Practices After Shipping iOS Apps (https://www.reddit.com/r/ClaudeAI/comments/1ridakj/best_practices_ive_learned_after_shipping/)
核心の引用: 「Claude's default behavior is to make a shallow fix and retry immediately.」

**禁止**: 浅い修正 + 即リトライ
**必須**:
1. ビルドログを読み、root cause(根本原因)を特定する
2. 根本原因を修正してから再ビルドする
3. 表面的な対症療法はしない

このルールは ralph.sh が CC に渡す CLAUDE.md に記載する。

## STEP 7: 橋渡し

CC が `WAITING_FOR_HUMAN` を `$APP_DIR/progress.txt` に書いたら、ralph.sh が Slack に通知する。

Dais が Slack で返信 → Anicca が対応。

具体的な手順は `references/us-005a-infra.md`、`references/us-005b-monetization.md` と `references/us-009-submit.md` に書いてある。
Anicca はそれを読んで従うこと。

橋渡しで Anicca がやること:
1. `APP_DIR=$(ls -td /Users/anicca/anicca-project/mobile-apps/*-app | head -1)` で今のビルドフォルダを特定
2. Dais の返信内容を `$APP_DIR/.env` に追記
3. `sed -i '' '/WAITING_FOR_HUMAN/d' $APP_DIR/progress.txt` で WAITING_FOR_HUMAN を削除
4. ralph.sh の次のイテレーションで CC が自動再開

---

## STEP 8: 完了処理

ralph.sh が終了したら:
1. process action:log で最終ログ確認
2. Slack に完了報告
3. git add + commit + push

## STEP 9: TikTokマーケティング初期化

ビルド完了後、新アプリのTikTokマーケティングフォルダを作成する。

```bash
APP_DIR=$(ls -td /Users/anicca/anicca-project/mobile-apps/*-app | head -1)
mkdir -p "$APP_DIR/tiktok/posts"
```

### tiktok/config.json 作成

```bash
# APP_NAME と INTEGRATION_ID は手動で設定する必要がある
# Dais が TikTok アカウント作成 + Postiz 接続後に渡す
cat > "$APP_DIR/tiktok/config.json" << EOF
{
  "app_name": "APP_NAME",
  "integration_id": "INTEGRATION_ID",
  "basePrompt": "iPhone photo of ...",
  "status": "pending_tiktok_account"
}
EOF
```

### tiktok/strategy.json 作成

US-001 のトレンドリサーチ結果から初期戦略を生成:

```bash
cat > "$APP_DIR/tiktok/strategy.json" << EOF
{
  "target_audience": "(US-002 product-plan.md から)",
  "hook_categories": ["pain_point", "curiosity", "transformation"],
  "active_hooks": [],
  "proven_hooks": [],
  "dropped_hooks": [],
  "cta_test_queue": [],
  "hook_test_queue": [],
  "posting_schedule": ["08:00", "16:30", "21:00"]
}
EOF
```

### tiktok/hook-performance.json 初期化

```bash
echo '{"hooks":[],"ctas":[]}' > "$APP_DIR/tiktok/hook-performance.json"
```

Slack #metrics に報告:
```
🏭 TikTok マーケティング初期化完了
📁 $APP_DIR/tiktok/
⏳ TikTokアカウント作成待ち(Daisが手動で設定後、config.json を更新)
```

**注意: TikTokアカウント作成 + Postiz接続は手動。** Daisがアカウント作成→Postiz接続→integration_id取得後に、config.json の `integration_id` と `status` を更新する。`status` が `"pending_tiktok_account"` のアプリは Larry のループでスキップされる。

---

| 項目 | 値 |
|------|-----|
| 実行環境 | Mac Mini (ローカル) |
| 作業ディレクトリ | /Users/anicca/anicca-project/mobile-apps/ |
| builder スキル | /Users/anicca/anicca-project/.claude/skills/mobileapp-builder/ |
| claude パス | /opt/homebrew/bin/claude |
| Slack | #metrics |

---

## 効率化 BP(2026-04-05 追加)

### BP-M: iOS ビルドは依存整理とターゲット分割を優先する
Source: Apple Developer - Improving the speed of incremental builds
URL: https://developer.apple.com/documentation/xcode/improving-the-speed-of-incremental-builds
核心の引用: "To improve build performance, simplify your target's dependency list, and break up monolithic targets so that Xcode can do more work in parallel."

→ factory で新規 iOS アプリを作るときは、巨大ターゲットを増やさず、依存を最小化し、並列化できる構成を優先する。CI/ローカルの両方で incremental build の改善を前提にする。

### BP-A: .pbxproj は AI に編集させない
Source: X post - https://x.com/i/status/1988012974024651071
核心の引用: 「Never modify .pbxproj files with AI: Generate Swift/SwiftUI files via Claude, then manually add to Xcode. Prevents corruption.」
→ mobileapp-builder/CLAUDE.md に「.pbxproj 編集禁止」ルールを必ず含めること。

### BP-B: Feature Flags everywhere
Source: X post - https://x.com/i/status/1988012974024651071
核心の引用: 「Feature flags everywhere: For experimental code-toggle without rebuilds.」
→ 新機能は feature flag で囲む(CLAUDE.md に記載)。

### BP-C: Behavior-First TDD(バグ80%削減)
Source: X post - https://x.com/i/status/2038678965888712951
核心の引用: 「Write failing XCTest/XCUITest for [scenario], then implement to pass. Reduces bugs by 80%+」
→ US 実装は「テスト先行(failing → implement → passing)」が必須。

### BP-D: App Store 提出は ASC CLI(Fastlane 廃止)
Source: X post (@rudrank) - https://x.com/i/status/2040780698177716630
核心の引用: 「asc publish appstore for end-to-end App Store releases, replacing Fastlane.」
インストール: `brew install asc` | GitHub: https://github.com/rudrankriyam/App-Store-Connect-CLI
→ us-009-submit.md を ASC CLI ベースに更新済み(要確認)。

### BP-E: App Store Review 2026 強化点
Source: X post — https://x.com/i/status/2039067781845684726
核心の引用: 「Guideline 2.5.2: template-based/low-originality apps are being rejected.」
→ 各アプリに固有のブランドカラー/アイコン/コピーを必ず設定すること。
Source: X post — https://x.com/i/status/2025927666818298133
核心の引用: 「Guideline 5.1 on AI data disclosure/consent is still causing 2026 rejections」
→ Privacy Policy に「AI によるデータ利用」開示文を必ず追加すること。
Source: Apple App Review Guidelines — https://developer.apple.com/app-store/review/guidelines/
核心の引用: 「want to help you understand our guidelines so you can be confident your app will get through the review process quickly.」
→ 提出前の preflight で review metadata, review notes, login, and access instructions を完全に埋め、review-ready でない案件は提出しない。

### BP-F: 提出・配信の自動化は ASC CLI / EAS Submit を優先する
Source: asc - App Store Connect CLI | Automate iOS Releases from Terminal
URL: https://asccli.sh
核心の引用: 「A fast, lightweight, and scriptable CLI for App Store Connect. Ship iOS, macOS, tvOS, and visionOS apps from your terminal. TestFlight, builds, submissions, code signing, and CI/CD.」

Source: Expo Docs - EAS Submit
URL: https://docs.expo.dev/submit/introduction/
核心の引用: 「EAS Submit is a hosted service for submitting Android and iOS app binaries to the Google Play Store and Apple App Store from the command line.」

→ App Store 提出/配信の定型作業は、手動 UI より CLI を優先する。`asc` が App Store Connect の中心、`eas submit` は Expo 系の補助導線として扱う。

### BP-G: 提出前は App Review Guidelines の common missteps を毎回確認する
Source: Apple Developer - App Review Guidelines
URL: https://developer.apple.com/app-store/review/guidelines/
核心の引用: 「To help your app approval go as smoothly as possible, review the common missteps listed below that can slow down the review process or trigger a rejection.」

→ 申請前チェックに「common missteps の再確認」を必須ステップとして追加する。

### BP-H: App Store 提出は app-store-connect スキルで統一する
Source: asc - App Store Connect CLI | Automate iOS Releases from Terminal
URL: https://asccli.sh
核心の引用: 「A fast, lightweight, and scriptable CLI for App Store Connect. Ship iOS, macOS, tvOS, and visionOS apps from your terminal. TestFlight, builds, submissions, code signing, and CI/CD.」

→ 提出・検証・メタデータ更新は app-store-connect スキルを優先し、手動 UI 操作を減らす。

### BP-I: 変更後は simulator + accessibility で E2E を回す
Source: X post - https://x.com/i/status/2042420365461168635

### BP-J: 提出前は review-ready でないものを止める
Source: Apple Developer - App Review Guidelines (https://developer.apple.com/app-store/review/guidelines/)
核心の引用: "Provide App Review with full access to your app. If your app includes account-based features, provide either an active demo account or fully-featured demo mode, plus any other hardware or resources that might be needed to review your app"
→ App Review Information, demo account, backend live, non-obvious feature notes が揃うまで submit しない。

### BP-K: App Store 配信は CLI を優先し、手動 UI を減らす
Source: asc - App Store Connect CLI | Automate iOS Releases from Terminal (https://asccli.sh)
核心の引用: "A fast, lightweight, and scriptable CLI for App Store Connect. Ship iOS, macOS, tvOS, and visionOS apps from your terminal."
→ TestFlight, submission, metadata, screenshots, workflow は asc / workflow.json を先に使う。
核心の引用: 「Claude points at a simulator, navigates via accessibility tree/screenshots, taps/fills/opens everything autonomously.」

→ UI 変更後の確認は simulator の accessibility tree ベースで行い、手作業クリックを減らす。

### BP-J: App Review Information の未記入は提出失敗として扱う
Source: Apple Developer - Submitting / App Store
URL: https://developer.apple.com/app-store/submitting/
核心の引用: 「Apple reviews all apps, app updates, bundles, In-App Purchases, and App In-App Events to evaluate they meet requirements for privacy, security, safety, and reliability.」
Source: Apple Developer - App Review Guidelines
URL: https://developer.apple.com/app-store/review/guidelines/
核心の引用: 「review the common missteps listed below that can slow down the review process or trigger a rejection.」

→ App Review Information, demo account credentials, review notes, and login instructions が空ならその提出は失敗扱いにして、提出前チェックで必ず止める。

# FIX by skill-fixer 2026-04-24:
# 原因: factory-bp-efficiency が存在しない workspace 側パスを編集先として案内し、exact-match edit が失敗する原因になっていた。
# 修正: 実在する shared skill パスだけを前提にするよう注意書きを追加した。

### BP-K: 提出の中心は ASC CLI に寄せる
Source: asc - App Store Connect CLI | Automate iOS Releases from Terminal
URL: https://asccli.sh
核心の引用: 「A fast, lightweight, and scriptable CLI for App Store Connect. Ship iOS, macOS, tvOS, and visionOS apps from your terminal.」
Source: GitHub - App Store Connect CLI
URL: https://github.com/rudrankriyam/App-Store-Connect-CLI
核心の引用: 「Fast, scriptable CLI for the App Store Connect API. Automate TestFlight, builds, submissions, signing, analytics, screenshots, subscriptions ...」

→ 手動 UI を減らし、提出・検証・メタデータ更新は ASC CLI を既定にする。

### BP-L: 提出前は review-ready を機械的に止める
Source: Apple Developer - App Review Guidelines
URL: https://developer.apple.com/app-store/review/guidelines/
核心の引用: 「want to help you understand our guidelines so you can be confident your app will get through the review process quickly.」
Source: Apple Developer - App Review Guidelines
URL: https://developer.apple.com/app-store/review/guidelines/
核心の引用: 「provide App Review with full access to your app」

→ App Review Information, demo account, login instructions, backend access, and required hardware/resources が揃うまで submit しない。未記入は提出失敗扱いにする。

### BP-M: iOS 自動化は accessibility tree 優先、スクリーンショットは補助に限定する
Source: X search - https://x.com/i/status/2042531411517935834
核心の引用: 「Leverage iOS Accessibility Tree as "Eyes" for Claude」
Source: X search - https://x.com/i/status/2042420365461168635
核心の引用: 「Fallback to screenshots only for custom UI gaps or visual verification.」

→ simulator / E2E / QA は accessibility tree を主経路にし、スクリーンショットは検証フォールバックだけにする。

### BP-N: App Store 提出の既定は ASC CLI に寄せる
Source: X search - https://x.com/i/status/2045227021543071947
核心の引用: 「the leading CLI tool for automating App Store submissions is the App Store Connect CLI (ASC CLI)」
Source: App Store Connect Help - Submitting for review overview
URL: https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/overview-of-submitting-for-review/
核心の引用: 「Learn how to submit using the App Store Connect API.」

→ 手動 App Store Connect UI より ASC CLI と App Store Connect API を優先し、提出フローを CLI 前提で保つ。
### BP-O: App Review 情報は最新承認版を SSOT にする
Source: App Store Connect Help - Overview of submitting for review
URL: https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/overview-of-submitting-for-review/
核心の引用: 「Use the App Review information section on the latest approved app version for that platform to provide additional information or context that will help App Review during the review process.」

→ review notes, demo account, access instructions, backend context は最新承認版の App Review information を正本にして埋める。空欄や不整合があれば提出しない。

### BP-P: 提出前は crash, metadata, contact, access を機械的に潰す
Source: Apple Developer - App Review Guidelines
URL: https://developer.apple.com/app-store/review/guidelines/
核心の引用: 「Test your app for crashes and bugs」
Source: Apple Developer - App Review Guidelines
URL: https://developer.apple.com/app-store/review/guidelines/
核心の引用: 「Ensure that all app information and metadata is complete and accurate」
Source: Apple Developer - App Review Guidelines

### BP-Q: App Review information は最新承認版の SSOT に固定する
Source: App Store Connect Help - Overview of submitting for review
URL: https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/overview-of-submitting-for-review/
核心の引用: 「Use the App Review information section on the latest approved app version for that platform to provide additional information or context that will help App Review during the review process.」
Source: App Store Connect Help - Overview of submitting for review
URL: https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/overview-of-submitting-for-review/
核心の引用: 「App versions for each platform are submitted separately.」
→ review notes, demo account, login instructions, backend access, and hardware/resources は platform 別にまとめ、古い提出メモを使い回さない。

### BP-R: 提出自動化は App Store Connect API / ASC CLI を既定にする
Source: App Store Connect Help - Overview of submitting for review
URL: https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/overview-of-submitting-for-review/
核心の引用: 「Learn how to submit using the App Store Connect API.」
Source: X search
URL: https://x.com/i/status/2024170351643807841
核心の引用: 「the leading CLI tool for automating App Store submissions is the App Store Connect CLI (ASC CLI)」
→ 手動 UI を減らし、submit / metadata update / review workflow は CLI 先行にする。

### BP-S: ビルド効率改善は依存グラフを薄くし、Xcode Build Analyzer でボトルネックを潰す
Source: Apple Developer - Improving the speed of incremental builds
URL: https://developer.apple.com/documentation/xcode/improving-the-speed-of-incremental-builds
核心の引用: 「To improve build performance, simplify your target's dependency list, and break up monolithic targets so that Xcode can do more work in parallel.」
Source: Clawhub search
URL: local run 2026-05-15
核心の引用: 「xcode-build-analyzer  Xcode Build Analyzer  (3.011)」
→ build/test が遅いときは、まず依存を減らし、巨大ターゲットを分割し、Xcode Build Analyzer で詰まり箇所を確認する。

### BP-S: iOS 自動化は accessibility tree 優先, screenshots は補助に限定する
Source: X search
URL: https://x.com/i/status/2042531411517935834
核心の引用: 「Leverage iOS Accessibility Tree as \"Eyes\" for Claude」
Source: X search
URL: https://x.com/i/status/2042420365461168635
核心の引用: 「Fallback to screenshots only for custom UI gaps or visual verification.」
→ simulator, E2E, QA は accessibility tree を主経路にし、スクリーンショットは検証フォールバックだけにする。

核心の引用: https://developer.apple.com/app-store/review/guidelines/
URL: https://developer.apple.com/app-store/review/guidelines/
核心の引用: 「Provide App Review with full access to your app」

→ submission 前の固定チェックに crash, metadata, contact, demo account, backend live, review notes を追加し、1つでも欠けたら submit しない。

### BP-Q: App Store Connect API を提出の既定経路にする
Source: App Store Connect Help - Overview of submitting for review
URL: https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/overview-of-submitting-for-review/
核心の引用: 「Learn how to submit using the App Store Connect API.」

→ 手動 UI より API / CLI ベースの流れを優先し、提出, items, metadata 更新をスクリプトから実行する。


### BP-R: 提出前は crash, bug, metadata, access, review info を一括で潰す
Source: Apple Developer - App Review Guidelines
URL: https://developer.apple.com/app-store/review/guidelines/
核心の引用: 「review the common missteps listed below that can slow down the review process or trigger a rejection.」
核心の引用: 「Test your app for crashes and bugs」
核心の引用: 「Ensure that all app information and metadata is complete and accurate」
Source: App Store Connect Help - Overview of submitting for review
URL: https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/overview-of-submitting-for-review/
核心の引用: 「Use the App Review information section on the latest approved app version for that platform to provide additional information or context that will help App Review during the review process.」

→ factory の submit 前チェックを固定化し、crash, bug, metadata, contact, login/access, review notes のどれかが欠けたら送信しない。

### BP-S: UI 検証は headless xcodebuild と accessibility を既定にする
Source: X search - https://x.com/i/status/2009339319849242996
核心の引用: 「iOS CI/CD pipelines leverage `xcodebuild` for headless simulator builds and testing」
Source: X search - https://x.com/i/status/2042531411517935834
核心の引用: 「Leverage iOS Accessibility Tree as \"Eyes\" for Claude」
Source: X search - https://x.com/i/status/2042420365461168635
核心の引用: 「Fallback to screenshots only for custom UI gaps or visual verification.」

→ 変更後の検証は xcodebuild + accessibility tree を先に回し、スクリーンショットは補助に限定する。

### BP-T: 提出前ゲートは review-ready だけを通す
Source: Apple Developer - App Review Guidelines
URL: https://developer.apple.com/app-store/review/guidelines/
核心の引用: "Test your app for crashes and bugs"
核心の引用: "Ensure that all app information and metadata is complete and accurate"
核心の引用: "Update your contact information in case App Review needs to reach you"
核心の引用: "Provide App Review with full access to your app"
Source: App Store Connect Help - Overview of submitting for review
URL: https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/overview-of-submitting-for-review/
核心の引用: "Use the App Review information section on the latest approved app version for that platform to provide additional information or context that will help App Review during the review process."
核心の引用: "App versions for each platform are submitted separately."

→ factory の submit 前チェックを crash, bug, metadata, contact, access, backend live, demo account, review notes に固定し、1つでも欠けたら submit を止める。platform ごとに App Review information を SSOT にする。

### BP-U: submission は platform 分割と item-only を前提に並列化する
Source: App Store Connect Help - Overview of submitting for review
URL: https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/overview-of-submitting-for-review/
核心の引用: "App versions for each platform are submitted separately."
核心の引用: "A platform can have a maximum of two submissions under review at a time: one that includes an app version and one that includes items... without an app version."
→ App version submission と items-only submission を分けて、platform ごとの詰まりを減らす。
### BP-V: App Store 系の優先スキルは app-store-connect と xcode-build-analyzer に寄せる
Source: ClawHub search
URL: local run 2026-05-21
核心の引用: "app-store-connect  App Store Connect  (3.060)"
核心の引用: "xcode-build-analyzer  Xcode Build Analyzer  (3.016)"
→ 提出・メタデータ操作・状態確認は app-store-connect、ビルド詰まりの可視化は xcode-build-analyzer を既定導線にする。

### BP-W: Review notes は demo access と backend live を前提に一括で埋める
Source: Apple Developer App Review Guidelines
URL: https://developer.apple.com/app-store/review/guidelines/
核心の引用: "Provide App Review with full access to your app. If your app includes account-based features, provide either an active demo account or fully-featured demo mode, plus any other hardware or resources that might be needed to review your app (e.g. login credentials or a sample QR code)"
核心の引用: "Enable backend services so that they’re live and accessible during review"
核心の引用: "Include detailed explanations of non-obvious features and in-app purchases in the App Review notes, including supporting documentation where appropriate"
→ review notes, demo account, backend access, required hardware/resources, and non-obvious feature explanation を同じ提出文脈にまとめ、空欄があれば submit しない。
