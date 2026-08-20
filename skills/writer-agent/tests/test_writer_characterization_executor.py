import importlib.util
import json
from pathlib import Path
import stat
import subprocess

import pytest


SCRIPT = Path(__file__).parents[1] / "scripts" / "writer_characterization_executor.py"
SPEC = importlib.util.spec_from_file_location("writer_characterization_executor", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True,
    ).stdout.strip()


def _unsafe_fixture(
    tmp_path: Path, *, test_source: str, command: list[str],
) -> tuple[Path, Path, Path, Path]:
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    branch = "repair/writer-test-characterization"
    _git(worktree, "init", "-b", branch)
    _git(worktree, "config", "user.email", "writer-test")
    _git(worktree, "config", "user.name", "Writer Test")
    (worktree / "skills/writer-agent/tests").mkdir(parents=True)
    readme = worktree / "README.md"
    readme.write_text("writer\n", encoding="utf-8")
    _git(worktree, "add", "README.md")
    _git(worktree, "commit", "-m", "initial")
    base_head = _git(worktree, "rev-parse", "HEAD")

    state_dir = tmp_path / "state"
    state_dir.mkdir()
    agent_receipt_path = state_dir / "agent-receipt.json"
    prompt_path = state_dir / "prompt.txt"
    prompt_path.write_text(
        f"Write JSON to {agent_receipt_path}\n", encoding="utf-8",
    )
    fingerprint = "a" * 64
    plan_path = state_dir / "plan.json"
    plan_path.write_text(json.dumps({
        "schema": "writer.self-heal.characterization-plan",
        "version": 1,
        "status": "READY_TO_GENERATE",
        "fingerprint": fingerprint,
        "base_head": base_head,
        "branch": branch,
        "worktree_path": str(worktree),
        "allowed_paths": ["skills/writer-agent/tests/"],
        "prompt_path": str(prompt_path),
        "agent_receipt_path": str(agent_receipt_path),
    }), encoding="utf-8")
    test_path = "skills/writer-agent/tests/test_generated_characterization.py"
    fake_runner = tmp_path / "fake-model-runner.py"
    fake_runner.write_text(
        "#!/usr/bin/env python3\n"
        "import json\n"
        "from pathlib import Path\n"
        "import re\n"
        "import sys\n"
        "prompt = Path(sys.argv[sys.argv.index('--prompt-file') + 1]).read_text()\n"
        "receipt = Path(re.search(r'Write JSON to (.+)', prompt).group(1))\n"
        f"test_path = Path({test_path!r})\n"
        f"test_path.write_text({test_source!r})\n"
        "receipt.write_text(json.dumps({\n"
        "  'schema':'writer.self-heal.characterization-agent-receipt',\n"
        "  'version':1,\n"
        f"  'fingerprint':{fingerprint!r},\n"
        f"  'test_path':{test_path!r},\n"
        f"  'command':{command!r},\n"
        "  'exit_code':1,\n"
        "  'failure_signature':'captured-preexisting-draft-not-reconciled',\n"
        "  'observed_at':'2026-08-06T19:20:00+09:00'\n"
        "}))\n",
        encoding="utf-8",
    )
    fake_runner.chmod(fake_runner.stat().st_mode | stat.S_IXUSR)
    return plan_path, fake_runner, state_dir / "verified.json", readme


