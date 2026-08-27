"""Schema-v2 registry validation and deterministic launchd job-model rendering."""

from __future__ import annotations

import json
import re
from pathlib import PurePosixPath


DOMAINS = {"physical", "mental", "financial", "earn", "growth", "system"}
EFFECTS = {"none", "publish", "message", "money", "application", "trade", "account_mutation"}
ROUTES = {"deterministic", "shared-agent-runner"}
CADENCES = {"start_interval_seconds", "calendar_interval", "run_at_load", "keep_alive"}
FIELDS = {
    "label", "domain", "entrypoint", "cadence", "effect_class", "state_root",
    "log_root", "cleanup", "provider_route",
}
SECRET_FIELD = re.compile(r"token|secret|password|credential|auth|api.?key", re.I)


def _fail(message: str) -> None:
    raise ValueError(message)


def validate_registry(registry: dict) -> dict:
    if not isinstance(registry, dict) or set(registry) != {"schema_version", "loops"}:
        _fail("registry must contain only schema_version and loops")
    if registry["schema_version"] != 2 or not isinstance(registry["loops"], dict):
        _fail("schema_version must be 2 and loops must be an object")
    labels = set()
    for loop_id, row in registry["loops"].items():
        if not isinstance(loop_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", loop_id):
            _fail(f"invalid loop id: {loop_id}")
        if not isinstance(row, dict):
            _fail(f"{loop_id}: entry must be an object")
        secret_fields = [key for key in row if SECRET_FIELD.search(key)]
        if secret_fields:
            _fail(f"{loop_id}: secret-like fields forbidden: {secret_fields}")
        missing, unknown = FIELDS - set(row), set(row) - FIELDS
        if missing:
            _fail(f"{loop_id}: missing fields: {sorted(missing)}")
        if unknown:
            _fail(f"{loop_id}: unknown fields: {sorted(unknown)}")
        label = row["label"]
        if not isinstance(label, str) or not label.startswith("ai.anicca.") or label in labels:
            _fail(f"{loop_id}: invalid or duplicate label")
        labels.add(label)
        if row["domain"] not in DOMAINS:
            _fail(f"{loop_id}: invalid domain")
        if row["effect_class"] not in EFFECTS:
            _fail(f"{loop_id}: invalid effect_class")
        if row["provider_route"] not in ROUTES:
            _fail(f"{loop_id}: invalid provider_route")
        entrypoint = row["entrypoint"]
        path = PurePosixPath(entrypoint) if isinstance(entrypoint, str) else PurePosixPath("/")
        if path.is_absolute() or ".." in path.parts or str(path) in {"", "."}:
            _fail(f"{loop_id}: entrypoint must be repository-relative")
        cadence = row["cadence"]
        if not isinstance(cadence, dict) or len(cadence) != 1 or set(cadence) - CADENCES:
            _fail(f"{loop_id}: cadence must contain exactly one allowed key")
        key, value = next(iter(cadence.items()))
        if key == "start_interval_seconds" and (not isinstance(value, int) or value <= 0):
            _fail(f"{loop_id}: invalid start_interval_seconds")
        if key in {"run_at_load", "keep_alive"} and value is not True:
            _fail(f"{loop_id}: {key} must be true")
        if key == "calendar_interval" and not isinstance(value, (dict, list)):
            _fail(f"{loop_id}: invalid calendar_interval")
        for root_field in ("state_root", "log_root"):
            if not isinstance(row[root_field], str) or not row[root_field].startswith("~/"):
                _fail(f"{loop_id}: {root_field} must be home-relative")
        cleanup = row["cleanup"]
        if not isinstance(cleanup, dict) or set(cleanup) != {"max_runs", "max_age_days"}:
            _fail(f"{loop_id}: cleanup contract is incomplete")
        if any(not isinstance(cleanup[key], int) or cleanup[key] <= 0 for key in cleanup):
            _fail(f"{loop_id}: cleanup bounds must be positive integers")
    return registry


def render_job_models(registry: dict) -> bytes:
    validate_registry(registry)
    models = [
        {"loop_id": loop_id, **registry["loops"][loop_id]}
        for loop_id in sorted(registry["loops"])
    ]
    return (json.dumps(models, sort_keys=True, separators=(",", ":")) + "\n").encode()
