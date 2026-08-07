import tempfile
import unittest
from pathlib import Path

from job_search_loop.thread_registry import ActiveThreadConflict, ThreadRegistry


class ThreadRegistryTests(unittest.TestCase):
    def test_one_work_item_has_one_idempotent_active_thread(self):
        with tempfile.TemporaryDirectory() as directory:
            registry = ThreadRegistry(Path(directory) / "threads.sqlite3")

            first = registry.bind(
                work_type="job_application",
                work_id="application-1",
                thread_id="thread-1",
                runtime_release_sha="abc123",
                run_id="run-92",
            )
            repeated = registry.bind(
                work_type="job_application",
                work_id="application-1",
                thread_id="thread-1",
                runtime_release_sha="abc123",
                run_id="run-93",
            )

            self.assertEqual(first["thread_id"], "thread-1")
            self.assertEqual(repeated["generation"], 1)
            self.assertEqual(repeated["last_run_id"], "run-93")
            with self.assertRaises(ActiveThreadConflict):
                registry.bind(
                    work_type="job_application",
                    work_id="application-1",
                    thread_id="thread-2",
                    runtime_release_sha="def456",
                    run_id="run-94",
                )
            self.assertEqual(
                registry.active("job_application", "application-1")["thread_id"],
                "thread-1",
            )
            registry.close()

    def test_archived_thread_becomes_predecessor_of_next_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            registry = ThreadRegistry(Path(directory) / "threads.sqlite3")
            registry.bind(
                work_type="job_application",
                work_id="application-1",
                thread_id="thread-1",
                runtime_release_sha="abc123",
                run_id="run-92",
            )

            registry.archive("job_application", "application-1")
            successor = registry.bind(
                work_type="job_application",
                work_id="application-1",
                thread_id="thread-2",
                runtime_release_sha="def456",
                run_id="run-93",
            )

            self.assertEqual(successor["generation"], 2)
            self.assertEqual(successor["predecessor_thread_id"], "thread-1")
            registry.close()


if __name__ == "__main__":
    unittest.main()
