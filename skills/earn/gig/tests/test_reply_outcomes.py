from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


# Measured 2026-08-06: replied threads and purchased projects share no ids at all.
#
#   replied   93000005, 90000007     the DM thread
#   purchased 90000004, 90000000     the talkroom, after the buyer paid
#             91000002,  91000014      the job request, for application-side work
#
# The id changes at the moment of purchase, so comparing the two sets directly reports zero
# conversions forever. The bridge exists on disk: a purchased project keeps the DM thread it
# grew out of, at projects/<project>/source/dm/thread-<DM_ID>-*.json.


def load():
    spec = importlib.util.spec_from_file_location(
        "reply_outcomes", SCRIPTS / "reply_outcomes.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_projects(tmp_path: Path, mapping: dict[str, list[str]]) -> Path:
    root = tmp_path / "projects"
    for project, dm_ids in mapping.items():
        dm_dir = root / project / "source" / "dm"
        dm_dir.mkdir(parents=True)
        for dm in dm_ids:
            (dm_dir / f"thread-{dm}-full.json").write_text("{}", encoding="utf-8")
    return root


def test_the_bridge_recovers_the_dm_thread_a_purchase_grew_from(tmp_path) -> None:
    m = load()
    root = make_projects(tmp_path, {"90000004": ["93000003"], "90000000": ["9926596"]})
    assert m.won_dm_thread_ids(root) == {"93000003", "9926596"}


def test_a_project_without_a_dm_origin_contributes_nothing(tmp_path) -> None:
    # Application-side work (91000002) never had a DM. It is a real conversion, but not one
    # any reply can take credit for, and crediting it would corrupt the dataset.
    m = load()
    root = make_projects(tmp_path, {"90000004": ["93000003"]})
    (root / "91000002" / "delivery").mkdir(parents=True)
    assert m.won_dm_thread_ids(root) == {"93000003"}


def test_a_missing_projects_root_is_empty_not_an_error(tmp_path) -> None:
    m = load()
    assert m.won_dm_thread_ids(tmp_path / "absent") == set()


def test_a_replied_thread_that_converted_is_labelled_won() -> None:
    m = load()
    assert m.label_for("93000003", {"93000003", "9926596"}) == "won"


def test_a_replied_thread_that_has_not_converted_is_silent_not_lost() -> None:
    # "silent" is the honest word. A buyer who has not answered yet has not refused, and
    # naming it "lost" would teach the wrong lesson to whatever reads this later.
    m = load()
    assert m.label_for("93000005", {"93000003"}) == "silent"


def test_labelling_joins_transcripts_without_rewriting_them() -> None:
    # The transcript ledger is append-only; rewriting past rows to add an outcome would be
    # editing history. The label is applied on read.
    m = load()
    transcripts = [
        {"talkroom_id": "93000003", "outgoing_body": "ご購入後に着手します", "outcome": None},
        {"talkroom_id": "93000005", "outgoing_body": "本日中にお送りします", "outcome": None},
    ]
    labelled = m.label_transcripts(transcripts, {"93000003"})

    assert [row["outcome"] for row in labelled] == ["won", "silent"]
    # The originals are untouched.
    assert [row["outcome"] for row in transcripts] == [None, None]
