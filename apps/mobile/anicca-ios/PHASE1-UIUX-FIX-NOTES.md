# Phase 1 UI/UX 修正記録

対象: `Daisuke134/anicca` / `claude/phase1-personalized-onboarding` / PR #9352。
委任元の 2026-11-14 F-01〜F-13 と添付監査フレームを仕様とする。
App Store Connect 操作・提出・ストア素材更新・commit/push は行わない。

## 作業計画

- [x] 共通テーマ: 既存 AppTheme / AppBackground / PrimaryButton / CardView を再利用し、系統Aへ統一。
- [x] オンボーディング: welcome→goal→name→pain→frequency→preview→schedule→permission。保存済み rawValue の移行を保持。不要画面を削除。
- [x] ペイウォール: 年額を主オファーとして、総請求額・期間・適用可能なトライアル・換算額・復元/規約を読み切れる形へ。
- [x] ホーム: 単一の今日の言葉、最初の介入との一致、テーマ選択表示、背景付き保存カード。
- [x] 補助画面: 通知・プロフィール・利用上限・習慣・認証・Widget・共有画像の見た目を統一。
- [ ] 検証: 既存/更新テスト、ローカル静的確認、Maestro 01〜13 の再撮影導線、独立レビュー。

レビュー重点: 再開時の互換性、通知リンク優先、初回/再起動の言葉の一致、トライアル対象外と代替商品の表示、長文/日本語/大きい文字の切れ。

## 環境と手順の証拠

- Git root: `/home/hatch/workspace/life-manager-phase1`。共通Gitディレクトリ: `/home/hatch/workspace/life-manager/.git`。既存の専用 worktree を使用。開始時の差分なし。開始 HEAD: `2bac2ac6c15b1de7df6005700bcee7d057a5fa2b`。
- `bash scripts/verify-source-boundary.sh`: exit 2。Life Manager 固定パスを期待するため失敗。実際の origin は委任文が指定する `https://github.com/Daisuke134/anicca.git` と一致。今回の明示的な委任を優先し、境界スクリプトは変更しない。
- `AGENTS.md` は Life Manager remote を正本とし、`docs/team/README.md` / `RULES.md` / `specs/apps.md` は無料トライアルなし・ハードペイウォールを記載。一方、現在のコードと今回の仕様は Anicca のソフトペイウォール＋適格な年額トライアル。今回の仕様と既存購入処理を優先する。
- Astra Advisor ツールは公開されていない。既存部品・依存を再利用する最小解を採用。
- 手順を実読: `/home/hatch/.codex/plugins/cache/openai-curated-remote/superpowers/7.0.1/skills/` 配下の `using-superpowers/SKILL.md`（Codex reference 含む）、`systematic-debugging/SKILL.md`、`writing-plans/SKILL.md`、`executing-plans/SKILL.md`、`dispatching-parallel-agents/SKILL.md`、`test-driven-development/SKILL.md`、`using-git-worktrees/SKILL.md`。仕上げで `requesting-code-review/SKILL.md`（reviewer template含む）、`verification-before-completion/SKILL.md`、`finishing-a-development-branch/SKILL.md` を実読。ユーザー指定の「差分を保持、Museがcommit/push」を仕上げ方法として適用した。
- Linux に `swift` / `swiftc` / `xcodebuild` は未検出。Xcode ビルド/単体テストの正本は委任元が push 後に実行する GitHub Actions。ローカル確認と区別して記録する。
- Apple価格表示根拠: https://developer.apple.com/app-store/subscriptions/ （2026-11-14 読取）。総請求額・更新期間を主表示、換算額を補助とする。

## F-01〜F-13 の結果

以下の「実装」は作業ツリーの差分を示す。ビルド成功・新フレームでの欠陥閉鎖を示すものではない。

