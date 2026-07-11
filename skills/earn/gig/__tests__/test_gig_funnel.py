#!/usr/bin/env python3
"""Unit tests for gig_funnel.py — deterministic funnel writer (gig L1-c).

Runs the real script against an isolated temp HOME with synthetic jsonl inputs and
asserts the overall + by_category counts and the append/robustness behaviour.
"""
import json
import os
import subprocess
import sys
import tempfile

SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "gig_funnel.py")


def write_jsonl(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def run(home, pass_id="p-test"):
    env = {**os.environ, "HOME": home}
    out = subprocess.check_output([sys.executable, SCRIPT, pass_id], env=env).decode().strip()
    return json.loads(out.splitlines()[-1])


def seed(home):
    gig = os.path.join(home, "gig")
    os.makedirs(gig, exist_ok=True)
    # applied: 3 applied (2 with category, 1 joined via lessons), 1 replied, 1 delivered
    write_jsonl(os.path.join(gig, "applied.jsonl"), [
        {"requestId": "1", "status": "applied", "category": "記事/blog"},
        {"requestId": "2", "status": "applied", "category": "記事/blog"},
        {"requestId": "3", "status": "applied"},                 # category joined from lessons -> コード
        {"requestId": "4", "status": "replied", "category": "記事/blog"},
        {"requestId": "5", "status": "delivered", "category": "コード"},
        {"requestId": "6", "status": "評価依頼"},                 # replied bucket, uncategorized
    ])
    write_jsonl(os.path.join(gig, "lessons.jsonl"), [
        {"requestId": "3", "category": "コード", "outcome": "rejected"},
        {"requestId": "2", "category": "記事/blog", "outcome": "accepted"},   # won +1
    ])
    write_jsonl(os.path.join(gig, "earnings.jsonl"), [
        {"requestId": "2", "status": "検収完了", "evidence": "url", "jpy": 5000},   # paid +1, jpy 5000
        {"requestId": "9", "status": "applied", "evidence": "", "jpy": 0},          # NOT settled -> ignored
    ])
    write_jsonl(os.path.join(gig, "shuppin.jsonl"), [
        {"service_id": "100", "action": "shuppin_published"},
        {"service_id": "100", "action": "shuppin_edited"},
        {"service_id": "101", "action": "shuppin_published"},
    ])
    return gig


def test_counts():
    with tempfile.TemporaryDirectory() as home:
        gig = seed(home)
        row = run(home)
        assert row["applied"] == 3, row
        assert row["replied"] == 3, row          # replied + delivered + 評価依頼
        assert row["won"] == 1, row
        assert row["paid"] == 1, row
        assert row["jpy"] == 5000, row
        assert row["listings_live"] == 2, row     # 2 distinct published service_ids
        bc = row["by_category"]
        assert bc["記事/blog"]["applied"] == 2, bc
        assert bc["コード"]["applied"] == 1, bc    # joined from lessons
        assert bc["記事/blog"]["won"] == 1, bc
        assert bc["記事/blog"]["paid"] == 1, bc
        assert bc["uncategorized"]["replied"] == 1, bc
        # a row was appended to gig-funnel.jsonl
        fp = os.path.join(gig, "gig-funnel.jsonl")
        assert os.path.exists(fp)
        assert len(open(fp).read().strip().splitlines()) == 1
        print("test_counts OK", json.dumps(row, ensure_ascii=False))


def test_append_and_empty():
    with tempfile.TemporaryDirectory() as home:
        os.makedirs(os.path.join(home, "gig"), exist_ok=True)
        # no input files at all -> must not crash, appends a zero row
        r1 = run(home, "p-1")
        assert r1["applied"] == 0 and r1["by_category"] == {}, r1
        r2 = run(home, "p-2")
        fp = os.path.join(home, "gig", "gig-funnel.jsonl")
        assert len(open(fp).read().strip().splitlines()) == 2, "second call must APPEND not overwrite"
        assert r2["pass_id"] == "p-2"
        print("test_append_and_empty OK")


def test_corrupt_lines_skipped():
    with tempfile.TemporaryDirectory() as home:
        gig = os.path.join(home, "gig")
        os.makedirs(gig, exist_ok=True)
        with open(os.path.join(gig, "applied.jsonl"), "w", encoding="utf-8") as f:
            f.write('{"requestId":"1","status":"applied","category":"X"}\n')
            f.write("this is not json\n")
            f.write('{"requestId":"2","status":"applied","category":"X"}\n')
        row = run(home)
        assert row["applied"] == 2, row
        print("test_corrupt_lines_skipped OK")


if __name__ == "__main__":
    test_counts()
    test_append_and_empty()
    test_corrupt_lines_skipped()
    print("ALL gig_funnel tests PASS")
