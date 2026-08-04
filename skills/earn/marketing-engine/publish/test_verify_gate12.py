import pathlib
import sqlite3
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from verify_gate12 import verify_gate12


def test_gate12_reports_real_scheduled_production_receipt(tmp_path):
    result = verify_gate12(engine=HERE.parent, evidence_root=tmp_path)
    assert result["implementation_status"] == "verified"
    assert result["evidence_status"] == "production_evidence_complete"
    assert result["external_effects"] == 3
    assert result["shadow_status"] == "shadow_valid"
    assert result["provider_upload_calls"] == 1
    assert result["provider_create_calls"] == 1
    assert result["provider_promote_calls"] == 1
    assert result["preview_media"]["video_codec"] == "h264"
    assert result["preview_media"]["audio_codec"] == "aac"
    assert result["preview_media"]["width"] == 720
    assert result["preview_media"]["height"] == 1280
    assert result["publisher_route"]["route_ready"] is True
    assert result["publisher_route"]["blockers"] == []
    assert result["native_candidate_scan"]["api_responses_observed"] == 2
    assert result["native_candidate_scan"]["profile_items_observed"] == 33
    assert result["native_candidate_scan"]["external_mutations"] == 0
    assert result["preflight_blocker"] is None
    assert result["visual_approval_status"] == "accepted"
    assert result["production_post_id"] == "cmsaselv6070sqn0yp7oix7yd"
    assert result["native_post_id"] == "7669159327655054613"
    assert result["native_post_url"] == "https://www.tiktok.com/@obou_anicca/video/7669159327655054613"
    with sqlite3.connect(tmp_path / "shadow-v2.sqlite3") as db:
        assert db.execute("SELECT COUNT(*) FROM intents").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM attempts").fetchone()[0] == 0
