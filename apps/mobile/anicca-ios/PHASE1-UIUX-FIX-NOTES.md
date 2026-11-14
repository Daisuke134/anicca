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
| D-03 通知設定の文字切れ | F-04: 短い見出し・折り返し・scroll本文 | 未完了（実装済み、05待ち） |
| D-04 浮いたGMT | F-04: 独立ラベル削除 | 未完了（実装済み、05待ち） |
| D-05 デザイン3系統 | F-01/F-13: 共通theme/componentへ統一 | 未完了（実装済み、全画面＋補助画面待ち） |
| D-06 無限フィードがホーム | F-05: 日単位で保持する単一表示 | 未完了（実装済み、09/12/13・スワイプ確認待ち） |
| D-07 導入なし | F-06: welcome復帰 | 未完了（実装済み、00待ち） |
| D-08 1画面2質問 | F-06: 名前を独立stepへ | 未完了（実装済み、01/01b待ち） |
| D-09 Q3 CTAなし・形/余白の不統一 | F-01: 選択カードとContinueを統一、自動遷移撤去 | 未完了（実装済み、03待ち） |
| D-10 同じCTAで別の行き先 | F-07: 通知時間選択/今日の言葉を区別 | 未完了（実装済み、04/08待ち） |
| D-11 テーマの選択印なし | F-08: check＋枠＋selected trait | 未完了（実装済み、11/13b待ち） |
| D-12 保存先でテーマを失う | F-09: 保存時背景カード | 未完了（実装済み、10待ち） |
| D-13 月額換算なし | F-03: 年額主表示に従属する換算 | 未完了（実装済み、07＋他プラン切替待ち） |
| D-14 初回ホームの言葉が異なる | F-10: 介入quoteをseed | 未完了（実装済み、08→09→13一致待ち） |
| D-15 許可画面の左右余白 | F-01/F-04: 共通24pt insetと折り返し | 未完了（実装済み、06待ち） |
| D-16 ストア1枚目が到達画面でない | F-11: ストア素材の別作業 | 未完了（今回のコード範囲外） |
