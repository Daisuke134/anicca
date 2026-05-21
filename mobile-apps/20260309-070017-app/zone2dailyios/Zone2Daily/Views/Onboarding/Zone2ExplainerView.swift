// File: Views/Onboarding/Zone2ExplainerView.swift
// Onboarding Step 2: Explain Zone 2 training
// Stub for US-006a — full implementation in US-006b

import SwiftUI

struct Zone2ExplainerView: View {
    @Bindable var viewModel: OnboardingViewModel

    var body: some View {
        VStack(spacing: 32) {
            Spacer()

            Image(systemName: "heart.fill")
                .font(.system(size: 80))
                .foregroundStyle(.brandPrimary)

            Text("What is Zone 2?")
                .font(.largeTitle.bold())
                .accessibilityIdentifier("onboarding_zone2_title")

            VStack(alignment: .leading, spacing: 16) {
                ExplainerRow(icon: "flame.fill", text: "Burns fat as primary fuel source")
                ExplainerRow(icon: "lungs.fill", text: "Builds aerobic base without fatigue")
                ExplainerRow(icon: "chart.line.uptrend.xyaxis", text: "Improves mitochondrial density")
                ExplainerRow(icon: "target", text: "150 min/week is the scientific target")
            }

            Text("Goal: \(Zone2Calculator.zone2MinHR(age: viewModel.age))–\(Zone2Calculator.zone2MaxHR(age: viewModel.age)) bpm for you")
                .font(.headline)
                .foregroundStyle(.brandPrimary)
                .accessibilityIdentifier("onboarding_zone2_range")

            Spacer()

            Button("Got it!") { viewModel.goNext() }
                .buttonStyle(.borderedProminent)
                .tint(.brandPrimary)
                .accessibilityIdentifier("btn_continue_explainer")
        }
        .padding(32)
    }
}

struct ExplainerRow: View {
    let icon: String
    let text: String

    var body: some View {
        Label(text, systemImage: icon)
            .font(.body)
    }
}
