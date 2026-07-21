#!/usr/bin/env python3
"""Contract tests for the TODO #3 state/artifact inventory."""

from __future__ import annotations

import ast
import base64
import csv
import hashlib
import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
from collections import Counter
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
PARENT = REPO / "docs/reference/cloud-agent-loop-inventory.tsv"
COLLECTOR = REPO / "scripts/collect-cloud-agent-state-artifact-metadata.py"
GENERATOR = REPO / "scripts/generate-cloud-agent-state-artifact-inventory.py"
OBSERVATIONS = REPO / "docs/reference/cloud-agent-state-artifact-observations.json"
DISCOVERY = REPO / "docs/reference/cloud-agent-state-artifact-discovery-manifest.json"
DISCOVERY_REVIEW = REPO / "docs/reference/cloud-agent-state-artifact-discovery-review.json"
OBJECTS = REPO / "docs/reference/cloud-agent-state-artifact-objects.json"
TRACKED = REPO / "docs/reference/cloud-agent-state-artifact-inventory.tsv"
DOCUMENTATION = REPO / "docs/reference/cloud-agent-state-artifact-inventory.md"


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


class StateArtifactInventoryContractTests(unittest.TestCase):
    def test_every_parent_has_exact_required_category_coverage_matrix(self) -> None:
        generator = load_module("state_artifact_generator_category_matrix", GENERATOR)
        parents = read_tsv(PARENT)
        rows = read_tsv(TRACKED)
        required = {"state", "log", "media", "transcript", "cache", "output"}
        self.assertEqual(required, set(generator.REQUIRED_ARTIFACT_CATEGORIES))
        coverage = [row for row in rows if row.get("artifact_role") == "category_coverage"]
        self.assertEqual(330 * 6, len(coverage))
        expected_loop_refs = {generator.loop_ref(parent) for parent in parents}
        self.assertEqual(expected_loop_refs, {row["loop_ref"] for row in coverage})
        pairs = [(row["loop_ref"], row["artifact_category"]) for row in coverage]
        self.assertEqual(len(pairs), len(set(pairs)))
        self.assertEqual(
            {(loop_ref, category) for loop_ref in expected_loop_refs for category in required},
            set(pairs),
        )
        self.assertTrue(
            all(row["coverage_resolution"] in {"discovered", "none_observed", "unverified"} for row in coverage)
        )
        self.assertTrue(
            all(row["artifact_category"] != "definition" for row in coverage)
        )

    def test_builder_manifest_stays_pending_while_separate_review_approves(self) -> None:
        generator = load_module("state_artifact_generator_independent_review", GENERATOR)
        manifest = json.loads(DISCOVERY.read_text(encoding="utf-8"))
        self.assertEqual("review_required", manifest["review_status"])
        self.assertTrue(DISCOVERY_REVIEW.is_file())
        review = json.loads(DISCOVERY_REVIEW.read_text(encoding="utf-8"))
        self.assertEqual("approved", review["review_status"])
        self.assertEqual(
            "todo3_independent_candidate_review_approved_v1", review["approval_basis"]
        )
        objects, edges = generator.build_inventory(
            read_tsv(PARENT),
            manifest,
            json.loads(OBSERVATIONS.read_text(encoding="utf-8")),
            review=review,
        )
        self.assertEqual(120, len(objects))
        self.assertEqual({"independent_review_approved"}, {row["review_mode"] for row in edges})

    def test_independent_approval_enables_normal_byte_exact_outputs(self) -> None:
        manifest = json.loads(DISCOVERY.read_text(encoding="utf-8"))
        review = json.loads(DISCOVERY_REVIEW.read_text(encoding="utf-8"))
        self.assertEqual("review_required", manifest["review_status"])
        self.assertEqual("approved", review["review_status"])
        self.assertEqual(
            "todo3_independent_candidate_review_approved_v1",
            review["approval_basis"],
        )
        self.assertEqual("independent_fresh_sol_review", review["reviewer_role"])
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            observations = temp / "observations.json"
            edges = temp / "edges.tsv"
            objects = temp / "objects.json"
            collect = subprocess.run(
                ["python3", str(COLLECTOR), "--output", str(observations)],
                cwd=REPO,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, collect.returncode, collect.stderr)
            generate = subprocess.run(
                [
                    "python3", str(GENERATOR), "--observations", str(observations),
                    "--output", str(edges), "--objects-output", str(objects),
                ],
                cwd=REPO,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, generate.returncode, generate.stderr)
            self.assertEqual(OBSERVATIONS.read_bytes(), observations.read_bytes())
            self.assertEqual(TRACKED.read_bytes(), edges.read_bytes())
            self.assertEqual(OBJECTS.read_bytes(), objects.read_bytes())
        self.assertEqual(
            "independent_review_approved",
            json.loads(OBSERVATIONS.read_text(encoding="utf-8"))["review_mode"],
        )
        self.assertEqual(
            {"independent_review_approved"},
            {row["review_mode"] for row in read_tsv(TRACKED)},
        )
        self.assertEqual(
            "independent_review_approved",
            json.loads(OBJECTS.read_text(encoding="utf-8"))["review_mode"],
        )

    def test_invalid_review_variants_fail_closed_without_output(self) -> None:
        approved = json.loads(DISCOVERY_REVIEW.read_text(encoding="utf-8"))
        zero_digest = "sha256:" + ":".join(["0" * 8] * 8)
        variants: dict[str, dict[str, object] | None] = {"missing": None}
        unapproved = json.loads(json.dumps(approved))
        unapproved["review_status"] = "review_required"
        unapproved["review_basis"] = "pending_independent_architecture_review"
        unapproved.pop("approval_basis", None)
        variants["unapproved"] = unapproved
        wrong_basis = json.loads(json.dumps(approved))
        wrong_basis["approval_basis"] = "wrong_basis"
        variants["wrong_basis"] = wrong_basis
        stale_manifest = json.loads(json.dumps(approved))
        stale_manifest["manifest_digest"] = zero_digest
        variants["stale_manifest"] = stale_manifest
        stale_parent = json.loads(json.dumps(approved))
        stale_parent["parent_inventory_digest"] = zero_digest
        variants["stale_parent"] = stale_parent
        stale_source = json.loads(json.dumps(approved))
        source_id = next(iter(stale_source["source_revisions"]))
        stale_source["source_revisions"][source_id] = zero_digest
        variants["stale_source"] = stale_source
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            for name, review in variants.items():
                review_path = temp / f"{name}.json"
                if review is not None:
                    review_path.write_text(json.dumps(review), encoding="utf-8")
                for tool, base_args, output in (
                    ("collector", ["python3", str(COLLECTOR)], temp / f"{name}-observations.json"),
                    ("generator", ["python3", str(GENERATOR)], temp / f"{name}-edges.tsv"),
                ):
                    completed = subprocess.run(
                        base_args + ["--review", str(review_path), "--output", str(output)],
                        cwd=REPO,
                        capture_output=True,
                        text=True,
                    )
                    with self.subTest(variant=name, tool=tool):
                        self.assertNotEqual(0, completed.returncode)
                        self.assertEqual("", completed.stdout)
                        self.assertFalse(output.exists())

    def test_candidate_mode_cannot_downgrade_an_approved_review(self) -> None:
        for command in (
            ["python3", str(COLLECTOR), "--candidate"],
            ["python3", str(GENERATOR), "--candidate"],
        ):
            completed = subprocess.run(command, cwd=REPO, capture_output=True, text=True)
            with self.subTest(command=Path(command[1]).name):
                self.assertNotEqual(0, completed.returncode)
                self.assertEqual("", completed.stdout)
                self.assertIn("candidate review artifact must remain pending", completed.stderr)
        rows = read_tsv(TRACKED)
        self.assertEqual({"independent_review_approved"}, {row["review_mode"] for row in rows})

    def test_manifest_review_and_observation_fields_are_privacy_validated(self) -> None:
        collector = load_module("state_artifact_collector_all_field_privacy", COLLECTOR)
        generator = load_module("state_artifact_generator_all_field_privacy", GENERATOR)
        parents = read_tsv(PARENT)
        manifest = json.loads(DISCOVERY.read_text(encoding="utf-8"))
        review = json.loads(DISCOVERY_REVIEW.read_text(encoding="utf-8"))
        observations = json.loads(OBSERVATIONS.read_text(encoding="utf-8"))
        changed_manifest = json.loads(json.dumps(manifest))
        changed_manifest["sources"][0]["source_locator"] = "/Users/private/source.py"
        with self.assertRaisesRegex(SystemExit, "unsafe field source_locator"):
            collector.validate_manifest(changed_manifest, parents)
        changed_review = json.loads(json.dumps(review))
        changed_review["reviewer_role"] = "account_id:personal-handle"
        with self.assertRaisesRegex(SystemExit, "unsafe field reviewer_role"):
            generator.build_inventory(
                parents, manifest, observations, changed_review
            )
        changed_observations = json.loads(json.dumps(observations))
        object_id = next(iter(changed_observations["objects"]))
        changed_observations["objects"][object_id]["discovery_evidence_locator"] = "line\nbreak"
        with self.assertRaisesRegex(SystemExit, "unsafe field discovery_evidence_locator"):
            generator.build_inventory(
                parents, manifest, changed_observations, review
            )

    def test_recursive_dict_keys_receive_the_same_privacy_policy(self) -> None:
        collector = load_module("state_artifact_collector_key_privacy", COLLECTOR)
        parents = read_tsv(PARENT)
        parent_id = parents[0]["inventory_id"]
        opaque = base64.urlsafe_b64encode(
            hashlib.sha256(b"todo3 malicious dictionary key").digest()
        ).decode()
        unsafe_keys = (
            parent_id,
            "/Users/private/key",
            "~/private/key",
            "C:\\Users\\private\\key",
            "\\\\server\\share\\key",
            "person@example.com",
            "Daisuke134",
            "job:private-12345678",
            "account_id:personal-handle",
            "TOKEN=fixture-value",
            "line\nbreak",
            opaque,
        )
        fixtures = {
            "manifest": json.loads(DISCOVERY.read_text(encoding="utf-8")),
            "review": json.loads(DISCOVERY_REVIEW.read_text(encoding="utf-8")),
            "observations": json.loads(OBSERVATIONS.read_text(encoding="utf-8")),
        }
        for label, fixture in fixtures.items():
            for unsafe_key in unsafe_keys:
                changed = json.loads(json.dumps(fixture))
                if label == "manifest":
                    target = changed["sources"][0]["declarations"][0]
                elif label == "review":
                    target = changed["source_revisions"]
                else:
                    target = changed["objects"][next(iter(changed["objects"]))]
                target[unsafe_key] = "fixture"
                with self.subTest(label=label, key=unsafe_key):
                    with self.assertRaises(SystemExit):
                        collector.validate_private_structure(changed, parents, label)

    def test_exact_schema_rejects_unknown_keys_at_every_level(self) -> None:
        collector = load_module("state_artifact_collector_exact_schemas", COLLECTOR)
        generator = load_module("state_artifact_generator_exact_schemas", GENERATOR)
        parents = read_tsv(PARENT)
        manifest = json.loads(DISCOVERY.read_text(encoding="utf-8"))
        review = json.loads(DISCOVERY_REVIEW.read_text(encoding="utf-8"))
        observations = json.loads(OBSERVATIONS.read_text(encoding="utf-8"))
        manifest_mutations = []
        changed = json.loads(json.dumps(manifest)); changed["unknown_top"] = "fixture"; manifest_mutations.append(changed)
        changed = json.loads(json.dumps(manifest)); changed["sources"][0]["unknown_source"] = "fixture"; manifest_mutations.append(changed)
        changed = json.loads(json.dumps(manifest)); changed["sources"][0]["declarations"][0]["unknown_declaration"] = "fixture"; manifest_mutations.append(changed)
        for changed in manifest_mutations:
            with self.assertRaisesRegex(SystemExit, "schema"):
                collector.validate_manifest(changed, parents)

        review_mutations = []
        changed = json.loads(json.dumps(review)); changed["unknown_top"] = "fixture"; review_mutations.append(changed)
        changed = json.loads(json.dumps(review)); changed["source_revisions"]["unknown_source"] = review["source_revisions"][next(iter(review["source_revisions"]))]; review_mutations.append(changed)
        for changed in review_mutations:
            with self.assertRaisesRegex(SystemExit, "schema"):
                collector.validate_review(changed, manifest, observations["source_revisions"], candidate=True)

        observation_mutations = []
        changed = json.loads(json.dumps(observations)); changed["unknown_top"] = "fixture"; observation_mutations.append(changed)
        for map_name, invalid_key in (
            ("source_revisions", "unknown_source"),
            ("loop_revisions", "unknown_loop"),
            ("definition_links", "unknown_loop"),
            ("declaration_links", "unknown_loop"),
            ("category_defaults", "unknown_category"),
            ("objects", "unknown_object"),
        ):
            changed = json.loads(json.dumps(observations))
            exemplar = next(iter(changed[map_name].values()))
            changed[map_name][invalid_key] = exemplar
            observation_mutations.append(changed)
        changed = json.loads(json.dumps(observations))
        object_id = next(iter(changed["objects"]))
        changed["objects"][object_id]["unknown_object_field"] = "fixture"
        observation_mutations.append(changed)
        for changed in observation_mutations:
            with self.assertRaisesRegex(SystemExit, "schema"):
                collector.validate_observations_schema(changed)

    def test_no_raw_parent_inventory_id_occurs_in_any_todo3_artifact(self) -> None:
        parents = read_tsv(PARENT)
        artifacts = [DISCOVERY, DISCOVERY_REVIEW, OBSERVATIONS, OBJECTS, TRACKED, DOCUMENTATION]
        for artifact in artifacts:
            self.assertTrue(artifact.is_file(), artifact.name)
            content = artifact.read_text(encoding="utf-8")
            for parent in parents:
                with self.subTest(artifact=artifact.name, parent=parent["inventory_id"]):
                    self.assertNotIn(parent["inventory_id"], content)

    def test_required_implementation_and_artifact_files_exist(self) -> None:
        for path in (COLLECTOR, GENERATOR, DISCOVERY, DISCOVERY_REVIEW, OBSERVATIONS, OBJECTS, TRACKED, DOCUMENTATION):
            with self.subTest(path=path.name):
                self.assertTrue(path.is_file())

    def test_tracked_inventory_has_exact_parent_coverage_and_current_schema(self) -> None:
        generator = load_module("state_artifact_generator_schema", GENERATOR)
        parents = read_tsv(PARENT)
        manifest = json.loads(DISCOVERY.read_text(encoding="utf-8"))
        review = json.loads(DISCOVERY_REVIEW.read_text(encoding="utf-8"))
        observations = json.loads(OBSERVATIONS.read_text(encoding="utf-8"))
        tracked_objects = json.loads(OBJECTS.read_text(encoding="utf-8"))["objects"]
        rows = read_tsv(TRACKED)
        self.assertEqual(list(generator.EDGE_FIELDS), list(rows[0]))
        self.assertEqual(330, len(parents))
        self.assertEqual(
            {generator.loop_ref(row) for row in parents},
            {row["loop_ref"] for row in rows},
        )
        self.assertGreater(len(rows), len(parents))
        objects, expected_rows = generator.build_inventory(
            parents, manifest, observations, review
        )
        self.assertEqual(tracked_objects, objects)
        self.assertEqual(rows, expected_rows)
        generator.validate_inventory(
            objects, rows, parents, manifest, observations, review, candidate=False
        )

    def test_live_inventory_distinguishes_all_required_statuses(self) -> None:
        objects = json.loads(OBJECTS.read_text(encoding="utf-8"))["objects"]
        self.assertEqual({"observed", "unverified"}, {item["artifact_status"] for item in objects})

    def test_rows_have_safe_locator_size_retention_ssot_and_revision_evidence(self) -> None:
        generator = load_module("state_artifact_generator_fields", GENERATOR)
        objects = json.loads(OBJECTS.read_text(encoding="utf-8"))["objects"]
        for item in objects:
            with self.subTest(object=item["artifact_object_id"]):
                self.assertNotIn("/Users/", "\t".join(item.values()))
                self.assertRegex(item["artifact_object_id"], generator.OBJECT_ID_PATTERN)
                self.assertTrue(
                    item["size_bytes"].isdigit()
                    or item["size_bytes"] in {"unknown", "not_applicable"}
                )
                self.assertIn(
                    item["retention_classification"],
                    {"durable_until_reconfigured", "version_controlled", "unknown", "not_applicable"},
                )
                self.assertIn(
                    item["ssot_classification"],
                    {"local_runtime_primary", "repository_primary", "cloud_primary", "unverified"},
                )
                self.assertRegex(item["observation_digest"], generator.DIGEST_PATTERN)
                generator.validate_evidence_coupling(item)

    def test_generator_preserves_one_parent_to_many_artifact_edges_deterministically(self) -> None:
        generator = load_module("state_artifact_generator_many", GENERATOR)
        parents = read_tsv(PARENT)
        manifest = json.loads(DISCOVERY.read_text(encoding="utf-8"))
        review = json.loads(DISCOVERY_REVIEW.read_text(encoding="utf-8"))
        observations = json.loads(OBSERVATIONS.read_text(encoding="utf-8"))
        first = generator.build_inventory(parents, manifest, observations, review)
        second = generator.build_inventory(parents, manifest, observations, review)
        self.assertEqual(first, second)
        _, edges = first
        counts = Counter(row["loop_ref"] for row in edges)
        self.assertTrue(all(value == 7 for value in counts.values()))
        self.assertEqual(len(edges), len({row["artifact_edge_id"] for row in edges}))

    def test_parent_revision_mismatch_and_raw_home_path_fail_closed(self) -> None:
        generator = load_module("state_artifact_generator_fail_closed", GENERATOR)
        parents = read_tsv(PARENT)
        manifest = json.loads(DISCOVERY.read_text(encoding="utf-8"))
        review = json.loads(DISCOVERY_REVIEW.read_text(encoding="utf-8"))
        observations = json.loads(OBSERVATIONS.read_text(encoding="utf-8"))
        mutated = json.loads(json.dumps(observations))
        mutated["parent_inventory_digest"] = "sha256:" + ":".join(["0" * 8] * 8)
        with self.assertRaisesRegex(SystemExit, "parent inventory revision mismatch"):
            generator.build_inventory(parents, manifest, mutated, review)
        objects, edges = generator.build_inventory(parents, manifest, observations, review)
        objects[0]["path_class"] = "/Users/private/state.json"
        with self.assertRaisesRegex(SystemExit, "unsafe artifact field"):
            generator.validate_inventory(objects, edges, parents, manifest, observations, review, candidate=False)
        objects, edges = generator.build_inventory(parents, manifest, observations, review)
        objects[0]["ssot_evidence_locator"] = "STATE_TOKEN=fixture-value"
        with self.assertRaises(SystemExit):
            generator.validate_inventory(objects, edges, parents, manifest, observations, review, candidate=False)

    def test_collector_reads_only_parent_tsv_and_uses_stat_metadata(self) -> None:
        source = COLLECTOR.read_text(encoding="utf-8")
        tree = ast.parse(source)
        forbidden = {
            node.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute)
            and node.attr in {"read_text", "read_bytes", "readlines"}
        }
        self.assertEqual(set(), forbidden)
        self.assertNotIn("os.environ", source)
        self.assertNotIn("subprocess", source)
        self.assertIn("lstat", source)

    def test_todo3_artifacts_are_secret_clean_and_opaque_fixture_is_detected(self) -> None:
        config = REPO / ".gitleaks-cloud-agent-state-artifact.toml"
        for source in (DISCOVERY, DISCOVERY_REVIEW, OBSERVATIONS, OBJECTS, TRACKED, DOCUMENTATION):
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
                hashlib.sha256(b"todo3 opaque high entropy regression").digest()
            ).decode().rstrip("=")
            fixture.write_text(material + "\n", encoding="utf-8")
            detected = subprocess.run(
                ["gitleaks", "detect", "--no-git", "--redact", "--config", str(config), "--source", str(fixture)],
                capture_output=True,
                text=True,
            )
        self.assertNotEqual(0, detected.returncode)

    def test_reviewed_discovery_manifest_and_object_inventory_exist(self) -> None:
        self.assertTrue(DISCOVERY.is_file())
        self.assertTrue(OBJECTS.is_file())

    def test_known_real_loops_have_definition_cache_and_media_edges(self) -> None:
        generator = load_module("state_artifact_generator_known_loops", GENERATOR)
        rows = read_tsv(TRACKED)
        objects = json.loads(OBJECTS.read_text(encoding="utf-8"))["objects"]
        by_id = {item["artifact_object_id"]: item for item in objects}
        parent_ids = {
            "openclaw:comedy-tiktok-cross-post-daily-1778242512055",
            "openclaw:opening-cafe-cross-post-daily-1778035787000",
        }
        parents = read_tsv(PARENT)
        loop_refs = {
            generator.loop_ref(parent)
            for parent in parents
            if parent["inventory_id"] in parent_ids
        }
        for reference in loop_refs:
            edges = [row for row in rows if row["loop_ref"] == reference]
            classes = {by_id[row["artifact_object_id"]]["path_class"] for row in edges}
            self.assertIn("scheduler:shared_definition_container", classes)
            self.assertIn("state:processed_identifier_cache", classes)
            self.assertIn("media:remote_input_pattern", classes)

    def test_openclaw_shared_container_is_one_object_not_222_sizes(self) -> None:
        rows = read_tsv(TRACKED)
        objects = json.loads(OBJECTS.read_text(encoding="utf-8"))["objects"]
        shared = [
            item for item in objects
            if item["path_class"] == "scheduler:shared_definition_container"
        ]
        self.assertEqual(1, len(shared))
        self.assertEqual("shared_container", shared[0]["size_scope"])
        references = [
            row for row in rows if row["artifact_object_id"] == shared[0]["artifact_object_id"]
        ]
        self.assertEqual(222, len(references))
        self.assertEqual(1, len({row["artifact_object_id"] for row in references}))

    def test_manifest_binds_parent_and_secure_source_revisions(self) -> None:
        generator = load_module("state_artifact_generator_manifest", GENERATOR)
        parents = read_tsv(PARENT)
        manifest = json.loads(DISCOVERY.read_text(encoding="utf-8"))
        review = json.loads(DISCOVERY_REVIEW.read_text(encoding="utf-8"))
        observations = json.loads(OBSERVATIONS.read_text(encoding="utf-8"))
        self.assertRegex(manifest["parent_inventory_digest"], generator.DIGEST_PATTERN)
        self.assertGreaterEqual(len(manifest["sources"]), 3)
        for source in manifest["sources"]:
            self.assertRegex(source["source_revision_digest"], generator.DIGEST_PATTERN)
        mutated = json.loads(json.dumps(observations))
        source_id = next(iter(mutated["source_revisions"]))
        mutated["source_revisions"][source_id] = "sha256:" + ":".join(["0" * 8] * 8)
        with self.assertRaisesRegex(SystemExit, "source revision mismatch"):
            generator.build_inventory(parents, manifest, mutated, review)
        stale_manifest = json.loads(json.dumps(manifest))
        stale_source = stale_manifest["sources"][0]
        stale_source["source_revision_digest"] = "sha256:" + ":".join(["0" * 8] * 8)
        stale_observations = json.loads(json.dumps(observations))
        stale_observations["discovery_manifest_digest"] = generator.canonical_digest(stale_manifest)
        stale_observations["source_revisions"][stale_source["source_id"]] = stale_source[
            "source_revision_digest"
        ]
        with self.assertRaisesRegex(SystemExit, "source revision mismatch"):
            generator.build_inventory(
                parents, stale_manifest, stale_observations, review
            )

    def test_static_source_declarations_require_literal_or_symbol_evidence(self) -> None:
        collector = load_module("state_artifact_collector_static_analysis", COLLECTOR)
        manifest = json.loads(DISCOVERY.read_text(encoding="utf-8"))
        manifest["sources"][0]["declarations"][0]["evidence_literals"] = [
            "artifact-name-not-present-in-reviewed-source"
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            candidate = Path(temp_dir) / "manifest.json"
            candidate.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(SystemExit, "source literal evidence mismatch"):
                collector.collect(PARENT, candidate, DISCOVERY_REVIEW, candidate=True)

    def test_retention_and_ssot_require_independent_evidence_coupling(self) -> None:
        generator = load_module("state_artifact_generator_evidence", GENERATOR)
        parents = read_tsv(PARENT)
        manifest = json.loads(DISCOVERY.read_text(encoding="utf-8"))
        review = json.loads(DISCOVERY_REVIEW.read_text(encoding="utf-8"))
        observations = json.loads(OBSERVATIONS.read_text(encoding="utf-8"))
        objects, edges = generator.build_inventory(
            parents, manifest, observations, review
        )
        changed = json.loads(json.dumps(objects))
        changed[0]["retention_classification"] = "version_controlled"
        changed[0]["retention_evidence_kind"] = "unverified"
        changed[0]["retention_evidence_locator"] = "unverified"
        with self.assertRaisesRegex(SystemExit, "retention evidence coupling"):
            generator.validate_inventory(
                changed, edges, parents, manifest, observations, review, candidate=False
            )
        changed = json.loads(json.dumps(objects))
        changed[0]["ssot_classification"] = "repository_primary"
        changed[0]["ssot_evidence_kind"] = "unverified"
        changed[0]["ssot_evidence_locator"] = "unverified"
        with self.assertRaisesRegex(SystemExit, "SSOT evidence coupling"):
            generator.validate_inventory(
                changed, edges, parents, manifest, observations, review, candidate=False
            )

    def test_artifact_object_fields_reject_identifiers_paths_controls_and_entropy(self) -> None:
        generator = load_module("state_artifact_generator_privacy", GENERATOR)
        parents = read_tsv(PARENT)
        manifest = json.loads(DISCOVERY.read_text(encoding="utf-8"))
        review = json.loads(DISCOVERY_REVIEW.read_text(encoding="utf-8"))
        observations = json.loads(OBSERVATIONS.read_text(encoding="utf-8"))
        objects, edges = generator.build_inventory(
            parents, manifest, observations, review
        )
        forbidden = (
            "Daisuke134",
            "comedy-tiktok-cross-post-daily-1778242512055",
            "account_id:personal-handle",
            "person@example.com",
            "/Users/private/state.json",
            "/var/private/state.json",
            "~/private/state.json",
            "C:\\Users\\private\\state.json",
            "\\\\server\\share\\state.json",
            "$HOME/private/state.json",
            "${HOME}/private/state.json",
            "%USERPROFILE%\\private\\state.json",
            "file:///private/state.json",
            "../private/state.json",
            "TOKEN=fixture",
            "line\nbreak",
            base64.urlsafe_b64encode(hashlib.sha256(b"object locator entropy").digest()).decode(),
        )
        for value in forbidden:
            changed = json.loads(json.dumps(objects))
            changed[0]["path_class"] = value
            with self.subTest(value=value):
                with self.assertRaises(SystemExit):
                    generator.validate_inventory(
                        changed, edges, parents, manifest, observations, review, candidate=False
                    )


if __name__ == "__main__":
    unittest.main()
