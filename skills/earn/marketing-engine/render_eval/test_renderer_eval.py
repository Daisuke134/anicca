import hashlib
import json
import pathlib
import subprocess
import sys

import pytest

HERE = pathlib.Path(__file__).resolve().parent
ENGINE = HERE.parent
sys.path.insert(0, str(HERE))

from renderer_eval import (append_receipt, build_fixtures, load_fixtures,
                           validate_fixture, validate_receipt)


def test_frozen_fixture_set_is_five_per_ebook_and_owned_assets_match():
    fixtures = load_fixtures(HERE / "renderer-fixtures.json")
    assert len(fixtures) == 10
    assert [row["product_id"] for row in fixtures].count("ebook-en") == 5
    assert [row["product_id"] for row in fixtures].count("ebook-ja") == 5
    assert len({row["fixture_id"] for row in fixtures}) == 10
    for row in fixtures:
        validate_fixture(row, engine=ENGINE, check_asset=True)
        asset = pathlib.Path(row["source_asset"])
        assert hashlib.sha256(asset.read_bytes()).hexdigest() == row["source_sha256"]
        assert (row["width"], row["height"]) == (720, 1280)


def test_fixture_builder_is_deterministic_and_product_isolated():
    first = build_fixtures(ENGINE)
    second = build_fixtures(ENGINE)
    assert first == second
    for row in first:
        assert row["hook_id"].startswith("hook.")
        assert row["account_id"] in {
            "tiktok.monk_anicca", "tiktok.obou_anicca"
        }
        assert row["language"] == ("en" if row["product_id"] == "ebook-en" else "ja")


def test_invalid_cross_product_fixture_fails_closed():
    row = build_fixtures(ENGINE)[0] | {"product_id": "ebook-ja"}
    with pytest.raises(ValueError, match="account product mismatch"):
        validate_fixture(row, engine=ENGINE, check_asset=False)


def test_receipts_are_append_only_and_exact_replay_dedupes(tmp_path):
    fixture = build_fixtures(ENGINE)[0]
    output = tmp_path / "clip.mp4"
    output.write_bytes(b"video")
    receipt = {
        "schema_version": "marketing.renderer-attempt.v1",
        "attempt_id": "attempt.test",
        "fixture_id": fixture["fixture_id"],
        "renderer_id": "safety-local",
        "renderer_version": "ffmpeg-test",
        "license": "local-tools-and-owned-inputs",
        "status": "success",
        "reason": None,
        "started_at": "2026-08-01T00:00:00Z",
        "finished_at": "2026-08-01T00:00:01Z",
        "latency_ms": 1000,
        "cost_usd": 0,
        "input_sha256": fixture["source_sha256"],
        "output_path": str(output),
        "output_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "probe": {"width": 720, "height": 1280, "duration": 8.0,
                  "video_codec": "h264", "audio_codec": "aac"},
        "publication_effects": [],
    }
    validate_receipt(receipt, fixture, check_output=True)
    ledger = tmp_path / "attempts.jsonl"
    assert append_receipt(ledger, receipt) is True
    assert append_receipt(ledger, receipt) is False
    assert len(ledger.read_text().splitlines()) == 1
    with pytest.raises(ValueError, match="conflicting replay"):
        append_receipt(ledger, receipt | {"cost_usd": 1})


def test_cli_check_rejects_missing_render_outputs(tmp_path):
    result = subprocess.run(
        [sys.executable, str(HERE / "renderer_eval.py"), "verify",
         "--fixtures", str(HERE / "renderer-fixtures.json"),
         "--receipts", str(tmp_path / "missing.jsonl")],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "missing successful safety receipt" in result.stderr
