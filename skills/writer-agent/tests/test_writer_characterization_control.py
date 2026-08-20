import importlib.util
import json
from pathlib import Path
import subprocess


SCRIPT = Path(__file__).parents[1] / "scripts" / "writer_characterization_control.py"
SPEC = importlib.util.spec_from_file_location("writer_characterization_control", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def _git(cwd: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True,
    )
    return completed.stdout.strip()


def test_prepare_creates_receipted_isolated_characterization_worktree(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "writer-test")
    _git(repo, "config", "user.name", "Writer Test")
    (repo / "README.md").write_text("writer\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "initial")
    base_head = _git(repo, "rev-parse", "HEAD")

    fingerprint = "e717150d6a6ab6e5379f586d5f462b1b62ae22ae614038464736df4d8feca09f"
    investigation_path = tmp_path / "investigation.json"
    investigation_path.write_text(
        json.dumps({
            "schema": "writer.self-heal.unknown-investigation",
            "version": 1,
            "fingerprint": fingerprint,
            "cause_status": "EVIDENCE_BACKED_HYPOTHESIS",
            "cause_hypothesis": (
                "preexisting_draft_was_not_reconciled_before_timeout_classification"
            ),
            "next_action": "CHARACTERIZE_PREEXISTING_EFFECT_RECONCILIATION",
            "evidence_gaps": [],
        }),
        encoding="utf-8",
    )
    repair_root = tmp_path / "repair-worktrees"
    state_dir = tmp_path / "repair-state"

    result = MODULE.prepare(
        repo,
        base_head,
        repair_root,
        state_dir,
        investigation_path,
        "2026-08-06T19:15:00+09:00",
    )

    worktree = Path(result["worktree_path"])
    assert worktree.is_dir()
    assert _git(worktree, "rev-parse", "HEAD") == base_head
    assert _git(worktree, "branch", "--show-current") == (
        "repair/writer-e717150d6a6a-characterization"
    )
    assert result["schema"] == "writer.self-heal.characterization-plan"
    assert result["status"] == "READY_TO_GENERATE"
    assert result["fingerprint"] == fingerprint
    assert result["allowed_paths"] == ["skills/writer-agent/tests/"]
    prompt = Path(result["prompt_path"])
    assert prompt.is_file()
    prompt_text = prompt.read_text(encoding="utf-8")
    assert str(investigation_path.resolve()) in prompt_text
    assert "Do not modify production code" in prompt_text
    assert "record the observed non-zero exit code" in prompt_text
