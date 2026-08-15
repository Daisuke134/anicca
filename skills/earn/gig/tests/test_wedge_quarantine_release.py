"""§FG' item 3: release the misattributed-quarantine ids, but never blind-resubmit.

Batch semantics (review round 2, reviewer N2): proving ABSENCE requires walking the entire
applied-offers history (~450 applications ≈ 20+ pages), so per-id readback calls would
repeat the identical walk 24 times -- and with the default 10-page budget every absent id
would truncate into inconclusive and NOTHING would ever be released. release() therefore
makes ONE readback call with every at/above-threshold id in expected_ids: the walk observes
all of history as it goes, ids found are present (left quarantined), ids not found after an
EXHAUSTIVE walk (return without a truncation raise) are absent (entry dropped). Any raise
-> zero releases, file untouched.

Live-lineage adaptation (§FK'): the quarantine store is dict-form with a TTL
({"count": N, "updated_at": ts}, 48h decay, 2026-08-08). The dead tree's release script
parsed only bare-int values, so against the live file it loaded {} and released nothing --
tonight's measured no-op. The script now goes through the SAME load/save the commit
boundary uses, so dict entries parse, TTL decay applies, and surviving entries keep their
own updated_at.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
SCRIPT = SCRIPTS / "wedge_quarantine_release.py"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def build():
    release_module = _load(SCRIPT, "wedge_quarantine_release_test")
    return release_module.parent, release_module


def _store(parent, tmp_path: Path):
    return parent.fence.IntentStore(tmp_path / "intents")


def _write_counts(parent, store, entries: dict[str, int]) -> Path:
    """The live on-disk shape: dict entries with a fresh updated_at."""
    path = store.root / "wedge-quarantine.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    now = time.time()
    path.write_text(
        json.dumps({
            key: {"count": value, "updated_at": now} for key, value in entries.items()
        }),
        encoding="utf-8",
    )
    return path


class FakeBatchReadback:
    """Answers one batched readback call from a fixed observed set, or raises."""

    def __init__(self, observed=frozenset(), error: BaseException | None = None):
        self.observed = set(observed)
        self.error = error
        self.calls: list[set[str]] = []

    def __call__(self, request_ids: set[str]) -> set[str]:
        self.calls.append(set(request_ids))
        if self.error is not None:
            raise self.error
        return set(self.observed)


def test_release_parses_the_live_dict_form_store_and_resets_only_confirmed_absent_ids(
    tmp_path: Path,
) -> None:
    parent, release_module = build()
    store = _store(parent, tmp_path)
    _write_counts(parent, store, {"95000005": 3, "95000006": 3, "95000007": 2})
    readback = FakeBatchReadback(observed={"95000006", "95000017"})

    outcomes = release_module.release(readback, store, threshold=3)

    assert outcomes == {
        "95000005": "released",
        "95000006": "already_applied_left_quarantined",
        "95000007": "below_threshold_untouched",
    }
    # ONE call, carrying exactly the quarantined ids -- not one walk per id.
    assert readback.calls == [{"95000005", "95000006"}]
    counts = parent.load_wedge_counts(store)
    assert counts.get("95000005") in (None, 0)
    assert counts.get("95000006") == 3
    assert counts.get("95000007") == 2


def test_release_fails_closed_for_every_id_when_the_batched_readback_raises(tmp_path: Path) -> None:
    parent, release_module = build()
    store = _store(parent, tmp_path)
    counts_path = _write_counts(
        parent, store, {"95000008": 3, "95000009": 4, "95000010": 1}
    )
    original = counts_path.read_text(encoding="utf-8")
    readback = FakeBatchReadback(
        error=parent.ReadbackScanTimeout("official_readback_truncated_after_10_pages_next_page_remains")
    )

    outcomes = release_module.release(readback, store, threshold=3)

    assert outcomes["95000008"] == "readback_inconclusive:ReadbackScanTimeout"
    assert outcomes["95000009"] == "readback_inconclusive:ReadbackScanTimeout"
    assert outcomes["95000010"] == "below_threshold_untouched"
    # Zero releases and zero writes: byte-identical file.
    assert counts_path.read_text(encoding="utf-8") == original


def test_release_preserves_the_surviving_entries_own_updated_at(tmp_path: Path) -> None:
    """A release run must not silently refresh the TTL clock on ids it leaves quarantined:
    resetting updated_at would extend a sentence the TTL was about to end."""
    parent, release_module = build()
    store = _store(parent, tmp_path)
    counts_path = store.root / "wedge-quarantine.json"
    counts_path.parent.mkdir(parents=True, exist_ok=True)
    old_stamp = time.time() - 3600  # one hour old, well inside the 48h TTL
    counts_path.write_text(
        json.dumps({
            "95000005": {"count": 3, "updated_at": old_stamp},
            "95000006": {"count": 3, "updated_at": old_stamp},
        }),
        encoding="utf-8",
    )
    readback = FakeBatchReadback(observed={"95000006"})

    outcomes = release_module.release(readback, store, threshold=3)

    assert outcomes["95000005"] == "released"
    raw = json.loads(counts_path.read_text(encoding="utf-8"))
    assert "95000005" not in raw
    assert raw["95000006"]["count"] == 3
    assert raw["95000006"]["updated_at"] == old_stamp


def test_release_handles_a_missing_or_empty_counts_file(tmp_path: Path) -> None:
    parent, release_module = build()
    store = _store(parent, tmp_path)

    outcomes = release_module.release(FakeBatchReadback(), store, threshold=3)

    assert outcomes == {}
    assert not (store.root / "wedge-quarantine.json").exists()


def test_cli_requires_a_lease_and_exposes_a_page_budget_for_deep_histories() -> None:
    """Same lease contract as every command here (no raw --ws-url), plus --max-pages so the
    release run can cover the real ~450-application history without changing the live
    per-candidate readback default."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"], capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "--lease-script" in result.stdout
    assert "--lease-task" in result.stdout
    assert "--max-pages" in result.stdout
    assert "--ws-url" not in result.stdout


