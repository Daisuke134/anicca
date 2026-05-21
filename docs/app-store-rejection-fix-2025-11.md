# App Store リジェクト対応記録 - 2025年11月

## 概要

2025年11月17日にApp Store審査でリジェクトされ、2つのガイドライン違反を指摘された。権限要求UIの改善と通知機能の任意化を実施し、再提出に向けた対応を完了した。

## リジェクト情報

- **Submission ID**: 07450f4c-d453-4101-9054-44e02bf8638e
- **審査日**: 2025年11月17日
- **バージョン**: 1.0
- **リジェクト理由**: 2つのガイドライン違反

## リジェクト理由の詳細

### 1. Guideline 5.1.1 - Legal - Privacy - Data Collection and Storage

**指摘内容：**
アプリがマイクへのアクセス許可を促す不適切な方法を使用している。具体的には、システムの許可ダイアログの前にカスタムメッセージが表示され、「Allow Microphone」というボタンが表示されている。このような表現は、ユーザーに許可を強制するものとして判断された。

**問題点：**
- `MicrophonePermissionStepView.swift` で「Allow Microphone」というボタン文言を使用
- システムの許可ダイアログの前に、許可を促すような説明カードを表示
- ユーザーの選択を尊重していないと判断された

**Appleの要求：**
- 許可要求プロセスで、許可を促す不適切な言葉をボタンに使用しない
- 「Continue」や「Next」などのニュートラルな表現を使用する
- 必要に応じて、許可が必要な理由を説明することは可能だが、ユーザーの選択を尊重する

### 2. Guideline 4.5.4 - Design - Apple Sites and Services

**指摘内容：**
アプリが機能するためにプッシュ通知が必要とされている。プッシュ通知は任意でなければならず、アプリ内での使用についてユーザーの同意を得る必要がある。

**問題点：**
- `NotificationPermissionStepView.swift` で、通知許可が得られない限り `next()` が呼ばれず、オンボーディングが進まない
- コード内に「User must grant permission to proceed」というコメントがあり、通知が必須であることが明示されていた
- 通知を許可しないとアプリが使えない設計になっていた

**Appleの要求：**
- プッシュ通知は任意でなければならない
- ユーザーの同意を得て使用する必要がある
- 通知を許可しなくてもアプリが正常に機能する必要がある

## 実施した対策

### 1. マイク許可UIの改善

#### 変更ファイル
- `aniccaios/aniccaios/Onboarding/MicrophonePermissionStepView.swift`
- `aniccaios/aniccaios/Resources/en.lproj/Localizable.strings`
- `aniccaios/aniccaios/Resources/ja.lproj/Localizable.strings`

#### 修正内容

**ボタン文言の変更：**
- 「Allow Microphone」→「Continue」に変更
- ボタンを押すとシステムの許可ダイアログが表示されるが、許可を強制する表現を排除

**説明文の改善：**
- 「Anicca needs microphone access...」→「Anicca uses your microphone... You can keep going without enabling it and turn it on anytime from Settings.」
- 許可しなくても続行できることを明示
- 後から設定で変更可能であることを説明

**UI要素の追加：**
- 「Maybe Later」ボタンを追加（`.ghost`スタイル）
- 拒否された場合に「Open Settings」ボタンを表示
- 補足説明テキストを追加：「Need the voice experience later? Just return to Settings → Anicca...」

**動作の変更：**
- 拒否されても `next()` を呼び出してオンボーディングを継続可能に
- 設定アプリを開く機能を追加（`UIApplication.openSettingsURLString`）

### 2. 通知機能の完全任意化

#### 変更ファイル
- `aniccaios/aniccaios/Onboarding/NotificationPermissionStepView.swift`
- `aniccaios/aniccaios/Resources/en.lproj/Localizable.strings`
- `aniccaios/aniccaios/Resources/ja.lproj/Localizable.strings`

#### 修正内容

**ボタン文言の変更：**
- 「Allow Notifications」→「Continue」に変更
- 許可を促す表現を排除

**説明文の改善：**
- 「Anicca needs notification access...」→「Notifications help Anicca... but they're optional and work even if you silence your phone.」
- 通知が任意であることを明示
- 後から設定で変更可能であることを説明

**UI要素の追加：**
- 「Maybe Later」ボタンを追加
- 拒否された場合に「Open Settings」ボタンを表示
- 補足説明テキストを追加：「Skip for now if you prefer. You can enable notifications anytime from Settings → Anicca.」

**動作の変更：**
- 拒否されても `next()` を呼び出してオンボーディングを継続可能に
- 許可が得られない場合でもアプリが正常に動作するように実装
- `NotificationScheduler` は権限が得られるまでスケジューリングを行わない（アプリ側でガードを実装）

**コードの修正：**
- 「User must grant permission to proceed」というコメントを削除
- 拒否時のエラーメッセージを削除し、代わりに設定への導線を提供

### 3. ローカライズ文字列の追加

#### 新規追加キー
- `common_maybe_later`: "Maybe Later" / "あとで設定する"
- `common_open_settings`: "Open Settings" / "設定を開く"
- `onboarding_microphone_optional_hint`: マイク許可の補足説明
- `onboarding_notifications_optional_hint`: 通知許可の補足説明

#### 変更されたキー
- `common_allow_microphone`: 削除（使用停止）
- `common_allow_notifications`: 削除（使用停止）
- `onboarding_microphone_description`: 内容を変更
- `onboarding_notifications_description`: 内容を変更

### 4. 技術的な修正

#### ButtonStyleの修正
- `ComponentsKit` の `ButtonStyle` に `.outline` が存在しないため、`.ghost` スタイルを使用
- 既存の実装パターンに合わせて統一

