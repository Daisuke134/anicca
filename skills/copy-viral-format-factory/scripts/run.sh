#!/usr/bin/env bash
# Copy-Viral-Format Factory — orchestrator (Dais 8-step flow, 2026-05-06).
#
# Stages:
#   1 DISCOVER  — find a viral source (YouTube ytsearch + yt-dlp)
#   2 DOWNLOAD  — mp4, frames@1fps, whisper transcript, BGM extract
#   3 ANALYZE   — pick top, write AGENT_INSTRUCTIONS.md, agent writes clone_spec.json
#   --- HALT-B ---
#   4 PROOF     — generate 1 clone video (iterate up to 5x with Dais visual review)
#   --- HALT-D ---
#   5 SPAWN     — write skill skeleton with locked avatar/voice/BGM/format
#   6 BANK      — agent writes 30 bank entries
#   --- HALT-E ---
#   7 CRON      — 3 daily slots, disabled until Dais enables
#
# Modes:
#   ondemand            : Stages 1-3 then HALT-B
#   ondemand-proof      : Stage 4 (proof iter), HALT-D
#   ondemand-iterate    : same as ondemand-proof (agent updated clone_spec)
#   ondemand-finalize   : Stage 5+6 (HALT-E for bank), then 7
#   weekly              : full ondemand from queue
set -euo pipefail

MODE="${1:-weekly}"
NICHE_ARG="${2:-}"
LANG_ARG="${3:-en}"

SKILL_DIR="$HOME/.openclaw/skills/copy-viral-format-factory"
STATE_DIR="$SKILL_DIR/state"
ROOT="$HOME/anicca-monk-factory"
set -a; . "$ROOT/.env"; set +a

# ─── RUN_DIR resolution ─────────────────────────────────────────────
case "$MODE" in
  ondemand-finalize|ondemand-proof|ondemand-iterate)
    RUN_DIR=$(ls -td "$STATE_DIR"/run_* 2>/dev/null | head -1)
    [ -z "$RUN_DIR" ] && { echo "❌ no run_dir found for $MODE"; exit 31; }
    RUN_TAG=$(basename "$RUN_DIR" | sed 's/^run_//')
    echo "  ↻ $MODE: resuming $RUN_DIR"
    ;;
  *)
    RUN_TAG=$(date +%Y%m%d_%H%M%S)
    RUN_DIR="$STATE_DIR/run_$RUN_TAG"
    mkdir -p "$RUN_DIR"
    ;;
esac

echo "═══════════════════════════════════════════════"
echo "  Copy-Viral-Format Factory — $RUN_TAG"
echo "  mode=$MODE  niche='$NICHE_ARG'  lang=$LANG_ARG"
echo "═══════════════════════════════════════════════"

# ─── Niche resolution (only for fresh runs) ─────────────────────────
if [ "$MODE" = "weekly" ]; then
  QUEUE="$STATE_DIR/niches_queue.txt"
  if [ ! -f "$QUEUE" ] || [ ! -s "$QUEUE" ]; then
    cat > "$QUEUE" <<'EOF'
buddhism|en
monk|en
mindfulness|en
stoicism|en
philosophy|en
meditation|en
無常|jp
仏教|jp
瞑想|jp
EOF
  fi
  LINE=$(head -1 "$QUEUE")
  NICHE_KW=$(echo "$LINE" | cut -d'|' -f1)
  LANG_ARG=$(echo "$LINE" | cut -d'|' -f2)
  tail -n +2 "$QUEUE" > "$QUEUE.tmp" && echo "$LINE" >> "$QUEUE.tmp" && mv "$QUEUE.tmp" "$QUEUE"
else
  NICHE_KW="$NICHE_ARG"
fi
[ -z "$NICHE_KW" ] && NICHE_KW="ai viral"

# Persist niche/slug into run_dir on fresh runs (Stage 4+ reuses)
if [ ! -f "$RUN_DIR/.niche" ]; then
  echo "$NICHE_KW" > "$RUN_DIR/.niche"
  NICHE_SLUG=$(echo "$NICHE_KW" | python3 -c "import sys,re; print(re.sub(r'[^a-z0-9]+','-', sys.stdin.read().strip().lower()).strip('-'))")
  [ -z "$NICHE_SLUG" ] && NICHE_SLUG="niche-$RUN_TAG"
  echo "$NICHE_SLUG" > "$RUN_DIR/.slug"
  echo "$LANG_ARG" > "$RUN_DIR/.lang"
