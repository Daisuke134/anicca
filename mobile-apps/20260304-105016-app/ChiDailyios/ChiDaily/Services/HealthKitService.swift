import HealthKit

actor HealthKitService {
    private let store = HKHealthStore()

    func requestAuthorization() async -> Bool {
        guard HKHealthStore.isHealthDataAvailable() else { return false }
        let typesToWrite: Set<HKSampleType> = [
            HKObjectType.categoryType(forIdentifier: .mindfulSession)!
        ]
        do {
            try await store.requestAuthorization(toShare: typesToWrite, read: [])
            return true
        } catch {
            return false
        }
    }

    func logCheckIn(date: Date) async {
        guard HKHealthStore.isHealthDataAvailable() else { return }
        let type = HKObjectType.categoryType(forIdentifier: .mindfulSession)!
        let sample = HKCategorySample(
            type: type,
            value: HKCategoryValue.notApplicable.rawValue,
            start: date,
            end: date.addingTimeInterval(120)
        )
        do {
            try await store.save(sample)
        } catch {
            // Silent fail — non-critical
        }
    }
}
