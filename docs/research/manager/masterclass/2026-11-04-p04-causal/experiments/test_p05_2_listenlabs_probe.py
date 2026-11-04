"""Safe local tests for the Listen Labs GET-only API probe; NO real calls or secrets."""
import json
import unittest
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError
from io import BytesIO
from p05_2_listenlabs_readonly_probe import ORIGIN, PATHS, safe_get


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload = json.dumps(payload).encode()
        self.status = status

    def read(self, limit=None):
        return self.payload[:limit] if limit else self.payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class ListenLabsSafeProbeTests(unittest.TestCase):
    def test_base_is_official(self):
        self.assertEqual(ORIGIN, "https://listenlabs.ai")

    def test_only_two_allowlisted_get_paths(self):
        self.assertEqual(set(PATHS), {"wallets", "studies"})

    def test_reject_unapproved_mutating_path(self):
        with self.assertRaises(ValueError):
            safe_get("bad", "/api/public/v1/studies/create", "synthetic-test-key")

    def test_probe_uses_get_not_post(self):
        with patch("p05_2_listenlabs_readonly_probe.urlopen",
                   return_value=FakeResponse({"wallets": []})) as mocked:
            result = safe_get("wallets", PATHS["wallets"], "synthetic-test-key")
            req = mocked.call_args.args[0]
            self.assertEqual(req.get_method(), "GET")
            self.assertEqual(result["http_status"], 200)
            self.assertEqual(result["wallets_count"], 0)

    def test_does_not_output_wallet_details(self):
        with patch("p05_2_listenlabs_readonly_probe.urlopen",
                   return_value=FakeResponse({"wallets": [
                       {"walletId": "SENSITIVE_ID", "balance": 999999},
                   ]})):
            x = safe_get("wallets", PATHS["wallets"], "synthetic-test-key")
            self.assertEqual(x["wallets_count"], 1)
            self.assertNotIn("SENSITIVE_ID", json.dumps(x))
            self.assertNotIn("999999", json.dumps(x))

    def test_studies_list_handled_without_raw_data(self):
        with patch("p05_2_listenlabs_readonly_probe.urlopen",
                   return_value=FakeResponse([
                       {"name": "SENSITIVE_RESEARCH_TITLE"},
                   ])):
            x = safe_get("studies", PATHS["studies"], "synthetic-test-key")
            self.assertEqual(x["response_type"], "list")
            self.assertNotIn("SENSITIVE_RESEARCH_TITLE", json.dumps(x))

    def test_invalid_credential_error_does_not_echo_text(self):
        with patch("p05_2_listenlabs_readonly_probe.urlopen",
                   side_effect=HTTPError(
                       ORIGIN + PATHS["wallets"], 401, "forbidden",
                       {}, BytesIO(b'{"error":"DO_NOT_LOG_USER_SECRET","code":"invalid_api_key"}'))):
            x = safe_get("wallets", PATHS["wallets"], "synthetic-test-key")
            self.assertEqual(x["http_status"], 401)
            self.assertEqual(x["error_code"], "invalid_api_key")
            self.assertNotIn("DO_NOT_LOG_USER_SECRET", json.dumps(x))

    def test_api_key_not_logged_in_response(self):
        key="synthetic-test-key"
        with patch("p05_2_listenlabs_readonly_probe.urlopen",
                   return_value=FakeResponse({"wallets": []})):
            r=safe_get("wallets",PATHS["wallets"],key)
        self.assertNotIn(key,json.dumps(r))


if __name__=="__main__":
    unittest.main()
