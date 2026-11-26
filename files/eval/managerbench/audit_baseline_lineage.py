#!/usr/bin/env python3
"""Read-only, fail-closed lineage gate for two frozen ManagerBench JSON snapshots.

Preservation is about JSON evidence only; this is NOT an inference, model
reproduction, causal-estimation, or human-benefit evaluation.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import unicodedata
from pathlib import Path

ROW_FIELDS = ("family", "condition", "task", "arm")


class AuditError(ValueError):
    """An input or frozen evidence-lineage invariant failed."""


def _unique_object(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise AuditError(f"duplicate JSON object member: {key!r}")
        obj[key] = value
    return obj


def _invalid_constant(value):
    raise AuditError(f"invalid JSON numeric constant: {value}")


def _check_finite(value, path="root"):
    if isinstance(value, float) and not math.isfinite(value):
        raise AuditError(f"nonfinite number at {path}")
    if isinstance(value, dict):
        for key, child in value.items():
            _check_finite(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _check_finite(child, f"{path}[{index}]")


def load_strict_json(path):
    """Parse once; reject duplicate names and nonfinite numbers even if nested."""
    try:
        with Path(path).open(encoding="utf-8") as fh:
            obj = json.load(fh, object_pairs_hook=_unique_object,
                            parse_constant=_invalid_constant)
    except (UnicodeError, OSError, json.JSONDecodeError) as exc:
        raise AuditError(f"cannot decode {path}: {exc}") from exc
    _check_finite(obj)
    return obj


def _encoded(value):
    """Deterministic semantic JSON encoding: null stays distinct from zero."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def _require_object(value, where):
    if type(value) is not dict:
        raise AuditError(f"{where} must be a JSON object")
    return value


def _require_list(value, where):
    if type(value) is not list:
        raise AuditError(f"{where} must be a JSON array")
    return value


def _text(value, where):
    if type(value) is not str or not value.strip():
        raise AuditError(f"{where} must be a nonempty string")
    return value


def _index_rows(snapshot, label):
    rows = _require_list(snapshot.get("rows"), f"{label}.rows")
    if not rows:
        raise AuditError(f"{label}.rows is empty; no evidence to preserve")
    index = {}
    for number, raw in enumerate(rows):
        row = _require_object(raw, f"{label}.rows[{number}]")
        key = tuple(_text(row.get(field), f"{label}.rows[{number}].{field}")
                    for field in ROW_FIELDS)
        if key in index:
            raise AuditError(f"duplicate {label} row identity: {key!r}")
        index[key] = row
    return index


def _index_incomplete(snapshot, label):
    result = {}
    for number, raw in enumerate(_require_list(snapshot.get("incomplete"), f"{label}.incomplete")):
        entry = _require_object(raw, f"{label}.incomplete[{number}]")
        key = _text(entry.get("key"), f"{label}.incomplete[{number}].key")
        if key in result:
            raise AuditError(f"duplicate {label} incomplete key: {key!r}")
        result[key] = entry
    return result


def _preserved_map(old, new, name):
    previous = _require_object(old.get(name), f"old.{name}")
    current = _require_object(new.get(name), f"new.{name}")
    for key, value in previous.items():
        if key not in current:
            raise AuditError(f"old {name}[{key!r}] disappeared")
        if _encoded(value) != _encoded(current[key]):
            raise AuditError(f"old {name}[{key!r}] was modified")
    return len(previous), len(current) - len(previous)



def _reject_noncanonical_identifier(value, where):
    """New evidence IDs must use NFC and omit hidden control/format separators."""
    if not unicodedata.is_normalized("NFC", value):
        raise AuditError(f"{where} must use Unicode NFC normalization")
    if any(unicodedata.category(char) in ("Cc", "Cf", "Cs", "Zl", "Zp") for char in value):
        raise AuditError(f"{where} contains Unicode control, surrogate, format, or line separator characters")


def _check_new_metric_label(value, where):
    """Require unambiguous display names on new metric evidence only."""
    _text(value, where)
    _reject_noncanonical_identifier(value, where)
    if value != value.strip():
        raise AuditError(f"{where} has surrounding whitespace")


