import os, sys
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(os.environ.get("MR_BOT_REPO", Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(REPO_ROOT / "skills/anicca-mr-bot/scripts"))
sys.path.insert(0, str(REPO_ROOT / "skills/_shared"))
import lateness_check as lc
def run():
    assert hasattr(lc, "mr_bot_enabled"), "mr_bot_enabled missing"
    assert lc.mr_bot_enabled({"mrBot": {"enabled": False}}) is False
    assert lc.mr_bot_enabled({"mrBot": {"enabled": True}}) is True
    assert lc.mr_bot_enabled({}) is True
    assert lc.RELENTLESS_MAX_DEFAULT == 3, f"retry cap should be 3, got {getattr(lc,'RELENTLESS_MAX_DEFAULT','MISSING')}"
    with mock.patch.dict(os.environ, {"MR_BOT_TEST_VALUE": "runtime-injected"}, clear=False):
        assert lc.env("MR_BOT_TEST_VALUE") == "runtime-injected"
    print("PASS")
run()

def run_renraku():
    import renraku
    assert hasattr(renraku, "auto_send_allowed"), "auto_send_allowed missing"
    assert renraku.auto_send_allowed({}) is False
    assert renraku.auto_send_allowed({"lateness": {"autoSendMail": True}}) is True
    assert renraku.auto_send_allowed({"lateness": {"autoSendMail": False}}) is False
    with mock.patch.dict(os.environ, {"MR_BOT_TEST_VALUE": "runtime-injected"}, clear=False):
        assert renraku.env("MR_BOT_TEST_VALUE") == "runtime-injected"
    print("PASS renraku")
run_renraku()
