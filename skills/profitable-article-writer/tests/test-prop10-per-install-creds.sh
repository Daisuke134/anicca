#!/usr/bin/env bash
# VSDD oracle — PROP-10 (REQ-15): every credential is read from the install's own env; a registry slot
# gates rail activation; no Dais/shared account literal is referenced anywhere in the skill tree.
set -uo pipefail
SKILL="/Users/anicca/anicca-human-funded/skills/profitable-article-writer"
fails=0
ok(){ [ "$1" = 1 ] || { echo "  - FAIL $2"; fails=$((fails+1)); }; }

# ---------- STATIC: no hardcoded shared/Dais account literal anywhere in the skill tree ----------
SHARED_LITERALS='keiodaisuke@gmail\.com|daisukenarita53@gmail\.com|Daisuke Narita|Daisuke134'
hits="$(grep -rEn "$SHARED_LITERALS" "$SKILL" 2>/dev/null | grep -v '/tests/' || true)"
ok "$([ -z "$hits" ] && echo 1 || echo 0)" "no hardcoded shared/Dais account literal in skill tree (found: ${hits:-none})"

# ---------- DYNAMIC: creds come ONLY from install env; registry gates activation per-slot ----------
T="$(mktemp -d)"; mkdir -p "$T/state"
OUT="$(ARTICLE_DIR="$T" NOTE_SESSION_COOKIE="fake-install-cookie-value" bash "$SKILL/identity/accounts.sh" 2>&1)"; rc=$?
ok "$([ $rc -eq 0 ] && echo 1 || echo 0)" "accounts.sh runs with only NOTE_SESSION_COOKIE set, rc=0 (rc=$rc): $OUT"
reg="$T/state/accounts.json"
ok "$([ -f "$reg" ] && echo 1 || echo 0)" "accounts.sh wrote a per-install registry ($reg)"
if [ -f "$reg" ]; then
  ok "$(grep -q '"note": *"active"' "$reg" && echo 1 || echo 0)" "note slot is active (its env cred was present)"
  ok "$(grep -q '"substack": *"unavailable"' "$reg" && echo 1 || echo 0)" "substack slot is unavailable (no env cred), not an error"
fi

[ $fails -eq 0 ] && { echo "PASS — PROP-10 per-install credential gating"; exit 0; } || { echo "FAIL ($fails)"; exit 1; }
