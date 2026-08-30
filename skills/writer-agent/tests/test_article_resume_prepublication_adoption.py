from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _write(path: Path, body: str, *, executable: bool = False) -> None:
    path.write_text(body, encoding="utf-8")
    if executable:
        path.chmod(0o755)


def _fake_df_env(tmp_path: Path) -> str:
    path = tmp_path / "df-env.sh"
    _write(
        path,
        "df() { printf '%s\\n' "
        "'Filesystem 1024-blocks Used Available Capacity Mounted on' "
        "'/dev/test 999999999 0 1000000 1% /'; }\n",
    )
    return str(path)


def test_cross_day_adoption_precedes_both_quality_plans_and_never_starts_daily(
    tmp_path: Path,
) -> None:
    fake_root = tmp_path / "writer-agent"
    scripts = fake_root / "scripts"
    runtime = fake_root / "runtime"
    state = tmp_path / "state"
    target_id = "20260829-165022"
    target = state / "runs" / target_id
    newer = state / "runs" / "20260830-151951"
    for run_dir, status in (
        (target, "provider-failed-ambiguous"),
        (newer, "interrupted-safe"),
    ):
        (run_dir / "gates").mkdir(parents=True)
        _write(run_dir / "article-daily-prompt.txt", "immutable prompt")
        _write(
            run_dir / "gates/generation-state.json",
            json.dumps({"run_id": run_dir.name, "status": status}),
        )
    scripts.mkdir(parents=True, exist_ok=True)
    runtime.mkdir()
    shutil.copy(ROOT / "scripts/article-resume-pending.sh", scripts)
    calls = tmp_path / "calls"
    _write(
        state / "articles.jsonl",
        json.dumps({"run_id": target_id, "published": False, "state": "pending"})
        + "\n",
    )
    _write(
        scripts / "article_daily_start_control.py",
        'print(\'{"action":"new","reason":"no-same-jst-day-run"}\')\n',
    )
    _write(scripts / "article_pending.py", 'print(\'{"status":"BLOCKED"}\')\n')
    _write(
        scripts / "article_generation_state.py",
        "import json, os, pathlib, sys\n"
        "run_dir = pathlib.Path(sys.argv[sys.argv.index('--run-dir') + 1])\n"
        "open(os.environ['CALLS'], 'a').write('adopt ' + run_dir.name + '\\n')\n"
        "if os.environ.get('ADOPTION_FAIL') == '1': raise SystemExit(9)\n"
        "state_path = run_dir / 'gates/generation-state.json'\n"
        "state = json.loads(state_path.read_text())\n"
        "state['status'] = 'quality-repair-ready'\n"
        "state_path.write_text(json.dumps(state))\n"
        "print(json.dumps({'action':'adopted','status':'quality-repair-ready'}))\n",
    )
    _write(
        scripts / "quality_feedback_recovery.py",
        "import json, os, sys\n"
        "def plan(*_args): return {'status':'NONE'}\n"
        "if __name__ == '__main__':\n"
        " open(os.environ['CALLS'], 'a').write('quality-feedback\\n')\n"
        " print(json.dumps({'status':'NONE'}))\n",
    )
    repair_prompt = target / "quality-repair-prompt.txt"
    _write(repair_prompt, "repair")
    _write(
        scripts / "quality_repair_control.py",
        "import json, os, sys\n"
        "command = sys.argv[1]\n"
        "if command == 'plan': open(os.environ['CALLS'], 'a').write('quality-plan\\n'); "
        f"print(json.dumps({{'status':'READY','reason':'tracked-reader-terminal-receipt-source-defect','run_id':{target_id!r}}}))\n"
        "elif command == 'begin': open(os.environ['CALLS'], 'a').write('quality-begin\\n'); "
        f"print(json.dumps({{'status':'prepared','run_id':{target_id!r},'prompt_path':{str(repair_prompt)!r}}}))\n"
        "else: "
        f"print(json.dumps({{'status':'ok','prompt_path':{str(repair_prompt)!r}}}))\n",
    )
    _write(
        scripts / "writer_capacity_floor.py",
        "print(536870912)\n",
    )
    _write(runtime / "model-runner-support.py", "raise SystemExit(0)\n")
    _write(
        runtime / "judge-broker.sh",
        "#!/usr/bin/env bash\nexit 0\n",
        executable=True,
    )
    _write(
        runtime / "model-runner.sh",
        "#!/usr/bin/env bash\nprintf 'model-runner\\n' >> \"$CALLS\"\nexit 97\n",
        executable=True,
    )
    daily = fake_root / "article-daily.sh"
    _write(
        daily,
        f"#!/usr/bin/env bash\nprintf daily > {str(tmp_path / 'daily-started')!r}\n",
        executable=True,
    )

    env = {
            **os.environ,
            "ARTICLE_ROOT": str(fake_root),
            "ARTICLE_STATE_DIR": str(state),
            "ARTICLE_OWNER_FENCE_ACTIVE": "1",
            "ARTICLE_LOCAL_DATE": "2026-08-31",
            "ARTICLE_LOCAL_HOUR": "00",
            "ARTICLE_DAILY_SCHEDULE_HOUR": "6",
            "ARTICLE_RESUME_MIN_FREE_BYTES": "536870912",
            "ARTICLE_RESUME_LOG": str(tmp_path / "resume.log"),
            "ARTICLE_MODEL_SUPPORT": str(runtime / "model-runner-support.py"),
            "ARTICLE_MODEL_RUNNER": str(runtime / "model-runner.sh"),
            "BASH_ENV": _fake_df_env(tmp_path),
            "CALLS": str(calls),
        }
    command = ["bash", str(scripts / "article-resume-pending.sh")]
    result = subprocess.run(
        command,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert calls.read_text().splitlines() == [
        f"adopt {target_id}",
        "quality-feedback",
        "quality-plan",
        "quality-begin",
        "model-runner",
    ]
    assert not (tmp_path / "daily-started").exists()
    assert json.loads((target / "gates/generation-state.json").read_text())["status"] == (
        "quality-repair-ready"
    )

    # Invalid adoption evidence is fail-closed before either quality planner.
    _write(
        target / "gates/generation-state.json",
        json.dumps({"run_id": target_id, "status": "provider-failed-ambiguous"}),
    )
    calls.unlink()
    failed = subprocess.run(
        command,
        env={**env, "ADOPTION_FAIL": "1"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert failed.returncode == 1
    assert calls.read_text().splitlines() == [f"adopt {target_id}"]
    assert not (tmp_path / "daily-started").exists()

    # A ledger-backed run in a non-candidate state is neutral; before 06:00 the
    # normal scheduler boundary returns without adoption or a new run.
    _write(
        target / "gates/generation-state.json",
        json.dumps({"run_id": target_id, "status": "interrupted-safe"}),
    )
    calls.unlink()
    neutral = subprocess.run(
        command,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert neutral.returncode == 0, neutral.stderr
    assert not calls.exists()
    assert not (tmp_path / "daily-started").exists()

    # Two ledger-backed ambiguous runs are never resolved by arbitrary sort
    # order; the owner refuses before invoking either adopter.
    _write(
        target / "gates/generation-state.json",
        json.dumps({"run_id": target_id, "status": "provider-failed-ambiguous"}),
    )
    _write(
        newer / "gates/generation-state.json",
        json.dumps({"run_id": newer.name, "status": "provider-failed-ambiguous"}),
    )
    _write(
        state / "articles.jsonl",
        "\n".join(
            json.dumps({"run_id": run_id, "published": False, "state": "pending"})
            for run_id in (target_id, newer.name)
        )
        + "\n",
    )
    ambiguous = subprocess.run(
        command,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert ambiguous.returncode == 1
    assert not calls.exists()
    assert not (tmp_path / "daily-started").exists()
