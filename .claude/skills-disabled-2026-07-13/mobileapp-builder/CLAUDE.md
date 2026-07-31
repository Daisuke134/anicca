# mobileapp-builder — CLAUDE.md
# Source: harrymunro/ralph-wiggum (https://github.com/harrymunro/ralph-wiggum/blob/main/CLAUDE.md)
# Source: Geoffrey Huntley (https://ghuntley.com/ralph/) — "use as little context as possible"
# Source: Anthropic harness (https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)

## Step 0: PATH Setup (MANDATORY — EVERY bash command)

Source: Claude Code Docs — https://docs.anthropic.com/en/docs/claude-code/overview
> "Each command runs in a new shell session. Environment variables set in one command are not automatically available in the next."

**Every single `Bash` tool call MUST start with this line. No exceptions:**

```bash
export PATH="/opt/homebrew/bin:/Users/anicca/Library/Python/3.9/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
```

Without this, `asc`, `fastlane`, `xcrun`, `simctl`, `axe`, `jq`, `ls`, `tail`, `grep` and all other commands will fail with `command not found`.
This is NOT optional. This is NOT a suggestion. Prepend it to EVERY command.

## Your Task

APP_DIR = このファイル (CLAUDE.md) が置かれているディレクトリのフルパス。

1. Read `$APP_DIR/prd.json`
2. Read `$APP_DIR/progress.txt` (check Codebase Patterns section FIRST)
3. Pick the **highest priority** user story where `passes: false`
4. Read `.claude/skills/mobileapp-builder/references/us-<NNN>-*.md` for this US
5. Read referenced skills (listed in the spec file)
6. Implement that single user story
7. Run verification checks listed in the spec
8. If checks pass, commit ALL changes: `feat: [US-ID] - [Title]`
9. Update `$APP_DIR/prd.json`: set `passes: true` + add notes
10. Append progress to `$APP_DIR/progress.txt`
11. Report via Slack (BOTH, curl FIRST):
    source ~/.config/mobileapp-builder/.env
    [ -f ./.env ] && source ./.env
    curl -s -X POST "$SLACK_WEBHOOK_AGENTS" -H 'Content-Type: application/json' -d '{"text":"🏭 <US-ID> 完了: <summary>"}'

## Special Slack Reports (US-001, US-007)

### US-001 完了時（アイデア報告）:
curl -s -X POST "$SLACK_WEBHOOK_AGENTS" -H 'Content-Type: application/json' -d '{"text":"📱 アイデア選定完了\nApp: <app_name>\n概要: <one_liner>\n理由: <why_this_trend>\nターゲット: <target_user>"}'

### US-007 完了時（TestFlightリンク報告）:
TESTFLIGHT_URL=$(asc testflight builds get-link --app <APP_ID> --build <BUILD_ID> 2>/dev/null || echo "N/A")
curl -s -X POST "$SLACK_WEBHOOK_AGENTS" -H 'Content-Type: application/json' -d '{"text":"🧪 TestFlight準備完了\nリンク: '"$TESTFLIGHT_URL"'\n↑タップしてテスト可能"}'

## CRITICAL Rules (違反 = リジェクト)

