import json
import subprocess
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).parents[1]))

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
