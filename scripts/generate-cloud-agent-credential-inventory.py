#!/usr/bin/env python3
"""Generate the fail-closed TODO #2 edge TSV from four non-secret inputs.

Inputs are the parent TSV, safe observations, independent review manifest, and
credential objects. Exact bindings are validated before the current edge TSV is
emitted, and credential values are never read.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
HOME = Path.home()
DEFAULT_PARENT = REPO / "docs" / "reference" / "cloud-agent-loop-inventory.tsv"
DEFAULT_OBSERVATIONS = REPO / "docs" / "reference" / "cloud-agent-credential-observations.json"
DEFAULT_REVIEW = REPO / "docs" / "reference" / "cloud-agent-credential-review-manifest.json"
DEFAULT_OBJECTS = REPO / "docs" / "reference" / "cloud-agent-credential-objects.json"
APPROVED_REVIEW_BASIS = "iteration_20_whole_change_approved"

EDGE_FIELDS = (
    "loop_dependency_edge_id",
    "inventory_id",
    "loop_state",
    "dependency_status",
    "credential_object_id",
    "consumer_locator",
    "permission_scope",
    "dependency_basis",
    "evidence_locator",
    "parent_metadata_digest",
    "source_revision_digest",
    "config_revision_digest",
)

REVIEW_REFERENCE_FIELDS = frozenset(
    {
        "credential_object_id", "provider", "account_alias", "credential_type",
        "credential_ref", "policy_status", "policy_basis", "evidence_locator",
        "consumer_locator", "permission_scope",
    }
)

SUBSCRIPTION_OAUTH_PROVIDERS = frozenset(
    {"anthropic", "claude-cli", "openai", "openai-codex", "codex"}
)
CREDENTIAL_TYPES = frozenset({"api_key", "delivery_ref", "env_ref", "oauth", "token"})
REAL_PROVIDERS = frozenset(
    {
        "anthropic", "openai", "claude-cli", "deepseek", "kimi", "moonshot",
        "blockrun", "xai", "google", "supabase", "stripe", "slack", "github",
        "apify", "telnyx", "twilio", "resend", "aws", "digitalocean", "cloudflare",
        "railway", "inngest", "composio", "steel", "elevenlabs", "revenuecat",
        "mixpanel", "tiktok", "meta", "x", "blotato", "agentmail", "perplexity",
        "replicate", "firecrawl", "telegram", "apple", "jupiter", "solana", "mem0",
        "printful", "unipile", "ethereum", "moltbook", "postgresql", "redis", "anicca-api",
        "life-manager", "none", "unverified",
    }
)

PROVIDER_PREFIXES = (
    (("ANTHROPIC_", "CLAUDE_"), "anthropic"),
    (("OPENAI_",), "openai"),
    (("GEMINI_", "GOOGLE_", "GOG_"), "google"),
    (("SUPABASE_",), "supabase"),
    (("SLACK_",), "slack"),
    (("GITHUB_", "GH_"), "github"),
    (("APIFY_",), "apify"),
    (("TELNYX_",), "telnyx"),
    (("TWILIO_",), "twilio"),
    (("STRIPE_",), "stripe"),
    (("RESEND_",), "resend"),
    (("AWS_",), "aws"),
    (("DIGITALOCEAN_", "DO_"), "digitalocean"),
    (("CLOUDFLARE_",), "cloudflare"),
    (("RAILWAY_",), "railway"),
    (("INNGEST_",), "inngest"),
    (("COMPOSIO_",), "composio"),
    (("STEEL_",), "steel"),
    (("ELEVENLABS_",), "elevenlabs"),
    (("REVENUECAT_", "EXPO_PUBLIC_REVENUECAT_"), "revenuecat"),
    (("MIXPANEL_",), "mixpanel"),
    (("TIKTOK_",), "tiktok"),
    (("INSTAGRAM_", "META_", "FACEBOOK_"), "meta"),
    (("TWITTER_", "X_"), "x"),
    (("BLOTATO_",), "blotato"),
    (("AGENTMAIL_",), "agentmail"),
    (("PERPLEXITY_",), "perplexity"),
    (("REPLICATE_",), "replicate"),
    (("FIRECRAWL_",), "firecrawl"),
    (("TELEGRAM_", "LM_TELEGRAM_"), "telegram"),
    (("APP_STORE_CONNECT_", "ASC_", "APNS_"), "apple"),
    (("DEEPSEEK_",), "deepseek"),
    (("JUPITER_",), "jupiter"),
    (("SOLANA_",), "solana"),
    (("MEM0_",), "mem0"),
    (("MOLTBOOK_",), "moltbook"),
    (("PRINTFUL_",), "printful"),
    (("UNIPILE_",), "unipile"),
    (("EVM_",), "ethereum"),
)

INTERNAL_PREFIXES = (
    "ADMIN_",
    "ANICCA_",
    "ASK_",
    "INTERNAL_",
    "LM_",
    "PROXY_",
)

SECRET_ASSIGNMENT = re.compile(
    r"(?:api[_-]?key|auth[_-]?token|token|secret|password|cookie|authorization|"
    r"credential)[A-Z0-9_. -]*=\S+",
    re.IGNORECASE,
)
SECRET_SIGNATURE = re.compile(
    r"(?:\b(?:ghp|github_pat|xox[baprs]|AKIA)[-_][A-Za-z0-9]{8,}|"
    r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.|"
    r"\b(?:Bearer|Basic)\s+[A-Za-z0-9+/=_-]{8,})"
)
EMAIL_VALUE = re.compile(r"\b[^\s/@]+@[^\s/@]+\.[^\s/@]+\b")
RAW_HOME = re.compile(r"(?:/Users/[^/\t\n]+/|[A-Za-z]:\\Users\\[^\\\t\n]+\\)")
RAW_WINDOWS_PATH = re.compile(r"^[A-Za-z]:[\\/]")
RAW_PORTABLE_PATH = re.compile(
    r"(?:~[\\/]|[A-Za-z]:[\\/]|\\\\|(?<![A-Za-z0-9._@+/-])/+)",
    re.IGNORECASE,
)
DIGEST_VALUE = re.compile(r"^(?:sha256:(?:[0-9a-f]{8}:){7}[0-9a-f]{8}|unverified)$")
GIT_BLOB_OID = r"[0-9a-f]{40,64}"
REPOSITORY_EVIDENCE_LOCATOR = re.compile(
    rf"path:([A-Za-z0-9._@+/-]+);blob:{GIT_BLOB_OID};"
    r"line:[1-9][0-9]*;symbol:env\.[A-Z][A-Z0-9_]*"
)
OPENCLAW_EVIDENCE_LOCATOR = re.compile(
    r"openclaw-cli:(?:models-auth-list|cron-list-safe-projection;job:"
    r"[A-Za-z0-9][A-Za-z0-9._-]{0,127})"
)
LAUNCHD_EVIDENCE_LOCATOR = re.compile(
    rf"launchd-components:path:([^;,]+);blob:{GIT_BLOB_OID}"
    rf"(?:,path:([^;,]+);blob:{GIT_BLOB_OID})*"
    r"(?:;symbol:env\.[A-Z][A-Z0-9_]*)?"
)
SYSTEM_PORTABLE_PATH = re.compile(
    r"system:/(?:bin|usr|opt/homebrew|Library|Applications)"
    r"(?:/[A-Za-z0-9._@+:-]+)*"
)
PORTABLE_RELATIVE_PATH = re.compile(r"[A-Za-z0-9._@+-]+(?:/[A-Za-z0-9._@+:-]+)*")


def _valid_relative_locator_path(value: str) -> bool:
    return (
        PORTABLE_RELATIVE_PATH.fullmatch(value) is not None
        and all(part not in {".", ".."} for part in value.split("/"))
    )


def _valid_portable_locator_path(value: str) -> bool:
    if SYSTEM_PORTABLE_PATH.fullmatch(value) is not None:
        return True
    if value.startswith("~/"):
        return _valid_relative_locator_path(value[2:])
    return _valid_relative_locator_path(value)


def valid_credential_evidence_locator(value: str) -> bool:
    if OPENCLAW_EVIDENCE_LOCATOR.fullmatch(value) is not None:
        return True
    repository_match = REPOSITORY_EVIDENCE_LOCATOR.fullmatch(value)
    if repository_match is not None:
        return _valid_relative_locator_path(repository_match.group(1))
    if LAUNCHD_EVIDENCE_LOCATOR.fullmatch(value) is None:
        return False
    portable_paths = re.findall(r"(?:^|,)path:([^;,]+);blob:", value.removeprefix("launchd-components:"))
    return bool(portable_paths) and all(
        _valid_portable_locator_path(path) for path in portable_paths
    )


def compact(value: object) -> str:
    return re.sub(r"[\t\r\n]+", " ", str(value)).strip()


def format_sha256_digest(hex_digest: str) -> str:
    if re.fullmatch(r"[0-9a-f]{64}", hex_digest) is None:
        raise ValueError("sha256 digest must contain 64 lowercase hex characters")
    return "sha256:" + ":".join(
        hex_digest[index : index + 8] for index in range(0, 64, 8)
    )


def canonical_digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return format_sha256_digest(hashlib.sha256(encoded).hexdigest())


def parent_metadata_digest(parent: dict[str, str]) -> str:
    return canonical_digest({key: parent[key] for key in sorted(parent)})


def validate_exact_parent_map(
    parent_rows: list[dict[str, str]], review_manifest: dict[str, object]
) -> None:
    parent_ids = {row["inventory_id"] for row in parent_rows}
    reviewed = set(review_manifest.get("parents", {}))
    if parent_ids != reviewed:
        raise SystemExit(
            "review parent exact-match failure: "
            f"missing={sorted(parent_ids-reviewed)} extra={sorted(reviewed-parent_ids)}"
        )


def validate_revision_chain(
    parent_rows: list[dict[str, str]],
    observations: dict[str, object],
    review_manifest: dict[str, object],
) -> None:
    if review_manifest.get("schema_version") != 2 or review_manifest.get("review_status") != "approved":
        raise SystemExit("independent review approval required")
    if review_manifest.get("review_basis") != APPROVED_REVIEW_BASIS:
        raise SystemExit("approved review basis required")
    validate_exact_parent_map(parent_rows, review_manifest)
    observed = observations.get("parents", {})
    reviewed = review_manifest.get("parents", {})
    if not isinstance(observed, dict) or not isinstance(reviewed, dict):
        raise SystemExit("revision inputs require parent maps")
    validate_openclaw_revision_binding(parent_rows, observations)
    validate_cron_evidence_maps(parent_rows, observations, review_manifest)
    for parent in parent_rows:
        parent_id = parent["inventory_id"]
        digest = parent_metadata_digest(parent)
        observation = observed.get(parent_id)
        review = reviewed.get(parent_id)
        if not isinstance(observation, dict) or not isinstance(review, dict):
            raise SystemExit(f"{parent_id}: missing revision record")
        if observation.get("parent_metadata_digest") != digest or review.get(
            "parent_metadata_digest"
        ) != digest:
            raise SystemExit(f"{parent_id}: parent metadata digest mismatch")
        validate_parent_review_record(parent, observation, review)
        if compact(review.get("decision", "")) in {"none", "references"} and not parent_evidence_verified(
            parent, observation
        ):
            raise SystemExit(f"{parent_id}: review decision requires verified evidence")
    expected_observation_digest = review_manifest.get("approved_observation_digest")
    if expected_observation_digest != canonical_digest(observations):
        raise SystemExit("observation digest mismatch")


def validate_openclaw_revision_binding(
    parent_rows: list[dict[str, str]], observations: dict[str, object]
) -> None:
    revision = observations.get("openclaw_revision")
    if not isinstance(revision, dict) or set(revision) != {
        "version_digest", "schema_digest",
    }:
        raise SystemExit("OpenClaw revision binding mismatch")
    version_digest = revision.get("version_digest")
    schema_digest = revision.get("schema_digest")
    verified = all(
        isinstance(value, str)
        and value != "unverified"
        and DIGEST_VALUE.fullmatch(value) is not None
        for value in (version_digest, schema_digest)
    )
    unverified = version_digest == "unverified" and schema_digest == "unverified"
    if not verified and not unverified:
        raise SystemExit("OpenClaw revision binding mismatch")
    gateway_digest = (
        canonical_digest({"version": version_digest, "schema": schema_digest})
        if verified else "unverified"
    )
    observed = observations.get("parents", {})
    if not isinstance(observed, dict):
        raise SystemExit("OpenClaw revision binding mismatch")
    for parent in parent_rows:
        if parent.get("source_type") != "openclaw_cron":
            continue
        parent_id = parent["inventory_id"]
        observation = observed.get(parent_id)
        if (
            not isinstance(observation, dict)
            or observation.get("source_revision_digest") != gateway_digest
        ):
            raise SystemExit(f"{parent_id}: OpenClaw revision binding mismatch")
        source_locator = compact(observation.get("source_evidence_locator", ""))
        if unverified:
            if source_locator != "unverified":
                raise SystemExit(f"{parent_id}: OpenClaw revision binding mismatch")
            continue
        locator_parts = source_locator.rsplit(";schema:", 1)
        if (
            len(locator_parts) != 2
            or not locator_parts[0].startswith("openclaw:")
            or locator_parts[0] == "openclaw:unverified"
            or locator_parts[1] != schema_digest
            or canonical_digest(locator_parts[0].removeprefix("openclaw:"))
            != version_digest
        ):
            raise SystemExit(f"{parent_id}: OpenClaw revision binding mismatch")
    for map_field in ("cron_lookup_failures", "cron_absence_observations"):
        evidence_map = observations.get(map_field)
        if not isinstance(evidence_map, dict) or any(
            not isinstance(evidence, dict)
            or evidence.get("gateway_revision_digest") != gateway_digest
            for evidence in evidence_map.values()
        ):
            raise SystemExit("OpenClaw revision binding mismatch")


CRON_EVIDENCE_FIELDS = {
    "job_id", "result", "list_complete", "individual_get",
    "gateway_revision_digest", "observed_at",
}
CRON_FAILURE_CLASSES = {
    "auth_error", "timeout", "unstructured_not_found", "parse_error",
    "gateway_error", "invalid",
}


def validate_cron_evidence_record(
    parent_id: str, evidence: object, evidence_kind: str
) -> dict[str, object]:
    if (
        not isinstance(evidence, dict)
        or set(evidence) != CRON_EVIDENCE_FIELDS
        or evidence.get("job_id") != parent_id.removeprefix("openclaw:")
        or evidence.get("list_complete") is not True
        or not isinstance(evidence.get("observed_at"), str)
        or re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z",
            evidence.get("observed_at", ""),
        ) is None
    ):
        raise SystemExit(f"{parent_id}: invalid cron {evidence_kind} evidence")
    gateway_digest = evidence.get("gateway_revision_digest")
    if not isinstance(gateway_digest, str) or (
        gateway_digest != "unverified"
        and DIGEST_VALUE.fullmatch(gateway_digest) is None
    ):
        raise SystemExit(f"{parent_id}: invalid cron {evidence_kind} evidence")
    if evidence_kind == "absence" and (
        evidence.get("result") != "not_found"
        or evidence.get("individual_get") != "not_found"
        or gateway_digest == "unverified"
    ):
        raise SystemExit(f"{parent_id}: invalid cron absence evidence")
    if evidence_kind == "lookup failure" and (
        evidence.get("result") != "unverified"
        or evidence.get("individual_get") not in CRON_FAILURE_CLASSES
    ):
        raise SystemExit(f"{parent_id}: invalid cron lookup failure evidence")
    return evidence


def validate_cron_evidence_maps(
    parent_rows: list[dict[str, str]],
    observations: dict[str, object],
    review_manifest: dict[str, object],
) -> None:
    parents_by_id = {parent["inventory_id"]: parent for parent in parent_rows}
    observed = observations.get("parents", {})
    reviewed = review_manifest.get("parents", {})
    if not isinstance(observed, dict) or not isinstance(reviewed, dict):
        raise SystemExit("cron evidence requires parent maps")
    specifications = (
        ("cron_lookup_failures", "cron_lookup_failure", "lookup failure"),
        ("cron_absence_observations", "cron_absence_evidence", "absence"),
    )
    seen: set[str] = set()
    for map_field, parent_field, evidence_kind in specifications:
        evidence_map = observations.get(map_field)
        if not isinstance(evidence_map, dict):
            raise SystemExit(f"{map_field}: exact object map required")
        for parent_id, evidence in evidence_map.items():
            parent = parents_by_id.get(parent_id)
            if not isinstance(parent, dict) or parent.get("source_type") != "openclaw_cron":
                raise SystemExit(f"{parent_id}: invalid cron {evidence_kind} evidence")
            validate_cron_evidence_record(parent_id, evidence, evidence_kind)
        expected_ids = {
            parent_id
            for parent_id, record in observed.items()
            if isinstance(record, dict) and parent_field in record
        }
        if set(evidence_map) != expected_ids:
            raise SystemExit(f"cron {evidence_kind} map ID mismatch")
        for parent_id, evidence in evidence_map.items():
            parent = parents_by_id.get(parent_id)
            observation = observed.get(parent_id)
            review = reviewed.get(parent_id)
            if (
                not isinstance(parent, dict)
                or parent.get("source_type") != "openclaw_cron"
                or not isinstance(observation, dict)
                or not isinstance(review, dict)
            ):
                raise SystemExit(f"{parent_id}: invalid cron {evidence_kind} evidence")
            if observation.get(parent_field) != evidence:
                raise SystemExit(f"{parent_id}: cron {evidence_kind} map binding mismatch")
            if evidence.get("gateway_revision_digest") != observation.get(
                "source_revision_digest"
            ):
                raise SystemExit(f"{parent_id}: invalid cron {evidence_kind} evidence")
            if parent_id in seen:
                raise SystemExit(f"{parent_id}: conflicting cron evidence")
            seen.add(parent_id)
            expected_basis = (
                "stale_parent_live_job_not_found"
                if evidence_kind == "absence"
                else "cron_metadata_unavailable"
            )
            expected_locator = (
                "openclaw-cli:cron-list-complete+cron-get;job:"
                + str(evidence["job_id"])
                + ";result:"
                + str(evidence["individual_get"])
            )
            if (
                review.get(parent_field) != evidence
                or compact(review.get("decision", "")) != "unverified"
                or compact(review.get("decision_basis", "")) != expected_basis
                or compact(review.get("evidence_locator", "")) != expected_locator
            ):
                raise SystemExit(
                    f"{parent_id}: cron {evidence_kind} review binding mismatch"
                )


def validate_cron_absence_evidence(
    parent: dict[str, str], observation: dict[str, object], review: dict[str, object]
) -> None:
    parent_id = parent["inventory_id"]
    evidence = observation.get("cron_absence_evidence")
    if evidence is None:
        if "cron_absence_evidence" in review:
            raise SystemExit(f"{parent_id}: cron absence review binding mismatch")
        return
    validate_cron_evidence_record(parent_id, evidence, "absence")
    if (
        parent.get("source_type") != "openclaw_cron"
        or evidence.get("gateway_revision_digest") != observation.get("source_revision_digest")
    ):
        raise SystemExit(f"{parent_id}: invalid cron absence evidence")
    expected_locator = (
        "openclaw-cli:cron-list-complete+cron-get;job:"
        + evidence["job_id"] + ";result:not_found"
    )
    if (
        review.get("cron_absence_evidence") != evidence
        or compact(review.get("decision", "")) != "unverified"
        or compact(review.get("decision_basis", "")) != "stale_parent_live_job_not_found"
        or compact(review.get("evidence_locator", "")) != expected_locator
    ):
        raise SystemExit(f"{parent_id}: cron absence review binding mismatch")


def validate_cron_lookup_failure(
    parent: dict[str, str], observation: dict[str, object], review: dict[str, object]
) -> None:
    parent_id = parent["inventory_id"]
    evidence = observation.get("cron_lookup_failure")
    if evidence is None:
        if "cron_lookup_failure" in review:
            raise SystemExit(f"{parent_id}: cron lookup failure review binding mismatch")
        return
    validate_cron_evidence_record(parent_id, evidence, "lookup failure")
    expected_locator = (
        "openclaw-cli:cron-list-complete+cron-get;job:"
        + str(evidence["job_id"])
        + ";result:"
        + str(evidence["individual_get"])
    )
    if (
        parent.get("source_type") != "openclaw_cron"
        or evidence.get("gateway_revision_digest") != observation.get("source_revision_digest")
        or review.get("cron_lookup_failure") != evidence
        or compact(review.get("decision", "")) != "unverified"
        or compact(review.get("decision_basis", "")) != "cron_metadata_unavailable"
        or compact(review.get("evidence_locator", "")) != expected_locator
    ):
        raise SystemExit(f"{parent_id}: cron lookup failure review binding mismatch")


def validate_dynamic_derived_references(
    parent_id: str, job_locator: str, references: object
) -> list[dict[str, str]]:
    if not isinstance(references, list) or not references:
        raise SystemExit(f"{parent_id}: nonempty derived references required")
    normalized: list[dict[str, str]] = []
    identities: set[tuple[str, str, str]] = set()
    for reference in references:
        if not isinstance(reference, dict) or set(reference) != {
            "kind", "credential_object_id", "evidence_locator",
        }:
            raise SystemExit(f"{parent_id}: invalid derived reference")
        kind = compact(reference.get("kind", ""))
        object_id = compact(reference.get("credential_object_id", ""))
        locator = compact(reference.get("evidence_locator", ""))
        suffix_valid = (
            kind == "model" and re.fullmatch(re.escape(job_locator) + r"#model\[[0-9]+\]", locator)
            or kind == "delivery" and locator == job_locator + "#delivery"
            or kind == "tools" and locator == job_locator + "#tools-inherited"
        )
        if (
            kind not in {"model", "delivery", "tools"}
            or (object_id != "unverified" and re.fullmatch(r"credential:object-[0-9]{15}", object_id) is None)
            or not suffix_valid
        ):
            raise SystemExit(f"{parent_id}: invalid derived reference")
        identity = (kind, object_id, locator)
        if identity in identities:
            raise SystemExit(f"{parent_id}: unique derived references required")
        identities.add(identity)
        normalized.append({"kind": kind, "credential_object_id": object_id, "evidence_locator": locator})
    return normalized


def dynamic_openclaw_evidence_verified(
    parent_id: str, observation: dict[str, object]
) -> bool:
    cron = observation.get("cron_metadata")
    source_locator = compact(observation.get("source_evidence_locator", ""))
    config_locator = compact(observation.get("config_evidence_locator", ""))
    source_parts = source_locator.rsplit(";schema:", 1)
    return (
        observation.get("inspection_status") == "verified"
        and revisions_verified(observation)
        and isinstance(cron, dict)
        and cron.get("payload_kind") == "agentTurn"
        and len(source_parts) == 2
        and source_parts[0].startswith("openclaw:")
        and source_parts[0] != "openclaw:unverified"
        and DIGEST_VALUE.fullmatch(source_parts[1]) is not None
        and config_locator
        == "openclaw-cli:cron-list-safe-projection;job:"
        + parent_id.removeprefix("openclaw:")
    )


def validate_parent_review_record(
    parent: dict[str, str], observation: dict[str, object], review: dict[str, object]
) -> None:
    parent_id = parent["inventory_id"]
    decision = compact(review.get("decision", "review_required"))
    if decision == "review_required":
        raise SystemExit(f"{parent_id}: review_required cannot generate edges")
    if decision not in {"none", "references", "unverified", "dynamic_openclaw"}:
        raise SystemExit(f"{parent_id}: invalid per-parent review decision")
    for field in (
        "source_revision_digest", "config_revision_digest",
        "source_evidence_locator", "config_evidence_locator",
    ):
        if review.get(field) != observation.get(field):
            raise SystemExit(f"{parent_id}: review revision evidence mismatch")
    validate_cron_absence_evidence(parent, observation, review)
    validate_cron_lookup_failure(parent, observation, review)
    if decision == "none" and review.get("evidence_locator") != observation.get(
        "source_evidence_locator"
    ):
        raise SystemExit(f"{parent_id}: decision evidence mismatch")
    if decision == "references" and parent.get("source_type") == "launchd":
        source_locator = compact(observation.get("source_evidence_locator", ""))
        references = review.get("references", [])
        if review.get("evidence_locator") != source_locator or not isinstance(references, list):
            raise SystemExit(f"{parent_id}: reference evidence mismatch")
        for reference in references:
            credential_ref = compact(reference.get("credential_ref", "")) if isinstance(reference, dict) else ""
            expected = source_locator + ";symbol:env." + credential_ref.removeprefix("env:")
            if not isinstance(reference, dict) or reference.get("evidence_locator") != expected:
                raise SystemExit(f"{parent_id}: reference evidence mismatch")
    if decision == "dynamic_openclaw":
        if parent.get("source_type") != "openclaw_cron":
            raise SystemExit(f"{parent_id}: dynamic_openclaw is only valid for cron jobs")
        if not dynamic_openclaw_evidence_verified(parent_id, observation):
            raise SystemExit(f"{parent_id}: dynamic_openclaw requires verified evidence")
        required = {"job_evidence_locator": observation.get("config_evidence_locator")}
        if (
            not isinstance(required["job_evidence_locator"], str)
            or review.get("job_evidence_locator") != required["job_evidence_locator"]
        ):
            raise SystemExit(f"{parent_id}: job-specific review evidence required")
        validate_dynamic_derived_references(
            parent_id, required["job_evidence_locator"], review.get("derived_references")
        )
    if parent.get("source_type") in {"repository_entrypoint", "railway_entrypoint"} and decision == "references":
        evidence_records = observation.get("reference_evidence", [])
        references = review.get("references", [])
        if not isinstance(evidence_records, list) or not isinstance(references, list):
            raise SystemExit(f"{parent_id}: repository reference exact-match failure")
        evidence_by_name: dict[str, list[str]] = {}
        for record in evidence_records:
            if not isinstance(record, dict):
                raise SystemExit(f"{parent_id}: repository reference exact-match failure")
            name = compact(record.get("reference_name", ""))
            locator = compact(record.get("symbol_locator", ""))
            if not name or not locator:
                raise SystemExit(f"{parent_id}: repository reference exact-match failure")
            evidence_by_name.setdefault(name, []).append(locator)
        reviewed_names = [
            compact(reference.get("credential_ref", "")).removeprefix("env:")
            for reference in references
            if isinstance(reference, dict)
        ]
        if sorted(reviewed_names) != sorted(evidence_by_name):
            raise SystemExit(
                f"{parent_id}: repository reference exact-match failure: "
                "reference is not reachable from start entrypoint or observed reference omitted"
            )
        consumer = typed_locator(parent)
        account_alias = "unresolved:" + consumer
        expected: list[dict[str, str]] = []
        for name, locators in sorted(evidence_by_name.items()):
            credential_ref = f"env:{name}"
            provider = real_provider(provider_for(name))
            policy_status = (
                "policy_violation"
                if credential_ref == "env:CLAUDE_CODE_OAUTH_TOKEN"
                else "observed"
            )
            # One review object represents each unique credential reference. When the
            # import graph has multiple reads, the lexical minimum locator is the
            # deterministic evidence binding; every occurrence remains in observation.
            evidence_locator = min(locators)
            expected.append({
                "credential_object_id": credential_object_id(
                    provider, account_alias, credential_ref
                ),
                "provider": provider,
                "account_alias": account_alias,
                "credential_type": "env_ref",
                "credential_ref": credential_ref,
                "policy_status": policy_status,
                "policy_basis": (
                    "subscription_oauth" if policy_status == "policy_violation" else "none"
                ),
                "evidence_locator": evidence_locator,
                "consumer_locator": consumer,
                "permission_scope": permission_scope_for(name),
            })
        normalized: list[dict[str, str]] = []
        for reference in references:
            if not isinstance(reference, dict) or set(reference) != REVIEW_REFERENCE_FIELDS:
                raise SystemExit(
                    f"{parent_id}: repository reference exact-match failure: "
                    "reference is not reachable from start entrypoint or reviewed fields mismatch"
                )
            normalized.append({key: compact(reference.get(key, "")) for key in reference})
        if sorted(normalized, key=lambda item: item["credential_ref"]) != expected:
            raise SystemExit(
                f"{parent_id}: repository reference exact-match failure: "
                "reference is not reachable from start entrypoint or reviewed fields mismatch"
            )


def build_review_manifest(
    parent_rows: list[dict[str, str]], observations: dict[str, object]
) -> dict[str, object]:
    raise SystemExit("review manifest must be independently authored")


def _base_revision_fields(
    parent: dict[str, str], observation: dict[str, object] | None = None
) -> dict[str, str]:
    observation = observation or {}
    return {
        "parent_metadata_digest": parent_metadata_digest(parent),
        "source_revision_digest": compact(
            observation.get("source_revision_digest", "unverified")
        ),
        "config_revision_digest": compact(
            observation.get("config_revision_digest", "unverified")
        ),
    }


def credential_object_id(provider: str, account_alias: str, credential_ref: str) -> str:
    digest = hashlib.sha256(
        f"{provider}\0{account_alias}\0{credential_ref}".encode()
    ).hexdigest()[:24]
    return f"credential:object-{int(digest[:12], 16):015d}"


def _edge_base(
    parent: dict[str, str],
    observation: dict[str, object],
    *,
    suffix: str,
    dependency_status: str,
    object_id: str,
    consumer_locator: str,
    permission_scope: str,
    dependency_basis: str,
    evidence_locator: str,
) -> dict[str, str]:
    return {
        "loop_dependency_edge_id": f"{parent['inventory_id']}|{suffix}",
        "inventory_id": parent["inventory_id"],
        "loop_state": compact(parent.get("state", "unverified")),
        "dependency_status": dependency_status,
        "credential_object_id": object_id,
        "consumer_locator": consumer_locator,
        "permission_scope": permission_scope,
        "dependency_basis": dependency_basis,
        "evidence_locator": evidence_locator,
        **_base_revision_fields(parent, observation),
    }


def reviewed_parent_edges(
    parent: dict[str, str],
    observation: dict[str, object],
    review: dict[str, object],
    credential_objects: dict[str, object],
) -> list[dict[str, str]]:
    decision = compact(review.get("decision", "review_required"))
    basis = compact(review.get("decision_basis", "pending"))
    evidence = compact(review.get("evidence_locator", parent["inventory_id"]))
    if decision == "review_required":
        raise SystemExit(f"{parent['inventory_id']}: review_required cannot generate edges")
    if not parent_evidence_verified(parent, observation):
        return [
            _edge_base(
                parent,
                observation,
                suffix="dependency:unverified",
                dependency_status="unverified",
                object_id="unverified",
                consumer_locator=typed_locator(parent),
                permission_scope="unverified",
                dependency_basis="revision_unverified",
                evidence_locator="reviewed-revision:unverified",
            )
        ]
    if decision == "none":
        if review.get("references") != [] or basis in {"", "pending", "none"}:
            raise SystemExit(f"{parent['inventory_id']}: explicit none requires evidence")
        return [
            _edge_base(
                parent,
                observation,
                suffix="dependency:none",
                dependency_status="none_observed",
                object_id="none",
                consumer_locator=typed_locator(parent),
                permission_scope="none",
                dependency_basis=basis,
                evidence_locator=evidence,
            )
        ]
    if decision == "unverified":
        return [
            _edge_base(
                parent,
                observation,
                suffix="dependency:unverified",
                dependency_status="unverified",
                object_id="unverified",
                consumer_locator=typed_locator(parent),
                permission_scope="unverified",
                dependency_basis=basis,
                evidence_locator=evidence,
            )
        ]
    if decision != "references" or not isinstance(review.get("references"), list):
        raise SystemExit(f"{parent['inventory_id']}: invalid review decision")
    result: list[dict[str, str]] = []
    for reference in review["references"]:
        if not isinstance(reference, dict):
            raise SystemExit(f"{parent['inventory_id']}: invalid reviewed reference")
        object_id = compact(reference.get("credential_object_id", ""))
        if object_id not in credential_objects:
            raise SystemExit(f"{parent['inventory_id']}: missing credential object")
        result.append(
            _edge_base(
                parent,
                observation,
                suffix="dependency:" + object_id.removeprefix("credential:"),
                dependency_status=compact(credential_objects[object_id].get("policy_status", "observed")),
                object_id=object_id,
                consumer_locator=compact(reference.get("consumer_locator", typed_locator(parent))),
                permission_scope=compact(reference.get("permission_scope", "unverified")),
                dependency_basis=basis,
                evidence_locator=compact(reference.get("evidence_locator", evidence)),
            )
        )
    return result


def build_credential_objects(
    parent_rows: list[dict[str, str]],
    observations: dict[str, object],
    review_manifest: dict[str, object],
) -> dict[str, object]:
    objects: dict[str, dict[str, str]] = {}
    object_consumers: dict[str, str] = {}

    def insert_once(object_id: str, candidate: dict[str, str], consumer: str) -> None:
        expected_id = credential_object_id(
            candidate["provider"], candidate["account_alias"], candidate["credential_ref"]
        )
        if object_id != expected_id:
            raise SystemExit(f"{object_id}: noncanonical credential object ID")
        prior_consumer = object_consumers.get(object_id)
        if candidate["account_alias"].startswith("unresolved") and (
            prior_consumer is not None and prior_consumer != consumer
        ):
            raise SystemExit("unresolved account identity cannot be shared across consumers")
        if object_id in objects and objects[object_id] != candidate:
            raise SystemExit(f"{object_id}: conflicting credential object evidence")
        objects[object_id] = candidate
        object_consumers.setdefault(object_id, consumer)

    reviewed = review_manifest.get("parents", {})
    if isinstance(reviewed, dict):
        for record in reviewed.values():
            if not isinstance(record, dict):
                continue
            for reference in record.get("references", []) if isinstance(record.get("references"), list) else []:
                if not isinstance(reference, dict):
                    continue
                object_id = compact(reference.get("credential_object_id", ""))
                if object_id:
                    candidate = {
                        key: compact(reference.get(key, ""))
                        for key in (
                            "provider", "account_alias", "credential_type", "credential_ref",
                            "policy_status", "policy_basis", "evidence_locator",
                        )
                    }
                    consumer = compact(reference.get("consumer_locator", "unverified"))
                    insert_once(object_id, candidate, consumer)
    agents = observations.get("agents", {})
    audit = observations.get("openclaw_audit", {})
    audit_counts = audit.get("finding_counts", {}) if isinstance(audit, dict) else {}
    if isinstance(agents, dict):
        for agent_alias, agent in agents.items():
            if not isinstance(agent, dict):
                continue
            profiles = agent.get("profiles", [])
            for profile in profiles if isinstance(profiles, list) else []:
                if not isinstance(profile, dict):
                    continue
                provider = compact(profile.get("provider", ""))
                alias = compact(profile.get("alias", ""))
                profile_type = compact(profile.get("type", ""))
                ref = f"openclaw-auth:{provider}:{alias}"
                object_id = credential_object_id(provider, compact(agent_alias), ref)
                oauth_policy = profile_type == "oauth" and provider in SUBSCRIPTION_OAUTH_PROVIDERS
                plaintext_policy = (
                    isinstance(audit_counts, dict)
                    and int(audit_counts.get(f"PLAINTEXT_FOUND:{provider}", 0)) > 0
                )
                insert_once(object_id, {
                    "provider": provider,
                    "account_alias": compact(agent_alias),
                    "credential_type": profile_type,
                    "credential_ref": ref,
                    "policy_status": "policy_violation" if oauth_policy or plaintext_policy else "observed",
                    "policy_basis": "subscription_oauth" if oauth_policy else "plaintext_credential" if plaintext_policy else "none",
                    "evidence_locator": "openclaw-cli:models-auth-list",
                }, "catalog:" + compact(agent_alias))
    parent_observations = observations.get("parents", {})
    if isinstance(parent_observations, dict):
        for parent_id, observation in parent_observations.items():
            if not isinstance(observation, dict):
                continue
            cron = observation.get("cron_metadata")
            if not isinstance(cron, dict) or cron.get("enabled") is not True:
                continue
            provider = compact(cron.get("delivery_provider", "none"))
            if provider in {"none", "unverified"}:
                continue
            account_alias = f"unresolved:{parent_id}"
            credential_ref = f"openclaw-delivery:{provider}:{parent_id.removeprefix('openclaw:')}"
            object_id = credential_object_id(provider, account_alias, credential_ref)
            insert_once(object_id, {
                "provider": provider,
                "account_alias": account_alias,
                "credential_type": "delivery_ref",
                "credential_ref": credential_ref,
                "policy_status": "observed",
                "policy_basis": "none",
                "evidence_locator": (
                    "openclaw-cli:cron-list-safe-projection;job:"
                    + parent_id.removeprefix("openclaw:")
                ),
            }, parent_id + "#delivery")
    findings: dict[str, dict[str, object]] = {}
    counts = audit.get("finding_counts", {}) if isinstance(audit, dict) else {}
    if isinstance(counts, dict):
        for key, count in counts.items():
            if key.endswith(":unattributed") and isinstance(count, int) and count > 0:
                finding_id = "finding:openclaw-config:" + key.lower().replace(":", "-")
                findings[finding_id] = {
                    "finding_code": key.rsplit(":", 1)[0],
                    "scope_locator": "openclaw:config",
                    "occurrence_count": count,
                    "loop_dependency_attribution": "unresolved",
                }
    return {
        "schema_version": 2,
        "credential_objects": dict(sorted(objects.items())),
        "finding_objects": dict(sorted(findings.items())),
    }


def expected_openclaw_derived_references(
    parent: dict[str, str], observation: dict[str, object], agent: dict[str, object],
    credential_objects: dict[str, object],
) -> list[dict[str, str]]:
    cron = observation.get("cron_metadata")
    if not isinstance(cron, dict):
        return []
    model_refs: list[str] = []
    providers: list[str] = []
    model_ref = cron.get("model_ref")
    if isinstance(model_ref, str) and model_ref != "inherited":
        model_refs.append(model_ref)
    else:
        providers.extend(value for value in agent.get("provider_chain", []) if isinstance(value, str))
    model_refs.extend(value for value in cron.get("fallback_refs", []) if isinstance(value, str))
    providers.extend(value.split("/", 1)[0] for value in model_refs if "/" in value)
    providers = list(dict.fromkeys(providers))
    job_locator = compact(observation.get("config_evidence_locator", ""))
    result: list[dict[str, str]] = []
    for index, provider in enumerate(providers):
        object_ids = sorted(
            object_id for object_id, record in credential_objects.items()
            if isinstance(record, dict)
            and record.get("provider") == provider
            and record.get("account_alias") == observation.get("agent_alias")
        ) or ["unverified"]
        for object_id in object_ids:
            result.append({
                "kind": "model", "credential_object_id": object_id,
                "evidence_locator": f"{job_locator}#model[{index}]",
            })
    delivery_provider = compact(cron.get("delivery_provider", "none"))
    if cron.get("enabled") is True and delivery_provider not in {"none", "unverified"}:
        delivery_ids = sorted(
            object_id for object_id, record in credential_objects.items()
            if isinstance(record, dict)
            and record.get("provider") == delivery_provider
            and record.get("account_alias") == f"unresolved:{parent['inventory_id']}"
        )
        result.append({
            "kind": "delivery",
            "credential_object_id": delivery_ids[0] if len(delivery_ids) == 1 else "unverified",
            "evidence_locator": job_locator + "#delivery",
        })
    if cron.get("tools_inherited") is True:
        result.append({
            "kind": "tools", "credential_object_id": "unverified",
            "evidence_locator": job_locator + "#tools-inherited",
        })
    return result


def _openclaw_edges_from_review(
    parent: dict[str, str], observation: dict[str, object],
    credential_objects: dict[str, object], derived_references: list[dict[str, str]],
) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for reference in derived_references:
        kind = reference["kind"]
        object_id = reference["credential_object_id"]
        locator = reference["evidence_locator"]
        index_match = re.search(r"#model\[([0-9]+)\]$", locator)
        consumer = (
            f"{parent['inventory_id']}#model[{index_match.group(1)}]" if kind == "model" and index_match
            else f"{parent['inventory_id']}#delivery" if kind == "delivery"
            else f"{parent['inventory_id']}#tools"
        )
        scope = "model:inference" if kind == "model" else "message:send" if kind == "delivery" else "unverified"
        basis = "cron_model_route" if kind == "model" else "cron_delivery_route" if kind == "delivery" else "tools_inherited_unresolved"
        if object_id == "unverified" or object_id not in credential_objects:
            status, scope, object_id = "unverified", "unverified", "unverified"
            if kind != "tools":
                basis = "provider_credential_unresolved" if kind == "model" else "delivery_credential_unresolved"
        else:
            status = compact(credential_objects[object_id].get("policy_status", "observed"))
        edge = _edge_base(
            parent, observation,
            suffix=f"dependency:{kind}:" + object_id.removeprefix("credential:"),
            dependency_status=status, object_id=object_id, consumer_locator=consumer,
            permission_scope=scope, dependency_basis=basis, evidence_locator=locator,
        )
        edge["loop_state"] = "enabled"
        result.append(edge)
    return result


def openclaw_parent_edges(
    parent: dict[str, str],
    observation: dict[str, object],
    credential_objects: dict[str, object],
    derived_references: list[dict[str, str]],
    review: dict[str, object],
) -> list[dict[str, str]]:
    cron = observation.get("cron_metadata")
    if (
        observation.get("inspection_status") != "verified"
        or not revisions_verified(observation)
        or compact(review.get("decision", "")) != "dynamic_openclaw"
        or not isinstance(cron, dict)
        or cron.get("payload_kind") != "agentTurn"
    ):
        return [
            _edge_base(
                parent, observation, suffix="dependency:unverified",
                dependency_status="unverified", object_id="unverified",
                consumer_locator=parent["inventory_id"], permission_scope="unverified",
                dependency_basis=compact(observation.get("reason", "cron_metadata_unavailable")),
                evidence_locator="openclaw-cli:cron-list-safe-projection",
            )
        ]
    if cron.get("enabled") is False:
        edge = _edge_base(
                parent, observation, suffix="dependency:inactive",
                dependency_status="inactive", object_id="none",
                consumer_locator=parent["inventory_id"], permission_scope="none",
                dependency_basis="loop_disabled",
                evidence_locator=compact(observation.get("config_evidence_locator", "")),
            )
        edge["loop_state"] = "disabled"
        return [edge]
    if cron.get("enabled") is not True:
        return [
            _edge_base(
                parent, observation, suffix="dependency:unverified",
                dependency_status="unverified", object_id="unverified",
                consumer_locator=parent["inventory_id"], permission_scope="unverified",
                dependency_basis=compact(observation.get("reason", "cron_metadata_unavailable")),
                evidence_locator="openclaw-cli:cron-list-safe-projection",
            )
        ]
    return _openclaw_edges_from_review(
        parent, observation, credential_objects, derived_references
    )


def build_loop_dependency_edges(
    parent_rows: list[dict[str, str]], observations: dict[str, object],
    review_manifest: dict[str, object], objects_artifact: dict[str, object],
) -> list[dict[str, str]]:
    observed = observations.get("parents", {})
    reviewed = review_manifest.get("parents", {})
    objects = objects_artifact.get("credential_objects", {})
    agents = observations.get("agents", {})
    if not all(isinstance(value, dict) for value in (observed, reviewed, objects, agents)):
        raise SystemExit("invalid object/edge inputs")
    result: list[dict[str, str]] = []
    for parent in parent_rows:
        observation = observed.get(parent["inventory_id"], {})
        review = reviewed.get(parent["inventory_id"], {})
        if not isinstance(observation, dict) or not isinstance(review, dict):
            raise SystemExit(f"{parent['inventory_id']}: missing observation or review")
        validate_parent_review_record(parent, observation, review)
        if parent["source_type"] == "openclaw_cron":
            agent = agents.get(observation.get("agent_alias"), {})
            reviewed_references = review.get("derived_references", [])
            if compact(review.get("decision", "")) == "dynamic_openclaw":
                expected = expected_openclaw_derived_references(
                    parent, observation, agent if isinstance(agent, dict) else {}, objects
                )
                if sorted(expected, key=canonical_digest) != sorted(reviewed_references, key=canonical_digest):
                    raise SystemExit(f"{parent['inventory_id']}: derived reference set mismatch")
            result.extend(openclaw_parent_edges(
                parent, observation, objects, reviewed_references, review
            ))
        else:
            result.extend(reviewed_parent_edges(parent, observation, review, objects))
    return sorted(result, key=lambda row: row["loop_dependency_edge_id"])


def validate_edge_revision_alignment(
    edges: list[dict[str, str]], observations: dict[str, object]
) -> None:
    parents = observations.get("parents", {})
    if not isinstance(parents, dict):
        raise SystemExit("observations require parent map")
    for edge in edges:
        parent_id = edge.get("inventory_id", "")
        observation = parents.get(parent_id)
        if not isinstance(observation, dict):
            raise SystemExit(f"{parent_id}: missing observation revision")
        for field, label in (
            ("parent_metadata_digest", "parent metadata digest mismatch"),
            ("source_revision_digest", "source revision digest mismatch"),
            ("config_revision_digest", "config revision digest mismatch"),
        ):
            if edge.get(field) != observation.get(field):
                raise SystemExit(f"{parent_id}: {label}")


def validate_credential_objects(artifact: dict[str, object]) -> None:
    if artifact.get("schema_version") != 2:
        raise SystemExit("credential objects: invalid schema_version")
    objects = artifact.get("credential_objects")
    findings = artifact.get("finding_objects")
    if not isinstance(objects, dict) or not isinstance(findings, dict):
        raise SystemExit("credential objects: invalid object maps")
    plaintext_finding_present = any(
        isinstance(record, dict) and record.get("finding_code") == "PLAINTEXT_FOUND"
        for record in findings.values()
    )
    plaintext_objects = 0
    for object_id, record in objects.items():
        if not re.fullmatch(r"credential:object-[0-9]{15}", object_id) or not isinstance(record, dict):
            raise SystemExit(f"{object_id}: invalid credential object")
        required = {
            "provider", "account_alias", "credential_type", "credential_ref",
            "policy_status", "policy_basis", "evidence_locator",
        }
        if required != set(record) or any(not compact(record[field]) for field in required):
            raise SystemExit(f"{object_id}: invalid credential object fields")
        for field in required:
            value = compact(record[field])
            if field == "evidence_locator":
                if not valid_credential_evidence_locator(value):
                    raise SystemExit(f"{object_id}: invalid evidence locator")
                continue
            if RAW_PORTABLE_PATH.search(value):
                raise SystemExit(f"{object_id}: raw absolute or home path")
        if record["provider"] not in REAL_PROVIDERS - {"none", "unverified"}:
            raise SystemExit(f"{object_id}: invalid credential provider")
        if record["credential_type"] not in CREDENTIAL_TYPES:
            raise SystemExit(f"{object_id}: invalid credential type")
        if record["policy_status"] not in {"observed", "policy_violation"}:
            raise SystemExit(f"{object_id}: invalid credential policy status")
        policy_tuple = (compact(record["policy_status"]), compact(record["policy_basis"]))
        if (
            record["credential_type"] == "oauth"
            and record["provider"] in SUBSCRIPTION_OAUTH_PROVIDERS
            and policy_tuple != ("policy_violation", "subscription_oauth")
        ):
            raise SystemExit(f"{object_id}: subscription OAuth policy mismatch")
        if "plaintext_credential" in policy_tuple:
            if policy_tuple != ("policy_violation", "plaintext_credential"):
                raise SystemExit(f"{object_id}: plaintext credential policy mismatch")
            plaintext_objects += 1
        elif policy_tuple == ("policy_violation", "none") and plaintext_finding_present:
            raise SystemExit(f"{object_id}: plaintext credential policy mismatch")
        elif policy_tuple not in {
            ("observed", "none"), ("policy_violation", "subscription_oauth")
        }:
            raise SystemExit(f"{object_id}: invalid credential policy tuple")
        expected_object_id = credential_object_id(
            compact(record["provider"]), compact(record["account_alias"]),
            compact(record["credential_ref"]),
        )
        if object_id != expected_object_id:
            raise SystemExit(f"{object_id}: noncanonical credential object ID")
        joined = "\t".join(compact(record[field]) for field in required)
        if SECRET_ASSIGNMENT.search(joined) or SECRET_SIGNATURE.search(joined) or EMAIL_VALUE.search(joined):
            raise SystemExit(f"{object_id}: possible secret-like value")
    finding_fields = {
        "finding_code", "scope_locator", "occurrence_count",
        "loop_dependency_attribution",
    }
    allowed_finding_codes = {
        "PLAINTEXT_FOUND", "REF_UNRESOLVED", "REF_SHADOWED", "LEGACY_RESIDUE",
    }
    for finding_id, record in findings.items():
        if not isinstance(record, dict) or set(record) != finding_fields:
            raise SystemExit(f"{finding_id}: invalid finding object fields")
        finding_code = compact(record.get("finding_code", ""))
        if finding_code not in allowed_finding_codes:
            raise SystemExit(f"{finding_id}: unknown finding code")
        expected_id = f"finding:openclaw-config:{finding_code.lower()}-unattributed"
        if finding_id != expected_id:
            raise SystemExit(f"{finding_id}: invalid finding object ID")
        if not isinstance(record.get("occurrence_count"), int) or record["occurrence_count"] <= 0:
            raise SystemExit(f"{finding_id}: positive occurrence_count required")
        locator = compact(record.get("scope_locator", ""))
        if RAW_HOME.search(locator) or str(HOME) in locator:
            raise SystemExit(f"{finding_id}: unsafe finding locator")
        if locator != "openclaw:config" or compact(
            record.get("loop_dependency_attribution", "")
        ) != "unresolved":
            raise SystemExit(f"{finding_id}: invalid finding tuple")
        joined = "\t".join(compact(value) for value in record.values())
        if SECRET_ASSIGNMENT.search(joined) or SECRET_SIGNATURE.search(joined) or EMAIL_VALUE.search(joined):
            raise SystemExit(f"{finding_id}: possible secret-like value")
    if plaintext_objects and not plaintext_finding_present:
        raise SystemExit("credential objects: plaintext finding required")


def validate_loop_dependency_edges(
    edges: list[dict[str, str]],
    parent_ids: set[str],
    observations: dict[str, object],
    objects_artifact: dict[str, object],
    review_manifest: dict[str, object] | None = None,
) -> None:
    objects = objects_artifact.get("credential_objects", {})
    if not isinstance(objects, dict):
        raise SystemExit("invalid credential object map")
    observed_parents = observations.get("parents", {})
    if not isinstance(observed_parents, dict):
        raise SystemExit("observations require parent map")
    ids = [edge.get("loop_dependency_edge_id", "") for edge in edges]
    if len(ids) != len(set(ids)):
        raise SystemExit("duplicate loop_dependency_edge_id")
    covered = {edge.get("inventory_id", "") for edge in edges}
    if covered != parent_ids:
        raise SystemExit("loop dependency parent coverage mismatch")
    allowed_status = {"observed", "none_observed", "unverified", "policy_violation", "inactive"}
    for edge in edges:
        edge_id = edge.get("loop_dependency_edge_id", "")
        missing = [field for field in EDGE_FIELDS if not compact(edge.get(field, ""))]
        if missing:
            raise SystemExit(f"{edge_id}: empty edge fields: {','.join(missing)}")
        if set(edge) != set(EDGE_FIELDS):
            raise SystemExit(f"{edge_id}: invalid edge schema")
        if edge["dependency_status"] not in allowed_status:
            raise SystemExit(f"{edge_id}: invalid dependency_status")
        if re.fullmatch(
            r"(?:enabled|disabled|loaded(?:;declared_entrypoint_missing)?|installed_not_loaded|"
            r"declared_in_repository(?:;runtime_not_verified_here)?|present_on_origin_[a-z0-9_-]+;deployment_health_not_part_of_TODO_1|"
            r"parse_error:[A-Za-z0-9_-]+)",
            edge["loop_state"],
        ) is None:
            raise SystemExit(f"{edge_id}: invalid loop_state")
        if edge["permission_scope"] == "api:access":
            raise SystemExit(f"{edge_id}: imprecise permission scope")
        object_id = edge["credential_object_id"]
        if edge["dependency_status"] in {"observed", "policy_violation"} and object_id not in objects:
            raise SystemExit(f"{edge_id}: missing credential object")
        if edge["dependency_status"] in {"observed", "policy_violation"} and edge[
            "permission_scope"
        ] in {"none", "unverified"}:
            raise SystemExit(f"{edge_id}: concrete permission scope required")
        if (
            edge["inventory_id"].startswith("openclaw:")
            and edge["dependency_status"] in {"observed", "policy_violation"}
        ):
            parent_observation = observed_parents.get(edge["inventory_id"], {})
            cron = (
                parent_observation.get("cron_metadata")
                if isinstance(parent_observation, dict) else None
            )
            if (
                not isinstance(parent_observation, dict)
                or parent_observation.get("inspection_status") != "verified"
                or not revisions_verified(parent_observation)
                or not isinstance(cron, dict)
                or cron.get("enabled") is not True
                or cron.get("payload_kind") != "agentTurn"
                or edge["loop_state"] != "enabled"
            ):
                raise SystemExit(
                    f"{edge_id}: OpenClaw observed edge requires verified live cron provenance"
                )
            reviewed_parents = (
                review_manifest.get("parents", {})
                if isinstance(review_manifest, dict) else {}
            )
            reviewed_parent = (
                reviewed_parents.get(edge["inventory_id"])
                if isinstance(reviewed_parents, dict) else None
            )
            derived = (
                reviewed_parent.get("derived_references")
                if isinstance(reviewed_parent, dict) else None
            )
            locator = edge["evidence_locator"]
            kind = (
                "model" if re.search(r"#model\[[0-9]+\]$", locator)
                else "delivery" if locator.endswith("#delivery")
                else "tools" if locator.endswith("#tools-inherited")
                else ""
            )
            exact_matches = []
            locator_object_matches = []
            if isinstance(derived, list):
                for reference in derived:
                    if not isinstance(reference, dict):
                        continue
                    if (
                        reference.get("credential_object_id") == object_id
                        and reference.get("evidence_locator") == locator
                    ):
                        locator_object_matches.append(reference)
                        if reference.get("kind") == kind:
                            exact_matches.append(reference)
            if (
                not isinstance(reviewed_parent, dict)
                or compact(reviewed_parent.get("decision", "")) != "dynamic_openclaw"
                or len(exact_matches) != 1
                or len(locator_object_matches) != 1
            ):
                raise SystemExit(
                    f"{edge_id}: OpenClaw edge derived reference mismatch"
                )
        if edge["dependency_status"] in {"none_observed", "inactive"} and (
            object_id != "none" or edge["permission_scope"] != "none"
        ):
            raise SystemExit(f"{edge_id}: {edge['dependency_status']} requires none object and scope")
        if edge["dependency_status"] == "unverified" and (
            object_id != "unverified" or edge["permission_scope"] != "unverified"
        ):
            raise SystemExit(f"{edge_id}: unverified requires unverified object and scope")
        if edge["dependency_status"] == "inactive":
            parent_observation = observed_parents.get(edge["inventory_id"], {})
            cron = parent_observation.get("cron_metadata") if isinstance(parent_observation, dict) else None
            if edge["loop_state"] != "disabled" or not isinstance(cron, dict) or cron.get("enabled") is not False:
                raise SystemExit(f"{edge_id}: inactive requires disabled live cron")
            if edge["inventory_id"].startswith("openclaw:"):
                reviewed_parents = (
                    review_manifest.get("parents", {})
                    if isinstance(review_manifest, dict) else {}
                )
                reviewed_parent = (
                    reviewed_parents.get(edge["inventory_id"])
                    if isinstance(reviewed_parents, dict) else None
                )
                revision_fields_match = (
                    isinstance(reviewed_parent, dict)
                    and all(
                        reviewed_parent.get(field) == parent_observation.get(field)
                        for field in (
                            "source_revision_digest", "config_revision_digest",
                            "source_evidence_locator", "config_evidence_locator",
                        )
                    )
                )
                config_locator = compact(
                    parent_observation.get("config_evidence_locator", "")
                ) if isinstance(parent_observation, dict) else ""
                try:
                    reviewed_references_valid = (
                        isinstance(reviewed_parent, dict)
                        and bool(validate_dynamic_derived_references(
                            edge["inventory_id"], config_locator,
                            reviewed_parent.get("derived_references"),
                        ))
                    )
                except SystemExit:
                    reviewed_references_valid = False
                if (
                    not isinstance(parent_observation, dict)
                    or not dynamic_openclaw_evidence_verified(
                        edge["inventory_id"], parent_observation
                    )
                    or not isinstance(reviewed_parent, dict)
                    or compact(reviewed_parent.get("decision", ""))
                    != "dynamic_openclaw"
                    or compact(reviewed_parent.get("decision_basis", ""))
                    != "official_cli_safe_projection"
                    or not revision_fields_match
                    or reviewed_parent.get("job_evidence_locator") != config_locator
                    or reviewed_parent.get("evidence_locator") != config_locator
                    or edge["evidence_locator"] != config_locator
                    or not reviewed_references_valid
                ):
                    raise SystemExit(
                        f"{edge_id}: inactive requires verified OpenClaw review provenance"
                    )
        if edge["dependency_status"] in {"observed", "policy_violation"} and (
            objects[object_id].get("policy_status") != edge["dependency_status"]
        ):
            raise SystemExit(f"{edge_id}: object policy_status mismatch")
        joined = "\t".join(edge[field] for field in EDGE_FIELDS)
        if RAW_HOME.search(joined) or str(HOME) in joined:
            raise SystemExit(f"{edge_id}: raw home path")
        if SECRET_ASSIGNMENT.search(joined) or SECRET_SIGNATURE.search(joined) or EMAIL_VALUE.search(joined):
            raise SystemExit(f"{edge_id}: possible secret-like value")
        for field in ("parent_metadata_digest", "source_revision_digest", "config_revision_digest"):
            if not DIGEST_VALUE.fullmatch(edge[field]):
                raise SystemExit(f"{edge_id}: invalid {field}")
    validate_edge_revision_alignment(edges, observations)


def revisions_verified(observation: dict[str, object]) -> bool:
    return all(
        isinstance(value := observation.get(field), str)
        and value != "unverified"
        and DIGEST_VALUE.fullmatch(value) is not None
        for field in ("source_revision_digest", "config_revision_digest")
    )


def parent_evidence_verified(
    parent: dict[str, str], observation: dict[str, object]
) -> bool:
    if not revisions_verified(observation):
        return False
    if parent.get("source_type") in {"repository_entrypoint", "railway_entrypoint"}:
        return observation.get("reference_inspection_status") == "verified"
    return True


def public_path(path: Path) -> str:
    try:
        return path.relative_to(REPO).as_posix()
    except ValueError:
        pass
    text = str(path)
    home = str(HOME)
    if text == home:
        return "~"
    if text.startswith(home + "/"):
        return "~" + text[len(home) :]
    return text


def provider_for(name: str) -> str:
    if name in {"DATABASE_URL", "POSTGRES_URL", "MONGODB_URI"}:
        return "database"
    if name == "REDIS_URL":
        return "redis"
    for prefixes, provider in PROVIDER_PREFIXES:
        if name.startswith(prefixes):
            return provider
    if name.startswith(INTERNAL_PREFIXES):
        return "internal"
    raise SystemExit(f"reviewed credential has no provider classification: {name}")


def typed_locator(parent: dict[str, str]) -> str:
    source_type = compact(parent.get("source_type", ""))
    inventory_id = compact(parent.get("inventory_id", ""))
    if source_type == "launchd" and inventory_id.startswith("launchd:"):
        return inventory_id
    if source_type == "repository_entrypoint" and inventory_id.startswith("package:"):
        return "repo:" + inventory_id.removeprefix("package:")
    if source_type == "railway_entrypoint":
        evidence = compact(parent.get("evidence", ""))
        match = re.fullmatch(
            r"https://github\.com/[^/]+/[^/]+/blob/([^/]+)/(.+package\.json)",
            evidence,
        )
        if not match:
            raise SystemExit(f"{inventory_id}: invalid Railway parent evidence locator")
        branch, manifest = match.groups()
        state = compact(parent.get("state", ""))
        if f"present_on_origin_{branch}" not in state:
            raise SystemExit(f"{inventory_id}: Railway revision not established by parent")
        return f"git:origin/{branch}:{manifest}#start"
    if source_type == "openclaw_cron":
        entrypoint = compact(parent.get("entrypoint", ""))
        match = re.fullmatch(r"openclaw_gateway:agentTurn:agent=([a-z0-9][a-z0-9-]*)", entrypoint)
        if not match:
            raise SystemExit(f"{inventory_id}: invalid OpenClaw agent metadata")
        return f"openclaw:agent:{match.group(1)}"
    raise SystemExit(f"{inventory_id}: unknown or malformed source_type={source_type}")


def real_provider(provider: str) -> str:
    return {"database": "postgresql", "internal": "anicca-api"}.get(provider, provider)


PERMISSION_SCOPE_BY_REFERENCE = {
    "ANICCA_AGENT_TOKEN": "agent:invoke",
    "ANICCA_AGENT_TOKEN_OLD": "agent:invoke",
    "ANICCA_PEER_TOKEN": "peer:invoke",
    "ASK_TOKEN": "service:invoke",
    "APNS_KEY_ID": "push:key_identify",
    "APNS_PRIVATE_KEY_P8": "push:sign",
    "BLOTATO_API_KEY": "content:publish",
    "CLAUDE_CODE_OAUTH_TOKEN": "model:inference",
    "COMPOSIO_API_KEY": "integration:execute",
    "DATABASE_URL": "database:connect",
    "DEEPSEEK_API_KEY": "model:inference",
    "EVM_PRIVATE_KEY": "wallet:sign",
    "EXPO_PUBLIC_REVENUECAT_ANDROID_API_KEY": "purchase:identify",
    "EXPO_PUBLIC_REVENUECAT_IOS_API_KEY": "purchase:identify",
    "EXPO_PUBLIC_REVENUECAT_TEST_API_KEY": "purchase:identify",
    "GEMINI_API_KEY": "model:inference",
    "GOG_KEYRING_PASSWORD": "keyring:unlock",
    "GOOGLE_API_KEY": "model:inference",
    "INTERNAL_API_TOKEN": "service:invoke",
    "INTERNAL_AUTH_SECRET": "token:sign_verify",
    "JUPITER_API_KEY": "dex:quote_read",
    "LM_CALL_SECRET": "call:authenticate",
    "LM_INBOUND_SECRET": "webhook:verify",
    "LM_TELEGRAM_BOT_TOKEN": "message:read_write",
    "LM_TELEGRAM_WEBHOOK_SECRET": "webhook:verify",
    "LM_UID_SECRET": "subject:derive",
    "MEM0_API_KEY": "memory:read_write",
    "MOLTBOOK_ACCESS_TOKEN": "content:publish",
    "OPENAI_API_KEY": "model:inference",
    "PROXY_AUTH_JWT_SECRET": "token:sign_verify",
    "PROXY_GUEST_JWT_SECRET": "token:sign_verify",
    "RESEND_API_KEY": "email:send",
    "REVENUECAT_REST_API_KEY": "subscriber:read_write",
    "REVENUECAT_WEBHOOK_SECRET": "webhook:verify",
    "SLACK_APP_TOKEN": "socket:connect",
    "SLACK_BOT_TOKEN": "message:read_write",
    "SLACK_METRICS_WEBHOOK_URL": "message:send",
    "SLACK_WEBHOOK_AGENTS": "message:send",
    "SLACK_WEBHOOK_URL": "message:send",
    "SOLANA_PRIVATE_KEY": "wallet:sign",
    "STRIPE_SECRET_KEY": "payment:read_write",
    "STRIPE_WEBHOOK_SECRET": "webhook:verify",
    "SUPABASE_SERVICE_ROLE_KEY": "database:admin",
    "TELEGRAM_BOT_TOKEN": "message:read_write",
    "TELNYX_API_KEY": "call:manage",
    "TWILIO_ACCOUNT_SID": "account:identify",
    "TWILIO_AUTH_TOKEN": "call:manage",
    "UNIPILE_NOTIFY_SECRET": "webhook:verify",
    "UNIPILE_TOKEN": "message:read_write",
    "X_BEARER_TOKEN": "social:read",
}


def permission_scope_for(reference_name: str) -> str:
    try:
        return PERMISSION_SCOPE_BY_REFERENCE[reference_name]
    except KeyError as error:
        raise SystemExit(
            f"reviewed credential has no precise permission scope: {reference_name}"
        ) from error


def read_parent(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        result = list(csv.DictReader(handle, delimiter="\t"))
    validate_parent_rows(result)
    return result


def read_json(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise SystemExit(f"{public_path(path)}: expected JSON object")
    return value


def validate_parent_rows(parent_rows: list[dict[str, str]]) -> None:
    required = {"inventory_id", "source_type", "entrypoint"}
    for index, row in enumerate(parent_rows, start=2):
        missing = sorted(field for field in required if not compact(row.get(field, "")))
        if missing:
            raise SystemExit(f"parent line {index}: empty fields: {','.join(missing)}")
    parent_ids = [row["inventory_id"] for row in parent_rows]
    if len(parent_ids) != len(set(parent_ids)):
        raise SystemExit("duplicate parent inventory_id detected")


def run_self_tests() -> None:
    assert provider_for("SUPABASE_SERVICE_ROLE_KEY") == "supabase"
    assert provider_for("STRIPE_SECRET_KEY") == "stripe"
    assert permission_scope_for("SUPABASE_SERVICE_ROLE_KEY") == "database:admin"
    assert credential_object_id(
        "supabase", "fixture", "env:SUPABASE_SERVICE_ROLE_KEY"
    ).startswith("credential:object-")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parent", type=Path, default=DEFAULT_PARENT)
    parser.add_argument("--observations", type=Path, default=DEFAULT_OBSERVATIONS)
    parser.add_argument("--review", type=Path, default=DEFAULT_REVIEW)
    parser.add_argument("--objects", type=Path, default=DEFAULT_OBJECTS)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.check or args.self_test:
        run_self_tests()
    if args.self_test and not args.check:
        print("self-tests: PASS", file=sys.stderr)
        return
    parent_rows = read_parent(args.parent)
    observations = read_json(args.observations)
    review_manifest = read_json(args.review)
    validate_revision_chain(parent_rows, observations, review_manifest)
    expected_objects = build_credential_objects(parent_rows, observations, review_manifest)
    objects_artifact = read_json(args.objects)
    if canonical_digest(objects_artifact) != canonical_digest(expected_objects):
        raise SystemExit("credential objects artifact is stale")
    validate_credential_objects(objects_artifact)
    result = build_loop_dependency_edges(
        parent_rows, observations, review_manifest, objects_artifact
    )
    validate_loop_dependency_edges(
        result,
        {row["inventory_id"] for row in parent_rows},
        observations,
        objects_artifact,
        review_manifest,
    )
    output_handle = args.output.open("w", encoding="utf-8", newline="") if args.output else sys.stdout
    writer = csv.DictWriter(output_handle, fieldnames=EDGE_FIELDS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows(result)
    if args.output:
        output_handle.close()
    if args.check:
        print(
            json.dumps(
                {
                    "parents": len(parent_rows),
                    "rows": len(result),
                    "by_status": dict(sorted(Counter(row["dependency_status"] for row in result).items())),
                    "credential_objects": len(objects_artifact["credential_objects"]),
                    "finding_objects": len(objects_artifact["finding_objects"]),
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
