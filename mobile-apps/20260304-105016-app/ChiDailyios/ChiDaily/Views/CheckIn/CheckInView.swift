import SwiftUI
import SwiftData

struct CheckInView: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var modelContext
    @State private var viewModel = CheckInViewModel()

    let options: [(emoji: String, label: String)] = [
        ("😴", NSLocalizedString("Very Low", comment: "")),
        ("😑", NSLocalizedString("Low", comment: "")),
        ("😊", NSLocalizedString("Moderate", comment: "")),
        ("😄", NSLocalizedString("Good", comment: "")),
        ("🌟", NSLocalizedString("Excellent", comment: ""))
    ]

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                progressBar
                if viewModel.isAnalyzing {
                    analyzingView
                } else if let result = viewModel.result {
                    ResultView(checkIn: result, onDone: { dismiss() })
                } else {
                    questionView
                }
            }
            .navigationTitle(NSLocalizedString("Today's Check-in", comment: ""))
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button(NSLocalizedString("Cancel", comment: "")) { dismiss() }
                }
            }
        }
    }

    private var progressBar: some View {
        GeometryReader { geo in
            ZStack(alignment: .leading) {
                Rectangle().fill(Color.secondary.opacity(0.2))
                Rectangle()
                    .fill(Color.chiAccent)
                    .frame(width: geo.size.width * CGFloat(viewModel.currentQuestion + 1) / 5)
                    .animation(.easeInOut, value: viewModel.currentQuestion)
            }
        }
        .frame(height: 4)
    }

    private var questionView: some View {
        VStack(spacing: Spacing.lg) {
            Text(viewModel.questions[viewModel.currentQuestion].title)
                .font(.headline)
                .multilineTextAlignment(.center)
                .padding(.horizontal, Spacing.lg)

            VStack(spacing: Spacing.sm) {
                ForEach(0..<5) { index in
                    let option = options[index]
                    QuestionRow(
                        option: index + 1,
                        label: option.label,
                        emoji: option.emoji,
                        isSelected: viewModel.answers[viewModel.currentQuestion] == index + 1,
                        onTap: { viewModel.selectAnswer(index + 1) }
                    )
                }
            }
            .padding(.horizontal, Spacing.md)

            Spacer()

            HStack(spacing: Spacing.md) {
                if viewModel.currentQuestion > 0 {
                    Button(NSLocalizedString("Back", comment: "")) {
                        viewModel.previousQuestion()
                    }
                    .buttonStyle(.bordered)
                }
                if viewModel.currentQuestion < 4 {
                    PrimaryButton(title: NSLocalizedString("Next →", comment: "")) {
                        viewModel.nextQuestion()
                    }
                } else {
                    PrimaryButton(title: NSLocalizedString("Get My Plan", comment: "")) {
                        Task { await viewModel.submitCheckIn(modelContext: modelContext) }
                    }
                }
            }
            .padding(.horizontal, Spacing.md)
            .padding(.bottom, Spacing.lg)
        }
    }

    private var analyzingView: some View {
        VStack(spacing: Spacing.lg) {
            Spacer()
            ProgressView()
                .scaleEffect(1.5)
            Text(NSLocalizedString("Analyzing your constitution...", comment: ""))
                .font(.headline)
                .foregroundStyle(.secondary)
            Spacer()
        }
    }
}
