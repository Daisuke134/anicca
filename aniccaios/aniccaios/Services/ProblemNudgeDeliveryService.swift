import Foundation

struct ProblemNudgeDelivery: Codable {
    let id: String
    let problemType: String
    let scheduledTime: String
    let deliveryDayLocal: String?
    let timezone: String?
    let lang: String?
    let variantIndex: Int
    let title: String
    let hook: String
    let detail: String
}

enum ProblemNudgeDeliveryError: Error {
    case invalidResponse
}

final class ProblemNudgeDeliveryService {
    static let shared = ProblemNudgeDeliveryService()
    private init() {}

    func fetchDelivery(id: String) async throws -> ProblemNudgeDelivery {
        var request = URLRequest(url: AppConfig.nudgeDeliveryURL(id: id))
        request.httpMethod = "GET"
        request.setValue(AppState.shared.resolveDeviceId(), forHTTPHeaderField: "device-id")

        let (data, response) = try await NetworkSessionManager.shared.session.data(for: request)
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            throw ProblemNudgeDeliveryError.invalidResponse
        }
        return try JSONDecoder().decode(ProblemNudgeDelivery.self, from: data)
    }
}

