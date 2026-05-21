import Foundation

final class AIStretchService {
    private let libraryService: StretchLibraryService

    init(libraryService: StretchLibraryService) {
        self.libraryService = libraryService
    }

    func generateRoutine(
        painAreas: Set<PainArea>,
        history: [StretchSession],
        exerciseCount: Int = 3,
        isPremium: Bool = false
    ) -> [StretchExercise] {
        let allExercises: [StretchExercise]
        if isPremium {
            allExercises = libraryService.exercises(for: painAreas)
        } else {
            allExercises = libraryService.freeExercises(for: painAreas)
        }

        let recentIds = Set(history.suffix(3).flatMap(\.exercises).map(\.id))
        let available = allExercises.filter { !recentIds.contains($0.id) }

        if available.count >= exerciseCount {
            return Array(available.shuffled().prefix(exerciseCount))
        }
        return Array(allExercises.shuffled().prefix(exerciseCount))
    }
}
