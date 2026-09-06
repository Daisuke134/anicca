"""Whether two listings sell the same thing to a buyer is a commercial judgement, not a
character-overlap measure. `_near_duplicate_listings` now asks a model that question under a
strict schema (see `skills/earn/gig/schemas/storefront_duplicate_judgement.schema.json`) and
`storefront_duplicate_judgement.schema.json`, and this file exercises every mechanical guard code
owns over the model's answer, using the eight real live listings this feature exists for: five SNS
posting-hygiene listings and three Excel/VBA automation listings that a 0.9 title-similarity ratio
could never see as duplicates (their closest pair measures 0.857 -- see the last test below)."""

import difflib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import storefront_direct as sd  # noqa: E402

TITLES = {
    "4244556": "SNS投稿の公開前確認を設計し",
    "4244912": "SNS投稿業務の引継ぎ手順を作成し",
    "4302213": "SNS投稿のAI導入で試す工程と確認表を作成し",
    "4330105": "SNS投稿のAI引継ぎ手順書を作成し",
    "4330753": "SNS投稿の公開前チェック表を設計し",
    "4244910": "定型Excel作業をVBAマクロで自動化し",
    "4313386": "定型Excelの転記・集計をVBAで自動化し",
    "4357844": "請求書の転記・集計をExcelマクロで自動化し",
}
FAMILIES = {
    "4244556": "sns_hygiene", "4244912": "sns_hygiene", "4302213": "sns_hygiene",
    "4330105": "sns_hygiene", "4330753": "sns_hygiene",
    "4244910": "excel_automation", "4313386": "excel_automation", "4357844": "excel_automation",
}
ROWS = [{"service_id": sid, "title_stem": title} for sid, title in TITLES.items()]
SNS_GROUP = {
    "service_ids": ["4244556", "4244912", "4302213", "4330105", "4330753"],
    "keep_service_id": "4244556",
    "reason": "同じSNS投稿の公開前運用を別の言い回しで売っている",
}
EXCEL_GROUP = {
    "service_ids": ["4244910", "4313386", "4357844"],
    "keep_service_id": "4244910",
    "reason": "同じExcel/VBA自動化を別の言い回しで売っている",
}
VALID_RESULT = {"groups": [SNS_GROUP, EXCEL_GROUP]}


def _run(rows, families, tmp_path, monkeypatch, *, result=None, error=None):
    if error is not None:
        def boom(**_kwargs):
            raise error
        monkeypatch.setattr(sd, "_invoke_duplicate_judgement_proposal", boom)
    else:
        def fake(**_kwargs):
            return result, {"provider": "codex", "model": "gpt-5.6-terra", "effort": "medium"}
        monkeypatch.setattr(sd, "_invoke_duplicate_judgement_proposal", fake)
    return sd._near_duplicate_listings(
        rows, families, state_dir=tmp_path, evidence_dir=tmp_path / "evidence",
    )


def test_valid_two_group_answer_produces_pairs_with_keep_as_survivor(tmp_path, monkeypatch):
    pairs = _run(ROWS, FAMILIES, tmp_path, monkeypatch, result=VALID_RESULT)
    assert len(pairs) == 6  # 4 SNS pairs + 2 Excel pairs (group of N -> N-1 pairs)
    for pair in pairs:
        keep, other = pair["service_ids"]
        assert keep in {"4244556", "4244910"}  # the survivor named by the model
        assert other != keep
        assert pair["reason"]
        assert isinstance(pair["title_similarity"], float)
    sns_others = {p["service_ids"][1] for p in pairs if p["service_ids"][0] == "4244556"}
    excel_others = {p["service_ids"][1] for p in pairs if p["service_ids"][0] == "4244910"}
    assert sns_others == {"4244912", "4302213", "4330105", "4330753"}
    assert excel_others == {"4313386", "4357844"}


def test_unknown_service_id_is_rejected_whole_result(tmp_path, monkeypatch):
    bad = {"groups": [{"service_ids": ["4244556", "9999999"], "keep_service_id": "4244556",
                        "reason": "x"}]}
    pairs = _run(ROWS, FAMILIES, tmp_path, monkeypatch, result=bad)
    assert pairs == []
    error_path = tmp_path / "evidence" / "duplicate-judgement-error.json"
    assert error_path.exists()
    assert "unknown_service_id" in json.loads(error_path.read_text(encoding="utf-8"))["error"]


def test_group_of_one_is_rejected(tmp_path, monkeypatch):
    bad = {"groups": [{"service_ids": ["4244556"], "keep_service_id": "4244556", "reason": "x"}]}
    assert _run(ROWS, FAMILIES, tmp_path, monkeypatch, result=bad) == []


def test_id_claimed_by_two_groups_is_rejected(tmp_path, monkeypatch):
    bad = {"groups": [
        {"service_ids": ["4244556", "4244912"], "keep_service_id": "4244556", "reason": "x"},
        {"service_ids": ["4244912", "4302213"], "keep_service_id": "4244912", "reason": "y"},
    ]}
    assert _run(ROWS, FAMILIES, tmp_path, monkeypatch, result=bad) == []


def test_keep_not_a_member_of_its_own_group_is_rejected(tmp_path, monkeypatch):
    bad = {"groups": [{"service_ids": ["4244556", "4244912"], "keep_service_id": "4302213",
                        "reason": "x"}]}
    assert _run(ROWS, FAMILIES, tmp_path, monkeypatch, result=bad) == []


def test_empty_reason_is_rejected(tmp_path, monkeypatch):
    bad = {"groups": [{"service_ids": ["4244556", "4244912"], "keep_service_id": "4244556",
                        "reason": "   "}]}
    assert _run(ROWS, FAMILIES, tmp_path, monkeypatch, result=bad) == []


def test_model_call_raising_produces_zero_pairs_and_leaves_ledger_untouched(tmp_path, monkeypatch):
    ledger = tmp_path / "duplicate-listings.jsonl"
    pairs = _run(ROWS, FAMILIES, tmp_path, monkeypatch, error=RuntimeError("boom"))
    assert pairs == []
    assert not ledger.exists()
    error_path = tmp_path / "evidence" / "duplicate-judgement-error.json"
    assert error_path.exists()
    assert "RuntimeError" in json.loads(error_path.read_text(encoding="utf-8"))["error"]


def test_schema_forbids_oneof_allof_not():
    """The structured-output provider rejects oneOf/allOf/not outright."""
    schema_path = (Path(__file__).resolve().parents[1]
                   / "schemas" / "storefront_duplicate_judgement.schema.json")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    def walk(node):
        if isinstance(node, dict):
            assert "oneOf" not in node
            assert "allOf" not in node
            assert "not" not in node
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(schema)


def test_measured_ratio_for_the_closest_real_pair_is_below_the_old_threshold():
    """4244912 x 4330105 is the closest pair among the eight measured listings: 0.857, below the
    0.9 gate the old ratio-based instrument required. This is why it never fired in production,
    and why nobody should lower the threshold to "fix" it -- the regression check for that."""
    ratio = difflib.SequenceMatcher(None, TITLES["4244912"], TITLES["4330105"]).ratio()
    assert ratio < 0.9
    assert round(ratio, 3) == 0.857
