# SPDX-License-Identifier: MIT
# wrappers/_common.py — shared loader for memU MemoryService.
#
# Resolves env-var-name fields in config.json (e.g. api_key: "DEEPSEEK_API_KEY")
# to actual env values, and writes per-invocation cost lines to ~/.anicca/memU/cost.log.

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from memu import MemoryService

REPO_ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = REPO_ROOT / "runtime" / "memu" / "config.json"
DATA_DIR = REPO_ROOT / "runtime" / "memu" / "data"
COST_LOG = Path.home() / ".anicca" / "memU" / "cost.log"


def _resolve_api_key(profile: dict[str, Any]) -> dict[str, Any]:
    """Replace api_key env-var-name with actual value. Empty placeholder for keyless backends."""
    name = profile.get("api_key", "")
    if name and name == name.upper() and not name.startswith("sk-"):
        profile["api_key"] = os.environ.get(name, "")
    return profile


def load_service() -> MemoryService:
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    cfg.pop("_comment", None)

    llm_profiles = cfg.get("llm_profiles", {})
    for key in list(llm_profiles.keys()):
        llm_profiles[key] = _resolve_api_key(llm_profiles[key])

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "resources").mkdir(parents=True, exist_ok=True)
    cfg.setdefault("blob_config", {})["resources_dir"] = str(DATA_DIR / "resources")

    return MemoryService(
        llm_profiles=llm_profiles,
        database_config=cfg.get("database_config"),
        blob_config=cfg.get("blob_config"),
        memorize_config=cfg.get("memorize_config"),
        retrieve_config=cfg.get("retrieve_config"),
    )


def log_cost(op: str, elapsed_s: float, payload: dict[str, Any]) -> None:
    COST_LOG.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(
        {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "op": op,
            "elapsed_s": round(elapsed_s, 3),
            "input_chars": payload.get("input_chars"),
            "items_extracted": payload.get("items_extracted"),
            "results_count": payload.get("results_count"),
            "ok": payload.get("ok", True),
        },
        ensure_ascii=False,
    )
    with COST_LOG.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def stderr(msg: str) -> None:
    sys.stderr.write(msg.rstrip() + "\n")
    sys.stderr.flush()
