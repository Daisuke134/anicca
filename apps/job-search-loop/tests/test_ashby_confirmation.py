import unittest

from job_search_loop.ashby_confirmation import (
    classify_confirmation,
    classify_post_click_observation,
    is_submit_mutation,
    submit_operation_from_payload,
)


SUCCESS = "Your application was successfully submitted. We'll contact you if there are next steps."


class AshbyConfirmationTests(unittest.TestCase):
    def test_post_click_observation_prefers_exact_submit_request(self):
        receipt = classify_post_click_observation(
            submit_operation="ApiSubmitSingleApplicationFormAction",
            recaptcha_started=True,
            visible_error_texts=[],
            unselected_required_answers=[],
            timed_out=False,
        )
        self.assertEqual(receipt["classification"], "request_started")
        self.assertFalse(receipt["retryable"])

    def test_post_click_observation_recognizes_exact_recaptcha_rejection(self):
        receipt = classify_post_click_observation(
            submit_operation=None,
            recaptcha_started=True,
            visible_error_texts=[
                "There was an error verifying that you are not a robot. Please try again."
            ],
            unselected_required_answers=[],
            timed_out=False,
        )
        self.assertEqual(receipt["classification"], "recaptcha_rejected")
        self.assertTrue(receipt["retryable"])

    def test_post_click_observation_keeps_validation_rejection_non_retryable(self):
        receipt = classify_post_click_observation(
            submit_operation=None,
            recaptcha_started=False,
            visible_error_texts=["Please select an option"],
            unselected_required_answers=["remote_work"],
            timed_out=False,
        )
        self.assertEqual(receipt["classification"], "validation_rejected")
        self.assertFalse(receipt["retryable"])
        self.assertEqual(len(receipt["visible_error_sha256"]), 1)
        self.assertNotIn("Please select an option", str(receipt))

    def test_post_click_observation_distinguishes_recaptcha_pending(self):
        receipt = classify_post_click_observation(
            submit_operation=None,
            recaptcha_started=True,
            visible_error_texts=[],
            unselected_required_answers=[],
            timed_out=True,
        )
        self.assertEqual(receipt["classification"], "recaptcha_pending")
        self.assertFalse(receipt["retryable"])

    def test_post_click_observation_distinguishes_silent_timeout(self):
        receipt = classify_post_click_observation(
            submit_operation=None,
            recaptcha_started=False,
            visible_error_texts=[],
            unselected_required_answers=[],
            timed_out=True,
        )
        self.assertEqual(receipt["classification"], "silent_timeout")
        self.assertFalse(receipt["retryable"])

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

    def test_graphql_success_accepts_ashby_employer_success_copy(self):
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
            status_text=(
                "Success\nYour application has been successfully submitted! "
                "We'll be in touch soon if there are any next steps. "
                "Thank you for your interest!"
            ),
            alert_text=None,
        )

        self.assertTrue(receipt["authoritative_success"])
        self.assertTrue(receipt["status_matches"])

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
        self.assertTrue(is_submit_mutation("ApiSubmitSingleApplicationFormAction"))
        self.assertTrue(is_submit_mutation("ApiSubmitMultipleFormsAction"))
        self.assertFalse(is_submit_mutation("submitApplicationFormAction"))
        self.assertFalse(is_submit_mutation("submitMultipleFormsAction"))
        self.assertFalse(is_submit_mutation("jobPostingFormQuery"))
        self.assertFalse(is_submit_mutation(None))

    def test_extracts_submit_operation_from_single_request_payload(self):
        self.assertEqual(
            submit_operation_from_payload(
                {"operationName": "ApiSubmitSingleApplicationFormAction"}
            ),
            "ApiSubmitSingleApplicationFormAction",
        )

    def test_extracts_one_submit_operation_from_batched_request_payload(self):
        self.assertEqual(
            submit_operation_from_payload(
                [
                    {"operationName": "jobPostingFormQuery"},
                    {"operationName": "ApiSubmitMultipleFormsAction"},
                ]
            ),
            "ApiSubmitMultipleFormsAction",
        )

    def test_rejects_response_field_names_unrelated_and_malformed_payloads(self):
        for payload in (
            {"operationName": "submitApplicationFormAction"},
            {"operationName": "jobPostingFormQuery"},
            [{"operationName": "submitMultipleFormsAction"}],
            "ApiSubmitSingleApplicationFormAction",
            None,
        ):
            with self.subTest(payload=payload):
                self.assertIsNone(submit_operation_from_payload(payload))

    def test_rejects_ambiguous_batch_with_multiple_submit_operations(self):
        self.assertIsNone(
            submit_operation_from_payload(
                [
                    {"operationName": "ApiSubmitSingleApplicationFormAction"},
                    {"operationName": "ApiSubmitMultipleFormsAction"},
                ]
            )
        )


if __name__ == "__main__":
    unittest.main()