else
  NICHE_KW=$(cat "$RUN_DIR/.niche")
  NICHE_SLUG=$(cat "$RUN_DIR/.slug")
  LANG_ARG=$(cat "$RUN_DIR/.lang")
fi

echo "🎯 niche='$NICHE_KW' slug=$NICHE_SLUG lang=$LANG_ARG"

# ─── Stages 1-3 (only on fresh ondemand/weekly) ─────────────────────
if [ "$MODE" = "ondemand" ] || [ "$MODE" = "weekly" ]; then
  bash "$SKILL_DIR/scripts/{{profile.lateness.stakeholders.senderType}}s/01_discover.sh" "$NICHE_KW" "$LANG_ARG" "$RUN_DIR"
  bash "$SKILL_DIR/scripts/{{profile.lateness.stakeholders.senderType}}s/02_download.sh" "$RUN_DIR"
  bash "$SKILL_DIR/scripts/{{profile.lateness.stakeholders.senderType}}s/03_analyze.sh" "$RUN_DIR" "$NICHE_KW" "$LANG_ARG"

  # HALT-B: clone_spec.json must exist before continuing
  if [ ! -f "$RUN_DIR/clone_spec.json" ]; then
    echo ""
    echo "═══════════════════════════════════════════════"
    echo "  ⏸ HALT-B — agent must write clone_spec.json IN-CONTEXT"
    echo "  Read: $RUN_DIR/AGENT_INSTRUCTIONS.md"
    echo "  Write: $RUN_DIR/clone_spec.json"
    echo "  Then: bash run.sh ondemand-proof \"$NICHE_KW\" \"$LANG_ARG\""
    echo "═══════════════════════════════════════════════"
    exit 0
  fi
fi

# ─── Skip detection (clone_spec says source isn't viable) ───────────
if [ -f "$RUN_DIR/clone_spec.json" ]; then
  SKIP=$(python3 -c "import json; print('1' if json.load(open('$RUN_DIR/clone_spec.json')).get('skip') else '0')" 2>/dev/null || echo 0)
  if [ "$SKIP" = "1" ]; then
    REASON=$(python3 -c "import json; print(json.load(open('$RUN_DIR/clone_spec.json')).get('reason','no reason'))")
    echo ""
    echo "═══════════════════════════════════════════════"
    echo "  ⏭ AGENT REJECTED SOURCE — no factory spawned"
    echo "  reason: $REASON"
    echo "═══════════════════════════════════════════════"
    exit 0
  fi
fi

# ─── Stage 4 PROOF (ondemand-proof / ondemand-iterate) ──────────────
if [ "$MODE" = "ondemand-proof" ] || [ "$MODE" = "ondemand-iterate" ] || [ "$MODE" = "ondemand" ] || [ "$MODE" = "weekly" ]; then
  if [ ! -f "$RUN_DIR/clone_spec.json" ]; then
    echo "❌ Stage 4 PROOF needs clone_spec.json first — write it then run ondemand-proof"
    exit 32
  fi
  bash "$SKILL_DIR/scripts/{{profile.lateness.stakeholders.senderType}}s/04_proof.sh" "$RUN_DIR"

  # Don't auto-continue past PROOF — Dais must explicitly say 👍
  ITER=$(cat "$RUN_DIR/iteration.txt" 2>/dev/null || echo 1)
  echo ""
  echo "═══════════════════════════════════════════════"
  echo "  ⏸ HALT-D — Dais visual review (iter $ITER / 5)"
  echo "  Original: $RUN_DIR/source_*.mp4"
  echo "  Clone:    $RUN_DIR/clone_iter${ITER}.mp4"
  echo "  Desktop side-by-side has both."
  echo ""
  echo "  If clone needs changes:"
  echo "    Agent edits clone_spec.json then:"
  echo "      bash run.sh ondemand-iterate \"$NICHE_KW\" \"$LANG_ARG\""
  echo ""
  echo "  If Dais 👍:"
  echo "      bash run.sh ondemand-finalize \"$NICHE_KW\" \"$LANG_ARG\""
  echo "═══════════════════════════════════════════════"
  exit 0
