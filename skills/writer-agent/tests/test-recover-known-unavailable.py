import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "recover-known-unavailable.py"


def executable(path: Path, body: str) -> Path:
    path.write_text("#!/usr/bin/env bash\nset -euo pipefail\n" + body, encoding="utf-8")
    path.chmod(0o755)
    return path


def state_file(root: Path) -> Path:
    run = root / "runs" / "daily-2026-07-29"
    gates = run / "gates"
    gates.mkdir(parents=True)
    path = gates / "publication-state.json"
    path.write_text(
        json.dumps(
            {
                "run_id": "daily-2026-07-29",
                "run_dir": str(run),
                "state_path": str(path),
                "ledger_path": str(root / "articles.jsonl"),
                "pairs": {
                    "note/ja": {
                        "status": "unavailable",
                        "error": "note_mcp_venv_missing",
                    },
                    "substack/ja": {
                        "status": "unavailable",
                        "error": "substack_editor_redirect_own_eyes_unverified",
                        "target_kind": "substack-draft-id",
                        "target": "208936451",
                    },
                    "x-article/ja": {
                        "status": "unavailable",
                        "error": "x_editor_login_wall_own_eyes_unverified",
                        "target": "https://x.com/compose/articles/edit/1",
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    return path


def test_recovers_only_proven_known_failures(tmp_path: Path) -> None:
    root = tmp_path / "state"
    state_file(root)
    calls = tmp_path / "calls"
    ensure = tmp_path / "ensure"
    ensure.write_text(
        '#!/usr/bin/env bash\nset -euo pipefail\nprintf "ensure:%s\\n" "$1" >>"$CALLS"\n',
        encoding="utf-8",
    )
    render = executable(
        tmp_path / "render",
        'printf "render:%s\\n" "$*" >>"$CALLS"\n',
    )
    guard = tmp_path / "guard"
    guard.write_text(
        'import os, sys\n'
        'with open(os.environ["CALLS"], "a", encoding="utf-8") as out:\n'
        '    out.write("guard:" + " ".join(sys.argv[1:]) + "\\n")\n',
        encoding="utf-8",
    )
    note_mcp = tmp_path / "note-mcp"
    note_mcp.mkdir()
    env = {
        **os.environ,
        "CALLS": str(calls),
        "NOTE_MCP_DIR": str(note_mcp),
        "ARTICLE_NOTE_RUNTIME_GUARD": str(ensure),
        "ARTICLE_RENDER_VERIFY": str(render),
        "ARTICLE_PUBLICATION_GUARD": str(guard),
    }

    subprocess.run(
        ["python3", str(SCRIPT), "--state-root", str(root)],
        env=env,
        check=True,
    )

    logged = calls.read_text(encoding="utf-8").splitlines()
    assert logged == [
        f"ensure:{note_mcp}",
        "guard:clear-unavailable --pair note/ja",
        "render:--platform substack --url "
        "https://aniccabuddha.substack.com/publish/post/208936451 --lang ja",
        "guard:register-intent --pair substack/ja "
        "--target-kind substack-draft-id --target 208936451",
    ]


def test_failed_probe_never_rearms(tmp_path: Path) -> None:
    root = tmp_path / "state"
    state_file(root)
    calls = tmp_path / "calls"
    failing = executable(tmp_path / "failing", "exit 9\n")
    guard = tmp_path / "guard"
    guard.write_text(
        'import os, sys\n'
        'with open(os.environ["CALLS"], "a", encoding="utf-8") as out:\n'
        '    out.write("guard:" + " ".join(sys.argv[1:]) + "\\n")\n',
        encoding="utf-8",
    )
    note_mcp = tmp_path / "note-mcp"
    note_mcp.mkdir()
    env = {
        **os.environ,
        "CALLS": str(calls),
        "NOTE_MCP_DIR": str(note_mcp),
        "ARTICLE_NOTE_RUNTIME_GUARD": str(failing),
        "ARTICLE_RENDER_VERIFY": str(failing),
        "ARTICLE_PUBLICATION_GUARD": str(guard),
    }

    subprocess.run(
        ["python3", str(SCRIPT), "--state-root", str(root)],
        env=env,
        check=True,
    )
    assert not calls.exists()
