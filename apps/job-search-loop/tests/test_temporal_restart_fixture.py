import sqlite3
import tempfile
import unittest
from pathlib import Path

from job_search_loop.temporal_restart_fixture import record_activity_effect


class TemporalRestartFixtureTests(unittest.TestCase):
    def test_replayed_activity_records_one_durable_effect(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "effects.sqlite3"

            first = record_activity_effect(database_path, "application:test-1")
            replay = record_activity_effect(database_path, "application:test-1")

            with sqlite3.connect(database_path) as connection:
                effect_count = connection.execute(
                    "SELECT COUNT(*) FROM activity_effects"
                ).fetchone()[0]
                attempt_count = connection.execute(
                    "SELECT COUNT(*) FROM activity_attempts"
                ).fetchone()[0]

            self.assertTrue(first)
            self.assertFalse(replay)
            self.assertEqual(effect_count, 1)
            self.assertEqual(attempt_count, 2)


if __name__ == "__main__":
    unittest.main()
