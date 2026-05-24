#!/usr/bin/env bash
# submit.sh — drive {{profile.lateness.stakeholders.channel}}-harness through the funder spec.
#
# Inputs:  $1 = path to funders/<id>.json
# Reads:   data/drafts/<funder>/.latest_payload  → resolved field values
# Env:     DRY_RUN  (true → print plan, never click submit)
#
# Guardrails:
#   - CAPTCHA → abort (handled in funder_loader.sh)
#   - missing required file path → abort
#   - K-Dense placeholders still pending → abort
#   - 2FA-blocking auth → abort

set -uo pipefail

SPEC="$1"
SKILL_DIR="${SKILL_DIR:-$HOME/.openclaw/skills/apply-to-funder}"
DRY_RUN="${DRY_RUN:-false}"
FUNDER_ID=$(jq -r '.id' "$SPEC")
DRAFT_DIR="$SKILL_DIR/data/drafts/$FUNDER_ID"
PAYLOAD_FILE=$(cat "$DRAFT_DIR/.latest_payload" 2>/dev/null || echo "")

[ -z "$PAYLOAD_FILE" ] || [ ! -f "$PAYLOAD_FILE" ] && {
  echo "🚨 no prepared payload — run MODE=prepare first"
  exit 4
}

echo "▶ submit  funder=$FUNDER_ID  payload=$PAYLOAD_FILE"

# Guardrail: K-Dense placeholders still present?
PENDING=$(jq -r 'to_entries[] | select(.value | tostring | test("__KDENSE_PENDING__")) | .key' "$PAYLOAD_FILE")
if [ -n "$PENDING" ]; then
  echo "🚨 K-Dense draft fields still pending — agent must fill these before submit:"
  echo "$PENDING" | sed 's/^/   - /'
  echo "   See $DRAFT_DIR/*.kdense.md for the draft requests."
  exit 5
fi

# Guardrail: file inputs must exist
FILE_FIELDS=$(jq -r '.pages[].fields[]? | select(.type=="file") | "\(.name)|\(.value_source)"' "$SPEC")
while IFS='|' read -r FNAME FSRC; do
  [ -z "$FNAME" ] && continue
  if [[ "$FSRC" == config.* ]]; then
    PATH_VAL=$(jq -r ".config[\"${FSRC#config.}\"]" "$SPEC")
    EXPANDED="${PATH_VAL/#\~/$HOME}"
    if [ ! -f "$EXPANDED" ]; then
      echo "🚨 file-input '$FNAME' missing on disk: $EXPANDED — abort."
      [ "$DRY_RUN" != "true" ] && exit 6
      echo "   [DRY_RUN] continuing despite missing file"
    fi
  fi
done <<< "$FILE_FIELDS"

# --- Plan output (always print, even live) ---
echo ""
echo "── {{profile.lateness.stakeholders.channel}} plan for $FUNDER_ID ──"
echo "  1. ensure Chrome 9223 ({{profile.lateness.stakeholders.channel}}-harness Way 2)"
AUTH_KIND=$(jq -r '.auth.kind // "none"' "$SPEC")
if [ "$AUTH_KIND" = "session_cookie" ]; then
  LOGIN_URL=$(jq -r '.auth.login_url' "$SPEC")
  echo "  2. login flow: visit $LOGIN_URL ; if redirected to sign_in → fill {{profile.lateness.stakeholders.channel}}/pw from env"
fi
DRAFT_STRATEGY=$(jq -r '.draft_resolution.strategy // "none"' "$SPEC")
if [ "$DRAFT_STRATEGY" = "continue_or_start" ]; then
  HOME_URL=$(jq -r '.draft_resolution.home_url' "$SPEC")
  echo "  3. resolve draft: visit $HOME_URL → click Continue/Start → extract draft_id"
fi
echo "  4. for each page in spec.pages:"
jq -r '.pages[] | "       - page=\(.name)  path_suffix=\(.path_suffix)  fields=\(.fields | length)"' "$SPEC"
echo "  5. for each field: lookup value from $PAYLOAD_FILE, fill via lib/form_filler.sh"
SUB_BTN=$(jq -r '.submit.button_text // "Submit"' "$SPEC")
SUB_URL_PAT=$(jq -r '.submit.success_url_pattern // "submitted"' "$SPEC")
echo "  6. click '$SUB_BTN'; verify URL matches /$SUB_URL_PAT/"
echo "── end plan ──"

if [ "$DRY_RUN" = "true" ]; then
  echo ""
  echo "  [DRY_RUN] not driving {{profile.lateness.stakeholders.channel}}, not clicking Submit. Plan-only."
  STATE_FILE="$SKILL_DIR/data/applications/$FUNDER_ID-latest.json"
  mkdir -p "$(dirname "$STATE_FILE")"
  jq -n --arg id "$FUNDER_ID" --arg payload "$PAYLOAD_FILE" --arg ts "$(date -u +%FT%TZ)" \
    '{funder_id:$id, payload:$payload, status:"dry_run_planned", planned_at:$ts}' \
    > "$STATE_FILE"
  echo "  state → $STATE_FILE"
  exit 0
fi

# --- Live mode: hand off to form_filler.sh ---
echo ""
echo "▶ live submit — invoking form_filler.sh"
bash "$SKILL_DIR/scripts/lib/form_filler.sh" "$SPEC" "$PAYLOAD_FILE"
RC=$?
exit $RC
