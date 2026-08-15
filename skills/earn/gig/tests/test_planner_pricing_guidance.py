from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


# V1 pricing correction (§FN' / §FR' item 1): null-budget software quotes use a
# scope/market-guided ¥50,000-300,000 reference band without becoming a hard validator
# ceiling. These are static prompt instructions; the model still judges each request
# from the immutable envelope.

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "application_planner.py"

HARD_PROHIBITION_CLASSES = {
    "video_or_animation": "video editing/production, live-action filming, AI video, animation, or MV",
    "physical_or_onsite": "on-site work or physical making/assembly/cleaning/repair/cooking/sewing/woodwork/model making/packing/shipping/delivery/receipt",
    "mandatory_human_presence": "explicitly required human face appearance/performance/voice recording/phone work, real-time live call, or video interview; vague meetings, ordinary communication, or possible consultation do not qualify",
    "explicit_ai_prohibition": "explicit prohibition on AI use",
    "illegal_or_unsafe": "illegal or unsafe work",
    "missing_legal_qualification": "legally required qualification that Kosuke does not hold",
    "mandatory_attribute_fabrication": "mandatory immutable/current personal identity or life-status fact that cannot be answered truthfully; skill, work experience, portfolio, achievements, tool experience, or preferred qualifications never qualify",
}

DISCRETIONARY_NON_REFUSAL_CONCEPTS = (
    "Experience uncertainty",
    "weak portfolio",
    "broad scope",
    "low budget",
    "difficulty",
    "unclear production scope",
    "possible optional consultation",
    "unverified achievements",
    "unverified Adobe experience",
)


def load_module():
    scripts_dir = str(MODULE_PATH.parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location("application_planner", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _envelope(*, budget_min: int | None, budget_max: int | None) -> dict:
    return {
        "request_details": [
            {
                "request_id": "97000001",
                "category": "コード",
                "budget_min_jpy": budget_min,
                "budget_max_jpy": budget_max,
            }
        ]
    }


def test_known_budget_prompt_never_exceeds_client_maximum() -> None:
    m = load_module()
    prompt = m.planner_prompt(_envelope(budget_min=10000, budget_max=10000))
    assert "budget_max_jpy" in prompt
    assert "budget_max_jpy を超えない" in prompt


def test_quote_request_prompt_uses_scope_market_and_reference_band() -> None:
    m = load_module()
    prompt = m.planner_prompt(_envelope(budget_min=None, budget_max=None))
    assert "見積依頼" in prompt
    assert "成果物" in prompt and "作業量" in prompt and "リスク" in prompt
    assert "通常のカテゴリ相場" in prompt
    assert "50,000" in prompt and "300,000" in prompt
    assert "案件ごと" in prompt


def test_quote_request_prompt_does_not_restore_the_old_15000_ceiling() -> None:
    m = load_module()
    prompt = m.planner_prompt(_envelope(budget_min=None, budget_max=None))
    assert "price_jpy <= 15000" not in prompt
    assert "15,000円" not in prompt
    assert "見積依頼" in prompt


def test_prompt_uses_hard_prohibition_ssot_and_keeps_discretionary_candidates() -> None:
    m = load_module()
    prompt = m.planner_prompt(_envelope(budget_min=None, budget_max=None))

    assert list(m.HARD_PROHIBITION_CLASSES) == list(HARD_PROHIBITION_CLASSES)
    assert m.HARD_PROHIBITION_CLASSES == HARD_PROHIBITION_CLASSES
    for reason_code, description in HARD_PROHIBITION_CLASSES.items():
        assert reason_code in prompt
        assert description in prompt
    for concept in DISCRETIONARY_NON_REFUSAL_CONCEPTS:
        assert concept in prompt
    assert "reason_codes[0]" in prompt
    assert "reason_codes[1]" in prompt
    assert "discretionary weaknesses, never refusal reasons" in prompt
    assert "work history, domain experience, portfolio, numeric achievement" in prompt
    assert "Even when the listing says it is required" in prompt
    assert "A generic meeting, discussion, interview, consultation" in prompt
    assert "Ambiguous modality remains submit_required" in prompt
    assert "3Dモデリング・3Dアニメーション・3D制作も対応 capability の範囲外" not in prompt
    assert "根拠のない実績を要求される案件は ineligible" not in prompt
