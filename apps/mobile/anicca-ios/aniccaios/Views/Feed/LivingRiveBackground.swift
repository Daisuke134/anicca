import SwiftUI
import RiveRuntime

/// The bundled artwork loops Ambient and briefly plays a transition on WordChanged.
private final class LivingRiveAnimation: ObservableObject {
    static let assetName = "living_home"
    static let artboardName = "LivingHome"
    static let stateMachineName = "Living"
    static let wordChangedTrigger = "WordChanged"

    let viewModel: RiveViewModel?

    init() {
        // Missing/empty resources must never reach Rive's force-trying convenience init.
        guard let url = Bundle.main.url(forResource: Self.assetName, withExtension: "riv"),
              let data = try? Data(contentsOf: url), !data.isEmpty else {
            viewModel = nil
            return
        }
        do {
            let model = try RiveModel(fileName: Self.assetName, loadCdn: false)
            try model.setArtboard(Self.artboardName)
            try model.setStateMachine(Self.stateMachineName)
            guard model.stateMachine?.getTrigger(Self.wordChangedTrigger) != nil else {
                viewModel = nil
                return
            }
            viewModel = RiveViewModel(
                model, stateMachineName: Self.stateMachineName,
                fit: .cover, autoPlay: false
            )
        } catch {
            // A missing or incompatible export leaves the existing theme intact.
            viewModel = nil
        }
    }
}

struct LivingRiveBackground: View {
    let wordID: String?
    @StateObject private var animation = LivingRiveAnimation()
    @Environment(\.scenePhase) private var scenePhase
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    private var canAnimate: Bool { scenePhase == .active && !reduceMotion }

    var body: some View {
        Group {
            if let viewModel = animation.viewModel {
                viewModel.view()
                    .opacity(0.3)
                    .onAppear { updatePlayback() }
                    .onDisappear { viewModel.pause() }
                    .onChange(of: canAnimate) { _ in updatePlayback() }
                    .onChange(of: wordID) { newID in
                        guard newID != nil, canAnimate else { return }
                        viewModel.triggerInput(LivingRiveAnimation.wordChangedTrigger)
                    }
            }
        }
        .allowsHitTesting(false)
        .accessibilityHidden(true)
    }

    private func updatePlayback() {
        if canAnimate {
            animation.viewModel?.play()
        } else {
            animation.viewModel?.pause()
        }
    }
}
