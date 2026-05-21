実装時に迷いやすいポイント
Scheduler差し替え
既存の WakeNotificationScheduler 依存をすべて HabitAlarmScheduler へ置換してください（AppState, Onboarding画面, AppDelegate など）。1箇所でも旧クラスが残るとビルドエラーになります。
App Intent連携
StartConversationIntent を新規ファイルで定義し、AlarmKit の secondaryIntent と listenForAlarmUpdates() 両方から呼び出す構造にします。Intent名・引数の型（HabitType識別子）を決め打ちし、IDの整合に注意してください。
AlarmKit / 通知フォールバック分岐
#available(iOS 18.0, *) で分岐する全てのメソッド（権限確認・スケジュール・キャンセル）を統一しておくと迷いがありません。HabitAlarmScheduler 内で完結させ、呼び出し側は分岐不要にします。
Entitlements確認
com.apple.developer.usernotifications.alarm が入った新規プロファイルでビルドするまで動作しません。古いプロファイルを使うとリンクエラーになるので注意。
Intent呼び出しのエラーハンドリング
AlarmKitからIntentが失敗した場合のフォールバックメッセージ（ログ出力等）を入れておくとデバッグしやすいです。


あなた側で必要な作業
Xcode環境
Xcode 26.1 と Command Line Tools を最新化し、Deployment Target を iOS 18.0 に変更。
App ID/プロビジョニング
Apple Developer ポータルで App ID の Alarms Capability を有効化 → 新しいプロビジョニングプロファイルをダウンロードし Xcode に適用。
実機テスト
iOS 18.2 端末で AlarmKit 動作確認。可能なら iOS 17 端末/シミュレータでもフォールバック通知を確認。
App Intent追加後の設定
新 Intent をターゲット設定（IntentDefinition の有無や Info.plist の参照）で認識させ、Product > Clean Build Folder を実行。
TestFlight/App Store 準備
実装後 feature/alarmkit ブランチを切り、アーカイブ・TestFlight アップロード→審査資料更新→本番リリースの順で進行。

