#!/usr/bin/env python3
"""Executable contract for the bounded repair channel (SSOT §9.3.1 item H2).

Three properties are non-negotiable and are asserted here before anything else:

* a candidate that fails its test gate can never become eligible;
* a repair attempt cannot write outside its isolated workspace;
* the external-effect prohibitions are enforced by code, not by prompt text.

Every test runs against a throwaway git repository and a fake `codex` binary, so
no live state, no live tree, and no provider are touched.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
RUNNER = ROOT / "runtime" / "model-runner.sh"


def _module(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


candidate = _module("writer_repair_candidate")
incidents = _module("writer_incident_queue")

FINGERPRINT = "b4" + "9" * 62
OBSERVED_AT = "2026-08-07T12:00:00Z"


# ---------------------------------------------------------------------------
# fixtures: a throwaway repo that looks enough like the real one
# ---------------------------------------------------------------------------

def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True,
    ).stdout.strip()


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    source = tmp_path / "repo"
    (source / "skills" / "writer-agent" / "tests").mkdir(parents=True)
    (source / "skills" / "writer-agent" / "scripts").mkdir(parents=True)
    (source / "skills" / "writer-agent" / "scripts" / "publish.py").write_text(
        "BODY = 'original'\n", encoding="utf-8",
    )
    _git(source, "init", "-q", "-b", "main", ".")
    _git(source, "config", "user.email", "repair@example.invalid")
    _git(source, "config", "user.name", "repair")
    _git(source, "add", "-A")
    _git(source, "commit", "-q", "-m", "base")
    return source


@pytest.fixture()
def verdict_checkpoint(tmp_path: Path) -> Path:
    """The H3 investigation checkpoint this repair channel acts on."""
    sessions = tmp_path / "state" / "self-heal" / "investigation-sessions"
    sessions.mkdir(parents=True)
    path = sessions / f"{FINGERPRINT}.json"
    path.write_text(
        json.dumps({
            "schema": "writer.self-heal.investigation-session",
            "version": 1,
            "fingerprint": FINGERPRINT,
            "status": "COMPLETE",
            "slice_count": 1,
            "max_slices": 3,
            "trigger": {"occurrence_count": 4, "deployed_commit": "a" * 40},
            "verdict": {
                "cause_status": "UNDETERMINED",
                "complete": True,
                "evidence_gaps": ["official_primary_document_research_required"],
                "findings": [],
                "primary_sources": [],
                "remaining_work": "fetch note's current terms and posting policy",
            },
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def _fake_codex(path: Path, body: str) -> Path:
    """A stand-in for the provider that performs a scripted edit.

    Its two control variables are `ARTICLE_`-prefixed on purpose: the channel
    builds the model child's environment from an allowlist, so a harness
    variable that is not allowlisted genuinely does not reach the child. The
    test adapts to the guardrail rather than the guardrail to the test.
    """
    path.write_text(
        "#!/usr/bin/env bash\n"
        "set -u\n"
        'printf "%s\\n" "$@" >>"$ARTICLE_CAPTURE_ARGS"\n'
        'cat >/dev/null\n'
        'printf \'{"type":"thread.started","thread_id":"probe-thread"}\\n\'\n'
        + body
        + '\nprintf \'{"type":"turn.completed","usage":{"input_tokens":11,'
        '"output_tokens":7}}\\n\'\n'
        'printf \'%s\' "$ARTICLE_LAST_MESSAGE" >"$ARTICLE_CODEX_LAST_MESSAGE_FILE"\n',
        encoding="utf-8",
    )
    path.chmod(0o755)
    return path


LAST_MESSAGE = json.dumps({
    "changed_paths": ["skills/writer-agent/scripts/publish.py"],
    "rationale": "normalise the body before the publisher sees it",
    "sources_used": [],
    "regression_test_path": "skills/writer-agent/tests/test_repair_regression.py",
    "complete": True,
    "remaining_work": None,
})


def _environment(fake_codex: Path, capture: Path) -> dict[str, str]:
    environment = os.environ.copy()
    environment.update({
        "ARTICLE_PROVIDER": "codex",
        "ARTICLE_CODEX_BIN": str(fake_codex),
        "ARTICLE_CAPTURE_ARGS": str(capture),
        "ARTICLE_LAST_MESSAGE": LAST_MESSAGE,
    })
    return environment


# A registry shaped like the shipped one but naming a host that exists only
# inside these tests.  It is here because the channel now refuses a handoff it
# could read nothing from -- `test_writer_repair_verdict_sources.py` owns that
# contract -- and every test in this file needs one readable document before it
# can reach the behaviour it is actually asserting.  No network is touched:
# `_offline_get` is injected in place of the real HTTPS getter.
TEST_REGISTRY = {
    "schema": "writer.self-heal.repair-source-registry",
    "version": 1,
    "destinations": {
        "note/ja": {
            "sources": [{
                "url": "https://terms.example.invalid/terms",
                "title": "note ご利用規約", "role": "binding-contract",
            }],
        },
    },
}


def _offline_get(url: str, *, timeout: int, max_bytes: int) -> dict:
    return {"http_status": 200, "content_type": "text/html", "body": b"terms"}


def _prepare(
    repo: Path, tmp_path: Path, verdict_checkpoint: Path, *,
    test_commands: list[list[str]] | None = None,
    source_urls: list[str] | None = None,
) -> dict:
    return candidate.prepare(
        repo=repo,
        base_ref="main",
        repair_root=tmp_path / "repairs",
        state_root=tmp_path / "state",
        fingerprint=FINGERPRINT,
        observed_at=OBSERVED_AT,
        destination="note/ja",
        source_urls=source_urls or [],
        source_registry=TEST_REGISTRY,
        getter=_offline_get,
        test_commands=test_commands,
    )


# ---------------------------------------------------------------------------
# RED 1 — a failing candidate can never become eligible
# ---------------------------------------------------------------------------

def test_a_candidate_that_fails_its_tests_is_discarded_and_cannot_be_registered(
    repo: Path, tmp_path: Path, verdict_checkpoint: Path,
) -> None:
    plan = _prepare(
        repo, tmp_path, verdict_checkpoint,
        test_commands=[["false"]],
    )
    fake = _fake_codex(
        tmp_path / "codex",
        'printf "BODY = %s\\n" "\'broken\'" '
        '>"$ARTICLE_REPAIR_WORKSPACE/skills/writer-agent/scripts/publish.py"\n',
    )
    receipt = candidate.execute(
        plan=plan,
        model_runner=RUNNER,
        observed_at=OBSERVED_AT,
        budget_seconds=120,
        environment=_environment(fake, tmp_path / "args.txt"),
    )

    assert receipt["status"] == "DISCARDED"
    assert receipt["decision"] == "DISCARD"
    assert receipt["failed_check"] == "test_gate"
    assert receipt["test_results"][0]["exit_code"] != 0
    assert "feature_commit" not in receipt

    queue = {
        "schema": incidents.SCHEMA, "version": 1,
        "items": {FINGERPRINT: {
            "fingerprint": FINGERPRINT, "state": "CLAIMED", "lease_id": "lease-1",
        }},
    }
    with pytest.raises(ValueError):
        incidents.register_candidate(
            queue, FINGERPRINT, "lease-1", Path(receipt["receipt_path"]), OBSERVED_AT,
        )


# ---------------------------------------------------------------------------
# RED 2 — a write outside the workspace is impossible, and detected if attempted
# ---------------------------------------------------------------------------

def test_repair_mode_command_line_carries_the_proven_sandbox_profile(
    tmp_path: Path,
) -> None:
    """The mode that can write is the mode that is caged. Measured 2026-08-07:
    workspace-write alone still permits writes to /tmp and $TMPDIR."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    capture = tmp_path / "args.txt"
    fake = _fake_codex(tmp_path / "codex", "")
    prompt = tmp_path / "prompt.txt"
    prompt.write_text("probe", encoding="utf-8")

    environment = os.environ.copy()
    environment.update({
        "ARTICLE_PROVIDER": "codex",
        "ARTICLE_CODEX_BIN": str(fake),
        "ARTICLE_MODEL_ROOT": str(tmp_path / "model-root"),
        "ARTICLE_MODEL_STATE_ROOT": str(tmp_path / "state"),
        "ARTICLE_PROVIDER_HEALTH": str(tmp_path / "health.json"),
        "ARTICLE_MODEL_LOG": str(tmp_path / "model.log"),
        "ARTICLE_REPAIR_WORKSPACE": str(workspace),
        "ARTICLE_CODEX_EVENTS_FILE": str(tmp_path / "events.jsonl"),
        "ARTICLE_CODEX_LAST_MESSAGE_FILE": str(tmp_path / "last.txt"),
        "ARTICLE_CAPTURE_ARGS": str(capture),
        "ARTICLE_LAST_MESSAGE": "{}",
    })
    result = subprocess.run(
        [str(RUNNER), "repair", "--prompt-file", str(prompt)],
        env=environment, text=True, capture_output=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    args = capture.read_text(encoding="utf-8").splitlines()

    assert args[args.index("--sandbox") + 1] == "workspace-write"
    assert "danger-full-access" not in args
    assert args[args.index("-C") + 1] == str(workspace)
    assert "sandbox_workspace_write.exclude_slash_tmp=true" in args
    assert "sandbox_workspace_write.exclude_tmpdir_env_var=true" in args
    assert "sandbox_workspace_write.network_access=false" in args
    assert "--ignore-user-config" in args
    assert "--add-dir" not in args
    # write capability and the machine-readable stream are one mode, inseparable
    assert "--json" in args
    assert args[args.index("-o") + 1] == str(tmp_path / "last.txt")


def test_repair_mode_refuses_to_run_without_a_workspace_or_an_event_stream(
    tmp_path: Path,
) -> None:
    fake = _fake_codex(tmp_path / "codex", "")
    prompt = tmp_path / "prompt.txt"
    prompt.write_text("probe", encoding="utf-8")
    capture = tmp_path / "args.txt"
    base = os.environ.copy()
    base.update({
        "ARTICLE_PROVIDER": "codex",
        "ARTICLE_CODEX_BIN": str(fake),
        "ARTICLE_MODEL_ROOT": str(tmp_path / "model-root"),
        "ARTICLE_MODEL_STATE_ROOT": str(tmp_path / "state"),
        "ARTICLE_PROVIDER_HEALTH": str(tmp_path / "health.json"),
        "ARTICLE_MODEL_LOG": str(tmp_path / "model.log"),
        "ARTICLE_CAPTURE_ARGS": str(capture),
        "ARTICLE_LAST_MESSAGE": "{}",
    })
    for missing in ("ARTICLE_REPAIR_WORKSPACE", "ARTICLE_CODEX_EVENTS_FILE"):
        environment = dict(base)
        environment["ARTICLE_REPAIR_WORKSPACE"] = str(tmp_path)
        environment["ARTICLE_CODEX_EVENTS_FILE"] = str(tmp_path / "events.jsonl")
        environment["ARTICLE_CODEX_LAST_MESSAGE_FILE"] = str(tmp_path / "last.txt")
        environment.pop(missing)
        result = subprocess.run(
            [str(RUNNER), "repair", "--prompt-file", str(prompt)],
            env=environment, text=True, capture_output=True, check=False,
        )
        assert result.returncode == 64, (missing, result.stdout, result.stderr)
        assert not capture.exists(), missing


def test_a_write_outside_the_workspace_is_detected_and_discards_the_candidate(
    repo: Path, tmp_path: Path, verdict_checkpoint: Path,
) -> None:
    """The sandbox prevents it; this proves the channel also *detects* it, so a
    profile regression cannot silently produce an eligible candidate."""
    plan = _prepare(repo, tmp_path, verdict_checkpoint, test_commands=[["true"]])
    outside = repo / "skills" / "writer-agent" / "scripts" / "publish.py"
    fake = _fake_codex(
        tmp_path / "codex",
        f'printf "BODY = %s\\n" "\'leaked\'" >"{outside}"\n',
    )
    receipt = candidate.execute(
        plan=plan, model_runner=RUNNER, observed_at=OBSERVED_AT,
        budget_seconds=120,
        environment=_environment(fake, tmp_path / "args.txt"),
    )
    assert receipt["status"] == "DISCARDED"
    assert receipt["failed_check"] == "workspace_boundary"
    assert receipt["workspace_boundary"]["source_repo_clean"] is False


# ---------------------------------------------------------------------------
# RED 3 — external-effect prohibitions live in code
# ---------------------------------------------------------------------------

def test_the_model_child_environment_carries_no_credential_material() -> None:
    polluted = {
        "PATH": "/usr/bin", "HOME": "/home/x", "LANG": "C",
        "ARTICLE_MODEL_ROOT": "/root", "ARTICLE_SOL_TRIGGER_RECEIPT": "/r.json",
        "NOTE_SESSION_COOKIE": "abc", "OPENAI_API_KEY": "sk-live",
        "GITHUB_TOKEN": "ghp_x", "AWS_SECRET_ACCESS_KEY": "y",
        "TELEGRAM_BOT_TOKEN": "z", "SOMETHING_PASSWORD": "p",
    }
    scrubbed = candidate.child_environment(polluted)
    assert scrubbed["PATH"] == "/usr/bin"
    assert scrubbed["ARTICLE_MODEL_ROOT"] == "/root"
    for forbidden in (
        "NOTE_SESSION_COOKIE", "OPENAI_API_KEY", "GITHUB_TOKEN",
        "AWS_SECRET_ACCESS_KEY", "TELEGRAM_BOT_TOKEN", "SOMETHING_PASSWORD",
        "ARTICLE_SOL_TRIGGER_RECEIPT",
    ):
        assert forbidden not in scrubbed


def test_a_repair_attempt_never_logs_or_records_health_into_the_live_state_tree(
    repo: Path, tmp_path: Path, verdict_checkpoint: Path,
) -> None:
    """Regression, observed for real on 2026-08-07: with these unset, the model
    runner defaults to `$HOME/profitable-claude/skills/writer-agent/state`, so a
    repair attempt appended to the live `model-runner.log` and created a
    `codex:repair` entry in the live `provider-health.json`. An isolated
    workspace is not isolation if the run still writes to live state."""
    plan = _prepare(repo, tmp_path, verdict_checkpoint, test_commands=[["true"]])
    fake = _fake_codex(
        tmp_path / "codex",
        'printf "BODY = %s\\n" "\'repaired\'" '
        '>"$ARTICLE_REPAIR_WORKSPACE/skills/writer-agent/scripts/publish.py"\n'
        'printf "%s\\n" "$ARTICLE_MODEL_LOG" >"$ARTICLE_CAPTURE_ARGS.log-path"\n'
        'printf "%s\\n" "$ARTICLE_PROVIDER_HEALTH" >"$ARTICLE_CAPTURE_ARGS.health-path"\n',
    )
    environment = _environment(fake, tmp_path / "args.txt")
    for key in (
        "ARTICLE_MODEL_LOG", "ARTICLE_PROVIDER_HEALTH",
        "ARTICLE_MODEL_STATE_ROOT", "ARTICLE_MODEL_ROOT",
    ):
        environment.pop(key, None)
    candidate.execute(
        plan=plan, model_runner=RUNNER, observed_at=OBSERVED_AT,
        budget_seconds=120, environment=environment,
    )
    state_root = str(tmp_path / "state")
    log_path = (tmp_path / "args.txt.log-path").read_text(encoding="utf-8").strip()
    health_path = (tmp_path / "args.txt.health-path").read_text(encoding="utf-8").strip()
    assert log_path.startswith(state_root), log_path
    assert health_path.startswith(state_root), health_path
    live_default = str(Path.home() / "profitable-claude" / "skills" / "writer-agent")
    assert not log_path.startswith(live_default), log_path
    assert not health_path.startswith(live_default), health_path


def test_source_fetching_is_get_only_https_only_and_refuses_private_hosts(
    tmp_path: Path,
) -> None:
    for url in (
        "http://note.com/terms",
        "file:///etc/passwd",
        "https://user:pw@note.com/terms",
        "https://127.0.0.1/terms",
        "https://localhost/terms",
        "https://192.168.0.5/terms",
    ):
        with pytest.raises(ValueError):
            candidate.assert_fetchable(url)
    candidate.assert_fetchable("https://note.com/terms")


def test_the_repair_channel_never_runs_a_publishing_or_pushing_git_command(
    repo: Path, tmp_path: Path, verdict_checkpoint: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every git invocation the channel makes is recorded by a shim on PATH.

    The shim is installed into the real process environment, because the
    channel's own git calls inherit it; a PATH passed only to the model child
    would prove nothing about the executor.
    """
    shim_dir = tmp_path / "bin"
    shim_dir.mkdir()
    log = tmp_path / "git-argv.txt"
    real_git_bin = subprocess.run(
        ["/usr/bin/env", "which", "git"], capture_output=True, text=True, check=True,
    ).stdout.strip()
    shim = shim_dir / "git"
    shim.write_text(
        "#!/usr/bin/env bash\n"
        f'printf "%s\\n" "$*" >>"{log}"\n'
        f'exec "{real_git_bin}" "$@"\n',
        encoding="utf-8",
    )
    shim.chmod(0o755)
    monkeypatch.setenv("PATH", f"{shim_dir}{os.pathsep}{os.environ['PATH']}")

    plan = _prepare(repo, tmp_path, verdict_checkpoint, test_commands=[["true"]])
    fake = _fake_codex(
        tmp_path / "codex",
        'printf "BODY = %s\\n" "\'repaired\'" '
        '>"$ARTICLE_REPAIR_WORKSPACE/skills/writer-agent/scripts/publish.py"\n',
    )
    receipt = candidate.execute(
        plan=plan, model_runner=RUNNER, observed_at=OBSERVED_AT,
        budget_seconds=120,
        environment=_environment(fake, tmp_path / "args.txt"),
    )
    assert receipt["status"] == "CANDIDATE_VERIFIED"
    recorded = log.read_text(encoding="utf-8") if log.is_file() else ""
    assert recorded, "the shim recorded nothing, so this test proves nothing"
    for forbidden in ("push", "remote", "fetch", "pull", "submodule"):
        assert forbidden not in recorded, recorded


def test_prepare_refuses_a_protected_branch_as_the_candidate_branch(
    repo: Path, tmp_path: Path, verdict_checkpoint: Path,
) -> None:
    with pytest.raises(ValueError):
        candidate.assert_unprotected_branch("main")
    with pytest.raises(ValueError):
        candidate.assert_unprotected_branch("dev")
    candidate.assert_unprotected_branch(f"repair/writer-{FINGERPRINT[:12]}-candidate")


def test_secret_material_in_a_change_discards_the_candidate(
    repo: Path, tmp_path: Path, verdict_checkpoint: Path,
) -> None:
    plan = _prepare(repo, tmp_path, verdict_checkpoint, test_commands=[["true"]])
    leak = "sk-" + "A" * 40
    fake = _fake_codex(
        tmp_path / "codex",
        f'printf "TOKEN = %s\\n" "{leak}" '
        '>"$ARTICLE_REPAIR_WORKSPACE/skills/writer-agent/scripts/publish.py"\n',
    )
    receipt = candidate.execute(
        plan=plan, model_runner=RUNNER, observed_at=OBSERVED_AT,
        budget_seconds=120,
        environment=_environment(fake, tmp_path / "args.txt"),
    )
    assert receipt["status"] == "DISCARDED"
    assert receipt["failed_check"] == "secret_scan"
    # the receipt names the rule and the file, never the matched material
    assert leak not in json.dumps(receipt)


# ---------------------------------------------------------------------------
# GREEN path — a verified candidate plus its receipt
# ---------------------------------------------------------------------------

def test_a_green_candidate_produces_a_receipt_the_incident_queue_accepts(
    repo: Path, tmp_path: Path, verdict_checkpoint: Path,
) -> None:
    plan = _prepare(repo, tmp_path, verdict_checkpoint, test_commands=[["true"]])
    fake = _fake_codex(
        tmp_path / "codex",
        'printf "BODY = %s\\n" "\'repaired\'" '
        '>"$ARTICLE_REPAIR_WORKSPACE/skills/writer-agent/scripts/publish.py"\n'
        'printf "def test_ok():\\n    assert True\\n" '
        '>"$ARTICLE_REPAIR_WORKSPACE/skills/writer-agent/tests/test_repair_regression.py"\n',
    )
    receipt = candidate.execute(
        plan=plan, model_runner=RUNNER, observed_at=OBSERVED_AT,
        budget_seconds=120,
        environment=_environment(fake, tmp_path / "args.txt"),
    )

    assert receipt["schema"] == "writer.self-heal.candidate-verification-receipt"
    assert receipt["status"] == "CANDIDATE_VERIFIED"
    assert receipt["decision"] == "ELIGIBLE_FOR_ISOLATED_FIXTURE_VERIFICATION"
    assert receipt["fingerprint"] == FINGERPRINT
    assert len(receipt["feature_commit"]) == 40
    assert receipt["invariants"] == {
        "draft_is_public": False, "incident_resolved": False, "deployed": False,
    }
    assert receipt["next_action"] == "VERIFY_SENSITIVE_REPAIR_IN_ISOLATED_FIXTURE"
    paths = {artifact["path"] for artifact in receipt["artifacts"]}
    assert "skills/writer-agent/scripts/publish.py" in paths
    assert all(path.startswith("skills/writer-agent/") for path in paths)
    # the verdict it acted on, and the diff it proposes
    assert receipt["verdict"]["cause_status"] == "UNDETERMINED"
    assert "original" in receipt["diff"] and "repaired" in receipt["diff"]
    # tokens and latency: measured, or unknown with a reason -- never a fake zero
    assert receipt["tokens"]["status"] == "measured"
    assert isinstance(receipt["latency_ms"]["model"], int)
    assert receipt["test_results"][0]["exit_code"] == 0
    # the live tree is untouched by construction: nothing was pushed or deployed
    assert receipt["deployed"] is False

    queue = {
        "schema": incidents.SCHEMA, "version": 1,
        "items": {FINGERPRINT: {
            "fingerprint": FINGERPRINT, "state": "CLAIMED", "lease_id": "lease-1",
        }},
    }
    result = incidents.register_candidate(
        queue, FINGERPRINT, "lease-1", Path(receipt["receipt_path"]), OBSERVED_AT,
    )
    assert result["next_action"] == "VERIFY_SENSITIVE_REPAIR_IN_ISOLATED_FIXTURE"


def test_the_default_test_gate_runs_the_real_writer_regression_suite() -> None:
    flattened = [" ".join(command) for command in candidate.DEFAULT_TEST_COMMANDS]
    assert any(
        "pytest" in command and "skills/writer-agent/tests" in command
        for command in flattened
    ), flattened


# ---------------------------------------------------------------------------
# bound, degrade, and re-arm
# ---------------------------------------------------------------------------

def test_attempts_are_bounded_then_degrade_and_stop_until_a_new_trigger(
    repo: Path, tmp_path: Path, verdict_checkpoint: Path,
) -> None:
    fake = _fake_codex(
        tmp_path / "codex",
        'printf "BODY = %s\\n" "\'broken\'" '
        '>"$ARTICLE_REPAIR_WORKSPACE/skills/writer-agent/scripts/publish.py"\n',
    )
    calls = tmp_path / "args.txt"
    for attempt in range(1, candidate.DEFAULT_MAX_CANDIDATE_ATTEMPTS + 1):
        plan = _prepare(repo, tmp_path, verdict_checkpoint, test_commands=[["false"]])
        receipt = candidate.execute(
            plan=plan, model_runner=RUNNER, observed_at=OBSERVED_AT,
            budget_seconds=120,
            environment=_environment(fake, calls),
        )
        assert receipt["status"] == "DISCARDED", attempt
        assert receipt["attempt"] == attempt

    calls_before = calls.read_text(encoding="utf-8")
    plan = _prepare(repo, tmp_path, verdict_checkpoint, test_commands=[["false"]])
    assert plan["status"] == "EXHAUSTED"
    assert candidate.DEFAULT_MAX_CANDIDATE_ATTEMPTS == plan["attempts_used"]
    assert "degrade" in plan["reason"] or "safest" in plan["reason"]
    # degrading must not spend another model call
    assert calls.read_text(encoding="utf-8") == calls_before

    # a genuinely new trigger -- here a new deployed code version -- re-arms it
    (tmp_path / "state" / "deployed-commit").write_text("b" * 40, encoding="utf-8")
    rearmed = _prepare(repo, tmp_path, verdict_checkpoint, test_commands=[["false"]])
    assert rearmed["status"] == "READY_TO_REPAIR"
    assert rearmed["attempts_used"] == 0


# ---------------------------------------------------------------------------
# primary sources
# ---------------------------------------------------------------------------

def test_fetched_sources_are_recorded_with_url_retrieval_time_and_hash(
    repo: Path, tmp_path: Path, verdict_checkpoint: Path,
) -> None:
    body = b"note terms of service"
    served = {"url": "https://note.example/terms", "body": body}

    def fake_get(url: str, *, timeout: int, max_bytes: int) -> dict:
        assert url == served["url"]
        return {
            "http_status": 200, "content_type": "text/html",
            "body": served["body"],
        }

    receipts = candidate.fetch_sources(
        [served["url"]], tmp_path / "sources", observed_at=OBSERVED_AT,
        getter=fake_get,
    )
    assert len(receipts) == 1
    row = receipts[0]
    assert row["status"] == "FETCHED"
    assert row["url"] == served["url"]
    assert row["fetched_at"] == OBSERVED_AT
    assert row["sha256"] == hashlib.sha256(body).hexdigest()
    assert Path(row["path"]).read_bytes() == body


def test_the_verdicts_own_primary_sources_are_what_gets_fetched(
    repo: Path, tmp_path: Path, verdict_checkpoint: Path,
) -> None:
    """The investigation could cite zero official documents because it had no
    network. Whatever it did name is exactly what this stage must fetch."""
    checkpoint = json.loads(verdict_checkpoint.read_text(encoding="utf-8"))
    checkpoint["verdict"]["primary_sources"] = [
        {"url": "https://note.example/terms", "title": "terms", "quote": ""},
    ]
    verdict_checkpoint.write_text(
        json.dumps(checkpoint, ensure_ascii=False), encoding="utf-8",
    )
    seen: list[str] = []

    def fake_get(url: str, *, timeout: int, max_bytes: int) -> dict:
        seen.append(url)
        return {"http_status": 200, "content_type": "text/html", "body": b"terms"}

    plan = candidate.prepare(
        repo=repo, base_ref="main", repair_root=tmp_path / "repairs",
        state_root=tmp_path / "state", fingerprint=FINGERPRINT,
        observed_at=OBSERVED_AT, test_commands=[["true"]], getter=fake_get,
    )
    assert seen == ["https://note.example/terms"]
    assert plan["sources"][0]["status"] == "FETCHED"
    assert plan["sources"][0]["sha256"] == hashlib.sha256(b"terms").hexdigest()
    # the prompt hands the model the URL and the hash, not a summary of them
    prompt = Path(plan["prompt_path"]).read_text(encoding="utf-8")
    assert "https://note.example/terms" in prompt
    assert plan["sources"][0]["sha256"] in prompt


def test_a_crashed_attempt_still_costs_a_slot_so_the_bound_fails_closed(
    repo: Path, tmp_path: Path, verdict_checkpoint: Path,
) -> None:
    """Prepared-but-never-executed must not be a free retry, or a repeatedly
    crashing attempt loops forever inside a bound that never advances."""
    for expected in (1, 2, 3):
        plan = _prepare(repo, tmp_path, verdict_checkpoint, test_commands=[["true"]])
        assert plan["attempt"] == expected
        # deliberately never execute
    exhausted = _prepare(repo, tmp_path, verdict_checkpoint, test_commands=[["true"]])
    assert exhausted["status"] == "EXHAUSTED"


def test_an_unfetchable_source_is_recorded_as_unfetched_never_invented(
    tmp_path: Path,
) -> None:
    def failing_get(url: str, *, timeout: int, max_bytes: int) -> dict:
        raise OSError("Name or service not known")

    receipts = candidate.fetch_sources(
        ["https://note.example/terms"], tmp_path / "sources",
        observed_at=OBSERVED_AT, getter=failing_get,
    )
    assert receipts[0]["status"] == "UNFETCHED"
    assert "Name or service not known" in receipts[0]["reason"]
    assert "sha256" not in receipts[0]
