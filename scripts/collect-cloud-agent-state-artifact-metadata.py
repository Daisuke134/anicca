#!/usr/bin/env python3
"""Collect metadata for reviewed state/artifact declarations without reading artifacts.

Reviewed source/config files are opened through TODO #2's verified-fd helper only
to compute revision digests. Runtime artifacts are never opened: their existence,
type, and size come exclusively from lstat. Prompts, payloads, authentication
data, cookies, and artifact contents stay outside this collector.
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import importlib.util
import json
import os
import re
import stat
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
HOME = Path.home()
DEFAULT_PARENT = REPO / "docs/reference/cloud-agent-loop-inventory.tsv"
DEFAULT_DISCOVERY = REPO / "docs/reference/cloud-agent-state-artifact-discovery-manifest.json"
DEFAULT_REVIEW = REPO / "docs/reference/cloud-agent-state-artifact-discovery-review.json"
DEFAULT_OUTPUT = REPO / "docs/reference/cloud-agent-state-artifact-observations.json"
DIGEST_PATTERN = re.compile(r"^sha256:(?:[0-9a-f]{8}:){7}[0-9a-f]{8}$")
SAFE_RELATIVE = re.compile(r"[A-Za-z0-9._@+-]+(?:/[A-Za-z0-9._@+:-]+)*")
REQUIRED_ARTIFACT_CATEGORIES = ("state", "log", "media", "transcript", "cache", "output")
CONTROL_PATTERN = re.compile(r"[\x00-\x1f\x7f]")
SECRET_ASSIGNMENT = re.compile(r"(?i)(?:key|token|secret|password)\s*=\s*\S+")
EMAIL_PATTERN = re.compile(r"(?i)[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}")
PERSONAL_OR_JOB = re.compile(
    r"(?i)(?:daisuke134|#job=|account(?:_id)?[:=][A-Za-z0-9._@+-]+|"
    r"(?:job|cron)[_:=/-][A-Za-z0-9._-]*[0-9]{8,})"
)
PORTABLE_PATH = re.compile(
    r"(?i)(?:^|[\s=])(?:~/|/|\\\\|[A-Za-z]:[\\/]|file://|\$HOME(?:/|\\)|"
    r"\$\{HOME\}(?:/|\\)|%USERPROFILE%(?:/|\\)|\.\./)"
)
OPAQUE_ENTROPY = re.compile(
    r"(?<![A-Za-z0-9_-])[A-Za-z0-9_-]{40,}={0,2}(?![A-Za-z0-9_-])"
)
MANIFEST_FIELDS = frozenset(
    {"schema_version", "review_status", "review_basis", "parent_inventory_digest", "sources"}
)
SOURCE_BASE_FIELDS = frozenset(
    {
        "source_id", "source_locator", "source_revision_digest", "analysis_method",
        "parent_binding", "declarations",
    }
)
DECLARATION_REQUIRED_FIELDS = frozenset(
    {
        "declaration_id", "artifact_category", "artifact_role", "path_class",
        "runtime_path_kind", "runtime_path",
    }
)
DECLARATION_ALLOWED_FIELDS = DECLARATION_REQUIRED_FIELDS | {
    "evidence_literals", "evidence_symbols"
}
REVIEW_COMMON_FIELDS = frozenset(
    {
        "schema_version", "review_status", "reviewer_role",
        "manifest_digest", "parent_inventory_digest", "source_revisions",
    }
)
OBSERVATION_FIELDS = frozenset(
    {
        "schema_version", "review_mode", "parent_inventory_digest",
        "discovery_manifest_digest", "source_revisions", "loop_revisions",
        "definition_links", "declaration_links", "unbound_discoveries",
        "category_defaults", "objects",
    }
)
OBSERVED_OBJECT_FIELDS = frozenset(
    {
        "artifact_object_id", "artifact_category", "artifact_kind", "path_class",
        "artifact_status", "size_bytes", "size_scope", "size_evidence",
        "retention_classification", "retention_evidence_kind",
        "retention_evidence_locator", "ssot_classification", "ssot_evidence_kind",
        "ssot_evidence_locator", "source_revision_digest", "discovery_evidence_kind",
        "discovery_evidence_locator",
    }
)
SOURCE_ID_PATTERN = re.compile(r"^source-[0-9]{15}$")
LOOP_REF_PATTERN = re.compile(r"^loop-[0-9]{15}$")
OBJECT_ID_PATTERN = re.compile(r"^artifact-object-[0-9]{15}$")


def canonical_digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    digest = hashlib.sha256(encoded).hexdigest()
    return "sha256:" + ":".join(digest[index:index + 8] for index in range(0, 64, 8))


def parent_metadata_digest(parent: dict[str, str]) -> str:
    return canonical_digest({key: parent[key] for key in sorted(parent)})


def loop_ref(parent: dict[str, str]) -> str:
    return opaque_id("loop", parent_metadata_digest(parent))


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
        raise SystemExit("discovery manifest must be an object")
    return value


def validate_private_structure(
    value: object,
    parents: list[dict[str, str]],
    label: str,
    field: str = "root",
) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise SystemExit(f"{label}: non-string field name")
            validate_private_string(key, parents, label, field + " dictionary key")
            validate_private_structure(child, parents, label, key)
        return
    if isinstance(value, list):
        for child in value:
            validate_private_structure(child, parents, label, field)
        return
    if not isinstance(value, str):
        return
    validate_private_string(value, parents, label, field)


def validate_private_string(
    value: str,
    parents: list[dict[str, str]],
    label: str,
    field: str,
) -> None:
    if any(parent["inventory_id"] in value for parent in parents):
        raise SystemExit(f"{label}: raw parent inventory id")
    if (
        CONTROL_PATTERN.search(value)
        or SECRET_ASSIGNMENT.search(value)
        or EMAIL_PATTERN.search(value)
        or PERSONAL_OR_JOB.search(value)
        or PORTABLE_PATH.search(value)
    ):
        raise SystemExit(f"{label}: unsafe field {field}")
    structured_label = re.fullmatch(r"[a-z][a-z0-9_:-]{0,96}", value) is not None
    if "digest" not in field and not structured_label and OPAQUE_ENTROPY.search(value):
        raise SystemExit(f"{label}: opaque entropy in field {field}")


def exact_keys(value: object, expected: frozenset[str] | set[str], label: str) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != set(expected):
        raise SystemExit(f"{label} schema mismatch")
    return value


def validate_manifest_schema(manifest: dict[str, object]) -> None:
    exact_keys(manifest, MANIFEST_FIELDS, "discovery manifest")
    sources = manifest.get("sources")
    if not isinstance(sources, list) or not sources:
        raise SystemExit("discovery manifest source schema mismatch")
    for source in sources:
        if not isinstance(source, dict):
            raise SystemExit("discovery source schema mismatch")
        expected = set(SOURCE_BASE_FIELDS)
        if source.get("parent_binding") == "explicit_parent_list":
            expected.add("loop_refs")
        if set(source) != expected:
            raise SystemExit("discovery source schema mismatch")
        declarations = source.get("declarations")
        if not isinstance(declarations, list) or not declarations:
            raise SystemExit("discovery declaration schema mismatch")
        for declaration in declarations:
            if not isinstance(declaration, dict):
                raise SystemExit("discovery declaration schema mismatch")
            keys = set(declaration)
            if (
                not DECLARATION_REQUIRED_FIELDS <= keys
                or not keys <= DECLARATION_ALLOWED_FIELDS
                or not keys & {"evidence_literals", "evidence_symbols"}
            ):
                raise SystemExit("discovery declaration schema mismatch")


def validate_review_schema(review: dict[str, object]) -> None:
    expected = set(REVIEW_COMMON_FIELDS)
    if review.get("review_status") == "approved":
        expected.add("approval_basis")
    elif review.get("review_status") == "review_required":
        expected.add("review_basis")
    else:
        raise SystemExit("independent review status schema mismatch")
    exact_keys(review, expected, "independent review artifact")
    revisions = review.get("source_revisions")
    if not isinstance(revisions, dict) or not revisions or not all(
        isinstance(key, str) and SOURCE_ID_PATTERN.fullmatch(key)
        and isinstance(value, str) and DIGEST_PATTERN.fullmatch(value)
        for key, value in revisions.items()
    ):
        raise SystemExit("independent review source revision schema mismatch")


def validate_observations_schema(observations: dict[str, object]) -> None:
    exact_keys(observations, OBSERVATION_FIELDS, "state/artifact observations")
    source_revisions = observations.get("source_revisions")
    if not isinstance(source_revisions, dict) or not all(
        SOURCE_ID_PATTERN.fullmatch(str(key)) and DIGEST_PATTERN.fullmatch(str(value))
        for key, value in source_revisions.items()
    ):
        raise SystemExit("observation source revision schema mismatch")
    loop_revisions = observations.get("loop_revisions")
    if not isinstance(loop_revisions, dict) or not all(
        LOOP_REF_PATTERN.fullmatch(str(key)) and DIGEST_PATTERN.fullmatch(str(value))
        for key, value in loop_revisions.items()
    ):
        raise SystemExit("observation loop revision schema mismatch")
    for map_name in ("definition_links", "declaration_links"):
        mapping = observations.get(map_name)
        if not isinstance(mapping, dict) or not all(
            LOOP_REF_PATTERN.fullmatch(str(key)) for key in mapping
        ):
            raise SystemExit(f"observation {map_name} schema mismatch")
    definition_links = observations["definition_links"]
    if not all(OBJECT_ID_PATTERN.fullmatch(str(value)) for value in definition_links.values()):
        raise SystemExit("observation definition link schema mismatch")
    declaration_links = observations["declaration_links"]
    if not all(
        isinstance(values, list) and all(OBJECT_ID_PATTERN.fullmatch(str(value)) for value in values)
        for values in declaration_links.values()
    ):
        raise SystemExit("observation declaration link schema mismatch")
    defaults = observations.get("category_defaults")
    if not isinstance(defaults, dict) or set(defaults) != set(REQUIRED_ARTIFACT_CATEGORIES) or not all(
        OBJECT_ID_PATTERN.fullmatch(str(value)) for value in defaults.values()
    ):
        raise SystemExit("observation category default schema mismatch")
    unbound = observations.get("unbound_discoveries")
    if not isinstance(unbound, list) or not all(OBJECT_ID_PATTERN.fullmatch(str(value)) for value in unbound):
        raise SystemExit("observation unbound discovery schema mismatch")
    objects = observations.get("objects")
    if not isinstance(objects, dict) or not objects:
        raise SystemExit("observation object map schema mismatch")
    for object_id, record in objects.items():
        if not OBJECT_ID_PATTERN.fullmatch(str(object_id)):
            raise SystemExit("observation object id schema mismatch")
        exact_keys(record, OBSERVED_OBJECT_FIELDS, "observation object")


def load_todo2_helpers():
    path = REPO / "scripts/collect-cloud-agent-credential-metadata.py"
    spec = importlib.util.spec_from_file_location("todo2_secure_metadata_helpers", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("TODO #2 secure metadata helpers unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def format_digest(raw: str) -> str:
    if re.fullmatch(r"[0-9a-f]{64}", raw) is None:
        raise RuntimeError("invalid source digest")
    return "sha256:" + ":".join(raw[index:index + 8] for index in range(0, 64, 8))


def safe_repo_source(locator: str) -> Path:
    if not locator.startswith("repo:"):
        raise SystemExit("reviewed source locator must be repository-relative")
    relative = locator.removeprefix("repo:")
    if SAFE_RELATIVE.fullmatch(relative) is None or any(
        part in {"", ".", ".."} for part in relative.split("/")
    ):
        raise SystemExit("invalid reviewed source locator")
    return REPO / relative


def secure_source_analysis(path: Path, helpers) -> tuple[str, set[str], set[str]]:
    descriptor = helpers._open_lstat_bound_fd(
        path, "state/artifact reviewed source", trusted_root=REPO
    )
    try:
        raw_digest = helpers._fd_sha256(descriptor)
        chunks: list[bytes] = []
        while chunk := os.read(descriptor, 1024 * 1024):
            chunks.append(chunk)
        os.lseek(descriptor, 0, os.SEEK_SET)
        tree = ast.parse(b"".join(chunks).decode("utf-8"), filename=path.name)
        literals = {
            node.value for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        }
        symbols = {
            node.id for node in ast.walk(tree) if isinstance(node, ast.Name)
        } | {
            node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
        }
        return format_digest(raw_digest), literals, symbols
    finally:
        os.close(descriptor)


def secure_source_digest(path: Path, helpers) -> str:
    return secure_source_analysis(path, helpers)[0]


def opaque_id(prefix: str, material: str) -> str:
    value = int(hashlib.sha256(material.encode()).hexdigest()[:12], 16)
    return f"{prefix}-{value:015d}"


def artifact_object_id(material: str) -> str:
    return opaque_id("artifact-object", material)


def inspect_path(path: Path | None) -> tuple[str, str, str]:
    if path is None:
        return "unverified", "unknown", "unavailable:not_local_or_unresolved"
    try:
        metadata = path.lstat()
    except OSError:
        return "unverified", "unknown", "unavailable:lstat"
    if not stat.S_ISREG(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
        return "unverified", "unknown", "unavailable:not_regular_file"
    return "observed", str(metadata.st_size), "lstat:regular_file"


def unverified_classifications() -> dict[str, str]:
    return {
        "retention_classification": "unknown",
        "retention_evidence_kind": "unverified",
        "retention_evidence_locator": "unverified",
        "ssot_classification": "unverified",
        "ssot_evidence_kind": "unverified",
        "ssot_evidence_locator": "unverified",
    }


def object_record(
    object_id: str,
    *,
    artifact_category: str,
    artifact_kind: str,
    path_class: str,
    path: Path | None,
    size_scope: str,
    source_revision_digest: str,
    discovery_evidence_kind: str,
    discovery_evidence_locator: str,
) -> dict[str, str]:
    status, size, size_evidence = inspect_path(path)
    return {
        "artifact_object_id": object_id,
        "artifact_category": artifact_category,
        "artifact_kind": artifact_kind,
        "path_class": path_class,
        "artifact_status": status,
        "size_bytes": size,
        "size_scope": size_scope if size.isdigit() else "unknown",
        "size_evidence": size_evidence,
        **unverified_classifications(),
        "source_revision_digest": source_revision_digest,
        "discovery_evidence_kind": discovery_evidence_kind,
        "discovery_evidence_locator": discovery_evidence_locator,
    }


def definition_target(parent: dict[str, str]) -> tuple[str, str, Path | None, str]:
    source_type = parent["source_type"]
    evidence = parent["evidence"]
    if source_type == "openclaw_cron":
        return (
            "openclaw-shared-definition-container",
            "scheduler:shared_definition_container",
            HOME / ".openclaw/cron/jobs.json",
            "shared_container",
        )
    if source_type == "launchd" and evidence.startswith("~/Library/LaunchAgents/"):
        return (
            "launchd-definition:" + canonical_digest(parent["inventory_id"]),
            "scheduler:launchd_definition",
            HOME / evidence[2:],
            "object",
        )
    if source_type == "repository_entrypoint" and SAFE_RELATIVE.fullmatch(evidence):
        return (
            "repository-definition:" + canonical_digest(parent["inventory_id"]),
            "scheduler:repository_definition",
            REPO / evidence,
            "object",
        )
    return (
        "unresolved-definition:" + canonical_digest(parent["inventory_id"]),
        "scheduler:unverified_definition",
        None,
        "unknown",
    )


def resolve_declaration_path(declaration: dict[str, object]) -> Path | None:
    kind = declaration.get("runtime_path_kind")
    value = declaration.get("runtime_path")
    if kind == "non_local" and value == "unverified":
        return None
    if not isinstance(value, str) or SAFE_RELATIVE.fullmatch(value) is None:
        raise SystemExit("invalid reviewed runtime path")
    if kind == "repo_relative":
        return REPO / value
    if kind == "home_relative":
        return HOME / value
    raise SystemExit("invalid reviewed runtime path kind")


def validate_manifest(
    manifest: dict[str, object], parents: list[dict[str, str]]
) -> list[dict[str, object]]:
    validate_private_structure(manifest, parents, "discovery manifest")
    validate_manifest_schema(manifest)
    if manifest.get("schema_version") != 2 or manifest.get("review_status") != "review_required":
        raise SystemExit("discovery manifest review status invalid")
    if manifest.get("review_basis") != "pending_independent_architecture_review":
        raise SystemExit("builder discovery manifest must remain pending")
    expected = canonical_digest([parent_metadata_digest(parent) for parent in parents])
    if manifest.get("parent_inventory_digest") != expected:
        raise SystemExit("discovery manifest parent revision mismatch")
    sources = manifest.get("sources")
    if not isinstance(sources, list) or not sources:
        raise SystemExit("discovery manifest sources missing")
    parent_ids = {parent["inventory_id"] for parent in parents}
    parent_refs = {loop_ref(parent) for parent in parents}
    serialized = json.dumps(manifest, sort_keys=True)
    if any(parent_id in serialized for parent_id in parent_ids):
        raise SystemExit("raw parent inventory id in discovery manifest")
    seen_sources: set[str] = set()
    seen_declarations: set[str] = set()
    for source in sources:
        if not isinstance(source, dict):
            raise SystemExit("invalid discovery source")
        source_id = source.get("source_id")
        if not isinstance(source_id, str) or not re.fullmatch(r"source-[0-9]{15}", source_id):
            raise SystemExit("invalid discovery source id")
        if source_id in seen_sources:
            raise SystemExit("duplicate discovery source id")
        seen_sources.add(source_id)
        if not DIGEST_PATTERN.fullmatch(str(source.get("source_revision_digest", ""))):
            raise SystemExit("invalid discovery source revision")
        declarations = source.get("declarations")
        if not isinstance(declarations, list) or not declarations:
            raise SystemExit("empty discovery source declarations")
        binding = source.get("parent_binding")
        if binding == "explicit_parent_list":
            bound = source.get("loop_refs")
            if not isinstance(bound, list) or not bound or not set(bound) <= parent_refs:
                raise SystemExit("invalid discovery parent binding")
        elif binding != "unbound_parent_unverified":
            raise SystemExit("invalid discovery parent binding")
        for declaration in declarations:
            if not isinstance(declaration, dict):
                raise SystemExit("invalid discovery declaration")
            declaration_id = declaration.get("declaration_id")
            if not isinstance(declaration_id, str) or not re.fullmatch(
                r"declaration-[0-9]{15}", declaration_id
            ):
                raise SystemExit("invalid discovery declaration id")
            if declaration_id in seen_declarations:
                raise SystemExit("duplicate discovery declaration id")
            seen_declarations.add(declaration_id)
            if declaration.get("artifact_category") not in REQUIRED_ARTIFACT_CATEGORIES:
                raise SystemExit("invalid discovery artifact category")
            evidence_literals = declaration.get("evidence_literals", [])
            evidence_symbols = declaration.get("evidence_symbols", [])
            if not isinstance(evidence_literals, list) or not isinstance(evidence_symbols, list):
                raise SystemExit("invalid discovery declaration evidence")
            if not evidence_literals and not evidence_symbols:
                raise SystemExit("discovery declaration evidence missing")
            if not all(isinstance(value, str) and value for value in evidence_literals + evidence_symbols):
                raise SystemExit("invalid discovery declaration evidence")
            resolve_declaration_path(declaration)
    return sources


def validate_review(
    review: dict[str, object],
    manifest: dict[str, object],
    source_revisions: dict[str, str],
    *,
    candidate: bool,
) -> str:
    validate_review_schema(review)
    expected = {
        "manifest_digest": canonical_digest(manifest),
        "parent_inventory_digest": manifest["parent_inventory_digest"],
        "source_revisions": dict(sorted(source_revisions.items())),
    }
    if review.get("schema_version") != 1 or any(review.get(key) != value for key, value in expected.items()):
        raise SystemExit("independent review binding mismatch")
    if candidate:
        if review.get("review_status") != "review_required" or review.get("review_basis") != "pending_independent_architecture_review":
            raise SystemExit("candidate review artifact must remain pending")
        return "candidate_review_required"
    if (
        review.get("review_status") != "approved"
        or review.get("approval_basis") != "todo3_independent_candidate_review_approved_v1"
        or review.get("reviewer_role") != "independent_fresh_sol_review"
    ):
        raise SystemExit("independent review approval required")
    return "independent_review_approved"


def collect(
    parent_path: Path,
    discovery_path: Path,
    review_path: Path = DEFAULT_REVIEW,
    *,
    candidate: bool = False,
) -> dict[str, object]:
    parents = read_parent(parent_path)
    manifest = read_json(discovery_path)
    sources = validate_manifest(manifest, parents)
    helpers = load_todo2_helpers()
    source_revisions: dict[str, str] = {}
    objects: dict[str, dict[str, str]] = {}
    definition_links: dict[str, str] = {}
    declaration_links: dict[str, list[str]] = {}
    unbound: list[str] = []

    for parent in sorted(parents, key=lambda row: row["inventory_id"]):
        key, path_class, path, scope = definition_target(parent)
        object_id = artifact_object_id(key)
        if object_id not in objects:
            objects[object_id] = object_record(
                object_id,
                artifact_category="definition",
                artifact_kind="definition",
                path_class=path_class,
                path=path,
                size_scope=scope,
                source_revision_digest="unverified",
                discovery_evidence_kind="parent_metadata",
                discovery_evidence_locator="parent:definition_metadata",
            )
        definition_links[loop_ref(parent)] = object_id

    for source in sources:
        source_id = str(source["source_id"])
        live_digest, literals, symbols = secure_source_analysis(
            safe_repo_source(str(source["source_locator"])), helpers
        )
        source_revisions[source_id] = live_digest
        bound_parents = source.get("loop_refs", [])
        for declaration in source["declarations"]:
            if not set(declaration.get("evidence_literals", [])) <= literals:
                raise SystemExit(f"{source_id}: reviewed source literal evidence mismatch")
            if not set(declaration.get("evidence_symbols", [])) <= symbols:
                raise SystemExit(f"{source_id}: reviewed source symbol evidence mismatch")
            declaration_id = str(declaration["declaration_id"])
            object_id = artifact_object_id("reviewed-declaration:" + declaration_id)
            objects[object_id] = object_record(
                object_id,
                artifact_category=str(declaration["artifact_category"]),
                artifact_kind=str(declaration["artifact_role"]),
                path_class=str(declaration["path_class"]),
                path=resolve_declaration_path(declaration),
                size_scope="object",
                source_revision_digest=live_digest,
                discovery_evidence_kind="reviewed_static_source",
                discovery_evidence_locator=source_id,
            )
            if source["parent_binding"] == "explicit_parent_list":
                for parent_reference in bound_parents:
                    declaration_links.setdefault(str(parent_reference), []).append(object_id)
            else:
                unbound.append(object_id)

    category_defaults: dict[str, str] = {}
    for category in REQUIRED_ARTIFACT_CATEGORIES:
        object_id = artifact_object_id("category-unverified:" + category)
        objects[object_id] = object_record(
            object_id,
            artifact_category=category,
            artifact_kind="coverage_unverified",
            path_class=f"{category}:unverified",
            path=None,
            size_scope="unknown",
            source_revision_digest="unverified",
            discovery_evidence_kind="unverified",
            discovery_evidence_locator="unverified",
        )
        category_defaults[category] = object_id

    review = read_json(review_path)
    validate_private_structure(review, parents, "independent review artifact")
    review_mode = validate_review(review, manifest, source_revisions, candidate=candidate)
    result = {
        "schema_version": 2,
        "review_mode": review_mode,
        "parent_inventory_digest": manifest["parent_inventory_digest"],
        "discovery_manifest_digest": canonical_digest(manifest),
        "source_revisions": dict(sorted(source_revisions.items())),
        "loop_revisions": {
            loop_ref(parent): parent_metadata_digest(parent)
            for parent in sorted(parents, key=loop_ref)
        },
        "definition_links": dict(sorted(definition_links.items())),
        "declaration_links": {
            key: sorted(value) for key, value in sorted(declaration_links.items())
        },
        "unbound_discoveries": sorted(unbound),
        "category_defaults": dict(sorted(category_defaults.items())),
        "objects": {key: objects[key] for key in sorted(objects)},
    }
    validate_observations_schema(result)
    validate_private_structure(result, parents, "state/artifact observations")
    serialized = json.dumps(result, sort_keys=True)
    if any(parent["inventory_id"] in serialized for parent in parents):
        raise SystemExit("raw parent inventory id in observations")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parent", type=Path, default=DEFAULT_PARENT)
    parser.add_argument("--discovery", type=Path, default=DEFAULT_DISCOVERY)
    parser.add_argument("--review", type=Path, default=DEFAULT_REVIEW)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--candidate", action="store_true")
    args = parser.parse_args()
    rendered = json.dumps(
        collect(args.parent, args.discovery, args.review, candidate=args.candidate),
        indent=2,
        sort_keys=True,
    ) + "\n"
    args.output.write_text(rendered, encoding="utf-8")


if __name__ == "__main__":
    main()
