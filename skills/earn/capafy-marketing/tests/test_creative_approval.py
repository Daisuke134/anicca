import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "scripts" / "creative_approval.py"
SPEC = importlib.util.spec_from_file_location("creative_approval", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)
check = MODULE.check


class CreativeApprovalTest(unittest.TestCase):
    def test_pending_and_approved_are_bound_to_exact_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / "reel.mp4"
            artifact.write_bytes(b"reviewed-video")
            digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
            state = root / "approval.json"
            row = {
                "agent_id": "7785270416",
                "artifact_path": str(artifact),
                "artifact_sha256": digest,
                "review_message_id": "29647",
                "status": "pending",
            }
            state.write_text(json.dumps(row), encoding="utf-8")
            self.assertEqual(check(state, "7785270416", root)["status"], "pending")
            row["status"] = "approved"
            state.write_text(json.dumps(row), encoding="utf-8")
            self.assertEqual(check(state, "7785270416", root)["artifact_sha256"], digest)
            artifact.write_bytes(b"different-video")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                check(state, "7785270416", root)


if __name__ == "__main__":
    unittest.main()
