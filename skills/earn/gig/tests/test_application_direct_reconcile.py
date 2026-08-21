import importlib.util
import inspect
import sys
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "application_direct.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("application_direct_reconcile_test", SCRIPT)
application_direct = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(application_direct)


def test_same_wake_reconcile_reuses_durable_parent_after_delay():
    source = inspect.getsource(application_direct.main)
    block = source[source.index("awaiting_exact_readback ="):source.index("if phase == \"refresh\"")]

    assert application_direct.SAME_WAKE_RECONCILE_DELAY_SECONDS == 60
    assert block.index("time.sleep(SAME_WAKE_RECONCILE_DELAY_SECONDS)") < block.index(
        "reconcile = _run_parent("
    )
    assert "attempt_budget_path=attempt_budget_path" in block
    assert 'lease_task=f"{lease_task}-reconcile"' in block
    assert "click_submit" not in block
