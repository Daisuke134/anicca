import os, sys
from pathlib import Path

REPO_ROOT = Path(os.environ.get("LIFE_MANAGER_REPO", Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(REPO_ROOT / "skills/anicca-life-manager/scripts"))
sys.path.insert(0, str(REPO_ROOT / "skills/_shared"))
import lateness_check as lc
def run():
    assert hasattr(lc, "life_manager_enabled"), "life_manager_enabled missing"
    assert lc.life_manager_enabled({"lifeManager": {"enabled": False}}) is False
    assert lc.life_manager_enabled({"lifeManager": {"enabled": True}}) is True
    assert lc.life_manager_enabled({}) is True
    assert lc.RELENTLESS_MAX_DEFAULT == 3, f"retry cap should be 3, got {getattr(lc,'RELENTLESS_MAX_DEFAULT','MISSING')}"
    print("PASS")
run()

def run_renraku():
    import renraku
    assert hasattr(renraku, "auto_send_allowed"), "auto_send_allowed missing"
    assert renraku.auto_send_allowed({}) is False
    assert renraku.auto_send_allowed({"lateness": {"autoSendMail": True}}) is True
    assert renraku.auto_send_allowed({"lateness": {"autoSendMail": False}}) is False
    print("PASS renraku")
run_renraku()
