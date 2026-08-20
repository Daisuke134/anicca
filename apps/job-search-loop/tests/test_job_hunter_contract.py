import importlib.util
import tomllib
import unittest
from pathlib import Path


try:
    yaml = importlib.util.find_spec("yaml")
except ModuleNotFoundError:
    yaml = None


class JobHunterContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo = Path(__file__).parents[3]
        cls.registry_path = cls.repo / "loops/job-hunter/registry.yaml"
        cls.loop_path = cls.repo / "loops/job-hunter/loop.toml"
        cls.cli_path = cls.repo / "skills/job-hunter/job-hunter-cli.sh"

    @unittest.skipUnless(yaml, "PyYAML is required to parse the registry contract")
    def test_registry_has_one_owner_and_bounded_schedules(self):
        import yaml as yaml_module

        registry = yaml_module.safe_load(self.registry_path.read_text(encoding="utf-8"))
        loops = registry["loops"]
        self.assertEqual(registry["executor"], "apps/job-search-loop")
        self.assertEqual(registry["state"]["root"], "~/.local/state/anicca/job-search")
        self.assertEqual(
            {item["id"] for item in loops}, {"acquisition", "inbox", "learning"}
        )
        self.assertEqual(
            {item["schedule"]["launchd_label"] for item in loops},
            {
                "ai.anicca.job-search-daily",
                "ai.anicca.job-search-inbox",
                "ai.anicca.job-search-learning",
            },
        )
        for item in loops:
            self.assertEqual(item["side_effect_owner"], "apps/job-search-loop")
            self.assertTrue(item["task_schema"].startswith("apps/job-search-loop/schemas/"))
            self.assertEqual(item["evidence_root"], "~/.local/state/anicca/job-search/evidence")

    def test_toml_scheduler_matches_registry_cadence_and_cli(self):
        loop = tomllib.loads(self.loop_path.read_text(encoding="utf-8"))
        jobs = loop["jobs"]
        self.assertEqual(loop["name"], "job-hunter")
        self.assertEqual(jobs["acquisition"]["interval_seconds"], 3600)
        self.assertEqual(jobs["inbox"]["interval_seconds"], 900)
        self.assertEqual(jobs["acquisition"]["label"], "ai.anicca.job-search-daily")
        self.assertEqual(jobs["inbox"]["label"], "ai.anicca.job-search-inbox")
        self.assertEqual(
            jobs["learning"]["calendar"], {"weekday": 1, "hour": 9, "minute": 15}
        )
        self.assertEqual(jobs["acquisition"]["program"], jobs["inbox"]["program"])
        if yaml:
            import yaml as yaml_module

            registry = yaml_module.safe_load(
                self.registry_path.read_text(encoding="utf-8")
            )
            by_id = {item["id"]: item for item in registry["loops"]}
            for job_id, job in jobs.items():
                schedule = by_id[job_id]["schedule"]
                if "interval_seconds" in job:
                    self.assertEqual(job["interval_seconds"], schedule["interval_seconds"])
                else:
                    self.assertEqual(job["calendar"], schedule["calendar"])
                self.assertEqual(
                    job["label"], schedule["launchd_label"]
                )

    def test_cli_delegates_without_a_second_executor_or_private_data(self):
        cli = self.cli_path.read_text(encoding="utf-8")
        for lane in ("run-daily.sh", "run-inbox.sh", "run-learning.sh", "healthcheck.sh", "install-launchd.sh"):
            self.assertIn(f"scripts/{lane}", cli)
        self.assertNotRegex(cli, r"(?:curl|sqlite|telegram|openclaw|browser)")
        self.assertNotRegex(cli, r"/(?:Users|home)/[^\s\"']+")
        self.assertNotIn("TELEGRAM_BOT_TOKEN", cli)


if __name__ == "__main__":
    unittest.main()
