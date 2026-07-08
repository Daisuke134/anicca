"""Kill-switch check -- the shared fail-closed pause mechanism for all three funding scripts.
Matches skills/earn/polymarket-trade's own convention ("touch KILL in this dir -> next run
exits without trading"), reused here for the funding skill's own KILL file.
"""
from __future__ import annotations

import os


def is_killed(skill_dir: str) -> bool:
    return os.path.exists(os.path.join(skill_dir, "KILL"))
