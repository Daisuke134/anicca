#!/usr/bin/env python3
"""Executable contract: an investigation verdict must hand over fetchable sources.

SSOT §9.3.1 rows H2 and H3.  The first completed `note/ja` investigation reached
`status COMPLETE`, `verdict.complete true`, `cause_status UNDETERMINED`,
`primary_sources []` and a `remaining_work` containing no URL at all.  Measured
in live state on 2026-08-07:

    state/self-heal/investigation-sessions/b4968e8b….json
      .verdict.primary_sources == []
      .verdict.complete        == true
      .verdict.cause_status    == "UNDETERMINED"

The H2 repair channel's only egress is `fetch_sources`, which takes explicit
URLs.  Handed that verdict, the first production repair would fetch zero
documents, produce no evidence-backed change, be discarded by the test gate, and
burn all three bounded attempts before degrading.  That is the "ran but did no
work" signature H1 exists to catch, arriving one organ earlier.

Three properties are asserted here:

* a verdict that names no resolvable source is **not** an actionable handoff --
  `complete` describes the investigation's own budget, not the repair channel's
  ability to act;
* refusing such a handoff costs **zero** candidate attempts and leaves **no**
  workspace, so the bounded budget is still there when sources exist;
* a fabricated or unreachable source is **visibly absent** -- it appears as an
  `UNFETCHED` row with its reason and never as evidence.

Every test runs against a throwaway git repository, a throwaway state root and
an injected `getter`.  No live state, no live tree and no network are touched;
the one test that reads the shipped registry reads it as data.
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
RUNNER = ROOT / "runtime" / "model-runner.sh"
REGISTRY = ROOT / "config" / "repair-source-registry.json"


def _module(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


candidate = _module("writer_repair_candidate")
wiring = _module("writer_repair_candidate_dispatch")
incidents = _module("writer_incident_queue")

FINGERPRINT = "b4" + "9" * 62
LEASE = "repair-13fb88fe834b462a91400ee97449befb"
OBSERVED_AT = "2026-08-07T12:00:00Z"
DESTINATION = "note/ja"

SHA256_RE = re.compile(r"[0-9a-f]{64}")

# A registry shaped like the shipped one but pointing at hosts that exist only
# inside this test, so resolution is exercised without any network.
TEST_REGISTRY = {
    "schema": "writer.self-heal.repair-source-registry",
    "version": 1,
    "destinations": {
        DESTINATION: {
            "sources": [
                {
                    "url": "https://terms.example.invalid/terms",
                    "title": "note ご利用規約",
                    "role": "binding-contract",
                },
            ],
        },
    },
}


# ---------------------------------------------------------------------------
# fixtures
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


def _write_investigation(
    state_root: Path, *, primary_sources: list[dict] | None = None,
) -> Path:
    """The live `note/ja` checkpoint shape, byte-for-byte in the parts that matter."""
    sessions = state_root / "self-heal" / "investigation-sessions"
    sessions.mkdir(parents=True, exist_ok=True)
    path = sessions / f"{FINGERPRINT}.json"
    path.write_text(
        json.dumps({
            "schema": "writer.self-heal.investigation-session",
            "version": 1,
            "fingerprint": FINGERPRINT,
            "status": "COMPLETE",
            "slice_count": 1,
            "max_slices": 3,
            "trigger": {"occurrence_count": 1, "deployed_commit": "a" * 40},
            "verdict": {
                "cause_status": "UNDETERMINED",
                "complete": True,
                "evidence_gaps": [
                    "browser_evidence_missing",
                    "official_primary_document_research_required",
                ],
                "findings": [],
                "primary_sources": primary_sources or [],
                "remaining_work": (
                    "外部取得可能な環境で、noteが現行で公式公開する「利用規約」、"
                    "投稿コンテンツの禁止・制限を定めるポリシーを原文取得する。"
                ),
            },
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def _serving(bodies: dict[str, bytes]) -> object:
    def getter(url: str, *, timeout: int, max_bytes: int) -> dict:
        if url not in bodies:
            raise OSError(f"Name or service not known: {url}")
        return {
            "http_status": 200, "content_type": "text/html", "body": bodies[url],
        }
    return getter


def _prepare(repo: Path, tmp_path: Path, **overrides):
    arguments = dict(
        repo=repo, base_ref="main", repair_root=tmp_path / "repairs",
        state_root=tmp_path / "state", fingerprint=FINGERPRINT,
        observed_at=OBSERVED_AT, destination=DESTINATION,
        source_registry=TEST_REGISTRY, test_commands=[["true"]],
    )
    arguments.update(overrides)
    return candidate.prepare(**arguments)


# ---------------------------------------------------------------------------
# RED 1 -- a verdict naming no resolvable source is not a complete handoff
# ---------------------------------------------------------------------------

def test_a_complete_verdict_naming_no_resolvable_source_is_not_an_actionable_handoff(
    repo: Path, tmp_path: Path,
) -> None:
    """`verdict.complete` is the investigation's budget, not a licence to repair.

    This is the live shape exactly: COMPLETE, complete true, UNDETERMINED, zero
    primary sources, and -- here -- no registry entry for the destination either.
    Nothing on disk can tell the repair channel what to fetch, so the handoff is
    refused by name rather than accepted and spent.
    """
    _write_investigation(tmp_path / "state")
    with pytest.raises(candidate.UnresolvableSourcesError) as raised:
        _prepare(repo, tmp_path, source_registry={"destinations": {}})
    message = str(raised.value)
    assert "primary_sources" in message
    assert DESTINATION in message


def test_a_verdict_with_no_sources_is_reported_unactionable_rather_than_complete(
    tmp_path: Path,
) -> None:
    """The distinction is named in code, not left implicit in a raise."""
    verdict = {
        "cause_status": "UNDETERMINED", "complete": True,
        "evidence_gaps": [], "findings": [], "primary_sources": [],
        "remaining_work": "fetch note's terms",
    }
    assert candidate.handoff_status(verdict, []) == candidate.HANDOFF_NO_SOURCES
    resolved = [{"url": "https://x.example.invalid/a", "provenance": "registry"}]
    assert candidate.handoff_status(verdict, resolved) == candidate.HANDOFF_ACTIONABLE


# ---------------------------------------------------------------------------
# RED 2 -- refusing an empty source set costs no attempt and leaves no workspace
# ---------------------------------------------------------------------------

def test_an_empty_source_set_consumes_no_candidate_attempt_and_leaves_no_workspace(
    repo: Path, tmp_path: Path,
) -> None:
    """Three refusals must not spend the three attempts a real repair needs.

    The measured hazard: with a zero-source verdict the channel would run the
    model three times, be discarded three times, and degrade -- after which a
    correct verdict could no longer be repaired under the same trigger.
    """
    _write_investigation(tmp_path / "state")
    for _ in range(3):
        with pytest.raises(candidate.UnresolvableSourcesError):
            _prepare(repo, tmp_path, source_registry={"destinations": {}})

    checkpoint = candidate.read_checkpoint(tmp_path / "state", FINGERPRINT)
    assert checkpoint is None or int(checkpoint.get("attempts", 0)) == 0
    assert not list((tmp_path / "repairs").glob("*")), "a refused handoff left a workspace"
    assert _git(repo, "worktree", "list").count("\n") == 0, "a refused handoff left a worktree"
    assert _git(repo, "branch", "--list", "repair/*") == ""

    # and the budget is intact the moment a source does exist
    plan = _prepare(
        repo, tmp_path,
        getter=_serving({"https://terms.example.invalid/terms": b"terms"}),
    )
    assert plan["status"] == "READY_TO_REPAIR"
    assert plan["attempt"] == 1
    assert plan["attempts_used"] == 0


# ---------------------------------------------------------------------------
# RED 3 -- fabricated or unreachable sources are visibly absent
# ---------------------------------------------------------------------------

def test_a_verdict_of_purely_fabricated_urls_is_refused_not_silently_accepted(
    repo: Path, tmp_path: Path,
) -> None:
    """An invented citation must be worse for the model than an absent one.

    Every named URL fails to resolve, so nothing was read; the channel refuses
    instead of running a repair whose only "evidence" is a list of URLs.
    """
    _write_investigation(tmp_path / "state", primary_sources=[
        {"url": "https://note.example.invalid/official-422-spec",
         "title": "invented", "quote": "invented"},
    ])
    with pytest.raises(candidate.UnresolvableSourcesError) as raised:
        _prepare(
            repo, tmp_path, source_registry={"destinations": {}},
            getter=_serving({}),
        )
    resolution = raised.value.resolution
    assert [row["status"] for row in resolution] == ["UNFETCHED"]
    assert "Name or service not known" in resolution[0]["reason"]
    assert "sha256" not in resolution[0]


def test_an_unreachable_source_is_carried_as_unfetched_beside_the_ones_that_arrived(
    repo: Path, tmp_path: Path,
) -> None:
    """Partial truth is kept legible: what arrived, what did not, and why."""
    _write_investigation(tmp_path / "state", primary_sources=[
        {"url": "https://note.example.invalid/dead", "title": "dead", "quote": ""},
    ])
    plan = _prepare(
        repo, tmp_path,
        getter=_serving({"https://terms.example.invalid/terms": b"terms"}),
    )
    by_url = {row["url"]: row for row in plan["sources"]}
    assert by_url["https://note.example.invalid/dead"]["status"] == "UNFETCHED"
    assert by_url["https://terms.example.invalid/terms"]["status"] == "FETCHED"
    prompt = Path(plan["prompt_path"]).read_text(encoding="utf-8")
    assert "UNFETCHED" in prompt, "the model must see which document never arrived"
    assert "https://note.example.invalid/dead" in prompt


# ---------------------------------------------------------------------------
# RED 4 -- the registry resolves what the verdict could not name
# ---------------------------------------------------------------------------

def test_the_registry_supplies_sources_for_the_destination_when_the_verdict_names_none(
    repo: Path, tmp_path: Path,
) -> None:
    """No model is asked to recall a URL; the destination maps to curated ones."""
    _write_investigation(tmp_path / "state")
    plan = _prepare(
        repo, tmp_path,
        getter=_serving({"https://terms.example.invalid/terms": b"note terms"}),
    )
    assert [row["url"] for row in plan["sources"]] == [
        "https://terms.example.invalid/terms",
    ]
    assert plan["sources"][0]["status"] == "FETCHED"
    assert plan["sources"][0]["provenance"] == f"registry:{DESTINATION}"
    assert plan["handoff"]["status"] == candidate.HANDOFF_ACTIONABLE
    assert plan["handoff"]["fetched"] == 1


def test_a_source_the_verdict_actually_read_is_preferred_over_the_registry(
    repo: Path, tmp_path: Path,
) -> None:
    """A verdict source carries a quote, so it was read; it leads, and the
    curated documents follow it rather than replacing it."""
    _write_investigation(tmp_path / "state", primary_sources=[
        {"url": "https://note.example.invalid/read",
         "title": "read", "quote": "本文に利用できない内容"},
    ])
    plan = _prepare(repo, tmp_path, getter=_serving({
        "https://note.example.invalid/read": b"read",
        "https://terms.example.invalid/terms": b"terms",
    }))
    assert [row["url"] for row in plan["sources"]] == [
        "https://note.example.invalid/read",
        "https://terms.example.invalid/terms",
    ]
    assert plan["sources"][0]["provenance"] == "verdict"
    assert plan["sources"][1]["provenance"] == f"registry:{DESTINATION}"


def test_registry_sources_are_deduplicated_against_the_verdicts_own(
    repo: Path, tmp_path: Path,
) -> None:
    _write_investigation(tmp_path / "state", primary_sources=[
        {"url": "https://terms.example.invalid/terms", "title": "t", "quote": "q"},
    ])
    plan = _prepare(
        repo, tmp_path,
        getter=_serving({"https://terms.example.invalid/terms": b"terms"}),
    )
    assert [row["url"] for row in plan["sources"]] == [
        "https://terms.example.invalid/terms",
    ]
    assert plan["sources"][0]["provenance"] == "verdict"


# ---------------------------------------------------------------------------
# RED 5 -- the shipped registry is curated evidence, not recalled text
# ---------------------------------------------------------------------------

def test_the_shipped_registry_carries_fetch_evidence_for_every_entry() -> None:
    """Every URL in the registry was fetched during curation, through the same
    guard the channel uses at run time.  An entry without a status and a content
    hash is a recalled URL, and a recalled URL is exactly what this file exists
    to prevent."""
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    assert registry["schema"] == candidate.REGISTRY_SCHEMA
    assert registry["version"] == 1
    assert DESTINATION in registry["destinations"]

    for destination, entry in registry["destinations"].items():
        assert entry["sources"], f"{destination} has no sources"
        for source in entry["sources"]:
            url = source["url"]
            assert url.startswith("https://"), url
            # the run-time SSRF guard must accept every curated URL
            assert candidate.assert_fetchable(url) == url
            verified = source["verified"]
            assert verified["http_status"] == 200, url
            assert SHA256_RE.fullmatch(verified["sha256"]), url
            assert isinstance(verified["bytes"], int) and verified["bytes"] > 0
            assert verified["fetched_at"]
            assert source["title"] and source["role"]


def test_the_shipped_registry_records_the_candidate_it_rejected() -> None:
    """`https://note.com/guideline` returns HTTP 200 and is not note's guideline;
    it is a user page titled `GuideLine@明日のその先へ｜note`.  Measured during
    curation.  A model recalling a plausible URL would have cited it, and the
    fetch would have "succeeded".  Status alone is not evidence of identity."""
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    rejected = registry["destinations"][DESTINATION]["rejected_candidates"]
    urls = {row["url"] for row in rejected}
    assert "https://note.com/guideline" in urls
    for row in rejected:
        assert row["reason"]
        assert "url" in row


def test_the_live_destination_resolves_through_the_shipped_registry() -> None:
    """The registry is loaded from its real path by default, so production does
    not depend on a caller remembering to pass it."""
    registry = candidate.load_source_registry()
    urls = [row["url"] for row in candidate.registry_sources(registry, DESTINATION)]
    assert urls, "note/ja resolves to nothing in the shipped registry"
    assert all(url.startswith("https://") for url in urls)


def test_an_unknown_destination_resolves_to_nothing_rather_than_to_a_guess() -> None:
    registry = candidate.load_source_registry()
    assert candidate.registry_sources(registry, "medium/en") == []
    assert candidate.registry_sources(registry, None) == []


# ---------------------------------------------------------------------------
# RED 6 -- the wired dispatcher refuses without charging a candidate attempt
# ---------------------------------------------------------------------------

def _queue(state_root: Path) -> Path:
    path = state_root / "self-heal" / "incident-queue.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({
            "schema": incidents.SCHEMA, "version": 1, "updated_at": OBSERVED_AT,
            "items": {FINGERPRINT: {
                "fingerprint": FINGERPRINT, "state": "CLAIMED", "lease_id": LEASE,
                "destination": DESTINATION, "run_id": "daily-2026-08-07",
                "revenue_role": "revenue-set", "blocking": True,
                "first_seen_at": "2026-08-07T05:27:19Z", "occurrence_count": 1,
                "next_action": "COLLECT_GAPS_THEN_SEARCH_OFFICIAL_PRIMARY_DOCS",
            }},
        }, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def test_the_dispatcher_refuses_an_unactionable_verdict_under_its_existing_bound(
    repo: Path, tmp_path: Path,
) -> None:
    """No new organ: the refusal travels the preparation-failure bound that
    already exists, so it is counted, receipted, and stops after three ticks
    instead of spinning every five minutes the way routing failures once did."""
    state_root = tmp_path / "state"
    _write_investigation(state_root)
    queue_path = _queue(state_root)

    outcomes = [
        wiring.dispatch(
            state_root=state_root, repo=repo, base_ref="main",
            repair_root=tmp_path / "repairs", model_runner=RUNNER,
            observed_at=OBSERVED_AT, budget_seconds=120,
            test_commands=[["true"]],
            source_registry={"destinations": {}},
            getter=_serving({}),
        )
        for _ in range(3)
    ]
    assert [outcome["status"] for outcome in outcomes] == [
        "REPAIR_FAILED", "REPAIR_FAILED", "REPAIR_PREPARATION_EXHAUSTED",
    ]
    assert "UnresolvableSourcesError" in outcomes[0]["error"]

    # the candidate budget was never touched
    checkpoint = candidate.read_checkpoint(state_root, FINGERPRINT)
    assert checkpoint is None or int(checkpoint.get("attempts", 0)) == 0

    # and the refusal is legible in the receipt, per URL
    receipt = json.loads(
        Path(outcomes[0]["repair_attempt_receipt"]).read_text(encoding="utf-8")
    )
    assert receipt["stage"] == "PREPARE"
    assert receipt["source_resolution"]["status"] == candidate.HANDOFF_NO_SOURCES
    assert receipt["invariants"] == {
        "draft_is_public": False, "incident_resolved": False, "deployed": False,
    }

    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    assert queue["items"][FINGERPRINT].get("candidate_receipt") is None


def test_a_dispatch_with_resolvable_sources_still_reaches_the_model(
    repo: Path, tmp_path: Path,
) -> None:
    """The gate must refuse emptiness, never work."""
    state_root = tmp_path / "state"
    _write_investigation(state_root)
    _queue(state_root)
    fake = tmp_path / "codex"
    fake.write_text(
        "#!/usr/bin/env bash\nset -u\ncat >/dev/null\n"
        'printf \'{"type":"thread.started","thread_id":"probe"}\\n\'\n'
        'printf "BODY = %s\\n" "\'repaired\'" '
        '>"$ARTICLE_REPAIR_WORKSPACE/skills/writer-agent/scripts/publish.py"\n'
        'printf "def test_ok():\\n    assert True\\n" '
        '>"$ARTICLE_REPAIR_WORKSPACE/skills/writer-agent/tests/test_repair_regression.py"\n'
        'printf \'{"type":"turn.completed","usage":{"input_tokens":1,'
        '"output_tokens":1}}\\n\'\n'
        'printf \'%s\' "$ARTICLE_LAST_MESSAGE" >"$ARTICLE_CODEX_LAST_MESSAGE_FILE"\n',
        encoding="utf-8",
    )
    fake.chmod(0o755)
    import os
    environment = os.environ.copy()
    environment.update({
        "ARTICLE_PROVIDER": "codex",
        "ARTICLE_CODEX_BIN": str(fake),
        "ARTICLE_LAST_MESSAGE": json.dumps({
            "changed_paths": ["skills/writer-agent/scripts/publish.py"],
            "rationale": "curated terms named the rule",
            "sources_used": ["https://terms.example.invalid/terms"],
            "regression_test_path": "skills/writer-agent/tests/test_repair_regression.py",
            "complete": True, "remaining_work": None,
        }, ensure_ascii=False),
    })
    outcome = wiring.dispatch(
        state_root=state_root, repo=repo, base_ref="main",
        repair_root=tmp_path / "repairs", model_runner=RUNNER,
        observed_at=OBSERVED_AT, budget_seconds=120, test_commands=[["true"]],
        source_registry=TEST_REGISTRY,
        getter=_serving({"https://terms.example.invalid/terms": b"terms"}),
        environment=environment,
    )
    assert outcome["status"] == "CANDIDATE_VERIFIED", outcome
