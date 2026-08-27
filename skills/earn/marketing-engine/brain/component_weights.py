#!/usr/bin/env python3
"""Product-isolated mature-outcome component weights and 80/20 selection."""
from __future__ import annotations

import json
from collections import defaultdict

from script_ledger import COMPONENTS, require


def build_weights(scripts: list[dict], outcomes: list[dict], product_id: str) -> dict:
    by_id = {row["script_id"]: row for row in scripts if row["product_id"] == product_id}
    groups: dict[tuple[str, str], list[float]] = defaultdict(list)
    for outcome in outcomes:
        if outcome.get("product_id") != product_id or outcome.get("status") != "mature":
            continue
        script = by_id.get(outcome.get("script_id"))
        score = outcome.get("score")
        require(script is not None and isinstance(score, (int, float)), "mature outcome script/score invalid")
        for component in COMPONENTS:
            groups[(component, script[component])].append(float(score))
    values = []
    for (component, value), scores in sorted(groups.items()):
        observations = len(scores)
        average = sum(scores) / observations
        values.append({"component": component, "value": value, "observations": observations,
                       "weight": round(average, 6),
                       "retire_eligible": observations >= 3 and average <= 0.3})
    return {"schema_version": "marketing.ebook-component-weights.v1", "product_id": product_id,
            "mature_outcomes": sum(len(scores) for scores in groups.values()) // len(COMPONENTS),
            "values": values}


def select_script(scripts: list[dict], weights: dict, *, slot_index: int) -> dict:
    require(slot_index >= 1, "positive slot index required")
    product_id = weights["product_id"]
    candidates = [row for row in scripts if row["product_id"] == product_id]
    require(candidates, "product scripts required")
    by_component = {(row["component"], row["value"]): row for row in weights["values"]}
    def score(script: dict) -> float:
        rows = [by_component.get((key, script[key])) for key in COMPONENTS]
        measured = [row["weight"] for row in rows if row]
        return sum(measured) / len(measured) if measured else 0.5
    ranked = sorted(candidates, key=lambda row: (score(row), row["script_id"]), reverse=True)
    exploration = slot_index % 5 == 0
    chosen = ranked[-1] if exploration else ranked[0]
    return {"script_id": chosen["script_id"], "product_id": product_id,
            "mode": "explore" if exploration else "exploit", "score": round(score(chosen), 6),
            "weight_input_sha256": __import__("hashlib").sha256(json.dumps(weights, sort_keys=True).encode()).hexdigest()}
