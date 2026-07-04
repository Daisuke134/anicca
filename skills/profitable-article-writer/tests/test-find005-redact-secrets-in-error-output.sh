#!/usr/bin/env bash
# VSDD oracle — Sprint-2 contract-review FIND-005 fix (security): lib/note_publish.sh's run_note_mode_a_publish
# re-emits each Python sub-step's raw combined stdout+stderr verbatim to its own stderr on failure. Every
# sub-step authenticates via NOTE_COOKIES_FILE against note_mcp (HTTP) or cloakbrowser (a real browser
# session) -- if either ever raises an exception whose message embeds request/response detail (e.g. an error
# body echoing a Set-Cookie header or a session/auth token), that content must never propagate unredacted
# into the wake's stderr/log stream, which CRIT-104 designates as a human/verifier-facing evidence surface.
#
# This test forces note_create_rich_draft's underlying call to fail with a SYNTHETIC secret-looking string
# in its output (a fake "python interpreter" == /bin/bash running a stub script, so this stays fully
# offline/hermetic -- no real note_mcp/cloakbrowser/network call) and proves the secret does NOT appear
# verbatim in run_note_mode_a_publish's final stderr output.
set -uo pipefail
SKILL="/Users/anicca/anicca-human-funded/skills/profitable-article-writer"
fails=0
ok(){ [ "$1" = 1 ] || { echo "  - FAIL $2"; fails=$((fails+1)); }; }

T="$(mktemp -d)"
COOKIES="$T/note-cookies.json"
printf '{"session_id": "abc123real"}' > "$COOKIES"
DRAFT="$T/draft.md"
printf '# t\n\nbody\n' > "$DRAFT"

SECRET="SUPERSECRET_TOKEN_9f8e7d6c5b4a"
FAKE_CREATE="$T/fake-create-rich-draft.sh"
cat > "$FAKE_CREATE" <<EOF
#!/usr/bin/env bash
echo "note_mcp.models.NoteAPIError: request failed, Set-Cookie: session_token=${SECRET}; Path=/; upstream said auth=${SECRET}" >&2
exit 1
EOF
chmod +x "$FAKE_CREATE"

# shellcheck disable=SC1091
source "$SKILL/lib/note_publish.sh"

OUT="$(NOTE_COOKIES_FILE="$COOKIES" NOTE_MCP_PY=/bin/bash NOTE_CREATE_RICH_DRAFT_PY="$FAKE_CREATE" \
  run_note_mode_a_publish "$DRAFT" "test title" "new" "500" "" 2>&1)"; rc=$?

ok "$([ $rc -ne 0 ] && echo 1 || echo 0)" "forced sub-step failure: run_note_mode_a_publish returns non-zero (rc=$rc)"
ok "$(! echo "$OUT" | grep -qF "$SECRET" && echo 1 || echo 0)" "the synthetic secret-looking string does NOT appear verbatim anywhere in the final error output"
ok "$(echo "$OUT" | grep -q 'REDACTED' && echo 1 || echo 0)" "the error output carries a [REDACTED] marker in place of the secret, proving redaction actually ran (not just silent dropping): $OUT"

# ---------- control: a failure message with NO secret-shaped content passes through unchanged (no
# over-redaction of ordinary diagnostic text) ----------
FAKE_CREATE2="$T/fake-create-rich-draft-plain.sh"
cat > "$FAKE_CREATE2" <<'EOF'
#!/usr/bin/env bash
echo "note_mcp.models.NoteAPIError: request failed, connection refused" >&2
exit 1
EOF
chmod +x "$FAKE_CREATE2"
OUT2="$(NOTE_COOKIES_FILE="$COOKIES" NOTE_MCP_PY=/bin/bash NOTE_CREATE_RICH_DRAFT_PY="$FAKE_CREATE2" \
  run_note_mode_a_publish "$DRAFT" "test title" "new" "500" "" 2>&1)"
ok "$(echo "$OUT2" | grep -q 'connection refused' && echo 1 || echo 0)" "control: ordinary diagnostic text with no secret-shaped content is NOT mangled by redaction: $OUT2"

[ $fails -eq 0 ] && { echo "PASS — FIND-005 fix: cookie/session/token-shaped content is redacted before re-emission, ordinary diagnostics are untouched"; exit 0; } || { echo "FAIL ($fails)"; exit 1; }
