#!/usr/bin/env bash
# VSDD oracle — PROP-12 (REQ-11): IF a platform account is absent THEN the skill SHALL self-create it
# zero-human where proven, OR flag the rail unavailable — it SHALL NEVER fail loudly or spew errors. No
# shared/Dais account literal anywhere in the self-create path.
set -uo pipefail
SKILL="/Users/anicca/anicca-human-funded/skills/profitable-article-writer"
fails=0
ok(){ [ "$1" = 1 ] || { echo "  - FAIL $2"; fails=$((fails+1)); }; }

# ---------- STATIC: no hardcoded shared/Dais account literal in the self-create path ----------
SHARED_LITERALS='keiodaisuke@gmail\.com|daisukenarita53@gmail\.com|Daisuke Narita|Daisuke134'
hits="$(grep -rEn "$SHARED_LITERALS" "$SKILL/identity" 2>/dev/null || true)"
ok "$([ -z "$hits" ] && echo 1 || echo 0)" "no hardcoded shared/Dais account literal in identity/ (found: ${hits:-none})"

# ---------- DYNAMIC 1: account absent, no self-create requested -> flags "unavailable", rc=0, no error-spew ----------
T="$(mktemp -d)"; mkdir -p "$T/state"
OUT="$(ARTICLE_DIR="$T" bash "$SKILL/identity/accounts.sh" 2>&1)"; rc=$?
ok "$([ $rc -eq 0 ] && echo 1 || echo 0)" "no creds at all -> accounts.sh completes cleanly, rc=0 (rc=$rc): $OUT"
reg="$T/state/accounts.json"
ok "$([ -f "$reg" ] && echo 1 || echo 0)" "a registry was still written with everything absent"
if [ -f "$reg" ]; then
  ok "$(grep -q '"note": *"unavailable"' "$reg" && echo 1 || echo 0)" "note slot flagged unavailable (no cred, no self-create) — never a loud failure"
fi
ok "$(! echo "$OUT" | grep -qiE 'error|traceback|exception' && echo 1 || echo 0)" "no error-log/stack-trace/exception text in accounts.sh output"

# ---------- DYNAMIC 2: account absent + <RAIL>_SELF_CREATE=1 on a NON-proven rail -> still degrades to
# ---------- "unavailable", never aborts the wake (rc=0, no crash) ----------
T2="$(mktemp -d)"; mkdir -p "$T2/state"
OUT2="$(ARTICLE_DIR="$T2" NOTE_SELF_CREATE=1 bash "$SKILL/identity/accounts.sh" 2>&1)"; rc2=$?
ok "$([ $rc2 -eq 0 ] && echo 1 || echo 0)" "NOTE_SELF_CREATE=1 on an unproven rail -> still completes cleanly, rc=0 (rc=$rc2): $OUT2"
reg2="$T2/state/accounts.json"
ok "$([ -f "$reg2" ] && echo 1 || echo 0)" "a registry was written for the self-create attempt"
if [ -f "$reg2" ]; then
  ok "$(grep -q '"note": *"unavailable"' "$reg2" && echo 1 || echo 0)" "note self-create on an unproven rail degrades to unavailable (self-create-or-flag, REQ-11)"
fi
ok "$(! echo "$OUT2" | grep -qiE 'error|traceback|exception' && echo 1 || echo 0)" "self-create attempt on unproven rail: no error-log/stack-trace/exception text"

# ---------- DYNAMIC 3 (contract-review FIND-004): account absent + <RAIL>_SELF_CREATE=1 on a rail injected
# ---------- into PROVEN_SELF_CREATE_RAILS -> the proven-rail branch is REACHABLE and resolves to a status
# ---------- DISTINCT from "unavailable" (the case construct is no longer dead code) ----------
T3="$(mktemp -d)"; mkdir -p "$T3/state"
OUT3="$(ARTICLE_DIR="$T3" NOTE_SELF_CREATE=1 PROVEN_SELF_CREATE_RAILS="note" bash "$SKILL/identity/accounts.sh" 2>&1)"; rc3=$?
ok "$([ $rc3 -eq 0 ] && echo 1 || echo 0)" "NOTE_SELF_CREATE=1 with 'note' injected into PROVEN_SELF_CREATE_RAILS -> still completes cleanly, rc=0 (rc=$rc3): $OUT3"
reg3="$T3/state/accounts.json"
ok "$([ -f "$reg3" ] && echo 1 || echo 0)" "a registry was written for the proven-rail self-create attempt"
if [ -f "$reg3" ]; then
  ok "$(grep -q '"note": *"self-create-eligible"' "$reg3" && echo 1 || echo 0)" "proven-rail self-create resolves to a status DISTINCT from 'unavailable' (self-create-eligible) — the case branch is live, not dead"
fi
ok "$(! echo "$OUT3" | grep -qiE 'error|traceback|exception' && echo 1 || echo 0)" "proven-rail self-create attempt: no error-log/stack-trace/exception text"
# same rail, no self-create requested at all -> still degrades to unavailable (the proven-rails list alone
# does not activate a rail; the flag AND the proven-list membership are both required)
T4="$(mktemp -d)"; mkdir -p "$T4/state"
OUT4="$(ARTICLE_DIR="$T4" PROVEN_SELF_CREATE_RAILS="note" bash "$SKILL/identity/accounts.sh" 2>&1)"; rc4=$?
ok "$([ $rc4 -eq 0 ] && echo 1 || echo 0)" "'note' in PROVEN_SELF_CREATE_RAILS but NO self-create flag set -> still completes cleanly, rc=0 (rc=$rc4)"
reg4="$T4/state/accounts.json"
if [ -f "$reg4" ]; then
  ok "$(grep -q '"note": *"unavailable"' "$reg4" && echo 1 || echo 0)" "proven rail with no self-create flag requested still degrades to unavailable (default path unaffected by the seam)"
fi

[ $fails -eq 0 ] && { echo "PASS — PROP-12 account-absent -> self-create-or-flag, never a loud failure"; exit 0; } || { echo "FAIL ($fails)"; exit 1; }
