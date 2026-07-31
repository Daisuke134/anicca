---
name: mobileapp-builder
description: Build and ship iOS apps to the App Store autonomously. Use when triggered by factory cron or told to "build an app", "run factory", "ship an app". Executes 9 user stories (US-001 to US-009) via ralph.sh loop, each as one Claude Code session.
allowed-tools: [Read, Write, Bash, Edit, Glob, Grep]
metadata:
  author: Anicca
  version: 3.0.0
  workflow-source: https://github.com/rshankras/claude-code-apple-skills/blob/main/skills/product/WORKFLOW.md
  loop-source: https://github.com/snarktank/ralph
---

# mobileapp-builder

Build and ship one iOS app per day to the App Store. 詳細は各 references/us-XXX.md を参照。

## Architecture

Source: rshankras ProductAgent WORKFLOW.md + snarktank/ralph

- **ralph.sh** loops through 9 US (user stories) in prd.json
- **1 US = 1 CC session** (one context window)
- Each US reads its `references/us-00X-*.md` for detailed instructions
- Each US reads relevant rshankras skills from `.claude/skills/`
- **validate.sh** runs after each iteration as external quality gate

## 9 User Stories (ralph dependency order)

| US | Phase | What | Skills | Reference |
|----|-------|------|--------|-----------|
| US-001 | Idea Discovery | Trend research + idea selection | `idea-generator` | `references/us-001-trend.md` |
| US-002 | Product Planning | Problem validation + MVP + positioning | `prd-generator` | (output: product-plan.md) |
| US-003 | Market Research | Competitive analysis + TAM/SAM/SOM | `competitive-analysis` | `references/us-003-research.md` |
| US-004a | Core Spec | PRD, ARCH, IMPL, TEST, RELEASE 生成 | `implementation-spec` | `references/us-004-specs.md` |
| US-004b | UX Spec | UX_SPEC, DESIGN_SYSTEM 生成 | `ios-ux-design` | `references/us-004-specs.md` |
| US-004-R | Spec Review | 全7ドキュメントレビュー → CRITICAL=0 | code-quality-reviewer (subagent) | `references/us-004-specs.md` |
| US-005a | Infrastructure | Privacy Policy + ASC app creation | `asc-cli-usage` | `references/us-005a-infra.md` |
| US-005b | Monetization | IAP + pricing + RC project + offerings | `asc-ppp-pricing` | `references/us-005b-monetization.md` |
| US-006a | TDD Data Layer | xcconfig, Protocol DI, Models, Services | `tdd-feature` | `references/us-006-implement.md` |
| US-006b | TDD Onboarding + Monetization | MVVM分割, Onboarding, PaywallView | `tdd-feature` | `references/us-006-implement.md` |
| US-006c | TDD Core Screens | Timer, Settings, ProgressDashboard | `tdd-feature` | `references/us-006-implement.md` |
| US-006d | TDD Polish | DESIGN_SYSTEM tokens, a11y IDs, Localization | `tdd-feature` | `references/us-006-implement.md` |
| US-006-R | Code Review | 006a-d 全体レビュー → CRITICAL=0 | code-quality-reviewer (subagent) | `references/us-006-implement.md` |
| US-007 | Testing | Maestro E2E (6 flows + Fix Loop) | `maestro-ui-testing` (RC Test Store + Fix Loop) | `references/us-007-testing.md` |
| US-008a | Screenshots | Capture + upload + review screenshots (en-US + ja) | `asc-shots-pipeline` | `references/us-008-release.md` Steps 1a-1h |
| US-008b | Metadata | ASC metadata sync (en-US + ja) | `asc-metadata-sync` | `references/us-008-release.md` Step 2 |
| US-008c | Build + Upload | IPA build + upload + version attach | `asc-xcode-build` | `references/us-008-release.md` Step 3 |
| US-008d | Compliance | Age rating + encryption + rights + availability + pricing + review details | `asc-release-flow` | `references/us-008-release.md` Steps 4-6 |
| US-008e | Preflight + TF | release-review + validate + TestFlight + Slack | `release-review` | `references/us-008-release.md` Steps 7-10 |
| US-009 | Submit | App Privacy (auto: asc web privacy) + submit → WAITING_FOR_REVIEW | `asc-submission-health` | `references/us-009-submit.md` |


## Slack Interaction

WAITING_FOR_HUMAN の詳細は `references/us-005a-infra.md`（2FA）と `references/us-005b-monetization.md`（RC setup）を参照。


## Claude Code Mental Model (NEW 2026-03-24, UPDATED 2026-03-29)

**Source 1**: Reddit r/ClaudeAI — Best practices after shipping iOS apps  
**URL**: https://www.reddit.com/r/ClaudeAI/comments/1ridakj/best_practices_ive_learned_after_shipping/  
**Core Quote**: "Claude Code is a brilliant junior developer who can write code faster than anyone I've ever seen. But like any junior dev, it needs guidance on architecture decisions, security practices, and long-term maintainability. **The senior engineer is still you.**"

**Source 2**: GitHub Gist — iOS Project Claude Code Setup  
**URL**: https://gist.github.com/joelklabo/6df9fa603bec3478dec7efc17ea44596  
**Core Quote**: "Never use raw xcodebuild commands. Always use the appropriate MCP tool: Building: `mcp__xcodebuildmcp__build_sim_name_proj`, Testing: `mcp__xcodebuildmcp__test_sim_name_proj`"

**Source 3**: Medium — Claude Code Plugins for iOS Teams  
**URL**: https://medium.com/@wesleymatlock/claude-code-plugins-for-ios-teams-automation-agents-and-guardrails-221a68eb57d5  
**Core Quote**: "If you wouldn't trust a junior engineer to do it unsupervised, don't hand it to an agent yet." / "Plugins are policy. Skills are tools. Agents are specialized subagents."

### What This Means for Factory

| Claude Code Does Well | Needs Human/Senior Guidance |
|----------------------|----------------------------|
| Fast code generation | Architecture decisions |
| Feature implementation | Security practices |
| Boilerplate reduction | Long-term maintainability |
| Happy path scenarios | Edge cases (network failures, unexpected API responses) |

### Build Failure Protocol (NEW 2026-03-29)

**Source**: Reddit r/ClaudeAI iOS best practices  
**Core Quote**: "The most dangerous pattern was what happens when a build or test *fails*. Claude's default behavior is to **make a shallow fix and retry immediately**."

**Rule**: When build/test fails, do NOT let CC retry with shallow fix.

1. **Capture Failure Log**: Save full error log to `logs/build-error-{timestamp}.log`
2. **Analyze Root Cause**: Read error log, identify root cause (not symptom)
3. **Document Decision**: Write analysis to `logs/build-fix-{timestamp}.md` with:
   - Error symptom
   - Root cause
   - Proposed fix
   - Risk assessment
4. **Fix Once, Properly**: Implement fix with full context (not quick patch)
5. **Verify Fix**: Run build again, confirm success
6. **Update SKILL.md if Pattern**: If error pattern repeats across apps, add to this SKILL.md

**Prohibited**: Immediate retry without root cause analysis. Shallow fixes that hide deeper issues.

### Security & Quality Checklist (Every App)

**Source**: Reddit r/ClaudeAI iOS best practices  
**Core principle**: "AI doesn't automatically enforce good practices. It gives you what you ask for."

