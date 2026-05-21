import Foundation
import OSLog

/// Polls server for pending worker-sent nudges (/api/mobile/nudge/send),
/// schedules them as local notifications, then acks delivery.
///
/// This is a pragmatic substitute for push: it delivers reliably whenever the app becomes active.
@MainActor
final class ServerNudgeInboxService {
    static let shared = ServerNudgeInboxService()

    private let logger = Logger(subsystem: "com.anicca.ios", category: "ServerNudgeInboxService")
    private let defaults = UserDefaults.standard
    private let lastPullKey = "last_server_nudge_pull_at"

    private init() {}

    struct PendingNudge: Decodable {
        let nudgeId: String
        let domain: String
        let title: String?
        let message: String
        let problemType: String?
        let templateId: String?
        let metadata: [String: AnyDecodable]?
        let createdAt: String?
    }

    struct PendingResponse: Decodable {
        let nudges: [PendingNudge]
        let version: String?
    }

    struct AckResponse: Decodable {
        let acked: Int
    }

    func pullAndScheduleIfAuthorized(force: Bool = false) async {
        // Throttle to avoid spamming the server.
        if !force, let last = defaults.object(forKey: lastPullKey) as? Date {
            if Date().timeIntervalSince(last) < 10 * 60 { return }
        }
        defaults.set(Date(), forKey: lastPullKey)

        let isAllowed = await NotificationScheduler.shared.isAuthorizedForAlerts()
        if !isAllowed { return }

        do {
            let pending = try await fetchPending()
            guard !pending.isEmpty else { return }

            var ackIds: [String] = []
            for n in pending {
                await NotificationScheduler.shared.scheduleNudgeNow(
                    nudgeId: n.nudgeId,
                    domain: n.domain,
                    message: n.message,
                    userInfo: [
                        "domain": n.domain,
                        "templateId": n.templateId ?? "",
                        "problemType": n.problemType ?? "",
                        "source": "app-nudge-sender"
                    ]
                )
                ackIds.append(n.nudgeId)
            }

            _ = try await ack(nudgeIds: ackIds)
        } catch {
            logger.error("Failed to pull/ack pending nudges: \(error.localizedDescription, privacy: .public)")
        }
    }

    func fetchPending() async throws -> [PendingNudge] {
        var req = URLRequest(url: AppConfig.nudgePendingURL)
        req.httpMethod = "GET"
        applyLegacyHeaders(&req)

        let (data, response) = try await NetworkSessionManager.shared.session.data(for: req)
        guard let http = response as? HTTPURLResponse else { throw URLError(.badServerResponse) }
        guard (200..<300).contains(http.statusCode) else {
            throw NSError(domain: "ServerNudgeInboxService", code: http.statusCode)
        }
        let decoded = try JSONDecoder().decode(PendingResponse.self, from: data)
        // Only schedule nudges that have a message (defensive).
        return decoded.nudges.filter { !$0.message.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
    }

    func ack(nudgeIds: [String]) async throws -> Int {
        guard !nudgeIds.isEmpty else { return 0 }

        var req = URLRequest(url: AppConfig.nudgeAckURL)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        applyLegacyHeaders(&req)

        let body = ["nudgeIds": nudgeIds]
        req.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (data, response) = try await NetworkSessionManager.shared.session.data(for: req)
        guard let http = response as? HTTPURLResponse else { throw URLError(.badServerResponse) }
        guard (200..<300).contains(http.statusCode) else {
            throw NSError(domain: "ServerNudgeInboxService", code: http.statusCode)
        }
        let decoded = try JSONDecoder().decode(AckResponse.self, from: data)
        return decoded.acked
    }

    private func applyLegacyHeaders(_ req: inout URLRequest) {
        let deviceId = AppState.shared.resolveDeviceId()
        let userId: String
        switch AppState.shared.authStatus {
        case .signedIn(let credentials):
            userId = credentials.userId
        default:
            userId = deviceId
        }

        req.setValue(deviceId, forHTTPHeaderField: "device-id")
        req.setValue(userId, forHTTPHeaderField: "user-id")
    }
}

// Minimal AnyDecodable for decoding unknown JSON payloads
struct AnyDecodable: Decodable {
    let value: Any

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if let v = try? container.decode(String.self) { value = v; return }
        if let v = try? container.decode(Int.self) { value = v; return }
        if let v = try? container.decode(Double.self) { value = v; return }
        if let v = try? container.decode(Bool.self) { value = v; return }
        if let v = try? container.decode([String: AnyDecodable].self) { value = v.mapValues { $0.value }; return }
        if let v = try? container.decode([AnyDecodable].self) { value = v.map { $0.value }; return }
        value = NSNull()
    }
}

