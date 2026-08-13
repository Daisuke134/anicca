import hashlib
import unittest

from job_search_loop.ats_page_observer import observe_current_page


class Page:
    frames = []

    def __init__(self, url, target):
        self.url = url
        self.target = target


class AtsPageObserverTests(unittest.TestCase):
    def test_uses_existing_context_and_returns_classifier_without_navigation(self):
        decoy = Page("https://careers.example/decoy", "human-tab")
        owned = Page("https://jobs.example/apply", "job-tab")

        class Browser:
            pass

        class Session:
            def __init__(self, page):
                self.page = page

            def send(self, _method):
                return {"targetInfo": {"targetId": self.page.target}}

        class Context:
            pages = [owned, decoy]

            def new_cdp_session(self, page):
                return Session(page)

        Browser.contexts = [Context()]

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
            {
                "version": 1,
                "lease_sha256": hashlib.sha256(b"lease-1").hexdigest(),
                "fence": 4,
                "baseline_sha256": [hashlib.sha256(b"human-tab").hexdigest()],
                "created_sha256": [hashlib.sha256(b"job-tab").hexdigest()],
            },
            {"target_id": "job-tab", "lease_id": "lease-1", "fence": 4},
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
        self.assertEqual(receipt["snapshot"]["url"], "https://jobs.example/apply")
        self.assertNotIn("navigate", receipt)


if __name__ == "__main__":
    unittest.main()
