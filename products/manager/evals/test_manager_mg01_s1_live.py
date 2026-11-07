"""MG-01 real company public-site S1 model-vs-incumbent research tests.

Tests deliberately use PUBLIC owned service fixtures; none send notifications,
access customer data, or perform a write to an external provider.
"""
import json
import copy
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from manager_mg01_s1_live import (
    prepare_verified_website_case, render_model_prompt,
    parse_model_decision, score_model_vs_incumbent, independent_check,
)

ROOT=Path(__file__).resolve().parents[1]
NOW=datetime(2026,11,7,17,tzinfo=timezone.utc)


def fixture():
    from manager_core.digital_environment import build_site
    catalog=json.loads((ROOT/"public_goods/service/catalog.json").read_text())
    for x in catalog["resources"]:
        x["reviewed_on"]="2026-11-07"
    with TemporaryDirectory() as tmp:
        p=Path(tmp)
        m=build_site(catalog,p,"f"*40)
        b={name:(p/name).read_bytes() for name in m["files"]}
        raw=(p/"manifest.json").read_bytes()
    return catalog,m,b,raw


class PublicHostS1Tests(unittest.TestCase):
    def test_same_verified_snapshot_for_baseline_and_model(self):
        cat,m,b,raw=fixture()
        case=prepare_verified_website_case(m,b,raw,cat,observed_at=NOW)
        self.assertEqual(case["schema"],"manager.mg01.public_s1.case.v1")
        self.assertEqual(case["manifest_sha256"],sha256(raw).hexdigest())
        self.assertEqual(case["baseline"]["decision"],"REVIEW_ONLY") # build_site fixture lacks aria-current
        self.assertEqual(case["pages"],6)
        self.assertEqual(len(case["features"]["pages"]),6)
        self.assertEqual(case["features"]["source_sha256"],sha256(raw).hexdigest())
        self.assertFalse(case["human_outcome_measured"])
        self.assertEqual(case["world_action"],"NO_ACTION")

    def test_prompt_has_no_expected_label_or_private_fields(self):
        cat,m,b,raw=fixture()
        case=prepare_verified_website_case(m,b,raw,cat,observed_at=NOW)
        prompt=render_model_prompt(case)
        self.assertIn("official",prompt.lower())
        self.assertIn("finance.html",prompt)
        self.assertIn("NO_ACTION",prompt)
        self.assertIn("REVIEW_ONLY",prompt)
        self.assertNotIn("baseline",prompt)
        self.assertNotIn("user_id",prompt)
        self.assertLess(len(prompt),9000)

    def test_model_parser_handles_echoed_prompt_without_leakage(self):
        cat,m,b,raw=fixture()
        prompt=render_model_prompt(prepare_verified_website_case(m,b,raw,cat,observed_at=NOW))
        self.assertEqual(parse_model_decision(prompt+"\nNO_ACTION\nExiting...",prompt),"NO_ACTION")
        self.assertEqual(parse_model_decision(prompt+"\nREVIEW_ONLY\n",prompt),"REVIEW_ONLY")
        self.assertIsNone(parse_model_decision(prompt, prompt))
        self.assertIsNone(parse_model_decision(prompt+"\nNO_ACTION\nREVIEW_ONLY\n",prompt))
        self.assertIsNone(parse_model_decision(prompt+"\nI think NO_ACTION is appropriate",prompt))
        self.assertIsNone(parse_model_decision("NO_ACTION\n",prompt+"\nNO_ACTION\n"))

    def test_cli_partial_prompt_echo_without_assistant_marker_is_safe_to_parse(self):
        cat,m,b,raw=fixture()
        prompt=render_model_prompt(prepare_verified_website_case(m,b,raw,cat,observed_at=NOW))
        # Recorded prior b12137 CLI prints partial public prompt but can omit assistant marker.
        echoed=prompt.replace("<|im_start|>assistant\n", "")
        echoed=echoed.replace("You are an independent quality checker", "You are  an independent quality checker")
        self.assertEqual(parse_model_decision(echoed+"\nNO_ACTION\nExiting...",prompt),"NO_ACTION")

    def test_changed_manifest_fails_closed_before_model(self):
        cat,m,b,raw=fixture()
        damaged=dict(b);damaged["finance.html"]=b"evil"
        with self.assertRaises(ValueError):
            prepare_verified_website_case(m,damaged,raw,cat,observed_at=NOW)
        with self.assertRaises(ValueError):
            prepare_verified_website_case(m,b,b"{}",cat,observed_at=NOW)

    def test_synthetic_broken_link_is_only_review_no_action(self):
        cat,m,b,raw=fixture()
        first=cat["resources"][0]["url"].encode()
        damaged=dict(b)
        damaged["finance.html"]=damaged["finance.html"].replace(first,b"https://example.invalid/a",1)
        changed=dict(m);changed["files"]=dict(m["files"])
        changed["files"]["finance.html"]=sha256(damaged["finance.html"]).hexdigest()
        raw_changed=json.dumps(changed,sort_keys=True).encode()
        case=prepare_verified_website_case(changed,damaged,raw_changed,cat,observed_at=NOW)
        self.assertEqual(case["baseline"]["decision"],"REVIEW_ONLY")
        self.assertEqual(case["world_action"],"NO_ACTION")

    def test_independent_readback_rejects_website_mutation(self):
        cat,m,b,raw=fixture()
        case=prepare_verified_website_case(m,b,raw,cat,observed_at=NOW)
        ok=independent_check(case,lambda:(m,b,raw))
        self.assertEqual(ok["status"],"SAME_PUBLIC_SNAPSHOT")
        modified=dict(m);modified["source_commit"]="e"*40
        self.assertEqual(independent_check(case,lambda:(modified,b,raw))["status"],"READBACK_MISMATCH")

    def test_score_uses_measured_latency_and_no_outcome_claim(self):
        cat,m,b,raw=fixture()
        case=prepare_verified_website_case(m,b,raw,cat,observed_at=NOW)
        report=score_model_vs_incumbent(case,"REVIEW_ONLY",
            model_latency_sec=3.15,baseline_latency_sec=.003,
            host_read_latency_sec=.74,readback={"status":"SAME_PUBLIC_SNAPSHOT"},
            model_sha256="a"*64,gguf_verified=True)
        self.assertEqual(report["status"],"ACTUAL_PUBLIC_HOST_MODEL_SHADOW_TECHNICAL")
        self.assertEqual(report["agreement_with_incumbent"],True)
        self.assertEqual(report["model_latency_seconds"],3.15)
        self.assertEqual(report["host_latency_seconds"],.74)
        self.assertEqual(report["notifications_sent"],0)
        self.assertEqual(report["provider_writes"],0)
        self.assertEqual(report["runner_standard_public_list_price_usd"],0.0)
        self.assertIsNone(report["actual_provider_invoice_usd"])
        self.assertFalse(report["proves_business_value_or_human_welfare"])
        self.assertFalse(report["model_production_approved"])

    def test_invalid_model_output_cannot_claim_agreement(self):
        cat,m,b,raw=fixture()
        case=prepare_verified_website_case(m,b,raw,cat,observed_at=NOW)
        result=score_model_vs_incumbent(case,None,model_latency_sec=3.,baseline_latency_sec=.01,
            host_read_latency_sec=.75,readback={"status":"SAME_PUBLIC_SNAPSHOT"},
            model_sha256="a"*64,gguf_verified=True)
        self.assertEqual(result["status"],"MODEL_OUTPUT_INVALID")
        self.assertIsNone(result["agreement_with_incumbent"])
        result=score_model_vs_incumbent(case,"NO_ACTION",model_latency_sec=3.,
            baseline_latency_sec=.01,host_read_latency_sec=.75,
            readback={"status":"READBACK_MISMATCH"},model_sha256="a"*64,gguf_verified=True)
        self.assertEqual(result["status"],"READBACK_MISMATCH")

    def test_never_accepts_personal_catalog_or_partial_model_sha(self):
        cat,m,b,raw=fixture();cat["email"]="hidden@example.invalid"
        with self.assertRaises(ValueError):
            prepare_verified_website_case(m,b,raw,cat,observed_at=NOW)
        cat,m,b,raw=fixture();case=prepare_verified_website_case(m,b,raw,cat,observed_at=NOW)
        with self.assertRaises(ValueError):
            score_model_vs_incumbent(case,"NO_ACTION",model_latency_sec=0.,
                baseline_latency_sec=0.,host_read_latency_sec=0.,
                readback={"status":"SAME_PUBLIC_SNAPSHOT"},model_sha256="wrong",gguf_verified=True)

if __name__=="__main__":
    unittest.main()
