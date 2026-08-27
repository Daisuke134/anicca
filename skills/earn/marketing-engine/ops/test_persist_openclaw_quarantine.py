from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("persist_openclaw_quarantine.py")
SPEC = importlib.util.spec_from_file_location("persist_openclaw_quarantine", MODULE_PATH)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


class PersistOpenClawTest(unittest.TestCase):
    def fixture(self, root: Path):
        store = root / "jobs.json"
        store.write_text(json.dumps({"jobs": [
            {"id": "retire", "enabled": True, "payload": {"keep": 1}},
            {"id": "keep", "enabled": True, "payload": {"keep": 2}},
        ]}))
        raw = store.read_bytes()
        snapshot = {"records": [{
            "runtime": "openclaw", "id": "retire", "enabled": True,
            "disposition": "retire", "source_path": str(store),
            "source_sha256": hashlib.sha256(raw).hexdigest(),
        }]}
        return store, snapshot

    def test_apply_changes_only_reviewed_enabled_flag_and_keeps_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store, snapshot = self.fixture(root)
            before = json.loads(store.read_text())
            result = module.persist(snapshot, root / "backup.json", True)
            after = json.loads(store.read_text())
            backup = json.loads((root / "backup.json").read_text())
        self.assertEqual(result["changed_ids"], ["retire"])
        self.assertFalse(after["jobs"][0]["enabled"])
        self.assertEqual(after["jobs"][0]["payload"], before["jobs"][0]["payload"])
        self.assertTrue(after["jobs"][1]["enabled"])
        self.assertEqual(backup, before)

    def test_hash_mismatch_fails_before_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store, snapshot = self.fixture(root)
            store.write_text("changed")
            with self.assertRaisesRegex(ValueError, "changed since"):
                module.persist(snapshot, root / "backup.json", True)
            self.assertFalse((root / "backup.json").exists())


if __name__ == "__main__":
    unittest.main()
