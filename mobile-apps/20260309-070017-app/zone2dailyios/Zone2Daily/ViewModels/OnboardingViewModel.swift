// File: ViewModels/OnboardingViewModel.swift
// F-002: Onboarding state management
// Stub for US-006a — full implementation in US-006b

import Foundation
import Observation

@Observable
final class OnboardingViewModel {
    var currentStep: Int = 0
    var age: Int = 30
    var isComplete: Bool = false

    func goNext() {
        if currentStep < 3 {
            currentStep += 1
        } else {
            isComplete = true
        }
    }

    func complete() {
        isComplete = true
    }
}
