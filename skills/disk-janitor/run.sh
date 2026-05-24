#!/usr/bin/env bash
# disk-janitor — every 3 hours, sweep known-disposable disk hogs.
set -uo pipefail

before_kb=$(df -k / | awk 'END{print $4}')

# Always-safe deletes
rm -rf "$HOME/anicca-project/sao-content-factory/remotion/out" 2>/dev/null
rm -rf "$HOME/anicca-project/sao-content-factory/remotion/.cache" 2>/dev/null
rm -f /tmp/*.md /tmp/x_thread_*.json /tmp/sao_draft_*.json /tmp/jobs.json.* 2>/dev/null

# Per-version output dirs older than 2 days
find "$HOME/anicca-project/sao-content-factory/assets" -type d -name output -mtime +2 -exec rm -rf {} + 2>/dev/null
find "$HOME/.openclaw/skills/sao-content-factory/output" -mindepth 3 -type d -mtime +2 -exec rm -rf {} + 2>/dev/null

# Big YouTube DLs older than 2 days (re-fetch on demand)
find "$HOME/anicca-project/sao-content-factory/assets" -type f -name 'yt_full.mp4' -mtime +2 -delete 2>/dev/null

# Suno raw stems older than 2 days (the trimmed bgm.mp3 stays)
find "$HOME/anicca-project/sao-content-factory/assets" -type f -name 'bgm_*_full.mp3' -mtime +2 -delete 2>/dev/null

# Claude harness transcripts older than 3h (115 crons spawn isolated sessions
# constantly; >1d was far too lax — /private/tmp hit 4.1GB on 2026-05-21).
# 3h window never touches an active interactive session's in-flight files.
find /private/tmp/claude-501 -mindepth 2 -type f -mmin +180 -delete 2>/dev/null
find /private/tmp/claude-501 -mindepth 2 -type d -empty -delete 2>/dev/null

# Chrome/Chromium code_sign_clone orphans in per-user /var/folders.
# agent-{{profile.lateness.stakeholders.channel}} / playwright spawn a full Chrome.app clone (~450MB framework
# each) per launch and never reap them — historically the #1 disk eater
# (seen at 41GB / 300+ clones). Unix-safe to delete even while Chrome runs
# (live procs keep their inodes; new launches recreate the clone). Only
# touch clone subdirs idle >60min so an in-flight launch is never cut.
for vf in /private/var/folders/*/*/X /private/var/folders/*/*/C; do
  [ -d "$vf" ] || continue
  find "$vf" -maxdepth 1 -type d -name '*code_sign_clone*' 2>/dev/null | while read -r cl; do
    find "$cl" -mindepth 1 -maxdepth 1 -mmin +60 -exec rm -rf {} + 2>/dev/null
  done
done

# OpenClaw workspace generated artifacts older than 2 days
find "$HOME/.openclaw/workspace" -maxdepth 1 -type d \( \
  -name 'reelclaw*' -o -name 'slideshow-*' -o -name 'TODAY-*' -o -name '*-run' -o -name '*-work' -o -name '*-test*' \
\) -mtime +2 -exec rm -rf {} + 2>/dev/null

# TikTok marketing dated outputs older than 2 days (keep shared assets/work/posts roots)
find "$HOME/.openclaw/workspace/tiktok-marketing" -maxdepth 1 -type d \( \
  -name '*2026*' -o -name 'morning-*' -o -name 'afternoon-*' -o -name 'evening-*' -o -name 'reelclaw-*' -o -name 'work-*' -o -name 'slideshow-*' -o -name 'test-*' -o -name 'demo-reel-*' \
\) -mtime +2 -exec rm -rf {} + 2>/dev/null

# Archived post bundles older than 3 days
find "$HOME/.openclaw/workspace/tiktok-marketing/posts" -mindepth 1 -maxdepth 1 -type d -mtime +3 -exec rm -rf {} + 2>/dev/null

