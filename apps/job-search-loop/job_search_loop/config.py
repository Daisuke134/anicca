from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Settings:
    state_dir: Path
    materials_dir: Path
    profile_path: Path
    daily_target: int
    auto_apply_threshold: int
    compensation_floor_jpy: int


def _required_string(value: dict[str, Any], key: str, where: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item.strip():
        raise ConfigError(f"{where}.{key} must be a non-empty string")
    return item.strip()


def validate_profile(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("version") != 1:
        raise ConfigError("profile.version must be 1")
    candidate = value.get("candidate")
    if not isinstance(candidate, dict):
        raise ConfigError("profile.candidate is required")
    _required_string(candidate, "name", "profile.candidate")
    facts = value.get("facts")
    if not isinstance(facts, list) or not facts:
        raise ConfigError("profile.facts must be a non-empty array")
    seen: set[str] = set()
    for index, fact in enumerate(facts):
        where = f"profile.facts[{index}]"
        if not isinstance(fact, dict):
            raise ConfigError(f"{where} must be an object")
        fact_id = _required_string(fact, "id", where)
        _required_string(fact, "claim", where)
        _required_string(fact, "evidence", where)
        if fact_id in seen:
            raise ConfigError(f"duplicate fact id: {fact_id}")
        seen.add(fact_id)
    return value


def _private_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path, 0o700)
    return path


def load_settings(
    *,
    profile_path: Path,
    strategy_path: Path,
    state_dir: Path,
    materials_dir: Path,
) -> Settings:
    if not profile_path.is_file():
        raise ConfigError(f"private profile not found: {profile_path}")
    os.chmod(profile_path, 0o600)
    try:
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        strategy = json.loads(strategy_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ConfigError(str(error)) from error
    validate_profile(profile)
    required = {
        "daily_target": 2,
        "auto_apply_threshold": 75,
        "compensation_floor_jpy": 7_000_000,
    }
    for key, expected in required.items():
        if strategy.get(key) != expected:
            raise ConfigError(f"strategy.{key} must be {expected}")
    return Settings(
        state_dir=_private_dir(state_dir),
        materials_dir=_private_dir(materials_dir),
        profile_path=profile_path,
        daily_target=required["daily_target"],
        auto_apply_threshold=required["auto_apply_threshold"],
        compensation_floor_jpy=required["compensation_floor_jpy"],
    )
