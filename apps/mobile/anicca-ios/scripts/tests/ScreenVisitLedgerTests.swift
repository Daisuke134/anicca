import Foundation

@main
struct ScreenVisitLedgerTests {
    static func main() {
        duplicateAppearanceKeepsOriginalVisitAndDuration()
        forwardAndBackNavigationCloseThePriorVisit()
        backgroundClearDoesNotCreateAnExit()
        print("ScreenVisitLedgerTests: PASS")
    }

    private static func duplicateAppearanceKeepsOriginalVisitAndDuration() {
        var ledger = ScreenVisitLedger()
        let start = Date(timeIntervalSince1970: 1_000)

        guard ledger.enter(screenID: "onboarding.goal", screenInstanceID: "goal-1", flowID: "onboarding", at: start)
            == .entered(previousExit: nil),
              ledger.enter(screenID: "onboarding.goal", screenInstanceID: "goal-1", flowID: "onboarding", at: start.addingTimeInterval(4))
            == .ignored,
              ledger.exit(nextScreenID: "paywall", at: start.addingTimeInterval(5))
            == ScreenVisitLedger.Exit(
                screenID: "onboarding.goal",
                screenInstanceID: "goal-1",
                flowID: "onboarding",
                nextScreenID: "paywall",
                observedDurationMS: 5_000
            ) else {
            fatalError("Repeated appearance must not restart or duplicate the same screen visit")
        }
    }

    private static func forwardAndBackNavigationCloseThePriorVisit() {
        var ledger = ScreenVisitLedger()
        let start = Date(timeIntervalSince1970: 2_000)
        _ = ledger.enter(screenID: "onboarding.goal", screenInstanceID: "goal-1", flowID: "onboarding", at: start)

        guard ledger.enter(screenID: "paywall", screenInstanceID: "paywall-1", flowID: "onboarding", at: start.addingTimeInterval(5))
            == .entered(previousExit: ScreenVisitLedger.Exit(
                screenID: "onboarding.goal",
                screenInstanceID: "goal-1",
                flowID: "onboarding",
                nextScreenID: "paywall",
                observedDurationMS: 5_000
            )),
              ledger.enter(screenID: "onboarding.goal", screenInstanceID: "goal-2", flowID: "onboarding", at: start.addingTimeInterval(8))
            == .entered(previousExit: ScreenVisitLedger.Exit(
                screenID: "paywall",
                screenInstanceID: "paywall-1",
                flowID: "onboarding",
                nextScreenID: "onboarding.goal",
                observedDurationMS: 3_000
            )) else {
            fatalError("Forward and back navigation must close each prior visit with the actual next screen")
        }
    }

    private static func backgroundClearDoesNotCreateAnExit() {
        var ledger = ScreenVisitLedger()
        let start = Date(timeIntervalSince1970: 3_000)
        _ = ledger.enter(screenID: "feed", screenInstanceID: "feed-1", flowID: "feed", at: start)
        ledger.clear()

        guard ledger.exit(nextScreenID: "feed", at: start.addingTimeInterval(20)) == nil,
              ledger.enter(screenID: "feed", screenInstanceID: "feed-2", flowID: "feed", at: start.addingTimeInterval(21))
            == .entered(previousExit: nil) else {
            fatalError("Backgrounding must clear a visit without reporting an exit")
        }
    }
}
