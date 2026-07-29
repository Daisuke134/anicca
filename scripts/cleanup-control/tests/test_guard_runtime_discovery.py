from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).parents[3]
GUARD = ROOT / "scripts" / "emergency-disk-guard.sh"


def test_guard_builds_runtime_manifest_before_pressure_sweep(tmp_path: Path) -> None:
    home = tmp_path / "home"
    state = home / ".openclaw" / "state"
    state.mkdir(parents=True)
    base_manifest = tmp_path / "base.json"
    base_manifest.write_text(
        '{"policy_version":"cleanup-v1","artifacts":[]}\n',
        encoding="utf-8",
    )
    runtime_manifest = state / "cleanup-runtime-manifest.json"
    calls = tmp_path / "calls.jsonl"
    fake_control = tmp_path / "fake_cleanup_control.py"
    fake_control.write_text(
        """\
import json
import os
import shutil
import sys

args = sys.argv[1:]
with open(os.environ["CALLS"], "a", encoding="utf-8") as handle:
    handle.write(json.dumps(args) + "\\n")
if args[0] == "runtime-manifest":
    source = args[args.index("--manifest") + 1]
    output = args[args.index("--output") + 1]
    shutil.copyfile(source, output)
    print(json.dumps({"status": "ok", "discovered": 0, "output": output}))
elif args[0] == "sweep":
    print(json.dumps({"status": "ok", "quarantined": 1, "bytes_quarantined": 8589934592}))
else:
    raise SystemExit(2)
""",
        encoding="utf-8",
    )

    environment = os.environ.copy()
    environment.update(
        {
            "CALLS": str(calls),
            "EMERGENCY_GUARD_TEST_HOME": str(home),
            "EMERGENCY_GUARD_TEST_FREE_GB": "4",
            "CLEANUP_CONTROL_PATH": str(fake_control),
            "CLEANUP_CONTROL_MANIFEST": str(base_manifest),
            "CLEANUP_CONTROL_LEDGER": str(tmp_path / "ledger.jsonl"),
            "CLEANUP_CONTROL_RUNTIME_MANIFEST": str(runtime_manifest),
            "CLEANUP_CONTROL_QUARANTINE_ROOT": str(tmp_path / "quarantine"),
        }
    )

    result = subprocess.run(
        ["/bin/bash", str(GUARD)],
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 3
    recorded = [json.loads(line) for line in calls.read_text(encoding="utf-8").splitlines()]
    assert [call[0] for call in recorded] == ["runtime-manifest", "sweep"]
    runtime_call, sweep_call = recorded
    assert runtime_call[runtime_call.index("--output") + 1] == str(runtime_manifest)
    assert sweep_call[sweep_call.index("--manifest") + 1] == str(runtime_manifest)
    roots = [
        runtime_call[index + 1]
        for index, value in enumerate(runtime_call)
        if value == "--root"
    ]
    assert roots == [
        str(home / "anicca-project/.worktrees"),
        str(home / "profitable-claude/.worktrees"),
        str(home / ".openclaw/.worktrees"),
        str(home / "anicca-project/work"),
        str(home / ".openclaw/external"),
        str(home / "anicca-project/apps"),
        str(home / "gig"),
        str(home / "anicca"),
    ]
    cache_roots = [
        runtime_call[index + 1]
        for index, value in enumerate(runtime_call)
        if value == "--cache-root"
    ]
    assert cache_roots == [
        str(home / "Library/Caches"),
        str(home / ".npm"),
        str(home / ".cargo/registry"),
        str(home / ".cargo/git"),
        str(home / ".cache"),
    ]
    published_run_roots = [
        runtime_call[index + 1]
        for index, value in enumerate(runtime_call)
        if value == "--published-run-root"
    ]
    assert published_run_roots == [str(home / ".openclaw/workspace/runs")]
    assert runtime_call[runtime_call.index("--min-cache-bytes") + 1] == "67108864"
