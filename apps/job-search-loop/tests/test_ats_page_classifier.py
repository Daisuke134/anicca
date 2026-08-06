import unittest

from job_search_loop.ats_page_classifier import classify_ats_page


class AtsPageClassifierTests(unittest.TestCase):
    def test_semantic_surfaces_classify_without_creating_success_truth(self):
        cases = [
            ("job_detail", "https://jobs.example/7", [{"tag": "button", "text": "Apply for this job"}]),
            ("account_auth", "https://jobs.example/create-account", [{"tag": "input", "type": "password", "label": "Password"}]),
            ("application_form", "https://jobs.example/apply", [{"tag": "input", "type": "file", "label": "Resume", "required": True}]),
            ("validation_error", "https://jobs.example/apply", [{"role": "alert", "text": "This field is required"}]),
            ("visible_captcha", "https://jobs.example/apply", [{"tag": "iframe", "frame_url": "https://hcaptcha.com/1/api.js", "text": "Verify you are human"}]),
            ("blocked_sso", "https://accounts.google.com/login", [{"tag": "button", "text": "Sign in with Google"}]),
            ("closed_posting", "https://jobs.example/7", [{"role": "status", "text": "This position is no longer available"}]),
            ("confirmation_like", "https://jobs.example/thank-you", [{"role": "status", "text": "Application submitted"}]),
            ("unknown", "https://jobs.example/loading", []),
        ]

        for expected, url, controls in cases:
            with self.subTest(expected=expected):
                receipt = classify_ats_page({
                    "version": 1,
                    "url": url,
                    "navigation_committed": True,
                    "frames": [{"url": url, "controls": controls}],
                })
                self.assertEqual(receipt["classification"], expected)
                self.assertFalse(receipt["application_confirmed"])
                if expected in {"visible_captcha", "blocked_sso", "closed_posting"}:
                    self.assertEqual(receipt["next_route"], "gmail_fallback_required")


if __name__ == "__main__":
    unittest.main()
