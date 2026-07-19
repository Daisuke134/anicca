#!/bin/bash
# The tick must run an instagrapi --keepalive probe for session_owner=instagrapi accounts
# (they are excluded from browser warming, so this is their ONLY between-post traffic),
# and that probe must live inside the clip_pass.sh concurrency guard.
#
# T resolves via `git rev-parse --show-toplevel` (worktree-relative, matching this test dir's
# own sibling tests' DIR convention) rather than a hardcoded $HOME/anicca — a hardcoded absolute
# path would test the PRIMARY checkout's copy of the script, not the one this branch/worktree
# actually edits, giving a false PASS/FAIL unrelated to this change.
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && git rev-parse --show-toplevel)"
T="$ROOT/skills/browser/scripts/session_vault_tick.sh"
fail(){ echo "FAIL: $*"; exit 1; }
grep -q 'session_owner // ""' "$T" || fail "roster filter missing"
grep -q -- '--keepalive' "$T" || fail "no instagrapi --keepalive probe wired"
grep -q 'poster.py' "$T" || fail "keepalive must go through poster.py (single owner of session logic)"
# the keepalive block must appear AFTER the clip_pass.sh guard line (same guard applies)
guard_line=$(grep -n 'pgrep -f "clip_pass' "$T" | head -1 | cut -d: -f1)
ka_line=$(grep -n -- '--keepalive' "$T" | head -1 | cut -d: -f1)
[ -n "$guard_line" ] && [ -n "$ka_line" ] && [ "$ka_line" -gt "$guard_line" ] || fail "keepalive not under clip_pass guard"
echo "PASS"
