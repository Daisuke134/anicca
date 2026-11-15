import XCTest
import RevenueCat
@testable import aniccaios

final class PaywallDisclosureTests: XCTestCase {
    func testFreeTrialRequiresThisProductsOfferAndConfirmedEligibility() {
        XCTAssertEqual(PaywallTrialPresentation.resolve(hasFreeTrial: true, isEligible: true), .eligible)
        XCTAssertEqual(PaywallTrialPresentation.resolve(hasFreeTrial: true, isEligible: false), .none)
    }

    func testUnknownEligibilityKeepsTheOfferConditional() {
        XCTAssertEqual(PaywallTrialPresentation.resolve(hasFreeTrial: true, isEligible: nil), .conditional)
    }

    func testLifetimeOrAnotherProductWithoutAFreeTrialCannotInheritAnAnnualTrial() {
        for eligibility in [true, false, nil] as [Bool?] {
            XCTAssertEqual(PaywallTrialPresentation.resolve(hasFreeTrial: false, isEligible: eligibility), .none)
        }
    }

    // Issue #9356: every plan is a card on the first screen, longest
    // commitment first — annual, monthly, weekly, lifetime.
    func testPlanOrderingPutsAnnualFirstAndLifetimeLast() {
        let ranks = ["annual": 0, "monthly": 1, "weekly": 2, "lifetime": 3]
        let ordered = PaywallPlanOrdering.ordered(["weekly", "lifetime", "monthly", "annual"]) { ranks[$0] ?? 4 }
        XCTAssertEqual(ordered, ["annual", "monthly", "weekly", "lifetime"])
    }

    func testPlanOrderingIsStableWithinEqualRanks() {
        let ordered = PaywallPlanOrdering.ordered(["b", "a", "c"]) { _ in 0 }
        XCTAssertEqual(ordered, ["b", "a", "c"])
    }

    // Issue #9356 E2E contract: the Maestro flows address plan cards as
    // paywall-plan-annual / -monthly / -weekly / -lifetime. PackageType's
    // rawValue is an Int, so the identifier suffix must come from the
    // explicit name mapping — never from rawValue (build-830 E2E failed
    // twice on numeric ids while all four cards were on screen).
    func testPlanIdentifierNamesMatchTheE2EContract() {
        XCTAssertEqual(PaywallVariantBView.planIdentifierName(for: .annual), "annual")
        XCTAssertEqual(PaywallVariantBView.planIdentifierName(for: .monthly), "monthly")
        XCTAssertEqual(PaywallVariantBView.planIdentifierName(for: .weekly), "weekly")
        XCTAssertEqual(PaywallVariantBView.planIdentifierName(for: .lifetime), "lifetime")
    }
}
