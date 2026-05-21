import Foundation

protocol HealthKitServiceProtocol {
    var isAvailable: Bool { get }
    func requestAuthorization() async throws
    func startHeartRateMonitoring(onUpdate: @escaping (Double) -> Void)
    func stopHeartRateMonitoring() -> (avg: Double?, max: Double?, samples: [Double])
}
