#!/usr/bin/env bash
# pick-region.sh — return the substrate+region with FEWEST live children.
# See SKILL.md for why. Pure bash + jq, no LLM call.
# Compatible with bash 3.2 (macOS default) — uses indexed arrays.
set -u

LINEAGE="${HOME}/.openclaw/workspace/ops/lineage.jsonl"
SUBSTRATE_HINT="${1:-}"     # optional pin — caller may force "conway" or "hetzner"
SURPLUS_TIER="${ANICCA_SURVIVAL_TIER:-normal}"   # set by budget-watcher

# All supported targets (HARD-CODED — never invent regions).
ALL_TARGETS=(
  "conway:auto"
  "e2b:us-east-1"
  "e2b:us-west-2"
  "e2b:eu-central-1"
  "hetzner:nbg1"
  "hetzner:fsn1"
  "hetzner:hel1"
  "hetzner:ash"
)

# When budget is tight, restrict to Conway only.
case "${SURPLUS_TIER}" in
  low_compute|critical|dead-grace) ALL_TARGETS=("conway:auto") ;;
esac

# Apply substrate hint (caller may have already chosen).
if [ -n "${SUBSTRATE_HINT}" ]; then
  FILTERED=()
  for T in "${ALL_TARGETS[@]}"; do
    case "$T" in "${SUBSTRATE_HINT}":*) FILTERED+=("$T") ;; esac
  done
  ALL_TARGETS=("${FILTERED[@]}")
fi

[ "${#ALL_TARGETS[@]}" -gt 0 ] || { echo "conway:auto"; exit 0; }

# Parallel arrays: COUNT_KEY[i] -> COUNT_VAL[i]. Initialise to 0.
COUNT_KEY=("${ALL_TARGETS[@]}")
COUNT_VAL=()
for _ in "${ALL_TARGETS[@]}"; do COUNT_VAL+=("0"); done

# Helper to bump a key's counter.
bump_target() {
  local needle="$1"
  local i
  for i in "${!COUNT_KEY[@]}"; do
    if [ "${COUNT_KEY[$i]}" = "$needle" ]; then
      COUNT_VAL[$i]=$((COUNT_VAL[i] + 1))
      return 0
    fi
  done
}

if [ -f "${LINEAGE}" ]; then
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    status=$(printf '%s' "$line" | jq -r '.status // "unknown"' 2>/dev/null) || continue
    case "$status" in dead|cleaned_up|failed) continue ;; esac
    sub=$(printf '%s' "$line" | jq -r '.substrate // "conway"' 2>/dev/null)
    reg=$(printf '%s' "$line" | jq -r '.region // "auto"' 2>/dev/null)
    bump_target "${sub}:${reg}"
  done < "${LINEAGE}"
fi

BEST_IDX=0
BEST_COUNT=${COUNT_VAL[0]}
for i in "${!COUNT_KEY[@]}"; do
  if [ "${COUNT_VAL[$i]}" -lt "$BEST_COUNT" ]; then
    BEST_IDX=$i
    BEST_COUNT=${COUNT_VAL[$i]}
  fi
done

echo "${COUNT_KEY[$BEST_IDX]}"