| 項目 | 変更内容・判断と対象ファイル（`aniccaios/` 以下） |
|---|---|
| F-01 | `DesignSystem/AppTheme.swift`、`AppBackground.swift`、`Components/PrimaryButton.swift`、`Components/CardView.swift` を共通土台とし、温かい薄緑グラデーション・セリフ見出し・深緑CTA・選択面＋枠＋右チェックへ統一。`Onboarding/StrugglesStepView.swift`、`StruggleDepthStepView.swift`、`NotificationPermissionStepView.swift`、`PaywallVariantBView.swift`、`Views/Feed/SettingsSheet.swift` の各シートにも適用。本文は読みやすいシステム書体を維持。テーマ画像のある言葉カードは画像を保持。 |
| F-02 | `Onboarding/PaywallVariantBView.swift` の前面を年額1オファーにし、他プランは「Other plans」シートへ移した。各プランの実価格を全文表示。日程は開始・請求開始の2行、折り返し可。通常文字サイズの1画面を目標にコンパクト化し、小画面・大型文字では `ViewThatFits` で1つのスクロールへ退避する。Restore Purchases / Terms / Privacy は維持。原寸での収まりは再撮影待ち。 |
| F-03 | 同ファイルの実総額＋実更新期間を主表示（title2）、年額の月額換算を下側のcaptionへ配置。「年払い」の文言を併記。価格は RevenueCat の実商品から計算し、固定額を書かない。`PaywallPackageSelection.swift` に適格性ルールを追加し、trial/CTA/日程は選択商品専用。Lifetimeへ替えると買い切り説明になり、年額trialを引き継がない。 |
| F-04 | `Onboarding/InitialAffirmationExperience.swift` の `OnboardingPage` で本文スクロールとCTAを分離し、見出し・本文を縦に折り返す。通知設定の英語見出しを “A moment for you” に短縮。孤立したタイムゾーン表示を削除し、本文で端末の現地時刻と説明。ペイウォール・プロフィール説明・共有カードの切り捨ても除去。 |
| F-05 | `Views/Feed/FeedRootView.swift` の既定ホームを今日の1つの言葉へ変更。分類メニュー・無限ページ追加を既定ホームから撤去。`Services/DailyAffirmationStore.swift` が現地日付・言語ごとに保存し、その日の再起動では再抽選しない。長文閲覧用スクロールは残すが、別の言葉へページ送りしない。通知タップの文は即時優先する。 |
| F-06 | `Onboarding/OnboardingStep.swift` の先頭をwelcomeへ戻し、goalの後に独立したnameを追加。`InitialAffirmationExperience.swift` の `PreferredNameStepView` は任意入力と端末内保存を説明。`OnboardingFlowView.swift`、`WelcomeStepView.swift`、`OnboardingProgressBar.swift`、`Services/AnalyticsManager.swift` を対応。旧rawValue 0〜8は維持し、新nameは9。welcomeをgoalへ読み替えない。旧processing/comparisonの保存値のみpreviewへ移行する。 |
| F-07 | `InitialAffirmationExperience.swift` でpreviewは “Choose my reminder times”、介入は “Open my daily moment” と行き先を分離。全6言語の文言を更新。 |
| F-08 | `Views/Feed/SettingsSheet.swift` の `ThemePickerView` に現在のテーマのチェック・緑枠・selected accessibility traitを追加し、現在テーマを先頭へ置く。`theme-selected-<rawValue>` をMaestroで確認できる。 |
| F-09 | `Services/LikedQuotesStore.swift` に保存時テーマを保持。`SettingsSheet.swift` の `LikedQuotesView` はその画像背景とセリフのカードで表示する。旧ID/本文保存を維持し、テーマ情報がない旧保存はsageMistを使う。`QuoteCardView.swift` から現在テーマを渡す。 |
| F-10 | `InitialAffirmationExperience.swift` の介入CTAから `DailyAffirmationStore.seed` に実際のquoteを渡し、ホームが同じものを読む。通知タップが来た場合はその通知文を優先し、その日の保存も置き換える。初回・再起動・日跨ぎ・言語切替を `DailyAffirmationStoreTests.swift` で検証する。 |
| F-11 | **変更しない。コード変更の対象外であり、ストア素材の別作業として残す。** App Storeスクリーンショット1枚目、掲載情報、提出には触れていない。D-16は未完了。 |
| F-12 | Welcomeのみ現行導線へ復帰。未参照の旧13 Viewを削除（下表）。`OnboardingBibleViews.swift` は現役 `PaywallFlowContainer` のみ保持。保存値の移行に必要なenumは残し、旧View参照を残さない。 |
| F-13 | `Views/Feed/SettingsSheet.swift` の設定・通知、`Views/Profile/TraitsDetailView.swift`、`Views/UsageLimitModalView.swift`、`Onboarding/RetentionOfferSheet.swift` / `PaywallPrimerStepView.swift`、`Settings/Habit*FollowUpView.swift`、`Session/AuthRequiredPlaceholderView.swift`、`Views/Feed/ShareImageRenderer.swift` を共通背景/書体/ボタンへ統一。`AniccaWidget/AniccaWidget.swift` / `AniccaWidgetLiveActivity.swift` / `WidgetShared.swift` も同じパレットとセリフへ変更。ロック画面のOSによる単色化・面積制約は保持。到達性は次表。 |

### F-12 削除したファイル・シンボル

| ファイル | 削除シンボル |
|---|---|
| `aniccaios/Onboarding/ProcessingStepView.swift`（ファイル削除） | `ProcessingStepView` |
| `aniccaios/Onboarding/PersonalizedInsightStepView.swift`（ファイル削除） | `PersonalizedInsightStepView` |
| `aniccaios/Onboarding/ValuePropStepView.swift`（ファイル削除） | `ValuePropStepView` |
| `aniccaios/Onboarding/OnboardingBibleViews.swift`（現役Container保持） | `AgeRangeStepView`, `GoalStepView`, `TinderPainCardsView`, `WhatTriedStepView`, `StressSliderStepView`, `SocialProofStepView`, `PreferredNudgeTimesView`, `MeditationExperienceStepView`, `ComparisonTableStepView`, `PaywallValueTimelineStepView` |

### F-13 再撮影での到達性

| 画面 | 再監査方法・現時点の制約 |
|---|---|
| ホーム設定 / 通知 / いいね / テーマ | canonical Maestroに操作・撮影を追加。設定は `settings-done` で閉じる。いいね=10、テーマ=11、設定=15、通知=16。 |
| TraitsDetail / UsageLimit / HabitSleep・Training・Wake / AuthRequired | 全Swift参照検索でViewの宣言しかなく、現在のアプリ導線から呼ばれていない。見た目のコードは変更したが、この修正で製品に新しい導線や強制課金/認証状態を追加しない。到達・実画面の再監査は未完了。 |
| RetentionOfferSheet | 購入キャンセル後に1回だけ到達する。通常の無料継続フローは購入を起動しないため、自動撮影には含めない。実StoreKitのキャンセル経路で別途確認が必要。 |
| PaywallPrimerStepView | `PaywallFlowContainer` のcaseは残るが、初期stepがplanSelectionでprimerへ戻す経路がない。F-13の指定どおり見た目を更新し、到達再監査は未完了として保持。 |
| Widget / Live Activity | WidgetBundleに登録済み。OSのウィジェット追加が別途必要。Live Activityはアプリ側の開始呼び出しがなく、Previewは更新したが実到達は未完了。アプリ内Maestro 01〜13では証明できない。 |
| 共有画像 | ホームの共有ボタンから既存rendererを呼ぶ。テーマ背景＋セリフを統一し、文字の4行制限を撤去。OS共有シート経由の画像保存・原寸チェックは別途必要。 |

