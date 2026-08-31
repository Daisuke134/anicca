#!/bin/bash
# Keeps free space above threshold so nothing (esp. claude remote-control) dies on ENOSPC.
# Only deletes regenerable caches. Never touches transcripts, memory, state, repos.
MIN_GB=25
free_gb() { df -g /System/Volumes/Data | awk 'NR==2{print $4}'; }
log() { echo "$(date '+%F %T') $*" >> ~/Library/Logs/disk-watchdog.log; }

[ "$(free_gb)" -ge "$MIN_GB" ] && exit 0
log "free=$(free_gb)G below ${MIN_GB}G — pruning"

# Releases outgrow everything else here: one 1.2GB tree every 10-20 minutes.
# Their own GC refuses to touch a release that a loaded agent references or a
# process holds open, so asking it for tighter retention cannot strand a loop.
newest=$(ls -t ~/loops/releases 2>/dev/null | head -1)
if [ -n "$newest" ] && [ -f "$HOME/loops/releases/$newest/runtime/loop/central_cleanup.py" ]; then
  out=$(cd "$HOME/loops/releases/$newest" && LIFE_MANAGER_RELEASE_KEEP=2 \
          python3 runtime/loop/central_cleanup.py --release-gc-only 2>/dev/null)
  log "release gc: $(printf '%s' "$out" | head -c 200)"
fi
# The GC renames a tree to <release>.gc-trash.<pid> before unlinking it; a run
# that dies in between leaves the whole 1.2GB behind under that name.
rm -rf "$HOME"/loops/releases/*.gc-trash.* 2>/dev/null

rm -rf ~/.npm/_cacache ~/Library/Caches/pip ~/.cache/uv ~/Library/Caches/Homebrew 2>/dev/null
rm -rf ~/Library/Developer/Xcode/DerivedData/* 2>/dev/null
rm -rf ~/.cache/anicca-clones/* ~/.cache/anicca-worktrees/* /tmp/anicca-* 2>/dev/null
find /private/tmp/claude-501 -maxdepth 2 -type d -mtime +2 -exec rm -rf {} + 2>/dev/null
find ~/Library/Logs -name '*.log' -size +200M -exec truncate -s 0 {} \; 2>/dev/null

log "after prune free=$(free_gb)G"
[ "$(free_gb)" -lt 3 ] && log "STILL CRITICAL — manual action needed"
exit 0
