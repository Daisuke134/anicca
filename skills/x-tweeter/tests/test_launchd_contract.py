from __future__ import annotations

import importlib.util
import tempfile
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[3]
PLISTGEN = ROOT / "bin" / "plistgen.py"
LOOP = ROOT / "loops" / "x-tweeter" / "loop.toml"


class XTweeterLaunchdContractTests(unittest.TestCase):
    def test_pass_is_hourly_on_affiliate_english_identity(self) -> None:
        self.assertTrue(LOOP.is_file(), f"missing loop declaration: {LOOP}")
        spec = importlib.util.spec_from_file_location("plistgen", PLISTGEN)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        loop = tomllib.loads(LOOP.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plist = module.build(
                loop, "pass", loop["jobs"]["pass"],
                root / "home", root / "current", root / "logs",
            )

        self.assertEqual(plist["Label"], "ai.anicca.x-tweeter-pass")
        self.assertEqual(plist["StartCalendarInterval"], [{"Minute": 0}])
        self.assertTrue(plist["ProgramArguments"][1].endswith(
            "/skills/x-tweeter/x-tweeter-cli.sh"
        ))
        environment = plist["EnvironmentVariables"]
        self.assertEqual(environment["X_REPOST_BROWSER_IDENTITY"], "x:affiliate-en")
        self.assertTrue(environment["X_TWEETER_STATE_DIR"].endswith("/loops/x-tweeter"))
        self.assertEqual(environment["X_REPOST_PUBLISH_TRANSPORT"], "postiz")

    def test_healthcheck_keeps_five_minute_observation(self) -> None:
        loop = tomllib.loads(LOOP.read_text(encoding="utf-8"))
        spec = importlib.util.spec_from_file_location("plistgen", PLISTGEN)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        health = module.build(
            loop, "healthcheck", loop["jobs"]["healthcheck"],
            Path("/tmp/home"), Path("/tmp/current"), Path("/tmp/logs"),
        )
        self.assertEqual(health["Label"], "ai.anicca.x-tweeter-healthcheck")
        self.assertEqual(health["StartInterval"], 300)


if __name__ == "__main__":
    unittest.main()