### 設計判断と既存仕様との差異

- 年額中心＋代替プランシートを採用。小画面やアクセシビリティ文字サイズでは、1画面への押し込みより全文と操作導線を保つ。通常サイズでの1画面条件は新フレームで判定する。
- trial期間・価格はStore商品、対象可否はRevenueCatの判定を使う。対象不明時は「対象の方は」と明記し無料CTAを出さない。実装のない「必ず課金前に通知する」という保証を削除し、日程を開始日と請求開始日に整理した。
- 継続オファーの未取得時固定価格 `$44.99` と根拠のない `25% OFF` 表示を削除。実商品が取得できない場合は読み込み/再読込を表示する。
- `PlanSelectionStepView.swift` は購入UIの重複を除去し、同じ `PaywallVariantBView` に委譲。旧callerのanalytics flow名は保持する。
- 保存済みテーマのない旧いいねはsageMistへフォールバックする。ホームは日単位で保持し、時間帯だけでは再抽選しない。通知の宛先がある場合は通知文を優先する。
- `README.md` の旧「goal開始→preview→paywall→feed」説明を実際の新導線へ更新した。ローカルのLife Manager remote/ハード課金文書との相違は環境欄に記載。

## 検証・引き継ぎ

| 検証 | 結果 |
|---|---|
| `python3 -m unittest discover -s apps/mobile/anicca-ios/scripts/tests -p 'test_*.py'` | 36件中35件成功、1件skip（Swift未検出）。出力: `Ran 36 tests … OK (skipped=1)`。購入配線23件・録画失敗検出・設定signout等。これはiOS単体テスト成功ではない。 |
| `python3 apps/mobile/anicca-ios/scripts/tests/test_analytics_provider_contract.py` | PASS。新name screen、単一ホームのview計測、旧paywallの共通UI委譲経路へ期待値を更新。 |
| `python3 apps/mobile/anicca-ios/scripts/localization/check_hardcoded_swiftui_text.py` | PASS。共有画像のブランドURLは `Text(verbatim:)` と明示。 |
| `python3 apps/mobile/anicca-ios/scripts/localization/check_strings_parity.py` | **既存不備でFAIL**。HEAD比較: de/fr/pt-BR各missing1327・extra3、es missing104・extra5、en/ja差分なし。今回の新たなキー欠落0。変更/追加23キーは全6言語に存在し、引数数も照合する。既存数千行の翻訳補完は本委任の対象外。 |
| `bash -n apps/mobile/anicca-ios/scripts/run-soft-paywall-maestro.sh` | PASS。 |
| canonical Maestro YAML / フレーム番号検査 | YAML解析PASS、01〜13それぞれ1件の保存先を確認。Welcome/name/他プラン/再起動後の選択テーマ/設定/通知の補助フレームも追加。 |
| `git diff --check` | PASS。 |
| Swift / Xcode | `swiftc` / `swift` / `xcodebuild` なし。Swiftの型・参照は手動＋独立レビューで確認するが、コンパイル/実行成功は主張しない。構文parserの一時導入もネットワーク制約で不可。プロジェクト依存の追加なし。 |
| 新規・更新XCTest | `DailyAffirmationStoreTests.swift` 4件、`PaywallDisclosureTests.swift` 3件を追加。`OnboardingV2Tests.swift`、`PersonalizationPhase1Tests.swift`、standalone `OnboardingJourneyTests.swift` / `PaywallPackageSelectionTests.swift` を確定仕様へ更新。Xcode projectに新規2ファイルと従来未登録のOnboardingV2Testsを登録。**実行未完了**。 |
| 独立レビュー | Sol (`gpt-6.1-sol`, effort `high`) に実差分の読取専用レビューを委任。結果: blocking 0、新規不具合の指摘0。既存LifetimeのCTAがSubscribeになる1件を指摘され、買い切り専用CTA（全6言語）へ修正した。購入UI/文言のコードレビューでありコンパイルや実画面を保証しない。 |
| GitHub Actions build | **未実行・Muse待ち**。commit/push後、`.github/workflows/anicca-ios-build.yml` の `Build and unit tests (unsigned)`（`workflow_dispatch: run_maestro=false`）を実行し、run URL・対象SHA・結果を追記する。 |
| GitHub Actions Maestro | **未実行・Muse待ち**。別dispatch `run_maestro=true` が正本。01〜13新フレームと動画を同一SHAのartifactから取り出して再監査する。ビルドjobはこのdispatchでは実行されないため両方必要。 |
| 提出 / commit / push / merge / cleanup | すべて未実施。指定branch/worktreeに差分を保持し、Museが確認後にcommit/pushする。 |

