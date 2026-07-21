#!/usr/bin/env python3
"""Collect privacy-safe, revision-bound metadata for TODO #4 external effects."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import re
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
RUNTIME = Path("/Users/anicca/anicca")
PROFITABLE = Path("/Users/anicca/profitable-claude")
LOCAL_SHARE = Path("/Users/anicca/.local/share/anicca")
DEFAULT_PARENT = REPO / "docs/reference/cloud-agent-loop-inventory.tsv"
DEFAULT_MANIFEST = REPO / "docs/reference/cloud-agent-external-effect-discovery-manifest.json"
DEFAULT_REVIEW = REPO / "docs/reference/cloud-agent-external-effect-discovery-review.json"
DEFAULT_OUTPUT = REPO / "docs/reference/cloud-agent-external-effect-observations.json"
REQUIRED_EFFECT_CATEGORIES = ("call", "post", "mail", "render", "wallet")
DIGEST_PATTERN = re.compile(r"^sha256:(?:[0-9a-f]{8}:){7}[0-9a-f]{8}$")
LOOP_REF_PATTERN = re.compile(r"^loop-[0-9]{15}$")
OBJECT_ID_PATTERN = re.compile(r"^effect-object-[0-9]{15}$")
CONTROL_PATTERN = re.compile(r"[\x00-\x1f\x7f]")
EMAIL_PATTERN = re.compile(r"(?i)[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}")
PHONE_PATTERN = re.compile(r"(?<![0-9])\+[1-9][0-9]{9,14}(?![0-9])")
WALLET_PATTERN = re.compile(r"(?i)(?:wallet[:=]\s*)?0x[0-9a-f]{40}")
SECRET_ASSIGNMENT = re.compile(r"(?i)(?:key|token|secret|password)\s*=\s*\S+")
OPAQUE_ENTROPY = re.compile(r"(?<![A-Za-z0-9_-])[A-Za-z0-9_-]{40,}={0,2}(?![A-Za-z0-9_-])")
PERSONAL_OR_JOB = re.compile(r"(?i)(?:daisuke134|account(?:_id)?[:=][A-Za-z0-9._@+-]+|#job=)")
PORTABLE_PATH = re.compile(r"(?i)(?:/Users/|~/|\\\\|[A-Za-z]:[\\/]|file://|\$HOME(?:/|\\)|\$\{HOME\})")

MANIFEST_FIELDS = frozenset({"schema_version", "parent_inventory_digest", "review_status", "review_basis", "sources"})
SOURCE_FIELDS = frozenset({"source_id", "source_locator", "source_revision_digest", "declarations"})
DECLARATION_FIELDS = frozenset({
    "effect_key", "effect_category", "effect_kind", "provider_class", "target_class",
    "action_class", "direction", "provider_tool_ref", "mutability", "financial_risk",
    "idempotency", "approval_gate", "execution_policy", "loop_refs", "evidence_tokens",
})
REVIEW_PENDING_FIELDS = frozenset({
    "schema_version", "review_status", "review_basis", "reviewer_role", "manifest_digest",
    "parent_inventory_digest", "source_revisions",
})
REVIEW_APPROVED_FIELDS = REVIEW_PENDING_FIELDS | {"approval_basis"}
PENDING_REVIEW_BASIS = "pending_independent_external_effect_review"
PENDING_REVIEWER_ROLE = "independent_fresh_reviewer_required"
APPROVED_REVIEW_BASIS = "todo4_independent_candidate_review_approved_v1"
APPROVED_REVIEWER_ROLE = "independent_fresh_sol_review"
OBSERVATION_FIELDS = frozenset({
    "schema_version", "parent_inventory_digest", "discovery_manifest_digest", "review_mode",
    "source_revisions", "loop_revisions", "objects",
})
OBJECT_FIELDS = frozenset({
    "effect_object_id", "effect_category", "effect_kind", "provider_class", "target_class",
    "action_class", "direction", "provider_tool_ref", "mutability", "financial_risk",
    "idempotency", "approval_gate", "execution_policy", "discovery_status",
    "source_revision_digest", "evidence_kind", "evidence_locator",
})

SOURCE_PATHS = {
    "repo:scripts/cross-poster/instagram_poster.py": (REPO / "scripts/cross-poster/instagram_poster.py", REPO),
    "repo:apps/api/src/routes/mobile/newsletter.js": (REPO / "apps/api/src/routes/mobile/newsletter.js", REPO),
    "runtime:skills/earn/clip/producer.sh": (RUNTIME / "skills/earn/clip/producer.sh", RUNTIME),
    "runtime:skills/anicca-life-manager/scripts/realtime_guide.py": (
        RUNTIME / "skills/anicca-life-manager/scripts/realtime_guide.py", RUNTIME
    ),
    "repo:.claude/skills/earn-gig/scripts/claw_agent.py": (
        REPO / ".claude/skills/earn-gig/scripts/claw_agent.py", REPO
    ),
    "profitable:skills/article-writer/scripts/zenn-deferred-worker.py": (
        PROFITABLE / "skills/article-writer/scripts/zenn-deferred-worker.py", PROFITABLE
    ),
    "local-share:orca-zenn-finalizer/finalizer.py": (
        LOCAL_SHARE / "orca-zenn-finalizer/finalizer.py", LOCAL_SHARE
    ),
}


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


def exact_keys(value: object, expected: frozenset[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != set(expected):
        raise SystemExit(f"{label} schema mismatch")


def validate_private_structure(value: object, parents: list[dict[str, str]], label: str) -> None:
    parent_ids = {row["inventory_id"] for row in parents}

    def visit(item: object, location: str) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                visit(str(key), f"{location}.key")
                visit(child, f"{location}.{key}")
            return
        if isinstance(item, list):
            for index, child in enumerate(item):
                visit(child, f"{location}[{index}]")
            return
        if not isinstance(item, str):
            return
        if item in parent_ids or CONTROL_PATTERN.search(item) or EMAIL_PATTERN.search(item):
            raise SystemExit(f"unsafe field {location}")
        if PHONE_PATTERN.search(item) or WALLET_PATTERN.search(item) or SECRET_ASSIGNMENT.search(item):
            raise SystemExit(f"unsafe field {location}")
        if PERSONAL_OR_JOB.search(item) or PORTABLE_PATH.search(item):
            raise SystemExit(f"unsafe field {location}")
        opaque = OPAQUE_ENTROPY.search(item)
        if (
            not DIGEST_PATTERN.fullmatch(item)
            and opaque
            and any(char.isupper() for char in opaque.group())
            and any(char.islower() for char in opaque.group())
            and any(char.isdigit() for char in opaque.group())
        ):
            raise SystemExit(f"unsafe field {location}")

    visit(value, label)


def load_todo2_helpers():
    path = REPO / "scripts/collect-cloud-agent-credential-metadata.py"
    spec = importlib.util.spec_from_file_location("todo2_external_effect_helpers", path)
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


def secure_source_analysis(locator: str, helpers) -> tuple[str, str]:
    if locator not in SOURCE_PATHS:
        raise SystemExit("unreviewed source locator")
    path, trusted_root = SOURCE_PATHS[locator]
    descriptor = helpers._open_lstat_bound_fd(path, "external-effect reviewed source", trusted_root=trusted_root)
    try:
        raw_digest = helpers._fd_sha256(descriptor)
        chunks: list[bytes] = []
        while chunk := os.read(descriptor, 1024 * 1024):
            chunks.append(chunk)
        return format_digest(raw_digest), b"".join(chunks).decode("utf-8")
    finally:
        os.close(descriptor)


def validate_manifest(manifest: dict[str, object], parents: list[dict[str, str]]) -> list[dict[str, object]]:
    exact_keys(manifest, MANIFEST_FIELDS, "external-effect manifest")
    validate_private_structure(manifest, parents, "external-effect manifest")
    if manifest.get("schema_version") != 1 or manifest.get("review_status") != "review_required":
        raise SystemExit("external-effect manifest review status mismatch")
    if manifest.get("review_basis") != "pending_independent_external_effect_review":
        raise SystemExit("external-effect manifest review basis mismatch")
    expected_parent = canonical_digest([parent_metadata_digest(parent) for parent in parents])
    if manifest.get("parent_inventory_digest") != expected_parent:
        raise SystemExit("parent inventory revision mismatch")
    sources = manifest.get("sources")
    if not isinstance(sources, list) or not sources:
        raise SystemExit("external-effect source schema mismatch")
    known_refs = {loop_ref(parent) for parent in parents}
    source_ids: set[str] = set()
    effect_keys: set[str] = set()
    categories: set[str] = set()
    for source in sources:
        exact_keys(source, SOURCE_FIELDS, "external-effect source")
        source_id = source.get("source_id")
        locator = source.get("source_locator")
        if not isinstance(source_id, str) or not re.fullmatch(r"source-[a-z0-9-]+", source_id):
            raise SystemExit("external-effect source id schema mismatch")
        if source_id in source_ids or locator not in SOURCE_PATHS:
            raise SystemExit("external-effect source identity mismatch")
        source_ids.add(source_id)
        if not DIGEST_PATTERN.fullmatch(str(source.get("source_revision_digest", ""))):
            raise SystemExit("external-effect source digest schema mismatch")
        declarations = source.get("declarations")
        if not isinstance(declarations, list) or not declarations:
            raise SystemExit("external-effect declaration schema mismatch")
        for declaration in declarations:
            exact_keys(declaration, DECLARATION_FIELDS, "external-effect declaration")
            key = declaration.get("effect_key")
            category = declaration.get("effect_category")
            if not isinstance(key, str) or not re.fullmatch(r"effect-[a-z0-9-]+", key) or key in effect_keys:
                raise SystemExit("external-effect key schema mismatch")
            if category not in REQUIRED_EFFECT_CATEGORIES:
                raise SystemExit("external-effect category schema mismatch")
            if declaration.get("execution_policy") not in {"allowed", "blocked", "unverified"}:
                raise SystemExit("external-effect policy schema mismatch")
            if re.fullmatch(r"tool-ref-[0-9]{15}", str(declaration.get("provider_tool_ref", ""))) is None:
                raise SystemExit("external-effect provider tool reference schema mismatch")
            refs = declaration.get("loop_refs")
            tokens = declaration.get("evidence_tokens")
            if not isinstance(refs, list) or len(refs) != len(set(refs)) or not set(refs) <= known_refs:
                raise SystemExit("external-effect loop reference schema mismatch")
            if not isinstance(tokens, list) or not tokens or not all(isinstance(token, str) and token for token in tokens):
                raise SystemExit("external-effect evidence token schema mismatch")
            effect_keys.add(key)
            categories.add(str(category))
    if categories != set(REQUIRED_EFFECT_CATEGORIES):
        raise SystemExit("external-effect required category discovery mismatch")
    return sources


def validate_review_schema(review: dict[str, object]) -> None:
    status = review.get("review_status") if isinstance(review, dict) else None
    exact_keys(review, REVIEW_APPROVED_FIELDS if status == "approved" else REVIEW_PENDING_FIELDS, "external-effect review")


def validate_review(
    review: dict[str, object], manifest: dict[str, object], source_revisions: dict[str, str], *, candidate: bool
) -> str:
    validate_review_schema(review)
    if review.get("schema_version") != 1:
        raise SystemExit("external-effect review schema mismatch")
    if review.get("manifest_digest") != canonical_digest(manifest):
        raise SystemExit("external-effect review manifest revision mismatch")
    if review.get("parent_inventory_digest") != manifest.get("parent_inventory_digest"):
        raise SystemExit("external-effect review parent revision mismatch")
    if review.get("source_revisions") != dict(sorted(source_revisions.items())):
        raise SystemExit("external-effect review source revision mismatch")
    if candidate:
        if (
            review.get("review_status"),
            review.get("review_basis"),
            review.get("reviewer_role"),
        ) != ("review_required", PENDING_REVIEW_BASIS, PENDING_REVIEWER_ROLE):
            raise SystemExit("candidate review artifact must remain pending")
        return "candidate_pending_review"
    if (
        review.get("review_status"),
        review.get("review_basis"),
        review.get("approval_basis"),
        review.get("reviewer_role"),
    ) != (
        "approved",
        APPROVED_REVIEW_BASIS,
        APPROVED_REVIEW_BASIS,
        APPROVED_REVIEWER_ROLE,
    ):
        raise SystemExit("independent external-effect review required")
    return "independent_review_approved"


def validate_observations_schema(observations: dict[str, object]) -> None:
    exact_keys(observations, OBSERVATION_FIELDS, "external-effect observations")
    if observations.get("schema_version") != 1:
        raise SystemExit("external-effect observations schema mismatch")
    for map_name, pattern in (("source_revisions", None), ("loop_revisions", LOOP_REF_PATTERN), ("objects", OBJECT_ID_PATTERN)):
        value = observations.get(map_name)
        if not isinstance(value, dict):
            raise SystemExit(f"external-effect {map_name} schema mismatch")
        if pattern is not None and not all(pattern.fullmatch(str(key)) for key in value):
            raise SystemExit(f"external-effect {map_name} schema mismatch")
    for object_id, record in observations["objects"].items():
        exact_keys(record, OBJECT_FIELDS, "external-effect observation object")
        if record.get("effect_object_id") != object_id:
            raise SystemExit("external-effect object identity mismatch")


def collect(parent_path: Path, manifest_path: Path, review_path: Path, *, candidate: bool) -> dict[str, object]:
    parents = read_parent(parent_path)
    manifest = read_json(manifest_path)
    sources = validate_manifest(manifest, parents)
    review = read_json(review_path)
    validate_private_structure(review, parents, "external-effect review")
    helpers = load_todo2_helpers()
    source_revisions: dict[str, str] = {}
    source_text: dict[str, str] = {}
    for source in sources:
        digest, text = secure_source_analysis(str(source["source_locator"]), helpers)
        if digest != source["source_revision_digest"]:
            raise SystemExit(f"{source['source_id']}: source revision mismatch")
        source_revisions[str(source["source_id"])] = digest
        source_text[str(source["source_id"])] = text
    review_mode = validate_review(review, manifest, source_revisions, candidate=candidate)
    objects: dict[str, dict[str, str]] = {}
    for source in sources:
        source_id = str(source["source_id"])
        for declaration in source["declarations"]:
            missing = [token for token in declaration["evidence_tokens"] if token not in source_text[source_id]]
            if missing:
                raise SystemExit(f"{source_id}: source token evidence mismatch")
            object_id = opaque_id("effect-object", str(declaration["effect_key"]))
            objects[object_id] = {
                "effect_object_id": object_id,
                "effect_category": str(declaration["effect_category"]),
                "effect_kind": str(declaration["effect_kind"]),
                "provider_class": str(declaration["provider_class"]),
                "target_class": str(declaration["target_class"]),
                "action_class": str(declaration["action_class"]),
                "direction": str(declaration["direction"]),
                "provider_tool_ref": str(declaration["provider_tool_ref"]),
                "mutability": str(declaration["mutability"]),
                "financial_risk": str(declaration["financial_risk"]),
                "idempotency": str(declaration["idempotency"]),
                "approval_gate": str(declaration["approval_gate"]),
                "execution_policy": str(declaration["execution_policy"]),
                "discovery_status": "observed",
                "source_revision_digest": source_revisions[source_id],
                "evidence_kind": "reviewed_source_token",
                "evidence_locator": source_id,
            }
    for category in REQUIRED_EFFECT_CATEGORIES:
        object_id = opaque_id("effect-object", f"default:{category}")
        objects[object_id] = {
            "effect_object_id": object_id,
            "effect_category": category,
            "effect_kind": "category_unverified",
            "provider_class": "unverified",
            "target_class": "unverified",
            "action_class": "unverified",
            "direction": "unverified",
            "provider_tool_ref": "unverified",
            "mutability": "unverified",
            "financial_risk": "unverified",
            "idempotency": "unverified",
            "approval_gate": "unverified",
            "execution_policy": "unverified",
            "discovery_status": "unverified",
            "source_revision_digest": "unverified",
            "evidence_kind": "unverified",
            "evidence_locator": "unverified",
        }
    result: dict[str, object] = {
        "schema_version": 1,
        "parent_inventory_digest": canonical_digest([parent_metadata_digest(parent) for parent in parents]),
        "discovery_manifest_digest": canonical_digest(manifest),
        "review_mode": review_mode,
        "source_revisions": dict(sorted(source_revisions.items())),
        "loop_revisions": dict(sorted((loop_ref(parent), parent_metadata_digest(parent)) for parent in parents)),
        "objects": dict(sorted(objects.items())),
    }
    validate_observations_schema(result)
    validate_private_structure(result, parents, "external-effect observations")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent", type=Path, default=DEFAULT_PARENT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--review", type=Path, default=DEFAULT_REVIEW)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--candidate", action="store_true")
    args = parser.parse_args()
    result = collect(args.parent, args.manifest, args.review, candidate=args.candidate)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write("\n")


if __name__ == "__main__":
    main()
