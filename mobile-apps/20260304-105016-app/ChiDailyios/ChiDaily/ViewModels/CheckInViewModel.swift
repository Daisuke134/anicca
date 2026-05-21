import SwiftUI
import SwiftData

@Observable
final class CheckInViewModel {
    var currentQuestion = 0
    var answers = [Int](repeating: 3, count: 5)
    var isAnalyzing = false
    var result: CheckIn?
    var error: String?

    private let foundationModels = FoundationModelsService()
    private let healthKit = HealthKitService()

    let questions: [CheckInQuestion] = [
        CheckInQuestion(key: "energy", title: NSLocalizedString("How is your energy today?", comment: "")),
        CheckInQuestion(key: "sleep", title: NSLocalizedString("How was your sleep last night?", comment: "")),
        CheckInQuestion(key: "digestion", title: NSLocalizedString("How is your digestion today?", comment: "")),
        CheckInQuestion(key: "emotions", title: NSLocalizedString("How are you feeling emotionally?", comment: "")),
        CheckInQuestion(key: "physical", title: NSLocalizedString("How does your body feel physically?", comment: ""))
    ]

    func selectAnswer(_ value: Int) {
        answers[currentQuestion] = value
    }

    func nextQuestion() {
        if currentQuestion < 4 {
            currentQuestion += 1
        }
    }

    func previousQuestion() {
        if currentQuestion > 0 {
            currentQuestion -= 1
        }
    }

    func submitCheckIn(modelContext: ModelContext) async {
        isAnalyzing = true
        defer { isAnalyzing = false }
        do {
            let (constitution, recommendations) = try await foundationModels.analyze(
                energy: answers[0], sleep: answers[1], digestion: answers[2],
                emotion: answers[3], physical: answers[4]
            )
            let checkIn = CheckIn(
                energyLevel: answers[0], sleepQuality: answers[1],
                digestionComfort: answers[2], emotionalState: answers[3],
                physicalSensation: answers[4],
                constitutionType: constitution.rawValue,
                foodRecommendation: recommendations.first(where: { $0.category == .food })?.body ?? "",
                movementRecommendation: recommendations.first(where: { $0.category == .movement })?.body ?? "",
                restRecommendation: recommendations.first(where: { $0.category == .rest })?.body ?? ""
            )
            modelContext.insert(checkIn)
            result = checkIn
            await healthKit.logCheckIn(date: checkIn.date)
        } catch {
            self.error = error.localizedDescription
        }
    }
}

struct CheckInQuestion {
    let key: String
    let title: String
}