| # | Rule |
|---|------|
| 17 | **Mixpanel 禁止**。アナリティクス SDK は一切入れない。Greenlight が tracking SDK 検出 = CRITICAL |
| 18 | **screenshot-creator スキル使用禁止**。Koubou（`asc screenshots frame`）のみ |
| 19 | **`ASC_BYPASS_KEYCHAIN=true` は絶対禁止。** iris session は US-005a Step 4.9 で管理する。`security unlock-keychain` + `unset ASC_BYPASS_KEYCHAIN` を使うこと |
| 20 | **オンボーディング最終画面はソフトペイウォール必須**。自前 SwiftUI PaywallView + Purchases.shared.purchase(package:)。RevenueCatUI 禁止。[Maybe Later] で閉じれる。Paywall はオンボーディング直後に配置（100% visibility rate 確保）。Source: https://appagent.com/blog/mobile-app-onboarding-5-paywall-optimization-strategies/ — 「Ensure that most existing users see the paywall by placing it immediately after the onboarding process」 |
| 20-BP15 | **Paywall は onboarding の延長線上に置く**。初回体験で核心価値を示した直後にペイウォールを出し、別フローに分離しない。Source: https://x.com/i/status/2044469491258491045 — 「Master Onboarding Before the Paywall: Show value in <30 seconds」 |
| 20-BP16 | **Day 0 で 30 秒の勝利を見せる**。最初の 30 秒以内に「できた」を体験させ、Paywall 到達前に価値を理解させる。Source: https://x.com/i/status/1895820573185622512 — 「Deliver a \"30-second win\" upfront」 |
| 20-BP17 | **onboarding は paywall 後も続ける**。初回成功まで案内を継続して、離脱を防ぐ。Source: https://x.com/i/status/2044806271040151936 — 「onboarding doesn't end at paywall—guide to first win」 |
| 20-DYN | **Dynamic Paywalls実装必須（35%改善）**。ユーザーセグメント（新規/復帰/高エンゲージ）or 時間ベース（初回7日以内、復帰後3日等）で割引・オファー内容を変える。`@AppStorage("firstLaunchDate")` + `@AppStorage("lastActiveDate")` で判定。静的ペイウォールは禁止。Source: https://adapty.io/blog/how-to-design-ios-paywall/ — 「**Dynamic paywalls with segmented or time-based discounts deliver approximately 35% higher conversion rates than static alternatives**」 |
| 20-PRICE | **アンカー価格設定: 月額を高く、年額を強調**。月額を年額等価より20-30%高く設定（例: 年$49.99 → 月$11.99）し、年額プランをデフォルト選択状態 + 視覚的に目立たせる（バッジ「Most Popular」・色・サイズ）。週次換算表示も追加（例: 年$49.99 → 「週$0.96から」）。ただし小さく月額・年額の正確な金額を併記（Apple規約準拠）。Source: https://superwall.com/blog/5-paywall-patterns-used-by-million-dollar-apps/ — 「**Price the monthly plan high. This isn't designed to sell; it's designed to make the annual plan look good. · Visually emphasize the annual plan.**」。Source: https://adapty.io/blog/app-pricing-models/ — 「**Weekly pricing (e.g., ~$4.99/week): makes a subscription feel "small" even if the monthly equivalent is high.**」。**Freemium + Monthly + Yearly が強固なデフォルト**: https://adapty.io/blog/app-pricing-models/ — 「For most consumer subscription apps, a strong default is: freemium + subscription with monthly and yearly plans」 |
| 20-TRIAL | **Free trial 繰り返し表示必須**。トライアル期間を headline + supporting copy + CTA + footer (Cancel anytime) の最低4箇所で繰り返す。1箇所だけでは弱い。Source: https://www.revenuecat.com/blog/growth/paywall-conversion-boosters/ — 「Simply including a "Start Free Trial" button isn't enough—the trial offer should be a central, recurring element throughout your paywall」 |
| 20-BP1 | **Day 0 aha! moment 最優先設計**。初回起動60分以内にアプリの核心価値を体験させる。Source: https://www.revenuecat.com/blog/growth/subscription-app-trends-benchmarks-2026/ — 「**55.4%** of all 3-day trial cancellations occur on Day 0」「**84%** of 3-day trial cancellations happen between Day 0 and Day 1」。オンボーディングは最短経路で価値提示 |
| 20-COPY | **ペイウォールコピーは明瞭 > 創造性**。ベネフィットを直接的に伝え、専門用語を避け、ユーザー成果に焦点を当てる。「What benefit? Why care? How improve life?」に答える。Source: https://www.revenuecat.com/blog/growth/paywall-conversion-boosters/ — 「When it comes to paywall copy, clarity trumps creativity every time. Users aren't looking to be entertained — they're evaluating whether your product is worth their money」 |
| 20-BP2 | **USP 一貫性（広告→オンボーディング→ペイウォール）**。アプリの Unique Selling Proposition を1行で定義し、広告テキスト・オンボーディング画面・ペイウォールヘッドラインで完全一致させる。Source: https://blog.funnelfox.com/effective-paywall-screen-designs-mobile-apps/ — 「**Consistent messaging from ad to onboarding to paywall increases conversions**」 |
| 20-CTA-EMOJI | **CTA ボタンにエモジ/矢印装飾必須（2x conv）**。CTAボタンテキストにエモジ（🙌, ✨等）やポインター矢印を追加する。装飾なしCTAの2倍のコンバージョン。Source: https://x.com/i/status/1964132458225348745 — 「Large, fixed CTA button always visible, add emojis/arrows—doubled conv in one case」 |
| 20-DRIP | **ポストクローズ段階的ディスカウント実装（Phase 2）**。初回クローズ→24hオファー（20-BP3）に加え、未購入ユーザーに平均コンバージョン時間で30%off → 7日後50%off → 14日後70%offの段階的プッシュ通知を送る。80-90%の初回非購入者をリカバーする。Source: https://x.com/i/status/1930792783763190200 — 「80-90% don't buy initially—catch with timed pushes: 30% off at avg conv time, escalate to 50-70%」 |
| 20-ANIM | **ペイウォールに animation 追加必須（12-18%改善）**。CTA ボタンに subtle pulse effect、プラン選択カードに gentle entrance effect を実装。静的デザインより注意を引く。Source: https://www.revenuecat.com/blog/growth/paywall-conversion-boosters/ — 「Animated elements on paywalls consistently improve conversion rates. When implemented correctly, animated elements typically increase conversion rates by 12-18% compared to static alternatives.」 |
| 20-BP3 | **ポストクローズ 24h オファー実装必須**。ユーザーがペイウォールを閉じた場合、`@AppStorage("paywallDismissedAt")` に Date() を保存し、次回起動時（24h以内）に限定オファー画面を1回のみ表示。10-15% ARPU 増。Source: https://adapty.io/blog/high-performing-paywall-2026/ — 「A 24-hour welcome offer, targeted only at non-converters... typically 10–15% ARPU」 |
| 20-BP4 | **ローカライゼーション = 最優先テスト項目**。英語+日本語は最低要件。LTV 改善で勝率 62.3%（全テストタイプ中最高）。Source: https://adapty.io/blog/high-performing-paywall-2026/ — 「Localization tests: 62.3% win rate on LTV — the highest of any category」 |
| 20-AB | **地域別A/Bテスト計画必須（Phase 2）**。リリース後1週間以内にRevenueCat Experimentsで地域セグメント（US, JP, EU等）ごとにペイウォールバリアント（コピー・価格表示順・オファー内容）をテストする計画を立てる。文化的ニュアンスで変換率が変わる。Source: https://www.revenuecat.com/blog/growth/guide-to-mobile-paywalls-subscription-apps/ — 「**Conducting regular A/B tests by region is important to capture cultural nuances**. By refining the experience based on specific regional insights, you can achieve higher conversions across diverse markets.」 |
| 20-ITER | **継続改善: 1週間ごとに1要素テスト**。初回実装後、1週間ごとにペイウォールの1要素（ヘッドライン、ベネフィット順序、価格表示、CTA文言）を変えたバリアントをテストする。20-50%の改善が見込める。Source: https://apphud.com/blog/design-high-converting-subscription-app-paywalls — 「**According to industry data, top-performing apps A/B test their paywalls frequently and have seen conversion rate lifts of up to 30–50% through continuous testing**」 |
| 20-TOGGLE | **Free trial toggle 絶対禁止（2026年2月時点）**。Apple は paywall 上の free trial toggle（試用期間をON/OFFするUI要素）を含むアプリを審査拒否する。trial の有無は別プラン（別 Product ID）として提供し、toggle UI は使わない。Source: https://www.revenuecat.com/blog/growth/paywall-redesigns-case-studies/ — 「**Sadly, as of February 2026, Apple is now rejecting apps that use a free trial toggle on their paywalls. This means for iOS apps you may need to try one of the other redesigns, or check out toggle-adjacent options here.**」 |
| 20-BP3 | **Year 2 retention は Week 1 で決まる**。年間サブスクの35%はMonth 1で自動更新OFF。Push 通知戦略に「Month 1 での価値リマインド + 自動更新再ON促進」を組み込む。Source: https://www.revenuecat.com/blog/growth/subscription-app-trends-benchmarks-2026/ — 「the first month accounts for **35%** of all annual cancellations」 |
| 20-ONB15 | **15分オンボーディング → 43%転換（投資=コミットメント）**。5分→15分に延長で月$20Kスケール成功例。診断質問 + AI生成パーソナライズ結果で「aha! moment」を早期提示。無価値な画面追加禁止。Source: https://stormy.ai/blog/mobile-app-onboarding-optimization-guide — 「increasing his onboarding time from 5 minutes to 15 minutes... achieving a 43% conversion rate... investment leads to commitment」 |
| 20-BP5 | **77% of users churn within 3 days**。Day 0-3のアクティベーションを最優先に設計する。初回起動60分以内に核心価値を提示し、Day 1-3にユーザーが「aha! moment」を経験する導線を確保する。Source: https://adapty.io/blog/how-to-build-app-onboarding-flows-that-convert/ — 「77% of people will never come back to your product after three days of downloading your app」 |
| 20-10PCT | **10% download→trial がペイド広告可否の閾値**。この水準未満は CAC > LTV になる。オンボーディングを週1要素テストし続け、10%到達後にペイド投入。Source: https://stormy.ai/blog/mobile-app-onboarding-optimization-guide — 「you do not stop tweaking your onboarding until you hit a 10% download to trial conversion rate. This is the minimum threshold required to make paid ads viable」 |
| 20-BP6 | **Button copy matters (3% → 27%)**。Paywall CTAボタンは「Subscribe」ではなく「Start your [N]-day free trial」を使う。具体的なトライアル期間を明記することで登録-トライアル転換率が9倍向上。Source: https://adapty.io/blog/how-to-build-app-onboarding-flows-that-convert/ — 「When it said "Subscribe", we had a 3% registration-to-trial rate. When it said "Start your 7-day free trial", we had a 27% registration-to-trial rate」 |
| 20-BP7 | **Good onboarding = 50%+ retention impact**。オンボーディング最適化は継続的な反復プロセスとして設計に組み込む。1つの実験で終わらず、複数回のA/Bテストで継続改善する。Source: https://adapty.io/blog/how-to-build-app-onboarding-flows-that-convert/ — 「A good onboarding flow can have an impact of more than 50% on your retention」 |
| 20-BP8 | **Personalization increases activation by 13%**。Onboardingで名前入力を含める（たとえデータベースに保存しなくても）。パーソナライゼーション効果でアクティベーション率が向上。Source: https://adapty.io/blog/how-to-build-app-onboarding-flows-that-convert/ — 「We added a name field to the onboarding. We didn't even use it. We didn't database it. We just wanted to see what would happen. And what we saw was a 13% uplift in activation」 |
| 20-BP9 | **87% leave if not clear**。Onboardingのシンプルさと明確さを最優先設計原則とする。ユーザーがアプリの価値を即座に理解できるようにし、複雑な説明や冗長な手順を避ける。Source: https://vwo.com/blog/mobile-app-onboarding-guide/ — 「87% of people have left an onboarding flow because it wasn't clear to them」 |
| 20-BP10 | **Interactive onboarding > static**。静的なスライド型オンボーディングを避け、ユーザーが実際にタスクを完了するインタラクティブな導線を採用する。読むだけより体験で学ぶ方が効果的。Source: https://vwo.com/blog/mobile-app-onboarding-guide/ — 「Replace static instructions with interactive walkthroughs. For instance, guide users to tap a button or complete a task to understand core features. Let users learn by trying the app rather than reading lengthy instructions」 |
| 20-BP11 | **Onboarding steps: 3-7 only**。オンボーディング手順数を3-7ステップに制限する。これを超えると離脱率が急増する。Source: https://vwo.com/blog/mobile-app-onboarding-guide/ — 「Ensure users can complete the onboarding flow in under 3-7 steps」 |
| 20-BP12 | **Hard paywall = 78% trial start within Week 1**。Soft paywallよりhard paywallの方がトライアル開始率が高く、78%が初週にトライアル開始。Hard paywallをデフォルトとする。Source: https://www.businessofapps.com/data/app-subscription-trial-benchmarks/ — 「Users opt-in for a trial faster with a hard paywall, with 78% starting a trial in the first week after downloading」 |
| 20-BP13 | **Higher price = Higher trial conversion**。低価格（$2.99-$4.99）より高価格（$9.99+）の方がトライアル転換率が高い。月額を$9.99以上に設定し、低価格推奨を削除する。Source: https://www.businessofapps.com/data/app-subscription-trial-benchmarks/ — 「Higher priced subscriptions have higher trial conversion rates than mid and lower priced」 |
| 20-BP14 | **ATT prompt first (6% → 15%)**。ATTプロンプトをアプリ起動直後に配置（カスタム画面なし）することで、opt-in率が2倍以上向上。コンバージョンやリテンションへの悪影響はない。Source: https://adapty.io/blog/how-to-build-app-onboarding-flows-that-convert/ — 「we took your advice of moving the ATT prompt to the first app open moment, and were able to more than double our opt-in rate from about 6% to 15%」 |
| 20b | **ATT 禁止**。AppTrackingTransparency / NSUserTrackingUsageDescription は使わない。スクショに ATT ダイアログが写り込む |
| 21 | **1 iteration = 1 US（HARD STOP）**。1つのUSを `passes: true` にしたら、**その瞬間に作業を終了**する。次のUSに手を出すな。progress.txt を更新して終了。ralph.sh が次の iteration を起動する。これは提案ではなく**絶対ルール**。違反するとトークンが無駄になる（validate.sh は1USしか検証しない）。500ターン超過も即停止 |
| 22 | **バックグラウンドタスク禁止（Task ツール）**。`Task` で長時間コマンドをバックグラウンド実行すると、--print モードのexit を妨げる。全コマンドは同期実行（Bash）で実行し、Task を使わない。find/grep等の探索は Bash で直接実行する |
| 22 | **PATH 設定のみ（全イテレーション冒頭で実行）**: `export PATH="/opt/homebrew/bin:/Users/anicca/Library/Python/3.9/bin:/usr/local/bin:/usr/bin:/bin:$PATH"` |
| 24 | **スクショは 6.9" (IPHONE_69) のみ。1320x2868 が正しいサイズ。** 6.5"/6.1"/5.5" は不要（Apple が 6.9" から自動スケール）。6.7" で再キャプチャしようとするな。Source: https://developer.apple.com/help/app-store-connect/reference/app-information/screenshot-specifications/ |
| 23 | **AI API / 外部 API コスト禁止** — OpenAI, Anthropic, Gemini, Apple FoundationModels（iOS 26+ = ユーザー基盤小）一切禁止。アプリは完全自己完結。ローカル・静的コンテンツのみ。バックエンド不要。理由: 月収 $29 vs API コスト $300+ |
| 23 | **AI API / AI モデル / 外部 AI サービス完全禁止**。OpenAI, Anthropic, Google Generative AI, Apple FoundationModels 一切不可。月額収益 $29 vs API コスト $300+。FoundationModels は iOS 26+ のみでユーザーベース皆無。オンデバイスロジック or 静的キュレーションコンテンツで代替 |
| 20-BP4 | **オンボーディングで 30-Second Win を先に見せる**。価値を paywall 前に体験させる。Source: https://x.com/i/status/1895820573185622512 — 「Deliver a \"30-second win\" upfront」 |
| 20-BP5 | **価格は 2-3 プランに整理し、年額を比較上有利に見せる**。Source: https://x.com/i/status/2044809040530674100 — 「Tier       | Price Example      | Best For」 |
| 25 | **progress.txt 管理**: Codebase Patterns + 現在 US の記録のみ保持。完了 US の詳細は `logs/us-XXX-summary.md` に移動。10KB 以下維持。Source: Anthropic harnesses — context 膨張防止 |
| 26 | **WAITING_FOR_HUMAN 最小化**: iris session は keychain（auto モード）で管理。`ASC_WEB_SESSION_CACHE_BACKEND=file` は絶対に設定するな（keychain を読まなくなる）。Check 6 の前に `security unlock-keychain` 必須。RC SK鍵のみ WAITING_FOR_HUMAN 使用可。Source: session_cache.go L103-118 |
| 27 | **.pbxproj 直接編集禁止**。新しいファイルは CC で作成し、Xcode で手動追加する。CC に .pbxproj を編集させるとプロジェクトが壊れる。Source: https://www.linkedin.com/posts/kris-puckett-0109041b_if-youre-building-an-ios-app-with-claude-activity-7393778932807852032-Pkuj — 「Never let AI modify .pbxproj files. Create files with Claude Code, add them to Xcode manually.」 |
| 28 | **iOS 26 SDK 必須（2026年4月以降）**。Xcode プロジェクト設定で `IPHONEOS_DEPLOYMENT_TARGET = 26.0` 以上。4月以降の提出では古い SDK は審査リジェクト。Source: https://medium.com/@thakurneeshu280/apple-app-store-submission-changes-april-2026-5fa8bc265bbe — 「Starting April 2026, apps and games uploaded to App Store Connect need to meet minimum SDK requirements」 |
| 29 | **プライバシー透明性（AI 連携アプリ）**。データ収集・利用を明示。Info.plist に `NSPrivacyCollectedDataTypes` + `NSPrivacyTracking` + AI 連携の開示。Source: https://theapplaunchpad.com/blog/app-store-review-guidelines — 「Privacy and data transparency are major priorities in 2026. Apps must clearly disclose what data they collect, how it is used, and obtain consent before sharing it with third parties, especially AI services.」 |
| 30 | **ランダム/匿名チャット = UGC 審査**。チャット機能にはモデレーション + 通報機能必須（App Review Guideline 1.2）。Source: https://developer.apple.com/news/?id=d75yllv4 — 「apps with random or anonymous chat are subject to the 1.2 User-Generated Content guideline」（2026年2月6日更新） |
| 38 | **アイコン・タイトルは完全オリジナル必須（Guideline 4.1(c)）**。他のデベロッパーのアイコン・ブランド名・アプリ名をアイコンやタイトルに無断使用禁止。特にAI生成クローンアプリは審査拒否リスク。Source: https://x.com/i/status/1989038309465600151 — 「Bans using other developers' icons, brands, or names in app icons/titles without permission. Targets copycats, especially AI-generated clones.」（Guideline 4.1(c)、2025年11月施行）factory生成アプリはアイコン・タイトルの独自性を必ず確認する。 |
| 31 | **ターゲット分割で並列ビルド**。依存関係を単純化し、モノリシックなターゲットを避ける（30-50%高速化）。Source: https://developer.apple.com/documentation/xcode/improving-the-speed-of-incremental-builds — 「To improve build performance, simplify your target's dependency list, and break up monolithic targets so that Xcode can do more work in parallel.」 |
| 32 | **フィードバックループを閉じる**。ビルド・テスト結果を直接処理し、自分でエラー原因を特定する。間接的なログ確認より直接結果をパースする方が精度高い。Source: https://plankenau.com/blog/post/claude-coding-an-ios-app — 「focus on closing the feedback loop, i.e., claude code does best when it can process the result of its changes in the most direct way possible.」 |
| 33 | **失敗時は浅い修正禁止 — 立ち止まって分析**。ビルド・テストが失敗したら即座にリトライせず、エラーログ全体を読み、根本原因を特定してから修正する。浅い修正 + 即リトライが最も危険なパターン。Source: https://www.reddit.com/r/ClaudeAI/comments/1ridakj/best_practices_ive_learned_after_shipping/ — 「the most dangerous pattern was none of the things you listed — it was what happens when a build or test fails. Claude's default behavior is to make a shallow fix and retry immediately.」 |
| 34 | **全ての変更を progress.txt に文書化**。次回セッションで5分で復帰できるように、変更内容・理由・検証結果を progress.txt に追記する。30分のチャンクでも作業可能にする。Source: https://www.zdnet.com/article/claude-code-vibe-coding-iphone-app-lessons/ — 「with vibe coding and my practice of making Claude document everything, I can work on my project even if I only have a 30-minute block of time.」 |
| 35 | **XcodeBuildMCP 使用 — 生の xcodebuild コマンド禁止**。構造化された出力とエラーハンドリングのため、MCP ツール（mcp__xcodebuildmcp__build_sim_name_proj, mcp__xcodebuildmcp__test_sim_name_proj）を使う。生の xcodebuild は危険。Source: https://gist.github.com/joelklabo/6df9fa603bec3478dec7efc17ea44596 — 「Never use raw xcodebuild commands. Always use the appropriate MCP tool」 |
| 36 | **iOS 26 deprecated API チェック**。10年以上前に deprecated されたキーは iOS 26 SDK でビルドエラーになる。新規アプリでは最新 API を使い、古いキーを使わない。Source: https://developer.apple.com/documentation/ios-ipados-release-notes/ios-ipados-26-release-notes — 「These keys have been deprecated for more than a decade. Affected apps rebuilt with the iOS or macOS 26 SDK will get errors.」 |
| 37 | **Build Timeline で blocking タスクを特定**。Xcode の Build Timeline を使ってコンパイル時間を支配しているファイルを特定し、大きなファイルを分割する。Source: https://bitrise.io/blog/post/expert-tips-to-speed-up-your-ios-builds — 「Use Xcode's Build Timeline to spot blocking tasks. Refactor or split large Swift files that dominate compile time.」 |

