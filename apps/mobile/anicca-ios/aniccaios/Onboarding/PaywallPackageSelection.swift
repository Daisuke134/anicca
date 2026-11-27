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

/// Stable display ordering for paywall plan cards (Issue #9356: every plan
/// on sale is visible on the first screen). Lower rank sorts first; equal
/// ranks keep the offering's own order.
enum PaywallPlanOrdering {
    static func ordered<Candidate>(_ candidates: [Candidate], rank: (Candidate) -> Int) -> [Candidate] {
        candidates.enumerated()
            .sorted { lhs, rhs in
                let leftRank = rank(lhs.element)
                let rightRank = rank(rhs.element)
                if leftRank != rightRank { return leftRank < rightRank }
                return lhs.offset < rhs.offset
            }
            .map(\.element)
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


/// Soft entry applies even while RevenueCat still assigns the retired hard offering.
/// Keep historical identifiers for offering selection and analytics compatibility.
enum PaywallGateVariant: String, Equatable {
    case soft
    case hard

    static let hardOfferingIdentifier = "anicca_variant_b_hard"
    static let experimentIdentifier = "HARD-PAYWALL-20261108"

    static func resolve(offeringIdentifier: String?) -> PaywallGateVariant { .soft }

    static func showsCloseButton(flowID: String, variant: PaywallGateVariant) -> Bool { true }
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

/// Which plans the paywall sells (decided 2026-11-15 from primary
/// sources: RevenueCat — two plans is the most common layout, one plan
/// highlighted with a savings badge; Adapty — weekly plans drive 55.5%
/// of subscription revenue and convert install→trial at 9.8% vs 1.8%
/// for annual, try 2–3 plans and never show five; winner I am runs
/// three tiers). Three plans are on sale: annual first (highlighted as
/// best value, default selection, 3-day free trial), then weekly, then
/// lifetime. Monthly is not sold on the paywall — four choices made
/// people deliberate instead of deciding.
enum PaywallPlanDisplay {
    static func isVisible(planName: String) -> Bool {
        planName == "annual" || planName == "weekly" || planName == "lifetime"
    }

    static func rank(planName: String) -> Int {
        switch planName {
        case "annual": return 0
        case "weekly": return 1
        case "lifetime": return 2
        default: return 3
        }
    }
}

/// Single-offer layout (Issue #731): the paywall leads with one offer —
/// the annual plan and its free trial — and folds the remaining plans
/// behind a visible "Other plans" row.
///
/// The row expands in place rather than opening a sheet. Issue #9356
/// rejected the earlier hidden-sheet version because the Lifetime row
/// was cut off and the plans were unreachable from the first screen;
/// this keeps the single-offer focus without hiding anything: the row
/// itself is always on screen and one tap shows every plan.
enum PaywallOfferLayout {
    /// The one plan the paywall leads with.
    static let primaryPlanName = "annual"

    static func isPrimary(planName: String) -> Bool {
        planName == primaryPlanName
    }

    /// The "Other plans" row stays expanded while a folded plan is the
    /// selected one, so the user can always see what they are buying.
    static func isExpanded(manuallyExpanded: Bool, selectedPlanName: String?) -> Bool {
        guard let selectedPlanName else { return manuallyExpanded }
        return manuallyExpanded || !isPrimary(planName: selectedPlanName)
    }
}

/// Whether the paywall may be presented at all (user rule, 2026-11-15:
/// a user who already pays never sees a paywall; everyone else does).
/// This is the single decision point every paywall entry uses, mirroring
/// the documented defaults of Superwall and RevenueCat: read the
/// entitlement before presenting, and present only to non-subscribers.
/// When the cached state may be stale, a live refresh decides; a failed
/// refresh falls back to the cached state rather than guessing.
enum PaywallPresentationPolicy {
    static func shouldPresent(isEntitled: Bool) -> Bool { !isEntitled }

    static func shouldPresent(refreshedIsEntitled: Bool?, cachedIsEntitled: Bool) -> Bool {
        if let refreshedIsEntitled { return shouldPresent(isEntitled: refreshedIsEntitled) }
        return shouldPresent(isEntitled: cachedIsEntitled)
    }
}

/// Unknown eligibility may describe the offer conditionally, but must not promise a free purchase.
enum PaywallTrialPresentation: Equatable {
    case none
    case conditional
    case eligible

    static func resolve(hasFreeTrial: Bool, isEligible: Bool?) -> Self {
        guard hasFreeTrial else { return .none }
        switch isEligible {
        case .some(true): return .eligible
        case .some(false): return .none
        case .none: return .conditional
        }
    }
}
