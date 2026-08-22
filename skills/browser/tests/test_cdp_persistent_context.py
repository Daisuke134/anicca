import builtins
import importlib.util
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).parents[3]
SCRIPT = ROOT / "skills/earn/gig/scripts/cdp_daily_driver_keepalive.py"
ENSURE = ROOT / "skills/browser/ensure_provision_browser.sh"

# The production module must be importable without the optional runtime installed.  The
# test double is only used while loading the pre-change module; tests below reject any
# cloakbrowser import made during a preflight.
sys.modules.setdefault(
    "cloakbrowser",
    types.SimpleNamespace(launch_persistent_context=lambda *args, **kwargs: None),
)
SPEC = importlib.util.spec_from_file_location("cdp_daily_driver_keepalive", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

GUARD_RELATIVE = Path(
    "gig/releases/life-manager/current/skills/earn/gig/scripts/gig_disk_guard.py"
)
STUB = """\
import json
import os
import sys
from pathlib import Path

capture = Path(os.environ["STUB_CAPTURE"])
keys = (
    "HOME", "GIG_DISK_HEADROOM_KIB", "GIG_HOST_STATE_DIR", "GIG_STATE_DIR",
    "GIG_IGNORE_DISK_PRESSURE_BLOCK", "GIG_IGNORE_DISK_WRITERS_STOP",
    "DISK_CONTROL_STATE_DIR", "OPENCLAW_STATE_DIR", "LIFE_MANAGER_HOST_STATE_DIR",
)
host_state = Path(os.environ["GIG_HOST_STATE_DIR"])
reason = None
for filename, candidate in (("disk-writers.stop", "disk_writers_stop"),
                            ("disk-pressure.block", "disk_pressure_block")):
    if (host_state / filename).is_file():
        reason = candidate
        break
record = {"argv": sys.argv, "isolated": sys.flags.isolated,
          "env": {key: os.environ[key] for key in keys if key in os.environ}}
capture.write_text(json.dumps(record), encoding="utf-8")
if reason:
    receipt = Path(os.environ["GIG_STATE_DIR"]) / "state/disk-headroom.json"
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps({"status": "failed", "failed": 1, "effect": 0,
                                   "readback": 0, "reason": reason,
                                   "required_bytes": int(os.environ["GIG_DISK_HEADROOM_KIB"]) * 1024}),
                       encoding="utf-8")
raise SystemExit(1 if reason else 0)
"""


class CdpPersistentContextPreflightTests(unittest.TestCase):
    def install_guard(self, home: Path) -> Path:
        guard = home / GUARD_RELATIVE
        guard.parent.mkdir(parents=True)
        guard.write_text(STUB, encoding="utf-8")
        guard.chmod(0o644)
        return guard

    def reject_browser_import(self):
        real_import = builtins.__import__

        def reject(name, *args, **kwargs):
            if name == "cloakbrowser":
                raise AssertionError("cloakbrowser imported before disk preflight")
            return real_import(name, *args, **kwargs)

        return reject

    def test_child_env_is_canonical_and_isolated_from_hostile_pythonpath(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            home = root / "home"
            home.mkdir()
            guard = self.install_guard(home)
            capture = root / "capture.json"
            hostile = root / "hostile"
            hostile.mkdir()
            marker = hostile / "sitecustomize-ran"
            (hostile / "sitecustomize.py").write_text(
                f"from pathlib import Path\nPath({str(marker)!r}).write_text('hostile')\n",
                encoding="utf-8",
            )
            environment = {
                "HOME": "/hostile/home",
                "PYTHONPATH": str(hostile),
                "GIG_DISK_HEADROOM_KIB": "0",
                "GIG_HOST_STATE_DIR": "/hostile/host-state",
                "GIG_STATE_DIR": "/hostile/lane-state",
                "GIG_IGNORE_DISK_PRESSURE_BLOCK": "1",
                "GIG_IGNORE_DISK_WRITERS_STOP": "true",
                "DISK_CONTROL_STATE_DIR": "/hostile/control",
                "OPENCLAW_STATE_DIR": "/hostile/openclaw",
                "LIFE_MANAGER_HOST_STATE_DIR": "/hostile/life-manager",
                "STUB_CAPTURE": str(capture),
            }
            with patch.dict(os.environ, environment, clear=False):
                self.assertTrue(MODULE._disk_preflight(home))
            record = json.loads(capture.read_text(encoding="utf-8"))
            self.assertEqual(record["argv"], [str(guard), "/usr/bin/true"])
            self.assertEqual(record["isolated"], 1)
            self.assertFalse(marker.exists())
            child_env = record["env"]
            self.assertEqual(child_env["HOME"], str(home))
            self.assertEqual(child_env["GIG_DISK_HEADROOM_KIB"], "524288")
            self.assertEqual(child_env["GIG_HOST_STATE_DIR"], str(home / ".openclaw/state"))
            self.assertEqual(
                child_env["GIG_STATE_DIR"],
                str(home / ".local/state/life-manager/browser-provision"),
            )
            for key in (
                "GIG_IGNORE_DISK_PRESSURE_BLOCK", "GIG_IGNORE_DISK_WRITERS_STOP",
                "DISK_CONTROL_STATE_DIR", "OPENCLAW_STATE_DIR",
                "LIFE_MANAGER_HOST_STATE_DIR",
            ):
                self.assertNotIn(key, child_env)

    def test_both_disk_flags_fail_closed_with_exact_receipts(self) -> None:
        for flag, reason in (("disk-writers.stop", "disk_writers_stop"),
                             ("disk-pressure.block", "disk_pressure_block")):
            with self.subTest(flag=flag), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                home = root / "home"
                host_state = home / ".openclaw/state"
                lane_state = home / ".local/state/life-manager/browser-provision"
                host_state.mkdir(parents=True)
                lane_state.mkdir(parents=True)
                (host_state / flag).write_text("blocked\n", encoding="utf-8")
                self.install_guard(home)
                capture = root / "capture.json"
                with patch.dict(
                    os.environ,
                    {
                        "HOME": "/hostile/home",
                        "STUB_CAPTURE": str(capture),
                        "GIG_IGNORE_DISK_PRESSURE_BLOCK": "1",
                        "GIG_IGNORE_DISK_WRITERS_STOP": "1",
                    },
                    clear=False,
                ):
                    self.assertFalse(MODULE._disk_preflight(home))
                receipt = json.loads((lane_state / "state/disk-headroom.json").read_text())
                self.assertEqual(receipt["reason"], reason)
                self.assertEqual(receipt["effect"], 0)
                self.assertEqual(receipt["required_bytes"], 524288 * 1024)
                with (
                    patch.object(MODULE, "_canonical_home", return_value=home),
                    patch.dict(
                        os.environ,
                        {"AFFILIATE_PROFILE": str(root / "profile"),
                         "STUB_CAPTURE": str(capture)},
                        clear=False,
                    ),
                    patch("builtins.__import__", side_effect=self.reject_browser_import()),
                ):
                    self.assertEqual(
                        MODULE.main(["--profile", str(root / "profile"), "--port", "9333"]),
                        1,
                    )

    def test_port_zero_preflight_only_reaches_guard_without_cloak_import(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            home = root / "home"
            home.mkdir()
            self.install_guard(home)
            capture = root / "capture.json"
            with (
                patch.dict(os.environ, {"HOME": "/hostile/home", "STUB_CAPTURE": str(capture)}, clear=False),
                patch.object(MODULE, "_canonical_home", return_value=home),
                patch("builtins.__import__", side_effect=self.reject_browser_import()),
            ):
                self.assertEqual(
                    MODULE.main(
                        ["--profile", str(root / "profile"), "--port", "0", "--preflight-only"]
                    ),
                    0,
                )
            self.assertTrue(capture.exists())

    def test_shell_preflight_precedes_profile_and_launch_side_effects(self) -> None:
        text = ENSURE.read_text(encoding="utf-8")
        launch = text.split("launch() {", 1)[1].split("\n}", 1)[0]
        preflight = launch.index("--port 0 --preflight-only")
        for effect in (
            'mkdir -p "$profile"',
            "clear_stale_singletons",
            'launchctl remove "$LABEL"',
            "sleep 1",
            "launchctl submit",
        ):
            self.assertLess(preflight, launch.index(effect))
        self.assertIn(
            '"$CLOAK_PY" "$KEEPALIVE" --profile "$profile" --port 0 --preflight-only',
            launch,
        )

    def test_missing_symlink_or_unreadable_guard_has_no_cloak_import(self) -> None:
        for kind in ("missing", "symlink", "unreadable"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                home = root / "home"
                home.mkdir()
                guard = home / GUARD_RELATIVE
                if kind == "symlink":
                    target = root / "guard-target.py"
                    target.write_text(STUB, encoding="utf-8")
                    guard.parent.mkdir(parents=True)
                    guard.symlink_to(target)
                elif kind == "unreadable":
                    self.install_guard(home).chmod(0)
                with (
                    patch.dict(os.environ, {"HOME": "/hostile/home"}, clear=False),
                    patch.object(MODULE, "_canonical_home", return_value=home),
                    patch("builtins.__import__", side_effect=self.reject_browser_import()),
                ):
                    self.assertEqual(
                        MODULE.main(["--profile", str(root / "profile"), "--port", "9333"]),
                        1,
                    )

    def test_invalid_port_has_no_cloak_import_or_effect(self) -> None:
        for port in ("-1", "65536", "not-an-int"):
            with self.subTest(port=port), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                with (
                    patch.object(MODULE, "_disk_preflight", return_value=True),
                    patch("builtins.__import__", side_effect=self.reject_browser_import()),
                ):
                    self.assertEqual(
                        MODULE.main(["--profile", str(root / "profile"), "--port", port]),
                        1,
                    )
                self.assertFalse((root / "profile").exists())


if __name__ == "__main__":
    unittest.main()
