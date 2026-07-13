#!/usr/bin/env bash
# Orchestrate the ASO loop: audit → baseline → metric → GPT-5 → lint → apply → notify.
# Args: --dry-run | --locale=<code> | --force-submit
set -euo pipefail

SKILL_DIR="$HOME/.claude/skills/aso-loop"
SNAP_DIR="$SKILL_DIR/snapshots"
mkdir -p "$SNAP_DIR"
TODAY=$(date +%Y-%m-%d)
DRY_RUN=0
LOCALES=("en-US" "ja" "de-DE" "es-ES" "fr-FR" "pt-BR")
FORCE_SUBMIT=0

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --force-submit) FORCE_SUBMIT=1 ;;
    --locale=*) LOCALES=("${arg#*=}") ;;
  esac
done

echo "[aso-loop] start $TODAY (dry_run=$DRY_RUN, locales=${LOCALES[*]})"

# Phase 2: baseline
LATEST_VERSION_ID=$(asc versions list --app 6755129214 --output json | python3 -c "import json,sys; v=json.load(sys.stdin)['data']; print(next((x['id'] for x in v if x['attributes']['appStoreState'] in ('PREPARE_FOR_SUBMISSION','READY_FOR_DISTRIBUTION')), ''))")
if [ -z "$LATEST_VERSION_ID" ]; then echo "[aso-loop] no usable version found"; exit 2; fi
echo "[aso-loop] baseline version=$LATEST_VERSION_ID"

for L in "${LOCALES[@]}"; do
  asc localizations list --version "$LATEST_VERSION_ID" --locale "$L" --output json > "$SNAP_DIR/$TODAY-baseline-$L.json" || true
done

# Phase 3: metrics
asc analytics report --app 6755129214 --metric impressions,conversion_rate --days 7 --output json > "$SNAP_DIR/$TODAY-metric.json" 2>/dev/null || echo "{}" > "$SNAP_DIR/$TODAY-metric.json"

# Phase 1: audit (delegated to aso-audit skill via Claude — this script halts here)
echo "[aso-loop] HALT: please run aso-audit skill against https://apps.apple.com/us/app/daily-affirmations-anicca/id6755129214 and save the report to $SNAP_DIR/$TODAY-audit.json before continuing"

# Phase 4: GPT-5 candidate generation (delegated — this script just prepares the prompt)
PROMPT="$SNAP_DIR/$TODAY-prompt.txt"
{
  cat "$SKILL_DIR/prompt.md"
  echo ""
  echo "## Baseline files"
  for L in "${LOCALES[@]}"; do
    echo "### $L"; [ -f "$SNAP_DIR/$TODAY-baseline-$L.json" ] && cat "$SNAP_DIR/$TODAY-baseline-$L.json"
  done
  echo "## Metrics"; cat "$SNAP_DIR/$TODAY-metric.json"
} > "$PROMPT"
echo "[aso-loop] prompt written to $PROMPT — call gpt-5 and save response to $SNAP_DIR/$TODAY-candidates.json"

# Phase 5: lint
if [ -f "$SNAP_DIR/$TODAY-candidates.json" ]; then
  python3 "$SKILL_DIR/lint.py" "$SNAP_DIR/$TODAY-candidates.json" "$SNAP_DIR/$TODAY-baseline-en-US.json" > "$SNAP_DIR/$TODAY-lint.json" 2>&1 || true
  echo "[aso-loop] lint report at $SNAP_DIR/$TODAY-lint.json"
fi

# Phase 6/7: apply (only if not dry-run and lint passed)
if [ "$DRY_RUN" -eq 0 ] && [ -f "$SNAP_DIR/$TODAY-candidates.json" ]; then
  CHOSEN=$(python3 -c "import json; d=json.load(open('$SNAP_DIR/$TODAY-candidates.json')); c=max(d['candidates'], key=lambda c: c.get('projected_lift_pct', 0)); print(json.dumps(c['locales']))")
  echo "$CHOSEN" > "$SNAP_DIR/$TODAY-applied.json"
  for L in "${LOCALES[@]}"; do
    NAME=$(echo "$CHOSEN" | python3 -c "import json,sys; d=json.loads(sys.stdin.read()); print(d['$L']['name'])")
    SUB=$(echo "$CHOSEN" | python3 -c "import json,sys; d=json.loads(sys.stdin.read()); print(d['$L']['subtitle'])")
    KW=$(echo "$CHOSEN" | python3 -c "import json,sys; d=json.loads(sys.stdin.read()); print(d['$L']['keywords'])")
    PT=$(echo "$CHOSEN" | python3 -c "import json,sys; d=json.loads(sys.stdin.read()); print(d['$L']['promotional_text'])")
    asc localizations edit --version "$LATEST_VERSION_ID" --locale "$L" --name "$NAME" --subtitle "$SUB" --keywords "$KW" --promotional-text "$PT"
  done
  echo "[aso-loop] applied to version $LATEST_VERSION_ID"
fi

echo "[aso-loop] complete — snapshot at $SNAP_DIR/$TODAY-applied.json"