## ASC CLI 正しいコマンド（skill 準拠）

| タスク | 正しいコマンド | スキル |
|--------|---------------|--------|
| スクショ capture | `asc screenshots capture --bundle-id ... --udid ... --output-dir ... --output json` | asc-shots-pipeline |
| スクショ upload | `asc screenshots upload --version-localization LOC_ID --path DIR --device-type IPHONE_69` | asc-shots-pipeline |
| Review screenshot | `asc subscriptions review-screenshots create --subscription-id ID --file PATH` | — |
| ビルド最新取得 | `asc builds list --app APP_ID --sort -uploadedDate --limit 1` | asc-build-lifecycle |
| ビルドをグループ追加 | `asc builds add-groups --build BUILD_ID --group GROUP_ID` | asc-testflight-orchestration |
| テスター追加 | `asc testflight beta-testers add --app APP_ID --email ... --group ...` | asc-testflight-orchestration |
| テスター招待 | `asc testflight beta-testers invite --app APP_ID --email ...` | asc-testflight-orchestration |
| Version ID 取得 | `asc versions list --app APP_ID` | asc-id-resolver |
| Loc ID 取得 | `asc app-store-version-localizations list --version-id VER_ID` | asc-id-resolver |
| App Privacy | `asc web privacy apply` + `publish`（自動、セッション切れ時のみ WAITING_FOR_HUMAN） | us-009-submit |
| RC Public Key | `curl -s "$RC_BASE/projects/$PID/apps/$AID/public_api_keys" -H "$AUTH" \| jq -r '.items[0].key'`（自動） | us-005b-monetization |
| 審査提出 | `asc review submissions-create --app APP_ID` → `items-add` → `submissions-submit` | asc-submission-health |

