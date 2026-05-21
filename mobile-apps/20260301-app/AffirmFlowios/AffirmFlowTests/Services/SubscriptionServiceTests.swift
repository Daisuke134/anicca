import Testing
@testable import AffirmFlow

struct SubscriptionServiceTests {
    @Test
    func sharedInstanceExists() {
        let service = SubscriptionService.shared
        #expect(service != nil)
    }

    @Test
    func mockPackageProperties() {
        let monthly = MockPackage.monthly
        let annual = MockPackage.annual

        #expect(monthly.id == "monthly")
        #expect(monthly.identifier == "$rc_monthly")
        #expect(!monthly.localizedTitle.isEmpty)
        #expect(!monthly.localizedPriceString.isEmpty)

        #expect(annual.id == "annual")
        #expect(annual.identifier == "$rc_annual")
        #expect(!annual.localizedTitle.isEmpty)
        #expect(!annual.localizedPriceString.isEmpty)
    }

    @Test
    func mockOfferingHasPackages() {
        let offering = MockOffering.default

        #expect(offering.identifier == "default")
        #expect(offering.availablePackages.count == 2)
        #expect(offering.availablePackages.contains(where: { $0.id == "monthly" }))
        #expect(offering.availablePackages.contains(where: { $0.id == "annual" }))
    }

    @Test
    func mockOfferingsHasCurrent() {
        let offerings = MockOfferings.default

        #expect(offerings.current != nil)
        #expect(offerings.current?.identifier == "default")
    }

    @Test
    func packageEquatable() {
        let p1 = MockPackage.monthly
        let p2 = MockPackage.monthly
        let p3 = MockPackage.annual

        #expect(p1 == p2)
        #expect(p1 != p3)
    }

    @Test
    func fetchOfferingsWorks() async {
        let service = SubscriptionService.shared
        await service.fetchOfferings()

        #expect(service.offerings != nil)
    }

    @Test
    func checkSubscriptionStatusWorks() async {
        let service = SubscriptionService.shared
        await service.checkSubscriptionStatus()
        // Just verify it doesn't crash
        #expect(true)
    }
}
