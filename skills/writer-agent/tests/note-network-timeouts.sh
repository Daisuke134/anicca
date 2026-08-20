#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PUBLISHER="$ROOT/scripts/publish-note.sh"

python3 - "$PUBLISHER" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
offenders = []
for number, line in enumerate(path.read_text().splitlines(), 1):
    stripped = line.lstrip()
    if "curl " in stripped and "--max-time " not in stripped:
        offenders.append((number, stripped))
assert not offenders, f"unbounded curl calls: {offenders}"
PY

echo "PASS: every note publisher network call has a deadline"
