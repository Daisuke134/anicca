#!/usr/bin/env python3
"""Free-only OmniAvatar adapter contract; never falls back to HeyGen or paid renderers."""
from __future__ import annotations

import hashlib
from pathlib import Path


SPACE = "alexnasa/OmniAvatar"
EXCLUDED = {"heygen", "paid", "fallback"}


def require(value: bool, message: str) -> None:
    if not value:
        raise ValueError(message)


def prepare(*, image: Path, audio: Path, script: str, renderer_id: str = "omniavatar-monk") -> dict:
    require(renderer_id == "omniavatar-monk", "only OmniAvatar renderer is allowed")
    require(image.is_file() and audio.is_file() and script.strip(), "OmniAvatar image/audio/script required")
    return {"renderer_id": renderer_id, "space": SPACE, "render_cost_usd": 0,
            "image_sha256": hashlib.sha256(image.read_bytes()).hexdigest(),
            "audio_sha256": hashlib.sha256(audio.read_bytes()).hexdigest(),
            "script_sha256": hashlib.sha256(script.encode()).hexdigest(),
            "explicitly_excluded": sorted(EXCLUDED), "external_effects": []}


def unavailable(request: dict, reason: str) -> dict:
    return {"status": "unavailable", "reason": reason, "request": request,
            "render_cost_usd": 0, "external_effects": [],
            "recovery": "retry the same free OmniAvatar path; do not substitute renderer"}
