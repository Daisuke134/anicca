"""Contract tests for the dedicated, parent-owned Apply executor."""

from __future__ import annotations

import json
import hashlib
import os
import plistlib
import sqlite3
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
DIRECT = SCRIPTS / "application_direct.py"
PLIST = ROOT / "launchd" / "ai.anicca.hf-gig-apply-direct.plist"
sys.path.insert(0, str(SCRIPTS))
from telegram_outbox import TelegramOutbox
import application_direct as direct


def _write_python(path: Path, body: str) -> Path:
    path.write_text("#!/usr/bin/env python3\n" + body, encoding="utf-8")
    path.chmod(0o755)
    return path


def test_direct_apply_ignores_legacy_category_and_budget_filters() -> None:
    prep = direct._official_open_scan_prep({
        "target_apply_per_pass": 7,
        "max_apply_per_pass": 7,
        "category_order": ["動画編集", "コンサル"],
        "skip_categories": ["データ入力"],
        "apply_skip_thresholds": {
            "max_applicants": 12,
            "min_contracted_to_skip": 1,
            "min_budget_jpy": 3000,
        },
        "active_strategy_experiment": {"id": "legacy"},
    })

    assert prep["target_apply_per_pass"] == 20
    assert prep["max_apply_per_pass"] == 20
    assert prep["category_order"] == []
    assert prep["apply_skip_thresholds"]["min_budget_jpy"] == 0
    assert prep["active_strategy_experiment"] is None


