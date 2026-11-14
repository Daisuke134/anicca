import Foundation

@main
struct OnboardingJourneyTests {
    static func main() {
        let journey = OnboardingStep.initialJourney
        precondition(journey == [.welcome, .goal, .name, .painPoints, .struggleFreq, .planReveal, .nudgeTimes, .notifications])
        precondition(OnboardingStep.welcome.nextInitialStep == .goal)
        precondition(OnboardingStep.goal.nextInitialStep == .name, "Name must be a separate question")
        precondition(OnboardingStep.name.nextInitialStep == .painPoints)
        precondition(OnboardingStep.painPoints.nextInitialStep == .struggleFreq)
        precondition(OnboardingStep.struggleFreq.nextInitialStep == .planReveal)
        precondition(OnboardingStep.planReveal.nextInitialStep == .nudgeTimes)
        precondition(OnboardingStep.nudgeTimes.nextInitialStep == .notifications)
        precondition(OnboardingStep.notifications.nextInitialStep == nil)
        precondition(OnboardingStep.welcome.resumableInitialStep == .welcome)
        precondition(OnboardingStep.processing.resumableInitialStep == .planReveal)
        precondition(OnboardingStep.comparison.resumableInitialStep == .planReveal)
        precondition(OnboardingStep.name.rawValue == 9, "New steps must not renumber persisted answers")
        for old in OnboardingStep.allCases {
            precondition(journey.contains(old.resumableInitialStep), "Every saved step must resume in the current journey")
        }
        print("OnboardingJourneyTests: PASS")
    }
}
