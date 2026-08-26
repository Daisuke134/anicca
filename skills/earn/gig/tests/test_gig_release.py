import importlib.util
from pathlib import Path
from types import SimpleNamespace


SCRIPT = Path(__file__).parents[1] / "scripts" / "gig_release.py"
SPEC = importlib.util.spec_from_file_location("gig_release_gc_test", SCRIPT)
gig_release = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(gig_release)


def test_writer_notification_identity_has_no_personal_public_default(monkeypatch):
    monkeypatch.setattr(gig_release, "OVERRIDES", Path("/nonexistent/install.json"))
    manifest, table = gig_release.settings(Path("/release"))
    job = next(
        row for row in manifest["jobs"]
        if row["label"] == "ai.anicca.writer-opportunity-response"
    )
    environment = gig_release.plist_for(job, table)["EnvironmentVariables"]

    assert not environment.get("WRITER_GMAIL_ACCOUNT")
    assert table["WRITER_TELEGRAM_TARGET"] == ""


def test_shared_launchd_path_resolves_user_installed_agent_tools(monkeypatch):
    monkeypatch.setattr(gig_release, "OVERRIDES", Path("/nonexistent/install.json"))
    manifest, table = gig_release.settings(Path("/release"))
    job = next(
        row for row in manifest["jobs"]
        if row["label"] == "ai.anicca.life-manager-upwork-free-loop"
    )

    environment = gig_release.plist_for(job, table)["EnvironmentVariables"]

    assert environment["PATH"].split(":")[0] == f'{table["HOME"]}/.local/bin'


def test_gc_preserves_release_referenced_by_loaded_launchd_job(tmp_path, monkeypatch):
    current_sha = "a" * 40
    loaded_sha = "b" * 40
    rollback_sha = "c" * 40
    stale_sha = "d" * 40
    for sha in (current_sha, loaded_sha, rollback_sha, stale_sha):
        release = tmp_path / sha
        release.mkdir()
        (release / "marker").write_text(sha, encoding="utf-8")
    (tmp_path / "current").symlink_to(current_sha)

    monkeypatch.setattr(gig_release, "RELEASE_ROOT", tmp_path)
    monkeypatch.setattr(gig_release, "CURRENT_RELEASE", tmp_path / "current")
    monkeypatch.setattr(
        gig_release,
        "loaded_program",
        lambda label: ["/bin/bash", str(tmp_path / loaded_sha / "browser.sh")],
    )
    monkeypatch.setattr(
        gig_release.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=""),
    )

    removed = gig_release.collect_old_releases()

    assert loaded_sha not in removed
    assert (tmp_path / loaded_sha).is_dir()


def test_gc_preserves_release_pinned_by_live_wrapper(tmp_path, monkeypatch):
    current_sha = "a" * 40
    pinned_sha = "b" * 40
    rollback_sha = "c" * 40
    stale_sha = "d" * 40
    for sha in (current_sha, pinned_sha, rollback_sha, stale_sha):
        release = tmp_path / sha
        release.mkdir()
        (release / "marker").write_text(sha, encoding="utf-8")
    (tmp_path / "current").symlink_to(current_sha)
    parent = tmp_path / pinned_sha / "skills" / "earn" / "gig" / "scripts" / "application_parent.py"
    parent.parent.mkdir(parents=True)
    parent.touch()

    monkeypatch.setattr(gig_release, "RELEASE_ROOT", tmp_path)
    monkeypatch.setattr(gig_release, "CURRENT_RELEASE", tmp_path / "current")
    monkeypatch.setattr(gig_release, "loaded_program", lambda _label: [])
    monkeypatch.setattr(gig_release.os, "getpid", lambda: 4242)
    monkeypatch.setattr(gig_release.os, "kill", lambda pid, signal: None)
    monkeypatch.setattr(
        gig_release.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=""),
    )

    marker = gig_release.pin_release_for_process(parent)
    removed = gig_release.collect_old_releases()

    assert marker == tmp_path / ".pins" / f"4242-{pinned_sha}"
    assert pinned_sha not in removed
    assert (tmp_path / pinned_sha).is_dir()


