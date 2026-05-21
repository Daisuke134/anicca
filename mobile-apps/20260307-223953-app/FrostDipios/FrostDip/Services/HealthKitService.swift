import Foundation
import HealthKit

/// Service classes (reference types) are exempt from the struct immutability rule.
final class HealthKitService: HealthKitServiceProtocol {
    private let healthStore = HKHealthStore()
    private var heartRateQuery: HKAnchoredObjectQuery?
    private var samples: [Double] = []
    private let samplesLock = NSLock()

    var isAvailable: Bool {
        HKHealthStore.isHealthDataAvailable()
    }

    func requestAuthorization() async throws {
        let heartRateType = HKQuantityType(.heartRate)
        try await healthStore.requestAuthorization(toShare: [], read: [heartRateType])
    }

    func startHeartRateMonitoring(onUpdate: @escaping (Double) -> Void) {
        samples = []
        let heartRateType = HKQuantityType(.heartRate)
        let predicate = HKQuery.predicateForSamples(withStart: Date(), end: nil)

        let query = HKAnchoredObjectQuery(
            type: heartRateType,
            predicate: predicate,
            anchor: nil,
            limit: HKObjectQueryNoLimit
        ) { [weak self] _, newSamples, _, _, _ in
            self?.processSamples(newSamples, onUpdate: onUpdate)
        }

        query.updateHandler = { [weak self] _, newSamples, _, _, _ in
            self?.processSamples(newSamples, onUpdate: onUpdate)
        }

        healthStore.execute(query)
        heartRateQuery = query
    }

    func stopHeartRateMonitoring() -> (avg: Double?, max: Double?, samples: [Double]) {
        if let query = heartRateQuery {
            healthStore.stop(query)
            heartRateQuery = nil
        }

        samplesLock.lock()
        let captured = samples
        samples = []
        samplesLock.unlock()

        guard !captured.isEmpty else { return (nil, nil, []) }

        let avg = captured.reduce(0, +) / Double(captured.count)
        let max = captured.max()
        return (avg: Optional(avg), max: max, samples: captured)
    }

    private func processSamples(_ newSamples: [HKSample]?, onUpdate: @escaping (Double) -> Void) {
        guard let heartRateSamples = newSamples as? [HKQuantitySample] else { return }
        for sample in heartRateSamples {
            let bpm = sample.quantity.doubleValue(for: HKUnit.count().unitDivided(by: .minute()))
            samplesLock.lock()
            samples.append(bpm)
            samplesLock.unlock()
            DispatchQueue.main.async { onUpdate(bpm) }
        }
    }
}
