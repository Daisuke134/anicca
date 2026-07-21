#!/usr/bin/env python3
"""Generate fail-closed external-effect objects and opaque loop edges for TODO #4."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import re
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
DEFAULT_PARENT = REPO / "docs/reference/cloud-agent-loop-inventory.tsv"
DEFAULT_MANIFEST = REPO / "docs/reference/cloud-agent-external-effect-discovery-manifest.json"
DEFAULT_REVIEW = REPO / "docs/reference/cloud-agent-external-effect-discovery-review.json"
DEFAULT_OBSERVATIONS = REPO / "docs/reference/cloud-agent-external-effect-observations.json"
DEFAULT_OBJECTS = REPO / "docs/reference/cloud-agent-external-effect-objects.json"
DEFAULT_OUTPUT = REPO / "docs/reference/cloud-agent-external-effect-inventory.tsv"
REQUIRED_EFFECT_CATEGORIES = ("call", "post", "mail", "render", "wallet")
EDGE_FIELDS = (
    "effect_edge_id", "loop_ref", "effect_object_id", "effect_role", "effect_category",
    "coverage_resolution", "policy_status", "evidence_kind", "evidence_locator", "review_mode",
    "parent_metadata_digest", "discovery_manifest_digest",
)
OBJECT_FIELDS = (
    "effect_object_id", "effect_category", "effect_kind", "provider_class", "target_class",
    "action_class", "direction", "provider_tool_ref", "mutability", "financial_risk",
    "idempotency", "approval_gate", "execution_policy", "discovery_status",
    "source_revision_digest", "evidence_kind", "evidence_locator", "observation_digest",
)
DIGEST_PATTERN = re.compile(r"^sha256:(?:[0-9a-f]{8}:){7}[0-9a-f]{8}$")
OBJECT_ID_PATTERN = re.compile(r"^effect-object-[0-9]{15}$")
LOOP_REF_PATTERN = re.compile(r"^loop-[0-9]{15}$")
EDGE_ID_PATTERN = re.compile(r"^effect-edge-[0-9]{15}$")


def canonical_digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    raw = hashlib.sha256(encoded).hexdigest()
    return "sha256:" + ":".join(raw[index:index + 8] for index in range(0, 64, 8))


def parent_metadata_digest(parent: dict[str, str]) -> str:
    return canonical_digest({key: parent[key] for key in sorted(parent)})


def loop_ref(parent: dict[str, str]) -> str:
    raw = hashlib.sha256(parent_metadata_digest(parent).encode()).hexdigest()
    return f"loop-{int(raw[:12], 16):015d}"


def opaque_id(prefix: str, material: str) -> str:
    raw = hashlib.sha256(material.encode()).hexdigest()
    return f"{prefix}-{int(raw[:12], 16):015d}"


def effect_edge_id(loop_reference: str, object_id: str, role: str, category: str) -> str:
    return opaque_id("effect-edge", f"{loop_reference}\0{object_id}\0{role}\0{category}")


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
    path = REPO / "scripts/collect-cloud-agent-external-effect-metadata.py"
    spec = importlib.util.spec_from_file_location("external_effect_secure_collector", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("external-effect collector unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def declaration_map(manifest: dict[str, object]) -> dict[str, dict[str, object]]:
    return {
        str(declaration["effect_key"]): declaration
        for source in manifest["sources"]
        for declaration in source["declarations"]
    }


def validate_revisions(
    parents: list[dict[str, str]], manifest: dict[str, object], observations: dict[str, object],
    review: dict[str, object], *, candidate: bool,
) -> str:
    collector = load_collector_module()
    sources = collector.validate_manifest(manifest, parents)
    collector.validate_observations_schema(observations)
    collector.validate_private_structure(review, parents, "external-effect review")
    collector.validate_private_structure(observations, parents, "external-effect observations")
    expected_parent = canonical_digest([parent_metadata_digest(parent) for parent in parents])
    if observations.get("parent_inventory_digest") != expected_parent:
        raise SystemExit("parent inventory revision mismatch")
    if observations.get("discovery_manifest_digest") != canonical_digest(manifest):
        raise SystemExit("discovery manifest revision mismatch")
    expected_loops = dict(sorted((loop_ref(parent), parent_metadata_digest(parent)) for parent in parents))
    if observations.get("loop_revisions") != expected_loops:
        raise SystemExit("opaque loop revision mismatch")
    observed_revisions = observations.get("source_revisions")
    helpers = collector.load_todo2_helpers()
    for source in sources:
        current, _ = collector.secure_source_analysis(str(source["source_locator"]), helpers)
        source_id = str(source["source_id"])
        reviewed = str(source["source_revision_digest"])
        if current != reviewed or observed_revisions.get(source_id) != reviewed:
            raise SystemExit(f"{source_id}: source revision mismatch")
    review_mode = collector.validate_review(review, manifest, dict(observed_revisions), candidate=candidate)
    if observations.get("review_mode") != review_mode:
        raise SystemExit("external-effect observation review mode mismatch")
    return review_mode


def build_inventory(
    parents: list[dict[str, str]], manifest: dict[str, object], observations: dict[str, object],
    review: dict[str, object], *, candidate: bool,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    review_mode = validate_revisions(parents, manifest, observations, review, candidate=candidate)
    observed = observations["objects"]
    objects: list[dict[str, str]] = []
    for object_id in sorted(observed):
        record = dict(observed[object_id])
        record["observation_digest"] = canonical_digest(record)
        objects.append(record)
    by_id = {item["effect_object_id"]: item for item in objects}
    defaults = {
        item["effect_category"]: item["effect_object_id"]
        for item in objects if item["effect_kind"] == "category_unverified"
    }
    declarations = declaration_map(manifest)
    bindings: dict[tuple[str, str], list[str]] = {}
    for effect_key, declaration in declarations.items():
        object_id = opaque_id("effect-object", effect_key)
        for reference in declaration["loop_refs"]:
            bindings.setdefault((reference, str(declaration["effect_category"])), []).append(object_id)
    edges: list[dict[str, str]] = []
    manifest_digest = canonical_digest(manifest)

    def append_edge(reference: str, object_id: str, role: str, category: str, resolution: str) -> None:
        item = by_id[object_id]
        policy = {"allowed": "allowed", "blocked": "policy_violation", "unverified": "unverified"}[
            item["execution_policy"]
        ]
        edges.append({
            "effect_edge_id": effect_edge_id(reference, object_id, role, category),
            "loop_ref": reference,
            "effect_object_id": object_id,
            "effect_role": role,
            "effect_category": category,
            "coverage_resolution": resolution,
            "policy_status": policy,
            "evidence_kind": item["evidence_kind"] if resolution == "discovered" else "unverified",
            "evidence_locator": item["evidence_locator"] if resolution == "discovered" else "unverified",
            "review_mode": review_mode,
            "parent_metadata_digest": observations["loop_revisions"][reference],
            "discovery_manifest_digest": manifest_digest,
        })

    for parent in parents:
        reference = loop_ref(parent)
        for category in REQUIRED_EFFECT_CATEGORIES:
            bound = sorted(bindings.get((reference, category), []))
            object_id = bound[0] if bound else defaults[category]
            append_edge(reference, object_id, "category_coverage", category, "discovered" if bound else "unverified")
        for category in REQUIRED_EFFECT_CATEGORIES:
            for object_id in sorted(bindings.get((reference, category), [])):
                append_edge(reference, object_id, "effect_binding", category, "discovered")
    edges.sort(key=lambda row: (row["loop_ref"], row["effect_role"], row["effect_category"], row["effect_object_id"]))
    validate_inventory(objects, edges, parents, manifest, observations, review, candidate=candidate)
    return objects, edges


def validate_inventory(
    objects: list[dict[str, str]], edges: list[dict[str, str]], parents: list[dict[str, str]],
    manifest: dict[str, object], observations: dict[str, object], review: dict[str, object], *, candidate: bool,
) -> None:
    collector = load_collector_module()
    review_mode = validate_revisions(parents, manifest, observations, review, candidate=candidate)
    known_refs = {loop_ref(parent) for parent in parents}
    object_ids: set[str] = set()
    for item in objects:
        if set(item) != set(OBJECT_FIELDS):
            raise SystemExit("external-effect object schema mismatch")
        object_id = item["effect_object_id"]
        if not OBJECT_ID_PATTERN.fullmatch(object_id) or object_id in object_ids:
            raise SystemExit("external-effect object identity mismatch")
        if item["effect_category"] not in REQUIRED_EFFECT_CATEGORIES:
            raise SystemExit("external-effect object category mismatch")
        if item["execution_policy"] not in {"allowed", "blocked", "unverified"}:
            raise SystemExit("external-effect object policy mismatch")
        if item["provider_tool_ref"] != "unverified" and re.fullmatch(r"tool-ref-[0-9]{15}", item["provider_tool_ref"]) is None:
            raise SystemExit("external-effect provider tool reference mismatch")
        if item["effect_category"] == "wallet" and item["execution_policy"] == "allowed":
            raise SystemExit("wallet mutation policy violation")
        if not DIGEST_PATTERN.fullmatch(item["observation_digest"]):
            raise SystemExit("external-effect observation digest mismatch")
        object_ids.add(object_id)
    edge_ids: set[str] = set()
    for row in edges:
        if set(row) != set(EDGE_FIELDS):
            raise SystemExit("external-effect edge schema mismatch")
        if not EDGE_ID_PATTERN.fullmatch(row["effect_edge_id"]) or row["effect_edge_id"] in edge_ids:
            raise SystemExit("external-effect edge identity mismatch")
        if row["loop_ref"] not in known_refs or row["effect_object_id"] not in object_ids:
            raise SystemExit("external-effect edge reference mismatch")
        if row["review_mode"] != review_mode:
            raise SystemExit("external-effect edge review mismatch")
        if row["coverage_resolution"] not in {"discovered", "none", "unverified"}:
            raise SystemExit("external-effect resolution mismatch")
        if row["effect_category"] == "wallet" and row["policy_status"] == "allowed":
            raise SystemExit("wallet edge policy violation")
        edge_ids.add(row["effect_edge_id"])
    coverage = [row for row in edges if row["effect_role"] == "category_coverage"]
    expected_pairs = {(reference, category) for reference in known_refs for category in REQUIRED_EFFECT_CATEGORIES}
    actual_pairs = {(row["loop_ref"], row["effect_category"]) for row in coverage}
    if len(coverage) != len(expected_pairs) or actual_pairs != expected_pairs:
        raise SystemExit("external-effect coverage matrix mismatch")
    collector.validate_private_structure({"objects": objects, "edges": edges}, parents, "external-effect inventory")


def render_tsv(rows: list[dict[str, str]]) -> str:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=EDGE_FIELDS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent", type=Path, default=DEFAULT_PARENT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--review", type=Path, default=DEFAULT_REVIEW)
    parser.add_argument("--observations", type=Path, default=DEFAULT_OBSERVATIONS)
    parser.add_argument("--objects-output", type=Path, default=DEFAULT_OBJECTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--candidate", action="store_true")
    args = parser.parse_args()
    parents = read_parent(args.parent)
    manifest = read_json(args.manifest)
    review = read_json(args.review)
    observations = read_json(args.observations)
    objects, edges = build_inventory(parents, manifest, observations, review, candidate=args.candidate)
    object_document = {
        "schema_version": 1,
        "parent_inventory_digest": observations["parent_inventory_digest"],
        "discovery_manifest_digest": observations["discovery_manifest_digest"],
        "review_mode": observations["review_mode"],
        "objects": objects,
    }
    args.objects_output.parent.mkdir(parents=True, exist_ok=True)
    with args.objects_output.open("w", encoding="utf-8") as handle:
        json.dump(object_document, handle, indent=2, sort_keys=True)
        handle.write("\n")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        handle.write(render_tsv(edges))


if __name__ == "__main__":
    main()
