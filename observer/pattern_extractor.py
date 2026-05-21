from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from statistics import pstdev
from typing import Any


def _parse_timestamp(value: str) -> datetime | None:
    if not value or not isinstance(value, str):
        return None

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def extract_time_patterns(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[datetime]] = defaultdict(list)

    for obs in observations:
        if obs.get("type") != "window":
            continue
        app = obs.get("app")
        ts = _parse_timestamp(obs.get("timestamp"))
        if not app or ts is None:
            continue
        grouped[app].append(ts)

    patterns: list[dict[str, Any]] = []
    for app, timestamps in grouped.items():
        day_coverage = len({ts.date() for ts in timestamps})
        if day_coverage < 4:
            continue

        minutes = [ts.hour * 60 + ts.minute for ts in timestamps]
        std_dev_minutes = pstdev(minutes)
        if std_dev_minutes > 20:
            continue

        patterns.append(
            {
                "type": "time_pattern",
                "app": app,
                "day_coverage": day_coverage,
                "std_dev_minutes": std_dev_minutes,
            }
        )

    return patterns


def extract_sequence_patterns(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def event_app(obs: dict[str, Any]) -> str | None:
        kind = obs.get("type")
        if kind == "app_switch":
            return obs.get("to_app")
        if kind == "window":
            return obs.get("app")
        return None

    apps = [event_app(obs) for obs in observations]
    apps = [app for app in apps if app]

    sequences: Counter[tuple[str, str, str]] = Counter()
    for idx in range(len(apps) - 2):
        seq = (apps[idx], apps[idx + 1], apps[idx + 2])
        if len(set(seq)) != 3:
            continue
        sequences[seq] += 1

    patterns: list[dict[str, Any]] = []
    for seq, frequency in sequences.items():
        if frequency < 3:
            continue
        patterns.append(
            {
                "type": "sequence_pattern",
                "sequence": list(seq),
                "frequency": frequency,
            }
        )

    return patterns


def extract_shell_patterns(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()

    for obs in observations:
        if obs.get("type") != "shell":
            continue
        command = obs.get("command")
        if not command or command == "[REDACTED]":
            continue
        counts[command] += 1

    patterns: list[dict[str, Any]] = []
    for command, frequency in counts.items():
        if frequency < 5:
            continue
        patterns.append(
            {
                "type": "shell_pattern",
                "command": command,
                "frequency": frequency,
            }
        )

    return patterns