AlarmKit移行とリリース準備プラン
AlarmKit対応（8ステップ）
iOS 18へのデプロイターゲット更新
aniccaios/aniccaios.xcodeproj/project.pbxproj
L221, L281, L316, L359, L432, L468, L535, L570 の IPHONEOS_DEPLOYMENT_TARGET = 16.0; をすべて 18.0 に書き換える。
変更後、Xcode 側でターゲットが iOS 18 になっているか確認。
Info.plist の AlarmKit 利用宣言
aniccaios/aniccaios/Info.plist
L5直下に <key>NSAlarmKitUsageDescription</key> と <string>アニッチャがアラームを鳴らすために必要です。</string> を追記。
既存の NSUserNotificationUsageDescription は残す。
AlarmKit 用エンタイトルメント追加
Xcode → TARGETS aniccaios → Signing & Capabilities → 「Alarms」機能を追加。
追加後、aniccaios/aniccaios/aniccaios.entitlements に <key>com.apple.developer.usernotifications.alarm</key><true/> が生成されているか確認（生成されない場合は L11 の直前に手動追記）。
AlarmKit スケジューラ新規作成
新規ファイル aniccaios/aniccaios/HabitAlarmScheduler.swift を追加。
主な構成:
import AlarmKit（iOS 18 以上のみ利用）と import UserNotifications。
final class HabitAlarmScheduler 内で static let shared を提供。
requestAuthorization()/alarmAuthorizationState()/requestAuthorizationIfNeeded() を用意し、#available(iOS 18.0, *) で AlarmKit と旧通知を切り替え。
scheduleAlarms(for:) で HabitType ごとに AlarmKit か旧通知をセット。
AlarmKit 側は AlarmManager.AlarmConfiguration を生成し、AlarmPresentation.Alert(title:habit.title, stopButton:.stopButton, secondaryButton:.openAppButton, secondaryButtonBehavior:.custom) を設定。
secondaryIntent に StartConversationIntent（ステップ6で追加）を渡し、metadata として Habit 種別保持用構造体を添付。
旧OSフォールバックは現行 WakeNotificationScheduler のロジックを移植。
cancelAll() と cancel(for:) を実装し、AlarmKit 使用時は AlarmManager.shared.cancel(id:) を呼ぶ。
AppState の依存更新とアラーム更新フック
aniccaios/aniccaios/AppState.swift
L38 を private let scheduler = HabitAlarmScheduler.shared に差し替え。
L95, L115 付近の await scheduler.scheduleNotifications(for: habitSchedules) を await scheduler.scheduleAlarms(for: habitSchedules) に変更。
init() の末尾で Task { await scheduler.syncScheduledAlarms(from: habitSchedules) } を追加して AlarmKit 再登録（フォールバック時は no-op）。
新規で func handleAlarmTrigger(habit: HabitType) を追加し、pendingHabitTrigger を設定していた既存 handleHabitTrigger 内から呼び出す形に整理。
AppIntent で会話起動 & AppDelegate 更新
aniccaios/aniccaios/Intents/StartConversationIntent.swift を新規作成。
import AppIntents, struct StartConversationIntent: AppIntent を定義し、@Parameter で habit ID を受け取る。
perform() で await AppState.shared.prepareForImmediateSession(habit:) を呼び出し、AudioSessionCoordinator を再構成。
AppDelegate.swift
L1 に import AlarmKit を追加。
L15〜L17 の WakeNotificationScheduler 呼び出しを削除し、代わりに Task { _ = await HabitAlarmScheduler.shared.requestAuthorizationIfNeeded() } を追加。
UNUserNotificationCenterDelegate 実装は iOS18未満フォールバック用として残しつつ、#available で切替。
AlarmKit の通知着信を扱うため、application(_:didFinishLaunchingWithOptions:) の末尾に listenForAlarmUpdates() 呼出を追加し、同ファイル内に private func listenForAlarmUpdates() を実装。AlarmManager.shared.alarmUpdates を Task で監視し、alarm.state == .alerting のときに StartConversationIntent を起動。
Onboarding の権限リクエスト更新
NotificationPermissionStepView.swift
L3 の import UserNotifications に import AlarmKit を追記。
L62〜L65 での設定取得を、iOS18 以上は await HabitAlarmScheduler.shared.alarmAuthorizationState() を利用する処理に変更。
L81 のリクエスト呼び出しを HabitAlarmScheduler.shared.requestAuthorization() に変更し、戻り値で notificationGranted を更新。
PermissionsStepView.swift
同様に WakeNotificationScheduler.shared.requestAuthorization() 参照箇所（L79 等）を HabitAlarmScheduler.shared.requestAuthorization() に置換。
旧 WakeNotificationScheduler の整理
WakeNotificationScheduler.swift を削除。
プロジェクトから参照が外れていることを Xcode で確認し、HabitAlarmScheduler が代替していることを確認。
AlarmKit 導入後の動作確認
iOS 18.5 実機で、起床・就寝・トレーニングそれぞれのアラームが AlarmKit UI（Start Conversation ボタン付き）で表示され、ボタンでアプリが前面化→会話開始することを確認。
iOS 17 以前のデバイス／シミュレータでフォールバック通知が従来通り動作することを確認。
TestFlight→App Store リリース手順
ブランチ整理
git checkout main && git pull
git checkout -b feature/alarmkit
上記 8 ステップ＋テストを完了後、PR 作成→レビュー→main マージ。
バイナリの署名確認
Xcode > Product > Archive で aniccaios をアーカイブ。
Organizer で Validate App を実行し、IPA が問題ないか確認。
TestFlight アップロード
Organizer の Distribute App → App Store Connect → Upload。
App Store Connect の TestFlight タブでビルド処理完了を待つ。
内部テスター（あなた＋チーム）を割り当て、起床アラームを重点的にテスト。
外部テスター対応（必要なら）
App Store Connect → TestFlight → 外部テスト で招待。
エクスポートコンプライアンス・プライバシー質問票 を最新化。
審査用メタデータ準備
App Store タブで App 情報・スクリーンショット（AlarmKit UI 含む）・キーワード・サポートURL を更新。
App Privacy 質問票を最新回答に更新。
App Store 審査提出
審査へ提出 を実行し、ステータスが Waiting For Review になることを確認。
リリース
審査通過後、Release をクリックし公開。
公開後、テスト端末で App Store 版をダウンロードし、AlarmKit が本番環境でも動くことを最終確認。
ドキュメント更新
上記手順を docs/ios.md に追記し、次回以降のリリース手順を標準化。