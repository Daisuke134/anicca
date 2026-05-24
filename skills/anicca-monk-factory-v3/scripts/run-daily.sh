#!/usr/bin/env bash
# ONE pipeline the cron runs end-to-end. Pure scripts → the cron agent just calls `bash run-daily.sh`
# (no fragile agent-drives-camofox steps, no per-step LLM, so it can't stall mid-way).
# login → rotate next script → render-submit (camofox) → render-download → burn captions →
# gen unique caption → post TikTok ({{profile.lateness.stakeholders.channel}}) → post IG (Postiz) → mark used → Slack #metrics report.
set -uo pipefail
SKILL="$HOME/.openclaw/skills/anicca-monk-factory-v3"; S="$SKILL/scripts"
OUT="$HOME/anicca-monk-factory/renders_v3"; mkdir -p "$OUT"
export GOG_KEYRING_PASSWORD="${GOG_KEYRING_PASSWORD:-<password>}"
LOG="$OUT/run-$(date +%Y%m%d-%H%M%S).log"; exec > >(tee -a "$LOG") 2>&1
ID=""
fail(){ bash "$S/report-slack.sh" "❌ Monk Factory FAILED at [$1] ${ID:+($ID)}: $2 (log: $LOG)"; exit 1; }

echo "=== [0] ensure HeyGen login ==="
bash "$S/ensure-heygen-login.sh" || fail login "ensure-heygen-login.sh failed"

echo "=== [1] pick next script (rotation) ==="
J=$(bash "$S/pick-next-script.sh" next) || fail pick "pick-next failed"
ID=$(printf '%s' "$J" | jq -r .id); SCRIPT=$(printf '%s' "$J" | jq -r .script)
[ -n "$ID" ] && [ "$ID" != "null" ] || fail pick "no script id"
echo "script: $ID"

echo "=== [2] render-submit (camofox HeyGen) ==="
PURL=$(bash "$S/render-submit.sh" "$SCRIPT" | grep '^PROJECT_URL=' | cut -d= -f2-)
[ -n "$PURL" ] || fail render-submit "no PROJECT_URL for $ID"
echo "project: $PURL"

echo "=== [3] render-download (poll /evaluate until mp4) ==="
bash "$S/render-download.sh" "$PURL" "$OUT/$ID.mp4" || fail render-download "$PURL"

echo "=== [4] burn captions ==="
bash "$S/burn-captions.sh" "$OUT/$ID.mp4" "$OUT/${ID}_captioned.mp4" || fail burn "burn-captions failed"

echo "=== [5] gen unique caption ==="
bash "$S/gen-caption.sh" "$ID" "$OUT/${ID}_tiktok.txt" "$OUT/${ID}_ig.txt" || fail caption "gen-caption failed"

echo "=== [6] post TikTok ({{profile.lateness.stakeholders.channel}}) ==="
TTOUT=$(bash "$S/post-tiktok.sh" "$OUT/${ID}_captioned.mp4" "$OUT/${ID}_tiktok.txt" 2>&1 || true)
echo "$TTOUT" | tail -6
TTURL=$(printf '%s' "$TTOUT" | grep -oE 'TIKTOK_URL=\S+' | tail -1 | cut -d= -f2-)

echo "=== [7] post IG (Postiz) ==="
IGOUT=$(bash "$S/post-ig-postiz.sh" "$OUT/${ID}_captioned.mp4" "$OUT/${ID}_ig.txt" 2>&1 || true)
echo "$IGOUT" | tail -4
IGURL=$(printf '%s' "$IGOUT" | grep -oE 'https://www\.instagram\.com/reel/[A-Za-z0-9_-]+' | tail -1)

echo "=== [8] mark used + report ==="
if [ -n "$TTURL" ] || [ -n "$IGURL" ]; then bash "$S/pick-next-script.sh" mark "$ID"; fi
bash "$S/report-slack.sh" "🧎 Monk Factory $ID DONE — TikTok=${TTURL:-FAILED} | IG=${IGURL:-FAILED}"
echo "RUN_DONE id=$ID tiktok=${TTURL:-FAILED} ig=${IGURL:-FAILED}"
