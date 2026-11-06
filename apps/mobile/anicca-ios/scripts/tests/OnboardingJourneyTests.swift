import Foundation

@main
struct OnboardingJourneyTests {
    static func main() {
        let journey = OnboardingStep.initialJourney
        precondition(journey.first == .goal, "First value must not be delayed by a welcome tour")
        precondition(OnboardingStep.goal.nextInitialStep == .planReveal, "Goal selection must open the real affirmation")
        precondition(OnboardingStep.planReveal.nextInitialStep == .nudgeTimes)
        precondition(OnboardingStep.nudgeTimes.nextInitialStep == .notifications)
        precondition(OnboardingStep.notifications.nextInitialStep == nil, "Notification refusal must still finish the questions")
        precondition(OnboardingStep.welcome.resumableInitialStep == .goal)
        precondition(OnboardingStep.painPoints.resumableInitialStep == .planReveal)
        precondition(OnboardingStep.processing.resumableInitialStep == .planReveal)
        precondition(OnboardingStep.notifications.resumableInitialStep == .notifications)
        for old in OnboardingStep.allCases {
            precondition(journey.contains(old.resumableInitialStep), "Every saved step must resume in the current journey")
        }
        print("OnboardingJourneyTests: PASS")
    }
}