def _lifecycle_row(request_id: str, *, form_state: str = "present", deadline_value: str = "2026-08-20") -> dict[str, object]:
    row: dict[str, object] = {
        "request_id": request_id, "canonical_url": f"https://coconala.com/requests/{request_id}",
        "title": f"request-{request_id}", "observed_at": "2026-08-13T00:00:00Z",
        "page_state": "present", "accepting_control": "present", "deadline_state": "future",
        "deadline_value": deadline_value, "form_state": form_state,
    }
    row["lifecycle_sha256"] = hashlib.sha256(json.dumps(
        {key: row[key] for key in ("request_id", "canonical_url", "page_state", "accepting_control", "deadline_state", "deadline_value", "form_state")},
        ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()
    if form_state != "present":
        row.update(status="officially_unavailable", reason_codes=[f"form_state:{form_state}"])
    return row


def _phase_evidence(root: Path, request_id: str, lifecycle: list[dict[str, object]]) -> None:
    root.mkdir()
    (root / "application-snapshot.json").write_text(json.dumps({"request_details": [{"request_id": request_id, "title": request_id}]}))
    (root / "application-decisions.json").write_text(json.dumps({"decisions": []}))
    (root / "parent-commit.json").write_text(json.dumps({"results": []}))
    (root / "application-observations.json").write_text(json.dumps({
        "version": 1, "raw_request_ids": [request_id], "already_applied_ids": [],
        "quarantined_ids": [], "filtered_results": [], "lifecycle_results": lifecycle,
    }))


def _fake_commands(root: Path) -> dict[str, Path]:
    prep = _write_python(root / "passprep.py", """
import json
from pathlib import Path
marker = Path(__file__).with_suffix('.calls')
marker.write_text(marker.read_text() + '1\\n' if marker.exists() else '1\\n')
print(json.dumps({'ok': True, 'pass_id': 'apply-direct-test',
                  'target_apply_per_pass': 8, 'max_apply_per_pass': 20,
                  'target_retainer_applications': 0,
                  'required_search_source_ids': ['single:new']}))
""")
    gate = _write_python(root / "b2_gate.py", """
import json
import os
import sys
from pathlib import Path
args = sys.argv
command = args[1]
marker = Path(__file__).with_suffix('.calls')
marker.write_text(marker.read_text() + command + '\\n' if marker.exists() else command + '\\n')
if command == 'build':
    out = Path(args[args.index('--output') + 1])
    required = (['single:new', 'single:category:次の情報源']
                if os.environ.get('FAKE_PARENT_MODE') == 'source-denied' else ['single:new'])
    out.write_text(json.dumps({'context_version': 7, 'objective': {
        'target_applications': 8, 'max_applications': 20,
        'target_retainer_applications': 0,
        'required_search_source_ids': required},
        'target_applications': 8, 'target_retainer_applications': 0,
        'required_search_source_ids': required}))
elif command == 'validate':
    if os.environ.get('FAKE_PARENT_MODE') == 'gate-blocking':
        print(json.dumps({'ok': False, 'errors': ['context_path_mismatch']}))
        raise SystemExit(1)
    print(json.dumps({'ok': True, 'errors': []}))
elif command == 'continuable':
    print(json.dumps({'continuable': False, 'verified_count': 0, 'target': 8}))
    raise SystemExit(1)
""")
    posting = _write_python(root / "posting_source.py", """
import os
from pathlib import Path
marker = Path(__file__).with_suffix('.calls')
marker.write_text(marker.read_text() + 'harvest\\n' if marker.exists() else 'harvest\\n')
if os.environ.get('FAKE_PARENT_MODE') == 'posting-fail':
    raise SystemExit(7)
""")
    brake = _write_python(root / "gig_brake.sh", "raise SystemExit(1)\n")
    parent = _write_python(root / "parent.py", """
import json
import os
import sys
from pathlib import Path
args = sys.argv
out = Path(args[args.index('--output') + 1])
evidence = Path(args[args.index('--evidence-dir') + 1])
evidence.mkdir(parents=True, exist_ok=True)
calls = evidence.parent / 'parent.calls'
calls.write_text(calls.read_text() + '1\\n' if calls.exists() else '1\\n')
cursor_path = Path(args[args.index('--cursor-contract') + 1]) if '--cursor-contract' in args else None
cursor = json.loads(cursor_path.read_text()) if cursor_path else None
phase = 'refresh' if cursor and 'page=' not in cursor.get('next_url', '') else 'coverage' if cursor else 'normal'
mode = os.environ.get('FAKE_PARENT_MODE', '')
source_id = (cursor or {}).get('source_id', 'single:new')
if mode == 'source-denied' and source_id == 'single:new' and cursor and 'page=' in cursor.get('next_url', ''):
    print(json.dumps({'ok': False, 'error': 'source_access_denied:single:new',
                      'error_type': 'ParentContractError'}), file=sys.stderr)
    raise SystemExit(2)
if not cursor:
    details = [
        {'request_id': 'newer', 'posted_at': '2026-08-11T02:00:00Z'},
        {'request_id': 'oldest', 'posted_at': '2026-08-11T01:00:00Z'},
        {'request_id': 'latest', 'observed_at': '2026-08-11T03:00:00Z'},
    ]
    decisions = [{'business_class': 'submit_required'}, {'business_class': 'submit_required'}]
    results = [
        {'status': 'confirmed'},
        {'status': 'awaiting_exact_id_readback'},
        {'status': 'submission_runtime_failed'},
    ]
elif mode == 'refresh-actionable' and phase == 'refresh':
    details = [{'request_id': 'refresh-action', 'title': '新着対象'}]
    decisions = [{'request_id': 'refresh-action', 'business_class': 'submit_required'}]
    results = [{'request_id': 'refresh-action', 'status': 'awaiting_exact_id_readback'}]
elif mode == 'hidden-refresh-effect' and phase == 'refresh':
    details = [{'request_id': 'hidden-effect', 'title': '新着確認済み'}]
    decisions = []
    results = [{'request_id': 'hidden-effect', 'status': 'confirmed'}]
elif mode == 'refresh-duplicate' and phase == 'refresh':
    details = [{'request_id': '91000060', 'title': '既存案件'}]
    decisions = [{'request_id': '91000060', 'business_class': 'duplicate_fenced'}]
    results = [{'request_id': '91000060', 'status': 'prepared_unconfirmed', 'business_class': 'duplicate_fenced'}]
elif mode == 'refresh-local-failure' and phase == 'refresh':
    details = [{'request_id': '91000061', 'title': '構造化判断欠落'}]
    decisions = []
    results = []
elif mode == 'overlap':
    if phase == 'refresh':
        details = [{'request_id': 'shared', 'title': '重複案件'}]
        decisions = [{'request_id': 'shared', 'business_class': 'hard_prohibited', 'reason_codes': ['mandatory_human_presence', '本人の顔出し出演が必須です。']}]
        results = [{'request_id': 'shared', 'status': 'hard_prohibited', 'business_class': 'hard_prohibited'}]
    else:
        details = [
            {'request_id': 'shared', 'title': '重複案件'},
            {'request_id': 'coverage-only', 'title': 'カバレッジ案件'},
        ]
        decisions = [{'request_id': 'shared', 'business_class': 'submit_required'},
                     {'request_id': 'coverage-only', 'business_class': 'hard_prohibited', 'reason_codes': ['mandatory_human_presence', '本人の顔出し出演が必須です。']}]
        results = [{'request_id': 'shared', 'status': 'confirmed'},
                   {'request_id': 'coverage-only', 'status': 'hard_prohibited', 'business_class': 'hard_prohibited'}]
else:
    details = [] if phase == 'refresh' else [{'request_id': 'coverage-only', 'title': '確認案件'}]
    decisions = [] if phase == 'refresh' else [{'request_id': 'coverage-only', 'business_class': 'hard_prohibited', 'reason_codes': ['mandatory_human_presence', '本人の顔出し出演が必須です。']}]
    results = [] if phase == 'refresh' else [{'request_id': 'coverage-only', 'status': 'hard_prohibited', 'business_class': 'hard_prohibited'}]
(evidence / 'application-snapshot.json').write_text(json.dumps({'request_details': details}))
(evidence / 'application-decisions.json').write_text(json.dumps({'decisions': decisions}))
(evidence / 'parent-commit.json').write_text(json.dumps({
    'planner_missing_request_ids': ['91000061'] if mode == 'refresh-local-failure' and phase == 'refresh' else [],
    'results': results,
}))
(evidence / 'application-observations.json').write_text(json.dumps({
    'version': 1,
    'raw_request_ids': [str(row['request_id']) for row in details if row.get('request_id')],
    'already_applied_ids': [],
    'quarantined_ids': [],
    'filtered_results': [],
    'lifecycle_results': [],
}))
source_url = (cursor or {}).get('next_url', 'https://coconala.com/requests?sort=new&recruiting=true')
has_next = 'yes' if mode == 'malformed-source' and phase == 'coverage' else bool(cursor) and mode != 'exhausted'
exhausted = has_next is False
out.write_text(json.dumps({'status': 'ok', 'applications': [], 'current_b2': {
    'search_sources': [{'source_id': source_id, 'url': source_url,
                       'has_next': has_next, 'exhausted': exhausted,
                       'inspected_count': len(details)}],
    'inspected_requests': details,
}}))
(evidence / 'summary.json').write_text(json.dumps({
    'status': 'success', 'task_label': 'gig-B2', 'result_path': str(out.resolve()),
}))
print(json.dumps({'status': 'ok'}))
""")
    openclaw = _write_python(root / "openclaw.py", """
import json
import sys
from pathlib import Path
args = sys.argv
message = args[args.index('--message') + 1]
marker = Path(__file__).with_suffix('.messages.jsonl')
with marker.open('a', encoding='utf-8') as handle:
    handle.write(json.dumps({'message': message}, ensure_ascii=False) + '\\n')
message_id = 'tg-current' if 'pass_id: current-pass' in message else 'tg-apply-1'
print(json.dumps({'messageId': message_id}))
""")
    return {'prep': prep, 'gate': gate, 'posting': posting, 'brake': brake, 'parent': parent, 'openclaw': openclaw}


def _invoke(root: Path, commands: dict[str, Path], output: Path,
            *, pass_id: str | None = "apply-direct-test", lock_held: bool = True,
            all_eligible: bool = False,
            search_objective_state: Path | None = None,
            fake_parent_mode: str | None = None) -> subprocess.CompletedProcess[str]:
    state = root / "state"
    env = os.environ.copy()
    if lock_held:
        env["GIG_CDP_LOCK_HELD"] = "1"
    else:
        env.pop("GIG_CDP_LOCK_HELD", None)
    if pass_id is None:
        env.pop("GIG_APPLY_PASS_ID", None)
    if fake_parent_mode is not None:
        env["FAKE_PARENT_MODE"] = fake_parent_mode
    command = [
        sys.executable, str(DIRECT),
        "--state-dir", str(state), "--passprep", str(commands['prep']),
        "--b2-gate", str(commands['gate']), "--parent", str(commands['parent']),
        "--posting-source", str(commands['posting']),
        "--operator-brake", str(commands['brake']),
        "--lease-script", str(root / "lease.py"),
        "--planner-runner", str(root / "runner.py"),
        "--intent-root", str(root / "intents"), "--ledger", str(root / "applied.jsonl"),
        "--telegram-database", str(root / "telegram-outbox.sqlite3"),
        "--telegram-target", "42", "--openclaw", str(commands['openclaw']),
        "--telegram-receipt-dir", str(root / "receipts"),
        "--output", str(output),
    ]
    if pass_id is not None:
        command[2:2] = ["--pass-id", pass_id]
    if all_eligible:
        command.append("--all-eligible")
    objective_state = search_objective_state or (root / "absent-b2-search-objective.json")
    command.extend(["--search-objective-state", str(objective_state)])
    return subprocess.run(command, env=env, capture_output=True, text=True, check=False)


def test_active_objective_wake_runs_refresh_then_coverage_and_checkpoints(tmp_path: Path):
    commands = _fake_commands(tmp_path)
    objective_state = tmp_path / "b2-search-objective.json"
    objective_state.write_text(json.dumps({
        "version": 1,
        "status": "active",
        "last_pass_id": "previous-pass",
        "updated_at": 1723340000,
        "cursor": {
            "source_id": "single:new",
            "previous_url": "https://coconala.com/requests?sort=new&recruiting=true&page=80",
            "next_url": "https://coconala.com/requests?sort=new&recruiting=true&page=81",
            "reason": "next_page",
            "prior_inspected_request_ids": ["91000059"],
        },
    }), encoding="utf-8")

    result = _invoke(
        tmp_path, commands, tmp_path / "active.json",
        pass_id="active-pass", search_objective_state=objective_state,
    )

    assert result.returncode == 0, result.stderr
    invocations = [
        json.loads((tmp_path / "state" / "active-pass" / f"parent.invocation-{phase}.json").read_text())
        for phase in ("refresh", "coverage")
    ]
    assert len((tmp_path / "state" / "active-pass" / "parent.calls").read_text().splitlines()) == 3
    refresh_args = invocations[0]["argv"]
    coverage_args = invocations[1]["argv"]
    assert refresh_args[refresh_args.index("--cursor-contract") + 1].endswith("b2-refresh-cursor.json")
    assert coverage_args[coverage_args.index("--cursor-contract") + 1].endswith("b2-coverage-cursor.json")
    assert coverage_args[coverage_args.index("--lease-task") + 1].endswith("-coverage")
    assert refresh_args.count("--all-eligible") == coverage_args.count("--all-eligible") == 0
    attempt_budget = str(
        tmp_path / "state" / "active-pass" / "submit-attempt-budget.json"
    )
    for phase in ("refresh", "coverage", "coverage-2"):
        argv = json.loads(
            (tmp_path / "state" / "active-pass" / f"parent.invocation-{phase}.json").read_text()
        )["argv"]
        assert argv[argv.index("--attempt-budget") + 1] == attempt_budget
    state = json.loads(objective_state.read_text(encoding="utf-8"))
    assert state["cursor"]["next_url"].endswith("page=83")
    payload = json.loads((tmp_path / "active.json").read_text(encoding="utf-8"))
    assert "既存B2 cursorを3 turn確認し、次pageへcheckpoint" in payload["report"]
    assert payload["failed"] == payload["pending"] == 0
    messages = [
        json.loads(line)["message"]
        for line in (tmp_path / "openclaw.messages.jsonl").read_text().splitlines()
    ]
    decisions = [message for message in messages if "[ココナラ][応募判断]" in message]
    assert len(decisions) == 1
    assert "coverage-only" in decisions[0] and "本人の出演・通話・面談" in decisions[0]
    assert sum("[ココナラ][応募]" in message for message in messages) == 1
    with sqlite3.connect(tmp_path / "telegram-outbox.sqlite3") as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM telegram_reports WHERE kind='apply-decision'"
        ).fetchone()[0] == 1


def test_active_refresh_actionable_does_not_run_coverage_or_checkpoint(tmp_path: Path):
    commands = _fake_commands(tmp_path)
    objective_state = tmp_path / "objective.json"
    original = {
        "version": 1, "status": "active", "last_pass_id": "old", "updated_at": 1,
        "cursor": {"source_id": "single:new", "previous_url": "https://coconala.com/requests?sort=new&recruiting=true&page=80",
                   "next_url": "https://coconala.com/requests?sort=new&recruiting=true&page=81", "reason": "next_page"},
    }
    objective_state.write_text(json.dumps(original), encoding="utf-8")
    result = _invoke(tmp_path, commands, tmp_path / "actionable.json", pass_id="actionable-pass",
                     search_objective_state=objective_state, fake_parent_mode="refresh-actionable")
    assert result.returncode == 0, result.stderr
    assert len((tmp_path / "state" / "actionable-pass" / "parent.calls").read_text().splitlines()) == 1
    assert json.loads(objective_state.read_text()) == original
    payload = json.loads((tmp_path / "actionable.json").read_text())
    assert "新着処理に応募対象1件または確認待ち1件があるため、深掘りを停止" in payload["report"]


def test_coverage_cursor_never_backtracks_to_an_earlier_missing_source(tmp_path: Path) -> None:
    context = tmp_path / "context.json"
    context.write_text(json.dumps({
        "target_applications": 8,
        "target_retainer_applications": 0,
        "required_search_source_ids": [
            "single:new", "single:category:first", "single:category:current",
            "single:category:next",
        ],
    }), encoding="utf-8")
    current_cursor = tmp_path / "current-cursor.json"
    current_cursor.write_text(json.dumps({
        "source_id": "single:category:current",
        "previous_url": "",
        "next_url": "https://coconala.com/requests?keyword=current&recruiting=true",
        "reason": "inspect_missing_source_by_keyword",
    }), encoding="utf-8")
    result = tmp_path / "result.json"
    result.write_text(json.dumps({
        "applications": [],
        "current_b2": {
            "search_sources": [{
                "source_id": "single:category:current",
                "url": "https://coconala.com/requests?keyword=current&recruiting=true",
                "has_next": False, "exhausted": True, "inspected_count": 0,
            }],
            "inspected_requests": [],
        },
    }), encoding="utf-8")
    summary = tmp_path / "summary.json"
    summary.write_text(json.dumps({
        "status": "success", "task_label": "gig-B2",
        "result_path": str(result.resolve()),
    }), encoding="utf-8")

    cursor = direct.next_search_cursor(summary, context, cursor_path=current_cursor)

    assert cursor["source_id"] == "single:category:next"
    assert cursor["source_id"] not in {"single:new", "single:category:first"}


def test_temporary_source_denial_continues_to_next_source_without_checkpoint(tmp_path: Path):
    commands = _fake_commands(tmp_path)
    objective_state = tmp_path / "objective.json"
    original = {
        "version": 1, "status": "active", "last_pass_id": "old", "updated_at": 1,
        "cursor": {
            "source_id": "single:new",
            "previous_url": "https://coconala.com/requests?sort=new&recruiting=true&page=80",
            "next_url": "https://coconala.com/requests?sort=new&recruiting=true&page=81",
            "reason": "next_page",
        },
    }
    objective_state.write_text(json.dumps(original), encoding="utf-8")

    result = _invoke(
        tmp_path, commands, tmp_path / "source-denied.json",
        pass_id="source-denied-pass", search_objective_state=objective_state,
        fake_parent_mode="source-denied",
    )

    assert result.returncode == 0, result.stderr
    run_dir = tmp_path / "state" / "source-denied-pass"
    failures = json.loads((run_dir / "temporary-source-failures.json").read_text())
    assert failures["sources"] == [{
        "source_id": "single:new", "phase": "coverage",
        "error": "source_access_denied", "temporary": True, "exhausted": False,
    }]
    fallback = json.loads((run_dir / "b2-next-cursor-1.json").read_text())
    assert fallback["source_id"] == "single:category:次の情報源"
    assert fallback["reason"] == "continue_after_temporary_source_failure"
    assert json.loads(objective_state.read_text()) == original
    payload = json.loads((tmp_path / "source-denied.json").read_text())
    assert payload["failed"] == 1
    assert "一時拒否source 1件を未完のまま保持し、次sourceまで継続" in payload["report"]
    assert len((run_dir / "parent.calls").read_text().splitlines()) == 3


def test_blocking_b2_validation_stops_before_cursor_checkpoint(tmp_path: Path):
    commands = _fake_commands(tmp_path)
    objective_state = tmp_path / "objective.json"
    original = {
        "version": 1, "status": "active", "last_pass_id": "old", "updated_at": 1,
        "cursor": {"source_id": "single:new", "previous_url": "https://coconala.com/requests?sort=new&recruiting=true&page=80",
                   "next_url": "https://coconala.com/requests?sort=new&recruiting=true&page=81", "reason": "next_page"},
    }
    objective_state.write_text(json.dumps(original), encoding="utf-8")

    result = _invoke(
        tmp_path, commands, tmp_path / "blocked.json", pass_id="blocked-pass",
        search_objective_state=objective_state, fake_parent_mode="gate-blocking",
    )

    assert result.returncode != 0
    assert json.loads(objective_state.read_text()) == original
    assert len((tmp_path / "state" / "blocked-pass" / "parent.calls").read_text().splitlines()) == 1
    gate = json.loads((tmp_path / "state" / "blocked-pass" / "b2-gate-result-refresh.json").read_text())
    assert gate == {"ok": False, "errors": ["context_path_mismatch"]}
    assert not (tmp_path / "posting_source.calls").exists()


def test_posting_harvest_failure_is_nonfatal_after_valid_parent_result(tmp_path: Path):
    commands = _fake_commands(tmp_path)

    result = _invoke(
        tmp_path, commands, tmp_path / "posting-fail.json",
        fake_parent_mode="posting-fail",
    )

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "posting_source.calls").read_text().splitlines() == ["harvest"]


