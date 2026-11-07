import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "cdp_tenant_context.py"
SPEC = importlib.util.spec_from_file_location("cdp_tenant_context", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FakePage:
    def __init__(self, context):
        self.context = context
        self.closed = False

    def goto(self, url, **kwargs):
        self.context.visits.append(url)

    def evaluate(self, _script, items):
        self.context.evaluated.append(items)

    def close(self):
        self.closed = True


class FakeContext:
    def __init__(self):
        self.cookies = None
        self.visits = []
        self.evaluated = []
        self.pages = []

    def add_cookies(self, cookies):
        self.cookies = cookies

    def new_page(self):
        page = FakePage(self)
        self.pages.append(page)
        return page


STATE = {
    "cookies": [{"name": "token", "value": "fixture", "domain": ".capafy.ai",
                 "path": "/", "expires": -1, "httpOnly": True, "secure": True,
                 "sameSite": "Lax"}],
    "origins": [{"origin": "https://capafy.ai",
                 "localStorage": [{"name": "auth-storage", "value": "{}"}]}],
}


class StorageStateSeedTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.profile = Path(self.tmp.name) / "profile"
        self.profile.mkdir()
        self.state_path = Path(self.tmp.name) / "browser-auth-state.json"
        self.state_path.write_text(json.dumps(STATE), encoding="utf-8")

    def test_first_seed_applies_cookies_and_local_storage(self):
        context = FakeContext()
        applied = MODULE._seed_storage_state(context, str(self.profile), self.state_path)
        self.assertEqual(applied, 1)
        self.assertEqual(context.cookies, STATE["cookies"])
        self.assertEqual(context.visits, ["https://capafy.ai"])
        self.assertEqual(context.evaluated, [STATE["origins"][0]["localStorage"]])
        self.assertTrue(context.pages[0].closed)
        marker = (self.profile / MODULE._SEED_MARKER).read_text(encoding="utf-8").strip()
        self.assertEqual(marker, MODULE._state_digest(self.state_path))

    def test_same_state_is_not_reseeded(self):
        first = FakeContext()
        MODULE._seed_storage_state(first, str(self.profile), self.state_path)
        second = FakeContext()
        applied = MODULE._seed_storage_state(second, str(self.profile), self.state_path)
        self.assertEqual(applied, 0)
        self.assertIsNone(second.cookies)
        self.assertEqual(second.visits, [])

    def test_changed_state_reseeds(self):
        MODULE._seed_storage_state(FakeContext(), str(self.profile), self.state_path)
        changed = dict(STATE, cookies=[dict(STATE["cookies"][0], value="rotated")])
        self.state_path.write_text(json.dumps(changed), encoding="utf-8")
        context = FakeContext()
        applied = MODULE._seed_storage_state(context, str(self.profile), self.state_path)
        self.assertEqual(applied, 1)
        self.assertEqual(context.cookies[0]["value"], "rotated")

    def test_failed_seed_writes_no_marker(self):
        class BrokenContext(FakeContext):
            def add_cookies(self, cookies):
                raise RuntimeError("cdp down")

        with self.assertRaises(RuntimeError):
            MODULE._seed_storage_state(BrokenContext(), str(self.profile), self.state_path)
        self.assertFalse((self.profile / MODULE._SEED_MARKER).exists())

    def test_missing_state_file_is_not_an_error(self):
        applied = MODULE._seed_storage_state(
            FakeContext(), str(self.profile), Path(self.tmp.name) / "absent.json")
        self.assertIsNone(applied)


class PreflightTest(unittest.TestCase):
    def test_invalid_port_rejected_before_launch(self):
        self.assertEqual(MODULE.main(["--profile", "/tmp/x", "--port", "70000"]), 1)
        self.assertEqual(MODULE.main(["--profile", "/tmp/x", "--port", "abc"]), 1)

    def test_preflight_only_accepts_a_roomy_filesystem(self):
        with tempfile.TemporaryDirectory() as raw:
            profile = str(Path(raw) / "profile")
            self.assertEqual(
                MODULE.main(["--profile", profile, "--port", "0", "--preflight-only"]), 0)


if __name__ == "__main__":
    unittest.main()
