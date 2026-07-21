#!/usr/bin/env python3
"""Contract tests for the TODO #4 external side-effect inventory."""

from __future__ import annotations

import ast
import base64
import csv
import hashlib
import importlib.util
import json
import subprocess
import tempfile
import unittest
from collections import Counter
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
PARENT = REPO / "docs/reference/cloud-agent-loop-inventory.tsv"
COLLECTOR = REPO / "scripts/collect-cloud-agent-external-effect-metadata.py"
GENERATOR = REPO / "scripts/generate-cloud-agent-external-effect-inventory.py"
MANIFEST = REPO / "docs/reference/cloud-agent-external-effect-discovery-manifest.json"
REVIEW = REPO / "docs/reference/cloud-agent-external-effect-discovery-review.json"
OBSERVATIONS = REPO / "docs/reference/cloud-agent-external-effect-observations.json"
OBJECTS = REPO / "docs/reference/cloud-agent-external-effect-objects.json"
TRACKED = REPO / "docs/reference/cloud-agent-external-effect-inventory.tsv"
DOCUMENTATION = REPO / "docs/reference/cloud-agent-external-effect-inventory.md"
CURRENT_PARENT_DIGEST = "sha256:90113e58:00a49511:9a84159b:1baf1728:c883a52b:0239dd87:113d1f8a:939d1e7c"
STALE_330_PARENT_DIGEST = "sha256:a0fde66c:f8f11931:6772a27d:4bf27026:f1c14816:e3bdbd49:8edb1504:26de2be4"
APPROVAL_BASIS = "todo4_independent_candidate_review_approved_v1"
APPROVED_REVIEWER_ROLE = "independent_fresh_sol_review"
NEW_PARENT_REVISIONS = {
    "launchd:ai.anicca.article-d7d8-finalizer": (
        "loop-278974739877248",
        "sha256:56b61d02:c6a4d79e:6b1ef369:c3b7cfbb:83d3b663:d0142a42:4b58824b:48195fc8",
    ),
    "launchd:ai.anicca.article-zenn-retry": (
        "loop-145753367515202",
        "sha256:80ac4e1d:a3944b38:a0f459ef:046f60a2:ae8b5d45:65f77323:19565cd1:a5605130",
    ),
    "launchd:ai.anicca.hf-gig-pass": (
        "loop-207168196247054",
        "sha256:a3b25724:9177c916:c8df7e58:a4394c3b:53c75a81:aad00585:e607dd4a:9fa12f3d",
    ),
    "launchd:ai.anicca.orca-zenn-finalizer": (
        "loop-173899012226255",
        "sha256:2acb3770:2eaf6c2a:eda0327c:b2cfbd67:de6beb9b:17ca0a68:cd58b090:e5f082bc",
    ),
}


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"not importable: {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


