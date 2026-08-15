"""The gig loop must bound the evidence it writes, without ever eating real work.

Measured 2026-07-30 against the live ~/gig before any policy existed:

    ~/gig                     2.8 GB
    ~/gig/evidence            693 MB  in 247 dirs + 114 loose files, grown in 2.1 days
      gig-pass-*               57 dirs  645 MB   (43 FAILED, 10 SUCCESS, 4 unknown)
      reply-detector-*        176 dirs  1.5 MB   (zero PNGs -- 0.2% of the corpus)
      loose root files        114 files 20.2 MB  (14.4 MB of it -B2-*-submitted.png PROOF)
    PNG                      3129 files 619.5 MB = 89% of all evidence bytes
      of which, inside pass dirs:
        PROOF   png            167 files  27.6 MB  (submitted/form/readback -- load bearing)
        BROWSE  png           2803 files 561.4 MB  (every request page the apply lane looked at)

So the dominant lever is not "failed vs successful pass" (failed passes are 75% of the
corpus and would be *kept* under that rule) -- it is the BROWSE screenshot, which is 81%
of every byte and which nothing ever reads back.

These tests pin the four things that must never break while that mass is bounded.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import evidence_gc  # noqa: E402


PNG = b"\x89PNG\r\n\x1a\n" + b"x" * 4096


def write(path: Path, payload: bytes = b"payload", *, mtime: float | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    if mtime is not None:
        os.utime(path, (mtime, mtime))
    return path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_digest(root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for current, _, files in os.walk(root):
        for name in files:
            path = Path(current) / name
            out[str(path.relative_to(root))] = digest(path)
    return out


class EvidenceGcTestCase(unittest.TestCase):
    """Shared fixture: a temp state dir shaped like the real ~/gig."""

    def setUp(self) -> None:
        import tempfile

        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.state = Path(self._tmp.name) / "gig"
        self.evidence = self.state / "evidence"
        self.evidence.mkdir(parents=True)
        self.now = 1785400000.0

    def pass_dir(
        self,
        pass_id: str,
        *,
        age_hours: float,
        browse_png: int = 3,
        proof: bool = True,
    ) -> Path:
        mtime = self.now - age_hours * 3600
        directory = self.evidence / f"gig-pass-{pass_id}"
        agent = directory / "agent-B2"
        for index in range(browse_png):
            write(agent / f"request-{index}.png", PNG, mtime=mtime)
        write(agent / "attempt-01.stdout.log", b"log" * 100, mtime=mtime)
        write(directory / "b2-context.json", b"{}", mtime=mtime)
        if proof:
            write(agent / "code-applied-readback.png", PNG, mtime=mtime)
            write(directory / f"gig-{pass_id}-B2-9001-form.png", PNG, mtime=mtime)
            write(directory / f"gig-{pass_id}-B2-9001-form.json", b"{}", mtime=mtime)
        os.utime(directory, (mtime, mtime))
        os.utime(agent, (mtime, mtime))
        return directory

    def detector_dir(self, run_id: str, *, age_hours: float) -> Path:
        mtime = self.now - age_hours * 3600
        directory = self.evidence / f"reply-detector-{run_id}"
        write(directory / "detector-result.json", b"{}", mtime=mtime)
        write(directory / "reply-queue.json", b"{}" * 100, mtime=mtime)
        os.utime(directory, (mtime, mtime))
        return directory

    def apply_direct_dir(self, run_id: str, *, age_hours: float, status: str) -> Path:
        mtime = self.now - age_hours * 3600
        directory = self.evidence / f"gig-apply-direct-{run_id}"
        agent = directory / "evidence" / "agent-B2"
        write(agent / "request-0.png", PNG, mtime=mtime)
        write(agent / "code-applied-readback.png", PNG, mtime=mtime)
        write(agent / "request-0.json", b"{}", mtime=mtime)
        write(agent / "attempt.stdout.log", b"log" * 100, mtime=mtime)
        write(directory / "b2-context.json", b"{}", mtime=mtime)
        write(directory / "result.json", json.dumps({"status": status}).encode(), mtime=mtime)
        os.utime(directory, (mtime, mtime))
        return directory

    def lane_lock(self, name: str, *, pid: int, evidence_dir: Path,
                  process_start: str | None = None) -> Path:
        """Write the lock metadata a live Hermes lane publishes for GC."""
        lock = self.state / f".gig-pass-{name}.lock.d"
        write(lock / "pid", f"{pid}\n".encode())
        metadata = {
            "pid": pid,
            "pass_id": evidence_dir.name.removeprefix("gig-pass-"),
            "evidence_dir": str(evidence_dir),
        }
        if process_start is not None:
            metadata["process_start"] = process_start
        write(lock / "meta.json", (json.dumps(metadata) + "\n").encode())
        return lock

    def run_gc(self, **overrides):
        policy = evidence_gc.Policy(**overrides) if overrides else evidence_gc.Policy()
        return evidence_gc.collect(
            state_dir=self.state,
            evidence_root=self.evidence,
            policy=policy,
            now=self.now,
        )


class ProtectedPathsTest(EvidenceGcTestCase):
    """Criterion 3: client deliverables and append-only ledgers are immutable."""

    def test_projects_deliverables_ledgers_survive_the_hardest_possible_gc(self) -> None:
        protected = {
            "projects/90000000/artifacts/v24.zip": os.urandom(2048),
            "projects/90000000/notes.md": b"# paid client work",
            "deliverables/final/report.pdf": os.urandom(4096),
            "applied.jsonl": b'{"requestId":"1"}\n{"requestId":"2"}\n',
            "gig-funnel.jsonl": b'{"ts":1}\n',
            "lessons.jsonl": b'{"lesson":"x"}\n',
            "work-events.jsonl": b'{"kind":"applied"}\n',
            "pass-failures.jsonl": b'{"pass_id":"gone"}\n',
        }
        for relative, payload in protected.items():
            write(self.state / relative, payload, mtime=self.now - 400 * 3600)

        for name in ("telegram-outbox.sqlite3", "connector-outbox.sqlite3",
                     "lane-actions.sqlite3", "gig-control.sqlite3"):
            connection = sqlite3.connect(self.state / name)
            connection.execute("CREATE TABLE t(a TEXT)")
            connection.execute("INSERT INTO t VALUES ('real work')")
            connection.commit()
            connection.close()
            os.utime(self.state / name, (self.now - 400 * 3600,) * 2)

        before = tree_digest(self.state)

        # 200 old, fat passes against a 1 KiB ceiling: GC has every incentive to
        # walk out of the evidence root looking for bytes.
        for index in range(200):
            self.pass_dir(f"178{index:04d}-x", age_hours=200 + index, browse_png=4)

        result = self.run_gc(high_water_bytes=1024, low_water_bytes=512,
                             gig_pass_keep_last=1, gig_pass_keep_daily=0)

        self.assertGreater(result.bytes_reclaimed, 0, "gc did nothing, so it proved nothing")

        after = tree_digest(self.state)
        for relative in protected:
            self.assertIn(relative, after, f"{relative} was deleted")
            self.assertEqual(before[relative], after[relative], f"{relative} was modified")
        for name in ("telegram-outbox.sqlite3", "connector-outbox.sqlite3",
                     "lane-actions.sqlite3", "gig-control.sqlite3"):
            self.assertEqual(before[name], after[name], f"{name} was modified")
            connection = sqlite3.connect(self.state / name)
            self.assertEqual(connection.execute("SELECT a FROM t").fetchall(), [("real work",)])
            connection.close()

    def test_gc_refuses_a_root_that_would_swallow_projects_or_ledgers(self) -> None:
        write(self.state / "projects/1/artifacts/v1.zip", b"deliverable")
        write(self.state / "applied.jsonl", b"{}\n")
        before = tree_digest(self.state)

        result = evidence_gc.collect(
            state_dir=self.state,
            evidence_root=self.state,          # misconfiguration: root == state dir
            policy=evidence_gc.Policy(high_water_bytes=1, low_water_bytes=0),
            now=self.now,
        )

        self.assertTrue(result.refused)
        self.assertEqual(result.bytes_reclaimed, 0)
        self.assertEqual(before, tree_digest(self.state))


class ReferencedEvidenceTest(EvidenceGcTestCase):
    """Criterion 4: evidence an unresolved record points at must survive."""

    def test_evidence_referenced_by_an_open_repair_row_survives_forced_gc(self) -> None:
        referenced = self.pass_dir("1780000-open", age_hours=900, browse_png=6)
        control = self.state / "gig-control.sqlite3"
        connection = sqlite3.connect(control)
        connection.execute(
            "CREATE TABLE repair_queue (incident_id INTEGER PRIMARY KEY, fingerprint TEXT,"
            " repair_class TEXT, state TEXT, evidence_json TEXT)"
        )
        connection.execute(
            "INSERT INTO repair_queue VALUES (1,'fp','cls','queued',?)",
            (json.dumps({"evidence_dir": str(referenced)}),),
        )
        # A resolved row must NOT pin anything.
        resolved = self.pass_dir("1780001-closed", age_hours=901, browse_png=6)
        connection.execute(
            "INSERT INTO repair_queue VALUES (2,'fp2','cls','recovered',?)",
            (json.dumps({"evidence_dir": str(resolved)}),),
        )
        connection.commit()
        connection.close()

        result = self.run_gc(high_water_bytes=1024, low_water_bytes=512,
                             gig_pass_keep_last=0, gig_pass_keep_daily=0)

        self.assertTrue(referenced.is_dir(), "evidence pinned by an open incident was deleted")
        self.assertIn(str(referenced), result.referenced_pins)
        self.assertFalse(resolved.exists(), "a recovered incident should not pin evidence forever")

    def test_last_pass_pins_its_evidence_unconditionally(self) -> None:
        current = self.pass_dir("1780002-last", age_hours=800, browse_png=6)
        write(self.state / ".last-pass",
              json.dumps({"pass_id": "1780002-last", "evidence_dir": str(current)}).encode())

        self.run_gc(high_water_bytes=1024, low_water_bytes=512,
                    gig_pass_keep_last=0, gig_pass_keep_daily=0)

        self.assertTrue(current.is_dir(), ".last-pass evidence was deleted")

    def test_a_recent_failure_pins_its_evidence_but_an_ancient_one_does_not(self) -> None:
        """The bug that made the first draft of this GC useless.

        pass-failures.jsonl is append-only and never resolves anything. Treating
        every row in it as an "unresolved record" pinned 228 of 249 directories on
        the live tree and reclaimed 3% of the corpus. A failure is closed by time.
        """
        recent = self.pass_dir("1780010-recent", age_hours=6, browse_png=6)
        ancient = self.pass_dir("1780011-ancient", age_hours=800, browse_png=6)
        write(self.state / "pass-failures.jsonl", b"".join(
            (json.dumps({"pass_id": p, "evidence_dir": str(d)}) + "\n").encode()
            for p, d in (("1780010-recent", recent), ("1780011-ancient", ancient))
        ))

        result = self.run_gc(high_water_bytes=1024, low_water_bytes=512,
                             gig_pass_keep_last=0, gig_pass_keep_daily=0,
                             pin_horizon_seconds=48 * 3600)

        self.assertTrue(recent.is_dir(), "a failure inside the debug horizon was deleted")
        self.assertFalse(ancient.exists(),
                         "an append-only history row pinned evidence forever")
        self.assertIn(str(recent), result.referenced_pins)
        self.assertNotIn(str(ancient), result.referenced_pins)

    def test_recent_parallel_lanes_and_running_sibling_keep_full_trees(self) -> None:
        pid = os.getpid()
        process_start = subprocess.check_output(
            ["ps", "-p", str(pid), "-o", "lstart="], text=True
        ).strip()
        alive = self.pass_dir("1785390000-paid", age_hours=50, browse_png=6)
        dead = self.pass_dir("1785390100-dead", age_hours=50, browse_png=6)
        invalid = self.pass_dir("1785390200-invalid", age_hours=50, browse_png=6)
        recent = self.pass_dir("1785390300-completed", age_hours=0.5, browse_png=6)
        outside = self.state / "not-evidence" / "gig-pass-outside"
        write(outside / "marker.txt", b"outside")
        before = tree_digest(alive)
        recent_before = tree_digest(recent)
        self.lane_lock("paid", pid=pid, evidence_dir=alive,
                       process_start=process_start)
        self.lane_lock("dead", pid=99999999, evidence_dir=dead,
                       process_start="never")
        self.lane_lock("invalid", pid=pid, evidence_dir=invalid,
                       process_start="pid-reused")
        self.lane_lock("outside", pid=pid, evidence_dir=outside,
                       process_start=process_start)

        result = self.run_gc(high_water_bytes=1024, low_water_bytes=512,
                             gig_pass_keep_last=0, gig_pass_keep_daily=0)

        self.assertTrue(alive.is_dir(), "a live sibling pass was deleted")
        self.assertEqual(before, tree_digest(alive),
                         "a live sibling pass was stripped during phase A")
        self.assertIn(str(alive), result.referenced_pins)
        self.assertEqual(recent_before, tree_digest(recent),
                         "a recently completed pass was stripped before audit")
        self.assertFalse(dead.exists(), "a dead sibling stopped being collectable")
        self.assertNotIn(str(invalid), result.referenced_pins,
                         "a PID-reused lock pinned evidence")
        self.assertNotIn(str(outside), result.referenced_pins,
                         "a lock override pinned a path outside evidence_root")
        self.assertTrue(outside.exists(), "GC reached outside evidence_root")

    def test_the_current_pass_is_never_collected(self) -> None:
        current = self.pass_dir("1780004-now", age_hours=0, browse_png=8)
        digest_before = tree_digest(current)

        evidence_gc.collect(
            state_dir=self.state,
            evidence_root=self.evidence,
            policy=evidence_gc.Policy(high_water_bytes=1, low_water_bytes=0,
                                      gig_pass_keep_last=0, gig_pass_keep_daily=0),
            now=self.now,
            current_evidence_dir=current,
        )

        self.assertEqual(digest_before, tree_digest(current))


class ScreenshotPolicyTest(EvidenceGcTestCase):
    """The dominant lever: browse screenshots go, proof screenshots stay."""

    def test_browse_screenshots_are_stripped_and_proof_screenshots_are_kept(self) -> None:
        directory = self.pass_dir("1780005-strip", age_hours=48, browse_png=5)
        write(self.state / "pass-report.jsonl",
              (json.dumps({"pass_id": "1780005-strip", "status": "success"}) + "\n").encode())

        result = self.run_gc()

        self.assertFalse((directory / "agent-B2" / "request-0.png").exists())
        self.assertTrue((directory / "agent-B2" / "code-applied-readback.png").exists())
        self.assertTrue((directory / "gig-1780005-strip-B2-9001-form.png").exists())
        self.assertTrue((directory / "gig-1780005-strip-B2-9001-form.json").exists())
        self.assertTrue((directory / "b2-context.json").exists())
        self.assertGreater(result.screenshots_removed, 0)

    def test_root_level_submitted_proof_is_never_deleted(self) -> None:
        # normalize_applied._evidence_ids and application_report._proven_ids glob
        # these off the evidence ROOT to prove an application really happened.
        proof = write(self.evidence / "gig-1770000-1-B2-91000057-submitted.png", PNG,
                      mtime=self.now - 5000 * 3600)
        intent = write(self.evidence / "gig-1770000-1-B2-91000057-submitted.intent.json", b"{}",
                       mtime=self.now - 5000 * 3600)
        junk = write(self.evidence / "_scratch.png", PNG, mtime=self.now - 5000 * 3600)

        self.run_gc(high_water_bytes=1024, low_water_bytes=512)

        self.assertTrue(proof.exists(), "application proof screenshot was deleted")
        self.assertTrue(intent.exists(), "submitted intent was deleted")
        self.assertFalse(junk.exists(), "old unreferenced scratch png should be collectable")

    def test_a_pinned_pass_still_loses_its_browse_screenshots(self) -> None:
        """A pin means "keep this directory", not "keep every browse photo in it".

        Exempting pinned dirs from screenshot stripping left phase A reclaiming
        16.8 MB of the measured 619.5 MB PNG mass, because the whole live corpus
        was younger than the 48 h pin horizon.
        """
        pinned = self.pass_dir("1780020-pinned", age_hours=48, browse_png=5)
        write(self.state / ".last-pass",
              json.dumps({"pass_id": "1780020-pinned", "evidence_dir": str(pinned)}).encode())

        result = self.run_gc()

        self.assertTrue(pinned.is_dir(), "a pinned directory was evicted")
        self.assertFalse((pinned / "agent-B2" / "request-0.png").exists())
        # ...but every non-screenshot byte and every proof image is untouched.
        self.assertTrue((pinned / "b2-context.json").exists())
        self.assertTrue((pinned / "agent-B2" / "attempt-01.stdout.log").exists())
        self.assertTrue((pinned / "agent-B2" / "code-applied-readback.png").exists())
        self.assertTrue((pinned / "gig-1780020-pinned-B2-9001-form.png").exists())
        self.assertEqual(result.screenshots_removed, 5)

    def test_a_failed_pass_keeps_its_screenshots_longer_than_a_successful_one(self) -> None:
        good = self.pass_dir("1780006-ok", age_hours=6, browse_png=4)
        bad = self.pass_dir("1780007-ng", age_hours=6, browse_png=4)
        write(self.state / "pass-report.jsonl",
              (json.dumps({"pass_id": "1780006-ok", "status": "success"}) + "\n").encode())
        write(self.state / "pass-failures.jsonl",
              (json.dumps({"pass_id": "1780007-ng", "status": "failed"}) + "\n").encode())

        self.run_gc(screenshot_ttl_success_seconds=3 * 3600,
                    screenshot_ttl_failed_seconds=24 * 3600)

        self.assertFalse((good / "agent-B2" / "request-0.png").exists())
        self.assertTrue((bad / "agent-B2" / "request-0.png").exists())

    def test_apply_direct_uses_result_status_ttl_and_preserves_current_run(self) -> None:
        success = self.apply_direct_dir("success", age_hours=7, status="ok")
        failed = self.apply_direct_dir("failed", age_hours=7, status="failed")
        current = self.apply_direct_dir("current", age_hours=0, status="ok")

        evidence_gc.collect(
            state_dir=self.state,
            evidence_root=self.evidence,
            policy=evidence_gc.Policy(high_water_bytes=10 ** 9, low_water_bytes=10 ** 8),
            now=self.now,
            current_evidence_dir=current,
        )

        self.assertFalse((success / "evidence/agent-B2/request-0.png").exists())
        self.assertTrue((success / "evidence/agent-B2/code-applied-readback.png").exists())
        self.assertTrue((success / "evidence/agent-B2/request-0.json").exists())
        self.assertTrue((success / "evidence/agent-B2/attempt.stdout.log").exists())
        self.assertTrue((failed / "evidence/agent-B2/request-0.png").exists())
        self.assertTrue((current / "evidence/agent-B2/request-0.png").exists())


class PartitionTest(EvidenceGcTestCase):
    """No-op ticks must not evict real history."""

    def test_reply_detector_ticks_cannot_push_out_gig_pass_history(self) -> None:
        passes = [self.pass_dir(f"1781{i:03d}-p", age_hours=30 + i, browse_png=1) for i in range(6)]
        for index in range(400):
            self.detector_dir(f"1782{index:04d}-d", age_hours=index * 0.1)

        result = self.run_gc(gig_pass_keep_last=6, detector_keep_last=20)

        for directory in passes:
            self.assertTrue(directory.is_dir(), f"{directory.name} was evicted by no-op ticks")
        survivors = sorted(p for p in self.evidence.iterdir()
                           if p.name.startswith("reply-detector-"))
        self.assertLessEqual(len(survivors), 20)
        self.assertGreater(result.dirs_removed, 300)

    def test_apply_direct_has_its_own_one_day_retention_partition(self) -> None:
        policy = evidence_gc.Policy()
        self.assertEqual(evidence_gc.partition_of("gig-apply-direct-run"), "apply-direct")
        self.assertEqual(policy.keep_last_for("apply-direct"), 288)
        self.assertEqual(policy.keep_daily_for("apply-direct"), 7)


class WatermarkTest(EvidenceGcTestCase):
    """kubelet-style hysteresis: start at high, stop at low, never at zero."""

    def test_gc_stops_at_the_low_watermark_instead_of_emptying_the_root(self) -> None:
        for index in range(40):
            self.pass_dir(f"1783{index:03d}-w", age_hours=index + 1, browse_png=6, proof=False)
        total_before = evidence_gc.tree_bytes(self.evidence)
        high = total_before // 2
        low = total_before // 4

        result = self.run_gc(high_water_bytes=high, low_water_bytes=low,
                             screenshot_ttl_success_seconds=10 ** 9,
                             screenshot_ttl_failed_seconds=10 ** 9,
                             gig_pass_keep_last=1, gig_pass_keep_daily=0)

        self.assertLessEqual(result.total_bytes_after, high)
        self.assertGreater(result.total_bytes_after, 0, "gc emptied the root instead of stopping at low")
        self.assertTrue(any(self.evidence.iterdir()), "always keep at least one item")

    def test_below_the_high_watermark_no_eviction_happens(self) -> None:
        directory = self.pass_dir("1784000-quiet", age_hours=1, browse_png=2)
        before = tree_digest(self.evidence)

        result = self.run_gc(high_water_bytes=10 ** 9, low_water_bytes=10 ** 8)

        self.assertEqual(result.dirs_removed, 0)
        self.assertEqual(before, tree_digest(self.evidence))
        self.assertTrue(directory.is_dir())

    def test_dual_bound_count_and_bytes(self) -> None:
        # Well under the byte ceiling, but far over the count bound.
        for index in range(80):
            self.detector_dir(f"1785{index:04d}-c", age_hours=index * 0.01)

        self.run_gc(high_water_bytes=10 ** 9, low_water_bytes=10 ** 8, detector_keep_last=12)

        survivors = [p for p in self.evidence.iterdir() if p.name.startswith("reply-detector-")]
        self.assertLessEqual(len(survivors), 12)
        self.assertGreaterEqual(len(survivors), 1)

    def test_keep_last_plus_daily_tiers(self) -> None:
        # 3 passes/day for 10 days.
        for day in range(10):
            for slot in range(3):
                self.pass_dir(f"1786{day:02d}{slot}-t", age_hours=day * 24 + slot + 1,
                              browse_png=1, proof=False)

        self.run_gc(gig_pass_keep_last=4, gig_pass_keep_daily=6,
                    high_water_bytes=10 ** 9, low_water_bytes=10 ** 8)

        survivors = sorted(p.name for p in self.evidence.iterdir() if p.name.startswith("gig-pass-"))
        # 4 newest + at most one per day for 6 further days.
        self.assertGreaterEqual(len(survivors), 4)
        self.assertLessEqual(len(survivors), 10)
        days = {int((self.now - p.stat().st_mtime) // 86400)
                for p in self.evidence.iterdir() if p.name.startswith("gig-pass-")}
        self.assertGreaterEqual(len(days), 4, "daily tier kept no long-tail history")


class CrashSafetyTest(EvidenceGcTestCase):
    """Criterion 6: interrupt it anywhere; a second run converges."""

    def test_trash_left_by_a_killed_sweeper_is_reaped_on_the_next_run(self) -> None:
        orphan = self.evidence / f"gig-pass-1787000-x{evidence_gc.TRASH_SUFFIX}9999"
        write(orphan / "agent-B2" / "request-0.png", PNG)
        self.pass_dir("1787001-y", age_hours=1, browse_png=1)

        result = self.run_gc(high_water_bytes=10 ** 9, low_water_bytes=10 ** 8)

        self.assertFalse(orphan.exists(), "crashed-run trash was not reaped")
        self.assertGreater(result.trash_reaped, 0)

    def test_two_runs_converge_and_the_second_is_a_no_op(self) -> None:
        for index in range(30):
            self.pass_dir(f"1788{index:03d}-i", age_hours=index + 1, browse_png=3, proof=False)

        first = self.run_gc(high_water_bytes=200_000, low_water_bytes=100_000,
                            gig_pass_keep_last=2, gig_pass_keep_daily=0)
        snapshot = tree_digest(self.evidence)
        second = self.run_gc(high_water_bytes=200_000, low_water_bytes=100_000,
                             gig_pass_keep_last=2, gig_pass_keep_daily=0)

        self.assertGreater(first.bytes_reclaimed, 0)
        self.assertEqual(second.bytes_reclaimed, 0, "gc is not idempotent")
        self.assertEqual(snapshot, tree_digest(self.evidence))

    def test_an_unreadable_entry_never_makes_gc_raise(self) -> None:
        directory = self.pass_dir("1789000-perm", age_hours=500, browse_png=2, proof=False)
        keeper = self.pass_dir("1789001-keep", age_hours=1, browse_png=1)
        os.chmod(directory, 0o000)
        self.addCleanup(lambda: os.chmod(directory, 0o700))

        result = self.run_gc(high_water_bytes=1024, low_water_bytes=512,
                            gig_pass_keep_last=1, gig_pass_keep_daily=0)

        self.assertIsInstance(result, evidence_gc.GcResult)
        self.assertTrue(keeper.is_dir())

    def test_a_missing_evidence_root_is_a_quiet_no_op(self) -> None:
        result = evidence_gc.collect(
            state_dir=self.state,
            evidence_root=self.state / "does-not-exist",
            policy=evidence_gc.Policy(),
            now=self.now,
        )
        self.assertEqual(result.bytes_reclaimed, 0)
        self.assertFalse(result.refused)


class EvidenceRecordTest(EvidenceGcTestCase):
    """One line of GC evidence per pass, in the pass's own record."""

    def test_cli_writes_a_result_json_and_appends_one_ledger_row(self) -> None:
        import subprocess

        current = self.pass_dir("1790000-cli", age_hours=0, browse_png=1)
        for index in range(30):
            self.pass_dir(f"1790{index:03d}-o", age_hours=100 + index, browse_png=4, proof=False)

        script = Path(evidence_gc.__file__)
        completed = subprocess.run(
            [sys.executable, str(script),
             "--state-dir", str(self.state),
             "--evidence-root", str(self.evidence),
             "--current-evidence-dir", str(current),
             "--high-water-bytes", "200000", "--low-water-bytes", "100000"],
            capture_output=True, text=True, timeout=120,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

        result_file = current / "evidence-gc.json"
        self.assertTrue(result_file.exists(), "no per-pass gc evidence written")
        record = json.loads(result_file.read_text())
        for key in ("dirs_removed", "files_removed", "screenshots_removed",
                    "bytes_reclaimed", "total_bytes_before", "total_bytes_after"):
            self.assertIn(key, record)
        self.assertGreater(record["bytes_reclaimed"], 0)
        self.assertEqual(record["total_bytes_after"],
                         record["total_bytes_before"] - record["bytes_reclaimed"])

        ledger = self.state / "evidence-gc.jsonl"
        self.assertTrue(ledger.exists())
        rows = [json.loads(line) for line in ledger.read_text().splitlines() if line.strip()]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["bytes_reclaimed"], record["bytes_reclaimed"])

    def test_the_cli_exits_zero_even_when_the_root_is_refused(self) -> None:
        import subprocess

        completed = subprocess.run(
            [sys.executable, str(Path(evidence_gc.__file__)),
             "--state-dir", str(self.state), "--evidence-root", str(self.state)],
            capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(completed.returncode, 0,
                         "gc must never change a pass's exit code")


class WiringTest(unittest.TestCase):
    """The sweeper self-schedules inside the runtime; it is not a new cron."""

    ROOT = Path(__file__).resolve().parents[1]

    def test_gig_pass_invokes_the_sweeper_without_being_able_to_fail_the_pass(self) -> None:
        text = (self.ROOT / "gig_pass.sh").read_text(encoding="utf-8")
        self.assertIn("evidence_gc.py", text)
        line = next(l for l in text.splitlines() if "evidence_gc.py" in l and "python3" in l)
        block = text.split("evidence_gc.py", 1)[1].split("\n\n", 1)[0]
        self.assertTrue("|| true" in block or "|| true" in line,
                        "evidence gc must never change the pass exit code")

    def test_the_auditor_also_sweeps_so_a_failing_loop_still_gets_collected(self) -> None:
        self.assertIn("evidence_gc.py", (self.ROOT / "auditor.sh").read_text(encoding="utf-8"))

    def test_application_direct_sweeps_its_run_root_after_creating_current_run(self) -> None:
        source = (self.ROOT / "scripts" / "application_direct.py").read_text(encoding="utf-8")
        self.assertIn("import evidence_gc", source)
        mkdir = source.index("run_dir.mkdir(parents=True, exist_ok=True)")
        sweep = source.index("evidence_gc.main([")
        self.assertLess(mkdir, sweep)
        for value in (
            '"--state-dir", str(args.state_dir.parent)',
            '"--evidence-root", str(args.state_dir)',
            '"--current-evidence-dir", str(run_dir)',
            '"--high-water-bytes", str(1 * 1024 * 1024 * 1024)',
            '"--low-water-bytes", str(750 * 1024 * 1024)',
            '"--quiet"',
        ):
            self.assertIn(value, source)
        self.assertIn("except Exception:", source[sweep:])


if __name__ == "__main__":
    unittest.main()
