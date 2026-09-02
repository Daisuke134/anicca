#!/usr/bin/env python3
"""Remove only regenerable Chromium caches for one registered browser identity."""

from __future__ import annotations

import argparse
import os
import shutil
import tomllib
from pathlib import Path


CACHE_NAMES = {
    "Cache", "Code Cache", "GPUCache", "DawnCache", "DawnWebGPUCache",
    "DawnGraphiteCache", "GrShaderCache", "GraphiteDawnCache", "Media Cache",
    "ShaderCache",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("identity")
    parser.add_argument("--registry", type=Path, required=True)
    args = parser.parse_args()
    registry = tomllib.loads(args.registry.expanduser().read_text(encoding="utf-8"))
    row = next((item for item in registry.get("identity", [])
                if item.get("id") == args.identity), None)
    if not row or not isinstance(row.get("profile"), str):
        return 1
    profile = Path(row["profile"]).expanduser().resolve()
    allowed = (Path.home() / ".cloak" / "profiles").resolve()
    if profile == allowed or allowed not in profile.parents or not profile.is_dir():
        return 1
    removed = 0
    for root, directories, _files in os.walk(profile, topdown=True, followlinks=False):
        parent = Path(root)
        for name in list(directories):
            if name not in CACHE_NAMES:
                continue
            target = parent / name
            directories.remove(name)
            if target.is_symlink():
                continue
            try:
                removed += sum(item.stat().st_size for item in target.rglob("*") if item.is_file())
                shutil.rmtree(target)
            except OSError:
                pass
    print(removed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
