import Foundation

@main
struct OnboardingJourneyTests {
    static func main() {
        let journey = OnboardingStep.initialJourney
        precondition(journey.first == .goal, "First value must not be delayed by a welcome tour")
        precondition(journey == [.goal, .painPoints, .struggleFreq, .source, .planReveal, .nudgeTimes, .notifications])
        precondition(OnboardingStep.goal.nextInitialStep == .painPoints)
        precondition(OnboardingStep.painPoints.nextInitialStep == .struggleFreq)
        precondition(OnboardingStep.struggleFreq.nextInitialStep == .source, "Source must follow struggle frequency")
        precondition(OnboardingStep.source.nextInitialStep == .planReveal, "Source must precede the personalized preview")
        precondition(OnboardingStep.planReveal.nextInitialStep == .nudgeTimes)
        precondition(OnboardingStep.nudgeTimes.nextInitialStep == .notifications)
        precondition(OnboardingStep.notifications.nextInitialStep == nil, "Notification refusal must still finish the questions")
        precondition(OnboardingStep.welcome.resumableInitialStep == .goal)
        precondition(OnboardingStep.painPoints.resumableInitialStep == .painPoints)
        precondition(OnboardingStep.source.resumableInitialStep == .source)
        precondition(OnboardingStep.processing.resumableInitialStep == .planReveal)
        precondition(OnboardingStep.notifications.resumableInitialStep == .notifications)
        for old in OnboardingStep.allCases {
            precondition(journey.contains(old.resumableInitialStep), "Every saved step must resume in the current journey")
        }
        let persistedSteps: [OnboardingStep] = [.welcome, .goal, .painPoints, .struggleFreq, .nudgeTimes, .processing, .planReveal, .comparison, .notifications, .source]
        for (rawValue, step) in persistedSteps.enumerated() {
            precondition(step.rawValue == rawValue, "Persisted step raw values must stay stable")
        }
        precondition(OnboardingStep.source.analyticsName == "source")
        precondition(OnboardingStep.migratedFromV7RawValue(9) == .notifications)
        precondition(OnboardingStep.migratedFromV6RawValue(9) == .nudgeTimes)
        print("OnboardingJourneyTests: PASS")
    }
}
