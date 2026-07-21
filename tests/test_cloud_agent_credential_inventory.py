#!/usr/bin/env python3
"""Contract tests for the TODO #2 credential-reference inventory."""

from __future__ import annotations

import csv
import ast
import base64
import contextlib
import hashlib
import io
import importlib.util
import inspect
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
GENERATOR = REPO / "scripts" / "generate-cloud-agent-credential-inventory.py"
COLLECTOR = REPO / "scripts" / "collect-cloud-agent-credential-metadata.py"
PARENT = REPO / "docs" / "reference" / "cloud-agent-loop-inventory.tsv"
TRACKED = REPO / "docs" / "reference" / "cloud-agent-credential-inventory.tsv"
OBSERVATIONS = REPO / "docs" / "reference" / "cloud-agent-credential-observations.json"
REVIEW = REPO / "docs" / "reference" / "cloud-agent-credential-review-manifest.json"
INDEPENDENT_REVIEW = REPO / "docs" / "reference" / "cloud-agent-credential-rebind-review.json"
OBJECTS = REPO / "docs" / "reference" / "cloud-agent-credential-objects.json"
DOCUMENTATION = REPO / "docs" / "reference" / "cloud-agent-credential-inventory.md"
TYPESCRIPT_VERSION = "5.5.4"
TYPESCRIPT_INTEGRITY = "sha512-Mtq29sKDAEYP7aljRgtPOpTvOfbwRWlS6dPRzwjdE+C0R4brX/GUyhHSecbHMFLNBLcJIPt9nl9yG5TZ1weH+Q=="
CURRENT_PARENT_DIGEST = "sha256:90113e58:00a49511:9a84159b:1baf1728:c883a52b:0239dd87:113d1f8a:939d1e7c"
NEW_PARENT_DIGESTS = {
    "launchd:ai.anicca.article-d7d8-finalizer": "sha256:56b61d02:c6a4d79e:6b1ef369:c3b7cfbb:83d3b663:d0142a42:4b58824b:48195fc8",
    "launchd:ai.anicca.article-zenn-retry": "sha256:80ac4e1d:a3944b38:a0f459ef:046f60a2:ae8b5d45:65f77323:19565cd1:a5605130",
    "launchd:ai.anicca.hf-gig-pass": "sha256:a3b25724:9177c916:c8df7e58:a4394c3b:53c75a81:aad00585:e607dd4a:9fa12f3d",
    "launchd:ai.anicca.orca-zenn-finalizer": "sha256:2acb3770:2eaf6c2a:eda0327c:b2cfbd67:de6beb9b:17ca0a68:cd58b090:e5f082bc",
}