# Honne AI generated outputs older than 3 days
find "$HOME/.openclaw/workspace/honne-ai" -mindepth 1 -maxdepth 1 -type d \( \
  -name 'runs' -o -name 'work' -o -name 'exports' -o -name 'build' -o -name 'builds' -o -name 'out' -o -name 'output' -o -name 'render' -o -name 'renders' -o -name 'reelclaw-runs' -o -name 'reelclaw-work' -o -name '_reelclaw_tmp' -o -name 'tmp' -o -name 'sample-renders' -o -name 'finals' -o -name '*run*' -o -name '*work*' -o -name '*render*' -o -name '*export*' -o -name '*build*' \
\) -mtime +3 -exec rm -rf {} + 2>/dev/null

# Mau TikTok rendered outputs older than 7 days
find "$HOME/.openclaw/workspace/mau-tiktok/output" -type f -mtime +7 -delete 2>/dev/null

# OpenClaw sessions.json index files: rotate when >50MB.
# Root cause of 2026-05-20 17h silence: 177MB sessions.json → V8 StructuredClone
# exhausted Node 4GB heap on gateway restart → crash loop. Stat-only check; never
# reads the JSON content (could OOM us). Live file reset to '[]' preserving mode.
for SJ in "$HOME"/.openclaw/agents/*/sessions/sessions.json; do
  [ -f "$SJ" ] || continue
  SZ=$(stat -f%z "$SJ" 2>/dev/null || stat -c%s "$SJ" 2>/dev/null || echo 0)
  if [ "$SZ" -gt $((50 * 1024 * 1024)) ]; then
    gzip -c "$SJ" > "${SJ}.archive-$(date -u +%Y%m%dT%H%M%SZ).gz" && printf '[]' > "$SJ" && chmod 600 "$SJ" 2>/dev/null
  fi
done

# === macOS dev-tool caches (regenerable) — the REAL hogs that filled / on
# 2026-05-21 (Simulator 5.7G, npm 3.6G, swiftpm 1.5G, DerivedData 2.4G, bun
# 1.1G, Homebrew 695M). All rebuild on demand.
# NEVER touch: ~/Library/Caches/camoufox (Camofox = main {{profile.lateness.stakeholders.channel}} stash),
# ~/.bun/bin (nano-banana + CLIs live here), node_modules, .git, state, .env.
rm -rf "$HOME/Library/Developer/Xcode/DerivedData"/* 2>/dev/null
rm -rf "$HOME/Library/Developer/CoreSimulator/Caches"/* 2>/dev/null
xcrun simctl delete unavailable 2>/dev/null
rm -rf "$HOME/Library/Caches/org.swift.swiftpm"/* 2>/dev/null
rm -rf "$HOME/Library/Caches/Homebrew"/* 2>/dev/null
rm -rf "$HOME/Library/Caches/colima"/* "$HOME/Library/Caches/Google"/* 2>/dev/null
rm -rf "$HOME/Library/Caches/node-gyp"/* "$HOME/Library/Caches/pip"/* 2>/dev/null
rm -rf "$HOME/.npm/_cacache" 2>/dev/null
rm -rf "$HOME/.bun/install/cache" 2>/dev/null

after_kb=$(df -k / | awk 'END{print $4}')
free_avail_gb=$(awk -v k="$after_kb" 'BEGIN{printf "%.2f", k/1024/1024}')
freed_mb=$(( (after_kb - before_kb) / 1024 ))

# Tiered safety net. 200MB was uselessly low — the box breaks long before that
# (cron .output writes fail at ENOSPC). Alert EARLY so it self-heals or a human
# acts before reaching zero.
hard_fail_kb=$((2 * 1024 * 1024))   # <2GB = emergency
warn_kb=$((5 * 1024 * 1024))        # <5GB = warn but ok
if [ "$after_kb" -lt "$hard_fail_kb" ]; then
  echo "❌ disk-janitor: only ${free_avail_gb}GB free after sweep (freed ${freed_mb}MB) — EMERGENCY, manual cleanup needed"
  exit 4
fi
if [ "$after_kb" -lt "$warn_kb" ]; then
  echo "⚠️ disk-janitor: freed ${freed_mb}MB · only ${free_avail_gb}GB free on / — getting low, investigate hogs"
  exit 0
fi

echo "🧹 disk-janitor: freed ${freed_mb}MB · ${free_avail_gb}GB free on /"
