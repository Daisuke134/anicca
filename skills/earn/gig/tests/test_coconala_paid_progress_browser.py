import hashlib
import importlib.util
import json
import asyncio
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "coconala_paid_progress_browser.py"

# Same idiom as test_coconala_reply_browser.py's JS_HARNESS: a real jsdom page evaluates the
# module's actual expression string, so the assertion is on what the browser would compute,
# not on whether a keyword appears in the JS source text.
STATE_JS_HARNESS = r"""
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const { JSDOM } = require("jsdom");
let input = "";
for await (const chunk of process.stdin) input += chunk;
const payload = JSON.parse(input);
const dom = new JSDOM(
  `<!doctype html><form class="d-messageForm">
    <div class="d-messageFormButtonArea_item-deliveryCheck">
      <input type="checkbox" ${payload.disabled ? "disabled" : ""} ${payload.checked ? "checked" : ""}>
    </div>
  </form>`,
  { url: payload.location, runScripts: "outside-only" }
);
const result = dom.window.eval(payload.expression);
process.stdout.write(JSON.stringify(result));
"""


def load_module():
    spec = importlib.util.spec_from_file_location("coconala_paid_progress_browser", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load coconala_paid_progress_browser")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _resolve_global_node_modules() -> str | None:
    # Tests must not depend on an interactive shell's rc file for jsdom to resolve, so the
    # global npm folder is passed explicitly instead of relying on ambient NODE_PATH.
    # Resolved once at import time: every call in this file wants the same path, and `npm
    # root -g` shells out on every invocation for no benefit.
    try:
        completed = subprocess.run(
            ["npm", "root", "-g"], capture_output=True, text=True, check=True
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return completed.stdout.strip() or None


NODE_GLOBAL_MODULES = _resolve_global_node_modules()
JSDOM_AVAILABLE = bool(NODE_GLOBAL_MODULES) and (Path(NODE_GLOBAL_MODULES) / "jsdom").is_dir()


def run_state_expression(expression: str, *, disabled: bool) -> dict:
    payload = {
        "location": "https://coconala.com/talkrooms/4201",
        "disabled": disabled,
        "checked": False,
        "expression": expression,
    }
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", STATE_JS_HARNESS],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=True,
        cwd=SCRIPT.parents[3],
        env={**os.environ, "NODE_PATH": NODE_GLOBAL_MODULES},
    )
    return json.loads(completed.stdout)


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
        # The sha256 identifies the package to us, never to the buyer. It stays bound to
        # the contract and lands in the evidence; it must not appear in what is read by a
        # customer. Order 91000002 was sent 「パッケージSHA-256: f0ce...」 on 2026-08-06.
        self.assertNotIn(self.digest, contract.message)
        self.assertNotIn("パッケージSHA", contract.message)
        self.assertEqual(contract.package_sha256, self.digest)

    def _revision_queue(self, blockers):
        """The 22:04 live shape (gig-pass-1786194006-85231, order 91000002): a complete
        revision riding the progress channel because 納品確認待ち disabled the checkbox."""
        queue = json.loads(json.dumps(self.queue))
        queue["revision_after_formal"] = True
        queue["talkroom_state"] = "納品確認待ち"
        queue["formal_delivery_observed"] = True
        queue["progress_payload"]["blockers"] = blockers
        return queue

    def test_a_revision_redelivery_with_zero_blockers_is_a_valid_contract(self):
        # Verbatim live failure 2026-08-08 22:04: blockers=[] crashed at
        # progress_blockers_invalid and the crash was booked as a delivery attempt.
        # A revision redelivery passed every gate; its honest blocker list is empty.
        contract = self.browser.validate_progress_contract(
            self._revision_queue([]), self.manifest, revision_after_formal=True
        )
        self.assertEqual(contract.package_sha256, self.digest)

    def test_an_ordinary_progress_delivery_still_requires_blockers(self):
        # The builder shape: progress exists BECAUSE blockers exist. Outside the
        # revision path the historical non-empty rule is unchanged.
        bad = json.loads(json.dumps(self.queue))
        bad["progress_payload"]["blockers"] = []
        with self.assertRaisesRegex(ValueError, "progress_blockers_invalid"):
            self.browser.validate_progress_contract(bad, self.manifest)

    def test_a_missing_blockers_key_fails_even_for_a_revision(self):
        # Empty LIST only; absent or None is a malformed payload either way.
        queue = self._revision_queue([])
        del queue["progress_payload"]["blockers"]
        with self.assertRaisesRegex(ValueError, "progress_blockers_invalid"):
            self.browser.validate_progress_contract(
                queue, self.manifest, revision_after_formal=True
            )

    def test_an_internal_token_in_the_builders_message_is_refused_before_send(self):
        bad = json.loads(json.dumps(self.queue))
        bad["progress_payload"]["message"] = (
            "修正版をお送りします。検証PASS、パッケージSHA-256を添付しました。"
        )
        with self.assertRaisesRegex(ValueError, "buyer_style_violation"):
            self.browser.validate_progress_contract(bad, self.manifest)

    def test_an_answer_carrying_an_internal_token_is_refused(self):
        with self.assertRaisesRegex(ValueError, "buyer_style_violation"):
            self.browser.validate_answer_contract(
                self.queue,
                {"version": 1, "status": "answer", "message": "acceptance は PASS です"},
            )

    def test_answer_attachment_is_bound_to_real_filename_and_hash(self):
        screenshot = self.root / "evidence" / "buyma-registration-date.png"
        screenshot.parent.mkdir()
        screenshot.write_bytes(b"official registration date screenshot")
        digest = hashlib.sha256(screenshot.read_bytes()).hexdigest()
        answer = {"version": 1, "status": "answer", "message": "登録日の画面を添付します。",
                  "attachment": {"path": str(screenshot), "filename": screenshot.name, "sha256": digest}}

        queue = {**self.queue, "project_root": str(self.root)}
        contract = self.browser.validate_answer_contract(queue, answer)

        self.assertEqual(contract.attachment_path, screenshot.resolve())
        screenshot.write_bytes(b"changed after contract validation")
        with self.assertRaisesRegex(ValueError, "answer_attachment_changed_before_upload"):
            self.browser.snapshot_answer_attachment(contract, self.root / "delivery/answer-evidence")
        screenshot.write_bytes(b"official registration date screenshot")
        pinned, snapshot_dir = self.browser.snapshot_answer_attachment(
            contract, self.root / "delivery/answer-evidence"
        )
        screenshot.write_bytes(b"changed source after immutable snapshot")
        self.assertEqual(hashlib.sha256(pinned.attachment_path.read_bytes()).hexdigest(), digest)
        self.browser.shutil.rmtree(snapshot_dir)
        screenshot.write_bytes(b"official registration date screenshot")
        answer["attachment"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "answer_attachment_invalid"):
            self.browser.validate_answer_contract(queue, answer)

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

    @unittest.skipUnless(JSDOM_AVAILABLE, "node + global jsdom not available")
    def test_browser_state_reads_formal_delivery_control_disabled_from_the_live_dom(self):
        # Regression for the incident where all three talkrooms showed
        # present=True checked=False disabled=True: the checkbox was never refusing a
        # click, it could not be clicked, and the readback had no field to say so.
        expression = self.browser.browser_state_expression("v3.zip")

        disabled_state = run_state_expression(expression, disabled=True)
        self.assertIs(disabled_state["formal_delivery_control_present"], True)
        self.assertIs(disabled_state["formal_delivery_control_checked"], False)
        self.assertIs(disabled_state["formal_delivery_control_disabled"], True)

        enabled_state = run_state_expression(expression, disabled=False)
        self.assertIs(enabled_state["formal_delivery_control_present"], True)
        self.assertIs(enabled_state["formal_delivery_control_disabled"], False)

    def test_browser_state_reads_selected_file_from_form_file_list(self):
        expression = self.browser.browser_state_expression("v3.zip")
        self.assertIn("input.files", expression)
        self.assertIn("selected_file_names", expression)
        self.assertIn("selectedFileNames.includes", expression)
        self.assertIn(".d-partOfFilename", expression)
        self.assertIn("renderedFileNames.includes", expression)

    def test_exact_message_and_attachment_is_deduplicated(self):
        # Keyed on the sha256 in the row text until 2026-08-07. The sha no longer reaches
        # the buyer, so keying on it would report every successful delivery as unsent; the
        # key is now our own opening, which is what we actually sent.
        message = (
            "お世話になっております。\n修正版 v3 をお届けします。\nご確認ください。"
        )
        state = {
            "seller_messages": [
                {"text": "old v2", "attachments": ["v2.zip"]},
                # innerText reflows the line breaks we sent into more whitespace than we
                # sent. Normalizing runs to one space is what makes the row still ours.
                {"text": message.replace("\n", " \n\n  "), "attachments": ["v3.zip"]},
            ]
        }
        match = self.browser.matching_seller_message(state, "v3.zip", message)
        self.assertEqual(match["attachments"], ["v3.zip"])
        # A different message with the same attachment is not our delivery.
        self.assertIsNone(
            self.browser.matching_seller_message(
                state, "v3.zip", "まったく別の文面をお送りしました。ご確認ください。"
            )
        )
        # Our message under a different attachment is not our delivery either.
        self.assertIsNone(
            self.browser.matching_seller_message(state, "v4.zip", message)
        )

    def test_upload_uses_native_cdp_file_input_path(self):
        calls = []
        class FakeSession:
            async def call(self, method, params=None):
                calls.append((method, params or {}))
                if method == "DOM.getDocument":
                    return {"root": {"nodeId": 7}}
                if method == "DOM.querySelector":
                    return {"nodeId": 9}
                return {}

        asyncio.run(self.browser._upload(FakeSession(), self.artifact))

        self.assertEqual(
            calls,
            [
                ("DOM.getDocument", {"depth": 1, "pierce": True}),
                ("DOM.querySelector", {"nodeId": 7, "selector": ".d-messageForm .isPC input[type=file]"}),
                ("DOM.setFileInputFiles", {"nodeId": 9, "files": [str(self.artifact.resolve())]}),
            ],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
