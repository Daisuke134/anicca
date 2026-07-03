#!/usr/bin/env bash
# identity/accounts.sh — per-install credential registry (REQ-15, REQ-11).
#
# INTERFACE:
#   env in:  ARTICLE_DIR (state dir)
#   env in:  NOTE_SESSION_COOKIE / SUBSTACK_API_KEY / X_API_KEY / ZENN_TOKEN / DEVTO_API_KEY
#            (each optional; presence activates that rail's registry slot — REQ-15)
#   env in:  <RAIL>_SELF_CREATE=1 → attempt a zero-human self-create for a PROVEN rail (REQ-11);
#            otherwise an absent-credential rail is flagged "unavailable", never a loud failure.
#   writes:  $ARTICLE_DIR/state/accounts.json — { "<rail>": "active" | "unavailable", ... }
#   NEVER reads or writes a shared/hardcoded Dais account literal (REQ-15) — every credential comes from
#   THIS install's own environment.
set -uo pipefail

ARTICLE_DIR="${ARTICLE_DIR:-}"
if [ -z "$ARTICLE_DIR" ]; then
  echo "identity/accounts.sh: ARTICLE_DIR is required" >&2
  exit 1
fi
mkdir -p "$ARTICLE_DIR/state"

# rail:credential-env-var pairs. Each credential comes ONLY from THIS install's own environment (REQ-15) —
# never a hardcoded/shared literal.
RAILS="note:NOTE_SESSION_COOKIE substack:SUBSTACK_API_KEY x:X_API_KEY zenn:ZENN_TOKEN devto:DEVTO_API_KEY"

# Rails whose zero-human self-create path is PROVEN (REQ-11: e.g. the Instagram Gmail-plus-address +
# OTP-auto-read pattern). None of this skill's rails have a proven self-create path yet — note/X account
# creation is phone-gated and NOT yet proven — so self-create always falls through to "unavailable" today.
# This list is the seam a later sprint extends once a rail's self-create is proven.
PROVEN_SELF_CREATE_RAILS=""

json="{"
first=1
for pair in $RAILS; do
  rail="${pair%%:*}"
  envvar="${pair##*:}"
  cred="$(eval "printf '%s' \"\${$envvar:-}\"")"

  status="unavailable"
  if [ -n "$cred" ]; then
    status="active"
  else
    self_create_var="$(echo "$rail" | tr '[:lower:]' '[:upper:]')_SELF_CREATE"
    self_create_flag="$(eval "printf '%s' \"\${$self_create_var:-}\"")"
    if [ "$self_create_flag" = "1" ]; then
      case " $PROVEN_SELF_CREATE_RAILS " in
        *" $rail "*)
          # Proven rail: attempt zero-human self-create (Sprint 2+ live seam). Never a loud failure either
          # way — a failed attempt still flags "unavailable", it does not abort the wake.
          status="unavailable"
          ;;
        *)
          status="unavailable"
          ;;
      esac
    fi
  fi

  if [ $first -eq 0 ]; then json="$json,"; fi
  first=0
  json="$json\"$rail\": \"$status\""
done
json="$json}"

tmp="$(mktemp "$ARTICLE_DIR/state/.accounts.json.XXXXXX")"
printf '%s\n' "$json" > "$tmp"
mv "$tmp" "$ARTICLE_DIR/state/accounts.json"

echo "ACCOUNTS_REGISTRY: wrote $ARTICLE_DIR/state/accounts.json"
exit 0
