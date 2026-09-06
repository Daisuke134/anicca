#!/usr/bin/env python3
"""Freeze a reproducible projection of registry ownership and receipt coverage."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_projection(*, registry: dict, adapters: dict, status: list[dict],
                     source_head: str, registry_sha256: str,
                     adapters_sha256: str) -> dict:
    expected = {
        "managed": len(registry["loops"]),
        "external": len(registry.get("external_labels", [])),
        "retired": len(registry.get("retired_labels", [])),
    }
    actual = Counter(row["classification"] for row in status)
    if set(actual) != set(expected) or any(
        actual.get(kind, 0) != count for kind, count in expected.items()
    ):
        raise ValueError(f"classification counts do not match registry: expected={expected} actual={dict(actual)}")

    local_inventory = []
    missing_terminal = []
    unmapped_effects = []
    retired_present = []
    for row in sorted(status, key=lambda item: item["label"]):
        loop_id = row["loop_id"]
        terminal = None
        if row.get("last_terminal_result") is not None:
            terminal = {
                "observed_at": row.get("last_pass"),
                "result": row["last_terminal_result"],
                "release_sha": row.get("event_release_sha"),
            }
        elif row["classification"] == "managed":
            missing_terminal.append(loop_id)

        effect_class = row.get("effect_class", "unknown")
        if effect_class in {"none", "unknown"}:
            official = {
                "status": "not_applicable" if effect_class == "none" else "unknown",
                "ref": None,
                "reason": "effect_class_none" if effect_class == "none" else "not_a_managed_effect",
            }
        else:
            official = {
                "status": row.get("effect_status", "unknown"),
                "ref": None,
                "reason": "no_common_receipt_mapping",
            }
            unmapped_effects.append(loop_id)

        if row.get("blocker") == "retired_still_present":
            retired_present.append(row["label"])
        local_inventory.append({
            "classification": row["classification"],
            "loop_id": loop_id,
            "label": row["label"],
            "owner": row["owner"],
            "last_terminal_receipt": terminal,
            "official_effect_receipt": official,
        })

    cloud_inventory = []
    missing_cloud_owner = []
    missing_cloud_receipt = []
    for adapter in sorted(adapters["adapters"], key=lambda item: item["adapter_id"]):
        adapter_id = adapter["adapter_id"]
        owner = adapter.get("owner")
        receipt_source = adapter.get("receipt_source")
        if not owner:
            missing_cloud_owner.append(adapter_id)
        if not receipt_source:
            missing_cloud_receipt.append(adapter_id)
        cloud_inventory.append({
            "adapter_id": adapter_id,
            "loop_id": adapter["loop_id"],
            "capability": adapter["capability"],
            "effect_classes": adapter["effect_classes"],
            "module_ref": adapter["module_ref"],
            "owner": owner,
            "receipt_source": receipt_source,
        })

    return {
        "schema_version": 1,
        "sources": {
            "git_head": source_head,
            "registry": "config/loop-registry.json",
            "registry_sha256": registry_sha256,
            "cloud_adapters": "apps/life-manager/config/loop-adapters.json",
            "cloud_adapters_sha256": adapters_sha256,
            "runtime_projection": "bin/lm-loop status all",
        },
        "counts": {
            **expected,
            "cloud_adapters": len(adapters["adapters"]),
        },
        "local_inventory": local_inventory,
        "cloud_inventory": cloud_inventory,
        "gaps": {
            "missing_terminal_receipts": sorted(missing_terminal),
            "unmapped_effect_receipts": sorted(unmapped_effects),
            "cloud_adapters_without_owner": sorted(missing_cloud_owner),
            "cloud_adapters_without_receipt_source": sorted(missing_cloud_receipt),
            "retired_labels_still_present": sorted(retired_present),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--status", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-head")
    args = parser.parse_args()

    root = args.root.resolve()
    registry_path = root / "config/loop-registry.json"
    adapters_path = root / "apps/life-manager/config/loop-adapters.json"
    source_head = args.source_head or subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    projection = build_projection(
        registry=json.loads(registry_path.read_text()),
        adapters=json.loads(adapters_path.read_text()),
        status=json.loads(args.status.read_text()),
        source_head=source_head,
        registry_sha256=sha256(registry_path),
        adapters_sha256=sha256(adapters_path),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(projection, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