def test_held_operator_brake_reports_before_source_planner_or_browser(tmp_path: Path):
    commands = _fake_commands(tmp_path)
    commands["brake"] = _write_python(tmp_path / "held_brake.py", "raise SystemExit(0)\n")

    result = _invoke(tmp_path, commands, tmp_path / "held.json", pass_id="held-pass")

    assert result.returncode != 0
    payload = json.loads((tmp_path / "held.json").read_text())
    assert payload["status"] == "operator_brake"
    assert payload["effect"] == payload["readback"] == payload["failed"] == 0
    assert "応募処理を開始しませんでした" in payload["report"]
    assert not (tmp_path / "passprep.calls").exists()
    assert not (tmp_path / "state" / "held-pass" / "parent.calls").exists()
    assert json.loads((tmp_path / "openclaw.messages.jsonl").read_text().splitlines()[0])["message"] == payload["report"]


def test_operator_brake_check_failure_is_fail_closed(tmp_path: Path):
    commands = _fake_commands(tmp_path)
    commands["brake"] = _write_python(tmp_path / "broken_brake.py", "raise SystemExit(2)\n")

    result = _invoke(tmp_path, commands, tmp_path / "failed.json", pass_id="failed-pass")

    assert result.returncode != 0
    payload = json.loads((tmp_path / "failed.json").read_text())
    assert payload["status"] == "failed"
    assert payload["error"] == "operator_brake_check_failed"
    assert payload["effect"] == payload["readback"] == 0
    assert payload["failed"] == 1
    assert not (tmp_path / "passprep.calls").exists()
    assert not (tmp_path / "state" / "failed-pass" / "parent.calls").exists()


def test_parent_renderer_wedge_retries_once_with_fresh_context(tmp_path: Path):
    parent = _write_python(tmp_path / "parent.py", """
import json
from pathlib import Path
marker = Path(__file__).with_suffix('.calls')
attempt = len(marker.read_text().splitlines()) + 1 if marker.exists() else 1
marker.write_text((marker.read_text() if marker.exists() else '') + f'{attempt}\\n')
if attempt == 1:
    print(json.dumps({'ok': False, 'error': 'cdp_browser_wedged_for_every_attempt'}))
    raise SystemExit(1)
print(json.dumps({'ok': True}))
""")
    stdout = tmp_path / "parent.stdout"
    stderr = tmp_path / "parent.stderr"

    completed = direct._run_parent(
        [sys.executable, str(parent)], os.environ.copy(), stdout, stderr,
    )

    assert completed.returncode == 0
    assert parent.with_suffix(".calls").read_text().splitlines() == ["1", "2"]
    assert json.loads(stdout.with_suffix(".recovery.json").read_text()) == {
        "trigger": "cdp_browser_wedged_for_every_attempt",
        "attempts": 2,
        "first_returncode": 1,
        "final_returncode": 0,
    }
    assert json.loads(stdout.with_name("parent.stdout.attempt-1").read_text())["error"] == "cdp_browser_wedged_for_every_attempt"


def test_parent_non_renderer_failure_is_not_retried(tmp_path: Path):
    parent = _write_python(tmp_path / "parent.py", """
import json
from pathlib import Path
marker = Path(__file__).with_suffix('.calls')
marker.write_text(marker.read_text() + '1\\n' if marker.exists() else '1\\n')
print(json.dumps({'ok': False, 'error': 'planner_failed'}))
raise SystemExit(1)
""")
    stdout = tmp_path / "parent.stdout"

    completed = direct._run_parent(
        [sys.executable, str(parent)], os.environ.copy(), stdout, tmp_path / "parent.stderr",
    )

    assert completed.returncode == 1
    assert parent.with_suffix(".calls").read_text().splitlines() == ["1"]
    assert not stdout.with_suffix(".recovery.json").exists()


def test_parent_renderer_retry_preserves_first_submission_failure(tmp_path: Path):
    parent = _write_python(tmp_path / "parent.py", """
import json, sys
from pathlib import Path
evidence = Path(sys.argv[sys.argv.index('--evidence-dir') + 1])
evidence.mkdir(parents=True, exist_ok=True)
marker = Path(__file__).with_suffix('.calls')
attempt = len(marker.read_text().splitlines()) + 1 if marker.exists() else 1
marker.write_text((marker.read_text() if marker.exists() else '') + f'{attempt}\\n')
status = 'submission_runtime_failed:ParentContractError' if attempt == 1 else 'prepared_unconfirmed'
business_class = None if attempt == 1 else 'duplicate_fenced'
(evidence / 'parent-commit.json').write_text(json.dumps({
    'planner_missing_request_ids': [],
    'results': [{'request_id': '5210212', 'status': status, 'business_class': business_class}],
}))
if attempt == 1:
    print(json.dumps({'ok': False, 'error': 'cdp_browser_wedged_for_every_attempt', 'results': 1}))
    raise SystemExit(1)
print(json.dumps({'ok': True, 'results': 1}))
""")
    evidence = tmp_path / "evidence"
    stdout = tmp_path / "parent.stdout"

    completed = direct._run_parent(
        [sys.executable, str(parent), "--evidence-dir", str(evidence)],
        os.environ.copy(), stdout, tmp_path / "parent.stderr",
    )

    assert completed.returncode == 0
    assert parent.with_suffix(".calls").read_text().splitlines() == ["1", "2"]
    first = json.loads((evidence / "parent-commit.attempt-1.json").read_text())
    merged = json.loads((evidence / "parent-commit.json").read_text())
    assert first["results"][0]["status"].startswith("submission_runtime_failed")
    assert merged["results"] == first["results"]