# --- End-to-end through the real paginating readback (ScanSocket fake CDP) ---------------

_fakes = _load(
    Path(__file__).with_name("test_official_readback_pagination.py"),
    "readback_pagination_fakes",
)
ScanSocket = _fakes.ScanSocket
FakeConnection = _fakes.FakeConnection

QUARANTINED = ("95000018", "95000019", "95000020")
PAGE2_URL = "https://coconala.com/mypage/job_matching/applied/offers?page=2"
PAGE3_URL = "https://coconala.com/mypage/job_matching/applied/offers?page=3"


def _page(parent, index: int, offer_ids: list[str], next_url: str | None):
    return {
        "url": parent._APPLIED_OFFERS_URL if index == 1 else (
            f"{parent._APPLIED_OFFERS_URL}?page={index}"
        ),
        "title": "応募・スカウト管理 | ココナラ",
        "offer_urls": [f"https://coconala.com/mypage/offers/{oid}" for oid in offer_ids],
        "next_href": next_url,
        "body": f"page{index}",
        "not_found": False,
    }


def _three_page_history(parent, present_id: str):
    """3 pages of history; `present_id`'s offer sits on page 2, everything else unrelated."""
    pages = [
        _page(parent, 1, ["9000001"], PAGE2_URL),
        _page(parent, 2, ["9000002"], PAGE3_URL),
        _page(parent, 3, ["9000003"], None),
    ]
    offer_details = {
        "https://coconala.com/mypage/offers/9000001": {"hidden": "95000002", "hrefs": [], "body": ""},
        "https://coconala.com/mypage/offers/9000002": {"hidden": present_id, "hrefs": [], "body": ""},
        "https://coconala.com/mypage/offers/9000003": {"hidden": "95000004", "hrefs": [], "body": ""},
    }
    return pages, offer_details


def _run_release(parent, release_module, tmp_path: Path, socket, *, max_pages: int):
    store = _store(parent, tmp_path)
    _write_counts(parent, store, {rid: 3 for rid in QUARANTINED})
    effects = parent.CdpParentEffects(
        ws_url="ws://127.0.0.1:9223/devtools/page/release-batch-test",
        evidence_dir=tmp_path / "evidence",
        ledger_path=tmp_path / "applied.jsonl",
        pass_id="release-batch-test",
    )
    (tmp_path / "evidence").mkdir(parents=True, exist_ok=True)

    def readback(request_ids: set[str]) -> set[str]:
        return effects._official_readback(
            request_ids, tmp_path / "evidence" / "wedge-release-readback.json",
            max_pages=max_pages,
        )

    with mock.patch.object(parent.websockets, "connect", lambda *a, **k: FakeConnection(socket)):
        outcomes = release_module.release(readback, store, threshold=3)
    return outcomes, store