canonical runnerは `frames/01-q1-goal.png` 〜 `frames/13-feed-after-relaunch.png` を保存する。
F-06の追加画面は00-welcome / 01b-name。08→09→13のquote本文一致、ホームのスワイプ不変、再起動後のsandWaveチェックもassertする。
旧v1.8系は履歴フローとして保持し、今回の正本は `maestro/v1.9.14/01-soft-paywall.yaml` とする。

独立レビューの判断保留は、Swiftコンパイル・実商品条件・小画面/大型文字/Widgetの実表示。いずれも未完了として上記CI/再撮影へ引き継ぐ。保留したminorや無視した指摘はない。

## 変更ファイル一覧

パスは `apps/mobile/anicca-ios/` からの相対。BOARDだけリポジトリrootから。

| ファイル | 差分 |
|---|---|
| `AniccaWidget/AniccaWidget.swift` | 変更 |
| `AniccaWidget/AniccaWidgetLiveActivity.swift` | 変更 |
| `AniccaWidget/WidgetShared.swift` | 変更 |
| `README.md` | 変更 |
| `aniccaios.xcodeproj/project.pbxproj` | 変更 |
| `aniccaios/DesignSystem/AppBackground.swift` | 変更 |
| `aniccaios/DesignSystem/AppTheme.swift` | 変更 |
| `aniccaios/DesignSystem/Components/CardView.swift` | 変更 |
| `aniccaios/DesignSystem/Components/PrimaryButton.swift` | 変更 |
| `aniccaios/Onboarding/InitialAffirmationExperience.swift` | 変更 |
| `aniccaios/Onboarding/NotificationPermissionStepView.swift` | 変更 |
| `aniccaios/Onboarding/OnboardingBibleViews.swift` | 変更 |
| `aniccaios/Onboarding/OnboardingFlowView.swift` | 変更 |
| `aniccaios/Onboarding/OnboardingProgressBar.swift` | 変更 |
| `aniccaios/Onboarding/OnboardingStep.swift` | 変更 |
| `aniccaios/Onboarding/PaywallPackageSelection.swift` | 変更 |
| `aniccaios/Onboarding/PaywallPrimerStepView.swift` | 変更 |
| `aniccaios/Onboarding/PaywallVariantBView.swift` | 変更 |
| `aniccaios/Onboarding/PersonalizedInsightStepView.swift` | 削除 |
| `aniccaios/Onboarding/PlanSelectionStepView.swift` | 変更 |
| `aniccaios/Onboarding/ProcessingStepView.swift` | 削除 |
| `aniccaios/Onboarding/RetentionOfferSheet.swift` | 変更 |
| `aniccaios/Onboarding/StruggleDepthStepView.swift` | 変更 |
| `aniccaios/Onboarding/StrugglesStepView.swift` | 変更 |
| `aniccaios/Onboarding/ValuePropStepView.swift` | 削除 |
| `aniccaios/Onboarding/WelcomeStepView.swift` | 変更 |
| `aniccaios/Resources/de.lproj/Localizable.strings` | 変更 |
| `aniccaios/Resources/en.lproj/Localizable.strings` | 変更 |
| `aniccaios/Resources/es.lproj/Localizable.strings` | 変更 |
| `aniccaios/Resources/fr.lproj/Localizable.strings` | 変更 |
| `aniccaios/Resources/ja.lproj/Localizable.strings` | 変更 |
| `aniccaios/Resources/pt-BR.lproj/Localizable.strings` | 変更 |
| `aniccaios/Services/AnalyticsManager.swift` | 変更 |
| `aniccaios/Services/LikedQuotesStore.swift` | 変更 |
| `aniccaios/Session/AuthRequiredPlaceholderView.swift` | 変更 |
| `aniccaios/Settings/HabitSleepFollowUpView.swift` | 変更 |
| `aniccaios/Settings/HabitTrainingFollowUpView.swift` | 変更 |
| `aniccaios/Settings/HabitWakeFollowUpView.swift` | 変更 |
| `aniccaios/Views/Feed/FeedRootView.swift` | 変更 |
| `aniccaios/Views/Feed/QuoteCardView.swift` | 変更 |
| `aniccaios/Views/Feed/SettingsSheet.swift` | 変更 |
| `aniccaios/Views/Feed/ShareImageRenderer.swift` | 変更 |
| `aniccaios/Views/Feed/ThemeStore.swift` | 変更 |
| `aniccaios/Views/Profile/TraitsDetailView.swift` | 変更 |
| `aniccaios/Views/UsageLimitModalView.swift` | 変更 |
| `aniccaiosTests/OnboardingV2Tests.swift` | 変更 |
| `aniccaiosTests/PersonalizationPhase1Tests.swift` | 変更 |
| `maestro/v1.9.14/01-soft-paywall.yaml` | 変更 |
| `scripts/run-soft-paywall-maestro.sh` | 変更 |
| `scripts/tests/OnboardingJourneyTests.swift` | 変更 |
| `scripts/tests/PaywallPackageSelectionTests.swift` | 変更 |
| `scripts/tests/test_analytics_provider_contract.py` | 変更 |
| `scripts/tests/test_paywall_selection_wiring.py` | 変更 |
| `docs/team/BOARD.md` | 変更 |
| `PHASE1-UIUX-FIX-NOTES.md` | 新規 |
| `aniccaios/Services/DailyAffirmationStore.swift` | 新規 |
| `aniccaiosTests/DailyAffirmationStoreTests.swift` | 新規 |
| `aniccaiosTests/PaywallDisclosureTests.swift` | 新規 |

## 欠陥 D-01〜D-16 の閉鎖状況