def test_b2_readback_aggregate_removes_an_id_later_observed(tmp_path: Path):
    commands = _fake_commands(tmp_path)
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "summary.json").write_text("{}")
    for name, request_ids in (("first", []), ("second", ["5210001"])):
        (evidence / f"parent-B2-applied-readback-{name}.json").write_text(json.dumps({
            "source": "code_owned_cdp_readback", "observed": True, "not_found": False,
            "expected_ids": ["5210001"], "request_ids": request_ids,
            "url": "https://coconala.com/mypage/job_matching/applied/offers",
        }))
    context = tmp_path / "context.json"
    context.write_text("{}")
    args = SimpleNamespace(
        b2_gate=commands["gate"], intent_root=tmp_path / "intents",
        ledger=tmp_path / "applied.jsonl",
    )

    assert direct._validate_parent_result(
        args=args, run_dir=tmp_path, phase="refresh", evidence_dir=evidence,
        context=context, pass_id="aggregate-pass", cursor_path=None,
        deferred_cursor_path=tmp_path / "cursor.json",
    ) == 0
    payload = json.loads((tmp_path / "code-applied-readback.json").read_text())
    assert payload["request_ids"] == ["5210001"]
    assert payload["applied_page_absent_request_ids"] == []


def test_refresh_hidden_effect_never_runs_coverage(tmp_path: Path):
    commands = _fake_commands(tmp_path)
    objective_state = tmp_path / "objective.json"
    original = {
        "version": 1, "status": "active", "last_pass_id": "old", "updated_at": 1,
        "cursor": {"source_id": "single:new", "previous_url": "https://coconala.com/requests?sort=new&recruiting=true&page=80",
                   "next_url": "https://coconala.com/requests?sort=new&recruiting=true&page=81", "reason": "next_page"},
    }
    objective_state.write_text(json.dumps(original), encoding="utf-8")

    result = _invoke(
        tmp_path, commands, tmp_path / "hidden-effect.json", pass_id="hidden-effect-pass",
        search_objective_state=objective_state, fake_parent_mode="hidden-refresh-effect",
        all_eligible=True,
    )

    assert result.returncode != 0
    assert len((tmp_path / "state" / "hidden-effect-pass" / "parent.calls").read_text().splitlines()) == 1
    assert json.loads(objective_state.read_text()) == original
    payload = json.loads((tmp_path / "hidden-effect.json").read_text())
    assert payload["effect"] == payload["readback"] == 1
    assert payload["failed"] == 1
    assert payload["business_success"] is False
    assert "新着処理の集計が不整合" in payload["report"]


def test_active_refresh_duplicate_only_runs_coverage_and_checkpoints(tmp_path: Path):
    commands = _fake_commands(tmp_path)
    objective_state = tmp_path / "objective.json"
    objective_state.write_text(json.dumps({
        "version": 1,
        "status": "active",
        "last_pass_id": "old",
        "updated_at": 1,
        "cursor": {
            "source_id": "single:new",
            "previous_url": "https://coconala.com/requests?sort=new&recruiting=true&page=80",
            "next_url": "https://coconala.com/requests?sort=new&recruiting=true&page=81",
            "reason": "next_page",
        },
    }), encoding="utf-8")

    result = _invoke(
        tmp_path, commands, tmp_path / "duplicate.json", pass_id="duplicate-pass",
        search_objective_state=objective_state, fake_parent_mode="refresh-duplicate",
    )

    assert result.returncode == 0, result.stderr
    assert len((tmp_path / "state" / "duplicate-pass" / "parent.calls").read_text().splitlines()) == 3
    state = json.loads(objective_state.read_text(encoding="utf-8"))
    assert state["cursor"]["next_url"].endswith("page=83")
    assert state["cursor"]["prior_inspected_request_ids"] == ["91000060"]
    payload = json.loads((tmp_path / "duplicate.json").read_text(encoding="utf-8"))
    assert payload["effect"] == payload["readback"] == 0
    assert sum(row["request_id"] == "91000060" for row in payload["report_results"]) == 1
    assert "重複防止1件" in payload["report"]
    assert "91000060" not in payload["report"]
    wake_cursor = json.loads(
        (tmp_path / "state" / "duplicate-pass" / "b2-coverage-cursor.json").read_text()
    )
    assert wake_cursor["prior_inspected_request_ids"] == ["91000060"]


def test_refresh_planner_missing_is_local_and_deep_coverage_continues(tmp_path: Path):
    commands = _fake_commands(tmp_path)
    objective_state = tmp_path / "objective.json"
    objective_state.write_text(json.dumps({
        "version": 1, "status": "active", "last_pass_id": "old", "updated_at": 1,
        "cursor": {"source_id": "single:new", "previous_url": "https://coconala.com/requests?sort=new&recruiting=true&page=80",
                   "next_url": "https://coconala.com/requests?sort=new&recruiting=true&page=81", "reason": "next_page"},
    }), encoding="utf-8")

    result = _invoke(
        tmp_path, commands, tmp_path / "local-failure.json", pass_id="local-failure-pass",
        search_objective_state=objective_state, fake_parent_mode="refresh-local-failure",
    )

    assert result.returncode == 0, result.stderr
    assert len((tmp_path / "state" / "local-failure-pass" / "parent.calls").read_text().splitlines()) == 3
    assert json.loads(objective_state.read_text())["cursor"]["next_url"].endswith("page=83")
    payload = json.loads((tmp_path / "local-failure.json").read_text())
    assert payload["failed"] == 1
    assert payload["effect"] == 0
    assert "情報の取得に失敗" not in payload["report"]
    messages = [
        json.loads(line)["message"]
        for line in (tmp_path / "openclaw.messages.jsonl").read_text().splitlines()
    ]
    transient = [message for message in messages if "判断を完了できませんでした" in message]
    assert len(transient) == 1 and "91000061" in transient[0]


def test_corrupt_active_objective_state_fails_without_parent(tmp_path: Path):
    commands = _fake_commands(tmp_path)
    objective_state = tmp_path / "objective.json"
    objective_state.write_text(json.dumps({"version": 1, "status": "active", "cursor": {}}), encoding="utf-8")
    result = _invoke(tmp_path, commands, tmp_path / "corrupt.json", pass_id="corrupt-pass",
                     search_objective_state=objective_state)
    assert result.returncode != 0
    assert not (tmp_path / "state" / "corrupt-pass" / "parent.calls").exists()
    payload = json.loads((tmp_path / "corrupt.json").read_text())
    assert payload["status"] == "failed"
    assert payload["failed"] == 1
    assert "応募情報源を読み取れませんでした" in payload["report"]
    assert "失敗" in payload["report"]


def test_active_phase_results_merge_each_request_id_once_with_truthful_priority(tmp_path: Path):
    commands = _fake_commands(tmp_path)
    objective_state = tmp_path / "objective.json"
    objective_state.write_text(json.dumps({
        "version": 1, "status": "active", "last_pass_id": "old", "updated_at": 1,
        "cursor": {"source_id": "single:new", "previous_url": "https://coconala.com/requests?sort=new&recruiting=true&page=80",
                   "next_url": "https://coconala.com/requests?sort=new&recruiting=true&page=81", "reason": "next_page"},
    }), encoding="utf-8")
    result = _invoke(tmp_path, commands, tmp_path / "overlap.json", pass_id="overlap-pass",
                     search_objective_state=objective_state, fake_parent_mode="overlap")
    assert result.returncode == 0, result.stderr
    payload = json.loads((tmp_path / "overlap.json").read_text())
    results = payload["report_results"]
    assert [row["request_id"] for row in results].count("shared") == 1
    assert next(row for row in results if row["request_id"] == "shared")["status"] == "confirmed"
    assert payload["observed"] == 2
    assert payload["actionable"] == payload["effect"] == payload["readback"] == 1
    assert payload["failed"] == payload["pending"] == 0
    assert "応募＋公式確認1件" in payload["report"]
    assert "依頼ID shared" not in payload["report"]


def test_phase_merge_does_not_hide_snapshot_when_one_observation_sidecar_is_missing(
    tmp_path: Path,
):
    phases = []
    for name, request_id in (("refresh", "refresh-id"), ("coverage", "coverage-id")):
        evidence = tmp_path / name
        evidence.mkdir()
        (evidence / "application-snapshot.json").write_text(json.dumps({
            "request_details": [{"request_id": request_id, "title": name}],
        }))
        (evidence / "application-decisions.json").write_text(json.dumps({"decisions": []}))
        (evidence / "parent-commit.json").write_text(json.dumps({"results": []}))
        phases.append((name, evidence, 0))
    (tmp_path / "refresh" / "application-observations.json").write_text(json.dumps({
        "version": 1,
        "raw_request_ids": ["refresh-id"],
        "already_applied_ids": [],
        "quarantined_ids": [],
        "filtered_results": [],
        "lifecycle_results": [],
    }))

    values = direct._merged_phase_summary(phases, tmp_path / "merged")

    assert values["observed"] == 2
    assert values["failed"] == 1


def test_phase_merge_fails_truthfully_instead_of_crashing_on_malformed_observations(
    tmp_path: Path,
):
    evidence = tmp_path / "refresh"
    evidence.mkdir()
    (evidence / "application-snapshot.json").write_text(json.dumps({
        "request_details": [{"request_id": "snapshot-id", "title": "確認案件"}],
    }))
    (evidence / "application-decisions.json").write_text(json.dumps({"decisions": []}))
    (evidence / "parent-commit.json").write_text(json.dumps({"results": []}))
    (evidence / "application-observations.json").write_text(json.dumps({
        "version": 1,
        "raw_request_ids": None,
        "already_applied_ids": [],
        "quarantined_ids": [],
        "filtered_results": None,
        "lifecycle_results": [],
    }))

    values = direct._merged_phase_summary([("refresh", evidence, 0)], tmp_path / "merged")

    assert values["observed"] == 1
    assert values["failed"] == 1


