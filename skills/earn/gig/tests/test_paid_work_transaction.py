import hashlib
import importlib.util
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


def load(name):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


transaction = load("paid_work_transaction")


class PaidWorkTransactionTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.root = base / "project"
        self.evidence_dir = base / "pass-evidence"
        self.stable = base / "delivery-evidence" / "contract.json"
        for name in ("requirements", "source", "artifacts", "acceptance", "delivery"):
            (self.root / name).mkdir(parents=True)
        self.req = self.root / "requirements" / "latest-feedback.json"
        self.req.write_bytes(b"old requirements\n")
        self.req.chmod(0o640)
        self.manifest = self.root / "delivery" / "paid-work-result.json"
        self.manifest.write_bytes(b'{"old":"manifest"}\n')
        self.stable.parent.mkdir()
        self.stable.write_bytes(b'{"old":"stable"}\n')
        (self.root / "state.json").write_text('{"current_version":"v2"}\n')
        self.validator = self.root / "source" / "validate_artifact.py"
        self.validator.write_text(
            "import json,sys,zipfile\n"
            "with zipfile.ZipFile(sys.argv[1]) as archive:\n"
            "    assert archive.testzip() is None\n"
            "print(json.dumps({'status':'PASS'}))\n"
        )
        contract = {
            "version": 1,
            "artifact": {
                "type": "zip",
                "min_size_bytes": 100,
                "allowed_suffixes": [".zip"],
                "safe_archive_paths": True,
            },
            "trusted_files": ["source/validate_artifact.py"],
            "commands": [
                {
                    "id": "domain-integrity",
                    "kind": "domain",
                    "argv": ["python3", "source/validate_artifact.py", "{artifact_path}"],
                    "timeout_seconds": 30,
                    "expect_stdout_json": {"status": "PASS"},
                },
                {
                    "id": "regression-suite",
                    "kind": "test",
                    "argv": ["python3", "source/validate_artifact.py", "{artifact_path}"],
                    "timeout_seconds": 30,
                    "expect_stdout_json": {"status": "PASS"},
                },
            ],
        }
        self.contract = self.root / "delivery" / "validation-contract.json"
        self.contract.write_text(json.dumps(contract) + "\n")
        self.docker_log = base / "fake-docker.jsonl"
        self.fake_docker = base / "fake-docker.py"
        self.fake_docker.write_text(
            "#!/usr/bin/env python3\n"
            "import json,os,sys\n"
            f"with open({str(self.docker_log)!r}, 'a', encoding='utf-8') as handle:\n"
            "    handle.write(json.dumps({'argv':sys.argv[1:],'env':dict(os.environ)}, separators=(',',':'))+'\\n')\n"
            "print(json.dumps({'status':'PASS'}))\n",
            encoding="utf-8",
        )
        self.fake_docker.chmod(0o755)
        patcher = mock.patch.dict(
            os.environ,
            {
                "GIG_PAID_VALIDATOR_DOCKER": str(self.fake_docker),
                "PAID_VALIDATOR_TEST_SECRET": "must-not-reach-docker",
            },
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def begin(self):
        return transaction.begin_transaction(self.root, self.stable, self.evidence_dir, min_mtime=0)

    def write_candidate(self, artifact_name="delivery-v3.zip", artifact_bytes=None, claimed_hash=None):
        artifact = self.root / "artifacts" / artifact_name
        if artifact_bytes is None:
            with zipfile.ZipFile(artifact, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("payload.txt", b"real v3 payload")
            artifact_bytes = artifact.read_bytes()
        else:
            artifact.write_bytes(artifact_bytes)
        acceptance = self.root / "acceptance" / "v3.json"
        acceptance.write_text('{"status":"PASS","acceptance_delta":["real command passed"]}\n')
        self.req.write_text('{"feedback":"actual"}\n')
        row = {
            "status": "ok", "project_root": str(self.root),
            "requirements_path": str(self.req), "artifact_path": str(artifact),
            "artifact_version": "v3", "acceptance_evidence_path": str(acceptance),
            "acceptance_status": "PASS", "acceptance_delta": ["real command passed"],
            "package_sha256": claimed_hash or hashlib.sha256(artifact_bytes).hexdigest(),
        }
        self.manifest.write_text(json.dumps(row, separators=(",", ":")) + "\n")
        return artifact, acceptance, row

    def test_runner_nonzero_after_mutation_rolls_back_and_quarantines_new_outputs(self):
        protected = (self.req, self.manifest, self.stable, self.contract, self.validator)
        before = {
            path: (path.read_bytes(), path.stat().st_mode & 0o777, path.stat().st_mtime_ns)
            for path in protected
        }
        state = self.begin()
        artifact, acceptance, _ = self.write_candidate()
        self.stable.write_bytes(b"mutated stable\n")
        self.contract.write_text('{"version":999}\n')
        self.validator.write_text("raise SystemExit('mutated')\n")
        for path in protected:
            path.chmod(0o777)
            os.utime(path, ns=(1_000_000_000, 1_000_000_000))
        ok, errors = transaction.rollback_transaction(state, "runner_nonzero")
        self.assertTrue(ok, errors)
        for path, (content, mode, mtime_ns) in before.items():
            with self.subTest(path=path):
                self.assertEqual(path.read_bytes(), content)
                self.assertEqual(path.stat().st_mode & 0o777, mode)
                self.assertEqual(path.stat().st_mtime_ns, mtime_ns)
        self.assertFalse(artifact.exists())
        self.assertFalse(acceptance.exists())
        rejected = self.evidence_dir / "rejected-output"
        self.assertTrue(any(path.name.endswith("delivery-v3.zip") for path in rejected.iterdir()))
        self.assertTrue(any(path.name.endswith("v3.json") for path in rejected.iterdir()))
        ledger = json.loads(state.read_text())
        self.assertEqual(ledger["status"], "rolled_back")
        self.assertTrue(all("sha256" in row and "content_b64" in row for row in ledger["snapshots"].values()))
        self.assertTrue(ledger["restored"])

    def test_fake_hash_rolls_back_and_quarantines_without_touching_baseline_outputs(self):
        old_artifact = self.root / "artifacts" / "delivery-v2.zip"
        old_acceptance = self.root / "acceptance" / "v2.json"
        old_artifact.write_bytes(b"baseline")
        old_acceptance.write_text('{"status":"PASS"}\n')
        state = self.begin()
        artifact, acceptance, _ = self.write_candidate(claimed_hash="0" * 64)
        ok, errors = transaction.validate_and_promote(state)
        self.assertFalse(ok)
        self.assertIn("package_sha256_mismatch", errors)
        self.assertTrue(old_artifact.exists())
        self.assertTrue(old_acceptance.exists())
        self.assertFalse(artifact.exists())
        self.assertFalse(acceptance.exists())
        self.assertEqual(self.stable.read_bytes(), b'{"old":"stable"}\n')

    def test_correct_hash_tiny_fake_is_rejected_by_preexisting_validation_contract(self):
        state = self.begin()
        artifact, acceptance, _ = self.write_candidate(
            artifact_bytes=b"fake artifact bytes",
        )
        self.assertEqual(artifact.stat().st_size, 19)

        ok, errors = transaction.validate_and_promote(state)

        self.assertFalse(ok)
        self.assertIn("artifact_contract_too_small", errors)
        self.assertFalse(artifact.exists())
        self.assertFalse(acceptance.exists())
        self.assertEqual(self.stable.read_bytes(), b'{"old":"stable"}\n')

    def test_imported_mutable_helper_cannot_execute_on_host_and_failure_rolls_back(self):
        marker = self.root.parent / "host-escape-marker"
        helper = self.root / "source" / "validator_helper.py"
        helper.write_text("def validate(_artifact):\n    return None\n")
        self.validator.write_text(
            "import json,sys\n"
            "import validator_helper\n"
            "validator_helper.validate(sys.argv[1])\n"
            "print(json.dumps({'status':'PASS'}))\n"
        )
        state = self.begin()
        helper.write_text(
            "from pathlib import Path\n"
            f"def validate(_artifact):\n    Path({str(marker)!r}).write_text('escaped')\n"
        )
        rejecting_docker = self.root.parent / "rejecting-docker.py"
        rejecting_docker.write_text("#!/usr/bin/env python3\nraise SystemExit(17)\n")
        rejecting_docker.chmod(0o755)
        artifact, acceptance, _ = self.write_candidate()

        with mock.patch.dict(os.environ, {"GIG_PAID_VALIDATOR_DOCKER": str(rejecting_docker)}):
            ok, errors = transaction.validate_and_promote(state)

        self.assertFalse(ok)
        self.assertIn("acceptance_contract_command_failed:domain-integrity", errors)
        self.assertFalse(marker.exists())
        self.assertFalse(artifact.exists())
        self.assertFalse(acceptance.exists())
        self.assertEqual(self.stable.read_bytes(), b'{"old":"stable"}\n')

    def test_daemon_down_is_infra_failure_not_contract_rejection(self):
        state = self.begin()
        artifact, acceptance, _ = self.write_candidate()
        daemon_down_docker = self.root.parent / "daemon-down-docker.py"
        daemon_down_docker.write_text(
            "#!/usr/bin/env python3\nimport sys\n"
            "sys.stderr.write('failed to connect to the docker API at "
            "unix:///var/run/docker.sock; check if the daemon is running\\n')\n"
            "raise SystemExit(1)\n"
        )
        daemon_down_docker.chmod(0o755)

        with mock.patch.dict(os.environ, {"GIG_PAID_VALIDATOR_DOCKER": str(daemon_down_docker)}):
            ok, errors = transaction.validate_and_promote(state)

        self.assertFalse(ok)
        self.assertIn("sandbox_infra_unavailable:domain-integrity", errors)
        self.assertNotIn("acceptance_contract_command_failed:domain-integrity", errors)
        ledger = json.loads(Path(state).read_text())
        self.assertEqual(ledger["failure_reason"], "sandbox_infra_unavailable")

    def test_missing_image_is_infra_failure(self):
        state = self.begin()
        self.write_candidate()
        no_image_docker = self.root.parent / "no-image-docker.py"
        no_image_docker.write_text(
            "#!/usr/bin/env python3\nimport sys\n"
            "sys.stderr.write('docker: Error response from daemon: "
            "No such image: openclaw-sandbox:bookworm-slim\\n')\n"
            "raise SystemExit(125)\n"
        )
        no_image_docker.chmod(0o755)

        with mock.patch.dict(os.environ, {"GIG_PAID_VALIDATOR_DOCKER": str(no_image_docker)}):
            ok, errors = transaction.validate_and_promote(state)

        self.assertFalse(ok)
        self.assertIn("sandbox_infra_unavailable:domain-integrity", errors)

    def test_malformed_manifest_quarantines_every_new_owned_output(self):
        baseline_artifact = self.root / "artifacts" / "baseline-v2.zip"
        baseline_acceptance = self.root / "acceptance" / "baseline-v2.json"
        baseline_requirement = self.root / "requirements" / "baseline.md"
        baseline_artifact.write_bytes(b"baseline artifact")
        baseline_acceptance.write_text('{"status":"PASS"}\n')
        baseline_requirement.write_text("baseline requirement\n")
        state = self.begin()

        new_artifact = self.root / "artifacts" / "nested" / "candidate-v3.zip"
        new_acceptance = self.root / "acceptance" / "nested" / "candidate-v3.json"
        new_requirement = self.root / "requirements" / "new-feedback.md"
        new_artifact.parent.mkdir()
        new_acceptance.parent.mkdir()
        new_artifact.write_bytes(b"candidate artifact")
        new_acceptance.write_text('{"status":"PASS"}\n')
        new_requirement.write_text("new requirement\n")
        self.manifest.write_text("{malformed json\n")

        ok, errors = transaction.rollback_transaction(state, "runner_nonzero")

        self.assertTrue(ok, errors)
        self.assertTrue(baseline_artifact.exists())
        self.assertTrue(baseline_acceptance.exists())
        self.assertTrue(baseline_requirement.exists())
        self.assertFalse(new_artifact.exists())
        self.assertFalse(new_acceptance.exists())
        self.assertFalse(new_requirement.exists())
        ledger = json.loads(state.read_text())
        self.assertEqual(
            {row["kind"] for row in ledger["quarantined"]},
            {"artifact", "acceptance", "requirements"},
        )

    def test_begin_fails_closed_without_preexisting_validation_contract(self):
        (self.root / "delivery" / "validation-contract.json").unlink()
        with self.assertRaisesRegex(ValueError, "acceptance_contract_missing_or_invalid"):
            self.begin()

    def test_begin_rejects_contract_whose_validator_argv_is_not_trusted(self):
        contract_path = self.root / "delivery" / "validation-contract.json"
        contract = json.loads(contract_path.read_text())
        other = self.root / "source" / "other_validator.py"
        other.write_text("print('unused')\n")
        contract["trusted_files"] = ["source/other_validator.py"]
        contract_path.write_text(json.dumps(contract) + "\n")

        with self.assertRaisesRegex(ValueError, "acceptance_contract_argv_file_untrusted"):
            self.begin()

    def test_valid_project_manifest_is_promoted_byte_exact_then_full_validated(self):
        state = self.begin()
        artifact, acceptance, _ = self.write_candidate()
        expected = self.manifest.read_bytes()
        ok, errors = transaction.validate_and_promote(state)
        self.assertTrue(ok, errors)
        self.assertEqual(self.stable.read_bytes(), expected)
        self.assertTrue(artifact.exists())
        self.assertTrue(acceptance.exists())
        ledger = json.loads(state.read_text())
        self.assertEqual(ledger["status"], "committed")
        self.assertEqual(
            [(row["kind"], row["rc"]) for row in ledger["validation"]["commands"]],
            [("domain", 0), ("test", 0)],
        )
        self.assertTrue(all(len(row["stdout_sha256"]) == 64 for row in ledger["validation"]["commands"]))
        self.assertTrue(all(len(row["stderr_sha256"]) == 64 for row in ledger["validation"]["commands"]))
        self.assertEqual(ledger["after"]["project_manifest"]["sha256"], hashlib.sha256(expected).hexdigest())
        self.assertEqual(ledger["after"]["stable_delivery_evidence"]["sha256"], hashlib.sha256(expected).hexdigest())

    def test_validation_commands_use_read_only_networkless_docker_policy_and_container_paths(self):
        state = self.begin()
        artifact, _, _ = self.write_candidate()

        ok, errors = transaction.validate_and_promote(state)

        self.assertTrue(ok, errors)
        calls = [json.loads(line) for line in self.docker_log.read_text().splitlines()]
        self.assertEqual(len(calls), 2)
        for call in calls:
            argv = call["argv"]
            self.assertEqual(argv[:2], ["run", "--rm"])
            self.assertIn("--network", argv)
            self.assertEqual(argv[argv.index("--network") + 1], "none")
            self.assertIn("--read-only", argv)
            self.assertEqual(argv[argv.index("--cap-drop") + 1], "ALL")
            self.assertEqual(argv[argv.index("--security-opt") + 1], "no-new-privileges")
            self.assertEqual(argv[argv.index("--pull") + 1], "never")
            mounts = [argv[index + 1] for index, token in enumerate(argv) if token == "--mount"]
            self.assertEqual(
                mounts,
                [f"type=bind,src={self.root.resolve()},dst=/workspace,readonly"],
            )
            self.assertNotIn("docker.sock", " ".join(argv))
            self.assertEqual(argv[argv.index("--tmpfs") + 1], "/tmp:rw,nosuid,nodev,size=64m")
            self.assertEqual(argv[argv.index("-w") + 1], "/workspace")
            image_index = argv.index("openclaw-sandbox:bookworm-slim")
            container_argv = argv[image_index + 1:]
            self.assertEqual(container_argv[0:2], ["python3", "source/validate_artifact.py"])
            self.assertEqual(container_argv[2], f"/workspace/artifacts/{artifact.name}")
            self.assertNotIn(str(self.root), " ".join(container_argv))
            self.assertNotIn("PAID_VALIDATOR_TEST_SECRET", call["env"])
            self.assertNotIn("GIG_PAID_VALIDATOR_DOCKER", call["env"])
            self.assertNotIn("HOME", call["env"])

    def test_preexisting_manifest_declared_outputs_are_never_quarantined(self):
        artifact = self.root / "artifacts" / "delivery-v2.zip"
        acceptance = self.root / "acceptance" / "v2.json"
        artifact.write_bytes(b"baseline")
        acceptance.write_text('{"status":"PASS","acceptance_delta":["old"]}\n')
        row = {"artifact_path": str(artifact), "acceptance_evidence_path": str(acceptance)}
        self.manifest.write_text(json.dumps(row) + "\n")
        state = self.begin()
        ok, errors = transaction.rollback_transaction(state, "runner_nonzero")
        self.assertTrue(ok, errors)
        self.assertTrue(artifact.exists())
        self.assertTrue(acceptance.exists())
        rejected = self.evidence_dir / "rejected-output"
        self.assertFalse(rejected.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
