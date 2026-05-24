#!/usr/bin/env bash
# sync-memory.sh — sync Anicca's Claude Code memory between machines (Mac Mini ↔
# MacBook) via a private git repo. Ported from Sutando scripts/sync-memory.sh.
#
# Setup (one-time per machine):
#   1. Create a PRIVATE GitHub repo (e.g. Daisuke134/anicca-memory).
#   2. Add to $ANICCA_HOME/.env:  ANICCA_MEMORY_REPO=git@github.com:you/anicca-memory.git
#   3. bash sync-memory.sh   (first run clones to ~/.anicca/memory-sync/)
#   4. Cron it every 10-30 min on each machine.
#
# Conflict model: rsync-mtime-wins + content cmp guard (append-only files like
# MEMORY.md index and build_log.md are safest). Commits are signed with the
# machine hostname so writes are attributable. Each machine also backs up its
# own non-shared state to machine-<hostname>/ (one-way) for disaster recovery.
set -uo pipefail

ANICCA_HOME="${ANICCA_HOME:-$HOME/.openclaw}"
WS="${ANICCA_WORKSPACE:-$ANICCA_HOME/workspace}"
SYNC_DIR="${ANICCA_MEMORY_SYNC_DIR:-$HOME/.anicca/memory-sync}"
MEMORY_DIR="${ANICCA_MEMORY_DIR:-$HOME/.claude/projects/-Users-anicca-anicca-project/memory}"
LOG="/tmp/anicca-sync-memory.log"
LOCK_DIR="/tmp/anicca-sync-memory.lock.d"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG"; }

# Load .env (cron/launchd don't run shell startup)
if [ -f "$ANICCA_HOME/.env" ]; then set -a; . "$ANICCA_HOME/.env"; set +a; fi

if [ -z "${ANICCA_MEMORY_REPO:-}" ]; then
  echo "sync-memory: ANICCA_MEMORY_REPO not set in $ANICCA_HOME/.env, skipping."; exit 0
fi

# --- Lock via atomic mkdir (stale >10min removed) ---
if [ -d "$LOCK_DIR" ] && find "$LOCK_DIR" -maxdepth 0 -mmin +10 2>/dev/null | grep -q .; then
  log "stale lock removed"; rm -rf "$LOCK_DIR"
fi
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "sync-memory: another instance running, skipping."; exit 0
fi
trap 'rm -rf "$LOCK_DIR"' EXIT INT TERM

# --- First-run clone ---
if [ ! -d "$SYNC_DIR/.git" ]; then
  log "first-run clone from $ANICCA_MEMORY_REPO"
  mkdir -p "$(dirname "$SYNC_DIR")"
  git clone --depth=10 "$ANICCA_MEMORY_REPO" "$SYNC_DIR" 2>&1 | tee -a "$LOG" || { echo "clone failed"; exit 1; }
fi

cd "$SYNC_DIR" || { log "cannot cd $SYNC_DIR"; exit 1; }

# --- Assert on main (drifted branch silently stops propagation) ---
BR="$(git symbolic-ref --short HEAD 2>/dev/null || echo '')"
if [ "$BR" != "main" ] && [ "$BR" != "master" ]; then
  git checkout main 2>/dev/null || git checkout master 2>/dev/null || { echo "sync-memory: cannot reach main"; exit 1; }
fi

# --- Pull --rebase, abort on conflict (save file list) ---
PULL=$(git pull --rebase 2>&1)
if [ $? -ne 0 ] && echo "$PULL" | grep -qi conflict; then
  CD="$SYNC_DIR/.conflicts-$(hostname -s)-$(date +%Y%m%d-%H%M%S)"; mkdir -p "$CD"
  git diff --name-only --diff-filter=U > "$CD/conflicting-files.txt" 2>/dev/null
  git rebase --abort 2>/dev/null
  echo "sync-memory: rebase conflict — see $CD. Resolve manually."; exit 1
fi

mkdir -p memory

copy_if_newer() {  # mtime-wins + content guard (linter mtime-bump = no-op)
  local src="$1" dst="$2"
  [ -e "$dst" ] && cmp -s "$src" "$dst" && return 1
  if [ ! -e "$dst" ] || [ "$src" -nt "$dst" ]; then cp "$src" "$dst"; return 0; fi
  return 1
}

# --- Local memory → sync (push direction) ---
PUSHED=0
if [ -d "$MEMORY_DIR" ]; then
  for f in "$MEMORY_DIR"/*.md; do
    [ -f "$f" ] || continue
    copy_if_newer "$f" "memory/$(basename "$f")" && PUSHED=$((PUSHED+1))
  done
fi

# --- Machine-specific one-way backup (disaster recovery; not bidirectional) ---
HOST="$(hostname -s)"; MDIR="machine-$HOST"; mkdir -p "$MDIR"
for f in "$WS/ops/build_log.md" "$WS/PERSONAL_CLAUDE.md" "$WS/core-status.json" \
         "$ANICCA_HOME/identity/profile.json"; do
  [ -f "$f" ] && copy_if_newer "$f" "$MDIR/$(basename "$f")"
done

# --- Commit + push if changed (signed with hostname) ---
if git diff --quiet && git diff --cached --quiet && [ -z "$(git ls-files --others --exclude-standard)" ]; then
  log "nothing to push"; echo "No changes to sync."
else
  git add -A
  git commit -m "Sync $HOST $(date +%Y-%m-%dT%H:%M)" >/dev/null 2>&1
  git push >>"$LOG" 2>&1 && { log "pushed"; echo "Pushed from $HOST ($PUSHED memory)."; } || log "push failed"
fi

# --- Sync → local (pull direction, mtime-based) ---
if [ -d "$MEMORY_DIR" ]; then
  for f in memory/*.md; do
    [ -f "$f" ] || continue
    copy_if_newer "$f" "$MEMORY_DIR/$(basename "$f")"
  done
fi

MC=$(ls memory/*.md 2>/dev/null | wc -l | tr -d ' ')
log "sync complete: $MC memory files"
echo "Sync complete. Memory: $MC files."
