"""The posting we applied to has to reach the project we won.

Against the real material: the committed fixture is the first 3 KB of the actual
application snapshot the pass wrote on 2026-08-07, and the backfill test replays the real
markdown shape of ``https://coconala.com/requests/91000002`` -- 枚数 4枚, the four
希望イメージ sliders, 納品ファイル形式 -- including the applicant roster that must be cut.
No test reaches the network.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "posting_source.py"
SPEC = importlib.util.spec_from_file_location("posting_source", SCRIPT)
posting_source = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(posting_source)

POSTING_MARKDOWN = """\
#  Canvaを使った画像編集・デザイン制作をお願いできる方を募集します
[ 写真加工・画像編集 ](https://coconala.com/requests/categories/350)
予算
5千円未満
納品希望日
2026年8月11日
枚数
4枚
希望イメージ
シンプル
3
複雑
納品ファイル形式
TTPX
###  募集内容
【業務内容】 ・Canvaを使った画像データの調整と加工、およびデザイン制作をお願いいたします。
###  応募者一覧
応募者
[ Sample｜サンプル研修資料×AI活用 ](https://coconala.com/users/2564121)
2026/08/06 12:34
"""


def _snapshot(request_id: str = "91000107") -> dict[str, object]:
    return {
        "version": 1,
        "observed_at": "2026-08-07T11:00:17+00:00",
        "request_details": [{
            "request_id": request_id,
            "canonical_url": f"https://coconala.com/requests/{request_id}",
            "title": "動画の企画・撮影・編集ディレクター募集",
            "category": "動画編集",
            "visible_text": "予算\n見積り希望\n納品ファイル形式\nMP4、MOV\n募集内容\n本文",
            "observed_at": "2026-08-07T11:00:17+00:00",
        }],
    }


def test_harvest_stores_the_posting_body_keyed_by_request_id(tmp_path):
    rows = posting_source.harvest_snapshot(_snapshot(), tmp_path / "postings")
    assert rows == [{
        "request_id": "91000107",
        "path": str(tmp_path / "postings" / "request-91000107.json"),
        "written": True,
    }]
    stored = json.loads((tmp_path / "postings" / "request-91000107.json").read_text(encoding="utf-8"))
    assert "MP4、MOV" in stored["body"]
    assert stored["source"] == "application_snapshot"


def test_reharvesting_an_unchanged_posting_rewrites_nothing(tmp_path):
    store = tmp_path / "postings"
    posting_source.harvest_snapshot(_snapshot(), store)
    path = store / "request-91000107.json"
    before = (path.read_bytes(), path.stat().st_mtime_ns)
    rows = posting_source.harvest_snapshot(_snapshot(), store)
    assert rows[0]["written"] is False
    assert (path.read_bytes(), path.stat().st_mtime_ns) == before


def test_install_copies_the_posting_into_a_won_project(tmp_path):
    store = tmp_path / "postings"
    posting_source.harvest_snapshot(_snapshot("91000002"), store)
    project = tmp_path / "projects" / "91000002"
    (project / "source").mkdir(parents=True)
    result = posting_source.install_posting(store, project, "91000002")
    assert result["written"] is True
    installed = json.loads(
        (project / "source" / "posting" / "request-91000002.json").read_text(encoding="utf-8")
    )
    assert installed["request_id"] == "91000002"
    # Idempotent: the project copy is content-addressed too.
    assert posting_source.install_posting(store, project, "91000002")["written"] is False


def test_install_is_a_no_op_before_the_project_exists(tmp_path):
    store = tmp_path / "postings"
    posting_source.harvest_snapshot(_snapshot("91000002"), store)
    assert posting_source.install_posting(store, tmp_path / "projects" / "91000002", "91000002") is None


def test_install_without_a_stored_posting_reports_absence(tmp_path):
    project = tmp_path / "projects" / "91000002"
    project.mkdir(parents=True)
    assert posting_source.install_posting(tmp_path / "postings", project, "91000002") is None


def test_the_applicant_roster_is_cut_and_the_spec_is_kept(tmp_path):
    body = posting_source.strip_applicant_roster(POSTING_MARKDOWN)
    assert "枚数\n4枚" in body
    assert "希望イメージ" in body
    assert "納品ファイル形式" in body
    assert "応募者一覧" not in body
    assert "Kosuke" not in body


def test_backfill_from_a_body_file_stores_and_installs(tmp_path, monkeypatch, capsys):
    project = tmp_path / "projects" / "91000002"
    project.mkdir(parents=True)
    source = tmp_path / "posting.md"
    source.write_text(POSTING_MARKDOWN, encoding="utf-8")
    exit_code = posting_source.main([
        "--store-root", str(tmp_path / "postings"),
        "backfill", "--request-id", "91000002", "--body-file", str(source),
        "--install", "--projects-root", str(tmp_path / "projects"),
    ])
    assert exit_code == 0
    report = json.loads(capsys.readouterr().out.strip())
    assert report["stored"]["written"] is True
    assert report["installed"]["written"] is True
    installed = json.loads(
        (project / "source" / "posting" / "request-91000002.json").read_text(encoding="utf-8")
    )
    assert "4枚" in installed["body"]
    assert installed["url"] == "https://coconala.com/requests/91000002"
    assert installed["source"] == "operator_body_file"


def test_a_request_id_that_is_not_an_id_is_refused(tmp_path):
    with pytest.raises(posting_source.PostingError):
        posting_source.canonical_request_id("../../etc/passwd")


def test_an_empty_posting_is_refused_rather_than_stored_as_proof_of_nothing(tmp_path):
    snapshot = _snapshot()
    snapshot["request_details"][0]["visible_text"] = "   \n\n  "
    rows = posting_source.harvest_snapshot(snapshot, tmp_path / "postings")
    assert rows[0]["error"] == "empty_posting_body"
    assert not (tmp_path / "postings" / "request-91000107.json").exists()


def test_the_stored_posting_is_owner_only(tmp_path):
    posting_source.harvest_snapshot(_snapshot(), tmp_path / "postings")
    path = tmp_path / "postings" / "request-91000107.json"
    assert path.stat().st_mode & 0o777 == 0o600


if __name__ == "__main__":  # pragma: no cover - convenience
    raise SystemExit(pytest.main([__file__, "-p", "no:randomly", "-q"]))
