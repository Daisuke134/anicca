"""G3 host read-only observation: no effects, no personal data, source-bound checks."""
import copy
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock
from manager_core.digital_environment import build_site
from manager_core.zero_ui_host_shadow_v1 import run_public_host_shadow

ROOT=Path(__file__).resolve().parents[1]
NOW=datetime(2026,11,7,18,tzinfo=timezone.utc)


def source_fixture():
    cat=json.loads((ROOT/"public_goods/service/catalog.json").read_text())
    for item in cat["resources"]:
        item["reviewed_on"]=datetime.now(timezone.utc).date().isoformat()
    with TemporaryDirectory() as td:
        out=Path(td)
        manifest=build_site(cat,out,"f"*40)
        bodies={name:(out/name).read_bytes() for name in manifest["files"]}
        raw=(out/"manifest.json").read_bytes()
    return cat,manifest,bodies,raw


class PublicHostShadowTests(unittest.TestCase):
    def test_disabled_never_reads_external_public_site(self):
        fetch=Mock(side_effect=AssertionError("network attempted"))
        out=run_public_host_shadow(enabled=False,read_snapshot=fetch)
        self.assertEqual(out["status"],"NO_ACTION")
        self.assertEqual(out["reason"],"DISABLED")
        self.assertEqual(out["external_writes"],0)
        self.assertEqual(out["notifications_sent"],0)
        fetch.assert_not_called()

    def test_verified_six_pages_same_input_baseline_and_candidate(self):
        cat,manifest,bodies,raw=source_fixture()
        fetch=Mock(return_value=(manifest,bodies,raw))
        result=run_public_host_shadow(enabled=True,read_snapshot=fetch,catalog=cat,observed_at=NOW)
        self.assertEqual(result["status"],"PUBLIC_HOST_READONLY_VERIFIED")
        self.assertEqual(result["page_count"],6)
        self.assertEqual(result["technical_proof"],"P2_ARTIFACT_ONLY")
        self.assertEqual(result["world_action"],"NO_ACTION")
        self.assertEqual(result["external_writes"],0)
        self.assertEqual(result["notifications_sent"],0)
        self.assertFalse(result["personal_data_accessed"])
        self.assertEqual(result["baseline"]["context_sha256"],result["candidate"]["context_sha256"])
        self.assertEqual(result["baseline"]["decision"],"NO_ACTION")
        self.assertEqual(result["candidate"]["decision"],"REVIEW_ONLY")
        self.assertEqual(result["candidate"]["proposed_action"],"ADD_CURRENT_PAGE_CUE")
        self.assertFalse(result["candidate"]["authorized_execution"])
        self.assertFalse(result["full_s1_model_vs_incumbent_proven"])
        self.assertFalse(result["human_benefit_measured"])
        fetch.assert_called_once_with()

    def test_page_hash_tamper_fails_closed(self):
        cat,manifest,bodies,raw=source_fixture()
        bodies["finance.html"]=b"malicious site content"
        with self.assertRaises(ValueError):
            run_public_host_shadow(enabled=True,read_snapshot=lambda:(manifest,bodies,raw),catalog=cat,observed_at=NOW)

    def test_manifest_raw_bytes_tamper_fails_closed(self):
        cat,manifest,bodies,raw=source_fixture()
        raw=b"{}"
        with self.assertRaises(ValueError):
            run_public_host_shadow(enabled=True,read_snapshot=lambda:(manifest,bodies,raw),catalog=cat,observed_at=NOW)

    def test_changed_link_can_only_be_proposed_for_review(self):
        cat,manifest,bodies,raw=source_fixture()
        modified=dict(bodies)
        old=cat["resources"][0]["url"]
        modified["finance.html"]=modified["finance.html"].replace(old.encode(),b"https://example.invalid/link",1)
        new_manifest=dict(manifest)
        new_manifest["files"]=dict(manifest["files"])
        new_manifest["files"]["finance.html"]=sha256(modified["finance.html"]).hexdigest()
        new_raw=json.dumps(new_manifest,sort_keys=True).encode()
        r=run_public_host_shadow(enabled=True,read_snapshot=lambda:(new_manifest,modified,new_raw),catalog=cat,observed_at=NOW)
        self.assertEqual(r["candidate"]["decision"],"REVIEW_ONLY")
        self.assertFalse(r["candidate"]["authorized_execution"])
        self.assertEqual(r["world_action"],"NO_ACTION")

    def test_no_user_identity_or_covert_tracking_from_catalog(self):
        cat,manifest,bodies,raw=source_fixture()
        cat["profile_id"]="unknown-person"
        with self.assertRaises(ValueError):
            run_public_host_shadow(enabled=True,read_snapshot=lambda:(manifest,bodies,raw),catalog=cat,observed_at=NOW)

    def test_reject_unreviewed_or_future_catalog(self):
        cat,manifest,bodies,raw=source_fixture()
        cat["resources"][0]["reviewed_on"]="2001-01-01"
        with self.assertRaises(ValueError):
            run_public_host_shadow(enabled=True,read_snapshot=lambda:(manifest,bodies,raw),catalog=cat,observed_at=NOW)


if __name__=="__main__":
    unittest.main()