#### 権限状態の管理
- `micDenied` / `notificationDenied` の状態を追加
- 権限状態を適切に更新するメソッドを追加（`updatePermissionSnapshot()` / `refreshAuthorizationState()`）

## App Reviewへの返信文

以下をResolution Centerに送信：

```
Subject: Resubmission - Permission UI Updates

Dear App Review Team,

Thank you for your feedback. We have addressed both issues:

Guideline 5.1.1 (Privacy - Data Collection):
- Changed the microphone permission button text from "Allow Microphone" to "Continue" to avoid directing users to grant permission.
- Added a "Maybe Later" option so users can proceed without granting microphone access.
- Added a link to Settings for users who want to enable microphone access later.

Guideline 4.5.4 (Design - Push Notifications):
- Made push notifications fully optional by adding a "Maybe Later" button that allows users to proceed without granting notification permission.
- Updated the notification description to clarify that notifications are optional and can be enabled anytime from Settings.
- The app now functions completely without push notifications; users can skip this step and continue using the app.

All permission requests now respect user choice, and users can proceed through onboarding without granting any permissions. Permissions can be enabled later from Settings if desired.

We have tested the updated flow in Sandbox and confirmed that:
- Users can skip both microphone and notification permissions
- The app functions normally without these permissions
- Users can enable permissions later from Settings

Please review the updated build. We believe it now fully complies with Apple's guidelines.

Thank you for your consideration.

Best regards,
[Your Name]
```

## 修正後の動作確認

### マイク許可フロー
1. ✅ オンボーディングで「Continue」ボタンを表示
2. ✅ ボタンを押すとシステムの許可ダイアログが表示
3. ✅ 許可されなくても「Maybe Later」で次へ進める
4. ✅ 拒否された場合は「Open Settings」ボタンを表示
5. ✅ 設定アプリへの導線が機能する

### 通知許可フロー
1. ✅ オンボーディングで「Continue」ボタンを表示
2. ✅ ボタンを押すとシステムの許可ダイアログが表示
3. ✅ 許可されなくても「Maybe Later」で次へ進める
4. ✅ 拒否された場合は「Open Settings」ボタンを表示
5. ✅ 通知が許可されていなくてもアプリが正常に動作する
6. ✅ `NotificationScheduler` は権限が得られるまでスケジューリングを行わない

## 学んだ教訓

### 1. 権限要求UIの設計原則
- **中立性**: 許可を促す表現（「Allow」「許可」など）をボタンに使用しない
- **選択の尊重**: ユーザーが拒否してもアプリを継続使用できる設計にする
- **後から変更可能**: 設定アプリへの導線を提供し、後から権限を有効化できることを明示

### 2. 通知機能の実装原則
- **任意性の確保**: 通知を許可しなくてもアプリの基本機能が動作する
- **明確な説明**: 通知が任意であることをUI上で明示する
- **柔軟な設計**: 権限が得られない場合でも、アプリ側で適切に処理する

### 3. Apple審査への対応
- **ガイドラインの理解**: 各ガイドラインの意図を理解し、表面的な修正ではなく根本的な改善を行う
- **明確な返信**: 修正内容を簡潔に説明し、審査員が理解しやすい形式で返信する
- **テストの重要性**: Sandbox環境で実際に動作確認を行い、修正が正しく機能することを確認する

## 今後の注意点

### 権限要求UI
- 新しい権限を追加する際は、必ず「Continue」などのニュートラルな表現を使用
- 「Maybe Later」や「Skip」オプションを必ず提供
- 設定アプリへの導線を常に用意する

### 通知機能
- 通知を必須機能として扱わない
- 権限が得られない場合でもアプリが正常に動作することを確認
- 通知スケジューリング前に権限チェックを実装

### 審査提出前のチェックリスト
- [ ] 権限要求ボタンの文言がニュートラルか
- [ ] 権限を拒否してもアプリが動作するか
- [ ] 設定アプリへの導線が機能するか
- [ ] 説明文が適切で、許可を強制していないか
- [ ] Sandbox環境で動作確認が完了しているか

## 参考リンク

- [App Store Review Guidelines - Guideline 5.1.1](https://developer.apple.com/app-store/review/guidelines/#privacy)
- [App Store Review Guidelines - Guideline 4.5.4](https://developer.apple.com/app-store/review/guidelines/#apple-sites-and-services)
- [Designing Appropriate Permission Requests](https://developer.apple.com/design/human-interface-guidelines/permissions)

## 関連ファイル

- `aniccaios/aniccaios/Onboarding/MicrophonePermissionStepView.swift`
- `aniccaios/aniccaios/Onboarding/NotificationPermissionStepView.swift`
- `aniccaios/aniccaios/Resources/en.lproj/Localizable.strings`
- `aniccaios/aniccaios/Resources/ja.lproj/Localizable.strings`
- `aniccaios/aniccaios/Notifications/NotificationScheduler.swift`

## Sandbox検証チェックリスト

- サンドボックスApple IDに切り替え → App Storeアプリでサインアウト
- TestFlight/実機で `aniccaios` を起動し、RevenueCat Offering `anicca` を取得
- 月額/年額の購入 → 1分以内に Paywall が閉じることを確認
- `VoiceSessionController` で WebRTC 接続 → `RTCMacros.h` エラーが出ない
- `https://anicca-proxy-production.up.railway.app/health` が200を返すこと

---

**最終更新**: 2025年11月19日
**対応者**: [Your Name]
**ステータス**: 修正完了、再提出準備完了


