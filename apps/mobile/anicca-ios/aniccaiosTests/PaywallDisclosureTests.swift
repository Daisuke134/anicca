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

    // Decided 2026-11-15 from primary sources (RevenueCat, Adapty,
    // winner I am's three tiers): the paywall sells exactly three
    // plans — annual highlighted first, then weekly, then lifetime.
    // Monthly is not sold on the paywall.
    func testPaywallShowsExactlyThreePlans() {
        XCTAssertTrue(PaywallPlanDisplay.isVisible(planName: "annual"))
        XCTAssertTrue(PaywallPlanDisplay.isVisible(planName: "weekly"))
        XCTAssertTrue(PaywallPlanDisplay.isVisible(planName: "lifetime"))
        XCTAssertFalse(PaywallPlanDisplay.isVisible(planName: "monthly"))
        XCTAssertFalse(PaywallPlanDisplay.isVisible(planName: "six-month"))
        XCTAssertFalse(PaywallPlanDisplay.isVisible(planName: "custom"))
        XCTAssertLessThan(PaywallPlanDisplay.rank(planName: "annual"), PaywallPlanDisplay.rank(planName: "weekly"))
        XCTAssertLessThan(PaywallPlanDisplay.rank(planName: "weekly"), PaywallPlanDisplay.rank(planName: "lifetime"))
    }

    // Issue #731: the first screen is the annual card. Weekly and
    // lifetime keep their order behind Other plans. With no annual
    // package, those plans stay on the first screen. "No payment now"
    // is only the eligible-trial line.
    func testFirstScreenFeaturesAnnualAndFoldsTheOtherPlans() {
        let plans = ["weekly", "lifetime", "annual"]
        XCTAssertEqual(PaywallPlanPresentation.featured(plans) { $0 == "annual" }, ["annual"])
        XCTAssertEqual(PaywallPlanPresentation.folded(plans) { $0 == "annual" }, ["weekly", "lifetime"])
        let withoutAnnual = ["weekly", "lifetime"]
        XCTAssertEqual(PaywallPlanPresentation.featured(withoutAnnual) { $0 == "annual" }, withoutAnnual)
        XCTAssertTrue(PaywallPlanPresentation.folded(withoutAnnual) { $0 == "annual" }.isEmpty)
        XCTAssertEqual(PaywallTrustLine.localizationKey(trialEligible: true), "paywall_no_payment_now_cancel")
        XCTAssertEqual(PaywallTrustLine.localizationKey(trialEligible: false), "paywall_cancel_anytime_settings")
    }

    // User rule (2026-11-15): a user who already pays never sees a
    // paywall; everyone else does. The live refresh decides when it
    // succeeds; the cached state is only the fallback for a failed one.
    func testPaywallPresentationPolicyHidesPaywallFromSubscribers() {
        XCTAssertFalse(PaywallPresentationPolicy.shouldPresent(isEntitled: true))
        XCTAssertTrue(PaywallPresentationPolicy.shouldPresent(isEntitled: false))
    }

    func testPaywallPresentationPolicyPrefersTheLiveRefresh() {
        XCTAssertFalse(PaywallPresentationPolicy.shouldPresent(refreshedIsEntitled: true, cachedIsEntitled: false))
        XCTAssertTrue(PaywallPresentationPolicy.shouldPresent(refreshedIsEntitled: false, cachedIsEntitled: true))
    }

    func testPaywallPresentationPolicyFallsBackToCacheWhenRefreshFails() {
        XCTAssertFalse(PaywallPresentationPolicy.shouldPresent(refreshedIsEntitled: nil, cachedIsEntitled: true))
        XCTAssertTrue(PaywallPresentationPolicy.shouldPresent(refreshedIsEntitled: nil, cachedIsEntitled: false))
    }

    // The home card states why the word is there (user rule, 2026-11-15:
    // the simulation's effect must be visible). The chosen intervention
    // and notification deliveries say they were chosen from the person's
    // answers. Unselected model candidates are never exposed as deck cards.
    func testHomeDeckCaptionKeysByOrigin() {
        let quote = Quote(id: "q1", text: "x")
        XCTAssertEqual(HomeDeckCard(quote: quote, origin: .selectedIntervention, deliveryId: nil).selectionCaptionKey, "feed_chosen_from_answers")
        XCTAssertEqual(HomeDeckCard(quote: quote, origin: .notification, deliveryId: nil).selectionCaptionKey, "feed_chosen_from_answers")
    }
}
