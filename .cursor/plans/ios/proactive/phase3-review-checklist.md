# Phase 3 実装レビューチェックリスト

**目的**: 実装後に抜け漏れがないかを確認するためのドキュメント
**作成日**: 2026-01-18

---

## 1. ProblemType.swift のローカライズ

### 1.1 positiveButtonText

**AS-IS**: 13個の問題タイプのポジティブボタン文言が日本語でハードコードされている。英語ユーザーには日本語が表示される。

**TO-BE**: `String(localized:)` を使用してローカライズキーを参照する。日本語と英語の両方で適切な文言が表示される。

**確認項目**:
- [ ] `positiveButtonText` が `String(localized: "problem_button_positive_\(self.rawValue)")` 形式になっている
- [ ] 13問題すべてのキーが `ja.lproj/Localizable.strings` に存在する
- [ ] 13問題すべてのキーが `en.lproj/Localizable.strings` に存在する

### 1.2 negativeButtonText

**AS-IS**: ネガティブボタン文言が日本語でハードコードされている。一部の問題タイプ（self_loathing, anxiety, loneliness）はnilを返す（1択ボタン）。

**TO-BE**: `String(localized:)` を使用。1択ボタンの問題タイプは引き続きnilを返す。

**確認項目**:
- [ ] `negativeButtonText` が `String(localized: "problem_button_negative_\(self.rawValue)")` 形式になっている
- [ ] 1択ボタンの問題タイプ（self_loathing, anxiety, loneliness）はnilを返す
- [ ] 該当するキーが `ja.lproj/Localizable.strings` に存在する
- [ ] 該当するキーが `en.lproj/Localizable.strings` に存在する

### 1.3 notificationTitle

**AS-IS**: 通知タイトルが日本語でハードコードされている（例：「就寝」「起床」「Self-Compassion」）。

**TO-BE**: `String(localized:)` を使用してローカライズキーを参照する。

**確認項目**:
- [ ] `notificationTitle` が `String(localized: "problem_notification_title_\(self.rawValue)")` 形式になっている
- [ ] 13問題すべてのキーが `ja.lproj/Localizable.strings` に存在する
- [ ] 13問題すべてのキーが `en.lproj/Localizable.strings` に存在する

---

## 2. NudgeContent.swift のローカライズ

### 2.1 notificationMessages

**AS-IS**: 13問題タイプの通知メッセージが日本語でハードコードされている。各問題タイプに1〜3個のバリエーションがある。

**TO-BE**: `String(localized:)` を使用してローカライズキーを参照する。

**確認項目**:
- [ ] `notificationMessages(for:)` が `String(localized: "nudge_\(problem.rawValue)_notification_\(index)")` 形式を返す
- [ ] 全バリエーション（約40キー）が `ja.lproj/Localizable.strings` に存在する
- [ ] 全バリエーション（約40キー）が `en.lproj/Localizable.strings` に存在する

### 2.2 detailMessages

**AS-IS**: 13問題タイプの詳細メッセージが日本語でハードコードされている。各問題タイプに1〜3個のバリエーションがある。

**TO-BE**: `String(localized:)` を使用してローカライズキーを参照する。

**確認項目**:
- [ ] `detailMessages(for:)` が `String(localized: "nudge_\(problem.rawValue)_detail_\(index)")` 形式を返す
- [ ] 全バリエーション（約40キー）が `ja.lproj/Localizable.strings` に存在する
- [ ] 全バリエーション（約40キー）が `en.lproj/Localizable.strings` に存在する

---

## 3. MyPathTabView.swift の改修

### 3.1 ハードコード文言のローカライズ

**AS-IS**: 「あなたが向き合いたい問題」「問題が選択されていません」などの文言が日本語でハードコードされている。

**TO-BE**: `String(localized:)` を使用してローカライズキーを参照する。

**確認項目**:
- [ ] ヘッダー説明文がローカライズキーを使用している
- [ ] 空状態のタイトルがローカライズキーを使用している
- [ ] 「深掘りする」などのボタン文言がローカライズキーを使用している
- [ ] 該当するキーが `ja.lproj/Localizable.strings` に存在する
- [ ] 該当するキーが `en.lproj/Localizable.strings` に存在する

### 3.2 カード全体タップ

**AS-IS**: 問題カード内に「深掘りする」ボタンがあり、ボタンをタップしないとDeepDiveシートが開かない。

**TO-BE**: カード全体をタップするとDeepDiveシートが開く。「深掘りする」ボタンは削除。

