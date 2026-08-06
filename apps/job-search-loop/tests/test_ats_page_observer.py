import unittest

from job_search_loop.ats_page_observer import observe_current_page


class Page:
    url = "https://jobs.example/apply"
    frames = []


class AtsPageObserverTests(unittest.TestCase):
    def test_uses_existing_context_and_returns_classifier_without_navigation(self):
        class Browser:
            contexts = [type("Context", (), {"pages": [Page()]})()]

        class Chromium:
            def connect_over_cdp(self, endpoint):
                self.endpoint = endpoint
                return Browser()

        chromium = Chromium()
        playwright = type("Playwright", (), {"chromium": chromium})()
        receipt = observe_current_page(
            {
                "status": "ready",
                "endpoint": "http://127.0.0.1:9222",
                "lease_id": "lease-1",
                "fence": 4,
            },
            playwright=playwright,
            snapshotter=lambda page, navigation_committed: {
                "version": 1,
                "url": page.url,
                "navigation_committed": navigation_committed,
                "frames": [{"url": page.url, "controls": [{"type": "file", "label": "Resume"}]}],
            },
        )

        self.assertEqual(chromium.endpoint, "http://127.0.0.1:9222")
        self.assertEqual(receipt["classification"]["classification"], "application_form")
        self.assertEqual(receipt["owner_fence"], 4)
        self.assertNotIn("navigate", receipt)


if __name__ == "__main__":
    unittest.main()
