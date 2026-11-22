"""Source integration checks; native behavior/rendering lives in WordShareContentTests."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2] / "aniccaios"

class WordShareWiringTests(unittest.TestCase):
    def test_home_pauses_for_share_sheet(self):
        source = (ROOT / "Views/Feed/FeedRootView.swift").read_text()
        self.assertIn("|| showQuoteShare", source)
        self.assertIn("onSharePresentationChange:", source)

    def test_deferred_home_refresh_is_replayed_after_dismissal(self):
        source = (ROOT / "Views/Feed/FeedRootView.swift").read_text()
        self.assertIn("refreshAfterShare = true", source)
        self.assertIn("if refreshAfterShare", source)
        self.assertIn("guard !showQuoteShare else { return }", source.split("private func applyPendingQuoteNavigation()", 1)[1])

    def test_export_uses_reflowed_words(self):
        source = (ROOT / "Views/Feed/ShareImageRenderer.swift").read_text()
        self.assertIn("Text(verbatim: content.exportText)", source)

    def test_sheet_records_real_presentation_and_success_only(self):
        source = (ROOT / "Views/Feed/QuoteCardView.swift").read_text()
        self.assertIn("override func viewDidAppear", source)
        self.assertIn("completed && error == nil", source)
        self.assertIn(".screenshotShareOpened", source)
        self.assertIn(".screenshotShareCompleted", source)

if __name__ == "__main__":
    unittest.main()