**閉鎖済み0件。全件未完了。** コード修正済みの候補も、新しい原寸フレームを委任元が目視するまで閉じない。

| 欠陥 | 対応項目・差分 | 状態 / 再監査対象 |
|---|---|---|
| D-01 全プランが見えない | F-02: 年額主表示＋全価格を持つ代替シート | 未完了（実装済み、07/14b待ち） |
| D-02 日程の文字切れ | F-02/F-04: 2行の日程と全文折り返し | 未完了（実装済み、07待ち） |
| D-03 通知設定の文字切れ | F-04: 短い見出し・折り返し・scroll本文 | 未完了（第2ラウンドの静かな時間説明を含む05再撮影待ち） |
| D-04 浮いたGMT | F-04: 独立ラベル削除 | 未完了（第2ラウンドの静かな時間説明を含む05再撮影待ち） |
| D-05 デザイン3系統 | F-01/F-13: 共通theme/componentへ統一 | 未完了（第2ラウンド新規17画面を含む全画面＋補助画面待ち） |
| D-06 無限フィードがホーム | F-05: 日単位で保持する単一表示 | 未完了（実装済み、09/12/13・スワイプ確認待ち） |
| D-07 導入なし | F-06: welcome復帰 | 未完了（実装済み、00待ち） |
| D-08 1画面2質問 | F-06: 名前を独立stepへ | 未完了（第2ラウンドも1画面1問。01/01b・01c/01d・02b〜h・03b〜i待ち） |
| D-09 Q3 CTAなし・形/余白の不統一 | F-01: 選択カードとContinueを統一、自動遷移撤去 | 未完了（実装済み、03待ち） |
| D-10 同じCTAで別の行き先 | F-07: 通知時間選択/今日の言葉を区別 | 未完了（実装済み、04/08待ち） |
| D-11 テーマの選択印なし | F-08: check＋枠＋selected trait | 未完了（実装済み、11/13b待ち） |
| D-12 保存先でテーマを失う | F-09: 保存時背景カード | 未完了（実装済み、10待ち） |
| D-13 月額換算なし | F-03: 年額主表示に従属する換算 | 未完了（実装済み、07＋他プラン切替待ち） |
| D-14 初回ホームの言葉が異なる | F-10: 介入quoteをseed | 未完了（実装済み、08→09→13一致待ち） |
| D-15 許可画面の左右余白 | F-01/F-04: 共通24pt insetと折り返し | 未完了（第2ラウンドの有効予定表示を含む06再撮影待ち） |
| D-16 ストア1枚目が到達画面でない | F-11: ストア素材の別作業 | 未完了（今回のコード範囲外） |

## 第2ラウンド — Issue #9353（2026-11-14）

確定仕様: 本会話の委任第2ラウンド（18:30 JST）。開始 HEAD `1f26b0f42`。指定の既存 worktree/branch に未コミット差分を残す。独立レビュー・commit/push は委任元が担当し、ASC 操作はしない。

### 実装計画と検証対象

- [x] `PersonalizationPhase1Tests.swift`: モジュール優先順・最大2・未選択非提示、重い気分のgentle固定、静かな時間の境界/明示時刻優先、旧profile/rawValue/判断点互換を先に追加。
- [x] `Models/AdaptiveOnboarding.swift` / `PersonalizationProfile.swift` / `UserProfile.swift`: 安定ID、欠損状態、DOB端末内保存、分析用snapshot、提案/抑制規則。既存の保存・質問カード・選択器の形を再利用。
- [x] `OnboardingStep.swift` / Flow / Progress / `AdaptiveQuestionStepView.swift`: Q-A〜Iとpainモジュールの適応旅程、1画面1問、再開。睡眠は理由・就寝・起床に分割。Q-Gは経験と不適合を分けて推測を避ける。
- [x] Selector / catalog / AppState / recorder: 回答を実際の文体・強度・候補除外/加点・通知提案へ接続。名前/DOBをsnapshot/同期へ渡さない。
- [x] 全6言語、新画面のMaestroフレーム、既存00〜16保持、READMEと本記録/欠陥表を更新。
- [ ] Python検査・差分検査、利用可能ならSwift/Xcode/Maestro実行。実行不能は未完了として明記し、成功と混同しない。


重点: 旧v8/name=9再開、途中終了後の保存、未提示回答の残存、夜跨ぎ静かな時間/全時間抑制、探索でも文脈/強度制約を破らないこと、名前とDOBの漏えい、選択時の確率とsnapshotの一致。

### 環境と初期証拠

- Git root `/home/hatch/workspace/life-manager-phase1`、common dir `/home/hatch/workspace/life-manager/.git`、origin `https://github.com/Daisuke134/anicca.git`、branch `claude/phase1-personalized-onboarding`。開始時クリーン。
- `bash scripts/verify-source-boundary.sh`: exit 2（Life Manager 固定パス）。今回の明示指定と実origin一致を優先し、スクリプトは変更しない。
- Astra Advisor は公開ツールにない。`using-superpowers`（Codex reference含む）、`brainstorming`、`writing-plans`、`executing-plans`、`using-git-worktrees`、`dispatching-parallel-agents`、`test-driven-development`（writing-good-tests含む）のインストール済み7.0.1手順を実読。仕様確定・人間手順不要・コミット不要という直接指示を優先する。
- baseline Python unittest: 36件、35成功、Swift未検出による1skip。Swift/swiftc/xcodebuildは未検出、Maestroのみ存在。SwiftのRED/GREENとiOS実画面はこのLinuxで証明できない。
- 研究原本: `Daisuke134/anicca-ops` の指定4ファイルを接続先と `/tmp/ops-check/files/` で確認。対応表 blob `cbd66d74dc19e829d420322b68c3a930c3ff6085`、simulation spec `a3ad3bb45214cfe65773c31e59531212e1706ed6`、products map `29b5d3419cf4842119fd1aa6f34becfdab87583a`、Humans& `6ec8f4013cd5c960887c7129eee6a7a83341153f`。回答は本人履歴とともに条件づけの材料とする。今回の質問追加だけでalgorithmic fidelity成立・シミュレーション検証済みとはしない。

