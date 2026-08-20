from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def executable(path: Path, body: str) -> None:
    path.write_text(body)
    path.chmod(0o755)


def test_note_resume_uses_failure_circuit_before_repeating_publisher(
    tmp_path: Path,
) -> None:
    """The real worker wiring must suppress a third unchanged note failure."""
    fake_root = tmp_path / "article-writer"
    state_dir = tmp_path / "state"
    run_dir = state_dir / "runs" / "daily-2026-07-30"
    scripts = fake_root / "scripts"
    runtime = fake_root / "runtime"
    gates = run_dir / "gates"
    scripts.mkdir(parents=True)
    runtime.mkdir()
    gates.mkdir(parents=True)
    (scripts / "note-publish").mkdir()
    (scripts / "_shared").mkdir()
    shutil.copy(ROOT / "scripts" / "article-resume-pending.sh", scripts)
    shutil.copy(ROOT / "scripts" / "resume_failure_circuit.py", scripts)
    shutil.copy(ROOT / "scripts" / "_shared" / "notifier.sh", scripts / "_shared")
    (scripts / "note-publish" / "set-eyecatch-draft.py").write_text(
        "selector_version = 1\n"
    )

    (scripts / "article_daily_start_control.py").write_text(
        'print(\'{"action":"skip-pending-worker"}\')\n'
    )
    for name in ("quality_feedback_recovery.py", "quality_repair_control.py"):
        (scripts / name).write_text('print(\'{"status":"NONE"}\')\n')
    (scripts / "recover-known-unavailable.py").write_text("raise SystemExit(0)\n")
    (scripts / "article_pending.py").write_text(
        "import json\n"
        f"print(json.dumps({{'status':'READY','run_id':'daily-2026-07-30',"
        f"'run_dir':{str(run_dir)!r},"
        f"'state_path':{str(gates / 'publication-state.json')!r},"
        f"'ledger_path':{str(state_dir / 'articles.jsonl')!r},"
        "'initialization_pairs':[],'eligible_pairs':['note/ja']}))\n"
    )
    executable(
        scripts / "publish-note-managed.py",
        "#!/usr/bin/env python3\n"
        "import os\n"
        "open(os.environ['CALLS'], 'a').write('call\\n')\n"
        "raise SystemExit('TimeoutError: upload button is absent')\n",
    )
    executable(
        scripts / "article-completion-notify.py",
        "#!/usr/bin/env python3\nraise SystemExit(0)\n",
    )
    executable(
        runtime / "model-runner.sh",
        "#!/usr/bin/env bash\nexit 91\n",
    )
    (runtime / "model-runner-support.py").write_text("raise SystemExit(0)\n")
    (gates / "publication-state.json").write_text(
        json.dumps(
            {
                "run_id": "daily-2026-07-30",
                "pairs": {
                    "note/ja": {
                        "status": "intent",
                        "target_kind": "note-key",
                        "target": "n-test",
                    }
                },
            }
        )
    )
    (state_dir / "articles.jsonl").write_text("")
    calls = tmp_path / "calls"
    log = tmp_path / "resume.log"
    env = {
        **os.environ,
        "ARTICLE_ROOT": str(fake_root),
        "ARTICLE_STATE_DIR": str(state_dir),
        "ARTICLE_LOCAL_DATE": "2026-07-30",
        "ARTICLE_RESUME_LOG": str(log),
        "ARTICLE_MODEL_RUNNER": str(runtime / "model-runner.sh"),
        "ARTICLE_MODEL_SUPPORT": str(runtime / "model-runner-support.py"),
        "CALLS": str(calls),
        "TELEGRAM_BOT_TOKEN": "",
        "TELEGRAM_CHAT_ID": "",
    }
    command = ["bash", str(scripts / "article-resume-pending.sh")]

    results = [
        subprocess.run(command, env=env, capture_output=True, text=True, check=False)
        for _ in range(3)
    ]

    assert [result.returncode for result in results] == [1, 0, 0]
    assert calls.read_text().splitlines() == ["call", "call"]
    assert "same-failure-circuit-open" in log.read_text()
