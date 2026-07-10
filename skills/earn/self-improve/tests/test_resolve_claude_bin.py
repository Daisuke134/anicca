"""tests/test_resolve_claude_bin.py — REQ-CB1..CB3 (promote-gate-claude-bin-fix).

`lib.promote_gate_run._resolve_claude_bin()` locates the `claude` CLI before the harness shells
out to it for the fresh per-candidate promotion adversary (REQ-RH4 step 3). Regression: under
launchd's minimal `PATH`, `shutil.which("claude")` returns `None` and the old hardcoded fallback
`/opt/homebrew/bin/claude` doesn't exist on this machine (the real npm-installed binary lives at
`~/.local/bin/claude`) — every promotable self-improve candidate has hit
`"claude binary not found (tried /opt/homebrew/bin/claude)"` as a result (see
`.vcsdd/features/promote-gate-claude-bin-fix/specs/behavioral-spec.md` for the full incident).

These tests never touch the real filesystem/PATH — `shutil.which`, `os.path.isfile`, and
`os.access` are all monkeypatched, so the suite is deterministic regardless of which machine or
worktree it runs in.
"""
import os
from unittest import mock

from lib import promote_gate_run


def _access_checking_x_ok(is_executable_fn):
    """Shared `os.access` fake: asserts every call passes `mode=os.X_OK` (never `os.F_OK`/
    `os.R_OK`), so a mutation swapping the permission flag fails these tests instead of passing
    them vacuously — that swap would silently reintroduce the exact stale-non-executable-file
    defect PROP-CB2c exists to prevent."""

    def fake_access(path, mode):
        assert mode == os.X_OK, f"expected os.access to be called with os.X_OK, got {mode!r}"
        return is_executable_fn(path)

    return fake_access


def test_path_hit_returns_which_result_unchanged():
    """REQ-CB1: when `shutil.which` finds a binary, use it — no fallback probing at all."""
    with mock.patch("shutil.which", return_value="/some/PATH/dir/claude") as mocked_which, mock.patch(
        "os.path.isfile"
    ) as mocked_isfile:
        result = promote_gate_run._resolve_claude_bin()

    assert result == "/some/PATH/dir/claude"
    mocked_which.assert_called_once_with("claude")
    mocked_isfile.assert_not_called()  # REQ-CB1 short-circuits before any fallback probing


def test_which_miss_falls_back_to_first_existing_known_good_path():
    """REQ-CB2: `shutil.which` misses; probe the ordered fallback list and return the first
    candidate that actually exists+is executable — NOT just the first candidate in the list.
    Asserts `os.path.isfile` was actually consulted (not just a hardcoded string returned),
    otherwise this test would trivially pass against the OLD, unfixed implementation too."""

    def fake_exists(path):
        # Only the SECOND known-good candidate "exists" on this fake filesystem.
        return path == "/opt/homebrew/bin/claude"

    with mock.patch("shutil.which", return_value=None), mock.patch(
        "os.path.isfile", side_effect=fake_exists
    ) as mocked_isfile, mock.patch("os.access", side_effect=_access_checking_x_ok(lambda _path: True)):
        result = promote_gate_run._resolve_claude_bin()

    assert result == "/opt/homebrew/bin/claude"
    assert mocked_isfile.call_count >= 2  # actually probed >=2 candidates, didn't just return a literal


def test_which_miss_and_no_fallback_exists_returns_original_default_string():
    """REQ-CB3: when NOTHING resolves (no PATH hit, no known-good path exists on disk), the
    function must still return the exact literal `/opt/homebrew/bin/claude` string so
    `_invoke_adversary`'s existing fail-closed `FileNotFoundError` handling and its error message
    (`f"claude binary not found (tried {claude_bin})"`) are byte-for-byte unchanged."""
    with mock.patch("shutil.which", return_value=None), mock.patch(
        "os.path.isfile", return_value=False
    ) as mocked_isfile, mock.patch("os.access", return_value=False):
        result = promote_gate_run._resolve_claude_bin()

    assert result == "/opt/homebrew/bin/claude"
    assert mocked_isfile.called  # actually probed the fallback list, didn't just skip straight to the default


def test_which_miss_prefers_local_bin_over_homebrew_when_both_exist():
    """REQ-CB2 ordering: `~/.local/bin/claude` (the actual install location observed on this
    machine, confirmed via `zsh -lc 'type claude'`) must be checked BEFORE `/opt/homebrew/bin/claude`
    so the real-world regression this fix targets is actually resolved, not just theoretically
    fixed."""
    local_bin_claude = os.path.expanduser("~/.local/bin/claude")

    def fake_exists(path):
        return path in (local_bin_claude, "/opt/homebrew/bin/claude")

    with mock.patch("shutil.which", return_value=None), mock.patch(
        "os.path.isfile", side_effect=fake_exists
    ), mock.patch("os.access", side_effect=_access_checking_x_ok(lambda _path: True)):
        result = promote_gate_run._resolve_claude_bin()

    assert result == local_bin_claude


def test_which_miss_skips_candidate_that_exists_but_is_not_executable():
    """REQ-CB2's "exists" test is `os.path.isfile` AND `os.access(path, os.X_OK)` — a candidate
    file that exists but lacks the executable bit (e.g. a stale/corrupt install, or a
    non-executable regular file left behind by a broken package manager step) must be skipped in
    favor of the next candidate in the ordered list, never returned as-is (which would make
    `_invoke_adversary`'s subsequent `subprocess.run` raise an uncaught `PermissionError` instead
    of the handled `FileNotFoundError` path)."""
    local_bin_claude = os.path.expanduser("~/.local/bin/claude")

    def fake_isfile(path):
        # Both candidates exist as files...
        return path in (local_bin_claude, "/opt/homebrew/bin/claude")

    with mock.patch("shutil.which", return_value=None), mock.patch(
        "os.path.isfile", side_effect=fake_isfile
    ), mock.patch(
        # ...but only the SECOND is actually executable.
        "os.access",
        side_effect=_access_checking_x_ok(lambda path: path == "/opt/homebrew/bin/claude"),
    ) as mocked_access:
        result = promote_gate_run._resolve_claude_bin()

    assert result == "/opt/homebrew/bin/claude"
    assert mocked_access.call_count >= 2  # both candidates' executable bit was actually checked