### 質問 → 合成ユーザーの材料 → 製品の変化

保存先は `UserProfile.personalization.adaptiveAnswers`（`values[安定ID]`、DOBだけ `birthDate`）。既存のname/goal/pain/frequency/時刻も同じ `personalization` に保持する。`AdaptiveOnboarding.swift` が語彙・制約・公開snapshot境界、`AdaptiveQuestionStepView.swift` が全新画面を担当する。旧profileの別UserDefaults keyから移行し、UserProfileの保存に成功した後で旧keyを除去する。新書込と読み出しは `UserProfile` に一本化した。AppStateの別プロフィールはcomputed accessorとし、signout時に旧回答/DOBのメモリコピーが残らない。

| 委任の番号 | 質問・安定ID / step rawValue | 合成ユーザーのどのデータか | 実装で変わること |
|---|---|---|---|
| Q-A | 生年月日または星座 `birth_context` / 10 | プロフィール属性。DOB入力時の年齢層、本人が選んだ星座。未入力の年齢・星座を推測しない | 任意のDOB/星座選択またはskip。DOBの月/現在の星座期間にだけ `birthday_season` 候補を許可。性格・能力を占わない。DOB自体は端末内のみ、snapshot/同期には `age_band` の列挙IDだけ |
| Q-B | 今日の気分 `mood_baseline` / 11 | 状態遷移モデル・反応シミュレーションの開始状態 | very_heavy/heavyならpreview/介入の候補はgentle限定。頻度のsupportiveより穏やかな方を採用 |
| Q-C | 信じたい言葉 `belief_themes` / 12 | 望む信念のテーマ分布 | self_trust/inner_peace/courage/forgiveness/gratitudeタグを加点。desired_state主カテゴリの優先を維持 |
| Q-D | 言葉のトーン `tone` / 13 | 同じ刺激への反応差を条件づける表現の好み | gentle/direct/poetic/practicalの明示文体タグに一致する候補だけを選ぶ |
| Q-E | 生活の文脈 `life_context` / 14 | 仕事・ケア・学業・転機の属性、セグメント軸 | 必要文脈タグが回答に無い候補を除外。work/parenting等を全員へ出さない |
| Q-F | 一日の錨 `routine_anchors` / 15 | 受容性の時間窓 | waking/commute→08:00、lunch→12:30、bedtime→21:30を初期提案。明示済み時刻は上書きしない |
| Q-G | これまで試したこと `prior_attempts` / 16 | 介入経験の履歴 | 実際に試した手段の候補だけを許可。first_timeは他項目と排他 |
| Q-G補足 | 合わなかった手段 `prior_helpfulness` / 26 | 介入の不適合履歴。経験と失敗を混同しない | 試した手段のみを選択肢にする追加1問。first_timeなら非提示。選択手段のmethodsタグ付き候補を除外 |
| Q-H | 始める理由 `start_reason` / 17 | 動機・緊急度、継続率モデルの条件 | overwhelmed/new_chapter/recommended/curiousに合う文面を加点、他の動機前提の文は除外。危機を煽らない |
| Q-I | 静かな時間 `quiet_hours` / 18 | 不応答・非受容性の制約 | 06–12、12–18、18–22、22–06の複数選択またはnone。半開区間・夜跨ぎ。明示時刻でも衝突は抑制。全枠を遮る場合は送信予定0を同期 |
| M-stress | 重くなる場面 `stress_trigger` / 19 | トリガーの文脈分布 | 回答に合うstress/grounding候補だけを許可し加点。morning/night/work候補に時間帯タグ |
| M-anxiety | 不安対象 `anxiety_target` / 20 | 未来・評価・健康・お金への不安軸 | 対象一致を加点、不一致を除外 |
| M-self-doubt | 自責場面 `self_criticism` / 21 | 内なる批判のテーマ | 仕事・人間関係・見た目・子育てに対応するself_trust/self_love候補の適合・加点 |
| M-procrastination | 回避対象 `avoidance_task` / 22 | 回避パターン | 仕事・返信・家事・自分の計画ごとに具体的な2分以内の一歩を選ぶ |
| M-sleep | 眠れない理由 `sleep_reason` / 23、平日の就寝 `bedtime` / 24、起床 `wake_time` / 25 | 睡眠文脈と生活リズムの近似。正確なクロノタイプ診断ではない | 夜だけrest候補を許可。22時前の就寝は早い夕方枠を提案。明示時刻・錨がある場合はそちらを優先。起床目安はsnapshotに保持 |

`unknown` はスキップ/未回答、`not_asked` は分岐非提示を示す。生年月日から星座を補完せず、星座から年齢を補完しない。任意質問の初期ピッカー値は、操作されるまで保存できない。通知許可の allowed/denied/skipped も保存・snapshotする。上記のデータだけで本人の反応を高精度に予測できると主張しない。実測反応履歴とAFゲートは研究側の契約を維持する。

