#!/usr/bin/env bash
set -euo pipefail

BASELINE=134500
TARGET=80000
context_output="$(mktemp "${TMPDIR:-/tmp}/floor-context.XXXXXX")"
trap 'rm -f "${context_output}"' EXIT

claude -p "/context" --output-format text >"${context_output}"

total="$(
  python3 - "${context_output}" <<'PY'
from pathlib import Path
import re
import sys

labels = (
    "System prompt",
    "System tools",
    "MCP",
    "Custom agents",
    "Memory",
    "Skills",
)
total = 0
seen = set()
for line in Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace").splitlines():
    normalized = line.strip()
    label = next((item for item in labels if item.lower() in normalized.lower()), None)
    if label is None:
        continue
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*k(?:\s+tokens?)?", normalized, re.I)
    if not match:
        match = re.search(r"([0-9][0-9,]*)\s+tokens?", normalized, re.I)
    if not match:
        continue
    key = (label, normalized)
    if key in seen:
        continue
    seen.add(key)
    value = float(match.group(1).replace(",", ""))
    if "k" in match.group(0).lower():
        value *= 1000
    total += round(value)
if total <= 0:
    raise SystemExit("could not parse token categories from /context output")
print(total)
PY
)"

reduction=$((BASELINE - total))
printf 'baseline=%d tokens\n' "${BASELINE}"
printf 'current=%d tokens\n' "${total}"
printf 'reduction=%d tokens\n' "${reduction}"
printf 'target=%d tokens\n' "${TARGET}"

if (( total <= TARGET )); then
  printf 'PASS: startup context is at or below target.\n'
  exit 0
fi

printf 'FAIL: startup context exceeds target by %d tokens.\n' "$((total - TARGET))"
printf '%s\n' 'Remaining candidates: disable whole unused plugins; reduce custom-agent definitions; audit unmeasured SessionStart output; remove additional unused MCP servers.'
exit 1
