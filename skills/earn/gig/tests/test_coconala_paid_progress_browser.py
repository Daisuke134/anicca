import hashlib
import importlib.util
import json
import asyncio
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "coconala_paid_progress_browser.py"


def load_module():
    spec = importlib.util.spec_from_file_location("coconala_paid_progress_browser", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load coconala_paid_progress_browser")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CoconalaPaidProgressBrowserTest(unittest.TestCase):
    def setUp(self):
        self.browser = load_module()
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "project"
        for name in ("artifacts", "acceptance", "delivery"):
            (self.root / name).mkdir(parents=True, exist_ok=True)
        self.artifact = self.root / "artifacts" / "v3.zip"
        self.artifact.write_bytes(b"real-v3-artifact")
        self.acceptance = self.root / "acceptance" / "v3.json"
        self.acceptance.write_text('{"status":"PASS"}\n', encoding="utf-8")
        self.digest = hashlib.sha256(self.artifact.read_bytes()).hexdigest()
        self.manifest = {
            "status": "ok",
            "project_root": str(self.root),
            "artifact_path": str(self.artifact),
            "artifact_version": "v3",
            "acceptance_evidence_path": str(self.acceptance),
            "acceptance_status": "PASS",
            "acceptance_delta": ["real regression suite passes"],
            "package_sha256": self.digest,
        }
        self.queue = {
            "talkroom_id": "4201",
            "marketplace_url": "https://coconala.com/talkrooms/4201",
            "delivery_action": "progress",
            "formal_delivery_checkbox": False,
            "progress_payload": {
                "mode": "progress",
                "formal_delivery_checkbox": False,
                "buyer_visible": True,
                "artifact_version": "v3",
                "acceptance_delta": ["real regression suite passes"],
                "blockers": ["buyer_agreement_not_observed"],
                "message": "お世話になっております。修正版 v3 をお送りします。\n今回の主な変更点です。\n・real regression suite passes\nご確認いただき、気になる点があれば遠慮なくお知らせください。",
            },
            "delivery_evidence": dict(self.manifest),
        }

    def tearDown(self):
        self.temp.cleanup()

    def test_contract_binds_queue_manifest_artifact_hash_and_message(self):
        contract = self.browser.validate_progress_contract(self.queue, self.manifest)

        self.assertEqual(contract.talkroom_url, self.queue["marketplace_url"])
        self.assertEqual(contract.artifact_path, self.artifact.resolve())
        self.assertEqual(contract.package_sha256, self.digest)
        self.assertIn("添付: v3.zip（v3）", contract.message)
        self.assertIn(f"パッケージSHA-256: {self.digest}", contract.message)

    def test_contract_rejects_mismatch_or_artifact_outside_project(self):
        bad_queue = json.loads(json.dumps(self.queue))
        bad_queue["delivery_evidence"]["package_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "queue_manifest_mismatch:package_sha256"):
            self.browser.validate_progress_contract(bad_queue, self.manifest)

        outside = Path(self.temp.name) / "outside.zip"
        outside.write_bytes(self.artifact.read_bytes())
        bad_manifest = dict(self.manifest, artifact_path=str(outside))
        bad_queue = json.loads(json.dumps(self.queue))
        bad_queue["delivery_evidence"]["artifact_path"] = str(outside)
        with self.assertRaisesRegex(ValueError, "artifact_outside_project_root"):
            self.browser.validate_progress_contract(bad_queue, bad_manifest)

    def test_contract_rejects_non_progress_or_formal_delivery(self):
        for field, value in (("delivery_action", "formal"), ("formal_delivery_checkbox", True)):
            bad = json.loads(json.dumps(self.queue))
            bad[field] = value
            with self.assertRaises(ValueError):
                self.browser.validate_progress_contract(bad, self.manifest)

    def test_state_predicates_wait_for_upload_and_enabled_send(self):
        base = {
            "url": self.queue["marketplace_url"],
            "formal_delivery_control_present": True,
            "formal_delivery_control_checked": False,
            "textarea_present": True,
            "form_has_artifact": False,
            "textarea_value": "",
            "send_button_present": True,
            "send_button_disabled": True,
        }
        self.assertFalse(self.browser.upload_ready(base))
        uploaded = dict(base, form_has_artifact=True)
        self.assertTrue(self.browser.upload_ready(uploaded))
        self.assertFalse(self.browser.send_ready(uploaded, "exact message"))
        sendable = dict(uploaded, textarea_value="exact message", send_button_disabled=False)
        self.assertTrue(self.browser.send_ready(sendable, "exact message"))
        self.assertFalse(self.browser.send_ready(dict(sendable, formal_delivery_control_checked=True), "exact message"))

    def test_browser_state_reads_selected_file_from_form_file_list(self):
        expression = self.browser.browser_state_expression("v3.zip")
        self.assertIn("input.files", expression)
        self.assertIn("selected_file_names", expression)
        self.assertIn("selectedFileNames.includes", expression)
        self.assertIn(".d-partOfFilename", expression)
        self.assertIn("renderedFileNames.includes", expression)

    def test_exact_seller_hash_and_attachment_is_deduplicated(self):
        state = {
            "seller_messages": [
                {"text": "old v2", "attachments": ["v2.zip"]},
                {"text": f"v3\n{self.digest}", "attachments": ["v3.zip"]},
            ]
        }
        match = self.browser.matching_seller_message(state, "v3.zip", self.digest)
        self.assertEqual(match["attachments"], ["v3.zip"])
        self.assertIsNone(self.browser.matching_seller_message(state, "v3.zip", "f" * 64))

    def test_upload_uses_native_playwright_file_chooser_path(self):
        calls = []

        class FakeLocator:
            def __init__(self, page_name):
                self.page_name = page_name

            async def set_input_files(self, path):
                calls.append(("set_input_files", self.page_name, path))

        class FakePage:
            def __init__(self, name, target_id):
                self.name = name
                self.target_id = target_id

            url = self.queue["marketplace_url"]

            def locator(self, selector):
                calls.append(("locator", self.name, selector))
                return FakeLocator(self.name)

        class FakeContext:
            pages = [
                FakePage("wrong-same-url", "other"),
                FakePage("exact-target", "abc"),
            ]

            async def new_cdp_session(self, page):
                class FakePageSession:
                    async def send(self, method):
                        calls.append(("target_info", page.name, method))
                        return {"targetInfo": {"targetId": page.target_id}}

                    async def detach(self):
                        calls.append(("detach", page.name))

                return FakePageSession()

        class FakeBrowser:
            contexts = [FakeContext()]

        class FakeChromium:
            async def connect_over_cdp(self, endpoint):
                calls.append(("connect_over_cdp", endpoint))
                return FakeBrowser()

        class FakePlaywright:
            chromium = FakeChromium()

        class FakeManager:
            async def __aenter__(self):
                return FakePlaywright()

            async def __aexit__(self, exc_type, exc, traceback):
                return False

        class FakeSession:
            ws_url = "ws://127.0.0.1:9223/devtools/page/abc"
            talkroom_url = self.queue["marketplace_url"]

            async def call(self, method, params=None):
                calls.append((method, params or {}))
                if method == "Runtime.evaluate":
                    return {"result": {"objectId": "legacy-file-input"}}
                if method == "DOM.describeNode":
                    return {"node": {"backendNodeId": 42}}
                return {}

        self.browser.async_playwright = lambda: FakeManager()
        asyncio.run(self.browser._upload(FakeSession(), self.artifact))

        self.assertEqual(
            calls,
            [
                ("connect_over_cdp", "http://127.0.0.1:9223"),
                ("target_info", "wrong-same-url", "Target.getTargetInfo"),
                ("detach", "wrong-same-url"),
                ("target_info", "exact-target", "Target.getTargetInfo"),
                ("detach", "exact-target"),
                (
                    "locator",
                    "exact-target",
                    ".d-messageForm .isPC input[type=file]",
                ),
                ("set_input_files", "exact-target", str(self.artifact)),
            ],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