### 適応規則・保存・テストの対応

全て `aniccaiosTests/PersonalizationPhase1Tests.swift`（既存XCTest target登録済み）に追加。下記は**テスト実装の一覧であり、Xcode実行成功ではない**。

| 規則 | 実装場所 | 固定するテスト |
|---|---|---|
| painのみで深掘り決定、提示順stress→anxiety→self_doubt→procrastination→sleep、上限2 | `OnboardingStep.deepDiveSteps` / `journey`、Flowの `nextStep` | `test_adaptiveModules_followPresentationOrderAndLimitToTwo`、`test_adaptiveJourney_insertsOnlySelectedModulesImmediatelyAfterPain` |
| 新raw値10〜26、旧0〜9/v6/v7を保持、不適合な保存済みmoduleはfrequencyへ | `OnboardingStep.resumableStep`、AppStateのstep versionは8維持 | `test_newRawValuesPreserveRoundOneAndLegacyMigration`、既存 `OnboardingV2Tests`、standalone `OnboardingJourneyTests` |
| 気分×頻度はgentle優先、探索も同じ制約 | `PersonalizationRules.intensity`、`PersonalizedNudgeSelector.isEligible` | `test_heavyMoodAlwaysChoosesGentlerIntensity`、`test_explorationCannotEscapeHeavyMoodToneOrContextConstraints`、`test_heavyMoodExcludesSupportiveCandidateButLightMoodCanChooseIt` |
| 明示時刻＞提案、静かな時間は常に抑制、別時刻への暗黙移動なし | `initialSlots` / `effectiveSlots` / `isQuiet`、ReminderScheduleStepView、通知許可画面、`deliveryPayload` | `test_quietHoursOverrideExplicitTimesWithoutAddingReplacements`、`test_quietHoursUseHalfOpenRangesAndWrapMidnight`、`test_anchorsOnlyProposeWhenNoExplicitScheduleExists`、`test_sleepProposalUsesBedtimeOnlyUntilExplicitChoice` |
| 安定ID/欠損/個人情報遮断、旧profileと判断点JSONL互換 | `answerSnapshot` / `deliveryPayload`、UserProfile Codable、AppState migration、DecisionPointRecorder | `test_skippedAndUnaskedAnswersRemainMissingAndPrivateValuesNeverReachSnapshot`、`test_roundOneProfileDecodesWithoutNewFieldsAndUserProfileKeepsAnswers`、`test_decisionSnapshotRoundTripsAndOldRecordStillDecodes`、`test_deliveryPayloadSuppressesQuietSlotsAndNeverExportsNameOrBirthDate` |
| 文脈・対象・不適合手段の除外、belief加点 | `AdaptiveAffirmationCatalog`、Selector | `test_selectorExcludesWrongAnxietyTargetAndUnhelpfulMethods`、`test_beliefThemeAddsWeightWithoutReplacingPrimaryGoal` |
| 試した経験≠失敗、noneの排他、季節≠性格推定、動的progress | `OnboardingQuestion.options`、`AdaptiveAnswers`、ProgressBar | `test_priorExperienceDoesNotImplyFailureAndOnlyTriedMethodsAreFollowUps`、`test_noneSelectionCannotCoexistWithContextOrQuietHours`、`test_milestoneIsCalendarContextAndSkippedBirthNeverInfersIt`、`test_progressIncludesOnlyTheActiveQuestions` |
| 連続回答の同期取りこぼし防止 | `ProfileSyncBuffer` / `ProfileSyncService.performSync` | `test_profileSyncBufferKeepsAnswersArrivingDuringAnOlderSend` |

選択policyは `rule_v2_adaptive`、質問/回答snapshotはversion 2、analytics flowは `adaptive-onboarding-v2`。49件の明示タグ候補（45gentle/4supportive）を6言語で追加し、旧利用者は旧候補を維持する。新回答のある利用者では、タグ不明の旧文を強度/文脈適合と推測して使わない。既存ε=0.1と実割当確率の記録は保持。分析payloadの `answer_ids` は `axis:enum_id` の配列、ローカル判断点には辞書snapshotを保存。DOB/名前のオブジェクトを分析へ渡さない。

同期の既存問題: 送信Aのawait中に回答Bが `pendingSync` を更新しても、A成功時の `pendingSync=nil` がBを消していた。送信前にbufferから取り出し、後続回答を順に排出する構造へ変更。失敗時も新しい回答を古い送信内容で上書きしない。静かな時間と通知選択を最後まで同期するための必要な修正であり、サーバー送達済みの証拠ではない。

### フレーム対応表（撮影経路の実装、画像生成は未実行）

`frames/` 以下、全て `.png`。既存00〜16の保存先と画面は変更していない。02のmainはsleep/anxietyを選択、03は既存のfrequencyである。新規画面の監査番号は新たなD番号を作らず、既存D-05（統一）/D-08（1画面1問）/D-09（選択とCTA）に対応させる。

