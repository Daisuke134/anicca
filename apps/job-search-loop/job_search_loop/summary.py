from __future__ import annotations

from collections import Counter


def build_summary(*, day: str, states: list[str], model_route: str) -> dict:
    return {
        "version": 1,
        "day": day,
        "counts": dict(sorted(Counter(states).items())),
        "model_route": model_route,
    }
