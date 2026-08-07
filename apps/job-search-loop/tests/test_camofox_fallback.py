import unittest

from job_search_loop.camofox_fallback import authorize_camofox_fallback


class CamofoxFallbackTests(unittest.TestCase):
    def test_fingerprint_rejection_before_click_gets_isolated_session(self):
        receipt = authorize_camofox_fallback(
            application_id="application-1",
            intent_id="intent-1",
            fence=3,
            classification="fingerprint_rejected",
            click_phase="pre_click",
            transport_phase="pre_request",
        )

        self.assertEqual(receipt["status"], "authorized")
        self.assertEqual(receipt["endpoint"], "http://127.0.0.1:9378")
        self.assertEqual(receipt["user_id"], "job-hunter")
        self.assertTrue(receipt["session_key"].startswith("ats-"))
        self.assertEqual(receipt["source_browser_owner"], "cloakbrowser")
        self.assertEqual(receipt["target_browser_owner"], "camofox")
        self.assertFalse(receipt["transfer_live_tab"])

    def test_clicked_request_or_non_fingerprint_outcome_is_rejected(self):
        cases = [
            ("visible_challenge", "pre_click", "pre_request"),
            ("fingerprint_rejected", "clicked", "pre_request"),
            ("fingerprint_rejected", "pre_click", "request_started"),
        ]

        for classification, click_phase, transport_phase in cases:
            with self.subTest(
                classification=classification,
                click_phase=click_phase,
                transport_phase=transport_phase,
            ):
                with self.assertRaises(ValueError):
                    authorize_camofox_fallback(
                        application_id="application-1",
                        intent_id="intent-1",
                        fence=3,
                        classification=classification,
                        click_phase=click_phase,
                        transport_phase=transport_phase,
                    )


if __name__ == "__main__":
    unittest.main()
