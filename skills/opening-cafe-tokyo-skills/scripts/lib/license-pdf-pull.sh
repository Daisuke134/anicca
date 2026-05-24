#!/usr/bin/env bash
# lib/license-pdf-pull.sh — auto-pull 飲食店営業許可 PDF from Gmail.
#
# Searches Gmail for license-related attachments (PDF/JPG/PNG) from likely
# senders (新宿区保健所 / shinjuku.lg.jp / shinjuku-ku.lg.jp / theghostrestaurant
# /kashispace / kumato / GoodKitchen) within last 30 days.
#
# Saves to data/cafe/license.pdf + extracts license number/type/expires (best
# effort regex on filename + body) into data/cafe/license.json.
#
# Idempotent: skips if license.json already has license_number filled.
#
# stdout final line:
#   ✅ license-pdf-pull: <result> (saved=<path>)
#   ❌ license-pdf-pull FAILED: <reason>

set -uo pipefail

SKILL=~/.openclaw/skills/opening-cafe-tokyo-skills
DATA_DIR="$SKILL/data/cafe"
LICENSE_JSON="$DATA_DIR/license.json"
LICENSE_PDF="$DATA_DIR/license.pdf"
mkdir -p "$DATA_DIR"

set -a; source "$HOME/.openclaw/.env"; set +a
: "${GOG_ACCOUNT:={{profile.contact.personalEmail}}}"
export GOG_ACCOUNT GOG_KEYRING_PASSWORD

# Idempotent: already pulled?
if [ -f "$LICENSE_JSON" ]; then
  EXISTING=$(jq -r '.license_number // empty' "$LICENSE_JSON" 2>/dev/null)
  if [ -n "$EXISTING" ]; then
    echo "✅ license-pdf-pull: already pulled (license=$EXISTING)"
    exit 0
  fi
fi

if ! command -v gog &>/dev/null; then
  echo "❌ license-pdf-pull FAILED: gog CLI missing"; exit 1
fi

# Search Gmail (last 30d, attachment, license keyword variants)
QUERY='subject:(営業許可 OR 飲食店 OR license) has:attachment newer_than:30d'
RESULTS=$(gog gmail search --query "$QUERY" --account "$GOG_ACCOUNT" --max 10 --json 2>/dev/null || echo '{"messages":[]}')
MSG_IDS=$(echo "$RESULTS" | jq -r '.messages[]?.id // empty' 2>/dev/null)

if [ -z "$MSG_IDS" ]; then
  echo "❌ license-pdf-pull FAILED: no matching {{profile.lateness.stakeholders.channel}}s found"
  cat > "$LICENSE_JSON" <<EOF
{
  "status": "awaiting_{{profile.lateness.stakeholders.channel}}",
  "license_number": null,
  "license_type": null,
  "license_expires": null,
  "license_doc_path": null,
  "checked_at": "$(date -u +%FT%TZ)"
}
EOF
  exit 1
fi

# Walk messages, find first attachment with PDF or image
SAVED=""
LICENSE_NUMBER=""
LICENSE_TYPE=""
LICENSE_EXPIRES=""

while IFS= read -r MID; do
  [ -z "$MID" ] && continue
  ATTS=$(gog gmail get "$MID" --account "$GOG_ACCOUNT" --json 2>/dev/null | jq -r '.payload.parts[]? | select(.filename != "" and .filename != null) | "\(.body.attachmentId)\t\(.filename)\t\(.mimeType)"')
  while IFS=$'\t' read -r AID FN MT; do
    [ -z "$AID" ] && continue
    case "$MT" in
      application/pdf|image/*)
        gog gmail attachment "$MID" --attachment-id "$AID" --account "$GOG_ACCOUNT" --out "$LICENSE_PDF" 2>/dev/null && SAVED="$LICENSE_PDF"
        # Extract from filename / body
        BODY=$(gog gmail get "$MID" --account "$GOG_ACCOUNT" --json 2>/dev/null | jq -r '.snippet // ""')
        LICENSE_NUMBER=$(echo "$BODY $FN" | grep -oE '第\s*[0-9]{6,}\s*号' | head -1 || true)
        LICENSE_TYPE=$(echo "$BODY" | grep -oE '飲食店営業[許可]*' | head -1 || true)
        LICENSE_EXPIRES=$(echo "$BODY" | grep -oE '20[0-9]{2}年[0-9]{1,2}月[0-9]{1,2}日' | tail -1 || true)
        [ -n "$SAVED" ] && break 2
        ;;
    esac
  done <<< "$ATTS"
done <<< "$MSG_IDS"

if [ -z "$SAVED" ]; then
  echo "❌ license-pdf-pull FAILED: no PDF/image attachment in matching {{profile.lateness.stakeholders.channel}}s"
  exit 1
fi

cat > "$LICENSE_JSON" <<EOF
{
  "status": "pulled",
  "license_number": "${LICENSE_NUMBER:-pending_extract}",
  "license_type": "${LICENSE_TYPE:-飲食店営業許可}",
  "license_expires": "${LICENSE_EXPIRES:-pending_extract}",
  "license_doc_path": "$SAVED",
  "pulled_at": "$(date -u +%FT%TZ)"
}
EOF

# Slack notify
if command -v openclaw &>/dev/null; then
  openclaw message send --channel slack --target "${SLACK_CHANNEL:-{{profile.channels.reportChannel}}}" \
    --message "🪪 license PDF pulled from Gmail → $SAVED (number=${LICENSE_NUMBER:-pending})" 2>/dev/null || true
fi

# Auto-trigger phase: license-upload (if Uber merchant exists)
if [ -f "$DATA_DIR/uber_signup.json" ]; then
  if jq -e '.merchant_store_id' "$DATA_DIR/uber_signup.json" >/dev/null 2>&1; then
    bash "$SKILL/scripts/lib/uber-license-upload.sh" 2>/dev/null || true
  fi
fi

echo "✅ license-pdf-pull: pulled (saved=$SAVED license=${LICENSE_NUMBER:-pending})"