| 新規ファイル名 | 画面 | 委任/監査対応 |
|---|---|---|
| `01c-birth-context.png` | 任意の生年月日/星座 | Q-A、D-05/08/09 |
| `01d-mood-baseline.png` | 気分 | Q-B、D-05/08/09 |
| `02b-anxiety-target.png` | 不安の対象 | M-anxiety、D-05/08/09 |
| `02c-sleep-reason.png` | 睡眠の理由 | M-sleep、D-05/08/09 |
| `02d-bedtime.png` | 平日の就寝 | M-sleep、D-05/08/09 |
| `02e-wake-time.png` | 平日の起床 | M-sleep、D-05/08/09 |
| `02f-stress-trigger.png` | 重くなる場面 | M-stress、D-05/08/09 |
| `02g-self-criticism.png` | 自責の場面 | M-self-doubt、D-05/08/09 |
| `02h-avoidance-task.png` | 先延ばしの対象 | M-procrastination、D-05/08/09 |
| `03b-belief-themes.png` | 信じたい言葉 | Q-C、D-05/08/09 |
| `03c-tone.png` | 文体 | Q-D、D-05/08/09 |
| `03d-life-context.png` | 生活の文脈 | Q-E、D-05/08/09 |
| `03e-routine-anchors.png` | 一日の錨 | Q-F、D-05/08/09 |
| `03f-prior-attempts.png` | 試したこと | Q-G、D-05/08/09 |
| `03g-prior-helpfulness.png` | 合わなかった経験 | Q-G補足、D-05/08/09 |
| `03h-start-reason.png` | 始める理由 | Q-H、D-05/08/09 |
| `03i-quiet-hours.png` | 静かな時間 | Q-I、D-05/08/09 |

Maestroは補助flow（stress/self_doubt、procrastination）→main flow（anxiety/sleep）を録画。mainはsleepを先に選択してもanxietyが先に出ることをassertする。補助flowもself_doubtを先に押してstressが先に出ることをassertする。未選択moduleの非表示も検査する。全体は回答によりfirst interventionまで20〜24画面。I amの25ステップ/約2分33秒は委任の実測値を設計の基準として採用したが、本実装の所要時間は**未測定**。

### 変更しない項目・未検証の境界

- 課金価格・ソフトペイウォール・購入処理・ASC素材/提出を変更しない。既存D-01〜D-16表を継続し、今回も新しい実フレームの目視までは閉じない。
- 既存翻訳欠落の大量補完は対象外。今回の質問106キーと言葉49キーは全6言語を揃える。
- APNsは既存のremote-only経路を維持する。iOSからは静かな時間を除いた時刻と0を含む回数を送る。サーバー側の受理・0件予定の尊重・実際の配信抑制はこのcheckoutに送信側実装がなく、外部readback未取得。端末のpayload検証を配信完了とは扱わない。
- シミュレーターでのSwiftコンパイル、XCTest、Maestro再撮影、長文/大型文字の目視、独立レビューは未完了。委任元の別エージェントによるレビューと既存CIでの検証に渡す。コンパイル成功とは記載しない。
- 文書とコードの相違は第1ラウンド欄を継承。加えてREADMEのXcode Cloud節はLife Manager remote表記が残り、この委任のoriginはAnicca。release構成は未検証かつ今回変更対象外のため書き換えない。

### 第2ラウンドの検証・引き継ぎ結果

| 実行/確認 | 結果 |
|---|---|
| Python既存suite `python3 -m unittest discover -s apps/mobile/anicca-ios/scripts/tests -p 'test_*.py'` | 36件、35成功、Swift依存1skip。最新の再実行ログは `/tmp/anicca-round2-final-tests.log`。iOSテストとは区別 |
| `test_analytics_provider_contract.py` | PASS。新規17screenのinventoryも追加 |
| `check_hardcoded_swiftui_text.py` | PASS |
| 新規ローカライズ照合 | 全6言語、質問106キー/候補49キー、キー集合・構文・候補ID一意を実ファイルから確認。モデルの質問/選択肢から必要キーを列挙して欠落0 |
| `check_strings_parity.py` | 既存不備でexit 1。HEAD比で差分不変: de/fr/pt-BR各missing1327 extra3、es missing104 extra5、ja missing0 extra0。今回追加による欠落0 |
| Maestro YAML、shell | 3 YAML parse、既存20フレーム名保持＋新規17フレーム重複なし、`bash -n scripts/run-soft-paywall-maestro.sh` PASS。録画ゲートの既存6件もPython suiteで成功 |
| `git diff --check` | PASS |
| 新規XCTest | `PersonalizationPhase1Tests.swift` に21件追加。旧journey期待値/ProgressBar/standalone旅程テストを新仕様へ更新。**Swift未検出でRED/GREEN未実行** |
| iOSビルド・Maestro実画面 | **未実行**。`xcodebuild -version` はexit 127、`swift/swiftc/xcrun` 未検出。既存CIの同一SHAに対しbuild/unit dispatchとMaestro dispatchを別々に実行する必要がある。撮影済み画像はない |
| 独立レビュー | 本委任の指定どおり委任元が別エージェントで実施。こちらの補助エージェントは資料調査・翻訳・候補文・Maestro実装であり、独立レビュー扱いにしない。モデルはnative harness継承、CLIモデル指定なし（Opus等とは称さない） |
| commit/push/merge/ASC/worktree cleanup | 全て未実施。HEAD `1f26b0f42` のまま、指定branch/worktreeに差分を保持 |

`verification-before-completion`、`finishing-a-development-branch`、同期不具合について `systematic-debugging` も実読。利用可能な検査の成功と、未実施のSwift型検査/実画面/外部readbackを分けて引き継ぐ。既存Xcode projectのアプリ側は `PBXFileSystemSynchronizedRootGroup` のため、新Swift/ローカライズファイルは自動所属。新XCTestは既に登録されたテストファイル内へ追加している。
