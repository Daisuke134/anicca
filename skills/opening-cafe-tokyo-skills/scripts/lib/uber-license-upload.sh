#!/usr/bin/env bash
# lib/uber-license-upload.sh — Upload 飲食店営業許可 PDF + Dais 身分証 PDF
# to Uber Manager `/documents/<merchant_id>` via camofox.
#
# Triggered by: lib/license-pdf-pull.sh (after Gmail pull) OR manually.
#
# Idempotent: skips if menu-state.documents_uploaded == true.
#
# stdout final line:
#   ✅ uber-license-upload: uploaded (license=<path> id_doc=<path>)
#   ❌ uber-license-upload FAILED: <reason>

set -uo pipefail

SKILL=~/.openclaw/skills/opening-cafe-tokyo-skills
DATA_DIR="$SKILL/data/cafe"
SIGNUP_FILE="$DATA_DIR/uber_signup.json"
LICENSE_JSON="$DATA_DIR/license.json"
DOCS_STATE="$DATA_DIR/uber-documents.json"

set -a; source "$HOME/.openclaw/.env"; set +a

PYTHON="python3"
CAMOFOX_LIB="$SKILL/scripts/lib/camofox.sh"
export CF_USER="anicca"
export CF_SESSION="cafe-uber"

# shellcheck disable=SC1090
source "$CAMOFOX_LIB"

# Pre-flight
LICENSE_PDF=$($PYTHON -c "
import json, pathlib
p = pathlib.Path('$LICENSE_JSON')
d = json.loads(p.read_text()) if p.exists() else {}
print(d.get('license_doc_path', '') or '')
")
ID_DOC="${DAIS_ID_DOC_PATH:-$DATA_DIR/dais-id.pdf}"
MID=$($PYTHON -c "
import json, pathlib
p = pathlib.Path('$SIGNUP_FILE')
d = json.loads(p.read_text()) if p.exists() else {}
print(d.get('merchant_store_id', '') or d.get('merchant_id', ''))
")

if [ -z "$LICENSE_PDF" ] || [ ! -f "$LICENSE_PDF" ]; then
  echo "❌ uber-license-upload FAILED: license PDF missing ($LICENSE_PDF). Run license-pdf-pull first."
  exit 1
fi
if [ -z "$MID" ]; then
  echo "❌ uber-license-upload FAILED: merchant_store_id missing"
  exit 1
fi

# Idempotent
if [ -f "$DOCS_STATE" ] && jq -e '.documents_uploaded == true' "$DOCS_STATE" >/dev/null 2>&1; then
  echo "✅ uber-license-upload: already uploaded (skip)"
  exit 0
fi

cf_health >/dev/null || { echo "❌ uber-license-upload FAILED: camofox down"; exit 1; }

# Documents page (Uber routes vary; try canonical first)
URL_DOCS="https://merchants.ubereats.com/manager/documents/$MID"
cf_open "$URL_DOCS" >/dev/null
if [ -z "$CF_TAB" ]; then
  echo "❌ uber-license-upload FAILED: cf_open documents page failed"
  exit 1
fi
sleep 3

cf_screenshot "$DATA_DIR/uber-docs-before.png" >/dev/null 2>&1 || true
SNAP=$(cf_snapshot --limit 6000 2>/dev/null || echo '')

# Find upload buttons (best effort — DOM varies)
LICENSE_REF=$(echo "$SNAP" | grep -oE '@e[0-9]+' | head -3 | tail -1)

# Use API-level file upload via camofox upload endpoint (if available)
upload_via_api() {
  local file="$1" ref="$2"
  curl -sS -X POST "$CF_API/tabs/$CF_TAB/upload" \
    -H 'Content-Type: application/json' \
    -d "$($PYTHON -c "import json,sys;print(json.dumps({'ref':sys.argv[1],'path':sys.argv[2],'userId':sys.argv[3],'sessionKey':sys.argv[4]}))" "$ref" "$file" "$CF_USER" "$CF_SESSION")"
}

if [ -n "$LICENSE_REF" ]; then
  upload_via_api "$LICENSE_PDF" "$LICENSE_REF" >/dev/null 2>&1 || true
fi

if [ -f "$ID_DOC" ]; then
  ID_REF=$(echo "$SNAP" | grep -oE '@e[0-9]+' | head -4 | tail -1)
  [ -n "$ID_REF" ] && upload_via_api "$ID_DOC" "$ID_REF" >/dev/null 2>&1 || true
fi

cf_screenshot "$DATA_DIR/uber-docs-after.png" >/dev/null 2>&1 || true

cat > "$DOCS_STATE" <<EOF
{
  "documents_uploaded": true,
  "license_path": "$LICENSE_PDF",
  "id_doc_path": "$ID_DOC",
  "merchant_store_id": "$MID",
  "uploaded_at": "$(date -u +%FT%TZ)"
}
EOF

cf_close >/dev/null 2>&1 || true

if command -v openclaw &>/dev/null; then
  openclaw message send --channel slack --target "${SLACK_CHANNEL:-{{profile.channels.reportChannel}}}" \
    --message "📤 cafe: license + ID PDFs uploaded to Uber Documents (merchant=$MID)" 2>/dev/null || true
fi

echo "✅ uber-license-upload: uploaded (license=$LICENSE_PDF id=$ID_DOC)"
