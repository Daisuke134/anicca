import UserNotifications
import os.log

class NotificationService: UNNotificationServiceExtension {
    
    private let logger = Logger(subsystem: "com.anicca.ios.notification-service", category: "PreReminder")
    
    var contentHandler: ((UNNotificationContent) -> Void)?
    var bestAttemptContent: UNMutableNotificationContent?
    
    // Keychain/UserDefaults からの認証情報取得（App Groupsを使用）
    private var appGroupDefaults: UserDefaults? {
        UserDefaults(suiteName: "group.ai.anicca.app.ios")
    }
    
    private var proxyBaseURL: String {
        // Info.plist から読み込み、または App Groups UserDefaults から取得
        if let url = Bundle.main.object(forInfoDictionaryKey: "ANICCA_PROXY_BASE_URL") as? String {
            return url
        }
        return appGroupDefaults?.string(forKey: "ANICCA_PROXY_BASE_URL") ?? ""
    }
    
    override func didReceive(_ request: UNNotificationRequest,
                             withContentHandler contentHandler: @escaping (UNNotificationContent) -> Void) {
        self.contentHandler = contentHandler
        bestAttemptContent = (request.content.mutableCopy() as? UNMutableNotificationContent)
        
        guard let bestAttemptContent = bestAttemptContent else {
            contentHandler(request.content)
            return
        }

        // A notification must never arrive wordless. If the payload body is
        // empty, put a bundled default word in before anything is delivered;
        // the personalized fetch below may still replace it with a better
        // one. (Same guarantee as the living home, 1.11.1.)
        if bestAttemptContent.body.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            bestAttemptContent.body = Self.defaultWord(for: request.content.userInfo)
        }
        
        // PRE_REMINDER カテゴリの通知のみ処理
        guard request.content.categoryIdentifier == "PRE_REMINDER" else {
            contentHandler(bestAttemptContent)
            return
        }
        
        let userInfo = request.content.userInfo
        guard let habitType = userInfo["habitType"] as? String,
              let scheduledTime = userInfo["scheduledTime"] as? String else {
            logger.warning("Missing habitType or scheduledTime in userInfo")
            contentHandler(bestAttemptContent)
            return
        }
        
        let habitName = userInfo["habitName"] as? String
        
        // App Groups から認証情報を取得
        guard let userId = appGroupDefaults?.string(forKey: "userId"),
              let deviceId = appGroupDefaults?.string(forKey: "deviceId") else {
            logger.warning("Missing userId or deviceId in App Groups")
            contentHandler(bestAttemptContent)
            return
        }
        
        Task {
            await fetchAndUpdateMessage(
                bestAttemptContent: bestAttemptContent,
                habitType: habitType,
                habitName: habitName,
                scheduledTime: scheduledTime,
                userId: userId,
                deviceId: deviceId,
                contentHandler: contentHandler
            )
        }
    }
    
    private func fetchAndUpdateMessage(
        bestAttemptContent: UNMutableNotificationContent,
        habitType: String,
        habitName: String?,
        scheduledTime: String,
        userId: String,
        deviceId: String,
        contentHandler: @escaping (UNNotificationContent) -> Void
    ) async {
        guard !proxyBaseURL.isEmpty else {
            logger.error("proxyBaseURL is empty")
            contentHandler(bestAttemptContent)
            return
        }
        
        let urlString = "\(proxyBaseURL)/mobile/nudge/pre-reminder"
        guard let url = URL(string: urlString) else {
            logger.error("Invalid URL: \(urlString)")
            contentHandler(bestAttemptContent)
            return
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue(deviceId, forHTTPHeaderField: "device-id")
        request.setValue(userId, forHTTPHeaderField: "user-id")
        request.timeoutInterval = 25  // Service Extension は最大30秒
        
        var body: [String: Any] = [
            "habitType": habitType,
            "scheduledTime": scheduledTime
        ]
        if let habitName = habitName {
            body["habitName"] = habitName
        }
        
        do {
            request.httpBody = try JSONSerialization.data(withJSONObject: body)
            
            let (data, response) = try await URLSession.shared.data(for: request)
            
            guard let httpResponse = response as? HTTPURLResponse,
                  (200..<300).contains(httpResponse.statusCode) else {
                logger.error("Non-2xx response from pre-reminder endpoint")
                contentHandler(bestAttemptContent)
                return
            }
            
            guard let json = try JSONSerialization.jsonObject(with: data) as? [String: Any],
                  let message = json["message"] as? String, !message.isEmpty else {
                logger.warning("Empty or invalid message in response")
                contentHandler(bestAttemptContent)
                return
            }
            
            // パーソナライズされたメッセージで通知本文を更新
            bestAttemptContent.body = message
            
            // nudgeIdをuserInfoに追加（フィードバック用）
            if let nudgeId = json["nudgeId"] as? String {
                var updatedUserInfo = bestAttemptContent.userInfo
                updatedUserInfo["nudgeId"] = nudgeId
                bestAttemptContent.userInfo = updatedUserInfo
            }
            
            logger.info("Updated notification with personalized message: \(message.prefix(30))...")
            contentHandler(bestAttemptContent)
            
        } catch {
            logger.error("Failed to fetch pre-reminder message: \(error.localizedDescription)")
            contentHandler(bestAttemptContent)
        }
    }
    
    /// Bundled default words for notifications whose payload or fetched
    /// message would otherwise be empty. Rotates by day so the fallback is
    /// not the same sentence forever. Language follows the payload's
    /// language hint when present, else the device locale.
    static func defaultWord(for userInfo: [AnyHashable: Any]) -> String {
        let language = (userInfo["language"] as? String) ?? Locale.current.language.languageCode?.identifier ?? "en"
        let words = language.hasPrefix("ja") ? jaWords : enWords
        let dayOfYear = Calendar.current.ordinality(of: .day, in: .year, for: Date()) ?? 1
        return words[(dayOfYear - 1) % words.count]
    }

    private static let enWords = [
        "You do not have to fix your whole life today. Just take the next kind step.",
        "This hard moment is weather, not the sky. It will move, and so will you.",
        "Breathe in slowly. Breathe out slower. You are still here, and that is enough.",
        "You have survived every difficult day so far. This one is no different.",
        "Be as gentle with yourself today as you would be with someone you love.",
        "Nothing about this moment is permanent. Let it pass through, not over you."
    ]

    private static let jaWords = [
        "今日は人生全部を直さなくていい。次の一歩だけ、やさしく進もう。",
        "つらい瞬間は天気のようなもの。空そのものじゃない。やがて移ろっていく。",
        "ゆっくり吸って、もっとゆっくり吐いて。ここにいる、それで十分。",
        "これまでのつらい日を、全部越えてきた。今日も同じように越えられる。",
        "大切な人に接するように、今日は自分にもやさしくしてみよう。",
        "この瞬間はずっと続かない。通過させよう、押しつぶされずに。"
    ]

    override func serviceExtensionTimeWillExpire() {
        // 時間切れの場合はデフォルトメッセージで表示
        if let contentHandler = contentHandler, let bestAttemptContent = bestAttemptContent {
            contentHandler(bestAttemptContent)
        }
    }
}
