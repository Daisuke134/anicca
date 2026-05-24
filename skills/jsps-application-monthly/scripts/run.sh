#!/usr/bin/env bash
# jsps-application-monthly — pick a JSPS/JST grant and hand off to apply-to-funder.
#
# Env:
#   MODE          run                       (default: run)
#   DRY_RUN       true | false              (default: false; cron sets JSPS_DRY_RUN→DRY_RUN)
#   JSPS_DRY_RUN  alias for DRY_RUN (cron-friendly env name)
#   FORCE_FUNDER  bypass picker, use this funder id directly
#   SKILL_DIR     override base
#
# Picker:
#   candidate = guides.json ∪ portfolio_jsps_funders
#   filter by: deadline within 60 days OR always-eligible
#   score by:  topic_match  + (verified_bonus if spec exists)
#   pick:      argmax

set -uo pipefail

SKILL_DIR="${SKILL_DIR:-$HOME/.openclaw/skills/jsps-application-monthly}"
FUNDER_SKILL="${FUNDER_SKILL:-$HOME/.openclaw/skills/apply-to-funder}"
{{profile.education.institution}}_FUNDS_DIR="${{{profile.education.institution}}_FUNDS_DIR:-$HOME/.openclaw/skills/naist-funds}"
PORTFOLIO_FILE="${PORTFOLIO_FILE:-$HOME/.openclaw/state/funder-portfolio.json}"

MODE="${MODE:-run}"
DRY_RUN="${DRY_RUN:-${JSPS_DRY_RUN:-false}}"
FORCE_FUNDER="${FORCE_FUNDER:-}"

mkdir -p "$SKILL_DIR/data"
TOPICS_FILE="$SKILL_DIR/data/research-topics.json"
LAST_PICK_FILE="$SKILL_DIR/data/last-pick.json"
MISSING_LOG="$SKILL_DIR/data/missing-specs.log"

# Seed topics on first run
if [ ! -f "$TOPICS_FILE" ]; then
  cat > "$TOPICS_FILE" <<'EOF'
{
  "topics": [
    "AI economic agency",
    "GDP attribution from AI activity",
    "Oogiri-bench Japanese humor benchmark",
    "AI responsibility and accountability",
    "AI mindfulness contemplative computing",
    "Autonomous algorithmic basic-income distribution",
    "Public-ledger AI philanthropy"
  ]
}
EOF
fi

echo "▶ jsps-application-monthly  mode=$MODE  dry_run=$DRY_RUN  force=$FORCE_FUNDER"

# --- 1. Build candidate pool ---
declare -a CAND_IDS=()
declare -a CAND_NAMES=()
declare -a CAND_DEADLINES=()
declare -a CAND_SUMMARIES=()

# 1a. naist-funds guides.json
GUIDES="${{profile.education.institution}}_FUNDS_DIR/data/guides.json"
if [ -f "$GUIDES" ]; then
  GCOUNT=$(jq '.guides | length' "$GUIDES")
  for ((i=0; i<GCOUNT; i++)); do
    G_ID=$(jq -r   ".guides[$i].id"          "$GUIDES")
    G_NAME=$(jq -r ".guides[$i].name"        "$GUIDES")
    G_DL=$(jq -r   ".guides[$i].deadline"    "$GUIDES")
    G_KW=$(jq -r   ".guides[$i].keywords | join(\" \")" "$GUIDES")
    CAND_IDS+=("$G_ID");          CAND_NAMES+=("$G_NAME")
    CAND_DEADLINES+=("$G_DL");    CAND_SUMMARIES+=("$G_KW")
  done
fi

# 1b. funder-portfolio.json (entries tagged jsps/jst)
if [ -f "$PORTFOLIO_FILE" ]; then
  FCOUNT=$(jq '.funders | length' "$PORTFOLIO_FILE")
  for ((i=0; i<FCOUNT; i++)); do
    TAGS=$(jq -r ".funders[$i].tags // [] | join(\" \")" "$PORTFOLIO_FILE")
    if echo "$TAGS" | grep -qiE 'jsps|kakenhi|学振|科研費|jst|presto|さきがけ|create|crest'; then
      F_ID=$(jq -r   ".funders[$i].id"            "$PORTFOLIO_FILE")
      F_DL=$(jq -r   ".funders[$i].next_deadline" "$PORTFOLIO_FILE")
      CAND_IDS+=("$F_ID");          CAND_NAMES+=("$F_ID")
      CAND_DEADLINES+=("$F_DL");    CAND_SUMMARIES+=("$TAGS")
    fi
  done
