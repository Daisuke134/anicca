"""Each loop wipes its own scratch dir, so subprocess temp files cannot leak to /tmp."""

from pathlib import Path

from runtime.loop.lm_loop_run import reset_loop_scratch


def test_reset_loop_scratch_removes_previous_run_leftovers(tmp_path: Path) -> None:
    state_root = tmp_path / "state"
    stale = state_root / "loop-tmp" / "capafy-ig-marketing-daily" / "npm-cache"
    stale.mkdir(parents=True)
    (stale / "blob.bin").write_bytes(b"x" * 1024)

    scratch = reset_loop_scratch(state_root, "capafy-ig-marketing-daily")

    assert scratch == state_root / "loop-tmp" / "capafy-ig-marketing-daily"
    assert scratch.is_dir()
    assert list(scratch.iterdir()) == []
    assert scratch.stat().st_mode & 0o777 == 0o700
