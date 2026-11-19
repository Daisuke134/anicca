# Gate 44514262070: paywall close の診断

判定: **TEST BUG**。テストはアプリに存在しない `feed-scroll` ScrollView を待っていた。現行ホームの主要要素 `feed-today` を閉じた直後と通常再起動後に検証するよう修正した。アプリの変更は不要。

## 観測証拠

対象 head: `181e572324e951252525e1790d6b2d5c38fb00fc`、branch: `codex/tap-fix-1100-port`。
入力ログ: `~/workspace/tmp_cache/gate44514/dl/art/20261119T112413Z-2305/testFullOnboardingCenterTaps.log`。

- 全質問と `theme-sandWave` を通過、t=228.57s に `paywall-plan-cta` を検索。
- t=230.93s: `Tap "paywall-close-button" Button[0.50, 0.50]`。
- t=231.07s: `Synthesize event`。
- t=231.79s: `Waiting 20.0s for "feed-scroll" ScrollView to exist`。
- t=251.87s に失敗時のAX snapshot要求、OnboardingTapE2ETests.swift:96 の assertion 失敗。256.297秒、1件失敗。

このログ単独ではホーム到着の実行時証明にはならない。ただしソースとの照合で、この期待値は正常にホームへ到着しても必ず失敗すると確認できる。

## アプリの実際の経路

パスは `apps/mobile/anicca-ios/` 起点。

1. `aniccaios/Onboarding/OnboardingBibleViews.swift:120` の閉じるボタンは `Button(action: onDismiss)`。IDは `paywall-close-button`。購入操作は呼ばない。
2. `Onboarding/OnboardingFlowView.swift:112` が `onDismiss: advance` を渡す。`advance()` の `.paywall` 分岐は `markOnboardingQuestionsCompleted()`、完了analytics、`completeFreeOnboarding()` を実行。
3. `completeFreeOnboarding()` は `appState.markOnboardingComplete()` を実行。`AppState.swift:180` は `isOnboardingComplete = true` と UserDefaultsへの保存、保存された途中stepの削除を行う。起動時は同じキーから完了状態を読み込む。
4. `ContentView.swift:20` のルーターは未完了時のみ `OnboardingFlowView`、完了後の signedOut / signedIn はともに `FeedRootView` を表示。
5. `Views/Feed/FeedRootView.swift:184` の主要デッキは `VerticalPager`、IDは `feed-today`（190行）。カードが空なら出ないため、ホームの空枠だけでは合格しない。補助要素は `feed-themes`、`feed-settings`、`feed-daily`、`feed-saved`、`feed-reminders`。カード本文は `quote-text`。
6. `VerticalPager.swift` は `UIViewControllerRepresentable` の `UIPageViewController`。内部UIScrollViewの存在と、IDがScrollView型に公開されることは別である。`feed-scroll` はアプリ実装全体に存在せず、変更前のE2Eテスト2箇所だけが参照していた。

## 中間画面の有無

`Onboarding/OnboardingStep.swift:69` の末尾は `.planReveal, .nudgeTimes, .notifications, .paywall`。最初の言葉のrevealはpaywallより前。`FirstInterventionStepView` は定義されているが現行フローから呼ばれない。paywallのprimerも閉じた後のステップではなく、コンテナの初期状態は `.planSelection`。

必須の追加タップはない。ルーターにはプロフィールbootstrap中の `ProgressView` と signingIn時の処理画面があるため、条件次第で一時的に待つ可能性はあるが、revealを自動で飛ばす処理や追加タップ、待ち時間延長は不要。20秒のホーム待機を維持。

## 修正と回帰防止

既存の成功経路として `maestro/v1.9.14/01-soft-paywall.yaml:239` も close 後に `feed-today` を待っている。この既存契約を再利用。

- `OnboardingTapE2ETests.swift` の到着・再起動の両方を `app.descendants(matching: .any).matching(identifier: "feed-today").firstMatch` の存在検証へ変更。
- 同じ両地点で paywall-close と welcome CTA の不在を検証。
- 3ケース、購入商品のロード確認、単回の通常center tap、スクリーンショット、通常再起動、20秒の上限を維持。ルートや課金の迂回は追加していない。
- Python契約テストの旧マーカーを更新し、到着・再起動両地点の検査が実装のホームIDに一致することと、不在検証が残ることを確認する回帰検査を追加。

## 検証

- 変更前: `python3 -m unittest discover -s apps/mobile/anicca-ios/scripts/tests -p 'test_*.py'` → 54件、52成功 / 2skip。
- RED: 契約テストを先に更新して `test_onboarding_ship_gate.py` を実行。旧IDと両地点の期待値不一致で失敗。
- GREEN: 同じ全Python構造テスト → 55件、**53成功 / 2skip**。skipは既存のSwift依存。構造検査はネイティブE2E合格の証明ではない。
- `git diff --check` → 合格。
- `bash apps/mobile/anicca-ios/scripts/onboarding-ship-gate.sh` → macOS / Xcode / iOS Simulator不在で実行不可。修正後のコンパイル・3ケースのnative GREENは未確認。次のmacOS gateで確認が必要。
- REVIEW.mdに従うセルフレビュー: 0 findings、tests/docsのみのLow risk。独立レビュー実施は主張しない。

## 手順・境界・不一致

使用手順: インストール済み `superpowers/7.0.1/skills/` の using-superpowers、systematic-debugging、test-driven-development（writing-good-tests含む）、verification-before-completion、finishing-a-development-branch。チーム README/RULES/OWNERSHIP/WORKFLOW/BOARD、REVIEW.mdを参照。Astra Advisorは公開されていない。既存のE2EとPython unittestを再利用し依存追加なし。

Git rootは `/home/hatch/workspace/anicca-wt-tap-fix-1100-port`、common Git directoryは `/home/hatch/workspace/life-manager/.git`、originは `https://github.com/Daisuke134/anicca.git`。事前のLife Manager向け文書と異なる。source-boundaryは旧canonical root `/home/hatch/Projects/life-manager-main` 不在で失敗。今回の明示overrideに従い指定worktree/branchで作業し、guardやremoteは変更しない。

ほかの既存文書不一致: チーム文書のhard-paywall指定は実装のfree completionと異なる。AppStateの完了処理コメントは旧handler名を参照し、質問完了コメントは旧paywall再開動作を説明しているが、現行OnboardingFlowViewのonAppearは質問完了ならfree completionする。コードの現行動作に従った。

指定ブランチへローカルcommitし、worktreeを維持。push / merge / release / ASC操作なし。コミットはこのレポートを含むGit履歴から特定可能。
