import subprocess
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "run-mercor-browser.sh"


class MercorBrowserPreflightTests(unittest.TestCase):
    def _text(self) -> str:
        self.assertTrue(SCRIPT.is_file(), "Mercor browser launcher is missing")
        return SCRIPT.read_text(encoding="utf-8")

    def test_production_script_exists(self) -> None:
        self.assertTrue(SCRIPT.is_file(), "Mercor browser launcher is missing")

    def test_guard_contract_is_canonical_and_fail_closed(self) -> None:
        text = self._text()
        self.assertIn("pwd.getpwuid", text)
        self.assertIn("/usr/bin/python3 -I", text)
        self.assertIn(
            'DISK_GUARD="$HOME/gig/releases/life-manager/current/skills/earn/gig/scripts/gig_disk_guard.py"',
            text,
        )
        self.assertIn('[[ ! -f "$DISK_GUARD"', text)
        self.assertIn('-L "$DISK_GUARD"', text)
        self.assertIn('! -r "$DISK_GUARD"', text)
        self.assertIn('/usr/bin/python3 -I "$DISK_GUARD" /usr/bin/true', text)
        self.assertIn('GIG_DISK_HEADROOM_KIB=524288', text)
        self.assertIn('GIG_HOST_STATE_DIR="$HOME/.openclaw/state"', text)
        self.assertIn(
            'GIG_STATE_DIR="$HOME/.local/state/life-manager/mercor-browser"',
            text,
        )
        unset_start = text.index("unset ")
        unset_end = text.index("\nGIG_DISK_HEADROOM_KIB", unset_start)
        unset_block = text[unset_start:unset_end]
        for name in (
            "GIG_IGNORE_DISK_PRESSURE_BLOCK",
            "GIG_IGNORE_DISK_WRITERS_STOP",
            "DISK_CONTROL_STATE_DIR",
            "OPENCLAW_STATE_DIR",
            "LIFE_MANAGER_HOST_STATE_DIR",
        ):
            self.assertIn(name, unset_block)

    def test_guard_precedes_profile_owner_cleanup_binary_and_exec(self) -> None:
        text = self._text()
        guard = text.index('/usr/bin/python3 -I "$DISK_GUARD" /usr/bin/true')
        for marker in (
            '! -d "$PROFILE"',
            '! -r "$PROFILE"',
            "pgrep",
            'rm -f "$PROFILE/SingletonLock"',
            "CHROMIUM_BIN=",
            'exec "$CHROMIUM_BIN"',
        ):
            self.assertLess(guard, text.index(marker), marker)

    def test_private_env_is_required_and_lifecycle_flags_are_preserved(self) -> None:
        text = self._text()
        for name in (
            "JOB_SEARCH_MERCOR_BROWSER_PROFILE",
            "JOB_SEARCH_MERCOR_CHROMIUM",
            "JOB_SEARCH_MERCOR_BROWSER_PORT",
        ):
            self.assertIn(name, text)
        self.assertIn('JOB_SEARCH_MERCOR_BROWSER_PROFILE:?', text)
        self.assertIn('JOB_SEARCH_MERCOR_CHROMIUM:?', text)
        self.assertIn('JOB_SEARCH_MERCOR_BROWSER_PORT:?', text)
        self.assertNotIn("JOB_SEARCH_BROWSER_PROFILE", text)
        self.assertNotIn("MERCOR_BROWSER_PROFILE:-", text)

        for argument in (
            "--no-first-run",
            "--no-default-browser-check",
            "--no-sandbox",
            "--password-store=basic",
            "--use-mock-keychain",
            "--disable-sync",
            "--disk-cache-size=104857600",
            "--media-cache-size=52428800",
            "--fingerprint=81234",
            "--fingerprint-platform=macos",
            "--remote-debugging-address=127.0.0.1",
            "--remote-allow-origins='*'",
            '--remote-debugging-port="$PORT"',
            '--user-data-dir="$PROFILE"',
            "about:blank",
        ):
            self.assertIn(argument, text)

    def test_singleton_cleanup_is_limited_to_known_files(self) -> None:
        text = self._text()
        self.assertIn("/bin/rm -f", text)
        rm_line = next(
            line for line in text.splitlines() if line.lstrip().startswith("/bin/rm -f")
        )
        for name in ("SingletonLock", "SingletonSocket", "SingletonCookie"):
            self.assertIn(f'"$PROFILE/{name}"', rm_line)
        self.assertNotIn("/*", rm_line)
        self.assertIn(
            '/usr/bin/pgrep -f -- "--user-data-dir=$PROFILE"',
            text,
        )
        self.assertIn('"--user-data-dir=$PROFILE"', text)

    def test_shell_syntax_is_valid(self) -> None:
        self.assertEqual(
            subprocess.run(
                ["/bin/zsh", "-n", str(SCRIPT)],
                check=False,
                capture_output=True,
                text=True,
            ).returncode,
            0,
        )


if __name__ == "__main__":
    unittest.main()
