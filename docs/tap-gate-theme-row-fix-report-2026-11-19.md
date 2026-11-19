# テーマ行の露出判定修正 — 2026-11-19

指定ブランチ内のテスト修正。**3ケースのネイティブ合格は未確認**。push・merge・ASC提出なし。

## 診断と一次証拠

- 対象: `Daisuke134/anicca`、`codex/tap-fix-1100-port`、変更前HEAD `734ad64fbc26969e2867626f1035f19f0be952fc`。1.10.1 / 836を維持。
- [失敗run 44498670650](https://github.com/Daisuke134/anicca/actions/runs/44498670650)。artifact ID `14517378349`、名前 `onboarding-normal-taps-734ad64fbc26969e2867626f1035f19f0be952fc`、200094146 bytes、SHA256 `dd809b09071fbe796008b1c31bb1c230f3c191a73b35edca276192637ce76de0`。
- ダウンロード先: `/home/hatch/workspace/tmp_cache/codex-tmp/tap-gate-44498670650.zip`。最初の `gh run download` はunexpected EOF。APIリダイレクト先をcurlで取得し、ZIP展開に成功。`/tmp`は使用していない。
- [元ログ抜粋](evidence/tap-gate-theme-row-2026-11-19/original-failure.txt): centerケースはテーマ画面に到達し、ScrollView `{{0.0, 154.7}, {440.0, 671.3}}` に8回のswipeDown。198.047秒で `Could not expose the complete row`。Sand Waveへのタップには到達していない。leading/trailingケースは未実行。
- xcresult Dataを既存libzstdで展開。録画オブジェクト `0~OxOf4mjvMbqB4LVg_E4Y9T4JNmlHcqxlCRJjR0OXQpoh1utYBuQBapb2fcMMmHVxkpU-PISw41oA6CW3x4ZCzA==` はQuickTime、194.686667秒。ffmpeg `-sseof -0.2 -frames:v 1` で[失敗直前画像](evidence/tap-gate-theme-row-2026-11-19/failure-video-final-frame.png)を抽出して目視確認。両カード全体とContinueが表示され、覆うUIはない。終端3秒前の画像との比較でもスワイプによるバウンスからの戻りを確認した。

根本原因はテスト側の余白条件。`SettingsSheet.swift` の `ThemePickerView` は2列、カード高220pt、grid外側padding16pt。onboardingでは `ThemeID.isFree` のSand Wave / Sage Mistだけが表示され、1段で収まる。通常位置では先頭カードの上端はviewport上端+16ptだが、旧 `select()` はviewportを上下20pt縮めてから**行全体**の包含を要求するため、上端4pt分が条件外になる。短い内容へのswipeDownはバウンスするだけで、静止後に条件を満たせない。録画ではカードの全体表示を確認できる。元ログにはカードの正確なaccessibility frameがないため、その座標の実測値まで断定していない。

## 変更

`apps/mobile/anicca-ios/aniccaiosUITests/OnboardingTapE2ETests.swift` の `select()` のみ。

1. `scroll.frame.intersection(app.frame)` を実際の可視領域として使う。追加20pt insetを除去。
2. 空のviewport/行を拒否し、行**全体**の包含と `isHittable` は維持。画面外の行をそのままタップしない。
3. 最大8回の通常スワイプを維持し、8回目の後も判定する。従来は8回目直後に無条件失敗していた。
4. 露出失敗時に座標・hittable値とスクリーンショットを保存し、return。失敗後のタップなし。
5. 既存の通常座標タップ1回、enabled/hittable待機、selected確認、3通りの横位置、全フローと再起動後の保存確認を維持。

アプリのpaddingをテストに合わせて増やす変更は不要と判断。新しい依存、長押し、再タップ、強制タップ、ルート/課金バイパスは追加していない。

## 他の選択行のソース監査

| 対象 | 全選択肢を生成する実装と露出条件 |
|---|---|
| 目標5行 | `InitialAffirmationExperience.swift / AffirmationGoalStepView`。共通OnboardingPage、ラベルpadding18、contentShapeあり |
| 適応質問19種 | `AdaptiveQuestionStepView.optionRows` と `AdaptiveOnboarding.OnboardingQuestion.optionIDs/options`。focus、birthの12星座、mood、belief、tone、life、routine、prior、start、quiet、およびstress/anxiety/selfCriticism/avoidance/sleep/bedtime/wake/priorHelpfulness。共通OnboardingPage、可変高テキスト、全行同じpadding18とcontentShape。priorHelpfulnessの候補フィルタも同じ行構造 |
| pain全5行 | `StrugglesStepView`。共通OnboardingPage、padding18、contentShapeあり |
| depth全4行 | `StruggleDepthStepView`。共通OnboardingPage、padding18、contentShapeあり |
| テーマ全2枚 | `ThemePickerView`。独自ScrollView内padding16、今回の余白不整合の対象。設定画面の有料テーマも同じgridだがonboardingの対象外 |
| アイコン全4行 | `OnboardingIconStepView`。共通OnboardingPage、画像64pt+padding12、contentShapeあり。既存ゲートは既定アイコンを直接tapし、OSアイコン変更ダイアログを避ける |
| リマインダー全preset slotと全frequency | `InitialAffirmationExperience.swift / ReminderScheduleStepView`。共通OnboardingPage、padding14、contentShape/selected traitあり。quiet hoursによる無効化は仕様 |

共通 `OnboardingPage` はcontentの縦padding20、横24、ScrollViewとbottom safeAreaInsetでフッターを分離する。ほかに同じ16対20の不整合は見つからなかった。micro preview・widget・通知許可は選択行一覧ではなくCTA。birthのdate pickerも別の入力形式。

これは全行実装の**ソース監査**であり、全候補・全言語・Dynamic Type・小画面での実測合格ではない。既存3ケースは全deep-dive分岐を通るが全候補をタップするテストではない。特大文字で行がviewportより高くなる場合やスワイプで行を飛び越える場合は引き続きゲートが失敗する。今回その判定は緩めていない。

## 検証と残作業

- 既存の失敗centerケースを回帰ケースとして使用。変更前のネイティブREDは上記run、変更後のネイティブGREENは未取得。
- `python3 -m unittest discover -s apps/mobile/anicca-ios/scripts/tests -p 'test_*.py'`: **54件、52成功、2 skip**（Swift不在）。[出力](evidence/tap-gate-theme-row-2026-11-19/python-tests.txt)。構造検査/スクリプト検査でありiOS動作証明ではない。
- `bash apps/mobile/anicca-ios/scripts/onboarding-ship-gate.sh`: exit69、macOS/Xcode/Simulatorが必要。VMにはswiftもxcodebuildもない。
- `git diff --check`: PASS。
- `requesting-code-review` に基づく独立read-only reviewer `/root/review`: 0 findings / 0 blocking。包含、最終スワイプ後判定、単回タップ、他行実装をレビュー。モデルは親設定継承、CLIモデルreadbackなし。Swiftコンパイル/実測はレビューでも未確認。
- 次の必要な証拠: この修正commitに対してmacOSで `ios-onboarding-ship-gate.yml` を実行し、center / leading / trailing全3件とpaywall→feed→relaunchを確認すること。今回は最優先の「do not push」に従い、workflow dispatchも未実行。旧remoteの再実行では修正検証にならない。

## 手順・境界

読んだスキル: `/home/hatch/.agents/skills/{using-superpowers,systematic-debugging,test-driven-development,verification-before-completion,requesting-code-review,finishing-a-development-branch}/SKILL.md` と `test-driven-development/writing-good-tests.md`。REVIEW.mdとdocs/teamのREADME/RULES/OWNERSHIP/WORKFLOW/BOARDも確認。Astra Advisorは公開ツールにないため使用していない。

Git rootは指定worktree、common dirは `/home/hatch/workspace/life-manager/.git`、originは `https://github.com/Daisuke134/anicca.git`。`bash scripts/verify-source-boundary.sh` は古いcanonical root `/home/hatch/Projects/life-manager-main` がないためexit2。Life Managerのorigin限定・別worktree作成・push・チーム返信ファイルの規定は今回の明示overrideで置き換える。guard本体は変更していない。チーム文書のハードペイウォール記述と現在の任意購入→無料feedの実装も不一致だが、本件では既存動作を維持。現在のbranchにコミットしてworktreeを残し、anicca-opsへの書き込みは行わない。
