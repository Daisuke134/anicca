import importlib.util
import subprocess
from pathlib import Path


ROOT = Path(__file__).parent
SPEC = importlib.util.spec_from_file_location("warmer", ROOT / "warmer.py")
warmer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(warmer)


class NeverClient:
    def __init__(self):
        raise AssertionError("instagrapi client must not be created before day3")


def test_day1_instagrapi_login_is_refused(tmp_path):
    result = warmer.establish_golden_session(
        "fresh", home=str(tmp_path), client_factory=NeverClient, warming_day_value=1
    )
    assert result["ok"] is False
    assert result["refused"] == "warming_day<3"


def test_golden_client_uses_required_delay_range(tmp_path):
    cloak = tmp_path / ".cloak"
    cloak.mkdir()
    (cloak / "ig-ready.json").write_text('{"username":"ready","pw":"secret"}')

    class Client:
        delay_range = None
        def login(self, username, password): return True
        def get_timeline_feed(self): return {"ok": True}
        def dump_settings(self, path): Path(path).write_text("{}")

    client = Client()
    result = warmer.establish_golden_session(
        "ready", home=str(tmp_path), client_factory=lambda: client, warming_day_value=3
    )
    assert result["ok"] is True
    assert client.delay_range == [1, 3]


def test_provision_refuses_main_9222_context():
    script = ROOT / "provision_prompt.sh"
    result = subprocess.run(
        ["bash", "-c", f"source {script!s}; require_ig_isolated_context 9222 dedicated-1"],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "main context" in result.stderr


def test_provision_accepts_dedicated_context():
    script = ROOT / "provision_prompt.sh"
    result = subprocess.run(
        ["bash", "-c", f"source {script!s}; require_ig_isolated_context 9331 dedicated-1"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0


def test_provision_requires_idempotent_cdp_field_replacement():
    script = ROOT / "provision_prompt.sh"
    env = {
        "IG_PROVISION_ACCOUNT_STATE_FILE": "/tmp/accounts.json",
        "IG_PROVISION_HANDLE_PREFIX": "capafy.skills",
        "IG_PROVISION_INSTANCE": "capafy",
        "IG_PROVISION_GMAIL_PLUS_TAG_PREFIX": "capafy",
        "IG_PROVISION_BIO_TEXT": "bio",
        "IG_PROVISION_BROWSER_INSTRUCTIONS": "Attach to isolated CDP.",
        "IG_PROVISION_PORT": "9331",
        "IG_PROVISION_CONTEXT_ID": "dedicated-1",
    }
    command = f"source {script!s}; render_ig_provision_prompt"
    result = subprocess.run(
        ["bash", "-c", command], capture_output=True, text=True, env=env,
    )
    assert result.returncode == 0
    assert "cdp.py replace" in result.stdout
    assert "Never retry a field with insert" in result.stdout
    assert "read the field value length back" in result.stdout
