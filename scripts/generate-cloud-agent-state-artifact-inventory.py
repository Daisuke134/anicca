#!/usr/bin/env python3
"""Generate fail-closed artifact-object and loop-to-object edge inventories."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import re
import sys
from collections import Counter
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
DEFAULT_PARENT = REPO / "docs/reference/cloud-agent-loop-inventory.tsv"
DEFAULT_DISCOVERY = REPO / "docs/reference/cloud-agent-state-artifact-discovery-manifest.json"
DEFAULT_REVIEW = REPO / "docs/reference/cloud-agent-state-artifact-discovery-review.json"
DEFAULT_OBSERVATIONS = REPO / "docs/reference/cloud-agent-state-artifact-observations.json"
DEFAULT_OBJECTS = REPO / "docs/reference/cloud-agent-state-artifact-objects.json"
DEFAULT_OUTPUT = REPO / "docs/reference/cloud-agent-state-artifact-inventory.tsv"

EDGE_FIELDS = (
    "artifact_edge_id",
    "loop_ref",
    "artifact_object_id",
    "artifact_role",
    "artifact_category",
    "coverage_resolution",
    "coverage_evidence_kind",
    "coverage_evidence_locator",
    "review_mode",
    "parent_metadata_digest",
    "discovery_manifest_digest",
)
FIELDS = EDGE_FIELDS
OBJECT_FIELDS = (
    "artifact_object_id",
    "artifact_category",
    "artifact_kind",
    "path_class",
    "artifact_status",
    "size_bytes",
    "size_scope",
    "size_evidence",
    "retention_classification",
    "retention_evidence_kind",
    "retention_evidence_locator",
    "ssot_classification",
    "ssot_evidence_kind",
    "ssot_evidence_locator",
    "source_revision_digest",
    "discovery_evidence_kind",
    "discovery_evidence_locator",
    "observation_digest",
)
OBSERVED_OBJECT_FIELDS = frozenset(set(OBJECT_FIELDS) - {"observation_digest"})
DIGEST_PATTERN = re.compile(r"^sha256:(?:[0-9a-f]{8}:){7}[0-9a-f]{8}$")
OBJECT_ID_PATTERN = re.compile(r"^artifact-object-[0-9]{15}$")
LOOP_REF_PATTERN = re.compile(r"^loop-[0-9]{15}$")
REQUIRED_ARTIFACT_CATEGORIES = ("state", "log", "media", "transcript", "cache", "output")
CONTROL_PATTERN = re.compile(r"[\x00-\x1f\x7f]")
SECRET_ASSIGNMENT = re.compile(r"(?i)(?:key|token|secret|password)\s*=\s*\S+")
EMAIL_PATTERN = re.compile(r"(?i)[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}")
OPAQUE_ENTROPY = re.compile(r"(?<![A-Za-z0-9_-])[A-Za-z0-9_-]{40,}={0,2}(?![A-Za-z0-9_-])")
PERSONAL_OR_JOB = re.compile(
    r"(?i)(?:daisuke134|#job=|(?:comedy-tiktok|opening-cafe)-cross-post-daily-[0-9]+|"
    r"account(?:_id)?[:=][A-Za-z0-9._@+-]+|(?:job|cron)[_:=/-][A-Za-z0-9._-]*[0-9]{8,})"
)
PORTABLE_PATH = re.compile(
    r"(?i)(?:^|[\s=])(?:~/|/|\\\\|[A-Za-z]:[\\/]|file://|\$HOME(?:/|\\)|"
    r"\$\{HOME\}(?:/|\\)|%USERPROFILE%(?:/|\\)|\.\./)"
)


def canonical_digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    digest = hashlib.sha256(encoded).hexdigest()
    return "sha256:" + ":".join(digest[index:index + 8] for index in range(0, 64, 8))


def parent_metadata_digest(parent: dict[str, str]) -> str:
    return canonical_digest({key: parent[key] for key in sorted(parent)})


def loop_ref(parent: dict[str, str]) -> str:
    digest = hashlib.sha256(parent_metadata_digest(parent).encode()).hexdigest()
    return f"loop-{int(digest[:12], 16):015d}"


def read_parent(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    ids = [row.get("inventory_id", "") for row in rows]
    if not rows or not all(ids) or len(ids) != len(set(ids)):
        raise SystemExit("invalid parent inventory")
    return rows


def read_json(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise SystemExit("JSON input must be an object")
    return value


def load_collector_module():
    path = REPO / "scripts/collect-cloud-agent-state-artifact-metadata.py"
    spec = importlib.util.spec_from_file_location("state_artifact_secure_collector", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("state/artifact collector unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_manifest_and_revisions(
    parents: list[dict[str, str]],
    manifest: dict[str, object],
    observations: dict[str, object],
    review: dict[str, object],
    *,
    candidate: bool,
) -> str:
    collector = load_collector_module()
    sources = collector.validate_manifest(manifest, parents)
    collector.validate_review_schema(review)
    collector.validate_observations_schema(observations)
    collector.validate_private_structure(review, parents, "independent review artifact")
    collector.validate_private_structure(observations, parents, "state/artifact observations")
    if observations.get("schema_version") != 2:
        raise SystemExit("state/artifact observation schema mismatch")
    expected_parent = canonical_digest([parent_metadata_digest(parent) for parent in parents])
    if observations.get("parent_inventory_digest") != expected_parent:
        raise SystemExit("parent inventory revision mismatch")
    expected_manifest = canonical_digest(manifest)
    if observations.get("discovery_manifest_digest") != expected_manifest:
        raise SystemExit("discovery manifest revision mismatch")
    observed_revisions = observations.get("source_revisions")
    if not isinstance(observed_revisions, dict):
        raise SystemExit("source revisions missing")
    helpers = collector.load_todo2_helpers()
    for source in sources:
        source_id = source["source_id"]
        current = collector.secure_source_digest(
            collector.safe_repo_source(source["source_locator"]), helpers
        )
        reviewed = source["source_revision_digest"]
        observed = observed_revisions.get(source_id)
        if current != reviewed or observed != reviewed:
            raise SystemExit(f"{source_id}: source revision mismatch")
    review_mode = collector.validate_review(
        review, manifest, dict(observed_revisions), candidate=candidate
    )
    if observations.get("review_mode") != review_mode:
        raise SystemExit("observation review mode mismatch")
    expected_loop_revisions = {
        loop_ref(parent): parent_metadata_digest(parent) for parent in parents
    }
    if observations.get("loop_revisions") != dict(sorted(expected_loop_revisions.items())):
        raise SystemExit("opaque loop revision mismatch")
    serialized_inputs = json.dumps(
        {"manifest": manifest, "review": review, "observations": observations}, sort_keys=True
    )
    if any(parent["inventory_id"] in serialized_inputs for parent in parents):
        raise SystemExit("raw parent inventory id in TODO #3 input artifact")
    return review_mode


def artifact_edge_id(loop_reference: str, object_id: str, role: str, category: str) -> str:
    digest = hashlib.sha256(
        f"{loop_reference}\0{object_id}\0{role}\0{category}".encode()
    ).hexdigest()
    return f"artifact-edge-{int(digest[:12], 16):015d}"


def privacy_safe_field(field: str, value: str) -> bool:
    if CONTROL_PATTERN.search(value) or SECRET_ASSIGNMENT.search(value):
        return False
    if EMAIL_PATTERN.search(value) or PERSONAL_OR_JOB.search(value):
        return False
    if PORTABLE_PATH.search(value):
        return False
    if field not in {"source_revision_digest", "observation_digest"} and OPAQUE_ENTROPY.search(value):
        return False
    return True


def validate_evidence_coupling(item: dict[str, str]) -> None:
    retention = (
        item["retention_classification"],
        item["retention_evidence_kind"],
        item["retention_evidence_locator"],
    )
    allowed_retention = {
        ("unknown", "unverified", "unverified"),
        ("version_controlled", "source_control_policy", "policy:repository_tracked"),
        ("durable_until_reconfigured", "operational_policy", "policy:runtime_persistence"),
        ("not_applicable", "scope_declaration", "scope:non_local"),
    }
    if retention not in allowed_retention:
        raise SystemExit(f"{item['artifact_object_id']}: retention evidence coupling failure")
    ssot = (
        item["ssot_classification"],
        item["ssot_evidence_kind"],
        item["ssot_evidence_locator"],
    )
    allowed_ssot = {
        ("unverified", "unverified", "unverified"),
        ("repository_primary", "source_control_schema", "schema:repository_primary"),
        ("local_runtime_primary", "operational_policy", "policy:local_runtime_primary"),
        ("cloud_primary", "operational_policy", "policy:cloud_primary"),
    }
    if ssot not in allowed_ssot:
        raise SystemExit(f"{item['artifact_object_id']}: SSOT evidence coupling failure")


def build_inventory(
    parents: list[dict[str, str]],
    manifest: dict[str, object],
    observations: dict[str, object],
    review: dict[str, object] | None = None,
    *,
    candidate: bool = False,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    if review is None:
        raise SystemExit("independent review approval required")
    review_mode = validate_manifest_and_revisions(
        parents, manifest, observations, review, candidate=candidate
    )
    raw_objects = observations.get("objects")
    definition_links = observations.get("definition_links")
    declaration_links = observations.get("declaration_links")
    unbound = observations.get("unbound_discoveries")
    category_defaults = observations.get("category_defaults")
    if not isinstance(raw_objects, dict) or not isinstance(definition_links, dict):
        raise SystemExit("artifact object observations missing")
    if (
        not isinstance(declaration_links, dict)
        or not isinstance(unbound, list)
        or not isinstance(category_defaults, dict)
    ):
        raise SystemExit("artifact discovery links missing")
    loop_refs = {loop_ref(parent) for parent in parents}
    if set(definition_links) != loop_refs or not set(declaration_links) <= loop_refs:
        raise SystemExit("artifact parent link coverage mismatch")
    if set(category_defaults) != set(REQUIRED_ARTIFACT_CATEGORIES):
        raise SystemExit("required artifact category defaults mismatch")
    referenced = set(definition_links.values()) | set(unbound) | set(category_defaults.values())
    for values in declaration_links.values():
        if not isinstance(values, list):
            raise SystemExit("artifact declaration link invalid")
        referenced.update(values)
    if referenced != set(raw_objects):
        raise SystemExit("artifact object/link exact-match failure")

    objects: list[dict[str, str]] = []
    for object_id in sorted(raw_objects):
        raw = raw_objects[object_id]
        if not isinstance(raw, dict) or set(raw) != OBSERVED_OBJECT_FIELDS:
            raise SystemExit(f"{object_id}: artifact object fields mismatch")
        item = {field: str(raw[field]) for field in OBSERVED_OBJECT_FIELDS}
        if item["artifact_object_id"] != object_id:
            raise SystemExit(f"{object_id}: artifact object id mismatch")
        item["observation_digest"] = canonical_digest(item)
        objects.append({field: item[field] for field in OBJECT_FIELDS})

    by_loop_ref = {loop_ref(parent): parent for parent in parents}
    by_object = {item["artifact_object_id"]: item for item in objects}
    edges: list[dict[str, str]] = []
    manifest_digest = canonical_digest(manifest)
    for reference in sorted(loop_refs):
        parent = by_loop_ref[reference]
        parent_digest = parent_metadata_digest(parent)
        definition_id = definition_links[reference]
        edges.append(
            {
                "artifact_edge_id": artifact_edge_id(reference, definition_id, "definition", "definition"),
                "loop_ref": reference,
                "artifact_object_id": definition_id,
                "artifact_role": "definition",
                "artifact_category": "definition",
                "coverage_resolution": "discovered",
                "coverage_evidence_kind": "parent_metadata",
                "coverage_evidence_locator": "parent:definition_metadata",
                "review_mode": review_mode,
                "parent_metadata_digest": parent_digest,
                "discovery_manifest_digest": manifest_digest,
            }
        )
        discovered_by_category: dict[str, str] = {}
        for object_id in declaration_links.get(reference, []):
            category = by_object[object_id]["artifact_category"]
            if category in discovered_by_category:
                raise SystemExit(f"{reference}: duplicate discovered category")
            discovered_by_category[category] = object_id
        for category in REQUIRED_ARTIFACT_CATEGORIES:
            object_id = discovered_by_category.get(category, category_defaults[category])
            discovered = category in discovered_by_category
            edges.append(
                {
                    "artifact_edge_id": artifact_edge_id(
                        reference, object_id, "category_coverage", category
                    ),
                    "loop_ref": reference,
                    "artifact_object_id": object_id,
                    "artifact_role": "category_coverage",
                    "artifact_category": category,
                    "coverage_resolution": "discovered" if discovered else "unverified",
                    "coverage_evidence_kind": "reviewed_static_source" if discovered else "unverified",
                    "coverage_evidence_locator": (
                        by_object[object_id]["discovery_evidence_locator"] if discovered else "unverified"
                    ),
                    "review_mode": review_mode,
                    "parent_metadata_digest": parent_digest,
                    "discovery_manifest_digest": manifest_digest,
                }
            )
    edges.sort(key=lambda row: row["artifact_edge_id"])
    validate_inventory(
        objects,
        edges,
        parents,
        manifest,
        observations,
        review,
        candidate=candidate,
        rebuild=False,
    )
    return objects, edges


def validate_inventory(
    objects: list[dict[str, str]],
    edges: list[dict[str, str]],
    parents: list[dict[str, str]],
    manifest: dict[str, object],
    observations: dict[str, object],
    review: dict[str, object],
    *,
    candidate: bool,
    rebuild: bool = True,
) -> None:
    expected_loop_refs = {loop_ref(parent) for parent in parents}
    object_ids = {item.get("artifact_object_id", "") for item in objects}
    if len(object_ids) != len(objects) or not all(OBJECT_ID_PATTERN.fullmatch(value) for value in object_ids):
        raise SystemExit("duplicate or invalid artifact object id")
    for item in objects:
        if set(item) != set(OBJECT_FIELDS) or any(item[field] == "" for field in OBJECT_FIELDS):
            raise SystemExit("artifact object schema mismatch")
        if item["artifact_status"] not in {"observed", "unverified", "none_observed", "inactive"}:
            raise SystemExit(f"{item['artifact_object_id']}: invalid artifact status")
        if item["artifact_category"] not in {*REQUIRED_ARTIFACT_CATEGORIES, "definition"}:
            raise SystemExit(f"{item['artifact_object_id']}: invalid artifact category")
        if item["size_scope"] not in {"shared_container", "object", "unknown"}:
            raise SystemExit(f"{item['artifact_object_id']}: invalid size scope")
        if not (item["size_bytes"].isdigit() or item["size_bytes"] in {"unknown", "not_applicable"}):
            raise SystemExit(f"{item['artifact_object_id']}: invalid size")
        if item["artifact_status"] == "observed" and not item["size_bytes"].isdigit():
            raise SystemExit(f"{item['artifact_object_id']}: observed object requires numeric size")
        if item["size_scope"] == "shared_container" and item["path_class"] != "scheduler:shared_definition_container":
            raise SystemExit(f"{item['artifact_object_id']}: invalid shared-container scope")
        if not DIGEST_PATTERN.fullmatch(item["observation_digest"]):
            raise SystemExit(f"{item['artifact_object_id']}: invalid observation digest")
        if item["source_revision_digest"] != "unverified" and not DIGEST_PATTERN.fullmatch(
            item["source_revision_digest"]
        ):
            raise SystemExit(f"{item['artifact_object_id']}: invalid source revision digest")
        validate_evidence_coupling(item)
        for field, value in item.items():
            if not privacy_safe_field(field, value):
                raise SystemExit(f"{item['artifact_object_id']}: unsafe artifact field {field}")

    covered = {edge.get("loop_ref", "") for edge in edges}
    if covered != expected_loop_refs or not all(LOOP_REF_PATTERN.fullmatch(value) for value in covered):
        raise SystemExit("artifact edge parent coverage mismatch")
    edge_ids = [edge.get("artifact_edge_id", "") for edge in edges]
    if len(edge_ids) != len(set(edge_ids)):
        raise SystemExit("duplicate artifact edge id")
    for edge in edges:
        if set(edge) != set(EDGE_FIELDS) or any(edge[field] == "" for field in EDGE_FIELDS):
            raise SystemExit("artifact edge schema mismatch")
        if edge["artifact_object_id"] not in object_ids:
            raise SystemExit("artifact edge references unknown object")
        if not DIGEST_PATTERN.fullmatch(edge["parent_metadata_digest"]):
            raise SystemExit("artifact edge parent digest invalid")
        if not DIGEST_PATTERN.fullmatch(edge["discovery_manifest_digest"]):
            raise SystemExit("artifact edge manifest digest invalid")
        if edge["review_mode"] not in {"candidate_review_required", "independent_review_approved"}:
            raise SystemExit("artifact edge review mode invalid")
        if edge["artifact_role"] == "definition":
            if (
                edge["artifact_category"] != "definition"
                or edge["coverage_resolution"] != "discovered"
                or edge["coverage_evidence_kind"] != "parent_metadata"
                or edge["coverage_evidence_locator"] != "parent:definition_metadata"
            ):
                raise SystemExit("definition edge cannot satisfy category coverage")
        elif edge["artifact_role"] == "category_coverage":
            resolution = edge["coverage_resolution"]
            if edge["artifact_category"] not in REQUIRED_ARTIFACT_CATEGORIES:
                raise SystemExit("invalid required artifact category")
            if resolution == "unverified" and (
                edge["coverage_evidence_kind"], edge["coverage_evidence_locator"]
            ) != ("unverified", "unverified"):
                raise SystemExit("unverified category evidence mismatch")
            if resolution == "discovered" and edge["coverage_evidence_kind"] != "reviewed_static_source":
                raise SystemExit("discovered category evidence mismatch")
            if resolution == "none_observed" and edge["coverage_evidence_kind"] not in {
                "operational_policy", "source_schema"
            }:
                raise SystemExit("none-observed category requires evidence")
            if resolution not in {"discovered", "none_observed", "unverified"}:
                raise SystemExit("invalid category coverage resolution")
        else:
            raise SystemExit("invalid artifact edge role")
        for field, value in edge.items():
            if not privacy_safe_field(field, edge[field]):
                raise SystemExit(f"{edge['artifact_edge_id']}: unsafe artifact edge field {field}")
    coverage = [edge for edge in edges if edge["artifact_role"] == "category_coverage"]
    pairs = [(edge["loop_ref"], edge["artifact_category"]) for edge in coverage]
    expected_pairs = {
        (reference, category)
        for reference in expected_loop_refs
        for category in REQUIRED_ARTIFACT_CATEGORIES
    }
    if len(pairs) != len(expected_pairs) or len(pairs) != len(set(pairs)) or set(pairs) != expected_pairs:
        raise SystemExit("required artifact category coverage matrix mismatch")
    definitions = [edge for edge in edges if edge["artifact_role"] == "definition"]
    if len(definitions) != len(expected_loop_refs) or {
        edge["loop_ref"] for edge in definitions
    } != expected_loop_refs:
        raise SystemExit("definition edge exact coverage mismatch")
    shared = [item for item in objects if item["path_class"] == "scheduler:shared_definition_container"]
    if len(shared) != 1:
        raise SystemExit("shared scheduler container must be one object")
    shared_refs = [edge for edge in edges if edge["artifact_object_id"] == shared[0]["artifact_object_id"]]
    openclaw_count = sum(parent["source_type"] == "openclaw_cron" for parent in parents)
    if len(shared_refs) != openclaw_count:
        raise SystemExit("shared scheduler container accounting mismatch")
    if rebuild:
        expected_objects, expected_edges = build_inventory(
            parents, manifest, observations, review, candidate=candidate
        )
        if objects != expected_objects or edges != expected_edges:
            raise SystemExit("artifact inventory does not match bound observations")
    serialized = json.dumps({"objects": objects, "edges": edges}, sort_keys=True)
    if any(parent["inventory_id"] in serialized for parent in parents):
        raise SystemExit("raw parent inventory id in generated TODO #3 artifacts")


def render_tsv(rows: list[dict[str, str]]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=EDGE_FIELDS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def render_objects(
    objects: list[dict[str, str]],
    manifest: dict[str, object],
    observations: dict[str, object],
    review: dict[str, object],
) -> str:
    payload = {
        "schema_version": 2,
        "parent_inventory_digest": observations["parent_inventory_digest"],
        "discovery_manifest_digest": canonical_digest(manifest),
        "independent_review_digest": canonical_digest(review),
        "review_mode": observations["review_mode"],
        "objects": objects,
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parent", type=Path, default=DEFAULT_PARENT)
    parser.add_argument("--discovery", type=Path, default=DEFAULT_DISCOVERY)
    parser.add_argument("--review", type=Path, default=DEFAULT_REVIEW)
    parser.add_argument("--observations", type=Path, default=DEFAULT_OBSERVATIONS)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--objects-output", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--candidate", action="store_true")
    args = parser.parse_args()
    parents = read_parent(args.parent)
    manifest = read_json(args.discovery)
    review = read_json(args.review)
    observations = read_json(args.observations)
    objects, edges = build_inventory(
        parents, manifest, observations, review, candidate=args.candidate
    )
    rendered_edges = render_tsv(edges)
    rendered_objects = render_objects(objects, manifest, observations, review)
    if args.output:
        args.output.write_text(rendered_edges, encoding="utf-8")
    else:
        print(rendered_edges, end="")
    if args.objects_output:
        args.objects_output.write_text(rendered_objects, encoding="utf-8")
    if args.check:
        print(
            json.dumps(
                {
                    "parents": len(parents),
                    "edges": len(edges),
                    "objects": len(objects),
                    "unbound_objects": len(observations["unbound_discoveries"]),
                    "review_mode": observations["review_mode"],
                    "category_coverage_edges": sum(
                        item["artifact_role"] == "category_coverage" for item in edges
                    ),
                    "definition_edges": sum(
                        item["artifact_role"] == "definition" for item in edges
                    ),
                    "by_resolution": dict(
                        sorted(Counter(item["coverage_resolution"] for item in edges).items())
                    ),
                    "by_status": dict(sorted(Counter(item["artifact_status"] for item in objects).items())),
                    "shared_container_objects": sum(
                        item["path_class"] == "scheduler:shared_definition_container"
                        for item in objects
                    ),
                    "shared_container_edges": sum(
                        item["artifact_object_id"] == next(
                            candidate["artifact_object_id"] for candidate in objects
                            if candidate["path_class"] == "scheduler:shared_definition_container"
                        )
                        for item in edges
                    ),
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