def test_phase_merge_rejects_valid_shape_that_omits_a_snapshot_candidate(tmp_path: Path):
    evidence = tmp_path / "refresh"
    evidence.mkdir()
    (evidence / "application-snapshot.json").write_text(json.dumps({
        "request_details": [{"request_id": "snapshot-id", "title": "確認案件"}],
    }))
    (evidence / "application-decisions.json").write_text(json.dumps({"decisions": []}))
    (evidence / "parent-commit.json").write_text(json.dumps({"results": []}))
    (evidence / "application-observations.json").write_text(json.dumps({
        "version": 1,
        "raw_request_ids": [],
        "already_applied_ids": [],
        "quarantined_ids": [],
        "filtered_results": [],
        "lifecycle_results": [],
    }))

    values = direct._merged_phase_summary([("refresh", evidence, 0)], tmp_path / "merged")

    assert values["observed"] == 1
    assert values["failed"] == 1


def test_phase_merge_retains_lifecycle_rows_by_exact_request_id(tmp_path: Path):
    _phase_evidence(tmp_path / "refresh", "5209929", [_lifecycle_row("5209929")])
    _phase_evidence(tmp_path / "coverage", "5204983", [_lifecycle_row("5204983", form_state="absent")])

    values = direct._merged_phase_summary(
        [("refresh", tmp_path / "refresh", 0), ("coverage", tmp_path / "coverage", 0)], tmp_path / "merged",
    )

    merged = json.loads((tmp_path / "merged" / "application-observations.json").read_text())
    assert {row["request_id"] for row in merged["lifecycle_results"]} == {"5209929", "5204983"}
    assert values["failed"] == 0


def test_officially_unavailable_lifecycle_is_counted_and_reported_compactly(tmp_path: Path):
    evidence = tmp_path / "evidence"
    _phase_evidence(evidence, "5204983", [_lifecycle_row("5204983", form_state="absent")])

    values = direct.summarize(evidence, 0, require_observations=True)
    report = direct._report("closed-pass", values)

    assert values["officially_unavailable_count"] == values["closed_filtered"] == 1
    assert values["officially_unavailable_ids"] == ["5204983"]
    assert not values["report_results"]
    assert "officially_unsubmittable: 公式送信不能: 1件（ID: 5204983）" in report
    assert report.count("officially_unsubmittable:") == report.count("5204983") == 1
    assert "見送り:" not in report
    notifications = direct._fresh_decision_notifications(evidence, values)
    assert len(notifications) == 1
    assert notifications[0][0] == (
        "gig:telegram:apply-decision:v2:5204983:officially_unsubmittable"
    )
    assert "公式に応募できない案件をスキップ" in notifications[0][1]

    changed = json.loads((evidence / "application-observations.json").read_text())
    changed["lifecycle_results"][0]["lifecycle_sha256"] = "f" * 64
    (evidence / "application-observations.json").write_text(json.dumps(changed))
    assert direct._fresh_decision_notifications(evidence, values)[0][0] == notifications[0][0]

    outbox = direct.TelegramOutbox(tmp_path / "telegram.sqlite3")
    outbox.enqueue(
        event_key="gig:telegram:apply-decision:v1:5204983:old-content-hash:officially_unsubmittable",
        kind="apply-decision", message=notifications[0][1], created_at=1,
        suppress_identical_body=False,
    )
    assert direct._decision_notification_exists(outbox, notifications[0][0]) is True


def test_lifecycle_unavailable_report_bounds_ids_and_excludes_unknown_duplicates(tmp_path: Path):
    ids = [str(5205012 - index) for index in range(12)]
    unavailable = [_lifecycle_row(request_id, form_state="absent") for request_id in ids]
    unknown = _lifecycle_row("5205999", form_state="unknown")
    unknown.update(status="unknown", reason_codes=["form_state:unknown"])
    _phase_evidence(tmp_path / "refresh", ids[0], unavailable)
    _phase_evidence(tmp_path / "coverage", ids[-1], [unavailable[-1], unknown])
    for root, raw_ids in ((tmp_path / "refresh", ids), (tmp_path / "coverage", [ids[-1], "5205999"])):
        path = root / "application-observations.json"
        payload = json.loads(path.read_text())
        path.write_text(json.dumps({**payload, "raw_request_ids": raw_ids}))

    values = direct._merged_phase_summary(
        [("refresh", tmp_path / "refresh", 0), ("coverage", tmp_path / "coverage", 0)], tmp_path / "merged",
    )
    report = direct._report("closed-many", values)
    sample = sorted(ids, key=int)[:8]

    assert values["officially_unavailable_count"] == values["closed_filtered"] == 12
    assert values["officially_unavailable_ids"] == sample
    assert f"公式送信不能: 12件（ID: {', '.join(sample)}、他4件）" in report
    assert report.count("公式送信不能:") == 1 and "他4件" in report
    assert all(report.count(request_id) == 1 for request_id in sample)
    assert "5205999" not in report and "見送り:" not in report


@pytest.mark.parametrize("kind", ["malformed", "conflict"])
def test_phase_merge_degrades_invalid_or_conflicting_lifecycle_evidence(tmp_path: Path, kind: str):
    refresh = _lifecycle_row("5209929")
    coverage = _lifecycle_row("5209929", form_state="absent")
    if kind == "malformed":
        refresh = _lifecycle_row("5209929", deadline_value="2026-02-30")
        coverage = []
    _phase_evidence(tmp_path / "refresh", "5209929", [refresh])
    _phase_evidence(tmp_path / "coverage", "5209929", coverage if isinstance(coverage, list) else [coverage])

    values = direct._merged_phase_summary(
        [("refresh", tmp_path / "refresh", 0), ("coverage", tmp_path / "coverage", 0)], tmp_path / "merged",
    )

    merged = json.loads((tmp_path / "merged" / "application-observations.json").read_text())
    assert values["failed"] == 1
    if kind == "conflict":
        assert merged["lifecycle_results"] == [coverage]


