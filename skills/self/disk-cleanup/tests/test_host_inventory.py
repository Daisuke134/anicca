import json
import subprocess
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).parents[1]))

import host_inventory  # noqa: E402
from host_inventory import collect_host_inventory  # noqa: E402


def fake_runner(argv: list[str], *, timeout: float) -> subprocess.CompletedProcess[str]:
    if argv[0].endswith("/df"):
        return subprocess.CompletedProcess(
            argv,
            0,
            "Filesystem 1024-blocks Used Available Capacity Mounted on\n"
            "/dev/test 100 40 60 40% /test\n",
            "",
        )
    return subprocess.CompletedProcess(argv, 0, "8\t%s\n" % argv[-1], "")


def test_fast_inventory_is_atomic_and_records_coverage_gaps(tmp_path: Path) -> None:
    (tmp_path / "Projects").mkdir()
    state = tmp_path / "state"

    payload = collect_host_inventory(
        home=tmp_path,
        state_dir=state,
        runner=fake_runner,
    )

    written = json.loads((state / "host-inventory.json").read_text())
    assert written["schema_version"] == "life-manager-host-inventory-v1"
    assert written["inventory_sha256"] == payload["inventory_sha256"]
    assert written["mode"] == "fast"
    assert written["coverage"]["mount_count"] == 1
    assert written["coverage"]["root_count"] >= 10
    assert written["coverage"]["gaps"]
    assert all(root["measurement"] == "metadata-only" for root in written["roots"])


def test_full_inventory_uses_bounded_du_only_for_allowlisted_families(tmp_path: Path) -> None:
    for directory in ("Projects", "anicca-project", "gig", ".openclaw", "Library"):
        (tmp_path / directory).mkdir()

    payload = collect_host_inventory(
        home=tmp_path,
        state_dir=tmp_path / "state",
        full=True,
        runner=fake_runner,
    )

    measurements = {root["measurement"] for root in payload["roots"]}
    assert "bounded-du" in measurements
    assert all(root["measurement"] in {"bounded-du", "metadata-only"} for root in payload["roots"])


def test_full_inventory_allows_slow_allowlisted_root_with_bounded_timeout(tmp_path: Path) -> None:
    (tmp_path / "Projects").mkdir()

    def timeout_sensitive_runner(
        argv: list[str], *, timeout: float
    ) -> subprocess.CompletedProcess[str]:
        if argv[0].endswith("/du") and timeout < 10:
            raise subprocess.TimeoutExpired(argv, timeout)
        return fake_runner(argv, timeout=timeout)

    payload = collect_host_inventory(
        home=tmp_path,
        state_dir=tmp_path / "state",
        full=True,
        runner=timeout_sensitive_runner,
    )

    projects = next(root for root in payload["roots"] if root["path"] == str(tmp_path / "Projects"))
    assert projects["measurement"] == "bounded-du"
    assert f"size-timeout:{tmp_path / 'Projects'}" not in payload["coverage"]["gaps"]


def test_full_inventory_gives_homebrew_a_longer_bounded_probe(tmp_path: Path) -> None:
    du_calls: list[tuple[str, float]] = []

    def recording_runner(
        argv: list[str], *, timeout: float
    ) -> subprocess.CompletedProcess[str]:
        if argv[0].endswith("/du"):
            du_calls.append((argv[-1], timeout))
        return fake_runner(argv, timeout=timeout)

    collect_host_inventory(
        home=tmp_path,
        state_dir=tmp_path / "state",
        full=True,
        runner=recording_runner,
    )

    assert ("/opt/homebrew", 30) in du_calls


def test_full_inventory_enforces_global_probe_budget(tmp_path: Path) -> None:
    for directory in (
        "Projects",
        "Projects/life-manager-main",
        "anicca-project",
        "anicca",
        "anicca-docs-tools",
        "anicca-portfolio-self-improve",
        "anicca-rtdash",
        "life-manager-repo-v0-retire",
        ".codex-worktrees",
        "gig",
        ".openclaw",
        "Library",
    ):
        (tmp_path / directory).mkdir(parents=True)

    clock = [0.0]
    du_timeouts: list[float] = []

    def budget_runner(
        argv: list[str], *, timeout: float
    ) -> subprocess.CompletedProcess[str]:
        if argv[0].endswith("/du"):
            du_timeouts.append(timeout)
            clock[0] += timeout
            raise subprocess.TimeoutExpired(argv, timeout)
        return fake_runner(argv, timeout=timeout)

    payload = collect_host_inventory(
        home=tmp_path,
        state_dir=tmp_path / "state",
        full=True,
        runner=budget_runner,
        clock=lambda: clock[0],
    )

    assert sum(du_timeouts) <= 90
    assert any(gap.startswith("size-budget-exhausted:") for gap in payload["coverage"]["gaps"])


def test_full_inventory_records_partial_du_size_on_permission_error(tmp_path: Path) -> None:
    (tmp_path / "Projects").mkdir()

    def partial_runner(
        argv: list[str], *, timeout: float
    ) -> subprocess.CompletedProcess[str]:
        if argv[0].endswith("/du"):
            return subprocess.CompletedProcess(argv, 1, f"64\t{argv[-1]}\n", "Operation not permitted")
        return fake_runner(argv, timeout=timeout)

    payload = collect_host_inventory(
        home=tmp_path,
        state_dir=tmp_path / "state",
        full=True,
        runner=partial_runner,
    )

    projects = next(root for root in payload["roots"] if root["path"] == str(tmp_path / "Projects"))
    assert projects["size_bytes"] == 64 * 1024
    assert projects["measurement"] == "bounded-du-partial"
    assert f"size-permission-partial:{tmp_path / 'Projects'}" in payload["coverage"]["gaps"]


def test_full_inventory_zero_budget_skips_mount_and_size_probes(tmp_path: Path) -> None:
    def no_probe_runner(argv: list[str], *, timeout: float) -> subprocess.CompletedProcess[str]:
        raise AssertionError(f"probe must not run with zero budget: {argv}")

    payload = collect_host_inventory(
        home=tmp_path,
        state_dir=tmp_path / "state",
        full=True,
        runner=no_probe_runner,
        budget_seconds=0,
    )

    assert payload["mounts"] == []
    assert "inventory-budget-exhausted" in payload["coverage"]["gaps"]


def test_inventory_classifies_permission_limited_root(tmp_path: Path, monkeypatch) -> None:
    protected = tmp_path / "Library"
    protected.mkdir()
    real_scandir = host_inventory.os.scandir

    def permission_scandir(path):
        if Path(path) == protected:
            raise PermissionError("operation not permitted")
        return real_scandir(path)

    monkeypatch.setattr(host_inventory.os, "scandir", permission_scandir)

    payload = collect_host_inventory(home=tmp_path, state_dir=tmp_path / "state")

    assert f"permission-limited:{protected}" in payload["coverage"]["gaps"]
