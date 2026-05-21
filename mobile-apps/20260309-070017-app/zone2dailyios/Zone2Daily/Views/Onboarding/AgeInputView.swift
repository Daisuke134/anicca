// File: Views/Onboarding/AgeInputView.swift
// SCR-001: Age input for Maffetone calculation
// DESIGN_SYSTEM §3 Spacing tokens, §2 Typography tokens

import SwiftUI
import SwiftData

struct AgeInputView: View {
    @Bindable var viewModel: OnboardingViewModel
    @Environment(\.modelContext) private var modelContext
    @Query private var profiles: [UserProfile]

    var isValid: Bool { viewModel.age >= 10 && viewModel.age <= 80 }

    var body: some View {
        VStack(spacing: Spacing.xl) {
            Spacer()

            Text("How old are you?")
                .font(.displayLarge)
                .multilineTextAlignment(.center)
                .accessibilityIdentifier("onboarding_age_title")

            Text("We use this to calculate your Zone 2 heart rate target.")
                .font(.bodyRegular)
                .foregroundStyle(Color.textSecondary)
                .multilineTextAlignment(.center)

            Text("\(viewModel.age)")
                .font(.system(size: 72, weight: .bold, design: .rounded))
                .foregroundStyle(Color.brandPrimary)
                .accessibilityIdentifier("onboarding_age_value")

            Slider(
                value: Binding(
                    get: { Double(viewModel.age) },
                    set: { viewModel.age = Int($0) }
                ),
                in: 10...80,
                step: 1
            )
            .tint(.brandPrimary)
            .accessibilityIdentifier("slider_age")

            HStack {
                Text("10")
                    .font(.labelSmall)
                    .foregroundStyle(Color.textSecondary)
                Spacer()
                Text("80")
                    .font(.labelSmall)
                    .foregroundStyle(Color.textSecondary)
            }

            if isValid {
                Text("Your Zone 2 HR: \(Zone2Calculator.zone2MinHR(age: viewModel.age))–\(Zone2Calculator.zone2MaxHR(age: viewModel.age)) bpm")
                    .font(.headlineMedium)
                    .foregroundStyle(Color.brandPrimary)
                    .accessibilityIdentifier("label_zone2_hr")
            }

            Spacer()

            Button("Continue") {
                saveProfile()
                viewModel.goNext()
            }
            .buttonStyle(.borderedProminent)
            .disabled(!isValid)
            .tint(.brandPrimary)
            .accessibilityIdentifier("btn_continue_age")
        }
        .padding(Spacing.xl)
    }

    private func saveProfile() {
        // Upsert: update existing profile if present, else insert
        if let existing = profiles.first {
            existing.age = viewModel.age
        } else {
            let profile = UserProfile(age: viewModel.age)
            modelContext.insert(profile)
        }
        try? modelContext.save()
    }
}
