import importlib.util
import json
import pathlib
import subprocess
import sys


ROOT = pathlib.Path(__file__).parent


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_synthetic_engagement_calls_are_zero_and_setup_becomes_ready():
    lifecycle = load("lifecycle")
    calls = {"health": 0, "follow": 0, "like": 0, "comment": 0, "scroll": 0}

    def probe(_account):
        calls["health"] += 1
        return {"ok": True, "publisher": "meta_graph", "publisher_account_id": "1784"}

    account = {"handle": "fresh", "status": "setup"}
    result = lifecycle.advance_account(account, probe)
    assert result["status"] == "publisher_ready"
    assert calls == {"health": 1, "follow": 0, "like": 0, "comment": 0, "scroll": 0}


def test_publisher_health_failure_is_persisted_end_to_end(tmp_path):
    state = tmp_path / "accounts.json"
    state.write_text(json.dumps([{"handle": "fresh", "status": "setup"}]))
    fixture = tmp_path / "health.json"
    fixture.write_text(json.dumps({"ok": False, "error": "permission missing"}))
    run = subprocess.run(
        [sys.executable, str(ROOT / "lifecycle.py"), str(state), "--health-fixture", str(fixture)],
        text=True,
        capture_output=True,
    )
    assert run.returncode == 1
    account = json.loads(state.read_text())[0]
    assert account["status"] == "publisher_failed"
    assert account["publisher_state"]["error"] == "permission missing"


def test_terminal_current_account_is_never_reused():
    lifecycle = load("lifecycle")
    terminal = {"handle": "old", "status": "session_failed", "note": "terminal"}
    assert lifecycle.advance_account(terminal, lambda _: {"ok": True}) == terminal


def test_runtime_has_no_day_count_or_synthetic_warmup_branches():
    runtime = "\n".join(
        (ROOT / name).read_text()
        for name in ("lifecycle.py", "publisher.py", "warmer.py", "account_state.sh")
    ).lower()
    for forbidden in ("warming_day", "promote_day", "warm.py", "get_timeline_feed", ".follow(", ".like(", ".comment("):
        assert forbidden not in runtime


def test_all_product_manifests_share_contract_with_separate_namespaces():
    manifests = [ROOT / "manifests" / f"{name}.manifest.sh" for name in ("capafy", "clip", "slideshow")]
    text = [path.read_text() for path in manifests]
    assert all('MKT_LIFECYCLE_CONTRACT="marketing-engine/v1"' in source for source in text)
    assert all('MKT_PUBLISHER="meta_graph"' in source for source in text)
    namespaces = []
    for source in text:
        line = next(line for line in source.splitlines() if line.startswith("MKT_STATE_NAMESPACE="))
        namespaces.append(line.split("=", 1)[1].strip('"'))
    assert len(set(namespaces)) == 3
    assert all(namespace.startswith("marketing.") for namespace in namespaces)
