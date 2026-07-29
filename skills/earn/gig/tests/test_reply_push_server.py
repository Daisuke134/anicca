import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "reply_push_server.py"


def load_module():
    spec = importlib.util.spec_from_file_location("reply_push_server", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load reply_push_server")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReplyPushServerTest(unittest.TestCase):
    def setUp(self):
        self.push = load_module()

    @staticmethod
    def payload(subject, sender="ココナラ <notice@mail.coconala.com>", body="private text"):
        return {"messages": [{"id": "gmail-1", "from": sender, "subject": subject, "body": body}]}

    def test_precontract_message_routes_to_detector_once_without_payload_in_command(self):
        calls = []
        result = self.push.dispatch_notification(
            self.payload("[ココナラ] 笑い上戸さんからメッセージが届いています"),
            detector=Path("/safe/reply_detector.py"),
            full_pass_launcher=Path("/safe/launch_gig_worker.sh"),
            spawn=lambda command: calls.append(command),
        )

        self.assertEqual(result, "reply")
        self.assertEqual(calls, [[
            self.push.sys.executable, "/safe/reply_detector.py", "--trigger", "gmail_push",
        ]])
        self.assertNotIn("private text", repr(calls))

    def test_paid_and_revision_notifications_preempt_to_full_pass(self):
        subjects = [
            "[ココナラ] buyerさんからトークルームに連絡がありました (トークルームNo:1)",
            "[ココナラ] 提案したサービスが購入されました（トークルームNo:1）",
            "[ココナラ]【差し戻し】が選択されました（トークルームNo:1）",
            "buyerさんから見積り相談（プロフィール経由）が届きました！",
        ]
        for subject in subjects:
            with self.subTest(subject=subject):
                calls = []
                result = self.push.dispatch_notification(
                    self.payload(subject),
                    detector=Path("/safe/reply_detector.py"),
                    full_pass_launcher=Path("/safe/launch_gig_worker.sh"),
                    spawn=lambda command: calls.append(command),
                )
                self.assertEqual(result, "full_pass")
                self.assertEqual(calls, [["/bin/bash", "/safe/launch_gig_worker.sh"]])

    def test_irrelevant_or_spoofed_mail_never_spawns(self):
        payloads = [
            self.payload("[ココナラ]応募した募集が終了しました（投稿No.1）"),
            self.payload(
                "[ココナラ] buyerさんからメッセージが届いています",
                sender="Coconala <attacker@example.com>",
            ),
            {"messages": "invalid"},
        ]
        for payload in payloads:
            with self.subTest(payload=payload):
                calls = []
                self.assertEqual(self.push.dispatch_notification(
                    payload,
                    detector=Path("/safe/reply_detector.py"),
                    full_pass_launcher=Path("/safe/launch_gig_worker.sh"),
                    spawn=lambda command: calls.append(command),
                ), "ignored")
                self.assertEqual(calls, [])

    def test_bearer_token_comparison_fails_closed(self):
        self.assertTrue(self.push.authorized("Bearer shared-secret", "shared-secret"))
        self.assertFalse(self.push.authorized("Bearer wrong", "shared-secret"))
        self.assertFalse(self.push.authorized("", "shared-secret"))
        self.assertFalse(self.push.authorized("Bearer shared-secret", ""))


if __name__ == "__main__":
    unittest.main(verbosity=2)
