#!/usr/bin/env python3
import json
import os
from typing import Any, Dict

BASE_DIR = os.path.expanduser("~/.openclaw/workspace/memory/tiktok")

FILES = {
    "profile": "profile.json",
    "content_bank": "content_bank.json",
    "analytics": "analytics.json",
    "pattern_report": "pattern_report.json",
}


def ensure_base_dir() -> None:
    os.makedirs(BASE_DIR, exist_ok=True)


def path_for(key: str) -> str:
    if key not in FILES:
        raise ValueError(f"Unknown storage key: {key}")
    ensure_base_dir()
    return os.path.join(BASE_DIR, FILES[key])


def default_data(key: str) -> Dict[str, Any]:
    defaults = {
        "profile": {
            "niche": "",
            "target_audience": "",
            "primary_goal": "",
            "pillars": [],
            "tone": "",
            "notes": "",
            "updated_at": ""
        },
        "content_bank": {
            "items": []
        },
        "analytics": {
            "videos": []
        },
        "pattern_report": {
            "generated_at": "",
            "summary": {},
            "recommendations": []
        },
    }
    return defaults[key]


def load_json(key: str) -> Dict[str, Any]:
    file_path = path_for(key)
    if not os.path.exists(file_path):
        return default_data(key)

    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(key: str, data: Dict[str, Any]) -> None:
    file_path = path_for(key)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
