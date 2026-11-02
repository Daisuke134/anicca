#!/usr/bin/env python3
"""Portable entrypoint for the shared HQ receiver, worker, and scheduler."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from runtime.team_hq.main import main

if __name__ == "__main__":
    raise SystemExit(main())
