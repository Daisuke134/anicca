import XCTest
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
}