| Category | Requirement | Verification |
|----------|-------------|--------------|
| **Secrets** | Never hardcode. Different tokens per environment (dev/staging/prod). Use .env + Keychain only | grep -r "api_key\|secret" --exclude=.env. iOS: KeychainAccess wrapper. Backend: dotenv |
| **Observability** | Crash reporting from day one (not after first angry review) | Check Sentry/Crashlytics init in AppDelegate |
| **Logging** | Persistent logs (not just console) | Check Logger usage in critical paths |
| **Health Check** | /health endpoint for backend | curl {API_URL}/health |
| **Input Validation** | Server-side validation. Never trust client data | Check API routes for validation |
| **Rate Limiting** | On auth and write operations | Check middleware in auth routes |
| **Staging** | Real staging environment (mirrors production) | .env has STAGING vars |
| **CORS** | Set to specific origins (not *) | Check backend CORS config |
| **CI/CD** | Automated testing + deployment pipeline | Check Fastfile existence |
| **Backups** | Test restore at least once | Document restore procedure |
| **Time** | Store in UTC, convert on display. Never mix UTC/local/JS defaults | grep "Date()" and check timezone handling. All DB timestamps = UTC. All API responses = ISO 8601 with Z suffix |

### 2026 App Store Privacy Requirements (AI Apps)

**Source**: AppLaunchpad App Store Review Guidelines 2026  
**URL**: https://theapplaunchpad.com/blog/app-store-review-guidelines  
**Core Quote**: "Privacy and data transparency are major priorities in 2026. Apps must clearly disclose what data they collect, how it is used, and obtain consent before sharing it with third parties, **especially AI services**."

#### If Your App Uses AI

| Requirement | Where to Implement |
|------------|-------------------|
| **What the AI does** | App description + in-app explainer |
| **What data it uses** | PrivacyInfo.xcprivacy + App Privacy labels |
| **How users can control/limit it** | Settings screen with AI toggle |
| **AI provider disclosure** | Privacy Policy + in-app notice |
| **Clear user consent** | Explicit opt-in before first AI call |

**Rejection risk**: Apps that mislead users about AI capabilities or hide automated processes are more likely to be rejected.


## CRITICAL RULES