fi

echo "  candidate pool: ${#CAND_IDS[@]} entries"
for ((i=0; i<${#CAND_IDS[@]}; i++)); do
  echo "    - ${CAND_IDS[$i]}  deadline=${CAND_DEADLINES[$i]}  name=\"${CAND_NAMES[$i]}\""
done

# --- 2. Pick ---
PICKED_ID=""
if [ -n "$FORCE_FUNDER" ]; then
  PICKED_ID="$FORCE_FUNDER"
  echo "  forcing funder=$PICKED_ID"
else
  TODAY=$(date +%Y-%m-%d)
  TODAY_TS=$(date +%s)
  BEST_SCORE=-999
  BEST_IDX=-1
  for ((i=0; i<${#CAND_IDS[@]}; i++)); do
    SCORE=0
    DL="${CAND_DEADLINES[$i]}"

    # deadline filter
    if [[ "$DL" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
      DL_TS=$(date -j -f %Y-%m-%d "$DL" +%s 2>/dev/null || date -d "$DL" +%s 2>/dev/null || echo 0)
      DAYS=$(( (DL_TS - TODAY_TS) / 86400 ))
      if [ $DAYS -lt 0 ]; then SCORE=$((SCORE - 100))            # past — heavy penalty
      elif [ $DAYS -lt 60 ]; then SCORE=$((SCORE + 50))          # within window
      else SCORE=$((SCORE + 5)); fi                              # later — small credit
    else
      # textual deadline like "毎年5月頃" or null → eligible, mild credit
      SCORE=$((SCORE + 10))
    fi

    # topic match
    SUMMARY="${CAND_SUMMARIES[$i]}"
    while read -r topic; do
      [ -z "$topic" ] && continue
      # any keyword from topic in summary?
      if echo "$SUMMARY" | grep -qi "$(echo "$topic" | awk '{print $1}')"; then
        SCORE=$((SCORE + 3))
      fi
    done < <(jq -r '.topics[]' "$TOPICS_FILE")

    # spec-exists bonus
    if [ -f "$FUNDER_SKILL/funders/${CAND_IDS[$i]}.json" ]; then
      SCORE=$((SCORE + 20))
    fi

    # avoid re-picking the very last one
    LAST_ID=$(jq -r '.id // ""' "$LAST_PICK_FILE" 2>/dev/null || echo "")
    if [ "${CAND_IDS[$i]}" = "$LAST_ID" ]; then
      SCORE=$((SCORE - 15))
    fi

    echo "    score ${CAND_IDS[$i]} = $SCORE"
    if [ $SCORE -gt $BEST_SCORE ]; then BEST_SCORE=$SCORE; BEST_IDX=$i; fi
  done

  [ $BEST_IDX -lt 0 ] && { echo "🚨 no candidates"; exit 1; }
  PICKED_ID="${CAND_IDS[$BEST_IDX]}"
  echo "  pick → $PICKED_ID  (score=$BEST_SCORE  name=\"${CAND_NAMES[$BEST_IDX]}\")"
fi

# --- 3. Spec exists? ---
SPEC="$FUNDER_SKILL/funders/$PICKED_ID.json"
if [ ! -f "$SPEC" ]; then
  TS=$(date -u +%FT%TZ)
  echo "🚨 funder spec missing for '$PICKED_ID'."
  echo "   Create $SPEC  (see yc-w26.json or jsps-grant-in-aid.json for schema)"
  echo "$TS  missing=$PICKED_ID  picker_run=jsps-application-monthly" >> "$MISSING_LOG"
  echo "   Logged to $MISSING_LOG"
  exit 3
fi

# --- 4. Persist last-pick ---
jq -n --arg id "$PICKED_ID" --arg ts "$(date -u +%FT%TZ)" \
  '{id:$id, picked_at:$ts}' > "$LAST_PICK_FILE"

# --- 5. Hand off to apply-to-funder ---
echo ""
echo "▶ handing off to apply-to-funder  funder=$PICKED_ID  dry_run=$DRY_RUN"
# IMPORTANT: clear our SKILL_DIR before the child call, otherwise apply-to-funder
# inherits jsps-application-monthly's SKILL_DIR and looks for funders/ in the wrong place.
SKILL_DIR="$FUNDER_SKILL" DRY_RUN="$DRY_RUN" MODE=submit \
  bash "$FUNDER_SKILL/scripts/run.sh" --funder "$PICKED_ID"
RC=$?
echo "  apply-to-funder rc=$RC"
exit $RC
