import Foundation

final class StretchLibraryService {
    private var allExercises: [StretchExercise] = []

    func loadFromBundle() {
        guard let url = Bundle.main.url(forResource: "StretchLibrary", withExtension: "json"),
              let data = try? Data(contentsOf: url),
              let exercises = try? JSONDecoder().decode([StretchExercise].self, from: data)
        else { return }
        allExercises = exercises
    }

    func exercises(for painAreas: Set<PainArea>) -> [StretchExercise] {
        allExercises.filter { painAreas.contains($0.category) }
    }

    func freeExercises(for painAreas: Set<PainArea>) -> [StretchExercise] {
        exercises(for: painAreas).filter { !$0.isPremium }
    }

    var all: [StretchExercise] { allExercises }
}