def test_batch_walks_history_exhaustively_and_splits_present_from_absent(tmp_path: Path) -> None:
    parent, release_module = build()
    pages, offer_details = _three_page_history(parent, QUARANTINED[0])
    socket = ScanSocket(pages, offer_details)

    outcomes, store = _run_release(parent, release_module, tmp_path, socket, max_pages=5)

    assert outcomes == {
        QUARANTINED[0]: "already_applied_left_quarantined",
        QUARANTINED[1]: "released",
        QUARANTINED[2]: "released",
    }
    # The walk reached the last page (exhaustion, not truncation) before deciding absence.
    assert PAGE3_URL in socket.navigated_urls
    assert parent.load_wedge_counts(store) == {QUARANTINED[0]: 3}


def test_batch_truncation_releases_nothing(tmp_path: Path) -> None:
    """max_pages=2 against a 3-page history: page 2 still shows a next link, so absence was
    never proven -- every id stays quarantined."""
    parent, release_module = build()
    pages, offer_details = _three_page_history(parent, QUARANTINED[0])
    socket = ScanSocket(pages[:2], offer_details)

    outcomes, store = _run_release(parent, release_module, tmp_path, socket, max_pages=2)

    assert all(
        value == "readback_inconclusive:ReadbackScanTimeout" for value in outcomes.values()
    )
    assert parent.load_wedge_counts(store) == {rid: 3 for rid in QUARANTINED}


def test_batch_early_exits_when_every_id_is_found_on_page_one(tmp_path: Path) -> None:
    parent, release_module = build()
    page1 = _page(parent, 1, ["9100001", "9100002", "9100003"], PAGE2_URL)
    offer_details = {
        f"https://coconala.com/mypage/offers/910000{n}": {
            "hidden": QUARANTINED[n - 1], "hrefs": [], "body": ""
        }
        for n in (1, 2, 3)
    }
    socket = ScanSocket([page1], offer_details)

    outcomes, _ = _run_release(parent, release_module, tmp_path, socket, max_pages=5)

    assert all(value == "already_applied_left_quarantined" for value in outcomes.values())
    # All found on page 1: the walk stopped instead of paying for the rest of history.
    assert PAGE2_URL not in socket.navigated_urls


def test_even_a_noop_drain_leaves_summary_evidence_on_disk(tmp_path: Path) -> None:
    """Tonight's live run (2026-08-10) parsed {} from the dict-form store, never called
    the readback, and left --evidence-dir empty -- the only proof it ran was stdout.
    main() now writes wedge-release-summary.json unconditionally. The ws URL below is a
    fixture string handed to a fake lease script; with an empty store the readback is
    never invoked and no CDP connection is ever attempted."""
    _, release_module = build()
    lease_script = tmp_path / "lease.py"
    lease_script.write_text(
        "#!/usr/bin/env python3\n"
        "import json, sys\n"
        "if sys.argv[1] == 'acquire':\n"
        "    print(json.dumps({'ok': True, 'ws': 'ws://127.0.0.1:1/devtools/page/noop',"
        " 'token': '0' * 32, 'generation': 1}))\n"
        "else:\n"
        "    print(json.dumps({'ok': True}))\n",
        encoding="utf-8",
    )
    evidence_dir = tmp_path / "evidence"

    code = release_module.main([
        "--intent-root", str(tmp_path / "intents"),  # empty store -> no quarantined ids
        "--evidence-dir", str(evidence_dir),
        "--ledger", str(tmp_path / "applied.jsonl"),
        "--lease-script", str(lease_script),
        "--lease-task", "noop-drain-test",
        "--max-pages", "30",
    ])

    assert code == 0
    summary = json.loads((evidence_dir / "wedge-release-summary.json").read_text(encoding="utf-8"))
    assert summary["outcomes"] == {}
    assert summary["readback_ran"] is False
    assert summary["max_pages"] == 30
    # The walk evidence is still only written when a walk actually happens.
    assert not (evidence_dir / "wedge-release-readback.json").exists()