**確認項目**:
- [ ] ProblemCardView全体に `.onTapGesture` または `Button` が適用されている
- [ ] 「深掘りする」ボタンが削除されている
- [ ] カードの右側に「→」シェブロンアイコンが表示されている

### 3.3 「＋ 課題を追加」ボタン

**AS-IS**: 課題を追加する手段がない。

**TO-BE**: ナビゲーションバーまたはリスト下部に「＋ 課題を追加」ボタンがあり、タップするとAddProblemSheetが表示される。

**確認項目**:
- [ ] 「＋ 課題を追加」ボタンが存在する
- [ ] ボタンをタップするとAddProblemSheetViewが表示される
- [ ] ボタン文言がローカライズされている

### 3.4 「Aniccaに伝える」セクション

**AS-IS**: ユーザーがAniccaに情報を伝える手段がない。

**TO-BE**: My Pathタブに「Aniccaに伝える」セクションがあり、3つの入力カード（今辛いのは、取り組んでいる目標は、覚えておいてほしいのは）が表示される。

**確認項目**:
- [ ] 「Aniccaに伝える」セクションヘッダーが存在する
- [ ] 3つの入力カードが表示されている
- [ ] 各カードをタップすると入力シートが表示される
- [ ] 入力内容がMemoryとして保存される
- [ ] セクションヘッダーとカード文言がローカライズされている

### 3.5 空状態のUI

**AS-IS**: 課題がない場合、「問題が選択されていません」と「プロフィール設定から...」という2行のテキストが表示される。

**TO-BE**: シンプルなアイコン、1行のテキスト、「＋ 課題を追加」ボタンのみ。明確な1つのアクション。

**確認項目**:
- [ ] 空状態でアイコンが表示されている
- [ ] 空状態で「向き合いたい課題を追加してみましょう」のような1行テキストが表示される
- [ ] 空状態で「＋ 課題を追加」ボタンが目立つ形で表示される
- [ ] 不要な説明文が削除されている

---

## 4. DeepDiveSheetView の改修

### 4.1 質問形式の変更

**AS-IS**: オープンエンド形式の質問（「夜更かしをやめられない本当の理由は何だと思う？」など）がリスト表示されている。

**TO-BE**: 選択肢形式の質問（「夜更かしして何をしてることが多い？」+ [SNS/YouTube/ゲーム/仕事/その他]）がチップUIで表示される。

**確認項目**:
- [ ] 質問がローカライズキー `deepdive_{problem}_q{n}` を使用している
- [ ] 選択肢がローカライズキー `deepdive_{problem}_q{n}_opt{m}` を使用している
- [ ] 選択肢がチップ（FlowLayout）形式で表示されている
- [ ] 複数選択が可能
- [ ] 選択状態が視覚的にわかる（色変更など）

### 4.2 共通質問

**AS-IS**: 共通質問がない。

**TO-BE**: すべての問題タイプで「どのくらい前からこの問題がある？」という共通質問が最初に表示される。選択肢は「最近/数ヶ月/1年以上/ずっと」。

**確認項目**:
- [ ] 共通質問がすべての問題タイプで最初に表示される
- [ ] 共通質問がローカライズキー `deepdive_common_duration_*` を使用している
- [ ] 4つの選択肢がチップ形式で表示される

### 4.3 保存ボタン

**AS-IS**: 選択内容を保存する手段がない。

**TO-BE**: シート下部に「保存」ボタンがあり、選択した回答が `UserProfile.problemDetails` に保存される。

**確認項目**:
- [ ] 「保存」ボタンが存在する
- [ ] ボタンをタップすると選択内容が保存される
- [ ] 保存先は `UserProfile.problemDetails[問題ID] = [選択した選択肢]`
- [ ] ボタン文言がローカライズされている

### 4.4 削除ボタン

**AS-IS**: 課題を削除する手段がない。

**TO-BE**: シート下部に「この課題を削除」ボタンがあり、タップするとAlertDialogで確認後に削除される。

**確認項目**:
- [ ] 「この課題を削除」ボタンが存在する（赤色、destructiveスタイル）
- [ ] ボタンをタップするとAlertDialogが表示される
- [ ] AlertDialogに「キャンセル」と「削除」ボタンがある
- [ ] 「削除」をタップすると `userProfile.struggles` から該当問題が削除される
- [ ] 削除後、関連する通知もキャンセルされる
- [ ] ボタン文言とAlertDialog文言がローカライズされている

---

## 5. 新規ファイル作成

### 5.1 Memory.swift

