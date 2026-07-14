#!/usr/bin/env bash
# clip_pass.sh — ONE clip pass as a Reflexion prompt-chain (copied from gig_pass.sh; NeurIPS 2023
# Reflexion: Actor = producer.sh + run.sh, Evaluator = clip-metrics, Self-Reflection = reflection.jsonl).
# Each LLM step is a SEPARATE bounded claude sub-call with a short focused prompt + --no-session-persistence
# (never bricks disk). PRODUCE + POST are deterministic (producer.sh makes a 1080x1920 clip; run.sh posts
# via instagrapi + reports to Telegram, respecting the cadence gate). State passes between steps through
# ~/clips/{reflection.jsonl,playbook.json,clip-metrics.jsonl}.
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
C="$HOME/anicca/skills/earn/clip"
CLAUDE="$(command -v claude || echo "$HOME/.local/bin/claude")"
STATE="$HOME/clips"
mkdir -p "$STATE"
log(){ echo "$(date '+%F %T') clip_pass: $*" >&2; }

# focused sub-call: run ONE step as its own bounded agent. --no-session-persistence + SKIP_PROMPT_HISTORY
# = write no transcript (the disk-brick source). env -u ANTHROPIC_API_KEY = subscription login.
step(){ # $1=label  $2=prompt
  log "STEP $1 start"
  CLAUDE_CODE_SKIP_PROMPT_HISTORY=1 env -u ANTHROPIC_API_KEY timeout 900 "$CLAUDE" --model sonnet --dangerously-skip-permissions --no-session-persistence --add-dir "$HOME" \
    -p "You are the Anicca clip earn-core (IG @aiclipsvault, niche = AI / money / wealth). set -a; . ~/.openclaw/.env 2>/dev/null; set +a. Do EXACTLY this ONE step, fully, then stop. $2" >/dev/null 2>&1
  log "STEP $1 done (rc=$?)"
}

# ── deterministic prelude: single-instance lock (mkdir = atomic on macOS) + disk guard ──
LOCKD=/tmp/anicca-clip-pass.lock.d
[ -d "$LOCKD" ] && [ $(( $(date +%s) - $(stat -f %m "$LOCKD" 2>/dev/null||echo 0) )) -gt 1800 ] && rmdir "$LOCKD" 2>/dev/null
mkdir "$LOCKD" 2>/dev/null || { log "another clip pass holds the lock — exit"; exit 0; }
trap 'rmdir "$LOCKD" 2>/dev/null' EXIT
FREE=$(df -g / | tail -1 | awk '{print $4}')
[ "${FREE:-99}" -lt 5 ] && { log "disk <5GB free — abort to protect the session"; exit 0; }

# ── LEARN (Reflexion: read prior reflection + scout winners → playbook) ──
step "LEARN" "STEP LEARN: read the LAST line of $STATE/reflection.jsonl (the previous pass's reflection — what was tried and what to adjust) and let it steer this pass. Then crwl ONE best-practice source on viral short-form (hooks / thumbnails / posting time / hashtags) AND scout 2-3 TOP-performing AI/money/wealth clip accounts on Instagram (view their recent reels), extract the generalized winning patterns, and MERGE them into $STATE/playbook.json as one compact json object {general:[...], components:{hook,thumbnail,caption,posting_time,hashtags}} (a pattern seen in 3+ winners => mark tier:core). Do not invent numbers; cite what you actually saw."

# ── PRODUCE (deterministic: producer.sh makes a captioned 1080x1920 clip into the queue) ──
log "PRODUCE: producer.sh"
bash "$C/producer.sh" >/dev/null 2>&1 || log "producer rc=$?"

# ── POST (deterministic: run.sh posts the next queued clip via instagrapi + Telegram; cadence-gated) ──
log "POST: run.sh EARN_MODE=execute"
EARN_MODE=execute bash "$C/run.sh" >/dev/null 2>&1 || log "run.sh rc=$?"

# ── MEASURE (Evaluator: read real view counts of recent reels) ──
step "MEASURE" "STEP MEASURE: resolve @aiclipsvault's CloakBrowser CDP port from $HOME/.cloak/clip-accounts.json, open instagram.com/aiclipsvault/ in it, and read the view + like counts of the 3 most recent reels. Append ONE compact json line per reel to $STATE/clip-metrics.jsonl: {ts:<integer epoch>, reel_url, views:<int>, likes:<int>}. Ground ONLY on the real numbers shown on the page; if logged out, restore the session first; never guess."

# ── REFLECT (Self-Reflection: verbal reinforcement for the next pass) ──
step "REFLECT" "STEP REFLECT (Reflexion verbal reinforcement): read tail -5 $STATE/clip-metrics.jsonl (recent reels' views) and the last line of $STATE/reflection.jsonl. Append ONE compact json line to $STATE/reflection.jsonl: {ts:<integer epoch>, tried:<what you changed this pass: hook / thumbnail / niche / posting-time / caption>, metrics_moved:<views delta vs the prior reels, or 'flat'>, next:<the single most promising lever to try next pass>}. Be concrete and honest; if views are flat, pick a DIFFERENT lever than last time."

log "pass complete"
