import Testing
@testable import ChiDaily

struct CheckInViewModelTests {

    @Test func initialState() {
        let vm = CheckInViewModel()
        #expect(vm.currentQuestion == 0)
        #expect(vm.answers == [3, 3, 3, 3, 3])
        #expect(vm.isAnalyzing == false)
        #expect(vm.result == nil)
    }

    @Test func questionsCount() {
        let vm = CheckInViewModel()
        #expect(vm.questions.count == 5)
    }

    @Test func nextQuestionAdvances() {
        let vm = CheckInViewModel()
        vm.nextQuestion()
        #expect(vm.currentQuestion == 1)
    }

    @Test func previousQuestionRetreats() {
        let vm = CheckInViewModel()
        vm.nextQuestion()
        vm.previousQuestion()
        #expect(vm.currentQuestion == 0)
    }

    @Test func previousQuestionAtZeroStaysZero() {
        let vm = CheckInViewModel()
        vm.previousQuestion()
        #expect(vm.currentQuestion == 0)
    }

    @Test func selectAnswerUpdatesAnswers() {
        let vm = CheckInViewModel()
        vm.selectAnswer(5)
        #expect(vm.answers[0] == 5)
    }

    @Test func nextQuestionAtEndStaysAtEnd() {
        let vm = CheckInViewModel()
        for _ in 0..<10 { vm.nextQuestion() }
        #expect(vm.currentQuestion == 4)
    }
}
