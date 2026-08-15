from __future__ import annotations

import importlib.util
import json
import stat
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


# followup_candidates caps a thread at three follow-ups, but the count it reads was
# hard-wired to 0 -- so wiring the sender before this ledger exists would have let one
# buyer receive an unbounded stream, which is precisely the 迷惑行為 the cap was chosen to
# avoid. The cap is only real once the count is durable.


def load():
    spec = importlib.util.spec_from_file_location(
        "followup_ledger", SCRIPTS / "followup_ledger.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_a_thread_never_contacted_counts_zero(tmp_path) -> None:
    m = load()
    assert m.followups_sent(tmp_path / "absent.jsonl") == {}


def test_recording_a_followup_makes_it_countable(tmp_path) -> None:
    m = load()
    path = tmp_path / "followups.jsonl"
    assert m.record_followup(path, thread_id="9976213", sent_at=1786000000) is True
    assert m.followups_sent(path) == {"9976213": 1}


def test_the_count_accumulates_per_thread(tmp_path) -> None:
    m = load()
    path = tmp_path / "followups.jsonl"
    for n in range(3):
        m.record_followup(path, thread_id="9976213", sent_at=1786000000 + n)
    m.record_followup(path, thread_id="93000001", sent_at=1786000000)
    assert m.followups_sent(path) == {"9976213": 3, "93000001": 1}


def test_the_ledger_is_append_only_and_private(tmp_path) -> None:
    # Buyers' identities. Same permission as the rest of the evidence tree.
    m = load()
    path = tmp_path / "followups.jsonl"
    m.record_followup(path, thread_id="1", sent_at=1)
    m.record_followup(path, thread_id="1", sent_at=2)
    assert len(path.read_text(encoding="utf-8").splitlines()) == 2
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_a_corrupt_line_does_not_lose_the_rest(tmp_path) -> None:
    m = load()
    path = tmp_path / "followups.jsonl"
    path.write_text(
        json.dumps({"thread_id": "1", "sent_at": 1}) + "\nnot json\n"
        + json.dumps({"thread_id": "1", "sent_at": 2}) + "\n",
        encoding="utf-8",
    )
    assert m.followups_sent(path) == {"1": 2}


def test_an_unwritable_ledger_reports_false_rather_than_raising(tmp_path) -> None:
    # Recording runs next to a real send. If it raised after the message went out, the
    # count would be wrong in the dangerous direction -- undercounting lets us send again.
    m = load()
    blocked = tmp_path / "afile"
    blocked.write_text("x", encoding="utf-8")
    assert m.record_followup(blocked / "inner" / "f.jsonl", thread_id="1", sent_at=1) is False


def test_the_cap_becomes_real_once_the_ledger_is_read(tmp_path) -> None:
    # The two halves together: a thread at the cap stops being a candidate.
    m = load()
    spec = importlib.util.spec_from_file_location(
        "followup_candidates_ledger", SCRIPTS / "followup_candidates.py"
    )
    assert spec and spec.loader
    candidates = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(candidates)

    path = tmp_path / "followups.jsonl"
    for n in range(3):
        m.record_followup(path, thread_id="9976213", sent_at=1786000000 + n)
    counts = m.followups_sent(path)

    now = 1786000000 + 20 * 86400
    row = {
        "thread_id": "9976213",
        "last_seller_sent_at": 1786000000,
        "followups_sent": counts.get("9976213", 0),
        "outcome": "silent",
    }
    assert candidates.is_candidate(row, now=now) is False
    fresh = {**row, "thread_id": "93000001", "followups_sent": counts.get("93000001", 0)}
    assert candidates.is_candidate(fresh, now=now) is True
