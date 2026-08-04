#!/usr/bin/env python3
"""Build immutable, comparable creative-treatment manifests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Iterable


PLAN_FIELDS = (
    "experiment_id", "creative_id", "product_id", "account_id", "hook_id",
    "hook_text", "tactic_id", "renderer_id", "cta", "destination_url",
)
CONFIG_FIELDS = (
    "cohort_id", "product_id", "account_id", "tactic_id", "renderer_id",
    "renderer_version", "renderer_source_path", "body_template_id", "body_text", "voice",
    "voice_rate", "caption_style_id", "clip_paths", "target_duration_seconds",
)
LOCKED_COHORT_FIELDS = (
    "cohort_id", "product_id", "account_id", "tactic_id", "renderer_id",
    "renderer_version", "renderer_source_path", "renderer_source_sha256",
    "body_template_id", "body_text", "voice",
    "voice_rate", "caption_style_id", "clip_set", "target_duration_seconds",
    "cta", "destination_url",
)


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_id(prefix: str, values: Iterable[str]) -> str:
    return f"{prefix}.{hashlib.sha256(chr(0).join(values).encode()).hexdigest()[:24]}"


def _require_fields(row: dict[str, Any], fields: Iterable[str], label: str) -> None:
    for field in fields:
        if field not in row or row[field] in (None, "", []):
            raise ValueError(f"{label} missing {field}")


def build_manifest(plan: dict[str, Any], config: dict[str, Any], *,
                   asset_path: Path, duration_seconds: float) -> dict[str, Any]:
    """Freeze a rendered treatment after every causal input is verifiable."""
    _require_fields(plan, PLAN_FIELDS, "experiment plan")
    _require_fields(config, CONFIG_FIELDS, "treatment config")
    if plan.get("schema_version") != "marketing.experiment-plan.v1":
        raise ValueError("unsupported experiment plan schema")
    if config.get("schema_version") != "marketing.cohort-treatment-config.v1":
        raise ValueError("unsupported treatment config schema")
    for field in ("product_id", "account_id", "tactic_id", "renderer_id"):
        if plan[field] != config[field]:
            raise ValueError(f"experiment plan {field} does not match frozen config")

    limits = config["target_duration_seconds"]
    if (not isinstance(limits, dict) or not isinstance(limits.get("min"), (int, float))
            or not isinstance(limits.get("max"), (int, float))
            or limits["min"] > limits["max"]):
        raise ValueError("invalid target_duration_seconds")
    if not limits["min"] <= duration_seconds <= limits["max"]:
        raise ValueError("duration outside frozen band")

    clips = []
    for raw_path in config["clip_paths"]:
        path = Path(raw_path)
        if not path.is_file():
            raise ValueError(f"missing frozen clip: {path}")
        clips.append({"path": str(path), "sha256": sha256_file(path)})
    renderer_source = Path(config["renderer_source_path"])
    if not renderer_source.is_file():
        raise ValueError("renderer source missing")
    asset_path = Path(asset_path)
    if not asset_path.is_file():
        raise ValueError("rendered asset missing")

    full_script = f'{plan["hook_text"]}{config["body_text"]}{plan["cta"]}'
    causal_identity = {
        "cohort_id": config["cohort_id"],
        "experiment_id": plan["experiment_id"],
        "hook_id": plan["hook_id"],
        "hook_text": plan["hook_text"],
        "body_template_id": config["body_template_id"],
        "body_text": config["body_text"],
        "voice": config["voice"],
        "voice_rate": config["voice_rate"],
        "caption_style_id": config["caption_style_id"],
        "renderer_version": config["renderer_version"],
        "renderer_source_sha256": sha256_file(renderer_source),
        "clip_set": clips,
        "cta": plan["cta"],
        "destination_url": plan["destination_url"],
    }
    return {
        "schema_version": "marketing.cohort-treatment.v1",
        "treatment_id": stable_id("treatment", [
            plan["experiment_id"], hashlib.sha256(canonical_json(causal_identity)).hexdigest()
        ]),
        "cohort_id": config["cohort_id"],
        "experiment_id": plan["experiment_id"],
        "creative_id": plan["creative_id"],
        "product_id": plan["product_id"],
        "account_id": plan["account_id"],
        "hook_id": plan["hook_id"],
        "hook_text": plan["hook_text"],
        "tactic_id": plan["tactic_id"],
        "renderer_id": plan["renderer_id"],
        "renderer_version": config["renderer_version"],
        "renderer_source_path": str(renderer_source),
        "renderer_source_sha256": sha256_file(renderer_source),
        "body_template_id": config["body_template_id"],
        "body_text": config["body_text"],
        "full_script": full_script,
        "script_sha256": hashlib.sha256(full_script.encode("utf-8")).hexdigest(),
        "voice": config["voice"],
        "voice_rate": config["voice_rate"],
        "caption_style_id": config["caption_style_id"],
        "clip_set": clips,
        "target_duration_seconds": dict(limits),
        "duration_seconds": round(float(duration_seconds), 3),
        "cta": plan["cta"],
        "destination_url": plan["destination_url"],
        "asset_path": str(asset_path),
        "asset_sha256": sha256_file(asset_path),
        "publication_effects": [],
    }


def render_treatment(plan: dict[str, Any], config: dict[str, Any], *,
                     output: Path, renderer: Callable[..., dict[str, Any]]) -> dict[str, Any]:
    """Render only through the frozen inputs, then bind the resulting asset."""
    full_script = f'{plan.get("hook_text", "")}{config.get("body_text", "")}{plan.get("cta", "")}'
    clips = [Path(path) for path in config.get("clip_paths", [])]
    receipt = renderer(
        script=full_script, output=Path(output), clips=clips,
        voice=config.get("voice"), voice_rate=config.get("voice_rate"),
        caption_style_id=config.get("caption_style_id"),
    )
    if receipt.get("external_cost_usd") != 0 or receipt.get("external_effects") != []:
        raise ValueError("cohort preview renderer caused an external effect or cost")
    return build_manifest(plan, config, asset_path=Path(output),
                          duration_seconds=receipt["duration"])


def validate_cohort_compatibility(existing: Iterable[dict[str, Any]],
                                  candidate: dict[str, Any]) -> None:
    """Reject any within-cohort drift except hook and per-item identities."""
    for row in existing:
        if row.get("cohort_id") != candidate.get("cohort_id"):
            continue
        for field in LOCKED_COHORT_FIELDS:
            if row.get(field) != candidate.get(field):
                raise ValueError(f"{field} drift inside cohort")


def append_manifest(path: Path, row: dict[str, Any]) -> bool:
    """Append once; identical replay dedupes and conflicting identity fails."""
    path = Path(path)
    existing = []
    if path.is_file():
        existing = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
                    if line.strip()]
    validate_cohort_compatibility(existing, row)
    for current in existing:
        if current.get("treatment_id") != row.get("treatment_id"):
            continue
        if current == row:
            return False
        raise ValueError("conflicting treatment replay")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return True


def verify_cohort_selection(manifests: Iterable[dict[str, Any]],
                            accepted_treatment_ids: Iterable[str], *,
                            required: int = 10,
                            min_unique_hooks: int = 10) -> dict[str, Any]:
    """Verify the exact publish set; rejected manifests stay outside it."""
    ids = list(accepted_treatment_ids)
    if len(ids) != required or len(set(ids)) != required:
        raise ValueError(f"selection must contain exactly {required} unique treatments")
    by_id = {row.get("treatment_id"): row for row in manifests}
    if any(treatment_id not in by_id for treatment_id in ids):
        raise ValueError("selected treatment is missing from immutable ledger")
    selected = [by_id[treatment_id] for treatment_id in ids]
    validate_cohort_compatibility(selected[:1], selected[1])
    for candidate in selected[2:]:
        validate_cohort_compatibility(selected[:1], candidate)
    experiments = {row.get("experiment_id") for row in selected}
    hooks = {row.get("hook_id") for row in selected}
    if len(experiments) != required:
        raise ValueError(f"selection requires {required} unique experiments")
    if len(hooks) < min_unique_hooks:
        raise ValueError(f"selection requires {min_unique_hooks} unique hooks")
    for row in selected:
        asset = Path(row["asset_path"])
        if not asset.is_file() or sha256_file(asset) != row.get("asset_sha256"):
            raise ValueError(f"asset hash mismatch: {row.get('treatment_id')}")
        renderer_source = Path(row["renderer_source_path"])
        if (not renderer_source.is_file()
                or sha256_file(renderer_source) != row.get("renderer_source_sha256")):
            raise ValueError(f"renderer source hash mismatch: {row.get('treatment_id')}")
        limits = row["target_duration_seconds"]
        if not limits["min"] <= row["duration_seconds"] <= limits["max"]:
            raise ValueError(f"duration outside frozen band: {row.get('treatment_id')}")
        for clip in row["clip_set"]:
            path = Path(clip["path"])
            if not path.is_file() or sha256_file(path) != clip["sha256"]:
                raise ValueError(f"clip hash mismatch: {row.get('treatment_id')}")
    return {
        "status": "verified",
        "cohort_id": selected[0]["cohort_id"],
        "accepted_count": len(selected),
        "experiment_count": len(experiments),
        "hook_count": len(hooks),
        "renderer_source_sha256": selected[0]["renderer_source_sha256"],
        "treatment_ids": ids,
        "publication_effects": [],
    }
