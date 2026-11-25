import SwiftUI

/// Poyo on screen. The face is an asset; the MOTION is code state
/// (`PoyoState`), never a video file:
///
/// - idle: slow breathing (scale) + gentle bob
/// - happy: soft bounce
/// - waiting: slow sway, sleepy face
/// - thinking: small side-to-side tilt pulses
/// - error: one small shake, then still (sad face — Poyo sits with you, no blame)
/// - celebrating: repeated happy hops (laughing face)
///
/// Decorative layer by design: if the image fails to load the view renders
/// nothing and never affects the words around it (home must never be empty
/// because of a mascot). The sprout gag (spec §3: "every day a little
/// different") is a deterministic rotation/scale wobble derived from a seed
/// (the current quote's id), so the same quote always shows the same Poyo.
struct PoyoView: View {
    let state: PoyoState
    var size: CGFloat = 64
    /// Seed for the sprout/shape gag — pass the current quote id on home.
    var seed: String = ""

    @State private var motionPhase = false
    @State private var shakeOffset: CGFloat = 0
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    init(expression: PoyoExpression, size: CGFloat = 64, seed: String = "") {
        self.state = PoyoState.from(expression: expression)
        self.size = size
        self.seed = seed
    }

    init(state: PoyoState, size: CGFloat = 64, seed: String = "") {
        self.state = state
        self.size = size
        self.seed = seed
    }

    /// Deterministic -1...1 wobble from the seed (stable per quote).
    private var gagWobble: Double {
        guard !seed.isEmpty else { return 0 }
        let hash = abs(seed.hashValue % 100)
        return Double(hash) / 50.0 - 1.0
    }

    private var breathingScale: CGFloat {
        guard !reduceMotion else { return 1 }
        switch state {
        case .idle, .waiting, .thinking:
            return motionPhase ? 1.04 : 0.98
        case .happy:
            return motionPhase ? 1.07 : 1.0
        case .celebrating:
            return motionPhase ? 1.10 : 0.96
        case .error:
            return 1
        }
    }

    private var bobOffset: CGFloat {
        guard !reduceMotion else { return 0 }
        switch state {
        case .idle, .thinking:
            return motionPhase ? -2 : 2
        case .happy:
            return motionPhase ? -4 : 0
        case .waiting:
            return motionPhase ? 1 : 3
        case .celebrating:
            return motionPhase ? -8 : 0
        case .error:
            return 0
        }
    }

    private var swayDegrees: Double {
        guard !reduceMotion else { return gagWobble * 2 }
        switch state {
        case .waiting:
            return (motionPhase ? 3.0 : -3.0) + gagWobble * 2
        case .thinking:
            return (motionPhase ? 2.0 : -2.0) + gagWobble * 2
        default:
            return gagWobble * 2
        }
    }

    private var motionAnimation: Animation {
        switch state {
        case .idle:
            return .easeInOut(duration: 2.4).repeatForever(autoreverses: true)
        case .waiting:
            return .easeInOut(duration: 3.2).repeatForever(autoreverses: true)
        case .thinking:
            return .easeInOut(duration: 0.9).repeatForever(autoreverses: true)
        case .happy:
            return .easeInOut(duration: 1.1).repeatForever(autoreverses: true)
        case .celebrating:
            return .easeInOut(duration: 0.55).repeatForever(autoreverses: true)
        case .error:
            return .default
        }
    }

    var body: some View {
        Image(state.expression.imageName)
            .resizable()
            .scaledToFit()
            .frame(width: size, height: size)
            .scaleEffect(breathingScale)
            .rotationEffect(.degrees(swayDegrees))
            .offset(x: shakeOffset, y: bobOffset)
            .accessibilityLabel(Text("ぽよ"))
            .onAppear {
                motionPhase = true
                if state == .error { playShake() }
            }
            .animation(motionAnimation, value: motionPhase)
    }

    /// One short shake for the error state, then stillness.
    private func playShake() {
        guard !reduceMotion else { return }
        let steps: [CGFloat] = [-4, 4, -3, 3, 0]
        for (index, value) in steps.enumerated() {
            DispatchQueue.main.asyncAfter(deadline: .now() + Double(index) * 0.07) {
                withAnimation(.linear(duration: 0.07)) { shakeOffset = value }
            }
        }
    }
}