def test_execute_accepts_only_a_reproduced_test_only_failure(tmp_path: Path) -> None:
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    _git(worktree, "init", "-b", "repair/writer-test-characterization")
    _git(worktree, "config", "user.email", "writer-test")
    _git(worktree, "config", "user.name", "Writer Test")
    tests_dir = worktree / "skills/writer-agent/tests"
    tests_dir.mkdir(parents=True)
    (worktree / "README.md").write_text("writer\n", encoding="utf-8")
    _git(worktree, "add", "README.md")
    _git(worktree, "commit", "-m", "initial")
    base_head = _git(worktree, "rev-parse", "HEAD")

    state_dir = tmp_path / "state"
    state_dir.mkdir()
    prompt_path = state_dir / "prompt.txt"
    agent_receipt_path = state_dir / "agent-receipt.json"
    prompt_path.write_text(
        f"Write JSON to {agent_receipt_path}\n",
        encoding="utf-8",
    )
    fingerprint = "a" * 64
    plan_path = state_dir / "plan.json"
    plan_path.write_text(
        json.dumps({
            "schema": "writer.self-heal.characterization-plan",
            "version": 1,
            "status": "READY_TO_GENERATE",
            "fingerprint": fingerprint,
            "base_head": base_head,
            "branch": "repair/writer-test-characterization",
            "worktree_path": str(worktree),
            "allowed_paths": ["skills/writer-agent/tests/"],
            "prompt_path": str(prompt_path),
            "agent_receipt_path": str(agent_receipt_path),
        }),
        encoding="utf-8",
    )
    fake_runner = tmp_path / "fake-model-runner.py"
    fake_runner.write_text(
        """#!/usr/bin/env python3
import json
from pathlib import Path
import re
import sys
prompt = Path(sys.argv[sys.argv.index('--prompt-file') + 1]).read_text()
receipt = Path(re.search(r'Write JSON to (.+)', prompt).group(1))
test_path = Path('skills/writer-agent/tests/test_generated_characterization.py')
test_path.write_text('def test_captured_failure():\\n    assert False, \\"captured-preexisting-draft-not-reconciled\\"\\n')
receipt.write_text(json.dumps({
  'schema':'writer.self-heal.characterization-agent-receipt',
  'version':1,
  'fingerprint':'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
  'test_path':str(test_path),
  'command':['python3','-m','pytest','-q',str(test_path)],
  'exit_code':1,
  'failure_signature':'captured-preexisting-draft-not-reconciled',
  'observed_at':'2026-08-06T19:20:00+09:00'
}))
""",
        encoding="utf-8",
    )
    fake_runner.chmod(fake_runner.stat().st_mode | stat.S_IXUSR)
    out_path = state_dir / "verified.json"

    result = MODULE.execute(plan_path, fake_runner, out_path, 30)

    assert result["status"] == "RED_VERIFIED"
    assert result["fingerprint"] == fingerprint
    assert result["test_path"] == (
        "skills/writer-agent/tests/test_generated_characterization.py"
    )
    assert result["observed_exit_code"] != 0
    assert result["failure_signature"] == (
        "captured-preexisting-draft-not-reconciled"
    )
    assert result["changed_paths"] == [
        "skills/writer-agent/tests/test_generated_characterization.py"
    ]
    assert result["next_action"] == "GENERATE_CANDIDATE_FIX"
    assert json.loads(out_path.read_text())["status"] == "RED_VERIFIED"


def test_execute_rejects_agent_supplied_non_pytest_command(tmp_path: Path) -> None:
    test_path = "skills/writer-agent/tests/test_generated_characterization.py"
    command = [
        "python3", "-c",
        "from pathlib import Path; Path('README.md').write_text('mutated'); "
        "raise SystemExit('captured-preexisting-draft-not-reconciled')",
        test_path,
    ]
    plan, runner, out, readme = _unsafe_fixture(
        tmp_path,
        test_source="def test_placeholder():\n    assert True\n",
        command=command,
    )

    with pytest.raises(ValueError, match="exact pytest argv"):
        MODULE.execute(plan, runner, out, 30)

    assert readme.read_text(encoding="utf-8") == "writer\n"


def test_execute_rejects_test_that_mutates_production_path(tmp_path: Path) -> None:
    test_path = "skills/writer-agent/tests/test_generated_characterization.py"
    plan, runner, out, readme = _unsafe_fixture(
        tmp_path,
        test_source=(
            "from pathlib import Path\n"
            "def test_captured_failure():\n"
            "    Path('README.md').write_text('mutated')\n"
            "    assert False, 'captured-preexisting-draft-not-reconciled'\n"
        ),
        command=["python3", "-m", "pytest", "-q", test_path],
    )

    with pytest.raises(ValueError, match="verification changed path outside allowed scope"):
        MODULE.execute(plan, runner, out, 30)

    assert readme.read_text(encoding="utf-8") == "mutated"
