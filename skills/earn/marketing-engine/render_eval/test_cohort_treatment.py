from __future__ import annotations

import copy
import hashlib
import json
import pathlib
import sys

import pytest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from cohort_treatment import (append_manifest, build_manifest, render_treatment,
                              validate_cohort_compatibility,
                              verify_cohort_selection)


def plan(index: int = 1) -> dict:
    return {
        "schema_version": "marketing.experiment-plan.v1",
        "experiment_id": f"experiment.{index:024x}",
        "creative_id": f"creative.{index:024x}",
        "product_id": "ebook-ja",
        "account_id": "tiktok.obou_anicca",
        "hook_id": f"hook.{index}",
        "hook_text": f"検証する冒頭文{index}。",
        "tactic_id": "tactic.faceless-visual-refresh-captions.v1",
        "renderer_id": "watercolor-monk",
        "cta": "『アニッチャ・リセット』を読む",
        "destination_url": "https://aniccaai.com/achan",
    }


def config(clips: list[pathlib.Path]) -> dict:
    renderer_source = clips[0].parent / "renderer.py"
    renderer_source.write_text("renderer-v1", encoding="utf-8")
    return {
        "schema_version": "marketing.cohort-treatment-config.v1",
        "cohort_id": "cohort.ebook-ja.tiktok.watercolor.24h.v1",
        "product_id": "ebook-ja",
        "account_id": "tiktok.obou_anicca",
        "tactic_id": "tactic.faceless-visual-refresh-captions.v1",
        "renderer_id": "watercolor-monk",
        "renderer_version": "watercolor-cohort-v1",
        "renderer_source_path": str(renderer_source),
        "body_template_id": "body.ebook-ja.boundary-reset.v1",
        "body_text": "今日から返事を急がず、自分が落ち着ける時間を守ってください。",
        "voice": "Kyoko",
        "voice_rate": 165,
        "caption_style_id": "ass.watercolor.safe-v1",
        "clip_paths": [str(path) for path in clips],
        "target_duration_seconds": {"min": 15.0, "max": 19.0},
    }


def make_manifest(tmp_path: pathlib.Path, index: int = 1, duration: float = 17.2):
    clips = [tmp_path / "a.mp4", tmp_path / "b.mp4"]
    for clip_index, clip in enumerate(clips):
        clip.write_bytes(f"clip-{clip_index}".encode())
    asset = tmp_path / f"output-{index}.mp4"
    asset.write_bytes(f"render-{index}".encode())
    return build_manifest(plan(index), config(clips), asset_path=asset,
                          duration_seconds=duration)


def test_manifest_binds_every_causal_input_and_hash(tmp_path):
    row = make_manifest(tmp_path)
    assert row["schema_version"] == "marketing.cohort-treatment.v1"
    assert row["full_script"] == (
        "検証する冒頭文1。今日から返事を急がず、自分が落ち着ける時間を守ってください。"
        "『アニッチャ・リセット』を読む"
    )
    assert row["script_sha256"] == hashlib.sha256(
        row["full_script"].encode("utf-8")).hexdigest()
    assert row["asset_sha256"] == hashlib.sha256(
        pathlib.Path(row["asset_path"]).read_bytes()).hexdigest()
    assert [item["path"] for item in row["clip_set"]] == [
        str(tmp_path / "a.mp4"), str(tmp_path / "b.mp4")]
    assert all(len(item["sha256"]) == 64 for item in row["clip_set"])
    assert row["renderer_source_sha256"] == hashlib.sha256(
        pathlib.Path(row["renderer_source_path"]).read_bytes()).hexdigest()
    assert row["publication_effects"] == []


@pytest.mark.parametrize("field", ["tactic_id", "renderer_id"])
def test_missing_exact_plan_identity_fails_closed(tmp_path, field):
    clips = [tmp_path / "a.mp4"]
    clips[0].write_bytes(b"clip")
    asset = tmp_path / "output.mp4"
    asset.write_bytes(b"render")
    bad = plan()
    bad.pop(field)
    with pytest.raises(ValueError, match=field):
        build_manifest(bad, config(clips), asset_path=asset,
                       duration_seconds=17.0)


def test_duration_outside_frozen_band_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="duration outside frozen band"):
        make_manifest(tmp_path, duration=7.698)


def test_only_hook_identity_and_script_may_change_inside_cohort(tmp_path):
    first = make_manifest(tmp_path, index=1)
    second = make_manifest(tmp_path, index=2)
    validate_cohort_compatibility([first], second)

    drift = copy.deepcopy(second)
    drift["voice_rate"] = 180
    with pytest.raises(ValueError, match="voice_rate drift"):
        validate_cohort_compatibility([first], drift)

    drift = copy.deepcopy(second)
    drift["clip_set"] = list(reversed(drift["clip_set"]))
    with pytest.raises(ValueError, match="clip_set drift"):
        validate_cohort_compatibility([first], drift)

    drift = copy.deepcopy(second)
    drift["renderer_source_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="renderer_source_sha256 drift"):
        validate_cohort_compatibility([first], drift)


def test_append_is_idempotent_and_conflict_fails(tmp_path):
    row = make_manifest(tmp_path)
    ledger = tmp_path / "cohort-treatments.jsonl"
    assert append_manifest(ledger, row) is True
    assert append_manifest(ledger, row) is False
    changed = json.loads(json.dumps(row, ensure_ascii=False))
    changed["duration_seconds"] = 17.3
    with pytest.raises(ValueError, match="conflicting treatment replay"):
        append_manifest(ledger, changed)


def test_render_treatment_passes_every_frozen_renderer_input(tmp_path):
    clips = [tmp_path / "a.mp4"]
    clips[0].write_bytes(b"clip")
    output = tmp_path / "render.mp4"
    seen = {}

    def fake_renderer(**kwargs):
        seen.update(kwargs)
        output.write_bytes(b"render")
        return {"duration": 17.0, "external_cost_usd": 0,
                "external_effects": []}

    frozen = config(clips)
    frozen["target_duration_seconds"] = {"min": 16.0, "max": 18.0}
    row = render_treatment(plan(), frozen, output=output, renderer=fake_renderer)
    assert seen == {
        "script": row["full_script"], "output": output, "clips": clips,
        "voice": "Kyoko", "voice_rate": 165,
        "caption_style_id": "ass.watercolor.safe-v1",
    }
    assert row["duration_seconds"] == 17.0


def test_selection_requires_ten_unique_exact_verified_treatments(tmp_path):
    rows = [make_manifest(tmp_path, index=index) for index in range(1, 11)]
    selected = verify_cohort_selection(rows, [row["treatment_id"] for row in rows],
                                       min_unique_hooks=10)
    assert selected["accepted_count"] == 10
    assert selected["experiment_count"] == 10
    assert selected["hook_count"] == 10

    with pytest.raises(ValueError, match="exactly 10"):
        verify_cohort_selection(rows, [row["treatment_id"] for row in rows[:9]])
    duplicate_hook = copy.deepcopy(rows)
    duplicate_hook[-1]["hook_id"] = duplicate_hook[0]["hook_id"]
    with pytest.raises(ValueError, match="10 unique hooks"):
        verify_cohort_selection(duplicate_hook,
                                [row["treatment_id"] for row in duplicate_hook],
                                min_unique_hooks=10)
    replicated = verify_cohort_selection(
        duplicate_hook, [row["treatment_id"] for row in duplicate_hook],
        min_unique_hooks=9)
    assert replicated["hook_count"] == 9
