#!/usr/bin/env bash
# publish-substack.sh — publish article to aniccabuddha.substack.com via Substack API
# Substack has an undocumented but working API at /api/v1/drafts that we POST to.
# Uses session cookies stored in ~/.openclaw/.env SUBSTACK_SESSION_COOKIE
#
# Usage:
#   bash publish-substack.sh --markdown-file <f> --title <t> --subtitle <s>
# stdout: release URL

set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

MD_FILE=""
TITLE=""
SUBTITLE=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --markdown-file) MD_FILE="$2"; shift 2 ;;
    --title)         TITLE="$2"; shift 2 ;;
    --subtitle)      SUBTITLE="$2"; shift 2 ;;
    --meta)          SUBTITLE="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 1 ;;
  esac
done
[[ -f "$MD_FILE" && -n "$TITLE" ]] || { echo "FATAL: --markdown-file --title required" >&2; exit 1; }

# --- fail-closed PII gate (scripts/pii-gate.py) ---------------------------------------
# Nothing operator-identifying may reach Substack. ANY non-zero exit from the gate -- a finding,
# an unconfigured blocklist, or an internal scanner error -- aborts this publish. Gate output
# goes to stderr so it cannot pollute this script's single-line stdout contract.
python3 "$DIR/pii-gate.py" --stage publish-substack "$MD_FILE" >&2 || exit $?


set -a; . "$HOME/.openclaw/.env" 2>/dev/null; set +a
[[ -n "${SUBSTACK_SESSION_COOKIE:-}" ]] || { echo "FATAL: SUBSTACK_SESSION_COOKIE missing in ~/.openclaw/.env" >&2; exit 2; }

PUBLICATION="${SUBSTACK_PUBLICATION:-aniccabuddha.substack.com}"
SUBDOMAIN="${PUBLICATION%.substack.com}"
# Resolve the byline from the authenticated publication ownership response.
# A hard-coded user ID can silently publish under the wrong identity after an
# account migration; exactly one owned publication/user match is required.
PROFILE="$(curl -sS --fail-with-body \
  "https://substack.com/api/v1/user/profile/self" \
  -H "Cookie: ${SUBSTACK_SESSION_COOKIE}" \
  -H "User-Agent: Mozilla/5.0" \
  -H "Accept: application/json")" || {
    echo "FATAL: Substack ownership probe failed" >&2
    exit 2
  }
BYLINE_ID="$(printf '%s' "$PROFILE" | jq -r --arg subdomain "$SUBDOMAIN" '
  [.publicationUsers[]
   | select((.publication.subdomain // "" | ascii_downcase) == ($subdomain | ascii_downcase))
   | .user_id]
  | if length == 1 and (.[0] | type) == "number" then .[0] else empty end
')"
[[ "$BYLINE_ID" =~ ^[0-9]+$ ]] || {
  echo "FATAL: Substack owned publication byline is missing or ambiguous" >&2
  exit 2
}
# Substack has no frontmatter concept and its draft renderer collapses GFM tables into one
# paragraph containing literal pipes.  Strip the duplicate metadata/title and convert every
# table to ordinary heading/list Markdown before draft_body leaves this process.
BODY_MD="$(python3 "$DIR/_shared/substack_compat.py" --strip-frontmatter-h1 "$MD_FILE")"

# Writer is a money loop: every Substack draft is subscriber-only and contains
# exactly one useful free preview before the paywall.  Keep this policy in one
# builder so create and repair paths cannot silently diverge.
PAYLOAD="$(printf '%s' "$BODY_MD" | python3 \
  "$DIR/substack-publish/substack_paid_payload.py" \
  --title "$TITLE" \
  --subtitle "$SUBTITLE" \
  --byline-id "$BYLINE_ID" \
  --after-chars "${SUBSTACK_PAYWALL_AFTER_CHARS:-1200}" \
  --minimum-free-chars "${SUBSTACK_MINIMUM_FREE_CHARS:-1000}")"

# POST to Substack draft creation endpoint
RESP="$(curl -sS \
  -X POST "https://${PUBLICATION}/api/v1/drafts" \
  -H "Content-Type: application/json" \
  -H "Cookie: ${SUBSTACK_SESSION_COOKIE}" \
  -d "$PAYLOAD" 2>&1)"

# Extract draft id
DRAFT_ID="$(printf '%s' "$RESP" | jq -r '.id // empty' 2>/dev/null)"
if [[ -z "$DRAFT_ID" ]]; then
  echo "FATAL: substack draft creation failed:" >&2
  printf '%s\n' "$RESP" >&2
  exit 3
fi

# DRAFT-ONLY, permanently (Dais 2026-07-12): this loop must never put an unreviewed
# article on the public internet. There used to be a POST to
# .../drafts/${DRAFT_ID}/publish right here that went live the instant the draft was
# created -- it is deliberately gone. Publishing is a human decision Dais makes from the
# Substack dashboard after reading the draft; there is no code path here that can do it
# for him.
SLUG="$(printf '%s' "$RESP" | jq -r '.slug // empty' 2>/dev/null)"
echo "DRAFT (unpublished) id=${DRAFT_ID} slug=${SLUG:-?} publication=${PUBLICATION} — review and publish by hand from the Substack dashboard"
