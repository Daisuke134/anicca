import Foundation

struct ScreenVisitLedger {
    struct Visit {
        let screenID: String
        let screenInstanceID: String
        let flowID: String
        let enteredAt: Date
    }

    struct Exit: Equatable {
        let screenID: String
        let screenInstanceID: String
        let flowID: String
        let nextScreenID: String
        let observedDurationMS: Int
    }

    enum EntryResult: Equatable {
        case ignored
        case entered(previousExit: Exit?)
    }

    private(set) var currentVisit: Visit?

    mutating func enter(screenID: String, screenInstanceID: String, flowID: String, at enteredAt: Date) -> EntryResult {
        guard currentVisit?.screenInstanceID != screenInstanceID else { return .ignored }
        let previousExit = exit(nextScreenID: screenID, at: enteredAt)
        currentVisit = Visit(
            screenID: screenID,
            screenInstanceID: screenInstanceID,
            flowID: flowID,
            enteredAt: enteredAt
        )
        return .entered(previousExit: previousExit)
    }

    mutating func exit(nextScreenID: String, screenInstanceID: String? = nil, at: Date) -> Exit? {
        guard let visit = currentVisit,
              screenInstanceID == nil || visit.screenInstanceID == screenInstanceID else { return nil }
        currentVisit = nil
        return Exit(
            screenID: visit.screenID,
            screenInstanceID: visit.screenInstanceID,
            flowID: visit.flowID,
            nextScreenID: nextScreenID,
            observedDurationMS: max(0, Int(at.timeIntervalSince(visit.enteredAt) * 1_000))
        )
    }

    mutating func clear() {
        currentVisit = nil
    }
}
