#!/usr/bin/env python3
"""A22: code-generated validation contract for NEW orders, before begin pins it.

A new order has an empty delivery/ directory -- that is a normal initial state,
not an infra failure (SSOT 26-gig-loop-asis-tobe-plan.md section 6 A13-1).  The
bootstrap must be idempotent, generic (no order-id special cases), and must
refuse to invent a contract for an ESTABLISHED project that lost its contract.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
BOOTSTRAP = SCRIPTS / "paid_work_contract_bootstrap.py"
sys.path.insert(0, str(SCRIPTS))

from paid_work_validation_contract import (  # noqa: E402
    CONTRACT_RELATIVE_PATH,
    parse_contract,
    trusted_paths,
)


def run_bootstrap(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(BOOTSTRAP), "--project-root", str(root)],
        capture_output=True,
        text=True,
    )


class ContractBootstrapTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "project"
        for name in ("requirements", "source", "work", "artifacts",
                     "acceptance", "delivery", "evidence"):
            (self.root / name).mkdir(parents=True)
        self.contract = self.root / CONTRACT_RELATIVE_PATH

    def test_new_order_gets_a_contract_begin_accepts(self) -> None:
        result = run_bootstrap(self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.contract.is_file())
        contract = parse_contract(self.contract.read_bytes())
        # begin_transaction requires every trusted file to exist and be non-empty.
        trusted = trusted_paths(contract, self.root.resolve())
        self.assertTrue(trusted)
        payload = json.loads(result.stdout)
        self.assertIs(payload.get("ok"), True)
        self.assertEqual(payload.get("action"), "created")

    def test_bootstrap_is_idempotent(self) -> None:
        first = run_bootstrap(self.root)
        self.assertEqual(first.returncode, 0, first.stderr)
        before = self.contract.read_bytes()
        second = run_bootstrap(self.root)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(self.contract.read_bytes(), before)
        payload = json.loads(second.stdout)
        self.assertEqual(payload.get("action"), "exists")

    def test_existing_contract_is_never_touched(self) -> None:
        custom = b'{"version": 1, "custom": "hand-written"}\n'
        self.contract.write_bytes(custom)
        result = run_bootstrap(self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.contract.read_bytes(), custom)

    def test_established_project_without_contract_is_refused(self) -> None:
        (self.root / "artifacts" / "delivery-v2.zip").write_bytes(b"x" * 2048)
        result = run_bootstrap(self.root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("contract_missing_on_established_project", result.stderr)
        self.assertFalse(self.contract.exists())

    def test_established_manifest_without_contract_is_refused(self) -> None:
        (self.root / "delivery" / "paid-work-result.json").write_text(
            '{"status":"ok"}\n'
        )
        result = run_bootstrap(self.root)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.contract.exists())

    def test_generated_validator_passes_a_real_artifact(self) -> None:
        run_bootstrap(self.root)
        validator = self.root / "validation" / "validate_delivery_generic.py"
        self.assertTrue(validator.is_file())
        artifact = self.root / "artifacts" / "delivery-v1.zip"
        artifact.write_bytes(b"x" * 2048)
        result = subprocess.run(
            [sys.executable, str(validator), str(artifact)],
            capture_output=True, text=True, cwd=self.root,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(result.stdout), {"status": "PASS", "errors": []}
        )

    def test_generated_validator_fails_a_tiny_fake(self) -> None:
        run_bootstrap(self.root)
        validator = self.root / "validation" / "validate_delivery_generic.py"
        artifact = self.root / "artifacts" / "delivery-v1.zip"
        artifact.write_bytes(b"tiny")
        result = subprocess.run(
            [sys.executable, str(validator), str(artifact)],
            capture_output=True, text=True, cwd=self.root,
        )
        self.assertNotEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "FAIL")
        self.assertIn("artifact_too_small", payload["errors"])


if __name__ == "__main__":
    unittest.main()