def test_exhausted_deep_coverage_completes_and_resets_to_refresh(tmp_path: Path):
    commands = _fake_commands(tmp_path)
    objective_state = tmp_path / "objective.json"
    objective_state.write_text(json.dumps({
        "version": 1, "status": "active", "last_pass_id": "old", "updated_at": 1,
        "cursor": {"source_id": "single:new", "previous_url": "https://coconala.com/requests?sort=new&recruiting=true&page=80",
                   "next_url": "https://coconala.com/requests?sort=new&recruiting=true&page=81", "reason": "next_page"},
    }), encoding="utf-8")

    result = _invoke(
        tmp_path, commands, tmp_path / "exhausted.json", pass_id="exhausted-pass",
        search_objective_state=objective_state, fake_parent_mode="exhausted",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads((tmp_path / "exhausted.json").read_text())
    assert payload["status"] == "ok"
    assert payload["failed"] == payload["pending"] == 0
    assert "全source探索完了" in payload["report"]
    run_dir = tmp_path / "state" / "exhausted-pass"
    assert len((run_dir / "parent.calls").read_text().splitlines()) == 1
    assert not (run_dir / "parent.invocation-coverage.json").exists()
    state = json.loads(objective_state.read_text())
    assert state["cursor"]["next_url"] == (
        "https://coconala.com/requests?sort=new&recruiting=true&page=2"
    )


def test_malformed_coverage_source_is_not_reported_as_exhausted(tmp_path: Path):
    commands = _fake_commands(tmp_path)
    objective_state = tmp_path / "objective.json"
    original = {
        "version": 1, "status": "active", "last_pass_id": "old", "updated_at": 1,
        "cursor": {"source_id": "single:new", "previous_url": "https://coconala.com/requests?sort=new&recruiting=true&page=80",
                   "next_url": "https://coconala.com/requests?sort=new&recruiting=true&page=81", "reason": "next_page"},
    }
    objective_state.write_text(json.dumps(original), encoding="utf-8")

    result = _invoke(
        tmp_path, commands, tmp_path / "malformed-source.json", pass_id="malformed-source-pass",
        search_objective_state=objective_state, fake_parent_mode="malformed-source",
    )

    assert result.returncode != 0
    assert json.loads(objective_state.read_text()) == original
    payload = json.loads((tmp_path / "malformed-source.json").read_text())
    assert payload["status"] == "failed"
    assert "全source探索完了" not in payload["report"]
    assert "次の探索位置を決められませんでした" in payload["report"]


def test_direct_apply_batches_parent_eligible_work_and_reports_readback(tmp_path: Path):
    commands = _fake_commands(tmp_path)
    result_path = tmp_path / "result.json"
    result = _invoke(tmp_path, commands, result_path)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload["observed"] == 3
    assert payload["actionable"] == 2
    assert payload["effect"] == 1
    assert payload["readback"] == 1
    assert payload["failed"] == 1
    assert payload["pending"] == 1
    assert payload["oldest"] == "2026-08-11T01:00:00Z"
    assert payload["transport"] == "sent"
    assert payload["message_id"] == "tg-apply-1"
    assert payload["report"].startswith("[ココナラ][応募]")
    assert "情報源状態: 深掘りcursorは未接続" in payload["report"]
    assert result.stdout.splitlines()[0].startswith("[ココナラ][応募]")
    invocation = tmp_path / "state" / "apply-direct-test" / "parent.invocation.json"
    invocation_payload = json.loads(invocation.read_text(encoding="utf-8"))
    argv = invocation_payload["argv"] if isinstance(invocation_payload, dict) else invocation_payload
    assert "--intent-root" in argv and "--ledger" in argv
    assert "--planner-runner" in argv and "--context" in argv
    lease_index = argv.index("--lease-task")
    assert argv[lease_index + 1] == "gig-apply-direct-apply-direct-test"
    assert argv.count("--lease-task") == 1
    assert not any("gig_pass.sh" in value for value in argv)
    assert not any("hermes" in value.lower() or "restart" in value.lower() for value in argv)
    assert "--max-applications" not in argv
    assert "--all-eligible" not in argv


def test_direct_all_eligible_passes_explicit_parent_flag(tmp_path: Path):
    commands = _fake_commands(tmp_path)
    result = _invoke(
        tmp_path,
        commands,
        tmp_path / "all-eligible.json",
        all_eligible=True,
    )
    assert result.returncode == 0, result.stderr
    invocation = tmp_path / "state" / "apply-direct-test" / "parent.invocation.json"
    payload = json.loads(invocation.read_text(encoding="utf-8"))
    argv = payload["argv"] if isinstance(payload, dict) else payload
    assert "--all-eligible" in argv


def test_restart_reuses_b2_context_without_repeating_passprep(tmp_path: Path):
    commands = _fake_commands(tmp_path)
    first = _invoke(tmp_path, commands, tmp_path / "first.json")
    second = _invoke(tmp_path, commands, tmp_path / "second.json")
    assert first.returncode == second.returncode == 0
    assert len((tmp_path / "passprep.calls").read_text().splitlines()) == 1
    assert (tmp_path / "b2_gate.calls").read_text().splitlines().count("build") == 1
    calls = tmp_path / "state" / "apply-direct-test" / "parent.calls"
    assert len(calls.read_text().splitlines()) == 2
    (tmp_path / "state" / "apply-direct-test" / "b2-context.json").unlink()
    assert _invoke(tmp_path, commands, tmp_path / "third.json").returncode == 0
    assert len((tmp_path / "passprep.calls").read_text().splitlines()) == 1
    assert (tmp_path / "b2_gate.calls").read_text().splitlines().count("build") == 2


def test_default_pass_id_is_unique_but_explicit_pass_id_is_deduped(tmp_path: Path):
    commands = _fake_commands(tmp_path)
    first_default = _invoke(tmp_path, commands, tmp_path / "first-default.json", pass_id=None)
    second_default = _invoke(tmp_path, commands, tmp_path / "second-default.json", pass_id=None)
    assert first_default.returncode == second_default.returncode == 0

    first_payload = json.loads((tmp_path / "first-default.json").read_text(encoding="utf-8"))
    second_payload = json.loads((tmp_path / "second-default.json").read_text(encoding="utf-8"))
    first_pass = first_payload["pass_id"]
    second_pass = second_payload["pass_id"]
    assert first_pass != second_pass
    assert (tmp_path / "state" / first_pass).is_dir()
    assert (tmp_path / "state" / second_pass).is_dir()

    with sqlite3.connect(tmp_path / "telegram-outbox.sqlite3") as connection:
        default_events = [
            row[0] for row in connection.execute(
                "SELECT event_key FROM telegram_reports WHERE kind=? ORDER BY report_id",
                ("apply-direct",),
            )
    ]
    assert default_events == [
        direct._telegram_event_key(first_pass, first_payload["report"]),
        direct._telegram_event_key(second_pass, second_payload["report"]),
    ]

    first_explicit = _invoke(tmp_path, commands, tmp_path / "first-explicit.json", pass_id="stable-pass")
    second_explicit = _invoke(tmp_path, commands, tmp_path / "second-explicit.json", pass_id="stable-pass")
    assert first_explicit.returncode == second_explicit.returncode == 0
    first_explicit_payload = json.loads((tmp_path / "first-explicit.json").read_text(encoding="utf-8"))
    second_explicit_payload = json.loads((tmp_path / "second-explicit.json").read_text(encoding="utf-8"))
    assert first_explicit_payload["pass_id"] == "stable-pass"
    assert second_explicit_payload["pass_id"] == "stable-pass"
    assert (tmp_path / "state" / "stable-pass").is_dir()
    with sqlite3.connect(tmp_path / "telegram-outbox.sqlite3") as connection:
        explicit_count = connection.execute(
            "SELECT COUNT(*) FROM telegram_reports WHERE event_key=?",
            (direct._telegram_event_key("stable-pass", first_explicit_payload["report"]),),
        ).fetchone()[0]
    assert explicit_count == 1


def test_parent_failure_cannot_be_reported_as_business_effect(tmp_path: Path):
    commands = _fake_commands(tmp_path)
    failing_parent = _write_python(tmp_path / "failing_parent.py", """
import sys
print('parent failed', file=sys.stderr)
raise SystemExit(42)
""")
    commands['parent'] = failing_parent
    result_path = tmp_path / "failed.json"
    result = _invoke(tmp_path, commands, result_path)
    assert result.returncode != 0
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload["effect"] == 0
    assert payload["readback"] == 0
    assert payload["failed"] >= 1
    assert payload["transport"] == "sent"
    assert payload["message_id"] == "tg-apply-1"
    assert payload["report"].startswith("[ココナラ][応募]")


def test_pre_submit_abort_is_failed_not_pending(tmp_path: Path):
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "application-snapshot.json").write_text(
        json.dumps({"request_details": [{"request_id": "1"}]}), encoding="utf-8"
    )
    (evidence / "application-decisions.json").write_text(
        json.dumps({"decisions": [{"request_id": "1", "business_class": "submit_required"}]}),
        encoding="utf-8",
    )
    (evidence / "parent-commit.json").write_text(json.dumps({"results": [
        {"request_id": "1", "status": "pre_submit_aborted:open_form:ParentContractError"},
    ]}), encoding="utf-8")
    values = direct.summarize(evidence, 0)
    assert values["failed"] == 1
    assert values["pending"] == 0


def test_prepared_unconfirmed_is_failed_not_pending(tmp_path: Path):
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "application-snapshot.json").write_text(
        json.dumps({"request_details": [{"request_id": "5207298"}]}), encoding="utf-8"
    )
    (evidence / "application-decisions.json").write_text(
        json.dumps({"decisions": [{"request_id": "5207298", "business_class": "submit_required"}]}),
        encoding="utf-8",
    )
    (evidence / "parent-commit.json").write_text(json.dumps({"results": [
        {"request_id": "5207298", "status": "prepared_unconfirmed"},
    ]}), encoding="utf-8")
    values = direct.summarize(evidence, 0)
    assert values["failed"] == 1
    assert values["pending"] == 0


def test_duplicate_fenced_prepared_sibling_is_excluded_from_counts(tmp_path: Path):
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "application-snapshot.json").write_text(json.dumps({
        "request_details": [
            {"request_id": "5210212", "title": "重複案件"},
            {"request_id": "5209850", "title": "確認案件"},
        ],
    }), encoding="utf-8")
    (evidence / "application-decisions.json").write_text(json.dumps({
        "decisions": [
            {"request_id": "5210212", "business_class": "submit_required"},
            {"request_id": "5209850", "business_class": "submit_required"},
        ],
    }), encoding="utf-8")
    (evidence / "parent-commit.json").write_text(json.dumps({"results": [
        {"request_id": "5210212", "status": "prepared_unconfirmed", "business_class": "duplicate_fenced"},
        {"request_id": "5209850", "status": "confirmed"},
    ]}), encoding="utf-8")

    values = direct.summarize(evidence, 0)

    assert values["actionable"] == 1
    assert values["effect"] == values["readback"] == 1
    assert values["failed"] == values["pending"] == 0


def test_planner_missing_request_is_transient_failure_without_hiding_sibling(tmp_path: Path):
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "application-snapshot.json").write_text(json.dumps({
        "request_details": [
            {"request_id": "91000001", "title": "継続案件"},
            {"request_id": "91000002", "title": "planner欠落案件"},
        ],
    }), encoding="utf-8")
    (evidence / "application-decisions.json").write_text(json.dumps({
        "decisions": [{"request_id": "91000001", "business_class": "submit_required", "price_jpy": 5000}],
    }), encoding="utf-8")
    (evidence / "parent-commit.json").write_text(json.dumps({
        "results": [{"request_id": "91000001", "status": "confirmed"}],
        "planner_missing_request_ids": ["91000002"],
    }), encoding="utf-8")

    values = direct.summarize(evidence, 0)
    missing = next(row for row in values["report_results"] if row["request_id"] == "91000002")
    report = direct._report("planner-missing", values)

    assert values["actionable"] == values["effect"] == values["readback"] == 1
    assert values["failed"] == 1
    assert missing == {
        "request_id": "91000002",
        "title": "planner欠落案件",
        "price_jpy": None,
        "status": "planner_missing_request_id",
        "business_class": None,
        "processing_disposition": "failed_transient",
        "effect": 0,
        "reason": "planner_missing_request_id",
        "outcome": "failed_transient",
    }
    assert "再判定待ち1件" in report and "91000002" not in report


