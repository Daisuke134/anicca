from pathlib import Path


ROOT = Path(__file__).parents[3]


def test_emergency_guard_runtime_dependencies_are_versioned() -> None:
    required = (
        ROOT / "scripts" / "emergency-disk-guard.sh",
        ROOT / "scripts" / "cleanup-control" / "cleanup_control.py",
        ROOT / "scripts" / "cleanup-control" / "artifact-lifecycle.json",
    )

    assert all(path.is_file() for path in required), [
        str(path) for path in required if not path.is_file()
    ]
