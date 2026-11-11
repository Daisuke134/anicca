/// Reconciles a paywall choice against the latest available package instances.
/// Kept independent of RevenueCat so selection can be tested without StoreKit.
enum PaywallPackageSelection {
    static func resolve<Candidate: Identifiable>(
        packages: [Candidate],
        selectedID: Candidate.ID?,
        isAnnual: (Candidate) -> Bool,
        isMonthly: (Candidate) -> Bool
    ) -> Candidate? {
        if let selectedID,
           let current = packages.first(where: { $0.id == selectedID }) {
            return current
        }

        return packages.first(where: isAnnual) ?? packages.first(where: isMonthly)
    }

    static func containsCurrentInstance<Candidate: AnyObject>(_ candidate: Candidate, in candidates: [Candidate]) -> Bool {
        candidates.contains { $0 === candidate }
    }
}

/// Fails closed unless both the App Store region and its refreshed offering are known.
enum PaywallStorefrontEligibility {
    static func sameStorefront(first: String?, second: String?) -> Bool {
        first?.uppercased() == second?.uppercased()
    }

    static func includesLifetime(countryCode: String?, offeringCountryCode: String?) -> Bool {
        guard let countryCode, let offeringCountryCode else { return false }
        let currentCountry = countryCode.uppercased()
        return offeringCountryCode.uppercased() == currentCountry
    }

    static func allowsPurchase(
        packageIsLifetime: Bool,
        packageIsCurrent: Bool,
        countryCode: String?,
        offeringCountryCode: String?
    ) -> Bool {
        packageIsCurrent && (!packageIsLifetime || includesLifetime(
            countryCode: countryCode,
            offeringCountryCode: offeringCountryCode
        ))
    }
}


/// A/B gate for the paywall, driven by which RevenueCat offering the
/// RevenueCat Experiment assigned to this user (delivered as
/// `offerings.current`).
///
/// - Control offering `anicca_variant_b`: soft paywall — the onboarding
///   close button stays and tapping it completes onboarding for free.
/// - Treatment offering `anicca_variant_b_hard`: hard paywall — no close
///   button in onboarding; onboarding completes only on purchase/restore
///   entitlement.
///
/// Kept free of RevenueCat types so the assignment rules can be unit
/// tested. Decided 2026-11-08: hard paywall rolls out behind an A/B
/// experiment instead of the previous all-users soft gate.
enum PaywallGateVariant: String, Equatable {
    case soft
    case hard

    /// Offering identifier of the hard-paywall treatment offering.
    static let hardOfferingIdentifier = "anicca_variant_b_hard"

    /// RevenueCat Experiment identifier for this gate A/B (2026-11-08).
    /// Recorded on the `experiment_exposure` analytics event.
    static let experimentIdentifier = "HARD-PAYWALL-20261108"

    static func resolve(offeringIdentifier: String?) -> PaywallGateVariant {
        offeringIdentifier == hardOfferingIdentifier ? .hard : .soft
    }

    /// The close button (free exit) is shown for existing-user surfaces
    /// (any flow other than onboarding) regardless of the gate, and in
    /// onboarding only for the soft gate.
    static func showsCloseButton(flowID: String, variant: PaywallGateVariant) -> Bool {
        flowID != "onboarding" || variant == .soft
    }
}

enum PaywallOfferingSelection {
    static func isLatestRefresh(requestID: Int, currentRequestID: Int) -> Bool {
        requestID == currentRequestID
    }

    static func isUnchangedStorefrontRevision(startingRevision: Int, currentRevision: Int) -> Bool {
        startingRevision == currentRevision
    }

    static func resolve<Offering>(
        current: Offering?,
        all: [String: Offering],
        fallbackIdentifier: String,
        isUsableForAnicca: (Offering) -> Bool,
        identifier: (Offering) -> String
    ) -> Offering? {
        // A running RevenueCat Experiment delivers the assigned offering as
        // `current`. When that assignment is one of the experiment
        // offerings (control or treatment), it must win over the configured
        // fallback so the A/B split actually reaches the plan screen.
        if let current, isUsableForAnicca(current) {
            let currentIdentifier = identifier(current)
            if currentIdentifier == fallbackIdentifier
                || currentIdentifier == PaywallGateVariant.hardOfferingIdentifier {
                return current
            }
        }
        // The app's plan screen must include its configured Lifetime product,
        // even when the shared current offering points at legacy subscriptions.
        if let configured = all[fallbackIdentifier], isUsableForAnicca(configured) {
            return configured
        }
        if let current, isUsableForAnicca(current) {
            return current
        }
        return nil
    }

    static func isUsableAnicca(productIdentifiers: [String], hasAnnualOrMonthlyPackage: Bool) -> Bool {
        guard hasAnnualOrMonthlyPackage, !productIdentifiers.isEmpty else { return false }
        return productIdentifiers.allSatisfy { $0.hasPrefix("ai.anicca.app.ios.") }
    }
}

enum OnboardingPaywallDecision: Equatable {
    case completeOnboarding
    case presentPaywall

    static func resolve(freshEntitlement: Bool?, cachedEntitlement: Bool) -> Self {
        guard let freshEntitlement else {
            return cachedEntitlement ? .completeOnboarding : .presentPaywall
        }
        return freshEntitlement ? .completeOnboarding : .presentPaywall
    }
}