def test_phase_merge_preserves_planner_missing_request_as_transient_failure(tmp_path: Path):
    evidence = tmp_path / "phase"
    _phase_evidence(evidence, "91000002", [])
    (evidence / "parent-commit.json").write_text(json.dumps({
        "results": [], "planner_missing_request_ids": ["91000002"],
    }), encoding="utf-8")

    values = direct._merged_phase_summary(
        [("phase", evidence, 0)], tmp_path / "merged",
    )
    persisted = json.loads((tmp_path / "merged" / "parent-commit.json").read_text())

    assert persisted["planner_missing_request_ids"] == ["91000002"]
    assert values["failed"] == 1
    assert values["effect"] == 0
    assert values["report_results"][0]["business_class"] is None
    assert values["report_results"][0]["processing_disposition"] == "failed_transient"


def test_dedupe_already_applied_is_not_failed_or_pending(tmp_path: Path):
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "application-snapshot.json").write_text(json.dumps({
        "request_details": [{"request_id": "91000005", "title": "既存案件"}],
    }), encoding="utf-8")
    (evidence / "application-decisions.json").write_text(json.dumps({
        "decisions": [{"request_id": "91000005", "business_class": "submit_required", "price_jpy": 7000}],
    }), encoding="utf-8")
    (evidence / "parent-commit.json").write_text(json.dumps({"results": [
        {"request_id": "91000005", "status": "dedupe_already_applied", "business_class": "duplicate_fenced"},
    ]}), encoding="utf-8")

    values = direct.summarize(evidence, 0)
    report = direct._report("already-applied-pass", values)
    assert values["effect"] == 0
    assert values["readback"] == 0
    assert values["failed"] == 0
    assert values["pending"] == 0
    assert "重複防止1件" in report
    assert "91000005" not in report and "既存案件" not in report


def test_report_describes_non_confirmed_parent_results_in_natural_language(tmp_path: Path):
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "application-snapshot.json").write_text(json.dumps({
        "request_details": [
            {"request_id": "91000001", "title": "AI資料作成"},
            {"request_id": "91000002", "title": "SNS運用支援"},
            {"request_id": "91000003", "title": "動画編集"},
            {"request_id": "91000004", "title": "保留案件"},
        ],
    }), encoding="utf-8")
    (evidence / "application-decisions.json").write_text(json.dumps({
        "decisions": [
            {"request_id": "91000002", "business_class": "hard_prohibited", "reason_codes": ["mandatory_human_presence", "本人の顔出し出演が必須です。"]},
            {"request_id": "91000003", "business_class": "submit_required", "price_jpy": 5000},
            {"request_id": "91000004", "business_class": "submit_required", "price_jpy": 6000},
        ],
    }), encoding="utf-8")
    (evidence / "parent-commit.json").write_text(json.dumps({"results": [
        {"request_id": "91000001", "status": "confirmed", "application": {
            "request_id": "91000001", "title": "AI資料作成", "price_jpy": 12345,
        }},
        {"request_id": "91000002", "status": "hard_prohibited", "business_class": "hard_prohibited"},
        {"request_id": "91000003", "status": "submission_failed:form_rejected", "error": "入力内容を拒否"},
        {"request_id": "91000004", "status": "prepared_unconfirmed", "business_class": "duplicate_fenced"},
    ]}), encoding="utf-8")

    report = direct._report("outcome-pass", direct.summarize(evidence, 0))

    assert "応募＋公式確認1件" in report
    assert "禁止条件1件" in report and "送信失敗1件" in report
    assert "重複防止1件" in report
    assert all(request_id not in report for request_id in ("91000001", "91000002", "91000003", "91000004"))
    (evidence / "application-snapshot.json").write_text(
        json.dumps({"request_details": []}), encoding="utf-8"
    )
    (evidence / "application-decisions.json").write_text(
        json.dumps({"decisions": []}), encoding="utf-8"
    )
    (evidence / "parent-commit.json").write_text(
        json.dumps({"results": []}), encoding="utf-8"
    )
    zero_report = direct._report("zero-source-pass", direct.summarize(evidence, 0))
    assert "今回の実行では募集を観測できませんでした。" in zero_report
    assert "応募＋公式確認0件" in zero_report
    bounded = direct._report("boundary", {"observed": 20, "actionable": 20, "effect": 0,
        "readback": 0, "failed": 20, "pending": 0, "oldest": None, "report_results": [
            {"request_id": str(index), "title": "T" * 500, "price_jpy": None,
             "status": "submission_failed:" + "S" * 500, "reason": "R" * 500, "outcome": "failed"}
            for index in range(20)]})
    assert len(bounded) <= 3900 and bounded.count("依頼ID ") == 0
    assert "送信失敗20件" in bounded


def test_report_parts_preserve_all_results_and_bound_sensitive_fields():
    long_request_id = "I" * 500
    results = [{
        "request_id": long_request_id if index == 0 else f"request-{index}",
        "title": "T" * 500,
        "price_jpy": True if index == 0 else None,
        "status": "submission_failed:" + "S" * 500,
        "reason": "R" * 500,
        "outcome": "failed",
    } for index in range(40)]
    messages = direct._reports("P" * 1000, {
        "observed": 40, "actionable": 0, "effect": 0, "readback": 0,
        "failed": 40, "pending": 0, "oldest": None, "report_results": results,
    })
    combined = "\n".join(messages)

    assert len(messages) == 1
    assert all(message.startswith("[ココナラ][応募]\npart ") for message in messages)
    assert all(len(message) <= 3900 for message in messages)
    assert all(f"request-{index}" not in combined for index in range(1, 40))
    assert combined.count("依頼ID ") == 0
    assert "送信失敗40件" in combined
    assert "1円" not in combined
    assert long_request_id not in combined and ("P" * 1000) not in combined


def test_report_parts_are_deduped_for_same_pass(tmp_path: Path):
    commands = _fake_commands(tmp_path)
    commands["parent"] = _write_python(tmp_path / "many_parent.py", """
import json
import sys
from pathlib import Path
args = sys.argv
evidence = Path(args[args.index('--evidence-dir') + 1])
evidence.mkdir(parents=True, exist_ok=True)
rows = [{'request_id': f'request-{index}', 'status': 'submission_failed:form'} for index in range(40)]
(evidence / 'application-snapshot.json').write_text(json.dumps({
    'request_details': [{'request_id': f'request-{index}', 'title': 'T' * 500} for index in range(40)]
}))
(evidence / 'application-decisions.json').write_text(json.dumps({'decisions': []}))
(evidence / 'parent-commit.json').write_text(json.dumps({'results': rows}))
Path(args[args.index('--output') + 1]).write_text(json.dumps({'status': 'ok'}))
print(json.dumps({'status': 'ok'}))
""")
    first = _invoke(tmp_path, commands, tmp_path / "parts-first.json", pass_id="parts-pass")
    second = _invoke(tmp_path, commands, tmp_path / "parts-second.json", pass_id="parts-pass")
    assert first.returncode == second.returncode == 0
    first_payload = json.loads((tmp_path / "parts-first.json").read_text(encoding="utf-8"))
    second_payload = json.loads((tmp_path / "parts-second.json").read_text(encoding="utf-8"))
    messages = (tmp_path / "openclaw.messages.jsonl").read_text(encoding="utf-8").splitlines()
    assert first_payload["transport"] == second_payload["transport"] == "sent"
    assert len(first_payload["reports"]) == 1
    assert len(first_payload["message_ids"]) == len(first_payload["reports"])
    assert len(messages) == 41
    bodies = [json.loads(line)["message"] for line in messages]
    assert sum("[ココナラ][応募判断]" in body for body in bodies) == 40
    assert sum("[ココナラ][応募]" in body for body in bodies) == 1
    assert second_payload["message_ids"] == first_payload["message_ids"]


def test_report_price_requires_positive_non_bool_integer():
    values = {
        "observed": 1, "actionable": 1, "effect": 0, "readback": 0,
        "failed": 1, "pending": 0, "oldest": None,
    }
    for price in (0, -1, True, "1000", None):
        report = direct._report("price-pass", {
            **values,
            "report_results": [{
                "request_id": "price", "title": "価格", "price_jpy": price,
                "status": "submission_failed:price", "reason": "確認不能", "outcome": "failed",
            }],
        })
        assert "送信失敗1件" in report and "提案額" not in report
    report = direct._report("price-pass", {
        **values,
        "report_results": [{
            "request_id": "price", "title": "価格", "price_jpy": 1000,
            "status": "submission_failed:price", "reason": "確認不能", "outcome": "failed",
        }],
    })
    assert "送信失敗1件" in report and "提案額" not in report


def test_long_pass_ids_get_distinct_event_keys(tmp_path: Path, monkeypatch):
    args = SimpleNamespace(
        telegram_database=tmp_path / "telegram.sqlite3",
        telegram_target="42",
        openclaw=Path("/bin/true"),
        telegram_receipt_dir=tmp_path / "receipts",
    )
    monkeypatch.setattr(direct, "dispatch_one", lambda *args, **kwargs: {"status": "queue_empty"})
    prefix = "long-pass-" + "P" * 200
    direct._send_telegram(prefix + "-one", "first", args)
    direct._send_telegram(prefix + "-two", "second", args)
    with sqlite3.connect(args.telegram_database) as connection:
        keys = [row[0] for row in connection.execute(
            "SELECT event_key FROM telegram_reports ORDER BY report_id"
        )]
    assert len(keys) == 2 and keys[0] != keys[1]