**❌ 存在しないフラグ（使うな）:** `--locale`, `--file`(screenshots upload), `--display-type`

## Progress Report Format
# Source: mischasigtermans/ralph (https://github.com/mischasigtermans/ralph)

APPEND to progress.txt (never replace):

```
## [Date] - [US-ID]: [Title]
- What was implemented
- Files changed
- **Learnings for future iterations:**
  - Patterns discovered
  - Gotchas encountered
---
```

## Token Efficiency (BP 6)
Source: ios-simulator-skill (https://github.com/conorluddy/ios-simulator-skill#output-efficiency)  
核心の引用: 「All scripts minimize output by default. Screen analysis: 200+ lines → 5 lines (97.5% savings).」

**デフォルト出力は 3-5 行のみ。詳細は必要時のみ。**
- `Bash` コマンド出力は簡潔に（ログ全文を貼らない）
- 長いログは `tail -20` / `grep` で要約
- JSON 出力は `jq` で必要フィールドのみ抽出
- 成功/失敗の結果だけ報告（詳細は求められたら）

**目標**: トークン使用量を最小化し、conversation を集中させる。

## Mandatory Quality Gates (Backpressure)
# Source: harrymunro/ralph-wiggum CLAUDE.md
# Quote: "Quality gates are mandatory blockers, not suggestions"

Before marking ANY story as `passes: true`, you MUST verify:
1. All acceptance criteria met with EVIDENCE (not assertion)
2. All checks in the reference file pass
3. git commit clean

### Forbidden Shortcuts
# Source: harrymunro/ralph-wiggum CLAUDE.md

| Forbidden | Why |
|-----------|-----|
| Mock/Stub RevenueCat | Must use real SDK |
| Skip subscription pricing | MISSING_METADATA = rejection |
| Python/Pillow for screenshots | Only Koubou + asc-shots-pipeline skill |
| Skip greenlight checks | External gate will catch and reset |
| Set passes:true without evidence | validate.sh will auto-reset |

### Evidence Over Assertion
# Source: harrymunro/ralph-wiggum CLAUDE.md
# Quote: "Never claim something works without proving it"

| Bad (Assertion) | Good (Evidence) |
|-----------------|-----------------|
| "Subscriptions configured" | "asc subscriptions list → state=READY_TO_SUBMIT" |
| "Screenshots uploaded" | "find screenshots/framed -name '*.png' \| wc -l → 3" |
| "Build valid" | "asc builds list → processingState=VALID" |

Run the command. See the output. Report the evidence.

## Secrets
Before any signing/build:
```
source ~/.config/mobileapp-builder/.env
[ -f ./.env ] && source ./.env
security unlock-keychain -p "$KEYCHAIN_PASSWORD" ~/Library/Keychains/login.keychain-db
```

## Stop Condition
# Source: harrymunro/ralph-wiggum + snarktank/ralph

After completing a story, check if ALL stories have `passes: true`.
If ALL complete: `<promise>COMPLETE</promise>`
If stories remain: end normally (next iteration picks up).

## CRITICAL RULES
- Read .claude/skills/mobileapp-builder/SKILL.md for all CRITICAL RULES
- ONE story per iteration (Source: ghuntley.com/ralph/ "one item per loop")
- Every source file change → git commit
- Every US start → Slack report
- Every US completion → update `$APP_DIR/progress.txt` + `$APP_DIR/prd.json` + git commit + Slack report
- DO NOT modify validate.sh or ralph.sh (external quality gates, not your files)
- DO NOT modify `.claude/skills/mobileapp-builder/prd.json` (テンプレート。`$APP_DIR/prd.json` のみ編集可)
- DO NOT modify `.claude/skills/mobileapp-builder/SKILL.md` or `.claude/skills/mobileapp-builder/CLAUDE.md` (テンプレート)

## 3-Attempt Limit
# Source: harrymunro/ralph-wiggum CLAUDE.md
# https://raw.githubusercontent.com/harrymunro/ralph-wiggum/main/CLAUDE.md
# Quote: "If you cannot make a story pass quality gates after 3 attempts: STOP"

If you cannot make a story pass after 3 attempts:
1. STOP — do not continue iterating
2. Document what's failing in progress.txt with "BLOCKED: <reason>"
3. **DO NOT SKIP to the next story** — wait for the issue to be resolved
4. Never use forbidden shortcuts to force a pass

**CRITICAL:** 前の US が完了していないまま次の US に進むと、モックコードや不完全な実装になる。
US は順序依存。US-005a（インフラ）→ US-005b（マネタイズ）→ US-006（実装）の順。
BLOCKED 状態で iteration を終了し、次の iteration で再試行を待つ。

## Consolidate Patterns
# Source: harrymunro/ralph-wiggum CLAUDE.md
# Quote: "add reusable patterns to Codebase Patterns at TOP of progress.txt"

If you discover a reusable pattern, add it to `## Codebase Patterns`
at the TOP of progress.txt (create if it doesn't exist).
Only general, reusable patterns — not story-specific details.


## US別詳細手順
各USの実行時は必ず対応する `references/us-XXX.md` を読むこと。
この CLAUDE.md には詳細を書かない。references が常に正本。

### ASC CLI スキル（補助参照 — 必要に応じて読む）
- US-008a screenshots: `.agents/skills/asc-shots-pipeline/SKILL.md` (screenshot pipeline patterns)
- US-008b metadata: `.agents/skills/asc-metadata-sync/SKILL.md` (metadata sync patterns)
- US-008e release: `.agents/skills/asc-release-flow/SKILL.md` (release flow)
- CLI usage: `.agents/skills/asc-cli-usage/SKILL.md` (flags/output/auth guidance)

| US-010 | Build Report | logs/ トークン集計 → build-report.json → Slack + X 投稿 | us-010-report |

## WAITING_FOR_HUMAN
progress.txt に `WAITING_FOR_HUMAN: <what you need>` を書いて passes: false にする。
ralph.sh が検知して Slack に通知する。
次のイテレーションで .env を確認して再開する。

## US-008 連続実行ルール（CRITICAL）
US-008a を開始したら、US-008e まで連続で完了させること。
途中で他の US（US-004b, US-004-R, US-005a 等）に移動してはならない。
prd.json の priority 順を無視して、US-008a → 008b → 008c → 008d → 008e の順に実行する。
理由: US-008a-d で取得した VERSION_ID, BUILD_ID, LOC_ID 等の環境変数が
有効な間に全ステップを完了しないと、途中で別の US に飛ばされてセッションが切れる。
