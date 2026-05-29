#!/usr/bin/env bash
# signature.sh — FR-007 mail-signature picker.
#
# Args:
#   $1 = thread_from  (the From: address of the inbound thread; required)
#   $2 = thread_to_csv (comma-separated recipients on the inbound thread; optional)
#
# Stdout: a ready-to-append signature block (no leading blank line; caller adds spacing).
#
# Rule:
#   If $thread_from or $thread_to_csv contains the user's workEmail
#   (case-insensitive, substring match), emit the legal name only.
#   Otherwise emit Anicca + businessEmail + JP-formatted phone (+optional website).
#
# Profile is read from ~/.openclaw/identity/profile.json (gitignored personal data).

set -uo pipefail

THREAD_FROM="${1:-}"
THREAD_TO="${2:-}"
PROFILE="$HOME/.openclaw/identity/profile.json"

if [ ! -f "$PROFILE" ]; then
  echo "[signature] profile.json missing at $PROFILE" >&2
  exit 2
fi

WORK_EMAIL=$(python3 -c "import json; print(json.load(open('$PROFILE'))['contact']['workEmail'])")

# Lowercase the search corpus + needle for a stable case-insensitive substring check.
WORK_EMAIL_LC=$(printf '%s' "$WORK_EMAIL" | tr '[:upper:]' '[:lower:]')
SEARCH_LC=$(printf '%s %s' "$THREAD_FROM" "$THREAD_TO" | tr '[:upper:]' '[:lower:]')

if [ -n "$WORK_EMAIL_LC" ] && printf '%s' "$SEARCH_LC" | grep -qF "$WORK_EMAIL_LC"; then
  # Work thread → legal name only
  python3 -c "import json; print(json.load(open('$PROFILE'))['identity']['legalName'])"
  exit 0
fi

# Default (personal / business / vendor): Anicca + business contact line
BUSINESS_EMAIL=$(python3 -c "import json; d=json.load(open('$PROFILE')); print(d['contact'].get('businessEmail',''))")
PHONE_RAW=$(python3 -c "import json; print(json.load(open('$PROFILE'))['contact']['phone'])")
WEBSITE=$(python3 -c "import json; d=json.load(open('$PROFILE')); print((d.get('business') or {}).get('website',''))")

# Format phone +81XXXXXXXXXX → '+81 XX-XXXX-XXXX' (10 digits after +81).
PHONE_FMT=$(printf '%s' "$PHONE_RAW" | sed -E 's/^\+81([0-9]{2})([0-9]{4})([0-9]{4})$/+81 \1-\2-\3/')

printf '%s\n' "Anicca"
if [ -n "$BUSINESS_EMAIL" ] && [ -n "$PHONE_FMT" ]; then
  if [ -n "$WEBSITE" ]; then
    printf '%s · %s · %s\n' "$BUSINESS_EMAIL" "$PHONE_FMT" "$WEBSITE"
  else
    printf '%s · %s\n' "$BUSINESS_EMAIL" "$PHONE_FMT"
  fi
elif [ -n "$BUSINESS_EMAIL" ]; then
  printf '%s\n' "$BUSINESS_EMAIL"
elif [ -n "$PHONE_FMT" ]; then
  printf '%s\n' "$PHONE_FMT"
fi
