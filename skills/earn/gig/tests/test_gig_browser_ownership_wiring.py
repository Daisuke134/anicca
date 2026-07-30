import os
import plistlib
import subprocess
from pathlib import Path


GIG_WORK = Path(__file__).resolve().parents[1]


def test_gig_pass_names_its_browser_owner_and_scopes_tab_gc():
    source = (GIG_WORK / "gig_pass.sh").read_text(encoding="utf-8")

    assert 'export CLOAK_BROWSER_OWNER="gig-pass"' in source
    assert 'cdp_tab_gc.py" --owner "$CLOAK_BROWSER_OWNER"' in source


def test_reply_detector_uses_a_separate_stable_browser_owner():
    source = (GIG_WORK / "scripts/reply_detector.py").read_text(encoding="utf-8")

    assert 'os.environ["CLOAK_BROWSER_OWNER"] = "gig-reply-detector"' in source


def test_all_browser_drivers_share_one_dedicated_gig_runtime():
    launchd = GIG_WORK / "launchd"
    for name in ("pass", "auditor", "reply-detector"):
        with (launchd / f"ai.anicca.hf-gig-{name}.plist").open("rb") as handle:
            environment = plistlib.load(handle)["EnvironmentVariables"]
        assert environment["CLOAK_CDP_BASE_URL"] == "http://127.0.0.1:9223"
        assert environment["CDP_DAILY_DRIVER_PORT"] == "9223"
        assert environment["CDP_DAILY_DRIVER_PROFILE"] == (
            "__HOME__/.cloak/profiles/gig-daily-driver"
        )
        assert environment["CLOAK_CONTEXT_LEASES_FILE"] == (
            "__HOME__/.cloak/vault/gig-leases.json"
        )
        assert environment["CLOAK_TARGET_OWNERS_FILE"] == (
            "__HOME__/.cloak/vault/gig-target-owners.json"
        )
        assert environment["CLOAK_BROWSER_LAUNCHD_LABEL"] == (
            "ai.anicca.hf-gig-browser"
        )
        assert environment["CDP_LOCK_DIR"] == "__HOME__/gig/.cdp-gig.lock"


def test_gig_browser_has_a_launchd_keepalive_owner():
    browser_plist = (
        GIG_WORK / "launchd" / "ai.anicca.hf-gig-browser.plist"
    )
    with browser_plist.open("rb") as handle:
        job = plistlib.load(handle)

    assert job["Label"] == "ai.anicca.hf-gig-browser"
    assert job["RunAtLoad"] is True
    assert job["KeepAlive"] is True
    arguments = job["ProgramArguments"]
    assert arguments == [
        "/bin/bash",
        "__LIFE_MANAGER_REPO__/skills/earn/gig/scripts/launch_gig_browser.sh",
    ]
    environment = job["EnvironmentVariables"]
    assert environment["GIG_BROWSER_PORT"] == "9223"
    assert environment["GIG_BROWSER_PROFILE"] == (
        "__HOME__/.cloak/profiles/gig-daily-driver"
    )
    launcher = (
        GIG_WORK / "scripts" / "launch_gig_browser.sh"
    ).read_text(encoding="utf-8")
    assert '--remote-debugging-port="$GIG_BROWSER_PORT"' in launcher
    assert '--user-data-dir="$GIG_BROWSER_PROFILE"' in launcher


def test_gig_browser_disables_post_quantum_tls_only_for_supported_chromium():
    launcher = (
        GIG_WORK / "scripts" / "launch_gig_browser.sh"
    ).read_text(encoding="utf-8")

    policy_write = launcher.index(
        "PostQuantumKeyAgreementEnabled -bool false"
    )
    browser_exec = launcher.index('exec "$chromium_bin"')
    assert policy_write < browser_exec
    assert "org.chromium.Chromium" in launcher
    assert "145" in launcher
    assert "146" in launcher


def test_nested_browser_step_inherits_universal_lock_without_deadlock(tmp_path):
    wrapper = GIG_WORK / "scripts/run_with_cdp_lock.sh"
    environment = os.environ.copy()
    environment["CDP_LOCK_DIR"] = str(tmp_path / "gig-browser.lock")
    completed = subprocess.run(
        [
            "bash",
            str(wrapper),
            "outer",
            "0",
            "--",
            "bash",
            str(wrapper),
            "inner",
            "0",
            "--",
            "/usr/bin/true",
        ],
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


def test_gig_evidence_helpers_follow_the_dedicated_cdp_url():
    for name in ("cdp_snapshot.py", "cdp_nav_snapshot.py"):
        source = (GIG_WORK / "scripts" / name).read_text(encoding="utf-8")
        assert "CLOAK_CDP_BASE_URL" in source
        assert 'f"ws://{urlparse(_cdp_base()).netloc}/devtools/page/{tab}"' in source


def test_b2_parent_reopens_applied_page_between_ledger_write_and_success_gate():
    source = (GIG_WORK / "gig_pass.sh").read_text(encoding="utf-8")

    report = source.index('scripts/application_report.py"')
    readback = source.index('scripts/coconala_applied_readback.py"')
    gate = source.index('scripts/b2_result_gate.py" validate')
    assert report < readback < gate
    assert 'cdp_context_lease.py" acquire "$readback_lease"' in source
    assert 'cdp_context_lease.py" release "$readback_lease"' in source
    assert '--output "$B2_READBACK"' in source


def test_read_only_reality_verifier_never_opens_a_visible_session_probe():
    source = (GIG_WORK / "gig_reality_verify.sh").read_text(encoding="utf-8")

    assert '"$VAULT" keepalive' not in source
    assert 'cdp_nav_snapshot.py" probe-session' in source
