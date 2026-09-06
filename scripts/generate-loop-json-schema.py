#!/usr/bin/env python3
"""Regenerate the single loop.json schema from the runtime registry contract."""

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime.loop.macos_loop_registry import render_loop_json_schema


TARGET = ROOT / "runtime/loop/loop.schema.json"


if __name__ == "__main__":
    TARGET.write_bytes(render_loop_json_schema())