| # | Rule |
|---|------|
| 1 | **提出前に全サブスクが READY_TO_SUBMIT**。MISSING_METADATA → Guideline 2.1 拒否 |
| 2 | **IAP pricing は全175カ国**。高価格サブスク（$9.99+/月）は低～中価格より trial conversion rate が高い。Source: https://www.revenuecat.com/blog/growth/subscription-app-trends-benchmarks-2026/ — 「Higher priced subscriptions have higher trial conversion rates than mid and lower priced」。デフォルト価格は $9.99/月を推奨 |
| 3 | **Superwall 禁止。RevenueCat SDK のみ** |
| 4 | **ビルドは `fastlane build` / `fastlane test`。xcodebuild 直接禁止。提出後は ASC CLI のみ** |
| 5 | **validate.sh が STOP ゲート**。FAIL なら次に進まない |
| 6 | **availability set は pricing の前** |
| 7 | **Privacy Policy URL は en-US AND ja 両方** |
| 8 | **RC Offerings は TestFlight 前に設定** |
| 9 | **locale は `ja`（`ja-JP` 無効）** |
| 10 | **IAP key は同一アカウントで使い回し** |
| 11 | **Paywall コピーは実機能確認してから書く** |
| 12 | **アナリティクス SDK 禁止**。Mixpanel/Firebase Analytics 等は入れない（CLAUDE.md Rule 17 参照） |
| 13 | **(欠番 — 旧 Mixpanel 連携ルール削除済)** |
| 14 | **スクショは AXe 本物（`brew install cameroncooke/axe/axe`）。axe-shim 禁止** |
| 15 | **RC API キーは Info.plist から。環境変数禁止** |
| 16 | **screenshot-creator スキル禁止。Koubou（`asc screenshots frame`）のみ** |
| 17 | **自前 SwiftUI PaywallView 必須。RevenueCatUI.PaywallView 禁止** |
| 18 | **ATT 禁止** |
| 19 | **オンボーディング最終画面はソフトペイウォール**。ただし、キャッシュフロー優先ならハードペイウォールを検討する。ハードペイウォール（フリーミアムなし）は Day-35 trial-to-paid conversion が 10.7% で、フリーミアムの 2.1% より高い。Source: https://www.revenuecat.com/blog/growth/subscription-app-trends-benchmarks-2026/ — 「hard paywalls have a median Day-35 trial-to-paid conversion rate of **10.7%**, compared to just **2.1%** for freemium apps」。
| 19-BP1 | **動的ペイウォール（セグメント化・期間限定割引）は静的より 35% 高コンバージョン**。RevenueCat Experiments / Adapty を使用。Source: https://adapty.io/blog/how-to-design-ios-paywall/ — 「**Dynamic paywalls with segmented or time-based discounts deliver approximately 35% higher conversion rates than static alternatives**」 |
| 19-BP10A | **Paywall 前に 30-second win を必ず入れる**。核心価値を 30 秒以内に体験させてから課金導線へ進める。Source: https://x.com/i/status/1895820573185622512 — 「Deliver a \"30-second win\" upfront」 |
| 19-BP11A | **onboarding は paywall で終わらない**。初回購入後も first win まで案内を続ける。Source: https://x.com/i/status/2044806271040151936 — 「onboarding doesn't end at paywall—guide to first win」 |
| 19-BP2 | **ペイウォール閉じた後の 24h 限定オファー（ポストクローズオファー）は ARPU 10-15% 増**。非コンバータにのみ表示。Source: https://adapty.io/blog/high-performing-paywall-2026/ — 「A 24-hour welcome offer, targeted only at non-converters, captures price-sensitive users... 10–15% ARPU」 |
| 19-BP3 | **ローカライゼーションテストは LTV 改善で最高勝率 62.3%**。英語+日本語は最低要件。Source: https://adapty.io/blog/high-performing-paywall-2026/ — 「Localization tests: 62.3% win rate on LTV — the highest of any category」 |
| 19-BP4 | **無料トライアルは複数箇所で言及**（ヘッドライン+CTA+補助テキスト）。単一 CTA では不十分。Source: https://www.revenuecat.com/blog/growth/paywall-conversion-boosters/ — 「the trial offer should be a central, recurring element throughout your paywall」 |
| 19-BP5 | **割引バッジは目立つように表示**（"Save 40%" 等）。小さく埋もれた表示はコンバージョンを損なう。Source: https://www.revenuecat.com/blog/growth/paywall-conversion-boosters/ — 「displaying the discount percentage prominently... significantly outperforms designs that bury this information」 |
| 19-BP6 | **アニメーション要素で 12-18% CVR 向上**。Subtle button pulsing、entrance effects、CTA highlighting で conversion 改善。動きに注目が集まり pattern interrupt 効果。Source: https://www.revenuecat.com/blog/growth/paywall-conversion-boosters/ — 「Animated elements on paywalls consistently improve conversion rates. When implemented correctly, animated elements typically increase conversion rates by 12-18% compared to static alternatives.」 |
| 19-BP7 | **価格アンカリング: 日割り換算表示必須**。"Just 33¢ per day" または "Less than a coffee per week" で高額感を軽減。毎月の絶対額より小さい単位で比較。Source: https://www.revenuecat.com/blog/growth/paywall-conversion-boosters/ — 「Effective price anchoring techniques include: Breaking down the cost to smaller, more digestible amounts ("Just 33¢ per day"), Comparing subscription cost to common everyday purchases ("Less than a coffee per week").」 |
| 19-BP8 | **CTA コピーテストで 10-20% CVR 改善**。"Subscribe" → "Start My Free Trial" / "Unlock Premium" / "Get Better Sleep Today" へ変更。Benefit-driven CTA が action-oriented。定期的にバリエーションテスト。Source: https://apphud.com/blog/design-high-converting-subscription-app-paywalls — 「Test variations of CTA copy regularly - even small wording tweaks can lead to 10–20% conversion lifts.」 |
| 19-BP9 | **Paywall 階層: 価値 → 機能 → 価格 → CTA**。ヘッドライン（value proposition）→ feature highlights → pricing → CTA の順。whitespace で clutter 回避。3秒ルール（3秒で理解できる）。Source: https://apphud.com/blog/design-high-converting-subscription-app-paywalls — 「Design and layout: Start with the headline (value), followed by a few visual feature highlights, then pricing, and finally a strong CTA. Use whitespace to prevent clutter.」 |
| 19-BP10 | **Paywall 前に 30-second win を必ず入れる**。核心価値を 30 秒以内に体験させてから課金導線へ進める。Source: https://x.com/i/status/1895820573185622512 — 「Deliver a \"30-second win\" upfront」 |
| 19-BP11 | **onboarding は paywall で終わらない**。初回購入後も first win まで案内を続ける。Source: https://x.com/i/status/2044806271040151936 — 「onboarding doesn't end at paywall—guide to first win」 |
| 20 | **validate.sh / ralph.sh を CC が編集・削除禁止（外部品質ゲート）** |
| 40 | **テンプレート編集禁止**: `.claude/skills/mobileapp-builder/` 内の prd.json, SKILL.md, CLAUDE.md は CC 編集禁止。`$APP_DIR/prd.json` のみ編集可 |
| 21 | **1アプリ = 1 RC プロジェクト** Source: https://community.revenuecat.com/general-questions-7/project-vs-app-1899 |
| 22 | **AXe 座標タップでタブ切り替え**。Tab Bar の accessibility label がない場合 |
| 23 | **Maestro E2E テスト必須。サブスク購入フローを含む** |
| 24 | **release-review 5 checklists 必須（US-008e）** |
| 25 | **App Privacy は asc web privacy apply + publish で自動（US-009）** |
| 26 | **demoAccountRequired = false を明示指定**。デフォルト true でデモアカ未入力だと提出ブロック |
| 27 | **PrivacyInfo.xcprivacy 必須**。Source: Apple WWDC23 |
| 28 | **ITSAppUsesNonExemptEncryption = NO を Info.plist に追加** |
| 29 | **KEYCHAIN_PASSWORD は env var から。ハードコード禁止**。Source: 12-Factor App |
| 30 | **availability set BEFORE pricing**。逆だと Apple 500 エラー |
| 31 | **asc validate Errors=0 必須（submit 前 STOP GATE）** |
| 32 | **提出コマンド: submissions-create + items-add + submissions-submit** |
| 33 | **Fastfile destination は UDID**。名前だと not found エラー |
| 34 | **RC delegate 名前衝突回避**。`RCPurchasesDelegate: NSObject, PurchasesDelegate` |
| 35 | **iOS 15: `Locale.current.language.languageCode` 禁止**。`Locale.current.languageCode` を使う |
| 36 | **iOS 15: `scrollContentBackground` 禁止**。ZStack + Color で代替 |
| 37 | **アイコンはビルド前に配置**。後から変更は version bump + 再ビルド |
| 38 | **SPM に RevenueCatUI を追加しない。RevenueCat のみ** |
| 39 | **毎 iteration = 新 CC プロセス（フレッシュ context）**。前回の学びは progress.txt のみ |
| 40 | **.pbxproj 編集禁止（CRITICAL）**。AI が .pbxproj を編集すると 90% のケースで破壊する。ファイル作成後、フォルダベース管理を使用。Source: https://www.linkedin.com/posts/kris-puckett-0109041b_if-youre-building-an-ios-app-with-claude-activity-7393778932807852032-Pkuj — 「Never let AI modify .pbxproj files. Create files with Claude Code, add them to Xcode manually.」 |
| 41 | **XcodeBuildMCP 優先使用**。生 xcodebuild コマンドの代わりに MCP ツール（mcp__xcodebuildmcp__build_sim_name_proj 等）を使用すると、ビルドエラーの自己修正が可能。Source: https://gist.github.com/joelklabo/6df9fa603bec3478dec7efc17ea44596 — 「Always Use MCP Tools. Never use raw xcodebuild commands.」 |
| 42 | **フォルダベース管理推奨**。.pbxproj 編集を避けるため、指定フォルダにソースを配置すれば Xcode が自動参照・ビルドに含める仕組みを活用。Source: https://dev.classmethod.jp/en/articles/claude-code-ios-app-development-ai-only/ — 「In folder format, simply placing source code in designated locations allows Xcode to automatically reference and include it in the build」 |
| 43 | **進捗記録の徹底**。全タスク完了時に進捗を明示的に記録し、次回セッションで 5 分でキャッチアップできるようにする。30 分スロットでも作業継続可能に。Source: https://www.zdnet.com/article/claude-code-vibe-coding-iphone-app-lessons/ — 「I ask Claude to come up to speed, which takes about five minutes. I can read our updated notes, give it a prompt, tell it to record its progress, and move on.」 |
| 44 | **ビルドフィードバックループの短縮**。ビルド結果・テスト結果を即座に CC にフィードバックする仕組みを作り、改善サイクルを高速化。Source: https://plankenau.com/blog/post/claude-coding-an-ios-app — 「focus on closing the feedback loop, i.e., claude code does best when it can process the result of its changes in the most direct way possible.」 |
| 45 | **2026プライバシーガイドライン必須**。AIサービスとのデータ共有は明示的同意。Source: https://theapplaunchpad.com/blog/app-store-review-guidelines — 「Apps must clearly disclose what data they collect, how it is used, and obtain consent before sharing it with third parties, especially AI services.」 |
| 46 | **April 2026 SDK deadline**。2026年4月までにXcode 26 SDKでビルドしたバージョンを提出。Source: https://medium.com/@thakurneeshu280/apple-app-store-submission-changes-april-2026-5fa8bc265bbe — 「Submit before April 2026 deadline」 |
| 41 | **IAP は2-3プラン: monthly + annual OR weekly + monthly + annual**。Source: Adapty iOS Paywall Design Guide 2026 (https://adapty.io/blog/how-to-design-ios-paywall/) — 「2 products vs 1 product +61%; 3 products vs 2 products +44%」。RevenueCat State of Subscription Apps 2025 — "Weekly plans capturing 47% of total revenue" |
| 42 | **US-005a 開始時に iris セッション確認必須**。`asc web auth status` で authenticated=false なら即 WAITING_FOR_HUMAN。retry 禁止。Source: Internal — iris session expiry blocked 5+ factory runs |
| 43 | **XcodeBuildMCP使用（raw xcodebuild禁止）**。Never use raw xcodebuild commands. Always use MCP tool: `mcp__xcodebuildmcp__build_sim_name_proj`, `mcp__xcodebuildmcp__test_sim_name_proj`. Source: https://gist.github.com/joelklabo/6df9fa603bec3478dec7efc17ea44596 |
| 44 | **iOS Simulator Skill（自動検出・自動起動）**。シミュレータ起動・操作はios-simulator-skillに任せる。手動でsimctl起動しない。Claude Code automatically detects when to use this skill. Source: https://github.com/conorluddy/ios-simulator-skill |
| 45 | **フィードバックループを閉じる**。ビルド後は必ずシミュレータで起動し、動作確認を実施。エラーログをClaude Codeが直接読めるようにする。"Focus on closing the feedback loop, i.e., claude code does best when it can process the result of its changes in the most direct way possible." Source: https://plankenau.com/blog/post/claude-coding-an-ios-app |
| 45-NEW | **Service Layer for API Calls（NEW 2026-03-29）**。全外部API呼び出しは独立したサービス層でラップ。rate limiting、caching、provider swapを考慮した設計。"When you're calling third-party APIs, take the extra time to create a clean service layer. Your future self will thank you when you need to add caching or swap providers." Source: https://www.reddit.com/r/ClaudeAI/comments/1ridakj/best_practices_ive_learned_after_shipping/ |
| 45-NEW2 | **Observability from Day 1（NEW 2026-03-29）**。Crash reporting（Sentry/Crashlytics）をプロジェクト初期から組み込む。"Crash reporting from day one, not after the first angry user review. Actual logging that persists somewhere, not just my terminal history." Source: https://www.reddit.com/r/ClaudeAI/comments/1ridakj/best_practices_ive_learned_after_shipping/ |
| 46 | **.pbxprojファイルはClaude Codeに触らせない（CRITICAL）**。新規ファイル作成はClaude Codeで、Xcodeプロジェクトへの追加は手動で行う。.pbxprojの直接編集を絶対禁止。"Never let AI modify .pbxproj files. Create files with Claude Code, add them to Xcode manually." Source: https://www.linkedin.com/posts/kris-puckett-0109041b_if-youre-building-an-ios-app-with-claude-activity-7393778932807852032-Pkuj |
| 47 | **iOS 26対応 — 新age rating system**。iOS 26以降のage ratingを正しく設定。古いrating keyは使わない。"Ratings for all apps and games on the App Store have been automatically updated to align with our new age rating system" Source: https://developer.apple.com/news/upcoming-requirements/ |
| 48 | **xcodebuild -destination で複数デバイステスト**。xcodebuild test実行時に `-destination 'platform=iOS Simulator,name=iPhone 16 Pro'` で明示的にデバイス指定。Source: https://developer.apple.com/library/archive/documentation/DeveloperTools/Conceptual/testing_with_xcode/chapters/08-automation.html |
| 49 | **Kodeco iOS Build Automation Guide準拠**。ビルド→アーカイブ→エクスポート→アップロードの全自動化パイプラインをKodecoガイドに従って実装。Source: https://www.kodeco.com/books/ios-app-distribution-best-practices/v1.0/chapters/12-build-automation |
| 50 | **必ず plan mode で開始**。全タスク開始時に plan mode でインタビューし、段階的計画を立てる。"always start with plan mode. ask Claude to interview you; ask the user a question" Source: https://github.com/shanraisshan/claude-code-best-practice |
| 51 | **変更後は必ずテスト**。Clean build folder (Cmd+Shift+K) → run → console 確認。"Test after every change!! Catch issues before they compound." Source: https://www.linkedin.com/posts/kris-puckett-0109041b_if-youre-building-an-ios-app-with-claude-activity-7393778932807852032-Pkuj |
| 52 | **1コンポーネント限定**。1セッションで1コンポーネントのみ実装。"Don't ask to 'refactor the whole app' Smaller scope = better results." Source: https://www.linkedin.com/posts/kris-puckett-0109041b_if-youre-building-an-ios-app-with-claude-activity-7393778932807852032-Pkuj |
| 53 | **iOS gotcha を即記録**。iOS 26 API問題等は .claude/rules/platform-gotchas.md に即追記。"NO .background() before .glassEffect() saved me from repeating that mistake 50+ times." Source: https://www.linkedin.com/posts/kris-puckett-0109041b_if-youre-building-an-ios-app-with-claude-activity-7393778932807852032-Pkuj |
| 54 | **CLAUDE.md は200行以内**。超える場合は .claude/rules/ に分割。"CLAUDE.md should target under 200 lines per file. 60 lines in humanlayer" Source: https://github.com/shanraisshan/claude-code-best-practice |
| 55 | **/compact at 50% context**。context 50%到達で手動 /compact 実行。"avoid agent dumb zone, do manual /compact at max 50%." Source: https://github.com/shanraisshan/claude-code-best-practice |
| 56 | **Cross-model QA**。実装完了後 Codex で plan/code をレビュー。"use a cross-model for QA — e.g. Codex for plan and implementation review" Source: https://github.com/shanraisshan/claude-code-best-practice |
| 57 | **Feature flags for experimental**。新機能は feature flag で on/off。"Toggle new features on/off without rebuilding. Makes rolling back instant." Source: https://www.linkedin.com/posts/kris-puckett-0109041b_if-youre-building-an-ios-app-with-claude-activity-7393778932807852032-Pkuj |
| 58 | **Debug logging を必ず追加**。複雑なフローには Logger 追加。"Ask Claude Code to add Logger statements for complex flows." Source: https://www.linkedin.com/posts/kris-puckett-0109041b_if-youre-building-an-ios-app-with-claude-activity-7393778932807852032-Pkuj |
| 59 | **Paywall に微細アニメーション**。Button pulse、entrance effects、motion で conversion +12~18%。静止画面の 2.9 倍。Source: https://adapty.io/blog/how-to-design-ios-paywall/ — 「Animated paywalls produce 2.9× higher conversion rates than static designs」 |
| 60 | **Paywall で user name personalization**。"[Name], unlock your premium features" で conversion +17%。Source: https://adapty.io/blog/how-to-design-ios-paywall/ — 「Adding the user's name to paywall copy (increases conversions by 17%)」 |
| 61 | **Discount percentage を prominent 表示**。"Save 50%" badge + strikethrough price で conversion +20~30%。Source: https://www.revenuecat.com/blog/growth/paywall-conversion-boosters/ |
| 62 | **Free trial を複数箇所で強調**。Headline、CTA、pricing に繰り返し記載で conversion +15~25%。Source: https://adapty.io/blog/how-to-design-ios-paywall/ — 「Trial mentioned multiple times: +15% to +25%」 |
| 63 | **Benefit-driven CTA**。"Subscribe" → "{Start\|Get\|Unlock} {my\|your} {plan\|access}" で conversion 向上。Source: https://blog.funnelfox.com/effective-paywall-screen-designs-mobile-apps/ — 「Replace generic CTAs like "Subscribe" with benefit-driven ones」 |
| 64 | **Social proof を pricing 近くに配置**。Reviews、testimonials、logos を paywall に追加で trust 向上。Source: https://blog.funnelfox.com/effective-paywall-screen-designs-mobile-apps/ |
| 65 | **Price anchoring copy**。"Just 33¢ per day" または "Less than a coffee per week" で高額感を軽減。Source: https://www.revenuecat.com/blog/growth/paywall-conversion-boosters/ |
| 66 | **docs/ で禁止キーワードは代替表現**。Grep AC が FAIL する。RevenueCatUI → "RC-UI-package", Mixpanel → "tracking-SDK", FoundationModels → "Apple-FM-API"。Source: Internal — 5+ apps (20260307-202456, 20260309-005930) |
| 67 | **Availability BEFORE Pricing (ASC API)**。`asc subscriptions availability set` を `asc subscriptions prices add` より前に実行。逆だと Apple API 500 エラー。Source: Internal — 4 apps (20260304-105016, 20260307-202456) |
| 68 | **ASC API Key: Developer role は app create 不可**。`asc apps create` は Apple ID + 2FA 必須。API Key は bundle-ids create のみ。"Admin" or "App Manager" role が必要。Source: Internal — 3 apps (20260301-app, 20260304-070221) |
| 69 | **RevenueCat Package は mock 不可**。Unit test では guard path（empty packages）+ restore path をテスト。購入フローは E2E で検証。Source: Internal — 3 apps (20260307-002214, 20260308-070022) |
| 70 | **iTunes API exact match は jq フィルタ必須**。`term=` は partial match。`jq 'select(.trackName | ascii_downcase == "exact_name")'` で完全一致確認。Source: Internal — 4 apps (20260304-070221, 20260308-070022) |
| 71 | **iOS 26 deprecated API 事前チェック必須**。ビルド前に deprecated API スキャンを実行。iOS 26 SDK でビルドすると 10 年以上前から非推奨のキーがエラーになる。Source: https://developer.apple.com/documentation/ios-ipados-release-notes/ios-ipados-26-release-notes — 「These keys have been deprecated for more than a decade. Affected apps rebuilt with the iOS or macOS 26 SDK will get errors.」 |
| 72 | **Xcode ビルド並列化のためにターゲット依存を最小化**。大きなターゲットを分割し、dependency list を簡素化して Xcode が並列ビルドできるようにする。Source: https://developer.apple.com/documentation/xcode/improving-the-speed-of-incremental-builds — 「simplify your target's dependency list, and break up monolithic targets so that Xcode can do more work in parallel」 |
| 73 | **1000行超の Swift ファイルは分割**。Xcode Build Timeline でボトルネックを特定し、大きなファイルをリファクタリング。コンパイル時間を短縮。Source: https://bitrise.io/blog/post/expert-tips-to-speed-up-your-ios-builds — 「Refactor or split large Swift files that dominate compile time」 |
| 74 | **fastlane 優先、xcodebuild 直接使用禁止（自動化）**。全ビルド自動化は fastlane または xcodebuild でスクリプト化。Source: https://www.reddit.com/r/Xcode/comments/1kceurw/script_automate_tasks_in_xcode/ — 「Try instead shell scripting and xcodebuild, or maybe look into fastlane which has scripts for all these kinds of steps, and more, ready to go」 |
| 71 | **iris session は ~7日で expire**。PREFLIGHT Check 6 で `asc web auth status` 確認必須。authenticated=false なら即 WAITING_FOR_HUMAN（2FA 必要）。Source: Internal — 4 apps (20260304-070221, 20260307-223953) |
| 72 | **Grep-based Gate check は context 確認**。"Don't use Mixpanel" も "Mixpanel" にマッチ。禁止記載時は代替表現を使う。Source: Internal — 3 apps (20260307-202456, 20260309-005930) |
| 73 | **Weekly subscription を primary option に**。Weekly = 55.5% of app revenue (2026)、install-to-trial 9.8% vs 1.8% annual。Weekly+trial が最高 LTV 成長率（636% vs annual 18.6%）。Source: https://adapty.io/blog/mobile-app-monetization-2026/ — 「Weekly subscriptions now generate 55.5% of all app revenue」 |
| 74 | **Paywall を onboarding 直後に配置**。89.4% の trial starts が Day 0。Day 1+ は single digits。Onboarding → Paywall が全体の trial acquisition strategy。Source: https://adapty.io/blog/mobile-app-monetization-2026/ — 「Your onboarding-to-paywall flow is essentially your entire trial acquisition strategy」 |
| 75 | **Locale tests を pricing tests より優先**。Translation/currency が最高 LTV uplift 62.3%。Price changes は 45.5%（最低）。Top 5 markets（日本、米国、英国、ドイツ、フランス）に localize。Source: https://adapty.io/blog/mobile-app-monetization-2026/ — 「Locale tests (translation and currency) deliver the highest LTV uplift at 62.3%」 |
| 76 | **A/B testing roadmap: Structure → Locale → Copy → Price**。Plan count/duration/trial が conversion +57~60% uplift。Price changes は最低（+28.3%）。Apps running 50+ experiments = 18.7x revenue vs 1 experiment。Source: https://adapty.io/blog/mobile-app-monetization-2026/ |
| 77 | **Consistent messaging: Ad → Onboarding → Paywall**。同じ価値提案、同じトーン、同じビジュアルで conversion 向上。Source: https://blog.funnelfox.com/effective-paywall-screen-designs-mobile-apps/ — 「Consistent messaging from ad to onboarding to paywall increases conversions」 |
| 78 | **Xcode 26 + iOS 26 SDK必須（2026年4月28日以降）**。Apps uploaded to App Store Connect must be built with Xcode 26 or later using an SDK for iOS 26, iPadOS 26, tvOS 26, visionOS 26. ビルド前にXcodeバージョンをチェック（26以上必須）。Source: https://medium.com/@thakurneeshu280/apple-app-store-submission-changes-april-2026-5fa8bc265bbe — 「The **April 2026** SDK requirements represent a significant but manageable update for Apple developers.」 |
| 79 | **Privacy透明性が2026年の最優先項目**。Apps must clearly disclose what data they collect, how it is used, and obtain consent before sharing it with third parties, especially AI services. PRD生成時に「どのデータを収集するか」を明確に定義し、Privacy Manifestを自動生成。Source: https://theapplaunchpad.com/blog/app-store-review-guidelines — 「**Privacy and data transparency are major priorities in 2026**」 |
| 80 | **Deprecated API警告を自動検出**。ビルド後にwarningログをスキャンし、"deprecated" キーワードを検出したら報告。iOS 26で多数のAPIが非推奨化されたため、リリース前に警告を検出しないと将来のSDKで動かなくなる。Source: https://medium.com/@saianbusekar/ios-26-migration-guide-update-your-legacy-apps-like-a-pro-f49b3a3aae9e — 「Check for deprecated APIs or features; Identify third-party dependencies that may need updates.」 |
| 81 | **Weekly + 3-day trial がデフォルト構成**。Weekly plan with 3-day free trial が1年LTV最高（annual比636%増）。LTV $7.40 → $54.50。Business/Productivity/Lifestyleではdirect buyers検討（trial CVRより高LTV）。Source: https://adapty.io/blog/high-performing-paywall-2026/ — 「The best setup by one-year LTV: Weekly plan with a 3-day free trial. This brings in 1.5x the average LTV of all other configurations... Adding a trial to a weekly plan takes LTV from $7.40 to $54.50 — a 636% increase.」 |
| 82 | **Onboarding完了率90-95%を目標**。90%未満ならフロー削減。Completion率1%向上 = Paywall到達率1%増 = 直接売上増。Source: https://adapty.io/blog/mobile-app-onboarding-vs-tutorials/ — 「Your app onboarding completion rate should hit 90-95%. That means 90-95% of users who start onboarding make it all the way to your first paywall... Improve your onboarding completion rate from 85% to 92%, and you just put 7% more users in front of your highest-converting paywall.」 |
| 83 | **Day 0に全集中**。90%のtrial starts、44.5%のpurchaseがDay 0。Day 1以降convert率single digits。Onboardingとpaywall一体設計。Source: https://adapty.io/blog/high-performing-paywall-2026/ — 「90% of trial starts happen on Day 0. 44.5% of all purchases happen on Day 0. Most users who don't convert during onboarding never come back to the paywall.」 |
| 84 | **Toggle trial UI を実装**。Paywall上でtrial on/off toggle配置。Upfront payment増 → ARPU 17-64%向上。Trial abuse削減。Source: https://www.revenuecat.com/blog/growth/paywall-redesigns-case-studies/ — 「Paywall 2 introduced a toggle for the free trial, allowing users to choose... The result was a 31% increase in install-to-trial conversions and a 64% uplift in revenue.」「resulted in a 17.02% boost in ARPU.」 |
| 85 | **Paywall直前5画面で価値提示**。Onboardingとpaywall一体設計。直前5画面が決める（paywallデザインではない）。Source: https://adapty.io/blog/high-performing-paywall-2026/ — 「The practical implication: the onboarding and the paywall are one funnel. What happens in the five screens before the paywall determines whether it converts — not the paywall design itself.」 |
| 86 | **Social proof を各画面に分散**。"Join 2M users" on screen 2、Testimonial on screen 5、Success metric on screen 8。Paywall最終画面のみでなく全体に散らす。Source: https://adapty.io/blog/mobile-app-onboarding-vs-tutorials/ — 「"Join 2M users" on screen 2. A testimonial on screen 5. A specific success metric on screen 8. Each reinforces that other people have solved this problem using your app.」 |
| 87 | **80%の売上は最初のpaywall**。ユーザーはプロダクト体験前にsubscribe。「使わせて良さを知ってもらう」は間違い。Onboarding = 購入意図構築フロー。Source: https://adapty.io/blog/mobile-app-onboarding-vs-tutorials/ — 「roughly 80% of subscription revenue comes from the first paywall shown after onboarding. Users haven't tried your core product yet.」 |
| 88 | **Hard vs Soft両方をA/Bテスト必須**。Hard = 21%高LTV、Soft = 50%高CVR。一方に固定は誤り。両方テストが最高leverage。Source: https://adapty.io/blog/high-performing-paywall-2026/ — 「Hard paywalls produce 21% higher LTV. Soft paywalls convert ~50% better. Both are true simultaneously, which is why picking one and sticking with it is the wrong approach.」 |
| 89 | **SwiftUI優先（UIKitより信頼性高）**。SwiftUIは箱から動作、UIKitは不安定。AIコーディングの正確性がSwiftUIで明らかに高い。Source: https://www.reddit.com/r/ClaudeAI/comments/1ridakj/best_practices_ive_learned_after_shipping/ — 「SwiftUI stuff works out of the box most of the time, I'm intervening less. UIKit is hit or miss.」 |
| 90 | **2026年4月28日以降はXcode 26+iOS 26 SDK必須**。全アップロードにXcode 26とiOS 26 SDK必須。この日以前に全toolchain更新完了。Source: https://developer.apple.com/news/upcoming-requirements/ — 「Begins April 28, 2026. Apps uploaded to App Store Connect must be built with Xcode 26 or later using an SDK for iOS 26, iPadOS 26, tvOS 26, visionOS 26, or later.」 |
| 91 | **AI利用app透明性必須（2026重要）**。AI使用を明確開示。どのAIサービス、どのデータ共有を説明。開示なし = リジェクトリスク高。Source: https://theapplaunchpad.com/blog/app-store-review-guidelines — 「Apps that use AI to generate content, give recommendations, or make automated decisions are reviewed more carefully and must clearly explain how they work.」 |
| 92 | **Incremental build最適化（target分割）**。依存関係を単純化、モノリシックtargetを分割し並列ビルド可能に。Source: https://developer.apple.com/documentation/xcode/improving-the-speed-of-incremental-builds — 「To improve build performance, simplify your target's dependency list, and break up monolithic targets so that Xcode can do more work in parallel.」 |
| 89 | **価格テストはLTV改善（CVRではない）**。Price test CVR win rate 28.3%（最低）、LTV lift 45.5%。高価格 = 高LTVユーザー獲得。12ヶ月未テストなら実施。Source: https://adapty.io/blog/high-performing-paywall-2026/ — 「Price tests rarely improve conversion — only a 28.3% win rate on conversion in the experiment data. But they lift LTV 45.5% of the time. Raising prices doesn't bring in more users; it brings in users worth more.」 |
| 90 | **年14.7実験が必須**。Top performerは平均14.7実験/年、40x売上差（vs 低実験企業）。Structure → Locale → Copy → Price順。Source: https://adapty.io/blog/high-performing-paywall-2026/ — 「Apps that run experiments consistently earn up to 40x more revenue. The average number of experiments among top performers is 14.7.」 |
| 91 | **Onboarding完了直後に星評価リクエスト**。プロダクト未使用でもOK（excited-to-use状態で5星付けやすい）。App Store CVR向上 → Install増 → Paywall到達増。Source: https://adapty.io/blog/mobile-app-onboarding-vs-tutorials/ — 「ask for a rating during or immediately after onboarding, before they've used the product... Most users who made it through onboarding are bought-in enough to give 5 stars. More ratings boost your App Store conversion.」 |
| 92 | **意味のある摩擦はcommitment向上**。Habit apps「5秒指押しcommit」等のインタラクティブ要素。Emotional categories（fitness/health/relationships）で有効。Source: https://adapty.io/blog/mobile-app-onboarding-vs-tutorials/ — 「Small amounts of friction — when they're meaningful — increase commitment. Not every screen needs to be frictionless. Sometimes you want users to pause and think.」 |
| 93 | **3日trial = 26%解約、30日trial = 51%解約**。Trial期間長い = 解約率高い。3日推奨（週次planとベストマッチ）。Source: https://www.businessofapps.com/data/app-subscription-trial-benchmarks/ — 「A three day trial on average will have 26% cancellations, while a 30 day one will have 51%」 |
| 94 | **高価格ほどtrial CVR高い**。$9.99+ subscription が mid/low-price比でtrial conversion高い。価格恐れるな、高めから開始。Source: https://www.businessofapps.com/data/app-subscription-trial-benchmarks/ — 「The higher the app subscription price, the higher the conversion rate for sub trials.」 |
| 95 | **Weekly + 3-day trial = 最高LTV構成（636%増）**。Weekly plan with 3-day free trial が annual より 1.5x LTV。$7.40 → $54.50。Productivity/Lifestyle/Business では direct buyers も検討（trial 不要で高 LTV）。Source: https://adapty.io/blog/high-performing-paywall-2026/ — 「Adding a trial to a weekly plan takes LTV from $7.40 to $54.50 — a 636% increase.」 |
| 96 | **動的Paywall = 35%高CVR**。Segmented or time-based discount 実装で静的比35%向上。Timer、user behavior trigger、region-based offer を組み込む。Source: https://adapty.io/blog/how-to-design-ios-paywall/ — 「Dynamic paywalls with segmented or time-based discounts deliver approximately 35% higher conversion rates than static alternatives」 |
| 97 | **Onboarding直後Paywall = 1.35% CVR（最高）**。90% trial starts、44.5% purchases が Day 0。Onboarding 完了直後に Paywall 表示必須（placement 最重要）。Source: https://adapty.io/blog/high-performing-paywall-2026/ — 「Onboarding paywalls with trials convert at 1.35% on average — the highest of any placement and trial combination」 |
| 98 | **Paywall アニメーション = 2.9x CVR**。CTA pulsing、countdown timer、carousel で +12-18% conversion。静止画面の2.9倍。Source: https://adapty.io/blog/how-to-design-ios-paywall/ — 「Animated paywalls produce 2.9× higher conversion rates than static designs」 |
| 99 | **Localization test = 最高勝率62.3%（price test 45.5%）**。Translation + currency が最優先テスト。日本・米国・英国・ドイツ・フランスで localize。Source: https://adapty.io/blog/high-performing-paywall-2026/ — 「Localization tests: 62.3% win rate on LTV — the highest of any category」 |
| 100 | **ATT 最初表示で受諾率2倍（6% → 15%）**。Custom 説明画面なし、system prompt のみ。Onboarding 最初画面で表示（conversion 影響なし）。Source: https://adapty.io/blog/how-to-build-app-onboarding-flows-that-convert/ — 「we took your advice of moving the ATT prompt to the first app open moment, and were able to more than double our opt-in rate from about 6% to 15%.」 |
| 101 | **年次プランのみ Trial 付与で高 ARPU 化**。Monthly は trial なし → 年次プラン誘導。Top apps の consistent pattern。Source: https://adapty.io/blog/high-performing-paywall-2026/ — 「Moving the free trial exclusively to the annual plan — and dropping it from monthly — is one of the most consistent patterns in top-performing apps right now」 |
| 102 | **Free vs Pro 比較表を Paywall に必須表示**。Top apps（fitness/education/productivity/AI）の標準パターン。「何が含まれるか？」の疑問を即解消。Source: https://adapty.io/blog/high-performing-paywall-2026/ — 「Free vs. Pro comparison tables are one of the most consistent paywall additions among top apps right now」 |
| 103 | **Onboarding = ブラインドデート（信頼構築が目的）**。Clear communication、Personalization、Trust-building（social proof）が必須要素。77% が3日以内離脱 → 初回体験で決まる。Source: https://adapty.io/blog/how-to-build-app-onboarding-flows-that-convert/ — 「Building trust is the entire goal of your onboarding. 77% of people will never come back to your product after three days」 |
| 104 | **CTA 文言で 3% → 27% CVR 改善**。"Subscribe" → "Start your N-day free trial" 形式で 9倍向上。Benefit-driven CTA 必須。Source: https://adapty.io/blog/how-to-build-app-onboarding-flows-that-convert/ — 「When it said "Subscribe", we had a 3% registration-to-trial rate. When it said "Start your 7-day free trial", we had a 27% registration-to-trial rate.」 |
| 105 | **14.7 実験/年 = 40x 売上差**。Top performers は年14.7実験。Structure（plan/trial）→ Locale → Copy → Price の順。Price test は最低勝率（28.3%）。Source: https://adapty.io/blog/high-performing-paywall-2026/ — 「Apps that run experiments consistently earn up to 40x more revenue. The average number of experiments among top performers is 14.7.」 |
| 106 | **価格テストは12ヶ月ごと必須（LTV 改善目的）**。CVR win rate 28.3%（最低）だが LTV lift 45.5%。高価格 = 高 LTV ユーザー獲得。13ヶ月収益で評価。Source: https://adapty.io/blog/high-performing-paywall-2026/ — 「Price tests rarely improve conversion — only a 28.3% win rate on conversion in the experiment data. But they lift LTV 45.5% of the time」 |
| 107 | **24時間限定オファー（Post-Paywall Welcome Offer）**。Onboarding paywall クローズ後、non-converters のみに時限付き割引（年次プラン）を表示。期待 ARPU uplift 10-15%。Full price で買った多数を devalue しない。Source: https://adapty.io/blog/high-performing-paywall-2026/ (2026-03-20) — 「Show a time-limited discount after a user closes the onboarding paywall without converting. A 24-hour welcome offer, targeted only at non-converters, captures price-sensitive users without devaluing the product for the majority who would have paid full price anyway. The expected impact is typically 10–15% ARPU.」 |
| 108 | **Hard Paywall = 5x Better D35 Conversion**。Hard paywalls: 10.7% D35 trial-to-paid conversion vs. Freemium: 2.1%（~5x差）。Hard paywalls: 8x higher RPI at day 60 ($3.09 vs $0.38)。Retention は同等（hard 27% vs freemium 28%）。Source: https://www.revenuecat.com/blog/growth/subscription-app-trends-benchmarks-2026/ (2026-03-20) — 「Hard paywalls have a median Day-35 trial-to-paid conversion rate of 10.7%, compared to just 2.1% for freemium apps.」 |
| 109 | **Day 0 Cancellation = 55% of 3-Day Trials**。55.4% of 3-day trial cancellations occur on Day 0。84% happen between Day 0 and Day 1。Users treat trials like impulsive retail purchases。Aha! moment 必須（first 60 minutes内）。Source: https://www.revenuecat.com/blog/growth/subscription-app-trends-benchmarks-2026/ (2026-03-20) — 「55% of all trial cancellations happen on Day 0. 84% of 3-day trial cancellations happen between Day 0 and Day 1.」 |
| 110 | **17–32日Trial = 70%高CVR（3日比）**。17–32 days trials: 42.5% median conversion vs. <4 days trials: 25.5%。Long trials give users time to integrate app into habits。3日 trial は cash flow 優先（短期収益重視）時のみ。Source: https://www.revenuecat.com/blog/growth/subscription-app-trends-benchmarks-2026/ (2026-03-20) — 「Trials of 17-32 days convert 70% better than 3-day trials (42.5% vs 25.5%).」 |
| 111 | **Annual Sub = Month 1 に 35% Cancel**。35% of annual cancellations occur in Month 1。72% cancel in Year 1（2025年は56%）。Users immediately toggle off auto-renew。Battle for Year 2 starts in Week 1。Month 1 intensive value reinforcement + win-back campaigns 必須。Source: https://www.revenuecat.com/blog/growth/subscription-app-trends-benchmarks-2026/ (2026-03-20) — 「Over one third of users cancel auto-renewal within the first month. 35% of all annual cancellations.」 |
| 112 | **Google Play Billing = 31% Involuntary Churn**。31% of Google Play cancellations are involuntary billing failures（App Store は 14%）。Dunning process 最適化 + grace periods で 15-20% lost revenue を即時回収可能。Android app は billing infrastructure が最優先課題。Source: https://www.revenuecat.com/blog/growth/subscription-app-trends-benchmarks-2026/ (2026-03-20) — 「31% of Google Play cancellations are involuntary billing failures — over double the rate of the App Store (14%).」 |
| 113 | **Consistent Messaging: Ad→Onboarding→Paywall**。同じ価値提案、同じトーン、同じビジュアルで conversion 向上。一貫性がない = 信頼損失 = CVR低下。Source: https://blog.funnelfox.com/effective-paywall-screen-designs-mobile-apps/ (2026-03-27) — 「Consistent messaging from ad to onboarding to paywall increases conversions」 |
| 114 | **Paywall配置 = Onboarding完了直後（最重要placement）**。89.4% の trial starts が Day 0。Onboarding → Paywall が全体の trial acquisition strategy。遅延配置は機会損失。Source: https://appagent.com/blog/mobile-app-onboarding-5-paywall-optimization-strategies/ (2026-03-27) — 「Ensure that most existing users see the paywall by placing it immediately after the onboarding process」 |
| 115 | **Regional A/B Testing 必須（文化的ニュアンス捕捉）**。Top 5 markets（日本・米国・英国・ドイツ・フランス）で独立テスト。Localization win rate 62.3%（最高）。Region-blind test は無効。Source: https://www.revenuecat.com/blog/growth/guide-to-mobile-paywalls-subscription-apps/ (2026-03-27) — 「Conducting regular A/B tests by region is important to capture cultural nuances」 |
| 116 | **Apple Free Trial Toggle 禁止（2026年2月～）**。Apple is now rejecting apps that use a free trial toggle on their paywalls。Toggle UI 削除必須。代替: 2プラン（trial有/無）を並列表示。Source: https://www.revenuecat.com/blog/growth/paywall-redesigns-case-studies/ (2026-03-27) — 「Sadly, as of February 2026, Apple is now rejecting apps that use a free trial toggle on their paywalls」 |
| 117 | **Paywall Reach 90%+ & 初期CR 20%+ を KPI として設定**。広告でスケールするにはPaywall到達率90%以上、初期conversion rate 20%以上が必須。この2指標を最優先モニタリング対象にする。Source: https://x.com/i/status/1964028056311419134 (2026-04-04) — 「Aim for 90%+ paywall reach (users seeing it) and 20%+ initial conversion to scale profitably with ads」 |
| 118 | **50+実験 = 中央値$914K収益**。Top revenue apps run 50+ paywall experiments（median $914K）。WeeklyサブスクがDay 0から55%収益構成。Weekly+trialのA/Bテストを最優先で開始。Source: https://x.com/i/status/2038161875335090560 (2026-04-04) — 「Run 50+ experiments for top revenue (median $914K). Weekly subs now drive 55% of revenue」 |
| 119 | **Personalized Onboarding 10〜14ステップが標準**。長くパーソナライズされたオンボーディング（10〜14+ステップ）がPaywall前の投資感（investment）を構築し、CVR向上。最初の質問から始めてコミットメント蓄積。Source: https://x.com/i/status/1985729675377741848 (2026-04-04) — 「Long, personalized onboarding (10-14+ steps) builds investment before paywall」 |
| 120 | **チャーン後5分以内に30%ディスカウント = 10%収益回復**。Paywall離脱ユーザーに約5分後に30%OFF割引プッシュを送ることで、失った収益の10%を回収可能。RevenueCat Experiments + push notificationで実装。Source: https://x.com/i/status/2006546946274549917 (2026-04-04) — 「Discount pushes (30%) to churned users after ~5min (recovers 10% lost revenue)」 |
| 121 | **Trial→Paid ベンチマーク: 20〜50%が正常範囲**。チェックリスト + quality leads + progressive commitment実装で50%達成可能。Signup→activation 20%→50%への改善は標準的改善幅。Source: https://x.com/i/status/2039334470416011399 (2026-04-04) — 「Signup → activation: 20% → 50% (via removing escapes and progressive commitment)」 |
| 122 | **初回起動30秒以内にコア機能体験 = 2%→40%メイン画面到達**。長いチュートリアル・強制アカウント作成・セットアップ画面を排除。第1画面をactionableにしてユーザーが即試せるようにする。Source: https://x.com/i/status/1895820573185622512 (2026-04-04) — 「Skip long tutorials, mandatory accounts, or setups. Make the first screen actionable. Example: 2% → 40% reaching main screen」 |
| 123 | **Guideline 2.5.2 強化 — 実行時コード変更禁止（2026年）**。アプリのレビュー後に機能を変更するコード（ダウンロード・インストール・実行）を含む全アプリが強制削除対象。2026年に「vibe coding」AIアプリビルダー系が複数削除（Anything app 3/26削除等）。工場で生成するアプリに「LLMがアプリ機能を変更するロジック」を絶対含めない。Source: https://x.com/i/status/2039067781845684726 (2026-04-04) — 「Increased enforcement of Guideline 2.5.2: No apps can download/install/execute code that changes features post-review. In 2026, this has targeted 'vibe coding' AI app builders」 |
| 124 | **ASC CLI v0.49.0 — `asc publish appstore` がE2E提出の標準コマンド**。v0.49.0（2026-04-01リリース）で `asc publish appstore` がローカルIPAアップロード含むエンドツーエンド提出に対応。US-008c/009では `asc publish appstore` を使用。`brew install rudrankriyam/tap/asc` でインストール。Source: https://x.com/i/status/2039413765243121847 (2026-04-04) — 「asc publish appstore handles end-to-end App Store publishing, including local IPA uploads」 |
| 125 | **レビュー遅延: 数時間→数週間（550k+提出/年）**。2026年の提出数急増（56-60%増、年55万+）によりレビュー期間が数時間から数日〜数週間に延長。リリース計画に最低2週間のバッファを設定。締め切りがある場合は提出を前倒し。Source: https://x.com/i/status/2039067781845684726 (2026-04-04) — 「56-60% surge in submissions (550k+ apps/year), causing review delays」 |

## Quality Gate Pattern

Source: SonarQube (https://docs.sonarsource.com/sonarqube-cloud/standards/managing-quality-gates/introduction-to-quality-gates)
> "It can be used to fail your CI pipeline if the quality gate fails."

Each US starts by verifying the previous US acceptance criteria.
Gate fails → do not execute this US. Fix the previous US first.
See each `references/us-00X.md` for specific gate checks.

## Folder Structure

Source: v3 spec §3

```
mobile-apps/<app-name>/
├── spec/01-trend.md              ← US-001
├── product-plan.md               ← US-002
├── competitive-analysis.md       ← US-003
├── market-research.md            ← US-003
├── progress.txt                  ← shared across iterations
├── .env                          ← RC keys (written by Anicca)
├── .app-privacy-done             ← touch by Anicca after Dais confirms
├── docs/                         ← US-004
│   ├── PRD.md, ARCHITECTURE.md, UX_SPEC.md, DESIGN_SYSTEM.md
│   ├── IMPLEMENTATION_GUIDE.md, TEST_SPEC.md, RELEASE_SPEC.md
├── screenshots/raw/ + framed/    ← US-008
└── <AppName>ios/                 ← US-006
    ├── <AppName>.xcodeproj/
    ├── <AppName>/ (App/, Views/, Models/, Services/, Resources/)
    └── <AppName>Tests/           ← US-007
```

## Reporting (ralph.sh → Slack)

ralph.sh posts to Slack #metrics via curl after each iteration.
CC does NOT post to Slack. ralph.sh (bash) does.

```bash
# In ralph.sh, after each iteration:
curl -s -X POST "https://slack.com/api/chat.postMessage" \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{"channel":"$SLACK_CHANNEL_ID","text":"🏭 Iteration $i done: $(head -3 progress.txt)"}"
```
## Reviewer Agent (v2 で追加予定)
Source: ManaLabs (https://manalabs.wtf/appfactory)
> 「A separate reviewer agent independently verifies every file」
v1 では validate.sh が品質ゲート。v2 で独立 reviewer agent を追加する。

## User Decision Gates (自動化)
Source: rshankras WORKFLOW.md — 各 Phase で「User Decision: BUILD / DONT BUILD」ゲートがある。
Factory では自動化のため、Rank 1 アイデアを自動選択し User Decision をスキップする。
## Detailed Instructions

**各 US の詳細手順は `references/us-00X-*.md` を参照。**
SKILL.md のコア指示のみここに記載。詳細は references/ に移動済み。

Source: Anthropic "The Complete Guide to Building Skills for Claude"
> "Keep SKILL.md focused on core instructions. Move detailed documentation to references/ and link to it."

## Files

| File | Purpose |
|------|---------|
| `ralph.sh` | Loop executor (1 US = 1 CC session) |
| `validate.sh` | External quality gate (SonarQube pattern) |
| `CLAUDE.md` | Template for CC instructions |
| `prd.json` | Template for backlog |
| `references/us-001-trend.md` | US-001 detailed instructions |
| `references/us-004-specs.md` | US-004 detailed instructions |
| `references/us-005a-infra.md` | US-005a: Privacy + ASC app creation |
| `references/us-005b-monetization.md` | US-005b: IAP + pricing + RevenueCat |
| `references/us-006-implement.md` | US-006 detailed instructions |
| `references/us-007-testing.md` | US-007 detailed instructions |
| `references/us-008-release.md` | US-008a~e detailed instructions (single file, steps referenced by sub-US) |
| `references/us-009-submit.md` | US-009 detailed instructions |
| `references/rshankras-WORKFLOW.md` | rshankras original workflow (reference) |
