#!/usr/bin/env python3
"""Compatibility imports for the canonical shared learning controller."""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from marketing.engine.learning.controller import (  # noqa: E402
    consume_weights,
    run_learning_controller,
)

__all__ = ["consume_weights", "run_learning_controller"]