def test_partial_multipart_delivery_is_truthful_and_deduped(tmp_path: Path):
    commands = _fake_commands(tmp_path)
    commands["parent"] = _write_python(tmp_path / "partial_parent.py", """
import json
import sys
from pathlib import Path
args = sys.argv
evidence = Path(args[args.index('--evidence-dir') + 1])
evidence.mkdir(parents=True, exist_ok=True)
rows = [{'request_id': f'request-{index}', 'status': 'submission_failed:form'} for index in range(40)]
(evidence / 'application-snapshot.json').write_text(json.dumps({
    'request_details': [{'request_id': f'request-{index}', 'title': 'T' * 500} for index in range(40)]
}))
(evidence / 'application-decisions.json').write_text(json.dumps({'decisions': []}))
(evidence / 'parent-commit.json').write_text(json.dumps({'results': rows}))
Path(args[args.index('--output') + 1]).write_text(json.dumps({'status': 'ok'}))
print(json.dumps({'status': 'ok'}))
""")
    commands["openclaw"] = _write_python(tmp_path / "partial_openclaw.py", """
import json
import sys
from pathlib import Path
args = sys.argv
message = args[args.index('--message') + 1]
calls = Path(__file__).with_suffix('.calls')
if not calls.exists():
    calls.write_text('first-failed')
    raise SystemExit(7)
marker = Path(__file__).with_suffix('.messages.jsonl')
with marker.open('a', encoding='utf-8') as handle:
    handle.write(json.dumps({'message': message}, ensure_ascii=False) + '\\n')
print(json.dumps({'messageId': 'tg-part'}))
""")
    first = _invoke(tmp_path, commands, tmp_path / "partial-first.json", pass_id="partial-pass")
    second = _invoke(tmp_path, commands, tmp_path / "partial-second.json", pass_id="partial-pass")
    assert first.returncode == second.returncode == 0
    first_payload = json.loads((tmp_path / "partial-first.json").read_text(encoding="utf-8"))
    second_payload = json.loads((tmp_path / "partial-second.json").read_text(encoding="utf-8"))
    messages = (tmp_path / "partial_openclaw.messages.jsonl").read_text(encoding="utf-8").splitlines()
    assert first_payload["transport"] == second_payload["transport"] == "sent"
    assert len(first_payload["reports"]) == 1
    assert len(messages) == 40
    assert second_payload["message_ids"] == first_payload["message_ids"]
    with sqlite3.connect(tmp_path / "telegram-outbox.sqlite3") as connection:
        states = dict(connection.execute(
            "SELECT state,COUNT(*) FROM telegram_reports GROUP BY state"
        ))
    assert states.get("pending", 0) == 0
    assert states["delivery_unknown"] == 1


def test_report_snapshot_identity_survives_single_multipart_transitions(tmp_path: Path):
    commands = _fake_commands(tmp_path)
    args = SimpleNamespace(
        telegram_database=tmp_path / "transition.sqlite3",
        telegram_target="42",
        openclaw=commands["openclaw"],
        telegram_receipt_dir=tmp_path / "transition-receipts",
    )
    pass_id = "transition-pass-" + "P" * 1000

    def values(count: int) -> dict[str, object]:
        return {
            "observed": count, "actionable": 0, "effect": 0, "readback": 0,
            "failed": count, "pending": 0, "oldest": None, "report_results": [
                {"request_id": str(index), "title": "T" * 500, "price_jpy": None,
                 "status": "submission_failed:" + "S" * 500, "reason": "R" * 500,
                 "outcome": "failed"}
                for index in range(count)
            ],
        }

    single_reports = direct._reports(pass_id, values(1))
    multipart_reports = direct._reports(pass_id, values(40))
    assert len(single_reports) == 1
    assert len(multipart_reports) == 1
    assert single_reports[0].splitlines()[1] == "part 1"
    assert multipart_reports[0].splitlines()[1] == "part 1"
    # A changed compact summary is a distinct report snapshot.
    assert direct._send_telegram(pass_id, single_reports[0], args)["status"] == "sent"
    for index, report in enumerate(multipart_reports, 1):
        assert direct._send_telegram(
            pass_id, report, args, part_index=index
        )["status"] == "sent"
    # Multipart -> single: returning to the original snapshot is deduped.
    assert direct._send_telegram(pass_id, single_reports[0], args)["status"] == "sent"
    for index, report in enumerate(multipart_reports, 1):
        assert direct._send_telegram(
            pass_id, report, args, part_index=index
        )["status"] == "sent"

    messages = (tmp_path / "openclaw.messages.jsonl").read_text(encoding="utf-8").splitlines()
    bodies = [json.loads(message)["message"] for message in messages]
    assert len(messages) == 2
    assert bodies.count(single_reports[0]) == 1
    assert all(bodies.count(report) == 1 for report in multipart_reports)
    with sqlite3.connect(args.telegram_database) as connection:
        keys = [row[0] for row in connection.execute(
            "SELECT event_key FROM telegram_reports ORDER BY report_id"
        )]
    assert len(keys) == 2
    assert len(set(keys)) == len(keys)
    assert all(len(key) <= 300 for key in keys)
    assert all(":part-1" not in key for key in keys)
    assert not any(":part-2" in key for key in keys)


def test_direct_invocation_uses_parent_lease_without_shared_cdp_lock(tmp_path: Path):
    commands = _fake_commands(tmp_path)
    result_path = tmp_path / "unlocked.json"
    result = _invoke(tmp_path, commands, result_path, lock_held=False)
    assert result.returncode == 0, result.stderr
    assert json.loads(result_path.read_text(encoding="utf-8"))["status"] == "ok"


def test_direct_sends_multiline_summary_and_dedupes_same_pass(tmp_path: Path):
    commands = _fake_commands(tmp_path)
    first = _invoke(tmp_path, commands, tmp_path / "first.json")
    second = _invoke(tmp_path, commands, tmp_path / "second.json")
    assert first.returncode == second.returncode == 0
    payload = json.loads((tmp_path / "second.json").read_text(encoding="utf-8"))
    assert payload["transport"] == "sent"
    assert payload["message_id"] == "tg-apply-1"
    messages = [
        json.loads(line)
        for line in (tmp_path / "openclaw.messages.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(messages) == 1
    receipts = list((tmp_path / "receipts").glob("*.json"))
    assert len(receipts) == 1
    assert json.loads(receipts[0].read_text(encoding="utf-8"))["message_id"] == "tg-apply-1"
    report = messages[0]["message"]
    assert report.startswith("[ココナラ][応募]\n")
    for field in ("observed", "actionable", "effect", "readback", "failed", "pending", "oldest"):
        assert f"{field}" in report


def test_direct_sends_current_event_without_draining_backlog(tmp_path: Path):
    commands = _fake_commands(tmp_path)
    database = tmp_path / "telegram-outbox.sqlite3"
    outbox = TelegramOutbox(database)
    for index in range(33):
        outbox.enqueue(
            event_key=f"old:event:{index}",
            kind="old",
            message=f"old backlog {index}",
            created_at=1 + index,
            suppress_identical_body=False,
        )

    first = _invoke(tmp_path, commands, tmp_path / "current.json", pass_id="current-pass")
    assert first.returncode == 0, first.stderr
    payload = json.loads((tmp_path / "current.json").read_text(encoding="utf-8"))
    assert payload["transport"] == "sent"
    assert payload["message_id"] == "tg-current"
    messages = [
        json.loads(line)
        for line in (tmp_path / "openclaw.messages.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(messages) == 1
    assert messages[0]["message"].startswith("[ココナラ][応募]")

    with sqlite3.connect(database) as connection:
        rows = list(connection.execute(
            "SELECT state,message_id FROM telegram_reports WHERE event_key=?",
            (direct._telegram_event_key("current-pass", payload["report"]),),
        ))
    assert rows == [("sent", "tg-current")]
    assert outbox.counts()["pending"] == 33
    second = _invoke(tmp_path, commands, tmp_path / "current-second.json", pass_id="current-pass")
    assert second.returncode == 0
    messages = (tmp_path / "openclaw.messages.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(messages) == 1


def test_apply_launchd_is_five_minute_locked_and_budgeted():
    plist = plistlib.loads(PLIST.read_bytes())
    assert plist["StartInterval"] == 60
    assert plist["EnvironmentVariables"]["GIG_OPERATOR_BRAKE_FILE"] == "__HOME__/.openclaw/state/gig-work/apply.operator.brake"
    args = plist["ProgramArguments"]
    assert args[0].endswith("python3")
    assert args[1].endswith("application_direct.py")
    assert args[2] == "--all-eligible"
    assert not any("run_with_cdp_lock.sh" in value for value in args)
    assert not any("gig_pass.sh" in value for value in args)
    assert "GIG_HERMES_OWNED_STEPS" not in plist["EnvironmentVariables"]
    env = plist["EnvironmentVariables"]
    assert env["ANICCA_BUDGET_REQUIRED"] == "1"
    assert env["ANICCA_BUDGET_DAILY_SCOPE"] == "gig-apply-direct"
    assert int(env["ANICCA_PASS_TOKEN_BUDGET"]) > 0
    assert int(env["ANICCA_LOOP_DAILY_TOKEN_BUDGET"]) > 0
