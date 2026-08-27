import json
import pathlib
import sys

import jsonschema
import pytest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from publish_cli import run_create_intent


def test_intent_create_resolves_immutable_route_from_registry(tmp_path):
    asset = tmp_path / "preview.mp4"
    asset.write_bytes(b"preview")
    output = tmp_path / "intent.json"
    result = run_create_intent(
        engine=HERE.parent, output_path=output,
        experiment_id="experiment.gate12", creative_id="creative.gate12",
        product_id="ebook-ja", account_id="tiktok.obou_anicca",
        hook_id="hook.gate12", renderer_id="watercolor-monk", adapter="postiz",
        asset_path=asset,
        caption="『アニッチャ・リセット』を読む https://aniccaai.com/go/ej_token ej_token",
        attribution_token="ej_token", scheduled_at="2026-08-02T02:00:00Z",
        visual_approval_id="visual.accepted.gate12", now="2026-08-02T00:00:00Z")
    intent = json.loads(output.read_text())
    assert result["publish_key"] == intent["publish_key"]
    assert intent["native_handle"] == "obou_anicca"
    assert intent["integration_id"] == "cmo5s4edx00vgn10ygnu34a0n"
    assert intent["provider_settings"]["__type"] == "tiktok"
    schema = json.loads((HERE.parent / "schemas/publication-intent.schema.json").read_text())
    jsonschema.validate(intent, schema)


def test_intent_create_rejects_cross_product_route_and_conflicting_output(tmp_path):
    asset = tmp_path / "preview.mp4"
    asset.write_bytes(b"preview")
    args = dict(
        engine=HERE.parent, output_path=tmp_path / "intent.json",
        experiment_id="experiment.gate12", creative_id="creative.gate12",
        product_id="ebook-ja", account_id="tiktok.obou_anicca",
        hook_id="hook.gate12", renderer_id="watercolor-monk", adapter="postiz",
        asset_path=asset,
        caption="『アニッチャ・リセット』を読む https://aniccaai.com/go/ej_token ej_token",
        attribution_token="ej_token", scheduled_at="2026-08-02T02:00:00Z",
        visual_approval_id="visual.accepted.gate12", now="2026-08-02T00:00:00Z")
    run_create_intent(**args)
    with pytest.raises(ValueError, match="conflicting immutable intent output"):
        run_create_intent(**(args | {"scheduled_at": "2026-08-02T03:00:00Z"}))
    with pytest.raises(ValueError, match="account product mismatch"):
        run_create_intent(**(args | {"output_path": tmp_path / "wrong.json",
                                     "product_id": "ebook-en"}))
    with pytest.raises(ValueError, match="scheduled time must be in the future"):
        run_create_intent(**(args | {"output_path": tmp_path / "past.json",
                                     "scheduled_at": "2026-08-01T23:59:59Z"}))
