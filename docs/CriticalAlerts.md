• 修正手順（Time Sensitive 通知版・行指定付き）

  1. aniccaios/aniccaios/Info.plist
      - 6行目の <string>https://…</string> の直後に以下4行を追加:

        <key>NSUserNotificationUsageDescription</key>
        <string>We use notifications to wake you up at the time you set.</string>
      - 9〜12行目の <array> 内に 12行目の直前で <string>remote-notification</string> を追加。
  2. リソース追加
      - ディレクトリ aniccaios/aniccaios/Resources/Prompts/ を新規作成。
      - apps/desktop/prompts/common.txt と apps/desktop/prompts/wake_up.txt をそのままコピーし、同名で配置。
  3. aniccaios/aniccaios/WakePromptBuilder.swift（新規ファイル）
      - Bundle.main.url(forResource:"common", withExtension:"txt", subdirectory:"Prompts") で common.txt を読
        み込み、
        同様に wake_up.txt を取得。
      - buildWakePrompt(wakeTime: DateComponents?, date: Date) -> String を定義し、
          - languageLine = "From now on I will write and speak only in English."
          - languageLabel = "English"
          - taskId = "wake_up__\(HHMM)"（2桁ゼロ埋め）
          - taskDescription = "Wake-up routine"
            を common.txt の ${…} プレースホルダへ .replacingOccurrences(of:) で反映。
      - wake_up.txt は buildRoutinePrompt 相当（寝床情報など未収集のプレースホルダは空文字で置換）で結合し、
        最終的に common + "\n\n" + wake を返却。
  4. aniccaios/aniccaios/WakeNotificationScheduler.swift（新規ファイル）
      - final class WakeNotificationScheduler を定義し static let shared = WakeNotificationScheduler()。
      - requestAuthorization() async -> Bool で
        UNUserNotificationCenter.current().requestAuthorization(options:
        [.alert, .sound, .badge, .timeSensitive]) を呼ぶ（.criticalAlert は含めない）。
      - registerCategories() にて UNNotificationAction(identifier:"start_conversation", title:"Start
        Conversation", options:[.foreground]) を作成し、カテゴリID "wake.alarm" を登録。
      - scheduleWakeNotification(for components: DateComponents)
          - 既存リクエストを removePendingNotificationRequests(withIdentifiers:["wake.alarm"]) で削除。
          - UNMutableNotificationContent に

            title = "Wake-Up Call"
            body = "Tap to talk with Anicca."
            categoryIdentifier = "wake.alarm"
            interruptionLevel = .timeSensitive
            sound = .default
          - トリガーは UNCalendarNotificationTrigger(dateMatching: components, repeats: true)。
      - cancelWakeNotification() を用意して removePendingNotificationRequests をラップ。
  5. aniccaios/aniccaios/AppState.swift（新規ファイル）
      - @MainActor final class AppState: ObservableObject とし、static let shared = AppState() を用意。
      - @Published var wakeTime: DateComponents?, @Published var isOnboardingComplete: Bool,
        @Published var pendingWakeTrigger: UUID? を保持。
      - private var pendingWakePrompt: String?、private let scheduler = WakeNotificationScheduler.shared、
        private let promptBuilder = WakePromptBuilder() を定義。
      - init() で UserDefaults.standard から wakeTimeKey（Dictionary 保存）、onboardingCompletedKey（Bool）を
        復元。
      - func updateWakeTime(_ date: Date)
          - Calendar.current から hour/minute を切り出し wakeTime に格納、
          - UserDefaults に保存後 await scheduler.scheduleWakeNotification(for: components) を呼ぶ。
      - func markOnboardingComplete() で isOnboardingComplete = true と保存。
      - func handleWakeTrigger() で pendingWakePrompt = promptBuilder.buildWakePrompt(wakeTime: wakeTime,
        date: Date())、
        pendingWakeTrigger = UUID()。
      - func consumeWakePrompt() -> String? で pendingWakePrompt を defer で nil にしつつ返却。
      - func clearPendingWakeTrigger() で pendingWakeTrigger = nil。
  6. aniccaios/aniccaios/AppDelegate.swift（新規ファイル）
      - class AppDelegate: NSObject, UIApplicationDelegate, UNUserNotificationCenterDelegate。
      - application(_:didFinishLaunchingWithOptions:) 内で

        UNUserNotificationCenter.current().delegate = self
        WakeNotificationScheduler.shared.registerCategories()
        を実行。
      - userNotificationCenter(_:didReceive:withCompletionHandler:) で
        if response.actionIdentifier == "start_conversation" || response.notification.request.identifier ==
        "wake.alarm" の場合に AppState.shared.handleWakeTrigger() を呼び、completionHandler()。
      - userNotificationCenter(_:willPresent:withCompletionHandler:) は [.banner, .sound] を返す。
  7. aniccaios/aniccaios/aniccaiosApp.swift
      - 8行目の直下に @UIApplicationDelegateAdaptor(AppDelegate.self) private var appDelegate を追加。
      - 10〜16行を以下に置換:

        @StateObject private var appState = AppState.shared

        var body: some Scene {
            WindowGroup {
                ContentRouterView()
                    .environmentObject(appState)
            }
        }
  8. aniccaios/aniccaios/ContentView.swift を ContentRouterView に改装
      - 10〜63行を削除し、代わりに

        struct ContentRouterView: View {
            @EnvironmentObject private var appState: AppState

            var body: some View {
                if appState.isOnboardingComplete {
                    SessionView()
                } else {
                    OnboardingFlowView()
                }
            }
        }
      - #Preview は ContentRouterView().environmentObject(AppState.shared) に更新。
  9. aniccaios/aniccaios/SessionView.swift（新規ファイル）
      - 既存のボタンUIを移植し、@StateObject private var controller = VoiceSessionController()・
        @EnvironmentObject private var appState を宣言。
      - var body の VStack に .padding() を維持。
      - .onChange(of: appState.pendingWakeTrigger) で id != nil の際に

        if let prompt = AppState.shared.consumeWakePrompt() {
            AppState.shared.clearPendingWakeTrigger()
            controller.start()
        }
        を実行（start() 内で prompt を拾うため consume だけ呼ぶ）。
      - 画面表示時に pendingWakeTrigger が既に存在する場合へ対応するため onAppear でも同処理を呼ぶ。
      - ボタンの手動開始は既存通り（タイトル “Start Voice Session” など英語のまま）。
  10. aniccaios/aniccaios/VoiceSessionController.swift
      - 6行目を @MainActor final class VoiceSessionController: NSObject, ObservableObject { に変更。
      - 240〜255行目付近の let update: [String: Any] = […] を以下へ更新:

        var sessionPayload: [String: Any] = [
            "modalities": ["audio"],
            "voice": "alloy",
            "turn_detection": [
                "type": "server_vad",
                "threshold": 0.5,
                "prefix_padding_ms": 300,
                "silence_duration_ms": 500,
                "create_response": true
            ],
            "max_response_output_tokens": "inf"
        ]
        if let prompt = AppState.shared.consumeWakePrompt() {
            sessionPayload["instructions"] = prompt
        }
        let update: [String: Any] = [
            "type": "session.update",
            "session": sessionPayload
        ]
      - sendSessionUpdate() 冒頭で AppState.shared.clearPendingWakeTrigger() を呼び出す処理を追加し、二重起動
        を防止。
  11. aniccaios/aniccaios/Onboarding/OnboardingStep.swift（新規ファイル）
      - enum OnboardingStep: Int { case welcome, permissions, wakeSetup } を定義。
  12. aniccaios/aniccaios/Onboarding/OnboardingFlowView.swift（新規ファイル）
      - @EnvironmentObject private var appState: AppState と @State private var step: OnboardingStep
        = .welcome。
      - var body で switch step を用い WelcomeStepView(next: advance) などを返す。
      - private func advance() で .welcome -> .permissions -> .wakeSetup ->
        appState.markOnboardingComplete()。
  13. WelcomeStepView.swift（新規）
      - 背景白・中央 Text("Welcome to Anicca")、下部 Button("Get Started") が next() を呼ぶ。
  14. PermissionsStepView.swift（新規）
      - @State private var micGranted = false, notificationGranted = false, isLoading = false.
      - Button("Allow Microphone") が AVAudioSession.sharedInstance().requestRecordPermission で更新。
      - Button("Allow Notifications") で Task { micGranted = await
        WakeNotificationScheduler.shared.requestAuthorization() }。
      - 両方 true になったら自動で next() を呼ぶ。
  15. WakeSetupStepView.swift（新規）
      - @EnvironmentObject private var appState: AppState、@State private var selectedDate = Date()。
      - DatePicker("Wake Time", selection: $selectedDate, displayedComponents: [.hourAndMinute])。
      - Button("Save Wake Time") で await appState.updateWakeTime(selectedDate)、next()。
  16. SessionView から通知設定未完了の場合に再申請できるよう、PermissionsStepView 完了後に
     WakeNotificationScheduler 登録済み。

  ———

  将来 Critical Alert を採用する際の差分

  1. WakeNotificationScheduler.requestAuthorization() の options 配列へ .criticalAlert を追加。
  2. 同クラスの scheduleWakeNotification 内で
      - content.interruptionLevel = .critical
      - content.sound = .defaultCritical
        に置き換え。
  3. Info.plist の <array> に既に追加済みの remote-notification に加え、Apple から entitlement 承認後
     に .entitlements ファイルへ com.apple.developer.usernotifications.critical-alerts を追加し、Xcode プロ
     ジェクト設定の Capabilities で Critical Alerts を有効化。
  4. PermissionsStepView の通知許可ボタン押下時に、承認後
     WakeNotificationScheduler.shared.requestAuthorization() が .criticalAlert を含むことを再確認する以外の
     コード変更は不要。

  ———

  完成後のUI/UX（プロモ動画イメージ）

  - Welcome: フルスクリーン白、中央 “Welcome to Anicca”、サブ文 “We’ll set up your wake-up routine.”。下部にブ
    ルーの “Get Started” ボタン。押下でスライド遷移。
  - Permissions: 2枚のカード表示。上段 “Microphone Access” にはグレーのマイクアイコン、文 “Enable live
    conversation when you wake up.”、右下に “Allow Microphone”。許可後は緑の “Enabled”。下段 “Time-Sensitive
    Alerts” も同様。両方 Enabled になると自動で次へ。
  - Wake Setup: ヘッダー “Set Your Wake Time”、中心に iOS ホイール式 DatePicker、サブ文 “Anicca will ring
    exactly at this minute.”、ボタン “Preview Alarm” とメイン “Save Wake Time”。保存成功でシート “All set!
    We’ll wake you every morning.” → “Continue”。
  - Home (SessionView): タイトル “Anicca Voice”、ステータス “Status: Disconnected”。下に “Start Voice Session”
    ボタン。
  - Morning: 設定時刻になるとロック画面に Time Sensitive 通知バナー “Wake-Up Call – Tap to talk with
    Anicca.”。サウンドと共に Start Conversation ボタンが表示され、タップでアプリが前面化。
  - Conversation: アプリ復帰直後にステータスが “Status: Connected” へ変化し、Anicca が自動で “It is 6 o’clock.
    Good morning. Stand up now.” と開始。その後「Stand up. Leave the bed. Count to three and move.」など
    wake_up.txt に沿った厳しい口調が連続。ユーザーが “I’m up.” と答えると “Good. You’re up. Keep moving to the
    sink.” のように続く。会話終了時にユーザーが End Session を押すと “Status: Session Ended” に戻る。

  ———

  パラメータ妥当性・未解決事項

  - 全ての通知 API 呼び出しは Apple 公式（UNUserNotificationCenter、Time Sensitive）仕様どおり。Critical Alert
    は entitlement 未承認のため現時点では一切使用せず、承認後の手順も明記済み。
  - Realtime セッション更新は docs/Using-realtime-models.md と docs/manage-conv.md のサンプル通り type:
    "session.update" で modalities・voice・turn_detection・instructions を送信しており、非公式パラメータは一切
    含んでいません。
  - プロンプトは公式デスクトップ実装 (apps/desktop/prompts/common.txt,wake_up.txt) をそのまま読み込んでおり、
    ID など独自拡張は不要。
  - 以上により追加の疑問点はありません。実装時に参照すべき仕様はすべてレポジトリ内ソースと Apple/OpenAI ドキュ
    メントで確認済みです。