#!/usr/bin/env bash
# ledger.sh — invariant-validated append to ~/.openclaw/state/politician/pac-ledger.jsonl
#
# Every entry written to pac-ledger.jsonl MUST include:
#   date                ISO8601 UTC
#   amount              numeric (in the entry's `currency`, NOT pre-converted)
#   currency            "USD" | "JPY"
#   entity_domicile     "DE-LLC" | "527" | "Super-PAC" | "501c4" | "政治団体"
#   recipient_type      "candidate" | "party" | "PAC" | "independent-expenditure-vendor"
#                       | "internal-transfer" | "vendor-non-political"
#   kind                FEC line item (e.g. "line_11a_individual") or analogous JP code
#
# Optional:
#   stripe_transfer_id, destination, memo, related_filing
#
# Why these invariants:
#   currency           — defends against the foreign-national wall: USD entries
#                        belong on US filings, JPY entries on JP 収支報告書.
#                        Mixing leaks JP money into US PAC reporting → felony.
#   entity_domicile    — same defense from the opposite direction. The PAC
#                        ledger should never contain DE-LLC operating spend.
#   recipient_type     — FEC requires it; SpeechNow forbids "candidate" or
#                        coordinated "PAC" from a Super PAC. Validation here
#                        catches that BEFORE the entry hits disk.

# Path resolved consistently across modes.
_LEDGER_PATH="${POLITICIAN_LEDGER:-$HOME/.openclaw/state/politician/pac-ledger.jsonl}"

ledger_path() { printf '%s\n' "$_LEDGER_PATH"; }

# ledger_validate <json_string>
#   Echoes "ok" on success and returns 0; on failure prints reason on stderr
#   and returns 1.
#   Caller pattern:
#     if ! ledger_validate "$ENTRY"; then ... abort transfer ... ; fi
ledger_validate() {
  local entry="$1"
  python3 - <<'PY' "$entry"
import json, sys
ALLOWED_CURRENCY = {"USD", "JPY"}
ALLOWED_DOMICILE = {"DE-LLC", "527", "Super-PAC", "501c4", "政治団体"}
ALLOWED_RECIPIENT = {
    "candidate", "party", "PAC", "independent-expenditure-vendor",
    "internal-transfer", "vendor-non-political",
}
REQUIRED = ["date", "amount", "currency", "entity_domicile", "recipient_type", "kind"]

raw = sys.argv[1]
try:
    e = json.loads(raw)
except Exception as ex:
    sys.stderr.write(f"[ledger_validate] not-json: {ex}\n")
    sys.exit(1)

missing = [k for k in REQUIRED if k not in e]
if missing:
    sys.stderr.write(f"[ledger_validate] missing fields: {missing}\n")
    sys.exit(1)

if e["currency"] not in ALLOWED_CURRENCY:
    sys.stderr.write(f"[ledger_validate] currency must be in {sorted(ALLOWED_CURRENCY)}, got {e['currency']!r}\n")
    sys.exit(1)
if e["entity_domicile"] not in ALLOWED_DOMICILE:
    sys.stderr.write(f"[ledger_validate] entity_domicile must be in {sorted(ALLOWED_DOMICILE)}, got {e['entity_domicile']!r}\n")
    sys.exit(1)
if e["recipient_type"] not in ALLOWED_RECIPIENT:
    sys.stderr.write(f"[ledger_validate] recipient_type must be in {sorted(ALLOWED_RECIPIENT)}, got {e['recipient_type']!r}\n")
    sys.exit(1)

# Cross-field invariant: a Super-PAC entity domicile cannot have
# recipient_type=candidate or recipient_type=PAC (those would be coordinated
# contributions in violation of SpeechNow). 11 C.F.R. § 109.21.
if e["entity_domicile"] == "Super-PAC" and e["recipient_type"] in {"candidate", "PAC"}:
    sys.stderr.write("[ledger_validate] Super-PAC cannot contribute to candidate or PAC (SpeechNow)\n")
    sys.exit(1)

# Cross-field invariant: a 政治団体 (JP) entity must use JPY.
if e["entity_domicile"] == "政治団体" and e["currency"] != "JPY":
    sys.stderr.write("[ledger_validate] 政治団体 entries must be JPY (foreign-national wall)\n")
    sys.exit(1)
# And a US-domiciled entity (DE-LLC, 527, Super-PAC, 501c4) must use USD.
if e["entity_domicile"] in {"DE-LLC", "527", "Super-PAC", "501c4"} and e["currency"] != "USD":
    sys.stderr.write(f"[ledger_validate] {e['entity_domicile']} entries must be USD (foreign-national wall)\n")
    sys.exit(1)

# Numeric amount (>=0; refunds use kind=refund + negative amount which we
# don't allow yet — refunds get their own dedicated entry once the schema
# evolves).
try:
    a = float(e["amount"])
except Exception:
    sys.stderr.write("[ledger_validate] amount must be numeric\n")
    sys.exit(1)
if a < 0:
    sys.stderr.write("[ledger_validate] amount must be non-negative (refunds: separate kind=refund flow, NYI)\n")
    sys.exit(1)

print("ok")
PY
}

# ledger_append <json_string>
#   Validates, compacts (one-line JSONL), then atomically appends to the ledger.
#   Returns 0 on success, 1 on validation or write failure.
ledger_append() {
  local entry="$1"
  if ! ledger_validate "$entry" >/dev/null; then
    return 1
  fi
  # Compact to one line so JSONL grep/tail works correctly even if the
  # caller built the entry with multi-line jq -n output.
  local compact
  compact="$(printf '%s' "$entry" | jq -c .)" || return 1
  local p="$_LEDGER_PATH"
  mkdir -p "$(dirname "$p")"
  [[ -f "$p" ]] || : > "$p"
  printf '%s\n' "$compact" >> "$p"
}

# ledger_summary
#   Print a one-line summary suitable for slack_post fields.
ledger_summary() {
  local p="$_LEDGER_PATH"
  if [[ ! -f "$p" ]]; then
    printf 'ledger=missing\n'; return 0
  fi
  python3 - <<PY "$p"
import json, sys
from collections import defaultdict
totals_usd = defaultdict(float)
totals_jpy = defaultdict(float)
n = 0
bad = 0
with open(sys.argv[1]) as f:
    for ln in f:
        ln = ln.strip()
        if not ln: continue
        n += 1
        try:
            e = json.loads(ln)
        except Exception:
            bad += 1; continue
        cur = e.get("currency"); amt = float(e.get("amount", 0))
        dom = e.get("entity_domicile", "?")
        if cur == "USD":
            totals_usd[dom] += amt
        elif cur == "JPY":
            totals_jpy[dom] += amt
parts = [f"entries={n}"]
if bad: parts.append(f"invalid={bad}")
for dom, t in sorted(totals_usd.items()):
    parts.append(f"USD/{dom}=\${t:.2f}")
for dom, t in sorted(totals_jpy.items()):
    parts.append(f"JPY/{dom}=¥{t:.0f}")
print(" ".join(parts))
PY
}