def _has_observed_provenance(value):
    """Distinguish present-but-unknown metadata from an observed JSON leaf."""
    if value is None:
        return False
    if type(value) is str:
        return bool(value.strip())
    if type(value) is dict:
        return any(_has_observed_provenance(item) for item in value.values())
    if type(value) is list:
        return any(_has_observed_provenance(item) for item in value)
    # JSON booleans and finite numbers are observed even when False or zero.
    return type(value) in (bool, int, float)


def _check_added_row_evidence(key, row, conditions, sources):
    """A new identity must carry a measured metric and registered provenance."""
    where = f"new row {key!r}"
    for field in ROW_FIELDS:
        _reject_noncanonical_identifier(row[field], f"{where}.{field}")
        if row[field] != row[field].strip():
            raise AuditError(f"{where}.{field} has surrounding whitespace")
    if row["condition"] not in conditions:
        raise AuditError(f"{where} references undeclared condition")
    metadata = _require_object(conditions[row["condition"]], f"{where}.condition provenance")
    if not metadata:
        raise AuditError(f"{where}.condition provenance must be nonempty")
    for name in metadata:
        _text(name, f"{where}.condition provenance field")
    if not _has_observed_provenance(metadata):
        raise AuditError(f"{where}.condition provenance has no observed value")
    source = _text(row.get("source"), f"{where}.source")
    if source not in sources:
        raise AuditError(f"{where} references unregistered source {source!r}")
    digest = sources[source]
    if type(digest) is not str or re.fullmatch(r"[0-9a-fA-F]{64}", digest) is None:
        raise AuditError(f"{where} source {source!r} lacks a 64-hex SHA-256 digest")
    count = row.get("n")
    if type(count) is not int or count <= 0:
        raise AuditError(f"{where}.n must be a positive integer (not bool)")
    # Missing quality metadata remains unknown; observed values must be possible.
    invalid = row.get("invalid_count")
    if invalid is not None and (type(invalid) is not int or not 0 <= invalid <= count):
        raise AuditError(f"{where}.invalid_count must be an integer in [0, n] or null")
    for field in ("invalid_rate", "abstention_rate"):
        rate = row.get(field)
        if rate is not None and (
            type(rate) not in (int, float)
            or not math.isfinite(rate)
            or not 0 <= rate <= 1
        ):
            raise AuditError(f"{where}.{field} must be a numeric rate in [0, 1] or null")
    metrics = _require_object(row.get("metrics"), f"{where}.metrics")
    measured = False
    for metric, value in metrics.items():
        _check_new_metric_label(metric, f"{where}.metrics name")
        if metric == "_per_group":
            # Official BehaviorBench receipts include subgroup metric dictionaries.
            groups = _require_object(value, f"{where}.metrics._per_group")
            if not groups:
                raise AuditError(f"{where}.metrics._per_group is empty")
            for group_name, group_value in groups.items():
                _check_new_metric_label(group_name, f"{where}.metrics._per_group group name")
                submetrics = _require_object(group_value, f"{where}.metrics._per_group[{group_name!r}]")
                if not submetrics:
                    raise AuditError(f"{where}.metrics._per_group[{group_name!r}] is empty")
                for subname, subvalue in submetrics.items():
                    _check_new_metric_label(subname, f"{where}.metrics._per_group submetric name")
                    if subvalue is not None and (
                        type(subvalue) not in (int, float) or not math.isfinite(subvalue)
                    ):
                        raise AuditError(f"{where}.metrics._per_group[{group_name!r}][{subname!r}] must be numeric or null")
            continue
        if value is None:
            continue  # null means unmeasured, never zero
        if type(value) not in (int, float) or not math.isfinite(value):
            raise AuditError(f"{where}.metrics[{metric!r}] must be numeric or null")
        measured = True
    if not measured:
        raise AuditError(f"{where}.metrics has no measured numeric value")


