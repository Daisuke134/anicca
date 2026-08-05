import unittest

from job_search_loop.ashby_confirmation import (
    classify_confirmation,
    is_submit_mutation,
)


SUCCESS = "Your application was successfully submitted. We'll contact you if there are next steps."


class AshbyConfirmationTests(unittest.TestCase):
    def test_single_form_requires_graphql_success_and_exact_status_ui(self):
        payload = {
            "data": {
                "submitApplicationFormAction": {
                    "applicationFormResult": {"__typename": "FormSubmitSuccess"}
                }
            }
        }

        receipt = classify_confirmation(
            payload,
            expected_success_text=SUCCESS,
            status_text=f"Success\n{SUCCESS}",
            alert_text=None,
        )

        self.assertTrue(receipt["authoritative_success"])
        self.assertEqual(receipt["operation"], "single")
        self.assertEqual(receipt["application_result"], "FormSubmitSuccess")
        self.assertTrue(receipt["status_matches"])
        self.assertNotIn("data", receipt)

    def test_http_200_graphql_form_render_is_not_submission_success(self):
        payload = {
            "data": {
                "submitApplicationFormAction": {
                    "applicationFormResult": {"__typename": "FormRender"}
                }
            }
        }

        receipt = classify_confirmation(
            payload,
            expected_success_text=SUCCESS,
            status_text=None,
            alert_text="We couldn't submit your application",
        )

        self.assertFalse(receipt["authoritative_success"])
        self.assertEqual(receipt["application_result"], "FormRender")
        self.assertTrue(receipt["alert_present"])

    def test_graphql_success_without_matching_ui_remains_unconfirmed(self):
        payload = {
            "data": {
                "submitApplicationFormAction": {
                    "applicationFormResult": {"__typename": "FormSubmitSuccess"}
                }
            }
        }

        receipt = classify_confirmation(
            payload,
            expected_success_text=SUCCESS,
            status_text="Success\nDifferent theme copy",
            alert_text=None,
        )

        self.assertFalse(receipt["authoritative_success"])
        self.assertFalse(receipt["status_matches"])

    def test_multiple_form_requires_application_and_every_survey_success(self):
        payload = {
            "data": {
                "submitMultipleFormsAction": {
                    "applicationFormResult": {"__typename": "FormSubmitSuccess"},
                    "surveyFormResults": [
                        {"__typename": "FormSubmitSuccess"},
                        {"__typename": "FormRender"},
                    ],
                }
            }
        }

        receipt = classify_confirmation(
            payload,
            expected_success_text=SUCCESS,
            status_text=f"Success\n{SUCCESS}",
            alert_text=None,
        )

        self.assertFalse(receipt["authoritative_success"])
        self.assertEqual(receipt["operation"], "multiple")
        self.assertEqual(
            receipt["survey_results"], ["FormSubmitSuccess", "FormRender"]
        )

    def test_receipt_hashes_untrusted_ui_instead_of_exposing_it(self):
        receipt = classify_confirmation(
            {},
            expected_success_text=SUCCESS,
            status_text="candidate@example.com +81-90-1234-5678",
            alert_text="candidate@example.com is invalid",
        )

        encoded = str(receipt)
        self.assertNotIn("candidate@example.com", encoded)
        self.assertNotIn("090", encoded)
        self.assertRegex(receipt["status_text_sha256"], r"^[a-f0-9]{64}$")
        self.assertRegex(receipt["alert_text_sha256"], r"^[a-f0-9]{64}$")

    def test_only_exact_ashby_submit_mutations_are_selected(self):
        self.assertTrue(is_submit_mutation("submitApplicationFormAction"))
        self.assertTrue(is_submit_mutation("submitMultipleFormsAction"))
        self.assertFalse(is_submit_mutation("jobPostingFormQuery"))
        self.assertFalse(is_submit_mutation(None))


if __name__ == "__main__":
    unittest.main()
