import plistlib
from pathlib import Path


LAUNCHD = Path(__file__).resolve().parents[1] / "launchd"
LABELS = (
    "ai.anicca.capafy-ig-account-manager",
    "ai.anicca.capafy-ig-marketing-daily",
)


def load(label):
    return plistlib.loads((LAUNCHD / f"{label}.plist").read_bytes())


def test_p1_jobs_call_source_controlled_scripts_directly():
    expected = {
        LABELS[0]: "capafy-ig-account-manager.sh",
        LABELS[1]: "capafy-ig-marketing-daily.sh",
    }
    for label, script in expected.items():
        data = load(label)
        assert data["Label"] == label
        assert data["ProgramArguments"] == [
            "/bin/bash",
            f"/Users/anicca/anicca/skills/earn/capafy-marketing/{script}",
        ]
        assert "scheduled_runner.py" not in str(data)


def test_p1_schedules_and_environment_are_explicit():
    manager, content = map(load, LABELS)
    assert manager["StartInterval"] == 300
    assert content["StartCalendarInterval"] == {"Hour": 16, "Minute": 0}
    for data in (manager, content):
        assert data["EnvironmentVariables"]["HOME"] == "/Users/anicca"
        assert "/opt/homebrew/bin" in data["EnvironmentVariables"]["PATH"]
        assert data["StandardOutPath"].startswith("/Users/anicca/.openclaw/logs/")
        assert data["StandardErrorPath"].startswith("/Users/anicca/.openclaw/logs/")


def test_labels_and_log_paths_are_unique():
    jobs = [load(label) for label in LABELS]
    assert len({job["Label"] for job in jobs}) == 2
    assert len({job["StandardOutPath"] for job in jobs}) == 2
    assert len({job["StandardErrorPath"] for job in jobs}) == 2


def test_synthetic_warmup_job_and_script_are_absent():
    root = LAUNCHD.parent
    assert not (LAUNCHD / "ai.anicca.capafy-marketing-warmup.plist").exists()
    assert not (root / "warm_jitter.sh").exists()