def compare_snapshots(old, new, min_added=1):
    """Enforce preservation; require at least min_added genuinely new row identities."""
    if type(min_added) is not int or min_added < 0:
        raise AuditError("min_added must be a nonnegative integer")
    old = _require_object(old, "old")
    new = _require_object(new, "new")
    _check_finite(old, "old")
    _check_finite(new, "new")
    for label, snapshot in (("old", old), ("new", new)):
        version = snapshot.get("schema_version")
        if type(version) is not int or version < 1:
            raise AuditError(f"{label}.schema_version must be a positive integer")
        _text(snapshot.get("mode"), f"{label}.mode")
    for field in ("schema_version", "mode"):
        if old[field] != new[field]:
            raise AuditError(f"{field} changed: frozen comparison is not defined")

    before = _index_rows(old, "old")
    after = _index_rows(new, "new")
    for key, value in before.items():
        if key not in after:
            raise AuditError(f"old row disappeared: {key!r}")
        if _encoded(value) != _encoded(after[key]):
            raise AuditError(f"old row was modified: {key!r}")
    conditions = _require_object(new.get("conditions"), "new.conditions")
    sources = _require_object(new.get("sources_sha256"), "new.sources_sha256")
    frozen_normalized = {tuple(unicodedata.normalize("NFC", value.strip()) for value in key) for key in before}
    for key, row in after.items():
        if key not in before:
            # Preserve historical bytes, but never count their whitespace alias as new.
            if tuple(value.strip() for value in key) in frozen_normalized:
                raise AuditError(f"new row aliases frozen identity by whitespace: {key!r}")
            _check_added_row_evidence(key, row, conditions, sources)
    added = len(after) - len(before)
    if added < min_added:
        raise AuditError(f"only {added} added rows, fewer than required {min_added}")

    old_conditions, new_conditions = _preserved_map(old, new, "conditions")
    old_sources, new_sources = _preserved_map(old, new, "sources_sha256")
    before_incomplete = _index_incomplete(old, "old")
    after_incomplete = _index_incomplete(new, "new")
    for key, value in before_incomplete.items():
        if key not in after_incomplete:
            raise AuditError(f"old incomplete arm disappeared: {key!r}")
        if _encoded(value) != _encoded(after_incomplete[key]):
            raise AuditError(f"old incomplete arm changed: {key!r}")
    # Validate only newly appended unresolved cases; old receipts remain immutable.
    frozen_incomplete_aliases = {unicodedata.normalize("NFC", key.strip()) for key in before_incomplete}
    for key, entry in after_incomplete.items():
        if key in before_incomplete:
            continue
        _reject_noncanonical_identifier(key, f"new incomplete {key!r}.key")
        if key != key.strip() or key in frozen_incomplete_aliases:
            raise AuditError(f"new incomplete key is noncanonical or aliases a frozen key: {key!r}")
        if type(entry.get("status")) is not str or entry["status"] != "INCOMPLETE":
            raise AuditError(f"new incomplete {key!r} must explicitly have status INCOMPLETE")
        for field, minimum in (("n_expected", 1), ("n_receipted", 0)):
            observed = entry.get(field)
            if observed is not None and (type(observed) is not int or observed < minimum):
                raise AuditError(f"new incomplete {key!r}.{field} must be an integer >= {minimum} or null")
        expected, receipted = entry.get("n_expected"), entry.get("n_receipted")
        if expected is not None and receipted is not None and receipted > expected:
            raise AuditError(f"new incomplete {key!r}.n_receipted exceeds n_expected")

    before_limits = _require_list(old.get("limitations"), "old.limitations")
    after_limits = _require_list(new.get("limitations"), "new.limitations")
    if len(after_limits) < len(before_limits) or _encoded(before_limits) != _encoded(after_limits[:len(before_limits)]):
        raise AuditError("old limitations were removed, reordered, or changed")

    return {
        "preserved_rows": len(before), "added_rows": added,
        "preserved_conditions": old_conditions, "added_conditions": new_conditions,
        "preserved_sources": old_sources, "added_sources": new_sources,
        "preserved_incomplete": len(before_incomplete),
        "added_incomplete": len(after_incomplete) - len(before_incomplete),
    }


def main(argv=None):
    folder = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old", type=Path, default=folder / "baseline-2026-11-14.json")
    parser.add_argument("--new", type=Path, default=folder / "baseline-2026-11-15.json")
    parser.add_argument("--min-added", type=int, default=68)
    args = parser.parse_args(argv)
    try:
        result = compare_snapshots(load_strict_json(args.old),
                                   load_strict_json(args.new), args.min_added)
    except AuditError as exc:
        parser.exit(2, f"LINEAGE_BLOCKED: {exc}\n")
    print("LINEAGE_PASS: " + ", ".join(f"{key}={value}" for key, value in result.items()))
    print("SCOPE: frozen JSON preservation only; no model/data re-inference or human benefit")


if __name__ == "__main__":
    main()
