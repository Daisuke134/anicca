#!/usr/bin/env bash
# prepare.sh — for a given funder spec, fetch live data, draft K-Dense fields,
# emit a flat per-field payload at data/drafts/<funder>/<ts>.payload.json.
#
# Inputs:  $1 = path to funders/<id>.json
# Outputs: data/drafts/<funder>/<ts>.payload.json   — fully-resolved field map
#          data/drafts/<funder>/<ts>.kdense.md      — list of K-Dense draft requests
# Env: DRY_RUN, SKILL_DIR

set -uo pipefail

SPEC="$1"
SKILL_DIR="${SKILL_DIR:-$HOME/.openclaw/skills/apply-to-funder}"
DRY_RUN="${DRY_RUN:-false}"
FUNDER_ID=$(jq -r '.id' "$SPEC")
TS=$(date +%Y%m%d-%H%M)
DRAFT_DIR="$SKILL_DIR/data/drafts/$FUNDER_ID"
mkdir -p "$DRAFT_DIR"

PAYLOAD_FILE="$DRAFT_DIR/$TS.payload.json"
KDENSE_FILE="$DRAFT_DIR/$TS.kdense.md"

echo "▶ prepare  funder=$FUNDER_ID  draft_dir=$DRAFT_DIR"

# --- 1. Live dashboard snapshot (if funder uses it) ---
DASH_URL=$(jq -r '.live_sources.dashboard_url // ""' "$SPEC")
DASH="{}"
if [ -n "$DASH_URL" ]; then
  if [ "$DRY_RUN" = "true" ]; then
    DASH='{"mrr":{"total_usd":67.99},"followers":{"total":1234},"views":{"weekly_total":5000},"spend":{"total_usd":250},"profit_usd":-180}'
    echo "  [DRY_RUN] using stub dashboard"
  else
    DASH=$(curl -sS --max-time 10 "$DASH_URL" 2>/dev/null || echo "{}")
  fi
fi
MRR=$(echo "$DASH" | jq -r '.mrr.total_usd // 0')
FOLLOWERS=$(echo "$DASH" | jq -r '.followers.total // 0')
WEEKLY_VIEWS=$(echo "$DASH" | jq -r '.views.weekly_total // 0')
SPEND=$(echo "$DASH" | jq -r '.spend.total_usd // 0')
PROFIT=$(echo "$DASH" | jq -r '.profit_usd // 0')
echo "  snapshot: mrr=\$$MRR followers=$FOLLOWERS"

# --- 2. Pre-built live pitch fragments (the things apply-to-yc.apply.sh builds inline) ---
# Funders can reference these via value_source=live:pitch.<key>
PITCH_MAKE="Anicca is a self-funding Buddhist AI entity. Ends suffering by every {{profile.lateness.stakeholders.senderType}} means: an iOS affirmation app, ambient music on Spotify, stand-up comedy practice, daily research blog, and a one-drink cafe in Shinjuku. 10% of every dollar earned auto-distributes as basic income (Stripe Connect, monthly). Live MRR \$$MRR. $FOLLOWERS followers. $WEEKLY_VIEWS weekly views. Open source. Public ledger."
PITCH_HOWFAR="Live: aniccaai.com (root dashboard with live numbers). iOS app shipped. 7+ Stripe products live. Basic-income transfers automated. 100+ OpenClaw cron jobs running 24/7. $FOLLOWERS followers across TikTok/YT/IG. $WEEKLY_VIEWS weekly views. Public github."
PITCH_MONEY="Stripe MRR \$$MRR live across iOS + 7 web subscriptions. 10% auto-routed to basic-income recipients monthly. Spend \$$SPEND/mo (Railway, Supabase, Anthropic API, Stripe fees). Profit \$$PROFIT/mo. Plan: replicate Anicca across niches — each new instance gets its own wallet and 10 humans on basic income."
PITCH_IDEAS="Anicca-ios, Letter, IGlowup, ClearPDF, ColdCraft, SignatureCraft, DeepworkFM, Monk products, Tomb-AI, comedy practice, Shinjuku cafe, music stockmusic, autonomous YC application loop."

PROG_USERNUMS="Live MRR \$$MRR. $FOLLOWERS followers across channels. $WEEKLY_VIEWS weekly views. iOS App Store live; 7+ Stripe products active."
PROG_REVSRC="Stripe direct (web subs) + RevenueCat (iOS in-app). Live numbers at aniccaai.com/dashboard.json."
PROG_GROWTH="Goal: \$10k MRR by YYYY-MM-DD. Current \$$MRR. Adding products weekly via OpenClaw factory crons."

# --- 3. Iterate fields, resolve value_source ---
> "$PAYLOAD_FILE.tmp"
> "$KDENSE_FILE"
echo "{}" > "$PAYLOAD_FILE.tmp"

PAGES_COUNT=$(jq '.pages | length' "$SPEC")

