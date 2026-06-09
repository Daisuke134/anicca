#!/usr/bin/env bash
# Unit: compose.py --offline reads fixtures and prints header + body, NO LLM call,
# NO outbound. Asserts every required section header appears verbatim.
set -euo pipefail
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PY="$SKILL_DIR/.venv/bin/python"

OUT="$("$PY" "$SKILL_DIR/scripts/compose.py" --offline \
  --cfo "$SKILL_DIR/tests/fixtures/anicca-cfo.json" \
  --heartbeat "$SKILL_DIR/tests/fixtures/heartbeat.jsonl" \
  --violations "$SKILL_DIR/tests/fixtures/violations.jsonl" \
  --now 2026-06-04T06:00:00+09:00)"

# Required subject prefix
echo "$OUT" | head -1 | grep -qE '^SUBJECT: \[Anicca\] Day [0-9]+ — MRR \$27' || { echo "FAIL subject"; exit 1; }

# Required section headers verbatim
for h in 'Headline (2026-06-04):' "Yesterday's heartbeat:" "Constitution-violations (24h):" "Errors from friction-fixer (24h):" "What I did:" "— Anicca"; do
  echo "$OUT" | grep -qF "$h" || { echo "FAIL missing section: $h"; exit 1; }
done

# Numeric correctness from fixture
echo "$OUT" | grep -qE 'MRR:[[:space:]]+\$27\.00' || { echo "FAIL MRR number"; exit 1; }
echo "$OUT" | grep -qE 'Runtime cost:[[:space:]]+\$99\.00' || { echo "FAIL runtime number"; exit 1; }
echo "$OUT" | grep -qE 'Status:[[:space:]]+HUNGRY' || { echo "FAIL status"; exit 1; }

# Heartbeat ratio = 2 ok / 3 total in last 24h
echo "$OUT" | grep -qE '2/3 ok' || { echo "FAIL heartbeat ratio"; exit 1; }

# Friction-fixer row renders the real schema (pattern_id / fix_script / exit_code / evidence)
echo "$OUT" | grep -qF '[P12] fix-disk-full.sh (resolved) — 93%→61%' || { echo "FAIL friction row render"; exit 1; }

echo "PASS"