**AS-IS**: メモリ（ユーザーがAniccaに伝えた情報）を保存するモデルがない。

**TO-BE**: `Memory` 構造体と `MemoryStore` クラスが存在し、メモリの保存・読み込み・削除ができる。

**確認項目**:
- [ ] `Memory` 構造体が存在する（id, timestamp, type, content）
- [ ] `MemoryType` enumが存在する（struggle, goal, note）
- [ ] `MemoryStore` クラスが存在する
- [ ] メモリの保存メソッドが存在する
- [ ] メモリの読み込みメソッドが存在する
- [ ] メモリの削除メソッドが存在する
- [ ] UserDefaultsに永続化される

### 5.2 AddProblemSheetView.swift

**AS-IS**: 課題追加シートがない。

**TO-BE**: 13個の問題タイプをチップ形式で表示し、複数選択して一括追加できるシートが存在する。

**確認項目**:
- [ ] AddProblemSheetViewが存在する
- [ ] 13問題タイプがチップ形式で表示される
- [ ] 既に選択済みの問題は選択不可（グレーアウト）または非表示
- [ ] 複数選択が可能
- [ ] 「追加」ボタンをタップすると `userProfile.struggles` に追加される
- [ ] 追加後、関連する通知がスケジュールされる
- [ ] UI文言がローカライズされている

### 5.3 TellAniccaView.swift（または同等の入力シート）

**AS-IS**: 「Aniccaに伝える」入力シートがない。

**TO-BE**: テキスト入力フィールドとキーボードが表示され、入力内容がMemoryとして保存される。保存後は「覚えました」と表示されて自動で閉じる。

**確認項目**:
- [ ] 入力シートが存在する
- [ ] テキスト入力フィールドが存在する
- [ ] キーボードが自動で表示される
- [ ] 入力内容がMemoryStoreに保存される
- [ ] 保存後「覚えました」トースト/表示が出る
- [ ] 自動で閉じる（0.8秒程度）
- [ ] UI文言がローカライズされている

### 5.4 DeepDiveQuestionsData.swift（またはデータ定義）

**AS-IS**: 深掘り質問と選択肢のデータ構造がない。

**TO-BE**: 13問題タイプ × 2〜3質問 × 4〜5選択肢のデータが定義されている。

**確認項目**:
- [ ] 各問題タイプの質問データが定義されている
- [ ] 各質問の選択肢データが定義されている
- [ ] ローカライズキーを使用している
- [ ] カスタム課題用の汎用質問も定義されている

---

## 6. UserProfile の拡張

### 6.1 problemDetails プロパティ

**AS-IS**: 深掘り回答を保存するプロパティがない。

**TO-BE**: `problemDetails: [String: [String]]` プロパティがあり、問題ID → 選択した選択肢のマッピングを保存する。

**確認項目**:
- [ ] `problemDetails` プロパティが存在する
- [ ] 型は `[String: [String]]`
- [ ] Codableに対応している

### 6.2 memories プロパティ

**AS-IS**: メモリを保存するプロパティがない。

**TO-BE**: `memories: [Memory]` プロパティがあり、ユーザーがAniccaに伝えた情報を保存する。

**確認項目**:
- [ ] `memories` プロパティが存在する
- [ ] 型は `[Memory]`
- [ ] Codableに対応している

### 6.3 customProblems プロパティ

**AS-IS**: カスタム課題を保存するプロパティがない。

**TO-BE**: `customProblems: [CustomProblem]` プロパティがあり、ユーザー定義の課題を保存する。

**確認項目**:
- [ ] `customProblems` プロパティが存在する
- [ ] 型は `[CustomProblem]`
- [ ] Codableに対応している

---

## 7. ProfileView.swift の改修

### 7.1 セクション非表示

**AS-IS**: traitsCard、idealsSection、strugglesSection、stickyModeSectionが表示されている。

**TO-BE**: これらのセクションは非表示（コメントアウトまたは条件分岐）。strugglesはMy Pathタブで管理するため。

**確認項目**:
- [ ] traitsCardが非表示
- [ ] idealsSectionが非表示
- [ ] strugglesSectionが非表示
- [ ] stickyModeSectionが非表示

### 7.2 デバッグ機能追加

**AS-IS**: Nudge/通知のテスト機能がない。

**TO-BE**: DEBUG時のみ、recordingSectionにNudge通知テストボタンと1枚画面テストボタンが表示される。

