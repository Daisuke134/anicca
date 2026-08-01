import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CAPAFY_DAILY = ROOT / "earn" / "capafy-marketing" / "capafy-ig-marketing-daily.sh"
CONFIG = Path.home() / "profitable-claude" / "skills" / "agent-runner" / "config.json"


def declared_task_class(script: Path) -> str:
    matches = re.findall(r"--task-class\s+([a-z-]+)", script.read_text(encoding="utf-8"))
    assert matches, "Capafy daily runner has no declared task class"
    return matches[-1]


def shell_default(script_text: str, variable: str) -> int:
    match = re.search(rf'export {variable}="\$\{{[^:}}]+:-([0-9]+)\}}"', script_text)
    assert match, f"{variable} is not exported with a numeric default"
    return int(match.group(1))


def test_capafy_marketer_has_required_runtime_and_token_reservation():
    task_class = declared_task_class(CAPAFY_DAILY)
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert task_class == "marketing-agent"
    assert config["task_classes"][task_class]["timeout_seconds"] >= 900
    assert config["task_classes"][task_class]["token_reservation"] >= 49152


def test_capafy_marketer_arms_a_bounded_daily_token_budget():
    text = CAPAFY_DAILY.read_text(encoding="utf-8")
    assert 'export ANICCA_BUDGET_SCOPE_ID=' in text
    pass_budget = shell_default(text, "ANICCA_PASS_TOKEN_BUDGET")
    daily_budget = shell_default(text, "ANICCA_LOOP_DAILY_TOKEN_BUDGET")
    assert 49152 <= pass_budget <= daily_budget
    assert daily_budget <= 2097152