fi

# ─── Stage 5 SPAWN (ondemand-finalize) ──────────────────────────────
if [ "$MODE" = "ondemand-finalize" ]; then
  bash "$SKILL_DIR/scripts/{{profile.lateness.stakeholders.senderType}}s/05_spawn.sh" "$RUN_DIR" "$NICHE_SLUG" "$LANG_ARG"

  NEW_SKILL_DIR="$HOME/.openclaw/skills/${NICHE_SLUG}-factory"

  # ─── Stage 6 BANK ── HALT-E if not yet written ────────────────────
  BANK_FILE="$RUN_DIR/new_bank.jsonl"
  if [ ! -s "$BANK_FILE" ]; then
    bash "$SKILL_DIR/scripts/{{profile.lateness.stakeholders.senderType}}s/06_bank.sh" "$RUN_DIR" "$NICHE_SLUG" "$LANG_ARG"
    if [ ! -s "$BANK_FILE" ]; then
      echo ""
      echo "═══════════════════════════════════════════════"
      echo "  ⏸ HALT-E — agent must write 30-entry bank"
      echo "  Read: $RUN_DIR/AGENT_INSTRUCTIONS_BANK.md"
      echo "  Write: $BANK_FILE  (30 lines, one JSON per line)"
      echo "  Then: bash run.sh ondemand-finalize \"$NICHE_KW\" \"$LANG_ARG\""
      echo "═══════════════════════════════════════════════"
      exit 0
    fi
  fi
  # Install bank into spawned skill
  cp "$BANK_FILE" "$NEW_SKILL_DIR/bank_${NICHE_SLUG}_${LANG_ARG}.jsonl"
  echo "  ✅ bank installed: $NEW_SKILL_DIR/bank_${NICHE_SLUG}_${LANG_ARG}.jsonl"

  # ─── Stage 7 CRON ─────────────────────────────────────────────────
  if [ -f "$NEW_SKILL_DIR/cron.template.txt" ]; then
    bash "$SKILL_DIR/scripts/{{profile.lateness.stakeholders.senderType}}s/07_schedule.sh" "$NICHE_SLUG" "$LANG_ARG" 2>/dev/null \
      || bash "$SKILL_DIR/scripts/{{profile.lateness.stakeholders.senderType}}s/06_schedule.sh" "$NICHE_SLUG" "$LANG_ARG" 2>/dev/null \
      || echo "  (cron add skipped — manual: openclaw cron add ...)"
  fi

  # Slack notify
  SUMMARY="🏭 New factory '${NICHE_SLUG}-factory' spawned, bank installed, 3 crons added (DISABLED)
- niche: $NICHE_KW ($LANG_ARG)
- skill: $NEW_SKILL_DIR
- bank:  $NEW_SKILL_DIR/bank_${NICHE_SLUG}_${LANG_ARG}.jsonl (30 entries)
- proof: $RUN_DIR/clone_iter*.mp4 (Dais 👍 to spawn)

Dais must:
1. openclaw cron enable <id>  (for the 3 daily slots)
2. account-creation-protocol  (3 fresh TT/IG/YT triplets)"

  echo ""
  echo "$SUMMARY"

  if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
    python3 - <<PY 2>/dev/null
import json, urllib.request, os
url = os.environ['SLACK_WEBHOOK_URL']
text = """${SUMMARY}"""
req = urllib.request.Request(url, data=json.dumps({'text': text}).encode(),
                              headers={'Content-Type': 'application/json'})
try: urllib.request.urlopen(req, timeout=10); print('  ✅ Slack notified')
except Exception as e: print(f'  ❌ Slack failed: {e}')
PY
  fi

  echo ""
  echo "═══════════════════════════════════════════════"
  echo "  ✅ copy-viral-format-factory done — $NICHE_SLUG"
  echo "═══════════════════════════════════════════════"
fi
