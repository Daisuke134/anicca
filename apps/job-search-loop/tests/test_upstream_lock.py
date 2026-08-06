import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "config" / "upstream-lock.v1.json"
ADOPTION = ROOT / "config" / "upstream-adoption.v1.json"
MASTER_DELTA = ROOT / "config" / "upstream-master-delta.v1.json"
RUNTIME_ADOPTION = ROOT / "config" / "upstream-runtime-adoption.v1.json"
APPLYPILOT_ADOPTION = ROOT / "config" / "applypilot-adoption.v1.json"


class UpstreamLockTests(unittest.TestCase):
    def test_applypilot_commit_is_content_addressed_and_agpl_licensed(self):
        data = json.loads(LOCK.read_text(encoding="utf-8"))
        upstream = data["upstreams"]["applypilot"]

        self.assertEqual(upstream["repository"], "https://github.com/Pickle-Pixel/ApplyPilot")
        self.assertEqual(upstream["package_version"], "0.3.0")
        self.assertEqual(upstream["commit_sha"], "4a8d521f67f5139811c0a910ef37410f8e6d836a")
        self.assertEqual(upstream["tree_sha"], "a81d5265f4313aeadc9da0099974ea2beeb90657")
        self.assertEqual(upstream["file_count"], 40)
        self.assertEqual(upstream["license"]["spdx"], "AGPL-3.0-only")
        self.assertEqual(upstream["license"]["blob_sha"], "be3f7b28e564e7dd05eaf59d64adba1a4065ac0e")
        self.assertEqual(
            upstream["license"]["content_sha256"],
            "0d96a4ff68ad6d4b6f1f30f713b18d5184912ba8dd389f86aa7710db079abcb0",
        )
        self.assertEqual(
            upstream["archive"]["content_sha256"],
            "951f7cf084023ddb4648496f29987ede848e33c64fbaf36468880dc3557bc9d1",
        )

    def test_applypilot_adoption_ledger_separates_planned_agpl_code_from_mit_monorepo(self):
        data = json.loads(APPLYPILOT_ADOPTION.read_text(encoding="utf-8"))

        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(data["upstream_commit"], "4a8d521f67f5139811c0a910ef37410f8e6d836a")
        self.assertEqual(data["license_boundary"]["upstream_spdx"], "AGPL-3.0-only")
        self.assertEqual(data["license_boundary"]["monorepo_spdx"], "MIT")
        self.assertEqual(data["license_boundary"]["derived_code_root"], "vendor/applypilot-derived")
        self.assertFalse(data["license_boundary"]["relicense_unrelated_monorepo"])
        self.assertEqual(data["copied_paths"], [])
        self.assertEqual(
            data["implemented_paths"],
            [
                {
                    "local_path": "job_search_loop/jobspy_adapter.py",
                    "upstream_contract_paths": ["src/applypilot/discovery/jobspy.py"],
                    "copied_source_lines": 0,
                    "license": "MIT",
                    "owner_task": "L-49K5B1",
                }
            ],
        )

        components = {item["id"]: item for item in data["components"]}
        self.assertEqual(
            set(components),
            {
                "jobspy_discovery", "workday_discovery", "smartextract_discovery",
                "detail_enrichment", "site_patterns", "generic_form_classification",
                "model_reported_applied", "permission_bypass", "manual_ats_skip",
                "applypilot_database", "applypilot_scheduler", "applypilot_browser_owner",
            },
        )
        for item in components.values():
            self.assertIn(item["decision"], {"adapt", "supersede"})
            self.assertTrue(item["source_paths"])
            self.assertTrue(item["local_authority"].strip())
            self.assertIn(item["owner_task"], {"L-49K5B", "L-49K5C"})
        for component_id in {
            "model_reported_applied", "permission_bypass", "manual_ats_skip",
            "applypilot_database", "applypilot_scheduler", "applypilot_browser_owner",
        }:
            self.assertEqual(components[component_id]["decision"], "supersede")

    def test_ai_job_search_v130_is_content_addressed_and_licensed(self):
        data = json.loads(LOCK.read_text(encoding="utf-8"))
        upstream = data["upstreams"]["mads-lorentzen-ai-job-search"]

        self.assertEqual(upstream["repository"], "https://github.com/MadsLorentzen/ai-job-search")
        self.assertEqual(upstream["release"], "v1.3.0")
        self.assertEqual(upstream["commit_sha"], "a8a10011126f443e0041bb4924a1106c2f7f7536")
        self.assertEqual(upstream["tree_sha"], "dd84a322610becd7c46b74f823d1e4ebc1c8432d")
        self.assertEqual(upstream["license"]["spdx"], "MIT")
        self.assertEqual(upstream["license"]["blob_sha"], "dd86a45cbf864dd2cd82df06064cb8cc9aef995a")
        self.assertEqual(
            upstream["license"]["content_sha256"],
            "accbf0accb87b7b905dd7ee0c7013075f0453637acf354ddae6fc0e4d8282e8e",
        )
        self.assertEqual(
            upstream["sources"]["release"],
            "https://github.com/MadsLorentzen/ai-job-search/releases/tag/v1.3.0",
        )
        self.assertEqual(
            upstream["sources"]["license"],
            "https://github.com/MadsLorentzen/ai-job-search/blob/v1.3.0/LICENSE",
        )

    def test_career_ops_v1250_is_content_addressed_and_licensed(self):
        data = json.loads(LOCK.read_text(encoding="utf-8"))
        self.assertIn("santifer-career-ops", data["upstreams"])
        upstream = data["upstreams"]["santifer-career-ops"]

        self.assertEqual(upstream["repository"], "https://github.com/santifer/career-ops")
        self.assertEqual(upstream["package_version"], "1.25.0")
        self.assertEqual(upstream["release"], "career-ops-v1.25.0")
        self.assertEqual(upstream["commit_sha"], "ae1a92dd1a4d299e637ce5d96f18e79f743a50ba")
        self.assertEqual(upstream["tree_sha"], "f0003d2870570efbb4595997d85bcb16e9586814")
        self.assertEqual(upstream["file_count"], 965)
        self.assertEqual(
            upstream["archive"],
            {
                "url": "https://api.github.com/repos/santifer/career-ops/tarball/ae1a92dd1a4d299e637ce5d96f18e79f743a50ba",
                "content_sha256": "65762e626ac69d83880b361a882ea4714387025940643ed03b4cd2481b555234",
            },
        )
        self.assertEqual(upstream["license"]["spdx"], "MIT")
        self.assertEqual(upstream["license"]["blob_sha"], "89c4ce0ad6b1db98d827ddd9725da5efdff55997")
        self.assertEqual(
            upstream["license"]["content_sha256"],
            "51989d2589b2aa87ca6cbb253391bcb476a21cbafdc71eea4410548538510870",
        )
        self.assertEqual(
            upstream["files"],
            {
                "LICENSE": {
                    "blob_sha": "89c4ce0ad6b1db98d827ddd9725da5efdff55997",
                    "content_sha256": "51989d2589b2aa87ca6cbb253391bcb476a21cbafdc71eea4410548538510870",
                    "size": 1090,
                },
                "README.md": {
                    "blob_sha": "bd87484929cdd45d611c3d2860e6f658730d427d",
                    "content_sha256": "0293b375b7cea0d8f7c70ea65a6567c5071317d9262a6ff4eae562188b17a4ec",
                    "size": 31737,
                },
                "docs/APPLY_AUTOFILL.md": {
                    "blob_sha": "43afc62bd3c2fb7ff8d939e5f3d115c01e2f8ee6",
                    "content_sha256": "05e2734a6f80b89adfa0297c41fa56e2c8f188b6c240b363a65a21ac98559551",
                    "size": 4186,
                },
                "package.json": {
                    "blob_sha": "aa157b12e6b6c26da9ac912ad348111a5cbdd9f4",
                    "content_sha256": "c30dd080f4e1b54520dea0779d79cdc08f61512702000d8047276a5301708a77",
                    "size": 3635,
                },
            },
        )
        self.assertEqual(
            upstream["sources"]["release"],
            "https://github.com/santifer/career-ops/releases/tag/career-ops-v1.25.0",
        )
        self.assertEqual(
            upstream["sources"]["license"],
            "https://github.com/santifer/career-ops/blob/career-ops-v1.25.0/LICENSE",
        )

    def test_browser_use_0137_is_content_addressed_licensed_and_dependency_locked(self):
        data = json.loads(LOCK.read_text(encoding="utf-8"))
        self.assertIn("browser-use", data["upstreams"])
        upstream = data["upstreams"]["browser-use"]

        self.assertEqual(upstream["repository"], "https://github.com/browser-use/browser-use")
        self.assertEqual(upstream["package_version"], "0.13.7")
        self.assertEqual(upstream["release"], "0.13.7")
        self.assertEqual(upstream["commit_sha"], "f0aa3a8bb03779c71a5aa262d389e3bfe6b77cdc")
        self.assertEqual(upstream["tree_sha"], "6ebd132305353e4e62d8b7f61736ccbcbb377ab8")
        self.assertEqual(upstream["file_count"], 480)
        self.assertEqual(upstream["license"]["spdx"], "MIT")
        self.assertEqual(upstream["license"]["blob_sha"], "1ea3836ce58a4cd32c90c0b4f4e736d840d23780")
        self.assertEqual(
            upstream["files"]["examples/use-cases/apply_to_job.py"]["content_sha256"],
            "95a9e9719a77060d5c1d2f482089fa3f3d993ec285ec9447314e120683c7979c",
        )
        self.assertEqual(upstream["upstream_dependency_lock"], "absent")

        dependency_lock = upstream["local_dependency_lock"]
        self.assertEqual(dependency_lock["resolver"], "uv 0.10.7")
        self.assertEqual(dependency_lock["python_version"], "3.12")
        self.assertEqual(dependency_lock["platform"], "aarch64-apple-darwin")
        self.assertTrue(dependency_lock["no_header"])
        self.assertTrue(dependency_lock["no_annotate"])
        lock_path = ROOT / dependency_lock["path"]
        self.assertTrue(lock_path.is_file())
        self.assertEqual(
            hashlib.sha256(lock_path.read_bytes()).hexdigest(),
            dependency_lock["content_sha256"],
        )
        self.assertEqual(
            upstream["consumed_contracts"],
            {
                "actions": [
                    "browser_use/tools/registry/service.py",
                    "browser_use/tools/registry/views.py",
                    "browser_use/tools/service.py",
                ],
                "history": ["browser_use/agent/views.py"],
                "screenshots": [
                    "browser_use/agent/views.py",
                    "browser_use/browser/session.py",
                    "browser_use/tools/service.py",
                ],
                "job_application_example": ["examples/use-cases/apply_to_job.py"],
            },
        )

    def test_temporal_server_and_python_sdk_are_content_addressed_and_rollback_pinned(self):
        data = json.loads(LOCK.read_text(encoding="utf-8"))
        server = data["upstreams"]["temporal-server"]
        sdk = data["upstreams"]["temporal-sdk-python"]

        self.assertEqual(server["repository"], "https://github.com/temporalio/temporal")
        self.assertEqual(server["release"], "v1.31.2")
        self.assertEqual(server["commit_sha"], "19a774302c613da9adc4436ab14278ccdca8e0a5")
        self.assertEqual(server["tree_sha"], "ffd7f02fe0639e9faf2b97702eb3ea0944bd48de")
        self.assertEqual(server["license"]["spdx"], "MIT")
        self.assertIn("darwin_arm64", server["artifacts"])
        self.assertIn("checksums", server["artifacts"])
        self.assertEqual(server["rollback"]["strategy"], "local_binary_previous_pin")

        self.assertEqual(sdk["repository"], "https://github.com/temporalio/sdk-python")
        self.assertEqual(sdk["release"], "1.31.0")
        self.assertEqual(sdk["commit_sha"], "84b519e0ff407b049da88ac7d1711f110494ff4d")
        self.assertEqual(sdk["tree_sha"], "6ca7d581e9e0bea3f19a0e1bf5f3a5ef9fec6d21")
        self.assertEqual(sdk["license"]["spdx"], "MIT")
        self.assertEqual(sdk["package"], "temporalio==1.31.0")
        self.assertEqual(
            set(sdk["consumed_contracts"]),
            {"workflow", "activity", "worker", "schedule", "client", "testing"},
        )
        self.assertEqual(sdk["rollback"]["strategy"], "uv_lock_previous_pin")

    def test_telemetry_runtime_is_content_addressed_licensed_and_hash_locked(self):
        data = json.loads(LOCK.read_text(encoding="utf-8"))
        python = data["upstreams"]["opentelemetry-python"]
        collector = data["upstreams"]["opentelemetry-collector-contrib"]
        backend = data["upstreams"]["grafana-otel-lgtm"]

        self.assertEqual(python["release"], "v1.44.0")
        self.assertEqual(python["commit_sha"], "53a5a40c9604583c501bcf13970a635f00e62df4")
        self.assertEqual(python["license"]["spdx"], "Apache-2.0")
        runtime_lock = python["local_dependency_lock"]
        self.assertEqual(runtime_lock["requirements"], [
            "opentelemetry-sdk==1.44.0",
            "opentelemetry-exporter-otlp-proto-http==1.44.0",
        ])
        lock_path = ROOT / runtime_lock["path"]
        self.assertTrue(lock_path.is_file())
        self.assertEqual(hashlib.sha256(lock_path.read_bytes()).hexdigest(), runtime_lock["content_sha256"])

        self.assertEqual(collector["release"], "v0.158.0")
        self.assertEqual(collector["license"]["spdx"], "Apache-2.0")
        self.assertEqual(collector["artifacts"]["darwin_arm64"]["content_sha256"], "e2b68ae0eeb165795c1c9aecc29d24fe91790dd6ec7d200dd7e5a8b226a2f636")

        self.assertEqual(backend["release"], "v0.30.0")
        self.assertEqual(backend["license"]["spdx"], "Apache-2.0")
        self.assertEqual(backend["image"], "grafana/otel-lgtm@sha256:46ca028e294bd728e8e930a28e887f640a8f2a9533cc283f79bcc6ab73d2ffd8")

    def test_browser_use_and_temporal_runtime_contracts_have_explicit_authorities(self):
        data = json.loads(RUNTIME_ADOPTION.read_text(encoding="utf-8"))
        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(
            data["pins"],
            {
                "browser_use": "0.13.7@f0aa3a8bb03779c71a5aa262d389e3bfe6b77cdc",
                "temporal_server": "1.31.2@19a774302c613da9adc4436ab14278ccdca8e0a5",
                "temporal_sdk_python": "1.31.0@84b519e0ff407b049da88ac7d1711f110494ff4d",
            },
        )
        components = {item["id"]: item for item in data["components"]}
        expected = {
            "browser_session", "browser_actions", "browser_history", "browser_screenshots",
            "browser_best_guess_answers", "browser_self_reported_success",
            "browser_unrestricted_submit", "browser_captcha_handling", "browser_generic_retry",
            "temporal_workflow", "temporal_activity", "temporal_schedule", "temporal_signal",
            "temporal_cancellation", "temporal_heartbeat", "temporal_history",
        }
        self.assertEqual(set(components), expected)
        self.assertEqual(len(data["components"]), len(expected))
        for item in components.values():
            self.assertIn(item["decision"], {"reuse", "adapt", "supersede"})
            self.assertTrue(item["source_paths"])
            self.assertTrue(item["local_authority"].strip())
            self.assertTrue(item["parity_tests"])
            for parity_test in item["parity_tests"]:
                self.assertTrue((ROOT / parity_test).is_file(), parity_test)
            self.assertRegex(item["owner_task"], r"^L-49K0[A-Z][0-9]?$|^L-49K0D2$")
        for component_id in {
            "browser_best_guess_answers", "browser_self_reported_success",
            "browser_unrestricted_submit", "browser_captcha_handling", "browser_generic_retry",
        }:
            self.assertEqual(components[component_id]["decision"], "supersede")
        self.assertEqual(
            components["browser_unrestricted_submit"]["local_authority"],
            "submission intent fence plus authoritative ATS or Gmail confirmation",
        )
        self.assertEqual(
            components["temporal_activity"]["local_authority"],
            "ledger idempotency key and side-effect fence",
        )

    def test_every_v130_component_has_one_explicit_adoption_decision(self):
        data = json.loads(ADOPTION.read_text(encoding="utf-8"))
        self.assertEqual(data["upstream_release"], "v1.3.0")
        self.assertEqual(
            data["upstream_commit"],
            "a8a10011126f443e0041bb4924a1106c2f7f7536",
        )

        components = data["components"]
        expected = {
            "profile_setup", "job_scraper", "rank", "apply", "outcome",
            "gmail_sync", "interview", "upskill", "html_report", "notion_sync",
            "portal_freehire", "portal_jobbank", "portal_jobdanmark",
            "portal_jobindex", "portal_jobnet", "portal_linkedin", "add_portal",
            "add_template", "expand", "reset", "salary_lookup", "latex_assets",
            "security_tooling", "upstream_update_tooling", "upstream_tests",
            "project_documentation", "claude_runtime_binding",
        }
        self.assertEqual({item["id"] for item in components}, expected)
        self.assertEqual(len(components), len(expected))

        for item in components:
            self.assertIn(item["decision"], {"reuse", "adapt", "supersede"})
            self.assertTrue(item["source_paths"])
            self.assertTrue(item["reason"].strip())
            self.assertTrue(item["local_contract"].strip())
            self.assertRegex(item["owner_task"], r"^L-\d+[A-Z]?$|^none$")

    def test_master_delta_is_recorded_without_automatic_activation(self):
        data = json.loads(MASTER_DELTA.read_text(encoding="utf-8"))
        self.assertEqual(data["base_release"], "v1.3.0")
        self.assertEqual(data["base_commit"], "a8a10011126f443e0041bb4924a1106c2f7f7536")
        self.assertEqual(data["master_commit"], "fcefb8150fb073ae0d86b5b7a6f09e94aa5976ee")
        self.assertEqual(data["ahead_by"], 3)
        self.assertEqual(data["changed_file_count"], 13)
        self.assertFalse(data["auto_activate"])

        candidates = {item["id"]: item for item in data["candidates"]}
        self.assertEqual(
            set(candidates),
            {"rank_language_gate_regression_tests", "robots_aware_web_research"},
        )
        for item in candidates.values():
            self.assertEqual(item["decision"], "port_later")
            self.assertTrue(item["source_commits"])
            self.assertTrue(item["changed_paths"])
            self.assertRegex(item["owner_task"], r"^L-\d+[A-Z]?$|^L-\d+\u2013L-\d+$")


if __name__ == "__main__":
    unittest.main()
