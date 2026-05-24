#!/usr/bin/env bash
# Pick the next script from bank_<lang>.jsonl, write to state/current_<lang>.json.
# Increments state/last_index_<lang>.json (wraps on overflow).
set -euo pipefail
LANG_ARG="${1:?usage: rotate_script.sh <en|jp>}"
ROOT="$HOME/anicca-monk-factory"
BANK="$ROOT/scripts/bank_$LANG_ARG.jsonl"
IDX_FILE="$ROOT/state/last_index_$LANG_ARG.json"
CUR_FILE="$ROOT/state/current_$LANG_ARG.json"

python3 - <<PY
import json, os, sys
bank = "$BANK"
idx_file = "$IDX_FILE"
cur_file = "$CUR_FILE"

# Load lines
with open(bank, encoding='utf-8') as f:
    lines = [l.rstrip('\n') for l in f if l.strip()]
total = len(lines)
if total == 0:
    print("❌ bank empty", file=sys.stderr); sys.exit(2)

# Read last index
try:
    last = json.load(open(idx_file)).get('index', -1)
except Exception:
    last = -1

next_i = (last + 1) % total
selected = json.loads(lines[next_i])

# Write current + new index
with open(cur_file, 'w', encoding='utf-8') as f:
    json.dump(selected, f, ensure_ascii=False, indent=2)
with open(idx_file, 'w') as f:
    json.dump({'index': next_i}, f)

print(f"✅ rotated to index {next_i}/{total-1}: {selected.get('id','?')} formula={selected.get('formula','?')}")
PY
