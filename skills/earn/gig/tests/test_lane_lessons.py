"""X19 (2026-07-27): applying well and delivering well are different skills.

lessons.jsonl held 280 rows with no lane attribution at all, so every lesson the apply
lane ever learned was mixed into the same pile as every lesson the fulfil lane learned.
A lane reading that pile learns mostly about work it does not do.

These tests fix the contract that separates them:
  - new rows MUST carry a lane, enforced at the write boundary (not by prompt wording)
  - past rows are NOT guessed at; they stay lane=null and the count stays visible
  - a lane reads only its own lessons, newest-first-kept, bounded
  - one corrupt line does not take the file down (there is really one in production)
  - the two existing readers keep working, because the file stays one file
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import lane_lessons  # noqa: E402


def write(path, lines):
    path.write_text("".join(line + "\n" for line in lines), encoding="utf-8")


def test_lane_set_matches_the_six_pass_lanes():
    assert set(lane_lessons.LANES) == {
        "apply",
        "reply",
        "fulfill",
        "list",
        "profile",
        "improve",
    }
    # The step labels gig_pass.sh uses must map onto exactly those lanes.
    assert lane_lessons.STEP_LANES == {
        "B2": "apply",
        "B1": "reply",
        "PAID_WORK": "fulfill",
        "B0": "list",
        "PROFILE": "profile",
        "LEARN": "improve",
    }


def test_legacy_rows_are_null_lane_and_are_never_guessed(tmp_path):
    # These rows look very much like apply lessons. Inferring is still forbidden:
    # a fabricated attribution is indistinguishable from a real one downstream.
    path = tmp_path / "lessons.jsonl"
    write(
        path,
        [
            json.dumps({"ts": 1, "category": "writing", "outcome": "accepted",
                        "lesson": "short proposals win"}),
            json.dumps({"ts": 2, "category": "writing", "outcome": "rejected",
                        "lesson": "applied too late"}),
        ],
    )
    rows, malformed = lane_lessons.read_rows(path)
    assert malformed == 0
    assert [lane_lessons.lane_of(row) for row in rows] == [None, None]
    assert lane_lessons.stats(rows) == {
        "total": 2, "attributed": 0, "null": 2,
        "apply": 0, "reply": 0, "fulfill": 0, "list": 0, "profile": 0, "improve": 0,
    }


def test_one_corrupt_line_does_not_lose_the_rest(tmp_path):
    # Production lessons.jsonl line 242 is a truncated append. The reader must survive it
    # and say so, because "the file silently got shorter" is the failure that hides.
    path = tmp_path / "lessons.jsonl"
    write(
        path,
        [
            json.dumps({"lane": "apply", "lesson": "before"}),
            '{"ts": 1784307929, "requestId": "N/A", "outcome": "needs_human", "reason',
            "",
            "[1, 2, 3]",  # valid JSON, wrong shape
            json.dumps({"lane": "apply", "lesson": "after"}),
        ],
    )
    rows, malformed = lane_lessons.read_rows(path)
    assert [row["lesson"] for row in rows] == ["before", "after"]
    assert malformed == 2  # the truncated line and the non-object line; blank is not damage


def test_a_lane_reads_only_its_own_lessons(tmp_path):
    path = tmp_path / "lessons.jsonl"
    write(
        path,
        [
            json.dumps({"lane": "apply", "lesson": "a1"}),
            json.dumps({"lane": "fulfill", "lesson": "f1"}),
            json.dumps({"lane": "apply", "lesson": "a2"}),
            json.dumps({"lesson": "legacy"}),
            json.dumps({"lane": "reply", "lesson": "r1"}),
        ],
    )
    rows, _ = lane_lessons.read_rows(path)
    assert [r["lesson"] for r in lane_lessons.select(rows, "apply")] == ["a1", "a2"]
    assert [r["lesson"] for r in lane_lessons.select(rows, "fulfill")] == ["f1"]
    # Unattributed rows belong to no lane. They are not a default bucket for everyone,
    # which is exactly the mixing this change exists to end.
    assert lane_lessons.select(rows, "profile") == []


def test_selection_is_bounded_and_drops_the_oldest_first(tmp_path):
    # Bound the prompt by construction. File order is the authority, not ts: two rows in
    # production have no ts at all, and an append-only ledger is already chronological.
    path = tmp_path / "lessons.jsonl"
    write(path, [json.dumps({"lane": "apply", "lesson": f"L{i}"}) for i in range(10)])
    rows, _ = lane_lessons.read_rows(path)
    kept = lane_lessons.select(rows, "apply", limit=3)
    assert [r["lesson"] for r in kept] == ["L7", "L8", "L9"]


def test_brief_is_compact_bounded_and_lane_scoped(tmp_path):
    path = tmp_path / "lessons.jsonl"
    write(
        path,
        [
            json.dumps({"lane": "apply", "ts": 1, "category": "writing",
                        "outcome": "accepted", "lesson": "x" * 5000,
                        "requestId": "req-1", "reason": "noise" * 500}),
            json.dumps({"lane": "reply", "lesson": "not for apply"}),
        ],
    )
    rows, _ = lane_lessons.read_rows(path)
    brief = lane_lessons.brief(rows, "apply", limit=5)
    decoded = json.loads(brief)
    assert decoded["lane"] == "apply"
    assert len(decoded["lessons"]) == 1
    entry = decoded["lessons"][0]
    # Allowlisted projection: the prompt gets the lesson, not the whole row.
    assert set(entry) <= {"ts", "category", "outcome", "lesson"}
    assert len(entry["lesson"]) <= lane_lessons.MAX_LESSON_CHARS
    assert "not for apply" not in brief
    assert len(brief) <= lane_lessons.MAX_BRIEF_CHARS


def test_brief_for_a_lane_with_no_lessons_is_still_valid_json(tmp_path):
    path = tmp_path / "lessons.jsonl"
    write(path, [json.dumps({"lane": "apply", "lesson": "a"})])
    rows, _ = lane_lessons.read_rows(path)
    assert json.loads(lane_lessons.brief(rows, "profile"))["lessons"] == []


def test_append_requires_a_real_lane(tmp_path):
    path = tmp_path / "lessons.jsonl"
    for bad in (None, "", "apply_lane", "APPLY", "everything"):
        with pytest.raises(ValueError):
            lane_lessons.append_row(path, {"lesson": "x"}, bad)
    assert not path.exists()


def test_append_preserves_every_existing_byte_including_the_corrupt_line(tmp_path):
    path = tmp_path / "lessons.jsonl"
    original = '{"lane": "apply", "lesson": "old"}\n{"truncated\n'
    path.write_text(original, encoding="utf-8")
    lane_lessons.append_row(path, {"lesson": "new"}, "reply")
    text = path.read_text(encoding="utf-8")
    assert text.startswith(original)
    tail = json.loads(text[len(original):])
    assert tail["lane"] == "reply" and tail["lesson"] == "new"


def test_append_refuses_to_let_the_payload_forge_a_different_lane(tmp_path):
    path = tmp_path / "lessons.jsonl"
    with pytest.raises(ValueError):
        lane_lessons.append_row(path, {"lane": "fulfill", "lesson": "x"}, "apply")


def test_append_recovers_from_a_file_missing_its_final_newline(tmp_path):
    # The production corruption is a half-written append. If the next append does not
    # start its own line, it welds itself onto the damaged one and loses a second row.
    path = tmp_path / "lessons.jsonl"
    path.write_text('{"lane": "apply", "lesson": "old"}', encoding="utf-8")
    lane_lessons.append_row(path, {"lesson": "new"}, "reply")
    rows, malformed = lane_lessons.read_rows(path)
    assert malformed == 0
    assert [r["lesson"] for r in rows] == ["old", "new"]


def test_cli_brief_and_stats_and_append(tmp_path):
    path = tmp_path / "lessons.jsonl"
    write(
        path,
        [
            json.dumps({"lane": "apply", "lesson": "a1"}),
            json.dumps({"lesson": "legacy"}),
            "{oops",
        ],
    )
    script = str(SCRIPTS / "lane_lessons.py")

    brief = subprocess.run(
        [sys.executable, script, "brief", "--lane", "apply", "--path", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout
    assert json.loads(brief)["lessons"][0]["lesson"] == "a1"

    stats = json.loads(subprocess.run(
        [sys.executable, script, "stats", "--path", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout)
    assert stats["total"] == 2 and stats["null"] == 1 and stats["apply"] == 1
    assert stats["malformed"] == 1

    appended = subprocess.run(
        [sys.executable, script, "append", "--lane", "reply", "--path", str(path),
         "--json", json.dumps({"lesson": "r1", "outcome": "accepted"})],
        capture_output=True, text=True, check=True,
    )
    assert appended.returncode == 0
    rows, _ = lane_lessons.read_rows(path)
    assert rows[-1] == {"lane": "reply", "lesson": "r1", "outcome": "accepted"}

    rejected = subprocess.run(
        [sys.executable, script, "append", "--lane", "nonsense", "--path", str(path),
         "--json", '{"lesson": "x"}'],
        capture_output=True, text=True,
    )
    assert rejected.returncode != 0


def test_cli_brief_on_a_missing_file_is_empty_not_an_error(tmp_path):
    # A brand-new ~/gig must not fail every lane prompt build.
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "lane_lessons.py"), "brief", "--lane", "apply",
         "--path", str(tmp_path / "absent.jsonl")],
        capture_output=True, text=True, check=True,
    )
    assert json.loads(result.stdout)["lessons"] == []


def test_existing_readers_still_see_one_file_with_their_own_keys(tmp_path):
    """gig_funnel.py joins on requestId/category/outcome; gig_selfimprove_verify.sh uses
    mtime. Adding a lane column keeps both working; splitting into six files would have
    broken the funnel's join and the mtime evidence, which is why the file stayed one."""
    path = tmp_path / "lessons.jsonl"
    lane_lessons.append_row(
        path,
        {"requestId": "req-9", "category": "writing", "outcome": "accepted",
         "lesson": "x"},
        "apply",
    )
    row = json.loads(path.read_text(encoding="utf-8").strip())
    assert row["requestId"] == "req-9"
    assert row["category"] == "writing"
    assert row["outcome"] == "accepted"