class ExternalEffectInventoryContractTests(unittest.TestCase):
    def test_required_files_and_exact_334_by_5_coverage_exist(self) -> None:
        for path in (COLLECTOR, GENERATOR, MANIFEST, REVIEW, OBSERVATIONS, OBJECTS, TRACKED, DOCUMENTATION):
            self.assertTrue(path.is_file(), path.name)
        generator = load_module("external_effect_generator_matrix", GENERATOR)
        self.assertEqual(
            ("call", "post", "mail", "render", "wallet"),
            tuple(generator.REQUIRED_EFFECT_CATEGORIES),
        )
        parents = read_tsv(PARENT)
        rows = read_tsv(TRACKED)
        coverage = [row for row in rows if row["effect_role"] == "category_coverage"]
        self.assertEqual(334, len(parents))
        self.assertEqual(334 * 5, len(coverage))
        expected_refs = {generator.loop_ref(parent) for parent in parents}
        pairs = {(row["loop_ref"], row["effect_category"]) for row in coverage}
        self.assertEqual(
            {(ref, category) for ref in expected_refs for category in generator.REQUIRED_EFFECT_CATEGORIES},
            pairs,
        )
        self.assertEqual(len(coverage), len(pairs))
        self.assertTrue(all(row["coverage_resolution"] in {"discovered", "none", "unverified"} for row in coverage))

    def test_rebind_artifacts_match_current_ordered_parent_revision_and_new_four(self) -> None:
        generator = load_module("external_effect_generator_334_revision", GENERATOR)
        parents = read_tsv(PARENT)
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        review = json.loads(REVIEW.read_text(encoding="utf-8"))
        observations = json.loads(OBSERVATIONS.read_text(encoding="utf-8"))
        expected_digest = generator.canonical_digest(
            [generator.parent_metadata_digest(parent) for parent in parents]
        )
        self.assertEqual(CURRENT_PARENT_DIGEST, expected_digest)
        self.assertEqual(CURRENT_PARENT_DIGEST, manifest["parent_inventory_digest"])
        self.assertEqual(CURRENT_PARENT_DIGEST, review["parent_inventory_digest"])
        self.assertEqual(CURRENT_PARENT_DIGEST, observations["parent_inventory_digest"])
        expected_refs = {generator.loop_ref(parent) for parent in parents}
        self.assertEqual(expected_refs, set(observations["loop_revisions"]))
        rows = read_tsv(TRACKED)
        self.assertEqual(expected_refs, {row["loop_ref"] for row in rows})
        parent_by_id = {parent["inventory_id"]: parent for parent in parents}
        for parent_id, (expected_ref, expected_revision) in NEW_PARENT_REVISIONS.items():
            with self.subTest(parent_id=parent_id):
                parent = parent_by_id[parent_id]
                self.assertEqual(expected_ref, generator.loop_ref(parent))
                self.assertEqual(expected_revision, generator.parent_metadata_digest(parent))
                self.assertEqual(expected_revision, observations["loop_revisions"][expected_ref])

    def test_stale_330_manifest_and_review_cannot_authorize_current_candidate(self) -> None:
        collector = load_module("external_effect_collector_stale_330", COLLECTOR)
        parents = read_tsv(PARENT)
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        review = json.loads(REVIEW.read_text(encoding="utf-8"))
        observations = json.loads(OBSERVATIONS.read_text(encoding="utf-8"))
        self.assertEqual(CURRENT_PARENT_DIGEST, manifest["parent_inventory_digest"])
        stale_manifest = json.loads(json.dumps(manifest))
        stale_manifest["parent_inventory_digest"] = STALE_330_PARENT_DIGEST
        with self.assertRaisesRegex(SystemExit, "parent inventory revision mismatch"):
            collector.validate_manifest(stale_manifest, parents)
        stale_review = json.loads(json.dumps(review))
        stale_review["parent_inventory_digest"] = STALE_330_PARENT_DIGEST
        with self.assertRaisesRegex(SystemExit, "review parent revision mismatch"):
            collector.validate_review(
                stale_review, manifest, observations["source_revisions"], candidate=False
            )

    def test_new_parent_effects_bind_only_verified_external_mutations(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        rows = read_tsv(TRACKED)
        expected_sources = {
            "profitable:skills/article-writer/scripts/zenn-deferred-worker.py": (
                NEW_PARENT_REVISIONS["launchd:ai.anicca.article-zenn-retry"][0],
                "sha256:de467764:09d44c61:45aa76f9:43d4083e:69f6efb0:2e1c0c03:1b3730c6:0beb06f4",
            ),
            "local-share:orca-zenn-finalizer/finalizer.py": (
                NEW_PARENT_REVISIONS["launchd:ai.anicca.orca-zenn-finalizer"][0],
                "sha256:85929c72:381db5d9:32484e85:a3047df8:457b3cf5:2f90b681:2d6850bf:43004e7d",
            ),
        }
        for locator, (reference, digest) in expected_sources.items():
            with self.subTest(locator=locator):
                sources = [source for source in manifest["sources"] if source["source_locator"] == locator]
                self.assertEqual(1, len(sources))
                self.assertEqual(digest, sources[0]["source_revision_digest"])
                self.assertEqual(1, len(sources[0]["declarations"]))
                declaration = sources[0]["declarations"][0]
                self.assertEqual("post", declaration["effect_category"])
                self.assertEqual([reference], declaration["loop_refs"])
                self.assertIn("git", " ".join(declaration["evidence_tokens"]))
                self.assertIn(
                    (reference, "post"),
                    {
                        (row["loop_ref"], row["effect_category"])
                        for row in rows if row["effect_role"] == "effect_binding"
                    },
                )
        bound_refs = {
            reference
            for source in manifest["sources"]
            for declaration in source["declarations"]
            for reference in declaration["loop_refs"]
        }
        for parent_id in (
            "launchd:ai.anicca.article-d7d8-finalizer",
            "launchd:ai.anicca.hf-gig-pass",
        ):
            reference = NEW_PARENT_REVISIONS[parent_id][0]
            self.assertNotIn(reference, bound_refs)
            coverage = [
                row for row in rows
                if row["loop_ref"] == reference and row["effect_role"] == "category_coverage"
            ]
            self.assertEqual(5, len(coverage))
            self.assertEqual({"unverified"}, {row["coverage_resolution"] for row in coverage})

    def test_approved_review_requires_one_coherent_exact_tuple(self) -> None:
        collector = load_module("external_effect_collector_approval_tuple", COLLECTOR)
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        review = json.loads(REVIEW.read_text(encoding="utf-8"))
        observations = json.loads(OBSERVATIONS.read_text(encoding="utf-8"))
        approved = json.loads(json.dumps(review))
        approved.update({
            "review_status": "approved",
            "review_basis": APPROVAL_BASIS,
            "approval_basis": APPROVAL_BASIS,
            "reviewer_role": APPROVED_REVIEWER_ROLE,
        })
        self.assertEqual(
            "independent_review_approved",
            collector.validate_review(
                approved, manifest, observations["source_revisions"], candidate=False
            ),
        )
        for field, invalid in (
            ("review_basis", "pending_independent_external_effect_review"),
            ("approval_basis", "pending_independent_external_effect_review"),
            ("reviewer_role", "independent_fresh_reviewer_required"),
        ):
            changed = json.loads(json.dumps(approved))
            changed[field] = invalid
            with self.subTest(field=field):
                with self.assertRaisesRegex(SystemExit, "independent external-effect review required"):
                    collector.validate_review(
                        changed, manifest, observations["source_revisions"], candidate=False
                    )

    def test_builder_manifest_cannot_promote_or_downgrade_review_state(self) -> None:
        collector = load_module("external_effect_collector_builder_review", COLLECTOR)
        parents = read_tsv(PARENT)
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual("review_required", manifest["review_status"])
        self.assertEqual("pending_independent_external_effect_review", manifest["review_basis"])
        for field, value, error in (
            ("review_status", "approved", "review status mismatch"),
            ("review_basis", APPROVAL_BASIS, "review basis mismatch"),
        ):
            changed = json.loads(json.dumps(manifest))
            changed[field] = value
            with self.subTest(field=field):
                with self.assertRaisesRegex(SystemExit, error):
                    collector.validate_manifest(changed, parents)

    def test_synthetic_pending_review_is_candidate_only_and_normal_fails_closed(self) -> None:
        review = json.loads(REVIEW.read_text(encoding="utf-8"))
        self.assertEqual("approved", review["review_status"])
        self.assertEqual(APPROVAL_BASIS, review["review_basis"])
        self.assertEqual(APPROVAL_BASIS, review["approval_basis"])
        self.assertEqual(APPROVED_REVIEWER_ROLE, review["reviewer_role"])
        pending = json.loads(json.dumps(review))
        pending.pop("approval_basis")
        pending.update({
            "review_status": "review_required",
            "review_basis": "pending_independent_external_effect_review",
            "reviewer_role": "independent_fresh_reviewer_required",
        })
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            pending_path = temp / "pending-review.json"
            pending_path.write_text(json.dumps(pending, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            candidate_observations = temp / "candidate-observations.json"
            candidate_objects = temp / "candidate-objects.json"
            candidate_edges = temp / "candidate-edges.tsv"
            normal_observations = temp / "normal-observations.json"
            normal_objects = temp / "normal-objects.json"
            normal_edges = temp / "normal-edges.tsv"
            normal_collect = subprocess.run(
                ["python3", str(COLLECTOR), "--review", str(pending_path),
                 "--output", str(normal_observations)],
                cwd=REPO, capture_output=True, text=True,
            )
            self.assertNotEqual(0, normal_collect.returncode)
            self.assertEqual("", normal_collect.stdout)
            self.assertFalse(normal_observations.exists())
            candidate_collect = subprocess.run(
                ["python3", str(COLLECTOR), "--candidate", "--review", str(pending_path),
                 "--output", str(candidate_observations)],
                cwd=REPO, capture_output=True, text=True,
            )
            self.assertEqual(0, candidate_collect.returncode, candidate_collect.stderr)
            self.assertEqual(
                "candidate_pending_review",
                json.loads(candidate_observations.read_text(encoding="utf-8"))["review_mode"],
            )
            normal_generate = subprocess.run(
                ["python3", str(GENERATOR), "--review", str(pending_path),
                 "--observations", str(candidate_observations),
                 "--objects-output", str(normal_objects), "--output", str(normal_edges)],
                cwd=REPO, capture_output=True, text=True,
            )
            self.assertNotEqual(0, normal_generate.returncode)
            self.assertEqual("", normal_generate.stdout)
            self.assertFalse(normal_objects.exists())
            self.assertFalse(normal_edges.exists())
            candidate_generate = subprocess.run(
                ["python3", str(GENERATOR), "--candidate", "--review", str(pending_path),
                 "--observations", str(candidate_observations),
                 "--objects-output", str(candidate_objects), "--output", str(candidate_edges)],
                cwd=REPO, capture_output=True, text=True,
            )
            self.assertEqual(0, candidate_generate.returncode, candidate_generate.stderr)
            self.assertTrue(candidate_objects.is_file())
            self.assertTrue(candidate_edges.is_file())

    def test_approved_normal_regeneration_is_byte_exact(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            observations = temp / "observations.json"
            objects = temp / "objects.json"
            edges = temp / "edges.tsv"
            collect = subprocess.run(
                ["python3", str(COLLECTOR), "--output", str(observations)],
                cwd=REPO, capture_output=True, text=True,
            )
            self.assertEqual(0, collect.returncode, collect.stderr)
            generate = subprocess.run(
                ["python3", str(GENERATOR), "--observations", str(observations),
                 "--objects-output", str(objects), "--output", str(edges)],
                cwd=REPO, capture_output=True, text=True,
            )
            self.assertEqual(0, generate.returncode, generate.stderr)
            self.assertEqual(OBSERVATIONS.read_bytes(), observations.read_bytes())
            self.assertEqual(OBJECTS.read_bytes(), objects.read_bytes())
            self.assertEqual(TRACKED.read_bytes(), edges.read_bytes())

    def test_known_effects_are_evidence_backed_and_wallet_is_not_allowed(self) -> None:
        objects = json.loads(OBJECTS.read_text(encoding="utf-8"))["objects"]
        by_category = {category: [] for category in ("call", "post", "mail", "render", "wallet")}
        for item in objects:
            if item["discovery_status"] == "observed":
                by_category[item["effect_category"]].append(item)
        for category in by_category:
            self.assertTrue(by_category[category], category)
        self.assertEqual({"blocked"}, {item["execution_policy"] for item in by_category["wallet"]})
        self.assertTrue(all(item["source_revision_digest"].startswith("sha256:") for values in by_category.values() for item in values))
        required_metadata = {
            "direction", "provider_tool_ref", "mutability", "financial_risk",
            "idempotency", "approval_gate",
        }
        for values in by_category.values():
            for item in values:
                self.assertTrue(required_metadata <= set(item))
                self.assertRegex(item["provider_tool_ref"], r"^tool-ref-[0-9]{15}$")
        wallet = by_category["wallet"][0]
        self.assertEqual("real_money", wallet["financial_risk"])
        self.assertEqual("execution_blocked", wallet["approval_gate"])

    def test_exact_bound_examples_and_shared_post_object(self) -> None:
        generator = load_module("external_effect_generator_known", GENERATOR)
        parents = read_tsv(PARENT)
        expected = {
            parent["inventory_id"]: generator.loop_ref(parent)
            for parent in parents
            if parent["inventory_id"] in {
                "openclaw:comedy-tiktok-cross-post-daily-1778242512055",
                "openclaw:opening-cafe-cross-post-daily-1778035787000",
                "package:apps/api/package.json#start",
                "launchd:ai.anicca.clip-loop",
                "launchd:ai.anicca.realtime-guide",
            }
        }
        rows = read_tsv(TRACKED)
        bindings = [row for row in rows if row["effect_role"] == "effect_binding"]
        bound_pairs = {(row["loop_ref"], row["effect_category"]) for row in bindings}
        for parent_id, category in (
            ("package:apps/api/package.json#start", "mail"),
            ("launchd:ai.anicca.clip-loop", "render"),
            ("launchd:ai.anicca.realtime-guide", "call"),
        ):
            self.assertIn((expected[parent_id], category), bound_pairs)
        post_rows = [row for row in bindings if row["effect_category"] == "post"]
        self.assertEqual(4, len(post_rows))
        legacy_post_rows = [
            row for row in post_rows
            if row["loop_ref"] in {
                expected["openclaw:comedy-tiktok-cross-post-daily-1778242512055"],
                expected["openclaw:opening-cafe-cross-post-daily-1778035787000"],
            }
        ]
        self.assertEqual(1, len({row["effect_object_id"] for row in legacy_post_rows}))
        self.assertEqual(
            {expected["openclaw:comedy-tiktok-cross-post-daily-1778242512055"],
             expected["openclaw:opening-cafe-cross-post-daily-1778035787000"]},
            {row["loop_ref"] for row in legacy_post_rows},
        )
        self.assertFalse(any(row["effect_category"] == "wallet" for row in bindings))

    def test_objects_and_edges_are_independent_opaque_records(self) -> None:
        generator = load_module("external_effect_generator_objects", GENERATOR)
        objects = json.loads(OBJECTS.read_text(encoding="utf-8"))["objects"]
        rows = read_tsv(TRACKED)
        bindings = [row for row in rows if row["effect_role"] == "effect_binding"]
        coverage = [row for row in rows if row["effect_role"] == "category_coverage"]
        self.assertEqual(list(generator.EDGE_FIELDS), list(rows[0]))
        self.assertEqual(12, len(objects))
        self.assertEqual(1677, len(rows))
        self.assertEqual(1670, len(coverage))
        self.assertEqual(7, len(bindings))
        self.assertEqual(
            {"call": 1, "mail": 1, "post": 4, "render": 1},
            dict(sorted(Counter(row["effect_category"] for row in bindings).items())),
        )
        self.assertTrue(all(generator.OBJECT_ID_PATTERN.fullmatch(item["effect_object_id"]) for item in objects))
        self.assertTrue(all(generator.LOOP_REF_PATTERN.fullmatch(row["loop_ref"]) for row in rows))
        self.assertEqual(len(rows), len({row["effect_edge_id"] for row in rows}))
        self.assertGreater(Counter(row["effect_object_id"] for row in rows).most_common(1)[0][1], 1)

    def test_manifest_observation_and_inventory_schemas_are_exact(self) -> None:
        collector = load_module("external_effect_collector_schema", COLLECTOR)
        generator = load_module("external_effect_generator_schema", GENERATOR)
        parents = read_tsv(PARENT)
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        review = json.loads(REVIEW.read_text(encoding="utf-8"))
        observations = json.loads(OBSERVATIONS.read_text(encoding="utf-8"))
        changed = json.loads(json.dumps(manifest)); changed["unknown"] = "fixture"
        with self.assertRaisesRegex(SystemExit, "schema"):
            collector.validate_manifest(changed, parents)
        changed = json.loads(json.dumps(review)); changed["unknown"] = "fixture"
        with self.assertRaisesRegex(SystemExit, "schema"):
            collector.validate_review(changed, manifest, observations["source_revisions"], candidate=False)
        changed = json.loads(json.dumps(observations)); changed["unknown"] = "fixture"
        with self.assertRaisesRegex(SystemExit, "schema"):
            collector.validate_observations_schema(changed)
        objects, rows = generator.build_inventory(parents, manifest, observations, review, candidate=False)
        objects[0]["unknown"] = "fixture"
        with self.assertRaisesRegex(SystemExit, "schema"):
            generator.validate_inventory(objects, rows, parents, manifest, observations, review, candidate=False)

    def test_revisions_fail_closed(self) -> None:
        generator = load_module("external_effect_generator_revision", GENERATOR)
        parents = read_tsv(PARENT)
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        review = json.loads(REVIEW.read_text(encoding="utf-8"))
        observations = json.loads(OBSERVATIONS.read_text(encoding="utf-8"))
        zero = "sha256:" + ":".join(["0" * 8] * 8)
        changed = json.loads(json.dumps(observations)); changed["parent_inventory_digest"] = zero
        with self.assertRaisesRegex(SystemExit, "parent inventory revision mismatch"):
            generator.build_inventory(parents, manifest, changed, review, candidate=False)
        changed = json.loads(json.dumps(observations)); changed["source_revisions"][next(iter(changed["source_revisions"]))] = zero
        with self.assertRaisesRegex(SystemExit, "source revision mismatch"):
            generator.build_inventory(parents, manifest, changed, review, candidate=False)

    def test_private_fields_and_keys_reject_identifiers_paths_and_opaque_values(self) -> None:
        collector = load_module("external_effect_collector_privacy", COLLECTOR)
        parents = read_tsv(PARENT)
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        opaque = base64.urlsafe_b64encode(hashlib.sha256(b"todo4 opaque fixture").digest()).decode()
        for unsafe in (
            "/Users/private/source.py", "~/private/source.py", "person@example.com",
            "account_id:private-handle", "wallet:0x1234567890abcdef1234567890abcdef12345678",
            "+15555550123", "TOKEN=fixture-value", "line\nbreak", opaque,
        ):
            changed = json.loads(json.dumps(manifest))
            changed["sources"][0]["declarations"][0]["target_class"] = unsafe
            with self.subTest(value=unsafe):
                with self.assertRaises(SystemExit):
                    collector.validate_private_structure(changed, parents, "manifest")
        changed = json.loads(json.dumps(manifest))
        changed["sources"][0]["declarations"][0]["person@example.com"] = "fixture"
        with self.assertRaises(SystemExit):
            collector.validate_private_structure(changed, parents, "manifest")

    def test_no_raw_parent_id_or_sensitive_locator_in_todo4_artifacts(self) -> None:
        artifacts = (MANIFEST, REVIEW, OBSERVATIONS, OBJECTS, TRACKED, DOCUMENTATION)
        parents = read_tsv(PARENT)
        for artifact in artifacts:
            content = artifact.read_text(encoding="utf-8")
            self.assertNotIn("/Users/", content)
            self.assertNotRegex(content, r"(?i)0x[0-9a-f]{40}")
            self.assertNotRegex(content, r"\+[1-9][0-9]{9,14}")
            for parent in parents:
                self.assertNotIn(parent["inventory_id"], content)

    def test_collector_uses_fd_bound_source_reads_and_no_subprocess_or_env(self) -> None:
        source = COLLECTOR.read_text(encoding="utf-8")
        tree = ast.parse(source)
        self.assertNotIn("subprocess", source)
        self.assertNotIn("os.environ", source)
        self.assertIn("_open_lstat_bound_fd", source)
        forbidden = {
            node.attr for node in ast.walk(tree)
            if isinstance(node, ast.Attribute) and node.attr in {"read_text", "read_bytes", "readlines"}
        }
        self.assertEqual(set(), forbidden)

    def test_todo4_artifacts_are_secret_clean_and_opaque_fixture_is_detected(self) -> None:
        config = REPO / ".gitleaks-cloud-agent-external-effect.toml"
        self.assertTrue(config.is_file())
        for source in (MANIFEST, REVIEW, OBSERVATIONS, OBJECTS, TRACKED, DOCUMENTATION):
            clean = subprocess.run(
                ["gitleaks", "detect", "--no-git", "--redact", "--config", str(config), "--source", str(source)],
                capture_output=True,
                text=True,
            )
            with self.subTest(source=source.name):
                self.assertEqual(0, clean.returncode, clean.stderr)
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = Path(temp_dir) / "opaque.txt"
            material = base64.urlsafe_b64encode(
                hashlib.sha256(b"todo4 high entropy regression fixture").digest()
            ).decode().rstrip("=")
            fixture.write_text(material + "\n", encoding="utf-8")
            detected = subprocess.run(
                ["gitleaks", "detect", "--no-git", "--redact", "--config", str(config), "--source", str(fixture)],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(0, detected.returncode)


if __name__ == "__main__":
    unittest.main()
