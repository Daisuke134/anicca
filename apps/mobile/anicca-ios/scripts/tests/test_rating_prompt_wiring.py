"""Source contracts for review telemetry and the post-value onboarding entry."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2] / 'aniccaios'

class RatingPromptWiringTests(unittest.TestCase):
    def test_eligible_request_emits_legacy_metric_with_explicit_semantics(self):
        source = (ROOT / 'Services/ReviewPromptCoordinator.swift').read_text()
        self.assertIn('track(.ratingPromptShown, ["presentation": "storekit_request"])', source)
        self.assertLess(source.index('guard ReviewPromptPolicy.shouldRequestReview'), source.index('track(.ratingPromptShown'))

    def test_onboarding_requests_only_after_insight_action(self):
        source = (ROOT / 'Onboarding/OnboardingFlowView.swift').read_text()
        advance = source.split('private func advance()')[1]
        self.assertIn('if step == .planReveal', advance)
        self.assertIn('ReviewPromptCoordinator.shared.requestReviewIfAppropriate', advance)

if __name__ == '__main__':
    unittest.main()
