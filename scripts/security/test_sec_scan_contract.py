import unittest
from pathlib import Path

import pii_shape_scan


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "sec-scan.yml"
YOUTUBE_CREATOR = (
    ROOT / "skills" / "youtube-channel-creator" / "scripts" / "create_channel.py"
)


class SecurityScanWorkflowContractTests(unittest.TestCase):
    def setUp(self):
        self.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_gitleaks_scans_worktree_and_full_history_with_fingerprint_baseline(self):
        self.assertIn("gitleaks dir .", self.workflow)
        self.assertNotIn("gitleaks detect", self.workflow)
        self.assertIn("--log-opts=--all", self.workflow)
        self.assertTrue((ROOT / ".gitleaksignore").is_file())
        git_scan_lines = [
            line
            for line in self.workflow.splitlines()
            if "gitleaks git ." in line
        ]
        self.assertTrue(git_scan_lines)

    def test_pii_gate_uses_redacted_path_scoped_fingerprints(self):
        self.assertIn("scripts/security/pii_shape_scan.py", self.workflow)
        self.assertIn(".pii-shape-allowlist", self.workflow)
        self.assertNotIn("grep -rIE", self.workflow)

    def test_pii_allowlist_contains_no_stale_fingerprint(self):
        allowlist_path = ROOT / ".pii-shape-allowlist"
        allowed = pii_shape_scan.load_allowlist(allowlist_path)
        actual = {
            finding.fingerprint
            for finding in pii_shape_scan.scan_paths(
                pii_shape_scan.discover_paths([ROOT]),
                root=ROOT,
            )
        }
        self.assertEqual(allowed - actual, frozenset())

    def test_python_job_runs_an_explicit_security_manifest(self):
        self.assertIn(".github/python-security-tests.txt", self.workflow)
        self.assertNotIn("find . -name 'test_*.py'", self.workflow)

    def test_youtube_phone_comes_only_from_runtime_configuration(self):
        source = YOUTUBE_CREATOR.read_text(encoding="utf-8")
        self.assertIn('default=os.environ.get("DAIS_PHONE")', source)
        self.assertIn("PHONE_REQUIRED", source)


if __name__ == "__main__":
    unittest.main()