def load_generator():
    spec = importlib.util.spec_from_file_location("credential_inventory", GENERATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("credential inventory generator is not importable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_collector():
    spec = importlib.util.spec_from_file_location("credential_metadata_collector", COLLECTOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("credential metadata collector is not importable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def pending_independent_review_fixture() -> dict:
    review = read_json(INDEPENDENT_REVIEW)
    review.pop("approval_basis", None)
    review["review_status"] = "review_required"
    review["review_basis"] = "pending_independent_credential_rebind_review"
    review["reviewer_role"] = "independent_fresh_reviewer_required"
    return review


class CredentialInventoryContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.generator = load_generator()
        cls.collector = load_collector()

    def test_tracked_inventory_exactly_matches_generator(self) -> None:
        parents = read_tsv(PARENT)
        observations = read_json(OBSERVATIONS)
        review = read_json(REVIEW)
        objects = read_json(OBJECTS)
        self.generator.validate_credential_objects(objects)
        expected = self.generator.build_loop_dependency_edges(parents, observations, review, objects)
        self.generator.validate_loop_dependency_edges(
            expected,
            {parent["inventory_id"] for parent in parents},
            observations,
            objects,
            review,
        )
        self.assertEqual(read_tsv(TRACKED), expected)

    def test_safe_metadata_collector_exists(self) -> None:
        self.assertTrue(COLLECTOR.is_file(), "safe credential metadata collector is missing")

    def test_cron_projection_pipeline_never_exposes_prompt_body_to_collector(self) -> None:
        sentinel = "PROMPT_BODY_SENTINEL_MUST_NOT_CROSS_BOUNDARY"
        with tempfile.TemporaryDirectory() as temp_dir:
            executable = Path(temp_dir) / "openclaw"
            executable.write_text(
                "#!/bin/sh\n"
                "printf '%s\\n' '"
                + json.dumps(
                    {
                        "jobs": [
                            {
                                "id": "fixture-job",
                                "enabled": True,
                                "agentId": "anicca",
                                "payload": {
                                    "kind": "agentTurn",
                                    "message": sentinel,
                                    "model": "deepseek/model-fixture",
                                    "fallbacks": ["openai/model-fixture"],
                                    "toolsAllow": ["slack"],
                                },
                                "delivery": {"channel": "telegram"},
                            }
                        ]
                    }
                )
                + "'\n",
                encoding="utf-8",
            )
            executable.chmod(0o755)
            path = temp_dir + os.pathsep + os.environ.get("PATH", "")
            with mock.patch.dict(os.environ, {"PATH": path}):
                projected = self.collector.run_cron_metadata_projection()
        text = json.dumps(projected)
        self.assertNotIn(sentinel, text)
        self.assertEqual(
            {"job_id", "enabled", "agent_id", "payload_kind", "model_ref", "fallback_refs", "fallbacks_inherited", "tools_allow", "tools_inherited", "delivery_provider"},
            set(projected["jobs"][0]),
        )

    def test_cli_allowlist_rejects_invalid_agent_and_any_extra_flag(self) -> None:
        invalid = [
            ("openclaw", "models", "status", "--agent", "../private", "--json"),
            ("openclaw", "models", "status", "--agent", "anicca", "--json", "--probe"),
            ("openclaw", "models", "auth", "list", "--agent", "anicca", "--allow-exec", "--json"),
            ("openclaw", "agents", "list", "--json", "--all"),
        ]
        for argv in invalid:
            with self.subTest(argv=argv), self.assertRaisesRegex(ValueError, "allowlist"):
                self.collector.run_json(argv, lambda _: None)

    def test_fixed_cron_projector_rejects_noncanonical_argv_before_spawn(self) -> None:
        with self.assertRaisesRegex(ValueError, "fixed projection allowlist"):
            self.collector._fixed_cron_projection(
                ("openclaw", "cron", "get", "../private"),
                self.collector.CRON_GET_SAFE_JQ_ARGV,
            )
        with self.assertRaisesRegex(ValueError, "fixed projection allowlist"):
            self.collector._fixed_cron_projection(
                self.collector.CRON_LIST_ARGV + ("--probe",),
                self.collector.CRON_SAFE_JQ_ARGV,
            )

    def test_fixed_gateway_cron_get_projection_is_safe_and_canonical(self) -> None:
        sentinel = "PROMPT_BODY_SENTINEL_MUST_NOT_CROSS_BOUNDARY"
        with tempfile.TemporaryDirectory() as temp_dir:
            executable = Path(temp_dir) / "openclaw"
            executable.write_text(
                "#!/bin/sh\nprintf '%s\\n' '"
                + json.dumps({
                    "id": "fixture-job", "enabled": True, "agentId": "anicca",
                    "payload": {"kind": "agentTurn", "message": sentinel, "model": "deepseek/model"},
                    "delivery": {"channel": "telegram"},
                })
                + "'\n",
                encoding="utf-8",
            )
            executable.chmod(0o755)
            argv = (
                "openclaw", "gateway", "call", "cron.get",
                "--params", '{"id":"fixture-job"}',
                "--json", "--timeout", "30000",
            )
            path = temp_dir + os.pathsep + os.environ.get("PATH", "")
            with mock.patch.dict(os.environ, {"PATH": path}):
                try:
                    projected = self.collector._fixed_cron_projection(
                        argv, self.collector.CRON_GET_SAFE_JQ_ARGV
                    )
                except ValueError as error:
                    self.fail(str(error))
        self.assertEqual("fixture-job", projected["jobs"][0]["job_id"])
        self.assertNotIn(sentinel, json.dumps(projected))

    def test_collect_requests_safe_cron_get_fallback_for_every_expected_job_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            parent_path = Path(temp_dir) / "parents.tsv"
            parent_path.write_text(
                "inventory_id\tsource_type\tentrypoint\tstate\tevidence\n"
                "openclaw:fixture-job\topenclaw_cron\t"
                "openclaw_gateway:agentTurn:agent=anicca\tenabled\tsafe-parent-metadata\n",
                encoding="utf-8",
            )
            requested = []

            def fake_projection(expected_job_ids=()):
                requested.extend(expected_job_ids)
                return {"schema_version": 1, "jobs": []}

            def unavailable(argv):
                raise subprocess.CalledProcessError(1, argv)

            with mock.patch.object(
                self.collector, "run_cron_metadata_projection", side_effect=fake_projection
            ):
                self.collector.collect(parent_path, runner=unavailable)
        self.assertEqual(["fixture-job"], requested)

    def test_collect_records_portable_cron_absence_evidence_with_gateway_revision(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            parent_path = Path(temp_dir) / "parents.tsv"
            parent_path.write_text(
                "inventory_id\tsource_type\tentrypoint\tstate\tevidence\n"
                "openclaw:missing-job\topenclaw_cron\t"
                "openclaw_gateway:agentTurn:agent=anicca\tenabled\tsafe-parent-metadata\n",
                encoding="utf-8",
            )

            def safe_gateway_metadata(argv):
                stdout = (
                    "{}" if argv == ("openclaw", "config", "schema")
                    else "OpenClaw fixture" if argv == ("openclaw", "--version")
                    else "[]" if argv == ("openclaw", "agents", "list", "--json")
                    else json.dumps({
                        "status": "clean",
                        "resolution": {"resolvabilityComplete": True},
                    }) if argv == ("openclaw", "secrets", "audit", "--json")
                    else ""
                )
                return subprocess.CompletedProcess(argv, 0, stdout=stdout)

            result = self.collector.collect(
                parent_path, runner=safe_gateway_metadata,
                cron_projection={
                    "schema_version": 2, "jobs": [],
                    "missing_jobs": [{
                        "job_id": "missing-job", "result": "not_found",
                        "list_complete": True, "individual_get": "not_found",
                    }],
                },
            )
        evidence = result["parents"]["openclaw:missing-job"].get("cron_absence_evidence")
        self.assertIsInstance(evidence, dict)
        self.assertEqual("not_found", evidence["result"])
        self.assertEqual("missing-job", evidence["job_id"])
        self.assertRegex(evidence["gateway_revision_digest"], self.generator.DIGEST_VALUE)
        self.assertRegex(evidence["observed_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

    def test_collect_rejects_nonexact_cron_absence_projection(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            parent_path = Path(temp_dir) / "parents.tsv"
            parent_path.write_text(
                "inventory_id\tsource_type\tentrypoint\tstate\tevidence\n"
                "openclaw:missing-job\topenclaw_cron\t"
                "openclaw_gateway:agentTurn:agent=anicca\tenabled\tsafe-parent-metadata\n",
                encoding="utf-8",
            )
            result = self.collector.collect(
                parent_path, runner=lambda argv: (_ for _ in ()).throw(RuntimeError("offline")),
                cron_projection={
                    "schema_version": 2, "jobs": [],
                    "missing_jobs": [{
                        "job_id": "missing-job", "result": "not_found",
                        "list_complete": True, "individual_get": "not_found",
                        "error_detail": "must-not-be-accepted",
                    }],
                },
            )
        self.assertNotIn(
            "cron_absence_evidence", result["parents"]["openclaw:missing-job"]
        )

    def test_collect_records_only_stable_cron_failure_class(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            parent_path = Path(temp_dir) / "parents.tsv"
            parent_path.write_text(
                "inventory_id\tsource_type\tentrypoint\tstate\tevidence\n"
                "openclaw:missing-job\topenclaw_cron\t"
                "openclaw_gateway:agentTurn:agent=anicca\tenabled\tsafe-parent-metadata\n",
                encoding="utf-8",
            )
            result = self.collector.collect(
                parent_path, runner=lambda argv: (_ for _ in ()).throw(RuntimeError("offline")),
                cron_projection={
                    "schema_version": 2, "jobs": [],
                    "missing_jobs": [{
                        "job_id": "missing-job", "result": "unverified",
                        "list_complete": True, "individual_get": "auth_error",
                    }],
                },
            )
        failure = result["parents"]["openclaw:missing-job"].get("cron_lookup_failure")
        self.assertIsInstance(failure, dict)
        self.assertEqual("auth_error", failure["individual_get"])
        self.assertEqual("unverified", failure["result"])
        self.assertRegex(failure["gateway_revision_digest"], self.generator.DIGEST_VALUE)
        self.assertRegex(failure["observed_at"], r"^\d{4}-\d{2}-\d{2}T")

    def test_unavailable_openclaw_version_or_schema_stays_unverified(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            parent_path = Path(temp_dir) / "parents.tsv"
            parent_path.write_text(
                "inventory_id\tsource_type\tentrypoint\tstate\tevidence\n"
                "openclaw:fixture-job\topenclaw_cron\t"
                "openclaw_gateway:agentTurn:agent=anicca\tenabled\tsafe-parent-metadata\n",
                encoding="utf-8",
            )

            def unavailable(argv):
                raise subprocess.CalledProcessError(1, argv)

            result = self.collector.collect(
                parent_path,
                runner=unavailable,
                cron_projection={
                    "schema_version": 2,
                    "jobs": [],
                    "missing_jobs": [{
                        "job_id": "fixture-job",
                        "result": "unverified",
                        "list_complete": True,
                        "individual_get": "gateway_error",
                    }],
                },
            )
        observation = result["parents"]["openclaw:fixture-job"]
        self.assertEqual("unverified", observation["source_revision_digest"])
        self.assertEqual(
            "unverified", observation["cron_lookup_failure"]["gateway_revision_digest"]
        )

    def test_complete_cron_list_and_failed_get_remains_unverified(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            executable = Path(temp_dir) / "openclaw"
            executable.write_text(
                "#!/bin/sh\n"
                "case \"$*\" in\n"
                "  *cron.list*) printf '%s\\n' '{\"jobs\":[],\"total\":0,\"offset\":0,\"limit\":200,\"hasMore\":false}' ;;\n"
                "  *cron.get*) exit 1 ;;\n"
                "esac\n",
                encoding="utf-8",
            )
            executable.chmod(0o755)
            path = temp_dir + os.pathsep + os.environ.get("PATH", "")
            with mock.patch.dict(os.environ, {"PATH": path}):
                projected = self.collector.run_cron_metadata_projection(("missing-job",))
        self.assertEqual([], projected["jobs"])
        self.assertIn("missing_jobs", projected)
        self.assertEqual(
            [{
                "job_id": "missing-job", "result": "unverified",
                "list_complete": True, "individual_get": "gateway_error",
            }],
            projected["missing_jobs"],
        )

    def test_cron_stderr_is_reduced_to_stable_class_without_body(self) -> None:
        sentinel = "STDERR_SECRET_SENTINEL_MUST_NOT_CROSS_BOUNDARY"
        with tempfile.TemporaryDirectory() as temp_dir:
            executable = Path(temp_dir) / "openclaw"
            executable.write_text(
                "#!/bin/sh\n"
                "case \"$*\" in\n"
                "  *cron.list*) printf '%s\\n' '{\"jobs\":[],\"total\":0,\"offset\":0,\"limit\":200,\"hasMore\":false}' ;;\n"
                f"  *cron.get*) printf '%s\\n' 'authentication failed {sentinel}' >&2; exit 1 ;;\n"
                "esac\n",
                encoding="utf-8",
            )
            executable.chmod(0o755)
            path = temp_dir + os.pathsep + os.environ.get("PATH", "")
            with mock.patch.dict(os.environ, {"PATH": path}):
                projected = self.collector.run_cron_metadata_projection(("missing-job",))
        self.assertEqual("auth_error", projected["missing_jobs"][0]["individual_get"])
        self.assertNotIn(sentinel, json.dumps(projected))

    def test_only_structured_gateway_not_found_is_accepted_as_absence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            executable = Path(temp_dir) / "openclaw"
            executable.write_text(
                "#!/bin/sh\n"
                "printf '%s\\n' '{\"error\":{\"code\":\"NOT_FOUND\"}}'\n"
                "exit 1\n",
                encoding="utf-8",
            )
            executable.chmod(0o755)
            argv = (
                "openclaw", "gateway", "call", "cron.get", "--params",
                '{"id":"missing-job"}', "--json", "--timeout", "30000",
            )
            path = temp_dir + os.pathsep + os.environ.get("PATH", "")
            with mock.patch.dict(os.environ, {"PATH": path}):
                try:
                    projected = self.collector._fixed_cron_projection(
                        argv, self.collector.CRON_GET_SAFE_JQ_ARGV
                    )
                except RuntimeError:
                    projected = {}
        self.assertEqual("not_found", projected["result"])
        self.assertEqual("NOT_FOUND", projected["error_code"])
        self.assertEqual([], projected["jobs"])

    def test_revision_records_fail_closed_for_unsafe_or_nonportable_inputs(self) -> None:
        launchd = {
            "inventory_id": "launchd:fixture", "source_type": "launchd",
            "entrypoint": "/tmp/prompt-payload.txt", "evidence": "relative.plist",
        }
        self.assertEqual("unverified", self.collector.source_revision_record(launchd)["digest"])
        self.assertEqual(
            "invalid_plist_locator", self.collector.source_revision_record(launchd).get("reason")
        )
        self.assertEqual("unverified", self.collector.config_revision_record(launchd)["digest"])
        railway = {
            "inventory_id": "railway:fixture", "source_type": "railway_entrypoint",
            "entrypoint": "node server.js", "evidence": "not-a-portable-git-locator",
        }
        self.assertEqual("unverified", self.collector.source_revision_record(railway)["digest"])
        self.assertEqual(
            {"digest": "unverified", "evidence_locator": "unverified"},
            self.collector.source_revision_record({"source_type": "mystery"}),
        )

    def test_collector_main_writes_only_serialized_safe_result(self) -> None:
        safe_result = {"schema_version": 1, "parents": {}, "agents": {}}
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "safe.json"
            with mock.patch.object(self.collector, "collect", return_value=safe_result), mock.patch.object(
                sys, "argv", [str(COLLECTOR), "--output", str(output)]
            ):
                self.collector.main()
            self.assertEqual(safe_result, json.loads(output.read_text(encoding="utf-8")))

    def test_review_required_cannot_generate_none_edge(self) -> None:
        parent = {"inventory_id": "launchd:fixture", "source_type": "launchd", "entrypoint": "/tmp/fixture", "state": "loaded"}
        observation = {
            "parent_metadata_digest": self.generator.parent_metadata_digest(parent),
            "source_revision_digest": "sha256:" + ":".join(["1" * 8] * 8),
            "config_revision_digest": "sha256:" + ":".join(["2" * 8] * 8),
            "source_evidence_locator": "path:fixture;blob:" + "a" * 40,
            "config_evidence_locator": "path:fixture.plist;blob:" + "b" * 40,
        }
        review = {"decision": "review_required", "decision_basis": "pending"}
        with self.assertRaisesRegex(SystemExit, "review_required"):
            self.generator.reviewed_parent_edges(parent, observation, review, {})

    def test_explicit_none_edge_uses_observation_revision_fields_exactly(self) -> None:
        parent = {"inventory_id": "launchd:fixture", "source_type": "launchd", "entrypoint": "/tmp/fixture", "state": "loaded"}
        observation = {
            "parent_metadata_digest": self.generator.parent_metadata_digest(parent),
            "source_revision_digest": "sha256:" + ":".join(["1" * 8] * 8),
            "config_revision_digest": "sha256:" + ":".join(["2" * 8] * 8),
            "source_evidence_locator": "path:fixture;blob:" + "a" * 40,
            "config_evidence_locator": "path:fixture.plist;blob:" + "b" * 40,
        }
        review = {
            "decision": "none",
            "decision_basis": "entrypoint_reference_review",
            "evidence_locator": "launchd:fixture",
            "references": [],
        }
        edge = self.generator.reviewed_parent_edges(parent, observation, review, {})[0]
        for field in ("parent_metadata_digest", "source_revision_digest", "config_revision_digest"):
            self.assertEqual(observation[field], edge[field])
        self.assertEqual("none_observed", edge["dependency_status"])

    def test_unverified_revision_forces_unverified_edge_despite_none_or_references_review(self) -> None:
        parent = {
            "inventory_id": "launchd:fixture", "source_type": "launchd",
            "entrypoint": "/tmp/fixture", "state": "loaded",
        }
        observation = {
            "parent_metadata_digest": self.generator.parent_metadata_digest(parent),
            "source_revision_digest": "unverified",
            "config_revision_digest": "sha256:" + ":".join(["2" * 8] * 8),
            "source_evidence_locator": "unverified",
            "config_evidence_locator": "path:fixture.plist;blob:" + "b" * 40,
        }
        object_id = "credential:object-000000000000001"
        objects = {
            object_id: {
                "provider": "internal", "account_alias": "unresolved:fixture",
                "credential_type": "env_ref", "credential_ref": "env:FIXTURE_TOKEN",
                "policy_status": "observed", "policy_basis": "none",
                "evidence_locator": "symbol:fixture#FIXTURE_TOKEN",
            }
        }
        reviews = (
            {
                "decision": "none", "decision_basis": "entrypoint_reference_review",
                "evidence_locator": "symbol:fixture", "references": [],
            },
            {
                "decision": "references", "decision_basis": "entrypoint_reference_review",
                "evidence_locator": "symbol:fixture",
                "references": [{
                    "credential_object_id": object_id,
                    "consumer_locator": "symbol:fixture",
                    "permission_scope": "internal:authenticate",
                    "evidence_locator": "symbol:fixture#FIXTURE_TOKEN",
                }],
            },
        )
        for review in reviews:
            with self.subTest(decision=review["decision"]):
                edge = self.generator.reviewed_parent_edges(
                    parent, observation, review, objects
                )[0]
                self.assertEqual("unverified", edge["dependency_status"])
                self.assertEqual("unverified", edge["credential_object_id"])
                self.assertEqual("unverified", edge["permission_scope"])

    def test_unverified_repository_reference_inspection_forces_unverified_edge(self) -> None:
        parent = {
            "inventory_id": "package:fixture/package.json#start",
            "source_type": "repository_entrypoint", "entrypoint": "node src/server.js",
            "state": "declared_in_repository", "evidence": "fixture/package.json",
        }
        observation = {
            "parent_metadata_digest": self.generator.parent_metadata_digest(parent),
            "source_revision_digest": "sha256:" + ":".join(["1" * 8] * 8),
            "config_revision_digest": "sha256:" + ":".join(["2" * 8] * 8),
            "source_evidence_locator": "git:HEAD;path:fixture/package.json",
            "config_evidence_locator": "git:HEAD;path:fixture/package.json",
            "reference_inspection_status": "unverified",
        }
        review = {
            "decision": "none", "decision_basis": "import_graph_review",
            "evidence_locator": "repo:fixture/package.json#start", "references": [],
        }
        edge = self.generator.reviewed_parent_edges(parent, observation, review, {})[0]
        self.assertEqual("unverified", edge["dependency_status"])

    def test_repository_review_reference_must_match_reachable_symbol_evidence(self) -> None:
        parent = {
            "inventory_id": "package:fixture/package.json#start",
            "source_type": "repository_entrypoint", "entrypoint": "node src/server.js",
            "state": "declared_in_repository", "evidence": "fixture/package.json",
        }
        observation = {
            "parent_metadata_digest": self.generator.parent_metadata_digest(parent),
            "source_revision_digest": "sha256:" + ":".join(["1" * 8] * 8),
            "config_revision_digest": "sha256:" + ":".join(["2" * 8] * 8),
            "source_evidence_locator": "git:HEAD;path:fixture/package.json",
            "config_evidence_locator": "git:HEAD;path:fixture/package.json",
            "reference_inspection_status": "verified",
            "reference_evidence": [{
                "reference_name": "REACHABLE_API_KEY", "path": "fixture/src/server.js",
                "blob_oid": "a" * 40, "line": 4,
                "symbol_locator": "path:fixture/src/server.js;blob:" + "a" * 40 + ";line:4;symbol:env.REACHABLE_API_KEY",
            }],
        }
        review = {
            "decision": "references", "decision_basis": "import_graph_review",
            "source_revision_digest": observation["source_revision_digest"],
            "config_revision_digest": observation["config_revision_digest"],
            "source_evidence_locator": observation["source_evidence_locator"],
            "config_evidence_locator": observation["config_evidence_locator"],
            "references": [{
                "credential_ref": "env:UNREACHABLE_API_KEY",
                "evidence_locator": "path:fixture/src/orphan.js;blob:" + "b" * 40 + ";line:1;symbol:env.UNREACHABLE_API_KEY",
            }],
        }
        with self.assertRaisesRegex(SystemExit, "reference is not reachable from start entrypoint"):
            self.generator.validate_parent_review_record(parent, observation, review)

    def test_repository_review_requires_exact_unique_observed_reference_set(self) -> None:
        parent = {
            "inventory_id": "package:fixture/package.json#start",
            "source_type": "repository_entrypoint", "entrypoint": "node src/server.js",
            "state": "declared_in_repository", "evidence": "fixture/package.json",
        }
        source_digest = "sha256:" + ":".join(["1" * 8] * 8)
        config_digest = "sha256:" + ":".join(["2" * 8] * 8)
        source_locator = "git:HEAD;path:fixture/package.json"
        config_locator = "git:HEAD;path:fixture/package.json"
        evidence = {
            "reference_name": "OPENAI_API_KEY", "path": "fixture/src/server.js",
            "blob_oid": "a" * 40, "line": 4,
            "symbol_locator": "path:fixture/src/server.js;blob:" + "a" * 40
            + ";line:4;symbol:env.OPENAI_API_KEY",
        }
        duplicate_evidence = {
            **evidence, "path": "fixture/src/worker.js", "line": 7,
            "symbol_locator": "path:fixture/src/worker.js;blob:" + "b" * 40
            + ";line:7;symbol:env.OPENAI_API_KEY",
        }
        observation = {
            "parent_metadata_digest": self.generator.parent_metadata_digest(parent),
            "source_revision_digest": source_digest,
            "config_revision_digest": config_digest,
            "source_evidence_locator": source_locator,
            "config_evidence_locator": config_locator,
            "reference_inspection_status": "verified",
            "reference_evidence": [evidence, duplicate_evidence],
        }
        consumer = self.generator.typed_locator(parent)
        account_alias = "unresolved:" + consumer
        object_id = self.generator.credential_object_id(
            "openai", account_alias, "env:OPENAI_API_KEY"
        )
        reference = {
            "credential_object_id": object_id,
            "provider": "openai", "account_alias": account_alias,
            "credential_type": "env_ref", "credential_ref": "env:OPENAI_API_KEY",
            "policy_status": "observed", "policy_basis": "none",
            "evidence_locator": evidence["symbol_locator"],
            "consumer_locator": consumer, "permission_scope": "model:inference",
        }
        review = {
            "decision": "references", "decision_basis": "import_graph_review",
            "source_revision_digest": source_digest,
            "config_revision_digest": config_digest,
            "source_evidence_locator": source_locator,
            "config_evidence_locator": config_locator,
            "references": [reference],
        }
        self.generator.validate_parent_review_record(parent, observation, review)
        mutations = (
            ({**review, "references": []}, "exact-match"),
            ({**review, "references": [reference, reference]}, "exact-match"),
            ({**review, "references": [{**reference, "evidence_locator": duplicate_evidence["symbol_locator"]}]}, "exact-match"),
            ({**review, "references": [{**reference, "consumer_locator": "repo:wrong/package.json#start"}]}, "exact-match"),
            ({**review, "references": [{**reference, "permission_scope": "unverified"}]}, "exact-match"),
            ({**review, "references": [{**reference, "credential_object_id": "credential:object-999999999999999"}]}, "exact-match"),
        )
        for mutated, message in mutations:
            with self.subTest(references=mutated["references"]), self.assertRaisesRegex(
                SystemExit, message
            ):
                self.generator.validate_parent_review_record(parent, observation, mutated)

    def test_pending_candidate_has_no_unapproved_repository_references(self) -> None:
        parents = read_tsv(PARENT)
        review = read_json(REVIEW)
        parent_by_id = {parent["inventory_id"]: parent for parent in parents}
        repository_reviews = [
            record for parent_id, record in review["parents"].items()
            if parent_by_id[parent_id]["source_type"]
            in {"repository_entrypoint", "railway_entrypoint"}
        ]
        self.assertTrue(repository_reviews)
        self.assertEqual({"unverified"}, {record["decision"] for record in repository_reviews})
        self.assertTrue(all(record["references"] == [] for record in repository_reviews))

    def test_openclaw_dynamic_decision_requires_job_specific_review_evidence(self) -> None:
        parent = {
            "inventory_id": "openclaw:fixture-job", "source_type": "openclaw_cron",
            "entrypoint": "openclaw_gateway:agentTurn:agent=anicca", "state": "disabled",
        }
        observation = {
            "parents": {parent["inventory_id"]: {
                "parent_metadata_digest": self.generator.parent_metadata_digest(parent),
                "source_revision_digest": "sha256:" + ":".join(["1" * 8] * 8),
                "config_revision_digest": "sha256:" + ":".join(["2" * 8] * 8),
                "source_evidence_locator": "openclaw:version;schema:" + "sha256:" + ":".join(["3" * 8] * 8),
                "config_evidence_locator": "openclaw-cli:cron-list-safe-projection;job:fixture-job",
                "inspection_status": "verified",
                "cron_metadata": {"enabled": False, "payload_kind": "agentTurn"},
            }},
            "agents": {},
        }
        review = {"parents": {parent["inventory_id"]: {
            "decision": "dynamic_openclaw",
            "decision_basis": "official_cli_safe_projection",
            "source_revision_digest": observation["parents"][parent["inventory_id"]]["source_revision_digest"],
            "config_revision_digest": observation["parents"][parent["inventory_id"]]["config_revision_digest"],
            "source_evidence_locator": observation["parents"][parent["inventory_id"]]["source_evidence_locator"],
            "config_evidence_locator": observation["parents"][parent["inventory_id"]]["config_evidence_locator"],
        }}}
        with self.assertRaisesRegex(SystemExit, "job-specific review evidence"):
            self.generator.build_loop_dependency_edges(
                [parent], observation, review,
                {"schema_version": 2, "credential_objects": {}, "finding_objects": {}},
            )

    def test_dynamic_openclaw_derived_references_require_exact_nonempty_schema(self) -> None:
        parent = {
            "inventory_id": "openclaw:fixture-job", "source_type": "openclaw_cron",
            "entrypoint": "openclaw_gateway:agentTurn:agent=anicca", "state": "enabled",
        }
        observation = {
            "parent_metadata_digest": self.generator.parent_metadata_digest(parent),
            "source_revision_digest": "sha256:" + ":".join(["1" * 8] * 8),
            "config_revision_digest": "sha256:" + ":".join(["2" * 8] * 8),
            "source_evidence_locator": "openclaw:version;schema:" + "sha256:" + ":".join(["3" * 8] * 8),
            "config_evidence_locator": "openclaw-cli:cron-list-safe-projection;job:fixture-job",
            "inspection_status": "verified",
            "cron_metadata": {"enabled": True, "payload_kind": "agentTurn"},
        }
        base = {
            "decision": "dynamic_openclaw", "decision_basis": "official_cli_safe_projection",
            "source_revision_digest": observation["source_revision_digest"],
            "config_revision_digest": observation["config_revision_digest"],
            "source_evidence_locator": observation["source_evidence_locator"],
            "config_evidence_locator": observation["config_evidence_locator"],
            "job_evidence_locator": observation["config_evidence_locator"],
            "references": [],
        }
        valid_ref = {
            "kind": "tools", "credential_object_id": "unverified",
            "evidence_locator": observation["config_evidence_locator"] + "#tools-inherited",
        }
        cases = (
            ({**base, "derived_references": []}, "nonempty derived references"),
            ({**base, "derived_references": [valid_ref, valid_ref]}, "unique derived references"),
            ({**base, "derived_references": [{**valid_ref, "kind": "mystery"}]}, "invalid derived reference"),
            ({**base, "derived_references": [{**valid_ref, "evidence_locator": "job:other"}]}, "invalid derived reference"),
        )
        for review, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(SystemExit, message):
                self.generator.validate_parent_review_record(parent, observation, review)

    def test_dynamic_edges_require_review_set_equal_to_observation_derivation(self) -> None:
        parent = {
            "inventory_id": "openclaw:fixture-job", "source_type": "openclaw_cron",
            "entrypoint": "openclaw_gateway:agentTurn:agent=anicca", "state": "enabled",
        }
        observed = {
            "parent_metadata_digest": self.generator.parent_metadata_digest(parent),
            "source_revision_digest": "sha256:" + ":".join(["1" * 8] * 8),
            "config_revision_digest": "sha256:" + ":".join(["2" * 8] * 8),
            "source_evidence_locator": "openclaw:version;schema:" + "sha256:" + ":".join(["3" * 8] * 8),
            "config_evidence_locator": "openclaw-cli:cron-list-safe-projection;job:fixture-job",
            "inspection_status": "verified", "agent_alias": "agent:anicca",
            "cron_metadata": {
                "enabled": True, "payload_kind": "agentTurn", "model_ref": "deepseek/model",
                "fallback_refs": [], "fallbacks_inherited": False, "tools_allow": [],
                "tools_inherited": True, "delivery_provider": "none",
            },
        }
        observations = {
            "parents": {parent["inventory_id"]: observed},
            "agents": {"agent:anicca": {
                "inspection_status": "verified", "provider_chain": ["deepseek"],
                "profiles": [{"alias": "sha256:aaaaaaaaaaaaaaaa", "provider": "deepseek", "type": "token"}],
            }},
            "openclaw_audit": {"finding_counts": {}},
        }
        objects = self.generator.build_credential_objects([parent], observations, {"parents": {}})
        review = {"parents": {parent["inventory_id"]: {
            "decision": "dynamic_openclaw", "decision_basis": "official_cli_safe_projection",
            "source_revision_digest": observed["source_revision_digest"],
            "config_revision_digest": observed["config_revision_digest"],
            "source_evidence_locator": observed["source_evidence_locator"],
            "config_evidence_locator": observed["config_evidence_locator"],
            "job_evidence_locator": observed["config_evidence_locator"],
            "derived_references": [{
                "kind": "tools", "credential_object_id": "unverified",
                "evidence_locator": observed["config_evidence_locator"] + "#tools-inherited",
            }],
            "references": [],
        }}}
        with self.assertRaisesRegex(SystemExit, "derived reference set mismatch"):
            self.generator.build_loop_dependency_edges([parent], observations, review, objects)

    def test_full_generation_rejects_dynamic_openclaw_with_unverified_source(self) -> None:
        observations = read_json(OBSERVATIONS)
        review = read_json(REVIEW)
        dynamic_id = next(
            parent_id for parent_id, record in review["parents"].items()
            if record["decision"] == "dynamic_openclaw"
        )
        observations["parents"][dynamic_id]["source_revision_digest"] = "unverified"
        observations["parents"][dynamic_id]["source_evidence_locator"] = "unverified"
        review["parents"][dynamic_id]["source_revision_digest"] = "unverified"
        review["parents"][dynamic_id]["source_evidence_locator"] = "unverified"
        review["review_status"] = "review_required"
        review["review_basis"] = self.generator.PENDING_REVIEW_BASIS
        review["approved_observation_digest"] = self.generator.canonical_digest(observations)
        with tempfile.TemporaryDirectory() as temp_dir:
            observations_path = Path(temp_dir) / "observations.json"
            review_path = Path(temp_dir) / "review.json"
            output_path = Path(temp_dir) / "inventory.tsv"
            observations_path.write_text(json.dumps(observations), encoding="utf-8")
            review_path.write_text(json.dumps(review), encoding="utf-8")
            with mock.patch.object(
                sys,
                "argv",
                [
                    str(GENERATOR), "--check", "--parent", str(PARENT),
                    "--observations", str(observations_path),
                    "--review", str(review_path), "--objects", str(OBJECTS),
                    "--output", str(output_path),
                ],
            ), self.assertRaisesRegex(SystemExit, "OpenClaw revision binding mismatch"):
                self.generator.main()

    def test_full_generation_rejects_unbound_openclaw_top_revision_mutations(self) -> None:
        base_observations = read_json(OBSERVATIONS)
        base_review = read_json(REVIEW)
        failure_id = next(iter(base_observations["cron_lookup_failures"]))
        arbitrary_digest = "sha256:" + ":".join(["4" * 8] * 8)

        def top_unverified(observations, review) -> None:
            observations["openclaw_revision"] = {
                "version_digest": "unverified", "schema_digest": "unverified",
            }

        def top_extra_field(observations, review) -> None:
            observations["openclaw_revision"]["extra"] = "field"

        def coordinated_failure_rewrite(observations, review) -> None:
            observations["cron_lookup_failures"][failure_id][
                "gateway_revision_digest"
            ] = arbitrary_digest
            observations["parents"][failure_id]["cron_lookup_failure"][
                "gateway_revision_digest"
            ] = arbitrary_digest
            observations["parents"][failure_id]["source_revision_digest"] = arbitrary_digest
            review["parents"][failure_id]["cron_lookup_failure"][
                "gateway_revision_digest"
            ] = arbitrary_digest
            review["parents"][failure_id]["source_revision_digest"] = arbitrary_digest

        for mutator in (top_unverified, top_extra_field, coordinated_failure_rewrite):
            observations = json.loads(json.dumps(base_observations))
            review = json.loads(json.dumps(base_review))
            mutator(observations, review)
            review["review_status"] = "review_required"
            review["review_basis"] = self.generator.PENDING_REVIEW_BASIS
            review["approved_observation_digest"] = self.generator.canonical_digest(observations)
            with tempfile.TemporaryDirectory() as temp_dir:
                observations_path = Path(temp_dir) / "observations.json"
                review_path = Path(temp_dir) / "review.json"
                output_path = Path(temp_dir) / "inventory.tsv"
                observations_path.write_text(json.dumps(observations), encoding="utf-8")
                review_path.write_text(json.dumps(review), encoding="utf-8")
                with self.subTest(mutator=mutator.__name__), mock.patch.object(
                    sys,
                    "argv",
                    [
                        str(GENERATOR), "--check", "--parent", str(PARENT),
                        "--observations", str(observations_path),
                        "--review", str(review_path), "--objects", str(OBJECTS),
                        "--output", str(output_path),
                    ],
                ), self.assertRaisesRegex(SystemExit, "OpenClaw revision binding mismatch"):
                    self.generator.main()

    def test_cron_absence_requires_exact_schema_and_review_binding(self) -> None:
        parent = {
            "inventory_id": "openclaw:missing-job", "source_type": "openclaw_cron",
            "entrypoint": "openclaw_gateway:agentTurn:agent=anicca", "state": "enabled",
        }
        evidence = {
            "job_id": "missing-job", "result": "not_found", "list_complete": True,
            "individual_get": "not_found",
            "gateway_revision_digest": "sha256:" + ":".join(["1" * 8] * 8),
            "observed_at": "2026-07-21T00:00:00Z",
        }
        observation = {
            "parent_metadata_digest": self.generator.parent_metadata_digest(parent),
            "source_revision_digest": evidence["gateway_revision_digest"],
            "config_revision_digest": "unverified",
            "source_evidence_locator": "openclaw:version;schema:" + "sha256:" + ":".join(["3" * 8] * 8),
            "config_evidence_locator": "unverified",
            "cron_absence_evidence": evidence,
        }
        review = {
            "decision": "unverified", "decision_basis": "stale_parent_live_job_not_found",
            "evidence_locator": "openclaw-cli:cron-list-complete+cron-get;job:missing-job;result:not_found",
            "references": [],
            "source_revision_digest": observation["source_revision_digest"],
            "config_revision_digest": observation["config_revision_digest"],
            "source_evidence_locator": observation["source_evidence_locator"],
            "config_evidence_locator": observation["config_evidence_locator"],
        }
        with self.assertRaisesRegex(SystemExit, "cron absence review binding"):
            self.generator.validate_parent_review_record(parent, observation, review)
        malformed = {**evidence}
        malformed.pop("observed_at")
        observation["cron_absence_evidence"] = malformed
        review["cron_absence_evidence"] = malformed
        with self.assertRaisesRegex(SystemExit, "invalid cron absence evidence"):
            self.generator.validate_parent_review_record(parent, observation, review)

    def test_revision_chain_rejects_cron_evidence_map_parent_and_review_drift(self) -> None:
        parents = read_tsv(PARENT)
        base_observations = read_json(OBSERVATIONS)
        base_review = read_json(REVIEW)
        failure_id = next(iter(base_observations["cron_lookup_failures"]))

        def assert_rejected(mutator, message: str) -> None:
            observations = json.loads(json.dumps(base_observations))
            review = json.loads(json.dumps(base_review))
            review["review_status"] = "review_required"
            review["review_basis"] = self.generator.PENDING_REVIEW_BASIS
            mutator(observations, review)
            review["approved_observation_digest"] = self.generator.canonical_digest(observations)
            with self.assertRaisesRegex(SystemExit, message):
                self.generator.validate_revision_chain(parents, observations, review)

        def mutate_top_timestamp(observations, review) -> None:
            observations["cron_lookup_failures"][failure_id]["observed_at"] = "2026-07-21T00:00:00Z"

        def mutate_top_schema(observations, review) -> None:
            observations["cron_lookup_failures"][failure_id]["extra"] = "field"

        def mutate_parent_only(observations, review) -> None:
            observations["parents"][failure_id]["cron_lookup_failure"]["observed_at"] = "2026-07-21T00:00:00Z"

        def remove_review_binding(observations, review) -> None:
            review["parents"][failure_id].pop("cron_lookup_failure", None)

        def inject_extra_field_absence(observations, review) -> None:
            job_id = failure_id.removeprefix("openclaw:")
            observations["cron_absence_observations"][failure_id] = {
                "job_id": job_id,
                "result": "not_found",
                "list_complete": True,
                "individual_get": "not_found",
                "gateway_revision_digest": observations["parents"][failure_id]["source_revision_digest"],
                "observed_at": "2026-07-21T00:00:00Z",
                "extra": "field",
            }

        cases = (
            (mutate_top_timestamp, "cron lookup failure map binding mismatch"),
            (mutate_top_schema, "invalid cron lookup failure evidence"),
            (mutate_parent_only, "cron lookup failure map binding mismatch"),
            (remove_review_binding, "cron lookup failure review binding mismatch"),
            (inject_extra_field_absence, "invalid cron absence evidence"),
        )
        for mutator, message in cases:
            with self.subTest(mutator=mutator.__name__):
                assert_rejected(mutator, message)

    def test_approved_review_binds_source_config_and_evidence_for_every_parent(self) -> None:
        parent = {
            "inventory_id": "launchd:fixture", "source_type": "launchd",
            "entrypoint": "/tmp/fixture", "state": "loaded",
        }
        digest = self.generator.parent_metadata_digest(parent)
        observed = {
            "parent_metadata_digest": digest,
            "source_revision_digest": "sha256:" + ":".join(["1" * 8] * 8),
            "config_revision_digest": "sha256:" + ":".join(["2" * 8] * 8),
            "source_evidence_locator": "path:fixture;blob:" + "a" * 40,
            "config_evidence_locator": "path:fixture.plist;blob:" + "b" * 40,
        }
        observations = {
            "parent_inventory_digest": self.generator.canonical_digest([digest]),
            "openclaw_revision": {
                "version_digest": "unverified", "schema_digest": "unverified",
            },
            "cron_lookup_failures": {}, "cron_absence_observations": {},
            "parents": {parent["inventory_id"]: observed},
        }
        review = {
            "schema_version": 2, "review_status": "review_required",
            "review_basis": self.generator.PENDING_REVIEW_BASIS,
            "approved_observation_digest": self.generator.canonical_digest(observations),
            "parents": {parent["inventory_id"]: {
                "parent_metadata_digest": digest,
                "decision": "none", "decision_basis": "entrypoint_reference_review",
                "evidence_locator": "path:fixture", "references": [],
            }},
        }
        with self.assertRaisesRegex(SystemExit, "review revision evidence mismatch"):
            self.generator.validate_revision_chain([parent], observations, review)

    def test_none_review_decision_evidence_binds_current_source_locator(self) -> None:
        parent = {
            "inventory_id": "launchd:fixture", "source_type": "launchd",
            "entrypoint": "/tmp/fixture", "state": "loaded",
        }
        observation = {
            "parent_metadata_digest": self.generator.parent_metadata_digest(parent),
            "source_revision_digest": "sha256:" + ":".join(["1" * 8] * 8),
            "config_revision_digest": "sha256:" + ":".join(["2" * 8] * 8),
            "source_evidence_locator": "launchd-components:path:system:/bin/true;blob:" + "a" * 40,
            "config_evidence_locator": "launchd-safe-config:path:fixture;digest:" + "sha256:" + ":".join(["2" * 8] * 8),
        }
        review = {
            "decision": "none", "decision_basis": "verified_entrypoint_no_credential_reference",
            "evidence_locator": "stale-source-locator", "references": [],
            "source_revision_digest": observation["source_revision_digest"],
            "config_revision_digest": observation["config_revision_digest"],
            "source_evidence_locator": observation["source_evidence_locator"],
            "config_evidence_locator": observation["config_evidence_locator"],
        }
        with self.assertRaisesRegex(SystemExit, "decision evidence mismatch"):
            self.generator.validate_parent_review_record(parent, observation, review)
        review.update({
            "decision": "references",
            "references": [{
                "credential_ref": "env:FIXTURE_TOKEN",
                "evidence_locator": "stale-source-locator;symbol:env.FIXTURE_TOKEN",
            }],
        })
        with self.assertRaisesRegex(SystemExit, "reference evidence mismatch"):
            self.generator.validate_parent_review_record(parent, observation, review)

    def test_unresolved_account_identity_cannot_share_or_overwrite_object(self) -> None:
        parents = [
            {"inventory_id": "launchd:a", "source_type": "launchd", "entrypoint": "a", "state": "loaded"},
            {"inventory_id": "launchd:b", "source_type": "launchd", "entrypoint": "b", "state": "loaded"},
        ]
        shared_id = self.generator.credential_object_id(
            "slack", "unresolved", "env:SLACK_BOT_TOKEN"
        )
        references = {}
        for parent in parents:
            references[parent["inventory_id"]] = {
                "decision": "references", "references": [{
                    "credential_object_id": shared_id,
                    "provider": "slack", "account_alias": "unresolved",
                    "credential_type": "env_ref", "credential_ref": "env:SLACK_BOT_TOKEN",
                    "policy_status": "observed", "policy_basis": "none",
                    "evidence_locator": "symbol:" + parent["inventory_id"],
                    "consumer_locator": parent["inventory_id"],
                    "permission_scope": "chat:write",
                }],
            }
        with self.assertRaisesRegex(SystemExit, "unresolved account identity"):
            self.generator.build_credential_objects(
                parents, {"agents": {}, "openclaw_audit": {}}, {"parents": references}
            )

    def test_object_id_is_canonical_and_catalog_cannot_overwrite_review_object(self) -> None:
        artifact = read_json(OBJECTS)
        object_id, record = next(iter(artifact["credential_objects"].items()))
        wrong_id = "credential:object-999999999999999"
        if wrong_id == object_id:
            wrong_id = "credential:object-999999999999998"
        mutated = json.loads(json.dumps(artifact))
        mutated["credential_objects"][wrong_id] = mutated["credential_objects"].pop(object_id)
        with self.assertRaisesRegex(SystemExit, "noncanonical credential object ID"):
            self.generator.validate_credential_objects(mutated)

        provider, account_alias, credential_ref = "deepseek", "agent:anicca", "openclaw-auth:deepseek:sha256:aaaaaaaaaaaaaaaa"
        canonical_id = self.generator.credential_object_id(provider, account_alias, credential_ref)
        review = {"parents": {"launchd:fixture": {"references": [{
            "credential_object_id": canonical_id, "provider": provider,
            "account_alias": account_alias, "credential_type": "token",
            "credential_ref": credential_ref, "policy_status": "observed",
            "policy_basis": "none", "evidence_locator": "review-evidence",
            "consumer_locator": "launchd:fixture", "permission_scope": "model:inference",
        }]}}}
        observations = {
            "agents": {account_alias: {"profiles": [{
                "provider": provider, "alias": "sha256:aaaaaaaaaaaaaaaa", "type": "token",
            }]}},
            "openclaw_audit": {"finding_counts": {}}, "parents": {},
        }
        with self.assertRaisesRegex(SystemExit, "conflicting credential object evidence"):
            self.generator.build_credential_objects([], observations, review)

    def test_finding_objects_require_exact_safe_schema(self) -> None:
        artifact = read_json(OBJECTS)
        finding_id, finding = next(iter(artifact["finding_objects"].items()))
        mutations = (
            ({**finding, "occurrence_count": 0}, "positive occurrence_count"),
            ({**finding, "finding_code": "UNKNOWN_FINDING"}, "unknown finding code"),
            ({**finding, "scope_locator": "/Users/fixture/private"}, "unsafe finding locator"),
            ({**finding, "scope_locator": "openclaw:other"}, "invalid finding tuple"),
            ({**finding, "loop_dependency_attribution": "resolved"}, "invalid finding tuple"),
            ({**finding, "extra": "field"}, "invalid finding object fields"),
        )
        for mutated, message in mutations:
            candidate = json.loads(json.dumps(artifact))
            candidate["finding_objects"][finding_id] = mutated
            with self.subTest(message=message), self.assertRaisesRegex(SystemExit, message):
                self.generator.validate_credential_objects(candidate)

    def test_finding_validator_accepts_every_primary_openclaw_audit_code(self) -> None:
        codes = {"PLAINTEXT_FOUND", "REF_UNRESOLVED", "REF_SHADOWED", "LEGACY_RESIDUE"}
        findings = {
            f"finding:openclaw-config:{code.lower()}-unattributed": {
                "finding_code": code,
                "scope_locator": "openclaw:config",
                "occurrence_count": 1,
                "loop_dependency_attribution": "unresolved",
            }
            for code in codes
        }
        try:
            self.generator.validate_credential_objects({
                "schema_version": 2, "credential_objects": {}, "finding_objects": findings,
            })
        except SystemExit as error:
            self.fail(str(error))

    def test_edge_cross_field_invariants_reject_each_single_field_mutation(self) -> None:
        observations = read_json(OBSERVATIONS)
        objects = read_json(OBJECTS)
        rows = read_tsv(TRACKED)
        observed = next(row for row in rows if row["dependency_status"] == "observed")
        none_edge = next(row for row in rows if row["dependency_status"] == "none_observed")
        unverified = next(row for row in rows if row["dependency_status"] == "unverified")
        object_id = observed["credential_object_id"]
        cases = (
            ({**none_edge, "credential_object_id": object_id}, "none_observed requires none object and scope"),
            ({**unverified, "credential_object_id": "none", "permission_scope": "none"}, "unverified requires unverified object and scope"),
            ({**observed, "dependency_status": "policy_violation"}, "object policy_status mismatch"),
            ({**observed, "permission_scope": "unverified"}, "concrete permission scope required"),
        )
        for edge, message in cases:
            parent_id = edge["inventory_id"]
            with self.subTest(message=message), self.assertRaisesRegex(SystemExit, message):
                self.generator.validate_loop_dependency_edges(
                    [edge], {parent_id},
                    {"parents": {parent_id: observations["parents"][parent_id]}},
                    objects,
                )

        inactive = next(row for row in rows if row["dependency_status"] == "inactive")
        parent_id = inactive["inventory_id"]
        with self.assertRaisesRegex(SystemExit, "inactive requires disabled live cron"):
            self.generator.validate_loop_dependency_edges(
                [{**inactive, "loop_state": "enabled"}], {parent_id},
                {"parents": {parent_id: observations["parents"][parent_id]}}, objects,
            )
        without_live_cron = json.loads(json.dumps(observations["parents"][parent_id]))
        without_live_cron.pop("cron_metadata", None)
        with self.assertRaisesRegex(SystemExit, "inactive requires disabled live cron"):
            self.generator.validate_loop_dependency_edges(
                [inactive], {parent_id}, {"parents": {parent_id: without_live_cron}}, objects,
            )

    def test_openclaw_observed_edges_require_verified_live_cron_provenance(self) -> None:
        observations = read_json(OBSERVATIONS)
        objects = read_json(OBJECTS)
        edge = next(
            row for row in read_tsv(TRACKED)
            if row["inventory_id"].startswith("openclaw:")
            and row["dependency_status"] in {"observed", "policy_violation"}
        )
        parent_id = edge["inventory_id"]
        baseline = observations["parents"][parent_id]

        def without_cron(observation, candidate) -> None:
            observation.pop("cron_metadata")

        def disabled(observation, candidate) -> None:
            observation["cron_metadata"]["enabled"] = False

        def wrong_payload(observation, candidate) -> None:
            observation["cron_metadata"]["payload_kind"] = "systemEvent"

        def unverified_inspection(observation, candidate) -> None:
            observation["inspection_status"] = "unverified"

        def unverified_source(observation, candidate) -> None:
            observation["source_revision_digest"] = "unverified"
            candidate["source_revision_digest"] = "unverified"

        def unverified_config(observation, candidate) -> None:
            observation["config_revision_digest"] = "unverified"
            candidate["config_revision_digest"] = "unverified"

        for mutator in (
            without_cron, disabled, wrong_payload, unverified_inspection,
            unverified_source, unverified_config,
        ):
            observation = json.loads(json.dumps(baseline))
            candidate = dict(edge)
            mutator(observation, candidate)
            with self.subTest(mutator=mutator.__name__), self.assertRaisesRegex(
                SystemExit, "OpenClaw observed edge requires verified live cron provenance"
            ):
                self.generator.validate_loop_dependency_edges(
                    [candidate], {parent_id}, {"parents": {parent_id: observation}}, objects,
                )

    def test_openclaw_observed_edge_requires_matching_reviewed_derived_reference(self) -> None:
        observations = read_json(OBSERVATIONS)
        review = read_json(REVIEW)
        objects = read_json(OBJECTS)
        edge = next(
            row for row in read_tsv(TRACKED)
            if row["inventory_id"].startswith("openclaw:")
            and row["dependency_status"] in {"observed", "policy_violation"}
        )
        parent_id = edge["inventory_id"]
        reviewed_parent = review["parents"][parent_id]
        matching = next(
            reference for reference in reviewed_parent["derived_references"]
            if reference["credential_object_id"] == edge["credential_object_id"]
            and reference["evidence_locator"] == edge["evidence_locator"]
        )
        missing = json.loads(json.dumps(reviewed_parent))
        missing["derived_references"].remove(matching)
        replaced = json.loads(json.dumps(reviewed_parent))
        replacement = next(
            reference for reference in replaced["derived_references"]
            if reference != matching
        )
        replacement["evidence_locator"] = matching["evidence_locator"]
        replacement["credential_object_id"] = matching["credential_object_id"]
        for candidate_review in (missing, replaced):
            try:
                with self.subTest(candidate_review=candidate_review), self.assertRaisesRegex(
                    SystemExit, "OpenClaw edge derived reference mismatch"
                ):
                    self.generator.validate_loop_dependency_edges(
                        [edge], {parent_id},
                        {"parents": {parent_id: observations["parents"][parent_id]}},
                        objects, {"parents": {parent_id: candidate_review}},
                    )
            except TypeError:
                self.fail("edge validator must accept reviewed provenance")

    def test_coherently_unverified_disabled_openclaw_generates_unverified_edge(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            parent_path = temp / "parents.tsv"
            parent_path.write_text(
                "inventory_id\tsource_type\tentrypoint\tstate\tevidence\n"
                "openclaw:disabled-fixture\topenclaw_cron\t"
                "openclaw_gateway:agentTurn:agent=anicca\tdisabled\tsafe-parent-metadata\n",
                encoding="utf-8",
            )
            parent = read_tsv(parent_path)[0]
            observed = {
                "parent_metadata_digest": self.generator.parent_metadata_digest(parent),
                "source_revision_digest": "unverified",
                "config_revision_digest": "unverified",
                "source_evidence_locator": "unverified",
                "config_evidence_locator": "unverified",
                "inspection_status": "unverified",
                "reason": "gateway_revision_unavailable",
                "cron_metadata": {"enabled": False, "payload_kind": "agentTurn"},
            }
            observations = {
                "schema_version": 1,
                "parent_inventory_digest": self.generator.canonical_digest(
                    [self.generator.parent_metadata_digest(parent)]
                ),
                "openclaw_revision": {
                    "version_digest": "unverified", "schema_digest": "unverified",
                },
                "cron_lookup_failures": {}, "cron_absence_observations": {},
                "parents": {parent["inventory_id"]: observed},
                "agents": {}, "openclaw_audit": {"finding_counts": {}},
            }
            review = {
                "schema_version": 2, "review_status": "review_required",
                "review_basis": self.generator.PENDING_REVIEW_BASIS,
                "approved_observation_digest": self.generator.canonical_digest(observations),
                "parents": {parent["inventory_id"]: {
                    "parent_metadata_digest": observed["parent_metadata_digest"],
                    "source_revision_digest": "unverified",
                    "config_revision_digest": "unverified",
                    "source_evidence_locator": "unverified",
                    "config_evidence_locator": "unverified",
                    "decision": "unverified",
                    "decision_basis": "gateway_revision_unavailable",
                    "evidence_locator": "safe-observation:gateway-revision-unavailable",
                    "references": [],
                }},
            }
            objects = {
                "schema_version": 2, "credential_objects": {}, "finding_objects": {},
            }
            self.generator.validate_revision_chain(
                [parent], observations, review, candidate=True
            )
            rows = self.generator.build_loop_dependency_edges(
                [parent], observations, review, objects
            )
            self.generator.validate_loop_dependency_edges(
                rows, {parent["inventory_id"]}, observations, objects, review
            )
        self.assertEqual(1, len(rows))
        self.assertEqual("unverified", rows[0]["dependency_status"])

    def test_openclaw_inactive_edge_requires_verified_review_provenance(self) -> None:
        observations = read_json(OBSERVATIONS)
        review = read_json(REVIEW)
        objects = read_json(OBJECTS)
        edge = next(
            row for row in read_tsv(TRACKED)
            if row["dependency_status"] == "inactive"
            and review["parents"][row["inventory_id"]]["decision"] == "dynamic_openclaw"
            and observations["parents"][row["inventory_id"]]["inspection_status"] == "verified"
        )
        parent_id = edge["inventory_id"]
        base_observation = observations["parents"][parent_id]
        base_review = review["parents"][parent_id]

        def inspection_unverified(observation, reviewed, candidate) -> None:
            observation["inspection_status"] = "unverified"

        def source_unverified(observation, reviewed, candidate) -> None:
            observation["source_revision_digest"] = "unverified"
            observation["source_evidence_locator"] = "unverified"
            reviewed["source_revision_digest"] = "unverified"
            reviewed["source_evidence_locator"] = "unverified"
            candidate["source_revision_digest"] = "unverified"

        def config_unverified(observation, reviewed, candidate) -> None:
            observation["config_revision_digest"] = "unverified"
            observation["config_evidence_locator"] = "unverified"
            reviewed["config_revision_digest"] = "unverified"
            reviewed["config_evidence_locator"] = "unverified"
            candidate["config_revision_digest"] = "unverified"

        def review_unverified(observation, reviewed, candidate) -> None:
            reviewed["decision"] = "unverified"

        for mutator in (
            inspection_unverified, source_unverified, config_unverified, review_unverified,
        ):
            observation = json.loads(json.dumps(base_observation))
            reviewed = json.loads(json.dumps(base_review))
            candidate = dict(edge)
            mutator(observation, reviewed, candidate)
            with self.subTest(mutator=mutator.__name__), self.assertRaisesRegex(
                SystemExit, "inactive requires verified OpenClaw review provenance"
            ):
                self.generator.validate_loop_dependency_edges(
                    [candidate], {parent_id}, {"parents": {parent_id: observation}},
                    objects, {"parents": {parent_id: reviewed}},
                )

    def test_openclaw_objects_are_unique_and_edges_are_loop_specific(self) -> None:
        parent = {"inventory_id": "openclaw:fixture-job", "source_type": "openclaw_cron", "entrypoint": "openclaw_gateway:agentTurn:agent=anicca", "state": "enabled"}
        observation = {
            "parents": {
                parent["inventory_id"]: {
                    "parent_metadata_digest": self.generator.parent_metadata_digest(parent),
                    "source_revision_digest": "sha256:" + ":".join(["1" * 8] * 8),
                    "config_revision_digest": "sha256:" + ":".join(["2" * 8] * 8),
                    "source_evidence_locator": "openclaw:version;schema:" + "sha256:" + ":".join(["3" * 8] * 8),
                    "config_evidence_locator": "openclaw-cli:cron-list-safe-projection;job:fixture-job",
                    "inspection_status": "verified",
                    "agent_alias": "agent:anicca",
                    "cron_metadata": {"enabled": True, "payload_kind": "agentTurn", "model_ref": "deepseek/model", "fallback_refs": [], "fallbacks_inherited": False, "tools_allow": [], "tools_inherited": True, "delivery_provider": "none"},
                }
            },
            "agents": {
                "agent:anicca": {
                    "inspection_status": "verified",
                    "provider_chain": ["deepseek"],
                    "profiles": [{"alias": "sha256:aaaaaaaaaaaaaaaa", "provider": "deepseek", "type": "token"}],
                }
            },
            "openclaw_audit": {"finding_counts": {"PLAINTEXT_FOUND:unattributed": 21}},
        }
        review = {"parents": {parent["inventory_id"]: {
            "decision": "dynamic_openclaw", "decision_basis": "official_cli_safe_projection",
            "source_revision_digest": observation["parents"][parent["inventory_id"]]["source_revision_digest"],
            "config_revision_digest": observation["parents"][parent["inventory_id"]]["config_revision_digest"],
            "source_evidence_locator": observation["parents"][parent["inventory_id"]]["source_evidence_locator"],
            "config_evidence_locator": observation["parents"][parent["inventory_id"]]["config_evidence_locator"],
            "job_evidence_locator": observation["parents"][parent["inventory_id"]]["config_evidence_locator"],
            "derived_references": [
                {
                    "kind": "model",
                    "credential_object_id": self.generator.credential_object_id(
                        "deepseek", "agent:anicca",
                        "openclaw-auth:deepseek:sha256:aaaaaaaaaaaaaaaa",
                    ),
                    "evidence_locator": observation["parents"][parent["inventory_id"]]["config_evidence_locator"] + "#model[0]",
                },
                {
                    "kind": "tools", "credential_object_id": "unverified",
                    "evidence_locator": observation["parents"][parent["inventory_id"]]["config_evidence_locator"] + "#tools-inherited",
                },
            ], "references": [],
        }}}
        objects = self.generator.build_credential_objects([parent], observation, review)
        edges = self.generator.build_loop_dependency_edges([parent], observation, review, objects)
        self.assertEqual(1, len(objects["credential_objects"]))
        self.assertEqual(1, len(objects["finding_objects"]))
        self.assertEqual(2, len(edges))
        observed_edge = next(edge for edge in edges if edge["dependency_status"] == "observed")
        self.assertIn(observed_edge["credential_object_id"], objects["credential_objects"])
        self.assertNotIn("provider", observed_edge)
        self.assertNotIn("credential_ref", observed_edge)

    def test_enabled_telegram_delivery_gets_consumer_specific_object_and_edge(self) -> None:
        parent = {
            "inventory_id": "openclaw:telegram-job", "source_type": "openclaw_cron",
            "entrypoint": "openclaw_gateway:agentTurn:agent=anicca", "state": "enabled",
        }
        parent_observation = {
            "parent_metadata_digest": self.generator.parent_metadata_digest(parent),
            "source_revision_digest": "sha256:" + ":".join(["1" * 8] * 8),
            "config_revision_digest": "sha256:" + ":".join(["2" * 8] * 8),
            "source_evidence_locator": "openclaw:version;schema:" + "sha256:" + ":".join(["3" * 8] * 8),
            "config_evidence_locator": "openclaw-cli:cron-list-safe-projection;job:telegram-job",
            "inspection_status": "verified", "agent_alias": "agent:anicca",
            "cron_metadata": {
                "enabled": True, "payload_kind": "agentTurn",
                "model_ref": "deepseek/model", "fallback_refs": [],
                "fallbacks_inherited": False, "tools_allow": [],
                "tools_inherited": True, "delivery_provider": "telegram",
            },
        }
        observations = {
            "parents": {parent["inventory_id"]: parent_observation},
            "agents": {"agent:anicca": {
                "inspection_status": "verified", "provider_chain": ["deepseek"],
                "profiles": [{"alias": "sha256:aaaaaaaaaaaaaaaa", "provider": "deepseek", "type": "token"}],
            }},
            "openclaw_audit": {"finding_counts": {}},
        }
        objects_artifact = self.generator.build_credential_objects(
            [parent], observations, {"parents": {}}
        )
        objects = objects_artifact["credential_objects"]
        telegram_objects = {
            object_id: record for object_id, record in objects.items()
            if record["provider"] == "telegram"
        }
        self.assertEqual(1, len(telegram_objects))
        telegram_id, telegram = next(iter(telegram_objects.items()))
        self.assertEqual("unresolved:openclaw:telegram-job", telegram["account_alias"])
        derived = self.generator.expected_openclaw_derived_references(
            parent, parent_observation, observations["agents"]["agent:anicca"], objects
        )
        edges = self.generator.openclaw_parent_edges(
            parent, parent_observation, objects, derived,
            {"decision": "dynamic_openclaw"},
        )
        delivery = next(edge for edge in edges if edge["dependency_basis"] == "cron_delivery_route")
        self.assertEqual(telegram_id, delivery["credential_object_id"])
        self.assertEqual("message:send", delivery["permission_scope"])

    def test_inherited_openclaw_tools_add_fail_closed_unverified_edge(self) -> None:
        parent = {
            "inventory_id": "openclaw:tools-job", "source_type": "openclaw_cron",
            "entrypoint": "openclaw_gateway:agentTurn:agent=anicca", "state": "enabled",
        }
        observation = {
            "parent_metadata_digest": self.generator.parent_metadata_digest(parent),
            "source_revision_digest": "sha256:" + ":".join(["1" * 8] * 8),
            "config_revision_digest": "sha256:" + ":".join(["2" * 8] * 8),
            "inspection_status": "verified", "agent_alias": "agent:anicca",
            "cron_metadata": {
                "enabled": True, "payload_kind": "agentTurn",
                "model_ref": "deepseek/model", "fallback_refs": [],
                "fallbacks_inherited": False, "tools_allow": [],
                "tools_inherited": True, "delivery_provider": "none",
            },
        }
        profile_ref = "openclaw-auth:deepseek:sha256:aaaaaaaaaaaaaaaa"
        object_id = self.generator.credential_object_id("deepseek", "agent:anicca", profile_ref)
        objects = {object_id: {
            "provider": "deepseek", "account_alias": "agent:anicca",
            "credential_type": "token", "credential_ref": profile_ref,
            "policy_status": "observed", "policy_basis": "none",
            "evidence_locator": "openclaw-cli:models-auth-list",
        }}
        derived = self.generator.expected_openclaw_derived_references(
            parent, observation, {"provider_chain": ["deepseek"], "profiles": []}, objects
        )
        edges = self.generator.openclaw_parent_edges(
            parent, observation, objects, derived,
            {"decision": "dynamic_openclaw"},
        )
        tools_edges = [edge for edge in edges if edge["dependency_basis"] == "tools_inherited_unresolved"]
        self.assertEqual(1, len(tools_edges))
        tools_edge = tools_edges[0]
        self.assertEqual("unverified", tools_edge["dependency_status"])
        self.assertEqual("unverified", tools_edge["credential_object_id"])
        self.assertEqual("unverified", tools_edge["permission_scope"])

    def test_disabled_openclaw_loop_has_no_active_credential_dependency(self) -> None:
        parent = {"inventory_id": "openclaw:disabled", "source_type": "openclaw_cron", "entrypoint": "openclaw_gateway:agentTurn:agent=anicca", "state": "disabled"}
        observation = {
            "parent_metadata_digest": self.generator.parent_metadata_digest(parent),
            "source_revision_digest": "sha256:" + ":".join(["1" * 8] * 8),
            "config_revision_digest": "sha256:" + ":".join(["2" * 8] * 8),
            "inspection_status": "verified",
            "cron_metadata": {"enabled": False, "payload_kind": "agentTurn"},
        }
        edge = self.generator.openclaw_parent_edges(
            parent, observation, {}, [], {"decision": "dynamic_openclaw"}
        )[0]
        self.assertEqual("inactive", edge["dependency_status"])
        self.assertEqual("none", edge["credential_object_id"])

    def test_live_cron_disabled_state_overrides_stale_parent_enabled_state(self) -> None:
        parent = {"inventory_id": "openclaw:stale", "source_type": "openclaw_cron", "entrypoint": "openclaw_gateway:agentTurn:agent=anicca", "state": "enabled"}
        observation = {
            "parent_metadata_digest": self.generator.parent_metadata_digest(parent),
            "source_revision_digest": "sha256:" + ":".join(["1" * 8] * 8),
            "config_revision_digest": "sha256:" + ":".join(["2" * 8] * 8),
            "inspection_status": "verified",
            "cron_metadata": {"enabled": False, "payload_kind": "agentTurn"},
        }
        edge = self.generator.openclaw_parent_edges(
            parent, observation, {}, [], {"decision": "dynamic_openclaw"}
        )[0]
        self.assertEqual("inactive", edge["dependency_status"])
        self.assertEqual("disabled", edge["loop_state"])

    def test_repository_revision_record_preserves_portable_commit_tree_and_blob_oids(self) -> None:
        values = {
            ("git", "rev-parse", "HEAD"): "a" * 40,
            ("git", "rev-parse", "HEAD^{tree}"): "b" * 40,
            ("git", "rev-parse", "HEAD:apps/api/package.json"): "c" * 40,
        }

        def fake_runner(argv):
            return subprocess.CompletedProcess(argv, 0, stdout=values[argv] + "\n", stderr="")

        parent = {
            "inventory_id": "package:apps/api/package.json#start",
            "source_type": "repository_entrypoint",
            "entrypoint": "node server.js",
            "state": "declared_in_repository",
            "evidence": "apps/api/package.json",
        }
        record = self.collector.source_revision_record(parent, fake_runner)
        self.assertEqual(
            self.collector.format_sha256_digest(
                self.collector.hashlib.sha256(record["evidence_locator"].encode()).hexdigest()
            ),
            record["digest"],
        )
        for oid in values.values():
            self.assertIn(oid, record["evidence_locator"])
        self.assertNotIn(str(REPO.parent), record["evidence_locator"])

    def test_repository_reference_evidence_follows_start_import_graph_with_path_blob_and_line(self) -> None:
        scanner = getattr(self.collector, "collect_repository_reference_evidence", None)
        self.assertIsNotNone(scanner, "repository import-graph evidence collector is missing")
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            package = root / "apps/api"
            (package / "src/services").mkdir(parents=True)
            (package / "package.json").write_text(
                json.dumps({"scripts": {"start": "node src/server.js"}}), encoding="utf-8"
            )
            (package / "src/server.js").write_text(
                "import './routes.js';\nimport('./services/apns.js');\n", encoding="utf-8"
            )
            (package / "src/routes.js").write_text(
                "const oldToken = process.env.ANICCA_AGENT_TOKEN_OLD;\n"
                "const database = process.env.DATABASE_URL;\n"
                "import './services/slack.js';\n",
                encoding="utf-8",
            )
            (package / "src/services/apns.js").write_text(
                "const keyId = process.env.APNS_KEY_ID;\n"
                "const p8 = process.env.APNS_PRIVATE_KEY_P8;\n",
                encoding="utf-8",
            )
            (package / "src/services/slack.js").write_text(
                "const hook = process.env.SLACK_WEBHOOK_AGENTS;\n", encoding="utf-8"
            )
            (package / "src/orphan.js").write_text(
                "const ignored = process.env.ORPHAN_API_KEY;\n", encoding="utf-8"
            )
            parent = {
                "inventory_id": "package:apps/api/package.json#start",
                "source_type": "repository_entrypoint",
                "entrypoint": "node src/server.js",
                "evidence": "apps/api/package.json",
            }
            records = scanner(parent, repo_root=root)
        self.assertEqual(
            {"ANICCA_AGENT_TOKEN_OLD", "APNS_KEY_ID", "APNS_PRIVATE_KEY_P8", "DATABASE_URL", "SLACK_WEBHOOK_AGENTS"},
            {record["reference_name"] for record in records},
        )
        self.assertNotIn("ORPHAN_API_KEY", {record["reference_name"] for record in records})
        for record in records:
            self.assertEqual(
                {"reference_name", "path", "blob_oid", "line", "symbol_locator"},
                set(record),
            )
            self.assertRegex(record["blob_oid"], r"^[0-9a-f]{40,64}$")
            self.assertGreater(record["line"], 0)
            self.assertNotEqual("apps/api/package.json", record["path"])

    def test_repository_ast_reference_projection_covers_js_ts_forms_and_literal_helpers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            package = root / "apps/api"
            (package / "src").mkdir(parents=True)
            (package / "package.json").write_text(
                json.dumps({"scripts": {"start": "node src/server.js"}}), encoding="utf-8"
            )
            (package / "src/server.js").write_text(
                "import './client.ts';\n", encoding="utf-8"
            )
            (package / "src/client.ts").write_text(
                "const direct = process.env.DIRECT_API_KEY;\n"
                "const bracket = process.env['BRACKET_TOKEN'];\n"
                "const { DESTRUCTURED_SECRET } = process.env;\n"
                "function requiredEnv(name: string) { return process.env[name]; }\n"
                "const helper = requiredEnv('MOLTBOOK_ACCESS_TOKEN');\n",
                encoding="utf-8",
            )
            parent = {
                "inventory_id": "package:apps/api/package.json#start",
                "source_type": "repository_entrypoint",
                "entrypoint": "node src/server.js",
                "evidence": "apps/api/package.json",
            }
            records = self.collector.collect_repository_reference_evidence(
                parent, repo_root=root
            )
        self.assertEqual(
            {
                "DIRECT_API_KEY", "BRACKET_TOKEN", "DESTRUCTURED_SECRET",
                "MOLTBOOK_ACCESS_TOKEN",
            },
            {record["reference_name"] for record in records},
        )

    def test_repository_ast_reference_projection_fails_closed_on_unresolved_dynamic_env(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            package = root / "apps/api"
            (package / "src").mkdir(parents=True)
            (package / "package.json").write_text(
                json.dumps({"scripts": {"start": "node src/server.js"}}), encoding="utf-8"
            )
            (package / "src/server.js").write_text(
                "const name = getName();\nconst value = process.env[name];\n",
                encoding="utf-8",
            )
            parent = {
                "inventory_id": "package:apps/api/package.json#start",
                "source_type": "repository_entrypoint",
                "entrypoint": "node src/server.js",
                "evidence": "apps/api/package.json",
            }
            with self.assertRaisesRegex(RuntimeError, "dynamic environment reference unresolved"):
                self.collector.collect_repository_reference_evidence(parent, repo_root=root)

    def _scan_single_repository_source(self, source: str) -> list[dict[str, object]]:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            package = root / "apps/api"
            (package / "src").mkdir(parents=True)
            (package / "package.json").write_text(
                json.dumps({"scripts": {"start": "node src/server.js"}}), encoding="utf-8"
            )
            (package / "src/server.js").write_text(source, encoding="utf-8")
            return self.collector.collect_repository_reference_evidence(
                {
                    "inventory_id": "package:apps/api/package.json#start",
                    "source_type": "repository_entrypoint",
                    "entrypoint": "node src/server.js",
                    "evidence": "apps/api/package.json",
                },
                repo_root=root,
            )

    def test_repository_ast_resolves_environment_alias_by_lexical_symbol(self) -> None:
        records = self._scan_single_repository_source(
            "const env = process.env;\nconst value = env.ALIASED_ENV_TOKEN;\n"
        )
        self.assertEqual(
            {"ALIASED_ENV_TOKEN"}, {record["reference_name"] for record in records}
        )

    def test_repository_ast_resolves_helper_alias_by_lexical_symbol(self) -> None:
        records = self._scan_single_repository_source(
            "function requiredEnv(name) { return process.env[name]; }\n"
            "const alias = requiredEnv;\n"
            "const value = alias('ALIASED_TOKEN');\n"
        )
        self.assertEqual(
            {"ALIASED_TOKEN"}, {record["reference_name"] for record in records}
        )

    def test_repository_ast_resolves_nested_helper_parameter_flow_to_fixpoint(self) -> None:
        records = self._scan_single_repository_source(
            "function inner(name) { return process.env[name]; }\n"
            "function outer(name) { return inner(name); }\n"
            "const value = outer('NESTED_TOKEN');\n"
        )
        self.assertEqual(
            {"NESTED_TOKEN"}, {record["reference_name"] for record in records}
        )

    def test_repository_ast_does_not_cross_lexical_shadowing(self) -> None:
        records = self._scan_single_repository_source(
            "const env = process.env;\n"
            "{ const env = {}; const ignored = env.SHADOWED_TOKEN; }\n"
            "const value = env.OUTER_TOKEN;\n"
        )
        names = {record["reference_name"] for record in records}
        self.assertEqual({"OUTER_TOKEN"}, names)
        self.assertNotIn("SHADOWED_TOKEN", names)

    def test_repository_ast_fails_closed_on_reassigned_alias_flow(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "dynamic environment reference unresolved"):
            self._scan_single_repository_source(
                "let env = process.env;\n"
                "env = getRuntimeEnvironment();\n"
                "const value = env.REASSIGNED_TOKEN;\n"
            )

    def test_repository_ast_resolves_environment_alias_assigned_after_declaration(self) -> None:
        records = self._scan_single_repository_source(
            "let env;\nenv = process.env;\nconst value = env.ASSIGNED_ENV_TOKEN;\n"
        )
        self.assertEqual(
            {"ASSIGNED_ENV_TOKEN"}, {record["reference_name"] for record in records}
        )

    def test_repository_ast_resolves_helper_alias_assigned_after_declaration(self) -> None:
        records = self._scan_single_repository_source(
            "function requiredEnv(name) { return process.env[name]; }\n"
            "let alias;\nalias = requiredEnv;\n"
            "const value = alias('ASSIGNED_HELPER_TOKEN');\n"
        )
        self.assertEqual(
            {"ASSIGNED_HELPER_TOKEN"}, {record["reference_name"] for record in records}
        )

    def test_repository_ast_resolves_process_alias_by_global_symbol_identity(self) -> None:
        records = self._scan_single_repository_source(
            "const proc = process;\nconst value = proc.env.PROCESS_ALIAS_TOKEN;\n"
        )
        self.assertEqual(
            {"PROCESS_ALIAS_TOKEN"}, {record["reference_name"] for record in records}
        )

    def test_repository_ast_keeps_global_process_identity_after_property_write(self) -> None:
        records = self._scan_single_repository_source(
            "process.env.RUNTIME_FLAG = 'false';\n"
            "const value = process.env.GLOBAL_PROCESS_TOKEN;\n"
        )
        self.assertEqual(
            {"GLOBAL_PROCESS_TOKEN"}, {record["reference_name"] for record in records}
        )

    def test_repository_ast_does_not_fail_closed_on_unrelated_recursion(self) -> None:
        records = self._scan_single_repository_source(
            "function recurse(value) { return value ? recurse(value - 1) : 0; }\n"
            "const token = process.env.STABLE_RECURSION_TOKEN;\n"
        )
        self.assertEqual(
            {"STABLE_RECURSION_TOKEN"}, {record["reference_name"] for record in records}
        )

    def test_repository_ast_treats_generated_prisma_as_dependency_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            package = root / "apps/api"
            generated = package / "src/generated/prisma/runtime"
            generated.mkdir(parents=True)
            (package / "package.json").write_text("{}", encoding="utf-8")
            (package / "src/server.js").write_text(
                "import './generated/prisma/runtime/library.js';\n"
                "import './owned.js';\n",
                encoding="utf-8",
            )
            (package / "src/owned.js").write_text(
                "const value = process.env.OWNED_SOURCE_TOKEN;\n", encoding="utf-8"
            )
            (generated / "library.js").write_text(
                "const env = flag ? {} : process.env;\nconst value = env[name];\n",
                encoding="utf-8",
            )
            records = self.collector.collect_repository_reference_evidence(
                {
                    "source_type": "repository_entrypoint",
                    "entrypoint": "node src/server.js",
                    "evidence": "apps/api/package.json",
                },
                repo_root=root,
            )
        self.assertEqual(
            {"OWNED_SOURCE_TOKEN"}, {record["reference_name"] for record in records}
        )

    def test_repository_ast_resolves_equivalent_conditional_aliases(self) -> None:
        records = self._scan_single_repository_source(
            "function requiredEnv(name) { return process.env[name]; }\n"
            "const env = enabled ? process.env : process.env;\n"
            "const reader = enabled ? requiredEnv : requiredEnv;\n"
            "const direct = env.CONDITIONAL_ENV_TOKEN;\n"
            "const helper = reader('CONDITIONAL_HELPER_TOKEN');\n"
        )
        self.assertEqual(
            {"CONDITIONAL_ENV_TOKEN", "CONDITIONAL_HELPER_TOKEN"},
            {record["reference_name"] for record in records},
        )

    def test_repository_ast_fails_closed_on_partially_unknown_conditional_alias(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "dynamic environment reference unresolved"):
            self._scan_single_repository_source(
                "const env = enabled ? process.env : getRuntimeEnvironment();\n"
                "const value = env.CONDITIONAL_UNKNOWN_TOKEN;\n"
            )

    def test_repository_ast_resolves_higher_order_helper_argument_and_return_flow(self) -> None:
        records = self._scan_single_repository_source(
            "function requiredEnv(name) { return process.env[name]; }\n"
            "function identity(reader) { return reader; }\n"
            "function invoke(reader, name) { return reader(name); }\n"
            "const alias = identity(requiredEnv);\n"
            "const value = invoke(alias, 'HIGHER_ORDER_TOKEN');\n"
        )
        self.assertEqual(
            {"HIGHER_ORDER_TOKEN"}, {record["reference_name"] for record in records}
        )

    def test_repository_ast_ignores_lexically_shadowed_process_parameter(self) -> None:
        records = self._scan_single_repository_source(
            "function local(process) { return process.env.SHADOWED_PROCESS_TOKEN; }\n"
        )
        self.assertEqual([], records)

    def test_repository_ast_tolerates_uninitialized_variables(self) -> None:
        records = self._scan_single_repository_source(
            "let delayed;\nconst value = process.env.STABLE_TOKEN;\n"
        )
        self.assertEqual(
            {"STABLE_TOKEN"}, {record["reference_name"] for record in records}
        )

    def test_repository_ast_tolerates_destructuring_without_initializer(self) -> None:
        records = self._scan_single_repository_source(
            "for (const { value } of []) {}\n"
            "const current = process.env.STABLE_TOKEN;\n"
        )
        self.assertEqual(
            {"STABLE_TOKEN"}, {record["reference_name"] for record in records}
        )

    def test_repository_ast_scans_object_literal_and_constructor_arguments(self) -> None:
        records = self._scan_single_repository_source(
            "const config = { secret: process.env.OBJECT_LITERAL_SECRET };\n"
            "const client = new Client({ token: process.env.CONSTRUCTOR_TOKEN });\n"
        )
        self.assertEqual(
            {"OBJECT_LITERAL_SECRET", "CONSTRUCTOR_TOKEN"},
            {record["reference_name"] for record in records},
        )

    def test_repository_ast_scans_conditional_tests_and_callback_bodies(self) -> None:
        records = self._scan_single_repository_source(
            "function mode() { return process.env.CONDITIONAL_TEST_TOKEN ? 'a' : 'b'; }\n"
            "router.post('/', async () => {\n"
            "  const secret = process.env.CALLBACK_BODY_SECRET;\n"
            "});\n"
        )
        self.assertEqual(
            {"CONDITIONAL_TEST_TOKEN", "CALLBACK_BODY_SECRET"},
            {record["reference_name"] for record in records},
        )

    def test_repository_ast_fails_closed_when_unknown_callee_receives_environment(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "dynamic environment reference unresolved"):
            self._scan_single_repository_source("unknownHelper(process.env);\n")

    def test_repository_ast_fails_closed_when_imported_callee_receives_environment(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            package = root / "apps/api"
            (package / "src").mkdir(parents=True)
            (package / "package.json").write_text("{}", encoding="utf-8")
            (package / "src/server.js").write_text(
                "import { inspectEnvironment } from './helper.js';\n"
                "inspectEnvironment(process.env);\n",
                encoding="utf-8",
            )
            (package / "src/helper.js").write_text(
                "export function inspectEnvironment(env) { return env?.IMPORTED_SECRET; }\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "dynamic environment reference unresolved"):
                self.collector.collect_repository_reference_evidence(
                    {
                        "source_type": "repository_entrypoint",
                        "entrypoint": "node src/server.js",
                        "evidence": "apps/api/package.json",
                    },
                    repo_root=root,
                )

    def test_repository_ast_fails_closed_when_mixed_callee_receives_environment(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "dynamic environment reference unresolved"):
            self._scan_single_repository_source(
                "function inspectEnvironment(env) { return env; }\n"
                "const inspect = enabled ? inspectEnvironment : unknownHelper;\n"
                "inspect(process.env);\n"
            )

    def test_repository_ast_ignores_unknown_call_without_environment_provenance(self) -> None:
        records = self._scan_single_repository_source(
            "function knownHelper(value) { return value; }\n"
            "const maybeHelper = enabled ? knownHelper : unknownHelper;\n"
            "maybeHelper(runtimeConfig);\n"
            "unknownHelper(runtimeConfig);\n"
            "const token = process.env.UNRELATED_UNKNOWN_CALL_TOKEN;\n"
        )
        self.assertEqual(
            {"UNRELATED_UNKNOWN_CALL_TOKEN"},
            {record["reference_name"] for record in records},
        )

    def test_repository_ast_propagates_process_environment_destructuring(self) -> None:
        records = self._scan_single_repository_source(
            "const { env } = process;\nconst token = env.DESTRUCTURED_PROCESS_TOKEN;\n"
        )
        self.assertEqual(
            {"DESTRUCTURED_PROCESS_TOKEN"},
            {record["reference_name"] for record in records},
        )

    def test_repository_ast_propagates_destructured_process_parameter(self) -> None:
        records = self._scan_single_repository_source(
            "function read({ env }) { return env.DESTRUCTURED_PARAMETER_SECRET; }\n"
            "read(process);\n"
        )
        self.assertEqual(
            {"DESTRUCTURED_PARAMETER_SECRET"},
            {record["reference_name"] for record in records},
        )

    def test_repository_ast_propagates_nested_process_destructuring(self) -> None:
        records = self._scan_single_repository_source(
            "const { env: { NESTED_PROCESS_SECRET } } = process;\n"
        )
        self.assertEqual(
            {"NESTED_PROCESS_SECRET"},
            {record["reference_name"] for record in records},
        )

    def test_repository_ast_fails_closed_on_computed_or_rest_process_destructuring(self) -> None:
        for source in (
            "const { [runtimeName]: value } = process.env;\n",
            "const { env, ...remainingProcess } = process;\n",
        ):
            with self.subTest(source=source), self.assertRaisesRegex(
                RuntimeError, "dynamic environment reference unresolved"
            ):
                self._scan_single_repository_source(source)

    def test_repository_ast_fails_closed_on_dynamic_require_or_import(self) -> None:
        for source in (
            "require(runtimeModulePath);\n",
            "import(resolveRuntimeModule());\n",
        ):
            with self.subTest(source=source), self.assertRaisesRegex(
                RuntimeError, "dynamic local import unresolved"
            ):
                self._scan_single_repository_source(source)

    def test_repository_ast_constant_folds_local_relative_import_binding(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            package = root / "apps/api"
            (package / "src").mkdir(parents=True)
            (package / "package.json").write_text("{}", encoding="utf-8")
            (package / "src/server.js").write_text(
                "const localModule = './helper.js';\nrequire(localModule);\n",
                encoding="utf-8",
            )
            (package / "src/helper.js").write_text(
                "const token = process.env.CONSTANT_FOLDED_IMPORT_TOKEN;\n",
                encoding="utf-8",
            )
            records = self.collector.collect_repository_reference_evidence(
                {
                    "source_type": "repository_entrypoint",
                    "entrypoint": "node src/server.js",
                    "evidence": "apps/api/package.json",
                },
                repo_root=root,
            )
        self.assertEqual(
            {"CONSTANT_FOLDED_IMPORT_TOKEN"},
            {record["reference_name"] for record in records},
        )

    def test_repository_literal_relative_import_missing_target_fails_closed(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "literal local import unresolved"):
            self._scan_single_repository_source("import './missing-helper.js';\n")

    def test_repository_literal_relative_import_unsupported_extension_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            package = root / "apps/api"
            (package / "src").mkdir(parents=True)
            (package / "package.json").write_text("{}", encoding="utf-8")
            (package / "src/server.js").write_text(
                "import './helper.json';\n", encoding="utf-8"
            )
            (package / "src/helper.json").write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "unsupported local import extension"):
                self.collector.collect_repository_reference_evidence(
                    {
                        "source_type": "repository_entrypoint",
                        "entrypoint": "node src/server.js",
                        "evidence": "apps/api/package.json",
                    },
                    repo_root=root,
                )

    def test_repository_literal_relative_import_symlink_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root = base / "repo"
            package = root / "apps/api"
            (package / "src").mkdir(parents=True)
            (package / "package.json").write_text("{}", encoding="utf-8")
            (package / "src/server.js").write_text(
                "import './helper.js';\n", encoding="utf-8"
            )
            outside = base / "outside-helper.js"
            outside.write_text("const safe = true;\n", encoding="utf-8")
            (package / "src/helper.js").symlink_to(outside)
            with self.assertRaisesRegex(RuntimeError, "unsafe local import path"):
                self.collector.collect_repository_reference_evidence(
                    {
                        "source_type": "repository_entrypoint",
                        "entrypoint": "node src/server.js",
                        "evidence": "apps/api/package.json",
                    },
                    repo_root=root,
                )

    def test_repository_literal_relative_import_replacement_race_fails_closed(self) -> None:
        actual_parser = (
            REPO / "tools/credential-ast-parser/node_modules/typescript/lib/typescript.js"
        ).read_bytes()
        actual_projector = (REPO / "scripts/project-js-env-references.js").read_bytes()
        real_run = subprocess.run
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root = base / "repo"
            package = root / "apps/api"
            (package / "src").mkdir(parents=True)
            (package / "package.json").write_text("{}", encoding="utf-8")
            source = package / "src/server.js"
            source.write_text("import './helper.js';\n", encoding="utf-8")
            helper = package / "src/helper.js"
            helper.write_text("const safe = true;\n", encoding="utf-8")
            outside = base / "outside-helper.js"
            outside.write_text("const replacement = true;\n", encoding="utf-8")
            parser = self._write_typescript_parser_fixture(root, parser_bytes=actual_parser)
            projector = root / "scripts/project-js-env-references.js"
            projector.parent.mkdir(parents=True)
            projector.write_bytes(actual_projector)
            replaced = False

            def replace_import_after_projection(*args, **kwargs):
                nonlocal replaced
                completed = real_run(*args, **kwargs)
                argv = args[0]
                if not replaced and argv[0] == "node":
                    helper.unlink()
                    helper.symlink_to(outside)
                    replaced = True
                return completed

            with mock.patch.object(self.collector, "REPO", root), mock.patch.object(
                self.collector, "_typescript_module_path", return_value=parser
            ), mock.patch.object(
                self.collector.subprocess, "run", side_effect=replace_import_after_projection
            ), self.assertRaisesRegex(RuntimeError, "unsafe local import path"):
                self.collector.collect_repository_reference_evidence(
                    {
                        "source_type": "repository_entrypoint",
                        "entrypoint": "node src/server.js",
                        "evidence": "apps/api/package.json",
                    },
                    repo_root=root,
                )

    def test_repository_import_keeps_resolved_regular_file_across_rename_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            package = root / "apps/api"
            (package / "src").mkdir(parents=True)
            (package / "package.json").write_text("{}", encoding="utf-8")
            (package / "src/server.js").write_text(
                "import './helper.js';\n", encoding="utf-8"
            )
            helper = package / "src/helper.js"
            original = b"const token = process.env.HELD_IMPORT_TOKEN;\n"
            helper.write_bytes(original)
            expected_blob = subprocess.run(
                ("git", "hash-object", "--stdin"),
                input=original,
                capture_output=True,
                check=True,
            ).stdout.decode().strip()
            original_resolver = self.collector._resolve_import
            replaced = False

            def replace_after_resolve(importer, specifier, trusted_root):
                nonlocal replaced
                resolved = original_resolver(importer, specifier, trusted_root)
                if not replaced:
                    os.replace(helper, helper.with_suffix(".js.resolved"))
                    helper.write_text(
                        "const replacement = process.env.REPLACEMENT_IMPORT_TOKEN;\n",
                        encoding="utf-8",
                    )
                    replaced = True
                return resolved

            with mock.patch.object(
                self.collector, "_resolve_import", side_effect=replace_after_resolve
            ):
                records = self.collector.collect_repository_reference_evidence(
                    {
                        "source_type": "repository_entrypoint",
                        "entrypoint": "node src/server.js",
                        "evidence": "apps/api/package.json",
                    },
                    repo_root=root,
                )
        self.assertEqual({"HELD_IMPORT_TOKEN"}, {record["reference_name"] for record in records})
        self.assertEqual({expected_blob}, {record["blob_oid"] for record in records})

    def _write_typescript_parser_fixture(
        self,
        root: Path,
        *,
        version: str = TYPESCRIPT_VERSION,
        integrity: str = TYPESCRIPT_INTEGRITY,
        parser_bytes: bytes | None = b"fixture parser",
    ) -> Path:
        tool = root / "tools/credential-ast-parser"
        module_root = tool / "node_modules/typescript"
        (module_root / "lib").mkdir(parents=True)
        package = {
            "name": "@anicca/credential-ast-parser",
            "version": "1.0.0",
            "private": True,
            "dependencies": {"typescript": version},
        }
        lock = {
            "name": package["name"], "version": package["version"],
            "lockfileVersion": 3, "requires": True,
            "packages": {
                "": {
                    "name": package["name"], "version": package["version"],
                    "dependencies": {"typescript": version},
                },
                "node_modules/typescript": {
                    "version": version,
                    "resolved": f"https://registry.npmjs.org/typescript/-/typescript-{version}.tgz",
                    "integrity": integrity,
                },
            },
        }
        (tool / "package.json").write_text(json.dumps(package), encoding="utf-8")
        (tool / "package-lock.json").write_text(json.dumps(lock), encoding="utf-8")
        (module_root / "package.json").write_text(
            json.dumps({"name": "typescript", "version": version}), encoding="utf-8"
        )
        module = module_root / "lib/typescript.js"
        if parser_bytes is not None:
            module.write_bytes(parser_bytes)
        return module

    def test_typescript_parser_dependency_is_pinned_inside_current_worktree(self) -> None:
        candidate = self.collector._typescript_module_path(repo_root=REPO)
        module = candidate.path
        self.assertEqual(
            (REPO / "tools/credential-ast-parser/node_modules/typescript/lib/typescript.js").resolve(),
            module,
        )
        self.assertTrue(module.is_relative_to(REPO.resolve()))
        package = read_json(REPO / "tools/credential-ast-parser/package.json")
        lock = read_json(REPO / "tools/credential-ast-parser/package-lock.json")
        self.assertEqual(TYPESCRIPT_VERSION, package["dependencies"]["typescript"])
        self.assertEqual(
            TYPESCRIPT_INTEGRITY,
            lock["packages"]["node_modules/typescript"]["integrity"],
        )

    def test_typescript_parser_rejects_outside_worktree_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            module = self._write_typescript_parser_fixture(root, parser_bytes=None)
            outside = root.parent / (root.name + "-outside-typescript.js")
            outside.write_bytes(b"outside parser")
            try:
                module.symlink_to(outside)
                with self.assertRaisesRegex(RuntimeError, "inside current worktree"):
                    self.collector._typescript_module_path(repo_root=root)
            finally:
                outside.unlink(missing_ok=True)

    def test_typescript_parser_lstats_every_component_before_read(self) -> None:
        actual_parser = (
            REPO / "tools/credential-ast-parser/node_modules/typescript/lib/typescript.js"
        ).read_bytes()
        relative_targets = (
            Path("tools/credential-ast-parser"),
            Path("tools/credential-ast-parser/package.json"),
            Path("tools/credential-ast-parser/package-lock.json"),
            Path("tools/credential-ast-parser/node_modules/typescript/package.json"),
            Path("tools/credential-ast-parser/node_modules/typescript/lib/typescript.js"),
        )
        for relative in relative_targets:
            with self.subTest(component=relative), tempfile.TemporaryDirectory() as temp_dir:
                base = Path(temp_dir)
                root = base / "root"
                root.mkdir()
                self._write_typescript_parser_fixture(root, parser_bytes=actual_parser)
                target = root / relative
                outside = base / "outside"
                outside.mkdir()
                replacement = outside / target.name
                if target.is_dir():
                    shutil.move(str(target), str(replacement))
                    target.symlink_to(replacement, target_is_directory=True)
                else:
                    target.unlink()
                    replacement.write_text("{}", encoding="utf-8")
                    target.symlink_to(replacement)
                with self.assertRaisesRegex(RuntimeError, "pre-read lstat"):
                    self.collector._typescript_module_path(repo_root=root)

    def test_typescript_parser_rejects_wrong_manifest_version(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_typescript_parser_fixture(root, version="5.5.3")
            with self.assertRaisesRegex(RuntimeError, "exact version"):
                self.collector._typescript_module_path(repo_root=root)

    def test_typescript_parser_rejects_manifest_lock_root_mismatch(self) -> None:
        installed_parser = (
            REPO / "tools/credential-ast-parser/node_modules/typescript/lib/typescript.js"
        ).read_bytes()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_typescript_parser_fixture(root, parser_bytes=installed_parser)
            package_path = root / "tools/credential-ast-parser/package.json"
            package = read_json(package_path)
            package["name"] = "@anicca/wrong-parser"
            package_path.write_text(json.dumps(package), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "manifest/lock mismatch"):
                self.collector._typescript_module_path(repo_root=root)

    def test_typescript_parser_rejects_wrong_lock_integrity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_typescript_parser_fixture(root, integrity="sha512-invalid")
            with self.assertRaisesRegex(RuntimeError, "lock integrity"):
                self.collector._typescript_module_path(repo_root=root)

    def test_typescript_parser_rejects_wrong_artifact_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_typescript_parser_fixture(root)
            with self.assertRaisesRegex(RuntimeError, "artifact digest"):
                self.collector._open_typescript_module(repo_root=root)

    def test_typescript_parser_missing_dependency_fails_closed_without_install(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_typescript_parser_fixture(root, parser_bytes=None)
            with mock.patch("subprocess.run") as run:
                with self.assertRaisesRegex(RuntimeError, "parser unavailable"):
                    self.collector._typescript_module_path(repo_root=root)
            run.assert_not_called()

    def test_typescript_parser_bootstrap_and_integrity_contract_is_documented(self) -> None:
        documentation = (REPO / "docs/reference/cloud-agent-credential-inventory.md").read_text(
            encoding="utf-8"
        )
        command = (
            "npm ci --ignore-scripts --no-audit --no-fund "
            "--prefix tools/credential-ast-parser"
        )
        self.assertIn(command, documentation)
        self.assertIn("f7ff3e27aafe5dcc82d0307575e9a7dc5b053b141da123bec81c858537765b56", documentation)
        source = COLLECTOR.read_text(encoding="utf-8")
        self.assertNotIn("REPO.parent.parent", source)
        self.assertNotIn("apps/landing/node_modules", source)

    def test_typescript_parser_package_and_lock_are_git_tracking_candidates(self) -> None:
        for relative in (
            "tools/credential-ast-parser/package.json",
            "tools/credential-ast-parser/package-lock.json",
        ):
            with self.subTest(path=relative):
                tracked = subprocess.run(
                    ["git", "ls-files", "--error-unmatch", relative],
                    cwd=REPO, text=True, capture_output=True, check=False,
                )
                ignored = subprocess.run(
                    ["git", "check-ignore", "-q", relative],
                    cwd=REPO, text=True, capture_output=True, check=False,
                )
                self.assertEqual(0, tracked.returncode)
                self.assertNotEqual(0, ignored.returncode)

    def test_ast_projection_uses_verified_parser_and_projector_fds_across_path_replacement(self) -> None:
        actual_parser = (
            REPO / "tools/credential-ast-parser/node_modules/typescript/lib/typescript.js"
        ).read_bytes()
        actual_projector = (REPO / "scripts/project-js-env-references.js").read_bytes()
        real_run = subprocess.run
        for replaced_name in ("parser", "projector"):
            with self.subTest(replaced_name=replaced_name), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                parser = self._write_typescript_parser_fixture(root, parser_bytes=actual_parser)
                projector = root / "scripts/project-js-env-references.js"
                projector.parent.mkdir(parents=True)
                projector.write_bytes(actual_projector)
                source = root / "fixture.js"
                source.write_text(
                    "const token = process.env.VERIFIED_FD_TOKEN;\n", encoding="utf-8"
                )
                replacement_target = parser if replaced_name == "parser" else projector

                def replace_then_run(*args, **kwargs):
                    original = replacement_target.with_suffix(replacement_target.suffix + ".original")
                    os.replace(replacement_target, original)
                    replacement_target.write_text("throw new Error('replacement opened');\n", encoding="utf-8")
                    return real_run(*args, **kwargs)

                with mock.patch.object(self.collector, "REPO", root), mock.patch.object(
                    self.collector, "_typescript_module_path", return_value=parser
                ), mock.patch.object(
                    self.collector.subprocess, "run", side_effect=replace_then_run
                ):
                    projection = self.collector._project_js_ts_source(source)
                self.assertEqual(
                    [{"reference_name": "VERIFIED_FD_TOKEN", "line": 1}],
                    projection["references"],
                )

    def test_typescript_parser_source_has_no_pathname_read_before_kernel_fd_chain(self) -> None:
        parser = (
            REPO / "tools/credential-ast-parser/node_modules/typescript/lib/typescript.js"
        )
        real_read_bytes = Path.read_bytes
        real_open = os.open
        parser_path_reads: list[Path] = []
        opens: list[tuple[str, int | None]] = []

        def observe_read_bytes(path: Path) -> bytes:
            if Path(path) == parser:
                parser_path_reads.append(Path(path))
            return real_read_bytes(path)

        def observe_open(path, flags, mode=0o777, *, dir_fd=None):
            opens.append((os.fspath(path), dir_fd))
            return real_open(path, flags, mode, dir_fd=dir_fd)

        with tempfile.TemporaryDirectory(dir=REPO) as temp_dir:
            source = Path(temp_dir) / "fixture.js"
            source.write_text(
                "const token = process.env.PARSER_SINGLE_FD_TOKEN;\n", encoding="utf-8"
            )
            with mock.patch.object(
                Path, "read_bytes", new=observe_read_bytes
            ), mock.patch.object(
                self.collector.os, "open", side_effect=observe_open
            ):
                projection = self.collector._project_js_ts_source(source)
        self.assertEqual(
            [{"reference_name": "PARSER_SINGLE_FD_TOKEN", "line": 1}],
            projection["references"],
        )
        self.assertEqual([], parser_path_reads, "parser source was read by pathname")
        self.assertEqual((os.path.sep, None), opens[0])

    def test_typescript_parser_identical_inode_replacement_after_metadata_fails_closed(self) -> None:
        actual_parser = (
            REPO / "tools/credential-ast-parser/node_modules/typescript/lib/typescript.js"
        ).read_bytes()
        actual_projector = (REPO / "scripts/project-js-env-references.js").read_bytes()
        with tempfile.TemporaryDirectory(dir=REPO) as temp_dir:
            root = Path(temp_dir)
            parser = self._write_typescript_parser_fixture(root, parser_bytes=actual_parser)
            projector = root / "scripts/project-js-env-references.js"
            projector.parent.mkdir(parents=True)
            projector.write_bytes(actual_projector)
            source = root / "fixture.js"
            source.write_text(
                "const token = process.env.PARSER_REPLACEMENT_TOKEN;\n", encoding="utf-8"
            )
            original_locator = self.collector._typescript_module_path
            replaced = False

            def replace_after_metadata(*, repo_root):
                nonlocal replaced
                located = original_locator(repo_root=repo_root)
                module = located.path if hasattr(located, "path") else located
                if not replaced:
                    os.replace(module, module.with_suffix(".js.metadata"))
                    module.write_bytes(actual_parser)
                    replaced = True
                return located

            with mock.patch.object(
                self.collector, "REPO", root
            ), mock.patch.object(
                self.collector, "_typescript_module_path", side_effect=replace_after_metadata
            ), self.assertRaisesRegex(RuntimeError, "replacement detected"):
                self.collector._project_js_ts_source(source)

    def test_repository_blob_identity_comes_from_projected_source_fd_across_replacement(self) -> None:
        actual_parser = (
            REPO / "tools/credential-ast-parser/node_modules/typescript/lib/typescript.js"
        ).read_bytes()
        actual_projector = (REPO / "scripts/project-js-env-references.js").read_bytes()
        real_run = subprocess.run
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            package = root / "apps/api"
            (package / "src").mkdir(parents=True)
            (package / "package.json").write_text("{}", encoding="utf-8")
            source = package / "src/server.js"
            original = b"const token = process.env.SOURCE_FD_IDENTITY_TOKEN;\n"
            source.write_bytes(original)
            expected_blob = real_run(
                ("git", "hash-object", "--stdin"),
                input=original,
                capture_output=True,
                check=True,
            ).stdout.decode().strip()
            parser = self._write_typescript_parser_fixture(root, parser_bytes=actual_parser)
            projector = root / "scripts/project-js-env-references.js"
            projector.parent.mkdir(parents=True)
            projector.write_bytes(actual_projector)
            replaced = False

            def replace_source_after_projection(*args, **kwargs):
                nonlocal replaced
                completed = real_run(*args, **kwargs)
                argv = args[0]
                if not replaced and argv[0] == "node":
                    held = source.with_suffix(".js.projected")
                    os.replace(source, held)
                    source.write_text("const replacement = true;\n", encoding="utf-8")
                    replaced = True
                return completed

            with mock.patch.object(self.collector, "REPO", root), mock.patch.object(
                self.collector, "_typescript_module_path", return_value=parser
            ), mock.patch.object(
                self.collector.subprocess, "run", side_effect=replace_source_after_projection
            ):
                records = self.collector.collect_repository_reference_evidence(
                    {
                        "source_type": "repository_entrypoint",
                        "entrypoint": "node src/server.js",
                        "evidence": "apps/api/package.json",
                    },
                    repo_root=root,
                )
        self.assertEqual(1, len(records))
        self.assertEqual(expected_blob, records[0]["blob_oid"])

    def test_verified_fd_rejects_ancestor_symlinks_for_parser_projector_and_source(self) -> None:
        for label in ("TypeScript parser", "JS/TS AST projector", "JS/TS source"):
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temp_dir:
                base = Path(temp_dir)
                root = base / "repo"
                outside = base / "outside"
                root.mkdir()
                outside.mkdir()
                (outside / "fixture.js").write_text("const safe = true;\n", encoding="utf-8")
                (root / "linked").symlink_to(outside, target_is_directory=True)
                with mock.patch.object(self.collector, "REPO", root), self.assertRaisesRegex(
                    RuntimeError, "ancestor"
                ):
                    descriptor = self.collector._open_lstat_bound_fd(
                        root / "linked/fixture.js", label
                    )
                    os.close(descriptor)

    def test_verified_fd_rejects_symlink_above_repository_root(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO) as temp_dir:
            base = Path(temp_dir)
            actual_parent = base / "actual-parent"
            actual_root = actual_parent / "repo"
            actual_root.mkdir(parents=True)
            (actual_root / "fixture.js").write_text("const safe = true;\n", encoding="utf-8")
            linked_parent = base / "linked-parent"
            linked_parent.symlink_to(actual_parent, target_is_directory=True)
            linked_root = linked_parent / "repo"
            with mock.patch.object(self.collector, "REPO", linked_root), self.assertRaisesRegex(
                RuntimeError, "trust anchor"
            ):
                descriptor = self.collector._open_lstat_bound_fd(
                    linked_root / "fixture.js", "JS/TS source"
                )
                os.close(descriptor)

    def test_verified_fd_keeps_root_parent_across_replacement(self) -> None:
        real_open = os.open
        with tempfile.TemporaryDirectory(dir=REPO) as temp_dir:
            base = Path(temp_dir)
            container = base / "trusted-container"
            root = container / "repo"
            outside = base / "outside"
            outside_root = outside / "repo"
            root.mkdir(parents=True)
            outside_root.mkdir(parents=True)
            target = root / "fixture.js"
            target.write_bytes(b"trusted root source")
            (outside_root / "fixture.js").write_bytes(b"replacement root source")
            held = base / "trusted-container-held"
            swapped = False

            def replace_root_parent(path, flags, mode=0o777, *, dir_fd=None):
                nonlocal swapped
                if dir_fd is None and Path(path) == root and not swapped:
                    os.replace(container, held)
                    container.symlink_to(outside, target_is_directory=True)
                    swapped = True
                descriptor = real_open(path, flags, mode, dir_fd=dir_fd)
                if dir_fd is not None and path == container.name and not swapped:
                    os.replace(container, held)
                    container.symlink_to(outside, target_is_directory=True)
                    swapped = True
                return descriptor

            with mock.patch.object(self.collector, "REPO", root), mock.patch.object(
                self.collector.os, "open", side_effect=replace_root_parent
            ):
                descriptor = self.collector._open_lstat_bound_fd(target, "JS/TS source")
                try:
                    self.assertEqual(b"trusted root source", os.read(descriptor, 1024))
                finally:
                    os.close(descriptor)

    def test_verified_fd_rejects_symlink_above_configured_trust_anchor(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO) as temp_dir:
            base = Path(temp_dir)
            actual_upper = base / "actual-upper"
            actual_anchor = actual_upper / "anchor"
            actual_root = actual_anchor / "repo"
            actual_root.mkdir(parents=True)
            (actual_root / "fixture.js").write_bytes(b"trusted source")
            linked_upper = base / "linked-upper"
            linked_upper.symlink_to(actual_upper, target_is_directory=True)
            linked_anchor = linked_upper / "anchor"
            linked_root = linked_anchor / "repo"
            with mock.patch.object(
                self.collector, "REPOSITORY_TRUST_ANCHOR", linked_anchor, create=True
            ), mock.patch.object(
                self.collector, "REPO", linked_root
            ), self.assertRaisesRegex(RuntimeError, "trust anchor"):
                descriptor = self.collector._open_lstat_bound_fd(
                    linked_root / "fixture.js", "JS/TS source"
                )
                os.close(descriptor)

    def test_verified_fd_keeps_anchor_upper_ancestor_across_replacement(self) -> None:
        real_open = os.open
        with tempfile.TemporaryDirectory(dir=REPO) as temp_dir:
            base = Path(temp_dir)
            upper = base / "iteration16-upper"
            anchor = upper / "anchor"
            root = anchor / "repo"
            outside_upper = base / "outside-upper"
            outside_root = outside_upper / "anchor/repo"
            root.mkdir(parents=True)
            outside_root.mkdir(parents=True)
            target = root / "fixture.js"
            target.write_bytes(b"trusted source")
            (outside_root / "fixture.js").write_bytes(b"replacement source")
            held = base / "iteration16-upper-held"
            swapped = False

            def replace_upper(path, flags, mode=0o777, *, dir_fd=None):
                nonlocal swapped
                if dir_fd is None and Path(path) == anchor and not swapped:
                    os.replace(upper, held)
                    upper.symlink_to(outside_upper, target_is_directory=True)
                    swapped = True
                descriptor = real_open(path, flags, mode, dir_fd=dir_fd)
                if dir_fd is not None and path == upper.name and not swapped:
                    os.replace(upper, held)
                    upper.symlink_to(outside_upper, target_is_directory=True)
                    swapped = True
                return descriptor

            with mock.patch.object(
                self.collector, "REPOSITORY_TRUST_ANCHOR", anchor, create=True
            ), mock.patch.object(
                self.collector, "REPO", root
            ), mock.patch.object(
                self.collector.os, "open", side_effect=replace_upper
            ):
                descriptor = self.collector._open_lstat_bound_fd(
                    target, "JS/TS source"
                )
                try:
                    self.assertEqual(b"trusted source", os.read(descriptor, 1024))
                finally:
                    os.close(descriptor)

    def test_production_repository_fd_chain_starts_at_kernel_root(self) -> None:
        real_open = os.open
        calls: list[tuple[str, int | None]] = []

        def observe_open(path, flags, mode=0o777, *, dir_fd=None):
            calls.append((os.fspath(path), dir_fd))
            return real_open(path, flags, mode, dir_fd=dir_fd)

        with mock.patch.object(self.collector.os, "open", side_effect=observe_open):
            descriptor = self.collector._open_lstat_bound_fd(
                REPO / "scripts/project-js-env-references.js", "JS/TS AST projector"
            )
            os.close(descriptor)
        self.assertEqual((os.path.sep, None), calls[0])
        self.assertFalse(
            [path for path, dir_fd in calls[1:] if dir_fd is None and os.path.isabs(path)],
            "production repository entered an absolute-path compatibility fallback",
        )

    def test_verified_fd_keeps_opened_ancestor_across_directory_replacement(self) -> None:
        real_open = os.open
        for label in ("TypeScript parser", "JS/TS AST projector", "JS/TS source"):
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temp_dir:
                base = Path(temp_dir)
                root = base / "repo"
                trusted = root / "trusted"
                outside = base / "outside"
                trusted.mkdir(parents=True)
                outside.mkdir()
                target = trusted / "fixture.js"
                target.write_bytes(b"trusted source")
                (outside / "fixture.js").write_bytes(b"replacement source")
                held = root / "trusted-held"
                swapped = False

                def racing_open(path, flags, mode=0o777, *, dir_fd=None):
                    nonlocal swapped
                    if dir_fd is None and Path(path) == target and not swapped:
                        os.replace(trusted, held)
                        trusted.symlink_to(outside, target_is_directory=True)
                        swapped = True
                    descriptor = real_open(path, flags, mode, dir_fd=dir_fd)
                    if dir_fd is not None and path == "trusted" and not swapped:
                        os.replace(trusted, held)
                        trusted.symlink_to(outside, target_is_directory=True)
                        swapped = True
                    return descriptor

                with mock.patch.object(self.collector, "REPO", root), mock.patch.object(
                    self.collector.os, "open", side_effect=racing_open
                ):
                    try:
                        descriptor = self.collector._open_lstat_bound_fd(target, label)
                    except RuntimeError as error:
                        self.fail(f"verified ancestor descriptor was not retained: {type(error).__name__}")
                    try:
                        self.assertEqual(b"trusted source", os.read(descriptor, 1024))
                    finally:
                        os.close(descriptor)

    def test_repository_reference_evidence_fails_closed_when_start_source_is_unavailable(self) -> None:
        parent = {
            "inventory_id": "package:fixture/package.json#start",
            "source_type": "repository_entrypoint", "entrypoint": "next start",
            "evidence": "fixture/package.json",
        }
        with tempfile.TemporaryDirectory() as temp_dir, self.assertRaisesRegex(
            RuntimeError, "start entrypoint source unavailable"
        ):
            self.collector.collect_repository_reference_evidence(
                parent, repo_root=Path(temp_dir)
            )

    def test_collect_wires_repository_reference_evidence_into_parent_observation(self) -> None:
        self.assertIn("reference_scanner", inspect.signature(self.collector.collect).parameters)
        with tempfile.TemporaryDirectory() as temp_dir:
            parent_path = Path(temp_dir) / "parents.tsv"
            parent_path.write_text(
                "inventory_id\tsource_type\tentrypoint\tstate\tevidence\n"
                "package:fixture/package.json#start\trepository_entrypoint\tnode src/server.js\t"
                "declared_in_repository\tfixture/package.json\n",
                encoding="utf-8",
            )
            evidence = [{
                "reference_name": "FIXTURE_API_KEY", "path": "fixture/src/server.js",
                "blob_oid": "a" * 40, "line": 3,
                "symbol_locator": "path:fixture/src/server.js;blob:" + "a" * 40 + ";line:3;symbol:env.FIXTURE_API_KEY",
            }]

            def unavailable(argv):
                raise subprocess.CalledProcessError(1, argv)

            result = self.collector.collect(
                parent_path, runner=unavailable,
                cron_projection={"schema_version": 1, "jobs": []},
                reference_scanner=lambda parent: evidence,
            )
        self.assertEqual(
            evidence,
            result["parents"]["package:fixture/package.json#start"]["reference_evidence"],
        )

    def test_launchd_argv_projection_keeps_only_retrievable_nonsecret_components(self) -> None:
        projector = getattr(self.collector, "project_launchd_argv_paths", None)
        self.assertIsNotNone(projector, "launchd argv safe projector is missing")
        raw_argv = [
            "/bin/zsh", "~/.local/bin/openclaw-with-env", "--config",
            "~/Library/Application Support/OpenClaw/config.json",
            "source ~/.env && exec ~/.local/bin/actual-wrapper",
            "~/Library/Logs/agent.log 2>&1",
            "source ~/.env && echo PROMPT_SENTINEL_MUST_NOT_CROSS_BOUNDARY",
        ]
        self.assertEqual(
            [
                "/bin/zsh",
                "~/.local/bin/openclaw-with-env",
                "~/Library/Application Support/OpenClaw/config.json",
                "~/.local/bin/actual-wrapper",
                "~/Library/Logs/agent.log",
            ],
            projector(raw_argv),
        )

    def test_launchd_env_like_suffixes_never_reach_blob_hasher(self) -> None:
        calls = []

        def spy_runner(argv):
            calls.append(argv)
            return subprocess.CompletedProcess(argv, 0, stdout="a" * 40 + "\n", stderr="")

        for name in ("service.env", "worker.env.local", ".env.production", ".env"):
            with self.subTest(name=name):
                self.assertIsNone(self.collector._blob_oid(Path("/tmp") / name, spy_runner))
        self.assertEqual([], calls)

    def test_launchd_homebrew_components_have_explicit_portable_locator(self) -> None:
        self.assertEqual(
            "system:/opt/homebrew/opt/ollama/bin/ollama",
            self.collector._portable_path(Path("/opt/homebrew/opt/ollama/bin/ollama")),
        )
        self.assertNotIn(
            "/dev/null", self.collector.project_launchd_argv_paths(["/bin/bash", "/dev/null"])
        )

    def test_launchd_config_revision_hashes_only_fixed_safe_projection(self) -> None:
        parent = {
            "inventory_id": "launchd:fixture", "source_type": "launchd",
            "entrypoint": "/bin/zsh fixture.sh", "evidence": "/tmp/fixture.plist",
        }
        safe_projection = {
            "schema_version": 2,
            "program": "/bin/zsh",
            "working_directory": "/tmp",
            "argument_count": 3,
            "paths": ["/bin/zsh", "/tmp/fixture.sh"],
        }

        hash_calls = []

        def forbidden_hash_runner(argv):
            hash_calls.append(argv)
            return subprocess.CompletedProcess(argv, 0, stdout="a" * 40 + "\n", stderr="")

        with mock.patch.object(
            self.collector, "run_launchd_metadata_projection", return_value=safe_projection
        ):
            record = self.collector.config_revision_record(parent, forbidden_hash_runner)
        self.assertRegex(record["digest"], self.generator.DIGEST_VALUE)
        self.assertIn("launchd-safe-config:", record["evidence_locator"])
        self.assertNotIn("blob:", record["evidence_locator"])
        self.assertEqual([], hash_calls)

        with mock.patch.object(
            self.collector, "run_launchd_metadata_projection", side_effect=RuntimeError("invalid plist")
        ):
            self.assertEqual(
                "unverified", self.collector.config_revision_digest(parent, forbidden_hash_runner)
            )
        self.assertEqual([], hash_calls)

    def test_launchd_fixed_projection_excludes_environment_variable_values(self) -> None:
        sentinel = "ENV_VALUE_SENTINEL_MUST_NOT_CROSS_BOUNDARY"
        with tempfile.TemporaryDirectory() as temp_dir:
            plist = Path(temp_dir) / "fixture.plist"
            plist.write_text(
                f'''<?xml version="1.0" encoding="UTF-8"?>
<plist version="1.0"><dict>
<key>Program</key><string>/bin/zsh</string>
<key>ProgramArguments</key><array><string>/bin/zsh</string><string>-c</string><string>fixture.sh</string></array>
<key>WorkingDirectory</key><string>{temp_dir}</string>
<key>EnvironmentVariables</key><dict><key>FIXTURE_TOKEN</key><string>{sentinel}</string></dict>
</dict></plist>''',
                encoding="utf-8",
            )
            projected = self.collector.run_launchd_metadata_projection(plist)
        self.assertEqual(
            {"schema_version", "program", "working_directory", "argument_count", "paths"},
            set(projected),
        )
        self.assertNotIn(sentinel, json.dumps(projected))

    def test_launchd_projection_resolves_relative_wrapper_against_working_directory(self) -> None:
        projector = getattr(self.collector, "run_launchd_metadata_projection", None)
        self.assertIsNotNone(projector, "launchd metadata fixed projection is missing")
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "scripts").mkdir()
            (root / "scripts/wrapper.sh").write_text("#!/bin/zsh\n", encoding="utf-8")
            plist = root / "fixture.plist"
            plist.write_text(
                f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">
<plist version=\"1.0\"><dict><key>WorkingDirectory</key><string>{root}</string>
<key>ProgramArguments</key><array><string>/bin/zsh</string><string>scripts/wrapper.sh</string></array>
</dict></plist>""",
                encoding="utf-8",
            )
            projected = projector(plist)
        self.assertEqual(str(root), projected["working_directory"])
        self.assertEqual(["/bin/zsh", "scripts/wrapper.sh"], projected["paths"])

    def test_launchd_plist_projection_never_returns_prompt_payload_or_secret_env_path(self) -> None:
        projector = getattr(self.collector, "run_launchd_argv_projection", None)
        self.assertIsNotNone(projector, "launchd plist fixed projection is missing")
        with tempfile.TemporaryDirectory() as temp_dir:
            plist = Path(temp_dir) / "fixture.plist"
            plist.write_text(
                """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">
<plist version=\"1.0\"><dict><key>ProgramArguments</key><array>
<string>/bin/zsh</string><string>-c</string>
<string>source ~/.env &amp;&amp; exec ~/.local/bin/safe-wrapper PROMPT_SENTINEL_MUST_NOT_CROSS_BOUNDARY</string>
</array></dict></plist>""",
                encoding="utf-8",
            )
            projected = projector(plist)
        self.assertEqual(["/bin/zsh", "~/.local/bin/safe-wrapper"], projected)
        self.assertNotIn("PROMPT_SENTINEL_MUST_NOT_CROSS_BOUNDARY", json.dumps(projected))

    def test_launchd_source_revision_binds_every_projected_wrapper_and_config_blob(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            wrapper = root / "env-wrapper"
            config = root / "safe-config.json"
            wrapper.write_text("#!/bin/zsh\nexec true\n", encoding="utf-8")
            config.write_text("{}\n", encoding="utf-8")
            plist = root / "fixture.plist"
            plist.write_text(
                f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">
<plist version=\"1.0\"><dict><key>ProgramArguments</key><array>
<string>/bin/zsh</string><string>{wrapper}</string><string>--config</string><string>{config}</string>
<string>{root / '.env'}</string>
</array></dict></plist>""",
                encoding="utf-8",
            )
            parent = {
                "inventory_id": "launchd:fixture", "source_type": "launchd",
                "entrypoint": "/bin/zsh &lt;shell-command-redacted&gt;",
                "evidence": str(plist), "state": "loaded",
            }
            record = self.collector.source_revision_record(parent)
        self.assertNotEqual("unverified", record["digest"])
        self.assertIn("launchd-components:", record["evidence_locator"])
        self.assertIn("path:system:/bin/zsh;blob:", record["evidence_locator"])
        self.assertIn("external:env-wrapper;blob:", record["evidence_locator"])
        self.assertIn("external:safe-config.json;blob:", record["evidence_locator"])
        self.assertNotIn(".env", record["evidence_locator"])

    def test_secrets_audit_codes_are_exact_primary_enum_and_unknown_is_rejected(self) -> None:
        codes = {"PLAINTEXT_FOUND", "REF_UNRESOLVED", "REF_SHADOWED", "LEGACY_RESIDUE"}
        projected = self.collector.project_secrets_audit({
            "status": "findings",
            "findings": [{"code": code, "provider": "deepseek"} for code in sorted(codes)],
        })
        self.assertEqual(
            {f"{code}:deepseek" for code in codes},
            set(projected["finding_counts"]),
        )
        with self.assertRaisesRegex(ValueError, "unknown secrets audit finding code"):
            self.collector.project_secrets_audit({
                "status": "findings", "findings": [{"code": "FUTURE_UNKNOWN"}],
            })

    def test_edge_revision_alignment_rejects_one_mutated_digest_with_specific_error(self) -> None:
        observation = {
            "parents": {
                "loop:a": {
                    "parent_metadata_digest": "sha256:" + ":".join(["1" * 8] * 8),
                    "source_revision_digest": "sha256:" + ":".join(["2" * 8] * 8),
                    "config_revision_digest": "sha256:" + ":".join(["3" * 8] * 8),
                }
            }
        }
        edge = {
            "loop_dependency_edge_id": "loop:a|dependency:none",
            "inventory_id": "loop:a",
            "loop_state": "enabled",
            "dependency_status": "none_observed",
            "credential_object_id": "none",
            "consumer_locator": "loop:a",
            "permission_scope": "none",
            "dependency_basis": "entrypoint_reference_review",
            "evidence_locator": "repo:path",
            **observation["parents"]["loop:a"],
        }
        mutated = {**edge, "config_revision_digest": "sha256:" + ":".join(["4" * 8] * 8)}
        with self.assertRaisesRegex(SystemExit, "loop:a.*config revision digest mismatch"):
            self.generator.validate_edge_revision_alignment([mutated], observation)

    def test_edge_validator_mutates_only_loop_state_and_reports_specific_error(self) -> None:
        parents = read_tsv(PARENT)
        observations = read_json(OBSERVATIONS)
        objects = read_json(OBJECTS)
        edge = dict(read_tsv(TRACKED)[0])
        mutated = {**edge, "loop_state": "mystery"}
        with self.assertRaisesRegex(SystemExit, "invalid loop_state"):
            self.generator.validate_loop_dependency_edges(
                [mutated], {edge["inventory_id"]},
                {"parents": {edge["inventory_id"]: observations["parents"][edge["inventory_id"]]}},
                objects,
            )

    def test_edge_validator_uses_valid_base_and_reports_each_single_field_mutation(self) -> None:
        observations = read_json(OBSERVATIONS)
        objects = read_json(OBJECTS)
        edge = dict(read_tsv(TRACKED)[0])
        parent_id = edge["inventory_id"]
        base_observations = {
            "parents": {parent_id: observations["parents"][parent_id]}
        }
        self.generator.validate_loop_dependency_edges(
            [edge], {parent_id}, base_observations, objects
        )
        cases = (
            ("dependency_status", "mystery", "invalid dependency_status"),
            ("permission_scope", "api:access", "imprecise permission scope"),
            ("source_revision_digest", "not-a-digest", "invalid source_revision_digest"),
            ("evidence_locator", "/Users/fixture/private", "raw home path"),
        )
        for field, value, message in cases:
            with self.subTest(field=field), self.assertRaisesRegex(SystemExit, message):
                self.generator.validate_loop_dependency_edges(
                    [{**edge, field: value}], {parent_id},
                    base_observations, objects,
                )
        with self.assertRaisesRegex(SystemExit, "invalid edge schema"):
            self.generator.validate_loop_dependency_edges(
                [{**edge, "extra": "field"}], {parent_id},
                base_observations, objects,
            )
        with self.assertRaisesRegex(SystemExit, "duplicate loop_dependency_edge_id"):
            self.generator.validate_loop_dependency_edges(
                [edge, dict(edge)], {parent_id},
                base_observations, objects,
            )
        with self.assertRaisesRegex(SystemExit, "parent coverage mismatch"):
            self.generator.validate_loop_dependency_edges(
                [edge], {parent_id, "missing-parent"},
                base_observations, objects,
            )

    def test_safe_projectors_reject_wrong_shapes_and_drop_invalid_entries(self) -> None:
        for projector in (
            self.collector.project_agents_list,
            self.collector.project_auth_list,
            self.collector.project_models_status,
            self.collector.project_secrets_audit,
        ):
            with self.subTest(projector=projector.__name__), self.assertRaises(ValueError):
                projector(None)
        agents = self.collector.project_agents_list(
            [None, {"id": "../bad", "model": "x/y"}, {"id": "good", "model": "missing-slash"}]
        )
        self.assertEqual({}, agents)
        profiles = self.collector.project_auth_list(
            {"profiles": [None, {"id": 1, "provider": "x", "type": "token"}, {"id": "a", "provider": "../x", "type": "token"}, {"id": "a", "provider": "x", "type": "password"}]}
        )
        self.assertEqual([], profiles)

    def test_railway_revision_record_uses_origin_branch_portable_oids(self) -> None:
        values = {
            ("git", "rev-parse", "origin/main"): "a" * 40,
            ("git", "rev-parse", "origin/main^{tree}"): "b" * 40,
            ("git", "rev-parse", "origin/main:apps/life-call/package.json"): "c" * 40,
        }
        def fake_runner(argv):
            return subprocess.CompletedProcess(argv, 0, stdout=values[argv] + "\n", stderr="")
        parent = {
            "source_type": "railway_entrypoint",
            "evidence": "https://github.com/example/repo/blob/main/apps/life-call/package.json",
        }
        record = self.collector.source_revision_record(parent, fake_runner)
        self.assertNotEqual("unverified", record["digest"])
        self.assertIn("git:origin/main", record["evidence_locator"])

    def test_credential_object_validator_reports_precise_single_field_failures(self) -> None:
        artifact = read_json(OBJECTS)
        self.generator.validate_credential_objects(artifact)
        object_id, record = next(iter(artifact["credential_objects"].items()))
        cases = (
            ({**artifact, "schema_version": 99}, "invalid schema_version"),
            ({**artifact, "credential_objects": []}, "invalid object maps"),
            ({**artifact, "credential_objects": {"bad-id": record}}, "invalid credential object"),
            ({**artifact, "credential_objects": {object_id: {**record, "provider": "unverified"}}}, "invalid credential provider"),
            ({**artifact, "credential_objects": {object_id: {**record, "policy_status": "mystery"}}}, "invalid credential policy status"),
        )
        for mutated, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(SystemExit, message):
                self.generator.validate_credential_objects(mutated)

    def test_credential_object_validator_enforces_oauth_and_plaintext_policy(self) -> None:
        artifact = read_json(OBJECTS)
        oauth_id, oauth = next(
            (object_id, record)
            for object_id, record in artifact["credential_objects"].items()
            if record["credential_type"] == "oauth"
            and record["provider"] in self.generator.SUBSCRIPTION_OAUTH_PROVIDERS
        )
        plaintext_id, plaintext = next(
            (object_id, record)
            for object_id, record in artifact["credential_objects"].items()
            if record["policy_basis"] == "plaintext_credential"
        )
        mutations = (
            (oauth_id, {**oauth, "policy_status": "observed"}, "subscription OAuth policy mismatch"),
            (oauth_id, {**oauth, "policy_basis": "none"}, "subscription OAuth policy mismatch"),
            (plaintext_id, {**plaintext, "policy_status": "observed"}, "plaintext credential policy mismatch"),
            (plaintext_id, {**plaintext, "policy_basis": "none"}, "plaintext credential policy mismatch"),
        )
        for object_id, mutated, message in mutations:
            candidate = json.loads(json.dumps(artifact))
            candidate["credential_objects"][object_id] = mutated
            with self.subTest(message=message), self.assertRaisesRegex(SystemExit, message):
                self.generator.validate_credential_objects(candidate)
        without_finding = json.loads(json.dumps(artifact))
        without_finding["finding_objects"] = {}
        with self.assertRaisesRegex(SystemExit, "plaintext finding required"):
            self.generator.validate_credential_objects(without_finding)

    def test_credential_object_validator_rejects_noncanonical_auth_kind_aliases(self) -> None:
        artifact = read_json(OBJECTS)
        self.generator.validate_credential_objects(artifact)
        oauth_id, oauth = next(
            (object_id, record)
            for object_id, record in artifact["credential_objects"].items()
            if record["credential_type"] == "oauth"
            and record["provider"] in self.generator.SUBSCRIPTION_OAUTH_PROVIDERS
        )
        plaintext_id, plaintext = next(
            (object_id, record)
            for object_id, record in artifact["credential_objects"].items()
            if record["policy_basis"] == "plaintext_credential"
        )
        cases = (
            (oauth_id, oauth, "oauth_token"),
            (oauth_id, oauth, "subscription_oauth"),
            (plaintext_id, plaintext, "plaintext"),
        )
        for object_id, record, alias in cases:
            candidate = json.loads(json.dumps(artifact))
            candidate["credential_objects"][object_id] = {
                **record,
                "credential_type": alias,
                "policy_status": "observed",
                "policy_basis": "none",
            }
            with self.subTest(alias=alias), self.assertRaisesRegex(
                SystemExit, "invalid credential type"
            ):
                self.generator.validate_credential_objects(candidate)

    def test_credential_object_validator_rejects_untyped_raw_path_locators(self) -> None:
        artifact = read_json(OBJECTS)
        self.generator.validate_credential_objects(artifact)
        object_id, record = next(iter(artifact["credential_objects"].items()))
        locators = (
            "locator:/home/fixture/private",
            "locator:/Users/fixture/private",
            "locator:/Volumes/private",
            "locator:C:/Users/fixture/private",
            r"locator:\\server\share",
            "locator:~/private",
        )
        for locator in locators:
            candidate = json.loads(json.dumps(artifact))
            candidate["credential_objects"][object_id] = {
                **record, "evidence_locator": locator,
            }
            with self.subTest(locator_kind=locator.split(":", 1)[0]), self.assertRaisesRegex(
                SystemExit, "invalid evidence locator"
            ):
                self.generator.validate_credential_objects(candidate)

    def test_credential_object_validator_rejects_boundary_position_raw_paths(self) -> None:
        artifact = read_json(OBJECTS)
        self.generator.validate_credential_objects(artifact)
        object_id, record = next(iter(artifact["credential_objects"].items()))
        raw_values = (
            "alias:/home/fixture/private",
            "alias:/Users/fixture/private",
            "alias:/Volumes/private",
            "alias:C:/Users/fixture/private",
            r"alias:\\server\share",
            "alias:~/private",
        )
        for value in raw_values:
            candidate = json.loads(json.dumps(artifact))
            candidate["credential_objects"][object_id] = {
                **record, "account_alias": value,
            }
            with self.subTest(value_kind=value.split(":", 1)[0]), self.assertRaisesRegex(
                SystemExit, "raw absolute or home path"
            ):
                self.generator.validate_credential_objects(candidate)

    def test_credential_object_validator_rejects_raw_paths_after_any_delimiter(self) -> None:
        artifact = read_json(OBJECTS)
        self.generator.validate_credential_objects(artifact)
        original_id, original = next(iter(artifact["credential_objects"].items()))
        malicious = (
            "alias|/Users/fixture/private",
            "alias'/home/fixture/private",
            "alias|C:/Users/fixture/private",
            r"alias|\\server\share",
        )
        for index, field in enumerate(original):
            record = {**original, field: malicious[index % len(malicious)]}
            object_id = self.generator.credential_object_id(
                record["provider"], record["account_alias"], record["credential_ref"]
            )
            candidate = json.loads(json.dumps(artifact))
            del candidate["credential_objects"][original_id]
            candidate["credential_objects"][object_id] = record
            expected = (
                "invalid evidence locator"
                if field == "evidence_locator"
                else "raw absolute or home path"
            )
            with self.subTest(field=field), self.assertRaisesRegex(SystemExit, expected):
                self.generator.validate_credential_objects(candidate)

    def test_credential_object_validator_rejects_multi_slash_paths_after_any_delimiter(self) -> None:
        artifact = read_json(OBJECTS)
        self.generator.validate_credential_objects(artifact)
        original_id, original = next(iter(artifact["credential_objects"].items()))
        malicious = (
            "alias|//Users/fixture/private",
            "alias'//home/fixture/private",
            "alias—//Volumes/fixture/private",
            "alias※//private/fixture",
        )
        for field in original:
            for value in malicious:
                record = {**original, field: value}
                object_id = self.generator.credential_object_id(
                    record["provider"], record["account_alias"], record["credential_ref"]
                )
                candidate = json.loads(json.dumps(artifact))
                del candidate["credential_objects"][original_id]
                candidate["credential_objects"][object_id] = record
                expected = (
                    "invalid evidence locator"
                    if field == "evidence_locator"
                    else "raw absolute or home path"
                )
                with self.subTest(field=field, value=value), self.assertRaisesRegex(
                    SystemExit, expected
                ):
                    self.generator.validate_credential_objects(candidate)

    def test_credential_object_validator_accepts_only_typed_portable_locator_paths(self) -> None:
        artifact = read_json(OBJECTS)
        self.generator.validate_credential_objects(artifact)
        object_id, record = next(iter(artifact["credential_objects"].items()))
        portable = json.loads(json.dumps(artifact))
        portable["credential_objects"][object_id] = {
            **record,
            "evidence_locator": (
                "launchd-components:path:system:/bin/true;blob:"
                + "a" * 40
                + ",path:~/portable/script.sh;blob:"
                + "b" * 40
            ),
        }
        self.generator.validate_credential_objects(portable)

    def test_credential_object_validator_rejects_raw_paths_in_every_string_field(self) -> None:
        artifact = read_json(OBJECTS)
        self.generator.validate_credential_objects(artifact)
        object_id, record = next(iter(artifact["credential_objects"].items()))
        raw_paths = (
            "/Users/fixture/private",
            "/home/fixture/private",
            "~/private",
            r"C:\Users\fixture\private",
        )
        for index, field in enumerate(record):
            candidate = json.loads(json.dumps(artifact))
            candidate["credential_objects"][object_id][field] = raw_paths[index % len(raw_paths)]
            expected_error = (
                "invalid evidence locator"
                if field == "evidence_locator"
                else "raw absolute or home path"
            )
            with self.subTest(field=field), self.assertRaisesRegex(
                SystemExit, expected_error
            ):
                self.generator.validate_credential_objects(candidate)
        portable = json.loads(json.dumps(artifact))
        portable["credential_objects"][object_id]["evidence_locator"] = (
            "launchd-components:path:system:/bin/bash;blob:"
            + "a" * 40
            + ",path:~/portable/script.sh;blob:"
            + "b" * 40
        )
        self.generator.validate_credential_objects(portable)

    def test_safe_projection_handles_invalid_provider_entries_without_leaking_details(self) -> None:
        projected = self.collector.project_models_status(
            {
                "defaultModel": None,
                "fallbacks": ["invalid"],
                "auth": {
                    "providers": [None, {"provider": "../bad"}],
                    "missingProvidersInUse": [None, "../bad", "openai"],
                },
            }
        )
        self.assertEqual([], projected["provider_chain"])
        self.assertEqual(["openai"], projected["missing_providers"])
        audit = self.collector.project_secrets_audit(
            {"status": "findings", "findings": [None, {"provider": "x"}], "summary": [], "resolution": []}
        )
        self.assertEqual({}, audit["finding_counts"])

    def test_launchd_config_revision_uses_safe_projection_without_raw_blob(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            plist = Path(temp_dir) / "fixture.plist"
            plist.write_text(
                "<plist version=\"1.0\"><dict><key>Program</key><string>/bin/true</string>"
                "<key>ProgramArguments</key><array><string>/bin/true</string></array></dict></plist>",
                encoding="utf-8",
            )
            record = self.collector.config_revision_record(
                {"source_type": "launchd", "evidence": str(plist)}
            )
        self.assertNotEqual("unverified", record["digest"])
        self.assertIn("launchd-safe-config:", record["evidence_locator"])
        self.assertNotIn("blob:", record["evidence_locator"])

    def test_tracked_candidate_observation_review_revision_chain_is_exact(self) -> None:
        parents = read_tsv(PARENT)
        observations = read_json(OBSERVATIONS)
        review = read_json(REVIEW)
        self.generator.validate_revision_chain(parents, observations, review, candidate=True)
        self.generator.validate_exact_parent_map(parents, review)
        self.assertEqual("review_required", review["review_status"])
        self.assertEqual(self.generator.PENDING_REVIEW_BASIS, review["review_basis"])
        self.assertEqual(self.generator.canonical_digest(observations), review["approved_observation_digest"])
        self.assertEqual(CURRENT_PARENT_DIGEST, observations["parent_inventory_digest"])
        self.assertEqual(334, len(observations["parents"]))
        self.assertEqual(334, len(review["parents"]))

    def test_separate_independent_review_artifact_is_approved_and_digest_bound(self) -> None:
        self.assertTrue(INDEPENDENT_REVIEW.is_file())
        independent = read_json(INDEPENDENT_REVIEW)
        review = read_json(REVIEW)
        observations = read_json(OBSERVATIONS)
        objects = read_json(OBJECTS)
        edges = read_tsv(TRACKED)
        self.assertEqual("approved", independent["review_status"])
        self.assertEqual(
            self.generator.APPROVED_INDEPENDENT_REVIEW_BASIS,
            independent["review_basis"],
        )
        self.assertEqual(
            self.generator.APPROVED_INDEPENDENT_REVIEW_BASIS,
            independent["approval_basis"],
        )
        self.assertEqual("independent_fresh_credential_reviewer", independent["reviewer_role"])
        self.assertEqual(self.generator.canonical_digest(review), independent["candidate_manifest_digest"])
        self.assertEqual(CURRENT_PARENT_DIGEST, independent["parent_inventory_digest"])
        self.assertEqual(self.generator.canonical_digest(observations), independent["observation_digest"])
        self.assertEqual(self.generator.canonical_digest(objects), independent["object_digest"])
        self.assertEqual(self.generator.canonical_digest(edges), independent["inventory_digest"])

    def test_builder_two_field_self_promotion_remains_rejected(self) -> None:
        promoted = read_json(REVIEW)
        promoted["review_status"] = "approved"
        promoted["review_basis"] = self.generator.APPROVED_REVIEW_BASIS
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            promoted_path = temp / "promoted-builder.json"
            output = temp / "must-not-exist.tsv"
            promoted_path.write_text(json.dumps(promoted), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(GENERATOR), "--review", str(promoted_path),
                 "--independent-review", str(INDEPENDENT_REVIEW), "--output", str(output)],
                cwd=REPO, text=True, capture_output=True,
            )
        self.assertNotEqual(0, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertFalse(output.exists())
        self.assertIn("builder review manifest must remain pending", result.stderr)

    def test_parent_inventory_top_digest_rejects_stale_omission_and_substitution(self) -> None:
        parents = read_tsv(PARENT)
        observations = read_json(OBSERVATIONS)
        review = read_json(REVIEW)
        zero = "sha256:" + ":".join(["0" * 8] * 8)
        variants = []
        stale = json.loads(json.dumps(observations)); stale["parent_inventory_digest"] = zero
        variants.append(stale)
        omitted = json.loads(json.dumps(observations))
        omitted["parent_inventory_digest"] = self.generator.canonical_digest(
            [self.generator.parent_metadata_digest(parent) for parent in parents[:-1]]
        )
        variants.append(omitted)
        substituted = json.loads(json.dumps(observations))
        changed_parents = [*parents[:-1], {**parents[-1], "entrypoint": "fixture-substitution"}]
        substituted["parent_inventory_digest"] = self.generator.canonical_digest(
            [self.generator.parent_metadata_digest(parent) for parent in changed_parents]
        )
        variants.append(substituted)
        for changed in variants:
            with self.subTest(digest=changed["parent_inventory_digest"]):
                with self.assertRaisesRegex(SystemExit, "parent inventory digest mismatch"):
                    self.generator.validate_revision_chain(parents, changed, review, candidate=True)

    def test_synthetic_pending_independent_review_is_candidate_only(self) -> None:
        parents = read_tsv(PARENT)
        observations = read_json(OBSERVATIONS)
        review = read_json(REVIEW)
        independent = pending_independent_review_fixture()
        objects = read_json(OBJECTS)
        edges = read_tsv(TRACKED)
        self.assertEqual("review_required", review["review_status"])
        self.assertEqual(self.generator.PENDING_REVIEW_BASIS, review["review_basis"])
        self.generator.validate_revision_chain(parents, observations, review, candidate=True)
        with self.assertRaisesRegex(SystemExit, "independent credential rebind review required"):
            self.generator.validate_independent_review(
                independent, parents, observations, review, objects, edges, candidate=False
            )
        self.generator.validate_independent_review(
            independent, parents, observations, review, objects, edges, candidate=True
        )

    def test_four_new_parents_are_explicitly_unverified_and_revision_bound(self) -> None:
        observations = read_json(OBSERVATIONS)
        review = read_json(REVIEW)
        self.assertEqual(set(NEW_PARENT_DIGESTS), set(NEW_PARENT_DIGESTS) & set(observations["parents"]))
        for parent_id, digest in NEW_PARENT_DIGESTS.items():
            with self.subTest(parent_id=parent_id):
                self.assertEqual(digest, observations["parents"][parent_id]["parent_metadata_digest"])
                self.assertEqual(digest, review["parents"][parent_id]["parent_metadata_digest"])
                self.assertEqual("unverified", review["parents"][parent_id]["decision"])
                self.assertEqual("independent_review_pending", review["parents"][parent_id]["decision_basis"])

    def test_tracked_stale_cron_parents_remain_unverified_without_explicit_absence(self) -> None:
        observations = read_json(OBSERVATIONS)
        review = read_json(REVIEW)
        expected = {
            "openclaw:891b90bb-104f-4f6c-86fb-b16bc6863a86",
            "openclaw:anicca-life-notify-poll",
            "openclaw:anicca-life-notify-scan",
            "openclaw:fastlane-affirmation-daily-post",
            "openclaw:ffe3152e-8a56-47bc-9ab9-d5cd59a85326",
        }
        self.assertEqual(set(), set(observations["cron_absence_observations"]))
        for parent_id in expected:
            observed = observations["parents"][parent_id]
            self.assertNotIn("cron_absence_evidence", observed)
            self.assertEqual("cron_metadata_unavailable", observed["reason"])
            reviewed = review["parents"][parent_id]
            self.assertEqual("unverified", reviewed["decision"])
            self.assertEqual("cron_metadata_unavailable", reviewed["decision_basis"])

    def test_credential_catalog_distinguishes_loop_used_and_catalog_only_objects(self) -> None:
        artifact = read_json(OBJECTS)
        object_ids = set(artifact["credential_objects"])
        loop_used = {
            row["credential_object_id"] for row in read_tsv(TRACKED)
            if row["credential_object_id"] in object_ids
        }
        self.assertEqual(54, len(object_ids))
        self.assertEqual(49, len(loop_used))
        self.assertEqual(5, len(object_ids - loop_used))

    def test_synthetic_pending_independent_review_blocks_normal_generation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            pending_path = temp / "pending-independent-review.json"
            output = temp / "must-not-exist.tsv"
            pending_path.write_text(
                json.dumps(pending_independent_review_fixture()), encoding="utf-8"
            )
            result = subprocess.run(
                [sys.executable, str(GENERATOR), "--independent-review", str(pending_path),
                 "--output", str(output)],
                cwd=REPO, text=True, capture_output=True,
            )
            self.assertFalse(output.exists())
        self.assertNotEqual(0, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertIn("independent credential rebind review required", result.stderr)

    def test_pending_review_candidate_passes_full_generation_contract(self) -> None:
        review = read_json(REVIEW)
        with tempfile.TemporaryDirectory() as temp_dir:
            pending = Path(temp_dir) / "pending-review.json"
            independent = Path(temp_dir) / "pending-independent-review.json"
            pending.write_text(json.dumps(review), encoding="utf-8")
            independent.write_text(
                json.dumps(pending_independent_review_fixture()), encoding="utf-8"
            )
            stdout = io.StringIO()
            stderr = io.StringIO()
            with mock.patch.object(
                sys,
                "argv",
                [
                    str(GENERATOR), "--check", "--candidate", "--parent", str(PARENT),
                    "--observations", str(OBSERVATIONS), "--review", str(pending),
                    "--independent-review", str(independent),
                    "--objects", str(OBJECTS),
                ],
            ), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                self.generator.main()
        self.assertEqual(TRACKED.read_text(encoding="utf-8"), stdout.getvalue())
        summary = json.loads(stderr.getvalue())
        self.assertEqual(334, summary["parents"])
        self.assertEqual(54, summary["credential_objects"])

    def test_tracked_artifacts_contain_no_synthesized_openclaw_bundle(self) -> None:
        objects = read_json(OBJECTS)["credential_objects"].values()
        self.assertNotIn("openclaw", {record["provider"] for record in objects})
        self.assertFalse(any(record["credential_ref"].startswith("config:openclaw.agent:") for record in objects))

    def test_tracked_parse_errors_are_unverified(self) -> None:
        parse_error_ids = {
            row["inventory_id"] for row in read_tsv(PARENT) if row["state"].startswith("parse_error")
        }
        tracked = [row for row in read_tsv(TRACKED) if row["inventory_id"] in parse_error_ids]
        self.assertEqual(5, len(parse_error_ids))
        self.assertEqual(parse_error_ids, {row["inventory_id"] for row in tracked})
        review = read_json(REVIEW)["parents"]
        self.assertNotIn("review_required", {review[parent_id]["decision"] for parent_id in parse_error_ids})

    def test_safe_metadata_artifacts_exclude_raw_identity_and_home_paths(self) -> None:
        text = OBSERVATIONS.read_text(encoding="utf-8") + REVIEW.read_text(encoding="utf-8")
        self.assertNotIn("@", text)
        self.assertNotIn("/Users/", text)
        for forbidden_key in ('"email"', '"displayName"', '"label"', '"configPath"'):
            self.assertNotIn(forbidden_key, text)

    def test_tracked_launchd_evidence_has_no_env_blob_or_external_basename_locator(self) -> None:
        parents = {row["inventory_id"]: row for row in read_tsv(PARENT)}
        observations = read_json(OBSERVATIONS)["parents"]
        launchd = {
            parent_id: observations[parent_id]
            for parent_id, parent in parents.items() if parent["source_type"] == "launchd"
        }
        gateway = launchd["launchd:ai.openclaw.gateway"]
        self.assertNotIn("ai.openclaw.gateway.env", gateway["source_evidence_locator"])
        self.assertFalse(any(
            "external:" in record["source_evidence_locator"] for record in launchd.values()
        ))
        self.assertEqual(
            15, sum(record["source_revision_digest"] == "unverified" for record in launchd.values())
        )
        for record in launchd.values():
            if record["config_revision_digest"] == "unverified":
                continue
            self.assertIn("launchd-safe-config:", record["config_evidence_locator"])
            self.assertNotIn("blob:", record["config_evidence_locator"])

    def test_targeted_gitleaks_gate_passes_artifacts_and_catches_runtime_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            for source in (OBSERVATIONS, REVIEW, OBJECTS, TRACKED):
                shutil.copy2(source, target / source.name)
            clean = subprocess.run(
                ["gitleaks", "dir", str(target), "--config", str(REPO / ".gitleaks-cloud-agent.toml"), "--redact", "--no-banner"],
                capture_output=True, text=True,
            )
            self.assertEqual(0, clean.returncode)
            fixture = target / TRACKED.name
            baseline = fixture.read_text(encoding="utf-8").rstrip("\n")
            def fixture_material(seed: str, length: int) -> str:
                return hashlib.sha256(seed.encode()).hexdigest()[:length]

            runtime_fixtures = (
                "SLACK_TOKEN=" + "xoxb" + "-135792468013-246801357924-"
                + fixture_material("slack runtime regression", 32),
                "GITHUB_TOKEN=" + "ghp" + "_"
                + fixture_material("github runtime regression", 36),
                "OPENAI_API_KEY=" + "sk" + "-"
                + fixture_material("openai prefix regression", 20)
                + "T3" + "BlbkFJ"
                + fixture_material("openai suffix regression", 20),
            )
            for runtime_fixture in runtime_fixtures:
                with self.subTest(runtime_fixture=runtime_fixture.split("=", 1)[0]):
                    fixture.write_text(baseline + "\t" + runtime_fixture + "\n", encoding="utf-8")
                    detected = subprocess.run(
                        ["gitleaks", "dir", str(target), "--config", str(REPO / ".gitleaks-cloud-agent.toml"), "--redact", "--no-banner"],
                        capture_output=True, text=True,
                    )
                    self.assertNotEqual(0, detected.returncode)

    def test_gitleaks_allows_public_immutable_github_blob_urls_but_rejects_opaque_entropy(self) -> None:
        command = [
            "gitleaks", "detect", "--no-git", "--redact", "--config",
            str(REPO / ".gitleaks-cloud-agent.toml"), "--source",
        ]
        public_blob_urls = subprocess.run(
            [*command, str(DOCUMENTATION)], capture_output=True, text=True,
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            opaque = Path(temp_dir) / "opaque.txt"
            material = base64.urlsafe_b64encode(
                hashlib.sha256(b"opaque prefixless root command regression").digest()
            ).decode().rstrip("=")
            opaque.write_text(
                "https://github.com/openclaw/openclaw/blob/"
                "744a698fc5e03e1f63429b0632f097872d62e6cd/src/secrets/audit.ts "
                + material + "\n",
                encoding="utf-8",
            )
            opaque_result = subprocess.run(
                [*command, str(opaque)], capture_output=True, text=True,
            )
        self.assertNotEqual(0, opaque_result.returncode)
        self.assertEqual(0, public_blob_urls.returncode, public_blob_urls.stderr)

    def test_gitleaks_catches_prefixless_high_entropy_in_every_string_field(self) -> None:
        fields = (
            "provider", "account_alias", "credential_type", "credential_ref",
            "policy_status", "policy_basis", "evidence_locator", "consumer_locator",
            "permission_scope", "dependency_basis", "source_revision_digest",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            fixture = target / "generic.json"
            for field in fields:
                material = base64.urlsafe_b64encode(
                    hashlib.sha256(("prefixless " + field).encode()).digest()
                ).decode().rstrip("=")
                fixture.write_text(json.dumps({field: material}) + "\n", encoding="utf-8")
                detected = subprocess.run(
                    ["gitleaks", "dir", str(target), "--config", str(REPO / ".gitleaks-cloud-agent.toml"), "--redact", "--no-banner"],
                    capture_output=True, text=True,
                )
                with self.subTest(field=field):
                    self.assertNotEqual(0, detected.returncode)

            safe_values = {
                "digest": "sha256:" + ":".join(["a1b2c3d4"] * 8),
                "blob": "a" * 40,
                "uuid": "12345678-1234-4234-8234-123456789abc",
                "object_id": "credential:object-123456789012345",
            }
            fixture.write_text(json.dumps(safe_values) + "\n", encoding="utf-8")
            safe = subprocess.run(
                ["gitleaks", "dir", str(target), "--config", str(REPO / ".gitleaks-cloud-agent.toml"), "--redact", "--no-banner"],
                capture_output=True, text=True,
            )
            self.assertEqual(0, safe.returncode)

            material = base64.urlsafe_b64encode(
                hashlib.sha256(b"same line prefixless secret").digest()
            ).decode().rstrip("=")
            fixture.write_text(
                json.dumps({"blob": "b" * 40, "account_alias": material}) + "\n",
                encoding="utf-8",
            )
            same_line = subprocess.run(
                ["gitleaks", "dir", str(target), "--config", str(REPO / ".gitleaks-cloud-agent.toml"), "--redact", "--no-banner"],
                capture_output=True, text=True,
            )
            self.assertNotEqual(0, same_line.returncode)

    def test_sha256_evidence_digests_use_fixed_low_entropy_chunks(self) -> None:
        digest = self.generator.canonical_digest({"fixture": "safe metadata"})
        self.assertRegex(digest, r"^sha256:(?:[0-9a-f]{8}:){7}[0-9a-f]{8}$")
        self.assertNotRegex(digest, r"[0-9a-f]{16}")

    def test_in_process_approved_check_covers_full_generation_path(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with mock.patch.object(
            sys,
            "argv",
            [str(GENERATOR), "--check", "--parent", str(PARENT)],
        ), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            self.generator.main()
        self.assertEqual(TRACKED.read_text(encoding="utf-8"), stdout.getvalue())
        self.assertEqual(
            {
                "by_status": {
                    "inactive": 177,
                    "none_observed": 70,
                    "observed": 46,
                    "policy_violation": 87,
                    "unverified": 80,
                },
                "credential_objects": 54,
                "finding_objects": 1,
                "parents": 334,
                "rows": 460,
            },
            json.loads(stderr.getvalue()),
        )

    def test_all_334_parent_ids_are_covered_without_unknown_parents(self) -> None:
        parents = read_tsv(PARENT)
        credentials = read_tsv(TRACKED)
        parent_ids = {row["inventory_id"] for row in parents}
        covered_ids = {row["inventory_id"] for row in credentials}
        self.assertEqual(334, len(parents))
        self.assertEqual(334, len(parent_ids))
        self.assertEqual(parent_ids, covered_ids)

    def test_required_columns_values_and_ids_are_complete(self) -> None:
        rows = read_tsv(TRACKED)
        self.assertEqual(list(self.generator.EDGE_FIELDS), list(rows[0]))
        self.assertTrue(all(all(row.values()) for row in rows))
        row_ids = [row["loop_dependency_edge_id"] for row in rows]
        self.assertEqual(len(row_ids), len(set(row_ids)))
        self.assertTrue(
            {row["dependency_status"] for row in rows}
            <= {"observed", "none_observed", "unverified", "policy_violation", "inactive"}
        )
        self.assertNotIn("unknown", {row["permission_scope"] for row in rows})

    def test_generator_exposes_only_current_edge_contract(self) -> None:
        legacy_symbols = {
            "FIELDS",
            "ReviewedReference",
            "REVIEWED_LOCATORS",
            "REVIEWED_ENV_REFERENCE_NAMES",
            "GENERIC_PLACEHOLDERS",
            "CREDENTIAL_SUFFIX",
            "URL_CREDENTIAL_NAMES",
            "LANGUAGE_PATTERNS",
            "credential_name",
            "explicit_env_reference_names",
            "validate_reviewed_manifest",
            "references_for_parent",
            "reference_row",
            "observed_rows",
            "status_row",
            "rows",
            "validate",
            "unverified_rows",
            "openclaw_review_rows",
        }
        self.assertTrue(
            legacy_symbols.isdisjoint(vars(self.generator)),
            "legacy credential-row schema remains publicly reachable",
        )
        documentation = self.generator.__doc__ or ""
        for phrase in (
            "parent TSV",
            "safe observations",
            "independent review manifest",
            "credential objects",
            "edge TSV",
            "fail-closed",
            "non-secret",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, documentation)

    def test_parent_validator_rejects_duplicate_inventory_id(self) -> None:
        duplicate = [
            {"inventory_id": "loop:a", "source_type": "launchd", "entrypoint": "a.sh"},
            {"inventory_id": "loop:a", "source_type": "launchd", "entrypoint": "b.sh"},
        ]
        with self.assertRaises(SystemExit):
            self.generator.validate_parent_rows(duplicate)

    def test_generator_source_does_not_read_process_environment_or_dotenv(self) -> None:
        source = GENERATOR.read_text(encoding="utf-8")
        tree = ast.parse(source)
        calls = {
            ast.unparse(node.func)
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
        }
        self.assertNotIn("os.getenv", calls)
        self.assertNotIn("os.environ.get", calls)
        self.assertNotIn("dotenv", source.lower())
        self.assertNotIn("subprocess", source)
        forbidden_reads = {
            node.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute)
            and node.attr in {"read_bytes", "read_text", "readlines"}
        }
        self.assertEqual(set(), forbidden_reads)

    def test_typed_locator_is_parent_derived_and_unknown_source_fails(self) -> None:
        repository = {
            "inventory_id": "package:services/fixture/package.json#start",
            "source_type": "repository_entrypoint",
            "entrypoint": "node server.js",
            "state": "declared_in_repository",
            "evidence": "services/fixture/package.json",
        }
        railway = {
            "inventory_id": "railway:fixture",
            "source_type": "railway_entrypoint",
            "entrypoint": "node server.js",
            "state": "present_on_origin_main;deployment_health_not_part_of_TODO_1",
            "evidence": "https://github.com/org/repo/blob/main/services/fixture/package.json",
        }
        self.assertEqual(
            "repo:services/fixture/package.json#start",
            self.generator.typed_locator(repository),
        )
        self.assertEqual(
            "git:origin/main:services/fixture/package.json#start",
            self.generator.typed_locator(railway),
        )
        with self.assertRaises(SystemExit):
            self.generator.typed_locator({**repository, "source_type": "mystery"})
        locator_source = inspect.getsource(self.generator.typed_locator)
        self.assertNotIn("apps/life-call", locator_source)

    def test_public_path_prefers_repo_relative_before_home_relative(self) -> None:
        with mock.patch.object(self.generator, "REPO", Path("/tmp/worktree")), mock.patch.object(
            self.generator, "HOME", Path("/tmp")
        ):
            self.assertEqual(
                "apps/api/src/server.js",
                self.generator.public_path(Path("/tmp/worktree/apps/api/src/server.js")),
            )

    def test_profile_projection_keeps_only_safe_alias_provider_and_type(self) -> None:
        raw = {
            "profiles": [
                {
                    "id": "openai:fixture-identity",
                    "provider": "openai",
                    "type": "oauth",
                    "label": "private-label",
                    "displayName": "private-display",
                }
            ]
        }
        projected = self.collector.project_auth_list(raw)
        self.assertEqual({"alias", "provider", "type"}, set(projected[0]))
        self.assertEqual("openai", projected[0]["provider"])
        self.assertEqual("oauth", projected[0]["type"])
        self.assertNotIn("fixture-identity", json.dumps(projected))
        self.assertNotIn("private-label", json.dumps(projected))

    def test_models_status_projection_drops_paths_values_labels_and_details(self) -> None:
        raw = {
            "defaultModel": "deepseek/deepseek-v4-flash",
            "fallbacks": ["openai/gpt-fixture"],
            "configPath": "/private/config",
            "auth": {
                "providers": [
                    {
                        "provider": "openai",
                        "effective": {"kind": "profiles", "detail": "private"},
                        "profiles": {"count": 2, "oauth": 2, "token": 0, "apiKey": 0, "labels": ["private"]},
                    }
                ],
                "missingProvidersInUse": [],
            },
        }
        projected = self.collector.project_models_status(raw)
        text = json.dumps(projected)
        self.assertEqual(["deepseek", "openai"], projected["provider_chain"])
        for forbidden in ("configPath", "detail", "labels", "/private"):
            self.assertNotIn(forbidden, text)

    def test_secrets_audit_projection_keeps_only_counts_and_safe_provider(self) -> None:
        raw = {
            "status": "findings",
            "summary": {"plaintextCount": 2},
            "resolution": {"refsChecked": 1, "skippedExecRefs": 0, "resolvabilityComplete": True},
            "findings": [
                {"code": "PLAINTEXT_FOUND", "provider": "deepseek", "message": "private"},
                {"code": "PLAINTEXT_FOUND", "message": "private"},
            ],
        }
        projected = self.collector.project_secrets_audit(raw)
        self.assertEqual(1, projected["finding_counts"]["PLAINTEXT_FOUND:deepseek"])
        self.assertEqual(1, projected["finding_counts"]["PLAINTEXT_FOUND:unattributed"])
        self.assertNotIn("private", json.dumps(projected))

    def test_collector_collects_safe_observations_with_fake_cli(self) -> None:
        header = (
            "inventory_id\tsource_type\towner\tscope\tcurrent_location\ttrigger\t"
            "entrypoint\tstate\tmigration_target\tevidence\n"
        )
        body = (
            "openclaw:a\topenclaw_cron\to\ts\tc\tt\t"
            "openclaw_gateway:agentTurn:agent=anicca\tenabled\tm\te\n"
            "openclaw:b\topenclaw_cron\to\ts\tc\tt\t"
            "openclaw_gateway:agentTurn:agent=missing-agent\tenabled\tm\te\n"
            "launchd:opaque\tlaunchd\to\ts\tc\tt\tunparsed_plist_entrypoint\t"
            "parse_error:Fixture\tm\te\n"
        )
        responses = {
            ("openclaw", "config", "schema"): "{}",
            ("openclaw", "--version"): "OpenClaw fixture (abcdef0)",
            ("openclaw", "agents", "list", "--json"): json.dumps(
                [{"id": "anicca", "model": "deepseek/model"}]
            ),
            ("openclaw", "secrets", "audit", "--json"): json.dumps(
                {
                    "status": "clean",
                    "summary": {},
                    "resolution": {"refsChecked": 1, "skippedExecRefs": 0, "resolvabilityComplete": True},
                    "findings": [],
                }
            ),
            ("openclaw", "models", "status", "--agent", "anicca", "--json"): json.dumps(
                {"defaultModel": "deepseek/model", "fallbacks": [], "auth": {"providers": []}}
            ),
            ("openclaw", "models", "auth", "list", "--agent", "anicca", "--json"): json.dumps(
                {"profiles": [{"id": "deepseek:fixture", "provider": "deepseek", "type": "token"}]}
            ),
        }

        def fake_runner(argv):
            return subprocess.CompletedProcess(argv, 0, stdout=responses[argv], stderr="")

        with tempfile.TemporaryDirectory() as temp_dir:
            parent_path = Path(temp_dir) / "parents.tsv"
            parent_path.write_text(header + body, encoding="utf-8")
            cron_projection = {
                "schema_version": 1,
                "jobs": [
                    {
                        "job_id": "a", "enabled": True, "agent_id": "anicca",
                        "payload_kind": "agentTurn", "model_ref": "deepseek/model",
                        "fallback_refs": [], "fallbacks_inherited": True,
                        "tools_allow": [], "tools_inherited": True, "delivery_provider": "none",
                    }
                ],
            }
            result = self.collector.collect(parent_path, fake_runner, cron_projection)
        self.assertEqual(3, len(result["parents"]))
        self.assertEqual("verified", result["agents"]["agent:anicca"]["inspection_status"])
        self.assertEqual("agent_not_configured", result["agents"]["agent:missing-agent"]["reason"])
        self.assertEqual("verified", result["parents"]["openclaw:a"]["inspection_status"])
        self.assertEqual("cron_metadata_unavailable", result["parents"]["openclaw:b"]["reason"])
        self.assertEqual("parse_error", result["parents"]["launchd:opaque"]["reason"])
        self.assertNotIn("deepseek:fixture", json.dumps(result))

    def test_source_revision_digest_uses_content_not_file_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "worker.sh"
            script.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            parent = {
                "inventory_id": "launchd:fixture",
                "source_type": "launchd",
                "entrypoint": str(script),
                "evidence": str(Path(temp_dir) / "fixture.plist"),
            }
            first = self.collector.source_revision_digest(parent)
            stat = script.stat()
            os.utime(script, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))
            metadata_only = self.collector.source_revision_digest(parent)
            script.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
            second = self.collector.source_revision_digest(parent)
        self.assertEqual(first, metadata_only)
        self.assertNotEqual(first, second)

    def test_repository_revision_uses_git_tree_object(self) -> None:
        calls = []

        def fake_runner(argv):
            calls.append(argv)
            return subprocess.CompletedProcess(argv, 0, stdout="a" * 40 + "\n", stderr="")

        parent = {
            "inventory_id": "repo:fixture",
            "source_type": "repository_entrypoint",
            "entrypoint": "apps/api/package.json#start",
            "state": "present",
            "evidence": "apps/api/package.json",
        }
        self.assertNotEqual("unverified", self.collector.source_revision_digest(parent, fake_runner))
        self.assertNotEqual("unverified", self.collector.config_revision_digest(parent, fake_runner))
        expected = [
            ("git", "rev-parse", "HEAD"),
            ("git", "rev-parse", "HEAD^{tree}"),
            ("git", "rev-parse", "HEAD:apps/api/package.json"),
        ]
        self.assertEqual(expected + expected, calls)

    def test_unavailable_source_revision_fails_closed(self) -> None:
        observation = {
            "source_revision_digest": "unverified",
            "config_revision_digest": "sha256:" + ":".join(["1" * 8] * 8),
        }
        self.assertFalse(self.generator.revisions_verified(observation))

    def test_revision_chain_rejects_parent_metadata_change(self) -> None:
        parent = {"inventory_id": "loop:a", "source_type": "launchd", "entrypoint": "a"}
        digest = self.generator.parent_metadata_digest(parent)
        observed = {
            "parent_metadata_digest": digest,
            "source_revision_digest": "unverified", "config_revision_digest": "unverified",
            "source_evidence_locator": "unverified", "config_evidence_locator": "unverified",
        }
        observations = {
            "parent_inventory_digest": self.generator.canonical_digest([digest]),
            "openclaw_revision": {
                "version_digest": "unverified", "schema_digest": "unverified",
            },
            "cron_lookup_failures": {}, "cron_absence_observations": {},
            "parents": {"loop:a": observed},
        }
        review = {
            "schema_version": 2,
            "review_status": "review_required",
            "review_basis": self.generator.PENDING_REVIEW_BASIS,
            "approved_observation_digest": self.generator.canonical_digest(observations),
            "parents": {"loop:a": {
                **observed, "decision": "unverified", "decision_basis": "fixture",
                "evidence_locator": "safe-observation:unverified", "references": [],
            }},
        }
        self.generator.validate_revision_chain([parent], observations, review)
        with self.assertRaisesRegex(SystemExit, "parent inventory digest mismatch"):
            self.generator.validate_revision_chain(
                [{**parent, "entrypoint": "changed"}], observations, review
            )

    def test_revision_chain_rejects_config_digest_change(self) -> None:
        parent = {"inventory_id": "loop:a", "source_type": "launchd", "entrypoint": "a"}
        parent_digest = self.generator.parent_metadata_digest(parent)
        observed = {
            "parent_metadata_digest": parent_digest,
            "source_revision_digest": "sha256:" + ":".join(["1" * 8] * 8),
            "config_revision_digest": "sha256:" + ":".join(["2" * 8] * 8),
            "source_evidence_locator": "path:fixture;blob:" + "a" * 40,
            "config_evidence_locator": "path:fixture.plist;blob:" + "b" * 40,
        }
        observations = {
            "parent_inventory_digest": self.generator.canonical_digest([parent_digest]),
            "openclaw_revision": {
                "version_digest": "unverified", "schema_digest": "unverified",
            },
            "cron_lookup_failures": {}, "cron_absence_observations": {},
            "parents": {"loop:a": observed},
        }
        review = {
            "schema_version": 2,
            "review_status": "review_required",
            "review_basis": self.generator.PENDING_REVIEW_BASIS,
            "approved_observation_digest": self.generator.canonical_digest(observations),
            "parents": {"loop:a": {
                **observed, "decision": "unverified", "decision_basis": "fixture",
                "evidence_locator": "safe-observation:unverified", "references": [],
            }},
        }
        changed = {
            "parent_inventory_digest": self.generator.canonical_digest([parent_digest]),
            "openclaw_revision": {
                "version_digest": "unverified", "schema_digest": "unverified",
            },
            "cron_lookup_failures": {}, "cron_absence_observations": {},
            "parents": {"loop:a": {**observed, "config_revision_digest": "sha256:" + ":".join(["3" * 8] * 8)}},
        }
        with self.assertRaisesRegex(SystemExit, "review revision evidence mismatch"):
            self.generator.validate_revision_chain(
                [parent], changed, review
            )

    def test_new_openclaw_parent_requires_explicit_review_exact_map(self) -> None:
        parents = [
            {"inventory_id": "openclaw:a", "source_type": "openclaw_cron", "entrypoint": "a"},
            {"inventory_id": "openclaw:new", "source_type": "openclaw_cron", "entrypoint": "b"},
        ]
        review = {"parents": {"openclaw:a": {}}}
        with self.assertRaisesRegex(SystemExit, "review parent exact-match failure"):
            self.generator.validate_exact_parent_map(parents, review)


if __name__ == "__main__":
    unittest.main()