def test_job_needs_activation_when_loaded_environment_is_stale(monkeypatch):
    job = {
        "label": "ai.anicca.hf-gig-reply-detector",
        "program": ["/usr/bin/python3", "{{RELEASE}}/reply_detector.py"],
        "env": {"GIG_NO_CONTACT_REGISTRY": "{{HOME}}/.config/no-contact.json"},
        "log_basename": "reply",
    }
    table = {
        "RELEASE": "/tmp/current",
        "HOME": "/Users/test",
        "GIG_LOG_DIR": "/tmp/logs",
    }
    desired = gig_release.plist_for(job, table)
    monkeypatch.setattr(gig_release, "loaded_program", lambda _label: desired["ProgramArguments"])
    monkeypatch.setattr(gig_release, "loaded_environment", lambda _label: {})

    assert gig_release.job_needs_activation(job, table) is True


def test_job_does_not_need_activation_when_program_and_environment_match(monkeypatch):
    job = {
        "label": "ai.anicca.hf-gig-reply-detector",
        "program": ["/usr/bin/python3", "{{RELEASE}}/reply_detector.py"],
        "env": {"GIG_NO_CONTACT_REGISTRY": "{{HOME}}/.config/no-contact.json"},
        "log_basename": "reply",
    }
    table = {
        "RELEASE": "/tmp/current",
        "HOME": "/Users/test",
        "GIG_LOG_DIR": "/tmp/logs",
    }
    desired = gig_release.plist_for(job, table)
    monkeypatch.setattr(gig_release, "loaded_program", lambda _label: desired["ProgramArguments"])
    monkeypatch.setattr(
        gig_release,
        "loaded_environment",
        lambda _label: desired["EnvironmentVariables"] | {"XPC_SERVICE_NAME": job["label"]},
    )

    assert gig_release.job_needs_activation(job, table) is False


def test_default_activation_never_restarts_a_busy_continuous_lane():
    label = "ai.anicca.hf-gig-reply-detector"

    assert gig_release.skip_busy_for_requested_activation(label, None) is True
    assert gig_release.skip_busy_for_requested_activation(label, {label}) is False


def test_upwork_browser_running_fence_uses_process_fallback(monkeypatch):
    label = "ai.anicca.life-manager-upwork-browser"
    ps_output = [""]

    def run(command, **_kwargs):
        if command[:2] == ["launchctl", "print"]:
            return SimpleNamespace(returncode=1, stdout="")
        if command == ["ps", "-axo", "command="]:
            return SimpleNamespace(returncode=0, stdout=ps_output[0])
        raise AssertionError(command)

    monkeypatch.setattr(gig_release.subprocess, "run", run)

    assert gig_release.is_running(label) is False
    ps_output[0] = "/Applications/Chromium --remote-debugging-port=9233\n"
    assert gig_release.is_running(label) is True


def test_coconala_browser_running_fence_uses_process_fallback(monkeypatch):
    label = "ai.anicca.hf-gig-browser"
    ps_output = [""]

    def run(command, **_kwargs):
        if command[:2] == ["launchctl", "print"]:
            return SimpleNamespace(returncode=1, stdout="")
        if command == ["ps", "-axo", "command="]:
            return SimpleNamespace(returncode=0, stdout=ps_output[0])
        raise AssertionError(command)

    monkeypatch.setattr(gig_release.subprocess, "run", run)

    assert gig_release.is_running(label) is False
    ps_output[0] = "/Applications/Chromium --remote-debugging-port=9223\n"
    assert gig_release.is_running(label) is True


def test_default_release_scope_is_only_the_four_coconala_business_lanes():
    assert gig_release.activation_labels(None) == {
        "ai.anicca.hf-gig-apply-direct",
        "ai.anicca.hf-gig-storefront-direct",
        "ai.anicca.hf-gig-reply-detector",
        "ai.anicca.hf-gig-paid-direct",
    }


def test_explicit_release_scope_is_preserved():
    assert gig_release.activation_labels({"example.job"}) == {"example.job"}
