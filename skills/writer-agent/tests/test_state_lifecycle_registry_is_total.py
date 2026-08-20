"""R1 (WRITER-AGENT-SSOT §9.3, test matrix row 1): the lifecycle registry is total.

Asserts three properties of `config/state-lifecycle.json` plus
`scripts/state-lifecycle-audit.py`:

1. Totality — every existing top-level path under the live state root is
   covered by the registry (explicit entry or path rule). An uncovered path is
   reported and makes the audit exit non-zero.
2. Fail-safe — an unclassified/unknown path resolves to `immutable-receipt`,
   never to a reclaimable class.
3. Mixed `runs/` — `runs/<id>/gates/publication-state.json` is an
   `immutable-receipt` while its sibling `model-stdout.log` is a
   `derived-artifact`.

Read-only: the fixture lives in a temp dir; the live tree is never written.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
AUDIT = SKILL_ROOT / "scripts" / "state-lifecycle-audit.py"
REGISTRY = SKILL_ROOT / "config" / "state-lifecycle.json"
# In the canonical tree the live state sits beside the scripts. A worktree has
# no state/ of its own, so WRITER_AGENT_STATE_ROOT lets this test point at the
# canonical tree instead of silently skipping.
LIVE_STATE = Path(os.environ.get("WRITER_AGENT_STATE_ROOT", str(SKILL_ROOT / "state")))
LIVE_LOGS = Path(os.path.expanduser("~/.openclaw/logs"))


def run_audit(*args):
    proc = subprocess.run(
        [sys.executable, str(AUDIT), *args],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
    )
    return proc


def run_audit_json(*args):
    proc = run_audit("--json", *args)
    try:
        report = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:  # pragma: no cover - diagnostic path
        raise AssertionError(
            f"audit did not emit JSON (exit {proc.returncode}):\n"
            f"stdout={proc.stdout!r}\nstderr={proc.stderr!r}"
        ) from exc
    return proc, report


def write(path: Path, text: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class StateLifecycleRegistryTotalityTest(unittest.TestCase):
    def test_state_lifecycle_registry_is_total(self):
        self.assertTrue(AUDIT.exists(), f"missing audit tool: {AUDIT}")
        self.assertTrue(REGISTRY.exists(), f"missing registry: {REGISTRY}")

        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))

        # The fail-safe default is encoded in the registry, not in a comment.
        self.assertEqual(registry.get("default_class"), "immutable-receipt")

        with tempfile.TemporaryDirectory(prefix="state-lifecycle-fixture.") as tmp:
            root = Path(tmp) / "state"
            logs = Path(tmp) / "logs"
            logs.mkdir(parents=True)

            # Registered top-level paths.
            write(root / "articles.jsonl", '{"id":"a"}\n')
            write(root / "runs" / "r1" / "gates" / "publication-state.json", "{}")
            write(root / "runs" / "r1" / "gates" / "media-candidates" / "c.png", "p")
            write(root / "runs" / "r1" / "model-stdout.log", "stdout")
            write(root / "runs" / "r1" / "headline-image.png", "png")
            write(root / "runs" / "r1" / "daily.meta.json", "{}")
            write(root / "interrupted-generation" / "daily-x" / "attempt-1" / "a.md", "m")

            # An unknown top-level path the registry has never seen.
            write(root / "zzz-unclassified-2099" / "payload.bin", "unknown")

            proc, report = run_audit_json(
                "--state-root", str(root), "--log-root", str(logs),
                "--explain", "runs/r1/gates/publication-state.json",
                "--explain", "runs/r1/model-stdout.log",
                "--explain", "zzz-unclassified-2099/payload.bin",
                "--explain", "runs/r1/gates/media-candidates/c.png",
                "--explain", "runs/r1/daily.meta.json",
                "--explain", "interrupted-generation/daily-x/attempt-1/a.md",
            )

            # 1. Totality: the uncovered top-level path is named and fails the run.
            self.assertIn(
                "zzz-unclassified-2099",
                report["unregistered_top_level"],
                report,
            )
            self.assertNotEqual(
                proc.returncode,
                0,
                "an unregistered top-level path MUST make the audit exit non-zero",
            )

            explain = report["explain"]

            # 2. Fail-safe: unknown resolves to immutable-receipt, and is listed.
            self.assertEqual(
                explain["zzz-unclassified-2099/payload.bin"]["class"],
                "immutable-receipt",
            )
            self.assertEqual(
                explain["zzz-unclassified-2099/payload.bin"]["basis"],
                "fail-safe-default",
            )
            self.assertIn(
                "zzz-unclassified-2099/payload.bin",
                report["fail_safe_default_paths"],
                report["fail_safe_default_paths"],
            )

            # 3. runs/ is mixed, expressed as per-run path patterns.
            self.assertEqual(
                explain["runs/r1/gates/publication-state.json"]["class"],
                "immutable-receipt",
            )
            self.assertEqual(
                explain["runs/r1/model-stdout.log"]["class"],
                "derived-artifact",
            )
            self.assertEqual(
                explain["runs/r1/gates/media-candidates/c.png"]["class"],
                "derived-artifact",
            )
            self.assertEqual(
                explain["runs/r1/daily.meta.json"]["class"],
                "immutable-receipt",
            )
            self.assertEqual(
                explain["interrupted-generation/daily-x/attempt-1/a.md"]["class"],
                "derived-artifact",
            )

            # Every class in the summary is one of the three declared classes.
            self.assertEqual(
                set(report["summary"]),
                {"immutable-receipt", "derived-artifact", "transient-log"},
            )

    def test_live_state_top_level_has_no_unclassified_remainder(self):
        if not LIVE_STATE.is_dir():
            self.skipTest(f"no live state root at {LIVE_STATE}")
        args = ["--state-root", str(LIVE_STATE)]
        if LIVE_LOGS.is_dir():
            args += ["--log-root", str(LIVE_LOGS)]
        proc, report = run_audit_json(*args)
        self.assertEqual(
            report["unregistered_top_level"],
            [],
            f"unclassified remainder on the live tree: {report['unregistered_top_level']}",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)


if __name__ == "__main__":
    unittest.main()