for ((p=0; p<PAGES_COUNT; p++)); do
  PAGE_NAME=$(jq -r ".pages[$p].name" "$SPEC")
  FIELDS_COUNT=$(jq ".pages[$p].fields | length" "$SPEC")

  for ((f=0; f<FIELDS_COUNT; f++)); do
    FIELD=$(jq -c ".pages[$p].fields[$f]" "$SPEC")
    FNAME=$(echo "$FIELD" | jq -r '.name')
    SRC=$(echo "$FIELD"   | jq -r '.value_source')
    KDENSE=$(echo "$FIELD"| jq -r '.kdense_invoke // false')

    VALUE=""

    if [ "$KDENSE" = "true" ]; then
      SKILL_NAME=$(echo "$SRC" | sed 's/^skill://')
      SECTION=$(echo "$FIELD" | jq -r '.section // .name')
      LANG=$(echo   "$FIELD" | jq -r '.language // "en"')
      TARGET=$(echo "$FIELD" | jq -r '.target_chars // .target_words // 500')
      cat >> "$KDENSE_FILE" <<EOF

## $PAGE_NAME / $FNAME  ←  invoke skill: $SKILL_NAME
- section: $SECTION
- language: $LANG
- target: $TARGET
- live snapshot: mrr=\$$MRR  followers=$FOLLOWERS

> Agent must read ~/.openclaw/skills/$SKILL_NAME/SKILL.md and follow it to produce the section text.
> Write the result to $DRAFT_DIR/$FNAME.md, then call:
>   jq '. + {"$FNAME": \$txt}' --arg txt "\$(cat $DRAFT_DIR/$FNAME.md)" $PAYLOAD_FILE > $PAYLOAD_FILE.new && mv $PAYLOAD_FILE.new $PAYLOAD_FILE

EOF
      if [ "$DRY_RUN" = "true" ]; then
        VALUE="[DRAFT REQUESTED — agent will invoke skill:$SKILL_NAME for section '$SECTION' (~$TARGET ${LANG}) — see $KDENSE_FILE]"
      else
        # In live mode, leave a placeholder; the parent agentTurn fills it.
        VALUE="__KDENSE_PENDING__:$SKILL_NAME:$FNAME"
      fi
    elif [[ "$SRC" == config.* ]]; then
      KEY="${SRC#config.}"
      VALUE=$(jq -r ".config.$KEY // empty" "$SPEC")
    elif [[ "$SRC" == env:* ]]; then
      ENV_VAR="${SRC#env:}"
      VALUE="${!ENV_VAR:-}"
    elif [[ "$SRC" == literal:* ]]; then
      VALUE="${SRC#literal:}"
    elif [[ "$SRC" == live:pitch.make ]];          then VALUE="$PITCH_MAKE"
    elif [[ "$SRC" == live:pitch.howfar ]];        then VALUE="$PITCH_HOWFAR"
    elif [[ "$SRC" == live:pitch.money ]];         then VALUE="$PITCH_MONEY"
    elif [[ "$SRC" == live:pitch.ideas ]];         then VALUE="$PITCH_IDEAS"
    elif [[ "$SRC" == live:progress.usernums ]];   then VALUE="$PROG_USERNUMS"
    elif [[ "$SRC" == live:progress.revenuesource ]]; then VALUE="$PROG_REVSRC"
    elif [[ "$SRC" == live:progress.growthrate ]]; then VALUE="$PROG_GROWTH"
    elif [[ "$SRC" == live:progress.monthly_revenue ]]; then
      VALUE="[0,0,0,0,0,$(printf '%.0f' "$MRR")]"
    else
      VALUE="[unresolved:$SRC]"
    fi

    # Append to payload
    jq --arg page "$PAGE_NAME" --arg name "$FNAME" --arg val "$VALUE" \
       '. + {($page+"."+$name): $val}' "$PAYLOAD_FILE.tmp" > "$PAYLOAD_FILE.tmp.new"
    mv "$PAYLOAD_FILE.tmp.new" "$PAYLOAD_FILE.tmp"
  done
done

mv "$PAYLOAD_FILE.tmp" "$PAYLOAD_FILE"
echo "  payload → $PAYLOAD_FILE"
echo "  kdense  → $KDENSE_FILE"

# Persist a 'latest' pointer for submit.sh
echo "$PAYLOAD_FILE" > "$DRAFT_DIR/.latest_payload"

# --- 4. Summary ---
TOTAL_FIELDS=$(jq 'length' "$PAYLOAD_FILE")
KDENSE_COUNT=$(grep -c '^## ' "$KDENSE_FILE" 2>/dev/null || echo 0)
echo "  fields=$TOTAL_FIELDS  kdense_drafts_required=$KDENSE_COUNT"

if [ "$DRY_RUN" = "true" ]; then
  echo ""
  echo "── DRY-RUN field plan ──"
  jq -r 'to_entries[] | "  \(.key): \(.value | tostring | .[0:120])"' "$PAYLOAD_FILE"
  echo "── end plan ──"
fi
