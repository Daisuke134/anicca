"""Zero-UI Shadow offline boundary: no invisible personal-data surveillance or effects."""
from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import patch
from manager_core.authority import Grant, AuthorityVerifier
from manager_core.zero_ui_shadow_v0 import evaluate_shadow

T=datetime(2026,11,7,15,tzinfo=timezone.utc)
H="a"*64

def consent():
    verifier=AuthorityVerifier({"host-integration":b"pseudofixed-fixture-issuer-key-material"})
    grant=Grant(grant_id="fixture-1",issuer="host-integration",domain="manager",
                action="shadow.observe",target="public_aggregate",limit=1.,
                not_before=T-timedelta(hours=1),expires_at=T+timedelta(hours=1))
    return verifier,grant,verifier.sign_for_fixture(grant)

def signal():
    return {"source":"public_aggregate","group_size":971,
            "source_sha256":H,"observed_at":T.isoformat()}

def model():
    return {"source":"trained_public_aggregate_head","domain":"HBCP_PUBLISHED_SMOKING_CESSATION_RCT_ARMS",
            "model_sha256":"b"*64,"prediction":15.87,
            "train_mean_baseline":16.52,
            "promoted_for_real_users":False}

class AmbientShadowTests(unittest.TestCase):
    def test_default_disabled_no_authority_or_side_effect(self):
        receipt=evaluate_shadow(signal(),model(),enabled=False,at=T)
        self.assertEqual(receipt["status"],"NO_ACTION")
        self.assertEqual(receipt["reason"],"SHADOW_DISABLED")
        self.assertEqual(receipt["notifications_sent"],0)
        self.assertEqual(receipt["provider_writes"],0)

    def test_approved_fixture_public_source_is_shadow_only_no_ui(self):
        verifier,grant,signature=consent()
        with patch("urllib.request.urlopen",side_effect=AssertionError("network forbidden")):
            r=evaluate_shadow(signal(),model(),enabled=True,at=T,verifier=verifier,grant=grant,signature=signature)
        self.assertEqual(r["status"],"SHADOW_ONLY")
        self.assertEqual(r["world_action"],"NO_ACTION")
        self.assertFalse(r["requires_extra_ui_or_prompt"])
        self.assertEqual(r["provider_writes"],0)
        self.assertEqual(r["notifications_sent"],0)
        self.assertFalse(r["personal_profile_created"])
        self.assertEqual(r["comparison"]["candidate"],15.87)
        self.assertEqual(r["comparison"]["baseline"],16.52)

    def test_unverified_scope_rejected_without_leaking_model(self):
        r=evaluate_shadow(signal(),model(),enabled=True,at=T)
        self.assertEqual(r["status"],"NO_ACTION")
        self.assertNotIn("comparison",r)

    def test_revoked_or_expired_scope_rejected(self):
        verifier,grant,signature=consent()
        revoked=AuthorityVerifier({"host-integration":b"pseudofixed-fixture-issuer-key-material"},revoked={"fixture-1"})
        r=evaluate_shadow(signal(),model(),enabled=True,at=T,verifier=revoked,grant=grant,signature=signature)
        self.assertEqual(r["status"],"NO_ACTION")
        r=evaluate_shadow(signal(),model(),enabled=True,at=T+timedelta(hours=3),verifier=verifier,grant=grant,signature=signature)
        self.assertEqual(r["status"],"NO_ACTION")

    def test_wrong_domain_and_scope_and_tampered_signature_rejected(self):
        verifier,grant,signature=consent()
        wrong=Grant(grant_id="x",issuer="host-integration",domain="manager",
                    action="notify.user",target="public_aggregate",limit=1.,
                    not_before=T-timedelta(hours=1),expires_at=T+timedelta(hours=1))
        invalid=verifier.sign_for_fixture(wrong)
        r=evaluate_shadow(signal(),model(),enabled=True,at=T,verifier=verifier,grant=wrong,signature=invalid)
        self.assertEqual(r["status"],"NO_ACTION")
        r=evaluate_shadow(signal(),model(),enabled=True,at=T,verifier=verifier,grant=grant,signature="wrong")
        self.assertEqual(r["status"],"NO_ACTION")

    def test_personal_history_or_small_group_rejected(self):
        v,g,signature=consent()
        for s in [dict(signal(),source="personal_history"),
                  dict(signal(),group_size=1),
                  dict(signal(),group_size=29),
                  dict(signal(),account_id="private-identity")]:
            r=evaluate_shadow(s,model(),enabled=True,at=T,verifier=v,grant=g,signature=signature)
            self.assertEqual(r["status"],"NO_ACTION")
            self.assertEqual(r["notifications_sent"],0)

    def test_future_or_stale_observation_rejected(self):
        v,g,signature=consent()
        for stamp in [T+timedelta(minutes=1),T-timedelta(days=8)]:
            r=evaluate_shadow(dict(signal(),observed_at=stamp.isoformat()),model(),enabled=True,at=T,verifier=v,grant=g,signature=signature)
            self.assertEqual(r["status"],"NO_ACTION")

    def test_malicious_model_claims_cannot_authorize_action(self):
        v,g,signature=consent()
        bad=dict(model(),promoted_for_real_users=True)
        r=evaluate_shadow(signal(),bad,enabled=True,at=T,verifier=v,grant=g,signature=signature)
        self.assertEqual(r["status"],"NO_ACTION")
        for key in ("model_benefit_proven","real_world_effect"):
            self.assertNotIn(key,r)

    def test_no_identifying_data_or_raw_context_in_result(self):
        v,g,signature=consent()
        r=evaluate_shadow(signal(),model(),enabled=True,at=T,verifier=v,grant=g,signature=signature)
        self.assertNotIn("grant_id",str(r))
        self.assertNotIn("fixture-1",str(r))
        self.assertNotIn("personal_history",str(r))
        self.assertNotIn("host-integration",str(r))

if __name__=="__main__":
    unittest.main()
