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
step "LEARN" "STEP LEARN (cold-start bible = docs/loop-engineering/47-cold-start-self-improvement-bible.md; IMITATE-FIRST,守破離). Read the LAST line of $STATE/reflection.jsonl to know the current PHASE and what to adjust. In the cold-start phase (own posts still noise, no self-outlier yet) you learn from WINNERS, not your own metrics: (1) scout the TOP 3-5 AI/money/wealth accounts on Instagram; (2) find each account's OUTLIER reels = posts ~3-10x above THAT account's own average views; (3) study those outliers for the levers IN THIS PRIORITY ORDER: #1 the first-3-second HOOK (this decides ~40-50%% of virality — most important by far), #2 pattern-interrupt / visual jolt, #3 thumbnail+title packaging, #4 mid retention move (~7s), #5 script structure+length, #6 posting-time/hashtags (lowest); transcribe the hook + structure. (4) MERGE the generalized winning patterns into $STATE/playbook.json {phase, general:[...], components:{hook,pattern_interrupt,thumbnail,retention_move,script,posting_time,hashtags}} (a lever seen in 3+ winner outliers => tier:core). Copy with HIGH fidelity (Shu phase). Do not invent numbers; cite the actual outlier reels you saw."

# ── AFF-FIND (MON-5: find the affiliate/product to promote → offer.json → caption link) ──
# Only runs when there is no fresh offer yet (finding an offer is not needed every pass).
if [ ! -s "$STATE/offer.json" ]; then
  step "AFF-FIND" "STEP AFF-FIND (MON-5): pick the affiliate/product this @aiclipsvault (niche AI/money/wealth) will promote, so we can monetize. Prefer, in order: (1) our OWN products (100%% margin, no signup) — the Anicca app or life manager, if a public link exists; (2) an INSTANT-signup high-commission affiliate: Digistore24 (2-min signup, no interview) or ClickBank, browse the marketplace, pick ONE offer that (a) matches AI/money/wealth, (b) has high commission (recurring SaaS 20-40%%/mo or 50-75%% RevShare digital), (c) is globally available. Use the AI's own email keiodaisuke+aiclips1@gmail.com for any signup (auto-read OTP via 'gog gmail'). Get the real affiliate LINK. Write ~/clips/offer.json = {network, offer_name, affiliate_link, commission, niche, joined:<true|false>, note}. If signup is blocked (captcha/verification you cannot pass this pass), still record the chosen offer + what is needed with joined:false. Be honest; do not invent a link."
fi

# ── PRODUCE (deterministic: producer.sh makes a captioned 1080x1920 clip into the queue) ──
log "PRODUCE: producer.sh"
bash "$C/producer.sh" >/dev/null 2>&1 || log "producer rc=$?"

# ── POST (deterministic: run.sh posts the next queued clip via instagrapi + Telegram; cadence-gated) ──
log "POST: run.sh EARN_MODE=execute"
EARN_MODE=execute bash "$C/run.sh" >/dev/null 2>&1 || log "run.sh rc=$?"

# ── MEASURE (Evaluator: read real view counts of recent reels) ──
step "MEASURE" "STEP MEASURE: resolve @aiclipsvault's CloakBrowser CDP port from $HOME/.cloak/clip-accounts.json, open instagram.com/aiclipsvault/ in it, and read the view + like counts of the 3 most recent reels. Append ONE compact json line per reel to $STATE/clip-metrics.jsonl: {ts:<integer epoch>, reel_url, views:<int>, likes:<int>}. Ground ONLY on the real numbers shown on the page; if logged out, restore the session first; never guess."

# ── REFLECT (Self-Reflection: verbal reinforcement for the next pass) ──
step "REFLECT" "STEP REFLECT (Reflexion + PHASE gate, bible = 47-cold-start-self-improvement-bible.md): read tail -10 $STATE/clip-metrics.jsonl and the last line of $STATE/reflection.jsonl. Decide the PHASE: 'imitate' while own posts are still noise (no self-outlier yet) — keep copying winners, don't over-trust your own tiny numbers; flip to 'optimize' ONLY once one of YOUR OWN reels hits ~3x your own average views (a self-outlier), then that reel becomes the new imitation source. Append ONE compact json line to $STATE/reflection.jsonl: {ts:<int epoch>, phase:<imitate|optimize>, tried:<what changed this pass, lever-named e.g. hook/pattern-interrupt/thumbnail>, metrics_moved:<views delta vs prior, or flat>, self_outlier:<true if a own-post hit 3x own avg, else false>, next:<the single most promising lever next pass — in imitate phase this is 'copy a fresh winner outlier's HOOK', prioritise the hook>}. Be concrete and honest; if flat, pick a DIFFERENT lever than last time (hook first)."

log "pass complete"
