"""Offline source contracts, not evidence of StoreKit or SDK runtime behavior."""
from pathlib import Path
import json
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs/gates/unfinished-transaction-decision-2026-11-16.md"
STATE = DOC.with_suffix(".json")

class UnfinishedTransactionWiringTests(unittest.TestCase):
    def test_owner_at_configuration(self):
        source = (ROOT / "aniccaios/Services/SubscriptionManager.swift").read_text()
        configure = source.split("Purchases.configure(", 1)[1].split(".build()", 1)[0]
        self.assertIn(".with(purchasesAreCompletedBy: .revenueCat, storeKitVersion: .default)", configure)
        self.assertIn(DOC.name, source)
        self.assertIn("5.78.0", source)

    def test_decision_and_honest_state(self):
        doc = DOC.read_text()
        for fact in ("RevenueCat", "every launch", "crash", "consumable",
                     "non-consumable", "CustomerInfo", "double", "force-quit",
                     "production", ".myApp", "storeKitVersion", "informational"):
            self.assertIn(fact, doc)
        state = json.loads(STATE.read_text())
        self.assertTrue(state["measurement"]["unfinished_count_and_age_tracked"])
        self.assertFalse(state["measurement"]["finishing_failures_tracked"])
        self.assertFalse(state["recovery"]["launch_drain_or_sdk_equivalent_verified"])
        self.assertFalse(state["recovery"]["foreground_redrain"])
        self.assertFalse(state["delivery"]["finish_only_after_delivery_and_verification"])

    def test_no_direct_purchase_or_transaction_finish(self):
        # All present purchase calls must be RevenueCat or local UI wrappers.
        for path in (ROOT / "aniccaios").rglob("*.swift"):
            source = path.read_text()
            for line in source.splitlines():
                if re.search(r"\.purchase\s*\(", line):
                    self.assertIn("Purchases.shared.purchase(", line, str(path))
                if re.search(r"\.finish\s*\(", line):
                    self.assertEqual(line.strip(), "continuation.finish()", str(path))
            self.assertNotRegex(source, r"SKPaymentQueue|SKPayment\(")

    def test_observation_and_lifecycle(self):
        manager = (ROOT / "aniccaios/Services/SubscriptionManager.swift").read_text()
        body = manager.split("func observeUnfinishedTransactions(", 1)[1].split("private func listenCustomerInfo", 1)[0]
        for token in ("guard isConfigured", "isObservingUnfinished", "defer",
                      "StoreKit.Transaction.unfinished", "case .verified",
                      "case .unverified", "purchaseDate", "max(0,",
                      '"unfinished_count"', '"oldest_dwell_seconds"',
                      '"unverified_count"', ".unfinishedTransactionsObserved"):
            self.assertIn(token, body)
        for forbidden in (".finish(", "updateSubscriptionInfo", "purchaseResult", "syncPurchases"):
            self.assertNotIn(forbidden, body)
        delegate = (ROOT / "aniccaios/AppDelegate.swift").read_text()
        launch, active = delegate.split("func applicationDidBecomeActive", 1)
        self.assertIn('observeUnfinishedTransactions(reason: "launch")', launch)
        self.assertIn('observeUnfinishedTransactions(reason: "foreground")', active)
        self.assertLess(launch.index("AnalyticsManager.shared.configure()"), launch.index('observeUnfinishedTransactions(reason: "launch")'))
        analytics = (ROOT / "aniccaios/Services/AnalyticsManager.swift").read_text()
        self.assertIn('case unfinishedTransactionsObserved = "unfinished_transactions_observed"', analytics)

if __name__ == "__main__":
    unittest.main()
