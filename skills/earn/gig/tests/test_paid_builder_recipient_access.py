from pathlib import Path


GIG_PASS = Path(__file__).resolve().parents[1] / "gig_pass.sh"


def test_paid_builder_prompt_turns_unopenable_artifact_feedback_into_nonarchive_contract():
    source = GIG_PASS.read_text(encoding="utf-8")
    assert "RECIPIENT-ACCESS FORMAT CONTRACT" in source
    assert "prior artifact cannot be opened" in source
    assert "never reuse or attach a ZIP" in source
    assert "real open/readback check" in source
    assert "recipient_access_required=true" in source
