import Foundation

@main
struct ScreenVisitLedgerTests {
    static func main() {
        duplicateAppearanceKeepsOriginalVisitAndDuration()
        forwardAndBackNavigationCloseThePriorVisit()
        backgroundClearDoesNotCreateAnExit()
        backgroundResumeTracksNextExplicitTransition()
        foregroundNavigationSupersedesSuspendedVisit()
        sessionResetDropsActiveAndSuspendedVisitsAndRotatesID()
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

    private static func backgroundResumeTracksNextExplicitTransition() {
        var ledger = ScreenVisitLedger()
        let start = Date(timeIntervalSince1970: 4_000)
        _ = ledger.enter(screenID: "onboarding.goal", screenInstanceID: "goal-1", flowID: "onboarding", at: start)
        ledger.suspend()

        guard ledger.exit(nextScreenID: "onboarding.pain_points", at: start.addingTimeInterval(30)) == nil,
              let resumed = ledger.resume(at: start.addingTimeInterval(31), screenInstanceID: "goal-2"),
              resumed.screenID == "onboarding.goal",
              resumed.screenInstanceID == "goal-2",
              resumed.flowID == "onboarding",
              resumed.enteredAt == start.addingTimeInterval(31),
              ledger.enter(screenID: "onboarding.pain_points", screenInstanceID: "pain-1", flowID: "onboarding", at: start.addingTimeInterval(34))
                == .entered(previousExit: ScreenVisitLedger.Exit(
                    screenID: "onboarding.goal",
                    screenInstanceID: "goal-2",
                    flowID: "onboarding",
                    nextScreenID: "onboarding.pain_points",
                    observedDurationMS: 3_000
                )) else {
            fatalError("Foreground resume must create a fresh visit that closes on the next explicit screen")
        }
    }

    private static func sessionResetDropsActiveAndSuspendedVisitsAndRotatesID() {
        var ledger = ScreenVisitLedger()
        let start = Date(timeIntervalSince1970: 5_000)
        let oldSessionID = ledger.sessionID
        _ = ledger.enter(screenID: "feed.settings", screenInstanceID: "settings-1", flowID: "feed", at: start)
        ledger.suspend()
        ledger.resetSession()

        guard ledger.sessionID != oldSessionID,
              ledger.currentVisit == nil,
              ledger.suspendedVisit == nil,
              ledger.resume(at: start.addingTimeInterval(1), screenInstanceID: "settings-2") == nil,
              ledger.enter(screenID: "onboarding.welcome", screenInstanceID: "welcome-1", flowID: "onboarding", at: start.addingTimeInterval(2))
                == .entered(previousExit: nil) else {
            fatalError("Sign-out must drop prior visits and rotate the analytics session identity")
        }
    }

    private static func foregroundNavigationSupersedesSuspendedVisit() {
        var ledger = ScreenVisitLedger()
        let start = Date(timeIntervalSince1970: 6_000)
        _ = ledger.enter(screenID: "feed", screenInstanceID: "feed-1", flowID: "feed", at: start)
        ledger.suspend()

        guard ledger.enter(screenID: "feed.saved", screenInstanceID: "saved-1", flowID: "feed", at: start.addingTimeInterval(1))
                == .entered(previousExit: nil),
              ledger.resume(at: start.addingTimeInterval(2), screenInstanceID: "feed-2") == nil,
              ledger.currentVisit?.screenID == "feed.saved" else {
            fatalError("A foreground route must replace the suspended screen before resume")
        }
    }
}
