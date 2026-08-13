import unittest

from job_search_loop.ats_page_classifier import (
    classify_ats_page,
    classify_execution_outcome,
)


class AtsPageClassifierTests(unittest.TestCase):
    def test_execution_outcomes_preserve_fence_and_require_telegram(self):
        cases = [
            ("invisible_recaptcha", dict(recaptcha_present=True)),
            ("visible_challenge", dict(visible_challenge=True)),
            ("fingerprint_rejected", dict(fingerprint_rejected=True)),
            ("request_started_unknown", dict(request_started=True)),
            ("confirmed_receipt", dict(request_started=True, authoritative_receipt=True)),
        ]

        for expected, overrides in cases:
            with self.subTest(expected=expected):
                values = {
                    "recaptcha_present": False,
                    "visible_challenge": False,
                    "fingerprint_rejected": False,
                    "request_started": False,
                    "authoritative_receipt": False,
                    **overrides,
                }
                receipt = classify_execution_outcome(**values)
                self.assertEqual(receipt["classification"], expected)
                self.assertTrue(receipt["preserve_fence"])
                self.assertTrue(receipt["telegram_required"])

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

    def test_generic_aria_alert_does_not_hide_the_apply_entry(self):
        receipt = classify_ats_page({
            "version": 1,
            "url": "https://example.myworkdayjobs.com/site/job/role",
            "navigation_committed": True,
            "frames": [{"controls": [
                {"role": "alert", "text": "Accessibility announcement"},
                {"tag": "button", "text": "Apply"},
            ]}],
        })

        self.assertEqual(receipt["classification"], "job_detail")
        self.assertEqual(receipt["next_route"], "terra_continue_formal")

    def test_native_sign_in_wins_over_optional_google_sso(self):
        receipt = classify_ats_page({
            "version": 1,
            "url": "https://example.wd5.myworkdayjobs.com/site/job/role/apply",
            "navigation_committed": True,
            "frames": [{"controls": [
                {"tag": "button", "text": "Sign In"},
                {"tag": "button", "text": "Sign In with Google"},
            ]}],
        })

        self.assertEqual(receipt["classification"], "account_auth")
        self.assertEqual(receipt["signals"], ["native_account_controls"])


if __name__ == "__main__":
    unittest.main()
