#!/usr/bin/env bash
# lib/letsfg.sh — flight search via LetsFG CLI
# Usage: bash lib/letsfg.sh <origin> <dest> <depart_date> <return_date> [currency] [out_json]
set -euo pipefail

ORIGIN="${1:-NRT}"
DEST="${2:-SFO}"
DEP="${3}"
RET="${4}"
CUR="${5:-JPY}"
OUT="${6:-/tmp/letsfg-${ORIGIN}-${DEST}-${DEP}.json}"

letsfg search "$ORIGIN" "$DEST" "$DEP" --return "$RET" --direct --currency "$CUR" --limit 30 --json 2>/dev/null > "$OUT" || {
  echo "❌ letsfg failed"
  exit 1
}

python3 << PY
import json
data = json.load(open("$OUT"))
offers = data if isinstance(data, list) else data.get('offers', data.get('results', []))
def to_jpy(o):
    p = o.get('price', 999999); c = o.get('currency', '?')
    if c == 'JPY': return p
    if c == 'USD': return p * 156
    if c == 'EUR': return p * 165
    if c == 'GBP': return p * 195
    return 999999
sorted_offers = sorted(offers, key=to_jpy)
print(f"Total: {len(offers)} offers")
for i, o in enumerate(sorted_offers[:5]):
    out = o.get('outbound',{}).get('segments',[{}])[0]
    inb = o.get('inbound',{}).get('segments',[{}])[0] if o.get('inbound') else {}
    last_in = o.get('inbound',{}).get('segments',[{}])[-1] if o.get('inbound') else {}
    print(f"#{i+1} ¥{to_jpy(o):>8,.0f} | {o.get('source','?'):15} | OUT: {out.get('airline_name','?')[:12]} {out.get('departure','')[:16]} | IN: {inb.get('airline_name','?')[:12]} {inb.get('departure','')[:16]}")
PY
