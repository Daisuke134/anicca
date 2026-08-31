#!/bin/bash
# Snapshots the health of every anicca/life-manager loop so a cleanup step can be
# proven harmless. Usage:
#   loop-guard.sh save <tag>    # write a snapshot
#   loop-guard.sh diff <tag>    # compare current state against that snapshot
#
# Health = two things a deletion can break, both stable enough to compare:
#   1. which loops launchd still has loaded
#   2. plists pointing at a release directory that no longer exists
#
# Deliberately NOT compared: the set of currently-running loops, and the set of
# non-zero exits. StartInterval jobs start and finish on their own schedule, so
# those two churn every few seconds regardless of what was deleted — comparing
# them reports a failure for every snapshot taken more than a moment apart.
# `report` prints them for the human to read; only `diff` decides pass/fail.
set -uo pipefail
DIR="${LOOP_GUARD_DIR:-$HOME/.local/state/loop-guard}"
mkdir -p "$DIR"

LOOPS='ai\.anicca|com\.anicca|ai\.hermes'

snapshot() {
  echo "## loaded"
  launchctl list 2>/dev/null | grep -E "$LOOPS" | awk '{print $3}' | sort
  echo "## missing-release-refs"
  for p in "$HOME"/Library/LaunchAgents/*.plist; do
    for r in $(grep -oE "$HOME/loops/releases/[0-9A-Za-z-]+" "$p" 2>/dev/null | sort -u); do
      [ -d "$r" ] || echo "$(basename "$p" .plist) -> $(basename "$r")"
    done
  done | sort
}

case "${1:-}" in
  save)
    [ -n "${2:-}" ] || { echo "usage: loop-guard.sh save <tag>" >&2; exit 2; }
    snapshot > "$DIR/$2.txt"
    echo "saved $DIR/$2.txt ($(grep -c . "$DIR/$2.txt") lines)"
    ;;
  diff)
    [ -n "${2:-}" ] || { echo "usage: loop-guard.sh diff <tag>" >&2; exit 2; }
    [ -f "$DIR/$2.txt" ] || { echo "no snapshot $2" >&2; exit 2; }
    snapshot > "$DIR/$2.now.txt"
    diff -u "$DIR/$2.txt" "$DIR/$2.now.txt" > "$DIR/$2.diff" && {
      echo "UNCHANGED — no loop was harmed"; exit 0; }

    # `launchctl list` drops a job for the moment it is being spawned or reaped,
    # so a label missing from the second snapshot is not yet evidence of harm.
    # Ask launchd about each one directly; only a label it no longer knows is real.
    gone=""
    while read -r lbl; do
      # "label -> release" lines belong to the missing-release-refs section. One
      # leaving that section means a dangling reference got resolved, which is an
      # improvement; only bare labels can represent a loop that went away.
      case "$lbl" in *" -> "*) continue ;; esac
      case "$lbl" in ai.*|com.*) ;; *) continue ;; esac
      launchctl print "gui/$UID/$lbl" >/dev/null 2>&1 || gone="$gone $lbl"
    done < <(grep '^-' "$DIR/$2.diff" | grep -v '^---' | sed 's/^-//')

    newrefs=$(grep '^+' "$DIR/$2.diff" | grep -v '^+++' | sed 's/^+//' | grep ' -> ' || true)

    if [ -z "$gone" ] && [ -z "$newrefs" ]; then
      echo "UNCHANGED — no loop was harmed (transient launchctl churn only)"
      exit 0
    fi
    echo "CHANGED — review before continuing:"
    [ -n "$gone" ] && echo "  loops launchd no longer knows:$gone"
    [ -n "$newrefs" ] && echo "  new dangling release refs: $newrefs"
    exit 1
    ;;
  report)
    echo "## running now"
    launchctl list 2>/dev/null | grep -E "$LOOPS" | awk '$1 != "-"' | wc -l | tr -d ' '
    echo "## non-zero exits now"
    launchctl list 2>/dev/null | grep -E "$LOOPS" \
      | awk '$2 != 0 && $2 != "-" {print "  "$3" exit="$2}' | sort
    ;;
  *)
    echo "usage: loop-guard.sh {save|diff|report} <tag>" >&2; exit 2 ;;
esac
