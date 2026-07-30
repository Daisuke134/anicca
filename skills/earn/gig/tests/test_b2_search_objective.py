import importlib.util
import json
import subprocess
import sys
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "b2_search_objective.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("b2_search_objective", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load b2_search_objective")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cursor():
    return {
        "source_id": "single:new",
        "previous_url": "https://coconala.com/requests?sort=new&page=8",
        "next_url": "https://coconala.com/requests?sort=new&page=9",
        "reason": "next_page",
        "prior_inspected_request_ids": ["5179001", "01KYKDECET9WAY0CKRBCKH81RC"],
    }


def test_checkpoint_survives_process_boundary_and_resumes_exact_next_page(tmp_path):
    module = load_module()
    state = tmp_path / "b2-search-objective.json"
    contract = tmp_path / "cursor.json"
    output = tmp_path / "resume.json"
    contract.write_text(json.dumps(cursor()))

    saved = module.checkpoint(
        state_path=state,
        cursor_path=contract,
        pass_id="pass-1",
        now=100,
    )
    resumed = module.resume(
        state_path=state,
        output_path=output,
        pass_id="pass-2",
        now=200,
    )

    assert saved["status"] == "active"
    assert saved["last_pass_id"] == "pass-1"
    assert resumed == cursor()
    assert json.loads(output.read_text()) == cursor()


def test_cli_resumes_the_exact_cursor_in_a_new_process(tmp_path):
    state = tmp_path / "b2-search-objective.json"
    contract = tmp_path / "cursor.json"
    output = tmp_path / "resume.json"
    contract.write_text(json.dumps(cursor()))

    checkpoint_process = subprocess.run(
        [
            sys.executable,
            str(MODULE_PATH),
            "checkpoint",
            "--state",
            str(state),
            "--cursor",
            str(contract),
            "--pass-id",
            "pass-1",
            "--now",
            "100",
        ],
        capture_output=True,
        text=True,
    )
    resume_process = subprocess.run(
        [
            sys.executable,
            str(MODULE_PATH),
            "resume",
            "--state",
            str(state),
            "--output",
            str(output),
            "--pass-id",
            "pass-2",
            "--now",
            "200",
        ],
        capture_output=True,
        text=True,
    )

    assert checkpoint_process.returncode == 0, checkpoint_process.stderr
    assert resume_process.returncode == 0, resume_process.stderr
    assert json.loads(resume_process.stdout) == cursor()
    assert json.loads(output.read_text()) == cursor()


def test_current_spot_route_checkpoint_resumes_exact_next_page(tmp_path):
    module = load_module()
    state = tmp_path / "b2-search-objective.json"
    contract = tmp_path / "cursor.json"
    output = tmp_path / "resume.json"
    current = {
        "source_id": "single:new",
        "previous_url": "https://coconala.com/job_matching/supplier/new?type=spot",
        "next_url": (
            "https://coconala.com/job_matching/supplier/new?type=spot&page=2"
        ),
        "reason": "next_page",
        "prior_inspected_request_ids": ["5183557"],
    }
    contract.write_text(json.dumps(current))

    module.checkpoint(
        state_path=state,
        cursor_path=contract,
        pass_id="1785373447-37605",
        now=100,
    )
    resumed = module.resume(
        state_path=state,
        output_path=output,
        pass_id="next-pass",
        now=200,
    )

    assert resumed == current
    assert json.loads(output.read_text()) == current


def test_four_verified_applications_complete_the_objective(tmp_path):
    module = load_module()
    state = tmp_path / "b2-search-objective.json"
    ledger = tmp_path / "applied.jsonl"
    state.write_text(json.dumps({
        "version": 1,
        "status": "active",
        "last_pass_id": "pass-1",
        "updated_at": 100,
        "cursor": cursor(),
    }))
    ledger.write_text("".join(
        json.dumps({
            "pass_id": "pass-2",
            "requestId": str(5179000 + index),
            "status": "applied",
            "submit_verified": True,
            "applied_page_verified": True,
        }) + "\n"
        for index in range(4)
    ))

    finished = module.finish(
        state_path=state,
        ledger_path=ledger,
        pass_id="pass-2",
        target=4,
        now=300,
    )

    assert finished["status"] == "completed"
    assert finished["verified_applications"] == 4
    assert module.resume(
        state_path=state,
        output_path=tmp_path / "resume.json",
        pass_id="pass-3",
        now=400,
    ) is None


def test_exhausted_wake_with_zero_results_remains_nonterminal(tmp_path):
    module = load_module()
    state = tmp_path / "b2-search-objective.json"
    ledger = tmp_path / "applied.jsonl"
    ledger.write_text("")

    finished = module.finish(
        state_path=state,
        ledger_path=ledger,
        pass_id="pass-2",
        target=4,
        now=300,
    )

    assert finished["status"] == "active"
    assert finished["verified_applications"] == 0
    assert finished["cursor"] == {
        "source_id": "single:new",
        "previous_url": "",
        "next_url": "https://coconala.com/requests?sort=new",
        "reason": "market_refresh_after_exhaustion",
    }
    assert finished["next_action"] == (
        "次の毎時サイクルで新着案件から探索を再開する"
    )


def test_checkpoint_rejects_non_marketplace_cursor(tmp_path):
    module = load_module()
    state = tmp_path / "b2-search-objective.json"
    contract = tmp_path / "cursor.json"
    contract.write_text(json.dumps({
        **cursor(),
        "next_url": "https://example.com/steal-session",
    }))

    try:
        module.checkpoint(
            state_path=state,
            cursor_path=contract,
            pass_id="pass-1",
            now=100,
        )
    except ValueError as error:
        assert str(error) == "cursor_next_url_invalid"
    else:
        raise AssertionError("invalid cursor was accepted")
    assert not state.exists()
