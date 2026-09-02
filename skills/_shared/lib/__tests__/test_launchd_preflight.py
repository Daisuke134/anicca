from __future__ import annotations

import subprocess

from skills._shared.lib.launchd_preflight import probe


def runner_for(overrides=None):
    overrides = overrides or {}
    defaults = {
        ("/usr/bin/id", "-u"): (0, "501\n", ""),
        ("/usr/bin/id", "-un"): (0, "anicca\n", ""),
        ("/usr/bin/dscl", ".", "-read", "/Users/anicca", "UniqueID"): (0, "UniqueID: 501\n", ""),
        ("/bin/launchctl", "managername"): (0, "Aqua\n", ""),
        ("/bin/launchctl", "manageruid"): (0, "501\n", ""),
        ("/bin/launchctl", "managerpid"): (0, "1\n", ""),
        ("/bin/launchctl", "print", "gui/501"): (0, "gui/501 = { }\n", ""),
    }
    defaults.update(overrides)

    def run(argv, **_kwargs):
        rc, stdout, stderr = defaults[tuple(argv)]
        return subprocess.CompletedProcess(argv, rc, stdout, stderr)

    return run


def test_accepts_resolved_aqua_domain():
    calls = []
    base = runner_for()

    def recording_runner(argv, **kwargs):
        calls.append(tuple(argv))
        return base(argv, **kwargs)

    result = probe(recording_runner)
    assert result["status"] == "pass"
    assert result["mutation_allowed"] is True
    assert not any(argv[1:2] and argv[1] in {"bootstrap", "bootout", "kickstart", "load", "unload"} for argv in calls)


def test_rejects_numeric_username_before_directory_services_lookup():
    result = probe(runner_for({("/usr/bin/id", "-un"): (0, "501\n", "")}))
    assert result["mutation_allowed"] is False
    assert "username_unresolved" in result["errors"]


def test_rejects_directory_services_failure():
    command = ("/usr/bin/dscl", ".", "-read", "/Users/anicca", "UniqueID")
    result = probe(runner_for({command: (1, "", "eServerError")}))
    assert result["mutation_allowed"] is False
    assert "directory_services_unresolved" in result["errors"]


def test_rejects_launchctl_141_without_mutation():
    command = ("/bin/launchctl", "print", "gui/501")
    result = probe(runner_for({command: (141, "", "Reentrancy avoided")}))
    assert result["mutation_allowed"] is False
    assert "gui_domain_unreadable" in result["errors"]
    assert result["observations"]["gui_domain"]["stderr"] == "Reentrancy avoided"


def test_rejects_launchctl_manager_153():
    command = ("/bin/launchctl", "manageruid")
    calls = []
    base = runner_for({command: (153, "", "manager unavailable")})

    def recording_runner(argv, **kwargs):
        calls.append(tuple(argv))
        return base(argv, **kwargs)

    result = probe(recording_runner)
    assert result["mutation_allowed"] is False
    assert "manager_uid_mismatch" in result["errors"]
    assert ("/bin/launchctl", "print", "gui/501") not in calls


def test_gig_healer_does_not_kickstart_when_preflight_fails():
    from skills.earn.gig.scripts import gig_healer

    calls = []
    base = runner_for({
        ("/bin/launchctl", "print", "gui/501"): (141, "", "Reentrancy avoided")
    })

    def recording_runner(argv, **kwargs):
        calls.append(tuple(argv))
        return base(argv, **kwargs)

    result = gig_healer.dispatch("scheduler_restart", uid=501, runner=recording_runner)
    assert result["error"] == "blocked_control_plane"
    assert result["side_effect_performed"] is False
    assert not any("kickstart" in argv for argv in calls)
