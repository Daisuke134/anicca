#!/usr/bin/env python3
"""Verify Gate 12 implementation and its honest pre-production blocker."""

from __future__ import annotations

import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ENGINE = HERE.parent
sys.path.insert(0, str(ENGINE / "measure"))

from attribution import campaign_token  # noqa: E402
from intent_store import IntentStore, build_intent  # noqa: E402
from postiz_adapter import PostizAdapter  # noqa: E402
from preflight import probe_media, validate_media, validate_preflight  # noqa: E402


def verify_gate12(*, engine: pathlib.Path = ENGINE,
                  evidence_root: pathlib.Path | None = None) -> dict:
    engine = pathlib.Path(engine)
    root = pathlib.Path(evidence_root) if evidence_root is not None else engine / "evidence/publish/gate12"
    asset = engine / "evidence/renderers/gate12-watercolor-preview.mp4"
    publication_id = "experiment.preview-gate12"
    token = campaign_token("ebook-ja", publication_id)
    intent = build_intent(
        experiment_id="experiment.preview-gate12", creative_id="creative.preview-gate12",
        product_id="ebook-ja", account_id="tiktok.obou_anicca",
        hook_id="hook.tiktok.7468922143619812626.002",
        renderer_id="watercolor-monk", adapter="postiz", asset_path=asset,
        caption=("距離を変えるとき。『アニッチャ・リセット』を読む "
                 f"https://aniccaai.com/go/{token} {token}"),
        attribution_token=token, scheduled_at="2026-08-02T01:00:00Z",
        integration_id="cmo5s4edx00vgn10ygnu34a0n", platform="tiktok",
        native_handle="obou_anicca",
        provider_settings={"__type": "tiktok", "title": "", "privacy_level": "PUBLIC_TO_EVERYONE",
            "duet": False, "stitch": False, "comment": True, "autoAddMusic": "no",
            "brand_content_toggle": False, "brand_organic_toggle": False,
            "video_made_with_ai": True, "content_posting_method": "DIRECT_POST"},
        visual_approval_id="visual.accepted.gate12-preview",
    )
    media = validate_media(probe_media(asset))
    route_doc = json.loads((engine / "evidence/publish/gate12/live-route-check-2026-08-02.json").read_text(
        encoding="utf-8"))
    routes = [row for row in route_doc.get("accounts", [])
              if row.get("account_id") == intent["account_id"]]
    if (route_doc.get("external_mutations") != 0 or len(routes) != 1 or
            routes[0].get("route_ready") is not True or routes[0].get("blockers") != []):
        raise ValueError("Gate 12 publisher-route evidence invalid")
    candidate_scan = json.loads((engine /
        "evidence/publish/gate12/prepublication-native-candidate-scan.json").read_text(
            encoding="utf-8"))
    if (candidate_scan.get("publish_key") != intent["publish_key"] or
            candidate_scan.get("external_mutations") != 0 or
            candidate_scan.get("api_responses_observed", 0) <= 0):
        raise ValueError("Gate 12 native-candidate scan evidence invalid")
    blocker = None
    try:
        validate_preflight(intent, engine=engine,
                           approvals_path=engine / "evidence/renderers/gate12-visual-approvals.jsonl")
    except ValueError as exc:
        blocker = str(exc)
    store = IntentStore(root / "shadow-v2.sqlite3")
    registration = store.register(intent)
    lease = store.acquire(intent["publish_key"], owner="gate12-verifier",
                          now="2026-08-02T00:00:00Z", ttl_seconds=300)
    if lease is None:
        raise ValueError("Gate 12 shadow lease unavailable")
    shadow = PostizAdapter(store, client=None).shadow(
        intent["publish_key"], "gate12-verifier", lease["fence"],
        now="2026-08-02T00:00:00Z")
    production_path = engine / "evidence/publish/gate12/production.sqlite3"
    production_intent_path = engine / "evidence/publish/gate12/production-intent.json"
    production = None
    attempts = []
    if production_path.exists() and production_intent_path.exists():
        production_intent = json.loads(production_intent_path.read_text(encoding="utf-8"))
        production_store = IntentStore(production_path)
        production = production_store.get(production_intent["publish_key"])
        attempts = production_store.attempts_for(production_intent["publish_key"])
    accepted_operations = {row["operation"] for row in attempts if row["state"] == "accepted"}
    native_complete = bool(production and production.get("native_post_id") and
                           production.get("native_post_url"))
    evidence_status = ("production_evidence_complete" if native_complete else
                       "scheduled_pending_native_receipt" if production and
                       production.get("provider_post_id") else
                       "ready_for_production")
    result = {
        "schema_version": "marketing.gate12-verification.v1",
        "implementation_status": "verified",
        "evidence_status": evidence_status,
        "preview_asset": str(asset),
        "preview_sha256": intent["asset_sha256"],
        "preview_media": media,
        "preview_telegram_message_id": 5113,
        "publish_key": intent["publish_key"],
        "preflight_blocker": blocker,
        "account_status": "approved_active",
        "visual_approval_status": "accepted" if blocker is None else "pending_owner",
        "publisher_route": routes[0],
        "native_candidate_scan": candidate_scan,
        "shadow_status": shadow["status"],
        "shadow_intent_created": registration["created"],
        "shadow_lease_fence": lease["fence"],
        "shadow_request_sha256": shadow["request_sha256"],
        "provider_upload_calls": int("upload_media" in accepted_operations),
        "provider_create_calls": int("create_draft" in accepted_operations),
        "provider_promote_calls": int("promote" in accepted_operations),
        "external_effects": len(accepted_operations),
        "production_post_receipt": production.get("provider_receipt") if production else None,
        "production_post_id": production.get("provider_post_id") if production else None,
        "native_post_id": production.get("native_post_id") if production else None,
        "native_post_url": production.get("native_post_url") if production else None,
    }
    root.mkdir(parents=True, exist_ok=True)
    (root / "verification.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(verify_gate12(), ensure_ascii=False, sort_keys=True))
