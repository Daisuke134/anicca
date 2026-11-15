"""Source contracts only; no Swift/RevenueCat runtime is exercised."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]

class FamilySharingWiringTests(unittest.TestCase):
    def test_callout_is_scoped_to_the_actual_product(self):
        source = (ROOT / 'aniccaios/Onboarding/PaywallVariantBView.swift').read_text()
        self.assertRegex(source, r'if package.storeProduct.isFamilyShareable\s*\{\s*Text\(String\(localized: "paywall_family_sharing"\)\)')
        for locale in ('en', 'ja', 'de', 'es', 'fr', 'pt-BR'):
            strings = (ROOT / f'aniccaios/Resources/{locale}.lproj/Localizable.strings').read_text()
            self.assertEqual(strings.count('"paywall_family_sharing" ='), 1)

    def test_ownership_mapping_and_backward_compatible_storage(self):
        model = (ROOT / 'aniccaios/Models/SubscriptionInfo.swift').read_text()
        manager = (ROOT / 'aniccaios/Services/SubscriptionManager.swift').read_text()
        self.assertIn('case purchased = "PURCHASED"', model)
        self.assertIn('case familyShared = "FAMILY_SHARED"', model)
        self.assertIn('ownershipType: OwnershipType? = nil', model)
        self.assertIn('case ownershipType = "ownership_type"', model)
        self.assertIn('decodeIfPresent(OwnershipType.self, forKey: .ownershipType)', model)
        self.assertIn('encodeIfPresent(ownershipType, forKey: .ownershipType)', model)
        self.assertIn('switch entitlement?.ownershipType', manager)
        self.assertIn('case .familyShared: ownershipType = .familyShared', manager)
        self.assertIn('case .purchased: ownershipType = .purchased', manager)
        self.assertIn('default: ownershipType = nil', manager)

    def test_education_flag_requires_live_shared_access_and_acknowledgement(self):
        source = (ROOT / 'aniccaios/AppState.swift').read_text()
        self.assertIn('@Published private(set) var needsFamilySharingEducation = false', source)
        self.assertIn('info.isEntitled && info.ownershipType == .familyShared', source)
        self.assertIn('!defaults.bool(forKey: familySharingEducationKey)', source)
        self.assertIn('func acknowledgeFamilySharingEducation()', source)
        self.assertIn('defaults.set(true, forKey: familySharingEducationKey)', source)
        self.assertIn('Purchases.shared.appUserID', source)

    def test_shared_unknown_and_mismatched_entitlements_cannot_emit_purchase(self):
        source = (ROOT / 'aniccaios/Services/AnalyticsManager.swift').read_text()
        observer = source.split('func observePurchase(', 1)[1].split('func updateSKANConversionValue', 1)[0]
        for guard in ('entitlement?.ownershipType == .purchased', 'entitlement?.productIdentifier == package.storeProduct.productIdentifier'):
            self.assertIn(guard, observer)
            self.assertLess(observer.index(guard), observer.index('guard purchaseObservations.record('))
        self.assertIn('"ownership_type": "PURCHASED"', observer)

if __name__ == '__main__':
    unittest.main()
