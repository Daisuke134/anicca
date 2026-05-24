---
name: factory-bp-efficiency
description: "Factory効率化BPを検索し、ファクトリープロセスを改善する。Use when triggered by factory-bp-efficiency cron or told to 'improve factory efficiency'."
---

# factory-bp-efficiency

BP-1: 「Keep each skill focused on one job」
Source: OpenClaw Skills Guide (https://openclaw-ai.online/skills/)

## 役割

ファクトリー自体の効率を上げるツール/スキル/プラクティスを検索し、プロセスを改善する。
**CCは使わない。Anicca（OpenClaw）が直接実行する。**

## 2026-04-26 追記

- App Store 提出の下準備は、まず crash/bug/metadata/contact/access を潰す。
  - Source: App Review Guidelines, https://developer.apple.com/app-store/review/guidelines/
  - Quote: "Make sure you: Test your app for crashes and bugs"
  - Source: App Review Guidelines, https://developer.apple.com/app-store/review/guidelines/
  - Quote: "Ensure that all app information and metadata is complete and accurate"
- App Review 情報は最新承認版の App Review information を使って、review に必要な文脈を必ず渡す。
  - Source: App Store Connect Help, https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/overview-of-submitting-for-review/
  - Quote: "Use the App Review information section on the latest approved app version for that platform to provide additional information or context that will help App Review during the review process."
- サブミッションは platform ごとに分け、App version 付きと items-only の同時進行を前提にする。
  - Source: App Store Connect Help, https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/overview-of-submitting-for-review/
  - Quote: "App versions for each platform are submitted separately."

## 2026-04-29 追記

- 提出前の失敗要因は、クラッシュ、バグ、メタデータ不備、連絡先不備、アクセス不足を先に潰す。
  - Source: App Review Guidelines, https://developer.apple.com/app-store/review/guidelines/
  - Quote: "Test your app for crashes and bugs"
  - Quote: "Ensure that all app information and metadata is complete and accurate"
  - Quote: "Update your contact information in case App Review needs to reach you"
  - Quote: "Provide App Review with full access to your app."
- App Review Information は最新承認版に置き、レビュー文脈をそこに集約する。
  - Source: App Store Connect Help, https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/overview-of-submitting-for-review/
  - Quote: "Use the App Review information section on the latest approved app version for that platform"
- サブミッションは platform 別、さらに item 別に分けて流す。
  - Source: App Store Connect Help, https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/overview-of-submitting-for-review/
  - Quote: "App versions for each platform are submitted separately."
  - Quote: "You can choose to submit items for review together with, or separately from, an app version."
  - Quote: "Each platform can have one app version submission under review at a time."
  - Quote: "A platform can have a maximum of two submissions under review at a time: one that includes an app version and one that includes items, like In-App Events or custom product pages, without an app version."
- 送信自動化は App Store Connect API を基点にし、ASC CLI を入口にする。
  - Source: App Store Connect Help, https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/overview-of-submitting-for-review/
  - Quote: "Learn how to submit using the App Store Connect API."
  - Source: X search, https://x.com/i/status/2024170351643807841
  - Quote: "the leading CLI tool for automating App Store submissions is the App Store Connect CLI (ASC CLI)"
- iOS CI は headless `xcodebuild` とアクセシビリティツリー優先で回し、スクリーンショットは補助に落とす。
  - Source: X search, https://x.com/i/status/2009339319849242996
  - Quote: "iOS CI/CD pipelines leverage `xcodebuild` for headless simulator builds and testing"
  - Source: X search, https://x.com/i/status/2042531411517935834
  - Quote: "Leverage iOS Accessibility Tree as \"Eyes\" for Claude"
  - Source: X search, https://x.com/i/status/2042420365461168635
  - Quote: "Fallback to screenshots only for custom UI gaps or visual verification."

## 2026-04-19 追記

- App Store 提出は App Store Connect CLI を中心にし、App Store Connect API 経由での送信を優先する。
  - Source: X search, https://x.com/i/status/2045227021543071947
  - Quote: "The primary CLI tool for automating App Store submissions in 2026 is App Store Connect CLI (ASC CLI)"
  - Source: App Store Connect Help, https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/overview-of-submitting-for-review/
  - Quote: "Learn how to submit using the App Store Connect API."
- App Review 情報は必須コンテキストとして扱い、最新承認版の App Review information を必ず埋める。
  - Source: App Store Connect Help, https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/overview-of-submitting-for-review/
  - Quote: "Use the App Review information section on the latest approved app version for that platform to provide additional information or context that will help App Review during the review process."
- iOS ビルドとテストは headless `xcodebuild` とキャッシュ、アクセシビリティ検証を前提にする。
  - Source: X search, https://x.com/i/status/2009339319849242996
  - Quote: "iOS CI/CD pipelines leverage `xcodebuild` for headless simulator builds and testing"
  - Source: Xcode 26 Release Notes, https://developer.apple.com/documentation/xcode-release-notes/xcode-26-release-notes
  - Quote: "Update your apps to use new features, and test your apps against API changes."
- iOS 自動化はアクセシビリティツリー優先で、スクリーンショットは検証用フォールバックに限定する。
  - Source: X search, https://x.com/i/status/2042531411517935834
  - Quote: "Leverage iOS Accessibility Tree as \"Eyes\" for Claude"
  - Source: X search, https://x.com/i/status/2042420365461168635
  - Quote: "Fallback to screenshots only for custom UI gaps or visual verification."
- iOS の UI 検証は XcodeBuildMCP と AXe を優先し、`xcodebuild` は build/run/test の実行基盤として使う。
  - Source: X search, https://x.com/i/status/2009339319849242996
  - Quote: "iOS CI/CD pipelines leverage `xcodebuild` for headless simulator builds and testing"
  - Source: X search, https://x.com/i/status/2007686252502437992
  - Quote: "accessibility tree (UI hierarchy) in Claude Code"
- App Review 送信前は、クラッシュ, バグ, メタデータ, 連絡先, アクセス不足を先に潰す。
  - Source: Apple Developer App Review Guidelines, https://developer.apple.com/app-store/review/guidelines/
  - Quote: "Test your app for crashes and bugs"
  - Quote: "Ensure that all app information and metadata is complete and accurate"
  - Quote: "Update your contact information in case App Review needs to reach you"
  - Quote: "Provide App Review with full access to your app."
- App Review 情報は最新承認版に集約し、プラットフォームごとに分けて submit する。
  - Source: App Store Connect Help, https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/overview-of-submitting-for-review/
  - Quote: "Use the App Review information section on the latest approved app version for that platform"
  - Quote: "App versions for each platform are submitted separately."
- スキルは単一用途に保つ。
  - Source: OpenClaw Skills Guide, https://openclaw-ai.online/skills/
  - Quote: "Keep each skill focused on one job"
- App Store 系の補助スキルを優先採用する。
  - Source: ClawHub search, local run 2026-04-19
  - Quote: "app-store-connect  App Store Connect  (3.427)"
  - Source: ClawHub search, local run 2026-04-19
  - Quote: "xcode-build-analyzer  Xcode Build Analyzer  (3.488)"
  - Source: ClawHub search, local run 2026-05-10
  - Quote: "xcodebuildmcp  xcodebuildmcp  (0.630)"
- App Review は安全性, performance, business, design, {{profile.lateness.stakeholders.senderType}} の観点で事前点検する。
  - Source: Apple Developer App Review Guidelines, https://developer.apple.com/app-store/review/guidelines/
  - Quote: "The following pages you will find our latest guidelines arranged into five clear sections: Safety, Performance, Business, Design, and Legal."

## 2026-05-08 追記

- App Review 送信前は、クラッシュ、バグ、メタデータ、連絡先、アクセス不足を必須ゲートにする。
  - Source: Apple Developer App Review Guidelines, https://developer.apple.com/app-store/review/guidelines/
  - Quote: "Test your app for crashes and bugs"
  - Quote: "Ensure that all app information and metadata is complete and accurate"
  - Quote: "Update your contact information in case App Review needs to reach you"
  - Quote: "Provide App Review with full access to your app."
- App Review 情報は最新承認版の同一 platform に集約し、review 文脈をそこに置く。
  - Source: App Store Connect Help, https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/overview-of-submitting-for-review/
  - Quote: "Use the App Review information section on the latest approved app version for that platform to provide additional information or context that will help App Review during the review process."
- App version と item-only submission は platform ごとに分け、App Store Connect API を送信基点にする。
  - Source: App Store Connect Help, https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/overview-of-submitting-for-review/
  - Quote: "App versions for each platform are submitted separately."
  - Quote: "You can choose to submit items for review together with, or separately from, an app version."
  - Quote: "Learn how to submit using the App Store Connect API."

## 2026-05-11 追記

- App Review notes are a required efficiency lever, not optional commentary. Always include cold-launch testing instructions, demo access, backend/live-service status, and a plain list of external services used.
  - Source: Apple Developer App Review Guidelines, https://developer.apple.com/app-store/review/guidelines/
  - Quote: "Include detailed explanations of non-obvious features and in-app purchases in the App Review notes, including supporting documentation where appropriate"
  - Source: App Store Connect Help, https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/overview-of-submitting-for-review/
  - Quote: "Use the App Review information section on the latest approved app version for that platform to provide additional information or context that will help App Review during the review process."
- Submission planning should stay platform-separated, with one app version submission per platform and one items-only submission maximum alongside it.
  - Source: App Store Connect Help, https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/overview-of-submitting-for-review/
  - Quote: "Each platform can have one app version submission under review at a time."
  - Quote: "A platform can have a maximum of two submissions under review at a time: one that includes an app version and one that includes items, like In-App Events or custom product pages, without an app version."

## 手順

### 1. BP検索（x_search + official docs）

x_search（Grokビルトインツール）で検索する。失敗した場合は、失敗ログを残したうえで公式文書と clawhub 結果を優先して進める。

```
x_search query="claude code iOS app automation best practice 2026"
x_search query="app store submission automation CLI 2026"
x_search query="App Store review guidelines changes 2026"
```

加えて、Apple の公式ページで review 要件と submit flow を確認する。
- https://developer.apple.com/app-store/review/guidelines/
- https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/overview-of-submitting-for-review/

※ x_searchはGrok経由でXを検索し、引用URL付きの要約を返す。
※ 公式文書の App Review information と metadata 要件を最優先にする。
※ clawhub では app-store-connect と xcode-build-analyzer を優先候補として扱う。

### 2. スキル検索（clawhub）

```bash
clawhub search "ios app" --limit 5
clawhub search "app store" --limit 5
clawhub search "xcode build" --limit 5
```

有用なスキルが見つかったら:
```bash
clawhub install <skill-name> --dir ~/.openclaw/skills
```

### 2.5 直近の改善優先順位
- 送信基盤は App Store Connect API / ASC CLI を前提にする。
- 提出前チェックは crash, bug, metadata, contact, access を必須ゲートにする。
- App Review 情報は最新承認版へ集約し、platform ごとに分けて submit する。
- iOS CI は headless `xcodebuild` と accessibility tree を先に使い、スクリーンショットは補助に落とす。
- ビルド可視化と修正支援には xcode-build-analyzer と xcodebuildmcp を優先採用する。
- clawhub では `app-store-connect` と `xcode-build-analyzer` を最優先候補として扱う。
- x_search が不調なら、公式文書と clawhub の検索結果をそのまま改善入力にする。

### 2.6 2026-05-13 の追加BP
- App Store 提出の効率化では、App Review notes に非自明機能、デモアクセス、バックエンド稼働状況、外部サービス一覧を必ず入れる。
  - Source: Apple Developer App Review Guidelines, https://developer.apple.com/app-store/review/guidelines/
  - Quote: "Include detailed explanations of non-obvious features and in-app purchases in the App Review notes, including supporting documentation where appropriate"
  - Source: Apple Developer App Review Guidelines, https://developer.apple.com/app-store/review/guidelines/
  - Quote: "Enable backend services so that they’re live and accessible during review"
- 提出は platform 別に分け、App version submission と items-only submission の両方を使って詰まりを減らす。
  - Source: App Store Connect Help, https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/overview-of-submitting-for-review/
  - Quote: "App versions for each platform are submitted separately."
  - Quote: "You can choose to submit items for review together with, or separately from, an app version."
  - Quote: "A platform can have a maximum of two submissions under review at a time: one that includes an app version and one that includes items... without an app version."
- OpenClaw のスキルは単一用途に保つ。
  - Source: OpenClaw Skills Guide, https://openclaw-ai.online/skills/
  - Quote: "Keep each skill focused on one job"

### 2.7 2026-05-14 の追加BP
- App Store 提出の効率化では、クラッシュ, バグ, メタデータ, 連絡先, アクセス不足, バックエンド可用性を先に潰し、レビュー文脈は最新承認版の App Review information に集約する。
  - Source: Apple Developer App Review Guidelines, https://developer.apple.com/app-store/review/guidelines/
  - Quote: "Test your app for crashes and bugs"
  - Quote: "Ensure that all app information and metadata is complete and accurate"
  - Quote: "Update your contact information in case App Review needs to reach you"
  - Quote: "Provide App Review with full access to your app."
  - Source: App Store Connect Help, https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/overview-of-submitting-for-review/
  - Quote: "Use the App Review information section on the latest approved app version for that platform to provide additional information or context that will help App Review during the review process."
- Platform ごとに submit を分け、app version submission と items-only submission を並行活用して待ち行列を短くする。
  - Source: App Store Connect Help, https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/overview-of-submitting-for-review/
  - Quote: "App versions for each platform are submitted separately."
  - Quote: "A platform can have a maximum of two submissions under review at a time: one that includes an app version and one that includes items... without an app version."
- OpenClaw のスキルは単一用途に保つ。
  - Source: OpenClaw Skills Guide, https://openclaw-ai.online/skills/
  - Quote: "Keep each skill focused on one job"

### 2.8 2026-05-17 の追加BP
- X search が使えないときは、クレジット/予算制限を先に疑い、公式文書と ClawHub の結果で代替する。
  - Source: x_search tool error, 2026-05-17
  - Quote: "Your team 8ca26a44-1fe7-4588-921b-abd9550c8dcc has either used all available credits or reached its monthly spending limit."
- App Store 提出効率では、App Review 事前点検を先にゲート化し、platform 分割と items-only submission を活用する。
  - Source: Apple Developer App Review Guidelines, https://developer.apple.com/app-store/review/guidelines/
  - Quote: "Test your app for crashes and bugs"
  - Quote: "Ensure that all app information and metadata is complete and accurate"
  - Quote: "Update your contact information in case App Review needs to reach you"
  - Quote: "Provide App Review with full access to your app."
  - Source: App Store Connect Help, https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/overview-of-submitting-for-review/
  - Quote: "App versions for each platform are submitted separately."
  - Quote: "A platform can have a maximum of two submissions under review at a time: one that includes an app version and one that includes items... without an app version."
- OpenClaw のスキルは単一用途に保ち、補助スキル候補は ClawHub で優先的に探す。
  - Source: OpenClaw Skills Guide, https://openclaw-ai.online/skills/
  - Quote: "Keep each skill focused on one job"

### 2.9 2026-05-18 の追加BP
- x_search が 403 でクレジット不足/上限到達を返したら、同一クエリの再試行をせず、公式ドキュメントと ClawHub の結果で代替する。
  - Source: x_search tool error, 2026-05-18
  - Quote: "Your team 8ca26a44-1fe7-4588-921b-abd9550c8dcc has either used all available credits or reached its monthly spending limit."

### 2.10 2026-05-19 の追加BP
- App Store 提出の中核は app-store-connect を優先し、送信・状態確認・メタデータ操作を CLI 基準に寄せる。
  - Source: ClawHub search, local run 2026-05-19
  - Quote: "app-store-connect  App Store Connect  (3.059)"
  - Source: App Store Connect Help, https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/overview-of-submitting-for-review/
  - Quote: "Learn how to submit using the App Store Connect API."
- ビルド可視化と修正補助には xcode-build-analyzer を優先し、Xcode 周りの詰まりを早く潰す。
  - Source: ClawHub search, local run 2026-05-19
  - Quote: "xcode-build-analyzer  Xcode Build Analyzer  (3.014)"
- App Review 情報は最新承認版に集約し、レビューに必要な文脈を最初から入れる。
  - Source: App Store Connect Help, https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/overview-of-submitting-for-review/
  - Quote: "Use the App Review information section on the latest approved app version for that platform to provide additional information or context that will help App Review during the review process."
  - Source: Apple Developer App Review Guidelines, https://developer.apple.com/app-store/review/guidelines/
  - Quote: "Include detailed explanations of non-obvious features and in-app purchases in the App Review notes, including supporting documentation where appropriate"

## 2026-05-20 の追加BP
- App Review の詰まりは、クラッシュ、バグ、メタデータ不備、連絡先不備、アクセス不足、バックエンド未稼働を先に潰して減らす。
  - Source: Apple Developer App Review Guidelines, https://developer.apple.com/app-store/review/guidelines/
  - Quote: "Test your app for crashes and bugs"
  - Quote: "Ensure that all app information and metadata is complete and accurate"
  - Quote: "Update your contact information in case App Review needs to reach you"
  - Quote: "Provide App Review with full access to your app."
  - Source: Apple Developer App Review Guidelines, https://developer.apple.com/app-store/review/guidelines/
  - Quote: "Enable backend services so that they’re live and accessible during review"
- 提出の文脈は最新承認版の App Review information に集約し、platform ごとに分けて submit する。
  - Source: App Store Connect Help, https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/overview-of-submitting-for-review/
  - Quote: "Use the App Review information section on the latest approved app version for that platform to provide additional information or context that will help App Review during the review process."
  - Quote: "App versions for each platform are submitted separately."
- 送信と状態確認は app-store-connect を基点にし、ビルド詰まりの可視化には xcode-build-analyzer を優先する。
  - Source: ClawHub search, local run 2026-05-19
  - Quote: "app-store-connect  App Store Connect  (3.059)"
  - Source: ClawHub search, local run 2026-05-19
  - Quote: "xcode-build-analyzer  Xcode Build Analyzer  (3.014)"
  - Source: App Store Connect Help, https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/overview-of-submitting-for-review/
  - Quote: "Learn how to submit using the App Store Connect API."
- 実行時の改善順は App Review の事前点検, App Review information 集約, platform 分割, app-store-connect 基点, xcode-build-analyzer の順に固定する.
  - Source: Apple Developer App Review Guidelines, https://developer.apple.com/app-store/review/guidelines/
  - Quote: "Test your app for crashes and bugs"
  - Quote: "Ensure that all app information and metadata is complete and accurate"
  - Quote: "Update your contact information in case App Review needs to reach you"
  - Quote: "Provide App Review with full access to your app."
  - Source: App Store Connect Help, https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/overview-of-submitting-for-review/
  - Quote: "Use the App Review information section on the latest approved app version for that platform to provide additional information or context that will help App Review during the review process."
  - Quote: "App versions for each platform are submitted separately."
- App Review notes should explicitly include demo access, backend/live-service status, and a plain list of external services used.
  - Source: Apple Developer App Review Guidelines, https://developer.apple.com/app-store/review/guidelines/
  - Quote: "Provide App Review with full access to your app. If your app includes account-based features, provide either an active demo account or fully-featured demo mode, plus any other hardware or resources that might be needed to review your app (e.g. login credentials or a sample QR code)"
  - Quote: "Enable backend services so that they’re live and accessible during review"
  - Quote: "Include detailed explanations of non-obvious features and in-app purchases in the App Review notes, including supporting documentation where appropriate"

## 2026-05-23 追記
- App Review 情報は送信前の必須 SSOT として扱い、レビュー文脈は latest approved app version の App Review information に集約する。
  - Source: App Store Connect Help, https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/overview-of-submitting-for-review/
  - Quote: "Use the App Review information section on the latest approved app version for that platform to provide additional information or context that will help App Review during the review process."
- 提出は platform ごとに分け、App Store Connect API を基点にして、必要に応じて ASC CLI と xcode-build-analyzer を組み合わせる。
  - Source: App Store Connect Help, https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/overview-of-submitting-for-review/
  - Quote: "App versions for each platform are submitted separately."
  - Source: App Store Connect Help, https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/overview-of-submitting-for-review/
  - Quote: "Learn how to submit using the App Store Connect API."
  - Source: ClawHub search, local run 2026-05-23
  - Quote: "app-store-connect  App Store Connect  (3.061)"
  - Source: ClawHub search, local run 2026-05-23
  - Quote: "xcode-build-analyzer  Xcode Build Analyzer  (3.018)"

### 3. 結果を保存

見つけたBPを以下に保存:
```
/Users/anicca/.openclaw/workspace/factory-evolution/efficiency-bp-YYYY-MM-DD.md
```

### 4. スキル編集

見つけたBPに基づき、該当スキルを差分編集:
- パス: `/Users/anicca/anicca-project/.claude/skills/mobileapp-builder/`
- または `/Users/anicca/.openclaw/skills/mobileapp-factory/SKILL.md`
- **編集先は実在パスだけを使う。`/Users/anicca/.openclaw/workspace/skills/mobileapp-factory/SKILL.md` は存在しない。**
- **全編集にソース+URL+原文引用を付ける**
- **edit は必ず事前に対象ファイルを read して、最小ブロックで差分更新する。巨大な一括 patch は使わない。**
- **apply_patch は使わない。1ファイルだけを直すなら `edit`、大きく変えるなら `write` で全文を書き換える。**
- App Store 提出系のスキルでは、App Review Information の未記入を必ず失敗条件として扱う
- 公式一次情報は Apple Developer の App Review Guidelines と App Review ページを優先する
- 送信時は App Store Connect の最新承認版にレビュー文脈を集約し、platform ごとに分けて扱う

### 5. git commit

```bash
cd /Users/anicca/anicca-project && git add -A && git commit -m "factory-bp-efficiency: [日付] [改善内容の要約]"
```

### 6. Slack報告

cron 実行では Slack 送信をしない。結果は `workspace/factory-evolution/efficiency-bp-YYYY-MM-DD.md` に保存して終了する。
手動実行で必要な場合のみ、別途人手で Slack に転記する。

# FIX by skill-fixer 2026-04-27:
# 原因: cron 実行で Slack 送信を試すと送信失敗や実行中断の原因になるため。
# 修正: cron では Slack 送信を完全に外し、ファイル保存のみを正にした。

# FIX by skill-fixer 2026-04-28:
# 原因: cron が `Apply Patch failed` で終わっていた。
# 修正: 変更適用は `edit` か `write` に統一し、`apply_patch` を禁止した。
