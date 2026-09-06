import json
import hashlib
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("worktree-lease.py")


def run(*args, cwd=None, check=True):
    return subprocess.run(args, cwd=cwd, check=check, text=True, capture_output=True)


class WorktreeLeaseTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name) / "repo"
        self.tree = Path(self.temp.name) / "tree"
        run("git", "init", "-b", "main", str(self.repo))
        run("git", "-C", str(self.repo), "config", "user.name", "Test")
        run("git", "-C", str(self.repo), "config", "user.email", "test@example.com")
        (self.repo / "README").write_text("test\n")
        run("git", "-C", str(self.repo), "add", "README")
        run("git", "-C", str(self.repo), "commit", "-m", "init")
        run("git", "-C", str(self.repo), "worktree", "add", "-b", "task", str(self.tree))

    def tearDown(self):
        self.temp.cleanup()

    def command(self, *args, check=True):
        return run("python3", str(SCRIPT), *args, cwd=self.tree, check=check)

    def lease_path(self):
        common = Path(run("git", "-C", str(self.tree), "rev-parse", "--git-common-dir").stdout.strip()).resolve()
        digest = hashlib.sha256(str(self.tree.resolve()).encode()).hexdigest()
        return common / "worktree-leases" / f"{digest}.json"

    def test_acquire_heartbeat_and_audit(self):
        acquired = json.loads(self.command("acquire", "--owner", "codex", "--task", "WT-04", "--ttl-hours", "1").stdout)
        self.assertEqual(acquired["owner"], "codex")
        audit = json.loads(self.command("audit").stdout)
        tree = next(item for item in audit if Path(item["worktree"]).resolve() == self.tree.resolve())
        self.assertEqual(tree["state"], "active")
        updated = json.loads(self.command("heartbeat", "--owner", "codex", "--ttl-hours", "2").stdout)
        self.assertEqual(updated["owner"], "codex")

    def test_heartbeat_rejects_wrong_owner(self):
        self.command("acquire", "--owner", "codex", "--task", "WT-04")
        result = self.command("heartbeat", "--owner", "other", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("owner mismatch", result.stderr)

    def test_unmanaged_worktree_is_visible(self):
        audit = json.loads(self.command("audit").stdout)
        tree = next(item for item in audit if Path(item["worktree"]).resolve() == self.tree.resolve())
        self.assertEqual(tree["state"], "unmanaged")

    def test_missing_native_lock_is_invalid_and_heartbeat_fails(self):
        self.command("acquire", "--owner", "codex", "--task", "WT-04")
        run("git", "-C", str(self.repo), "worktree", "unlock", str(self.tree))
        audit = json.loads(self.command("audit").stdout)
        tree = next(item for item in audit if Path(item["worktree"]).resolve() == self.tree.resolve())
        self.assertEqual(tree["state"], "invalid")
        self.assertNotEqual(self.command("heartbeat", "--owner", "codex", check=False).returncode, 0)

    def test_invalid_json_does_not_stop_audit(self):
        self.command("acquire", "--owner", "codex", "--task", "WT-04")
        self.lease_path().write_text("not json\n")
        audit = json.loads(self.command("audit").stdout)
        tree = next(item for item in audit if Path(item["worktree"]).resolve() == self.tree.resolve())
        self.assertEqual(tree["state"], "invalid")

    def test_existing_native_lock_is_preserved(self):
        run("git", "-C", str(self.repo), "worktree", "lock", "--reason", "other-owner", str(self.tree))
        result = self.command("acquire", "--owner", "codex", "--task", "WT-04", check=False)
        self.assertNotEqual(result.returncode, 0)
        listing = run("git", "-C", str(self.repo), "worktree", "list", "--porcelain").stdout
        self.assertIn("locked other-owner", listing)

    def test_malformed_lease_fields_are_invalid(self):
        self.command("acquire", "--owner", "codex", "--task", "WT-04")
        original = json.loads(self.lease_path().read_text())
        mutations = (
            {"owner": ""},
            {"task": None},
            {"head": "bad"},
            {"worktree": "/wrong"},
            {"created_at": "no-time"},
            {"heartbeat_at": "2999-01-01T00:00:00Z"},
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                lease = original | mutation
                self.lease_path().write_text(json.dumps(lease))
                audit = json.loads(self.command("audit").stdout)
                tree = next(item for item in audit if Path(item["worktree"]).resolve() == self.tree.resolve())
                self.assertEqual(tree["state"], "invalid")

    def test_binary_lease_is_isolated(self):
        self.command("acquire", "--owner", "codex", "--task", "WT-04")
        self.lease_path().write_bytes(b"\xff\xfe")
        audit = json.loads(self.command("audit").stdout)
        tree = next(item for item in audit if Path(item["worktree"]).resolve() == self.tree.resolve())
        self.assertEqual(tree["state"], "invalid")

    def test_boolean_schema_is_invalid(self):
        self.command("acquire", "--owner", "codex", "--task", "WT-04")
        lease = json.loads(self.lease_path().read_text())
        lease["schema_version"] = True
        self.lease_path().write_text(json.dumps(lease))
        audit = json.loads(self.command("audit").stdout)
        tree = next(item for item in audit if Path(item["worktree"]).resolve() == self.tree.resolve())
        self.assertEqual(tree["state"], "invalid")

    def test_blank_owner_or_task_is_rejected_before_lock(self):
        for arguments in (("--owner", " ", "--task", "WT-04"), ("--owner", "codex", "--task", " ")):
            with self.subTest(arguments=arguments):
                result = self.command("acquire", *arguments, check=False)
                self.assertNotEqual(result.returncode, 0)
                listing = run("git", "-C", str(self.repo), "worktree", "list", "--porcelain").stdout
                self.assertNotIn("\nlocked", listing)


if __name__ == "__main__":
    unittest.main()
