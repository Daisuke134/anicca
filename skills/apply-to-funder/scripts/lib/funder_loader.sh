#!/usr/bin/env bash
# funder_loader.sh — sources the funder JSON spec into env vars, validates basics.
# Reads $1 (path to funders/<id>.json). Exports: FUNDER_ID, FUNDER_NAME, FUNDER_URL,
# FUNDER_TYPE, FUNDER_VERIFIED, FUNDER_CAPTCHA, FUNDER_AUTH_KIND.

funder_load() {
  local spec="$1"
  [ ! -f "$spec" ] && { echo "🚨 spec not found: $spec"; return 1; }

  export FUNDER_ID=$(jq -r '.id' "$spec")
  export FUNDER_NAME=$(jq -r '.name' "$spec")
  export FUNDER_URL=$(jq -r '.url' "$spec")
  export FUNDER_TYPE=$(jq -r '.funder_type' "$spec")
  export FUNDER_VERIFIED=$(jq -r '.verified' "$spec")
  export FUNDER_CAPTCHA=$(jq -r '.captcha // "null"' "$spec")
  export FUNDER_AUTH_KIND=$(jq -r '.auth.kind // "none"' "$spec")
  export FUNDER_AUTH_BLOCKING=$(jq -r '.auth.blocking // false' "$spec")
  export FUNDER_DEADLINE=$(jq -r '.next_deadline // ""' "$spec")
  export FUNDER_CURRENCY=$(jq -r '.currency' "$spec")

  echo "  loaded: id=$FUNDER_ID  type=$FUNDER_TYPE  verified=$FUNDER_VERIFIED  auth=$FUNDER_AUTH_KIND"

  # Guardrail 1: CAPTCHA → abort early
  if [ "$FUNDER_CAPTCHA" != "null" ] && [ -n "$FUNDER_CAPTCHA" ]; then
    echo "🚨 funder requires CAPTCHA ($FUNDER_CAPTCHA) — autonomous submit aborted."
    echo "   Run MODE=prepare to draft, then submit manually."
    if [ "${MODE:-submit}" = "submit" ] && [ "${DRY_RUN:-false}" != "true" ]; then
      echo "   Aborting submit. Use MODE=prepare to still produce drafts."
      return 10
    fi
  fi

  # Guardrail 2: institutional 2FA blocking
  if [ "$FUNDER_AUTH_BLOCKING" = "true" ] && [ "${MODE:-submit}" = "submit" ] && [ "${DRY_RUN:-false}" != "true" ]; then
    local msg=$(jq -r '.auth.human_required_message // "🚨 human-only auth required"' "$spec")
    echo "$msg"
    return 11
  fi

  return 0
}