**確認項目**:
- [ ] `#if DEBUG` で囲まれている
- [ ] 「Nudge通知テスト（夜更かし）」ボタンが存在する
- [ ] 「1枚画面テスト（夜更かし）」ボタンが存在する
- [ ] ボタンをタップすると対応する動作が実行される

---

## 8. ProblemNotificationScheduler.swift の改修

### 8.1 testNotificationメソッド

**AS-IS**: テスト用の即時通知発火メソッドがない。

**TO-BE**: `testNotification(for problem: ProblemType)` メソッドがあり、5秒後に指定した問題の通知を発火する。

**確認項目**:
- [ ] `testNotification(for:)` メソッドが存在する
- [ ] `#if DEBUG` で囲まれている
- [ ] 5秒後に通知が発火する
- [ ] 通知の内容は実際のNudgeContentを使用する

### 8.2 カスタム課題対応

**AS-IS**: 13問題タイプのみ対応。カスタム課題の通知スケジュール機能がない。

**TO-BE**: カスタム課題の通知もスケジュールできる。時刻は9:00と20:00。

**確認項目**:
- [ ] `scheduleCustomProblemNotifications(for:)` メソッドが存在する
- [ ] カスタム課題の通知が9:00と20:00にスケジュールされる
- [ ] 通知の内容はカスタム課題用の汎用文言を使用する

---

## 9. AppState.swift のマイグレーション

### 9.1 既存ユーザーのstrugglesマイグレーション

**AS-IS**: 既存ユーザーのstrugglesには古いキー（`poor_sleep`, `stress`, `focus`, `motivation`, `self_doubt`など）が保存されている可能性がある。

**TO-BE**: アプリ起動時にマイグレーションが実行され、古いキーが新しいキーに変換される。

**確認項目**:
- [ ] `migrateStruggles()` メソッドが存在する
- [ ] アプリ起動時にマイグレーションが実行される
- [ ] `poor_sleep` → `staying_up_late` に変換される
- [ ] `self_doubt` → `self_loathing` に変換される
- [ ] `motivation` → `procrastination` に変換される
- [ ] `focus` → `procrastination` に変換される
- [ ] `relationships` → `loneliness` に変換される
- [ ] マッピングにないキー（`stress`, `time_management`, `burnout`, `energy`, `work_life_balance`）は削除される
- [ ] 既に新しいキーの場合はそのまま保持される

---

## 10. Localizable.strings の完全性

### 10.1 ja.lproj/Localizable.strings

**確認項目**:
- [ ] ProblemTypeボタン文言（13 × 2 = 最大26キー）
- [ ] ProblemType通知タイトル（13キー）
- [ ] NudgeContent通知文言（約40キー）
- [ ] NudgeContent詳細文言（約40キー）
- [ ] DeepDive質問（13問題 × 2〜3質問 = 約30キー）
- [ ] DeepDive選択肢（約120キー）
- [ ] DeepDive共通質問（5キー）
- [ ] My PathタブUI文言（約15キー）
- [ ] カスタム課題用文言（約10キー）
- [ ] 共通UI文言（cancel, delete, save等）

### 10.2 en.lproj/Localizable.strings

**確認項目**:
- [ ] 上記すべてのキーに対応する英語版が存在する
- [ ] 英語として自然な文言になっている

---

## 11. 全体チェック

### 11.1 ビルドエラーがないこと

**確認項目**:
- [ ] Xcodeでビルドが成功する
- [ ] ローカライズキーの参照エラーがない

### 11.2 日本語UIでの動作確認

**確認項目**:
- [ ] My Pathタブが正常に表示される
- [ ] 課題カードが正常に表示される
- [ ] DeepDiveシートが正常に動作する
- [ ] 課題追加シートが正常に動作する
- [ ] 「Aniccaに伝える」が正常に動作する
- [ ] 通知が正常に発火する
- [ ] NudgeCardViewが正常に表示される

### 11.3 英語UIでの動作確認

**確認項目**:
- [ ] デバイス言語を英語に変更する
- [ ] すべての文言が英語で表示される
- [ ] 日本語が混在していない

---

## サマリー

| カテゴリ | 確認項目数 |
|---------|-----------|
| ProblemType.swift | 9 |
| NudgeContent.swift | 6 |
| MyPathTabView.swift | 20 |
| DeepDiveSheetView | 16 |
| 新規ファイル | 20 |
| UserProfile | 6 |
| ProfileView.swift | 6 |
| ProblemNotificationScheduler.swift | 7 |
| AppState.swift | 9 |
| Localizable.strings | 12 |
| 全体チェック | 10 |
| **合計** | **約120項目** |
