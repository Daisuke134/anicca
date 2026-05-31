"""FR-013 — find Pattern-Keys recurring N+ times in a .learnings/*.md file.

A recurring Pattern-Key in ERRORS.md (≥ 2 occurrences) is a signal that a
new skill should be extracted; in LEARNINGS.md it's a signal that a
best-practice should be promoted to a SOP. The heartbeat reads this
module's output to queue skill-extraction work (Plan-T18).

Public API:
    find_recurring_patterns(path: str, min_count: int = 2) -> dict[str, int]

CLI:
    python3 pattern-extract.py <path> [<min_count>]
    # prints '<count>\t<key>' per recurring pattern, sorted by count desc.
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

KEY_RE = re.compile(r"^\s*\*\*Pattern-Key\*\*\s*:\s*(\S+)", re.MULTILINE)


def find_recurring_patterns(path: str, min_count: int = 2) -> dict:
    """Return {key: count} for keys whose count ≥ min_count.

    Missing or unreadable file → empty dict (don't crash the caller).
    """
    try:
        text = Path(path).read_text()
    except (FileNotFoundError, PermissionError, OSError):
        return {}
    counts = Counter(KEY_RE.findall(text))
    return {k: v for k, v in counts.items() if v >= min_count}


def _main() -> int:
    if len(sys.argv) < 2:
        print("usage: pattern-extract.py <path> [<min_count>]", file=sys.stderr)
        return 2
    path = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    recs = find_recurring_patterns(path, n)
    # Sort by count desc, then key asc for stable output.
    for key, count in sorted(recs.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"{count}\t{key}")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
